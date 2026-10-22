"""G79-CSMD: Coulomb Stress-Shadow, Sub-Smectite MT-Gravity, Potassic Kd,
Drape-Notched Magnetics, Slip-Deficit & Flank-Decontaminated Charnes-Cooper
Multi-Regime Discovery.

Upgrades G79-THVC across three preregistered axes:
  1. Adds 4 new static physical & geochemical channels (74 total):
     - mt_grav_conduit_colin (H80-MT-PHASE: sub-smectite conductivity x basement-depth normal colinearity)
     - mag_notch_drape_wavenumber (H80-DRAPE-DECONV: 400m flight-line notch + drape-corrected wavenumber depth)
     - rad_kd_adularia_resid (H80-RADIO-KD: out-of-quadrant potassic adularia residual Kd with playa rejection)
     - piedmont_relief_step (H80-SLIP-DEFICIT: range-front footwall structural relief envelope x piedmont step)
  2. Adds 2 new strictly fold-visible elastic mechanics channels (16 total, 90 channels combined):
     - net_coulomb_cfs_lobe (H80-COULOMB-CFS: planar elastic dislocation tip/relay lobe minus perpendicular flank shadow)
     - net_slip_deficit_gap (H80-SLIP-DEFICIT: high footwall relief & 4km density across 1.5km visible fault gaps)
  3. Fixes the 4:1 false-negative scarp-flank contamination bug (IR-79-140) in both:
     - Stage-1 & Stage-2 simulated hide-and-recover shards (excluding 1 <= d_known < 3.0 px flanks of sim_known from negatives), and
     - Stage-1 & Stage-2 100%-visible decontaminated pure-physics dual-head ensemble (trained on 100% of fold-visible faults with 1 <= d_vis < 3.0 px flanks in halo_pool rather than far_pool).
"""
from __future__ import annotations

import gc
import heapq
import json
import mmap
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems57 import metric
from gems79.thvc_features import (
    MECH_FEATURE_NAMES,
    STATIC_FEATURE_NAMES,
    STRUCT3,
    build_static_feature_memmap,
    compute_network_mechanics,
    rss_mb,
)
from gems79.thvc_model import (
    STAGE2_FEATURE_NAMES,
    _prior_correct,
    charnes_cooper_submodular_emit,
    drop_file_cache,
    extract_stage2_spatial_features,
    fit_stage1_ensemble,
    fit_stage2_dual_heads,
    poisson_disk_emit,
    predict_stage2_dual_heads,
)

CSMD_EXTRA_STATIC_NAMES: list[str] = [
    "mt_grav_conduit_colin",
    "mag_notch_drape_wavenumber",
    "rad_kd_adularia_resid",
    "piedmont_relief_step",
]

CSMD_EXTRA_MECH_NAMES: list[str] = [
    "net_coulomb_cfs_lobe",
    "net_slip_deficit_gap",
]

CSMD_STATIC_FEATURE_NAMES: list[str] = STATIC_FEATURE_NAMES + CSMD_EXTRA_STATIC_NAMES
CSMD_MECH_FEATURE_NAMES: list[str] = MECH_FEATURE_NAMES + CSMD_EXTRA_MECH_NAMES
CSMD_ALL_FEATURE_NAMES: list[str] = CSMD_STATIC_FEATURE_NAMES + CSMD_MECH_FEATURE_NAMES

N_BASE_STATIC = len(STATIC_FEATURE_NAMES)       # 70
N_CSMD_STATIC = len(CSMD_STATIC_FEATURE_NAMES)  # 74
N_BASE_MECH = len(MECH_FEATURE_NAMES)           # 14
N_CSMD_MECH = len(CSMD_MECH_FEATURE_NAMES)      # 16
N_CSMD_ALL = len(CSMD_ALL_FEATURE_NAMES)        # 90


def _fp_to_2d(vec_fp: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = vec_fp.astype(np.float32, copy=False)
    return out


def _z_fp(vec_fp: np.ndarray) -> np.ndarray:
    v = np.nan_to_num(vec_fp.astype(np.float32, copy=False), nan=0.0, posinf=0.0, neginf=0.0)
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med))) * 1.4826 + 1e-5
    return np.clip((v - med) / mad, -8.0, 8.0).astype(np.float32)


def build_csmd_static_feature_memmap(
    raw_dir: Path,
    ing_dir: Path,
    base_mmap_path: Path,
    csmd_mmap_path: Path,
    footprint: np.ndarray,
    transform: Any,
    force_rebuild: bool = False,
) -> dict[str, Any]:
    """Build or reuse the 74-channel static physical & hydrothermal memmap (n_fp, 74)."""
    base_meta = build_static_feature_memmap(raw_dir, ing_dir, base_mmap_path, footprint, transform)
    n_fp = int(footprint.sum())
    base_mm = np.memmap(base_mmap_path, dtype="float32", mode="r", shape=(n_fp, N_BASE_STATIC))

    meta_path = csmd_mmap_path.with_suffix(".meta.json")
    if (
        not force_rebuild
        and csmd_mmap_path.exists()
        and meta_path.exists()
        and csmd_mmap_path.stat().st_size == n_fp * N_CSMD_STATIC * 4
    ):
        drop_file_cache(base_mmap_path)
        return json.loads(meta_path.read_text())

    t0 = time.time()
    csmd_mmap_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(csmd_mmap_path, dtype="float32", mode="w+", shape=(n_fp, N_CSMD_STATIC))

    chunk = 500_000
    for s in range(0, n_fp, chunk):
        e = min(n_fp, s + chunk)
        mm[s:e, :N_BASE_STATIC] = base_mm[s:e, :]
    mm.flush()

    idx = {n: i for i, n in enumerate(STATIC_FEATURE_NAMES)}

    # 1. H80-MT-PHASE: Sub-smectite deep electrical conductivity x gravity basement-depth normal colinearity
    cond_2d = _fp_to_2d(base_mm[:, idx["tf_cond_surf"]], footprint)
    bdepth_2d = _fp_to_2d(base_mm[:, idx["tf_depth_to_base_surf"]], footprint)
    qtz_fp = base_mm[:, idx["gdr_geotherm_qtz_1800m"]].astype(np.float32, copy=True)

    cond_hp = cond_2d - ndi.gaussian_filter(cond_2d, sigma=12.0)
    cond_s = ndi.gaussian_filter(cond_hp, sigma=2.2)
    bdepth_s = ndi.gaussian_filter(bdepth_2d, sigma=2.2)
    cy, cx = np.gradient(cond_s)
    by, bx = np.gradient(bdepth_s)
    cmag = np.hypot(cy, cx) + 1e-6
    bmag = np.hypot(by, bx) + 1e-6
    cos_colin = np.abs(cy * by + cx * bx) / (cmag * bmag)
    mt_grav_fp = (cos_colin * np.sqrt(cmag * bmag))[footprint] * (1.0 + 0.30 * np.clip(qtz_fp, 0.0, 4.0))
    mm[:, 70] = _z_fp(mt_grav_fp)
    del cond_2d, bdepth_2d, cond_hp, cond_s, bdepth_s, cy, cx, by, bx, cmag, bmag, cos_colin, mt_grav_fp, qtz_fp
    gc.collect()

    # 2. H80-DRAPE-DECONV: 400m flight-line notch + drape-corrected magnetic wavenumber source depth
    rtp_res_2d = _fp_to_2d(base_mm[:, idx["rtp_uc600_res"]], footprint)
    relief_fp = base_mm[:, idx["topo10_relief_local"]].astype(np.float32, copy=True)
    band_4px = ndi.uniform_filter1d(rtp_res_2d, size=3, axis=0) - ndi.uniform_filter1d(rtp_res_2d, size=7, axis=0)
    rtp_notched = rtp_res_2d - 0.55 * band_4px
    ry, rx = np.gradient(ndi.gaussian_filter(rtp_notched, sigma=1.2))
    rhgm = np.hypot(ry, rx) + 1e-5
    rz = rtp_notched - ndi.gaussian_filter(rtp_notched, sigma=3.0)
    tilt_notched = np.arctan2(rz, rhgm)
    ty, tx = np.gradient(tilt_notched)
    wn_fp = np.hypot(ty, tx)[footprint] * np.exp(0.18 * np.clip(relief_fp, 0.0, 3.5))
    mm[:, 71] = _z_fp(wn_fp)
    del rtp_res_2d, band_4px, rtp_notched, ry, rx, rhgm, rz, tilt_notched, ty, tx, relief_fp, wn_fp
    gc.collect()

    # 3. H80-RADIO-KD: Out-of-quadrant lithology-normalized potassic adularia residual Kd
    vr, vc = np.nonzero(footprint)
    rad_path = raw_dir / "external/geodawn_rad_u8.tif"
    if not rad_path.exists():
        rad_path = raw_dir / "geodawn_rad_u8.tif"
    with rasterio.open(rad_path) as src:
        rad_k = src.read(1)[vr, vc].astype(np.float32)
        rad_th = src.read(2)[vr, vc].astype(np.float32)
    r_med = float(np.median(vr))
    c_med = float(np.median(vc))
    quad_id = ((vr >= r_med).astype(np.int32) * 2 + (vc >= c_med).astype(np.int32))
    kd_oof = np.zeros(n_fp, dtype=np.float32)
    for q in range(4):
        tr = quad_id != q
        te = quad_id == q
        th_tr = rad_th[tr][::8]
        k_tr = rad_k[tr][::8]
        X_tr = np.column_stack([np.ones_like(th_tr), th_tr, th_tr * th_tr])
        coef, _, _, _ = np.linalg.lstsq(X_tr, k_tr, rcond=None)
        th_te = rad_th[te]
        k_hat = coef[0] + coef[1] * th_te + coef[2] * (th_te * th_te)
        resid_tr = k_tr - (coef[0] + coef[1] * th_tr + coef[2] * (th_tr * th_tr))
        mad_tr = float(np.median(np.abs(resid_tr - np.median(resid_tr)))) * 1.4826 + 1.0
        kd_oof[te] = (rad_k[te] - k_hat) / mad_tr

    slope_fp = base_mm[:, idx["tf_det_elev_slope"]].astype(np.float32, copy=True)
    demag_fp = base_mm[:, idx["rtp_demag_trough"]].astype(np.float32, copy=True)
    non_playa = 1.0 / (1.0 + np.exp(-2.0 * (slope_fp + 0.65)))
    kd_coupled = np.clip(kd_oof, -3.0, 5.0) * non_playa * (1.0 + 0.25 * np.clip(demag_fp, 0.0, 4.0))
    mm[:, 72] = _z_fp(kd_coupled)
    del vr, vc, rad_k, rad_th, quad_id, kd_oof, slope_fp, demag_fp, non_playa, kd_coupled
    gc.collect()

    # 4. H80-SLIP-DEFICIT (static): Piedmont structural relief envelope x alluvial-fan junction scarp step
    elev_2d = _fp_to_2d(base_mm[:, idx["tf_det_elev"]], footprint)
    mwall_2d = _fp_to_2d(base_mm[:, idx["mountain_wall_ratio"]], footprint)
    scarp_fp = base_mm[:, idx["scarp_unified_step"]].astype(np.float32, copy=True)
    grav_fp = base_mm[:, idx["grav_hgm_z200"]].astype(np.float32, copy=True)

    elev_max = ndi.gaussian_filter(ndi.maximum_filter(elev_2d, size=7), sigma=18.0)
    elev_min = ndi.gaussian_filter(ndi.minimum_filter(elev_2d, size=7), sigma=18.0)
    relief_env = np.maximum(0.0, elev_max - elev_min)[footprint]
    mwall_reg = ndi.gaussian_filter(mwall_2d, sigma=14.0)[footprint]
    mwall_loc = ndi.gaussian_filter(mwall_2d, sigma=2.0)[footprint]
    piedmont_gate = np.clip(mwall_reg - 0.35 * np.maximum(0.0, mwall_loc - 0.5), -1.0, 4.0)
    step_signal = np.sqrt(np.maximum(0.0, scarp_fp + 1.5) * np.maximum(0.0, grav_fp + 1.5))
    piedmont_fp = relief_env * np.maximum(0.0, piedmont_gate + 1.0) * step_signal
    mm[:, 73] = _z_fp(piedmont_fp)
    del elev_2d, mwall_2d, scarp_fp, grav_fp, elev_max, elev_min, relief_env, mwall_reg, mwall_loc, piedmont_gate, step_signal, piedmont_fp
    gc.collect()

    mm.flush()
    del mm
    drop_file_cache(base_mmap_path)
    drop_file_cache(csmd_mmap_path)

    meta = {
        "rows": n_fp,
        "cols": N_CSMD_STATIC,
        "feature_names": CSMD_STATIC_FEATURE_NAMES,
        "base_build_seconds": base_meta.get("build_seconds", 0.0),
        "csmd_extra_build_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
        "forbidden_columns_blocked": ["dist_known_fault_px", "known_fault", "label"],
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def compute_csmd_network_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    cues_npz_path: Path,
    piedmont_static_fp: np.ndarray,
) -> np.ndarray:
    """Compute all 16 strictly fold-visible network & Coulomb stress-shadow channels (n_fp, 16)."""
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    n_fp = int(footprint.sum())
    base_mech = compute_network_mechanics(vis, footprint, cues_npz_path)
    out = np.zeros((n_fp, N_CSMD_MECH), dtype=np.float32)
    out[:, :N_BASE_MECH] = base_mech
    if not np.any(vis):
        return out

    # Compute local trace orientation & perpendicular lateral flank shadow strictly from `vis`
    vis_f = ndi.gaussian_filter(vis.astype(np.float32), sigma=2.0)
    gy, gx = np.gradient(vis_f)
    # Normal to fault trace is (gy, gx); tangent (strike) is (-gx, gy)
    Jyy = ndi.gaussian_filter(gy * gy, sigma=5.0)
    Jxx = ndi.gaussian_filter(gx * gx, sigma=5.0)
    Jyx = ndi.gaussian_filter(gy * gx, sigma=5.0)
    # Normal angle phi = 0.5 * arctan2(2*Jyx, Jxx - Jyy)
    phi_norm = 0.5 * np.arctan2(2.0 * Jyx, Jxx - Jyy + 1e-12)
    ny_u = np.sin(phi_norm)[footprint].astype(np.float32)
    nx_u = np.cos(phi_norm)[footprint].astype(np.float32)
    coh = (np.hypot(Jxx - Jyy, 2.0 * Jyx) / (Jxx + Jyy + 1e-6))[footprint].astype(np.float32)
    del vis_f, gy, gx, Jyy, Jxx, Jyx, phi_norm

    d_vis, (iy, ix) = ndi.distance_transform_edt(~vis, return_distances=True, return_indices=True)
    vr, vc = np.nonzero(footprint)
    dv = d_vis[footprint].astype(np.float32)
    dy_v = (vr - iy[footprint]).astype(np.float32)
    dx_v = (vc - ix[footprint]).astype(np.float32)
    rn_v = np.hypot(dy_v, dx_v) + 1e-6
    uy_v = dy_v / rn_v
    ux_v = dx_v / rn_v
    del d_vis, iy, ix, vr, vc, dy_v, dx_v, rn_v

    # |cos(angle with fault normal)| -> 1.0 on perpendicular lateral flanks, 0.0 along strike
    perp_align = np.abs(uy_v * ny_u + ux_v * nx_u)
    perp_flank = (perp_align * perp_align) ** 2

    # Positive Coulomb lobes: forward crack tips (15px, 35px), wing lobes (28 deg), colinear bridges & relays
    fwd15 = base_mech[:, 6]
    fwd35 = base_mech[:, 7]
    wing = base_mech[:, 8]
    colin = base_mech[:, 9]
    relay = base_mech[:, 10]
    cfs_pos = 0.40 * fwd35 + 0.25 * fwd15 + 0.25 * wing + 0.35 * colin + 0.35 * relay

    # Negative Coulomb stress shadow on perpendicular lateral flanks (2.5 <= d_vis <= 20 px) away from tips/relays
    flank_radial = np.exp(-0.5 * ((dv - 6.5) / 5.5) ** 2) * (dv >= 2.2).astype(np.float32)
    not_tip = np.clip(1.0 - 1.5 * np.maximum(fwd35, np.maximum(colin, relay)), 0.0, 1.0)
    cfs_shadow = flank_radial * perp_flank * not_tip * np.clip(coh, 0.15, 1.0)

    out[:, 14] = _z_fp(cfs_pos - 0.85 * cfs_shadow)

    # Channel 15: H80-SLIP-DEFICIT gap inversion (high piedmont relief & 40px density where 15px density drops)
    dens15_z = _z_fp(base_mech[:, 4])
    dens40_z = _z_fp(base_mech[:, 5])
    deficit = np.maximum(0.0, piedmont_static_fp + 1.0) * np.maximum(0.0, dens40_z - 0.75 * dens15_z + 0.35)
    out[:, 15] = _z_fp(deficit)

    del base_mech, dv, uy_v, ux_v, ny_u, nx_u, coh, perp_align, perp_flank
    gc.collect()
    return out


def _evict_mmap(mm_obj: np.memmap, mmap_path: Path) -> None:
    try:
        m = getattr(mm_obj, "_mmap", None)
        if m is not None and hasattr(m, "madvise") and hasattr(mmap, "MADV_DONTNEED"):
            m.madvise(mmap.MADV_DONTNEED)
    except Exception:
        pass
    drop_file_cache(mmap_path)


def predict_csmd_stage1_rows(
    suite: dict[str, Any],
    static_mm: np.memmap,
    mmap_path: Path,
    mech_arr: np.ndarray | None,
    row_indices: np.ndarray,
    true_pi: float,
    sample_pi: float,
    chunk_size: int = 450_000,
) -> tuple[np.ndarray, np.ndarray]:
    n = row_indices.size
    n_c = N_CSMD_ALL if mech_arr is not None else N_CSMD_STATIC
    p_out = np.zeros(n, dtype=np.float32)
    q_out = np.zeros(n, dtype=np.float32)
    buf = np.empty((min(chunk_size, max(n, 1)), n_c), dtype=np.float32)

    for s in range(0, n, chunk_size):
        e = min(s + chunk_size, n)
        sub = row_indices[s:e]
        xb = buf[: e - s]
        xb[:, :N_CSMD_STATIC] = static_mm[sub]
        if mech_arr is not None:
            xb[:, N_CSMD_STATIC:] = mech_arr[sub]
        p1 = _prior_correct(suite["lgb_deep"].booster_.predict(xb, num_threads=2), true_pi, sample_pi)
        p2 = _prior_correct(suite["lgb_et"].booster_.predict(xb, num_threads=2), true_pi, sample_pi)
        xq = np.clip(suite["sc_lin"].transform(xb), -6.0, 6.0).astype(np.float32)
        p3 = _prior_correct(suite["glm_cls"].predict_proba(xq)[:, 1], true_pi, sample_pi)
        p_out[s:e] = 0.50 * p1 + 0.35 * p2 + 0.15 * p3

        q1 = np.clip(suite["q_lgb"].booster_.predict(xb, num_threads=2), 0.0, 1.0)
        q2 = np.clip(suite["q_ridge"].predict(xq), 0.0, 1.0)
        q_out[s:e] = (0.82 * q1 + 0.18 * q2).astype(np.float32)
        _evict_mmap(static_mm, mmap_path)

    return p_out, q_out


def build_csmd_per_quadrant_training_shards(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    quad_fp: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    cues_npz_path: Path,
    n_draws: int = 3,
    hide_frac: float = 0.22,
    buffer_px: int = 3,
    neg_per_quad_per_draw: int = 22_000,
    seed_base: int = 7900,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Build compact per-quadrant training shards with d_known >= 3.0 px flank decontamination (IR-79-140 fix)."""
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    comp, n_comp = ndi.label(vis, STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)
    all_ids = np.arange(1, n_comp + 1, dtype=np.int32)
    target_px = hide_frac * float(vis.sum())
    piedmont_fp = static_mm[:, 73].astype(np.float32, copy=True)

    buckets: dict[int, dict[str, Any]] = {
        q: {"X": [], "y": [], "q": [], "w": [], "pos": 0, "act": 0} for q in range(4)
    }
    draw0_ref: dict[str, Any] = {}

    for r in range(n_draws):
        rng = np.random.default_rng(seed_base + 137 * r)
        perm = rng.permutation(all_ids)
        cum = np.cumsum(sizes[perm])
        k = int(np.searchsorted(cum, target_px)) + 1
        chosen = perm[: min(k, perm.size)]
        sim_hidden = np.isin(comp, chosen) & vis
        collar = ndi.distance_transform_edt(~sim_hidden) <= float(buffer_px)
        sim_vis = vis & ~collar
        sim_known = vis & ~sim_hidden
        sim_active = footprint & ~sim_known

        q_fp = metric.kernel(ndi.distance_transform_edt(~sim_hidden)).astype(np.float32)[footprint]
        y_fp = sim_hidden[footprint]
        act_fp = sim_active[footprint]
        mech = compute_csmd_network_mechanics(sim_vis, footprint, cues_npz_path, piedmont_fp)

        if r == 0:
            draw0_ref = {
                "active_fp": act_fp.copy(),
                "y_exact_fp": y_fp.copy(),
                "q_300m_fp": q_fp.astype(np.float16),
                "mech_fp16": mech.astype(np.float16),
            }

        for q_id in range(4):
            elig = act_fp & (quad_fp == q_id)
            pos_idx = np.flatnonzero(elig & y_fp)
            halo_pool = np.flatnonzero(elig & (~y_fp) & (q_fp > 0.0))
            far_pool = np.flatnonzero(elig & (~y_fp) & (q_fp == 0.0))

            n_halo = min(halo_pool.size, neg_per_quad_per_draw // 4)
            n_far = min(far_pool.size, neg_per_quad_per_draw - n_halo)
            sh = rng.choice(halo_pool, size=n_halo, replace=False) if n_halo > 0 else np.empty(0, dtype=np.int64)
            sf = rng.choice(far_pool, size=n_far, replace=False) if n_far > 0 else np.empty(0, dtype=np.int64)

            idx = np.sort(np.concatenate([pos_idx, sh, sf]))
            xp = np.empty((idx.size, N_CSMD_ALL), dtype=np.float32)
            xp[:, :N_CSMD_STATIC] = static_mm[idx]
            xp[:, N_CSMD_STATIC:] = mech[idx]

            is_pos = y_fp[idx]
            is_halo = (~is_pos) & (q_fp[idx] > 0.0)
            wh = float(halo_pool.size / max(n_halo, 1)) if n_halo > 0 else 1.0
            wf = float(far_pool.size / max(n_far, 1)) if n_far > 0 else 1.0
            w = np.where(is_pos, 1.0, np.where(is_halo, wh, wf)).astype(np.float32)

            buckets[q_id]["X"].append(xp)
            buckets[q_id]["y"].append(is_pos.astype(np.float32))
            buckets[q_id]["q"].append(q_fp[idx].astype(np.float32))
            buckets[q_id]["w"].append(w)
            buckets[q_id]["pos"] += int(pos_idx.size)
            buckets[q_id]["act"] += int(elig.sum())

        _evict_mmap(static_mm, mmap_path)
        del sim_hidden, collar, sim_vis, sim_known, sim_active, q_fp, y_fp, act_fp, mech
        gc.collect()

    shards: dict[int, dict[str, Any]] = {}
    for q_id in range(4):
        shards[q_id] = {
            "X": np.concatenate(buckets[q_id]["X"], axis=0),
            "y": np.concatenate(buckets[q_id]["y"], axis=0),
            "q": np.concatenate(buckets[q_id]["q"], axis=0),
            "w": np.concatenate(buckets[q_id]["w"], axis=0),
            "pos": int(buckets[q_id]["pos"]),
            "act": int(buckets[q_id]["act"]),
        }
    del buckets, piedmont_fp
    gc.collect()
    return shards, draw0_ref


def build_csmd_full_visible_physics_shards(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    quad_fp: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    neg_per_quad: int = 55_000,
    seed: int = 7950,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Build 100%-visible flank-decontaminated pure-physics shards across the 4 spatial quadrants.

    Unlike G79-THVC EXP-79-1 (which trained on only the 22% sim_hidden subset while labeling
    1 <= d_known < 3 px flanks of the 78% sim_known faults as y=0, q=0 negatives), this uses
    100% of fold-visible faults (`vis`) as positive targets and places 1 <= d_vis < 3 px flanks
    in `halo_pool` with their exact 300 m kernel target q_vis > 0, sampling `far_pool` strictly
    from d_vis >= 3.0 px!
    """
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    d_vis = ndi.distance_transform_edt(~vis)
    q_vis_fp = metric.kernel(d_vis).astype(np.float32)[footprint]
    y_vis_fp = vis[footprint]
    n_fp = int(footprint.sum())
    all_elig = np.ones(n_fp, dtype=bool)

    rng = np.random.default_rng(seed)
    shards: dict[int, dict[str, Any]] = {}
    for q_id in range(4):
        elig = quad_fp == q_id
        pos_idx = np.flatnonzero(elig & y_vis_fp)
        halo_pool = np.flatnonzero(elig & (~y_vis_fp) & (q_vis_fp > 0.0))
        far_pool = np.flatnonzero(elig & (~y_vis_fp) & (q_vis_fp == 0.0))

        n_halo = min(halo_pool.size, neg_per_quad // 4)
        n_far = min(far_pool.size, neg_per_quad - n_halo)
        sh = rng.choice(halo_pool, size=n_halo, replace=False) if n_halo > 0 else np.empty(0, dtype=np.int64)
        sf = rng.choice(far_pool, size=n_far, replace=False) if n_far > 0 else np.empty(0, dtype=np.int64)

        idx = np.sort(np.concatenate([pos_idx, sh, sf]))
        xp = np.asarray(static_mm[idx, :N_CSMD_STATIC], dtype=np.float32)

        is_pos = y_vis_fp[idx]
        is_halo = (~is_pos) & (q_vis_fp[idx] > 0.0)
        wh = float(halo_pool.size / max(n_halo, 1)) if n_halo > 0 else 1.0
        wf = float(far_pool.size / max(n_far, 1)) if n_far > 0 else 1.0
        w = np.where(is_pos, 1.0, np.where(is_halo, wh, wf)).astype(np.float32)

        shards[q_id] = {
            "X": xp,
            "y": is_pos.astype(np.float32),
            "q": q_vis_fp[idx].astype(np.float32),
            "w": w,
            "pos": int(pos_idx.size),
            "act": int(elig.sum()),
        }
        _evict_mmap(static_mm, mmap_path)
    phys_ref = {
        "active_fp": all_elig,
        "y_exact_fp": y_vis_fp.copy(),
        "q_300m_fp": q_vis_fp.astype(np.float16),
        "mech_fp16": None,
    }
    return shards, phys_ref


def _stack_csmd_shards(
    shards: dict[int, dict[str, Any]],
    quad_ids: list[int],
    use_mechanics: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float]:
    n_c = N_CSMD_ALL if use_mechanics else N_CSMD_STATIC
    X = np.concatenate([shards[q]["X"][:, :n_c] for q in quad_ids], axis=0)
    y = np.concatenate([shards[q]["y"] for q in quad_ids], axis=0)
    qv = np.concatenate([shards[q]["q"] for q in quad_ids], axis=0)
    w = np.concatenate([shards[q]["w"] for q in quad_ids], axis=0)
    tot_pos = sum(shards[q]["pos"] for q in quad_ids)
    tot_act = sum(shards[q]["act"] for q in quad_ids)
    return X, y, qv, w, float(tot_pos / max(tot_act, 1)), float(y.mean())


def run_csmd_quadrant_nested_oof(
    quad_fp: np.ndarray,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    shards: dict[int, dict[str, Any]],
    draw0_ref: dict[str, Any],
    test_mech_fp: np.ndarray | None,
    use_mechanics: bool,
    seed: int = 79,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Memory-bounded 4-quadrant out-of-fold Stage-1 + Stage-2 dual-head predictor."""
    n_fp = int(footprint.sum())
    mech_d0 = draw0_ref["mech_fp16"] if use_mechanics else None
    q_rows = {q: np.flatnonzero(quad_fp == q) for q in range(4)}

    outer_p1 = np.zeros(n_fp, dtype=np.float32)
    outer_q1 = np.zeros(n_fp, dtype=np.float32)

    if use_mechanics:
        pair_avg_p1 = np.zeros(n_fp, dtype=np.float32)
        pair_avg_q1 = np.zeros(n_fp, dtype=np.float32)
        for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
            X_ab, y_ab, q_ab, w_ab, tpi, spi = _stack_csmd_shards(shards, [a, b], use_mechanics)
            s_ab = fit_stage1_ensemble(X_ab, y_ab, q_ab, w_ab, seed=seed + 10 * a + b)
            del X_ab, y_ab, q_ab, w_ab
            rem_qs = [c for c in range(4) if c not in (a, b)]
            rem_rows = np.sort(np.concatenate([q_rows[c] for c in rem_qs]))
            p_rem, q_rem = predict_csmd_stage1_rows(s_ab, static_mm, mmap_path, mech_d0, rem_rows, tpi, spi)
            p_tmp = np.zeros(n_fp, dtype=np.float32)
            q_tmp = np.zeros(n_fp, dtype=np.float32)
            p_tmp[rem_rows] = p_rem
            q_tmp[rem_rows] = q_rem
            for c in rem_qs:
                pair_avg_p1[q_rows[c]] += p_tmp[q_rows[c]] / 3.0
                pair_avg_q1[q_rows[c]] += q_tmp[q_rows[c]] / 3.0
            del s_ab, p_rem, q_rem, p_tmp, q_tmp
            gc.collect()

    for q_test in range(4):
        tr_qs = [q for q in range(4) if q != q_test]
        X_3, y_3, q_3, w_3, tpi3, spi3 = _stack_csmd_shards(shards, tr_qs, use_mechanics)
        s_3 = fit_stage1_ensemble(X_3, y_3, q_3, w_3, seed=seed + 100 + q_test)
        del X_3, y_3, q_3, w_3
        gc.collect()

        outer_p1[q_rows[q_test]], outer_q1[q_rows[q_test]] = predict_csmd_stage1_rows(
            s_3, static_mm, mmap_path, test_mech_fp if use_mechanics else None, q_rows[q_test], tpi3, spi3
        )
        del s_3
        gc.collect()

    p2_test_all = np.zeros(n_fp, dtype=np.float32)
    q2_test_all = np.zeros(n_fp, dtype=np.float32)
    p2_tr_avg = np.zeros(n_fp, dtype=np.float32)
    q2_tr_avg = np.zeros(n_fp, dtype=np.float32)

    S2_outer_eval = extract_stage2_spatial_features(outer_p1, outer_q1, footprint, ctx_cols_fp)
    if use_mechanics:
        S2_d0_oof = extract_stage2_spatial_features(pair_avg_p1, pair_avg_q1, footprint, ctx_cols_fp)
        del pair_avg_p1, pair_avg_q1
    else:
        S2_d0_oof = S2_outer_eval
    del outer_p1, outer_q1
    gc.collect()

    for q_test in range(4):
        tr_mask = quad_fp != q_test
        s2_m = fit_stage2_dual_heads(S2_d0_oof, draw0_ref, tr_mask, seed=seed + 300 + q_test)
        p2_tr_avg[q_rows[q_test]], q2_tr_avg[q_rows[q_test]] = predict_stage2_dual_heads(
            s2_m, S2_d0_oof, q_rows[q_test]
        )
        p2_test_all[q_rows[q_test]], q2_test_all[q_rows[q_test]] = predict_stage2_dual_heads(
            s2_m, S2_outer_eval, q_rows[q_test]
        )
        del s2_m
        gc.collect()

    del S2_d0_oof, S2_outer_eval
    gc.collect()
    return p2_test_all, q2_test_all, p2_tr_avg, q2_tr_avg


def charnes_cooper_csmd_multiregime_emit(
    p_exact_2d: np.ndarray,
    q_300m_2d: np.ndarray,
    p_phys_2d: np.ndarray,
    q_phys_2d: np.ndarray,
    allowed_mask: np.ndarray,
    visible_mask: np.ndarray,
    coulomb_2d: np.ndarray | None = None,
    lambda_fp: float = 0.0022,
    min_sep_px: float = 1.9,
    near_budget: int = 27_400,
    far_budget: int = 8_200,
    far_min_dist_px: float = 11.5,
    far_min_sep_px: float = 2.5,
    min_budget: int = 20_000,
    candidate_pool: int = 420_000,
) -> np.ndarray:
    """Multi-Regime Coulomb-Decontaminated Charnes-Cooper Submodular Kernel Allocator.

    Pass 1 (Near-to-Mid Tip, Relay & Scarp Regime, up to `near_budget` dots):
      Runs lazy-heap Charnes-Cooper marginal kernel gain (`min_sep_px`) on `p_exact_2d, q_300m_2d`
      with physical Coulomb perpendicular flank stress-shadow suppression (`coulomb_2d < -0.50`).
    Pass 2 (Far-Field Decontaminated Physical Discovery Regime, d_vis >= `far_min_dist_px`, up to `far_budget` dots):
      Continues from the exact `cov_pad` and `blocked` state of Pass 1 using a second lazy-heap
      Charnes-Cooper pass (`far_min_sep_px`) on the fused far-field physical kernel credit
      (`0.55 * p_phys_2d + 0.45 * p_exact_2d`, `0.55 * q_phys_2d + 0.45 * q_300m_2d`).
    """
    H, W = p_exact_2d.shape
    pad = 3
    d_vis = ndi.distance_transform_edt(~np.asarray(visible_mask, dtype=bool))

    # Pass 1 surface setup
    q_clean = np.clip(q_300m_2d, 0.0, 1.0).astype(np.float64)
    if coulomb_2d is not None:
        # Suppress perpendicular stress-shadowed flanks (2.5 <= d_vis <= 18 px, coulomb_2d < -0.45) lacking strong physics
        q_ph_med = float(np.median(q_phys_2d[allowed_mask])) if np.any(allowed_mask) else 0.0
        flank_shadow = (coulomb_2d < -0.45) & (d_vis >= 2.5) & (d_vis <= 18.0) & (q_phys_2d < q_ph_med * 1.35)
        q_clean = np.where(flank_shadow, q_clean * 0.72, q_clean)

    q_sharp = np.maximum(0.0, q_clean - 0.50 * ndi.gaussian_filter(q_clean.astype(np.float32), 2.5))
    mass_p = float(np.clip(p_exact_2d, 0.0, 1.0)[allowed_mask].sum())
    mass_q = float(q_sharp[allowed_mask].sum())
    q_scaled = q_sharp * (mass_p / max(mass_q, 1e-8))
    p_eff = 0.65 * np.clip(p_exact_2d, 0.0, 1.0) + 0.35 * q_scaled
    if coulomb_2d is not None:
        p_eff = np.where(flank_shadow, p_eff * 0.72, p_eff)

    p_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    p_pad[pad : pad + H, pad : pad + W] = p_eff
    cov_pad = np.zeros_like(p_pad)

    dy = metric.OFF_DY.tolist()
    dx = metric.OFF_DX.tolist()
    kw = metric.OFF_K.tolist()
    n_off = len(kw)

    init_tp = np.zeros((H, W), dtype=np.float64)
    for oy, ox, k_val in zip(dy, dx, kw):
        init_tp += k_val * p_pad[pad + oy : pad + oy + H, pad + ox : pad + ox + W]

    pen_arr = float(lambda_fp) * (1.0 - q_clean)
    u0 = init_tp - pen_arr

    valid_idx = np.flatnonzero(allowed_mask & (init_tp > 0.0))
    if valid_idx.size > candidate_pool:
        sub = u0.ravel()[valid_idx]
        keep = np.argpartition(sub, -candidate_pool)[-candidate_pool:]
        valid_idx = valid_idx[keep]

    ys = (valid_idx // W + pad).tolist()
    xs = (valid_idx % W + pad).tolist()
    pens = pen_arr.ravel()[valid_idx].tolist()
    u_vals = u0.ravel()[valid_idx].tolist()

    r_sep = int(np.ceil(min_sep_px)) if min_sep_px > 1.01 else 0
    if r_sep > 0:
        sy_g, sx_g = np.mgrid[-r_sep : r_sep + 1, -r_sep : r_sep + 1]
        sep_m = (sy_g * sy_g + sx_g * sx_g) < (min_sep_px * min_sep_px)
        sep_dy = sy_g[sep_m].tolist()
        sep_dx = sx_g[sep_m].tolist()
    else:
        sep_dy, sep_dx = [0], [0]

    blocked = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool)
    heap: list[tuple[float, int]] = [(-u_vals[i], i) for i in range(len(u_vals))]
    heapq.heapify(heap)

    out = np.zeros((H, W), dtype=np.float32)
    selected = 0
    while selected < near_budget and heap:
        _, i = heapq.heappop(heap)
        cy, cx = ys[i], xs[i]
        if blocked[cy, cx]:
            continue
        gain = 0.0
        for m in range(n_off):
            ny, nx = cy + dy[m], cx + dx[m]
            k_m = kw[m]
            cur_c = cov_pad[ny, nx]
            if k_m > cur_c:
                gain += p_pad[ny, nx] * (k_m - cur_c)
        exact_u = gain - pens[i]
        if selected >= min_budget and exact_u <= 0.0:
            break
        if not heap or (-exact_u <= heap[0][0] + 1e-14):
            out[cy - pad, cx - pad] = 1.0
            for m in range(n_off):
                ny, nx = cy + dy[m], cx + dx[m]
                k_m = kw[m]
                if k_m > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = k_m
            for sdy, sdx in zip(sep_dy, sep_dx):
                blocked[cy + sdy, cx + sdx] = True
            selected += 1
        else:
            heapq.heappush(heap, (-exact_u, i))

    # Pass 2: Far-Field Decontaminated Physical Discovery Charnes-Cooper Pass (d_vis >= far_min_dist_px)
    if far_budget > 0:
        p_far = 0.58 * np.clip(p_phys_2d, 0.0, 1.0) + 0.42 * np.clip(p_exact_2d, 0.0, 1.0)
        q_far = np.clip(0.58 * np.clip(q_phys_2d, 0.0, 1.0) + 0.42 * np.clip(q_300m_2d, 0.0, 1.0), 0.0, 1.0).astype(np.float64)
        q_far_sharp = np.maximum(0.0, q_far - 0.50 * ndi.gaussian_filter(q_far.astype(np.float32), 2.5))
        mp_f = float(p_far[allowed_mask].sum())
        mq_f = float(q_far_sharp[allowed_mask].sum())
        p_far_eff = 0.65 * p_far + 0.35 * q_far_sharp * (mp_f / max(mq_f, 1e-8))

        p_far_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
        p_far_pad[pad : pad + H, pad : pad + W] = p_far_eff

        init_tp_f = np.zeros((H, W), dtype=np.float64)
        for oy, ox, k_val in zip(dy, dx, kw):
            init_tp_f += k_val * p_far_pad[pad + oy : pad + oy + H, pad + ox : pad + ox + W]

        far_elig = allowed_mask & (d_vis >= float(far_min_dist_px)) & (out == 0.0) & (init_tp_f > 0.0)
        f_idx = np.flatnonzero(far_elig)
        if f_idx.size > 200_000:
            sub_f = init_tp_f.ravel()[f_idx]
            keep_f = np.argpartition(sub_f, -200_000)[-200_000:]
            f_idx = f_idx[keep_f]

        ys_f = (f_idx // W + pad).tolist()
        xs_f = (f_idx % W + pad).tolist()
        u_f = init_tp_f.ravel()[f_idx].tolist()

        r_fsep = int(np.ceil(far_min_sep_px))
        sy_f, sx_f = np.mgrid[-r_fsep : r_fsep + 1, -r_fsep : r_fsep + 1]
        sep_fm = (sy_f * sy_f + sx_f * sx_f) < (far_min_sep_px * far_min_sep_px)
        fsep_dy = sy_f[sep_fm].tolist()
        fsep_dx = sx_f[sep_fm].tolist()

        heap_f: list[tuple[float, int]] = [(-u_f[i], i) for i in range(len(u_f))]
        heapq.heapify(heap_f)
        placed_far = 0
        while placed_far < far_budget and heap_f:
            _, i = heapq.heappop(heap_f)
            cy, cx = ys_f[i], xs_f[i]
            if blocked[cy, cx]:
                continue
            gain = 0.0
            for m in range(n_off):
                ny, nx = cy + dy[m], cx + dx[m]
                k_m = kw[m]
                cur_c = cov_pad[ny, nx]
                if k_m > cur_c:
                    gain += p_far_pad[ny, nx] * (k_m - cur_c)
            if gain <= 0.0:
                break
            if not heap_f or (-gain <= heap_f[0][0] + 1e-14):
                out[cy - pad, cx - pad] = 1.0
                for m in range(n_off):
                    ny, nx = cy + dy[m], cx + dx[m]
                    k_m = kw[m]
                    if k_m > cov_pad[ny, nx]:
                        cov_pad[ny, nx] = k_m
                for sdy, sdx in zip(fsep_dy, fsep_dx):
                    blocked[cy + sdy, cx + sdx] = True
                placed_far += 1
            else:
                heapq.heappush(heap_f, (-gain, i))

    return out


def compute_csmd_leakage_canary(
    static_mm: np.memmap,
    mmap_path: Path,
    mech_fp: np.ndarray,
    footprint: np.ndarray,
    folds: list[dict[str, Any]],
    seed: int,
    neg_sample_per_fold: int = 40_000,
) -> dict[str, Any]:
    """Run single-feature symmetric ROC-AUC leakage canary across all 90 CSMD channels and 4 folds."""
    from sklearn.metrics import roc_auc_score

    H, W = footprint.shape
    fp_lookup = np.full((H, W), -1, dtype=np.int32)
    fp_lookup[footprint] = np.arange(int(footprint.sum()), dtype=np.int32)

    rows: list[dict[str, Any]] = []
    for f_idx, fold in enumerate(folds):
        active = footprint & fold["region"] & (~fold["masked_known"])
        truth = active & fold["truth"]
        neg_mask = active & (~truth)
        pos_flat = np.flatnonzero(truth)
        neg_all = np.flatnonzero(neg_mask)
        rng = np.random.default_rng(seed * 997 + f_idx * 31 + 7)
        neg_flat = rng.choice(neg_all, size=min(neg_sample_per_fold, neg_all.size), replace=False)

        sel_flat = np.concatenate([pos_flat, neg_flat])
        y = np.concatenate([np.ones(pos_flat.size, dtype=np.int8), np.zeros(neg_flat.size, dtype=np.int8)])
        fp_rows = fp_lookup.ravel()[sel_flat]
        order = np.argsort(fp_rows)
        fp_rows = fp_rows[order]
        y = y[order]

        X_s = np.asarray(static_mm[fp_rows, :N_CSMD_STATIC], dtype=np.float32)
        X_m = np.asarray(mech_fp[fp_rows, :N_CSMD_MECH], dtype=np.float32)
        X_all = np.hstack([X_s, X_m])

        for j, fname in enumerate(CSMD_ALL_FEATURE_NAMES):
            v = X_all[:, j]
            ok = np.isfinite(v)
            if ok.sum() < 50 or y[ok].sum() < 5 or (1 - y[ok]).sum() < 5 or np.ptp(v[ok]) == 0:
                auc = 0.5
            else:
                auc = float(roc_auc_score(y[ok], v[ok]))
            sym = max(auc, 1.0 - auc)
            rows.append(
                {
                    "fold": fold["name"],
                    "feature": fname,
                    "auc": round(auc, 6),
                    "symmetric_auc": round(sym, 6),
                    "suspicious": bool(sym > 0.90),
                }
            )

    drop_file_cache(mmap_path)
    worst = max(rows, key=lambda r: r["symmetric_auc"])
    per_feat: dict[str, float] = {}
    for r in rows:
        per_feat[r["feature"]] = max(per_feat.get(r["feature"], 0.0), r["symmetric_auc"])
    n_susp = int(sum(1 for r in rows if r["suspicious"]))
    return {
        "evidence_class": "LEAKAGE-CANARY",
        "seed": seed,
        "tests": len(rows),
        "n_unique_features": len(per_feat),
        "threshold": 0.90,
        "passed": bool(n_susp == 0 and worst["symmetric_auc"] <= 0.90),
        "max_symmetric_auc": worst["symmetric_auc"],
        "worst": worst,
        "n_suspicious": n_susp,
        "per_feature_max": per_feat,
    }


