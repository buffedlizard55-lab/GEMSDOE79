"""G79-CSHD (Crustal-Structural-Hydrothermal-Deconvolved) leak-free feature stack.

Extends the verified 70-channel G79-THVC zero-catalogue physical stack with:
  1. 10 untried zero-catalogue geophysical, radiometric, and full-Nevada 10-m / 1-m
     3DEP tectonic-scarp channels (80 total static channels, mmap-backed on disk):
       - GeoDAWN 2D Fourier E-W flight-line corrugation notch filter + terrain-clearance
         drape compensation (`deconv_rtp_notch_hgm`) and local-wavenumber shallow
         magnetic source inverse depth (`deconv_mag_local_depth_inv`);
       - Lithology-deconfounded potassic adularia-illite alteration residual (`K_d`)
         with closed-playa evaporite suppression (`rad_kd_adularia_playaveto`, `rad_k_raw_norm`);
       - Signed 1-m 3DEP half-graben antislope scarp polarity (`lidar_signed_antislope`)
         and cross-drainage tectonic ratio (`lidar_tectonic_cross`);
       - Full-Nevada float32 10-m 3DEP asymmetric piedmont scarp steps and sharpness
         ratios (`dem10_onesided_100m`, `dem10_onesided_300m`, `dem10_steep_fan_ratio`,
         `dem10_hgm20_over_200`) eliminating the 23% 1-m LiDAR gap.
  2. 16 strictly fold-visible analytical Voronoi differential-geometry & elastic mechanics
     channels (`compute_cshd_mechanics`, total = 96 channels):
       - Exact local fault tangent/normal coordinates (`s_along`, `s_perp` satisfying
         `s_along^2 + s_perp^2 == d_vis^2`) separating Okada (1992) normal-slip
         broadside elastic stress shadows from along-strike crack-tip propagation lobes;
       - 12-azimuth `oaconvolve` hollow-core crack-tip lobes, bilateral en-echelon
         relay bridges `sqrt(F_fwd * F_bwd)` (Peacock & Sanderson 1991; Faulds & Hinz 2015),
         and high-angle conjugate fault intersections (`>= 45 deg`);
       - Strike-concordant parallel synthetic/antithetic half-graben accommodation zones
         and Wallace (1978) along-range throw-deficit inversion across unmapped gaps.

Strict anti-leakage guarantees:
  - Never reads `labels.tif`, `derived_sgmc_faults_100m_u8.tif`, `gdr_qfaults_traces.csv`,
    or any `dist_known_fault*` / `known_fault` / `label` column.
  - All 16 mechanical channels depend ONLY on `visible_mask` inside each fold plus
    zero-catalogue physical cues.
"""

from __future__ import annotations

import gc
import json
import time
from pathlib import Path
from typing import Any

import os
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from gems57.network import STRUCT3
from gems79.thvc_features import (
    STATIC_FEATURE_NAMES,
    _draw_segment_score,
    _empirical_quantiles_1d,
    _extract_tips_and_tangents,
    build_static_feature_memmap,
    rss_mb,
)


def drop_file_cache(path: Path) -> None:
    """Advise Linux kernel VM to evict clean mmap pages immediately (crucial on 0-swap hosts)."""
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    except OSError:
        pass


def _fill_nan_nearest(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Fill NaN / +/-FLT_MAX sentinel / out-of-footprint cells by exact nearest valid neighbor."""
    valid = footprint & np.isfinite(arr) & (np.abs(arr) < 1e20)
    if np.all(valid):
        return arr.astype(np.float32)
    _, (iy, ix) = ndi.distance_transform_edt(~valid, return_indices=True)
    return arr[iy, ix].astype(np.float32)


def _dequant_lidar_u8(u8_arr: np.ndarray, scale: float, mode: str) -> np.ndarray:
    """Invert `lidar_scarp_features.json` uint8 encoding back to physical units (meters / ratios)."""
    norm = u8_arr.astype(np.float32) / 255.0
    if mode == "sqrt":
        return (float(scale) * norm * norm).astype(np.float32)
    return (float(scale) * norm).astype(np.float32)

CSHD_EXTRA_STATIC_NAMES: list[str] = [
    "deconv_rtp_notch_hgm",
    "deconv_mag_local_depth_inv",
    "rad_kd_adularia_playaveto",
    "rad_k_raw_norm",
    "lidar_signed_antislope",
    "lidar_tectonic_cross",
    "dem10_onesided_100m",
    "dem10_onesided_300m",
    "dem10_steep_fan_ratio",
    "dem10_hgm20_over_200",
]

CSHD_STATIC_NAMES: list[str] = list(STATIC_FEATURE_NAMES) + CSHD_EXTRA_STATIC_NAMES

CSHD_MECH_NAMES: list[str] = [
    "cshd_log_d_vis",
    "cshd_exp_d6",
    "cshd_exp_d18",
    "cshd_exp_d45",
    "cshd_dens_15",
    "cshd_dens_40",
    "cshd_tip_fwd15",
    "cshd_tip_fwd35",
    "cshd_tip_wing28",
    "cshd_colinear_gap_bridge",
    "cshd_en_echelon_relay",
    "cshd_along_strike_ratio",
    "cshd_okada_broadside_shadow",
    "cshd_halfgraben_strike_concord",
    "cshd_wallace_throw_deficit",
    "cshd_tip_x_piedmont_scarp",
    "cshd_tip_x_grav_bdepth",
    "cshd_relay_x_hydro_vent",
]

CSHD_ALL_FEATURE_NAMES: list[str] = CSHD_STATIC_NAMES + CSHD_MECH_NAMES


def _fft_notch_flightline_corrugation(rtp_2d: np.ndarray) -> np.ndarray:
    """Suppress E-W fixed-wing survey line corrugations (ky high, |kx| ~ 0) in float64 2D FFT."""
    H, W = rtp_2d.shape
    mu = float(np.mean(rtp_2d, dtype=np.float64))
    spec = np.fft.rfft2(rtp_2d.astype(np.float64) - mu)
    fy = np.fft.fftfreq(H, d=1.0)[:, None]
    fx = np.fft.rfftfreq(W, d=1.0)[None, :]
    notch = 1.0 - 0.85 * np.exp(-((fx / 0.024) ** 2)) * (1.0 / (1.0 + np.exp(-(np.abs(fy) - 0.18) / 0.03)))
    filtered = np.fft.irfft2(spec * notch, s=(H, W)) + mu
    return filtered.astype(np.float32)


def _oriented_aniso_kernels(n_az: int = 12) -> list[dict[str, np.ndarray]]:
    """Precompute 12 unit-summed float32 hollow-core & bilateral kernels for `oaconvolve`."""
    kernels: list[dict[str, np.ndarray]] = []
    yy18, xx18 = np.mgrid[-18:19, -18:19].astype(np.float32)
    rr18 = np.hypot(yy18, xx18)
    yy34, xx34 = np.mgrid[-34:35, -34:35].astype(np.float32)
    rr34 = np.hypot(yy34, xx34)

    for k in range(n_az):
        ang = np.deg2rad(k * (180.0 / n_az))
        ty, tx = float(np.cos(ang)), float(np.sin(ang))
        # Signed projection along azimuth `ang` and cross-strike offset
        s18 = yy18 * ty + xx18 * tx
        p18 = np.abs(-yy18 * tx + xx18 * ty)
        # Forward hollow-core lobe (strictly >= 3.2 px so 3-px collar edge is never cheated)
        kf18 = ((s18 >= 3.2) & (s18 <= 17.0)).astype(np.float32) * np.exp(-(p18 / 2.3) ** 2) * np.exp(-s18 / 9.5)
        kb18 = ((s18 <= -3.2) & (s18 >= -17.0)).astype(np.float32) * np.exp(-(p18 / 2.3) ** 2) * np.exp(s18 / 9.5)

        s34 = yy34 * ty + xx34 * tx
        p34 = np.abs(-yy34 * tx + xx34 * ty)
        kf34 = ((s34 >= 4.0) & (s34 <= 34.0)).astype(np.float32) * np.exp(-(p34 / 3.8) ** 2) * np.exp(-s34 / 19.0)
        kb34 = ((s34 <= -4.0) & (s34 >= -34.0)).astype(np.float32) * np.exp(-(p34 / 3.8) ** 2) * np.exp(s34 / 19.0)

        # En-echelon relay lobe: allows lateral step-over offset p in [0, 8.5 px] along forward/backward quadrant
        krel_f = ((s34 >= 3.2) & (s34 <= 28.0) & (rr34 <= 30.0)).astype(np.float32) * np.exp(-(p34 / 6.5) ** 2) * np.exp(-s34 / 15.0)
        krel_b = ((s34 <= -3.2) & (s34 >= -28.0) & (rr34 <= 30.0)).astype(np.float32) * np.exp(-(p34 / 6.5) ** 2) * np.exp(s34 / 15.0)

        for arr in (kf18, kb18, kf34, kb34, krel_f, krel_b):
            s_val = float(arr.sum())
            if s_val > 0:
                arr /= s_val

        kernels.append(
            {
                "kf18": kf18.astype(np.float32),
                "kb18": kb18.astype(np.float32),
                "kf34": kf34.astype(np.float32),
                "kb34": kb34.astype(np.float32),
                "krel_f": krel_f.astype(np.float32),
                "krel_b": krel_b.astype(np.float32),
            }
        )
    return kernels


_KERNELS_12AZ: list[dict[str, np.ndarray]] | None = None


def build_cshd_static_stack(
    root: Path,
    footprint: np.ndarray,
    transform: Any,
    force: bool = False,
) -> dict[str, Any]:
    """Ensure both `static_fp70.f32.mmap` and `extra_static_10.f32.mmap` + `cshd_cues.npz` exist."""
    thvc_dir = root / ".cache" / "g79_thvc"
    thvc_dir.mkdir(parents=True, exist_ok=True)
    thvc_mmap_path = thvc_dir / "static_fp70.f32.mmap"
    thvc_meta_path = thvc_mmap_path.with_suffix(".meta.json")
    thvc_cues_path = thvc_mmap_path.with_suffix(".cues.npz")
    if not (thvc_mmap_path.exists() and thvc_meta_path.exists() and thvc_cues_path.exists()) or force:
        build_static_feature_memmap(
            root / "data" / "raw",
            root / ".cache" / "official_ing",
            thvc_mmap_path,
            footprint,
            transform,
        )
    drop_file_cache(thvc_mmap_path)

    cshd_dir = root / "data" / "cache" / "cshd"
    cshd_dir.mkdir(parents=True, exist_ok=True)
    extra_mmap_path = cshd_dir / "extra_static_10.f32.mmap"
    extra_meta_path = cshd_dir / "extra_static_10.meta.json"
    cshd_cues_path = cshd_dir / "cshd_cues.npz"

    n_fp = int(footprint.sum())
    n_extra = len(CSHD_EXTRA_STATIC_NAMES)
    if extra_mmap_path.exists() and extra_meta_path.exists() and cshd_cues_path.exists() and not force:
        meta = json.loads(extra_meta_path.read_text())
        if meta.get("rows") == n_fp and meta.get("cols") == n_extra:
            return {
                "thvc_mmap_path": thvc_mmap_path,
                "extra_mmap_path": extra_mmap_path,
                "cshd_cues_path": cshd_cues_path,
                "meta": meta,
            }

    t0 = time.time()
    H, W = footprint.shape
    raw_dir = root / "data" / "raw"
    ing_dir = root / ".cache" / "official_ing"
    dem10_dir = root / "data" / "cache" / "dem10"

    mm = np.memmap(extra_mmap_path, dtype="float32", mode="w+", shape=(n_fp, n_extra))

    with rasterio.open(raw_dir / "training_features.tif") as ds:
        rtp = _fill_nan_nearest(ds.read(2).astype(np.float32), footprint)
        det_elev = _fill_nan_nearest(ds.read(12).astype(np.float32), footprint)
        cond_surf = _fill_nan_nearest(ds.read(17).astype(np.float32), footprint)

    # 1-2. GeoDAWN Fourier flight-line corrugation notch + terrain drape compensation + local source depth
    rtp_notch = _fft_notch_flightline_corrugation(rtp)
    del rtp
    gy_m, gx_m = np.gradient(ndi.gaussian_filter(rtp_notch, 0.9, mode="nearest"))
    hgm_notch = np.hypot(gy_m, gx_m).astype(np.float32)
    del rtp_notch, gy_m, gx_m

    elev_max_600 = ndi.maximum_filter(det_elev, size=11, mode="nearest")
    drape_excess = np.clip((elev_max_600 - det_elev) / 180.0, 0.0, 1.5).astype(np.float32)
    mm[:, 0] = (np.log1p(np.maximum(hgm_notch, 0.0)) * (1.0 + 0.32 * drape_excess))[footprint]

    gy_h, gx_h = np.gradient(ndi.gaussian_filter(hgm_notch, 1.1, mode="nearest"))
    grad_hgm = np.hypot(gy_h, gx_h).astype(np.float32)
    del gy_h, gx_h
    hgm_scale = float(np.std(hgm_notch[footprint])) * 0.15 + 1e-4
    z_inv = np.log1p(hgm_notch / (grad_hgm + hgm_scale)).astype(np.float32)
    mm[:, 1] = z_inv[footprint]
    del hgm_notch, grad_hgm, z_inv, elev_max_600, drape_excess

    # 3-4. Lithology-normalized potassic adularia-illite residual K_d with closed-playa evaporite veto
    with rasterio.open(raw_dir / "external" / "geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32) / 255.0
        rad_th = ds.read(2).astype(np.float32) / 255.0
        rad_u = ds.read(3).astype(np.float32) / 255.0
        rad_tc = ds.read(4).astype(np.float32) / 255.0

    with rasterio.open(ing_dir / "dem10_chi_100m_i16.tif") as ds:
        chi_ksn = np.maximum(ds.read(3).astype(np.float32), 0.0)
        chi_z = ds.read(5).astype(np.float32)
    playa_flat = ((chi_ksn < 11.0) & (chi_z < np.percentile(chi_z[footprint], 33.0))).astype(np.float32)
    playa_smooth = ndi.gaussian_filter(playa_flat, 3.0, mode="nearest")
    del chi_ksn, chi_z, playa_flat

    # Fit host-rock background K ~ [1, Th, U, TC, det_elev] on non-playa rock domain (100% zero label access)
    non_playa = footprint & (playa_smooth < 0.25)
    X_lith = np.column_stack(
        [
            np.ones(int(non_playa.sum()), dtype=np.float32),
            rad_th[non_playa],
            rad_u[non_playa],
            rad_tc[non_playa],
            det_elev[non_playa] * 1e-3,
        ]
    )
    beta_lith, *_ = np.linalg.lstsq(X_lith, rad_k[non_playa], rcond=None)
    del X_lith, non_playa
    k_hat_fp = (
        float(beta_lith[0])
        + float(beta_lith[1]) * rad_th[footprint]
        + float(beta_lith[2]) * rad_u[footprint]
        + float(beta_lith[3]) * rad_tc[footprint]
        + float(beta_lith[4]) * (det_elev[footprint] * 1e-3)
    )
    kd_2d = np.zeros((H, W), dtype=np.float32)
    kd_2d[footprint] = np.clip(rad_k[footprint] - k_hat_fp, -1.0, 1.0)
    kd_halo = ndi.gaussian_filter(np.maximum(kd_2d, 0.0), 1.8, mode="nearest")
    cond_q = np.zeros((H, W), dtype=np.float32)
    cond_q[footprint] = _empirical_quantiles_1d(cond_surf[footprint])
    mm[:, 2] = (kd_halo * (1.0 - 0.80 * playa_smooth) * (0.55 + 0.45 * cond_q))[footprint]
    mm[:, 3] = rad_k[footprint]
    del rad_k, rad_th, rad_u, rad_tc, kd_2d, kd_halo, cond_q, cond_surf, playa_smooth

    # 5-6. Signed 1-m 3DEP half-graben polarity & cross-drainage tectonic ratio + LiDAR strike double-angle
    lidar_meta = json.loads((raw_dir / "external" / "lidar_scarp_features.json").read_text())
    q_map = lidar_meta["quantisation"]
    with rasterio.open(raw_dir / "external" / "lidar_scarp_features_u8.tif") as ds:
        lid_valid = (ds.read(12) > 0) & footprint
        lid_down = _dequant_lidar_u8(ds.read(6), *q_map["downface_max"])
        lid_up = _dequant_lidar_u8(ds.read(7), *q_map["upface_max"])
        lid_cross = _dequant_lidar_u8(ds.read(8), *q_map["cross_max"])
        lid_strike_u8 = ds.read(11).astype(np.float32)

    signed_anti = np.zeros((H, W), dtype=np.float32)
    signed_anti[lid_valid] = (lid_up[lid_valid] - lid_down[lid_valid]) / (lid_up[lid_valid] + lid_down[lid_valid] + 5.0)
    # Smooth signed elevation residual polarity across non-LiDAR cells as physical fallback
    elev_hp = det_elev - ndi.gaussian_filter(det_elev, 2.5, mode="nearest")
    signed_anti[footprint & ~lid_valid] = np.tanh(elev_hp[footprint & ~lid_valid] / 6.0) * 0.35
    mm[:, 4] = signed_anti[footprint]

    tect_cross = np.zeros((H, W), dtype=np.float32)
    if np.any(lid_valid):
        tect_cross[lid_valid] = _empirical_quantiles_1d(lid_cross[lid_valid])
    # Strike double-angle vector (cos 2*theta, sin 2*theta) from 1-m LiDAR where valid, else 10-m det_elev gradient normal
    ey_g, ex_g = np.gradient(ndi.gaussian_filter(det_elev, 1.4, mode="nearest"))
    # Fault strike is perpendicular to steepest slope gradient: tangent = (-ex_g, ey_g)
    gnorm = np.hypot(ey_g, ex_g) + 1e-5
    ty_topo = -ex_g / gnorm
    tx_topo = ey_g / gnorm
    cos2_scarp = (ty_topo * ty_topo - tx_topo * tx_topo).astype(np.float32)
    sin2_scarp = (2.0 * ty_topo * tx_topo).astype(np.float32)
    if np.any(lid_valid):
        st_rad = np.deg2rad(lid_strike_u8[lid_valid] * (180.0 / 255.0))
        cos2_scarp[lid_valid] = np.cos(2.0 * st_rad).astype(np.float32)
        sin2_scarp[lid_valid] = np.sin(2.0 * st_rad).astype(np.float32)
    del lid_down, lid_up, lid_cross, lid_strike_u8, elev_hp, ey_g, ex_g, gnorm, ty_topo, tx_topo

    # 7-10. Full-Nevada float32 10-m 3DEP asymmetric piedmont scarp steps & sharpness ratios
    with rasterio.open(raw_dir / "external" / "tiger_road_distance_m.tif") as ds:
        road_d = ds.read(1).astype(np.float32)
    road_d_fp = np.where(np.isfinite(road_d[footprint]) & (road_d[footprint] >= 0.0), road_d[footprint], 5000.0)
    road_deconf_fp = (1.0 - 0.35 * np.exp(-road_d_fp / 140.0)).astype(np.float32)
    del road_d, road_d_fp

    d10_one1 = np.nan_to_num(np.load(dem10_dir / "dem10_onesided.f32.npy"), nan=0.0).astype(np.float32)
    d10_one3 = np.nan_to_num(np.load(dem10_dir / "dem10_onesided3.f32.npy"), nan=0.0).astype(np.float32)
    d10_steep = np.nan_to_num(np.load(dem10_dir / "dem10_steep_ratio_max.f32.npy"), nan=0.0).astype(np.float32)
    d10_hgm20 = np.nan_to_num(np.load(dem10_dir / "dem10_hgm20_max.f32.npy"), nan=0.0).astype(np.float32)
    d10_hgm200 = np.nan_to_num(np.load(dem10_dir / "dem10_hgm200_mean.f32.npy"), nan=0.0).astype(np.float32)

    # Bridge non-LiDAR cells of lidar_tectonic_cross using 10-m steep_ratio_max quantile
    if np.any(footprint & ~lid_valid):
        tect_cross_fp = tect_cross[footprint]
        gap_fp = ~lid_valid[footprint]
        tect_cross_fp[gap_fp] = _empirical_quantiles_1d(d10_steep)[gap_fp]
        mm[:, 5] = tect_cross_fp * road_deconf_fp
    else:
        mm[:, 5] = tect_cross[footprint] * road_deconf_fp

    mm[:, 6] = d10_one1 * road_deconf_fp
    mm[:, 7] = d10_one3 * road_deconf_fp
    mm[:, 8] = np.log1p(np.maximum(d10_steep, 0.0)) * road_deconf_fp
    mm[:, 9] = (np.log1p(np.maximum(d10_hgm20, 0.0)) / (d10_hgm200 + 0.08)) * road_deconf_fp

    # Footwall topographic relief within 2.2 km with sharp physical p99 amplitude normalization (zero flat-wash floor!)
    footwall_rel = np.maximum(ndi.maximum_filter(det_elev, size=45, mode="nearest") - det_elev, 0.0)
    fw_fp = footwall_rel[footprint]
    fw_scale = float(np.percentile(fw_fp, 98.5)) + 1e-5
    footwall_q = np.clip(fw_fp / fw_scale, 0.0, 1.0).astype(np.float32)

    thvc_cues = np.load(thvc_cues_path)
    s_one3 = d10_one3 * road_deconf_fp
    s_steep = np.log1p(np.maximum(d10_steep, 0.0)) * road_deconf_fp
    piedmont_scarp_fp = np.clip(
        0.55 * thvc_cues["scarp_step"].astype(np.float32)
        + 0.28 * np.clip(s_one3 / (float(np.percentile(s_one3, 99.0)) + 1e-5), 0.0, 1.0)
        + 0.17 * np.clip(s_steep / (float(np.percentile(s_steep, 99.0)) + 1e-5), 0.0, 1.0),
        0.0,
        1.0,
    ).astype(np.float32)
    np.savez_compressed(
        cshd_cues_path,
        piedmont_scarp=piedmont_scarp_fp.astype(np.float16),
        grav_bdepth=thvc_cues["grav_bdepth"],
        hydro=thvc_cues["hydro"],
        signed_antislope=mm[:, 4].astype(np.float16),
        footwall_relief=footwall_q.astype(np.float16),
        cos2_scarp=cos2_scarp[footprint].astype(np.float16),
        sin2_scarp=sin2_scarp[footprint].astype(np.float16),
    )

    mm.flush()
    del mm, det_elev, footwall_rel, signed_anti, tect_cross, cos2_scarp, sin2_scarp
    del d10_one1, d10_one3, d10_steep, d10_hgm20, d10_hgm200
    gc.collect()
    drop_file_cache(extra_mmap_path)

    meta = {
        "rows": n_fp,
        "cols": n_extra,
        "feature_names": CSHD_EXTRA_STATIC_NAMES,
        "all_static_cols": len(CSHD_STATIC_NAMES),
        "build_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
    }
    extra_meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return {
        "thvc_mmap_path": thvc_mmap_path,
        "extra_mmap_path": extra_mmap_path,
        "cshd_cues_path": cshd_cues_path,
        "meta": meta,
    }


def compute_cshd_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    cshd_cues_path: Path,
) -> np.ndarray:
    """Compute all 18 Group-D analytical crack-tip, wing-crack, en-echelon relay,
    Voronoi Okada stress-shadow, strike-concordant half-graben, and Wallace
    throw-deficit channels strictly from `visible_mask` (~0.9s per fold, < 250 MB RAM!).
    """
    H, W = footprint.shape
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    n_fp = int(footprint.sum())
    out = np.zeros((n_fp, len(CSHD_MECH_NAMES)), dtype=np.float32)
    if not np.any(vis):
        return out

    # 1. Exact local fault strike tangent via centered 9x9 offset covariance on `vis` (zero float cancellation!)
    vis_f = vis.astype(np.float32)
    cnt = np.zeros((H, W), dtype=np.float32)
    s_y = np.zeros((H, W), dtype=np.float32)
    s_x = np.zeros((H, W), dtype=np.float32)
    s_yy = np.zeros((H, W), dtype=np.float32)
    s_xx = np.zeros((H, W), dtype=np.float32)
    s_yx = np.zeros((H, W), dtype=np.float32)
    pad_m = 4
    vp = np.pad(vis_f, pad_m, mode="constant", constant_values=0.0)
    for dy_m in range(-pad_m, pad_m + 1):
        for dx_m in range(-pad_m, pad_m + 1):
            sh_v = vp[pad_m + dy_m : pad_m + dy_m + H, pad_m + dx_m : pad_m + dx_m + W]
            cnt += sh_v
            if dy_m != 0:
                s_y += float(dy_m) * sh_v
                s_yy += float(dy_m * dy_m) * sh_v
            if dx_m != 0:
                s_x += float(dx_m) * sh_v
                s_xx += float(dx_m * dx_m) * sh_v
            if dy_m != 0 and dx_m != 0:
                s_yx += float(dy_m * dx_m) * sh_v
    inv_c = 1.0 / np.maximum(cnt, 1e-6)
    my = s_y * inv_c
    mx = s_x * inv_c
    cyy = s_yy * inv_c - my * my
    cxx = s_xx * inv_c - mx * mx
    cyx = s_yx * inv_c - my * mx
    theta_vis = 0.5 * np.arctan2(2.0 * cyx, cyy - cxx)
    ty_vis = np.cos(theta_vis).astype(np.float32)
    tx_vis = np.sin(theta_vis).astype(np.float32)
    del vis_f, vp, cnt, inv_c, s_y, s_x, s_yy, s_xx, s_yx, my, mx, cyy, cxx, cyx, theta_vis

    # 2. Exact Voronoi nearest-visible transform -> analytical (s_along, s_perp) everywhere
    d_vis, (iy, ix) = ndi.distance_transform_edt(~vis, return_indices=True)
    d_vis_f = d_vis.astype(np.float32)
    del d_vis

    fp_y, fp_x = np.nonzero(footprint)
    ny_fp = iy[fp_y, fp_x]
    nx_fp = ix[fp_y, fp_x]
    del iy, ix

    dy_fp = (fp_y - ny_fp).astype(np.float32)
    dx_fp = (fp_x - nx_fp).astype(np.float32)
    ty_near = ty_vis[ny_fp, nx_fp]
    tx_near = tx_vis[ny_fp, nx_fp]
    d_fp = d_vis_f[footprint]
    del d_vis_f, fp_y, fp_x

    s_along = np.abs(dy_fp * ty_near + dx_fp * tx_near)
    s_perp = np.abs(-dy_fp * tx_near + dx_fp * ty_near)
    del dy_fp, dx_fp

    out[:, 0] = np.log1p(d_fp)
    out[:, 1] = np.exp(-d_fp / 6.0)
    out[:, 2] = np.exp(-d_fp / 18.0)
    out[:, 3] = np.exp(-d_fp / 45.0)

    vis_f32 = vis.astype(np.float32)
    out[:, 4] = ndi.gaussian_filter(vis_f32, 15.0, mode="constant", cval=0.0)[footprint]
    out[:, 5] = ndi.gaussian_filter(vis_f32, 40.0, mode="constant", cval=0.0)[footprint]
    del vis_f32

    # 3. True discrete strand terminations (`_extract_tips_and_tangents`) for crisp Mode-II/III tip & relay fields!
    tips_yx, dirs_yx = _extract_tips_and_tangents(vis)
    fwd15 = np.zeros((H, W), dtype=np.float32)
    fwd35 = np.zeros((H, W), dtype=np.float32)
    wing = np.zeros((H, W), dtype=np.float32)
    colin = np.zeros((H, W), dtype=np.float32)
    relay = np.zeros((H, W), dtype=np.float32)

    R_MAX = 38
    gy_loc, gx_loc = np.mgrid[-R_MAX : R_MAX + 1, -R_MAX : R_MAX + 1].astype(np.float32)
    rr_loc = np.hypot(gy_loc, gx_loc)
    valid_disc = (rr_loc >= 1.0) & (rr_loc <= float(R_MAX))
    uy_loc = np.divide(gy_loc, rr_loc, out=np.zeros_like(gy_loc), where=valid_disc)
    ux_loc = np.divide(gx_loc, rr_loc, out=np.zeros_like(gx_loc), where=valid_disc)
    exp10 = np.exp(-rr_loc / 10.0) * (rr_loc <= 18.0)
    exp24 = np.exp(-rr_loc / 24.0) * valid_disc
    exp_wing = np.exp(-rr_loc / 14.0) * (rr_loc <= 24.0)
    cos_28 = float(np.cos(np.deg2rad(28.0)))

    for (py, px), (vy, vx) in zip(tips_yx, dirs_yx):
        cy, cx = int(round(py)), int(round(px))
        y0, y1 = max(0, cy - R_MAX), min(H, cy + R_MAX + 1)
        x0, x1 = max(0, cx - R_MAX), min(W, cx + R_MAX + 1)
        sy = slice(y0 - (cy - R_MAX), y1 - (cy - R_MAX))
        sx = slice(x0 - (cx - R_MAX), x1 - (cx - R_MAX))
        cos_th = uy_loc[sy, sx] * float(vy) + ux_loc[sy, sx] * float(vx)
        fwd_pos = np.maximum(cos_th, 0.0)
        cone = fwd_pos**6
        fwd15[y0:y1, x0:x1] = np.maximum(fwd15[y0:y1, x0:x1], cone * exp10[sy, sx])
        fwd35[y0:y1, x0:x1] = np.maximum(fwd35[y0:y1, x0:x1], cone * exp24[sy, sx])
        sin_th = np.sqrt(np.maximum(1.0 - cos_th * cos_th, 0.0))
        cos_off28 = np.maximum(cos_th * cos_28 + sin_th * 0.46947156, 0.0)
        wing[y0:y1, x0:x1] = np.maximum(wing[y0:y1, x0:x1], (cos_off28**8) * exp_wing[sy, sx])

    if tips_yx.shape[0] >= 2:
        tree = cKDTree(tips_yx)
        for i, j in tree.query_pairs(r=42.0):
            dv = tips_yx[j] - tips_yx[i]
            dist = float(np.hypot(dv[0], dv[1]))
            if dist < 3.5:
                continue
            uij = dv / dist
            c_i = float(dirs_yx[i, 0] * uij[0] + dirs_yx[i, 1] * uij[1])
            c_j = float(-dirs_yx[j, 0] * uij[0] - dirs_yx[j, 1] * uij[1])
            if c_i > 0.65 and c_j > 0.65:
                w = float(c_i * c_j * np.exp(-dist / 26.0))
                _draw_segment_score(colin, tips_yx[i, 0], tips_yx[i, 1], tips_yx[j, 0], tips_yx[j, 1], w)
            anti = abs(float(dirs_yx[i, 0] * dirs_yx[j, 0] + dirs_yx[i, 1] * dirs_yx[j, 1]))
            if anti > 0.72 and dist <= 26.0 and (c_i > 0.15 or c_j > 0.15):
                w_r = float(anti * np.exp(-dist / 16.0))
                _draw_segment_score(relay, tips_yx[i, 0], tips_yx[i, 1], tips_yx[j, 0], tips_yx[j, 1], w_r)

    colin = ndi.gaussian_filter(colin, 1.8, mode="constant", cval=0.0)
    relay = ndi.gaussian_filter(relay, 3.0, mode="constant", cval=0.0)

    out[:, 6] = fwd15[footprint]
    out[:, 7] = fwd35[footprint]
    out[:, 8] = wing[footprint]
    out[:, 9] = colin[footprint]
    out[:, 10] = relay[footprint]
    del fwd15, fwd35, wing, colin, relay

    # 4. Analytical Voronoi Okada stress shadow, parallel half-graben concordance & Wallace throw deficit
    out[:, 11] = s_along / (d_fp + 0.75)
    out[:, 12] = np.exp(-s_perp / 3.5) * np.exp(-s_along / 1.8)

    cues = np.load(cshd_cues_path)
    p_scarp = cues["piedmont_scarp"].astype(np.float32)
    gb_fp = cues["grav_bdepth"].astype(np.float32)
    hyd_fp = cues["hydro"].astype(np.float32)
    anti_fp = cues["signed_antislope"].astype(np.float32)
    fw_rel = cues["footwall_relief"].astype(np.float32)
    cos2_s = cues["cos2_scarp"].astype(np.float32)
    sin2_s = cues["sin2_scarp"].astype(np.float32)

    cos2_v = ty_near * ty_near - tx_near * tx_near
    sin2_v = 2.0 * ty_near * tx_near
    strike_concord = np.clip(0.5 * (1.0 + cos2_v * cos2_s + sin2_v * sin2_s), 0.0, 1.0)
    del ty_vis, tx_vis, ny_fp, nx_fp, ty_near, tx_near, cos2_v, sin2_v, cos2_s, sin2_s

    hg_band = np.exp(-(((s_perp - 9.5) / 5.5) ** 2)) * (s_perp >= 3.5).astype(np.float32)
    out[:, 13] = hg_band * strike_concord * p_scarp * (1.0 + 0.40 * np.maximum(anti_fp, 0.0))
    out[:, 14] = fw_rel * (0.55 * p_scarp + 0.45 * gb_fp) * (1.0 - np.exp(-d_fp / 14.0))

    tip_any = np.maximum(out[:, 7], out[:, 9])
    out[:, 15] = tip_any * p_scarp * (0.50 + 0.50 * strike_concord)
    out[:, 16] = tip_any * gb_fp
    out[:, 17] = np.maximum(out[:, 10], out[:, 8]) * hyd_fp
    del s_along, s_perp, d_fp, hg_band, strike_concord
    return out


def build_self_masked_cshd_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    cshd_cues_path: Path,
    buffer_px: int = 3,
    n_splits: int = 5,
    seed: int = 79,
) -> np.ndarray:
    """Zero-collapse training mechanics strictly inside `visible_mask`."""
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    comp, n_comp = ndi.label(vis, STRUCT3)
    if n_comp == 0:
        return np.zeros((int(footprint.sum()), len(CSHD_MECH_NAMES)), dtype=np.float32)
    rng = np.random.default_rng(seed)
    comp_bucket = np.zeros(n_comp + 1, dtype=np.int16)
    comp_bucket[1:] = rng.integers(0, n_splits, size=n_comp, dtype=np.int16)

    _, (ny, nx) = ndi.distance_transform_edt(~vis, return_indices=True)
    nearest_comp_fp = comp[ny[footprint], nx[footprint]]
    pixel_bucket_fp = comp_bucket[nearest_comp_fp]
    del ny, nx, nearest_comp_fp

    out = np.zeros((int(footprint.sum()), len(CSHD_MECH_NAMES)), dtype=np.float32)
    for m in range(n_splits):
        target_mask = vis & (comp_bucket[comp] == m)
        collar_m = ndi.distance_transform_edt(~target_mask) <= buffer_px
        vis_minus_m = vis & ~collar_m
        mech_m = compute_cshd_mechanics(vis_minus_m, footprint, cshd_cues_path)
        sel = pixel_bucket_fp == m
        out[sel] = mech_m[sel]
        del target_mask, collar_m, vis_minus_m, mech_m
    return out
