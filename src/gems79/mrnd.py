"""H79-MRND: Multi-Regime Brittle-Crustal Nested Discovery.

Preregistered before any execution in ``registry/preregistration_mrnd.json``
(SHA-256 locked in ``evidence/preregistration_mrnd_sha256.txt``) and documented
in ``research/hypotheses_mrnd_800321e2.md``.

Scientific architecture
-----------------------
1. Physically decodes USGS 3DEP 1 m lidar scarp descriptors via exact inverse
   square-root / linear quantisation metadata (``lidar_scarp_features.json``),
   suppresses anthropogenic highway/canal embankments using U.S. Census
   TIGER/Line distance (``tiger_road_distance_m.tif``), and separates contour-
   parallel normal fault scarps from down-slope erosional gullies/canyons via
   ``scarp_vs_channel = (max(upface, downface) - cross_max) / (sum + 1e-3)``.
2. Integrates multi-scale potential-field horizontal-gradient worms across
   isostatic gravity, reduced-to-pole magnetics, upward-continued TMI_up150,
   and MT electrical conductivity interacted with sedimentary cover thickness
   (``depth_to_base_surf``).
3. Integrates INGENIOUS (DOE GDR 1391) aqueous geothermometry (quartz,
   chalcedony, Na-K-Ca cation) and measured spring/well temperatures across
   27,092 sites plus Quaternary volcanic vents — strictly dropping
   ``dist_known_fault_px`` on ingest.
4. Trains three specialized ``HistGradientBoostingRegressor`` models predicting
   official 300 m kernel credit ``k(d) = max(1 - d/3px, 0)`` on nested hidden
   fault components within three Basin-and-Range structural domains:
     * Regime I  (0 < d <= 1,400 m, share 0.24): relays, crack tips, splays
     * Regime II (1,400 < d <= 4,500 m, share 0.34): piedmont bajada scarps
     * Regime III (d > 4,500 m, share 0.42): concealed intra-basin & blind upflow
   with dimensionless within-regime footwall canyon relief suppression
   (``Hermant et al., 2025``), calibrated analytically into a single continuous
   confidence surface ``S(x) in [0, 1]`` prior to deterministic 3 px NMS.

No registry raster (``.cache/registry/**``) is ever read during feature
construction, training, surface calibration, or dot placement.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CACHE = ROOT / ".cache" / "mrnd"
STRUCT8 = np.ones((3, 3), bool)
PIXEL_M = 100.0

REGIME_SPECS = (
    ("R1_relay_tip_mod", 0.0, 14.0, 0.24),
    ("R2_piedmont_bajada", 14.0, 45.0, 0.34),
    ("R3_concealed_intrabasin", 45.0, float("inf"), 0.42),
)

RAD_BANDS = ("K", "Th", "U", "TC")
EXT_BANDS = ("ThK", "UK", "UTh", "TMI_up150")
LIDAR_FEATURE_BANDS = (
    "ex_max",
    "ex_mean",
    "step_max",
    "lapneg_max",
    "lappos_max",
    "downface_max",
    "upface_max",
    "cross_max",
    "relief",
    "coh100",
)
GEOMETRY_NAMES = (
    "log_dist_visible",
    "visible_density_s5",
    "visible_density_s20",
    "log_dist_visible_tip",
    "tip_propagation_cone",
    "lidar_strike_alignment",
    "strike_field_coherence",
)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_lidar_band(q: np.ndarray, xmax: float, mode: str) -> np.ndarray:
    """Invert quantisation defined in ``lidar_scarp_features.json``.

    ``q == 0`` marks cells without 3DEP lidar coverage and decodes to ``NaN``.
    """
    arr = np.asarray(q)
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    ok = arr > 0
    if not np.any(ok):
        return out
    t = (arr[ok].astype(np.float32) - 1.0) / 254.0
    if mode == "sqrt":
        out[ok] = (float(xmax) * t * t).astype(np.float32)
    elif mode == "linear":
        out[ok] = (float(xmax) * t).astype(np.float32)
    else:
        raise ValueError(f"Unsupported quantisation mode: {mode!r}")
    return out


def road_deseam_weight(road_dist_m: np.ndarray, scale_m: float = 150.0, floor: float = 0.15) -> np.ndarray:
    """Suppress highway, railroad, and canal embankment scarps near TIGER roads."""
    d = np.where(np.isfinite(road_dist_m), np.maximum(road_dist_m, 0.0), scale_m)
    return np.clip(d / float(scale_m), float(floor), 1.0).astype(np.float32)


def scarp_vs_channel_index(upface: np.ndarray, downface: np.ndarray, cross: np.ndarray) -> np.ndarray:
    """Discriminate contour-parallel fault scarps (>0) from down-slope gullies (<0)."""
    along_slope = np.maximum(upface, downface)
    out = np.full(upface.shape, np.nan, dtype=np.float32)
    ok = np.isfinite(along_slope) & np.isfinite(cross)
    num = along_slope[ok] - cross[ok]
    den = along_slope[ok] + cross[ok] + 1e-3
    out[ok] = (num / den).astype(np.float32)
    return out


def compute_canyon_bedrock_penalty(
    det_elev: np.ndarray,
    det_elev_slope: np.ndarray,
    depth_to_base: np.ndarray,
    lidar_relief: np.ndarray,
    scarp_channel: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Dimensionless [0, 1] indicator of bare footwall erosional canyon terrain.

    Fires only where uplifted mountain-block elevation and steep slope/relief
    coincide with thin/absent sedimentary cover (Hermant et al., 2025), spared
    when contour-parallel fault-scarp polarity dominates over channel banks.
    """
    fp = np.asarray(footprint, bool)

    def _upper_ramp(arr: np.ndarray, lo_q: float, hi_q: float) -> np.ndarray:
        ok = fp & np.isfinite(arr)
        if not np.any(ok):
            return np.zeros(arr.shape, np.float32)
        lo, hi = np.percentile(arr[ok], [lo_q, hi_q])
        span = max(float(hi - lo), 1e-6)
        r = np.zeros(arr.shape, np.float32)
        r[ok] = np.clip((arr[ok] - lo) / span, 0.0, 1.0).astype(np.float32)
        return r

    elev_high = _upper_ramp(det_elev, 55.0, 88.0)
    slope_high = _upper_ramp(det_elev_slope, 55.0, 88.0)
    relief_high = _upper_ramp(lidar_relief, 50.0, 85.0)
    steepness = np.where(np.isfinite(lidar_relief), 0.5 * slope_high + 0.5 * relief_high, slope_high)

    thin_cover = np.ones(det_elev.shape, np.float32)
    ok_cov = fp & np.isfinite(depth_to_base)
    thin_cover[ok_cov] = (1.0 - np.clip(depth_to_base[ok_cov] / 250.0, 0.0, 1.0)).astype(np.float32)

    channel_factor = np.ones(det_elev.shape, np.float32)
    ok_sc = fp & np.isfinite(scarp_channel)
    # Strong contour-parallel scarps (scarp_channel > +0.25) reduce canyon penalty;
    # channel-bank incisions (scarp_channel < 0) receive full penalty.
    channel_factor[ok_sc] = np.clip(1.0 - np.clip(scarp_channel[ok_sc], 0.0, 0.8), 0.25, 1.0).astype(np.float32)

    penalty = (elev_high * steepness * thin_cover * channel_factor).astype(np.float32)
    penalty[~fp] = 0.0
    return penalty


def rasterize_hydrothermal_features(
    wellspring_csv: Path,
    vents_csv: Path,
    shape: tuple[int, int],
    footprint: np.ndarray,
) -> dict[str, np.ndarray]:
    """Build label-free hydrothermal upflow, geothermometry & vent fields.

    Explicitly strips ``dist_known_fault_px`` on ingest so catalogue distances
    in the tabular compilations can never leak into static features.
    """
    h, w = shape
    fp = np.asarray(footprint, bool)
    temp_impulse = np.zeros(shape, np.float32)
    geotherm_impulse = np.zeros(shape, np.float32)
    thermal_mask = np.zeros(shape, bool)

    def _fval(raw: str | None) -> float:
        if raw is None:
            return float("nan")
        s = raw.strip()
        if not s:
            return float("nan")
        try:
            v = float(s)
            return v if np.isfinite(v) else float("nan")
        except ValueError:
            return float("nan")

    with Path(wellspring_csv).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        allowed_cols = [c for c in (reader.fieldnames or []) if c != "dist_known_fault_px"]
        assert "dist_known_fault_px" not in allowed_cols
        for row in reader:
            rec = {k: row[k] for k in allowed_cols}
            r = int(float(rec["row"]))
            c = int(float(rec["col"]))
            if not (0 <= r < h and 0 <= c < w):
                continue
            tc = _fval(rec.get("temp_c"))
            qtz = _fval(rec.get("geothermquartz_c"))
            chalc = _fval(rec.get("geothermchalc_c"))
            cat = _fval(rec.get("geothermcat_c"))
            tcls = (rec.get("thermalclass") or "").strip().lower()

            w_temp = 0.0
            if np.isfinite(tc) and tc > 25.0:
                w_temp = min(tc - 25.0, 120.0) / 50.0
            elif tcls == "hot":
                w_temp = 0.8
            elif tcls == "warm":
                w_temp = 0.35
            if w_temp > temp_impulse[r, c]:
                temp_impulse[r, c] = w_temp

            gt_candidates = [v for v in (qtz, chalc, cat) if np.isfinite(v) and v < 350.0]
            if gt_candidates:
                gt_max = max(gt_candidates)
                if gt_max > 70.0:
                    w_gt = min(gt_max - 70.0, 160.0) / 80.0
                    if w_gt > geotherm_impulse[r, c]:
                        geotherm_impulse[r, c] = w_gt

            if (
                (np.isfinite(tc) and tc >= 37.0)
                or (np.isfinite(qtz) and qtz >= 80.0)
                or tcls in ("hot", "warm")
            ):
                thermal_mask[r, c] = True

    vent_mask = np.zeros(shape, bool)
    with Path(vents_csv).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        allowed_cols = [c for c in (reader.fieldnames or []) if c != "dist_known_fault_px"]
        assert "dist_known_fault_px" not in allowed_cols
        for row in reader:
            rec = {k: row[k] for k in allowed_cols}
            r = int(float(rec["row"]))
            c = int(float(rec["col"]))
            if 0 <= r < h and 0 <= c < w:
                vent_mask[r, c] = True

    d_therm = (
        ndi.distance_transform_edt(~thermal_mask).astype(np.float32)
        if thermal_mask.any()
        else np.full(shape, 250.0, np.float32)
    )
    d_vent = (
        ndi.distance_transform_edt(~vent_mask).astype(np.float32)
        if vent_mask.any()
        else np.full(shape, 300.0, np.float32)
    )
    out = {
        "hydro_temp_plume_s6": ndi.gaussian_filter(temp_impulse, 6.0).astype(np.float32),
        "hydro_temp_plume_s20": ndi.gaussian_filter(temp_impulse, 20.0).astype(np.float32),
        "hydro_geotherm_s8": ndi.gaussian_filter(geotherm_impulse, 8.0).astype(np.float32),
        "hydro_geotherm_s24": ndi.gaussian_filter(geotherm_impulse, 24.0).astype(np.float32),
        "log_dist_thermal_spring": np.log1p(np.minimum(d_therm, 250.0)).astype(np.float32),
        "log_dist_volcanic_vent": np.log1p(np.minimum(d_vent, 300.0)).astype(np.float32),
    }
    for k in out:
        out[k] = np.where(fp, out[k], np.nan).astype(np.float32)
    return out


def _robust(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """(x - median) / IQR on valid footprint cells; invalid -> NaN."""
    out = np.full(a.shape, np.nan, np.float32)
    v = a[valid]
    if v.size == 0:
        return out
    q25, q50, q75 = np.percentile(v, [25, 50, 75])
    scale = float(q75 - q25) or float(np.std(v)) or 1.0
    out[valid] = np.clip((v - q50) / scale, -30.0, 30.0).astype(np.float32)
    return out


def build_static_stack(
    footprint: np.ndarray,
    road_scale_m: float = 150.0,
    road_floor: float = 0.15,
) -> tuple[np.ndarray, np.ndarray, list[str], dict]:
    """Build or load cached float16 footprint feature stack + canyon penalty vector."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out_mat = CACHE / "static_stack_f16.npy"
    out_can = CACHE / "canyon_penalty_f32.npy"
    meta_path = CACHE / "static_stack.json"
    if out_mat.exists() and out_can.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return np.load(out_mat, mmap_mode="r"), np.load(out_can), meta["names"], meta

    fp = np.asarray(footprint, bool)
    idx = np.flatnonzero(fp)
    cols: list[np.ndarray] = []
    names: list[str] = []
    inputs: dict[str, str] = {}

    def add(name: str, arr: np.ndarray, valid: np.ndarray) -> None:
        cols.append(_robust(arr, valid & fp).ravel()[idx].astype(np.float16))
        names.append(name)

    # 1. Geophysical, geodetic, seismicity & DEM compilation (19 bands + worms)
    tf_path = RAW / "training_features.tif"
    inputs["training_features.tif"] = _sha(tf_path)
    saved: dict[str, np.ndarray] = {}
    with rasterio.open(tf_path) as src:
        descr = src.descriptions
        for b in range(1, src.count + 1):
            a = src.read(b).astype(np.float32)
            valid = np.isfinite(a) & (a > -1e30)
            short = descr[b - 1].split(" - ")[0]
            add("tf_" + short, a, valid)
            if short in ("det_elev", "det_elev_slope", "depth_to_base_surf"):
                saved[short] = np.where(valid, a, np.nan)
            if short in ("det_elev", "iso_grav_anom", "rtp"):
                med = float(np.median(a[valid & fp]))
                filled = np.where(valid, a, med)
                sigmas = (1.0, 3.0) if short == "det_elev" else (
                    (2.0, 5.0, 12.0) if short == "iso_grav_anom" else (2.0, 5.0)
                )
                for s in sigmas:
                    gm = ndi.gaussian_gradient_magnitude(filled, s).astype(np.float32)
                    add(f"{short}_gradmag_s{s:g}", gm, valid)
                    if short == "iso_grav_anom" and s == 2.0:
                        saved["grav_worm_s2"] = np.where(valid, gm, np.nan)
                    add(f"{short}_log_s{s:g}", ndi.gaussian_laplace(filled, s).astype(np.float32), valid)
                    del gm
                del filled
            elif short in ("cond_surf", "tc"):
                med = float(np.median(a[valid & fp]))
                filled = np.where(valid, a, med)
                gm = ndi.gaussian_gradient_magnitude(filled, 3.0 if short == "cond_surf" else 2.0).astype(np.float32)
                tag = "cond_surf_gradmag_s3" if short == "cond_surf" else "tilt_depth_grad_s2"
                add(tag, gm, valid)
                del filled, gm
            del a, valid
    gc.collect()

    cov_ok = np.isfinite(saved["depth_to_base_surf"]) & np.isfinite(saved["grav_worm_s2"])
    cover_worm = np.where(
        cov_ok,
        np.log1p(np.maximum(saved["depth_to_base_surf"], 0.0)) * saved["grav_worm_s2"],
        np.nan,
    ).astype(np.float32)
    add("cover_grav_worm", cover_worm, cov_ok)
    del cover_worm, cov_ok

    # 2. TIGER road distance + physically decoded 3DEP lidar scarp descriptors
    road_path = RAW / "external" / "tiger_road_distance_m.tif"
    lidar_meta_path = RAW / "external" / "lidar_scarp_features.json"
    lidar_path = RAW / "external" / "lidar_scarp_features_u8.tif"
    inputs["tiger_road_distance_m.tif"] = _sha(road_path)
    inputs["lidar_scarp_features.json"] = _sha(lidar_meta_path)
    inputs["lidar_scarp_features_u8.tif"] = _sha(lidar_path)

    with rasterio.open(road_path) as src:
        road_m = src.read(1).astype(np.float32)
    road_valid = np.isfinite(road_m) & (road_m >= 0.0)
    add("log_tiger_road_dist_m", np.log1p(np.maximum(road_m, 0.0)).astype(np.float32), road_valid)
    w_road = road_deseam_weight(road_m, scale_m=road_scale_m, floor=road_floor)
    del road_m, road_valid

    qspec = json.loads(lidar_meta_path.read_text())["quantisation"]
    decoded_lidar: dict[str, np.ndarray] = {}
    with rasterio.open(lidar_path) as src:
        descr = list(src.descriptions)
        for name in LIDAR_FEATURE_BANDS:
            xmax, mode = qspec[name]
            raw_q = src.read(descr.index(name) + 1)
            dec = decode_lidar_band(raw_q, float(xmax), str(mode))
            add("lidar_" + name, dec, np.isfinite(dec))
            decoded_lidar[name] = dec
            del raw_q

    l_ok = np.isfinite(decoded_lidar["lapneg_max"]) & np.isfinite(decoded_lidar["lappos_max"])
    dipole = np.where(
        l_ok,
        w_road * np.sqrt(np.maximum(decoded_lidar["lapneg_max"] * decoded_lidar["lappos_max"], 0.0)),
        np.nan,
    ).astype(np.float32)
    add("deseamed_scarp_dipole", dipole, l_ok)

    b_ok = np.isfinite(decoded_lidar["ex_max"]) & np.isfinite(decoded_lidar["relief"])
    bajada_prom = np.where(
        b_ok,
        w_road * decoded_lidar["ex_max"] / (0.05 + decoded_lidar["relief"] / 300.0),
        np.nan,
    ).astype(np.float32)
    add("bajada_prominence", bajada_prom, b_ok)

    sc_vs_ch = scarp_vs_channel_index(
        decoded_lidar["upface_max"], decoded_lidar["downface_max"], decoded_lidar["cross_max"]
    )
    add("scarp_vs_channel", sc_vs_ch, np.isfinite(sc_vs_ch))

    pol_ok = np.isfinite(decoded_lidar["upface_max"]) & np.isfinite(decoded_lidar["downface_max"])
    polarity = np.full(fp.shape, np.nan, np.float32)
    polarity[pol_ok] = (
        (decoded_lidar["upface_max"][pol_ok] - decoded_lidar["downface_max"][pol_ok])
        / (decoded_lidar["upface_max"][pol_ok] + decoded_lidar["downface_max"][pol_ok] + 1e-3)
    ).astype(np.float32)
    add("antislope_polarity", polarity, pol_ok)

    for tag, arr in (
        ("deseamed_step_max5", w_road * decoded_lidar["step_max"]),
        ("deseamed_ex_max5", w_road * decoded_lidar["ex_max"]),
        ("deseamed_dipole_max5", dipole),
    ):
        v = np.isfinite(arr)
        mx = ndi.maximum_filter(np.where(v, arr, 0.0), size=5).astype(np.float32)
        add(tag, mx, v)
        del mx

    canyon_grid = compute_canyon_bedrock_penalty(
        det_elev=saved["det_elev"],
        det_elev_slope=saved["det_elev_slope"],
        depth_to_base=saved["depth_to_base_surf"],
        lidar_relief=decoded_lidar["relief"],
        scarp_channel=sc_vs_ch,
        footprint=fp,
    )
    canyon_vec = canyon_grid.ravel()[idx].astype(np.float32)
    np.save(out_can, canyon_vec)
    del decoded_lidar, dipole, bajada_prom, sc_vs_ch, polarity, w_road, canyon_grid
    gc.collect()

    # 3. GeoDAWN radiometrics & upward-continued magnetics
    for fname, bands in (
        ("geodawn_rad_u8.tif", RAD_BANDS),
        ("geodawn_extensions_u8.tif", EXT_BANDS),
    ):
        p = RAW / "external" / fname
        inputs[fname] = _sha(p)
        with rasterio.open(p) as src:
            descr = list(src.descriptions)
            for name in bands:
                a = src.read(descr.index(name) + 1).astype(np.float32)
                valid = a > 0
                add(name, a, valid)
                if name == "TMI_up150":
                    med = float(np.median(a[valid & fp]))
                    gm = ndi.gaussian_gradient_magnitude(np.where(valid, a, med), 3.0).astype(np.float32)
                    add("tmi_up150_worm_s3", gm, valid)
                    del gm
                del a, valid

    # 4. INGENIOUS well/spring aqueous geothermometry & Quaternary volcanic vents
    ws_path = RAW / "external" / "gdr_wellspring_in_footprint.csv"
    vv_path = RAW / "external" / "gdr_volcanic_vents_in_footprint.csv"
    inputs["gdr_wellspring_in_footprint.csv"] = _sha(ws_path)
    inputs["gdr_volcanic_vents_in_footprint.csv"] = _sha(vv_path)
    hydro = rasterize_hydrothermal_features(ws_path, vv_path, fp.shape, fp)
    for k, arr in hydro.items():
        add(k, arr, np.isfinite(arr))
    cond_ok = np.isfinite(hydro["hydro_geotherm_s24"]) & np.isfinite(saved["grav_worm_s2"])
    conduit = np.where(
        cond_ok, hydro["hydro_geotherm_s24"] * saved["grav_worm_s2"], np.nan
    ).astype(np.float32)
    add("hydro_struct_conduit", conduit, cond_ok)
    del hydro, conduit, saved
    gc.collect()

    mat = np.stack(cols, axis=1)
    np.save(out_mat, mat)
    meta = dict(
        names=names,
        n_footprint=int(idx.size),
        n_features=len(names),
        dtype="float16",
        normalisation="(x - median)/IQR over footprint clipped to [-30, 30]; NaN where missing",
        inputs_sha256=inputs,
    )
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    del mat, cols
    gc.collect()
    return np.load(out_mat, mmap_mode="r"), np.load(out_can), names, meta


def geometry_features(
    visible: np.ndarray,
    footprint: np.ndarray,
    lidar_strike: np.ndarray,
    lidar_coh: np.ndarray,
) -> dict[str, np.ndarray]:
    """Out-of-fold catalogue-geometry & crack-tip propagation features."""
    vis = np.asarray(visible, bool)
    fp = np.asarray(footprint, bool)
    d = ndi.distance_transform_edt(~vis).astype(np.float32)
    vf = vis.astype(np.float32)
    m = vis.astype(np.uint8)
    nb = ndi.convolve(m, np.ones((3, 3), np.uint8), mode="constant") - m
    tips = vis & (nb <= 1)

    if tips.any():
        dt, tip_idx = ndi.distance_transform_edt(~tips, return_indices=True)
        dt = dt.astype(np.float32)
    else:
        dt = np.full(vis.shape, 200.0, np.float32)
        tip_idx = None

    gy = ndi.sobel(vf, 0)
    gx = ndi.sobel(vf, 1)
    jxx = ndi.gaussian_filter(gx * gx, 20.0)
    jyy = ndi.gaussian_filter(gy * gy, 20.0)
    jxy = ndi.gaussian_filter(gx * gy, 20.0)
    tr = jxx + jyy + 1e-9
    coh = (np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy * jxy) / tr).astype(np.float32)
    theta_n = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    strike_rad = theta_n + 0.5 * np.pi  # along-strike azimuth in (col, row) frame

    # Directional crack-tip propagation cone: projects along local strike off each endpoint
    if tip_idx is not None:
        tr_y, tr_x = tip_idx[0], tip_idx[1]
        yy, xx = np.indices(vis.shape, dtype=np.float32)
        vy = yy - tr_y.astype(np.float32)
        vx = xx - tr_x.astype(np.float32)
        norm = np.hypot(vx, vy) + 1e-6
        sx = np.cos(strike_rad[tr_y, tr_x])
        sy = np.sin(strike_rad[tr_y, tr_x])
        cos_align = np.abs(vx * sx + vy * sy) / norm
        tip_cone = (np.exp(-dt / 18.0) * (cos_align ** 3)).astype(np.float32)
        del tip_idx, tr_y, tr_x, yy, xx, vy, vx, norm, sx, sy, cos_align
    else:
        tip_cone = np.zeros(vis.shape, np.float32)

    strike_deg = (np.degrees(theta_n) + 90.0) % 180.0
    delta = np.radians(2.0 * (lidar_strike - strike_deg))
    align = np.where(
        np.isfinite(lidar_strike),
        np.cos(delta) * np.nan_to_num(lidar_coh, nan=0.0),
        np.nan,
    ).astype(np.float32)

    out = {
        "log_dist_visible": np.log1p(np.minimum(d, 250.0)).astype(np.float32),
        "visible_density_s5": ndi.gaussian_filter(vf, 5.0).astype(np.float32),
        "visible_density_s20": ndi.gaussian_filter(vf, 20.0).astype(np.float32),
        "log_dist_visible_tip": np.log1p(np.minimum(dt, 250.0)).astype(np.float32),
        "tip_propagation_cone": tip_cone,
        "lidar_strike_alignment": align,
        "strike_field_coherence": coh,
        "_dist_px": d,
    }
    for k in GEOMETRY_NAMES:
        out[k] = np.where(fp, out[k], np.nan).astype(np.float32)
    return out


def regime_id_from_dist_px(dist_px: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Assign each allowed pixel to regime 0 (R1), 1 (R2), or 2 (R3); -1 elsewhere."""
    reg = np.full(dist_px.shape, -1, dtype=np.int8)
    ok = np.asarray(allowed, bool)
    for r_idx, (_, lo_px, hi_px, _) in enumerate(REGIME_SPECS):
        m = ok & (dist_px > lo_px) & (dist_px <= hi_px)
        reg[m] = r_idx
    return reg


def calibrate_regime_surface(
    raw_regime_scores: dict[int, np.ndarray],
    regime_map: np.ndarray,
    allowed: np.ndarray,
    canyon_grid: np.ndarray,
    canyon_weight: float = 0.45,
    budget_scale: int = 37654,
) -> np.ndarray:
    """Calibrate per-regime predictions into one continuous surface in [0, 1].

    Within each regime ``r``:
      1. Standardise ``raw_regime_scores[r]`` to zero mean / unit variance on
         allowed pixels in regime ``r`` and subtract ``canyon_weight * C_canyon``.
      2. Compute descending rank ``1 .. N_r`` (stable row-major tie break).
      3. Set ``S(x) = exp(-rank_r(x) / (q_r * budget_scale))``.

    Analytic guarantee: the top ``budget_scale`` level set ``S(x) >= exp(-1)``
    allocates exact shares ``(q_1, q_2, q_3)`` across the three structural
    domains prior to spacing, with zero access to any registry raster.
    """
    surf = np.zeros(regime_map.shape, dtype=np.float32)
    flat_surf = surf.ravel()
    flat_can = canyon_grid.ravel()
    allow = np.asarray(allowed, bool)

    for r_idx, (_, _, _, share) in enumerate(REGIME_SPECS):
        mask = allow & (regime_map == r_idx)
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            continue
        vals = np.asarray(raw_regime_scores[r_idx], dtype=np.float64)
        mu = float(np.mean(vals))
        sd = float(np.std(vals))
        if not np.isfinite(sd) or sd < 1e-12:
            sd = 1.0
        adj = (vals - mu) / sd - float(canyon_weight) * flat_can[idx].astype(np.float64)
        order = np.argsort(-adj, kind="stable")
        ranks = np.empty(idx.size, dtype=np.float64)
        ranks[order] = np.arange(1, idx.size + 1, dtype=np.float64)
        denom = max(float(share) * float(budget_scale), 1.0)
        flat_surf[idx] = np.exp(-ranks / denom).astype(np.float32)

    return surf
