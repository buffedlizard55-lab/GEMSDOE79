#!/usr/bin/env python3
"""H79-FF1 X1: far-field (10-30 px) band placement on the reused NHR surface.

Reuses scripts/run_nhr.py Stack/training_rows/fit/predict_surface (import, no
fork), shared gems57 evaluator and gems79.placement.place. Preregistered in
registry/preregistration_ff1.json before any result.
Stages: holdout --seed S | final-surface | final-dots
"""
from __future__ import annotations
import argparse, gc, hashlib, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw, quadrant_ids
from gems79.placement import place
import analyze_h33
import run_nhr
from run_nhr import Stack, training_rows, fit, predict_surface

BUDGET = 37654
BAND = (10, 30)  # px = 1-3 km at 100 m/px
OUT = ROOT / "evidence" / "ff1"
CACHE = ROOT / ".cache" / "ff1"

def log(*a): print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)

def band_mask(visible):
    d = ndi.distance_transform_edt(~np.asarray(visible, bool))
    return (d >= BAND[0]) & (d <= BAND[1]), d

def stage_holdout(seed):
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    quad = quadrant_ids(grid.footprint)
    geom_vis = stack.geometry(visible)

    # Leakage canaries: reuse NHR X1 canary computation verbatim via run_nhr logic
    # (same feature stack; band is a placement mask, not a feature). Import the
    # shared canary function as run_nhr does.
    from run_experiment import canaries
    class LazyFeatures:
        def __init__(self): self.names = list(stack.static_names) + ["geom_" + n for n in run_nhr.nhr.GEOMETRY_NAMES]
        def items(self):
            fpi = np.flatnonzero(grid.footprint)
            for j, n in enumerate(stack.static_names):
                col = np.zeros(grid.footprint.size, np.float32)
                col[fpi] = np.nan_to_num(np.asarray(stack.static[:, j], np.float32), nan=-99.0)
                yield n, col.reshape(grid.shape)
            for n in run_nhr.nhr.GEOMETRY_NAMES:
                yield "geom_" + n, np.nan_to_num(geom_vis[n], nan=-99.0)
    c_rows = canaries(LazyFeatures(), folds, seed)
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                  worst=max(c_rows, key=lambda r: r["symmetric_auc"]))
    log("canary max", canary["max_symmetric_auc"], canary["worst"]["feature"])
    del c_rows; gc.collect()

    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    band, _d = band_mask(visible)
    terms, fold_receipts = {}, []
    for fold in folds:
        q = fold["fold"]
        train_region = grid.footprint & (quad != q) & (quad >= 0)
        X, y, rec = training_rows(stack, visible, train_region, seed * 100 + q)
        m_full = fit(X, y, seed * 100 + q)
        del X, y; gc.collect()
        region = fold["region"]
        allowed_base = region & grid.footprint & ~fold["masked_known"]
        allowed_band = allowed_base & band
        s_full = predict_surface(m_full, stack, allowed_base, geom_vis, True)
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = (sy, sx)
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        arms = {"candidate": (s_full, allowed_band), "uniform_control": (rng_surface, allowed_band),
                "unrestricted_nhr_reference": (s_full, allowed_base)}
        for name, (surf, allowed) in arms.items():
            dots, info = place(surf[sl], allowed[sl], budget)
            if info["exhausted"]: log(name, "EXHAUSTED", info)
            _, bt = evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
        d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
        h33_ff = (d28_pos[sl] & region[sl] & (d_vis > 2)).astype(np.float32)
        _, bt = evaluator.evaluate(h33_ff, local, grid.footprint[sl],
                                   origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt
        fold_receipts.append(dict(fold=fold["name"], budget=budget, nested=rec,
                                  band_cells=int((allowed_band & region).sum()),
                                  withheld_truth=int((fold["truth"] & region).sum())))
        del s_full, m_full; gc.collect()
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    out = dict(schema_version=1, lane="H79-FF1", experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(), runtime_s=round(time.time() - t0, 1),
               band_px=list(BAND), leakage_canary=canary, holdout=summary, folds=fold_receipts,
               h33_control_source=d28src, feature_names=stack.names)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"x1_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    log({k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in summary["scores"].items()})

def stage_final_surface():
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    cat = grid.catalogue
    X, y, rec = training_rows(stack, cat, grid.footprint, 790000)
    m = fit(X, y, 790000); del X, y; gc.collect()
    geom = stack.geometry(cat)
    allowed_base = grid.footprint & ~cat
    surf = predict_surface(m, stack, allowed_base, geom, True)
    v = surf[allowed_base]
    norm = np.zeros(grid.shape, np.float32)
    norm[allowed_base] = ((v - v.min()) / max(float(np.ptp(v)), 1e-12)).astype(np.float32)
    band, d = band_mask(cat)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_surface.npy", norm)
    np.save(CACHE / "final_band.npy", band & allowed_base)
    meta = dict(nested=rec, band_px=list(BAND),
                surface_sha256=hashlib.sha256(norm.tobytes()).hexdigest(),
                band_cells=int((band & allowed_base).sum()),
                median_dist_catalogue_px=float(np.median(d[allowed_base])),
                feature_names=stack.names)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "x1_final_surface.json").write_text(json.dumps(meta, indent=2) + "\n")
    log(meta)

def stage_final_dots():
    grid = load_grid(ROOT / "data/reference")
    norm = np.load(CACHE / "final_surface.npy"); band = np.load(CACHE / "final_band.npy")
    dots, info = place(norm, band, BUDGET)
    np.save(CACHE / "final_dots.npy", dots)
    meta = dict(placement=info, dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(), n_dots=int(dots.sum()))
    (OUT / "x1_final_dots.json").write_text(json.dumps(meta, indent=2) + "\n")
    log(meta)

if __name__ == "__main__":
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "H79-FF1",
        reason="H79-FF1 is stopped and archived (HOLDOUT-DTI 0.0250/0.0249 < uniform; surface duplicate).",
    )
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["holdout", "final-surface", "final-dots"])
    ap.add_argument("--seed", type=int, default=20); a = ap.parse_args()
    {"holdout": lambda: stage_holdout(a.seed), "final-surface": stage_final_surface, "final-dots": stage_final_dots}[a.stage]()
