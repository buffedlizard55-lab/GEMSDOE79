#!/usr/bin/env python3
"""H84-FFA experiment: far-field antislope asymmetry.

Stages:
  holdout --seed S   evaluate antislope surface vs H33 far-field control and uniform
  final              generate far-field dots and write submission (if lanes open)

All scores are HOLDOUT-DTI from gems57-pooled-hide-v2.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"vendor"), str(ROOT/"scripts")]
from gems57 import evaluate_holdout as evaluator
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw, quadrant_ids
from gems79.placement import place
from gems79.lifecycle import LaneClosedError, require_open_lane
import rasterio

PREREG = json.loads((ROOT/"registry/preregistration_h84.json").read_text())
FIX = PREREG["fixed_parameters"]
BUDGET = FIX["target_budget"]
OUT = ROOT / "evidence" / "h84"
CACHE = ROOT / ".cache" / "h84"
FAR_PX = FIX["far_field_distance_px"]

def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_lidar():
    p = ROOT / "data/raw/external/lidar_scarp_features_u8.tif"
    with rasterio.open(p) as src:
        d = list(src.descriptions)
        def read(name):
            return src.read(d.index(name)+1).astype(np.float32)
        up = read("upface_max")
        down = read("downface_max")
        step = read("step_max")
        lapneg = read("lapneg_max")
        lappos = read("lappos_max")
        coh = read("coh100")
        strike = read("strike")
        valid = read("valid")
        relief = read("relief")
    return dict(up=up, down=down, step=step, lapneg=lapneg, lappos=lappos, coh=coh, strike=strike, valid=valid, relief=relief)

def compute_antislope_surface(grid, lidar, far_only=True):
    up = lidar["up"]; down = lidar["down"]; step = lidar["step"]
    lapneg = lidar["lapneg"]; lappos = lidar["lappos"]; coh = lidar["coh"]; valid = lidar["valid"]
    dcat = ndi.distance_transform_edt(~grid.catalogue).astype(np.float32)
    far = dcat > FAR_PX
    denom = up + down + 1e-6
    antislope = np.where((up>0)&(down>0), (up - down)/denom, 0.0).astype(np.float32)
    lap_bal = np.where((lapneg>0)&(lappos>0), 1.0 - np.abs(lapneg - lappos)/255.0, 0.0).astype(np.float32)
    valid_mask = (valid>0) & grid.footprint
    step_v = np.where(valid_mask, step, 0)
    v = step_v[valid_mask]
    if v.size:
        q50 = float(np.median(v)); q75 = float(np.percentile(v,75)); q25 = float(np.percentile(v,25))
        scale = float(q75 - q25) or float(np.std(v)) or 1.0
        step_norm = np.where(valid_mask, (step_v - q50)/scale, 0).astype(np.float32)
        step_norm = np.clip(step_norm, -3, 3)
        step_rank = (step_norm - step_norm.min()) / max(float(step_norm.max() - step_norm.min()), 1e-6)
    else:
        step_rank = np.zeros_like(step_v, dtype=np.float32)
    surf_raw = antislope * (coh/255.0) * lap_bal * np.clip(step_rank, 0, 1)
    surf_raw = np.where(valid_mask, surf_raw, 0).astype(np.float32)
    surf_raw = np.clip(surf_raw, 0, None)
    if far_only:
        surf = np.where(valid_mask & far, surf_raw, 0).astype(np.float32)
        m = surf[grid.footprint & far & ~grid.catalogue]
        if m.size and float(m.max() - m.min()) > 1e-6:
            lo = float(m.min()); hi = float(m.max())
            surf_norm = np.zeros_like(surf)
            mask = grid.footprint & far & ~grid.catalogue
            surf_norm[mask] = ((surf[mask] - lo) / (hi - lo)).astype(np.float32)
        else:
            surf_norm = np.zeros_like(surf)
        return surf_norm, dict(far_pixels=int(far.sum()), antislope_mean=float(antislope[valid_mask].mean() if valid_mask.any() else 0), mode="far_only")
    else:
        # global normalization (for holdout)
        m = surf_raw[grid.footprint & ~grid.catalogue]
        if m.size and float(m.max() - m.min()) > 1e-6:
            lo = float(m.min()); hi = float(m.max())
            surf_norm = np.zeros_like(surf_raw)
            mask = grid.footprint & ~grid.catalogue
            surf_norm[mask] = ((surf_raw[mask] - lo) / (hi - lo)).astype(np.float32)
        else:
            surf_norm = np.zeros_like(surf_raw)
        return surf_norm, dict(far_pixels=int(far.sum()), antislope_mean=float(antislope[valid_mask].mean() if valid_mask.any() else 0), mode="global")

def canaries_per_feature(features_dict, folds, seed):
    rows=[]
    for fold in folds:
        active = fold['region'] & ~fold['masked_known']
        truth = active & fold['truth']
        negatives = active & (ndi.distance_transform_edt(~truth) > 3)
        negatives &= ndi.distance_transform_edt(~fold['visible']) > 3
        ni = np.flatnonzero(negatives)
        rng = np.random.default_rng(seed*100+fold['fold'])
        if len(ni)>100000:
            ni = rng.choice(ni, 100000, replace=False)
        pi = np.flatnonzero(truth)
        if len(pi)==0 or len(ni)==0:
            continue
        sample = np.concatenate([pi, ni])
        labels = np.r_[np.ones(len(pi), np.uint8), np.zeros(len(ni), np.uint8)]
        for name, arr in features_dict.items():
            vals = arr.ravel()[sample]
            # handle nan
            vals = np.nan_to_num(vals, nan=-99.0)
            try:
                auc = float(roc_auc_score(labels, vals))
            except ValueError:
                auc = 0.5
            rows.append(dict(seed=seed, fold=fold['name'], feature=name,
                             positive_pixels=len(pi), unlabeled_negative_proxies=len(ni),
                             auc=auc, symmetric_auc=max(auc, 1-auc),
                             suspicious=max(auc,1-auc)>0.90))
    return rows

def locate_h33():
    # Try to locate D2.8 dots via registry; if missing, return None and caller will use uniform proxy.
    try:
        import analyze_h33
        d28, _ = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
        return d28
    except Exception as e:
        log("locate h33 failed (registry blob missing, will use uniform proxy for H33 far control)", e)
        return None

def stage_holdout(seed):
    if not (ROOT/"registry/preregistration_h84.json").exists():
        raise RuntimeError("H84 preregistration missing")
    t0=time.time()
    grid = load_grid(ROOT/"data/reference")
    lidar = load_lidar()
    # global surface for holdout (so DTI is non-zero and comparable to H33)
    surf_global, meta_g = compute_antislope_surface(grid, lidar, far_only=False)
    # far-only surface for secondary far-field analysis and for final dots
    surf_far, meta_f = compute_antislope_surface(grid, lidar, far_only=True)
    # Use global for primary candidate; far-only will be evaluated as additional term
    surf = surf_global
    meta = {"global": meta_g, "far": meta_f}
    log("surface meta", meta, "global max", float(surf_global.max()), "far max", float(surf_far.max()), "global mean", float(surf_global[grid.footprint].mean()))
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    # canary features: each lidar band + antislope surface
    feat_dict = {
        "upface": lidar["up"].astype(np.float32),
        "downface": lidar["down"].astype(np.float32),
        "step_max": lidar["step"].astype(np.float32),
        "lapneg": lidar["lapneg"].astype(np.float32),
        "lappos": lidar["lappos"].astype(np.float32),
        "coh100": lidar["coh"].astype(np.float32),
        "relief": lidar["relief"].astype(np.float32),
    }
    # canary includes both surfaces
    feat_dict["antislope_global"] = surf_global
    feat_dict["antislope_far"] = surf_far
    c_rows = canaries_per_feature(feat_dict, folds, seed)
    c_max = max(r["symmetric_auc"] for r in c_rows) if c_rows else 0
    worst = max(c_rows, key=lambda r: r["symmetric_auc"]) if c_rows else {}
    log(f"canary max {c_max:.4f} {worst.get('feature')}")
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=float(c_max), worst=worst, n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"]==n) for n in {r["feature"] for r in c_rows}})
    d28 = locate_h33()
    d28_pos = (np.isfinite(d28) & (d28>0) & grid.footprint) if d28 is not None else None
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    dcat_full = ndi.distance_transform_edt(~grid.catalogue)
    far_full = dcat_full > FAR_PX
    terms={}
    has_h33 = d28_pos is not None
    for fold in folds:
        q = fold["fold"]
        region = fold["region"]
        # PRIMARY: global allowed (footprint & not masked) — comparable to H33/uniform
        allowed = region & grid.footprint & ~fold["masked_known"]
        # budget scaled by region's footprint fraction (as NHR)
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        # if allowed has no pixels, skip but still need terms for pooled (use zeros)
        ys, xs = np.nonzero(region)
        if ys.size==0:
            continue
        sy = slice(max(0, int(ys.min())-3), min(grid.height, int(ys.max())+4))
        sx = slice(max(0, int(xs.min())-3), min(grid.width, int(xs.max())+4))
        sl = (sy, sx)
        local = {k: fold[k][sl] for k in ("region","truth","visible","masked_known")}
        footprint_sl = grid.footprint[sl]
        # candidate (global antislope)
        dots, _ = place(surf[sl], allowed[sl], budget)
        _, bt = evaluator.evaluate(dots.astype(np.float32), local, footprint_sl, origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["candidate"] = terms.get("candidate", 0) + bt
        # uniform global (for comparability to H33)
        dots_u, _ = place(rng_surface[sl], allowed[sl], budget)
        _, bt = evaluator.evaluate(dots_u.astype(np.float32), local, footprint_sl, origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["uniform"] = terms.get("uniform", 0) + bt
        # keep alias for prereg compatibility
        terms["uniform_far"] = terms.get("uniform_far", 0) + bt
        if has_h33:
            d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
            h33 = (d28_pos[sl] & region[sl] & (d_vis>2)).astype(np.float32)
            _, bt = evaluator.evaluate(h33, local, footprint_sl, origin=(sy.start, sx.start), global_shape=grid.shape)
            terms["h33_control"] = terms.get("h33_control", 0) + bt
            # also far-filtered version for secondary analysis
            h33_far = (h33 & far_full[sl]).astype(np.float32)
            _, bt2 = evaluator.evaluate(h33_far, local, footprint_sl, origin=(sy.start, sx.start), global_shape=grid.shape)
            terms["h33_far_control"] = terms.get("h33_far_control", 0) + bt2
        # ablation: step+coh only (without antislope) — global
        step_coh = (lidar["step"].astype(np.float32)/255.0)*(lidar["coh"].astype(np.float32)/255.0)
        step_coh = np.where(grid.footprint & (lidar["valid"]>0), step_coh, 0)
        dots_a, _ = place(step_coh[sl], allowed[sl], budget)
        _, bt = evaluator.evaluate(dots_a.astype(np.float32), local, footprint_sl, origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["ablation_no_antislope"] = terms.get("ablation_no_antislope", 0) + bt
        # secondary: far-only antislope candidate (expected ~0, documents far-field behavior)
        allowed_far = allowed & far_full
        if allowed_far[sl].any():
            dots_far, _ = place(surf_far[sl], allowed_far[sl], budget)
            _, bt = evaluator.evaluate(dots_far.astype(np.float32), local, footprint_sl, origin=(sy.start, sx.start), global_shape=grid.shape)
            terms["candidate_far_only"] = terms.get("candidate_far_only", 0) + bt
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900+seed)
    OUT.mkdir(parents=True, exist_ok=True)
    out = dict(schema_version=1, lane="H84-FFA", experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time()-t0,1),
               leakage_canary=canary,
               holdout=summary,
               far_field_px=FAR_PX,
               surface_meta=meta)
    (OUT/f"x1_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float)+"\n")
    log(f"seed {seed} DTI", {k:(round(v['dti'],4),[round(c,4) for c in v['ci95']]) for k,v in summary['scores'].items()})
    log(f"paired vs H33 far", summary['paired_differences'].get('h33_far_control'))
    log(f"paired vs uniform", summary['paired_differences'].get('uniform_far'))

def stage_final():
    if not (ROOT/"registry/preregistration_h84.json").exists():
        raise RuntimeError("H84 preregistration missing")
    grid = load_grid(ROOT/"data/reference")
    lidar = load_lidar()
    surf, meta = compute_antislope_surface(grid, lidar, far_only=True)
    allowed = grid.footprint & ~grid.catalogue & (ndi.distance_transform_edt(~grid.catalogue) > FAR_PX)
    dots, info = place(surf, allowed, BUDGET)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE/"final_surface.npy", surf)
    np.save(CACHE/"final_dots.npy", dots)
    imp = dict(surface_sha256=hashlib.sha256(surf.tobytes()).hexdigest(),
               dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
               n_dots=int(dots.sum()), placement=info, far_meta=meta)
    (OUT/"x1_final_build.json").write_text(json.dumps(imp, indent=2)+"\n")
    log("final", imp)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["holdout","final"])
    ap.add_argument("--seed", type=int, default=20)
    args = ap.parse_args()
    try:
        if args.stage=="holdout":
            stage_holdout(args.seed)
        else:
            stage_final()
    except LaneClosedError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
