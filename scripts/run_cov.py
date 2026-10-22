#!/usr/bin/env python3
"""H79-COV experiment C1: canaries + two-seed buffered hide-and-recover + final map.

Identical folds, evaluator, budgets, allocator, model hyperparameters and
controls to H79-NHR (scripts/run_nhr.py); the ONLY change is the input
channel set (preregistered closed list in src/gems79/covanti.py, no
catalogue-geometry features). All scores are HOLDOUT-DTI from
gems57-pooled-hide-v2. Nothing is tuned on the holdout.

Stages are sequenced to honour IR-79-54: `final` writes surface+dots to the
cache only; packaging (scripts/build_cov_submission.py) runs after the
surface and final uniqueness scans exist.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator          # noqa: E402
from gems57.grid import load_grid                          # noqa: E402
from gems57.holdout import buffered_component_draw, quadrant_ids  # noqa: E402
from gems79 import covanti, nhr                            # noqa: E402
from gems79.placement import place                         # noqa: E402
import analyze_h33                                         # noqa: E402
from run_experiment import canaries                        # noqa: E402

PREREG = json.loads((ROOT / "registry/preregistration_g79cov_20261022.json").read_text())
FIX = PREREG["fixed_parameters"]
BUDGET = 37654
OUT = ROOT / "evidence" / "cov"
CACHE = ROOT / ".cache" / "cov"


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


class Stack:
    """Footprint-row channel matrix served by full-grid flat index. No geometry."""

    def __init__(self, grid):
        self.grid = grid
        self.static, self.names, self.meta = covanti.build_cov_stack(grid.footprint)
        self.row_of = np.full(grid.footprint.size, -1, np.int64)
        fpi = np.flatnonzero(grid.footprint)
        self.row_of[fpi] = np.arange(fpi.size)

    def rows(self, flat_idx):
        return np.asarray(self.static[self.row_of[flat_idx]], np.float32)


def training_rows(stack, context, region, seed):
    """Nested hide-to-recover rows inside region (identical scheme to H79-NHR)."""
    rng = np.random.default_rng(seed)
    fp = stack.grid.footprint
    X, y, receipts = [], [], []
    for rep in range(FIX["nested_replicates_per_model"]):
        hidden, remaining = nhr.nested_hide(context, region, rng, FIX["nested_hide_fraction"],
                                            FIX["nested_buffer_px"])
        t = nhr.kernel_target(hidden)
        base = region & fp & ~context
        pos = np.flatnonzero(base & (t > 0))
        neg_pool = np.flatnonzero(base & (t == 0))
        neg = rng.choice(neg_pool, min(FIX["negatives_sampled_per_replicate"], neg_pool.size),
                         replace=False)
        idx = np.concatenate([pos, neg])
        X.append(stack.rows(idx)); y.append(t.ravel()[idx])
        receipts.append(dict(replicate=rep, hidden_pixels=int(hidden.sum()),
                             positive_rows=int(pos.size), negative_rows=int(neg.size)))
        del t, hidden, remaining
        gc.collect()
    return np.concatenate(X), np.concatenate(y), receipts


def fit(X, y, seed):
    m = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=63,
                                      min_samples_leaf=200, l2_regularization=1.0,
                                      random_state=seed, early_stopping=False)
    m.fit(X, y)
    return m


def predict_surface(model, stack, cells_mask, chunk=400_000):
    surf = np.zeros(stack.grid.shape, np.float32)
    idx = np.flatnonzero(cells_mask)
    flat = surf.ravel()
    for s in range(0, idx.size, chunk):
        part = idx[s:s + chunk]
        flat[part] = model.predict(stack.rows(part)).astype(np.float32)
    m = float(flat[idx].min()) if idx.size else 0.0
    if m <= 0:
        flat[idx] -= m - 1e-6
    return surf


def stage_holdout(seed):
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    quad = quadrant_ids(grid.footprint)

    log("canaries")
    class LazyFeatures:
        def __init__(self):
            self.names = list(stack.names)
        def items(self):
            fpi = np.flatnonzero(grid.footprint)
            for j, n in enumerate(stack.names):
                col = np.zeros(grid.footprint.size, np.float32)
                col[fpi] = np.nan_to_num(np.asarray(stack.static[:, j], np.float32), nan=-99.0)
                yield n, col.reshape(grid.shape)
    c_rows = canaries(LazyFeatures(), folds, seed)
    gc.collect()
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                  worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
                  n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"] == n)
                                   for n in {r["feature"] for r in c_rows}})
    log("canary max", canary["max_symmetric_auc"], canary["worst"]["feature"])
    if canary["n_suspicious"]:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"c1_canary_failure_seed{seed}.json").write_text(json.dumps(canary, indent=2) + "\n")
        raise SystemExit("LEAKAGE CANARY > 0.90 — lane stops before any score is trusted")

    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    terms, fold_receipts = {}, []
    for fold in folds:
        q = fold["fold"]
        train_region = grid.footprint & (quad != q) & (quad >= 0)
        log(f"fold {fold['name']}: nested rows")
        X, y, rec = training_rows(stack, visible, train_region, seed * 100 + q)
        log(f"fold {fold['name']}: fit ({X.shape})")
        model = fit(X, y, seed * 100 + q)
        del X, y; gc.collect()
        region = fold["region"]
        allowed = region & grid.footprint & ~fold["masked_known"]
        surf = predict_surface(model, stack, allowed)
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = sy, sx
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        for name, s in {"candidate": surf, "uniform_control": rng_surface}.items():
            dots, _ = place(s[sl], allowed[sl], budget)
            _, bt = evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
        d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
        h33_ff = (d28_pos[sl] & region[sl] & (d_vis > 2)).astype(np.float32)
        _, bt = evaluator.evaluate(h33_ff, local, grid.footprint[sl],
                                   origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt
        fold_receipts.append(dict(fold=fold["name"], budget=budget, nested=rec,
                                  withheld_truth=int((fold["truth"] & region).sum())))
        del surf, model; gc.collect()
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    out = dict(schema_version=1, lane="H79-COV", experiment="C1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time() - t0, 1), leakage_canary=canary,
               holdout=summary, folds=fold_receipts,
               h33_control_source=d28src, feature_names=stack.names,
               cov_stack_inputs=stack.meta["inputs_sha256"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"c1_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    s = summary["scores"]
    log({k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in s.items()})


def stage_final():
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    cat = grid.catalogue
    log("final: nested rows over the whole footprint")
    X, y, rec = training_rows(stack, cat, grid.footprint, 790000)
    m = fit(X, y, 790000)
    del X, y; gc.collect()
    allowed = grid.footprint & ~cat
    surf = predict_surface(m, stack, allowed)
    v = surf[allowed]
    norm = np.zeros(grid.shape, np.float32)
    norm[allowed] = ((v - v.min()) / max(float(np.ptp(v)), 1e-12)).astype(np.float32)
    dots, info = place(norm, allowed, BUDGET)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_surface.npy", norm)
    np.save(CACHE / "final_dots.npy", dots)
    meta = dict(nested=rec, placement=info,
                surface_sha256=hashlib.sha256(norm.tobytes()).hexdigest(),
                dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
                n_dots=int(dots.sum()), feature_names=stack.names)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "c1_final_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    log(meta["n_dots"], info)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["holdout", "final"])
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    stage_holdout(a.seed) if a.stage == "holdout" else stage_final()
