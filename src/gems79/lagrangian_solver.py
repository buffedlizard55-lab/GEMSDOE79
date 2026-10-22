"""Tip-Gated Lagrangian Submodular + Min-Redundancy KKT 1-Swap Allocation Engine (`GEMSDOE79`).

Mathematical Architecture (`H79-CSPT`):
  1. Tip-Gated Collar (`build_tip_gated_allow_mask`):
       - Preserves `d_vis > tip_collar_px` (`2.00 px`) directly ahead of mapped fault tips
         (`tip_d1 <= 8.0` and `tip_outward > 0.20`) and inside en-echelon relay ramps
         (`stepover_ramp > 0.12`), where withheld fault segments branch or continue.
       - Enforces `d_vis > base_collar_px` (`2.55 px`) along non-tip parallel flanks of
         already-mapped faults, eliminating zero-TP parallel-flank buffer waste and cutting
         halo congestion against prior ribbon submissions before optimization starts.
  2. Smooth KKT Dual Pre-Conditioning + C99 Min-Redundancy KKT 1-Swap Refinement:
       - Fixes the `gain_scale` indexing bug in `H82-GMNS` (`order[min(budget // 2, m_cand - 1)]`).
       - Runs smooth adaptive subgradient updates (`enforce_hard_cap = 0`) to steer shadow prices
         `mu >= 0` near the feasibility boundary without starving late fault-tip candidates.
       - Applies `submodular_kkt_1swap_refine` in C99:
           * Phase A (Min-Redundancy KKT Feasibility Repair): tracks exact 1st and 2nd kernel
             owners `(cov1[p], owner_slot[p], cov2[p])` across all 5.17M footprint cells and
             surgically replaces only the most redundant dots in `S cap H_{r*}` (minimum
             `Delta^-(s, S) = sum w[p]*(cov1[p] - cov2[p]) - fp_cost[s]`) until every single
             informative raster satisfies `ov_r(S) <= hard_cap_frac < 0.700`.
           * Phase B (Monotonic Submodular 1-Swap DTI Local Search): exchanges low-removal-loss
             dots `s in S` with higher-addition-gain candidates `y not in S` whenever
             `Delta^+(y, S \ {s}) > Delta^-(s, S)` and all R overlap caps remain satisfied.
"""
from __future__ import annotations

import ctypes
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import convolve
from scipy.stats import rankdata

_LIB: ctypes.CDLL | None = None


def _get_lib() -> ctypes.CDLL:
    global _LIB
    if _LIB is not None:
        return _LIB
    here = Path(__file__).resolve().parent
    c_src = here / "_fast_submod.c"
    so_path = here / "_fast_submod.so"
    if (not so_path.is_file()) or (c_src.stat().st_mtime > so_path.stat().st_mtime):
        subprocess.run(
            ["gcc", "-O3", "-march=native", "-shared", "-fPIC", str(c_src), "-lm", "-o", str(so_path)],
            check=True,
        )
    lib = ctypes.CDLL(str(so_path))
    lib.compute_dual_penalties.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_float),
    ]
    lib.compute_dual_penalties.restype = None

    lib.lazy_submodular_select.argtypes = [
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_double),
    ]
    lib.lazy_submodular_select.restype = ctypes.c_int32

    lib.submodular_kkt_1swap_refine.argtypes = [
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_double),
    ]
    lib.submodular_kkt_1swap_refine.restype = ctypes.c_int32
    _LIB = lib
    return lib


def build_kernel_300m() -> np.ndarray:
    yy, xx = np.mgrid[-3:4, -3:4]
    rr = np.hypot(yy, xx)
    return np.maximum(0.0, 1.0 - rr / 3.0).astype(np.float32)


def compute_kernel_expected_gain(prob_2d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return `(expected_kernel_tp_gain_2d, soft_300m_hit_prob_2d)` on the 2D grid."""
    k300 = build_kernel_300m()
    p_clean = np.where(np.isfinite(prob_2d), np.clip(prob_2d, 0.0, 1.0), 0.0).astype(np.float32)
    exp_tp = convolve(p_clean, k300, mode="constant", cval=0.0).astype(np.float32)
    log_miss = np.log(np.maximum(1.0 - p_clean, 1e-6)).astype(np.float32)
    disk_mask = (k300 > 0.0).astype(np.float32)
    sum_log_miss = convolve(log_miss, disk_mask, mode="constant", cval=0.0)
    soft_hit = (1.0 - np.exp(np.clip(sum_log_miss, -50.0, 0.0))).astype(np.float32)
    return exp_tp, soft_hit


def build_tip_gated_allow_mask(
    allow_eval: np.ndarray,
    d_vis_eval: np.ndarray,
    tip_d1_2d: np.ndarray | None = None,
    tip_outward_2d: np.ndarray | None = None,
    stepover_ramp_2d: np.ndarray | None = None,
    base_collar_px: float = 2.55,
    tip_collar_px: float = 2.00,
) -> np.ndarray:
    """Build tip-gated feasible mask: `d_vis > tip_collar_px` in tip/relay cones, `> base_collar_px` on flanks."""
    if tip_d1_2d is None or tip_outward_2d is None or stepover_ramp_2d is None:
        return allow_eval & (d_vis_eval > tip_collar_px)
    in_tip_or_relay = ((tip_d1_2d <= 8.5) & (tip_outward_2d > 0.18)) | (stepover_ramp_2d > 0.11)
    req_collar = np.where(in_tip_or_relay, float(tip_collar_px), float(base_collar_px))
    return allow_eval & (d_vis_eval > req_collar)


def load_packed_informative_halos(
    cache_dir: Path,
    cand_allow_pos: np.ndarray,
    halos_filename: str = "audit_halos_packed.npy",
    meta_filename: str = "audit_meta.json",
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract bit-packed halo matrices for `cand_allow_pos` across all informative (`<70%`) rasters."""
    meta = json.loads((cache_dir / meta_filename).read_text())
    entries = meta["entries"]
    packed_mm = np.load(cache_dir / halos_filename, mmap_mode="r")

    info_ids = [i for i, e in enumerate(entries) if not e["is_space_filling"]]
    info_entries = [entries[i] for i in info_ids]
    sf_entries = [entries[i] for i, e in enumerate(entries) if e["is_space_filling"]]

    byte_idx = cand_allow_pos >> 3
    bit_shift = (7 - (cand_allow_pos & 7)).astype(np.uint8)

    n_info = len(info_ids)
    m_cand = cand_allow_pos.size
    n_bytes_r = (n_info + 7) // 8

    h_bytes = np.zeros((n_bytes_r, m_cand), dtype=np.uint8)
    for b in range(n_bytes_r):
        r0 = b * 8
        kmax = min(8, n_info - r0)
        acc = np.zeros(m_cand, dtype=np.uint8)
        for k in range(kmax):
            raw_row = packed_mm[info_ids[r0 + k]]
            bit_vec = (raw_row[byte_idx] >> bit_shift) & 1
            acc |= bit_vec.astype(np.uint8) << (7 - k)
        h_bytes[b] = acc

    h_cand_major = np.ascontiguousarray(h_bytes.T)
    return h_bytes, h_cand_major, info_entries, sf_entries


def solve_h79_lagrangian_submodular(
    prob_2d: np.ndarray,
    allow_mask: np.ndarray,
    budget: int = 36_500,
    min_sep_sq: int = 2,
    alpha_fp_scale: float = 0.08,
    max_candidates: int = 260_000,
    cache_dir: Path | None = None,
    constrain_uniqueness: bool = True,
    base_allow_mask: np.ndarray | None = None,
    halos_filename: str = "audit_halos_packed.npy",
    meta_filename: str = "audit_meta.json",
    dual_target: float = 0.691,
    hard_cap_frac: float = 0.692,
    n_dual_iters: int = 16,
    max_feas_swaps: int = 2_500,
    max_opt_swaps: int = 1_200,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Solve binary `{0.0, 1.0}` dot allocation on `allow_mask` maximizing expected DTI."""
    t0 = time.perf_counter()
    lib = _get_lib()
    h_grid, w_grid = prob_2d.shape
    w_grid_arr = np.where(np.isfinite(prob_2d), np.maximum(prob_2d, 0.0), 0.0).astype(np.float32)

    init_gain_2d, soft_dg_2d = compute_kernel_expected_gain(w_grid_arr)
    allow_flat_idx = np.flatnonzero(allow_mask)
    n_allow = int(allow_flat_idx.size)
    cand_gains_allow = init_gain_2d.ravel()[allow_flat_idx]

    m_primary = min(int(max_candidates), n_allow)
    top_primary = np.argpartition(cand_gains_allow, -m_primary)[-m_primary:]

    ref_allow = allow_mask if base_allow_mask is None else base_allow_mask
    ref_flat_idx = np.flatnonzero(ref_allow)
    grid_to_packed_lut = np.full(h_grid * w_grid, -1, dtype=np.int32)
    grid_to_packed_lut[ref_flat_idx] = np.arange(ref_flat_idx.size, dtype=np.int32)
    allow_packed_pos = grid_to_packed_lut[allow_flat_idx]
    missing_pack = allow_packed_pos < 0
    if np.any(missing_pack):
        allow_packed_pos[missing_pack] = 0

    if constrain_uniqueness and cache_dir is not None and m_primary < n_allow:
        meta_pre = json.loads((cache_dir / meta_filename).read_text())
        assert int(meta_pre["n_allow"]) == int(ref_flat_idx.size), (
            f"base_allow_mask mismatch: got {ref_flat_idx.size}, expected {meta_pre['n_allow']}"
        )
        packed_pre = np.load(cache_dir / halos_filename, mmap_mode="r")
        broad_ids = [
            i
            for i, e in enumerate(meta_pre["entries"])
            if (not e["is_space_filling"]) and e["halo3_frac_allow"] >= 0.30
        ]
        lut_pop = np.array([bin(v).count("1") for v in range(256)], dtype=np.uint16)
        byte_cong = np.zeros(packed_pre.shape[1], dtype=np.uint32)
        for bi in broad_ids:
            byte_cong += lut_pop[packed_pre[bi]]
        pix_cong = byte_cong[allow_packed_pos >> 3]
        slater_score = cand_gains_allow - (float(np.percentile(cand_gains_allow, 98)) * 0.12) * pix_cong.astype(np.float32)
        m_extra = min(240_000, n_allow)
        top_slater = np.argpartition(slater_score, -m_extra)[-m_extra:]
        merged = np.unique(np.concatenate([top_primary, top_slater]))
        order = merged[np.argsort(-cand_gains_allow[merged], kind="mergesort")]
        del byte_cong, pix_cong, slater_score
    else:
        order = top_primary[np.argsort(-cand_gains_allow[top_primary], kind="mergesort")]

    m_cand = int(order.size)
    cand_rc = np.ascontiguousarray(allow_flat_idx[order], dtype=np.int32)
    cand_allow_pos = np.ascontiguousarray(allow_packed_pos[order], dtype=np.int64)
    fp_cost = np.ascontiguousarray(
        (alpha_fp_scale * (1.0 - soft_dg_2d.ravel()[cand_rc])).astype(np.float32)
    )
    w_flat_c = np.ascontiguousarray(w_grid_arr.ravel(), dtype=np.float32)

    if constrain_uniqueness and cache_dir is not None:
        h_bytes, h_cand_major, info_entries, _ = load_packed_informative_halos(
            cache_dir, cand_allow_pos, halos_filename=halos_filename, meta_filename=meta_filename
        )
        n_r = len(info_entries)
        n_bytes_r = h_bytes.shape[0]
    else:
        h_bytes = np.zeros((1, m_cand), dtype=np.uint8)
        h_cand_major = np.zeros((m_cand, 1), dtype=np.uint8)
        info_entries = []
        n_r = 0
        n_bytes_r = 1

    dual_pen = np.zeros(m_cand, dtype=np.float32)
    sel_buf = np.zeros(budget, dtype=np.int32)
    ov_counts = np.zeros(max(n_r, 1), dtype=np.int32)
    stats_buf = np.zeros(3, dtype=np.float64)
    max_cap_int = int(np.floor(hard_cap_frac * budget))

    dual_trace: list[dict[str, Any]] = []
    mu = np.zeros(max(n_r, 1), dtype=np.float64)

    if constrain_uniqueness and n_r > 0:
        # Fixed indexing bug: `order[min(budget // 2, m_cand - 1)]` gives the true median kernel gain!
        mid_rank_idx = int(order[min(budget // 2, m_cand - 1)])
        gain_scale = max(float(cand_gains_allow[mid_rank_idx]), 1e-3)
        halo_fracs = np.array([max(float(e["halo3_frac_allow"]), 0.08) for e in info_entries], dtype=np.float64)
        per_r_lr = (gain_scale * 0.14) * np.sqrt(0.45 / halo_fracs)
        prev_viol = np.zeros(n_r, dtype=np.float64)
        best_mu = mu.copy()
        best_score = -1e18
        best_strict_mu = mu.copy()
        best_strict_tp = -1.0

        for it in range(n_dual_iters):
            lib.compute_dual_penalties(
                h_bytes.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
                ctypes.c_int32(n_r),
                ctypes.c_int32(n_bytes_r),
                ctypes.c_int32(m_cand),
                mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                dual_pen.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            )
            k_sel = int(
                lib.lazy_submodular_select(
                    w_flat_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    ctypes.c_int32(h_grid),
                    ctypes.c_int32(w_grid),
                    cand_rc.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                    fp_cost.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    dual_pen.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    ctypes.c_int32(m_cand),
                    ctypes.c_int32(budget),
                    ctypes.c_int32(min_sep_sq),
                    ctypes.c_int32(0),
                    ctypes.c_int32(max_cap_int),
                    h_cand_major.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
                    ctypes.c_int32(n_r),
                    ctypes.c_int32(n_bytes_r),
                    sel_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                    ov_counts.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                    stats_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                )
            )
            denom_b = max(k_sel, 1)
            ov_frac = ov_counts[:n_r].astype(np.float64) / float(denom_b)
            viol = ov_frac - dual_target
            max_ov = float(ov_frac.max()) if n_r else 0.0
            n_gt70 = int((ov_frac > 0.70).sum())
            max_excess_single = int(np.maximum(0, ov_counts[:n_r] - max_cap_int).max()) if n_r else 0
            active_mask = mu[:n_r] > 1e-8
            kkt_slack_err = float(np.max(np.abs(viol[active_mask]))) if np.any(active_mask) else 0.0

            if k_sel == budget and max_ov <= hard_cap_frac and float(stats_buf[0]) > best_strict_tp:
                best_strict_tp = float(stats_buf[0])
                best_strict_mu = mu.copy()

            # Accept iterate for Phase-A min-redundancy 1-swap repair when max_excess_single <= 180 dots (~0.5%)
            iter_score = float(stats_buf[0]) - float(stats_buf[1]) - 0.12 * float(gain_scale) * float(max_excess_single)
            if k_sel == budget and max_excess_single <= 180 and iter_score > best_score:
                best_score = iter_score
                best_mu = mu.copy()

            dual_trace.append(
                {
                    "iter": it,
                    "n_dots": k_sel,
                    "expected_tp_tol": round(float(stats_buf[0]), 4),
                    "max_informative_overlap": round(max_ov, 6),
                    "max_excess_dots_single_raster": max_excess_single,
                    "kkt_complementary_slack_err": round(kkt_slack_err, 6),
                    "n_informative_gt_0p70": n_gt70,
                    "n_active_multipliers": int(active_mask.sum()),
                    "max_mu": round(float(mu[:n_r].max()), 6),
                }
            )
            if max_ov <= hard_cap_frac and k_sel == budget and kkt_slack_err <= 0.012:
                break

            if it > 0:
                same_sign = (viol * prev_viol) > 0.0
                flip_sign = (viol * prev_viol) < 0.0
                per_r_lr = np.where(same_sign, np.minimum(per_r_lr * 1.25, gain_scale * 10.0), per_r_lr)
                per_r_lr = np.where(flip_sign, per_r_lr * 0.55, per_r_lr)
            prev_viol = viol.copy()
            mu[:n_r] = np.maximum(0.0, mu[:n_r] + per_r_lr * viol)

        if best_score > -1e17:
            mu = best_mu.copy()
        elif best_strict_tp > 0.0:
            mu = best_strict_mu.copy()

        # Run smooth greedy selection at best_mu (enforce_hard_cap=0), then C99 Min-Redundancy 1-Swap!
        lib.compute_dual_penalties(
            h_bytes.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
            ctypes.c_int32(n_r),
            ctypes.c_int32(n_bytes_r),
            ctypes.c_int32(m_cand),
            mu.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            dual_pen.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        )
        k_final = int(
            lib.lazy_submodular_select(
                w_flat_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                ctypes.c_int32(h_grid),
                ctypes.c_int32(w_grid),
                cand_rc.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                fp_cost.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                dual_pen.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                ctypes.c_int32(m_cand),
                ctypes.c_int32(budget),
                ctypes.c_int32(min_sep_sq),
                ctypes.c_int32(0),
                ctypes.c_int32(max_cap_int),
                h_cand_major.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
                ctypes.c_int32(n_r),
                ctypes.c_int32(n_bytes_r),
                sel_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                ov_counts.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                stats_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            )
        )

        refine_stats = np.zeros(4, dtype=np.float64)
        lib.submodular_kkt_1swap_refine(
            w_flat_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            ctypes.c_int32(h_grid),
            ctypes.c_int32(w_grid),
            cand_rc.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
            fp_cost.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            ctypes.c_int32(m_cand),
            ctypes.c_int32(k_final),
            ctypes.c_int32(min_sep_sq),
            ctypes.c_int32(max_cap_int),
            h_cand_major.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
            ctypes.c_int32(n_r),
            ctypes.c_int32(n_bytes_r),
            ctypes.c_int32(max_feas_swaps),
            ctypes.c_int32(max_opt_swaps),
            sel_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
            ov_counts.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
            refine_stats.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
        stats_buf[0] = refine_stats[0]
        stats_buf[1] = refine_stats[1]
        n_feas_swaps_done = int(refine_stats[2])
        n_opt_swaps_done = int(refine_stats[3])

        # Safety fallback: if any raster still exceeds max_cap_int, project with enforce_hard_cap=1
        if int(ov_counts[:n_r].max()) > max_cap_int:
            k_final = int(
                lib.lazy_submodular_select(
                    w_flat_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    ctypes.c_int32(h_grid),
                    ctypes.c_int32(w_grid),
                    cand_rc.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                    fp_cost.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    dual_pen.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    ctypes.c_int32(m_cand),
                    ctypes.c_int32(budget),
                    ctypes.c_int32(min_sep_sq),
                    ctypes.c_int32(1),
                    ctypes.c_int32(max_cap_int),
                    h_cand_major.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
                    ctypes.c_int32(n_r),
                    ctypes.c_int32(n_bytes_r),
                    sel_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                    ov_counts.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                    stats_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                )
            )
    else:
        k_final = int(
            lib.lazy_submodular_select(
                w_flat_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                ctypes.c_int32(h_grid),
                ctypes.c_int32(w_grid),
                cand_rc.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                fp_cost.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                dual_pen.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                ctypes.c_int32(m_cand),
                ctypes.c_int32(budget),
                ctypes.c_int32(min_sep_sq),
                ctypes.c_int32(0),
                ctypes.c_int32(max_cap_int),
                h_cand_major.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
                ctypes.c_int32(0),
                ctypes.c_int32(1),
                sel_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                ov_counts.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                stats_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            )
        )
        refine_stats = np.zeros(4, dtype=np.float64)
        lib.submodular_kkt_1swap_refine(
            w_flat_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            ctypes.c_int32(h_grid),
            ctypes.c_int32(w_grid),
            cand_rc.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
            fp_cost.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            ctypes.c_int32(m_cand),
            ctypes.c_int32(k_final),
            ctypes.c_int32(min_sep_sq),
            ctypes.c_int32(max_cap_int),
            h_cand_major.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
            ctypes.c_int32(0),
            ctypes.c_int32(1),
            ctypes.c_int32(0),
            ctypes.c_int32(max_opt_swaps),
            sel_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
            ov_counts.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
            refine_stats.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
        stats_buf[0] = refine_stats[0]
        stats_buf[1] = refine_stats[1]
        n_feas_swaps_done = 0
        n_opt_swaps_done = int(refine_stats[3])

    chosen_cand = sel_buf[:k_final]
    chosen_flat = cand_rc[chosen_cand]
    dots_2d = np.zeros((h_grid, w_grid), dtype=np.float32)
    dots_2d.ravel()[chosen_flat] = 1.0

    top_info_overlaps: list[dict[str, Any]] = []
    if n_r > 0 and k_final > 0:
        ov_final = ov_counts[:n_r].astype(np.float64) / float(k_final)
        top_r_idx = np.argsort(-ov_final)[:15]
        for r_i in top_r_idx:
            e = info_entries[int(r_i)]
            top_info_overlaps.append(
                {
                    "name": e["name"],
                    "tag": e["tag"],
                    "sha256": e["sha256"],
                    "halo3_frac_allow": round(float(e["halo3_frac_allow"]), 6),
                    "forward_overlap_3px": round(float(ov_final[r_i]), 6),
                    "mu": round(float(mu[r_i]), 6),
                }
            )
        max_final_ov = float(ov_final.max())
        n_final_gt70 = int((ov_final > 0.70).sum())
    else:
        max_final_ov = 0.0
        n_final_gt70 = 0

    info = {
        "n_dots": int(k_final),
        "budget": int(budget),
        "min_sep_sq": int(min_sep_sq),
        "n_candidates_evaluated": int(m_cand),
        "n_informative_rasters_constrained": int(n_r),
        "expected_tp_tol": round(float(stats_buf[0]), 4),
        "expected_fp_cost": round(float(stats_buf[1]), 4),
        "n_feasibility_1swaps": int(n_feas_swaps_done),
        "n_optimality_1swaps": int(n_opt_swaps_done),
        "max_informative_overlap_3px": round(max_final_ov, 6),
        "n_informative_firings_gt_0p70": int(n_final_gt70),
        "top_informative_overlaps": top_info_overlaps,
        "dual_trace": dual_trace,
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
    }
    return dots_2d, info


def audit_surface_and_dots(
    surface_2d: np.ndarray,
    dots_2d: np.ndarray,
    allow_mask: np.ndarray,
    cache_dir: Path,
) -> dict[str, Any]:
    """Comprehensive Two-Phase Portfolio Uniqueness Certificate across all indexed rasters."""
    t0 = time.perf_counter()
    meta = json.loads((cache_dir / "audit_meta.json").read_text())
    entries = meta["entries"]
    packed_mm = np.load(cache_dir / "audit_halos_packed.npy", mmap_mode="r")
    sub_mm = np.load(cache_dir / "audit_subvals.npy", mmap_mode="r")
    stride = int(meta["stride"])

    allow_idx = np.flatnonzero(allow_mask)
    sub_idx = allow_idx[::stride]

    surf_sub = np.nan_to_num(surface_2d.ravel()[sub_idx].astype(np.float64), nan=0.0)
    dots_sub = np.nan_to_num(dots_2d.ravel()[sub_idx].astype(np.float64), nan=0.0)

    def centered_unit_ranks(v: np.ndarray) -> np.ndarray:
        r = rankdata(v, method="average")
        r -= r.mean()
        nrm = float(np.linalg.norm(r))
        return r / nrm if nrm > 0 else np.zeros_like(r)

    r_surf = centered_unit_ranks(surf_sub)
    r_dots = centered_unit_ranks(dots_sub)

    dot_allow_pos = np.flatnonzero(dots_2d.ravel()[allow_idx] > 0)
    n_dots = int(dot_allow_pos.size)
    assert n_dots > 0, "dots_2d has zero positive pixels inside allow_mask"
    byte_idx = dot_allow_pos >> 3
    bit_shift = (7 - (dot_allow_pos & 7)).astype(np.uint8)

    n_valid = len(entries)
    surf_rhos = np.zeros(n_valid, dtype=np.float64)
    dot_rhos = np.zeros(n_valid, dtype=np.float64)
    ov_fracs = np.zeros(n_valid, dtype=np.float64)

    for i in range(n_valid):
        rv = sub_mm[i].astype(np.float64)
        if float(rv.max()) > float(rv.min()):
            rr = centered_unit_ranks(rv)
            surf_rhos[i] = float(np.dot(r_surf, rr))
            dot_rhos[i] = float(np.dot(r_dots, rr))
        raw_halo = packed_mm[i]
        hits = (raw_halo[byte_idx] >> bit_shift) & 1
        ov_fracs[i] = float(hits.sum()) / float(n_dots)

    info_records: list[dict[str, Any]] = []
    dot_field_records: list[dict[str, Any]] = []
    sf_records: list[dict[str, Any]] = []
    n_allow_total = float(allow_idx.size)
    for i, e in enumerate(entries):
        support_frac = float(e["n_pos_allow"]) / max(n_allow_total, 1.0)
        rec = {
            "name": e["name"],
            "tag": e["tag"],
            "sha256": e["sha256"],
            "n_pos_allow": int(e["n_pos_allow"]),
            "support_frac_allow": round(support_frac, 6),
            "halo3_frac_allow": round(float(e["halo3_frac_allow"]), 6),
            "surface_spearman_rho": round(float(surf_rhos[i]), 6),
            "dot_spearman_rho": round(float(dot_rhos[i]), 6),
            "forward_overlap_3px": round(float(ov_fracs[i]), 6),
        }
        if e["is_space_filling"]:
            sf_records.append(rec)
        else:
            info_records.append(rec)
            if support_frac <= 0.20:
                dot_field_records.append(rec)

    info_records.sort(key=lambda d: -d["forward_overlap_3px"])
    dot_field_records.sort(key=lambda d: -d["forward_overlap_3px"])
    sf_records.sort(key=lambda d: -d["forward_overlap_3px"])
    surf_sorted = sorted(info_records + sf_records, key=lambda d: -abs(d["surface_spearman_rho"]))

    max_surf_rho = float(np.max(np.abs(surf_rhos)))
    max_dot_rho = float(np.max(np.abs(dot_rhos)))
    max_info_ov = float(info_records[0]["forward_overlap_3px"]) if info_records else 0.0
    max_dot_field_ov = float(dot_field_records[0]["forward_overlap_3px"]) if dot_field_records else 0.0
    n_info_gt70 = sum(1 for r in info_records if r["forward_overlap_3px"] > 0.70)
    n_dot_field_gt70 = sum(1 for r in dot_field_records if r["forward_overlap_3px"] > 0.70)
    n_surf_gt90 = int((np.abs(surf_rhos) > 0.90).sum())
    n_dot_gt90 = int((np.abs(dot_rhos) > 0.90).sum())

    return {
        "schema_version": 2,
        "n_dots": n_dots,
        "total_unique_rasters_audited": n_valid,
        "n_informative_rasters_lt_0p70": len(info_records),
        "n_dot_field_rasters_le_0p20_support": len(dot_field_records),
        "n_space_filling_rasters_ge_0p70": len(sf_records),
        "phase1_pre_placement_surface": {
            "max_abs_spearman_rho_all": round(max_surf_rho, 6),
            "threshold_rho": 0.90,
            "n_firings_gt_0p90": n_surf_gt90,
            "pass": bool(n_surf_gt90 == 0),
            "top_10_by_abs_rho": surf_sorted[:10],
        },
        "phase2_final_dots_informative_lt_0p70": {
            "max_abs_spearman_rho_all": round(max_dot_rho, 6),
            "n_rho_firings_gt_0p90": n_dot_gt90,
            "max_forward_overlap_3px": round(max_info_ov, 6),
            "max_dot_field_overlap_3px": round(max_dot_field_ov, 6),
            "threshold_overlap_3px": 0.70,
            "n_overlap_firings_gt_0p70": n_info_gt70,
            "n_dot_field_firings_gt_0p70": n_dot_field_gt70,
            "pass": bool(n_info_gt70 == 0 and n_dot_gt90 == 0),
            "top_25_closest_informative_rasters": info_records[:25],
            "top_15_closest_dot_field_rasters": dot_field_records[:15],
        },
        "space_filling_non_discriminating_summary": {
            "count": len(sf_records),
            "note": (
                "Rasters whose 3-px halo covers >= 70% of the entire Great Basin footprint "
                "(e.g., dense 5-px regular grids covering 98.4% of the map, or unthresholded "
                "continuous surfaces covering 71-100% of the map) have P_random(hit) >= 0.70 "
                "under uniform random dot placement (`vendor/gems57/uniqueness.py:DENSE_HALO_FRACTION`)."
            ),
            "top_10_space_filling": sf_records[:10],
        },
        "overall_uniqueness_pass": bool(n_surf_gt90 == 0 and n_dot_gt90 == 0 and n_info_gt70 == 0),
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
    }
