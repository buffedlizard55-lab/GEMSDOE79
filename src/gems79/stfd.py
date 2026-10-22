"""G79-STFD: Seismo-Tectonic Fluid-Strain, Survey-Propensity Debiased Multi-Physics,
Throw-Polarized Hanging-Wall Mechanics, and Self-Consistent Fractional Dinkelbach Discovery.

Preregistration: ``registry/preregistration_g79_stfd.json``
Locked SHA-256:  ``4d62ae4c25c638fe5e24a40f279623e05c995503a1684cb81f47f56ce4e90a75``

Strict scientific & engineering invariants:
  1. Zero access to any prior prediction raster from ``registry/``, ``archive/``, or ``docs/downloads/``.
  2. Strict 4-fold Leave-One-Quadrant-Out (``LOQO``) spatial blocking on all holdout evaluations:
     held-out quadrant pixels never enter Stage-1, Stage-2, pure-physics OOF, or Dinkelbach tuning.
  3. Zero geographic split leakage: cross-quadrant regional elevation ``abs_elev_km`` and binary
     survey block flag ``geodawn_area1_hires`` are excluded from the feature matrix and replaced by
     domain-invariant local operators (``piedmont_rel_height_4km``, ``piedmont_break_curvature``,
     within-``acq_id`` Gaussian rank-normal gradients, and ``lidar_present``-stratified scarp quantiles).
  4. Strict memory hygiene for 3.8 GiB zero-swap hosts: explicit ``MADV_DONTNEED`` / ``POSIX_FADV_DONTNEED``
     page-cache eviction after every memmap pass.
"""
from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.special import ndtri
from scipy.stats import rankdata

from gems57 import metric, network
from gems79.cskd import (
    CSKD_MECH_NAMES,
    CSKD_STATIC_NAMES,
    _infill_2d_sentinels,
    _release_mm,
    build_cskd_static_memmaps,
    compute_cskd_mechanics,
)
from gems79.lifecycle import LaneClosedError
from gems79.thvc_features import STATIC_FEATURE_NAMES, TF_BAND_NAMES, rss_mb
from gems79.thvc_model import (
    _prior_correct,
    _sparse_line_integral,
    fit_stage1_ensemble,
    fit_stage2_dual_heads,
    predict_stage2_dual_heads,
)

STRUCT3 = np.ones((3, 3), dtype=np.int8)

# Retain all 70 THVC static features + 12 domain-invariant CSKD physical deconfounders
# (dropping index 70 = geodawn_area1_hires and index 75 = abs_elev_km which encode NW vs SE geography).
_DROPPED_CSKD_GEOGRAPHIC = frozenset({"geodawn_area1_hires", "abs_elev_km"})
STFD_RETAINED_CSKD_INDICES: tuple[int, ...] = tuple(
    i for i, name in enumerate(CSKD_STATIC_NAMES) if name not in _DROPPED_CSKD_GEOGRAPHIC
)

STFD_NEW_STATIC_NAMES = [
    "seis_swarm_log_excess",
    "seis_swarm_fraction",
    "geod_transtension_obliquity",
    "seis_swarm_x_transtension",
    "seis_deq_grad_boundary",
    "piedmont_rel_height_4km",
    "piedmont_break_curvature",
    "rtp_hgm_block_qnorm",
    "grav_hgm_block_qnorm",
    "scarp_modality_qnorm",
    "grav_bdepth_concordance",
    "scarp_throw_polarity_match",
    "lidar_strike_x_grav_align",
    "cond_conduit_grad_300m",
    "clean_shoreline_mine_road_veto",
]

STFD_STATIC_NAMES: list[str] = [CSKD_STATIC_NAMES[i] for i in STFD_RETAINED_CSKD_INDICES] + STFD_NEW_STATIC_NAMES

STFD_NEW_MECH_NAMES = [
    "net_hangingwall_dip_proj",
    "net_tip_x_swarm_strain",
    "net_piedmont_slip_deficit",
    "net_junction_hydro_conduit",
]

STFD_MECH_NAMES: list[str] = list(CSKD_MECH_NAMES) + STFD_NEW_MECH_NAMES
STFD_ALL_FEATURE_NAMES: list[str] = STFD_STATIC_NAMES + STFD_MECH_NAMES

N_STFD_STATIC = len(STFD_STATIC_NAMES)  # 97
N_STFD_MECH = len(STFD_MECH_NAMES)      # 22
N_STFD_ALL = len(STFD_ALL_FEATURE_NAMES)  # 119

assert len(STFD_RETAINED_CSKD_INDICES) == 82
assert N_STFD_STATIC == 97
assert N_STFD_MECH == 22
assert N_STFD_ALL == 119
assert len(set(STFD_ALL_FEATURE_NAMES)) == 119


def require_open_stfd_lane(root: Path, *, reason: str | None = None) -> None:
    """Fail-closed lifecycle guard on ``run_card_stfd.json`` without mutating ``run_card.json``."""
    extra = f" ({reason})" if reason else ""
    rc_path = Path(root) / "run_card_stfd.json"
    try:
        card = json.loads(rc_path.read_text())
    except (OSError, ValueError) as exc:
        raise LaneClosedError(f"G79-STFD: cannot establish open lane{extra}; no files changed") from exc
    if not isinstance(card, dict) or card.get("lane") != "G79-STFD":
        raise LaneClosedError(f"G79-STFD: mismatched run card{extra}; no files changed")
    if card.get("verdict") not in ("pending", "in_progress") or card.get("stop_reason") or card.get("stopped") is True:
        raise LaneClosedError(
            f"G79-STFD: lane is closed ({card.get('verdict', 'unknown')}){extra}; "
            "do not restart, retune, or repackage it. Audit frozen evidence instead."
        )


def _group_rank_gauss(values_fp: np.ndarray, groups_fp: np.ndarray) -> np.ndarray:
    """Exact within-group Gaussian rank-normal transform on footprint pixels, bounded to [-4, 4]."""
    out = np.zeros(values_fp.shape[0], dtype=np.float32)
    vals = np.nan_to_num(np.asarray(values_fp, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    for g in np.unique(groups_fp):
        m = groups_fp == g
        n = int(m.sum())
        if n <= 2:
            continue
        u = (rankdata(vals[m], method="average") - 0.5) / float(n)
        u = np.clip(u, 1e-4, 1.0 - 1e-4)
        out[m] = np.clip(ndtri(u), -4.0, 4.0).astype(np.float32)
    return out


def _unit_rank_01(values_fp: np.ndarray) -> np.ndarray:
    vals = np.nan_to_num(np.asarray(values_fp, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    n = vals.size
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    return ((rankdata(vals, method="average") - 0.5) / float(n)).astype(np.float32)


def build_stfd_static_memmap(
    root: Path,
    cskd_cache_dir: Path,
    out_mmap_path: Path,
    stfd_cues_path: Path,
    footprint: np.ndarray,
    transform: Any,
) -> tuple[np.memmap, Path]:
    """Build or reload the 97-channel domain-debiased pure-physics float32 memmap."""
    n_fp = int(footprint.sum())
    out_mmap_path.parent.mkdir(parents=True, exist_ok=True)
    cskd_mmap_path = cskd_cache_dir / "cskd_static_fp84.f32.mmap"
    cskd_cues_path = cskd_mmap_path.with_suffix(".cues.npz")
    if (
        out_mmap_path.exists()
        and out_mmap_path.stat().st_size == n_fp * N_STFD_STATIC * 4
        and stfd_cues_path.exists()
        and cskd_cues_path.exists()
    ):
        return np.memmap(out_mmap_path, dtype=np.float32, mode="r", shape=(n_fp, N_STFD_STATIC)), cskd_cues_path

    print(f"[stfd] Building 97-ch domain-debiased static memmap -> {out_mmap_path} (RSS={rss_mb():.0f} MB)", flush=True)
    build_cskd_static_memmaps(
        raw_dir=root / "data/raw",
        ing_dir=root / ".cache/official_ing",
        cskd_src_dir=root / ".cache/cskd_sources",
        cache_dir=cskd_cache_dir,
        footprint=footprint,
        transform=transform,
    )
    cskd_mm = np.memmap(cskd_mmap_path, dtype=np.float32, mode="r", shape=(n_fp, len(CSKD_STATIC_NAMES)))

    idx_shore = CSKD_STATIC_NAMES.index("lahontan_shoreline_veto")
    idx_mine = CSKD_STATIC_NAMES.index("blm_mine_prox_350m")
    idx_road = STATIC_FEATURE_NAMES.index("road_proximity_confound")
    idx_rtp_notched = CSKD_STATIC_NAMES.index("rtp_flight_notched_hgm")
    idx_grav_hgm = STATIC_FEATURE_NAMES.index("grav_hgm_z200")
    idx_rad_kd = CSKD_STATIC_NAMES.index("rad_kd_clean_conduit")
    idx_lidar_pres = STATIC_FEATURE_NAMES.index("lidar_present")
    idx_scarp_clean = CSKD_STATIC_NAMES.index("scarp_lahontan_mine_clean")

    shore_fp = np.empty(n_fp, dtype=np.float32)
    mine_fp = np.empty(n_fp, dtype=np.float32)
    road_fp = np.empty(n_fp, dtype=np.float32)
    rtp_hgm_fp = np.empty(n_fp, dtype=np.float32)
    grav_hgm_fp = np.empty(n_fp, dtype=np.float32)
    rad_kd_fp = np.empty(n_fp, dtype=np.float32)
    lidar_pres_fp = np.empty(n_fp, dtype=np.float32)
    scarp_clean_fp = np.empty(n_fp, dtype=np.float32)

    mm = np.memmap(out_mmap_path, dtype=np.float32, mode="w+", shape=(n_fp, N_STFD_STATIC))
    ret_idx = np.asarray(STFD_RETAINED_CSKD_INDICES, dtype=np.int64)
    chunk = 400_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        blk = np.array(cskd_mm[s:e], dtype=np.float32, copy=True)
        mm[s:e, :82] = blk[:, ret_idx]
        shore_fp[s:e] = blk[:, idx_shore]
        mine_fp[s:e] = blk[:, idx_mine]
        road_fp[s:e] = blk[:, idx_road]
        rtp_hgm_fp[s:e] = blk[:, idx_rtp_notched]
        grav_hgm_fp[s:e] = blk[:, idx_grav_hgm]
        rad_kd_fp[s:e] = blk[:, idx_rad_kd]
        lidar_pres_fp[s:e] = blk[:, idx_lidar_pres]
        scarp_clean_fp[s:e] = blk[:, idx_scarp_clean]
        del blk
        mm.flush()
        _release_mm(cskd_mm, cskd_mmap_path)
        _release_mm(mm, out_mmap_path)

    def _clean_tf(ds_obj: Any, bname: str) -> np.ndarray:
        raw = ds_obj.read(TF_BAND_NAMES.index(bname) + 1)
        valid = footprint & np.isfinite(raw) & (np.abs(raw) < 1e10)
        return _infill_2d_sentinels(raw, valid)

    # Read seismo-geodetic, basement-depth, gravity, and conductivity bands from training_features.tif
    tf_path = root / "data/raw/training_features.tif"
    with rasterio.open(tf_path) as ds:
        geod_shear = _clean_tf(ds, "geod_shearrate")
        geod_dil = _clean_tf(ds, "geod_dilaterate")
        deq_2d = np.maximum(_clean_tf(ds, "deq_n100a15"), 0.0)
        ieq_2d = np.maximum(_clean_tf(ds, "ieq_n100a15"), 0.0)
        iso_grav_2d = _clean_tf(ds, "iso_grav_anom")
        bdepth_2d = np.maximum(_clean_tf(ds, "depth_to_base_surf"), 0.0)
        cond_2d = _clean_tf(ds, "cond_surf")

    with rasterio.open(root / ".cache/cskd_sources/geodawn_dem_a2_100m.tif") as ds:
        dem_raw = ds.read(1)
        dem_2d = _infill_2d_sentinels(dem_raw, footprint & np.isfinite(dem_raw) & (dem_raw > -500.0))
        del dem_raw

    with rasterio.open(root / ".cache/cskd_sources/acquisition_block_id_100m.tif") as ds:
        acq_fp = ds.read(1)[footprint].astype(np.int16)

    dem10_onesided_fp = np.load(root / "data/cache/dem10/dem10_onesided3.f32.npy").astype(np.float32)

    with rasterio.open(root / "data/raw/external/lidar_scarp_features_u8.tif") as ds:
        downface_fp = ds.read(6)[footprint].astype(np.float32) / 255.0
        upface_fp = ds.read(7)[footprint].astype(np.float32) / 255.0
        coh100_fp = ds.read(10)[footprint].astype(np.float32) / 255.0
        strike_lid_fp = (ds.read(11)[footprint].astype(np.float32) / 255.0) * np.pi

    unmined_w = np.clip(1.0 - 0.85 * mine_fp, 0.05, 1.0)

    # 1-5: Seismo-geodetic brittle-fluid mesh partitioning (Sibson 1996)
    ieq_fp = ieq_2d[footprint]
    deq_fp = deq_2d[footprint]
    log_ieq_2d = np.log1p(ieq_2d)
    log_deq_2d = np.log1p(deq_2d)
    swarm_excess_fp = ((log_ieq_2d[footprint] - log_deq_2d[footprint]) * unmined_w).astype(np.float32)

    p75_ieq = max(float(np.percentile(ieq_fp[ieq_fp > 0], 75)) if np.any(ieq_fp > 0) else 1.0, 1e-4)
    swarm_frac_fp = (
        (ieq_fp / (ieq_fp + deq_fp + 1e-4)) * np.tanh(ieq_fp / p75_ieq) * unmined_w
    ).astype(np.float32)

    r_dil = _unit_rank_01(np.maximum(geod_dil[footprint], 0.0))
    r_shr = _unit_rank_01(np.maximum(geod_shear[footprint], 0.0))
    geod_transt_fp = ((2.0 * r_dil * r_shr) / (r_dil + r_shr + 1e-4)).astype(np.float32)
    swarm_x_transt_fp = (np.maximum(swarm_excess_fp, 0.0) * geod_transt_fp).astype(np.float32)

    dgy = ndi.gaussian_filter(log_deq_2d, 4.0, order=(1, 0), mode="nearest")
    dgx = ndi.gaussian_filter(log_deq_2d, 4.0, order=(0, 1), mode="nearest")
    seis_grad_fp = np.hypot(dgy, dgx)[footprint].astype(np.float32)
    del ieq_2d, deq_2d, log_ieq_2d, log_deq_2d, dgy, dgx, geod_shear, geod_dil

    # 6-7: Domain-invariant local basin-relative piedmont geometry (zero regional elevation trend)
    dem_base_low = np.minimum(
        ndi.grey_erosion(dem_2d, size=(25, 25)),
        ndi.gaussian_filter(dem_2d, 35.0, mode="nearest"),
    )
    dem_base_smooth = ndi.gaussian_filter(dem_base_low, 12.0, mode="nearest")
    del dem_base_low
    h_rel_m = np.maximum(dem_2d - dem_base_smooth, 0.0)
    del dem_base_smooth
    piedmont_rel_fp = np.clip(h_rel_m[footprint] / 250.0, 0.0, 3.0).astype(np.float32)

    lap_dem = (
        ndi.gaussian_filter(dem_2d, 5.0, order=(2, 0), mode="nearest")
        + ndi.gaussian_filter(dem_2d, 5.0, order=(0, 2), mode="nearest")
    )
    piedmont_break_fp = (
        np.maximum(lap_dem[footprint], 0.0)
        * np.exp(-np.abs(h_rel_m[footprint] - 40.0) / 55.0)
        * np.clip(1.0 - shore_fp, 0.0, 1.0)
    ).astype(np.float32)
    del dem_2d, h_rel_m, lap_dem

    # 8-10: Within-survey-block & within-LiDAR-modality Gaussian quantile normalization
    rtp_qnorm_fp = _group_rank_gauss(rtp_hgm_fp, acq_fp)
    grav_qnorm_fp = _group_rank_gauss(grav_hgm_fp, acq_fp)
    has_lidar = (lidar_pres_fp > 0.5).astype(np.int8)
    raw_mod_scarp = np.where(has_lidar > 0, scarp_clean_fp, dem10_onesided_fp * np.clip(1.0 - shore_fp, 0.0, 1.0))
    scarp_qnorm_fp = _group_rank_gauss(raw_mod_scarp, has_lidar)
    del acq_fp, rtp_hgm_fp, grav_hgm_fp, raw_mod_scarp, has_lidar

    # 11-13: Basement-gravity vector concordance, scarp throw polarity, & strike alignment
    by_2d = ndi.gaussian_filter(bdepth_2d, 3.0, order=(1, 0), mode="nearest").astype(np.float64)
    bx_2d = ndi.gaussian_filter(bdepth_2d, 3.0, order=(0, 1), mode="nearest").astype(np.float64)
    gy_2d = ndi.gaussian_filter(iso_grav_2d, 3.0, order=(1, 0), mode="nearest").astype(np.float64)
    gx_2d = ndi.gaussian_filter(iso_grav_2d, 3.0, order=(0, 1), mode="nearest").astype(np.float64)

    b_mag = np.hypot(by_2d, bx_2d)
    g_mag = np.hypot(gy_2d, gx_2d)
    ub_y = by_2d / (b_mag + 1e-6)
    ub_x = bx_2d / (b_mag + 1e-6)
    ug_y = gy_2d / (g_mag + 1e-6)
    ug_x = gx_2d / (g_mag + 1e-6)
    # Down-dropped alluvial hanging wall => +grad(bdepth) aligns with -grad(iso_grav)
    dot_bg = np.clip(-(ub_y * ug_y + ub_x * ug_x), -1.0, 1.0)
    amp_bg = np.sqrt(_unit_rank_01(b_mag[footprint]) * _unit_rank_01(g_mag[footprint]))
    grav_bdepth_conc_fp = (dot_bg[footprint] * amp_bg).astype(np.float32)

    scarp_pol_fp = (
        ((upface_fp - downface_fp) * np.tanh(b_mag[footprint] / (np.percentile(b_mag[footprint], 75) + 1e-5)))
        * dot_bg[footprint]
    ).astype(np.float32)

    # Gravity contact strike normal is (gy, gx), so contact strike azimuth in image coords is atan2(-gx, gy)
    theta_grav_fp = np.mod(np.arctan2(-gx_2d[footprint], gy_2d[footprint]), np.pi).astype(np.float32)
    lidar_grav_align_fp = (np.abs(np.cos(strike_lid_fp - theta_grav_fp)) * coh100_fp).astype(np.float32)

    # Save hanging-wall unit normal (ub_y, ub_x) & bounded [0, 1] interaction cues for mechanics
    hw_ny_2d = ub_y.astype(np.float16)
    hw_nx_2d = ub_x.astype(np.float16)
    bdepth_km_fp = np.clip(bdepth_2d[footprint] / 1000.0, 0.2, 2.5).astype(np.float16)
    del by_2d, bx_2d, gy_2d, gx_2d, b_mag, g_mag, ub_y, ub_x, ug_y, ug_x, dot_bg, amp_bg, bdepth_2d, iso_grav_2d

    # 14-15: Surface conductivity conduit contrast & unified reliability mask
    cond_res = cond_2d - ndi.gaussian_filter(cond_2d, 15.0, mode="nearest")
    cgy = ndi.gaussian_filter(cond_2d, 3.0, order=(1, 0), mode="nearest")
    cgx = ndi.gaussian_filter(cond_2d, 3.0, order=(0, 1), mode="nearest")
    cond_conduit_fp = (
        (_unit_rank_01(np.maximum(cond_res[footprint], 0.0)) + _unit_rank_01(np.hypot(cgy, cgx)[footprint]))
        * (0.5 + np.maximum(rad_kd_fp, 0.0))
    ).astype(np.float32)
    del cond_2d, cond_res, cgy, cgx

    clean_veto_fp = (
        np.clip(1.0 - 0.85 * shore_fp, 0.05, 1.0)
        * np.clip(1.0 - 0.80 * mine_fp, 0.05, 1.0)
        * np.clip(1.0 - 0.50 * road_fp, 0.15, 1.0)
    ).astype(np.float32)

    new_cols = [
        swarm_excess_fp,
        swarm_frac_fp,
        geod_transt_fp,
        swarm_x_transt_fp,
        seis_grad_fp,
        piedmont_rel_fp,
        piedmont_break_fp,
        rtp_qnorm_fp,
        grav_qnorm_fp,
        scarp_qnorm_fp,
        grav_bdepth_conc_fp,
        scarp_pol_fp,
        lidar_grav_align_fp,
        cond_conduit_fp,
        clean_veto_fp,
    ]
    assert len(new_cols) == len(STFD_NEW_STATIC_NAMES) == 15
    for j, col in enumerate(new_cols):
        mm[:, 82 + j] = np.nan_to_num(col, nan=0.0, posinf=0.0, neginf=0.0)
    mm.flush()

    np.savez_compressed(
        stfd_cues_path,
        cskd_cues_path=str(cskd_cues_path),
        hw_ny_2d=hw_ny_2d,
        hw_nx_2d=hw_nx_2d,
        bdepth_km_fp=bdepth_km_fp,
        swarm_transt_fp=swarm_x_transt_fp.astype(np.float16),
        grav_bdepth_conc_fp=np.maximum(grav_bdepth_conc_fp, 0.0).astype(np.float16),
        rad_kd_pos_fp=np.maximum(rad_kd_fp, 0.0).astype(np.float16),
        scarp_qnorm_fp=scarp_qnorm_fp.astype(np.float16),
        clean_veto_fp=clean_veto_fp.astype(np.float16),
        piedmont_break_fp=piedmont_break_fp.astype(np.float16),
    )
    _release_mm(mm, out_mmap_path)
    gc.collect()
    print(f"[stfd] Completed 97-ch static memmap (RSS={rss_mb():.0f} MB)", flush=True)
    return np.memmap(out_mmap_path, dtype=np.float32, mode="r", shape=(n_fp, N_STFD_STATIC)), cskd_cues_path


def compute_stfd_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    cskd_cues_path: Path,
    stfd_cues_path: Path,
) -> np.ndarray:
    """Compute all 22 fold-visible mechanics channels strictly from ``visible_mask``."""
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    n_fp = int(footprint.sum())
    out = np.zeros((n_fp, N_STFD_MECH), dtype=np.float32)
    if not np.any(vis):
        return out

    base18 = compute_cskd_mechanics(vis, footprint, cskd_cues_path)
    out[:, :18] = base18

    zc = np.load(stfd_cues_path)
    hw_ny_2d = zc["hw_ny_2d"].astype(np.float32)
    hw_nx_2d = zc["hw_nx_2d"].astype(np.float32)
    bdepth_km_fp = zc["bdepth_km_fp"].astype(np.float32)
    swarm_transt_fp = zc["swarm_transt_fp"].astype(np.float32)
    grav_bdepth_conc_fp = zc["grav_bdepth_conc_fp"].astype(np.float32)
    rad_kd_pos_fp = zc["rad_kd_pos_fp"].astype(np.float32)

    # 19: Okada (1992) asymmetric hanging-wall surface projection along +grad(depth_to_base)
    dist_2d, inds = ndi.distance_transform_edt(~vis, return_indices=True)
    yy, xx = np.nonzero(footprint)
    ay = inds[0, yy, xx]
    ax = inds[1, yy, xx]
    dy = (yy - ay).astype(np.float32)
    dx = (xx - ax).astype(np.float32)
    d_fp = dist_2d[yy, xx].astype(np.float32)
    inv_d = 1.0 / np.maximum(d_fp, 1.0)
    cos_hw = (dy * hw_ny_2d[ay, ax] + dx * hw_nx_2d[ay, ax]) * inv_d
    # 55-deg dipping normal fault splay projects ~0.70 * h_sed (7 px per km of basin fill)
    opt_offset_px = 3.5 + 7.0 * bdepth_km_fp
    hw_proj = np.maximum(cos_hw, 0.0) * np.exp(-((d_fp - opt_offset_px) ** 2) / (2.0 * (4.5 + 2.5 * bdepth_km_fp) ** 2))
    out[:, 18] = hw_proj.astype(np.float32)
    del dist_2d, inds, yy, xx, ay, ax, dy, dx, cos_hw, opt_offset_px, hw_proj

    # 20: Crack-tip & relay stepover stress lobe x active microseismic swarm-transtension
    tip_relay = base18[:, CSKD_MECH_NAMES.index("net_tip_fwd_35px")] + 0.5 * base18[
        :, CSKD_MECH_NAMES.index("net_relay_stepover")
    ]
    out[:, 19] = (tip_relay * (0.25 + swarm_transt_fp)).astype(np.float32)

    # 21: Shadow-decontaminated range-front slip deficit x concordant basement-gravity throw
    shadow = base18[:, CSKD_MECH_NAMES.index("net_coulomb_shadow")]
    deficit = base18[:, CSKD_MECH_NAMES.index("net_slip_deficit_front")]
    out[:, 20] = (np.clip(1.0 - shadow, 0.0, 1.0) * deficit * np.log1p(grav_bdepth_conc_fp)).astype(np.float32)

    # 22: Curewitz & Karson (1997) triple-junction breccia damage-zone hydrothermal conduit
    junc_2d = network.junctions(vis).astype(np.float32)
    j_halo = 0.65 * ndi.gaussian_filter(junc_2d, 8.0, mode="constant") + 0.35 * ndi.gaussian_filter(
        junc_2d, 22.0, mode="constant"
    )
    j_fp = j_halo[footprint]
    scale_j = float(np.percentile(j_fp, 99.8)) if np.any(j_fp > 0) else 1.0
    j_norm = np.clip(j_fp / max(scale_j, 1e-6), 0.0, 1.5)
    out[:, 21] = (j_norm * (0.35 + rad_kd_pos_fp) * np.exp(-np.maximum(d_fp - 3.0, 0.0) / 28.0)).astype(np.float32)
    del base18, junc_2d, j_halo, j_fp, d_fp
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def build_stfd_full_visible_physics_shards(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    quad_fp: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    *,
    neg_per_quad: int = 58_000,
    seed: int = 7950,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Train zero-catalogue 97-ch pure physics on 100% of fold-visible faults with flank decontamination."""
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    d_vis_2d = ndi.distance_transform_edt(~vis).astype(np.float32)
    q_vis_fp = metric.kernel(d_vis_2d).astype(np.float32)[footprint]
    d_vis_fp = d_vis_2d[footprint]
    y_vis_fp = vis[footprint]
    del d_vis_2d

    shards: dict[int, dict[str, Any]] = {}
    for qid in range(4):
        rng = np.random.default_rng(seed + 37 * qid)
        in_q = quad_fp == qid
        pos_idx = np.flatnonzero(in_q & y_vis_fp)
        halo_pool = np.flatnonzero(in_q & (~y_vis_fp) & (d_vis_fp >= 1.0) & (q_vis_fp > 0.0))
        far_pool = np.flatnonzero(in_q & (~y_vis_fp) & (d_vis_fp >= 3.0))

        nh = min(halo_pool.size, neg_per_quad // 4)
        nf = min(far_pool.size, neg_per_quad - nh)
        sh = rng.choice(halo_pool, size=nh, replace=False) if nh > 0 else np.empty(0, dtype=np.int64)
        sf = rng.choice(far_pool, size=nf, replace=False) if nf > 0 else np.empty(0, dtype=np.int64)
        idx = np.sort(np.concatenate([pos_idx, sh, sf]))

        X_q = np.array(static_mm[idx], dtype=np.float32, copy=True)
        is_pos = y_vis_fp[idx]
        is_halo = (~is_pos) & (q_vis_fp[idx] > 0.0)
        wh = float(halo_pool.size / max(nh, 1)) if nh > 0 else 1.0
        wf = float(far_pool.size / max(nf, 1)) if nf > 0 else 1.0
        w_q = np.where(is_pos, 1.0, np.where(is_halo, wh, wf)).astype(np.float32)

        shards[qid] = {
            "X": X_q,
            "y": is_pos.astype(np.float32),
            "q": q_vis_fp[idx].astype(np.float32),
            "w": w_q,
            "pos_mass": float(pos_idx.size),
            "act_mass": float(int(in_q.sum())),
        }

    _release_mm(static_mm, mmap_path)
    phys_ref = {
        "active_fp": np.ones_like(y_vis_fp, dtype=bool),
        "y_exact_fp": y_vis_fp,
        "q_300m_fp": q_vis_fp.astype(np.float16),
        "mech_fp16": None,
    }
    return shards, phys_ref


def build_stfd_stratified_topology_shards(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    quad_fp: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    cskd_cues_path: Path,
    stfd_cues_path: Path,
    *,
    n_draws: int = 4,
    hide_frac: float = 0.22,
    buffer_px: int = 3,
    neg_per_quad_per_draw: int = 36_000,
    seed_base: int = 7900,
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    """Quadrant-stratified inner hide-and-recover draws preventing single-quadrant starvation."""
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    quad_2d = np.full(footprint.shape, -1, dtype=np.int8)
    quad_2d[footprint] = quad_fp

    comp, n_comp = ndi.label(vis, STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)

    # Partition visible fault components cleanly by majority quadrant so EVERY inner draw
    # hides exact hide_frac inside EACH quadrant independently (matching gems57.holdout)!
    comp_quads: dict[int, np.ndarray] = {}
    for qid in range(4):
        ids_q = np.unique(comp[vis & (quad_2d == qid)])
        comp_quads[qid] = ids_q[ids_q > 0]

    acc: dict[int, dict[str, list[Any]]] = {
        q: {"X": [], "y": [], "q": [], "w": [], "pos_mass": [], "act_mass": []} for q in range(4)
    }
    draw_refs: list[dict[str, Any]] = []

    for r in range(n_draws):
        chosen_list = []
        for qid in range(4):
            rng_q = np.random.default_rng(seed_base + 1000 * r + 97 * qid)
            pool_q = comp_quads[qid]
            if pool_q.size == 0:
                continue
            target_q = hide_frac * float((vis & (quad_2d == qid)).sum())
            perm = rng_q.permutation(pool_q)
            cum = np.cumsum(sizes[perm])
            k = int(np.searchsorted(cum, target_q)) + 1
            chosen_list.append(perm[: min(k, perm.size)])

        chosen_all = np.unique(np.concatenate(chosen_list)) if chosen_list else np.empty(0, dtype=np.int32)
        sim_hidden = np.isin(comp, chosen_all) & vis
        collar = ndi.distance_transform_edt(~sim_hidden) <= float(buffer_px)
        sim_vis = vis & ~collar
        sim_known = vis & ~sim_hidden
        sim_active = footprint & ~sim_known

        d_hid_2d = ndi.distance_transform_edt(~sim_hidden).astype(np.float32)
        q_fp = metric.kernel(d_hid_2d).astype(np.float32)[footprint]
        y_fp = sim_hidden[footprint]
        act_fp = sim_active[footprint]
        d_sim_fp = ndi.distance_transform_edt(~sim_vis).astype(np.float32)[footprint]
        del d_hid_2d

        mech = compute_stfd_mechanics(sim_vis, footprint, cskd_cues_path, stfd_cues_path)

        if r < 2:
            mpath = str(mmap_path.parent / f"_tmp_draw_mech_{seed_base}_{r}.npy")
            np.save(mpath, mech.astype(np.float16))
            draw_refs.append(
                {
                    "active_fp": act_fp.copy(),
                    "y_exact_fp": y_fp.copy(),
                    "q_300m_fp": q_fp.astype(np.float16),
                    "mech_path": mpath,
                }
            )

        for qid in range(4):
            rng = np.random.default_rng(seed_base + 500 * r + 31 * qid)
            in_q = (quad_fp == qid) & act_fp
            pos_idx = np.flatnonzero(in_q & y_fp)
            # Match Stage-1 and Stage-2 active support (act_fp = footprint & ~sim_known) identically so
            # Stage-1 learns p1 -> 0 inside the 300 m exclusion collar around sim_vis rather than
            # extrapolating high probabilities into d_sim <= 3.0 and corrupting Stage-2 line integrals.
            halo_pool = np.flatnonzero(in_q & (~y_fp) & (q_fp > 0.0))
            far_pool = np.flatnonzero(in_q & (~y_fp) & (q_fp == 0.0))

            nh = min(halo_pool.size, neg_per_quad_per_draw // 4)
            nf = min(far_pool.size, neg_per_quad_per_draw - nh)
            sh = rng.choice(halo_pool, size=nh, replace=False) if nh > 0 else np.empty(0, dtype=np.int64)
            sf = rng.choice(far_pool, size=nf, replace=False) if nf > 0 else np.empty(0, dtype=np.int64)
            idx = np.sort(np.concatenate([pos_idx, sh, sf]))
            if idx.size == 0:
                continue

            X_part = np.empty((idx.size, N_STFD_ALL), dtype=np.float32)
            X_part[:, :N_STFD_STATIC] = static_mm[idx]
            X_part[:, N_STFD_STATIC:] = mech[idx]
            _release_mm(static_mm, mmap_path)

            is_pos = y_fp[idx]
            is_halo = (~is_pos) & (q_fp[idx] > 0.0)
            wh = float(halo_pool.size / max(nh, 1)) if nh > 0 else 1.0
            wf = float(far_pool.size / max(nf, 1)) if nf > 0 else 1.0
            w_part = np.where(is_pos, 1.0, np.where(is_halo, wh, wf)).astype(np.float32)

            acc[qid]["X"].append(X_part)
            acc[qid]["y"].append(is_pos.astype(np.float32))
            acc[qid]["q"].append(q_fp[idx].astype(np.float32))
            acc[qid]["w"].append(w_part)
            acc[qid]["pos_mass"].append(float(pos_idx.size))
            acc[qid]["act_mass"].append(float(int(in_q.sum())))

        del sim_hidden, collar, sim_vis, sim_known, sim_active, q_fp, y_fp, act_fp, d_sim_fp, mech
        gc.collect()

    shards_out: dict[int, dict[str, Any]] = {}
    for qid in range(4):
        shards_out[qid] = {
            "X": np.concatenate(acc[qid]["X"], axis=0) if acc[qid]["X"] else np.zeros((0, N_STFD_ALL), np.float32),
            "y": np.concatenate(acc[qid]["y"], axis=0) if acc[qid]["y"] else np.zeros(0, np.float32),
            "q": np.concatenate(acc[qid]["q"], axis=0) if acc[qid]["q"] else np.zeros(0, np.float32),
            "w": np.concatenate(acc[qid]["w"], axis=0) if acc[qid]["w"] else np.zeros(0, np.float32),
            "pos_mass": float(sum(acc[qid]["pos_mass"])),
            "act_mass": float(sum(acc[qid]["act_mass"])),
        }
    return shards_out, draw_refs


def _stack_stfd_shards(
    shards: dict[int, dict[str, Any]],
    qids: list[int],
    use_mechanics: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float]:
    n_cols = N_STFD_ALL if use_mechanics else N_STFD_STATIC
    Xs = [shards[q]["X"][:, :n_cols] for q in qids if shards[q]["X"].shape[0] > 0]
    ys = [shards[q]["y"] for q in qids if shards[q]["X"].shape[0] > 0]
    qs = [shards[q]["q"] for q in qids if shards[q]["X"].shape[0] > 0]
    ws = [shards[q]["w"] for q in qids if shards[q]["X"].shape[0] > 0]
    X = np.concatenate(Xs, axis=0)
    y = np.concatenate(ys, axis=0)
    q = np.concatenate(qs, axis=0)
    w = np.concatenate(ws, axis=0)
    tot_pos = sum(shards[q]["pos_mass"] for q in qids)
    tot_act = sum(shards[q]["act_mass"] for q in qids)
    return X, y, q, w, float(tot_pos / max(tot_act, 1.0)), float(y.mean())


def _build_stfd_stage2_features(
    p1_fp: np.ndarray,
    q1_fp: np.ndarray,
    footprint: np.ndarray,
    ctx_cols_fp: np.ndarray,
    p_phys_fp: np.ndarray | None = None,
    q_phys_fp: np.ndarray | None = None,
) -> np.ndarray:
    """21-channel Stage-2 directional line-integral + Sato ridge + OOF pure-physics stacker."""
    H, W = footprint.shape
    n_fp = int(footprint.sum())
    n_ctx = ctx_cols_fp.shape[1]
    extra_phys = 4 if p_phys_fp is not None else 0
    n_s2 = 13 + n_ctx + extra_phys

    p2d = np.zeros((H, W), dtype=np.float32)
    q2d = np.zeros((H, W), dtype=np.float32)
    p2d[footprint] = p1_fp
    q2d[footprint] = q1_fp

    out = np.empty((n_fp, n_s2), dtype=np.float16)
    p_clip = np.clip(p1_fp, 1e-6, 1.0 - 1e-6)
    out[:, 0] = p1_fp.astype(np.float16)
    out[:, 1] = np.clip(np.log(p_clip / (1.0 - p_clip)), -20.0, 20.0).astype(np.float16)
    out[:, 2] = q1_fp.astype(np.float16)

    g08 = ndi.gaussian_filter(p2d, 0.8, mode="constant", cval=0.0)
    g15 = ndi.gaussian_filter(p2d, 1.5, mode="constant", cval=0.0)
    g4 = ndi.gaussian_filter(p2d, 4.0, mode="constant", cval=0.0)
    g10 = ndi.gaussian_filter(p2d, 10.0, mode="constant", cval=0.0)
    qg1 = ndi.gaussian_filter(q2d, 1.0, mode="constant", cval=0.0)

    out[:, 3] = g15[footprint].astype(np.float16)
    out[:, 4] = g4[footprint].astype(np.float16)
    out[:, 5] = g10[footprint].astype(np.float16)

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

    out[:, 6] = max7[footprint].astype(np.float16)
    out[:, 7] = max17[footprint].astype(np.float16)
    out[:, 8] = np.clip(max17[footprint] / (min17[footprint] + 1e-4), 0.0, 500.0).astype(np.float16)
    out[:, 9] = (max7[footprint] - g4[footprint]).astype(np.float16)
    out[:, 10] = sato[footprint].astype(np.float16)
    out[:, 11] = ndi.gaussian_filter(q2d, 3.0, mode="constant", cval=0.0)[footprint].astype(np.float16)
    out[:, 12] = q_line17[footprint].astype(np.float16)
    out[:, 13 : 13 + n_ctx] = ctx_cols_fp.astype(np.float16)
    del p2d, q2d, g08, g15, g4, g10, qg1, max7, max17, min17, q_line17, hyy, hxx, hxy, tr, disc, sato
    gc.collect()

    if p_phys_fp is not None and q_phys_fp is not None:
        base_c = 13 + n_ctx
        pp2d = np.zeros((H, W), dtype=np.float32)
        pp2d[footprint] = p_phys_fp
        pp_g15 = ndi.gaussian_filter(pp2d, 1.5, mode="constant", cval=0.0)
        del pp2d
        pp_line17 = np.zeros((H, W), dtype=np.float32)
        for az in (0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5):
            pp_line17 = np.maximum(pp_line17, _sparse_line_integral(pp_g15, half_span=8, step=2, angle_deg=az))
        del pp_g15
        out[:, base_c] = p_phys_fp.astype(np.float16)
        out[:, base_c + 1] = q_phys_fp.astype(np.float16)
        out[:, base_c + 2] = pp_line17[footprint].astype(np.float16)
        out[:, base_c + 3] = np.maximum(p_phys_fp - p1_fp, 0.0).astype(np.float16)
        del pp_line17
        gc.collect()

    return out


def predict_stfd_stage1_rows(
    suite: dict[str, Any],
    static_mm: np.memmap,
    mmap_path: Path,
    mech_arr: np.ndarray | None,
    row_indices: np.ndarray,
    true_pi: float,
    sample_pi: float,
    chunk_size: int = 450_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Dimension-general Stage-1 multi-family prediction with immediate page-cache eviction."""
    n = row_indices.size
    n_static = int(static_mm.shape[1])
    n_c = n_static + (0 if mech_arr is None else int(mech_arr.shape[1]))
    p_out = np.zeros(n, dtype=np.float32)
    q_out = np.zeros(n, dtype=np.float32)
    buf = np.empty((min(chunk_size, max(n, 1)), n_c), dtype=np.float32)

    for s in range(0, n, chunk_size):
        e = min(s + chunk_size, n)
        sub = row_indices[s:e]
        xb = buf[: e - s]
        xb[:, :n_static] = static_mm[sub]
        if mech_arr is not None:
            xb[:, n_static:] = mech_arr[sub]
        p1 = _prior_correct(suite["lgb_deep"].booster_.predict(xb, num_threads=2), true_pi, sample_pi)
        p2 = _prior_correct(suite["lgb_et"].booster_.predict(xb, num_threads=2), true_pi, sample_pi)
        xq = np.clip(suite["sc_lin"].transform(xb), -6.0, 6.0).astype(np.float32)
        p3 = _prior_correct(suite["glm_cls"].predict_proba(xq)[:, 1], true_pi, sample_pi)
        p_out[s:e] = 0.50 * p1 + 0.35 * p2 + 0.15 * p3

        q1 = np.clip(suite["q_lgb"].booster_.predict(xb, num_threads=2), 0.0, 1.0)
        q2 = np.clip(suite["q_ridge"].predict(xq), 0.0, 1.0)
        q_out[s:e] = (0.82 * q1 + 0.18 * q2).astype(np.float32)
        _release_mm(static_mm, mmap_path)

    return p_out, q_out


def run_stfd_quadrant_nested_oof(
    quad_fp: np.ndarray,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    shards: dict[int, dict[str, Any]],
    draw_refs: list[dict[str, Any]],
    test_mech_fp: np.ndarray | None,
    use_mechanics: bool,
    *,
    phys_pair_oof: tuple[np.ndarray, np.ndarray] | None = None,
    phys_outer_oof: tuple[np.ndarray, np.ndarray] | None = None,
    seed: int = 79,
) -> dict[str, Any]:
    """Strict 4-fold Leave-One-Quadrant-Out (LOQO) 2-stage multi-draw stacked predictor."""
    n_fp = int(footprint.sum())
    q_rows = {q: np.flatnonzero(quad_fp == q) for q in range(4)}
    n_cols = N_STFD_ALL if use_mechanics else N_STFD_STATIC

    # Step 1: Fit all C(4, 2) = 6 two-quadrant models once and evaluate on every inner draw_ref
    n_refs = len(draw_refs)
    pair_preds_by_ref: list[dict[tuple[int, int], dict[int, tuple[np.ndarray, np.ndarray]]]] = [
        {} for _ in range(n_refs)
    ]
    feature_gains = np.zeros(n_cols, dtype=np.float64)

    for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
        X_ab, y_ab, q_ab, w_ab, tpi, spi = _stack_stfd_shards(shards, [a, b], use_mechanics)
        s_ab = fit_stage1_ensemble(X_ab, y_ab, q_ab, w_ab, seed=seed + 10 * a + b)
        del X_ab, y_ab, q_ab, w_ab
        rem_qs = [c for c in range(4) if c not in (a, b)]
        rem_rows = np.sort(np.concatenate([q_rows[c] for c in rem_qs]))
        for r_idx, dref in enumerate(draw_refs):
            mech_r = None
            if use_mechanics:
                if dref.get("mech_path") is not None:
                    mech_r = np.load(dref["mech_path"], mmap_mode="r")
                else:
                    mech_r = dref.get("mech_fp16")
            p_rem, q_rem = predict_stfd_stage1_rows(s_ab, static_mm, mmap_path, mech_r, rem_rows, tpi, spi)
            if mech_r is not None and isinstance(mech_r, np.memmap):
                _release_mm(mech_r, Path(dref["mech_path"]))
            del mech_r
            p_tmp = np.zeros(n_fp, dtype=np.float16)
            q_tmp = np.zeros(n_fp, dtype=np.float16)
            p_tmp[rem_rows] = p_rem.astype(np.float16)
            q_tmp[rem_rows] = q_rem.astype(np.float16)
            pair_preds_by_ref[r_idx][(a, b)] = {c: (p_tmp[q_rows[c]], q_tmp[q_rows[c]]) for c in rem_qs}
            del p_rem, q_rem, p_tmp, q_tmp
        del s_ab
        gc.collect()

    # Delete temporary draw mechanics files on disk immediately once pairwise predictions complete
    for dref in draw_refs:
        dref["mech_fp16"] = None
        mp = dref.pop("mech_path", None)
        if mp:
            Path(mp).unlink(missing_ok=True)
    gc.collect()

    # Step 2: Fit 4 outer 3-quadrant LOQO Stage-1 models and predict held-out quadrant q_test
    outer_p1 = np.zeros(n_fp, dtype=np.float32)
    outer_q1 = np.zeros(n_fp, dtype=np.float32)
    for q_test in range(4):
        tr_qs = [q for q in range(4) if q != q_test]
        X_3, y_3, q_3, w_3, tpi3, spi3 = _stack_stfd_shards(shards, tr_qs, use_mechanics)
        s_3 = fit_stage1_ensemble(X_3, y_3, q_3, w_3, seed=seed + 100 + q_test)
        feature_gains += 0.25 * s_3["lgb_deep"].booster_.feature_importance(importance_type="gain")
        del X_3, y_3, q_3, w_3
        outer_p1[q_rows[q_test]], outer_q1[q_rows[q_test]] = predict_stfd_stage1_rows(
            s_3,
            static_mm,
            mmap_path,
            test_mech_fp if use_mechanics else None,
            q_rows[q_test],
            tpi3,
            spi3,
        )
        del s_3
        gc.collect()

    # Release training shards (~250 MB) in place before building Stage-2 spatial line integrals
    shards.clear()
    gc.collect()

    # Average pairwise inner OOF predictions across all training quadrants (strictly out-of-quadrant)
    avg3_p1 = np.zeros(n_fp, dtype=np.float32)
    avg3_q1 = np.zeros(n_fp, dtype=np.float32)
    for c in range(4):
        pairs_for_c = [(a, b) for (a, b) in pair_preds_by_ref[0] if c not in (a, b)]
        avg3_p1[q_rows[c]] = sum(pair_preds_by_ref[0][ab][c][0] for ab in pairs_for_c) / float(len(pairs_for_c))
        avg3_q1[q_rows[c]] = sum(pair_preds_by_ref[0][ab][c][1] for ab in pairs_for_c) / float(len(pairs_for_c))

    # Build outer Stage-2 feature matrix once (each quadrant uses its own strictly out-of-quadrant outer_p1/outer_q1)
    S2_outer = _build_stfd_stage2_features(
        outer_p1,
        outer_q1,
        footprint,
        ctx_cols_fp,
        p_phys_fp=phys_outer_oof[0] if phys_outer_oof is not None else None,
        q_phys_fp=phys_outer_oof[1] if phys_outer_oof is not None else None,
    )

    # Step 3: For each held-out quadrant q_test, fit Stage 2 strictly on tr_qs across ALL draw_refs and average!
    final_p2 = np.zeros(n_fp, dtype=np.float32)
    final_q2 = np.zeros(n_fp, dtype=np.float32)
    for q_test in range(4):
        tr_qs = [q for q in range(4) if q != q_test]
        tr_mask = quad_fp != q_test
        p_acc = np.zeros(q_rows[q_test].size, dtype=np.float32)
        q_acc = np.zeros(q_rows[q_test].size, dtype=np.float32)

        for r_idx, dref in enumerate(draw_refs):
            in_p1 = np.zeros(n_fp, dtype=np.float32)
            in_q1 = np.zeros(n_fp, dtype=np.float32)
            for c in tr_qs:
                rem = sorted([q for q in tr_qs if q != c])
                ab = (rem[0], rem[1])
                in_p1[q_rows[c]], in_q1[q_rows[c]] = pair_preds_by_ref[r_idx][ab][c]
            in_p1[q_rows[q_test]] = outer_p1[q_rows[q_test]]
            in_q1[q_rows[q_test]] = outer_q1[q_rows[q_test]]

            S2_in = _build_stfd_stage2_features(
                in_p1,
                in_q1,
                footprint,
                ctx_cols_fp,
                p_phys_fp=phys_pair_oof[0] if phys_pair_oof is not None else None,
                q_phys_fp=phys_pair_oof[1] if phys_pair_oof is not None else None,
            )
            s2_m = fit_stage2_dual_heads(S2_in, dref, tr_mask, seed=seed + 400 + 29 * r_idx + q_test)
            pr_q, qr_q = predict_stage2_dual_heads(s2_m, S2_outer, q_rows[q_test])
            p_acc += pr_q / float(n_refs)
            q_acc += qr_q / float(n_refs)
            del S2_in, s2_m, pr_q, qr_q
            gc.collect()

        final_p2[q_rows[q_test]] = p_acc
        final_q2[q_rows[q_test]] = q_acc

    del S2_outer, pair_preds_by_ref
    gc.collect()

    names = STFD_ALL_FEATURE_NAMES if use_mechanics else STFD_STATIC_NAMES
    gain_total = max(float(feature_gains.sum()), 1e-9)
    top_features = sorted(
        ({"feature": names[i], "gain_share": round(float(feature_gains[i] / gain_total), 6)} for i in range(n_cols)),
        key=lambda d: -d["gain_share"],
    )

    return {
        "p2_fp": final_p2,
        "q2_fp": final_q2,
        "pair_oof_p1": avg3_p1,
        "pair_oof_q1": avg3_q1,
        "outer_p1": outer_p1,
        "outer_q1": outer_q1,
        "top_features": top_features,
    }


def calibrate_quadrant_posteriors_to_visible_density(
    p_2d: np.ndarray,
    q_2d: np.ndarray,
    visible_mask: np.ndarray,
    allow_mask: np.ndarray,
    quad_2d: np.ndarray,
    *,
    strength: float = 0.85,
    budget_ref: int = 37_654,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Zero-leakage order-statistic tail calibration aligning LOQO quadrant posteriors with visible fault density.

    In any region ``Q_k``, ``visible_mask & Q_k`` and ``allow_mask & Q_k`` are 100% observable at both holdout
    and live full-catalogue inference without touching hidden truth. Aligning the top ``K_k = 2.2 * budget_ref * vis_share[k]``
    candidate tail threshold across quadrants prevents heavy-tailed background floor noise from inverting quadrant
    allocation and starving 10 m DEM quadrants.
    """
    vis = np.asarray(visible_mask, dtype=bool)
    allow = np.asarray(allow_mask, dtype=bool)
    p_cal = p_2d.copy().astype(np.float32)
    q_cal = q_2d.copy().astype(np.float32)

    vis_counts = np.array([float((vis & (quad_2d == k)).sum()) for k in range(4)], dtype=np.float64)
    vis_share = vis_counts / max(float(vis_counts.sum()), 1.0)
    allow_counts = np.array([float((allow & (quad_2d == k)).sum()) for k in range(4)], dtype=np.float64)
    allow_share = allow_counts / max(float(allow_counts.sum()), 1.0)

    def _compute_quad_multipliers(arr: np.ndarray, mult_strength: float) -> tuple[np.ndarray, np.ndarray]:
        vals_all = arr[allow]
        if vals_all.size == 0 or float(np.std(vals_all)) < 1e-6:
            ratios = np.clip(vis_share / np.maximum(allow_share, 1e-6), 0.45, 2.25)
            return (1.0 - mult_strength) + mult_strength * ratios, ratios
        taus = np.ones(4, dtype=np.float64)
        for k in range(4):
            vq = arr[allow & (quad_2d == k)]
            if vq.size == 0:
                continue
            kk = min(max(int(round(budget_ref * 2.2 * vis_share[k])), 64), vq.size - 1)
            taus[k] = max(float(np.partition(vq, vq.size - kk)[vq.size - kk]), 1e-7)
        tau_ref = float(np.median(taus))
        ratios = np.clip(tau_ref / taus, 0.45, 2.25)
        return (1.0 - mult_strength) + mult_strength * ratios, taus

    mults_p, taus_p = _compute_quad_multipliers(p_2d, strength)
    mults_q, taus_q = _compute_quad_multipliers(q_2d, strength)

    diag: dict[str, Any] = {}
    for k in range(4):
        m_q = allow & (quad_2d == k)
        if not np.any(m_q):
            continue
        p_cal[m_q] = np.clip(p_2d[m_q] * float(mults_p[k]), 0.0, 0.96)
        q_cal[m_q] = np.clip(q_2d[m_q] * float(mults_q[k]), 0.0, 0.98)
        diag[f"quad_{k}"] = {
            "visible_fault_share": round(float(vis_share[k]), 5),
            "raw_p_tail_tau": round(float(taus_p[k]), 6),
            "raw_q_tail_tau": round(float(taus_q[k]), 6),
            "applied_p_multiplier": round(float(mults_p[k]), 5),
            "applied_q_multiplier": round(float(mults_q[k]), 5),
        }
    return p_cal, q_cal, diag


def dinkelbach_stfd_emit(
    p_2d: np.ndarray,
    q_2d: np.ndarray,
    p_phys_cal_2d: np.ndarray,
    q_phys_cal_2d: np.ndarray,
    allow_mask: np.ndarray,
    visible_mask: np.ndarray,
    *,
    coulomb_shadow_2d: np.ndarray | None = None,
    alpha: float = 0.2,
    beta: float = 0.8,
    min_sep_px: float = 2.05,
    near_max_budget: int = 38_600,
    near_min_budget: int = 26_000,
    far_reserve_budget: int = 2_400,
    far_min_dist_px: float = 10.0,
    far_min_sep_px: float = 2.5,
    dinkelbach_iters: int = 2,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Scale-consistent fixed-point fractional Dinkelbach kernel allocator with off-catalogue far-field reserve.

    Before submodular cover depletion (C == 0), a single dot's expected kernel credit is E[dT(x | empty)] = q(x).
    Rescaling raw 29-offset kernel sums by the exact self-consistency factor
        eta = sum_{x in T_ref} q(x) / sum_{x in T_ref} sum_delta p(x + delta) k(delta)
    puts marginal coverage gains dT(x | C) in exact true-positive pixel units matching ``gems57.metric``, so
        theta^{(t+1)} = TP_hat(S^{(t)}) / [ alpha * (TP_hat(S^{(t)}) + |S^{(t)}| - M_hat(S^{(t)})) + beta * K_hat ]
    converges self-consistently without arbitrary penalty constants.
    """
    import heapq

    H, W = p_2d.shape
    pad = 4
    vis = np.asarray(visible_mask, dtype=bool)
    allow = np.asarray(allow_mask, dtype=bool) & (~vis)
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)

    p_eff = np.clip(np.asarray(p_2d, dtype=np.float64), 0.0, 0.98).copy()
    q_eff = np.clip(np.asarray(q_2d, dtype=np.float64), 0.0, 0.98).copy()
    if coulomb_shadow_2d is not None:
        flank_damp = 1.0 - 0.16 * np.clip(coulomb_shadow_2d, 0.0, 1.0) * (d_vis < 8.0)
        p_eff *= flank_damp
        q_eff *= flank_damp

    # Expected hidden positive pixel count in scored domain (~25% of visible pixels under 20% hide)
    k_hat = max(0.24 * float(vis.sum()), float(p_eff[allow].sum()), 50.0)

    dy_list = metric.OFF_DY.tolist()
    dx_list = metric.OFF_DX.tolist()
    kw_list = metric.OFF_K.tolist()
    n_off = len(kw_list)

    r_ceil = int(np.ceil(min_sep_px))
    sep_y, sep_x = [], []
    for j in range(-r_ceil, r_ceil + 1):
        for i in range(-r_ceil, r_ceil + 1):
            if j * j + i * i < min_sep_px * min_sep_px - 1e-9:
                sep_y.append(j)
                sep_x.append(i)

    cy, cx = np.nonzero(allow)
    if cy.size == 0:
        return np.zeros((H, W), dtype=np.float32), {"total_emitted_dots": 0}
    if cy.size > 400_000:
        init_score = p_eff[cy, cx] + 0.35 * q_eff[cy, cx]
        keep = np.argpartition(init_score, -400_000)[-400_000:]
        cy, cx = cy[keep], cx[keep]

    raw_p_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    raw_p_pad[pad : pad + H, pad : pad + W] = p_eff

    raw_g0 = np.zeros(cy.size, dtype=np.float64)
    for k_i in range(n_off):
        raw_g0 += raw_p_pad[cy + pad + dy_list[k_i], cx + pad + dx_list[k_i]] * kw_list[k_i]
    q_cand = q_eff[cy, cx]

    # Exact unit-consistency factor eta aligning E[dT(x | C=0)] with calibrated self-credit q(x)
    n_ref = min(cy.size, max(near_min_budget, 200))
    ref_sel = np.argpartition(raw_g0, -n_ref)[-n_ref:]
    eta = float(np.clip(q_cand[ref_sel].sum() / max(float(raw_g0[ref_sel].sum()), 1e-9), 0.02, 20.0))

    p_pad = raw_p_pad * eta
    gain0 = raw_g0 * eta
    del raw_p_pad, raw_g0

    theta = 0.205
    best_cov = None
    best_blocked = None
    best_out = None
    near_emitted = 0

    for _it in range(max(1, dinkelbach_iters)):
        cov_pad = np.zeros_like(p_pad)
        blocked_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool)
        out_bool = np.zeros((H, W), dtype=bool)

        u0 = gain0 - theta * alpha * (gain0 + 1.0 - q_cand)
        order = np.argsort(-u0)[: min(cy.size, 280_000)]
        heap: list[tuple[float, int]] = [(-float(u0[i]), int(i)) for i in order]
        heapq.heapify(heap)

        tot_tp = 0.0
        tot_m = 0.0
        n_acc = 0

        while heap and n_acc < near_max_budget:
            neg_u, idx = heapq.heappop(heap)
            ry = int(cy[idx]) + pad
            rx = int(cx[idx]) + pad
            if blocked_pad[ry, rx]:
                continue

            dg = 0.0
            for k_i in range(n_off):
                rem = kw_list[k_i] - cov_pad[ry + dy_list[k_i], rx + dx_list[k_i]]
                if rem > 0.0:
                    dg += p_pad[ry + dy_list[k_i], rx + dx_list[k_i]] * rem

            cur_d = alpha * (tot_tp + n_acc - tot_m) + beta * k_hat + 1e-9
            cur_theta = tot_tp / cur_d if n_acc >= max(near_min_budget // 8, 50) else theta
            u_exact = dg - cur_theta * alpha * (dg + 1.0 - float(q_cand[idx]))

            if u_exact < (-neg_u) - 1e-7:
                heapq.heappush(heap, (-u_exact, idx))
                continue

            if u_exact <= 0.0 and n_acc >= near_min_budget:
                break

            out_bool[ry - pad, rx - pad] = True
            n_acc += 1
            tot_tp += dg
            tot_m += float(q_cand[idx])
            for k_i in range(n_off):
                ny, nx = ry + dy_list[k_i], rx + dx_list[k_i]
                if kw_list[k_i] > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = kw_list[k_i]
            for sj, si in zip(sep_y, sep_x):
                blocked_pad[ry + sj, rx + si] = True

        denom_final = alpha * (tot_tp + n_acc - tot_m) + beta * k_hat + 1e-9
        theta = float(np.clip(tot_tp / denom_final, 0.08, 0.45))
        best_cov = cov_pad
        best_blocked = blocked_pad
        best_out = out_bool
        near_emitted = n_acc

    assert best_out is not None and best_cov is not None and best_blocked is not None

    # Phase 2: Dedicated off-catalogue pure-physics discovery reserve (d_vis >= far_min_dist_px)
    far_added = 0
    if far_reserve_budget > 0:
        far_mask = allow & (d_vis >= far_min_dist_px) & (~best_out)
        fy, fx = np.nonzero(far_mask)
        if fy.size > 0:
            p_far_blend = 0.72 * np.clip(p_phys_cal_2d, 0.0, 1.0) + 0.28 * np.clip(p_2d, 0.0, 1.0)
            q_far_blend = 0.72 * np.clip(q_phys_cal_2d, 0.0, 1.0) + 0.28 * np.clip(q_2d, 0.0, 1.0)

            pf_pad = np.zeros_like(p_pad)
            pf_pad[pad : pad + H, pad : pad + W] = p_far_blend * eta

            r_far = int(np.ceil(far_min_sep_px))
            fsep_y, fsep_x = [], []
            for j in range(-r_far, r_far + 1):
                for i in range(-r_far, r_far + 1):
                    if j * j + i * i < far_min_sep_px * far_min_sep_px - 1e-9:
                        fsep_y.append(j)
                        fsep_x.append(i)

            ey, ex = np.nonzero(best_out)
            for y0, x0 in zip(ey.tolist(), ex.tolist()):
                for sj, si in zip(fsep_y, fsep_x):
                    best_blocked[y0 + pad + sj, x0 + pad + si] = True

            fg0 = np.zeros(fy.size, dtype=np.float64)
            for k_i in range(n_off):
                fg0 += pf_pad[fy + pad + dy_list[k_i], fx + pad + dx_list[k_i]] * kw_list[k_i]
            fq = q_far_blend[fy, fx]
            fu0 = fg0 - 0.5 * theta * alpha * (1.0 - fq)
            forder = np.argsort(-fu0)[: min(fy.size, 140_000)]
            fheap: list[tuple[float, int]] = [(-float(fu0[i]), int(i)) for i in forder]
            heapq.heapify(fheap)

            while fheap and far_added < far_reserve_budget:
                neg_u, idx = heapq.heappop(fheap)
                ry = int(fy[idx]) + pad
                rx = int(fx[idx]) + pad
                if best_blocked[ry, rx]:
                    continue
                dg = 0.0
                for k_i in range(n_off):
                    rem = kw_list[k_i] - best_cov[ry + dy_list[k_i], rx + dx_list[k_i]]
                    if rem > 0.0:
                        dg += pf_pad[ry + dy_list[k_i], rx + dx_list[k_i]] * rem
                u_ex = dg - 0.5 * theta * alpha * (1.0 - float(fq[idx]))
                if u_ex < (-neg_u) - 1e-7:
                    heapq.heappush(fheap, (-u_ex, idx))
                    continue
                best_out[ry - pad, rx - pad] = True
                far_added += 1
                for k_i in range(n_off):
                    ny, nx = ry + dy_list[k_i], rx + dx_list[k_i]
                    if kw_list[k_i] > best_cov[ny, nx]:
                        best_cov[ny, nx] = kw_list[k_i]
                for sj, si in zip(fsep_y, fsep_x):
                    best_blocked[ry + sj, rx + si] = True

    emitted_total = int(best_out.sum())
    d_emit = d_vis[best_out] if emitted_total > 0 else np.zeros(1, dtype=np.float32)
    info = {
        "eta_unit_consistency": round(eta, 6),
        "converged_dinkelbach_theta": round(float(theta), 6),
        "implied_lambda_fp": round(float((alpha * theta) / max(1.0 - alpha * theta, 1e-6)), 6),
        "near_dinkelbach_dots": int(near_emitted),
        "far_pure_physics_reserve_dots": int(far_added),
        "total_emitted_dots": emitted_total,
        "min_dist_to_visible_px": round(float(d_emit.min()), 4),
        "median_dist_to_visible_px": round(float(np.median(d_emit)), 4),
        "p90_dist_to_visible_px": round(float(np.percentile(d_emit, 90)), 4),
        "fraction_gt_2km_from_visible": round(float((d_emit > 20.0).mean()), 6),
    }
    return best_out.astype(np.float32), info
