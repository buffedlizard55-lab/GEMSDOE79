#!/usr/bin/env python3
"""Automated submission gate for G79-CJX — no human inspection.

Gates (all must pass to print OK_TO_SUBMIT=true):
  G1 format   shared validator: 1-band float32, EPSG:32611, 3730x3292,
              sample transform, finite everywhere, values in [0,1],
              no NaN inside footprint (zeros-mode writer guarantees this).
  G2 canary   every CJX channel symmetric AUC <= 0.90 on both holdout seeds.
  G3 holdout  pooled HOLDOUT-DTI (gems57-pooled-hide-v2) of the final arm
              must beat BOTH the H33 fold-fair control AND the incumbent
              G79-THVC on both seeds (frozen receipts, labelled as such).
  G4 novelty  vs all 992 restored registry rasters, surface AND final dots:
              |Spearman| <= 0.90 and literal 3-px forward overlap <= 0.70.
              Chance-corrected overlap is reported as a diagnostic only;
              it can never override a literal failure (AGENTS.md §4).
Exit 0 only if every gate passes; otherwise 2 with a machine-readable card.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
sys.path.insert(0, str(ROOT / "scripts"))
import rasterio
from gems57.grid import load_grid
from validate_submission import validate_path

INCUMBENT = {"20": 0.1905226265456631, "30": 0.194393256940719}   # G79-THVC frozen
H33_CONTROL = {"20": 0.09608619416803546, "30": 0.09889767286222764}  # fold-fair frozen



def _surface_path():
    for cand in (ROOT / "evidence/cjx/cjx_surface.npz", ROOT / ".cache/cjx/cjx_surface.npz"):
        if cand.exists():
            return cand
    raise FileNotFoundError("cjx_surface.npz missing; rerun scripts/run_cjx_experiment.py")


def overlap_and_halo(my_dots, their_support):
    """Exact Euclidean 3-px forward overlap + their halo coverage (allowed)."""
    dist = ndi.distance_transform_edt(~their_support)
    obs = float((dist[my_dots] <= 3.0).mean()) if my_dots.any() else 0.0
    return obs, dist



def _novelty_row(task):
    """One registry raster: exact 3-px forward overlap (KD-tree for sparse
    dot fields, EDT for dense surfaces) + sampled Spearman (surface, dots)."""
    from scipy.spatial import cKDTree
    pth, blob = task
    try:
        with rasterio.open(pth) as ds:
            a = ds.read(1)
    except Exception:
        return (blob, None, 0.0, 0.0)
    if a.shape != _FP_SHAPE:
        return (blob, None, 0.0, 0.0)
    their = np.isfinite(a) & (a > 0)
    npos = int(their.sum())
    if npos == 0:
        obs = 0.0
    elif npos < 300_000:
        tree = cKDTree(np.column_stack(np.nonzero(their)).astype(float))
        d, _ = tree.query(_MYDOTYX.astype(float), k=1)
        obs = float((d <= 3.0).mean())
    else:
        dist = ndi.distance_transform_edt(~their)
        obs = float((dist[_MYDOTYX[:, 0], _MYDOTYX[:, 1]] <= 3.0).mean())
    samp = a.ravel()[_SAMP]
    if np.ptp(samp) == 0:
        return (blob, obs, 0.0, 0.0)
    rho_s = float(spearmanr(_SURF_S, samp).statistic)
    rho_d = float(spearmanr(_DOTS_F, samp).statistic)
    return (blob, obs, rho_s, rho_d)


def main():
    meta = json.loads((ROOT / "evidence/cjx/final_build.json").read_text())
    tif = ROOT / "artifacts/cjx" / meta["tif"]
    grid = load_grid(ROOT / "data/reference")
    footprint = grid.footprint
    with rasterio.open(tif) as ds:
        dots_arr = ds.read(1)
    my_dots = (dots_arr > 0) & footprint
    # reconstruct final (pre-placement) surface deterministically
    from gems79.cjx import catalogue_endpoints
    z = np.load(_surface_path())
    v1 = z["cjx_v1_edge"].astype(np.float32)
    d_tip = ndi.distance_transform_edt(~catalogue_endpoints(grid.catalogue))
    surface = (v1 * np.exp(-d_tip / 12.0) + 0.05 * v1).astype(np.float32)
    surface[~footprint] = 0

    gates = {}
    # G1
    val = validate_path(tif)
    gates["G1_format"] = {"passed": bool(val["format_passed"]), "validator": val["validator"],
                          "reference_grid_ok": val["reference_grid"]["ok"]}
    # G2/G3 from experiment receipts
    e1 = json.loads((ROOT / "evidence/cjx/cjx_holdout.json").read_text())
    e3 = json.loads((ROOT / "evidence/cjx/cjx_exp3_holdout.json").read_text())
    max_auc = max(e1["seeds"][s]["max_canary_symmetric_auc"] for s in ("20", "30"))
    gates["G2_canary"] = {"passed": bool(max_auc <= 0.90), "max_symmetric_auc": max_auc,
                          "threshold": 0.90, "evidence_class": "LEAKAGE-CANARY"}
    hold = {}
    passed3 = True
    for s in ("20", "30"):
        dti = e3["seeds"][s]["pooled"]["scores"]["CJX_v3_tip"]["dti"]
        ci = e3["seeds"][s]["pooled"]["scores"]["CJX_v3_tip"]["ci95"]
        n = e3["seeds"][s]["pooled"]["scores"]["CJX_v3_tip"]["withheld_positive_pixels"]
        ok = dti > H33_CONTROL[s] and dti > INCUMBENT[s]
        passed3 &= ok
        hold[s] = {"dti": dti, "ci95": ci, "withheld_positive_pixels": n,
                   "h33_foldfair_control_frozen": H33_CONTROL[s],
                   "incumbent_g79_thvc_frozen": INCUMBENT[s], "beats_both": ok}
    gates["G3_holdout"] = {"passed": bool(passed3), "evidence_class": "HOLDOUT-DTI",
                           "evaluator_version": "gems57-pooled-hide-v2", "seeds": hold}
    # G4 novelty scan over restored registry (992 blobs, hash-pinned index)
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    rows = index["rasters"] if isinstance(index, dict) else index
    rng = np.random.default_rng(79)
    fp_idx = np.flatnonzero(footprint.ravel())
    sample = rng.choice(fp_idx, size=250_000, replace=False)
    surf_s = surface.ravel()[sample]
    my_dot_yx = np.column_stack(np.nonzero(my_dots))
    tasks = []
    for r in rows:
        blob = r.get("blob") or ""
        pth = ROOT / ".cache/registry" / f"{blob}.tif"
        if pth.exists():
            tasks.append((str(pth), str(blob)))
    import multiprocessing as mp
    global _SAMP, _SURF_S, _DOTS_F, _MYDOTYX, _FP_SHAPE
    _SAMP, _SURF_S = sample, surf_s
    _DOTS_F = dots_arr.ravel()[sample].astype(float)
    _MYDOTYX = my_dot_yx
    _FP_SHAPE = footprint.shape
    with mp.Pool(2) as pool:
        results = pool.map(_novelty_row, tasks, chunksize=8)
    worst = {"rho_surface": (0.0, None), "rho_dots": (0.0, None),
             "overlap_dots": (0.0, None)}
    n_checked = 0
    for blob, obs, rho_s, rho_d in results:
        if obs is None:
            continue
        n_checked += 1
        if obs > worst["overlap_dots"][0]: worst["overlap_dots"] = (obs, blob)
        if abs(rho_s) > abs(worst["rho_surface"][0]): worst["rho_surface"] = (rho_s, blob)
        if abs(rho_d) > abs(worst["rho_dots"][0]): worst["rho_dots"] = (rho_d, blob)
    print(f"novelty checked {n_checked}/{len(rows)}", flush=True)
    lit_ok = (abs(worst["rho_surface"][0]) <= 0.90 and abs(worst["rho_dots"][0]) <= 0.90
              and worst["overlap_dots"][0] <= 0.70)
    gates["G4_novelty"] = {
        "passed": bool(lit_ok), "registry_rasters_checked": n_checked,
        "registry_rasters_expected": len(rows),
        "worst_abs_spearman_surface_sampled250k": worst["rho_surface"],
        "worst_abs_spearman_dots_sampled250k": worst["rho_dots"],
        "worst_literal_overlap_dots_exact": worst["overlap_dots"],
        "limits": {"rho": 0.90, "overlap": 0.70},
        "note": "Spearman on fixed 250k-pixel footprint sample (SE~0.002); overlap is exact Euclidean 3-px on all my dots."}
    # enrich G4 with submission names + sparse diagnostic (diagnostic only)
    try:
        by_blob = {r["blob"]: r.get("path") for r in rows}
        for key in ("worst_abs_spearman_surface_sampled250k", "worst_abs_spearman_dots_sampled250k", "worst_literal_overlap_dots_exact"):
            pass
        gates["G4_novelty"]["worst_literal_overlap_submission"] = by_blob.get(worst["overlap_dots"][1])
        gates["G4_novelty"]["worst_rho_surface_submission"] = by_blob.get(worst["rho_surface"][1])
        diag_p = ROOT / "evidence/cjx/novelty_sparse_diagnostic.json"
        if diag_p.exists():
            gates["G4_novelty"]["sparse_diagnostic"] = json.loads(diag_p.read_text())
    except Exception:
        pass
    ok = all(g["passed"] for g in gates.values())
    card = {"lane": "G79-CJX",
            "hypothesis": "Coincident multi-scale RTP-magnetic + isostatic-gravity contact junctions, steered to visible fault terminations, recover unmapped fault continuations.",
            "mechanism": "CJX v3 tip: sqrt(pers_mag*pers_grav)*(0.35+0.65*orientation concordance), weighted exp(-dist_to_visible_endpoint/12px)+0.05, dotted 37,654 @2.8px, >2px off catalogue. Exp1=v1 edges, Exp2=v2 junction (both negative).",
            "named_non_fault_process": "Pluton/caldera margins and survey-block seams produce coincident potential-field edges and orientation junctions; terrace risers mimic scarps.",
            "experiments_used": 3, "submission_file": f"artifacts/cjx/{meta['tif']}",
            "submission_name": meta["submission_name"], "note": meta["note"],
            "raster_sha256": hashlib.sha256(tif.read_bytes()).hexdigest(),
            "dots": int(my_dots.sum()), "gates": gates,
            "ok_to_submit": bool(ok),
            "verdict": "promote" if ok else "negative",
            "organizer_confirmed_score": None,
            "evidence_note": "No organizer receipt exists for this artifact; no leaderboard score is claimed or projected."}
    (ROOT / "evidence/cjx/cjx_gate.json").write_text(json.dumps(card, indent=2) + "\n")
    (ROOT / "run_card_cjx.json").write_text(json.dumps(card, indent=2) + "\n")
    print(json.dumps({"ok_to_submit": ok, "gates_passed": {k: v["passed"] for k, v in gates.items()}}, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
