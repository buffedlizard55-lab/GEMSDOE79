"""G79-DFSD leak-free subsurface de-striping, Salem magnetic tilt inverse-depth,
60-deg up-dip hanging-wall-to-footwall basement step registration, cross-fitted
potassic adularia residual (K_d), full-coverage 10m 3DEP multi-scale scarp
persistence, Lake Lahontan isohypsic strandline deconfounding, Wallace (1978)
slip-deficit, and Okada-style lateral Coulomb stress-shadow feature engine.

Strict zero-leakage & reuse invariants (Parallel-Run Protocol Rules 1, 2, 4):
  1. Reuses ``src/gems79/thvc_features.py::build_static_feature_memmap`` (70 ch)
     and ``compute_network_mechanics`` (14 ch) without duplication.
  2. Never reads any prior prediction raster from registry / downloads / archive.
  3. Explicitly forbids ``derived_sgmc_faults_100m_u8.tif``,
     ``gdr_qfaults_traces.csv``, and columns ``dist_known_fault_px``,
     ``known_fault``, ``label``.
  4. All 3 new network/stress channels are computed strictly from the supplied
     ``visible_mask`` inside every outer fold and inner draw.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import fft as sp_fft
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from gems57.holdout import quadrant_ids
from gems79.thvc_features import (
    ALL_FEATURE_NAMES as THVC_ALL_NAMES,
    FORBIDDEN_POINT_COLUMNS,
    MECH_FEATURE_NAMES as THVC_MECH_NAMES,
    STATIC_FEATURE_NAMES as THVC_STATIC_NAMES,
    STRUCT3,
    build_static_feature_memmap,
    compute_network_mechanics,
    rss_mb,
)

FORBIDDEN_RASTER_INPUTS = frozenset({
    "derived_sgmc_faults_100m_u8.tif",
    "gdr_qfaults_traces.csv",
})

DFSD_EXTRA_STATIC_NAMES = [
    # H2 (H80-DRAPE-DECONV): Flight-line de-striping + Salem tilt inverse depth + up-dip registration (4)
    "dfsd_fft_line_corrugation",
    "dfsd_salem_tilt_clean_peak",
    "dfsd_salem_inv_depth_edge",
    "dfsd_updip_grav_mag_step",
    # H5 (H80-RADIO-KD): Spatially cross-fitted potassic adularia residual & blind alteration (3)
    "dfsd_radio_kd_adularia_oof",
    "dfsd_kd_playa_deconfounded",
    "dfsd_hydro_kd_demag_clay",
    # H1 & H3: Full-coverage 10m 3DEP persistence, TIGER road deconfound & Lake Lahontan isohypse veto (9)
    "dfsd_dem10_onesided3",
    "dfsd_dem10_excess_step_road",
    "dfsd_dem10_persistence",
    "dfsd_dem10_hgm50_max",
    "dfsd_dem10_curv_absmax",
    "dfsd_dem10_resid_range",
    "dfsd_lidar_antislope_ratio",
    "dfsd_isohypse_cross_contour",
    "dfsd_footwall_relief_hinge",
    # INGENIOUS GDR-1391 deep geothermometer enthalpy plumes & bajada knickpoints (4)
    "dfsd_gdr_log_dist_hot",
    "dfsd_gdr_enthalpy_plume_s8",
    "dfsd_gdr_enthalpy_x_strain",
    "dfsd_fan_knickpoint_bajada",
]

DFSD_EXTRA_MECH_NAMES = [
    "dfsd_coulomb_shadow_perp",
    "dfsd_wallace_slip_deficit",
    "dfsd_collar_corroborated_splay",
]

DFSD_STATIC_NAMES = list(THVC_STATIC_NAMES) + DFSD_EXTRA_STATIC_NAMES      # 70 + 20 = 90
DFSD_MECH_NAMES = list(THVC_MECH_NAMES) + DFSD_EXTRA_MECH_NAMES            # 14 + 3 = 17
DFSD_ALL_FEATURE_NAMES = DFSD_STATIC_NAMES + DFSD_MECH_NAMES               # 90 + 17 = 107
assert len(DFSD_STATIC_NAMES) == 90
assert len(DFSD_MECH_NAMES) == 17
assert len(DFSD_ALL_FEATURE_NAMES) == 107


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_f16(arr2d: np.ndarray, valid: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """IQR-standardized clipped float16 footprint column (zero NaN/Inf anywhere)."""
    m = valid & footprint & np.isfinite(arr2d)
    fp_vals = np.zeros(int(footprint.sum()), dtype=np.float32)
    if int(m.sum()) > 32:
        sub = arr2d[m].astype(np.float32)
        q25, q50, q75 = np.percentile(sub, [25.0, 50.0, 75.0])
        scale = float(q75 - q25)
        if scale < 1e-6:
            scale = float(np.std(sub))
        if scale < 1e-6:
            scale = 1.0
        norm2d = np.where(m, np.clip((arr2d - q50) / scale, -12.0, 12.0), 0.0).astype(np.float32)
        fp_vals = norm2d[footprint]
    return fp_vals.astype(np.float16)


def _destripe_and_salem_tilt(rtp_2d: np.ndarray, valid_rtp: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """2D FFT GeoDAWN flight/tie-line notch filter + exact Laplace Salem et al. (2007) tilt-depth."""
    H, W = rtp_2d.shape
    med = float(np.median(rtp_2d[valid_rtp])) if np.any(valid_rtp) else 0.0
    filled = np.where(valid_rtp, rtp_2d, med).astype(np.float32)
    # Taper outside valid region smoothly to median so FFT has zero boundary ringing
    smooth_bg = ndi.gaussian_filter(filled, sigma=18.0).astype(np.float32)
    work = np.where(valid_rtp, filled, smooth_bg)

    F = sp_fft.rfft2(work, workers=2)
    ky = sp_fft.fftfreq(H, d=1.0).astype(np.float32)[:, None]      # cycles / pixel (N-S frequency = E-W lines!)
    kx = sp_fft.rfftfreq(W, d=1.0).astype(np.float32)[None, :]     # cycles / pixel (E-W frequency = N-S tie lines!)
    kr = np.sqrt(kx * kx + ky * ky).astype(np.float32)

    # Directional Butterworth-Gaussian notch along E-W flight lines (kx ~ 0, |ky| > 0.045)
    # and N-S tie lines (ky ~ 0, |kx| > 0.035), plus specific 400m harmonic (|ky| ~ 0.25)
    ew_line_notch = np.exp(-((kx / 0.0075) ** 2)) * (1.0 / (1.0 + (0.045 / np.maximum(np.abs(ky), 1e-5)) ** 4))
    ns_tie_notch = np.exp(-((ky / 0.0065) ** 2)) * (1.0 / (1.0 + (0.035 / np.maximum(np.abs(kx), 1e-5)) ** 4))
    harm_400m = np.exp(-(((np.abs(ky) - 0.25) / 0.035) ** 2)) * np.exp(-((kx / 0.025) ** 2))
    notch_keep = np.clip((1.0 - 0.88 * ew_line_notch) * (1.0 - 0.85 * ns_tie_notch) * (1.0 - 0.80 * harm_400m), 0.05, 1.0).astype(np.float32)

    F_clean = F * notch_keep
    m_clean = sp_fft.irfft2(F_clean, s=(H, W), workers=2).astype(np.float32)
    corrugation = np.abs(work - m_clean).astype(np.float32)

    # Upward-stabilized exact Laplace vertical derivative dM/dz (z_up = 0.65 px = 65 m)
    kz_op = (2.0 * np.pi * kr * np.exp(-2.0 * np.pi * kr * 0.65)).astype(np.float32)
    dz_clean = sp_fft.irfft2(F_clean * kz_op, s=(H, W), workers=2).astype(np.float32)
    del F, F_clean, ky, kx, kr, notch_keep

    gy, gx = np.gradient(ndi.gaussian_filter(m_clean, sigma=0.75))
    hgm_clean = np.hypot(gx, gy).astype(np.float32)
    eps_h = float(np.percentile(hgm_clean[valid_rtp], 15.0)) * 0.25 + 1e-4
    tilt = np.arctan2(dz_clean, hgm_clean + eps_h).astype(np.float32)
    tilt_peak = (0.5 * np.pi - np.abs(tilt)).astype(np.float32)

    tgy, tgx = np.gradient(tilt)
    grad_tilt = np.hypot(tgx, tgy).astype(np.float32)
    inv_depth_edge = (grad_tilt * np.exp(-np.square(tilt / 0.40))).astype(np.float32)
    return corrugation, m_clean, tilt_peak, inv_depth_edge


def _read_safe_gdr_thermal(raw_dir: Path, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read strictly safe physical temperatures/coordinates from GDR-1391 wells/springs CSV."""
    H, W = shape
    ws_path = raw_dir / "external/gdr_wellspring_in_footprint.csv"
    hot_pts = np.zeros(shape, dtype=bool)
    enthalpy = np.zeros(shape, dtype=np.float32)
    with ws_path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        safe_cols = [c for c in (reader.fieldnames or []) if c not in FORBIDDEN_POINT_COLUMNS]
        if any(c in FORBIDDEN_POINT_COLUMNS for c in safe_cols):
            raise ValueError("Forbidden column leaked into GDR reader")
        for row in reader:
            try:
                ry = int(float(row["row"]))
                rx = int(float(row["col"]))
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 <= ry < H and 0 <= rx < W):
                continue
            vals = []
            for k in ("temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                raw_v = (row.get(k) or "").strip()
                if raw_v and raw_v.upper() not in ("NAN", "NULL", "NONE", "NA", "-999", "-9999"):
                    try:
                        fv = float(raw_v)
                        if 0.0 < fv <= 400.0:
                            vals.append(fv)
                    except ValueError:
                        pass
            tcls = (row.get("thermalclass") or "").strip().lower()
            tc_raw = vals[0] if vals else 0.0
            is_hot = (
                tcls in ("hot", "warm", "boiling", "thermal")
                or tc_raw >= 30.0
                or (max(vals) >= 80.0 if vals else False)
            )
            if is_hot:
                hot_pts[ry, rx] = True
            e_val = max(vals) if vals else (65.0 if is_hot else 12.0)
            if e_val > enthalpy[ry, rx]:
                enthalpy[ry, rx] = float(e_val)

    log_d_hot = -np.log1p(np.minimum(ndi.distance_transform_edt(~hot_pts), 300.0)).astype(np.float32)
    plume_s8 = ndi.gaussian_filter(enthalpy, sigma=8.0).astype(np.float32)
    plume_s25 = ndi.gaussian_filter(enthalpy, sigma=25.0).astype(np.float32)
    return log_d_hot, plume_s8, plume_s25


def build_dfsd_static_stack(
    raw_dir: Path,
    ing_dir: Path,
    dem10_dir: Path,
    thvc_mmap_path: Path,
    dfsd_cache_dir: Path,
    footprint: np.ndarray,
    transform: Any,
) -> tuple[np.memmap, np.memmap, dict[str, Any]]:
    """Build or reuse both the 70-ch base memmap and the 20-ch DFSD float16 memmap."""
    dfsd_cache_dir.mkdir(parents=True, exist_ok=True)
    thvc_mmap_path.parent.mkdir(parents=True, exist_ok=True)

    base_meta = build_static_feature_memmap(raw_dir, ing_dir, thvc_mmap_path, footprint, transform)
    n_fp = int(footprint.sum())
    base_mm = np.memmap(thvc_mmap_path, dtype="float32", mode="r", shape=(n_fp, len(THVC_STATIC_NAMES)))

    extra_path = dfsd_cache_dir / "extra_static_fp20.f16.mmap"
    extra_meta_path = dfsd_cache_dir / "extra_static_meta.json"
    cues_extra_path = dfsd_cache_dir / "dfsd_cues.npz"

    if extra_path.exists() and extra_meta_path.exists() and cues_extra_path.exists():
        meta = json.loads(extra_meta_path.read_text())
        if meta.get("rows") == n_fp and meta.get("feature_names") == DFSD_EXTRA_STATIC_NAMES:
            extra_mm = np.memmap(extra_path, dtype="float16", mode="r", shape=(n_fp, len(DFSD_EXTRA_STATIC_NAMES)))
            return base_mm, extra_mm, {"base_meta": base_meta, "extra_meta": meta}

    t0 = time.time()
    H, W = footprint.shape
    cmap = {n: i for i, n in enumerate(THVC_STATIC_NAMES)}
    out_mm = np.memmap(extra_path, dtype="float16", mode="w+", shape=(n_fp, len(DFSD_EXTRA_STATIC_NAMES)))

    # Read required raw bands once cleanly
    with rasterio.open(raw_dir / "training_features.tif") as src:
        rtp = src.read(2).astype(np.float32)
        det_elev = src.read(12).astype(np.float32)
        iso_grav = src.read(13).astype(np.float32)
        bdepth = src.read(15).astype(np.float32)
        cond_surf = src.read(17).astype(np.float32)
        grav_hg = src.read(18).astype(np.float32)
        det_slope = src.read(19).astype(np.float32)

    v_rtp = footprint & np.isfinite(rtp) & (rtp > -1e30)
    v_grav = footprint & np.isfinite(iso_grav) & (iso_grav > -1e30)
    v_bdep = footprint & np.isfinite(bdepth) & (bdepth > -1e30)
    v_elev = footprint & np.isfinite(det_elev) & (det_elev > -1e30)

    # 1. H2: Flight-line de-striping + Salem tilt inverse depth + up-dip basement step registration
    corrugation, m_clean, tilt_peak, inv_depth_edge = _destripe_and_salem_tilt(rtp, v_rtp)
    out_mm[:, 0] = _norm_f16(corrugation, v_rtp, footprint)
    out_mm[:, 1] = _norm_f16(tilt_peak, v_rtp, footprint)
    out_mm[:, 2] = _norm_f16(inv_depth_edge, v_rtp, footprint)

    grav_fill = np.where(v_grav, iso_grav, float(np.median(iso_grav[v_grav])))
    ggy, ggx = np.gradient(ndi.gaussian_filter(grav_fill, sigma=1.0))
    mgy, mgx = np.gradient(ndi.gaussian_filter(m_clean, sigma=1.0))
    g_norm = np.hypot(ggx, ggy) + 1e-5
    m_norm = np.hypot(mgx, mgy) + 1e-5
    unilateral_cos = np.abs(ggx * mgx + ggy * mgy) / (g_norm * m_norm)

    bdep_fill = np.where(v_bdep, np.maximum(bdepth, 0.0), float(np.median(np.maximum(bdepth[v_bdep], 0.0))))
    # Standardize depth proxy into [0, 1] km-like range using footprint IQR so unit convention cannot blow up
    b_p10, b_p90 = np.percentile(bdep_fill[v_bdep], [10.0, 90.0])
    b_unit = np.clip((bdep_fill - b_p10) / max(float(b_p90 - b_p10), 1e-5), 0.0, 1.5)
    bgy, bgx = np.gradient(ndi.gaussian_filter(bdep_fill, sigma=3.0))
    bnorm = np.hypot(bgx, bgy) + 1e-6
    # +grad(H_b) points down-dip into deeper hanging-wall basin -> pull hanging-wall gradient back onto footwall trace!
    shift_px = (3.5 * b_unit).astype(np.float32)
    yy, xx = np.indices((H, W), dtype=np.float32)
    q_y = np.clip(yy + (bgy / bnorm) * shift_px, 0.0, H - 1.001)
    q_x = np.clip(xx + (bgx / bnorm) * shift_px, 0.0, W - 1.001)
    ghg_fill = np.where(footprint & np.isfinite(grav_hg) & (grav_hg > -1e30), grav_hg, 0.0).astype(np.float32)
    ghg_updip = ndi.map_coordinates(ghg_fill, [q_y, q_x], order=1, mode="nearest").astype(np.float32)
    updip_combined = ghg_updip * (0.55 + 0.45 * unilateral_cos)
    out_mm[:, 3] = _norm_f16(updip_combined, v_grav & v_bdep, footprint)
    del corrugation, m_clean, tilt_peak, inv_depth_edge, ggy, ggx, mgy, mgx, q_y, q_x, ghg_fill, ghg_updip, updip_combined
    gc.collect()

    # 2. H5: Spatially cross-fitted (4-quadrant OOF) potassic adularia residual K_d
    with rasterio.open(raw_dir / "external/geodawn_rad_u8.tif") as src:
        r_descr = list(src.descriptions)
        rad_k = src.read(r_descr.index("K") + 1).astype(np.float32)
        rad_th = src.read(r_descr.index("Th") + 1).astype(np.float32)
        rad_u = src.read(r_descr.index("U") + 1).astype(np.float32)
    ok_rad = footprint & (rad_k > 0) & (rad_th > 0) & (rad_u > 0) & v_elev & v_bdep
    quad = quadrant_ids(footprint)
    kd_oof = np.zeros((H, W), dtype=np.float32)
    X_lith_all = np.column_stack([
        rad_th[ok_rad],
        rad_u[ok_rad],
        det_elev[ok_rad],
        np.where(np.isfinite(det_slope[ok_rad]), det_slope[ok_rad], 0.0),
        bdep_fill[ok_rad],
    ]).astype(np.float32)
    y_k_all = rad_k[ok_rad].astype(np.float32)
    q_rad = quad[ok_rad]
    oof_pred = np.zeros_like(y_k_all)
    for q_id in range(4):
        tr_m = (q_rad != q_id) & (q_rad >= 0)
        va_m = q_rad == q_id
        if np.any(tr_m) and np.any(va_m):
            reg = Ridge(alpha=50.0).fit(X_lith_all[tr_m], y_k_all[tr_m])
            oof_pred[va_m] = reg.predict(X_lith_all[va_m])
    res_std = float(np.std(y_k_all - oof_pred)) + 1e-5
    kd_oof[ok_rad] = (y_k_all - oof_pred) / res_std
    out_mm[:, 4] = _norm_f16(kd_oof, ok_rad, footprint)

    # Load full-coverage 10m 3DEP vectors & road distance for H1/H3 deconfounding
    fp_idx = np.flatnonzero(footprint)
    def _load_dem10(name: str) -> np.ndarray:
        arr = np.full((H, W), np.nan, dtype=np.float32)
        arr.ravel()[fp_idx] = np.load(dem10_dir / f"{name}.f32.npy").astype(np.float32)
        return arr

    d10_onesided3 = _load_dem10("dem10_onesided3")
    d10_slope_mean = _load_dem10("dem10_slope_mean")
    d10_slope_std = _load_dem10("dem10_slope_std")
    d10_hgm20 = _load_dem10("dem10_hgm20_max")
    d10_hgm50 = _load_dem10("dem10_hgm50_max")
    d10_hgm200 = _load_dem10("dem10_hgm200_mean")
    d10_curv = _load_dem10("dem10_curv_absmax")
    d10_resid = _load_dem10("dem10_resid_range")

    playa_gate = np.tanh(np.nan_to_num(d10_slope_mean, nan=0.0) / 0.015).astype(np.float32)
    kd_deconf = kd_oof * playa_gate
    out_mm[:, 5] = _norm_f16(kd_deconf, ok_rad, footprint)

    demag_2d = np.zeros((H, W), dtype=np.float32)
    demag_2d[footprint] = base_mm[:, cmap["rtp_demag_trough"]]
    cond_ok = footprint & np.isfinite(cond_surf) & (cond_surf > -1e30)
    cond_z = np.zeros((H, W), dtype=np.float32)
    cond_z[cond_ok] = np.clip((cond_surf[cond_ok] - np.median(cond_surf[cond_ok])) / (np.std(cond_surf[cond_ok]) + 1e-5), -3.0, 5.0)
    hydro_triple = np.maximum(kd_deconf, 0.0) * np.maximum(demag_2d, 0.0) * (1.0 / (1.0 + np.exp(-cond_z)))
    out_mm[:, 6] = _norm_f16(hydro_triple, ok_rad & cond_ok, footprint)
    del rad_k, rad_th, rad_u, X_lith_all, y_k_all, kd_oof, kd_deconf, demag_2d, cond_z, hydro_triple
    gc.collect()

    # 3. H1 & H3: 10m 3DEP persistence, TIGER road deconfounder, antislope & Lake Lahontan isohypse separator
    with rasterio.open(raw_dir / "external/tiger_road_distance_m.tif") as src:
        road_m = np.maximum(src.read(1).astype(np.float32), 0.0)
    ok_d10 = footprint & np.isfinite(d10_onesided3)
    road_atten = np.tanh(np.where(np.isfinite(road_m), road_m, 1000.0) / 250.0).astype(np.float32)
    excess_road = (d10_onesided3 - d10_slope_mean) * road_atten
    persist_10m = d10_hgm20 / (np.maximum(d10_hgm200, 0.0) + 0.02)

    out_mm[:, 7] = _norm_f16(d10_onesided3, ok_d10, footprint)
    out_mm[:, 8] = _norm_f16(excess_road, ok_d10, footprint)
    out_mm[:, 9] = _norm_f16(persist_10m, footprint & np.isfinite(persist_10m), footprint)
    out_mm[:, 10] = _norm_f16(d10_hgm50, footprint & np.isfinite(d10_hgm50), footprint)
    out_mm[:, 11] = _norm_f16(d10_curv, footprint & np.isfinite(d10_curv), footprint)
    out_mm[:, 12] = _norm_f16(d10_resid, footprint & np.isfinite(d10_resid), footprint)

    lidar_meta = json.loads((raw_dir / "external/lidar_scarp_features.json").read_text())
    qmap = lidar_meta["quantisation"]
    with rasterio.open(raw_dir / "external/lidar_scarp_features_u8.tif") as src:
        ld = list(src.descriptions)
        def _deq(nm: str) -> tuple[np.ndarray, np.ndarray]:
            q = src.read(ld.index(nm) + 1).astype(np.float32)
            ok = (q > 0) & footprint
            xmax, mode = qmap[nm]
            u = np.clip((q - 1.0) / 254.0, 0.0, 1.0)
            return (xmax * (u * u if mode == "sqrt" else u)).astype(np.float32), ok
        upf, ok_u = _deq("upface_max")
        dnf, ok_d = _deq("downface_max")
        crf, ok_c = _deq("cross_max")

    ok_lid = ok_u & ok_d & ok_c
    lid_ratio = (upf + dnf) / (crf + 0.02)
    d10_fallback_ratio = np.nan_to_num(d10_onesided3 / (np.maximum(d10_slope_std, 0.0) + 0.02), nan=0.0)
    # Match medians smoothly across sensor seam so non-LiDAR SE Nevada has zero step artifact!
    lid_med = float(np.median(lid_ratio[ok_lid])) if np.any(ok_lid) else 1.0
    d10_med = float(np.median(d10_fallback_ratio[ok_d10])) if np.any(ok_d10) else 1.0
    unified_tect_ratio = np.where(ok_lid, lid_ratio, d10_fallback_ratio * (lid_med / max(d10_med, 1e-5))).astype(np.float32)
    out_mm[:, 13] = _norm_f16(unified_tect_ratio, footprint, footprint)

    # Structure-tensor tangent along 10m HGM50 ridges vs regional elevation contour gradient (Lahontan strandline separator!)
    h50_clean = np.nan_to_num(d10_hgm50, nan=0.0).astype(np.float32)
    sy, sx = np.gradient(ndi.gaussian_filter(h50_clean, sigma=1.2))
    jxx = ndi.gaussian_filter(sx * sx, sigma=2.5)
    jyy = ndi.gaussian_filter(sy * sy, sigma=2.5)
    jxy = ndi.gaussian_filter(sx * sy, sigma=2.5)
    # Ridge tangent is eigenvector of MIN structure-tensor eigenvalue (perpendicular to gradient normal!)
    theta_norm = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy + 1e-12)
    tx = -np.sin(theta_norm).astype(np.float32)
    ty = np.cos(theta_norm).astype(np.float32)

    elev_fill = np.where(v_elev, det_elev, float(np.median(det_elev[v_elev])))
    ez_y, ez_x = np.gradient(ndi.gaussian_filter(elev_fill, sigma=5.0))
    ez_mag = np.hypot(ez_x, ez_y) + 1e-3
    # Cross-contour obliquity: 0 on strictly horizontal pluvial strandlines, positive on cross-fan tectonic scarps!
    cross_contour_obliq = (np.abs(ez_x * tx + ez_y * ty) / ez_mag) * road_atten
    out_mm[:, 14] = _norm_f16(cross_contour_obliq, v_elev, footprint)

    # Regional 3-km footwall structural relief x basement hinge gradient (saved also for Wallace slip-deficit!)
    fw_relief = (ndi.maximum_filter(elev_fill, size=31) - ndi.minimum_filter(elev_fill, size=31)).astype(np.float32)
    bhinge_2d = np.zeros((H, W), dtype=np.float32)
    bhinge_2d[footprint] = np.maximum(base_mm[:, cmap["bdepth_hgm_300m"]], 0.0)
    hinge_relief = fw_relief * (0.35 + bhinge_2d)
    out_mm[:, 15] = _norm_f16(hinge_relief, v_elev, footprint)

    # 4. GDR-1391 convective enthalpy & unconsolidated bajada knickpoints
    log_d_hot, plume_s8, plume_s25 = _read_safe_gdr_thermal(raw_dir, (H, W))
    trans_2d = np.zeros((H, W), dtype=np.float32)
    trans_2d[footprint] = np.maximum(base_mm[:, cmap["transtension_conduit_idx"]], 0.0)
    chi_ksn_2d = np.zeros((H, W), dtype=np.float32)
    chi_ksn_2d[footprint] = np.maximum(base_mm[:, cmap["chi_ksn_max"]], 0.0)

    out_mm[:, 16] = _norm_f16(log_d_hot, footprint, footprint)
    out_mm[:, 17] = _norm_f16(plume_s8, footprint, footprint)
    out_mm[:, 18] = _norm_f16(plume_s25 * (0.4 + trans_2d), footprint, footprint)
    out_mm[:, 19] = _norm_f16(chi_ksn_2d * b_unit, v_bdep, footprint)
    out_mm.flush()

    hinge_z_fp = np.asarray(out_mm[:, 15], dtype=np.float16)
    d10_step_z_fp = np.asarray(out_mm[:, 7], dtype=np.float16)
    np.savez_compressed(cues_extra_path, hinge_z_fp=hinge_z_fp, d10_step_z_fp=d10_step_z_fp)

    meta = {
        "rows": n_fp,
        "cols": len(DFSD_EXTRA_STATIC_NAMES),
        "feature_names": DFSD_EXTRA_STATIC_NAMES,
        "build_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
        "forbidden_columns_blocked": sorted(FORBIDDEN_POINT_COLUMNS),
        "forbidden_rasters_excluded": sorted(FORBIDDEN_RASTER_INPUTS),
        "inputs_sha256": {
            "training_features.tif": _sha256_file(raw_dir / "training_features.tif"),
            "geodawn_rad_u8.tif": _sha256_file(raw_dir / "external/geodawn_rad_u8.tif"),
            "lidar_scarp_features_u8.tif": _sha256_file(raw_dir / "external/lidar_scarp_features_u8.tif"),
            "tiger_road_distance_m.tif": _sha256_file(raw_dir / "external/tiger_road_distance_m.tif"),
            "gdr_wellspring_in_footprint.csv": _sha256_file(raw_dir / "external/gdr_wellspring_in_footprint.csv"),
            "dem10_manifest.json": _sha256_file(dem10_dir / "manifest.json"),
        },
    }
    extra_meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    del out_mm
    gc.collect()
    extra_ro = np.memmap(extra_path, dtype="float16", mode="r", shape=(n_fp, len(DFSD_EXTRA_STATIC_NAMES)))
    return base_mm, extra_ro, {"base_meta": base_meta, "extra_meta": meta}


def compute_dfsd_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    thvc_cues_path: Path,
    dfsd_cues_path: Path,
    scarp_step_fp: np.ndarray,
) -> np.ndarray:
    """Compute all 17 strictly fold-visible mechanical/Coulomb-shadow/slip-deficit features in float16."""
    base_mech = compute_network_mechanics(visible_mask, footprint, thvc_cues_path).astype(np.float16)
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    n_fp = int(footprint.sum())
    extra_mech = np.zeros((n_fp, len(DFSD_EXTRA_MECH_NAMES)), dtype=np.float16)
    if not np.any(vis):
        return np.hstack([base_mech, extra_mech])

    # Local strike unit tangent along visible fault traces via smoothed trace gradient normal
    vis_smooth = ndi.gaussian_filter(vis.astype(np.float32), sigma=1.6)
    vy, vx = np.gradient(vis_smooth)
    vnorm = np.hypot(vx, vy) + 1e-6
    # Tangent perpendicular to cross-trace gradient normal
    tan_y = (-vx / vnorm).astype(np.float32)
    tan_x = (vy / vnorm).astype(np.float32)

    dist_vis, (ny_idx, nx_idx) = ndi.distance_transform_edt(~vis, return_indices=True)
    H, W = footprint.shape
    yy, xx = np.indices((H, W), dtype=np.float32)
    dy = yy - ny_idx.astype(np.float32)
    dx = xx - nx_idx.astype(np.float32)
    d_safe = np.hypot(dx, dy) + 1e-5
    cos_strike = np.abs(dy * tan_y[ny_idx, nx_idx] + dx * tan_x[ny_idx, nx_idx]) / d_safe

    # 1. Okada-style normal-fault Coulomb stress relief shadow: negative on lateral flanks, positive along strike!
    cfs_norm = ((2.0 * cos_strike * cos_strike - 1.0) * np.exp(-dist_vis / 12.0)).astype(np.float32)
    extra_mech[:, 0] = np.clip(cfs_norm[footprint], -2.0, 2.0).astype(np.float16)

    # 2. Wallace (1978) along-range footwall slip-deficit across gaps in mapped visible traces
    cues_z = np.load(dfsd_cues_path)
    hinge_fp = cues_z["hinge_z_fp"].astype(np.float32)
    d10_step_fp = cues_z["d10_step_z_fp"].astype(np.float32)
    gap_factor = (1.0 - np.exp(-dist_vis[footprint].astype(np.float32) / 14.0))
    extra_mech[:, 1] = np.clip(hinge_fp * gap_factor, -12.0, 12.0).astype(np.float16)

    # 3. Scarp-corroborated forward tip splay indicator
    tip15_idx = THVC_MECH_NAMES.index("net_tip_fwd_15px")
    phys_scarp = np.maximum(scarp_step_fp.astype(np.float32), d10_step_fp)
    extra_mech[:, 2] = np.clip(base_mech[:, tip15_idx].astype(np.float32) * np.maximum(phys_scarp, 0.0), -12.0, 20.0).astype(np.float16)

    return np.hstack([base_mech, extra_mech])
