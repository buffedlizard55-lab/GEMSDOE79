"""H79-FNHR: Far-Field Geothermal, Basement-Dipole & Road-Deconfounded Antislope NHR.

Implements the preregistered architecture in ``research/hypotheses_fnhr.md`` and
``registry/preregistration_fnhr.json`` with strictly zero registry access, zero
overlap capping, and explicit anti-leakage exclusions:

1. H1 (INGENIOUS GDR-1391 Hydrothermal & Vent Conduit Features):
   Multi-scale enthalpy plumes (sigma = 8 px, 25 px) and log-EDT distances built
   strictly from physical point coordinates and fluid geochemistry/temperature
   (``row``, ``col``, ``temp_c``, ``geothermquartz_c``, ``geothermchalc_c``,
   ``geothermcat_c``, ``thermalclass``, plus Quaternary/Neogene volcanic vents),
   explicitly ignoring ``dist_known_fault_px``.
2. H2 (Basement Potential-Field Dipole & Radiometric Alteration Coupling):
   Shallow-minus-upward-continued magnetic dipole contrast ``z(TMI) - z(TMI_up150)``,
   regional-residual high-pass contrasts on gravity & magnetic horizontal gradients,
   basement depth & subsurface electrical conductivity, and K/Th/U ratios.
3. H3 (Antislope Half-Graben Polarity & 10 m 3DEP Persistence, Road-Deconfounded):
   Exact physical dequantization of 2 m USGS 3DEP LiDAR bands (with ``q == 0`` mapped
   to ``NaN`` rather than conflating missing tiles with flat terrain), signed uphill
   antislope polarity ``upface_max - downface_max``, tectonic-to-fluvial step ratio
   ``(upface_max + downface_max) / (cross_max + 0.02)``, full-coverage 10 m 3DEP
   excess one-sided step & persistence ratio, and US Census TIGER highway/rail
   embankment attenuation ``dem10_onesided3 * tanh(road_dist_m / 250 m)``.
4. H4 (Decontaminated Nested Hide-and-Recover + Out-of-Quadrant Pure-Physics Head):
   Fixes ``IR-79-61`` by excluding ``d(x, remaining) < 3.0 px`` from nested negative
   samples so unhidden fault scarps are never labelled ``y = 0``, and fits a separate
   pure-physics head ``m_phys`` on 100 % of ``visible`` inside ``train_region``.
5. H5 (Basin-and-Range Stratified Distance-Regime Surface & 3 px Placement):
   Smooth analytic crossover ``lambda(d) = d^2 / (d^2 + d0^2)`` (``d0 = 12 px``)
   mapped monotonically onto continuous surface ``P_w(x) in [0, 1]`` and placed with
   strict global 3.0 px minimum Euclidean spacing across budget ``B = 37,654``.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

from . import nhr

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DEM10_DIR = ROOT / "data" / "cache" / "dem10"
CACHE = ROOT / ".cache" / "fnhr"

FORBIDDEN_INPUT_NAMES = frozenset({
    "derived_sgmc_faults_100m_u8.tif",
    "gdr_qfaults_traces.csv",
})
FORBIDDEN_CSV_COLUMNS = frozenset({"dist_known_fault_px"})

DEM10_NAMES = (
    "dem10_slope_max",
    "dem10_slope_mean",
    "dem10_slope_std",
    "dem10_hgm20_max",
    "dem10_hgm50_max",
    "dem10_hgm200_mean",
    "dem10_steep_ratio_max",
    "dem10_resid_std",
    "dem10_resid_range",
    "dem10_curv_absmax",
    "dem10_onesided",
    "dem10_onesided3",
    "dem10_valid_frac",
)

BAND_EDGES_PX = (
    (2.0, 5.0),
    (5.0, 10.0),
    (10.0, 20.0),
    (20.0, 50.0),
    (50.0, float("inf")),
)

CROSSOVER_D0_PX = 12.0


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _robust_flat(arr: np.ndarray, valid: np.ndarray, fp_idx: np.ndarray) -> np.ndarray:
    """Robust IQR-normalized float16 vector over ``fp_idx``, ``NaN`` where invalid."""
    v = arr[valid]
    out = np.full(arr.shape, np.nan, np.float32)
    if v.size > 0:
        q25, q50, q75 = np.percentile(v, [25.0, 50.0, 75.0])
        scale = float(q75 - q25) or float(np.std(v)) or 1.0
        out[valid] = np.clip((v - q50) / scale, -60.0, 60.0).astype(np.float32)
    return out.ravel()[fp_idx].astype(np.float16)


def _float_or_nan(val: str) -> float:
    if val is None:
        return float("nan")
    s = val.strip()
    if not s or s.upper() in ("NULL", "NAN", "NONE", "NA", "-999", "-9999"):
        return float("nan")
    try:
        x = float(s)
        return x if np.isfinite(x) and x > -90.0 else float("nan")
    except ValueError:
        return float("nan")


def _build_gdr_channels(shape: tuple[int, int], footprint: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Construct pure-physical GDR-1391 thermal & volcanic channels (H1)."""
    h, w = shape
    ws_path = RAW / "external" / "gdr_wellspring_in_footprint.csv"
    vv_path = RAW / "external" / "gdr_volcanic_vents_in_footprint.csv"
    hashes = {
        "gdr_wellspring_in_footprint.csv": _sha(ws_path),
        "gdr_volcanic_vents_in_footprint.csv": _sha(vv_path),
    }

    all_pts = np.zeros(shape, dtype=bool)
    hot_pts = np.zeros(shape, dtype=bool)
    enthalpy = np.zeros(shape, dtype=np.float32)

    with ws_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        safe_fields = [c for c in (reader.fieldnames or []) if c not in FORBIDDEN_CSV_COLUMNS]
        assert "dist_known_fault_px" not in safe_fields
        for row in reader:
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError):
                continue
            if not (0 <= r < h and 0 <= c < w):
                continue
            all_pts[r, c] = True
            tc = _float_or_nan(row.get("temp_c", ""))
            tq = _float_or_nan(row.get("geothermquartz_c", ""))
            tch = _float_or_nan(row.get("geothermchalc_c", ""))
            tcat = _float_or_nan(row.get("geothermcat_c", ""))
            tclass = (row.get("thermalclass") or "").strip().lower()
            is_hot = (
                tclass in ("hot", "warm", "boiling", "thermal")
                or (np.isfinite(tc) and tc >= 30.0)
                or (np.isfinite(tq) and tq >= 80.0)
                or (np.isfinite(tch) and tch >= 80.0)
            )
            if is_hot:
                hot_pts[r, c] = True
            temps = [x for x in (tc, tq, tch, tcat) if np.isfinite(x) and 0.0 < x <= 400.0]
            score = max(temps) if temps else (60.0 if is_hot else 15.0)
            if score > enthalpy[r, c]:
                enthalpy[r, c] = float(score)

    vent_pts = np.zeros(shape, dtype=bool)
    with vv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        safe_fields = [c for c in (reader.fieldnames or []) if c not in FORBIDDEN_CSV_COLUMNS]
        assert "dist_known_fault_px" not in safe_fields
        for row in reader:
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError):
                continue
            if 0 <= r < h and 0 <= c < w:
                vent_pts[r, c] = True

    d_all = np.log1p(np.minimum(ndi.distance_transform_edt(~all_pts), 300.0)).astype(np.float32)
    d_hot = np.log1p(np.minimum(ndi.distance_transform_edt(~hot_pts), 300.0)).astype(np.float32)
    d_vent = np.log1p(np.minimum(ndi.distance_transform_edt(~vent_pts), 400.0)).astype(np.float32)
    plume_s8 = ndi.gaussian_filter(enthalpy, sigma=8.0).astype(np.float32)
    plume_s25 = ndi.gaussian_filter(enthalpy, sigma=25.0).astype(np.float32)

    return (
        {
            "gdr_log_dist_wellspring": d_all,
            "gdr_log_dist_hot_geotherm": d_hot,
            "gdr_enthalpy_plume_s8": plume_s8,
            "gdr_enthalpy_plume_s25": plume_s25,
            "gdr_log_dist_volcanic_vent": d_vent,
        },
        hashes,
    )


def build_physics_stack(footprint: np.ndarray) -> tuple[np.ndarray, list[str], dict]:
    """Build or load cached pure-physics feature matrix ``(n_fp, F_phys)`` in float16."""
    CACHE.mkdir(parents=True, exist_ok=True)
    mat_path = CACHE / "phys_stack_f16.npy"
    meta_path = CACHE / "phys_stack.json"
    if mat_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return np.load(mat_path, mmap_mode="r"), meta["names"], meta

    fp = np.asarray(footprint, bool)
    fp_idx = np.flatnonzero(fp)
    cols: list[np.ndarray] = []
    names: list[str] = []
    inputs: dict[str, str] = {}

    def push(name: str, arr: np.ndarray, valid: np.ndarray) -> None:
        cols.append(_robust_flat(arr, valid & fp, fp_idx))
        names.append(name)

    # 1. GeoDAWN 19 geophysical, geodetic, seismic & regional elevation bands + contrasts
    tf_path = RAW / "training_features.tif"
    inputs["training_features.tif"] = _sha(tf_path)
    saved_tf: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    with rasterio.open(tf_path) as src:
        descr = list(src.descriptions)
        for b in range(1, src.count + 1):
            short = descr[b - 1].split(" - ")[0].strip()
            a = src.read(b).astype(np.float32)
            valid = np.isfinite(a) & (a > -1e30)
            push(f"tf_{short}", a, valid)
            if short in ("det_elev_slope", "iso_grav_anom_hg", "tmi_hg", "geod_dilaterate", "geod_shearrate", "tmi"):
                saved_tf[short] = (a, valid)
            else:
                del a, valid

    for short in ("det_elev_slope", "iso_grav_anom_hg", "tmi_hg"):
        a, valid = saved_tf[short]
        med = float(np.median(a[valid & fp]))
        filled = np.where(valid, a, med)
        resid = (filled - ndi.gaussian_filter(filled, sigma=15.0)).astype(np.float32)
        push(f"tf_hp15_{short}", resid, valid)
        del filled, resid

    dil, v_dil = saved_tf["geod_dilaterate"]
    shr, v_shr = saved_tf["geod_shearrate"]
    v_str = v_dil & v_shr & fp
    transtens = np.zeros(fp.shape, dtype=np.float32)
    transtens[v_str] = (
        ((dil[v_str] - np.median(dil[v_str])) / (np.std(dil[v_str]) + 1e-9))
        * ((shr[v_str] - np.median(shr[v_str])) / (np.std(shr[v_str]) + 1e-9))
    )
    push("tf_transtensional_strain_coupling", transtens, v_str)
    del transtens
    tmi_raw, v_tmi = saved_tf["tmi"]
    saved_tf.clear()

    # 2. Full-coverage 10 m USGS 3DEP terrain step & multi-scale persistence (H3)
    dem_manifest = json.loads((DEM10_DIR / "manifest.json").read_text())
    inputs["dem10_manifest_sha256"] = hashlib.sha256((DEM10_DIR / "manifest.json").read_bytes()).hexdigest()
    dem_saved: dict[str, np.ndarray] = {}
    for dname in DEM10_NAMES:
        vec = np.load(DEM10_DIR / f"{dname}.f32.npy").astype(np.float32)
        grid2d = np.full(fp.shape, np.nan, dtype=np.float32)
        grid2d.ravel()[fp_idx] = vec
        valid = np.isfinite(grid2d)
        push(dname, grid2d, valid)
        if dname in ("dem10_onesided3", "dem10_slope_mean", "dem10_hgm20_max", "dem10_hgm200_mean"):
            dem_saved[dname] = grid2d
        else:
            del grid2d
        del vec
    excess_step = dem_saved["dem10_onesided3"] - dem_saved["dem10_slope_mean"]
    push("dem10_excess_onesided3", excess_step, np.isfinite(excess_step))
    persist = dem_saved["dem10_hgm20_max"] / (np.maximum(dem_saved["dem10_hgm200_mean"], 0.0) + 0.02)
    push("dem10_scarp_persistence_ratio", persist, np.isfinite(persist))
    dem10_onesided3 = dem_saved["dem10_onesided3"]
    dem_saved.clear()
    del excess_step, persist

    # 3. Physically dequantized 2 m USGS 3DEP LiDAR bands + antislope & tectonic ratios (H3)
    lidar_path = RAW / "external" / "lidar_scarp_features_u8.tif"
    lidar_meta = json.loads((RAW / "external" / "lidar_scarp_features.json").read_text())
    inputs["lidar_scarp_features_u8.tif"] = _sha(lidar_path)
    qmap = lidar_meta["quantisation"]
    lidar_saved: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    with rasterio.open(lidar_path) as src:
        descr = list(src.descriptions)
        for name in ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
                     "downface_max", "upface_max", "cross_max", "relief", "coh100", "valid"):
            q = src.read(descr.index(name) + 1).astype(np.float32)
            ok = (q > 0) & fp
            xmax, mode = qmap[name]
            unit = np.clip((q - 1.0) / 254.0, 0.0, 1.0)
            phys = xmax * (unit * unit if mode == "sqrt" else unit)
            push(f"lidar_{name}", phys, ok)
            if name in ("downface_max", "upface_max", "cross_max", "step_max"):
                lidar_saved[name] = (phys, ok)
                if name in ("step_max", "upface_max"):
                    mx5 = ndi.maximum_filter(np.where(ok, phys, 0.0), size=5).astype(np.float32)
                    push(f"lidar_{name}_max5", mx5, ok)
            else:
                del phys, ok
            del q, unit

    upf, ok_u = lidar_saved["upface_max"]
    dnf, ok_d = lidar_saved["downface_max"]
    crf, ok_c = lidar_saved["cross_max"]
    ok_udc = ok_u & ok_d & ok_c
    push("lidar_antislope_polarity", upf - dnf, ok_u & ok_d)
    push("lidar_tectonic_to_fluvial_ratio", (upf + dnf) / (crf + 0.02), ok_udc)
    lidar_saved.clear()
    del upf, dnf, crf, ok_u, ok_d, ok_c, ok_udc

    # 4. GeoDAWN Radiometrics & Shallow Magnetic Dipole Contrast (H2)
    for fname, prefix in (("geodawn_rad_u8.tif", "rad"), ("geodawn_extensions_u8.tif", "ext")):
        p = RAW / "external" / fname
        inputs[fname] = _sha(p)
        with rasterio.open(p) as src:
            descr = list(src.descriptions)
            for name in descr:
                a = src.read(descr.index(name) + 1).astype(np.float32)
                ok = (a > 0) & fp
                push(f"{prefix}_{name}", a, ok)
                if fname == "geodawn_extensions_u8.tif" and name == "TMI_up150":
                    ok_m = ok & v_tmi
                    z_tmi = (tmi_raw - np.median(tmi_raw[ok_m])) / (np.std(tmi_raw[ok_m]) + 1e-9)
                    z_up = (a - np.median(a[ok_m])) / (np.std(a[ok_m]) + 1e-9)
                    push("mag_shallow_dipole_residual", (z_tmi - z_up).astype(np.float32), ok_m)
                    del z_tmi, z_up
                del a, ok
    del tmi_raw, v_tmi

    # 5. INGENIOUS GDR-1391 Hydrothermal Plumes & Volcanic Vent Features (H1)
    gdr_channels, gdr_hashes = _build_gdr_channels(fp.shape, fp)
    inputs.update(gdr_hashes)
    for gname, garr in gdr_channels.items():
        push(gname, garr, np.isfinite(garr) & fp)
    gdr_channels.clear()

    # 6. US Census TIGER Anthropic Road Deconfounder (H3)
    road_path = RAW / "external" / "tiger_road_distance_m.tif"
    inputs["tiger_road_distance_m.tif"] = _sha(road_path)
    with rasterio.open(road_path) as src:
        road_m = np.maximum(src.read(1).astype(np.float32), 0.0)
    ok_r = np.isfinite(road_m) & fp
    push("tiger_log_road_dist_m", np.log1p(road_m).astype(np.float32), ok_r)
    atten = dem10_onesided3 * np.tanh(road_m / 250.0).astype(np.float32)
    push("dem10_onesided3_road_deconfounded", atten, ok_r & np.isfinite(dem10_onesided3))
    del road_m, atten, dem10_onesided3

    mat = np.stack(cols, axis=1)
    np.save(mat_path, mat)
    meta = {
        "lane_id": "H79-FNHR",
        "names": names,
        "n_features": len(names),
        "n_footprint": int(fp_idx.size),
        "dtype": "float16",
        "forbidden_inputs_excluded": sorted(FORBIDDEN_INPUT_NAMES),
        "forbidden_csv_columns_excluded": sorted(FORBIDDEN_CSV_COLUMNS),
        "inputs_sha256": inputs,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.load(mat_path, mmap_mode="r"), names, meta


def decontaminated_nested_rows(
    phys_fp: np.ndarray,
    fp: np.ndarray,
    fp_idx: np.ndarray,
    lidar_strike: np.ndarray,
    lidar_coh: np.ndarray,
    visible: np.ndarray,
    train_region: np.ndarray,
    seed: int,
    n_rep: int = 3,
    neg_per_rep: int = 100_000,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Build false-negative-decontaminated nested training rows (IR-79-61 fix).

    Excludes ``d(x, remaining) < 3.0 px`` from negative pool so real fault scarps
    flanking the 80 % unhidden training faults are never labelled ``y = 0``.
    """
    rng = np.random.default_rng(seed)
    xs, ys, receipts = [], [], []
    fp_lookup = np.full(fp.shape, -1, dtype=np.int32)
    fp_lookup.ravel()[fp_idx] = np.arange(fp_idx.size, dtype=np.int32)

    for rep in range(n_rep):
        hidden, remaining = nhr.nested_hide(visible & train_region, train_region, rng, 0.20, 3)
        if not hidden.any():
            continue
        t = nhr.kernel_target(hidden)
        d_rem = ndi.distance_transform_edt(~remaining)
        pos_mask = train_region & fp & ~visible & (t > 0.0)
        # IR-79-61 fix: exclude pixels inside the 3.0 px scarp halo of remaining visible faults!
        clean_neg_mask = train_region & fp & ~visible & (t == 0.0) & (d_rem >= 3.0)
        pos_flat = np.flatnonzero(pos_mask)
        neg_pool = np.flatnonzero(clean_neg_mask)
        take = neg_pool[rng.choice(neg_pool.size, size=min(neg_per_rep, neg_pool.size), replace=False)]
        sel = np.concatenate([pos_flat, take])
        rows_fp = fp_lookup.ravel()[sel]
        gf = nhr.geometry_features(remaining, fp, lidar_strike, lidar_coh)
        gmat = np.column_stack([gf[name].ravel()[sel] for name in nhr.GEOMETRY_NAMES]).astype(np.float32)
        xs.append(np.hstack([phys_fp[rows_fp].astype(np.float32), gmat]))
        ys.append(t.ravel()[sel].astype(np.float32))
        receipts.append({
            "rep": rep,
            "hidden_px": int(hidden.sum()),
            "positives": int(pos_flat.size),
            "clean_negatives": int(take.size),
            "excluded_remaining_halo_px": int((train_region & fp & ~visible & (t == 0.0) & (d_rem < 3.0)).sum()),
        })
    return np.concatenate(xs, axis=0), np.concatenate(ys, axis=0), receipts


def physics_rows(
    phys_fp: np.ndarray,
    fp: np.ndarray,
    fp_idx: np.ndarray,
    visible: np.ndarray,
    train_region: np.ndarray,
    seed: int,
    neg_sample: int = 320_000,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Build pure-physics training rows against 100 % of ``visible`` in ``train_region``."""
    rng = np.random.default_rng(seed)
    fp_lookup = np.full(fp.shape, -1, dtype=np.int32)
    fp_lookup.ravel()[fp_idx] = np.arange(fp_idx.size, dtype=np.int32)
    t_vis = nhr.kernel_target(visible & train_region)
    in_reg = train_region & fp
    pos_flat = np.flatnonzero(in_reg & (t_vis > 0.0))
    neg_pool = np.flatnonzero(in_reg & (t_vis == 0.0))
    take = neg_pool[rng.choice(neg_pool.size, size=min(neg_sample, neg_pool.size), replace=False)]
    sel = np.concatenate([pos_flat, take])
    rows_fp = fp_lookup.ravel()[sel]
    return (
        phys_fp[rows_fp].astype(np.float32),
        t_vis.ravel()[sel].astype(np.float32),
        {"positives_full_visible_halo": int(pos_flat.size), "negatives_sampled": int(take.size)},
    )


def blend_dual_heads(
    s_nest: np.ndarray,
    s_phys: np.ndarray,
    dist_vis: np.ndarray,
    domain_mask: np.ndarray,
    d0_px: float = CROSSOVER_D0_PX,
) -> np.ndarray:
    """Rank-calibrated smooth physical crossover ``S(x)`` inside ``domain_mask``."""
    out = np.zeros(s_nest.shape, dtype=np.float32)
    idx = np.flatnonzero(domain_mask)
    if idx.size == 0:
        return out
    rn = rankdata(s_nest.ravel()[idx], method="average").astype(np.float64) / float(idx.size)
    rp = rankdata(s_phys.ravel()[idx], method="average").astype(np.float64) / float(idx.size)
    d2 = np.square(dist_vis.ravel()[idx].astype(np.float64))
    lam = d2 / (d2 + d0_px * d0_px)
    out.ravel()[idx] = ((1.0 - lam) * rn + lam * rp).astype(np.float32)
    return out


def build_regime_surface_and_dots(
    raw_score: np.ndarray,
    dist_vis: np.ndarray,
    allowed: np.ndarray,
    quotas: tuple[float, ...],
    budget: int = 37_654,
    spacing: int = 3,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Construct monotone continuous regime surface ``P_w(x)`` and global 3 px dot field."""
    assert len(quotas) == len(BAND_EDGES_PX)
    assert abs(sum(quotas) - 1.0) < 1e-6
    h, w = raw_score.shape
    surface = np.zeros(raw_score.shape, dtype=np.float32)
    b_eff = 4.5 * float(budget)

    # Monotone continuous regime surface P_w(x) in (0, 1] on allowed domain
    for b_idx, ((lo, hi), qw) in enumerate(zip(BAND_EDGES_PX, quotas)):
        in_band = allowed & (dist_vis > lo) & (dist_vis <= hi)
        b_flat = np.flatnonzero(in_band)
        if b_flat.size == 0 or qw <= 0:
            continue
        order_up = rankdata(raw_score.ravel()[b_flat], method="ordinal").astype(np.float64)
        top_rank = float(b_flat.size) - order_up + 1.0
        tau = top_rank / float(qw)
        surface.ravel()[b_flat] = np.exp(-tau / b_eff).astype(np.float32)

    near2 = allowed & (dist_vis <= 2.0)
    n2_flat = np.flatnonzero(near2)
    if n2_flat.size > 0:
        order_up = rankdata(raw_score.ravel()[n2_flat], method="ordinal").astype(np.float64)
        top_rank = float(n2_flat.size) - order_up + 1.0
        surface.ravel()[n2_flat] = np.exp(-(b_eff * 3.0 + top_rank) / b_eff).astype(np.float32)

    # Strict global >= 3.0 px Euclidean spacing across all bands simultaneously
    blocked = ~allowed.copy()
    emitted = np.zeros(raw_score.shape, dtype=bool)
    yy, xx = np.mgrid[-spacing:spacing + 1, -spacing:spacing + 1]
    dy = yy[yy * yy + xx * xx < spacing * spacing]
    dx = xx[yy * yy + xx * xx < spacing * spacing]

    target_counts = [int(round(q * budget)) for q in quotas]
    target_counts[-1] += budget - sum(target_counts)
    placed_per_band: dict[str, int] = {}
    total_placed = 0

    for (lo, hi), target_b in zip(BAND_EDGES_PX, target_counts):
        label = f"({lo:g},{hi if np.isfinite(hi) else 'inf'}] px"
        b_flat = np.flatnonzero(allowed & (dist_vis > lo) & (dist_vis <= hi))
        b_sorted = b_flat[np.argsort(-raw_score.ravel()[b_flat], kind="stable")]
        cnt = 0
        for idx in b_sorted:
            if cnt >= target_b:
                break
            y, x = divmod(int(idx), w)
            if blocked[y, x]:
                continue
            emitted[y, x] = True
            cnt += 1
            total_placed += 1
            ny, nx = y + dy, x + dx
            good = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
            blocked[ny[good], nx[good]] = True
        placed_per_band[label] = cnt

    # Deterministic backfill if any narrow band saturates spacing before reaching quota
    if total_placed < budget:
        rem_flat = np.flatnonzero(allowed & ~emitted)
        rem_sorted = rem_flat[np.argsort(-surface.ravel()[rem_flat], kind="stable")]
        for idx in rem_sorted:
            if total_placed >= budget:
                break
            y, x = divmod(int(idx), w)
            if blocked[y, x]:
                continue
            emitted[y, x] = True
            total_placed += 1
            ny, nx = y + dy, x + dx
            good = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
            blocked[ny[good], nx[good]] = True

    d_dots = dist_vis[emitted]
    stats = {
        "requested": int(budget),
        "emitted": int(emitted.sum()),
        "spacing_px": int(spacing),
        "quotas": list(quotas),
        "placed_per_band": placed_per_band,
        "median_dist_px": float(np.median(d_dots)) if d_dots.size else 0.0,
        "mean_dist_px": float(np.mean(d_dots)) if d_dots.size else 0.0,
        "fraction_le_5px": float(np.mean(d_dots <= 5.0)) if d_dots.size else 0.0,
        "fraction_gt_10px": float(np.mean(d_dots > 10.0)) if d_dots.size else 0.0,
    }
    return surface, emitted, stats
