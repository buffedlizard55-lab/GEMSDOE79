"""G79-CSKD: Lahontan Equipotential Isohypse & BLM Mine-Deconfounded Multi-Physics,
Flight-Notched Magnetics, Cross-Regressed Potassic Adularia Kd, Elastic Coulomb Stress-Shadow
& Along-Range Slip-Deficit Counterfactual Charnes-Cooper Discovery.

All static transforms are 100% label-free physical/geomorphic/survey operators.
All network/Coulomb/slip-deficit transforms take an explicit ``visible_mask`` and never
access withheld holdout faults. Shared ``vendor/gems57/*`` modules are reused unmodified.
"""
from __future__ import annotations

import gc
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
    _empirical_quantiles_1d,
    build_static_feature_memmap,
    compute_network_mechanics,
    rss_mb,
)
from gems79.thvc_model import (
    STAGE2_FEATURE_NAMES,
    charnes_cooper_submodular_emit,
    drop_file_cache,
    extract_stage2_spatial_features,
    fit_stage1_ensemble,
    fit_stage2_dual_heads,
    poisson_disk_emit,
    predict_stage1_rows,
    predict_stage2_dual_heads,
)

CSKD_EXTRA_STATIC_NAMES: list[str] = [
    "abs_elev_km",
    "basin_floor_closure",
    "lahontan_isohypse_env",
    "scarp_strike_elev_climb",
    "lahontan_shoreline_veto",
    "scarp_lahontan_mine_clean",
    "blm_mine_prox_350m",
    "blm_log_dist_m",
    "geodawn_area1_hires",
    "rtp_flight_notched_hgm",
    "mag_local_wavenumber_kloc",
    "rad_tc_total_count",
    "rad_kd_adularia_resid",
    "rad_kd_clean_conduit",
]

CSKD_STATIC_NAMES: list[str] = STATIC_FEATURE_NAMES + CSKD_EXTRA_STATIC_NAMES

CSKD_EXTRA_MECH_NAMES: list[str] = [
    "net_coulomb_shadow",
    "net_coulomb_oblique_lobe",
    "net_slip_deficit_front",
    "net_clean_scarp_x_slipdef",
]

CSKD_MECH_NAMES: list[str] = MECH_FEATURE_NAMES + CSKD_EXTRA_MECH_NAMES
CSKD_ALL_FEATURE_NAMES: list[str] = CSKD_STATIC_NAMES + CSKD_MECH_NAMES


def _release_mm(mm: np.memmap, mmap_path: Path) -> None:
    """Release active PTE pages from RSS via madvise(MADV_DONTNEED) + posix_fadvise."""
    try:
        if getattr(mm, "_mmap", None) is not None:
            mm._mmap.madvise(mmap.MADV_DONTNEED)
    except Exception:
        pass
    drop_file_cache(mmap_path)


def _infill_2d_sentinels(arr: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    """Nearest-neighbor Euclidean infill of sentinel/NaN cells across the full 2D grid."""
    out = np.asarray(arr, dtype=np.float32).copy()
    if np.all(valid_mask):
        return out
    if not np.any(valid_mask):
        return np.zeros_like(out, dtype=np.float32)
    _, (iy, ix) = ndi.distance_transform_edt(~valid_mask, return_indices=True)
    bad = ~valid_mask
    out[bad] = out[iy[bad], ix[bad]]
    return out


def _fft_flightline_notch_and_kloc(rtp_2d: np.ndarray, dx_m: float = 100.0) -> tuple[np.ndarray, np.ndarray]:
    """2D Fourier E-W survey flight-line micro-leveling notch + Thurston-Smith (1997) local wavenumber.

    GeoDAWN Area 2 was flown along E-W lines spaced 400 m apart (Nyquist/2 on a 100-m grid),
    creating N-S wavenumber corrugations (large |k_y|, near-zero |k_x|). We apply a smooth
    directional Gaussian notch centered on k_x ~ 0 for |k_y| >= 2*pi / 650 m combined with
    z = 150 m upward continuation to stabilize phase derivatives, then evaluate:
      1. Notched horizontal gradient magnitude ||grad RTP_notched||
      2. Local wavenumber k_loc = ||grad theta_tilt|| (proportional to 1 / z_top over vertical contacts).
    """
    pad = 48
    f_pad = np.pad(rtp_2d.astype(np.float32, copy=False), pad, mode="reflect")
    ny, nx = f_pad.shape
    ky = 2.0 * np.pi * np.fft.fftfreq(ny, d=dx_m).astype(np.float32)[:, None]
    kx = 2.0 * np.pi * np.fft.rfftfreq(nx, d=dx_m).astype(np.float32)[None, :]
    k_rad = np.hypot(ky, kx)

    # Directional stop-band notch for E-W flight-line corrugations (|ky| high, |kx| near 0)
    ky_cut = float(2.0 * np.pi / 650.0)
    high_ky = 1.0 / (1.0 + np.exp(-(np.abs(ky) - ky_cut) / 0.0020))
    narrow_kx = np.exp(-((kx / (0.14 * np.abs(ky) + 1e-4)) ** 2))
    notch = 1.0 - 0.88 * high_ky * narrow_kx

    spec = np.fft.rfft2(f_pad) * notch
    H0, W0 = rtp_2d.shape
    f_150 = np.fft.irfft2(spec * np.exp(-150.0 * k_rad), s=(ny, nx))[pad : pad + H0, pad : pad + W0].astype(np.float32)
    f_350 = np.fft.irfft2(spec * np.exp(-350.0 * k_rad), s=(ny, nx))[pad : pad + H0, pad : pad + W0].astype(np.float32)
    del spec, f_pad, k_rad, notch, high_ky, narrow_kx

    gy, gx = np.gradient(f_150)
    hgm = np.hypot(gx, gy) + 1e-5
    dz = (f_150 - f_350) / 2.0  # per-100m vertical derivative
    tilt = np.arctan2(dz, hgm)
    ty, tx = np.gradient(tilt)
    kloc = np.clip(np.hypot(tx, ty), 0.0, 2.5).astype(np.float32)
    return hgm.astype(np.float32), kloc


def build_cskd_static_memmaps(
    raw_dir: Path,
    ing_dir: Path,
    cskd_src_dir: Path,
    cache_dir: Path,
    footprint: np.ndarray,
    transform: Any,
) -> dict[str, Any]:
    """Build or reuse the 70-channel base memmap + 14-channel CSKD static physical memmap -> combined 84-ch memmap."""
    t0 = time.time()
    cache_dir.mkdir(parents=True, exist_ok=True)
    n_fp = int(footprint.sum())
    n_tot = len(CSKD_STATIC_NAMES)
    out_path = cache_dir / "cskd_static_fp84.f32.mmap"
    meta_path = out_path.with_suffix(".meta.json")
    cues_path = out_path.with_suffix(".cues.npz")

    if out_path.is_file() and meta_path.is_file() and cues_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("rows") == n_fp
            and meta.get("cols") == n_tot
            and meta.get("feature_names") == CSKD_STATIC_NAMES
            and out_path.stat().st_size == n_fp * n_tot * 4
        ):
            return meta

    # Step 1: Build 70-channel base memmap via verified thvc_features builder, then copy into columns 0..69
    base70_path = cache_dir / "base_static_fp70.f32.mmap"
    base_meta = build_static_feature_memmap(raw_dir, ing_dir, base70_path, footprint, transform)
    base_mm = np.memmap(base70_path, dtype="float32", mode="r", shape=(n_fp, len(STATIC_FEATURE_NAMES)))

    mm = np.memmap(out_path, dtype="float32", mode="w+", shape=(n_fp, n_tot))
    chunk = 500_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        mm[s:e, : len(STATIC_FEATURE_NAMES)] = base_mm[s:e]
    mm.flush()

    bmap = {name: i for i, name in enumerate(STATIC_FEATURE_NAMES)}
    H, W = footprint.shape

    def read_base_2d(col_name: str) -> np.ndarray:
        out2 = np.zeros((H, W), dtype=np.float32)
        out2[footprint] = base_mm[:, bmap[col_name]]
        return out2

    u_step = read_base_2d("scarp_unified_step")
    u_curv = read_base_2d("scarp_unified_curv")
    u_line = read_base_2d("scarp_unified_line")
    road_prox = read_base_2d("road_proximity_confound")
    rtp_2d = read_base_2d("tf_rtp")
    demag_2d = read_base_2d("rtp_demag_trough")
    grav_hgm_z200 = read_base_2d("grav_hgm_z200")
    del base_mm
    drop_file_cache(base70_path)
    # Remove intermediate 1.44 GB base70 file once copied into 84-ch memmap to keep disk clean
    base70_cues = base70_path.with_suffix(".cues.npz")
    base_cues_data = dict(np.load(base70_cues))
    base70_path.unlink(missing_ok=True)
    base70_path.with_suffix(".meta.json").unlink(missing_ok=True)
    base70_cues.unlink(missing_ok=True)
    gc.collect()

    col_map = {name: i for i, name in enumerate(CSKD_STATIC_NAMES)}

    def write_col(name: str, arr2d: np.ndarray) -> None:
        vec = np.asarray(arr2d[footprint], dtype=np.float32)
        vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
        mm[:, col_map[name]] = vec

    # 1. Official USGS GeoDAWN 100-m Airborne Radar/GPS Absolute Elevation Z(x)
    with rasterio.open(cskd_src_dir / "geodawn_dem_a2_100m.tif") as ds:
        dem_raw = ds.read(1).astype(np.float32)
    valid_dem = footprint & np.isfinite(dem_raw) & (dem_raw > -1e5)
    dem_z = _infill_2d_sentinels(dem_raw, valid_dem)
    del dem_raw, valid_dem
    write_col("abs_elev_km", dem_z / 1000.0)

    # Smooth 300-m elevation gradient & regional 2.5-km basin-floor closure
    z_sm3 = ndi.gaussian_filter(dem_z, 3.0, mode="nearest")
    zy, zx = np.gradient(z_sm3)
    grad_z_mag = np.hypot(zx, zy)
    z_reg25 = ndi.gaussian_filter(dem_z, 25.0, mode="nearest")
    closure_raw = np.maximum(z_reg25 - z_sm3, 0.0) * np.exp(-grad_z_mag / 2.5)
    write_col("basin_floor_closure", closure_raw)

    # Pleistocene Pluvial Lake Lahontan (~1332 m Sehoo, ~1245 m recessional) & Bonneville (~1552 m) envelope
    lah_env = (
        np.exp(-0.5 * ((dem_z - 1332.0) / 48.0) ** 2)
        + 0.70 * np.exp(-0.5 * ((dem_z - 1245.0) / 45.0) ** 2)
        + 0.35 * np.exp(-0.5 * ((dem_z - 1552.0) / 38.0) ** 2)
    ).astype(np.float32)
    write_col("lahontan_isohypse_env", lah_env)

    # Dominant 8-azimuth scarp strike unit tangent t_scarp & along-scarp absolute elevation climb |t_scarp . grad Z|
    scarp_raw = 0.45 * u_step + 0.25 * u_curv + 0.30 * u_line
    best_resp = np.full((H, W), -1e9, dtype=np.float32)
    best_ty = np.zeros((H, W), dtype=np.float32)
    best_tx = np.zeros((H, W), dtype=np.float32)
    pad_s = 5
    scarp_pad = np.pad(scarp_raw, pad_s, mode="edge")
    for k_az in range(8):
        rad = np.deg2rad(k_az * 22.5)
        ty, tx = float(np.cos(rad)), float(np.sin(rad))
        acc = np.zeros((H, W), dtype=np.float32)
        for s_off in range(-4, 5):
            dy_i, dx_i = int(round(s_off * ty)), int(round(s_off * tx))
            acc += scarp_pad[pad_s + dy_i : pad_s + dy_i + H, pad_s + dx_i : pad_s + dx_i + W]
        acc *= 1.0 / 9.0
        upd = acc > best_resp
        best_resp = np.where(upd, acc, best_resp)
        best_ty = np.where(upd, ty, best_ty)
        best_tx = np.where(upd, tx, best_tx)
    del scarp_pad, scarp_raw, best_resp, u_curv, u_line

    strike_climb = np.abs(best_ty * zy + best_tx * zx).astype(np.float32)
    write_col("scarp_strike_elev_climb", strike_climb)
    sin_oblique = np.clip(strike_climb / (grad_z_mag + 0.25), 0.0, 1.0)
    shoreline_veto = (u_step * lah_env * (1.0 - sin_oblique)).astype(np.float32)
    write_col("lahontan_shoreline_veto", shoreline_veto)
    del best_ty, best_tx, zy, zx, grad_z_mag, sin_oblique

    # 2. Official US BLM Closed Mining Claims Distance (m)
    with rasterio.open(cskd_src_dir / "blm_closed_claim_distance_m.tif") as ds:
        blm_d = ds.read(1).astype(np.float32)
    blm_d = np.where(np.isfinite(blm_d) & (blm_d >= 0.0), blm_d, 10000.0)
    blm_prox = np.exp(-blm_d / 350.0).astype(np.float32)
    write_col("blm_mine_prox_350m", blm_prox)
    write_col("blm_log_dist_m", np.log1p(blm_d))
    del blm_d

    sv_q = np.zeros((H, W), dtype=np.float32)
    sv_q[footprint] = _empirical_quantiles_1d(shoreline_veto[footprint])
    clean_scarp = (
        u_step
        * (1.0 - 0.65 * sv_q * lah_env / np.maximum(lah_env.max(), 1.0))
        * (1.0 - 0.55 * blm_prox)
        * (1.0 - 0.35 * road_prox)
    ).astype(np.float32)
    write_col("scarp_lahontan_mine_clean", clean_scarp)
    del lah_env, shoreline_veto, sv_q, road_prox, u_step

    # 3. Official USGS GeoDAWN Survey Acquisition Block & 2D Fourier Flight-Line Notch + Local Wavenumber
    with rasterio.open(cskd_src_dir / "acquisition_block_id_100m.tif") as ds:
        acq_id = ds.read(1)
    area1_flag = ((acq_id == 1) & footprint).astype(np.float32)
    write_col("geodawn_area1_hires", area1_flag)
    del acq_id, area1_flag

    rtp_infill = _infill_2d_sentinels(rtp_2d, footprint)
    notched_hgm, mag_kloc = _fft_flightline_notch_and_kloc(rtp_infill)
    write_col("rtp_flight_notched_hgm", notched_hgm)
    write_col("mag_local_wavenumber_kloc", mag_kloc)
    del rtp_2d, rtp_infill, notched_hgm, mag_kloc
    gc.collect()

    # 4. Lithology-Normalized Potassic Adularia-Illite Residual Kd(x) from all 4 GeoDAWN Radiometric Bands
    with rasterio.open(raw_dir / "external/geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32) / 255.0
        rad_th = ds.read(2).astype(np.float32) / 255.0
        rad_tc = ds.read(4).astype(np.float32) / 255.0
    write_col("rad_tc_total_count", rad_tc)

    # Unsupervised spectral background regression K_hat(Th, TC) across active footprint (zero labels!)
    th_fp = rad_th[footprint].astype(np.float64)
    tc_fp = rad_tc[footprint].astype(np.float64)
    k_fp = rad_k[footprint].astype(np.float64)
    A = np.column_stack([np.ones_like(th_fp), th_fp, tc_fp, th_fp * th_fp, th_fp * tc_fp, tc_fp * tc_fp])
    # Regularized normal equations (6x6 matrix!) -> <0.05s, exact, zero memory spike
    ata = A.T @ A + 1e-2 * np.eye(6)
    atb = A.T @ k_fp
    beta_kd = np.linalg.solve(ata, atb)
    k_hat_fp = A @ beta_kd
    del A, th_fp, tc_fp, k_fp
    kd_2d = np.zeros((H, W), dtype=np.float32)
    kd_2d[footprint] = np.maximum(rad_k[footprint] - k_hat_fp.astype(np.float32), 0.0)
    # Subtract broad 3-km plutonic background so Kd highlights localized fault-conduit alteration
    kd_local = np.maximum(kd_2d - 0.65 * ndi.gaussian_filter(kd_2d, 30.0, mode="nearest"), 0.0)
    write_col("rad_kd_adularia_resid", kd_local)

    playa_q = np.zeros((H, W), dtype=np.float32)
    playa_q[footprint] = _empirical_quantiles_1d(closure_raw[footprint])
    kd_clean = (
        kd_local
        * (1.0 - 0.60 * blm_prox)
        * (1.0 - 0.50 * (playa_q ** 2))
        * np.log1p(np.maximum(demag_2d, 0.0))
    ).astype(np.float32)
    write_col("rad_kd_clean_conduit", kd_clean)
    del rad_k, rad_th, rad_tc, kd_2d, kd_local, closure_raw, playa_q, blm_prox, demag_2d

    # Save compact static cues for Group D slip-deficit & clean-scarp mechanics
    z_max18 = ndi.maximum_filter(z_sm3, size=31, mode="nearest")
    z_min18 = ndi.minimum_filter(z_sm3, size=31, mode="nearest")
    footwall_relief_3km = np.maximum(z_max18 - z_min18, 0.0)
    throw_proxy_fp = (
        _empirical_quantiles_1d(footwall_relief_3km[footprint])
        * _empirical_quantiles_1d(grav_hgm_z200[footprint])
    ).astype(np.float16)
    del dem_z, z_sm3, z_reg25, z_max18, z_min18, footwall_relief_3km, grav_hgm_z200

    np.savez_compressed(
        cues_path,
        scarp_step=base_cues_data["scarp_step"],
        grav_bdepth=base_cues_data["grav_bdepth"],
        hydro=np.maximum(
            base_cues_data["hydro"].astype(np.float32),
            0.75 * _empirical_quantiles_1d(kd_clean[footprint]),
        ).astype(np.float16),
        clean_scarp=clean_scarp[footprint].astype(np.float16),
        throw_proxy=throw_proxy_fp,
    )
    del clean_scarp, kd_clean, base_cues_data
    mm.flush()
    del mm
    drop_file_cache(out_path)
    gc.collect()

    meta = {
        "rows": n_fp,
        "cols": n_tot,
        "feature_names": CSKD_STATIC_NAMES,
        "base_meta": base_meta,
        "kd_regression_coefficients": [round(float(x), 6) for x in beta_kd],
        "build_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def _strand_orientations_and_lengths(vis: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute local unit fault strike tangent (ty, tx) and connected-component pixel size on ``vis``."""
    H, W = vis.shape
    comp, n_comp = ndi.label(vis, STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1).astype(np.float32)
    sizes[0] = 0.0
    comp_len = sizes[comp]

    # Smooth structure-tensor orientation of visible traces at sigma = 2.0 px
    vf = ndi.gaussian_filter(vis.astype(np.float32), 1.5, mode="constant", cval=0.0)
    gy, gx = np.gradient(vf)
    jyy = ndi.gaussian_filter(gy * gy, 2.5, mode="constant", cval=0.0)
    jxx = ndi.gaussian_filter(gx * gx, 2.5, mode="constant", cval=0.0)
    jyx = ndi.gaussian_filter(gy * gx, 2.5, mode="constant", cval=0.0)
    # Normal direction is principal eigenvector of gradient outer product; tangent is perpendicular!
    theta_n = 0.5 * np.arctan2(2.0 * jyx, jxx - jyy + 1e-12)
    # Tangent perpendicular to gradient normal: (-sin(theta_n), cos(theta_n)) in (x, y) -> (cos, -sin) in (y, x)
    # Wait: theta_n = 0.5 * atan2(2*gx*gy, gx^2 - gy^2) gives angle from x-axis!
    nx_u = np.cos(theta_n).astype(np.float32)
    ny_u = np.sin(theta_n).astype(np.float32)
    ty_u = nx_u  # since t = (-ny, nx) -> ty = -ny? Wait: ny*ty + nx*tx = sin*cos - cos*sin = 0!
    tx_u = -ny_u
    return ty_u, tx_u, comp_len


def compute_cskd_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    cues_npz_path: Path,
) -> np.ndarray:
    """Compute all 18 Group D mechanics channels (14 base + 4 Coulomb stress-shadow & slip-deficit)
    strictly from ``visible_mask``. Returns shape ``(n_fp, 18)`` in ``float32``.
    """
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    n_fp = int(footprint.sum())
    out = np.zeros((n_fp, len(CSKD_MECH_NAMES)), dtype=np.float32)
    if not np.any(vis):
        return out

    out[:, : len(MECH_FEATURE_NAMES)] = compute_network_mechanics(vis, footprint, cues_npz_path)

    ty_u, tx_u, comp_len = _strand_orientations_and_lengths(vis)
    d_vis, (ny_idx, nx_idx) = ndi.distance_transform_edt(~vis, return_indices=True)
    d_fp = d_vis[footprint].astype(np.float32)
    fy, fx = np.nonzero(footprint)
    vy = ny_idx[footprint]
    vx = nx_idx[footprint]

    dy = (fy - vy).astype(np.float32)
    dx = (fx - vx).astype(np.float32)
    inv_d = 1.0 / np.maximum(d_fp, 1e-4)
    uy = dy * inv_d
    ux = dx * inv_d

    t_y = ty_u[vy, vx]
    t_x = tx_u[vy, vx]
    L_near = comp_len[vy, vx]

    cos_a = np.abs(t_y * uy + t_x * ux)
    sin_a = np.sqrt(np.maximum(1.0 - cos_a * cos_a, 0.0))

    # 1. Broadside normal-fault elastic Coulomb stress-drop shadow (Delta_CFS < 0, Crider & Pollard 1998)
    long_w = np.clip((L_near - 10.0) / 30.0, 0.0, 1.5)
    coulomb_shadow = (
        long_w
        * (sin_a ** 4)
        * (d_fp > 3.0)
        * np.exp(-np.maximum(d_fp - 3.0, 0.0) / 10.5)
    ).astype(np.float32)

    # 2. Conjugate oblique / splay dilatational Coulomb lobe (alpha ~ 25-38 deg -> cos_a ~ 0.84)
    oblique_ang = np.exp(-0.5 * ((cos_a - 0.84) / 0.11) ** 2)
    coulomb_oblique = (
        np.clip(L_near / 20.0, 0.2, 1.4)
        * oblique_ang
        * (d_fp > 3.0)
        * np.exp(-np.maximum(d_fp - 3.0, 0.0) / 15.0)
    ).astype(np.float32)

    # 3. Along-range footwall structural relief minus mapped-trace slip-deficit
    cues = np.load(cues_npz_path)
    throw_fp = cues["throw_proxy"].astype(np.float32)
    clean_scarp_fp = cues["clean_scarp"].astype(np.float32)
    vis_dens25 = ndi.gaussian_filter(vis.astype(np.float32), 25.0, mode="constant", cval=0.0)[footprint]
    slip_def = (throw_fp * np.exp(-vis_dens25 / 0.010)).astype(np.float32)

    # 4. Clean tectonic scarp x (slip-deficit OR relay) attenuated by broadside Coulomb shadow
    relay_fp = out[:, MECH_FEATURE_NAMES.index("net_relay_stepover")]
    clean_x_def = (
        clean_scarp_fp
        * np.maximum(slip_def, relay_fp)
        * (1.0 - 0.45 * np.clip(coulomb_shadow, 0.0, 1.0))
    ).astype(np.float32)

    base_m = len(MECH_FEATURE_NAMES)
    out[:, base_m + 0] = coulomb_shadow
    out[:, base_m + 1] = coulomb_oblique
    out[:, base_m + 2] = slip_def
    out[:, base_m + 3] = clean_x_def
    del ty_u, tx_u, comp_len, d_vis, ny_idx, nx_idx
    return out


def build_cskd_training_shards(
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
    seed_base: int = 8100,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Build decontaminated per-quadrant inner training shards strictly on ``d(x, sim_vis) > 3.0 px``.

    Fixes IR-79-140:
      - Unhidden fault flanks at ``0 < d(x, sim_vis) <= 3.0 px`` are NEVER sampled into ``far_pool``
        as ``y = 0`` negatives!
      - Known unhidden catalogue pixels inside ``collar`` (``vis & ~sim_hidden``) are NEVER sampled
        as ``y = 0`` negatives!
      - Both Stage 1 and Stage 2 train on the exact ``d(x, sim_vis) > 3.0 px`` domain used at
        evaluation and live emission time!
    """
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    comp, n_comp = ndi.label(vis, STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)
    all_ids = np.arange(1, n_comp + 1, dtype=np.int32)
    target_px = hide_frac * float(vis.sum())

    buckets: dict[int, dict[str, list[Any] | int]] = {
        q: {"X": [], "y": [], "q": [], "w": [], "pos": 0, "act": 0} for q in range(4)
    }
    draw0_ref: dict[str, Any] = {}
    n_static = len(CSKD_STATIC_NAMES)
    n_all = len(CSKD_ALL_FEATURE_NAMES)

    for r in range(n_draws):
        rng = np.random.default_rng(seed_base + 149 * r)
        perm = rng.permutation(all_ids)
        cum = np.cumsum(sizes[perm])
        k = int(np.searchsorted(cum, target_px)) + 1
        chosen = perm[: min(k, perm.size)]
        sim_hidden = np.isin(comp, chosen) & vis
        collar = ndi.distance_transform_edt(~sim_hidden) <= float(buffer_px)
        sim_vis = vis & ~collar
        sim_known = vis & ~sim_hidden

        d_sim_vis = ndi.distance_transform_edt(~sim_vis)
        # Strict d > buffer_px domain matching buffered_component_draw and live placement!
        sim_eval_domain = footprint & (~sim_known) & (d_sim_vis > float(buffer_px))

        q_fp = metric.kernel(ndi.distance_transform_edt(~sim_hidden)).astype(np.float32)[footprint]
        y_fp = sim_hidden[footprint]
        act_fp = sim_eval_domain[footprint]
        mech = compute_cskd_mechanics(sim_vis, footprint, cues_npz_path)

        if r == 0:
            draw0_ref = {
                "active_fp": act_fp.copy(),
                "score_active_fp": (footprint & (~sim_known))[footprint].copy(),
                "d_sim_fp": d_sim_vis[footprint].astype(np.float16),
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
            xp = np.empty((idx.size, n_all), dtype=np.float32)
            xp[:, :n_static] = static_mm[idx]
            xp[:, n_static:] = mech[idx]

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

        _release_mm(static_mm, mmap_path)
        del sim_hidden, collar, sim_vis, sim_known, d_sim_vis, sim_eval_domain, q_fp, y_fp, act_fp, mech
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
    del buckets
    gc.collect()
    return shards, draw0_ref


def stack_cskd_shards(
    shards: dict[int, dict[str, Any]],
    quad_ids: list[int],
    use_mechanics: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float]:
    n_c = len(CSKD_ALL_FEATURE_NAMES) if use_mechanics else len(CSKD_STATIC_NAMES)
    X = np.concatenate([shards[q]["X"][:, :n_c] for q in quad_ids], axis=0)
    y = np.concatenate([shards[q]["y"] for q in quad_ids], axis=0)
    qv = np.concatenate([shards[q]["q"] for q in quad_ids], axis=0)
    w = np.concatenate([shards[q]["w"] for q in quad_ids], axis=0)
    tot_pos = sum(shards[q]["pos"] for q in quad_ids)
    tot_act = sum(shards[q]["act"] for q in quad_ids)
    return X, y, qv, w, float(tot_pos / max(tot_act, 1)), float(y.mean())


def predict_cskd_stage1_rows(
    suite: dict[str, Any],
    static_mm: np.memmap,
    mmap_path: Path,
    mech_arr: np.ndarray | None,
    row_indices: np.ndarray,
    true_pi: float,
    sample_pi: float,
    chunk_size: int = 450_000,
) -> tuple[np.ndarray, np.ndarray]:
    from gems79.thvc_model import _prior_correct

    n = row_indices.size
    n_static = len(CSKD_STATIC_NAMES)
    n_c = len(CSKD_ALL_FEATURE_NAMES) if mech_arr is not None else n_static
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


def run_cskd_quadrant_nested_oof(
    quad_fp: np.ndarray,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    shards: dict[int, dict[str, Any]],
    draw0_ref: dict[str, Any],
    test_mech_fp: np.ndarray | None,
    use_mechanics: bool,
    seed: int = 81,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Combinatorially exact C(4,2) = 6 pairwise inner fits + 4 outer fits across all 4 quadrants."""
    n_fp = int(footprint.sum())
    mech_d0 = draw0_ref["mech_fp16"] if use_mechanics else None
    q_rows = {q: np.flatnonzero(quad_fp == q) for q in range(4)}

    pair_preds: dict[tuple[int, int], dict[int, tuple[np.ndarray, np.ndarray]]] = {}
    for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
        X_ab, y_ab, q_ab, w_ab, tpi, spi = stack_cskd_shards(shards, [a, b], use_mechanics)
        s_ab = fit_stage1_ensemble(X_ab, y_ab, q_ab, w_ab, seed=seed + 10 * a + b)
        del X_ab, y_ab, q_ab, w_ab
        rem_qs = [c for c in range(4) if c not in (a, b)]
        rem_rows = np.sort(np.concatenate([q_rows[c] for c in rem_qs]))
        p_rem, q_rem = predict_cskd_stage1_rows(s_ab, static_mm, mmap_path, mech_d0, rem_rows, tpi, spi)
        p_tmp = np.zeros(n_fp, dtype=np.float32)
        q_tmp = np.zeros(n_fp, dtype=np.float32)
        p_tmp[rem_rows] = p_rem
        q_tmp[rem_rows] = q_rem
        pair_preds[(a, b)] = {c: (p_tmp[q_rows[c]], q_tmp[q_rows[c]]) for c in rem_qs}
        del s_ab, p_rem, q_rem, p_tmp, q_tmp
        gc.collect()

    outer_p1 = np.zeros(n_fp, dtype=np.float32)
    outer_q1 = np.zeros(n_fp, dtype=np.float32)
    for q_test in range(4):
        tr_qs = [q for q in range(4) if q != q_test]
        X_3, y_3, q_3, w_3, tpi3, spi3 = stack_cskd_shards(shards, tr_qs, use_mechanics)
        s_3 = fit_stage1_ensemble(X_3, y_3, q_3, w_3, seed=seed + 100 + q_test)
        del X_3, y_3, q_3, w_3
        outer_p1[q_rows[q_test]], outer_q1[q_rows[q_test]] = predict_cskd_stage1_rows(
            s_3, static_mm, mmap_path, test_mech_fp if use_mechanics else None, q_rows[q_test], tpi3, spi3
        )
        del s_3
        gc.collect()

    p2_test_all = np.zeros(n_fp, dtype=np.float32)
    q2_test_all = np.zeros(n_fp, dtype=np.float32)
    p2_tr_avg = np.zeros(n_fp, dtype=np.float32)
    q2_tr_avg = np.zeros(n_fp, dtype=np.float32)

    S2_outer_eval = extract_stage2_spatial_features(outer_p1, outer_q1, footprint, ctx_cols_fp)
    del outer_p1, outer_q1
    gc.collect()

    pair_avg_p1 = np.zeros(n_fp, dtype=np.float32)
    pair_avg_q1 = np.zeros(n_fp, dtype=np.float32)
    for q_val in range(4):
        others = [q for q in range(4) if q != q_val]
        sub_pairs = [(others[0], others[1]), (others[0], others[2]), (others[1], others[2])]
        for sp_pair in sub_pairs:
            pair_avg_p1[q_rows[q_val]] += pair_preds[sp_pair][q_val][0] / 3.0
            pair_avg_q1[q_rows[q_val]] += pair_preds[sp_pair][q_val][1] / 3.0
    S2_pair_oof = extract_stage2_spatial_features(pair_avg_p1, pair_avg_q1, footprint, ctx_cols_fp)
    del pair_avg_p1, pair_avg_q1, pair_preds
    gc.collect()

    for q_test in range(4):
        tr_mask = quad_fp != q_test
        s2_m = fit_stage2_dual_heads(S2_pair_oof, draw0_ref, tr_mask, seed=seed + 300 + q_test)
        p2_tr_avg[q_rows[q_test]], q2_tr_avg[q_rows[q_test]] = predict_stage2_dual_heads(
            s2_m, S2_pair_oof, q_rows[q_test]
        )
        p2_test_all[q_rows[q_test]], q2_test_all[q_rows[q_test]] = predict_stage2_dual_heads(
            s2_m, S2_outer_eval, q_rows[q_test]
        )
        del s2_m
        gc.collect()

    del S2_pair_oof, S2_outer_eval
    gc.collect()
    return p2_test_all, q2_test_all, p2_tr_avg, q2_tr_avg


def blend_counterfactual_posteriors(
    p_full_2d: np.ndarray,
    q_full_2d: np.ndarray,
    p_zero_2d: np.ndarray,
    q_zero_2d: np.ndarray,
    d_vis_2d: np.ndarray,
    allowed_mask: np.ndarray,
    w_base: float,
    w_far: float,
    d0_px: float = 18.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Mass-conserving spatial counterfactual fusion between full structural head and zero-catalogue physics head."""
    if w_base <= 0.0 and w_far <= 0.0:
        return p_full_2d, q_full_2d
    # Normalize zero-catalogue head on allowed_mask so its total mass matches p_full / q_full!
    mp_f = float(np.clip(p_full_2d, 0.0, 1.0)[allowed_mask].sum())
    mp_z = float(np.clip(p_zero_2d, 0.0, 1.0)[allowed_mask].sum())
    mq_f = float(np.clip(q_full_2d, 0.0, 1.0)[allowed_mask].sum())
    mq_z = float(np.clip(q_zero_2d, 0.0, 1.0)[allowed_mask].sum())
    pz_cal = np.clip(p_zero_2d * (mp_f / max(mp_z, 1e-8)), 0.0, 0.95)
    qz_cal = np.clip(q_zero_2d * (mq_f / max(mq_z, 1e-8)), 0.0, 0.98)

    d2 = d_vis_2d.astype(np.float32) ** 2
    w_map = np.clip(float(w_base) + float(w_far) * (d2 / (d2 + float(d0_px * d0_px))), 0.0, 0.85)
    p_cf = ((1.0 - w_map) * p_full_2d + w_map * pz_cal).astype(np.float32)
    q_cf = ((1.0 - w_map) * q_full_2d + w_map * qz_cal).astype(np.float32)
    return p_cf, q_cf
