"""G79-STEPCO fixed feature transforms (preregistration 2026-10-22).

Catalogue-independent transforms of the pinned cached stacks. No prior
submission raster enters any feature. Arrays are written one per file under a
cache directory because the sandbox has ~4 GB RAM; nothing here keeps the full
feature stack in memory.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

# 8 trace-normal axes at radius ~3 px (integer offsets, no wraparound).
STEP_OFFSETS = ((0, 3), (1, 3), (2, 2), (3, 1), (3, 0), (3, -1), (2, -2), (1, -3))

# training_features.tif band order verified from the file's own descriptions
# on 2026-10-22 (see reports/session_review_220dabc8.md).
BANDS = {
    "mag_anom": 1, "rtp": 2, "tmi_hg": 3, "geod_2ndinv": 4,
    "iso_grav_anom_slope": 5, "tc": 6, "geod_shearrate": 7,
    "geod_dilaterate": 8, "tmi_vg": 9, "deq_n100a15": 10,
    "iso_grav_anom_vg": 11, "det_elev": 12, "iso_grav_anom": 13,
    "tmi": 14, "depth_to_base_surf": 15, "ieq_n100a15": 16,
    "cond_surf": 17, "iso_grav_anom_hg": 18, "det_elev_slope": 19,
}

TRANSFORM_FIELDS = ("det_elev", "iso_grav_anom", "log_depth", "rtp", "cond_surf")
RAW_FEATURES = (
    "mag_anom", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "log_deq",
    "iso_grav_anom_vg", "det_elev", "iso_grav_anom", "tmi", "log_depth",
    "log_ieq", "cond_surf", "iso_grav_anom_hg", "det_elev_slope", "rtp",
)
LIDAR_FEATURES = tuple(f"lidar_{n}" for n in (
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
    "downface_max", "upface_max", "cross_max", "relief", "coh100"))
RAD_FEATURES = ("rad_K", "rad_Th", "rad_U", "rad_TC", "rad_ThK", "rad_UK",
                "rad_UTh", "rad_TMI_up150")


def feature_names() -> list[str]:
    names: list[str] = []
    for f in TRANSFORM_FIELDS:
        names += [f"{f}_step", f"{f}_grad1", f"{f}_grad3", f"{f}_abslap2"]
    names += list(RAW_FEATURES)
    names += list(LIDAR_FEATURES) + ["lidar_valid"]
    names += list(RAD_FEATURES)
    return names


def _shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Edge-padded integer shift (never wraps)."""
    p = np.pad(a, ((abs(dy), abs(dy)), (abs(dx), abs(dx))), mode="edge")
    y0, x0 = abs(dy) + dy, abs(dx) + dx
    return p[y0:y0 + a.shape[0], x0:x0 + a.shape[1]]


def step_dipole(field: np.ndarray) -> np.ndarray:
    """Max |field(+3 px across trace) - field(-3 px)| over 8 normals."""
    sm = ndi.gaussian_filter(field, 1.5, mode="nearest")
    out = np.zeros(field.shape, np.float32)
    for dy, dx in STEP_OFFSETS:
        d = np.abs(_shift(sm, dy, dx) - _shift(sm, -dy, -dx))
        np.maximum(out, d, out=out)
        del d
    return out


def grad_mag(field: np.ndarray, sigma: float) -> np.ndarray:
    gx = ndi.gaussian_filter(field, sigma, order=(0, 1), mode="nearest")
    gy = ndi.gaussian_filter(field, sigma, order=(1, 0), mode="nearest")
    out = np.hypot(gx, gy).astype(np.float32)
    del gx, gy
    return out


def abs_laplacian(field: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    lap = (ndi.gaussian_filter(field, sigma, order=(2, 0), mode="nearest")
           + ndi.gaussian_filter(field, sigma, order=(0, 2), mode="nearest"))
    return np.abs(lap).astype(np.float32)


def _read_filled(src, band: int, footprint: np.ndarray):
    a = src.read(band).astype(np.float32)
    nodata = src.nodata
    valid = footprint & np.isfinite(a) & (a > -1e38)
    if nodata is not None and np.isfinite(nodata):
        valid &= a != np.float32(nodata)
    if not valid.any():
        raise ValueError(f"band {band} has no valid cells")
    filled = np.where(valid, a, np.median(a[valid])).astype(np.float32)
    return filled, valid


def build(training_path, lidar_path, rad_path, ext_path, footprint, out_dir):
    """Compute every preregistered feature; returns a receipt dict."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    footprint = np.asarray(footprint, bool)
    raw: dict[str, Path] = {}
    all_valid = footprint.copy()
    band_valid_counts = {}
    with rasterio.open(training_path) as src:
        if src.count != 19:
            raise ValueError(f"expected 19 bands, got {src.count}")
        descriptions = list(src.descriptions)
        for name, band in BANDS.items():
            filled, valid = _read_filled(src, band, footprint)
            all_valid &= valid
            band_valid_counts[name] = int(valid.sum())
            key = name
            if name == "depth_to_base_surf":
                filled = np.log1p(np.clip(filled, 0, None)).astype(np.float32)
                key = "log_depth"
            elif name == "deq_n100a15":
                filled = np.log1p(np.clip(filled, 0, None)).astype(np.float32)
                key = "log_deq"
            elif name == "ieq_n100a15":
                filled = np.log1p(np.clip(filled, 0, None)).astype(np.float32)
                key = "log_ieq"
            p = out_dir / f"raw_{key}.npy"
            np.save(p, filled)
            raw[key] = p
            del filled, valid
    # support: complete 9x9 valid neighbourhood in every training band
    support = ndi.minimum_filter(all_valid.astype(np.uint8), size=9,
                                 mode="constant", cval=0) > 0
    support &= footprint
    np.save(out_dir / "support.npy", support)

    written: list[str] = []

    def emit(name, arr):
        arr = np.asarray(arr, dtype=np.float32)
        if arr.shape != footprint.shape or not np.isfinite(arr).all():
            raise ValueError(f"feature {name} shape/finite violation")
        np.save(out_dir / f"{name}.npy", arr)
        written.append(name)

    for field_name in TRANSFORM_FIELDS:
        f = np.load(raw[field_name])
        print(f"STEPCO transforms: {field_name}", flush=True)
        emit(f"{field_name}_step", step_dipole(f))
        emit(f"{field_name}_grad1", grad_mag(f, 1.0))
        emit(f"{field_name}_grad3", grad_mag(f, 3.0))
        emit(f"{field_name}_abslap2", abs_laplacian(f, 2.0))
        del f
    for name in RAW_FEATURES:
        emit(name, np.load(raw[name]))

    with rasterio.open(lidar_path) as src:
        valid_band = src.read(12) > 0
        for i, name in enumerate(LIDAR_FEATURES, start=1):
            a = src.read(i).astype(np.float32)
            emit(name, np.where(valid_band, a, 0.0))
            del a
        emit("lidar_valid", (valid_band & footprint).astype(np.float32))
    for path, bands in ((rad_path, RAD_FEATURES[:4]), (ext_path, RAD_FEATURES[4:])):
        with rasterio.open(path) as src:
            for i, name in enumerate(bands, start=1):
                emit(name, src.read(i).astype(np.float32))

    names = feature_names()
    if written != names:
        raise AssertionError(f"feature order drift: {written} != {names}")
    for p in raw.values():
        p.unlink(missing_ok=True)
    return {
        "feature_names": names,
        "n_features": len(names),
        "band_descriptions": descriptions,
        "band_valid_counts": band_valid_counts,
        "support_pixels": int(support.sum()),
        "footprint_pixels": int(footprint.sum()),
        "step_offsets": [list(o) for o in STEP_OFFSETS],
    }
