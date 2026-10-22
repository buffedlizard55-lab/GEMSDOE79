#!/usr/bin/env python3
"""Automated submission gate for G79-CJX — no human inspection.

Default CLI invocation (`python scripts/cjx_gate.py`) enforces the closed-lane
lifecycle guard (`enforce_open_lane`) before rewriting receipts. Pass
`--verify-readonly` to verify the committed CJX GeoTIFF, ZIP, and gate receipts
on a clean checkout without requiring gitignored caches or mutating files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
sys.path.insert(0, str(ROOT / "scripts"))
import rasterio
from gems57.grid import load_grid
from gems79.lifecycle import enforce_open_lane
from validate_submission import validate_path

INCUMBENT = {"20": 0.1905226265456631, "30": 0.194393256940719}   # G79-THVC frozen
H33_CONTROL = {"20": 0.09608619416803546, "30": 0.09889767286222764}  # fold-fair frozen


def _surface_path() -> Path:
    for cand in (ROOT / "evidence/cjx/cjx_surface.npz", ROOT / ".cache/cjx/cjx_surface.npz"):
        if cand.exists():
            return cand
    raise FileNotFoundError("cjx_surface.npz missing; closed lane G79-CJX must use --verify-readonly")


def overlap_and_halo(my_dots, their_support):
    """Exact Euclidean 3-px forward overlap + their halo coverage (allowed)."""
    dist = ndi.distance_transform_edt(~their_support)
    obs = float((dist[my_dots] <= 3.0).mean()) if my_dots.any() else 0.0
    return obs, dist


def evaluate_novelty_bounds(
    *,
    n_checked: int,
    n_expected: int,
    rho_surface: float,
    rho_dots: float,
    overlap_dots: float,
) -> bool:
    """Fail-closed G4 check: incomplete registry coverage never passes."""
    if n_expected <= 0 or n_checked != n_expected:
        return False
    return (
        abs(float(rho_surface)) <= 0.90
        and abs(float(rho_dots)) <= 0.90
        and float(overlap_dots) <= 0.70
    )


def _novelty_row(task):
    """One registry raster: exact 3-px forward overlap + sampled Spearman."""
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


def _verify_readonly(root: Path = ROOT) -> dict:
    meta = json.loads((root / "evidence/cjx/final_build.json").read_text(encoding="utf-8"))
    card = json.loads((root / "run_card_cjx.json").read_text(encoding="utf-8"))
    gate_copy = json.loads((root / "evidence/cjx/cjx_gate.json").read_text(encoding="utf-8"))
    tif = root / "artifacts/cjx" / meta["tif"]
    zip_path = root / "artifacts/cjx" / meta["zip"]
    grid = load_grid(root / "data/reference")
    footprint = grid.footprint

    val = validate_path(tif)
    tif_bytes = tif.read_bytes()
    tif_sha = hashlib.sha256(tif_bytes).hexdigest()
    with rasterio.open(tif) as ds:
        dots_arr = ds.read(1)
    dots_count = int(((dots_arr > 0) & footprint).sum())

    zip_ok = False
    if zip_path.is_file():
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            zip_ok = (zf.testzip() is None) and names == [tif.name] and zf.read(tif.name) == tif_bytes

    receipt_consistent = (
        card == gate_copy
        and card.get("raster_sha256") == tif_sha == meta.get("tif_sha256")
        and card.get("dots") == dots_count == meta.get("dots")
        and len(str(card.get("note", ""))) <= 140
    )
    g1_ok = bool(val["format_passed"] and val["reference_grid"]["ok"] and zip_ok and receipt_consistent)

    e1 = json.loads((root / "evidence/cjx/cjx_holdout.json").read_text(encoding="utf-8"))
    e3 = json.loads((root / "evidence/cjx/cjx_exp3_holdout.json").read_text(encoding="utf-8"))
    max_auc = max(float(e1["seeds"][s]["max_canary_symmetric_auc"]) for s in ("20", "30"))
    g2_ok = bool(max_auc <= 0.90)

    g3_ok = True
    for s in ("20", "30"):
        dti = float(e3["seeds"][s]["pooled"]["scores"]["CJX_v3_tip"]["dti"])
        g3_ok = g3_ok and (dti > H33_CONTROL[s] and dti > INCUMBENT[s])

    nov = card.get("gates", {}).get("G4_novelty", {})
    g4_ok = evaluate_novelty_bounds(
        n_checked=int(nov.get("registry_rasters_checked", 0)),
        n_expected=int(nov.get("registry_rasters_expected", 0)),
        rho_surface=float((nov.get("worst_abs_spearman_surface_sampled250k") or [1.0])[0]),
        rho_dots=float((nov.get("worst_abs_spearman_dots_sampled250k") or [1.0])[0]),
        overlap_dots=float((nov.get("worst_literal_overlap_dots_exact") or [1.0])[0]),
    )

    gates_passed = {
        "G1_format": g1_ok,
        "G2_canary": g2_ok,
        "G3_holdout": g3_ok,
        "G4_novelty": g4_ok,
    }
    ok_to_submit = all(gates_passed.values()) and bool(card.get("ok_to_submit"))
    return {
        "lane": "G79-CJX",
        "mode": "readonly_verification",
        "ok_to_download": g1_ok,
        "ok_to_submit": ok_to_submit,
        "verdict": "promote" if ok_to_submit else "negative",
        "raster_sha256": tif_sha,
        "dots": dots_count,
        "gates_passed": gates_passed,
    }


def _recompute_and_write() -> int:
    enforce_open_lane(ROOT, "G79-CJX", reason="cjx_gate receipt rewrite")
    meta = json.loads((ROOT / "evidence/cjx/final_build.json").read_text(encoding="utf-8"))
    tif = ROOT / "artifacts/cjx" / meta["tif"]
    grid = load_grid(ROOT / "data/reference")
    footprint = grid.footprint
    with rasterio.open(tif) as ds:
        dots_arr = ds.read(1)
    my_dots = (dots_arr > 0) & footprint
    from gems79.cjx import catalogue_endpoints

    z = np.load(_surface_path())
    v1 = z["cjx_v1_edge"].astype(np.float32)
    d_tip = ndi.distance_transform_edt(~catalogue_endpoints(grid.catalogue))
    surface = (v1 * np.exp(-d_tip / 12.0) + 0.05 * v1).astype(np.float32)
    surface[~footprint] = 0

    gates = {}
    val = validate_path(tif)
    gates["G1_format"] = {
        "passed": bool(val["format_passed"] and val["reference_grid"]["ok"]),
        "validator": val["validator"],
        "reference_grid_ok": val["reference_grid"]["ok"],
    }
    e1 = json.loads((ROOT / "evidence/cjx/cjx_holdout.json").read_text(encoding="utf-8"))
    e3 = json.loads((ROOT / "evidence/cjx/cjx_exp3_holdout.json").read_text(encoding="utf-8"))
    max_auc = max(e1["seeds"][s]["max_canary_symmetric_auc"] for s in ("20", "30"))
    gates["G2_canary"] = {
        "passed": bool(max_auc <= 0.90),
        "max_symmetric_auc": max_auc,
        "threshold": 0.90,
        "evidence_class": "LEAKAGE-CANARY",
    }
    hold = {}
    passed3 = True
    for s in ("20", "30"):
        dti = e3["seeds"][s]["pooled"]["scores"]["CJX_v3_tip"]["dti"]
        ci = e3["seeds"][s]["pooled"]["scores"]["CJX_v3_tip"]["ci95"]
        n = e3["seeds"][s]["pooled"]["scores"]["CJX_v3_tip"]["withheld_positive_pixels"]
        ok = dti > H33_CONTROL[s] and dti > INCUMBENT[s]
        passed3 &= ok
        hold[s] = {
            "dti": dti,
            "ci95": ci,
            "withheld_positive_pixels": n,
            "h33_foldfair_control_frozen": H33_CONTROL[s],
            "incumbent_g79_thvc_frozen": INCUMBENT[s],
            "beats_both": ok,
        }
    gates["G3_holdout"] = {
        "passed": bool(passed3),
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": "gems57-pooled-hide-v2",
        "seeds": hold,
    }
    index = json.loads((ROOT / "registry/registry_index.json").read_text(encoding="utf-8"))
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
    worst = {"rho_surface": (0.0, None), "rho_dots": (0.0, None), "overlap_dots": (0.0, None)}
    n_checked = 0
    for blob, obs, rho_s, rho_d in results:
        if obs is None:
            continue
        n_checked += 1
        if obs > worst["overlap_dots"][0]:
            worst["overlap_dots"] = (obs, blob)
        if abs(rho_s) > abs(worst["rho_surface"][0]):
            worst["rho_surface"] = (rho_s, blob)
        if abs(rho_d) > abs(worst["rho_dots"][0]):
            worst["rho_dots"] = (rho_d, blob)
    lit_ok = evaluate_novelty_bounds(
        n_checked=n_checked,
        n_expected=len(rows),
        rho_surface=worst["rho_surface"][0],
        rho_dots=worst["rho_dots"][0],
        overlap_dots=worst["overlap_dots"][0],
    )
    gates["G4_novelty"] = {
        "passed": bool(lit_ok),
        "registry_rasters_checked": n_checked,
        "registry_rasters_expected": len(rows),
        "worst_abs_spearman_surface_sampled250k": worst["rho_surface"],
        "worst_abs_spearman_dots_sampled250k": worst["rho_dots"],
        "worst_literal_overlap_dots_exact": worst["overlap_dots"],
        "limits": {"rho": 0.90, "overlap": 0.70},
        "note": "Spearman on fixed 250k-pixel footprint sample (SE~0.002); overlap is exact Euclidean 3-px on all my dots.",
    }
    by_blob = {r["blob"]: r.get("path") for r in rows}
    gates["G4_novelty"]["worst_literal_overlap_submission"] = by_blob.get(worst["overlap_dots"][1])
    gates["G4_novelty"]["worst_rho_surface_submission"] = by_blob.get(worst["rho_surface"][1])
    diag_p = ROOT / "evidence/cjx/novelty_sparse_diagnostic.json"
    if diag_p.exists():
        gates["G4_novelty"]["sparse_diagnostic"] = json.loads(diag_p.read_text(encoding="utf-8"))
    ok = all(g["passed"] for g in gates.values())
    card = {
        "lane": "G79-CJX",
        "hypothesis": "Coincident multi-scale RTP-magnetic + isostatic-gravity contact junctions, steered to visible fault terminations, recover unmapped fault continuations.",
        "mechanism": "CJX v3 tip: sqrt(pers_mag*pers_grav)*(0.35+0.65*orientation concordance), weighted exp(-dist_to_visible_endpoint/12px)+0.05, dotted 37,654 @2.8px, >2px off catalogue. Exp1=v1 edges, Exp2=v2 junction (both negative).",
        "named_non_fault_process": "Pluton/caldera margins and survey-block seams produce coincident potential-field edges and orientation junctions; terrace risers mimic scarps.",
        "experiments_used": 3,
        "submission_file": f"artifacts/cjx/{meta['tif']}",
        "submission_name": meta["submission_name"],
        "note": meta["note"],
        "raster_sha256": hashlib.sha256(tif.read_bytes()).hexdigest(),
        "dots": int(my_dots.sum()),
        "gates": gates,
        "ok_to_submit": bool(ok),
        "verdict": "promote" if ok else "negative",
        "organizer_confirmed_score": None,
        "evidence_note": "No organizer receipt exists for this artifact; no leaderboard score is claimed or projected.",
    }
    (ROOT / "evidence/cjx/cjx_gate.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (ROOT / "run_card_cjx.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok_to_submit": ok, "gates_passed": {k: v["passed"] for k, v in gates.items()}}, indent=2))
    return 0 if ok else 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--verify-readonly",
        action="store_true",
        help="Verify committed CJX bytes and receipts read-only without rewriting files.",
    )
    args = ap.parse_args(argv)
    if args.verify_readonly:
        summary = _verify_readonly(ROOT)
        print(json.dumps(summary, indent=2, allow_nan=False))
        return 0 if summary["ok_to_submit"] else 2
    return _recompute_and_write()


if __name__ == "__main__":
    raise SystemExit(main())
