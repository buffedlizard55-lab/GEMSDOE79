#!/usr/bin/env python3
"""G79-STEPCO S1: one preregistered experiment (registry/preregistration_g79stepco_20261022.json).

Order is mandatory: features -> leakage canaries -> two-seed buffered
hide-and-recover vs matched controls -> (only then) final fit -> surface
uniqueness -> placement -> final uniqueness -> shared-writer GeoTIFF.
Shared vendor tools (evaluate_holdout, submission_writer, uniqueness) are
used unmodified. No upload, no slot selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator
from gems57 import uniqueness as shared
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw
from gems57.submission_writer import write_submission
from gems79 import stepco
from gems79.placement import place
import run_experiment  # reuse the exact canary implementation from the E1 lane

BUDGET = 37654
CACHE = ROOT / ".cache/stepco"
EV = ROOT / "evidence/stepco"
SEEDS = (20, 30)
HGB = dict(max_iter=250, learning_rate=0.06, max_leaf_nodes=63,
           min_samples_leaf=40, l2_regularization=1.0, random_state=79)
D28_SHA256 = "3e78737f0da8dd2ca66cc6caac0ce8eeefcd6715707f8d1bd3091845cd9bcc30"
H33_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
EPROBA_SHA256 = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(p: Path, v) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, allow_nan=False) + "\n")


def build_features(grid):
    receipt_p = EV / "feature_receipt.json"
    if receipt_p.exists() and (CACHE / "support.npy").exists():
        r = json.loads(receipt_p.read_text())
        if all((CACHE / f"{n}.npy").exists() for n in r["feature_names"]):
            print("STEPCO features: cache present", flush=True)
            return r
    r = stepco.build(
        ROOT / "data/raw/training_features.tif",
        ROOT / "data/raw/external/lidar_scarp_features_u8.tif",
        ROOT / "data/raw/external/geodawn_rad_u8.tif",
        ROOT / "data/raw/external/geodawn_extensions_u8.tif",
        grid.footprint, CACHE)
    r["file_sha256"] = {n: sha256_file(CACHE / f"{n}.npy") for n in r["feature_names"]}
    r["support_sha256"] = sha256_file(CACHE / "support.npy")
    r["input_sha256"] = {
        "training_features.tif": sha256_file(ROOT / "data/raw/training_features.tif"),
        "lidar_scarp_features_u8.tif": sha256_file(ROOT / "data/raw/external/lidar_scarp_features_u8.tif"),
        "geodawn_rad_u8.tif": sha256_file(ROOT / "data/raw/external/geodawn_rad_u8.tif"),
        "geodawn_extensions_u8.tif": sha256_file(ROOT / "data/raw/external/geodawn_extensions_u8.tif"),
    }
    write_json(receipt_p, r)
    return r


def registry_records():
    """Verified registry rasters restored into .cache/clones (git-blob + sha pins)."""
    cache_p = CACHE / "registry_records.json"
    if cache_p.exists():
        return json.loads(cache_p.read_text())
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    by_blob = {r["blob"]: r for r in index["rasters"]}
    found = {}
    for tif in sorted((ROOT / ".cache/clones").rglob("*.tif")):
        data = tif.read_bytes()
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if blob in pins and blob not in found:
            sha = hashlib.sha256(data).hexdigest()
            if sha == pins[blob]["sha256"] and len(data) == by_blob[blob]["size"]:
                row = by_blob[blob]
                found[blob] = {"repo": row["repo"], "path": row["path"], "blob": blob,
                               "sha256": sha, "file": str(tif),
                               "submission": row["repo"] + ":" + row["path"]}
    records = sorted(found.values(), key=lambda r: (r["repo"], r["path"]))
    out = {"records": records, "verified": len(records),
           "indexed_total": len(index["rasters"]),
           "all_pin_sha256": sorted(p["sha256"] for p in pins.values())}
    CACHE.mkdir(parents=True, exist_ok=True)
    write_json(cache_p, out)
    print(f"registry verified restored: {len(records)}/{len(index['rasters'])}", flush=True)
    return out


def vendor_inventory(records, complete: bool):
    return {"rasters": [{"repo_first": r["repo"], "sources": [r["submission"]],
                          "cache_file": r["file"], "sha256": r["sha256"]} for r in records],
            "complete_accessible_scan": complete, "errors": []}


def load_features(names):
    return {n: np.load(CACHE / f"{n}.npy", mmap_mode="r") for n in names}


def sample_matrix(features, names, flat_idx):
    X = np.empty((len(flat_idx), len(names)), np.float32)
    for j, n in enumerate(names):
        X[:, j] = np.asarray(features[n]).ravel()[flat_idx]
    return X


def fit_model(features, names, grid, support, positives_mask, rng_seed):
    d_pos = ndi.distance_transform_edt(~positives_mask)
    neg_pool = np.flatnonzero(support & grid.footprint & ~positives_mask & (d_pos > 3))
    rng = np.random.default_rng(rng_seed)
    neg_idx = rng.choice(neg_pool, size=min(240_000, len(neg_pool)), replace=False)
    pos_idx = np.flatnonzero(support & positives_mask)
    X = sample_matrix(features, names, np.r_[pos_idx, neg_idx])
    y = np.r_[np.ones(len(pos_idx), np.uint8), np.zeros(len(neg_idx), np.uint8)]
    w = np.r_[np.full(len(pos_idx), 0.5 / len(pos_idx)),
              np.full(len(neg_idx), 0.5 / len(neg_idx))].astype(np.float64)
    model = HistGradientBoostingClassifier(**HGB)
    model.fit(X, y, sample_weight=w)
    info = {"n_positive": int(len(pos_idx)), "n_negative_proxy": int(len(neg_idx)),
            "hyperparameters": HGB, "rng_seed": rng_seed}
    return model, info


def predict_surface(model, features, names, shape, out_path):
    out = np.lib.format.open_memmap(out_path, mode="w+", dtype=np.float32, shape=shape)
    rows = 256
    for y0 in range(0, shape[0], rows):
        y1 = min(shape[0], y0 + rows)
        X = np.empty(((y1 - y0) * shape[1], len(names)), np.float32)
        for j, n in enumerate(names):
            X[:, j] = np.asarray(features[n][y0:y1]).ravel()
        out[y0:y1] = model.predict_proba(X)[:, 1].reshape(y1 - y0, shape[1]).astype(np.float32)
        del X
    out.flush()
    del out
    return np.load(out_path, mmap_mode="r")


def holdout_seed(grid, features, names, support, seed, d28_pos, exclude):
    use = [n for n in names if n not in exclude]
    feats_use = {n: features[n] for n in use}
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    t0 = time.time()
    rows = run_experiment.canaries(feats_use, folds, seed)
    bad = [r for r in rows if r["suspicious"]]
    write_json(EV / f"canaries_s1_seed{seed}.json",
               {"passed": not bad, "threshold": 0.90, "rows": rows,
                "evidence_class": "LEAKAGE-CANARY", "evaluator_version": evaluator.VERSION,
                "max_symmetric_auc": max(r["symmetric_auc"] for r in rows),
                "worst": max(rows, key=lambda r: r["symmetric_auc"])})
    print(f"seed {seed} canaries: {len(rows)} tests, max symmetric AUC "
          f"{max(r['symmetric_auc'] for r in rows):.4f} ({time.time()-t0:.0f}s)", flush=True)
    if bad:
        raise SystemExit(f"CANARY FAIL seed {seed}: {bad[:3]}")

    visible = folds[0]["visible"]
    model, fit_info = fit_model(feats_use, use, grid, support, visible, 790_000 + seed)
    surface = predict_surface(model, feats_use, use, grid.shape,
                              CACHE / f"surface_s1_seed{seed}.npy")
    # surface-as-feature canary diagnostic (fitted on visible only)
    surf_auc = []
    for fold in folds:
        active = fold["region"] & ~fold["masked_known"]
        truth = active & fold["truth"]
        neg = active & (ndi.distance_transform_edt(~truth) > 3) & (ndi.distance_transform_edt(~fold["visible"]) > 3)
        pi, ni = np.flatnonzero(truth), np.flatnonzero(neg)
        rng = np.random.default_rng(seed * 100 + fold["fold"])
        if len(ni) > 100_000:
            ni = rng.choice(ni, 100_000, replace=False)
        idx = np.r_[pi, ni]
        auc = float(roc_auc_score(np.r_[np.ones(len(pi)), np.zeros(len(ni))],
                                   np.asarray(surface).ravel()[idx]))
        surf_auc.append({"fold": fold["name"], "auc": auc,
                          "symmetric_auc": max(auc, 1 - auc)})

    rng_surface = np.random.default_rng(79221022).random(grid.shape, dtype=np.float32)
    terms, per_fold, placements = {}, [], []
    arm_surfaces = {"candidate": surface, "uniform_control": rng_surface,
                    "dem_step_only_control": features["det_elev_step"]}
    for fold in folds:
        ys, xs = np.nonzero(fold["region"])
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = (sy, sx)
        local_fold = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
        allowed = support[sl] & fold["region"][sl] & (d_vis > 2)
        budget = int(round(BUDGET * fold["region"].sum() / grid.footprint.sum()))
        for name, surf in arm_surfaces.items():
            dots, pl = place(np.asarray(surf[sl], dtype=np.float32), allowed, budget)
            res, bt = evaluator.evaluate(dots.astype(np.float32), local_fold,
                                         grid.footprint[sl], origin=(sy.start, sx.start),
                                         global_shape=grid.shape)
            terms[name] = terms.get(name, np.zeros_like(bt)) + bt
            per_fold.append({"arm": name, "fold": fold["name"], **res})
            placements.append({"arm": name, "fold": fold["name"], **pl})
            print(f"HOLDOUT-DTI seed={seed} {fold['name']} {name}: {res['dti']:.4f} "
                  f"n_truth={res['n_truth']} emitted={res['n_emitted']}", flush=True)
        h33 = (d28_pos[sl] & fold["region"][sl] & (d_vis > 2)).astype(np.float32)
        res, bt = evaluator.evaluate(h33, local_fold, grid.footprint[sl],
                                     origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", np.zeros_like(bt)) + bt
        per_fold.append({"arm": "h33_foldfair_control", "fold": fold["name"], **res})
        print(f"HOLDOUT-DTI seed={seed} {fold['name']} h33_foldfair_control: {res['dti']:.4f} "
              f"emitted={res['n_emitted']}", flush=True)
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    summary.update(seed=seed, fit=fit_info, surface_canary_diagnostic=surf_auc,
                   fold_receipts=[f["receipt"] for f in folds], per_fold=per_fold,
                   placement=placements, features_used=use,
                   evidence_class="HOLDOUT-DTI")
    write_json(EV / f"holdout_s1_seed{seed}.json", summary)
    return summary


def matched_budget_overlap(my_dots, their_values, footprint, budget=BUDGET):
    ep = np.where(footprint & np.isfinite(their_values), their_values, 0.0)
    flat = np.flatnonzero(footprint)
    top = flat[np.argsort(-ep.ravel()[flat], kind="stable")[:budget]]
    top_mask = np.zeros(ep.shape, bool)
    top_mask.ravel()[top] = True
    return float(shared.dot_overlap(my_dots, top_mask)), int(top_mask.sum())


def uniqueness_phase(candidate, grid, records_obj, phase, my_dots=None):
    records = records_obj["records"]
    complete = records_obj["verified"] == records_obj["indexed_total"]
    inv = vendor_inventory(records, complete)
    t0 = time.time()

    def prog(i, n, row):
        if i % 50 == 0 or i == n:
            print(f"uniqueness[{phase}] {i}/{n} ({time.time()-t0:.0f}s)", flush=True)

    raw = shared.compare_array_to_registry(
        np.asarray(candidate, dtype=np.float32), inv, grid.footprint,
        include_reverse=True, progress=prog,
        expected_grid=(grid.shape, grid.crs, grid.transform))
    two = shared.two_phase_summary(raw["rows"], int(grid.footprint.sum()),
                                   expected_rasters=records_obj["indexed_total"])
    out = {"phase": phase, "shared_tool": "gems57.uniqueness.compare_array_to_registry",
           "shared_tool_sha256": sha256_file(Path(shared.__file__)),
           "registry_checked": records_obj["verified"],
           "registry_indexed_total": records_obj["indexed_total"],
           "complete_indexed_scan": complete and raw["registry_rasters_checked"] == records_obj["verified"],
           "literal_summary": {k: raw[k] for k in (
               "worst_spearman_full_footprint", "worst_rho_submission", "worst_dot_overlap",
               "worst_overlap_submission", "worst_jaccard_dot_sets", "duplicate_count",
               "unique", "byte_unique_among_checked", "pixel_unique_among_checked",
               "missing_or_invalid")},
           "two_phase_summary": two, "rows": raw["rows"]}
    if my_dots is not None:
        dense = [r for r in raw["rows"] if r.get("representation") == "continuous_surface"
                 or (r.get("their_dots", 0) / max(int(grid.footprint.sum()), 1)
                     > shared.DENSE_SUPPORT_FRACTION)]
        mb = []
        by_file = {r["submission"]: rec for r, rec in zip(raw["rows"], records)}
        for r in dense:
            rec = by_file.get(r["submission"])
            if rec is None:
                continue
            with rasterio.open(rec["file"]) as ds:
                vals = ds.read(1).astype(np.float32)
            ov, n = matched_budget_overlap(my_dots, vals, grid.footprint)
            mb.append({"submission": r["submission"], "sha256": rec["sha256"],
                       "their_positive_support": r["their_dots"],
                       "matched_budget_their_dots": n, "forward_overlap_3px": ov,
                       "literal_forward_overlap_3px": r["my_dots_within_3px_of_theirs"],
                       "spearman_full_footprint": r["spearman_full_footprint"]})
        out["matched_budget_dense"] = sorted(mb, key=lambda x: -x["forward_overlap_3px"])
        out["matched_budget_worst_overlap"] = max((m["forward_overlap_3px"] for m in mb), default=None)
    write_json(EV / f"uniqueness_s1_{phase}.json", out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exclude-features", default="",
                    help="S2 canary ablation only: comma-separated feature names to drop")
    ap.add_argument("--experiment", default="s1")
    args = ap.parse_args()
    exclude = set(filter(None, args.exclude_features.split(",")))
    started = datetime.now(timezone.utc)
    grid = load_grid(ROOT / "data/reference")
    receipt = build_features(grid)
    names = receipt["feature_names"]
    features = load_features(names)
    support = np.load(CACHE / "support.npy")
    records_obj = registry_records()
    by_sha = {r["sha256"]: r for r in records_obj["records"]}
    if D28_SHA256 not in by_sha:
        raise SystemExit("D2.8 incumbent witness (sha 3e78737f…) not restored")
    with rasterio.open(by_sha[D28_SHA256]["file"]) as ds:
        d28 = ds.read(1)
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    del d28

    summaries = [holdout_seed(grid, features, names, support, s, d28_pos, exclude) for s in SEEDS]
    gates = {}
    for s in summaries:
        sc, pd_ = s["scores"], s["paired_differences"]
        gates[f"seed_{s['seed']}"] = {
            "candidate_dti": sc["candidate"]["dti"],
            "beats_uniform_point": sc["candidate"]["dti"] > sc["uniform_control"]["dti"],
            "beats_dem_step_point": sc["candidate"]["dti"] > sc["dem_step_only_control"]["dti"],
            "beats_h33_foldfair_point": sc["candidate"]["dti"] > sc["h33_foldfair_control"]["dti"],
            "beats_h33_foldfair_ci95_above_0": pd_["h33_foldfair_control"]["ci95"][0] > 0,
            "canaries_passed": True,
        }
    holdout_pass = all(all(v.values()) if isinstance(v, dict) else v
                       for g in gates.values() for v in [g])
    holdout_pass = all(g["beats_uniform_point"] and g["beats_dem_step_point"]
                       and g["beats_h33_foldfair_ci95_above_0"] for g in gates.values())
    print(json.dumps({"holdout_gates": gates, "holdout_pass": holdout_pass}, indent=2), flush=True)

    # Final fit (full catalogue) — the surface is computed regardless so a
    # negative result remains a downloadable, clearly-labelled deliverable,
    # but placement stops if the surface duplicates a prior by rank corr.
    use = [n for n in names if n not in exclude]
    feats_use = {n: features[n] for n in use}
    model, fit_info = fit_model(feats_use, use, grid, support, grid.catalogue, 790_999)
    surface = predict_surface(model, feats_use, use, grid.shape, CACHE / "surface_s1_final.npy")
    surf_arr = np.asarray(surface)
    surf_sha = hashlib.sha256(np.ascontiguousarray(surf_arr).tobytes()).hexdigest()
    emission_surface = np.where(grid.footprint & ~grid.catalogue, surf_arr, 0.0).astype(np.float32)
    uni_surface = uniqueness_phase(emission_surface, grid, records_obj, "surface")
    worst_rho = uni_surface["two_phase_summary"]["literal_reading"]["worst_spearman_full_footprint"]
    rho_dup = bool(worst_rho is not None and worst_rho > shared.RHO_LIMIT)
    print(f"surface uniqueness: worst rho={worst_rho} duplicate_by_rho={rho_dup}", flush=True)

    state = {"experiment": args.experiment, "started_utc": started.isoformat(),
             "holdout_gates": gates, "holdout_pass": holdout_pass,
             "final_fit": fit_info, "surface_sha256": surf_sha,
             "surface_worst_rho": worst_rho, "duplicate_by_surface_rho": rho_dup,
             "excluded_features": sorted(exclude)}
    if rho_dup:
        state["verdict"] = "negative"
        state["stop_reason"] = "duplicate_surface_rank_correlation"
        write_json(EV / "experiment_s1_state.json", state)
        print(json.dumps(state, indent=2))
        return

    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    allowed = grid.footprint & support & (d_cat > 2)
    dots, placement = place(emission_surface, allowed, BUDGET, spacing=3)
    prediction = dots.astype(np.float32)
    uni_final = uniqueness_phase(prediction, grid, records_obj, "final", my_dots=dots)
    two = uni_final["two_phase_summary"]
    like = two["like_for_like_reading"]
    dup_final = bool(like["duplicate"])
    mb_worst = uni_final.get("matched_budget_worst_overlap")
    if mb_worst is not None and mb_worst > shared.OVERLAP_LIMIT:
        dup_final = True
    state.update(placement=placement, duplicate_final_dots=dup_final,
                 matched_budget_worst_overlap=mb_worst,
                 final_worst_dotfield_overlap=like["worst_forward_overlap_dot_fields"],
                 final_worst_rho=two["literal_reading"]["worst_spearman_full_footprint"],
                 literal_worst_overlap=two["literal_reading"]["worst_forward_overlap"])
    promote = bool(holdout_pass and not dup_final)
    state["verdict"] = "promote" if promote else "negative"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = "zeros" if promote else "DO-NOT-SUBMIT"
    name = f"gems79-stepco-{args.experiment}-37654dots-{stamp}-{surf_sha[:8]}-{suffix}"
    note = (f"GEMSDOE79 STEPCO {args.experiment}: multi-field step-dipole HGB, 37654 dots s3, "
            f"cat>2px; holdout-gated {stamp}")[:140]
    out = ROOT / "docs/downloads" / f"{name}.tif"
    receipt_w = write_submission(out, prediction, ROOT / "data/reference/sample_submission.tif",
                                 grid.footprint, note=note, name=name,
                                 catalogue=grid.catalogue,
                                 metadata={"lane": "G79-STEPCO", "experiment": args.experiment,
                                           "surface_sha256": surf_sha,
                                           "verdict": state["verdict"],
                                           "human_inspection_required": False})
    state.update(submission_name=name, submission_note=note,
                 submission_file=str(out.relative_to(ROOT)),
                 raster_sha256=receipt_w["sha256"], writer_receipt=receipt_w)
    state["byte_distinct_from_all_992_pins"] = receipt_w["sha256"] not in set(records_obj["all_pin_sha256"])
    state["finished_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(EV / "experiment_s1_state.json", state)
    print(json.dumps({k: state[k] for k in ("verdict", "submission_file", "raster_sha256",
                                             "holdout_pass", "duplicate_final_dots")}, indent=2))


if __name__ == "__main__":
    main()
