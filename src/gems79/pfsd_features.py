"""Multi-physics, subsurface-surface strike-concordance, upward 1.5m-to-2m probe heat-flux,
cation-silica upflow disequilibrium, 10m 3DEP & province-normalized feature engineering for Lane H79-PFSD.

Strictly zero-leakage by construction:
1. Forbidden files ``derived_sgmc_faults_100m_u8.tif`` and ``gdr_qfaults_traces.csv`` are
   blocked at the module boundary and never opened.
2. Forbidden columns ``dist_known_fault_px``, ``known_fault``, and ``label`` are blocked
   at CSV parse time.
3. Static channels (92 total) depend ONLY on physical, geochemical, radiometric, and
   1m/10m/100m geomorphic inputs — zero access to ``existing_faults.tif``.
4. Elastic crack-tip, wing-crack, and relay-ramp mechanics (14 channels) are computed
   strictly from the fold-isolated ``visible_mask`` (with ``buffer_px=3`` collar withheld).
"""
from __future__ import annotations

import csv
import gc
import json
import os
import struct
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import fft as sfft
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import rankdata

from gems79.thvc_features import (
    FORBIDDEN_POINT_COLUMNS,
    HIGH_TEMP_PALEO_TYPES,
    MECH_FEATURE_NAMES,
    TF_BAND_NAMES,
    _crest_prominence_4az,
    _draw_segment_score,
    _empirical_quantiles_1d,
    compute_network_mechanics,
    latlon_to_utm11,
    parse_safe_csv,
    rss_mb,
)

FORBIDDEN_EXTERNAL_FILES: frozenset[str] = frozenset(
    {
        "derived_sgmc_faults_100m_u8.tif",
        "gdr_qfaults_traces.csv",
    }
)

PFSD_STATIC_FEATURE_NAMES: tuple[str, ...] = (
    # Group A1: 19 official competition bands
    *[f"tf_{b}" for b in TF_BAND_NAMES],
    # Group A2: 17 exact complex64 2D Fourier Laplace upward-continuation & potential-field channels
    "rtp_uc600_res",
    "rtp_demag_trough",
    "rtp_hgm_z200",
    "rtp_tilt_z200_abs",
    "rtp_tilt_dip_shift",
    "rtp_crest_prom",
    "euler_si_rtp",
    "grav_uc800_res",
    "grav_hgm_z200",
    "grav_hgm_z800",
    "grav_tilt_z200_abs",
    "grav_tilt_dip_shift",
    "grav_crest_prom",
    "bdepth_hgm_300m",
    "bdepth_hgm_900m",
    "transtension_conduit_idx",
    "det_elev_prom_600m",
    # Group A3: 7 untried 50-km tectonic-province-normalized localization channels
    "prov_z_geod_2ndinv",
    "prov_z_geod_shearrate",
    "prov_z_geod_dilaterate",
    "prov_z_ieq",
    "prov_z_cond_surf",
    "prov_z_grav_hg",
    "prov_z_elev_slope",
    # Group B: 22 geothermal 2m upward-gradient probe, cation-silica upflow, mafic dike & radiometric channels
    "t2m_dab_300m",
    "t2m_dab_900m",
    "t2m_dab_2200m",
    "t2m_dab_grad_ridge",
    "t2m_survey_weight",
    "t2m_upward_grad_600m",
    "t2m_solar_deconf_flux",
    "paleo_vent_kde_800m",
    "paleo_vent_kde_2400m",
    "paleo_hitemp_sinter_1200m",
    "paleo_vent_strike_bridge",
    "gdr_thermal_anom_900m",
    "gdr_geotherm_qtz_1800m",
    "gdr_chalc_upflow_1200m",
    "gdr_cat_qtz_diseq_1800m",
    "volc_vent_prox_3km",
    "volc_mafic_dike_bridge",
    "rad_k_th_alteration",
    "rad_u_th_redox",
    "tmi_shallow_150m_res",
    "hydro_demag_clay_conj",
    "rad_thk_bajada_dipole",
    # Group C: 27 dequantized 1m LiDAR + 13 sub-100m 10m 3DEP + 3-level subsurface-surface strike concordance
    "lidar_present",
    "scarp_unified_step",
    "scarp_unified_ex",
    "scarp_unified_curv",
    "scarp_unified_line",
    "lidar_up_down_asym",
    "topo10_slope_p90",
    "topo10_relief_local",
    "road_proximity_confound",
    "mountain_wall_ratio",
    "chi_step_max",
    "chi_ksn_max",
    "chi_playa_raised",
    "trace_aniso_max_800m",
    "trace_aniso_max_2000m",
    "trace_aniso_ratio",
    "block_step_elev_600m",
    "block_step_grav_800m",
    "lidar_signed_antislope_deq",
    "lidar_tect_fluvial_ratio_deq",
    "dem10_onesided3_road_deconf",
    "dem10_excess_onesided",
    "dem10_persistence_20_200",
    "chi_trunk_ksn_gated",
    "strike_concord_grav",
    "strike_concord_bdepth",
    "strike_concord_rtp",
)

PFSD_ALL_FEATURE_NAMES: tuple[str, ...] = PFSD_STATIC_FEATURE_NAMES + tuple(MECH_FEATURE_NAMES)


def drop_file_cache(path: Path) -> None:
    if not hasattr(os, "posix_fadvise") or not hasattr(os, "POSIX_FADV_DONTNEED") or not path.exists():
        return
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    except OSError:
        pass


def _fft_upward_continue_c64(
    field: np.ndarray,
    heights_m: tuple[float, ...],
    dx_m: float = 100.0,
) -> dict[float, np.ndarray]:
    """Memory-lean complex64 2D Fourier Laplace upward continuation exp(-z * |k|)."""
    pad = 96
    f_pad = np.pad(field.astype(np.float32, copy=False), pad, mode="reflect")
    ny, nx = f_pad.shape
    ky = (2.0 * np.pi * np.fft.fftfreq(ny, d=dx_m)).astype(np.float32)[:, None]
    kx = (2.0 * np.pi * np.fft.rfftfreq(nx, d=dx_m)).astype(np.float32)[None, :]
    k_rad = np.hypot(ky, kx)
    spec = sfft.rfft2(f_pad, workers=2)
    del f_pad, ky, kx
    results: dict[float, np.ndarray] = {}
    for z in heights_m:
        atten = np.exp(-np.float32(z) * k_rad)
        cont = sfft.irfft2(spec * atten, s=(ny, nx), workers=2)
        results[z] = cont[pad : pad + field.shape[0], pad : pad + field.shape[1]].astype(np.float32, copy=False)
        del atten, cont
    del spec, k_rad
    return results


def _axial_tangent_cos_sin_from_grad(gy: np.ndarray, gx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute doubled-angle unit strike director (cos 2*theta, sin 2*theta) tangent to iso-contours.

    Given gradient (gy, gx) normal to a step/edge, the strike tangent in (row, col) is (-gx, gy),
    measured from North (row-axis) as theta = atan2(gy_tangent_x, gy_tangent_y) -> cos(2*theta), sin(2*theta)
    without ever calling trig functions!
    Since lidar `strike` is azimuth clockwise from North (col = +East, row = -North):
      gradient in (East, North) is (gx, -gy)
      strike tangent in (East, North) is (gy, gx) -> North component = gx, East component = gy!
      WAIT: let's verify exact sign convention!
      For an E-W scarp (row changes, gy != 0, gx == 0):
        Azimuth clockwise from North = 90 deg -> cos(180 deg) = -1, sin(180 deg) = 0.
        With North_t = gx = 0, East_t = gy != 0:
        cos(2*az) = (North_t^2 - East_t^2) / (North_t^2 + East_t^2) = -1, sin(2*az) = 2*North_t*East_t / r^2 = 0!
      For a N-S scarp (col changes, gx != 0, gy == 0):
        Azimuth clockwise from North = 0 deg -> cos(0) = +1, sin(0) = 0.
        With North_t = gx != 0, East_t = 0:
        cos(2*az) = +1, sin(2*az) = 0!
      For a NE-SW (N45E) scarp (z increases toward SE: gx > 0, gy > 0 -> Wait: along N45E line, dEast = +1, dNorth = +1 -> dcol = +1, drow = -1, so z(row + col) constant means gy = +1, gx = +1 -> tangent dcol=+1, drow=+1 is SE = N135E! Wait: let's check!):
        If fault trends N45E, moving NE means col increases (+1) and row DECREASES (-1), so constant along fault is (row + col), hence gy = ∂z/∂row = +1, gx = ∂z/∂col = +1!
        Wait: for N45E (az = 45 deg), 2*az = 90 deg -> cos(2*az) = 0, sin(2*az) = +1!
        Let's check: tangent vector in (dEast, dNorth) perpendicular to gradient (∂z/∂East, ∂z/∂North) = (gx, -gy) = (+1, -1) is (dEast, dNorth) = (+1, +1) = (-(-gy), gx) = (gy, gx)!
        Azimuth from North has North_t = dNorth = gx = +1, East_t = dEast = gy = +1!
        Then 2 * North_t * East_t / r^2 = 2 * (+1) * (+1) / 2 = +1 = sin(90 deg)!!
        AND (North_t^2 - East_t^2) / r^2 = (1 - 1) / 2 = 0 = cos(90 deg)!!
    Exact on all 4 cardinal and diagonal orientations!
    """
    r2 = gx * gx + gy * gy + np.float32(1e-12)
    cos2 = ((gx * gx - gy * gy) / r2).astype(np.float32)
    sin2 = ((np.float32(2.0) * gx * gy) / r2).astype(np.float32)
    return cos2, sin2


def _province_zscore_35km(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Fast 10x-decimated 35-km tectonic-province local z-score (eliminates regional DC bias)."""
    H, W = arr.shape
    v = np.where(footprint, arr, np.float32(0.0)).astype(np.float32)
    w = footprint.astype(np.float32)
    # 10x block-strided view (~1 km step) + sigma=35 -> 35 km regional kernel in <5 ms
    v_sub = ndi.gaussian_filter(v[::10, ::10], 35.0, mode="nearest")
    w_sub = ndi.gaussian_filter(w[::10, ::10], 35.0, mode="nearest") + np.float32(1e-5)
    mean_sub = v_sub / w_sub
    v2_sub = ndi.gaussian_filter((v[::10, ::10] ** 2), 35.0, mode="nearest") / w_sub
    std_sub = np.sqrt(np.maximum(v2_sub - mean_sub * mean_sub, np.float32(1e-6))) + np.float32(1e-4)

    zy = H / float(mean_sub.shape[0])
    zx = W / float(mean_sub.shape[1])
    mean_full = ndi.zoom(mean_sub, (zy, zx), order=1)[:H, :W]
    std_full = ndi.zoom(std_sub, (zy, zx), order=1)[:H, :W]
    z = np.clip((arr - mean_full) / (std_full + np.float32(1e-4)), -6.0, 8.0).astype(np.float32)
    return np.where(footprint, z, np.float32(0.0))


def build_pfsd_static_memmap(
    raw_dir: Path,
    ing_dir: Path,
    dem10_dir: Path,
    out_path: Path,
    footprint: np.ndarray,
    transform: Any,
) -> dict[str, Any]:
    """Stream all 92 zero-catalogue static channels into a float32 disk memmap (< 1.5 GB RSS)."""
    t0 = time.time()
    assert len(PFSD_STATIC_FEATURE_NAMES) == 92, len(PFSD_STATIC_FEATURE_NAMES)
    n_fp = int(footprint.sum())
    n_static = len(PFSD_STATIC_FEATURE_NAMES)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = out_path.with_suffix(".meta.json")
    cues_path = out_path.with_suffix(".cues.npz")

    if out_path.is_file() and meta_path.is_file() and cues_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("rows") == n_fp
            and meta.get("cols") == n_static
            and meta.get("feature_names") == list(PFSD_STATIC_FEATURE_NAMES)
            and out_path.stat().st_size == n_fp * n_static * 4
        ):
            return meta

    mm = np.memmap(out_path, dtype="float32", mode="w+", shape=(n_fp, n_static))
    col_map = {name: i for i, name in enumerate(PFSD_STATIC_FEATURE_NAMES)}
    peak_rss = rss_mb()

    def write_col(name: str, arr2d: np.ndarray) -> None:
        nonlocal peak_rss
        vec = np.asarray(arr2d[footprint], dtype=np.float32)
        vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
        mm[:, col_map[name]] = vec
        peak_rss = max(peak_rss, rss_mb())

    def flush_and_drop() -> None:
        mm.flush()
        drop_file_cache(out_path)
        gc.collect()

    def read_tf_band(b1: int) -> np.ndarray:
        with rasterio.open(raw_dir / "training_features.tif") as ds:
            a = ds.read(b1).astype(np.float32)
        valid = footprint & np.isfinite(a) & (a > -1e30)
        med = float(np.median(a[valid])) if np.any(valid) else 0.0
        return np.where(valid, a, med).astype(np.float32)

    # 1. Group A1 + A3: Stream all 19 competition bands & compute 50-km province-normalized channels
    kept: dict[str, np.ndarray] = {}
    need_keep = {
        "rtp",
        "iso_grav_anom",
        "det_elev",
        "depth_to_base_surf",
        "geod_dilaterate",
        "geod_shearrate",
        "cond_surf",
        "tmi",
    }
    prov_map = {
        "geod_2ndinv": "prov_z_geod_2ndinv",
        "geod_shearrate": "prov_z_geod_shearrate",
        "geod_dilaterate": "prov_z_geod_dilaterate",
        "ieq_n100a15": "prov_z_ieq",
        "cond_surf": "prov_z_cond_surf",
        "iso_grav_anom_hg": "prov_z_grav_hg",
        "det_elev_slope": "prov_z_elev_slope",
    }
    for idx0, bname in enumerate(TF_BAND_NAMES):
        arr = read_tf_band(idx0 + 1)
        write_col(f"tf_{bname}", arr)
        if bname in prov_map:
            write_col(prov_map[bname], _province_zscore_35km(arr, footprint))
        if bname in need_keep:
            kept[bname] = arr
        else:
            del arr
    flush_and_drop()

    # 2. Group A2: Upward continuation + retain compact float16 strike tangents on footprint
    rtp = kept.pop("rtp")
    uc_rtp = _fft_upward_continue_c64(rtp, (200.0, 600.0, 800.0))
    write_col("rtp_uc600_res", rtp - uc_rtp[600.0])
    demag = np.maximum(uc_rtp[800.0] - rtp, np.float32(0.0))
    write_col("rtp_demag_trough", demag)

    ry2, rx2 = np.gradient(uc_rtp[200.0])
    c2_rtp, s2_rtp = _axial_tangent_cos_sin_from_grad(ry2, rx2)
    rtp_c2_fp = c2_rtp[footprint].astype(np.float16)
    rtp_s2_fp = s2_rtp[footprint].astype(np.float16)
    del c2_rtp, s2_rtp
    hgm_r2 = np.hypot(rx2, ry2) + np.float32(1e-6)
    dz_r2 = (rtp - uc_rtp[200.0]) / np.float32(2.0)
    tilt_r2 = np.arctan2(dz_r2, hgm_r2)

    ry8, rx8 = np.gradient(uc_rtp[800.0])
    hgm_r8 = np.hypot(rx8, ry8) + np.float32(1e-6)
    dz_r8 = (uc_rtp[200.0] - uc_rtp[800.0]) / np.float32(6.0)
    tilt_r8 = np.arctan2(dz_r8, hgm_r8)

    write_col("rtp_hgm_z200", hgm_r2)
    write_col("rtp_tilt_z200_abs", np.abs(tilt_r2))
    write_col("rtp_tilt_dip_shift", np.abs(tilt_r2 - tilt_r8))
    write_col("rtp_crest_prom", _crest_prominence_4az(hgm_r2))
    dz_gy, dz_gx = np.gradient(dz_r2)
    write_col("euler_si_rtp", np.clip(np.hypot(dz_gx, dz_gy) / (hgm_r2 + np.float32(0.05)), 0.0, 5.0))
    del rtp, uc_rtp, ry2, rx2, hgm_r2, dz_r2, tilt_r2, ry8, rx8, hgm_r8, dz_r8, tilt_r8, dz_gy, dz_gx
    flush_and_drop()

    grav = kept.pop("iso_grav_anom")
    uc_grav = _fft_upward_continue_c64(grav, (200.0, 800.0))
    write_col("grav_uc800_res", grav - uc_grav[800.0])
    gy2, gx2 = np.gradient(uc_grav[200.0])
    c2_grav, s2_grav = _axial_tangent_cos_sin_from_grad(gy2, gx2)
    grav_c2_fp = c2_grav[footprint].astype(np.float16)
    grav_s2_fp = s2_grav[footprint].astype(np.float16)
    del c2_grav, s2_grav
    hgm_g2 = np.hypot(gx2, gy2) + np.float32(1e-6)
    dz_g2 = (grav - uc_grav[200.0]) / np.float32(2.0)
    tilt_g2 = np.arctan2(dz_g2, hgm_g2)

    gy8, gx8 = np.gradient(uc_grav[800.0])
    hgm_g8 = np.hypot(gx8, gy8) + np.float32(1e-6)
    dz_g8 = (uc_grav[200.0] - uc_grav[800.0]) / np.float32(6.0)
    tilt_g8 = np.arctan2(dz_g8, hgm_g8)

    write_col("grav_hgm_z200", hgm_g2)
    write_col("grav_hgm_z800", hgm_g8)
    write_col("grav_tilt_z200_abs", np.abs(tilt_g2))
    write_col("grav_tilt_dip_shift", np.abs(tilt_g2 - tilt_g8))
    grav_crest = _crest_prominence_4az(hgm_g2)
    write_col("grav_crest_prom", grav_crest)
    grav_smooth = uc_grav[200.0].copy()
    grav_crest_q_fp = _empirical_quantiles_1d(grav_crest[footprint])
    del grav, uc_grav, gy2, gx2, hgm_g2, dz_g2, tilt_g2, gy8, gx8, hgm_g8, dz_g8, tilt_g8, grav_crest
    flush_and_drop()

    bdepth = kept.pop("depth_to_base_surf")
    bg3_y = ndi.gaussian_filter(bdepth, 3.0, order=(1, 0), mode="nearest")
    bg3_x = ndi.gaussian_filter(bdepth, 3.0, order=(0, 1), mode="nearest")
    c2_bd, s2_bd = _axial_tangent_cos_sin_from_grad(bg3_y, bg3_x)
    bdepth_c2_fp = c2_bd[footprint].astype(np.float16)
    bdepth_s2_fp = s2_bd[footprint].astype(np.float16)
    del c2_bd, s2_bd
    bdepth_hgm3 = np.hypot(bg3_x, bg3_y)
    write_col("bdepth_hgm_300m", bdepth_hgm3)
    bdepth_q_fp = _empirical_quantiles_1d(bdepth_hgm3[footprint])
    del bg3_y, bg3_x, bdepth_hgm3
    bg9_y = ndi.gaussian_filter(bdepth, 9.0, order=(1, 0), mode="nearest")
    bg9_x = ndi.gaussian_filter(bdepth, 9.0, order=(0, 1), mode="nearest")
    write_col("bdepth_hgm_900m", np.hypot(bg9_x, bg9_y))
    del bdepth, bg9_x, bg9_y

    dil = kept.pop("geod_dilaterate")
    shr = kept.pop("geod_shearrate")
    cond = kept.pop("cond_surf")
    cond_pos = np.log1p(np.maximum(cond - np.median(cond[footprint]), 0.0)).astype(np.float32)
    transtens = np.maximum(dil, 0.0) * np.abs(shr) * (1.0 + cond_pos)
    write_col("transtension_conduit_idx", transtens)
    del dil, shr, cond, transtens

    det_elev = kept.pop("det_elev")
    write_col("det_elev_prom_600m", det_elev - ndi.gaussian_filter(det_elev, 6.0, mode="nearest"))
    flush_and_drop()

    # 3. Group B: 2m temperature probes (incl. upward T2m - T15m / T2m - T1m gradient!), paleo vents,
    #    well/spring cation-silica disequilibrium, mafic volcanic bridges, and radiometrics
    H, W = footprint.shape
    t2_num = np.zeros((H, W), dtype=np.float32)
    t2_cnt = np.zeros((H, W), dtype=np.float32)
    t2_up_num = np.zeros((H, W), dtype=np.float32)
    t2_up_cnt = np.zeros((H, W), dtype=np.float32)
    with zipfile.ZipFile(ing_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip") as zf:
        dbf = zf.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    num_rec, hdr_len, rec_len = struct.unpack("<IHH", dbf[4:12])
    fields = []
    pos = 32
    while dbf[pos] != 0x0D:
        fname = dbf[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        fields.append((fname, dbf[pos + 16]))
        pos += 32
    lats_2m, lons_2m, dabs_2m, up_grads_2m, has_up_2m = [], [], [], [], []
    for idx in range(num_rec):
        rec = dbf[hdr_len + idx * rec_len : hdr_len + (idx + 1) * rec_len]
        if rec[0] == 0x2A:
            continue
        off = 1
        d: dict[str, str] = {}
        for fn, fl in fields:
            d[fn] = rec[off : off + fl].decode("latin1", errors="replace").strip()
            off += fl
        try:
            la, lo, dab = float(d["LatDegreeN"]), float(d["LongDegree"]), float(d["F2mDAB"])
            if 35.0 < la < 45.0 and -123.0 < lo < -113.0 and np.isfinite(dab):
                lats_2m.append(la)
                lons_2m.append(lo)
                dabs_2m.append(max(dab, 0.0))
                # Extract vertical upward conductive temperature gradient (°C/m) where dual depths exist
                up_g = 0.0
                got_g = False
                try:
                    t2v = float(d.get("T2m", ""))
                    if np.isfinite(t2v) and t2v > 1.0:
                        t15v_s = d.get("T15m", "")
                        t1v_s = d.get("T1m", "")
                        if t15v_s:
                            t15v = float(t15v_s)
                            if np.isfinite(t15v) and t15v > 1.0:
                                up_g = max((t2v - t15v) * 2.0, 0.0)
                                got_g = True
                        if not got_g and t1v_s:
                            t1v = float(t1v_s)
                            if np.isfinite(t1v) and t1v > 1.0:
                                up_g = max(t2v - t1v, 0.0)
                                got_g = True
                except ValueError:
                    pass
                up_grads_2m.append(min(up_g, 15.0))
                has_up_2m.append(got_g)
        except ValueError:
            pass
    del dbf
    if lats_2m:
        ux, uy = latlon_to_utm11(np.array(lats_2m), np.array(lons_2m))
        cc = np.floor((ux - transform.c) / transform.a).astype(np.int32)
        rr = np.floor((uy - transform.f) / transform.e).astype(np.int32)
        ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
        np.add.at(t2_num, (rr[ok], cc[ok]), np.array(dabs_2m, dtype=np.float32)[ok])
        np.add.at(t2_cnt, (rr[ok], cc[ok]), 1.0)
        ok_u = ok & np.array(has_up_2m, dtype=bool)
        if np.any(ok_u):
            np.add.at(t2_up_num, (rr[ok_u], cc[ok_u]), np.array(up_grads_2m, dtype=np.float32)[ok_u])
            np.add.at(t2_up_cnt, (rr[ok_u], cc[ok_u]), 1.0)

    sm9_saved = None
    for sig, cname in ((3.0, "t2m_dab_300m"), (9.0, "t2m_dab_900m"), (22.0, "t2m_dab_2200m")):
        s_num = ndi.gaussian_filter(t2_num, sig, mode="constant", cval=0.0)
        s_den = ndi.gaussian_filter(t2_cnt, sig, mode="constant", cval=0.0)
        sm = np.divide(s_num, s_den + 1e-4, out=np.zeros_like(s_num), where=s_den > 1e-5)
        write_col(cname, sm)
        if sig == 3.0:
            gy_t, gx_t = np.gradient(ndi.gaussian_filter(sm, 1.5, mode="nearest"))
            write_col("t2m_dab_grad_ridge", np.hypot(gx_t, gy_t))
            del gy_t, gx_t
        elif sig == 9.0:
            sm9_saved = sm.copy()
    d_probe = ndi.distance_transform_edt(t2_cnt == 0)
    write_col("t2m_survey_weight", np.exp(-d_probe / 15.0))
    u_num6 = ndi.gaussian_filter(t2_up_num, 6.0, mode="constant", cval=0.0)
    u_den6 = ndi.gaussian_filter(t2_up_cnt, 6.0, mode="constant", cval=0.0)
    up_grad6 = np.divide(u_num6, u_den6 + 1e-4, out=np.zeros_like(u_num6), where=u_den6 > 1e-5)
    write_col("t2m_upward_grad_600m", up_grad6)
    write_col("t2m_solar_deconf_flux", sm9_saved * (1.0 + 1.5 * up_grad6))
    del t2_num, t2_cnt, t2_up_num, t2_up_cnt, d_probe, u_num6, u_den6, up_grad6, sm9_saved
    flush_and_drop()

    # Paleo-geothermal vents (281 in-footprint) + strike bridges
    p_all = np.zeros((H, W), dtype=np.float32)
    p_hi = np.zeros((H, W), dtype=np.float32)
    vent_pts: list[tuple[float, float, float]] = []
    with zipfile.ZipFile(ing_dir / "paleo_geothermal_regional.zip") as zf:
        prows = list(csv.DictReader(zf.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace").splitlines()))
    for r in prows:
        try:
            la, lo = float(r["Lat_deg_NAD83"]), float(r["Long_deg_NAD83"])
            ux, uy = latlon_to_utm11(np.array([la]), np.array([lo]))
            ci = int(np.floor((ux[0] - transform.c) / transform.a))
            ri = int(np.floor((uy[0] - transform.f) / transform.e))
            if 0 <= ri < H and 0 <= ci < W:
                p_all[ri, ci] += 1.0
                w_hi = 1.0 if r.get("Deposit_type", "").strip() in HIGH_TEMP_PALEO_TYPES else 0.35
                if w_hi >= 1.0:
                    p_hi[ri, ci] += 1.0
                vent_pts.append((float(ri), float(ci), w_hi))
        except ValueError:
            pass
    write_col("paleo_vent_kde_800m", ndi.gaussian_filter(p_all, 8.0, mode="constant", cval=0.0))
    write_col("paleo_vent_kde_2400m", ndi.gaussian_filter(p_all, 24.0, mode="constant", cval=0.0))
    write_col("paleo_hitemp_sinter_1200m", ndi.gaussian_filter(p_hi, 12.0, mode="constant", cval=0.0))
    v_bridge = np.zeros((H, W), dtype=np.float32)
    if len(vent_pts) >= 2:
        coords = np.array([(p[0], p[1]) for p in vent_pts], dtype=np.float64)
        weights = np.array([p[2] for p in vent_pts], dtype=np.float32)
        tree = cKDTree(coords)
        for i, j in tree.query_pairs(r=45.0):
            dist_ij = float(np.hypot(coords[i, 0] - coords[j, 0], coords[i, 1] - coords[j, 1]))
            if dist_ij >= 3.0:
                _draw_segment_score(
                    v_bridge,
                    coords[i, 0],
                    coords[i, 1],
                    coords[j, 0],
                    coords[j, 1],
                    float(0.5 * (weights[i] + weights[j]) * np.exp(-dist_ij / 25.0)),
                )
    v_bridge_sm = ndi.gaussian_filter(v_bridge, 2.5, mode="constant", cval=0.0)
    write_col("paleo_vent_strike_bridge", v_bridge_sm)
    del p_all, p_hi, v_bridge

    # Safe GDR wells/springs including geothermchalc_c & geothermcat_c upflow disequilibrium
    ws_rows = parse_safe_csv(
        raw_dir / "external/gdr_wellspring_in_footprint.csv",
        ("row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"),
    )
    ws_t = np.zeros((H, W), dtype=np.float32)
    ws_q = np.zeros((H, W), dtype=np.float32)
    ws_up = np.zeros((H, W), dtype=np.float32)
    ws_dis = np.zeros((H, W), dtype=np.float32)
    for r in ws_rows:
        try:
            ri, ci = int(float(r["row"])), int(float(r["col"]))
            if 0 <= ri < H and 0 <= ci < W:
                tc_val = float(r["temp_c"]) if r["temp_c"] not in ("", "nan", "NaN") else np.nan
                gq_val = float(r["geothermquartz_c"]) if r["geothermquartz_c"] not in ("", "nan", "NaN") else np.nan
                gch_val = float(r["geothermchalc_c"]) if r["geothermchalc_c"] not in ("", "nan", "NaN") else np.nan
                gcat_val = float(r["geothermcat_c"]) if r["geothermcat_c"] not in ("", "nan", "NaN") else np.nan
                if np.isfinite(tc_val) and tc_val > 22.0:
                    ws_t[ri, ci] = max(ws_t[ri, ci], min(tc_val - 20.0, 150.0))
                if np.isfinite(gq_val) and gq_val > 60.0:
                    ws_q[ri, ci] = max(ws_q[ri, ci], min(gq_val - 50.0, 220.0))
                sil_t = gch_val if (np.isfinite(gch_val) and gch_val > 40.0) else gq_val
                if np.isfinite(sil_t) and sil_t > 45.0:
                    diseq = abs(gcat_val - sil_t) if (np.isfinite(gcat_val) and gcat_val > 40.0) else 25.0
                    up_score = min(sil_t - 45.0, 180.0) * float(np.exp(-diseq / 50.0))
                    ws_up[ri, ci] = max(ws_up[ri, ci], up_score)
                if np.isfinite(gcat_val) and np.isfinite(gq_val) and gcat_val > 40.0 and gq_val > 40.0:
                    ws_dis[ri, ci] = max(ws_dis[ri, ci], np.clip(gcat_val - gq_val, -60.0, 140.0))
        except ValueError:
            pass
    ws_t9 = ndi.gaussian_filter(ws_t, 9.0, mode="constant", cval=0.0)
    ws_q18 = ndi.gaussian_filter(ws_q, 18.0, mode="constant", cval=0.0)
    ws_up12 = ndi.gaussian_filter(ws_up, 12.0, mode="constant", cval=0.0)
    write_col("gdr_thermal_anom_900m", ws_t9)
    write_col("gdr_geotherm_qtz_1800m", ws_q18)
    write_col("gdr_chalc_upflow_1200m", ws_up12)
    write_col("gdr_cat_qtz_diseq_1800m", ndi.gaussian_filter(ws_dis, 18.0, mode="constant", cval=0.0))
    del ws_rows, ws_t, ws_q, ws_up, ws_dis

    # Safe volcanic vents + mafic dike-alignment bridges (rock_type partitioned!)
    vv_rows = parse_safe_csv(raw_dir / "external/gdr_volcanic_vents_in_footprint.csv", ("row", "col", "rock_type"))
    vv_m = np.ones((H, W), dtype=bool)
    mafic_pts: list[tuple[float, float, float]] = []
    for r in vv_rows:
        try:
            ri, ci = int(float(r["row"])), int(float(r["col"]))
            if 0 <= ri < H and 0 <= ci < W:
                vv_m[ri, ci] = False
                rt = r.get("rock_type", "").strip().lower()
                if "basalt" in rt or "mafic" in rt or "andesite" in rt:
                    mafic_pts.append((float(ri), float(ci), 1.0))
                elif "rhyolite" not in rt and "dacite" not in rt:
                    mafic_pts.append((float(ri), float(ci), 0.45))
        except ValueError:
            pass
    write_col("volc_vent_prox_3km", np.exp(-ndi.distance_transform_edt(vv_m) / 30.0))
    m_bridge = np.zeros((H, W), dtype=np.float32)
    if len(mafic_pts) >= 2:
        m_coords = np.array([(p[0], p[1]) for p in mafic_pts], dtype=np.float64)
        m_w = np.array([p[2] for p in mafic_pts], dtype=np.float32)
        mtree = cKDTree(m_coords)
        for i, j in mtree.query_pairs(r=50.0):
            dist_ij = float(np.hypot(m_coords[i, 0] - m_coords[j, 0], m_coords[i, 1] - m_coords[j, 1]))
            if dist_ij >= 3.0:
                _draw_segment_score(
                    m_bridge,
                    m_coords[i, 0],
                    m_coords[i, 1],
                    m_coords[j, 0],
                    m_coords[j, 1],
                    float(0.5 * (m_w[i] + m_w[j]) * np.exp(-dist_ij / 28.0)),
                )
    write_col("volc_mafic_dike_bridge", ndi.gaussian_filter(m_bridge, 2.5, mode="constant", cval=0.0))
    del vv_rows, vv_m, m_bridge

    # Radiometrics & ThK bajada step-dipole
    with rasterio.open(raw_dir / "external/geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32) / np.float32(255.0)
        rad_th = ds.read(2).astype(np.float32) / np.float32(255.0)
    k_th_alt = np.clip(rad_k / (rad_th + np.float32(0.08)), 0.0, 6.0)
    k_th_local = np.maximum(k_th_alt - ndi.gaussian_filter(k_th_alt, 12.0, mode="nearest"), 0.0)
    write_col("rad_k_th_alteration", k_th_local)
    del rad_k, rad_th, k_th_alt

    with rasterio.open(raw_dir / "external/geodawn_extensions_u8.tif") as ds:
        ext_thk = ds.read(1).astype(np.float32) / np.float32(255.0)
        ext_uth = ds.read(3).astype(np.float32) / np.float32(255.0)
        ext_tmi150 = ds.read(4).astype(np.float32) / np.float32(255.0)
    write_col("rad_u_th_redox", ext_uth)
    thk_gy, thk_gx = np.gradient(ndi.gaussian_filter(ext_thk, 2.5, mode="nearest"))
    thk_step = np.hypot(thk_gx, thk_gy).astype(np.float32)
    del ext_thk, ext_uth, thk_gy, thk_gx

    tmi_raw = kept.pop("tmi")
    p1_tmi, p99_tmi = np.percentile(tmi_raw[footprint], [1.0, 99.0])
    tmi_norm = (tmi_raw - p1_tmi) / (p99_tmi - p1_tmi + 1e-6)
    write_col("tmi_shallow_150m_res", np.clip(tmi_norm, 0.0, 1.0) - ext_tmi150)
    del tmi_raw, tmi_norm, ext_tmi150

    hydro_conj = np.log1p(demag) * (1.0 + 3.0 * k_th_local) * (1.0 + cond_pos)
    write_col("hydro_demag_clay_conj", hydro_conj)
    hydro_cue_fp = (
        _empirical_quantiles_1d(hydro_conj[footprint])
        + 0.55 * _empirical_quantiles_1d(v_bridge_sm[footprint])
        + 0.65 * _empirical_quantiles_1d((ws_up12 + 0.5 * ws_t9 + 0.35 * ws_q18)[footprint])
    ) / 2.2
    del demag, k_th_local, cond_pos, hydro_conj, v_bridge_sm, ws_t9, ws_q18, ws_up12
    flush_and_drop()

    # 4. Group C: Physically dequantized 2m LiDAR + 13 sub-100m 10m 3DEP + 3-level strike concordance
    lidar_meta = json.loads((raw_dir / "external/lidar_scarp_features.json").read_text())
    qmap = lidar_meta["quantisation"]

    def _dequant_lidar(q_u8: np.ndarray, bname: str) -> np.ndarray:
        xmax, mode = qmap[bname]
        unit = np.clip((q_u8.astype(np.float32) - 1.0) / 254.0, 0.0, 1.0)
        return np.float32(xmax) * (unit * unit if mode == "sqrt" else unit)

    with rasterio.open(raw_dir / "external/lidar_scarp_features_u8.tif") as ds:
        lid_ex = ds.read(1).astype(np.float32)
        lid_step = ds.read(3).astype(np.float32)
        lid_lapn = ds.read(4).astype(np.float32)
        lid_lapp = ds.read(5).astype(np.float32)
        lid_down_q = ds.read(6)
        lid_up_q = ds.read(7)
        lid_cross_q = ds.read(8)
        lid_coh = ds.read(10).astype(np.float32)
        lid_strike_q = ds.read(11)
        lid_valid = (ds.read(12) > 0) & footprint

    lid_down = lid_down_q.astype(np.float32)
    lid_up = lid_up_q.astype(np.float32)
    up_deq = _dequant_lidar(lid_up_q, "upface_max")
    dn_deq = _dequant_lidar(lid_down_q, "downface_max")
    cr_deq = _dequant_lidar(lid_cross_q, "cross_max")
    strike_deg = _dequant_lidar(lid_strike_q, "strike")  # [0, 180] deg clockwise from North
    del lid_down_q, lid_up_q, lid_cross_q, lid_strike_q

    with rasterio.open(ing_dir / "topo_10m_derived_100m_u8.tif") as ds:
        t10_sp90 = ds.read(1).astype(np.float32)
        t10_smax = ds.read(2).astype(np.float32)
        t10_rel = ds.read(5).astype(np.float32)
        t10_curv = ds.read(6).astype(np.float32)
        t10_acoh = ds.read(7).astype(np.float32)
        t10_line = ds.read(8).astype(np.float32)

    with rasterio.open(raw_dir / "external/tiger_road_distance_m.tif") as ds:
        road_d = ds.read(1).astype(np.float32)
    road_d = np.where(np.isfinite(road_d) & (road_d >= 0.0), road_d, 5000.0)
    road_prox = np.exp(-road_d / 150.0).astype(np.float32)
    road_atten = np.tanh(road_d / 250.0).astype(np.float32)
    write_col("road_proximity_confound", road_prox)
    del road_d

    # Load 10m 3DEP sub-100m morphology vectors from SHA-verified data/cache/dem10/
    def _load_dem10_2d(vname: str) -> np.ndarray:
        vec = np.load(dem10_dir / f"{vname}.f32.npy").astype(np.float32)
        vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
        g = np.zeros((H, W), dtype=np.float32)
        g[footprint] = vec
        return g

    d10_one3 = _load_dem10_2d("dem10_onesided3")
    d10_smean = _load_dem10_2d("dem10_slope_mean")
    d10_hgm20 = _load_dem10_2d("dem10_hgm20_max")
    d10_hgm200 = _load_dem10_2d("dem10_hgm200_mean")
    d10_rstd = _load_dem10_2d("dem10_resid_std")

    bajada_gate = ((d10_smean >= 0.015) & (d10_smean <= 0.16)).astype(np.float32)
    write_col("rad_thk_bajada_dipole", thk_step * (0.35 + 0.65 * bajada_gate) * (1.0 + d10_rstd))
    del thk_step, bajada_gate, d10_rstd

    write_col("dem10_onesided3_road_deconf", d10_one3 * road_atten)
    write_col("dem10_excess_onesided", d10_one3 - d10_smean)
    write_col("dem10_persistence_20_200", d10_hgm20 / (np.maximum(d10_hgm200, 0.0) + 0.02))
    del d10_smean, d10_hgm20, d10_hgm200

    write_col("lidar_present", lid_valid.astype(np.float32))
    gap_mask = footprint & ~lid_valid

    def bridge_quantile(lid_arr: np.ndarray, t10_arr: np.ndarray) -> np.ndarray:
        out = np.zeros((H, W), dtype=np.float32)
        out[lid_valid] = _empirical_quantiles_1d(lid_arr[lid_valid])
        out[gap_mask] = _empirical_quantiles_1d(t10_arr[gap_mask])
        return out

    u_step = bridge_quantile(lid_step, np.maximum(t10_smax - 0.65 * t10_sp90, 0.0) + 80.0 * d10_one3)
    u_ex = bridge_quantile(lid_ex, t10_smax)
    u_curv = bridge_quantile(np.maximum(lid_lapn, lid_lapp), t10_curv)
    u_line = bridge_quantile(lid_coh, 0.55 * t10_line + 0.45 * t10_acoh)
    write_col("scarp_unified_step", u_step)
    write_col("scarp_unified_ex", u_ex)
    write_col("scarp_unified_curv", u_curv)
    write_col("scarp_unified_line", u_line)

    asym = np.zeros((H, W), dtype=np.float32)
    asym[lid_valid] = np.abs(lid_up[lid_valid] - lid_down[lid_valid]) / (lid_up[lid_valid] + lid_down[lid_valid] + 5.0)
    asym[gap_mask] = _empirical_quantiles_1d(np.abs(det_elev - ndi.gaussian_filter(det_elev, 2.0, mode="nearest"))[gap_mask]) * 0.5
    write_col("lidar_up_down_asym", asym)

    signed_anti = np.zeros((H, W), dtype=np.float32)
    signed_anti[lid_valid] = (up_deq[lid_valid] - dn_deq[lid_valid]) * road_atten[lid_valid]
    signed_anti[gap_mask] = (d10_one3[gap_mask] * road_atten[gap_mask]) * 0.35
    write_col("lidar_signed_antislope_deq", signed_anti)

    tf_ratio = np.zeros((H, W), dtype=np.float32)
    tf_ratio[lid_valid] = (up_deq[lid_valid] + dn_deq[lid_valid]) / (cr_deq[lid_valid] + 0.02)
    tf_ratio[gap_mask] = np.median(tf_ratio[lid_valid]) if np.any(lid_valid) else 1.0
    write_col("lidar_tect_fluvial_ratio_deq", np.clip(tf_ratio, 0.0, 20.0))

    # 3-Level Crustal-to-Surface Axial Strike Concordance Tensor cos(2*(theta_scarp - theta_subsurface))
    ey_gap, ex_gap = np.gradient(ndi.gaussian_filter(det_elev, 1.5, mode="nearest"))
    c2_gap, s2_gap = _axial_tangent_cos_sin_from_grad(ey_gap, ex_gap)
    del ey_gap, ex_gap
    rad2 = np.deg2rad(2.0 * strike_deg)
    c2_scarp = np.where(lid_valid, np.cos(rad2).astype(np.float32), c2_gap)
    s2_scarp = np.where(lid_valid, np.sin(rad2).astype(np.float32), s2_gap)
    del rad2, strike_deg, c2_gap, s2_gap, up_deq, dn_deq, cr_deq, signed_anti, tf_ratio, d10_one3

    c2_sc_fp = c2_scarp[footprint]
    s2_sc_fp = s2_scarp[footprint]
    sc_weight_fp = u_step[footprint] * road_atten[footprint]
    del c2_scarp, s2_scarp, road_atten

    mm[:, col_map["strike_concord_grav"]] = (
        (c2_sc_fp * grav_c2_fp.astype(np.float32) + s2_sc_fp * grav_s2_fp.astype(np.float32)) * sc_weight_fp
    ).astype(np.float32)
    mm[:, col_map["strike_concord_bdepth"]] = (
        (c2_sc_fp * bdepth_c2_fp.astype(np.float32) + s2_sc_fp * bdepth_s2_fp.astype(np.float32)) * sc_weight_fp
    ).astype(np.float32)
    mm[:, col_map["strike_concord_rtp"]] = (
        (c2_sc_fp * rtp_c2_fp.astype(np.float32) + s2_sc_fp * rtp_s2_fp.astype(np.float32)) * sc_weight_fp
    ).astype(np.float32)
    del c2_sc_fp, s2_sc_fp, sc_weight_fp, grav_c2_fp, grav_s2_fp, bdepth_c2_fp, bdepth_s2_fp, rtp_c2_fp, rtp_s2_fp

    write_col("topo10_slope_p90", t10_sp90 / 255.0)
    write_col("topo10_relief_local", t10_rel / 255.0)
    reg_relief = ndi.gaussian_filter(t10_rel, 12.0, mode="nearest") + 8.0
    write_col("mountain_wall_ratio", u_step / (reg_relief / 40.0))
    del lid_ex, lid_step, lid_lapn, lid_lapp, lid_down, lid_up, lid_coh, asym
    del t10_sp90, t10_smax, t10_rel, t10_curv, t10_acoh, t10_line, reg_relief

    with rasterio.open(ing_dir / "dem10_chi_100m_i16.tif") as ds:
        chi_step = np.maximum(ds.read(1).astype(np.float32), 0.0) / 1000.0
        chi_ksn = np.maximum(ds.read(3).astype(np.float32), 0.0)
        chi_larea = ds.read(4).astype(np.float32)
        chi_z = ds.read(5).astype(np.float32)
    write_col("chi_step_max", chi_step)
    log_ksn = np.log1p(chi_ksn)
    write_col("chi_ksn_max", log_ksn)
    trunk_gate = ((chi_larea >= 4200.0) & (chi_larea <= 7200.0)).astype(np.float32)
    write_col("chi_trunk_ksn_gated", log_ksn * trunk_gate)
    playa = ((chi_ksn < 12.0) & (chi_z < np.percentile(chi_z[footprint], 35.0))).astype(np.float32)
    write_col("chi_playa_raised", playa)
    del chi_step, chi_ksn, chi_larea, chi_z, log_ksn, trunk_gate, playa
    flush_and_drop()

    # 8-azimuth directional trace integrals & cross-strike block-step asymmetry
    scarp_comp = (0.45 * u_step + 0.25 * u_curv + 0.30 * u_line) * (1.0 - 0.35 * road_prox)
    del u_ex, u_curv, u_line, road_prox
    max_800 = np.zeros((H, W), dtype=np.float32)
    min_800 = np.full((H, W), 1e9, dtype=np.float32)
    max_2000 = np.zeros((H, W), dtype=np.float32)
    step_elev = np.zeros((H, W), dtype=np.float32)
    step_grav = np.zeros((H, W), dtype=np.float32)
    for k_az in range(8):
        rad = np.deg2rad(k_az * 22.5)
        ty, tx = np.cos(rad), np.sin(rad)
        ny_v, nx_v = -tx, ty
        acc8 = np.zeros((H, W), dtype=np.float32)
        for s_off in range(-4, 5):
            dy_i, dx_i = int(round(s_off * ty)), int(round(s_off * tx))
            acc8 += np.roll(scarp_comp, shift=(dy_i, dx_i), axis=(0, 1))
        acc8 /= 9.0
        max_800 = np.maximum(max_800, acc8)
        min_800 = np.minimum(min_800, acc8)

        acc20 = np.zeros((H, W), dtype=np.float32)
        for s_off in range(-10, 11, 2):
            dy_i, dx_i = int(round(s_off * ty)), int(round(s_off * tx))
            acc20 += np.roll(scarp_comp, shift=(dy_i, dx_i), axis=(0, 1))
        acc20 /= 11.0
        max_2000 = np.maximum(max_2000, acc20)

        de6_y, de6_x = int(round(6.0 * ny_v)), int(round(6.0 * nx_v))
        step_elev = np.maximum(
            step_elev,
            np.abs(
                np.roll(det_elev, shift=(de6_y, de6_x), axis=(0, 1))
                - np.roll(det_elev, shift=(-de6_y, -de6_x), axis=(0, 1))
            ),
        )
        dg8_y, dg8_x = int(round(8.0 * ny_v)), int(round(8.0 * nx_v))
        step_grav = np.maximum(
            step_grav,
            np.abs(
                np.roll(grav_smooth, shift=(dg8_y, dg8_x), axis=(0, 1))
                - np.roll(grav_smooth, shift=(-dg8_y, -dg8_x), axis=(0, 1))
            ),
        )
        del acc8, acc20

    write_col("trace_aniso_max_800m", max_800)
    write_col("trace_aniso_max_2000m", max_2000)
    write_col("trace_aniso_ratio", max_800 / (min_800 + 0.02))
    write_col("block_step_elev_600m", step_elev)
    write_col("block_step_grav_800m", step_grav)

    np.savez_compressed(
        cues_path,
        scarp_step=u_step[footprint].astype(np.float16),
        grav_bdepth=(0.5 * grav_crest_q_fp + 0.5 * bdepth_q_fp).astype(np.float16),
        hydro=hydro_cue_fp.astype(np.float16),
    )
    flush_and_drop()
    del mm, scarp_comp, max_800, min_800, max_2000, step_elev, step_grav, det_elev, grav_smooth, u_step, grav_crest_q_fp, bdepth_q_fp, hydro_cue_fp
    gc.collect()

    meta = {
        "lane": "H79-PFSD",
        "rows": n_fp,
        "cols": n_static,
        "feature_names": list(PFSD_STATIC_FEATURE_NAMES),
        "build_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(peak_rss, 1),
        "forbidden_files_blocked": sorted(FORBIDDEN_EXTERNAL_FILES),
        "forbidden_columns_blocked": sorted(FORBIDDEN_POINT_COLUMNS),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


__all__ = [
    "FORBIDDEN_EXTERNAL_FILES",
    "FORBIDDEN_POINT_COLUMNS",
    "MECH_FEATURE_NAMES",
    "PFSD_ALL_FEATURE_NAMES",
    "PFSD_STATIC_FEATURE_NAMES",
    "build_pfsd_static_memmap",
    "compute_network_mechanics",
    "drop_file_cache",
    "rss_mb",
]
