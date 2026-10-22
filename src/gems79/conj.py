"""G79-CONJ fold-safe cross-strike conjugate-strand channels + adaptive emission.

Preregistration: registry/preregistration_g79_conj.json (2026-10-22, before any result).

Every channel here is computed ONLY from a supplied visible catalogue mask and
the static ``depth_to_base_surf`` field (throw sense). No prior prediction
raster and no withheld truth enters. Strike geometry reuses the shared
``gems57.network`` frame (nearest_frame / local_strike / offset_components /
segments / junctions); nothing in vendor/ is modified.
"""
from __future__ import annotations

import heapq
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor"))
from gems57 import metric, network  # noqa: E402

CONJ_FEATURE_NAMES = [
    "conj_hw_near",
    "conj_hw_mid",
    "conj_hw_far",
    "conj_fw_near",
    "conj_fw_mid",
    "conj_fw_far",
    "conj_len_scaled",
    "conj_dperp_over_len",
    "conj_junc_10",
    "conj_junc_30",
    "conj_bend",
    "conj_parallel_support",
]

_OFFSETS = [(5.0, 2.5), (11.0, 4.0), (22.0, 7.0)]  # (spacing px, sigma px)


def _p999_normalize(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    vals = a[mask]
    if vals.size == 0:
        return a
    scale = float(np.percentile(vals, 99.9))
    if scale <= 0:
        return a
    return np.clip(a / scale, 0.0, 1.0).astype(np.float32)


def compute_conj_channels(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    depth_to_base_2d: np.ndarray,
) -> np.ndarray:
    """Return (n_footprint, 12) float32 CONJ channels from the visible mask only."""
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    n_fp = int(footprint.sum())
    out = np.zeros((n_fp, len(CONJ_FEATURE_NAMES)), dtype=np.float32)
    if not np.any(vis):
        return out
    H, W = footprint.shape

    # Junction proximity (independent of the strike frame).
    junc = network.junctions(vis).astype(np.float32)
    out[:, 8] = _p999_normalize(ndi.gaussian_filter(junc, 10.0), footprint)[footprint]
    out[:, 9] = _p999_normalize(ndi.gaussian_filter(junc, 30.0), footprint)[footprint]
    del junc

    # Nearest-visible frame + anchor strike/coherence.
    dist, iy, ix = network.nearest_frame(vis)
    strike_map, coh_map = network.local_strike(vis, smooth_px=3.0)
    strike_a = strike_map[iy, ix]
    coh_a = coh_map[iy, ix].astype(np.float32)
    del strike_map, coh_map

    yy, xx = np.nonzero(footprint)
    ay = iy[yy, xx].astype(np.float64)
    ax = ix[yy, xx].astype(np.float64)
    dy = yy.astype(np.float64) - ay
    dx = xx.astype(np.float64) - ax
    strike_fp = strike_a[yy, xx].astype(np.float64)
    coh_fp = coh_a[yy, xx]
    dist_fp = dist[yy, xx].astype(np.float32)
    del dist, iy, ix, strike_a, coh_a

    valid = np.isfinite(strike_fp)
    d_par = np.zeros(n_fp, dtype=np.float64)
    d_perp = np.zeros(n_fp, dtype=np.float64)
    side = np.zeros(n_fp, dtype=np.float64)
    if np.any(valid):
        dp, dperp, sd = network.offset_components(
            dy[valid], dx[valid], strike_fp[valid]
        )
        d_par[valid], d_perp[valid], side[valid] = dp, dperp, sd
    del dy, dx

    # Anchor segment length (junction anchors -> default 12 px chunk length).
    seg, n_seg, _ = network.segments(vis, max_len_px=12)
    table = network.segment_table(seg, n_seg)
    seg_at_anchor = seg[np.rint(ay).astype(np.int64), np.rint(ax).astype(np.int64)]
    length_lut = table.length.copy()
    length_lut[0] = 12.0
    seg_len = length_lut[seg_at_anchor].astype(np.float64)
    del seg, table, seg_at_anchor, length_lut

    # Throw sense: basement depth sampled +/-5 px along the strike normal.
    depth = np.asarray(depth_to_base_2d, dtype=np.float64)
    depth = np.where(np.isfinite(depth) & (depth > -1e30), depth, np.nan)
    th = np.radians(np.where(valid, strike_fp, 0.0))
    ur, uc = -np.cos(th), np.sin(th)          # along-strike unit (row, col)
    pr, pc = -uc, ur                           # strike normal, matches offset_components side sign
    ay_i = np.rint(ay).astype(np.int64)
    ax_i = np.rint(ax).astype(np.int64)
    py_p = np.clip(np.rint(ay + 5.0 * pr).astype(np.int64), 0, H - 1)
    px_p = np.clip(np.rint(ax + 5.0 * pc).astype(np.int64), 0, W - 1)
    py_m = np.clip(np.rint(ay - 5.0 * pr).astype(np.int64), 0, H - 1)
    px_m = np.clip(np.rint(ax - 5.0 * pc).astype(np.int64), 0, W - 1)
    d_plus = depth[py_p, px_p]
    d_minus = depth[py_m, px_m]
    hw_sign = np.where(
        np.isfinite(d_plus) & np.isfinite(d_minus) & (d_plus != d_minus),
        np.sign(d_plus - d_minus),
        0.0,
    )
    is_hw = np.where(
        (hw_sign == 0.0) | (side == 0.0),
        0.5,
        np.where(side == hw_sign, 1.0, 0.0),
    )
    del depth, th, ur, uc, pr, pc, ay, ax, ay_i, ax_i, py_p, px_p, py_m, px_m, d_plus, d_minus, hw_sign

    along = np.exp(-np.abs(d_par) / 25.0)
    base = np.where(valid, coh_fp * along, 0.0)
    for j, (s, sig) in enumerate(_OFFSETS):
        ridge = np.exp(-((d_perp - s) ** 2) / (2.0 * sig * sig)) * base
        out[:, j] = (is_hw * ridge).astype(np.float32)
        out[:, 3 + j] = ((1.0 - is_hw) * ridge).astype(np.float32)
    out[:, 6] = np.where(
        valid,
        np.exp(-d_perp / (0.35 * seg_len + 3.0)) * np.exp(-np.abs(d_par) / (seg_len + 10.0)),
        0.0,
    ).astype(np.float32)
    out[:, 7] = np.where(valid, np.clip(d_perp / (seg_len + 1.0), 0.0, 5.0), 0.0).astype(np.float32)
    out[:, 10] = (np.exp(-dist_fp / 12.0) * (1.0 - coh_fp)).astype(np.float32)
    out[:, 11] = np.where(
        valid,
        coh_fp * np.exp(-np.abs(d_par) / 40.0) * np.exp(-((d_perp - 8.0) ** 2) / (2.0 * 36.0)),
        0.0,
    ).astype(np.float32)
    return out


def adaptive_dinkelbach_emit(
    p_2d: np.ndarray,
    q_2d: np.ndarray,
    allowed_mask: np.ndarray,
    *,
    alpha: float = 0.2,
    beta: float = 0.8,
    dti_prior: float = 0.10,
    min_sep_px: float = 1.9,
    max_budget: int = 55_000,
    min_budget: int = 20_000,
    candidate_pool: int = 420_000,
    lambda_update_every: int = 1_000,
) -> tuple[np.ndarray, dict]:
    """Greedy max-cover emission with Dinkelbach-updated FP price.

    Expected TP gain of a dot is computed exactly against the current kernel
    cover under p (the calibrated exact-trace posterior); expected FP cost is
    (1 - q) with q the learned 300 m kernel-credit head. The FP price
    lambda_fp = alpha*DTI_hat/(1-alpha*DTI_hat) is re-derived every
    ``lambda_update_every`` accepted dots from accumulated expected TP/FP and
    the expected truth mass N_hat = sum(p) over the footprint, and emission
    stops when the best exact marginal utility is <= 0 (after min_budget).
    """
    H, W = p_2d.shape
    pad = 3
    p = np.clip(np.asarray(p_2d, dtype=np.float64), 0.0, 1.0)
    q = np.clip(np.asarray(q_2d, dtype=np.float64), 0.0, 1.0)
    p_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    p_pad[pad:pad + H, pad:pad + W] = p
    cov_pad = np.zeros_like(p_pad)
    n_hat = float(p.sum())

    dy = metric.OFF_DY.tolist()
    dx = metric.OFF_DX.tolist()
    kw = metric.OFF_K.tolist()
    n_off = len(kw)

    init_tp = np.zeros((H, W), dtype=np.float64)
    for oy, ox, k_val in zip(dy, dx, kw):
        init_tp += k_val * p_pad[pad + oy:pad + oy + H, pad + ox:pad + ox + W]
    pen = 1.0 - q

    def lam_from_dti(dti_hat: float) -> float:
        dti_hat = min(max(dti_hat, 1e-6), 0.95)
        return alpha * dti_hat / (1.0 - alpha * dti_hat)

    lam = lam_from_dti(dti_prior)
    u0 = init_tp - lam * pen
    valid_idx = np.flatnonzero(allowed_mask & (init_tp > 0.0))
    if valid_idx.size > candidate_pool:
        sub = u0.ravel()[valid_idx]
        keep = np.argpartition(sub, -candidate_pool)[-candidate_pool:]
        valid_idx = valid_idx[keep]
    ys = (valid_idx // W + pad).astype(np.int64)
    xs = (valid_idx % W + pad).astype(np.int64)
    gain_ub = init_tp.ravel()[valid_idx].copy()   # upper-bound TP gain per candidate
    pen_v = pen.ravel()[valid_idx].copy()
    del init_tp, u0, pen, q

    r_sep = int(np.ceil(min_sep_px)) if min_sep_px > 1.01 else 0
    if r_sep > 0:
        sy_g, sx_g = np.mgrid[-r_sep:r_sep + 1, -r_sep:r_sep + 1]
        sep_m = (sy_g * sy_g + sx_g * sx_g) < (min_sep_px * min_sep_px)
        sep_dy = sy_g[sep_m].tolist()
        sep_dx = sx_g[sep_m].tolist()
    else:
        sep_dy, sep_dx = [0], [0]

    blocked = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool)
    alive = np.ones(valid_idx.size, dtype=bool)

    def build_heap() -> list:
        idxs = np.flatnonzero(alive)
        heap = [(-(gain_ub[i] - lam * pen_v[i]), int(i)) for i in idxs]
        heapq.heapify(heap)
        return heap

    heap = build_heap()
    out = np.zeros((H, W), dtype=np.float32)
    selected = 0
    tp_exp = 0.0
    fp_exp = 0.0
    since_update = 0
    lambda_trace = [{"dots": 0, "lambda_fp": lam, "dti_hat": dti_prior}]
    stop_reason = "budget_cap"
    while selected < max_budget and heap:
        _, i = heapq.heappop(heap)
        if not alive[i]:
            continue
        cy, cx = int(ys[i]), int(xs[i])
        if blocked[cy, cx]:
            alive[i] = False
            continue
        gain = 0.0
        for m in range(n_off):
            ny, nx = cy + dy[m], cx + dx[m]
            k_m = kw[m]
            cur = cov_pad[ny, nx]
            if k_m > cur:
                gain += p_pad[ny, nx] * (k_m - cur)
        gain_ub[i] = gain
        exact_u = gain - lam * pen_v[i]
        if selected >= min_budget and exact_u <= 0.0 and (not heap or -exact_u <= heap[0][0] + 1e-14):
            stop_reason = "marginal_utility_nonpositive"
            break
        if not heap or (-exact_u <= heap[0][0] + 1e-14):
            if selected >= min_budget and exact_u <= 0.0:
                stop_reason = "marginal_utility_nonpositive"
                break
            out[cy - pad, cx - pad] = 1.0
            for m in range(n_off):
                ny, nx = cy + dy[m], cx + dx[m]
                if kw[m] > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = kw[m]
            for sdy, sdx in zip(sep_dy, sep_dx):
                blocked[cy + sdy, cx + sdx] = True
            alive[i] = False
            selected += 1
            tp_exp += gain
            fp_exp += float(pen_v[i])
            since_update += 1
            if since_update >= lambda_update_every:
                since_update = 0
                fn_exp = max(n_hat - tp_exp, 0.0)
                den = tp_exp + alpha * fp_exp + beta * fn_exp
                dti_hat = float(tp_exp / den) if den > 0 else dti_prior
                lam = lam_from_dti(dti_hat)
                lambda_trace.append({"dots": selected, "lambda_fp": lam, "dti_hat": dti_hat,
                                     "tp_exp": tp_exp, "fp_exp": fp_exp})
                heap = build_heap()
        else:
            heapq.heappush(heap, (-exact_u, i))
    info = {
        "emitted_dots": int(selected),
        "stop_reason": stop_reason,
        "expected_truth_mass_n_hat": n_hat,
        "final_tp_exp": tp_exp,
        "final_fp_exp": fp_exp,
        "lambda_trace_tail": lambda_trace[-6:],
        "lambda_updates": len(lambda_trace) - 1,
    }
    return out, info
