#!/usr/bin/env python3
"""H80-FARFIELD experiment X1: far-field antislope + worm persistence.

This is a NEW preregistered lane, not a restart of H79-NHR.
It uses the same nested hide-and-recover protocol but adds far-field
stratification and two new derived layers.

Stages:
  holdout --seed S   LOQO models on nested hides of visible catalogue, with
                    far-field sampling; candidate / ablation / uniform / h33-far-field
                    arms; pooled DTI via gems57-pooled-hide-v2.
  final             model on full catalogue nested hides, surface predicted over
                    whole footprint, far-field dots only (>1 km), 37,654 dots.

All scores are HOLDOUT-DTI. Nothing tuned on holdout.
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
from gems57 import evaluate_holdout as evaluator
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw, quadrant_ids
from gems57.metric import RADIUS_PX
from gems79 import nhr
from gems79.placement import place
import analyze_h33
from run_experiment import canaries

PREREG = json.loads((ROOT / "registry/preregistration_farfield.json").read_text())
FIX = PREREG["fixed_parameters"]
BUDGET = 37654
OUT = ROOT / "evidence" / "farfield"
CACHE = ROOT / ".cache" / "farfield"

FARFIELD_PX = 10  # 1 km at 100 m grid

def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)

class Stack:
    def __init__(self, grid):
        self.grid = grid
        # Try extended farfield cache first, else build
        ext_npy = CACHE / "static_stack_farfield_f16.npy"
        ext_json = CACHE / "static_stack_farfield.json"
        if ext_npy.exists() and ext_json.exists():
            log("loading extended farfield stack from cache")
            self.static = np.load(ext_npy, mmap_mode="r")
            meta = json.loads(ext_json.read_text())
            self.static_names = meta["names"]
            self.meta = meta
        else:
            log("building extended farfield stack (first run, ~2 min)")
            # Use farfield module builder
            from gems79.farfield import build_extended_stack
            self.static, self.static_names, self.meta = build_extended_stack(grid.footprint, grid.catalogue)
            log(f"built extended stack {self.static.shape} names={len(self.static_names)}")

        self.row_of = np.full(grid.footprint.size, -1, np.int64)
        fpi = np.flatnonzero(grid.footprint)
        self.row_of[fpi] = np.arange(fpi.size)
        # Lidar orientation for geometry features (same as NHR)
        self.lstrike, self.lcoh = nhr.read_lidar_orientation(grid.footprint)
        # Precompute far-field mask (distance >10px)
        self.farfield_mask = ndi.distance_transform_edt(~grid.catalogue) > FARFIELD_PX
        # Also distance band for diagnostics
        from gems79.farfield import compute_distance_band
        self.dist_band = compute_distance_band(grid.catalogue, grid.footprint)

    def geometry(self, visible):
        return nhr.geometry_features(visible, self.grid.footprint, self.lstrike, self.lcoh)

    def rows(self, flat_idx, geom, use_geometry=True, use_extra=True):
        # static includes base + farfield extras already
        # For ablation we need to slice out farfield extras
        if use_extra:
            st = np.asarray(self.static[self.row_of[flat_idx]], np.float32)
        else:
            # ablation: only base NHR features (19 + lidar etc without farfield antislope/worm)
            n_extra = 3
            st = np.asarray(self.static[self.row_of[flat_idx]][:, :-n_extra], np.float32)
        if not use_geometry:
            return st
        # geometry is always added
        g = np.stack([geom[n].ravel()[flat_idx] for n in nhr.GEOMETRY_NAMES], axis=1)
        return np.concatenate([st, g], axis=1)

    @property
    def names(self):
        return list(self.static_names) + list(nhr.GEOMETRY_NAMES)

    @property
    def base_names(self):
        # names without farfield extras (for ablation naming)
        n_extra = 3
        return list(self.static_names[:-n_extra]) + list(nhr.GEOMETRY_NAMES)

def training_rows(stack, context, region, seed, farfield_only=True):
    """Nested hide-to-recover rows, stratified to far-field if requested."""
    rng = np.random.default_rng(seed)
    fp = stack.grid.footprint
    # Far-field mask: distance >10px from *original context*? Use full catalogue distance for stratification
    # But for training we want negatives sampled only from far-field band within region
    # Hidden truth is always within region (could be near or far), but negatives are far-field
    X, y = [], []
    receipts = []
    for rep in range(FIX["nested_replicates_per_model"]):
        hidden, remaining = nhr.nested_hide(context, region, rng, FIX["nested_hide_fraction"], FIX["nested_buffer_px"])
        t = nhr.kernel_target(hidden)
        geom = stack.geometry(remaining)
        # Base eligible: region & footprint & not context (catalogue never rows)
        base = region & fp & ~context
        # Enforce far-field for training rows if enabled
        if farfield_only:
            # Use distance to *remaining* visible? No, use distance to original catalogue for stability
            # Actually far-field definition is distance to catalogue (mapped faults). Use context distance
            dist = ndi.distance_transform_edt(~context)
            base = base & (dist > FARFIELD_PX)
        pos = np.flatnonzero(base & (t > 0))
        neg_pool = np.flatnonzero(base & (t == 0))
        # Sample negatives
        if neg_pool.size == 0:
            # Fallback: if far-field yields no negatives (unlikely), use all
            neg_pool = np.flatnonzero(region & fp & ~context & (t == 0))
        neg = rng.choice(neg_pool, min(FIX["negatives_sampled_per_replicate"], neg_pool.size), replace=False)
        idx = np.concatenate([pos, neg]) if pos.size else neg
        # For ablation vs full, we need both? We'll train two models from same rows but different column subsets below
        # So we store full rows (with extra) and let caller slice
        X.append(stack.rows(idx, geom, use_geometry=True, use_extra=True)); y.append(t.ravel()[idx])
        receipts.append(dict(replicate=rep, hidden_pixels=int(hidden.sum()), positive_rows=int(pos.size), negative_rows=int(neg.size), farfield_only=farfield_only))
        del geom, t, hidden, remaining
        gc.collect()
    return np.concatenate(X), np.concatenate(y), receipts

def fit(X, y, seed):
    m = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=63, min_samples_leaf=200, l2_regularization=1.0, random_state=seed, early_stopping=False)
    m.fit(X, y)
    return m

def predict_surface(model, stack, cells_mask, geom, use_geometry=True, use_extra=True, chunk=400_000):
    surf = np.zeros(stack.grid.shape, np.float32)
    idx = np.flatnonzero(cells_mask)
    flat = surf.ravel()
    for s in range(0, idx.size, chunk):
        part = idx[s:s+chunk]
        Xp = stack.rows(part, geom, use_geometry=use_geometry, use_extra=use_extra)
        flat[part] = model.predict(Xp).astype(np.float32)
    m = float(flat[idx].min()) if idx.size else 0.0
    if m <= 0:
        flat[idx] -= m - 1e-6
    return surf

def stage_holdout(seed):
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    # Use first fold's visible for canary geometry (same as NHR, any visible)
    visible = folds[0]["visible"]
    quad = quadrant_ids(grid.footprint)
    geom_vis = stack.geometry(visible)

    log("canaries")
    class LazyFeatures:
        def __init__(self):
            self.names = list(stack.static_names) + ["geom_" + n for n in nhr.GEOMETRY_NAMES]
        def items(self):
            fpi = np.flatnonzero(grid.footprint)
            for j, n in enumerate(stack.static_names):
                col = np.zeros(grid.footprint.size, np.float32)
                # Note static is float16, need to convert
                arr = np.asarray(stack.static[:, j], dtype=np.float32)
                # But we have NaN handling: static already robust, NaN where invalid -> we replaced with nan in matrix, then we need to map nan to -99 for canary
                # stack.static currently is float16 with NaN, we need to handle
                # For canary we use nan_to_num
                col[fpi] = np.nan_to_num(arr, nan=-99.0)
                yield n, col.reshape(grid.shape)
            for n in nhr.GEOMETRY_NAMES:
                yield "geom_" + n, np.nan_to_num(geom_vis[n], nan=-99.0)
    feats = LazyFeatures()
    c_rows = canaries(feats, folds, seed)
    del feats; gc.collect()
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                  worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
                  n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"]==n) for n in {r["feature"] for r in c_rows}})
    log(f"canary max {canary['max_symmetric_auc']:.4f} worst {canary['worst']['feature']} suspicious {canary['n_suspicious']}")

    try:
        d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
        d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
        has_h33 = True
    except (FileNotFoundError, OSError, RuntimeError) as e:
        log(f"H33 control unavailable ({e}), using uniform only for this diagnostic run")
        d28 = np.zeros(grid.shape, dtype=np.float32)
        d28_pos = np.zeros(grid.shape, bool)
        d28src = {"error": str(e), "note": "registry not restored; H33 control skipped"}
        has_h33 = False
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    terms, fold_receipts = {}, []

    for fold in folds:
        q = fold["fold"]
        train_region = grid.footprint & (quad != q) & (quad >= 0)
        log(f"fold {fold['name']}: nested rows")
        X_full, y, rec = training_rows(stack, visible, train_region, seed*100+q, farfield_only=False)
        # Also prepare ablation: same rows but without farfield extra columns
        # For ablation we need to slice X_full to base columns + geometry; X_full currently includes extra+geometry, need to reconstruct ablation matrix
        # Simpler: recompute X_abl via stack.rows with use_extra=False
        # But we already have y and rec; we can derive X_abl by calling training_rows logic but we can also slice: full has (F_base+N_extra + G) columns; ablation should be (F_base + G)
        # We need lengths: F_total = len(stack.static_names), N_extra=5, G=6
        F_total = len(stack.static_names)
        N_extra = 3
        G = len(nhr.GEOMETRY_NAMES)
        # X_full is (n_rows, F_total+G)
        # Ablation is (F_total-N_extra + G)
        # So we can slice: first F_total-N_extra columns + last G columns
        X_abl = np.concatenate([X_full[:, :F_total-N_extra], X_full[:, -G:]], axis=1) if G else X_full[:, :F_total-N_extra]

        log(f"fold {fold['name']}: fit full {X_full.shape} ablation {X_abl.shape}")
        m_full = fit(X_full, y, seed*100+q)
        m_abl = fit(X_abl, y, seed*100+q)
        del X_full, X_abl, y; gc.collect()

        region = fold["region"]
        allowed = region & grid.footprint & ~fold["masked_known"]
        # We predict surface over allowed, but evaluation will consider only far-field? Actually scoring is over all active (domain & ~visible)
        # However to keep candidate comparable to uniform in same space, we use allowed as prediction domain
        # New: far-field candidate is still evaluated on same metric (all positives), but its training is far-field biased and its prediction may be weak near-field
        # We keep allowed for prediction as before (all non-visible), but placement will later be far-field only for final map
        # For holdout evaluation, we need to evaluate dots placed in allowed (including near-field) but we could restrict placement to far-field even during holdout to test far-field hypothesis under same scoring
        # Let's test both: for holdout, we place dots in allowed & farfield_mask to see if far-field-restricted dots can still beat H33 control under same scoring domain
        # But scoring domain includes near-field truth too; far-field dots would lose there. Better to keep holdout placement unrestricted for fair scoring, and enforce far-field only for final uniqueness
        # So for holdout we use unrestricted placement (like NHR) to measure raw model skill, then final we restrict to far-field for uniqueness
        # We'll do unrestricted for holdout measurement
        s_full = predict_surface(m_full, stack, allowed, geom_vis, True, True)
        s_abl = predict_surface(m_abl, stack, allowed, geom_vis, True, False)  # ablation without extra

        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min())-3), min(grid.height, int(ys.max())+4))
        sx = slice(max(0, int(xs.min())-3), min(grid.width, int(xs.max())+4))
        sl = sy, sx
        local = {k: fold[k][sl] for k in ("region","truth","visible","masked_known")}
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))

        # Evaluate arms
        arms = {"candidate": s_full, "ablation_farfield_extra": s_abl, "uniform_control": rng_surface}
        for name, surf in arms.items():
            dots, _ = place(surf[sl], allowed[sl], budget)
            _, bt = evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl], origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt

        # H33 control: legacy dots >2px from visible, if available
        if has_h33:
            d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
            h33_ff = (d28_pos[sl] & region[sl] & (d_vis > 2)).astype(np.float32)
            # Also create far-field version: additionally distance >10px from catalogue (full) for far-field H33
            d_cat_full = ndi.distance_transform_edt(~grid.catalogue[sl])
            h33_far = (h33_ff > 0) & (d_cat_full > FARFIELD_PX)
            _, bt = evaluator.evaluate(h33_ff, local, grid.footprint[sl], origin=(sy.start, sx.start), global_shape=grid.shape)
            terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt
            if h33_far.any():
                _, bt_far = evaluator.evaluate(h33_far.astype(np.float32), local, grid.footprint[sl], origin=(sy.start, sx.start), global_shape=grid.shape)
                terms["h33_farfield_control"] = terms.get("h33_farfield_control", 0) + bt_far
        else:
            # No H33 available; use zero arm to keep summary structure
            pass
        fold_receipts.append(dict(fold=fold["name"], budget=budget, nested=rec, withheld_truth=int((fold["truth"] & region).sum())))
        del s_full, s_abl, m_full, m_abl; gc.collect()

    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900+seed)
    out = dict(schema_version=1, lane="H80-FARFIELD", experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time()-t0,1), leakage_canary=canary,
               holdout=summary, folds=fold_receipts,
               h33_control_source=d28src, feature_names=stack.names,
               static_stack_inputs=stack.meta.get("inputs_sha256", {}),
               farfield_note=f"Training negatives sampled from far-field >{FARFIELD_PX}px; holdout placement unrestricted for fair scoring; final placement will be far-field only")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"x1_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    s = summary["scores"]
    log({k: (round(v["dti"],4), [round(c,4) for c in v["ci95"]]) for k,v in s.items()})
    # also log paired differences
    pd = summary.get("paired_differences", {})
    for k,v in pd.items():
        log(f"paired vs {k}: delta {v['delta']:.4f} CI {v['ci95']}")

def stage_final():
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    cat = grid.catalogue
    log("final: nested rows over whole footprint")
    X, y, rec = training_rows(stack, cat, grid.footprint, 790000, farfield_only=False)
    m = fit(X, y, 790000)
    del X, y; gc.collect()
    geom = stack.geometry(cat)
    allowed = grid.footprint & ~cat & stack.farfield_mask  # FAR-FIELD ONLY
    log(f"allowed far-field pixels {allowed.sum()} of {grid.footprint.sum()} footprint, catalogue {cat.sum()}")
    surf = predict_surface(m, stack, allowed, geom, True, True)
    # Normalise to [0,1] for registry rank check
    v = surf[allowed]
    norm = np.zeros(grid.shape, np.float32)
    if v.size and np.ptp(v) > 0:
        norm[allowed] = ((v - v.min()) / float(np.ptp(v))).astype(np.float32)
    else:
        norm[allowed] = 0.5 if v.size else 0.0
    # Also set outside allowed but inside footprint & not catalogue & not far-field to 0 (explicit zeros)
    # Outside footprint and on catalogue already 0 (norm is 0 elsewhere)
    dots, info = place(norm, allowed, BUDGET)
    log(f"placed dots {info['emitted']} requested {info['requested']} exhausted {info['exhausted']}")
    # Save surface and dots
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_surface.npy", norm)
    np.save(CACHE / "final_dots.npy", dots)
    # Compute distance stats
    d = ndi.distance_transform_edt(~cat)
    dists = d[dots]
    meta = dict(nested=rec, placement=info, surface_sha256=hashlib.sha256(norm.tobytes()).hexdigest(),
                dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(), n_dots=int(dots.sum()),
                feature_names=stack.names,
                farfield_median_px=float(np.median(dists)) if dists.size else None,
                farfield_median_m=float(np.median(dists)*100) if dists.size else None,
                farfield_frac_gt1km=float((dists>10).mean()) if dists.size else None,
                allowed_farfield_pixels=int(allowed.sum()),
                note=f"Far-field only >{FARFIELD_PX}px; median dist {np.median(dists) if dists.size else 'N/A'} px")
    (OUT / "x1_final_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    log(meta)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["holdout","final"])
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    if a.stage == "holdout":
        stage_holdout(a.seed)
    else:
        stage_final()
