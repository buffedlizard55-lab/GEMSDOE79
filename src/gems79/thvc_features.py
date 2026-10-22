"""G79-THVC leak-free multi-physics, shallow 2-m thermal probe, paleo-geothermal
vent, hydrothermal alteration, Fourier potential-field continuation, multi-scale
terrain (1m LiDAR + 10m 3DEP + bedrock chi), and fold-isolated crack-tip / relay
mechanics feature engine.

Strict zero-leakage invariants:
  1. Never reads any prior prediction raster from registry / downloads.
  2. Never reads pre-Quaternary SGMC fault rasters as labels or direct targets.
  3. Explicitly raises ValueError if any forbidden label-proxy column
     (``dist_known_fault_px``, ``known_fault``, ``label``) is requested or used.
  4. Streams static channels directly to disk float32 memmap so peak RSS stays
     well under 800 MB on a 3.8 GiB sandbox.
  5. Group D network features are computed strictly from a supplied visible
     mask; training uses 5-fold component-masked inner partitions with the exact
     same ``buffer_px=3`` collar as outer holdout evaluation to prevent
     ``d_vis == 0`` self-memorization and guarantee zero train/test shift.
"""
from __future__ import annotations

import csv
import gc
import json
import resource
import struct
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import rankdata

FORBIDDEN_POINT_COLUMNS = frozenset({"dist_known_fault_px", "known_fault", "label"})
STRUCT3 = np.ones((3, 3), dtype=np.int8)

TF_BAND_NAMES = [
    "mag_anom",
    "rtp",
    "tmi_hg",
    "geod_2ndinv",
    "iso_grav_anom_slope",
    "tc",
    "geod_shearrate",
    "geod_dilaterate",
    "tmi_vg",
    "deq_n100a15",
    "iso_grav_anom_vg",
    "det_elev",
    "iso_grav_anom",
    "tmi",
    "depth_to_base_surf",
    "ieq_n100a15",
    "cond_surf",
    "iso_grav_anom_hg",
    "det_elev_slope",
]

HIGH_TEMP_PALEO_TYPES = frozenset(
    {
        "Sinter",
        "Explosion craters",
        "Silicified fault breccia",
        "Silica vein",
        "Calcite-qtz veins",
        "Sulfur",
        "Argillic alteration",
        "Silica-cemented sand",
        "Silica-cemented mud or ash",
    }
)

STATIC_FEATURE_NAMES = (
    [f"tf_{b}" for b in TF_BAND_NAMES]  # 0..18 (19)
    + [
        # Group A derived: Fourier Laplace continuation & crustal physics (17)
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
        # Group B: 2-m thermal probes, paleo-geothermal vents, GDR thermal, gamma-ray alteration (16)
        "t2m_dab_300m",
        "t2m_dab_900m",
        "t2m_dab_2200m",
        "t2m_dab_grad_ridge",
        "t2m_survey_weight",
        "paleo_vent_kde_800m",
        "paleo_vent_kde_2400m",
        "paleo_hitemp_sinter_1200m",
        "paleo_vent_strike_bridge",
        "gdr_thermal_anom_900m",
        "gdr_geotherm_qtz_1800m",
        "volc_vent_prox_3km",
        "rad_k_th_alteration",
        "rad_u_th_redox",
        "tmi_shallow_150m_res",
        "hydro_demag_clay_conj",
        # Group C: 1m LiDAR + 10m 3DEP quantile-bridged scarps + chi + cross-strike steps (18)
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
    ]
)

MECH_FEATURE_NAMES = [
    "net_log_dist",
    "net_exp_near_600",
    "net_exp_mid_1800",
    "net_exp_far_4500",
    "net_density_15px",
    "net_density_40px",
    "net_tip_fwd_15px",
    "net_tip_fwd_35px",
    "net_tip_wing_lobe",
    "net_colinear_bridge",
    "net_relay_stepover",
    "net_tip_x_scarp",
    "net_tip_x_grav_bdepth",
    "net_relay_x_hydro",
]

ALL_FEATURE_NAMES = STATIC_FEATURE_NAMES + MECH_FEATURE_NAMES


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def latlon_to_utm11(lat_deg: np.ndarray, lon_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact Snyder (1987, USGS Bull. 1532) Transverse Mercator to EPSG:32611."""
    a = 6378137.0
    f = 1.0 / 298.257223563
    e2 = f * (2.0 - f)
    ep2 = e2 / (1.0 - e2)
    k0 = 0.9996
    lat = np.deg2rad(np.asarray(lat_deg, dtype=np.float64))
    lon = np.deg2rad(np.asarray(lon_deg, dtype=np.float64))
    lon0 = np.deg2rad(-117.0)
    sin_lat, cos_lat, tan_lat = np.sin(lat), np.cos(lat), np.tan(lat)
    n_val = a / np.sqrt(1.0 - e2 * sin_lat**2)
    t_val = tan_lat**2
    c_val = ep2 * cos_lat**2
    a_val = cos_lat * (lon - lon0)
    m_val = a * (
        (1.0 - e2 / 4.0 - 3.0 * e2**2 / 64.0 - 5.0 * e2**3 / 256.0) * lat
        - (3.0 * e2 / 8.0 + 3.0 * e2**2 / 32.0 + 45.0 * e2**3 / 1024.0) * np.sin(2.0 * lat)
        + (15.0 * e2**2 / 256.0 + 45.0 * e2**3 / 1024.0) * np.sin(4.0 * lat)
        - (35.0 * e2**3 / 3072.0) * np.sin(6.0 * lat)
    )
    x = 500000.0 + k0 * n_val * (
        a_val
        + (1.0 - t_val + c_val) * a_val**3 / 6.0
        + (5.0 - 18.0 * t_val + t_val**2 + 72.0 * c_val - 58.0 * ep2) * a_val**5 / 120.0
    )
    y = k0 * (
        m_val
        + n_val
        * tan_lat
        * (
            a_val**2 / 2.0
            + (5.0 - t_val + 9.0 * c_val + 4.0 * c_val**2) * a_val**4 / 24.0
            + (61.0 - 58.0 * t_val + t_val**2 + 600.0 * c_val - 330.0 * ep2) * a_val**6 / 720.0
        )
    )
    return x, y


def parse_safe_csv(csv_path: Path, allowed_columns: tuple[str, ...]) -> list[dict[str, str]]:
    """Read only explicitly whitelisted columns; reject any forbidden leakage column."""
    bad = set(allowed_columns) & FORBIDDEN_POINT_COLUMNS
    if bad:
        raise ValueError(f"Forbidden leakage column requested: {sorted(bad)}")
    out: list[dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            out.append({k: row[k] for k in allowed_columns})
    return out


def _empirical_quantiles_1d(vals: np.ndarray) -> np.ndarray:
    if vals.size == 0 or np.ptp(vals) <= 0:
        return np.zeros(vals.shape, dtype=np.float32)
    return ((rankdata(vals, method="average") - 1.0) / max(vals.size - 1, 1)).astype(np.float32)


def _fft_upward_continue(field: np.ndarray, heights_m: tuple[float, ...], dx_m: float = 100.0) -> dict[float, np.ndarray]:
    """Exact 2D Fourier Laplace upward continuation exp(-z * |k|) with mirror edge taper."""
    pad = 96
    f_pad = np.pad(field.astype(np.float32), pad, mode="reflect")
    ny, nx = f_pad.shape
    ky = 2.0 * np.pi * np.fft.fftfreq(ny, d=dx_m).astype(np.float32)[:, None]
    kx = 2.0 * np.pi * np.fft.rfftfreq(nx, d=dx_m).astype(np.float32)[None, :]
    k_rad = np.hypot(ky, kx)
    spec = np.fft.rfft2(f_pad)
    results: dict[float, np.ndarray] = {}
    for z in heights_m:
        cont = np.fft.irfft2(spec * np.exp(-float(z) * k_rad), s=(ny, nx))
        results[z] = cont[pad : pad + field.shape[0], pad : pad + field.shape[1]].astype(np.float32)
    del spec, k_rad, f_pad
    return results


def _crest_prominence_4az(g: np.ndarray) -> np.ndarray:
    """Blakely-Simpson (1986) ridge excess above opposing 2-px neighbors across 4 azimuths."""
    g = g.astype(np.float32, copy=False)
    out = np.zeros_like(g)
    for dy, dx in ((2, 0), (0, 2), (2, 2), (2, -2)):
        p1 = np.roll(g, shift=(dy, dx), axis=(0, 1))
        p2 = np.roll(g, shift=(-dy, -dx), axis=(0, 1))
        excess = g - 0.5 * (p1 + p2)
        out = np.maximum(out, excess)
    out[:2, :] = 0.0
    out[-2:, :] = 0.0
    out[:, :2] = 0.0
    out[:, -2:] = 0.0
    return np.maximum(out, 0.0)


def _draw_segment_score(grid: np.ndarray, r0: float, c0: float, r1: float, c1: float, val: float) -> None:
    steps = max(int(np.hypot(r1 - r0, c1 - c0) * 1.5), 2)
    ts = np.linspace(0.0, 1.0, steps, dtype=np.float32)
    rr = np.rint(r0 + ts * (r1 - r0)).astype(np.int32)
    cc = np.rint(c0 + ts * (c1 - c0)).astype(np.int32)
    ok = (rr >= 0) & (rr < grid.shape[0]) & (cc >= 0) & (cc < grid.shape[1])
    if np.any(ok):
        np.maximum.at(grid, (rr[ok], cc[ok]), np.float32(val))


def build_static_feature_memmap(
    raw_dir: Path,
    ing_dir: Path,
    out_path: Path,
    footprint: np.ndarray,
    transform: Any,
) -> dict[str, Any]:
    """Stream all 70 static channels into a float32 memmap over the 5,167,373 active cells."""
    t0 = time.time()
    n_fp = int(footprint.sum())
    n_static = len(STATIC_FEATURE_NAMES)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = out_path.with_suffix(".meta.json")
    if out_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("rows") == n_fp
            and meta.get("cols") == n_static
            and meta.get("feature_names") == STATIC_FEATURE_NAMES
            and out_path.stat().st_size == n_fp * n_static * 4
        ):
            return meta

    mm = np.memmap(out_path, dtype="float32", mode="w+", shape=(n_fp, n_static))
    col_map = {name: i for i, name in enumerate(STATIC_FEATURE_NAMES)}

    def write_col(name: str, arr2d: np.ndarray) -> None:
        vec = np.asarray(arr2d[footprint], dtype=np.float32)
        vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
        mm[:, col_map[name]] = vec

    def read_tf_band(b1: int) -> np.ndarray:
        with rasterio.open(raw_dir / "training_features.tif") as ds:
            a = ds.read(b1).astype(np.float32)
        valid = footprint & np.isfinite(a) & (a > -1e30)
        med = float(np.median(a[valid])) if np.any(valid) else 0.0
        a = np.where(valid, a, med).astype(np.float32)
        return a

    # 1. Stream all 19 official competition bands + retain compact references needed for transforms
    kept: dict[str, np.ndarray] = {}
    need_keep = {"rtp", "iso_grav_anom", "det_elev", "depth_to_base_surf", "geod_dilaterate", "geod_shearrate", "cond_surf", "tmi"}
    for idx0, bname in enumerate(TF_BAND_NAMES):
        arr = read_tf_band(idx0 + 1)
        write_col(f"tf_{bname}", arr)
        if bname in need_keep:
            kept[bname] = arr
        else:
            del arr
    gc.collect()

    # 2. Exact 2D Fourier Laplace upward continuation on RTP & Isostatic Gravity
    rtp = kept.pop("rtp")
    uc_rtp = _fft_upward_continue(rtp, (200.0, 600.0, 800.0))
    write_col("rtp_uc600_res", rtp - uc_rtp[600.0])
    demag = np.maximum(uc_rtp[800.0] - rtp, 0.0)
    write_col("rtp_demag_trough", demag)

    ry2, rx2 = np.gradient(uc_rtp[200.0])
    hgm_r2 = np.hypot(rx2, ry2) + 1e-6
    dz_r2 = (rtp - uc_rtp[200.0]) / 2.0
    tilt_r2 = np.arctan2(dz_r2, hgm_r2)

    ry8, rx8 = np.gradient(uc_rtp[800.0])
    hgm_r8 = np.hypot(rx8, ry8) + 1e-6
    dz_r8 = (uc_rtp[200.0] - uc_rtp[800.0]) / 6.0
    tilt_r8 = np.arctan2(dz_r8, hgm_r8)

    write_col("rtp_hgm_z200", hgm_r2)
    write_col("rtp_tilt_z200_abs", np.abs(tilt_r2))
    write_col("rtp_tilt_dip_shift", np.abs(tilt_r2 - tilt_r8))
    write_col("rtp_crest_prom", _crest_prominence_4az(hgm_r2))
    dz_gy, dz_gx = np.gradient(dz_r2)
    write_col("euler_si_rtp", np.clip(np.hypot(dz_gx, dz_gy) / (hgm_r2 + 0.05), 0.0, 5.0))
    del rtp, uc_rtp, ry2, rx2, hgm_r2, dz_r2, tilt_r2, ry8, rx8, hgm_r8, dz_r8, tilt_r8, dz_gy, dz_gx
    gc.collect()

    grav = kept.pop("iso_grav_anom")
    uc_grav = _fft_upward_continue(grav, (200.0, 800.0))
    write_col("grav_uc800_res", grav - uc_grav[800.0])
    gy2, gx2 = np.gradient(uc_grav[200.0])
    hgm_g2 = np.hypot(gx2, gy2) + 1e-6
    dz_g2 = (grav - uc_grav[200.0]) / 2.0
    tilt_g2 = np.arctan2(dz_g2, hgm_g2)

    gy8, gx8 = np.gradient(uc_grav[800.0])
    hgm_g8 = np.hypot(gx8, gy8) + 1e-6
    dz_g8 = (uc_grav[200.0] - uc_grav[800.0]) / 6.0
    tilt_g8 = np.arctan2(dz_g8, hgm_g8)

    write_col("grav_hgm_z200", hgm_g2)
    write_col("grav_hgm_z800", hgm_g8)
    write_col("grav_tilt_z200_abs", np.abs(tilt_g2))
    write_col("grav_tilt_dip_shift", np.abs(tilt_g2 - tilt_g8))
    grav_crest = _crest_prominence_4az(hgm_g2)
    write_col("grav_crest_prom", grav_crest)
    grav_smooth = uc_grav[200.0].copy()
    del grav, uc_grav, gy2, gx2, dz_g2, tilt_g2, gy8, gx8, hgm_g8, dz_g8, tilt_g8
    gc.collect()

    bdepth = kept.pop("depth_to_base_surf")
    bg3_y = ndi.gaussian_filter(bdepth, 3.0, order=(1, 0), mode="nearest")
    bg3_x = ndi.gaussian_filter(bdepth, 3.0, order=(0, 1), mode="nearest")
    bdepth_hgm3 = np.hypot(bg3_x, bg3_y)
    write_col("bdepth_hgm_300m", bdepth_hgm3)
    bg9_y = ndi.gaussian_filter(bdepth, 9.0, order=(1, 0), mode="nearest")
    bg9_x = ndi.gaussian_filter(bdepth, 9.0, order=(0, 1), mode="nearest")
    write_col("bdepth_hgm_900m", np.hypot(bg9_x, bg9_y))
    del bdepth, bg3_x, bg3_y, bg9_x, bg9_y

    dil = kept.pop("geod_dilaterate")
    shr = kept.pop("geod_shearrate")
    cond = kept.pop("cond_surf")
    cond_pos = np.log1p(np.maximum(cond - np.median(cond[footprint]), 0.0))
    transtens = np.maximum(dil, 0.0) * np.abs(shr) * (1.0 + cond_pos)
    write_col("transtension_conduit_idx", transtens)
    del dil, shr, cond, transtens

    det_elev = kept.pop("det_elev")
    det_prom = det_elev - ndi.gaussian_filter(det_elev, 6.0, mode="nearest")
    write_col("det_elev_prom_600m", det_prom)
    del det_prom
    gc.collect()

    # 3. Group B: Shallow 2-m temperature probes (2,782 stations), Paleo-geothermal vents (281), GDR thermal, GeoDAWN rad
    H, W = footprint.shape
    t2_num = np.zeros((H, W), dtype=np.float32)
    t2_cnt = np.zeros((H, W), dtype=np.float32)
    with zipfile.ZipFile(ing_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip") as zf:
        dbf = zf.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    num_rec, hdr_len, rec_len = struct.unpack("<IHH", dbf[4:12])
    fields = []
    pos = 32
    while dbf[pos] != 0x0D:
        fname = dbf[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        fields.append((fname, dbf[pos + 16]))
        pos += 32
    lats_2m, lons_2m, dabs_2m = [], [], []
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

    for sig, cname in ((3.0, "t2m_dab_300m"), (9.0, "t2m_dab_900m"), (22.0, "t2m_dab_2200m")):
        s_num = ndi.gaussian_filter(t2_num, sig, mode="constant", cval=0.0)
        s_den = ndi.gaussian_filter(t2_cnt, sig, mode="constant", cval=0.0)
        sm = np.divide(s_num, s_den + 1e-4, out=np.zeros_like(s_num), where=s_den > 1e-5)
        write_col(cname, sm)
        if sig == 3.0:
            gy_t, gx_t = np.gradient(ndi.gaussian_filter(sm, 1.5, mode="nearest"))
            write_col("t2m_dab_grad_ridge", np.hypot(gx_t, gy_t))
            del gy_t, gx_t
    d_probe = ndi.distance_transform_edt(t2_cnt == 0)
    write_col("t2m_survey_weight", np.exp(-d_probe / 15.0))
    del t2_num, t2_cnt, d_probe
    gc.collect()

    # Paleo-geothermal vents (281 in-footprint) + strike bridges across nearby vents
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
    gc.collect()

    # Safe GDR wells/springs & volcanic vents (FORBIDDEN columns never touched!)
    ws_rows = parse_safe_csv(
        raw_dir / "external/gdr_wellspring_in_footprint.csv",
        ("row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c"),
    )
    ws_t = np.zeros((H, W), dtype=np.float32)
    ws_q = np.zeros((H, W), dtype=np.float32)
    for r in ws_rows:
        try:
            ri, ci = int(float(r["row"])), int(float(r["col"]))
            if 0 <= ri < H and 0 <= ci < W:
                tc_val = float(r["temp_c"]) if r["temp_c"] not in ("", "nan", "NaN") else 0.0
                gq_val = float(r["geothermquartz_c"]) if r["geothermquartz_c"] not in ("", "nan", "NaN") else 0.0
                if np.isfinite(tc_val) and tc_val > 22.0:
                    ws_t[ri, ci] = max(ws_t[ri, ci], min(tc_val - 20.0, 150.0))
                if np.isfinite(gq_val) and gq_val > 60.0:
                    ws_q[ri, ci] = max(ws_q[ri, ci], min(gq_val - 50.0, 220.0))
        except ValueError:
            pass
    ws_t9 = ndi.gaussian_filter(ws_t, 9.0, mode="constant", cval=0.0)
    ws_q18 = ndi.gaussian_filter(ws_q, 18.0, mode="constant", cval=0.0)
    write_col("gdr_thermal_anom_900m", ws_t9)
    write_col("gdr_geotherm_qtz_1800m", ws_q18)
    del ws_rows, ws_t, ws_q

    vv_rows = parse_safe_csv(raw_dir / "external/gdr_volcanic_vents_in_footprint.csv", ("row", "col"))
    vv_m = np.ones((H, W), dtype=bool)
    for r in vv_rows:
        try:
            ri, ci = int(float(r["row"])), int(float(r["col"]))
            if 0 <= ri < H and 0 <= ci < W:
                vv_m[ri, ci] = False
        except ValueError:
            pass
    write_col("volc_vent_prox_3km", np.exp(-ndi.distance_transform_edt(vv_m) / 30.0))
    del vv_m

    # Radiometrics & GeoDAWN shallow magnetic residual
    with rasterio.open(raw_dir / "external/geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32) / 255.0
        rad_th = ds.read(2).astype(np.float32) / 255.0
    k_th_alt = np.clip(rad_k / (rad_th + 0.08), 0.0, 6.0)
    k_th_local = np.maximum(k_th_alt - ndi.gaussian_filter(k_th_alt, 12.0, mode="nearest"), 0.0)
    write_col("rad_k_th_alteration", k_th_local)
    del rad_k, rad_th, k_th_alt

    with rasterio.open(raw_dir / "external/geodawn_extensions_u8.tif") as ds:
        ext_uth = ds.read(3).astype(np.float32) / 255.0
        ext_tmi150 = ds.read(4).astype(np.float32) / 255.0
    write_col("rad_u_th_redox", ext_uth)
    tmi_raw = kept.pop("tmi")
    tmi_norm = (tmi_raw - np.percentile(tmi_raw[footprint], 1.0)) / (
        np.percentile(tmi_raw[footprint], 99.0) - np.percentile(tmi_raw[footprint], 1.0) + 1e-6
    )
    write_col("tmi_shallow_150m_res", np.clip(tmi_norm, 0.0, 1.0) - ext_tmi150)
    del tmi_raw, tmi_norm, ext_uth, ext_tmi150

    hydro_conj = np.log1p(demag) * (1.0 + 3.0 * k_th_local) * (1.0 + cond_pos)
    write_col("hydro_demag_clay_conj", hydro_conj)
    hydro_cue = (
        _empirical_quantiles_1d(hydro_conj[footprint])
        + 0.6 * _empirical_quantiles_1d(v_bridge_sm[footprint])
        + 0.6 * _empirical_quantiles_1d((ws_t9 + 0.5 * ws_q18)[footprint])
    )
    hydro_2d = np.zeros((H, W), dtype=np.float32)
    hydro_2d[footprint] = hydro_cue / 2.2
    del demag, k_th_local, cond_pos, hydro_conj, v_bridge_sm, ws_t9, ws_q18
    gc.collect()

    # 4. Group C: Quantile-bridged 1m LiDAR + 10m 3DEP + bedrock chi + road confound + 8-azimuth trace/step
    with rasterio.open(raw_dir / "external/lidar_scarp_features_u8.tif") as ds:
        lid_ex = ds.read(1).astype(np.float32)
        lid_step = ds.read(3).astype(np.float32)
        lid_lapn = ds.read(4).astype(np.float32)
        lid_lapp = ds.read(5).astype(np.float32)
        lid_down = ds.read(6).astype(np.float32)
        lid_up = ds.read(7).astype(np.float32)
        lid_coh = ds.read(10).astype(np.float32)
        lid_valid = (ds.read(12) > 0) & footprint

    with rasterio.open(ing_dir / "topo_10m_derived_100m_u8.tif") as ds:
        t10_sp90 = ds.read(1).astype(np.float32)
        t10_smax = ds.read(2).astype(np.float32)
        t10_rel = ds.read(5).astype(np.float32)
        t10_curv = ds.read(6).astype(np.float32)
        t10_acoh = ds.read(7).astype(np.float32)
        t10_line = ds.read(8).astype(np.float32)

    write_col("lidar_present", lid_valid.astype(np.float32))
    gap_mask = footprint & ~lid_valid

    def bridge_quantile(lid_arr: np.ndarray, t10_arr: np.ndarray) -> np.ndarray:
        out = np.zeros((H, W), dtype=np.float32)
        out[lid_valid] = _empirical_quantiles_1d(lid_arr[lid_valid])
        out[gap_mask] = _empirical_quantiles_1d(t10_arr[gap_mask])
        return out

    u_step = bridge_quantile(lid_step, np.maximum(t10_smax - 0.65 * t10_sp90, 0.0))
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
    write_col("topo10_slope_p90", t10_sp90 / 255.0)
    write_col("topo10_relief_local", t10_rel / 255.0)

    reg_relief = ndi.gaussian_filter(t10_rel, 12.0, mode="nearest") + 8.0
    write_col("mountain_wall_ratio", u_step / (reg_relief / 40.0))
    del lid_ex, lid_step, lid_lapn, lid_lapp, lid_down, lid_up, lid_coh, asym
    del t10_sp90, t10_smax, t10_rel, t10_curv, t10_acoh, t10_line, reg_relief

    with rasterio.open(raw_dir / "external/tiger_road_distance_m.tif") as ds:
        road_d = ds.read(1).astype(np.float32)
    road_d = np.where(np.isfinite(road_d) & (road_d >= 0.0), road_d, 5000.0)
    road_prox = np.exp(-road_d / 150.0).astype(np.float32)
    write_col("road_proximity_confound", road_prox)
    del road_d

    with rasterio.open(ing_dir / "dem10_chi_100m_i16.tif") as ds:
        chi_step = np.maximum(ds.read(1).astype(np.float32), 0.0) / 1000.0
        chi_ksn = np.maximum(ds.read(3).astype(np.float32), 0.0)
        chi_z = ds.read(5).astype(np.float32)
    write_col("chi_step_max", chi_step)
    write_col("chi_ksn_max", np.log1p(chi_ksn))
    playa = ((chi_ksn < 12.0) & (chi_z < np.percentile(chi_z[footprint], 35.0))).astype(np.float32)
    write_col("chi_playa_raised", playa)
    del chi_step, chi_ksn, chi_z, playa
    gc.collect()

    # 8-azimuth directional trace integrals & cross-strike block-step asymmetry
    scarp_comp = (0.45 * u_step + 0.25 * u_curv + 0.30 * u_line) * (1.0 - 0.35 * road_prox)
    del u_ex, u_curv, u_line, road_prox
    max_800 = np.zeros((H, W), dtype=np.float32)
    min_800 = np.full((H, W), 1e9, dtype=np.float32)
    max_2000 = np.zeros((H, W), dtype=np.float32)
    step_elev = np.zeros((H, W), dtype=np.float32)
    step_grav = np.zeros((H, W), dtype=np.float32)
    for k_az in range(8):
        ang_deg = k_az * 22.5
        # scipy gaussian_filter1d along rotated axes approximated cleanly via oriented 2D separable/convolve kernel
        rad = np.deg2rad(ang_deg)
        ty, tx = np.cos(rad), np.sin(rad)
        ny_v, nx_v = -tx, ty
        # 9-tap line filter for 800 m along strike
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

        # Cross-strike step asymmetry at +/- 6 px (elev) and +/- 8 px (gravity)
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

    # Save compact static physical cues needed by Group D physics x tip/relay interactions
    cues_path = out_path.with_suffix(".cues.npz")
    np.savez_compressed(
        cues_path,
        scarp_step=u_step[footprint].astype(np.float16),
        grav_bdepth=(
            0.5 * _empirical_quantiles_1d(grav_crest[footprint])
            + 0.5 * _empirical_quantiles_1d(bdepth_hgm3[footprint])
        ).astype(np.float16),
        hydro=hydro_2d[footprint].astype(np.float16),
    )
    mm.flush()
    del mm, scarp_comp, max_800, min_800, max_2000, step_elev, step_grav, det_elev, grav_smooth, grav_crest, bdepth_hgm3, u_step, hydro_2d
    gc.collect()

    meta = {
        "rows": n_fp,
        "cols": n_static,
        "feature_names": STATIC_FEATURE_NAMES,
        "build_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
        "forbidden_columns_blocked": sorted(FORBIDDEN_POINT_COLUMNS),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def _extract_tips_and_tangents(vis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Extract skeleton/strand terminations and local outward unit tangent vectors."""
    vis_u8 = vis.astype(np.uint8)
    nbr_cnt = ndi.convolve(vis_u8, STRUCT3, mode="constant", cval=0) - vis_u8
    # True strand endpoints (1 neighbor) or sharp bends/tips (<=2 neighbors in component)
    endpoints = vis & ((nbr_cnt == 1) | (nbr_cnt == 0))
    comp, n_comp = ndi.label(vis, STRUCT3)
    ty_list, tx_list, vy_list, vx_list = [], [], [], []
    slices = ndi.find_objects(comp)
    for cid, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        sub = comp[sl] == cid
        if int(sub.sum()) < 3:
            continue
        ep_sub = endpoints[sl] & sub
        ey, ex = np.nonzero(ep_sub)
        if ey.size == 0:
            sy, sx = np.nonzero(sub)
            # Closed loop fallback: take extreme endpoints along principal axis
            pts = np.column_stack([sy, sx]).astype(np.float64)
            pts_c = pts - pts.mean(axis=0)
            _, _, vt = np.linalg.svd(pts_c, full_matrices=False)
            proj = pts_c @ vt[0]
            picks = [int(np.argmin(proj)), int(np.argmax(proj))]
            ey, ex = sy[picks], sx[picks]
        sy_all, sx_all = np.nonzero(sub)
        pts_all = np.column_stack([sy_all, sx_all]).astype(np.float64)
        oy, ox = sl[0].start, sl[1].start
        for py, px in zip(ey.tolist(), ex.tolist()):
            d = np.hypot(pts_all[:, 0] - py, pts_all[:, 1] - px)
            loc = pts_all[(d > 0.0) & (d <= 9.0)]
            if loc.shape[0] < 2:
                loc = pts_all[d > 0.0]
            if loc.shape[0] == 0:
                continue
            # Outward vector points AWAY from interior mean of strand toward tip!
            vec = np.array([float(py) - loc[:, 0].mean(), float(px) - loc[:, 1].mean()], dtype=np.float64)
            nrm = float(np.hypot(vec[0], vec[1]))
            if nrm < 1e-6:
                continue
            vec /= nrm
            ty_list.append(float(oy + py))
            tx_list.append(float(ox + px))
            vy_list.append(vec[0])
            vx_list.append(vec[1])
    if not ty_list:
        return np.zeros((0, 2), dtype=np.float64), np.zeros((0, 2), dtype=np.float64)
    return np.column_stack([ty_list, tx_list]), np.column_stack([vy_list, vx_list])


def compute_network_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    cues_npz_path: Path,
) -> np.ndarray:
    """Compute all 14 Group D elastic crack-tip, wing-crack & relay mechanics strictly from ``visible_mask``.

    Returns shape ``(n_fp, 14)`` in ``float32``.
    """
    H, W = footprint.shape
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    n_fp = int(footprint.sum())
    out = np.zeros((n_fp, len(MECH_FEATURE_NAMES)), dtype=np.float32)
    if not np.any(vis):
        return out

    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    out[:, 0] = np.log1p(d_vis[footprint])
    out[:, 1] = np.exp(-d_vis[footprint] / 6.0)
    out[:, 2] = np.exp(-d_vis[footprint] / 18.0)
    out[:, 3] = np.exp(-d_vis[footprint] / 45.0)
    del d_vis

    vis_f = vis.astype(np.float32)
    out[:, 4] = ndi.gaussian_filter(vis_f, 15.0, mode="constant", cval=0.0)[footprint]
    out[:, 5] = ndi.gaussian_filter(vis_f, 40.0, mode="constant", cval=0.0)[footprint]
    del vis_f

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
        # +/- 28 deg transtensional wing cracks (Pollard & Segall 1987)
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
            # Co-linear blind wash gap bridge
            if c_i > 0.65 and c_j > 0.65:
                w = float(c_i * c_j * np.exp(-dist / 26.0))
                _draw_segment_score(colin, tips_yx[i, 0], tips_yx[i, 1], tips_yx[j, 0], tips_yx[j, 1], w)
            # En-echelon overlapping / stepping relay ramp (Peacock & Sanderson 1991; Faulds & Hinz 2015)
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

    cues = np.load(cues_npz_path)
    scarp_fp = cues["scarp_step"].astype(np.float32)
    gb_fp = cues["grav_bdepth"].astype(np.float32)
    hyd_fp = cues["hydro"].astype(np.float32)
    tip_any = np.maximum(out[:, 7], out[:, 9])
    out[:, 11] = tip_any * scarp_fp
    out[:, 12] = tip_any * gb_fp
    out[:, 13] = np.maximum(out[:, 10], out[:, 8]) * hyd_fp
    del fwd15, fwd35, wing, colin, relay
    return out


def build_self_masked_training_mechanics(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    cues_npz_path: Path,
    buffer_px: int = 3,
    n_splits: int = 5,
    seed: int = 79,
) -> np.ndarray:
    """Construct zero-collapse training Group D channels strictly inside ``visible_mask``.

    Partitions connected components of ``visible_mask`` into ``n_splits`` disjoint sets,
    assigns every footprint pixel to the split of its nearest ``visible_mask`` component
    via exact Voronoi nearest-index EDT, and evaluates ``compute_network_mechanics`` on
    ``visible_mask & ~collar(split_m, buffer_px)`` so EVERY training positive & nearby
    negative experiences the exact ``buffer_px=3`` holdout geometry instead of ``d_vis==0``.
    """
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    comp, n_comp = ndi.label(vis, STRUCT3)
    if n_comp == 0:
        return np.zeros((int(footprint.sum()), len(MECH_FEATURE_NAMES)), dtype=np.float32)
    rng = np.random.default_rng(seed)
    comp_bucket = np.zeros(n_comp + 1, dtype=np.int16)
    comp_bucket[1:] = rng.integers(0, n_splits, size=n_comp, dtype=np.int16)

    # Exact Voronoi partition of entire grid to nearest visible component pixel
    _, (ny, nx) = ndi.distance_transform_edt(~vis, return_indices=True)
    nearest_bucket_fp = comp_bucket[comp[ny[footprint], nx[footprint]]]
    del ny, nx

    out = np.zeros((int(footprint.sum()), len(MECH_FEATURE_NAMES)), dtype=np.float32)
    for b in range(n_splits):
        held_b = np.isin(comp, np.flatnonzero(comp_bucket == b)) & vis
        collar_b = ndi.distance_transform_edt(~held_b) <= float(buffer_px)
        vis_b = vis & ~collar_b
        part_feat = compute_network_mechanics(vis_b, footprint, cues_npz_path)
        sel = nearest_bucket_fp == b
        out[sel] = part_feat[sel]
        del held_b, collar_b, vis_b, part_feat
        gc.collect()
    return out
