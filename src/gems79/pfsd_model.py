"""Flank-decontaminated Dual-Expert (Uncorrupted Pure-Physics + Nested Elastic-Mechanical)
spatial meta-learner and Quadrant-Equilibrated Charnes-Cooper Submodular Allocator for Lane H79-PFSD.

Resolves all three root-cause bottlenecks identified in G79-THVC:
1. Uncorrupted 100%-visible out-of-quadrant Pure-Physics Expert (eliminating the 78%
   positive-as-negative simulated-hide label corruption on zero-catalogue physical training).
2. Strict 300-m (3.0 px) unhidden-flank decontamination in BOTH Stage-1 shard construction
   AND Stage-2 Dual-Expert meta-learning (stopping Stage 1 & Stage 2 from labelling unhidden
   Quaternary fault scarps as y = 0 / q = 0), while preserving exact Horvitz-Thompson
   importance weights and 250k-pixel uniform inner mean conservation.
3. Inner-CV-selected quadrant tail-scale equilibration before Charnes-Cooper submodular
   300-m kernel allocation (preventing high-strain SW Walker Lane from starving NE/NW folds).
"""
from __future__ import annotations

import gc
import time
from itertools import combinations
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from gems57 import metric
from gems79.pfsd_features import (
    PFSD_ALL_FEATURE_NAMES,
    PFSD_STATIC_FEATURE_NAMES,
    compute_network_mechanics,
    drop_file_cache,
    rss_mb,
)
from gems79.thvc_features import STRUCT3
from gems79.thvc_model import (
    _sparse_line_integral,
    charnes_cooper_submodular_emit,
    poisson_disk_emit,
)

PRED_CHUNK_ROWS = 320_000


def _compute_hard_neg_weights(static_mm: np.memmap, neg_idx: np.ndarray, mmap_path: Path) -> np.ndarray:
    m_col = PFSD_STATIC_FEATURE_NAMES.index("mountain_wall_ratio")
    r_col = PFSD_STATIC_FEATURE_NAMES.index("road_proximity_confound")
    sc_col = PFSD_STATIC_FEATURE_NAMES.index("scarp_unified_step")
    m_neg = np.asarray(static_mm[neg_idx, m_col], dtype=np.float32)
    r_neg = np.asarray(static_mm[neg_idx, r_col], dtype=np.float32)
    sc_neg = np.asarray(static_mm[neg_idx, sc_col], dtype=np.float32)
    drop_file_cache(mmap_path)
    raw = (1.0 + 0.85 * np.clip(m_neg, 0.0, 2.0) + 0.95 * r_neg + 0.35 * sc_neg).astype(np.float32)
    return raw / max(float(raw.mean()), 1e-6)


def fit_pure_physics_ensemble(
    X_bin: np.ndarray,
    y_bin: np.ndarray,
    w_bin: np.ndarray,
    X_reg: np.ndarray,
    q_reg: np.ndarray,
    w_reg: np.ndarray,
    seed: int = 79,
) -> dict[str, Any]:
    """Fit uncorrupted zero-catalogue 3-family physical expert (LightGBM + ExtraTrees-LGBM + HistGBDT)."""
    pos_w = float(w_bin[y_bin == 1].sum())
    neg_w = float(w_bin[y_bin == 0].sum())
    spw = min(max(neg_w / max(pos_w, 1.0), 1.0), 5.0)

    m_lgb = lgb.LGBMClassifier(
        n_estimators=250,
        learning_rate=0.055,
        num_leaves=63,
        min_child_samples=80,
        subsample=0.80,
        subsample_freq=1,
        colsample_bytree=0.68,
        reg_alpha=2.0,
        reg_lambda=8.0,
        scale_pos_weight=spw,
        n_jobs=2,
        random_state=seed,
        verbose=-1,
    )
    m_lgb.fit(X_bin, y_bin, sample_weight=w_bin)

    m_et = lgb.LGBMClassifier(
        n_estimators=260,
        learning_rate=0.06,
        num_leaves=95,
        extra_trees=True,
        min_child_samples=70,
        subsample=0.80,
        subsample_freq=1,
        colsample_bytree=0.58,
        reg_alpha=1.5,
        reg_lambda=10.0,
        scale_pos_weight=spw,
        n_jobs=2,
        random_state=seed + 17,
        verbose=-1,
    )
    m_et.fit(X_bin, y_bin, sample_weight=w_bin)

    m_hgb = HistGradientBoostingRegressor(
        loss="squared_error",
        max_iter=130,
        learning_rate=0.065,
        max_leaf_nodes=47,
        min_samples_leaf=80,
        l2_regularization=6.0,
        early_stopping=True,
        random_state=seed + 31,
    )
    m_hgb.fit(X_reg, q_reg, sample_weight=w_reg)

    base_pi = float(y_bin.mean())
    sample_pi = min(max((pos_w * spw) / max(pos_w * spw + neg_w, 1.0), 1e-5), 0.999)
    return {
        "lgb_deep": m_lgb,
        "lgb_et": m_et,
        "hgb_q": m_hgb,
        "base_pi": base_pi,
        "sample_pi": sample_pi,
    }


def _prior_correct(p_raw: np.ndarray, true_pi: float, sample_pi: float) -> np.ndarray:
    p_c = np.clip(p_raw.astype(np.float64), 1e-6, 1.0 - 1e-6)
    odds_mult = (true_pi / max(1.0 - true_pi, 1e-9)) / (sample_pi / max(1.0 - sample_pi, 1e-9))
    corr = (p_c * odds_mult) / (1.0 - p_c + p_c * odds_mult)
    return corr.astype(np.float32)


def predict_pure_physics_rows(
    model: dict[str, Any],
    static_mm: np.memmap,
    mmap_path: Path,
    row_indices: np.ndarray,
    true_pi: float,
) -> tuple[np.ndarray, np.ndarray]:
    n = row_indices.size
    p_out = np.empty(n, dtype=np.float32)
    q_out = np.empty(n, dtype=np.float32)
    for s in range(0, n, PRED_CHUNK_ROWS):
        e = min(s + PRED_CHUNK_ROWS, n)
        sl = row_indices[s:e]
        X_c = np.nan_to_num(np.asarray(static_mm[sl], dtype=np.float32), nan=0.0, posinf=1e7, neginf=-1e7)
        drop_file_cache(mmap_path)
        p1 = model["lgb_deep"].booster_.predict(X_c, num_threads=2)
        p2 = model["lgb_et"].booster_.predict(X_c, num_threads=2)
        p_raw = 0.55 * p1 + 0.45 * p2
        p_out[s:e] = _prior_correct(p_raw, true_pi=true_pi, sample_pi=model["sample_pi"])
        q_out[s:e] = np.clip(model["hgb_q"].predict(X_c), 0.0, 1.0).astype(np.float32)
        del X_c
    return p_out, q_out


def run_pure_physics_oof(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    quad_fp: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    neg_per_fold: int = 110_000,
    halo_per_fold: int = 38_000,
    seed: int = 79,
    fit_full_model: bool = False,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any] | None]:
    """Train uncorrupted zero-catalogue Pure-Physics Expert strictly out-of-quadrant."""
    n_fp = int(footprint.sum())
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    quad_2d = np.full(footprint.shape, -1, dtype=np.int16)
    quad_2d[footprint] = quad_fp

    p_phys_oof = np.zeros(n_fp, dtype=np.float32)
    q_phys_oof = np.zeros(n_fp, dtype=np.float32)
    rng = np.random.default_rng(seed)

    for q_val in range(4):
        vis_tr_2d = vis & (quad_2d != q_val)
        d_tr = ndi.distance_transform_edt(~vis_tr_2d)[footprint].astype(np.float32)
        in_tr = quad_fp != q_val

        pos_idx = np.flatnonzero(in_tr & vis_tr_2d[footprint])
        halo_pool = np.flatnonzero(in_tr & (~vis_tr_2d[footprint]) & (d_tr < 3.0))
        clean_neg_pool = np.flatnonzero(in_tr & (d_tr > 3.0))

        n_neg = min(neg_per_fold, clean_neg_pool.size)
        neg_idx = rng.choice(clean_neg_pool, size=n_neg, replace=False)
        neg_idx.sort()
        w_neg = _compute_hard_neg_weights(static_mm, neg_idx, mmap_path)

        X_pos = np.nan_to_num(np.asarray(static_mm[pos_idx], dtype=np.float32), nan=0.0, posinf=1e7, neginf=-1e7)
        X_neg = np.nan_to_num(np.asarray(static_mm[neg_idx], dtype=np.float32), nan=0.0, posinf=1e7, neginf=-1e7)
        drop_file_cache(mmap_path)

        X_bin = np.vstack([X_pos, X_neg])
        y_bin = np.concatenate([np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)])
        w_bin = np.concatenate([np.ones(pos_idx.size, dtype=np.float32), w_neg])

        n_halo = min(halo_per_fold, halo_pool.size)
        halo_idx = rng.choice(halo_pool, size=n_halo, replace=False) if n_halo > 0 else np.empty(0, dtype=np.int64)
        halo_idx.sort()
        X_halo = (
            np.nan_to_num(np.asarray(static_mm[halo_idx], dtype=np.float32), nan=0.0, posinf=1e7, neginf=-1e7)
            if halo_idx.size
            else np.empty((0, X_pos.shape[1]), dtype=np.float32)
        )
        drop_file_cache(mmap_path)

        X_reg = np.vstack([X_pos, X_halo, X_neg])
        q_reg = np.concatenate(
            [
                np.ones(pos_idx.size, dtype=np.float32),
                metric.kernel(d_tr[halo_idx]).astype(np.float32) if halo_idx.size else np.empty(0, dtype=np.float32),
                np.zeros(neg_idx.size, dtype=np.float32),
            ]
        )
        true_pi = float(pos_idx.size / max(int(in_tr.sum()), 1))
        neg_scale = min(max(float(clean_neg_pool.size) / max(neg_idx.size, 1), 1.0), 30.0)
        halo_scale = min(max(float(halo_pool.size) / max(halo_idx.size, 1), 1.0), 8.0) if halo_idx.size else 1.0
        w_reg = np.concatenate(
            [
                np.full(pos_idx.size, 3.5, dtype=np.float32),
                np.full(halo_idx.size, 1.5 * halo_scale / 4.0, dtype=np.float32),
                w_neg * (neg_scale / 10.0),
            ]
        )
        del X_pos, X_neg, X_halo

        pm = fit_pure_physics_ensemble(X_bin, y_bin, w_bin, X_reg, q_reg, w_reg, seed=seed + 101 * q_val)
        del X_bin, y_bin, w_bin, X_reg, q_reg, w_reg
        gc.collect()

        va_rows = np.flatnonzero(quad_fp == q_val)
        p_phys_oof[va_rows], q_phys_oof[va_rows] = predict_pure_physics_rows(pm, static_mm, mmap_path, va_rows, true_pi=true_pi)
        del pm, d_tr
        gc.collect()

    full_model = None
    if fit_full_model:
        d_all = ndi.distance_transform_edt(~vis)[footprint].astype(np.float32)
        pos_all = np.flatnonzero(vis[footprint])
        halo_all_pool = np.flatnonzero((~vis[footprint]) & (d_all < 3.0))
        neg_all_pool = np.flatnonzero(d_all > 3.0)
        neg_all = rng.choice(neg_all_pool, size=min(int(neg_per_fold * 1.35), neg_all_pool.size), replace=False)
        neg_all.sort()
        halo_all = rng.choice(halo_all_pool, size=min(int(halo_per_fold * 1.35), halo_all_pool.size), replace=False)
        halo_all.sort()
        w_neg_all = _compute_hard_neg_weights(static_mm, neg_all, mmap_path)
        Xp = np.nan_to_num(np.asarray(static_mm[pos_all], dtype=np.float32), nan=0.0, posinf=1e7, neginf=-1e7)
        Xh = np.nan_to_num(np.asarray(static_mm[halo_all], dtype=np.float32), nan=0.0, posinf=1e7, neginf=-1e7)
        Xn = np.nan_to_num(np.asarray(static_mm[neg_all], dtype=np.float32), nan=0.0, posinf=1e7, neginf=-1e7)
        drop_file_cache(mmap_path)

        Xb = np.vstack([Xp, Xn])
        yb = np.concatenate([np.ones(pos_all.size, dtype=np.int32), np.zeros(neg_all.size, dtype=np.int32)])
        wb = np.concatenate([np.ones(pos_all.size, dtype=np.float32), w_neg_all])

        Xr = np.vstack([Xp, Xh, Xn])
        qr = np.concatenate(
            [
                np.ones(pos_all.size, dtype=np.float32),
                metric.kernel(d_all[halo_all]).astype(np.float32),
                np.zeros(neg_all.size, dtype=np.float32),
            ]
        )
        neg_sc = min(max(float(neg_all_pool.size) / max(neg_all.size, 1), 1.0), 30.0)
        halo_sc = min(max(float(halo_all_pool.size) / max(halo_all_pool.size if halo_all.size == 0 else halo_all.size, 1), 1.0), 8.0)
        wr = np.concatenate(
            [
                np.full(pos_all.size, 3.5, dtype=np.float32),
                np.full(halo_all.size, 1.5 * halo_sc / 4.0, dtype=np.float32),
                w_neg_all * (neg_sc / 10.0),
            ]
        )
        del Xp, Xh, Xn, d_all
        full_model = fit_pure_physics_ensemble(Xb, yb, wb, Xr, qr, wr, seed=seed + 777)
        full_model["true_pi_all"] = float(pos_all.size / max(n_fp, 1))
        del Xb, yb, wb, Xr, qr, wr
        gc.collect()

    return p_phys_oof, q_phys_oof, full_model


def build_decontaminated_quadrant_shards(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    quad_fp: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    cues_npz_path: Path,
    n_draws: int = 3,
    hide_frac: float = 0.22,
    buffer_px: int = 3,
    neg_per_quad_per_draw: int = 24_000,
    seed_base: int = 7900,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Build flank-decontaminated simulated component-hide shards inside ``visible_mask``.

    Preserves exact Horvitz-Thompson importance weights across ``pos + halo + far`` (fixing the
    omitted halo regression pool), while strictly excluding ``d(x, sim_vis) <= 3.0 px`` unhidden
    real fault flanks from BOTH ``halo_pool`` and ``far_pool`` so real Quaternary fault scarps
    are never labelled ``y = 0`` or ``q = 0``!
    """
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    comp, n_comp = ndi.label(vis, STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)
    all_ids = np.arange(1, n_comp + 1, dtype=np.int32)
    target_px = hide_frac * float(vis.sum())

    buckets: dict[int, dict[str, Any]] = {
        q: {"X": [], "y": [], "q": [], "w": [], "pos": 0, "act": 0} for q in range(4)
    }
    draw0_info: dict[str, Any] = {}

    for d_idx in range(n_draws):
        rng = np.random.default_rng(seed_base + 137 * d_idx)
        perm = rng.permutation(all_ids)
        cum = np.cumsum(sizes[perm])
        k = int(np.searchsorted(cum, target_px)) + 1
        chosen = perm[: min(k, perm.size)]
        sim_hidden = np.isin(comp, chosen) & vis

        d_held = ndi.distance_transform_edt(~sim_hidden)
        collar = d_held <= float(buffer_px)
        sim_vis = vis & (~collar)
        sim_known = vis & (~sim_hidden)
        sim_active = footprint & (~sim_known)

        d_sim_vis = ndi.distance_transform_edt(~sim_vis)[footprint].astype(np.float32)
        clean_unhidden_fp = d_sim_vis > 3.0

        q_fp = metric.kernel(d_held).astype(np.float32)[footprint]
        y_fp = sim_hidden[footprint]
        act_fp = sim_active[footprint]
        mech = compute_network_mechanics(sim_vis, footprint, cues_npz_path)

        if d_idx == 0:
            draw0_info = {
                "mech_fp16": np.clip(np.nan_to_num(mech, nan=0.0, posinf=3e4, neginf=-3e4), -3e4, 3e4).astype(np.float16),
                "y_exact_fp": y_fp.copy(),
                "q_300_fp": q_fp.copy(),
                "active_fp": act_fp.copy(),
                "clean_unhidden_fp": clean_unhidden_fp.copy(),
            }

        for q_id in range(4):
            elig = act_fp & (quad_fp == q_id)
            pos_idx = np.flatnonzero(elig & y_fp)
            # Strict 300-m unhidden-flank decontamination on BOTH halo and far background pools!
            halo_pool = np.flatnonzero(elig & (~y_fp) & (q_fp > 0.0) & clean_unhidden_fp)
            far_pool = np.flatnonzero(elig & (~y_fp) & (q_fp == 0.0) & clean_unhidden_fp)

            n_halo = min(halo_pool.size, neg_per_quad_per_draw // 4)
            n_far = min(far_pool.size, neg_per_quad_per_draw - n_halo)
            sh = rng.choice(halo_pool, size=n_halo, replace=False) if n_halo > 0 else np.empty(0, dtype=np.int64)
            sf = rng.choice(far_pool, size=n_far, replace=False) if n_far > 0 else np.empty(0, dtype=np.int64)

            idx = np.sort(np.concatenate([pos_idx, sh, sf]))
            xp = np.empty((idx.size, len(PFSD_ALL_FEATURE_NAMES)), dtype=np.float32)
            xp[:, : len(PFSD_STATIC_FEATURE_NAMES)] = np.nan_to_num(static_mm[idx], nan=0.0, posinf=1e7, neginf=-1e7)
            xp[:, len(PFSD_STATIC_FEATURE_NAMES) :] = np.nan_to_num(mech[idx], nan=0.0, posinf=1e7, neginf=-1e7)

            is_pos = y_fp[idx]
            is_halo = (~is_pos) & (q_fp[idx] > 0.0)
            wh = float(halo_pool.size / max(n_halo, 1)) if n_halo > 0 else 1.0
            wf = float(far_pool.size / max(n_far, 1)) if n_far > 0 else 1.0
            w = np.where(is_pos, 1.0, np.where(is_halo, wh, wf)).astype(np.float32)

            buckets[q_id]["X"].append(xp)
            buckets[q_id]["y"].append(is_pos.astype(np.int8))
            buckets[q_id]["q"].append(q_fp[idx].astype(np.float32))
            buckets[q_id]["w"].append(w)
            buckets[q_id]["pos"] += int(pos_idx.size)
            buckets[q_id]["act"] += int(elig.sum())

        drop_file_cache(mmap_path)
        del sim_hidden, d_held, collar, sim_vis, sim_known, sim_active, d_sim_vis, q_fp, y_fp, act_fp, mech
        gc.collect()

    shards: dict[int, dict[str, Any]] = {}
    for q_id in range(4):
        shards[q_id] = {
            "X": np.concatenate(buckets[q_id]["X"], axis=0),
            "y": np.concatenate(buckets[q_id]["y"], axis=0),
            "q": np.concatenate(buckets[q_id]["q"], axis=0),
            "w": np.concatenate(buckets[q_id]["w"], axis=0),
            "n_active": int(buckets[q_id]["act"]),
            "n_pos": int(buckets[q_id]["pos"]),
        }
    del buckets
    gc.collect()
    return shards, draw0_info


def _stack_shards(
    shards: dict[int, dict[str, Any]], q_ids: list[int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float]:
    X = np.concatenate([shards[q]["X"] for q in q_ids], axis=0)
    y = np.concatenate([shards[q]["y"].astype(np.int32) for q in q_ids], axis=0)
    q_arr = np.concatenate([shards[q]["q"] for q in q_ids], axis=0)
    w_arr = np.concatenate([shards[q]["w"] for q in q_ids], axis=0)
    tot_act = sum(shards[q]["n_active"] for q in q_ids)
    tot_pos = sum(shards[q]["n_pos"] for q in q_ids)
    true_pi = float(tot_pos / max(tot_act, 1))
    sample_pi = float(y.mean())
    return X, y, q_arr, w_arr, true_pi, sample_pi


def fit_stage1_mech_ensemble(
    X: np.ndarray,
    y: np.ndarray,
    q300: np.ndarray,
    sample_w: np.ndarray,
    seed: int = 79,
) -> dict[str, Any]:
    """Fit preregistered 3-family Stage-1 ensemble (LightGBM + ExtraTrees-LGBM + HistGBDT)."""
    yi = y.astype(np.int32)
    w_mod = np.clip(sample_w / (np.median(sample_w[sample_w > 1.0]) if np.any(sample_w > 1.0) else 1.0), 0.25, 10.0)

    # Exact trace classifiers exclude 1-2 px halo rows (q300 > 0 & yi == 0) so centerlines stay sharp!
    cls_keep = (yi == 1) | (q300 == 0.0)
    Xc = X[cls_keep]
    yc = yi[cls_keep]
    cls_sample_pi = float(yc.mean())

    m_lgb = lgb.LGBMClassifier(
        n_estimators=165,
        learning_rate=0.055,
        num_leaves=63,
        max_depth=8,
        min_child_samples=130,
        subsample=0.80,
        subsample_freq=1,
        colsample_bytree=0.68,
        reg_alpha=3.0,
        reg_lambda=15.0,
        n_jobs=2,
        random_state=seed + 11,
        verbose=-1,
    )
    m_lgb.fit(Xc, yc)

    m_et = lgb.LGBMClassifier(
        n_estimators=175,
        learning_rate=0.055,
        num_leaves=47,
        max_depth=7,
        min_child_samples=190,
        extra_trees=True,
        subsample=0.80,
        subsample_freq=1,
        colsample_bytree=0.62,
        reg_alpha=4.0,
        reg_lambda=20.0,
        n_jobs=2,
        random_state=seed + 23,
        verbose=-1,
    )
    m_et.fit(Xc, yc)

    m_hgb = HistGradientBoostingRegressor(
        loss="squared_error",
        max_iter=125,
        learning_rate=0.06,
        max_leaf_nodes=47,
        min_samples_leaf=140,
        l2_regularization=12.0,
        early_stopping=True,
        random_state=seed + 31,
    )
    m_hgb.fit(X, q300, sample_weight=w_mod)

    m_q_lgb = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=150,
        learning_rate=0.055,
        num_leaves=47,
        max_depth=7,
        min_child_samples=160,
        subsample=0.80,
        subsample_freq=1,
        colsample_bytree=0.68,
        reg_alpha=3.0,
        reg_lambda=18.0,
        n_jobs=2,
        random_state=seed + 53,
        verbose=-1,
    )
    m_q_lgb.fit(X, q300, sample_weight=w_mod)

    return {
        "lgb_deep": m_lgb,
        "lgb_et": m_et,
        "hgb_q": m_hgb,
        "q_lgb": m_q_lgb,
        "eff_sample_pi": cls_sample_pi,
    }


def predict_stage1_mech_rows(
    models: dict[str, Any],
    static_mm: np.memmap,
    mmap_path: Path,
    mech_fp16: np.ndarray,
    row_indices: np.ndarray,
    true_pi: float,
) -> tuple[np.ndarray, np.ndarray]:
    n = row_indices.size
    p_out = np.empty(n, dtype=np.float32)
    q_out = np.empty(n, dtype=np.float32)
    sample_pi = models["eff_sample_pi"]
    for s in range(0, n, PRED_CHUNK_ROWS):
        e = min(s + PRED_CHUNK_ROWS, n)
        sl = row_indices[s:e]
        X_s = np.nan_to_num(np.asarray(static_mm[sl], dtype=np.float32), nan=0.0, posinf=1e7, neginf=-1e7)
        drop_file_cache(mmap_path)
        X_c = np.hstack([X_s, mech_fp16[sl].astype(np.float32)])
        del X_s
        p1 = _prior_correct(models["lgb_deep"].booster_.predict(X_c, num_threads=2), true_pi, sample_pi)
        p2 = _prior_correct(models["lgb_et"].booster_.predict(X_c, num_threads=2), true_pi, sample_pi)
        p_out[s:e] = 0.56 * p1 + 0.44 * p2
        q1 = np.clip(models["q_lgb"].booster_.predict(X_c, num_threads=2), 0.0, 1.0)
        q2 = np.clip(models["hgb_q"].predict(X_c), 0.0, 1.0)
        q_out[s:e] = (0.65 * q1 + 0.35 * q2).astype(np.float32)
        del X_c
    return p_out, q_out


def extract_stage2_dual_expert_features(
    p1_mech_fp: np.ndarray,
    q1_mech_fp: np.ndarray,
    p_phys_fp: np.ndarray,
    q_phys_fp: np.ndarray,
    footprint: np.ndarray,
    ctx_cols_fp: np.ndarray,
) -> np.ndarray:
    """Build 23-channel bilinear 8-azimuth Sato trace + Dual-Expert corroboration matrix (float16)."""
    H, W = footprint.shape
    n_fp = int(footprint.sum())
    p2d = np.zeros((H, W), dtype=np.float32)
    q2d = np.zeros((H, W), dtype=np.float32)
    qp2d = np.zeros((H, W), dtype=np.float32)
    p2d[footprint] = p1_mech_fp
    q2d[footprint] = q1_mech_fp
    qp2d[footprint] = q_phys_fp

    g08 = ndi.gaussian_filter(p2d, 0.8, mode="constant", cval=0.0)
    g15 = ndi.gaussian_filter(p2d, 1.5, mode="constant", cval=0.0)
    g4 = ndi.gaussian_filter(p2d, 4.0, mode="constant", cval=0.0)
    g10 = ndi.gaussian_filter(p2d, 10.0, mode="constant", cval=0.0)
    qg1 = ndi.gaussian_filter(q2d, 1.0, mode="constant", cval=0.0)
    qpg3 = ndi.gaussian_filter(qp2d, 3.0, mode="constant", cval=0.0)

    max7 = np.zeros((H, W), dtype=np.float32)
    max17 = np.zeros((H, W), dtype=np.float32)
    min17 = np.full((H, W), 1e9, dtype=np.float32)
    q_line17 = np.zeros((H, W), dtype=np.float32)

    for az in (0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5):
        l7 = _sparse_line_integral(g08, half_span=3, step=1, angle_deg=az)
        l17 = _sparse_line_integral(g15, half_span=8, step=2, angle_deg=az)
        ql17 = _sparse_line_integral(qg1, half_span=8, step=2, angle_deg=az)
        max7 = np.maximum(max7, l7)
        max17 = np.maximum(max17, l17)
        min17 = np.minimum(min17, l17)
        q_line17 = np.maximum(q_line17, ql17)

    hyy = ndi.gaussian_filter(g15, 1.0, order=(2, 0), mode="nearest")
    hxx = ndi.gaussian_filter(g15, 1.0, order=(0, 2), mode="nearest")
    hxy = ndi.gaussian_filter(g15, 1.0, order=(1, 1), mode="nearest")
    tr = hxx + hyy
    disc = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy * hxy, 0.0))
    sato = np.maximum(-0.5 * (tr - disc), 0.0)

    S2 = np.empty((n_fp, 23), dtype=np.float16)
    p_clip = np.clip(p1_mech_fp, 1e-6, 1.0 - 1e-6)
    pp_clip = np.clip(p_phys_fp, 1e-6, 1.0 - 1e-6)

    S2[:, 0] = p1_mech_fp.astype(np.float16)
    S2[:, 1] = np.clip(np.log(p_clip / (1.0 - p_clip)), -20.0, 20.0).astype(np.float16)
    S2[:, 2] = q1_mech_fp.astype(np.float16)
    S2[:, 3] = g15[footprint].astype(np.float16)
    S2[:, 4] = g4[footprint].astype(np.float16)
    S2[:, 5] = g10[footprint].astype(np.float16)
    S2[:, 6] = max7[footprint].astype(np.float16)
    S2[:, 7] = max17[footprint].astype(np.float16)
    S2[:, 8] = np.clip(max17[footprint] / (min17[footprint] + 1e-4), 0.0, 500.0).astype(np.float16)
    S2[:, 9] = (max7[footprint] - g4[footprint]).astype(np.float16)
    S2[:, 10] = sato[footprint].astype(np.float16)
    S2[:, 11] = ndi.gaussian_filter(q2d, 3.0, mode="constant", cval=0.0)[footprint].astype(np.float16)
    S2[:, 12] = q_line17[footprint].astype(np.float16)
    # 6 Dual-Expert Pure-Physics corroboration channels
    S2[:, 13] = p_phys_fp.astype(np.float16)
    S2[:, 14] = np.clip(np.log(pp_clip / (1.0 - pp_clip)), -20.0, 20.0).astype(np.float16)
    S2[:, 15] = q_phys_fp.astype(np.float16)
    S2[:, 16] = qpg3[footprint].astype(np.float16)
    S2[:, 17] = np.sqrt(np.maximum(p1_mech_fp * p_phys_fp, 0.0)).astype(np.float16)
    S2[:, 18] = np.sqrt(np.maximum(q1_mech_fp * q_phys_fp, 0.0)).astype(np.float16)
    # 4 physical context gates
    S2[:, 19:23] = np.clip(np.nan_to_num(ctx_cols_fp, nan=0.0, posinf=3e4, neginf=-3e4), -3e4, 3e4).astype(np.float16)
    S2 = np.nan_to_num(S2, nan=0.0, posinf=3e4, neginf=-3e4)
    del p2d, q2d, qp2d, g08, g15, g4, g10, qg1, qpg3, max7, max17, min17, q_line17, hyy, hxx, hxy, tr, disc, sato
    gc.collect()
    return S2


def fit_stage2_dual_expert_heads(
    S2_fp16: np.ndarray,
    draw0_info: dict[str, Any],
    allowed_fp_mask: np.ndarray,
    seed: int = 79,
) -> dict[str, Any]:
    """Fit flank-decontaminated Stage-2 Dual-Expert spatial meta-learners with exact
    Horvitz-Thompson importance weights and 250k-pixel uniform inner mean conservation."""
    rng = np.random.default_rng(seed + 900)
    elig = draw0_info["active_fp"] & allowed_fp_mask
    y = draw0_info["y_exact_fp"]
    q = draw0_info["q_300_fp"].astype(np.float32)
    clean_unhidden_fp = draw0_info["clean_unhidden_fp"]

    pos_idx = np.flatnonzero(elig & y)
    # Strict unhidden-flank decontamination (d_sim_vis > 3.0 px) on BOTH halo and far pools!
    halo_pool = np.flatnonzero(elig & (~y) & (q > 0.0) & clean_unhidden_fp)
    far_pool = np.flatnonzero(elig & (~y) & (q == 0.0) & clean_unhidden_fp)
    nh = min(halo_pool.size, 30_000)
    nf = min(far_pool.size, 130_000)
    sh = rng.choice(halo_pool, size=nh, replace=False) if nh > 0 else np.empty(0, dtype=np.int64)
    sf = rng.choice(far_pool, size=nf, replace=False) if nf > 0 else np.empty(0, dtype=np.int64)

    # Exact trace classifiers exclude 1-2 px halo rows so centerlines stay razor-sharp
    idx_cls = np.sort(np.concatenate([pos_idx, sf]))
    X_cls = S2_fp16[idx_cls].astype(np.float32)
    y_cls = y[idx_cls].astype(np.int32)
    sample_pi_cls = float(y_cls.mean())
    true_pi = float(pos_idx.size / max(int(elig.sum()), 1))

    # 300-m kernel regressors use exact Horvitz-Thompson weights over pos + halo + clean_far
    idx_reg = np.sort(np.concatenate([pos_idx, sh, sf]))
    X_reg = S2_fp16[idx_reg].astype(np.float32)
    q_reg = q[idx_reg]
    is_pos_r = y[idx_reg]
    is_halo_r = (~is_pos_r) & (q_reg > 0.0)
    wh = float(halo_pool.size / max(nh, 1)) if nh > 0 else 1.0
    wf = float(far_pool.size / max(nf, 1)) if nf > 0 else 1.0
    w_reg = np.where(is_pos_r, 1.0, np.where(is_halo_r, wh, wf)).astype(np.float32)

    scaler = StandardScaler()
    X_cls_sc = np.clip(scaler.fit_transform(X_cls), -8.0, 8.0)
    X_reg_sc = np.clip(scaler.transform(X_reg), -8.0, 8.0)

    mlp_p = MLPClassifier(
        hidden_layer_sizes=(32, 16),
        alpha=2.5,
        batch_size=2048,
        max_iter=20,
        early_stopping=True,
        tol=1e-3,
        random_state=seed + 1,
    )
    mlp_p.fit(X_cls_sc, y_cls)

    lgb_p = lgb.LGBMClassifier(
        n_estimators=135,
        learning_rate=0.05,
        num_leaves=23,
        max_depth=5,
        min_child_samples=260,
        colsample_bytree=0.80,
        subsample=0.80,
        subsample_freq=1,
        reg_alpha=5.0,
        reg_lambda=25.0,
        n_jobs=2,
        random_state=seed + 3,
        verbose=-1,
    )
    lgb_p.fit(X_cls, y_cls)

    lgb_q = lgb.LGBMRegressor(
        n_estimators=140,
        learning_rate=0.05,
        num_leaves=27,
        max_depth=5,
        min_child_samples=240,
        colsample_bytree=0.80,
        subsample=0.80,
        subsample_freq=1,
        reg_alpha=5.0,
        reg_lambda=25.0,
        n_jobs=2,
        random_state=seed + 7,
        verbose=-1,
    )
    lgb_q.fit(X_reg, q_reg, sample_weight=w_reg)

    ridge_q = Ridge(alpha=300.0)
    ridge_q.fit(X_reg_sc, q_reg, sample_weight=w_reg)

    # Smooth strictly-monotone mean conservation on 250k uniform clean inner pixels
    elig_clean = elig & (y | clean_unhidden_fp)
    elig_all = np.flatnonzero(elig_clean)
    cal_idx = np.sort(rng.choice(elig_all, size=min(250_000, elig_all.size), replace=False))
    cal_X = S2_fp16[cal_idx].astype(np.float32)
    cal_sc = np.clip(scaler.transform(cal_X), -8.0, 8.0)

    rp = 0.65 * _prior_correct(lgb_p.booster_.predict(cal_X, num_threads=2), true_pi, sample_pi_cls) + 0.35 * _prior_correct(
        mlp_p.predict_proba(cal_sc)[:, 1], true_pi, sample_pi_cls
    )
    rq = np.clip(0.80 * lgb_q.booster_.predict(cal_X, num_threads=2) + 0.20 * ridge_q.predict(cal_sc), 0.0, 1.0)

    scale_p = float(np.clip(y[cal_idx].mean() / max(float(rp.mean()), 1e-8), 0.35, 3.0))
    scale_q = float(np.clip(q[cal_idx].mean() / max(float(rq.mean()), 1e-8), 0.35, 3.0))

    return {
        "scaler": scaler,
        "mlp_p": mlp_p,
        "lgb_p": lgb_p,
        "lgb_q": lgb_q,
        "ridge_q": ridge_q,
        "sample_pi_cls": sample_pi_cls,
        "true_pi": true_pi,
        "scale_p": scale_p,
        "scale_q": scale_q,
    }


def predict_stage2_dual_expert_heads(
    s2_model: dict[str, Any],
    S2_fp16: np.ndarray,
    row_indices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n = row_indices.size
    p_out = np.empty(n, dtype=np.float32)
    q_out = np.empty(n, dtype=np.float32)
    scaler = s2_model["scaler"]
    tpi = s2_model["true_pi"]
    spi = s2_model["sample_pi_cls"]
    sp = s2_model["scale_p"]
    sq = s2_model["scale_q"]

    for s in range(0, n, PRED_CHUNK_ROWS):
        e = min(s + PRED_CHUNK_ROWS, n)
        sl = row_indices[s:e]
        X_c = S2_fp16[sl].astype(np.float32)
        X_sc = np.clip(scaler.transform(X_c), -8.0, 8.0)
        pl = _prior_correct(s2_model["lgb_p"].booster_.predict(X_c, num_threads=2), tpi, spi)
        pm = _prior_correct(s2_model["mlp_p"].predict_proba(X_sc)[:, 1], tpi, spi)
        p_out[s:e] = np.clip((0.65 * pl + 0.35 * pm) * sp, 0.0, 1.0).astype(np.float32)

        ql = s2_model["lgb_q"].booster_.predict(X_c, num_threads=2)
        qr = s2_model["ridge_q"].predict(X_sc)
        q_out[s:e] = np.clip(np.clip(0.80 * ql + 0.20 * qr, 0.0, 1.0) * sq, 0.0, 1.0).astype(np.float32)
        del X_c, X_sc
    return p_out, q_out


def run_dual_expert_nested_oof(
    quad_fp: np.ndarray,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    shards: dict[int, dict[str, Any]],
    draw0_info: dict[str, Any],
    test_mech_fp16: np.ndarray,
    p_phys_oof: np.ndarray,
    q_phys_oof: np.ndarray,
    seed: int = 79,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact C(4,2)=6 pairwise nested OOF Stage-1 + flank-decontaminated Dual-Expert Stage-2."""
    n_fp = int(footprint.sum())
    pair_models: dict[tuple[int, int], tuple[dict[str, Any], float]] = {}

    for qa, qb in combinations(range(4), 2):
        t0 = time.time()
        X_p, y_p, q_p, w_p, t_pi, _ = _stack_shards(shards, [qa, qb])
        pm = fit_stage1_mech_ensemble(X_p, y_p, q_p, w_p, seed=seed + 13 * qa + 29 * qb)
        pair_models[(qa, qb)] = (pm, t_pi)
        del X_p, y_p, q_p, w_p
        gc.collect()
        print(f"    [C(4,2) pair ({qa},{qb})] fitted in {time.time()-t0:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

    p_test_oof = np.zeros(n_fp, dtype=np.float32)
    q_test_oof = np.zeros(n_fp, dtype=np.float32)
    p_inner_tr_accum = np.zeros(n_fp, dtype=np.float32)
    q_inner_tr_accum = np.zeros(n_fp, dtype=np.float32)
    inner_cnt = np.zeros(n_fp, dtype=np.float32)

    for k_test in range(4):
        tr_quads = [q for q in range(4) if q != k_test]
        p1_tr_oof = np.zeros(n_fp, dtype=np.float32)
        q1_tr_oof = np.zeros(n_fp, dtype=np.float32)
        for j_val in tr_quads:
            rem = tuple(sorted(q for q in tr_quads if q != j_val))
            pm, t_pi = pair_models[rem]
            rows_j = np.flatnonzero(quad_fp == j_val)
            p1_tr_oof[rows_j], q1_tr_oof[rows_j] = predict_stage1_mech_rows(
                pm, static_mm, mmap_path, draw0_info["mech_fp16"], rows_j, t_pi
            )

        X_3, y_3, q_3, w_3, t_pi3, _ = _stack_shards(shards, tr_quads)
        full3_m = fit_stage1_mech_ensemble(X_3, y_3, q_3, w_3, seed=seed + 101 * k_test)
        del X_3, y_3, q_3, w_3
        gc.collect()

        rows_k = np.flatnonzero(quad_fp == k_test)
        p1_tr_oof[rows_k], q1_tr_oof[rows_k] = predict_stage1_mech_rows(
            full3_m, static_mm, mmap_path, test_mech_fp16, rows_k, t_pi3
        )
        del full3_m
        gc.collect()

        S2_fold = extract_stage2_dual_expert_features(
            p1_tr_oof, q1_tr_oof, p_phys_oof, q_phys_oof, footprint, ctx_cols_fp
        )
        del p1_tr_oof, q1_tr_oof
        allow_tr = quad_fp != k_test
        s2_m = fit_stage2_dual_expert_heads(S2_fold, draw0_info, allow_tr, seed=seed + 211 * k_test)

        p_test_oof[rows_k], q_test_oof[rows_k] = predict_stage2_dual_expert_heads(s2_m, S2_fold, rows_k)
        tr_rows = np.flatnonzero(allow_tr)
        pt_tr, qt_tr = predict_stage2_dual_expert_heads(s2_m, S2_fold, tr_rows)
        p_inner_tr_accum[tr_rows] += pt_tr
        q_inner_tr_accum[tr_rows] += qt_tr
        inner_cnt[tr_rows] += 1.0
        del S2_fold, s2_m, pt_tr, qt_tr
        gc.collect()
        print(f"    [outer fold {k_test}] Dual-Expert Stage-2 OOF complete, RSS={rss_mb():.1f} MB", flush=True)

    del pair_models
    gc.collect()
    p_inner_avg = np.divide(p_inner_tr_accum, np.maximum(inner_cnt, 1.0))
    q_inner_avg = np.divide(q_inner_tr_accum, np.maximum(inner_cnt, 1.0))
    return p_test_oof, q_test_oof, p_inner_avg, q_inner_avg


def equilibrate_quadrant_posteriors(
    p_map: np.ndarray,
    q_map: np.ndarray,
    quad_2d: np.ndarray,
    allowed_mask: np.ndarray,
    gamma: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Gentle tail-scale equilibration across spatial quadrants (fixes Fold-3 OOF starvation)."""
    if gamma <= 1e-6:
        return p_map.astype(np.float32, copy=True), q_map.astype(np.float32, copy=True)

    scales_q = np.ones(4, dtype=np.float64)
    scales_p = np.ones(4, dtype=np.float64)
    for q_id in range(4):
        m = allowed_mask & (quad_2d == q_id)
        if np.any(m):
            scales_q[q_id] = max(float(np.percentile(q_map[m], 99.2)), 1e-5)
            scales_p[q_id] = max(float(np.percentile(p_map[m], 99.2)), 1e-5)
    gmean_q = float(np.exp(np.mean(np.log(scales_q))))
    gmean_p = float(np.exp(np.mean(np.log(scales_p))))

    p_eq = p_map.astype(np.float32, copy=True)
    q_eq = q_map.astype(np.float32, copy=True)
    for q_id in range(4):
        m = allowed_mask & (quad_2d == q_id)
        if np.any(m):
            mult_q = float((gmean_q / scales_q[q_id]) ** gamma)
            mult_p = float((gmean_p / scales_p[q_id]) ** gamma)
            q_eq[m] = np.clip(q_eq[m] * mult_q, 0.0, 1.0)
            p_eq[m] = np.clip(p_eq[m] * mult_p, 0.0, 1.0)
    return p_eq, q_eq


__all__ = [
    "PRED_CHUNK_ROWS",
    "_stack_shards",
    "build_decontaminated_quadrant_shards",
    "charnes_cooper_submodular_emit",
    "equilibrate_quadrant_posteriors",
    "extract_stage2_dual_expert_features",
    "fit_pure_physics_ensemble",
    "fit_stage1_mech_ensemble",
    "fit_stage2_dual_expert_heads",
    "poisson_disk_emit",
    "predict_pure_physics_rows",
    "predict_stage1_mech_rows",
    "predict_stage2_dual_expert_heads",
    "run_dual_expert_nested_oof",
    "run_pure_physics_oof",
]
