#!/usr/bin/env python3
"""G79-CJX preregistered experiment driver (registry/preregistration_cjx.json).

Stages: features -> holdout -> final.  Shared tools only:
gems57.holdout.buffered_component_draw, gems57.evaluate_holdout,
gems57.submission_writer.write_submission, gems79.placement.place.
Feature surfaces are catalogue-free, hence identical in every fold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import evaluate_holdout as ev  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems79.cjx import SIGMAS, fill_invalid, geomean2, junction_at_scale, percentile_rank  # noqa: E402
from gems79.placement import place  # noqa: E402

RAW = ROOT / "data" / "raw"
CACHE = ROOT / ".cache" / "cjx"
OUT = ROOT / "evidence" / "cjx"
BUDGET = 20_000
BUDGET_SENSITIVITY = 37_654
SPACING = 3
SEEDS = (20, 30)
FEATURES = [
    "raw_rtp_rank", "raw_grav_rank",
    "j_rtp_s1", "j_rtp_s2", "j_rtp_s4", "j_grav_s1", "j_grav_s2", "j_grav_s4",
    "pers_rtp", "pers_grav", "edge_rtp_s2", "edge_grav_s2",
    "CJXJ", "CJXFULL", "abs_tmi_hg_rank", "abs_grav_hg_rank", "EDGE",
]


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def save(name, arr):
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / f"{name}.npy", np.asarray(arr, np.float32))
    log("saved", name)


def load(name):
    return np.load(CACHE / f"{name}.npy")


def stage_features():
    grid = load_grid(RAW)
    fp = grid.footprint
    receipt = {"bands": {}, "fill_medians": {}}
    pers = {}
    edge_rank = {}
    with rasterio.open(RAW / "training_features.tif") as s:
        desc = list(s.descriptions)
        receipt["band_descriptions"] = {str(i + 1): d for i, d in enumerate(desc)}
        fields = {}
        for band, key in ((2, "rtp"), (13, "grav")):
            a = s.read(band).astype(np.float32)
            valid = np.isfinite(a) & (a > -1e30) & fp
            filled, med = fill_invalid(a, valid)
            receipt["fill_medians"][key] = med
            receipt["bands"][key] = {"band": band, "valid_footprint_cells": int(valid.sum()),
                                     "min": float(a[valid].min()), "max": float(a[valid].max())}
            fields[key] = (filled, valid)
            save(f"raw_{key}_rank", percentile_rank(filled, valid))
            del a
        for key, (filled, valid) in fields.items():
            ranks = []
            for sigma in SIGMAS:
                j, sm = junction_at_scale(filled, valid, sigma)
                save(f"j_{key}_s{int(sigma)}", j)
                ranks.append(percentile_rank(j, valid))
                if sigma == 2.0:
                    edge_rank[key] = percentile_rank(sm, valid)
                    save(f"edge_{key}_s2", edge_rank[key])
                del j, sm
            p = np.minimum(np.minimum(ranks[0], ranks[1]), ranks[2]).astype(np.float32)
            del ranks
            pers[key] = p
            save(f"pers_{key}", p)
            del filled
        # EDGE control: plain horizontal-gradient magnitudes (bands 3 and 18)
        edge_parts = []
        for band, name in ((3, "abs_tmi_hg_rank"), (18, "abs_grav_hg_rank")):
            a = s.read(band).astype(np.float32)
            valid = np.isfinite(a) & (a > -1e30) & fp
            r = percentile_rank(np.abs(a), valid)
            receipt["bands"][name] = {"band": band, "valid_footprint_cells": int(valid.sum()),
                                      "min": float(a[valid].min()), "max": float(a[valid].max()),
                                      "statistic": "percentile rank of |value|"}
            save(name, r)
            edge_parts.append(r)
            del a, r
    cjxj = geomean2(pers["rtp"], pers["grav"])
    save("CJXJ", cjxj)
    full = (cjxj * geomean2(edge_rank["rtp"], edge_rank["grav"])).astype(np.float32)
    save("CJXFULL", full)
    save("EDGE", geomean2(edge_parts[0], edge_parts[1]))
    OUT.mkdir(parents=True, exist_ok=True)
    receipt["features"] = FEATURES
    receipt["feature_files_sha256"] = {
        n: hashlib.sha256((CACHE / f"{n}.npy").read_bytes()).hexdigest() for n in FEATURES
    }
    (OUT / "feature_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    log("features done")


def allowed_global(grid):
    dcat = ndi.distance_transform_edt(~grid.catalogue)
    return grid.footprint & (dcat > 2)


def stage_holdout():
    grid = load_grid(RAW)
    fp, cat = grid.footprint, grid.catalogue
    aglob = allowed_global(grid)
    n_glob = int(aglob.sum())
    arms = ["CJXJ", "CJXFULL_20K", "CJXFULL_37654", "EDGE", "UNIFORM"]
    surfaces = {n: load(n) for n in ("CJXJ", "CJXFULL", "EDGE")}
    results = {}
    for seed in SEEDS:
        folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3)
        # --- leakage-canary sample (collected once per seed) ---
        pos_parts, neg_parts = [], []
        for fi, fold in enumerate(folds):
            pos_parts.append(np.flatnonzero(fold["region"] & fold["truth"]))
            pool = np.flatnonzero(fold["region"] & fp & ~cat)
            rng = np.random.default_rng(seed * 100 + fi)
            neg_parts.append(pool[rng.choice(pool.size, size=min(120_000, pool.size), replace=False)])
        pos = np.concatenate(pos_parts); neg = np.concatenate(neg_parts)
        del pos_parts, neg_parts
        sample = np.concatenate([pos, neg])
        y = np.zeros(sample.size); y[: pos.size] = 1.0
        canaries = {}
        for name in FEATURES:
            v = load(name).ravel()[sample].astype(np.float64)
            auc = float(roc_auc_score(y, v))
            canaries[name] = {"auc": auc, "symmetric_auc": max(auc, 1.0 - auc)}
            del v
        worst = max(canaries, key=lambda k: canaries[k]["symmetric_auc"])
        log(f"seed {seed} canary max {canaries[worst]['symmetric_auc']:.4f} ({worst}); npos={pos.size}")
        # --- arms x folds ---
        terms = {a: None for a in arms}
        fold_info = []
        rng_u = np.random.default_rng(123)
        fold_allowed = []
        for fold in folds:
            dknown = ndi.distance_transform_edt(~fold["masked_known"])
            fold_allowed.append(fold["region"] & fp & ~fold["masked_known"] & (dknown > 2))
            del dknown
        for arm in arms:
            budget_global = BUDGET_SENSITIVITY if arm == "CJXFULL_37654" else BUDGET
            surf_name = {"CJXJ": "CJXJ", "CJXFULL_20K": "CJXFULL",
                         "CJXFULL_37654": "CJXFULL", "EDGE": "EDGE"}.get(arm)
            for fi, fold in enumerate(folds):
                allowed = fold_allowed[fi]
                budget = int(round(budget_global * int(allowed.sum()) / n_glob))
                if arm == "UNIFORM":
                    surf = np.where(allowed, rng_u.random(fp.shape, dtype=np.float32), 0).astype(np.float32)
                else:
                    surf = np.where(allowed, surfaces[surf_name], 0).astype(np.float32)
                dots, info = place(surf, allowed, budget, spacing=SPACING)
                del surf
                _, term = ev.evaluate(dots.astype(np.float32), fold, fp)
                terms[arm] = term if terms[arm] is None else terms[arm] + term
                if arm == arms[0]:
                    fold_info.append({"fold": fold["name"], "allowed": int(allowed.sum())})
                fold_info[fi][arm] = {"budget": budget, "emitted": info["emitted"]}
                del dots, term
            log(f"seed {seed} arm {arm} done")
        summary = ev.pooled_summary(terms, draws=1000, seed=520810 + seed, candidate="CJXFULL_20K")
        results[f"seed{seed}"] = {
            "withheld_positive_pixels_sampled_for_canary": int(pos.size),
            "canaries": canaries,
            "canary_max_symmetric_auc": canaries[worst]["symmetric_auc"],
            "canary_worst_feature": worst,
            "canary_gate_le_0_90": bool(canaries[worst]["symmetric_auc"] <= 0.90),
            "folds": fold_info,
            "summary": summary,
        }
        log(f"seed {seed}", {k: round(v["dti"], 4) for k, v in summary["scores"].items()})
        del folds, fold_allowed, terms, sample, y, pos, neg
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "holdout_results.json").write_text(json.dumps(results, indent=2) + "\n")
    log("holdout done")


def stage_final():
    grid = load_grid(RAW)
    fp, cat = grid.footprint, grid.catalogue
    aglob = allowed_global(grid)
    surf = load("CJXFULL")
    dots, info = place(np.where(aglob, surf, 0).astype(np.float32), aglob, BUDGET, spacing=SPACING)
    log("placement", info)
    prediction = dots.astype(np.float32)
    cfg = hashlib.sha256(
        (ROOT / "registry" / "preregistration_cjx.json").read_bytes()
        + hashlib.sha256((CACHE / "CJXFULL.npy").read_bytes()).digest()
    ).hexdigest()[:10]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    name = f"gems79-cjx-junction-20000dots-{stamp}-{cfg}-zeros"
    note = "GEMSDOE79 G79-CJX: RTP x gravity persistent director junctions, catalogue-free, 20k dots s3"
    assert len(name) <= 140 and len(note) <= 140, (len(name), len(note))
    outdir = ROOT / "archive" / "g79_cjx"
    outdir.mkdir(parents=True, exist_ok=True)
    receipt = write_submission(
        outdir / f"{name}.tif", prediction, RAW / "sample_submission.tif", fp,
        note=note, name=name, catalogue=cat,
        metadata={"lane": "G79-CJX", "placement": info, "config_hash10": cfg,
                  "preregistration": "registry/preregistration_cjx.json"},
    )
    np.save(CACHE / "final_dots.npy", dots)
    (OUT / "final_receipt.json").write_text(json.dumps(
        {"submission_name": name, "note": note, "note_chars": len(note),
         "writer_receipt_file": f"archive/g79_cjx/{name}.json",
         "raster_sha256": receipt["sha256"], "zip_sha256": receipt["zip_sha256"],
         "bytes": receipt["bytes"], "placement": info}, indent=2) + "\n")
    log("final written", name, receipt["sha256"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=("features", "holdout", "final", "all"), required=True)
    args = ap.parse_args()
    t0 = time.time()
    if args.stage in ("features", "all"):
        stage_features()
    if args.stage in ("holdout", "all"):
        stage_holdout()
    if args.stage in ("final", "all"):
        stage_final()
    log("elapsed", round(time.time() - t0, 1), "s")


def _guard_open() -> None:
    """Fail closed once this lane's terminal card exists (no restarts/retunes).

    gems79.lifecycle.enforce_open_lane guards the *canonical* lane in
    run_card.json (G79-THVC, untouched by this lane), so a non-canonical lane
    needs its own equivalent check against its own preregistration/card.
    """
    prereg = ROOT / "registry" / "preregistration_cjx.json"
    if not prereg.is_file():
        sys.stderr.write("G79-CJX: preregistration missing; no files changed\n")
        raise SystemExit(2)
    if (ROOT / "run_card_cjx.json").exists():
        sys.stderr.write(
            "G79-CJX is closed (run_card_cjx.json exists; 3/3 preregistered arms "
            "exhausted). Do not restart, retune, or repackage it. No files changed.\n"
        )
        raise SystemExit(2)


if __name__ == "__main__":
    _guard_open()
    main()
