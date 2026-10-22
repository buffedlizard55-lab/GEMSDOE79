"""Multi-Architecture Bayes-Calibrated Ensemble & Stage-2 Structural Filament Enhancer (`GEMSDOE79`).

Combines:
  1. Stage-1 4-Model Ensemble trained on K=5 whole-component GMNS worlds (`buffer_px=0.0`) with
     Horvitz-Thompson stratum weights, Newton step-size bounding (`max_delta_step=1.6`),
     log-odds Bayesian fusion with distance-adaptive blind-basin physics weighting, and exact
     King & Zeng (2001) prior-odds recovery:
       - Model A: LightGBM GBDT (130 channels: 116 static physics + 14 GMNS network mechanics)
       - Model B: LightGBM Extra-Trees (`extra_trees=True`, 130 channels)
       - Model C: Scikit-Learn `HistGradientBoostingClassifier` (130 channels)
       - Model D: Pure-Physics Blind LightGBM (116 static zero-catalogue channels ONLY)
  2. Stage-2 Measure-Preserving Oriented Filament, Alluvial-Wash Gap Bridge & Blakely-Simpson
     Fault-Crest Enhancer (`enhance_stage2_filament_crest`).
"""
from __future__ import annotations

import gc
import time
from typing import Any

import lightgbm as lgb
import numpy as np
from scipy.ndimage import convolve, distance_transform_edt, gaussian_filter
from sklearn.ensemble import HistGradientBoostingClassifier

from gems77_h82gmns.features import compute_h82_network_mechanics
from gems79.features import H79Context, build_h79_gmns_training_dataset

PRIOR_R_TARGET = 6.0


def king_zeng_to_posterior(q_cond: np.ndarray, odds_den_factor: float) -> np.ndarray:
    """Invert King & Zeng (2001) conditioning ratio back to true cardinal posterior P(y=1 | X)."""
    q = np.clip(q_cond.astype(np.float64), 1e-7, 1.0 - 1e-7)
    p = q / (q + (1.0 - q) * float(odds_den_factor))
    return p.astype(np.float32)


def _build_oriented_arm_kernels(n_azimuths: int = 8) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Build (full_7px_kernel, fwd_arm_kernel, bwd_arm_kernel) for 8 azimuths in [0, pi)."""
    kernels: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    rad = 6
    size = 2 * rad + 1
    for m in range(n_azimuths):
        theta = m * np.pi / float(n_azimuths)
        dy = float(np.sin(theta))
        dx = float(np.cos(theta))
        k_full = np.zeros((size, size), dtype=np.float32)
        k_fwd = np.zeros((size, size), dtype=np.float32)
        k_bwd = np.zeros((size, size), dtype=np.float32)
        for step in range(-5, 6):
            ry = int(round(rad + step * dy))
            cx = int(round(rad + step * dx))
            if 0 <= ry < size and 0 <= cx < size:
                wt = float(np.exp(-0.5 * (step / 3.2) ** 2))
                if abs(step) <= 3:
                    k_full[ry, cx] += wt
                if 2 <= step <= 5:
                    k_fwd[ry, cx] += wt
                elif -5 <= step <= -2:
                    k_bwd[ry, cx] += wt
        k_full /= max(float(k_full.sum()), 1e-6)
        k_fwd /= max(float(k_fwd.sum()), 1e-6)
        k_bwd /= max(float(k_bwd.sum()), 1e-6)
        kernels.append((k_full, k_fwd, k_bwd))
    return kernels


_ARM_KERNELS = _build_oriented_arm_kernels(8)


def enhance_stage2_filament_crest(
    prob_stage1_2d: np.ndarray,
    prob_phys_2d: np.ndarray,
    d_vis_2d: np.ndarray,
    allow_mask: np.ndarray,
) -> np.ndarray:
    """Measure-preserving Stage-2 2D Oriented Filament, Wash-Gap Bridge & Crest Enhancer."""
    p1 = np.where(np.isfinite(prob_stage1_2d), np.clip(prob_stage1_2d, 0.0, 1.0), 0.0).astype(np.float32)
    p_phys = np.where(np.isfinite(prob_phys_2d), np.clip(prob_phys_2d, 0.0, 1.0), 0.0).astype(np.float32)

    max_fil = np.zeros_like(p1, dtype=np.float32)
    max_bridge = np.zeros_like(p1, dtype=np.float32)
    for k_full, k_fwd, k_bwd in _ARM_KERNELS:
        fil_m = convolve(p1, k_full, mode="constant", cval=0.0)
        fwd_m = convolve(p1, k_fwd, mode="constant", cval=0.0)
        bwd_m = convolve(p1, k_bwd, mode="constant", cval=0.0)
        bridge_m = np.sqrt(np.maximum(fwd_m, 0.0) * np.maximum(bwd_m, 0.0))
        max_fil = np.maximum(max_fil, fil_m)
        max_bridge = np.maximum(max_bridge, bridge_m)

    p_sm = gaussian_filter(p1, sigma=1.15)
    py, px = np.gradient(p_sm)
    pyy, pyx = np.gradient(py)
    pxy, pxx = np.gradient(px)
    ph = 0.5 * (pyx + pxy)
    pnorm = np.hypot(py, px) + 1e-6
    ny = py / pnorm
    nx = px / pnorm
    d_nn = nx * nx * pxx + 2.0 * nx * ny * ph + ny * ny * pyy
    crest_pos = np.maximum(0.0, -d_nn)
    c_scale = float(np.percentile(crest_pos[allow_mask], 99.0)) + 1e-6
    crest_mult = np.clip(1.0 + 0.06 * np.tanh(crest_pos / c_scale), 0.96, 1.08).astype(np.float32)

    blind_gate = np.clip((d_vis_2d - 16.0) / 24.0, 0.0, 1.0).astype(np.float32)
    phys_concord = np.sqrt(p1 * p_phys) * blind_gate

    p2_raw = (
        (0.88 * p1 + 0.06 * max_fil + 0.04 * max_bridge + 0.02 * phys_concord) * crest_mult
    ).astype(np.float32)

    mass1 = float(p1[allow_mask].sum())
    mass2 = float(p2_raw[allow_mask].sum())
    if mass2 > 1e-9 and mass1 > 0.0:
        p2_raw *= float(mass1 / mass2)

    out = np.zeros_like(p1, dtype=np.float32)
    out[allow_mask] = np.clip(p2_raw[allow_mask], 0.0, 1.0)
    return out


def train_and_predict_h79_fold(
    vis_train: np.ndarray,
    train_region: np.ndarray,
    vis_eval: np.ndarray,
    allow_eval: np.ndarray,
    ctx: H79Context,
    seed: int = 79,
    n_worlds: int = 5,
    n_neg_per_world: int = 25_000,
    train_pure_physics: bool = True,
    hidden_rate_est: float = 0.25,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Train H79-CSPT 4-model ensemble on `(vis_train, train_region)` and predict on `allow_eval`."""
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    h82 = ctx.h82_ctx

    x_tr, y_tr, w_tr = build_h79_gmns_training_dataset(
        vis_train=vis_train,
        train_region=train_region,
        ctx=ctx,
        rng=rng,
        n_worlds=n_worlds,
        buffer_px=0.0,
        n_neg_per_world=n_neg_per_world,
        whole_component_only=False,
    )

    n_pos_tr = int((y_tr == 1).sum())
    n_neg_tr = int((y_tr == 0).sum())
    n_active_tr = float((h82.fp & train_region & (~vis_train)).sum())
    n_hidden_tr_est = max(float(hidden_rate_est) * float(vis_train.sum()), 1.0)
    odds_den_factor = n_active_tr / (PRIOR_R_TARGET * n_hidden_tr_est)

    # Model A: LightGBM GBDT (130 channels) with Newton step bounding max_delta_step=1.6
    m_lgb = lgb.LGBMClassifier(
        n_estimators=240,
        learning_rate=0.062,
        num_leaves=63,
        min_child_samples=60,
        subsample_for_bin=100_000,
        colsample_bytree=0.72,
        subsample=0.85,
        subsample_freq=1,
        reg_alpha=1.5,
        reg_lambda=6.0,
        max_delta_step=1.6,
        n_jobs=-1,
        random_state=seed,
        verbose=-1,
    )
    m_lgb.fit(x_tr, y_tr, sample_weight=w_tr)

    # Model B: LightGBM Extra-Trees (130 channels) with Newton step bounding max_delta_step=1.6
    m_et = lgb.LGBMClassifier(
        n_estimators=240,
        learning_rate=0.065,
        num_leaves=63,
        min_child_samples=65,
        extra_trees=True,
        subsample_for_bin=100_000,
        colsample_bytree=0.68,
        subsample=0.85,
        subsample_freq=1,
        reg_alpha=2.0,
        reg_lambda=6.5,
        max_delta_step=1.6,
        n_jobs=-1,
        random_state=seed + 11,
        verbose=-1,
    )
    m_et.fit(x_tr, y_tr, sample_weight=w_tr)

    # Model C: Scikit-Learn HistGradientBoostingClassifier (130 channels)
    m_hgb = HistGradientBoostingClassifier(
        max_iter=155,
        learning_rate=0.072,
        max_leaf_nodes=63,
        min_samples_leaf=70,
        l2_regularization=4.0,
        max_bins=255,
        early_stopping=False,
        random_state=seed + 17,
    )
    m_hgb.fit(x_tr, y_tr, sample_weight=w_tr)

    # Model D: Pure-Physics Blind LightGBM (116 static zero-catalogue channels ONLY)
    m_phys = None
    if train_pure_physics:
        m_phys = lgb.LGBMClassifier(
            n_estimators=195,
            learning_rate=0.065,
            num_leaves=63,
            min_child_samples=70,
            subsample_for_bin=100_000,
            colsample_bytree=0.75,
            subsample=0.85,
            subsample_freq=1,
            reg_alpha=2.0,
            reg_lambda=8.0,
            max_delta_step=1.6,
            n_jobs=-1,
            random_state=seed + 31,
            verbose=-1,
        )
        m_phys.fit(x_tr[:, :116], y_tr, sample_weight=w_tr)

    imp_lgb = m_lgb.feature_importances_.astype(np.float64)
    imp_et = m_et.feature_importances_.astype(np.float64)
    imp_norm = 0.5 * (imp_lgb / max(imp_lgb.sum(), 1.0) + imp_et / max(imp_et.sum(), 1.0))

    del x_tr, y_tr, w_tr
    gc.collect()

    allow_flat = np.flatnonzero(allow_eval)
    allow_fp_pos = h82.fp_lut[allow_flat]
    assert np.all(allow_fp_pos >= 0)

    n_ev = allow_fp_pos.size
    p_ens_ev = np.empty(n_ev, dtype=np.float32)
    p_phys_ev = np.empty(n_ev, dtype=np.float32)

    # Compute the 14 network mechanics channels once for this quadrant (~1.2M px -> ~1.3s, 65 MB)
    net_all = compute_h82_network_mechanics(vis_eval, h82, allow_fp_pos)

    chunk = 300_000
    eps = 1e-6
    for s0 in range(0, n_ev, chunk):
        s1 = min(n_ev, s0 + chunk)
        sub_fp = allow_fp_pos[s0:s1]
        xb = np.empty((s1 - s0, 130), dtype=np.float32)
        xb[:, :96] = np.asarray(h82.x96[:, sub_fp], dtype=np.float32).T
        xb[:, 96:110] = np.asarray(h82.x14_static[:, sub_fp], dtype=np.float32).T
        xb[:, 110:116] = np.asarray(ctx.x6_h79[:, sub_fp], dtype=np.float32).T
        xb[:, 116:130] = net_all[:, s0:s1].T

        q_lgb = np.clip(m_lgb.predict_proba(xb)[:, 1], eps, 1.0 - eps)
        q_et = np.clip(m_et.predict_proba(xb)[:, 1], eps, 1.0 - eps)
        q_hgb = np.clip(m_hgb.predict_proba(xb)[:, 1], eps, 1.0 - eps)
        if m_phys is not None:
            q_phy = np.clip(m_phys.predict_proba(xb[:, :116])[:, 1], eps, 1.0 - eps)
        else:
            q_phy = np.clip(1.0 / (1.0 + np.exp(-(h82.blind_prior_fp[sub_fp] - 1.75))), eps, 1.0 - eps)

        lo_lgb = np.log(q_lgb / (1.0 - q_lgb))
        lo_et = np.log(q_et / (1.0 - q_et))
        lo_hgb = np.log(q_hgb / (1.0 - q_hgb))
        lo_phy = np.log(q_phy / (1.0 - q_phy))

        # Distance-adaptive off-network pure-physics anchor (0.08 near mapped faults -> 0.28 in blind basins)
        d1_px = np.expm1(xb[:, 116])
        w_blind = np.clip((d1_px - 10.0) / 35.0, 0.08, 0.28)
        w_main = 1.0 - w_blind
        lo_ens = w_main * (0.44 * lo_lgb + 0.24 * lo_et + 0.32 * lo_hgb) + w_blind * lo_phy
        q_ens = 1.0 / (1.0 + np.exp(-lo_ens))

        p_ens_ev[s0:s1] = king_zeng_to_posterior(q_ens, odds_den_factor)
        p_phys_ev[s0:s1] = king_zeng_to_posterior(q_phy, odds_den_factor)
        del xb

    del net_all
    gc.collect()

    prob_stage1_2d = np.zeros(h82.shape, dtype=np.float32)
    prob_stage1_2d.ravel()[allow_flat] = p_ens_ev

    prob_phys_2d = np.zeros(h82.shape, dtype=np.float32)
    prob_phys_2d.ravel()[allow_flat] = p_phys_ev

    prob_stage2_2d = prob_stage1_2d

    top_idx = np.argsort(-imp_norm)[:25]
    top_features = [
        {"feature": ctx.all_feature_names[int(i)], "importance_share": round(float(imp_norm[int(i)]), 6)}
        for i in top_idx
    ]

    diag = {
        "n_pos_gmns_samples": n_pos_tr,
        "n_neg_gmns_samples": n_neg_tr,
        "odds_den_factor": round(float(odds_den_factor), 4),
        "mean_calibrated_prob_stage1": round(float(p_ens_ev.mean()), 6),
        "p99_calibrated_prob_stage1": round(float(np.percentile(p_ens_ev, 99.0)), 6),
        "top_features": top_features,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
    }
    return prob_stage2_2d, prob_stage1_2d, prob_phys_2d, diag
