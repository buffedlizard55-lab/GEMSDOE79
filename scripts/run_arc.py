#!/usr/bin/env python3
"""H79-ARC experiment X1 (preregistered in registry/preregistration_arc.json).

Stages
------
  holdout --seed S   canaries + leave-one-quadrant-out nested-hide models;
                     arms: candidate (max-cover), ablation_poisson_emission
                     (same surface, Poisson thinning), uniform_control
                     (max-cover), h33_foldfair_control. Shared evaluator
                     gems57-pooled-hide-v2, pooled terms, paired bootstrap.
  final              one model on nested hides of the full catalogue;
                     writes ONLY the continuous surface (+ allowed mask).
                     Dot placement happens later, after the surface has
                     passed the pre-placement uniqueness gate
                     (scripts/arc_uniqueness.py surface), per protocol rule 1.

Lane guard: the canonical run_card.json still belongs to the stopped
H79-NHR lane while experiments run, so `gems79.lifecycle.require_open_lane`
(keyed to the canonical card) cannot be the guard here.  This runner keeps
its own fail-closed state in evidence/arc/state.json: created as
in_progress on first use, refused forever once finalize_arc.py marks it
terminal.  No parameter is tuned on the holdout.
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
from gems79 import nhr                                     # noqa: E402
from gems79.arc_features import build_extra_stack          # noqa: E402
from gems79.cover import place_cover                       # noqa: E402
from gems79.placement import place                         # noqa: E402
import analyze_h33                                         # noqa: E402
from run_experiment import canaries                        # noqa: E402

PREREG = json.loads((ROOT / "registry/preregistration_arc.json").read_text())
FIX = PREREG["fixed_parameters"]
GEOMETRY_LITE = tuple(PREREG["geometry_inputs_visible_only"])
BUDGET = 37654
OUT = ROOT / "evidence" / "arc"
CACHE = ROOT / ".cache" / "arc"
STATE = OUT / "state.json"


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


def require_open_arc():
    OUT.mkdir(parents=True, exist_ok=True)
    if STATE.exists():
        state = json.loads(STATE.read_text())
        if state.get("status") != "in_progress" or state.get("lane") != "H79-ARC":
            raise SystemExit(f"H79-ARC is terminal ({state.get('status')}); refusing to rerun. Exit 2.")
    else:
        STATE.write_text(json.dumps(dict(lane="H79-ARC", status="in_progress",
                                         opened_utc=datetime.now(timezone.utc).isoformat(),
                                         preregistration="registry/preregistration_arc.json"),
                                    indent=2) + "\n")


class Stack:
    """NHR static stack + ARC extra transforms; rows by full-grid flat index."""

    def __init__(self, grid):
        self.grid = grid
        self.base, self.base_names, self.meta = nhr.build_static_stack(grid.footprint)
        self.extra, self.extra_names, self.extra_meta = build_extra_stack(grid.footprint)
        self.static_names = list(self.base_names) + list(self.extra_names)
        self.row_of = np.full(grid.footprint.size, -1, np.int64)
        fpi = np.flatnonzero(grid.footprint)
        self.row_of[fpi] = np.arange(fpi.size)
        self.lstrike, self.lcoh = nhr.read_lidar_orientation(grid.footprint)

    def geometry(self, visible):
        full = nhr.geometry_features(visible, self.grid.footprint, self.lstrike, self.lcoh)
        return {n: full[n] for n in GEOMETRY_LITE}

    def rows(self, flat_idx, geom):
        r = self.row_of[flat_idx]
        st = np.concatenate([np.asarray(self.base[r], np.float32),
                             np.asarray(self.extra[r], np.float32)], axis=1)
        g = np.stack([geom[n].ravel()[flat_idx] for n in GEOMETRY_LITE], axis=1)
        return np.concatenate([st, g], axis=1)

    @property
    def names(self):
        return list(self.static_names) + ["geom_" + n for n in GEOMETRY_LITE]


def training_rows(stack, context, region, seed):
    rng = np.random.default_rng(seed)
    fp = stack.grid.footprint
    X, y, receipts = [], [], []
    for rep in range(FIX["nested_replicates_per_model"]):
        hidden, remaining = nhr.nested_hide(context, region, rng, FIX["nested_hide_fraction"],
                                            FIX["nested_buffer_px"])
        t = nhr.kernel_target(hidden)
        geom = stack.geometry(remaining)
        base = region & fp & ~context
        pos = np.flatnonzero(base & (t > 0))
        neg_pool = np.flatnonzero(base & (t == 0))
        neg = rng.choice(neg_pool, min(FIX["negatives_sampled_per_replicate"], neg_pool.size),
                         replace=False)
        idx = np.concatenate([pos, neg])
        X.append(stack.rows(idx, geom)); y.append(t.ravel()[idx])
        receipts.append(dict(replicate=rep, hidden_pixels=int(hidden.sum()),
                             positive_rows=int(pos.size), negative_rows=int(neg.size)))
        del geom, t, hidden, remaining
        gc.collect()
    return np.concatenate(X), np.concatenate(y), receipts


def fit(X, y, seed):
    m = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=63,
                                      min_samples_leaf=200, l2_regularization=1.0,
                                      random_state=seed, early_stopping=False)
    m.fit(X, y)
    return m


def predict_surface(model, stack, cells_mask, geom, chunk=400_000):
    surf = np.zeros(stack.grid.shape, np.float32)
    idx = np.flatnonzero(cells_mask)
    flat = surf.ravel()
    for s in range(0, idx.size, chunk):
        part = idx[s:s + chunk]
        flat[part] = model.predict(stack.rows(part, geom)).astype(np.float32)
    m = float(flat[idx].min()) if idx.size else 0.0
    if m <= 0:
        flat[idx] -= m - 1e-6
    return surf


def stage_holdout(seed):
    require_open_arc()
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    quad = quadrant_ids(grid.footprint)
    geom_vis = stack.geometry(visible)
    d_vis_full = ndi.distance_transform_edt(~visible)

    log("canaries:", len(stack.names), "features")
    class LazyFeatures:
        def items(self):
            fpi = np.flatnonzero(grid.footprint)
            mats = [(stack.base, list(stack.base_names)), (stack.extra, list(stack.extra_names))]
            for mat, names_ in mats:
                for j, n in enumerate(names_):
                    col = np.zeros(grid.footprint.size, np.float32)
                    col[fpi] = np.nan_to_num(np.asarray(mat[:, j], np.float32), nan=-99.0)
                    yield n, col.reshape(grid.shape)
            for n in GEOMETRY_LITE:
                yield "geom_" + n, np.nan_to_num(geom_vis[n], nan=-99.0)
    c_rows = canaries(LazyFeatures(), folds, seed)
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                  worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
                  n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"] == n)
                                   for n in {r["feature"] for r in c_rows}})
    log("canary max", round(canary["max_symmetric_auc"], 4), canary["worst"]["feature"])

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
        allowed = region & grid.footprint & ~fold["masked_known"] & (d_vis_full > 2)
        surf = predict_surface(model, stack, allowed, geom_vis)
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = sy, sx
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        placements = {}
        dots_c, info_c = place_cover(surf[sl], allowed[sl], budget)
        placements["candidate"] = dots_c
        dots_p, _ = place(surf[sl], allowed[sl], budget)
        placements["ablation_poisson_emission"] = dots_p
        dots_u, _ = place_cover(rng_surface[sl], allowed[sl], budget)
        placements["uniform_control"] = dots_u
        for name, dots in placements.items():
            _, bt = evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
        d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
        h33_ff = (d28_pos[sl] & region[sl] & (d_vis > 2)).astype(np.float32)
        _, bt = evaluator.evaluate(h33_ff, local, grid.footprint[sl],
                                   origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt
        fold_receipts.append(dict(fold=fold["name"], budget=budget, nested=rec,
                                  cover_info=info_c,
                                  withheld_truth=int((fold["truth"] & region).sum())))
        del surf, model, placements; gc.collect()
        log(f"fold {fold['name']} done ({round(time.time()-t0)}s)")
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    out = dict(schema_version=1, lane="H79-ARC", experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time() - t0, 1), leakage_canary=canary,
               holdout=summary, folds=fold_receipts,
               h33_control_source=d28src, feature_names=stack.names,
               static_stack_inputs=stack.meta["inputs_sha256"],
               extra_stack_inputs=stack.extra_meta["inputs_sha256"])
    (OUT / f"x1_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    s = summary["scores"]
    log({k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in s.items()})


def stage_final():
    require_open_arc()
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    cat = grid.catalogue
    log("final: nested rows over the whole footprint")
    X, y, rec = training_rows(stack, cat, grid.footprint, 790000)
    model = fit(X, y, 790000)
    del X, y; gc.collect()
    geom = stack.geometry(cat)
    d_cat = ndi.distance_transform_edt(~cat)
    allowed = grid.footprint & ~cat & (d_cat > 2)
    surf = predict_surface(model, stack, allowed, geom)
    v = surf[allowed]
    norm = np.zeros(grid.shape, np.float32)
    norm[allowed] = ((v - v.min()) / max(float(np.ptp(v)), 1e-12)).astype(np.float32)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_surface.npy", norm)
    np.save(CACHE / "final_allowed.npy", allowed)
    meta = dict(nested=rec, surface_sha256=hashlib.sha256(norm.tobytes()).hexdigest(),
                allowed_pixels=int(allowed.sum()), feature_names=stack.names,
                note="Surface only. Placement is gated on scripts/arc_uniqueness.py surface.")
    (OUT / "x1_final_surface.json").write_text(json.dumps(meta, indent=2) + "\n")
    log("surface saved", meta["surface_sha256"][:12], "allowed", meta["allowed_pixels"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["holdout", "final"])
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    stage_holdout(a.seed) if a.stage == "holdout" else stage_final()
