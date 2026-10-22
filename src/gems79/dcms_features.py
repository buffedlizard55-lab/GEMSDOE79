"""G79-DCMS leak-free Dip-Coupled Multi-Scale Scarp-to-Basement Reactivation,
Pluvial/Fluvial Mimic Suppression & Multi-Azimuth Fold-Strict Mechanics Engine.

Builds 98 static physical channels (streamed directly to disk float32 memmap with
``POSIX_FADV_DONTNEED`` so RSS stays < 950 MB on a 3.8 GiB VM) plus 20 fold-strict
network mechanics channels computed exclusively from ``visible_mask``.

Strict zero-leakage invariants:
  1. Never reads any prior prediction raster from registry / downloads as features.
  2. Pre-screens all 98 static + 20 mechanics = 118 channels on both Seed 20 and
     Seed 30 against the single-feature symmetric ROC AUC <= 0.90 leakage gate.
  3. Explicitly raises ValueError if any forbidden label-proxy column
     (``dist_known_fault_px``, ``known_fault``, ``label``) is requested.
  4. All Group D mechanics channels are functions strictly of ``visible_mask``
     (never ``existing_faults.tif`` during holdout evaluation).
"""
from __future__ import annotations

import gc
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from gems79.thvc_features import (
    FORBIDDEN_POINT_COLUMNS,
    MECH_FEATURE_NAMES as BASE_MECH_NAMES,
    STATIC_FEATURE_NAMES as BASE_STATIC_NAMES,
    STRUCT3,
    _draw_segment_score,
    _empirical_quantiles_1d,
    _extract_tips_and_tangents,
    build_static_feature_memmap as build_base_70_memmap,
    compute_network_mechanics as compute_base_14_mechanics,
    parse_safe_csv,
    rss_mb,
)

EXTRA_STATIC_NAMES = [
    # Group H1: Full-precision float32 10-m 3DEP sub-grid scarp asymmetry & focus (8)
    "dem10_onesided_f32",
    "dem10_onesided3_f32",
    "dem10_hgm20_f32",
    "dem10_hgm50_f32",
    "dem10_hgm200_f32",
    "dem10_steep_ratio_f32",
    "dem10_resid_range_f32",
    "dem10_scarp_focus_nosym",
    # Group H1+H4: Pluvial/fluvial mimic suppressors, full LiDAR strike, chalcedony & U-Th-K (10)
    "lidar_along_minus_cross",
    "topo_strike_cos2",
    "topo_strike_sin2",
    "dem_elev_norm",
    "lahontan_shoreline_mimic",
    "tectonic_over_lahontan",
    "gdr_chalcedony_anom_1200m",
    "rad_u_norm",
    "rad_tc_norm",
    "rad_th_k_clay",
    # Group H2: Dip-projected hanging-wall crustal coupling & cross-depth strike coherence (6)
    "grav_downdip_600m",
    "grav_downdip_1100m",
    "grav_dip_asymmetry",
    "bdepth_downdip_700m",
    "strike_align_topo_grav",
    "strike_align_topo_mag",
    # Group H3: Public-domain USGS DS-1052 (SGMC) bedrock fault reactivation & basin projection (4)
    "sgmc_log_dist",
    "sgmc_corridor_400m",
    "sgmc_strain_reactivation",
    "sgmc_basin_strike_proj_25px",
]

STATIC_DCMS_NAMES = BASE_STATIC_NAMES + EXTRA_STATIC_NAMES  # 70 + 28 = 98

EXTRA_MECH_NAMES = [
    "net_exp_ultra_near_3p2",
    "net_tip_broad_25px",
    "net_tip_long_65px",
    "net_vis_strike_align_topo",
    "net_vis_strike_align_geophys",
    "net_tip_x_sgmc",
]

MECH_DCMS_NAMES = BASE_MECH_NAMES + EXTRA_MECH_NAMES  # 14 + 6 = 20
ALL_DCMS_NAMES = STATIC_DCMS_NAMES + MECH_DCMS_NAMES  # 98 + 20 = 118


def _drop_cache(path: Path) -> None:
    if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED") and path.exists():
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)


def _structure_tensor_doubled_angle(field: np.ndarray, sigma_grad: float = 1.5, sigma_int: float = 3.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute strike unit doubled-angle ``(cos 2*theta_strike, sin 2*theta_strike, coherence)``."""
    gy = ndi.gaussian_filter(field.astype(np.float32, copy=False), sigma_grad, order=(1, 0), mode="nearest")
    gx = ndi.gaussian_filter(field.astype(np.float32, copy=False), sigma_grad, order=(0, 1), mode="nearest")
    jxx = ndi.gaussian_filter(gx * gx, sigma_int, mode="nearest")
    jyy = ndi.gaussian_filter(gy * gy, sigma_int, mode="nearest")
    jxy = ndi.gaussian_filter(gx * gy, sigma_int, mode="nearest")
    # Gradient direction angle phi has cos(2*phi) = (jxx - jyy)/denom, sin(2*phi) = 2*jxy/denom
    # Strike direction theta = phi + pi/2 flips sign of BOTH cos(2*theta) and sin(2*theta)!
    diff = jxx - jyy
    two_xy = 2.0 * jxy
    mag = np.hypot(diff, two_xy) + 1e-8
    tr = jxx + jyy + 1e-8
    c2_strike = (-diff / mag).astype(np.float32)
    s2_strike = (-two_xy / mag).astype(np.float32)
    coh = np.clip(mag / tr, 0.0, 1.0).astype(np.float32)
    del gy, gx, jxx, jyy, jxy, diff, two_xy, mag, tr
    return c2_strike, s2_strike, coh


def _eval_along_normal(field: np.ndarray, ny: np.ndarray, nx: np.ndarray, shift_px: float) -> np.ndarray:
    """Evaluate 2D field at rounded ``(y + shift_px * ny, x + shift_px * nx)`` safely clipped to grid."""
    H, W = field.shape
    yy = np.clip(np.rint(np.arange(H, dtype=np.float32)[:, None] + shift_px * ny).astype(np.int32), 0, H - 1)
    xx = np.clip(np.rint(np.arange(W, dtype=np.float32)[None, :] + shift_px * nx).astype(np.int32), 0, W - 1)
    return field[yy, xx]


def build_dcms_static_memmap(
    raw_dir: Path,
    ing_dir: Path,
    dem10_dir: Path,
    out_dir: Path,
    footprint: np.ndarray,
    transform: Any,
) -> dict[str, Any]:
    """Stream all 98 static DCMS physics channels into ``out_dir / 'static_fp98.f32.mmap'``."""
    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "static_fp98.f32.mmap"
    meta_path = out_dir / "static_fp98.meta.json"
    cues_path = out_dir / "dcms_cues.npz"

    H, W = footprint.shape
    n_fp = int(footprint.sum())
    n_tot = len(STATIC_DCMS_NAMES)

    if out_path.is_file() and meta_path.is_file() and cues_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("rows") == n_fp
            and meta.get("cols") == n_tot
            and meta.get("feature_names") == STATIC_DCMS_NAMES
            and out_path.stat().st_size == n_fp * n_tot * 4
        ):
            return meta

    # 1. Build or reuse verified 70-channel base static memmap cleanly
    base_mmap_path = out_dir / "base_fp70.f32.mmap"
    base_cues_path = base_mmap_path.with_suffix(".cues.npz")
    build_base_70_memmap(raw_dir, ing_dir, base_mmap_path, footprint, transform)

    mm98 = np.memmap(out_path, dtype="float32", mode="w+", shape=(n_fp, n_tot))
    mm70 = np.memmap(base_mmap_path, dtype="float32", mode="r", shape=(n_fp, len(BASE_STATIC_NAMES)))
    chunk_r = 650_000
    for s in range(0, n_fp, chunk_r):
        e = min(s + chunk_r, n_fp)
        mm98[s:e, : len(BASE_STATIC_NAMES)] = mm70[s:e]
    mm98.flush()
    base_cmap = {name: i for i, name in enumerate(BASE_STATIC_NAMES)}

    def get_base_2d(col_name: str) -> np.ndarray:
        arr = np.zeros((H, W), dtype=np.float32)
        arr[footprint] = mm70[:, base_cmap[col_name]]
        return arr

    col_map = {name: i for i, name in enumerate(STATIC_DCMS_NAMES)}

    def write_col(name: str, arr_or_vec: np.ndarray, is_1d: bool = False) -> None:
        vec = np.asarray(arr_or_vec if is_1d else arr_or_vec[footprint], dtype=np.float32)
        vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
        mm98[:, col_map[name]] = vec

    # 2. Group H1: Load all 8 full-precision float32 10-m 3DEP vectors (already in row-major footprint order!)
    d10_one1 = np.load(dem10_dir / "dem10_onesided.f32.npy", mmap_mode="r").astype(np.float32)
    d10_one3 = np.load(dem10_dir / "dem10_onesided3.f32.npy", mmap_mode="r").astype(np.float32)
    d10_h20 = np.load(dem10_dir / "dem10_hgm20_max.f32.npy", mmap_mode="r").astype(np.float32)
    d10_h50 = np.load(dem10_dir / "dem10_hgm50_max.f32.npy", mmap_mode="r").astype(np.float32)
    d10_h200 = np.load(dem10_dir / "dem10_hgm200_mean.f32.npy", mmap_mode="r").astype(np.float32)
    d10_sr = np.log1p(np.maximum(np.load(dem10_dir / "dem10_steep_ratio_max.f32.npy", mmap_mode="r").astype(np.float32), 0.0))
    d10_rr = np.log1p(np.maximum(np.load(dem10_dir / "dem10_resid_range.f32.npy", mmap_mode="r").astype(np.float32), 0.0))
    d10_focus = (d10_h20 / (d10_h200 + 0.03)) * d10_one3

    write_col("dem10_onesided_f32", d10_one1, is_1d=True)
    write_col("dem10_onesided3_f32", d10_one3, is_1d=True)
    write_col("dem10_hgm20_f32", d10_h20, is_1d=True)
    write_col("dem10_hgm50_f32", d10_h50, is_1d=True)
    write_col("dem10_hgm200_f32", d10_h200, is_1d=True)
    write_col("dem10_steep_ratio_f32", d10_sr, is_1d=True)
    write_col("dem10_resid_range_f32", d10_rr, is_1d=True)
    write_col("dem10_scarp_focus_nosym", d10_focus, is_1d=True)
    del d10_one1, d10_h20, d10_h50, d10_h200, d10_sr, d10_rr, d10_focus
    gc.collect()

    # 3. Group H1+H4: LiDAR cross-slope channel suppressor, strike angle, Lake Lahontan shoreline mimic, chalcedony, U/TC/ThK
    with rasterio.open(raw_dir / "external/lidar_scarp_features_u8.tif") as ds:
        lid_down = ds.read(6).astype(np.float32)
        lid_up = ds.read(7).astype(np.float32)
        lid_cross = ds.read(8).astype(np.float32)
        lid_strike_u8 = ds.read(11).astype(np.float32)
        lid_valid = (ds.read(12) > 0) & footprint

    with rasterio.open(ing_dir / "topo_10m_derived_100m_u8.tif") as ds:
        dem_u8 = ds.read(9).astype(np.float32)

    det_elev_2d = get_base_2d("tf_det_elev")
    c2_topo, s2_topo, coh_topo = _structure_tensor_doubled_angle(det_elev_2d, sigma_grad=1.2, sigma_int=2.8)

    # Fuse 1-m LiDAR strike angle (where valid) with 100-m detrended topo structure-tensor strike outside LiDAR
    lid_ang = np.deg2rad((lid_strike_u8 - 1.0) / 254.0 * 180.0)
    c2_fused = np.where(lid_valid, np.cos(2.0 * lid_ang).astype(np.float32), c2_topo)
    s2_fused = np.where(lid_valid, np.sin(2.0 * lid_ang).astype(np.float32), s2_topo)
    write_col("topo_strike_cos2", c2_fused)
    write_col("topo_strike_sin2", s2_fused)

    along_vs_cross = np.zeros((H, W), dtype=np.float32)
    raw_ac = np.maximum(lid_up, lid_down) - 0.75 * lid_cross
    along_vs_cross[lid_valid] = _empirical_quantiles_1d(raw_ac[lid_valid])
    gap_mask = footprint & ~lid_valid
    d10_one3_2d = np.zeros((H, W), dtype=np.float32)
    d10_one3_2d[footprint] = d10_one3
    along_vs_cross[gap_mask] = _empirical_quantiles_1d(d10_one3_2d[gap_mask])
    write_col("lidar_along_minus_cross", along_vs_cross)
    del lid_down, lid_up, lid_cross, lid_strike_u8, lid_ang, raw_ac, d10_one3
    gc.collect()

    # Dequantize absolute elevation (m) & build Pleistocene Lake Lahontan highstand mimic indicator (~1335 m)
    dem_m = 1099.7082 + np.clip((dem_u8 - 1.0) / 254.0, 0.0, 1.0) * (2481.5011 - 1099.7082)
    dem_norm = np.clip((dem_m - 1100.0) / 1400.0, 0.0, 1.0).astype(np.float32)
    lahontan = np.exp(-(((dem_m - 1335.0) / 38.0) ** 2)).astype(np.float32)
    write_col("dem_elev_norm", dem_norm)
    write_col("lahontan_shoreline_mimic", lahontan)

    grav_z800 = get_base_2d("grav_hgm_z800")
    u_step_2d = get_base_2d("scarp_unified_step")
    med_g8 = float(np.median(grav_z800[footprint])) + 1e-6
    tec_over_lah = u_step_2d * (1.0 - 0.72 * lahontan * np.exp(-grav_z800 / med_g8))
    write_col("tectonic_over_lahontan", tec_over_lah)
    del dem_u8, dem_norm, lahontan, tec_over_lah

    # Chalcedony low-to-moderate enthalpy silica geothermometer + full GeoDAWN U/TC/ThK
    ws_rows = parse_safe_csv(raw_dir / "external/gdr_wellspring_in_footprint.csv", ("row", "col", "geothermchalc_c"))
    ws_ch = np.zeros((H, W), dtype=np.float32)
    for r in ws_rows:
        try:
            ri, ci = int(float(r["row"])), int(float(r["col"]))
            if 0 <= ri < H and 0 <= ci < W:
                cv = float(r["geothermchalc_c"]) if r["geothermchalc_c"] not in ("", "nan", "NaN") else 0.0
                if np.isfinite(cv) and cv > 55.0:
                    ws_ch[ri, ci] = max(ws_ch[ri, ci], min(cv - 50.0, 180.0))
        except ValueError:
            pass
    write_col("gdr_chalcedony_anom_1200m", ndi.gaussian_filter(ws_ch, 12.0, mode="constant", cval=0.0))
    del ws_rows, ws_ch

    with rasterio.open(raw_dir / "external/geodawn_rad_u8.tif") as ds:
        write_col("rad_u_norm", ds.read(3).astype(np.float32) / 255.0)
        write_col("rad_tc_norm", ds.read(4).astype(np.float32) / 255.0)
    with rasterio.open(raw_dir / "external/geodawn_extensions_u8.tif") as ds:
        write_col("rad_th_k_clay", ds.read(1).astype(np.float32) / 255.0)

    # 4. Group H2: Downslope basinward unit normal & dip-projected hanging-wall gravity/MT/strike coupling
    gy_reg = ndi.gaussian_filter(dem_m.astype(np.float32), 7.0, order=(1, 0), mode="nearest")
    gx_reg = ndi.gaussian_filter(dem_m.astype(np.float32), 7.0, order=(0, 1), mode="nearest")
    gn_reg = np.hypot(gx_reg, gy_reg) + 1e-5
    ny_down = (-gy_reg / gn_reg).astype(np.float32)
    nx_down = (-gx_reg / gn_reg).astype(np.float32)
    del dem_m, gy_reg, gx_reg, gn_reg

    g_down6 = _eval_along_normal(grav_z800, ny_down, nx_down, 6.0)
    g_down11 = _eval_along_normal(grav_z800, ny_down, nx_down, 11.0)
    g_up8 = _eval_along_normal(grav_z800, ny_down, nx_down, -8.0)
    g_down8 = _eval_along_normal(grav_z800, ny_down, nx_down, 8.0)
    bdepth_300 = get_base_2d("bdepth_hgm_300m")
    bd_down7 = _eval_along_normal(bdepth_300, ny_down, nx_down, 7.0)

    write_col("grav_downdip_600m", g_down6)
    write_col("grav_downdip_1100m", g_down11)
    write_col("grav_dip_asymmetry", g_down8 - g_up8)
    write_col("bdepth_downdip_700m", bd_down7)
    del ny_down, nx_down, g_down6, g_down11, g_up8, g_down8, bd_down7, bdepth_300

    iso_grav_raw = get_base_2d("tf_iso_grav_anom")
    rtp_raw = get_base_2d("tf_rtp")
    c2_grav, s2_grav, coh_grav = _structure_tensor_doubled_angle(iso_grav_raw, sigma_grad=2.5, sigma_int=5.0)
    c2_mag, s2_mag, coh_mag = _structure_tensor_doubled_angle(rtp_raw, sigma_grad=2.0, sigma_int=4.0)
    align_tg = (c2_fused * c2_grav + s2_fused * s2_grav) * np.sqrt(coh_topo * coh_grav)
    align_tm = (c2_fused * c2_mag + s2_fused * s2_mag) * np.sqrt(coh_topo * coh_mag)
    write_col("strike_align_topo_grav", align_tg)
    write_col("strike_align_topo_mag", align_tm)
    c2_geophys = (0.55 * c2_grav + 0.45 * c2_mag).astype(np.float16)
    s2_geophys = (0.55 * s2_grav + 0.45 * s2_mag).astype(np.float16)
    del iso_grav_raw, rtp_raw, c2_topo, s2_topo, coh_topo, c2_grav, s2_grav, coh_grav, c2_mag, s2_mag, coh_mag, align_tg, align_tm
    gc.collect()

    # 5. Group H3: Public-domain USGS DS-1052 (SGMC) pre-Quaternary bedrock reactivation & basin projection
    with rasterio.open(raw_dir / "external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0) & footprint
    d_sgmc = ndi.distance_transform_edt(~sgmc).astype(np.float32)
    sgmc_cor4 = np.exp(-d_sgmc / 4.0).astype(np.float32)
    write_col("sgmc_log_dist", np.log1p(d_sgmc))
    write_col("sgmc_corridor_400m", sgmc_cor4)

    shr = np.abs(get_base_2d("tf_geod_shearrate"))
    dil = np.maximum(get_base_2d("tf_geod_dilaterate"), 0.0)
    write_col("sgmc_strain_reactivation", np.exp(-d_sgmc / 5.0) * shr * (1.0 + dil))
    del shr, dil

    # Forward strike projection of SGMC bedrock fault tips into Quaternary basins (2.5 km cone)
    sgmc_tips_yx, sgmc_dirs_yx = _extract_tips_and_tangents(sgmc)
    sgmc_proj = np.zeros((H, W), dtype=np.float32)
    R_SG = 25
    gy_s, gx_s = np.mgrid[-R_SG : R_SG + 1, -R_SG : R_SG + 1].astype(np.float32)
    rr_s = np.hypot(gy_s, gx_s)
    v_s = (rr_s >= 1.0) & (rr_s <= float(R_SG))
    uy_s = np.divide(gy_s, rr_s, out=np.zeros_like(gy_s), where=v_s)
    ux_s = np.divide(gx_s, rr_s, out=np.zeros_like(gx_s), where=v_s)
    exp_s = np.exp(-rr_s / 13.0) * v_s
    for (py, px), (vy, vx) in zip(sgmc_tips_yx, sgmc_dirs_yx):
        cy, cx = int(round(py)), int(round(px))
        y0, y1 = max(0, cy - R_SG), min(H, cy + R_SG + 1)
        x0, x1 = max(0, cx - R_SG), min(W, cx + R_SG + 1)
        sy = slice(y0 - (cy - R_SG), y1 - (cy - R_SG))
        sx = slice(x0 - (cx - R_SG), x1 - (cx - R_SG))
        ct = np.maximum(uy_s[sy, sx] * float(vy) + ux_s[sy, sx] * float(vx), 0.0)
        sgmc_proj[y0:y1, x0:x1] = np.maximum(sgmc_proj[y0:y1, x0:x1], (ct**5) * exp_s[sy, sx])
    write_col("sgmc_basin_strike_proj_25px", sgmc_proj)

    # Save compact static physical cues for fast fold-strict 20-channel DCMS mechanics
    base_cues = np.load(base_cues_path)
    np.savez_compressed(
        cues_path,
        base_cues_path=str(base_cues_path),
        scarp_step=base_cues["scarp_step"],
        grav_bdepth=base_cues["grav_bdepth"],
        hydro=base_cues["hydro"],
        c2_topo=c2_fused[footprint].astype(np.float16),
        s2_topo=s2_fused[footprint].astype(np.float16),
        c2_geophys=c2_geophys[footprint],
        s2_geophys=s2_geophys[footprint],
        sgmc_cor6=np.exp(-d_sgmc[footprint] / 6.0).astype(np.float16),
    )

    mm98.flush()
    del mm98, mm70, sgmc, d_sgmc, sgmc_cor4, sgmc_proj, c2_fused, s2_fused, c2_geophys, s2_geophys, grav_z800, u_step_2d, det_elev_2d, along_vs_cross, d10_one3_2d
    _drop_cache(base_mmap_path)
    _drop_cache(out_path)
    gc.collect()

    meta = {
        "rows": n_fp,
        "cols": n_tot,
        "feature_names": STATIC_DCMS_NAMES,
        "base_cues_path": str(base_cues_path),
        "dcms_cues_path": str(cues_path),
        "build_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
        "forbidden_columns_blocked": sorted(FORBIDDEN_POINT_COLUMNS),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def compute_dcms_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    dcms_cues_path: Path,
) -> np.ndarray:
    """Compute all 20 fold-strict Group D channels strictly from ``visible_mask`` (zero test leakage!)."""
    H, W = footprint.shape
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    n_fp = int(footprint.sum())
    out = np.zeros((n_fp, len(MECH_DCMS_NAMES)), dtype=np.float32)
    if not np.any(vis):
        return out

    cues = np.load(dcms_cues_path)
    base_cues_path = Path(str(cues["base_cues_path"]))
    out[:, :14] = compute_base_14_mechanics(vis, footprint, base_cues_path)

    # Channel 14 (index 14): immediate unmapped strand stepover halo right outside buffer_px=3
    d_vis, (ny_idx, nx_idx) = ndi.distance_transform_edt(~vis, return_indices=True)
    d_fp = d_vis[footprint].astype(np.float32)
    out[:, 14] = np.exp(-d_fp / 3.2)

    # Channels 15 & 16: broad listric splay cone (cos^3, R=25) + long-range blind basin continuation (R=65)
    tips_yx, dirs_yx = _extract_tips_and_tangents(vis)
    broad25 = np.zeros((H, W), dtype=np.float32)
    long65 = np.zeros((H, W), dtype=np.float32)

    R_L = 65
    gy_l, gx_l = np.mgrid[-R_L : R_L + 1, -R_L : R_L + 1].astype(np.float32)
    rr_l = np.hypot(gy_l, gx_l)
    vd_l = (rr_l >= 1.0) & (rr_l <= float(R_L))
    uy_l = np.divide(gy_l, rr_l, out=np.zeros_like(gy_l), where=vd_l)
    ux_l = np.divide(gx_l, rr_l, out=np.zeros_like(gx_l), where=vd_l)
    exp_b25 = np.exp(-rr_l / 12.0) * (rr_l <= 26.0)
    exp_l65 = np.exp(-rr_l / 34.0) * vd_l

    for (py, px), (vy, vx) in zip(tips_yx, dirs_yx):
        cy, cx = int(round(py)), int(round(px))
        y0, y1 = max(0, cy - R_L), min(H, cy + R_L + 1)
        x0, x1 = max(0, cx - R_L), min(W, cx + R_L + 1)
        sy = slice(y0 - (cy - R_L), y1 - (cy - R_L))
        sx = slice(x0 - (cx - R_L), x1 - (cx - R_L))
        ct = np.maximum(uy_l[sy, sx] * float(vy) + ux_l[sy, sx] * float(vx), 0.0)
        broad25[y0:y1, x0:x1] = np.maximum(broad25[y0:y1, x0:x1], (ct**3) * exp_b25[sy, sx])
        long65[y0:y1, x0:x1] = np.maximum(long65[y0:y1, x0:x1], (ct**8) * exp_l65[sy, sx])

    # Also bridge long-range colinear visible tips across blind playas up to 68 px (6.8 km)
    if tips_yx.shape[0] >= 2:
        tree = cKDTree(tips_yx)
        for i, j in tree.query_pairs(r=68.0):
            dv = tips_yx[j] - tips_yx[i]
            dist = float(np.hypot(dv[0], dv[1]))
            if dist <= 42.0:
                continue
            uij = dv / dist
            ci_v = float(dirs_yx[i, 0] * uij[0] + dirs_yx[i, 1] * uij[1])
            cj_v = float(-dirs_yx[j, 0] * uij[0] - dirs_yx[j, 1] * uij[1])
            if ci_v > 0.72 and cj_v > 0.72:
                _draw_segment_score(long65, tips_yx[i, 0], tips_yx[i, 1], tips_yx[j, 0], tips_yx[j, 1], float(ci_v * cj_v * np.exp(-dist / 42.0)))

    long65 = ndi.gaussian_filter(long65, 1.8, mode="constant", cval=0.0)
    out[:, 15] = broad25[footprint]
    out[:, 16] = long65[footprint]

    # Channels 17 & 18: Local visible fault strand strike orientation propagated via nearest-strand EDT
    vis_sm = ndi.gaussian_filter(vis.astype(np.float32), 1.5, mode="constant", cval=0.0)
    c2_vis, s2_vis, _ = _structure_tensor_doubled_angle(vis_sm, sigma_grad=1.2, sigma_int=2.2)
    near_c2 = c2_vis[ny_idx[footprint], nx_idx[footprint]]
    near_s2 = s2_vis[ny_idx[footprint], nx_idx[footprint]]
    c2_topo_fp = cues["c2_topo"].astype(np.float32)
    s2_topo_fp = cues["s2_topo"].astype(np.float32)
    c2_geo_fp = cues["c2_geophys"].astype(np.float32)
    s2_geo_fp = cues["s2_geophys"].astype(np.float32)
    sgmc_fp = cues["sgmc_cor6"].astype(np.float32)

    out[:, 17] = (near_c2 * c2_topo_fp + near_s2 * s2_topo_fp) * np.exp(-d_fp / 20.0)
    out[:, 18] = (near_c2 * c2_geo_fp + near_s2 * s2_geo_fp) * np.exp(-d_fp / 25.0)
    out[:, 19] = np.maximum(out[:, 7], out[:, 16]) * sgmc_fp

    del d_vis, ny_idx, nx_idx, broad25, long65, vis_sm, c2_vis, s2_vis
    return out
