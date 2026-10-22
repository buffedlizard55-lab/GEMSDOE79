#!/usr/bin/env python3
"""H79-FFAS experiment X1: canaries + two-seed buffered hide-and-recover + final map.

Stages
------
  holdout --seed S   closed-form FFAS surface from the visible catalogue;
                     candidate / no-farfield / equal-polarity / uniform / h33-fold-fair
                     arms; shared evaluator, pooled terms, paired spatial bootstrap.
  final              same formula on the full catalogue; 37,654 dots off-catalogue.

All scores written here are HOLDOUT-DTI from gems57-pooled-hide-v2. Nothing is
tuned on the holdout: every parameter comes from registry/preregistration_ffas.json.
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
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator          # noqa: E402
from gems57.grid import load_grid                          # noqa: E402
from gems57.holdout import buffered_component_draw         # noqa: E402
from gems79 import ffas                                    # noqa: E402
from gems79.lifecycle import LaneClosedError, require_open_lane  # noqa: E402
from gems79.placement import place                         # noqa: E402
import analyze_h33                                         # noqa: E402
from run_experiment import canaries                        # noqa: E402

PREREG = json.loads((ROOT / "registry/preregistration_ffas.json").read_text())
FIX = PREREG["fixed_parameters"]
BUDGET = ffas.BUDGET
OUT = ROOT / "evidence" / "ffas"
CACHE = ROOT / ".cache" / "ffas"


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


def stage_holdout(seed: int) -> None:
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    bands, lidar_meta = ffas.load_lidar()
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    log("canaries")
    feats = ffas.feature_maps(bands, visible, grid.footprint)
    # canaries() uses roc_auc_score; replace NaN with a sentinel below the support
    filled = {n: np.nan_to_num(a, nan=-99.0) for n, a in feats.items()}
    c_rows = canaries(filled, folds, seed)
    canary = dict(
        evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
        max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
        worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
        n_suspicious=sum(r["suspicious"] for r in c_rows),
        per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"] == n)
                         for n in {r["feature"] for r in c_rows}},
    )
    log("canary max", canary["max_symmetric_auc"], canary["worst"]["feature"])

    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    terms, fold_receipts = {}, []
    for fold in folds:
        region = fold["region"]
        vis = fold["visible"]
        known = fold["masked_known"]
        allowed = ffas.allowed_mask(grid.footprint, vis, known, region)
        s_cand = ffas.surface(bands, vis, grid.footprint, known, upface_boost=2.0, farfield=True)
        s_nofar = ffas.surface(bands, vis, grid.footprint, known, upface_boost=2.0, farfield=False)
        s_equal = ffas.surface(bands, vis, grid.footprint, known, upface_boost=1.0, farfield=True)
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = sy, sx
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        arms = {
            "candidate": s_cand,
            "ablation_no_farfield": s_nofar,
            "ablation_equal_polarity": s_equal,
            "uniform_control": rng_surface,
        }
        for name, surf in arms.items():
            dots, _ = place(surf[sl], allowed[sl], budget, spacing=ffas.SPACING_PX)
            _, bt = evaluator.evaluate(
                dots.astype(np.float32), local, grid.footprint[sl],
                origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
        d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
        h33_ff = (d28_pos[sl] & region[sl] & (d_vis > 2)).astype(np.float32)
        _, bt = evaluator.evaluate(
            h33_ff, local, grid.footprint[sl],
            origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt
        fold_receipts.append(dict(
            fold=fold["name"], budget=budget,
            withheld_truth=int((fold["truth"] & region).sum()),
            allowed_cells=int(allowed.sum())))
        log(f"fold {fold['name']} budget={budget} truth={fold_receipts[-1]['withheld_truth']}")

    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    out = dict(
        schema_version=1, lane="H79-FFAS", experiment="X1", seed=seed,
        evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
        generated_utc=datetime.now(timezone.utc).isoformat(),
        runtime_s=round(time.time() - t0, 1), leakage_canary=canary,
        holdout=summary, folds=fold_receipts,
        h33_control_source=d28src, lidar=lidar_meta,
        formula=FIX["formula"],
        preregistration_sha256=hashlib.sha256(
            (ROOT / "registry/preregistration_ffas.json").read_bytes()).hexdigest(),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"x1_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    s = summary["scores"]
    log({k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in s.items()})


def stage_surface() -> None:
    """Write the continuous rank surface only. Placement waits for the surface uniqueness scan."""
    grid = load_grid(ROOT / "data/reference")
    bands, lidar_meta = ffas.load_lidar()
    cat = grid.catalogue
    log("final surface (no placement yet)")
    surf = ffas.surface(bands, cat, grid.footprint, cat, upface_boost=2.0, farfield=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_surface.npy", surf)
    OUT.mkdir(parents=True, exist_ok=True)
    meta = dict(
        lane="H79-FFAS", experiment="X1", phase="surface",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        surface_sha256=hashlib.sha256(surf.tobytes()).hexdigest(),
        lidar=lidar_meta, formula=FIX["formula"],
        positive_surface_pixels=int((surf > 0).sum()),
        surface_max=float(surf.max()),
    )
    (OUT / "x1_surface_build.json").write_text(json.dumps(meta, indent=2, default=float) + "\n")
    log("surface", meta["surface_sha256"][:12], "positive", meta["positive_surface_pixels"])


def stage_place() -> None:
    grid = load_grid(ROOT / "data/reference")
    surf = np.load(CACHE / "final_surface.npy")
    allowed = ffas.allowed_mask(grid.footprint, grid.catalogue, grid.catalogue)
    dots, info = place(surf, allowed, BUDGET, spacing=ffas.SPACING_PX)
    np.save(CACHE / "final_dots.npy", dots)
    dcat = ndi.distance_transform_edt(~grid.catalogue)
    meta = dict(
        lane="H79-FFAS", experiment="X1", phase="place",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        placement=info,
        surface_sha256=hashlib.sha256(surf.tobytes()).hexdigest(),
        dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
        n_dots=int(dots.sum()),
        formula=FIX["formula"],
        min_distance_to_visible_px=ffas.MIN_DISTANCE_TO_VISIBLE_PX,
        allowed_cells=int(allowed.sum()),
        median_catalogue_distance_px=float(np.median(dcat[dots])) if dots.any() else None,
        fraction_gt_10px=float((dcat[dots] > 10).mean()) if dots.any() else None,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "x1_final_build.json").write_text(json.dumps(meta, indent=2, default=float) + "\n")
    log(meta["n_dots"], info, "median_d_cat_px", meta["median_catalogue_distance_px"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["holdout", "surface", "place"])
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    try:
        require_open_lane(ROOT, "H79-FFAS")
        if a.stage == "holdout":
            stage_holdout(a.seed)
        elif a.stage == "surface":
            stage_surface()
        else:
            stage_place()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
