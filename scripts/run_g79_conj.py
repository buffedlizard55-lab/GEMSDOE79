#!/usr/bin/env python3
"""G79-CONJ preregistered experiment runner (registry/preregistration_g79_conj.json).

Stages: canary | seed20 | seed30 | live
Reuse, don't rebuild: THVC static stack builder + network mechanics + CC emitter
(src/gems79/thvc_*), shared gems57 holdout/evaluator/metric/writer. New code is
only the CONJ channels and the adaptive Dinkelbach emitter (src/gems79/conj.py).
"""
from __future__ import annotations

import argparse
import gc
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
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]

import lightgbm as lgb  # noqa: E402
from gems57 import evaluate_holdout, holdout, metric  # noqa: E402
from gems57.grid import Grid  # noqa: E402
from gems79.conj import CONJ_FEATURE_NAMES, adaptive_dinkelbach_emit, compute_conj_channels  # noqa: E402
from gems79.thvc_features import (  # noqa: E402
    MECH_FEATURE_NAMES,
    STATIC_FEATURE_NAMES,
    TF_BAND_NAMES,
    compute_network_mechanics,
    rss_mb,
)
from gems79.thvc_model import _prior_correct, charnes_cooper_submodular_emit  # noqa: E402

CACHE = ROOT / ".cache" / "g79_conj"
THVC_CACHE = ROOT / ".cache" / "g79_thvc"
MMAP = THVC_CACHE / "static_fp70.f32.mmap"
CUES = MMAP.with_suffix(".cues.npz")
STRUCT3 = np.ones((3, 3), dtype=bool)
N_STATIC = len(STATIC_FEATURE_NAMES)
N_MECH = len(MECH_FEATURE_NAMES)
N_CONJ = len(CONJ_FEATURE_NAMES)
ALL_NAMES = STATIC_FEATURE_NAMES + MECH_FEATURE_NAMES + CONJ_FEATURE_NAMES


def load_grid_and_depth():
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
        transform, crs = ds.transform, ds.crs
    with rasterio.open(ROOT / "data/raw/existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & footprint
    band = TF_BAND_NAMES.index("depth_to_base_surf") + 1
    with rasterio.open(ROOT / "data/raw/training_features.tif") as ds:
        depth = ds.read(band).astype(np.float64)
    grid = Grid(footprint, cat, str(crs), transform, footprint.shape[0], footprint.shape[1])
    return grid, footprint, cat, depth


def static_memmap(footprint):
    return np.memmap(MMAP, dtype="float32", mode="r",
                     shape=(int(footprint.sum()), N_STATIC))


def symmetric_auc(y: np.ndarray, x: np.ndarray) -> float:
    if y.sum() == 0 or y.sum() == y.size or np.ptp(x) == 0:
        return 0.5
    a = roc_auc_score(y, x)
    return float(max(a, 1.0 - a))


def stage_canary() -> dict:
    grid, footprint, cat, depth = load_grid_and_depth()
    out = {"lane": "G79-CONJ", "experiment": "EXP-CONJ-1", "threshold": 0.90, "seeds": {}}
    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        vis = folds[0]["visible"]
        truth = folds[0]["hidden_all"]
        active = np.zeros_like(footprint)
        for f in folds:
            active |= footprint & f["region"] & ~f["masked_known"]
        conj = compute_conj_channels(vis, footprint, depth)
        fp_idx = np.flatnonzero(footprint)
        act_local = np.flatnonzero(active.ravel()[fp_idx])
        y_all = truth.ravel()[fp_idx][act_local]
        rng = np.random.default_rng(7900 + seed)
        neg = np.flatnonzero(~y_all)
        if neg.size > 400_000:
            neg = rng.choice(neg, size=400_000, replace=False)
        sel = np.sort(np.concatenate([np.flatnonzero(y_all), neg]))
        rows = {}
        for j, name in enumerate(CONJ_FEATURE_NAMES):
            auc = symmetric_auc(y_all[sel], conj[act_local[sel], j].astype(np.float64))
            rows[name] = {"symmetric_auc": round(auc, 6), "passed": bool(auc <= 0.90)}
        out["seeds"][str(seed)] = {
            "withheld_positive_pixels": int(y_all.sum()),
            "active_pixels": int(act_local.size),
            "channels": rows,
            "max_symmetric_auc": max(r["symmetric_auc"] for r in rows.values()),
            "all_passed": all(r["passed"] for r in rows.values()),
        }
        print(f"[canary seed={seed}] max AUC={out['seeds'][str(seed)]['max_symmetric_auc']:.4f} "
              f"all_passed={out['seeds'][str(seed)]['all_passed']}", flush=True)
        del conj
        gc.collect()
    out["all_passed"] = all(s["all_passed"] for s in out["seeds"].values())
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "canary.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def build_training_rows(vis, footprint, depth, static_mm, seed_base: int, n_draws: int = 3):
    """Pooled nested hide-to-recover rows inside `vis` (THVC shard recipe, pooled)."""
    comp, n_comp = ndi.label(vis, STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)
    all_ids = np.arange(1, n_comp + 1, dtype=np.int32)
    target_px = 0.22 * float(vis.sum())
    Xs, ys, qs, ws = [], [], [], []
    tot_pos = tot_act = 0
    for r in range(n_draws):
        rng = np.random.default_rng(seed_base + 137 * r)
        perm = rng.permutation(all_ids)
        cum = np.cumsum(sizes[perm])
        k = int(np.searchsorted(cum, target_px)) + 1
        chosen = perm[: min(k, perm.size)]
        hidden = np.isin(comp, chosen) & vis
        collar = ndi.distance_transform_edt(~hidden) <= 3.0
        sim_vis = vis & ~collar
        known = vis & ~hidden
        active = footprint & ~known
        q_fp = metric.kernel(ndi.distance_transform_edt(~hidden)).astype(np.float32)[footprint]
        y_fp = hidden[footprint]
        act_fp = active[footprint]
        mech = compute_network_mechanics(sim_vis, footprint, CUES).astype(np.float16)
        conj = compute_conj_channels(sim_vis, footprint, depth).astype(np.float16)
        elig = act_fp
        pos_idx = np.flatnonzero(elig & y_fp)
        halo_pool = np.flatnonzero(elig & (~y_fp) & (q_fp > 0.0))
        far_pool = np.flatnonzero(elig & (~y_fp) & (q_fp == 0.0))
        n_halo = min(halo_pool.size, 30_000)
        n_far = min(far_pool.size, 90_000)
        sh = rng.choice(halo_pool, size=n_halo, replace=False) if n_halo else np.empty(0, np.int64)
        sf = rng.choice(far_pool, size=n_far, replace=False) if n_far else np.empty(0, np.int64)
        idx = np.sort(np.concatenate([pos_idx, sh, sf]))
        X = np.empty((idx.size, N_STATIC + N_MECH + N_CONJ), dtype=np.float32)
        X[:, :N_STATIC] = static_mm[idx]
        X[:, N_STATIC:N_STATIC + N_MECH] = mech[idx]
        X[:, N_STATIC + N_MECH:] = conj[idx]
        is_pos = y_fp[idx]
        is_halo = (~is_pos) & (q_fp[idx] > 0.0)
        wh = float(halo_pool.size / max(n_halo, 1)) if n_halo else 1.0
        wf = float(far_pool.size / max(n_far, 1)) if n_far else 1.0
        w = np.where(is_pos, 1.0, np.where(is_halo, wh, wf)).astype(np.float32)
        Xs.append(X); ys.append(is_pos.astype(np.float32)); qs.append(q_fp[idx]); ws.append(w)
        tot_pos += int(pos_idx.size); tot_act += int(elig.sum())
        print(f"  draw {r}: rows={idx.size:,} pos={pos_idx.size:,} RSS={rss_mb():.0f}MB", flush=True)
        del hidden, collar, sim_vis, known, active, q_fp, y_fp, act_fp, mech, conj, X
        gc.collect()
    X = np.concatenate(Xs); y = np.concatenate(ys); q = np.concatenate(qs); w = np.concatenate(ws)
    return X, y, q, w, float(tot_pos / max(tot_act, 1)), float(y.mean())


def fit_ensemble(X, y, q, w, seed: int):
    yi = y.astype(np.int32)
    w_mod = np.clip(w / (np.median(w[w > 1.0]) if np.any(w > 1.0) else 1.0), 0.25, 10.0)
    deep = lgb.LGBMClassifier(n_estimators=140, learning_rate=0.06, num_leaves=63, max_depth=8,
                              min_child_samples=140, subsample=0.80, subsample_freq=1,
                              colsample_bytree=0.68, reg_alpha=3.0, reg_lambda=15.0,
                              n_jobs=2, random_state=seed + 11, verbose=-1)
    deep.fit(X, yi)
    et = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.06, num_leaves=35, max_depth=6,
                            min_child_samples=220, extra_trees=True, subsample=0.80,
                            subsample_freq=1, colsample_bytree=0.62, reg_alpha=4.0,
                            reg_lambda=20.0, n_jobs=2, random_state=seed + 23, verbose=-1)
    et.fit(X, yi)
    qm = lgb.LGBMRegressor(objective="regression", n_estimators=135, learning_rate=0.06,
                           num_leaves=47, max_depth=7, min_child_samples=170, subsample=0.80,
                           subsample_freq=1, colsample_bytree=0.68, reg_alpha=3.0,
                           reg_lambda=18.0, n_jobs=2, random_state=seed + 53, verbose=-1)
    qm.fit(X, q, sample_weight=w_mod)
    return {"deep": deep, "et": et, "q": qm}


def predict_full(models, static_mm, mech16, conj16, true_pi, sample_pi, use_conj=True):
    n = static_mm.shape[0]
    n_c = N_STATIC + N_MECH + (N_CONJ if use_conj else 0)
    p_out = np.zeros(n, dtype=np.float32)
    q_out = np.zeros(n, dtype=np.float32)
    chunk = 400_000
    for s in range(0, n, chunk):
        e = min(s + chunk, n)
        xb = np.empty((e - s, n_c), dtype=np.float32)
        idx = np.arange(s, e)
        xb[:, :N_STATIC] = static_mm[idx]
        xb[:, N_STATIC:N_STATIC + N_MECH] = mech16[idx]
        if use_conj:
            xb[:, N_STATIC + N_MECH:] = conj16[idx]
        p1 = _prior_correct(models["deep"].booster_.predict(xb, num_threads=2), true_pi, sample_pi)
        p2 = _prior_correct(models["et"].booster_.predict(xb, num_threads=2), true_pi, sample_pi)
        p_out[s:e] = 0.6 * p1 + 0.4 * p2
        q_out[s:e] = np.clip(models["q"].booster_.predict(xb, num_threads=2), 0.0, 1.0)
        del xb
    return p_out, q_out


def train_and_predict(vis, footprint, depth, static_mm, seed_base: int):
    """Returns (p96,q96,p84,q84,meta) footprint vectors."""
    t0 = time.time()
    X, y, q, w, true_pi, sample_pi = build_training_rows(vis, footprint, depth, static_mm, seed_base)
    mech16 = compute_network_mechanics(vis, footprint, CUES).astype(np.float16)
    conj16 = compute_conj_channels(vis, footprint, depth).astype(np.float16)
    n = static_mm.shape[0]
    p96 = np.zeros(n, np.float32); q96 = np.zeros(n, np.float32)
    p84 = np.zeros(n, np.float32); q84 = np.zeros(n, np.float32)
    gains = np.zeros(N_STATIC + N_MECH + N_CONJ)
    for rep, sd in enumerate((seed_base, seed_base + 41)):
        m = fit_ensemble(X, y, q, w, seed=sd)
        gains += 0.5 * m["deep"].booster_.feature_importance(importance_type="gain")
        pr, qr = predict_full(m, static_mm, mech16, conj16, true_pi, sample_pi, use_conj=True)
        p96 += 0.5 * pr; q96 += 0.5 * qr
        del m, pr, qr
        m84 = fit_ensemble(X[:, :N_STATIC + N_MECH], y, q, w, seed=sd + 7)
        pr, qr = predict_full(m84, static_mm, mech16, conj16, true_pi, sample_pi, use_conj=False)
        p84 += 0.5 * pr; q84 += 0.5 * qr
        del m84, pr, qr
        gc.collect()
    top = sorted(({"feature": ALL_NAMES[i], "gain_share": round(float(gains[i] / max(gains.sum(), 1e-9)), 6)}
                  for i in range(len(ALL_NAMES))), key=lambda r: -r["gain_share"])[:25]
    meta = {"train_seconds": round(time.time() - t0, 1), "train_rows": int(X.shape[0]),
            "true_pi": true_pi, "sample_pi": sample_pi, "top25_gain": top,
            "conj_gain_share_total": round(float(gains[N_STATIC + N_MECH:].sum() / max(gains.sum(), 1e-9)), 6)}
    del X, y, q, w, mech16, conj16
    gc.collect()
    return p96, q96, p84, q84, meta


def to2d(vec, footprint):
    a = np.zeros(footprint.shape, dtype=np.float32)
    a[footprint] = vec
    return a


def stage_seed(seed: int) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    ckpt = CACHE / f"eval_seed{seed}.json"
    if ckpt.exists():
        print(f"[seed={seed}] reusing {ckpt}", flush=True)
        return json.loads(ckpt.read_text())
    t0 = time.time()
    grid, footprint, cat, depth = load_grid_and_depth()
    static_mm = static_memmap(footprint)
    folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    vis = folds[0]["visible"]
    d_vis = ndi.distance_transform_edt(~vis)
    allow = footprint & (d_vis > 2.0)
    del d_vis

    post = CACHE / f"posteriors_seed{seed}.npz"
    if post.exists():
        z = np.load(post)
        p96, q96, p84, q84 = (z[k].astype(np.float32) for k in ("p96", "q96", "p84", "q84"))
        meta = json.loads((CACHE / f"trainmeta_seed{seed}.json").read_text())
    else:
        p96, q96, p84, q84, meta = train_and_predict(vis, footprint, depth, static_mm, seed_base=7000 + seed)
        np.savez_compressed(post, p96=p96.astype(np.float16), q96=q96.astype(np.float16),
                            p84=p84.astype(np.float16), q84=q84.astype(np.float16))
        (CACHE / f"trainmeta_seed{seed}.json").write_text(json.dumps(meta, indent=2) + "\n")

    P, Q = to2d(p96, footprint), to2d(q96, footprint)
    P84, Q84 = to2d(p84, footprint), to2d(q84, footprint)
    del p96, q96, p84, q84

    exp2 = charnes_cooper_submodular_emit(P, Q, allow, lambda_fp=0.0022, min_sep_px=1.9,
                                          max_budget=40_000, min_budget=20_000)
    exp3, e3info = adaptive_dinkelbach_emit(P, Q, allow, min_sep_px=1.9,
                                             max_budget=55_000, min_budget=20_000)
    abl = charnes_cooper_submodular_emit(P84, Q84, allow, lambda_fp=0.0022, min_sep_px=1.9,
                                         max_budget=40_000, min_budget=20_000)
    d28_path = ROOT / ".cache/registry/bfb7e86d046dd178c3d6ab60522861b5464dd420.tif"
    with rasterio.open(d28_path) as ds:
        d28 = (ds.read(1) > 0) & footprint
    c2 = (d28 & allow).astype(np.float32)
    rng = np.random.default_rng(79000 + seed)
    c0 = np.zeros(footprint.shape, dtype=np.float32)
    c0.ravel()[rng.choice(np.flatnonzero(allow), size=37_654, replace=False)] = 1.0

    preds = {"EXP-CONJ-2_cc": exp2, "EXP-CONJ-3_dinkelbach": exp3,
             "ABL_zero_conj_cc": abl, "C2_h33_analogue_foldfair": c2, "C0_random_B37654": c0}
    surface_sha = hashlib.sha256(np.ascontiguousarray(P).tobytes()).hexdigest()
    terms = {}
    per_fold = {}
    for name, pred in preds.items():
        acc = None; fl = []
        for fi, fold in enumerate(folds):
            res, tm = evaluate_holdout.evaluate(pred, fold, footprint)
            fl.append({"fold": fi, "dti": round(float(res["dti"]), 6),
                       "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"])})
            acc = tm if acc is None else acc + tm
        terms[name] = acc; per_fold[name] = fl
    cand = "EXP-CONJ-3_dinkelbach"
    pooled = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810 + seed, candidate=cand)
    pooled["per_fold"] = per_fold
    out = {"seed": seed, "evaluator_version": pooled["evaluator_version"],
           "elapsed_seconds": round(time.time() - t0, 1), "train_meta": meta,
           "exp3_emission": e3info, "surface_p_sha256_decoded": surface_sha,
           "dot_counts": {k: int((v > 0).sum()) for k, v in preds.items()},
           "pooled": pooled}
    ckpt.write_text(json.dumps(out, indent=2) + "\n")
    np.savez_compressed(CACHE / f"dots_seed{seed}.npz",
                        **{k: np.flatnonzero(v > 0).astype(np.int32) for k, v in preds.items()})
    for k, v in pooled["scores"].items():
        print(f"[seed={seed}] {k}: HOLDOUT-DTI={v['dti']:.6f} CI[{v['ci95'][0]:.4f},{v['ci95'][1]:.4f}] "
              f"n={v['withheld_positive_pixels']} dots={out['dot_counts'][k]:,}", flush=True)
    return out


def stage_live() -> dict:
    e20 = json.loads((CACHE / "eval_seed20.json").read_text())
    s = e20["pooled"]["scores"]
    chosen = "EXP-CONJ-3_dinkelbach" if s["EXP-CONJ-3_dinkelbach"]["dti"] > s["EXP-CONJ-2_cc"]["dti"] else "EXP-CONJ-2_cc"
    grid, footprint, cat, depth = load_grid_and_depth()
    static_mm = static_memmap(footprint)
    post = CACHE / "posteriors_live.npz"
    if post.exists():
        z = np.load(post)
        p96, q96 = z["p96"].astype(np.float32), z["q96"].astype(np.float32)
        meta = json.loads((CACHE / "trainmeta_live.json").read_text())
    else:
        p96, q96, _p84, _q84, meta = train_and_predict(cat, footprint, depth, static_mm, seed_base=9100)
        np.savez_compressed(post, p96=p96.astype(np.float16), q96=q96.astype(np.float16))
        (CACHE / "trainmeta_live.json").write_text(json.dumps(meta, indent=2) + "\n")
    P, Q = to2d(p96, footprint), to2d(q96, footprint)
    d_cat = ndi.distance_transform_edt(~cat)
    allow = footprint & (d_cat > 2.0)
    if chosen == "EXP-CONJ-3_dinkelbach":
        dots, info = adaptive_dinkelbach_emit(P, Q, allow, min_sep_px=1.9,
                                               max_budget=55_000, min_budget=20_000)
    else:
        dots = charnes_cooper_submodular_emit(P, Q, allow, lambda_fp=0.0022, min_sep_px=1.9,
                                              max_budget=40_000, min_budget=20_000)
        info = {"emitted_dots": int((dots > 0).sum()), "emission": "cc_lambda_0.0022_sep_1.9_cap_40000"}
    # Surface for the pre-placement uniqueness audit: p normalized on allowed domain.
    surf = np.where(allow, P / max(float(P[allow].max()), 1e-9), 0.0).astype(np.float32)
    np.savez_compressed(CACHE / "live_dots.npz",
                        dots=np.flatnonzero(dots > 0).astype(np.int32),
                        surface_sha=np.array([hashlib.sha256(np.ascontiguousarray(surf).tobytes()).hexdigest()]))
    from gems57.grid import write_geotiff
    write_geotiff(CACHE / "live_surface.tif", np.clip(surf, 0, 1).astype(np.float32))
    write_geotiff(CACHE / "live_dots.tif", dots.astype(np.float32))
    meta_out = {"chosen_emission_from_seed20": chosen, "emission_info": info,
                "dots": int((dots > 0).sum()), "train_meta": meta,
                "surface_decoded_sha256": hashlib.sha256(np.ascontiguousarray(surf).tobytes()).hexdigest(),
                "dots_decoded_sha256": hashlib.sha256(np.ascontiguousarray(dots.astype(np.float32)).tobytes()).hexdigest()}
    (CACHE / "live_meta.json").write_text(json.dumps(meta_out, indent=2) + "\n")
    print(json.dumps({k: meta_out[k] for k in ("chosen_emission_from_seed20", "dots")}, indent=1), flush=True)
    print(json.dumps(info, indent=1, default=float), flush=True)
    return meta_out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", required=True, choices=("canary", "seed20", "seed30", "live"))
    a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    if a.stage == "canary":
        stage_canary()
    elif a.stage == "seed20":
        stage_seed(20)
    elif a.stage == "seed30":
        stage_seed(30)
    else:
        stage_live()


if __name__ == "__main__":
    main()
