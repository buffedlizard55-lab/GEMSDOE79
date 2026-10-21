"""Input loading for lane H79-MCT (all inputs SHA-256 pinned; see registry/data_manifest.json).

Nothing here touches the catalogue except :func:`load_grid`, which returns it as a
separate boolean mask.  Every feature channel is catalogue-free by construction so the
hide-and-recover holdout is honest (protocol rule 2).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

from . import ROOT

sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as G  # noqa: E402

RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache"
FEAT = CACHE / "features"
DEM10 = CACHE / "dem10"
TRAINING_FEATURES = RAW / "training_features.tif"
LIDAR = RAW / "external" / "lidar_scarp_features_u8.tif"
H19_5 = RAW / "scored" / "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"

# Band numbers (1-based) of training_features.tif, verified from the file's band descriptions.
TF_BANDS = {
    "mag_anom": 1, "rtp": 2, "tmi_hg": 3, "geod_2ndinv": 4, "iso_grav_anom_slope": 5, "tc": 6,
    "geod_shearrate": 7, "geod_dilaterate": 8, "tmi_vg": 9, "deq_n100a15": 10, "iso_grav_anom_vg": 11,
    "det_elev": 12, "iso_grav_anom": 13, "tmi": 14, "depth_to_base_surf": 15, "ieq_n100a15": 16,
    "cond_surf": 17, "iso_grav_anom_hg": 18, "det_elev_slope": 19,
}

# LiDAR cache (u8) band order and de-quantisation parameters, copied from
# data/cache/lidar_scarp_features.json (GEMSDOE24 @ 07345ea0).  q = 1 + round(254*t(clip(x/xmax,0,1)))
LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "strike", "valid"]
LIDAR_QUANT = {
    "ex_max": (1.5, "sqrt"), "ex_mean": (0.3, "sqrt"), "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"), "lappos_max": (0.05, "sqrt"), "downface_max": (1.0, "sqrt"),
    "upface_max": (1.0, "sqrt"), "cross_max": (1.0, "sqrt"), "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"), "strike": (180.0, "linear"), "valid": (1.0, "linear"),
}

DEM10_CHANNELS = ["dem10_slope_max", "dem10_slope_mean", "dem10_slope_std", "dem10_hgm20_max",
                  "dem10_hgm50_max", "dem10_hgm200_mean", "dem10_steep_ratio_max", "dem10_resid_std",
                  "dem10_resid_range", "dem10_curv_absmax", "dem10_onesided", "dem10_onesided3",
                  "dem10_valid_frac"]


def load_grid() -> G.Grid:
    """Footprint + catalogue from the bridged rasters (hash-checked by gems57.grid)."""
    return G.load_grid(ROOT / "data" / "bridge")


def read_tf_band(name: str, footprint: np.ndarray | None = None) -> np.ndarray:
    """One float32 band of training_features.tif with nodata -> NaN."""
    with rasterio.open(TRAINING_FEATURES) as ds:
        b = ds.read(TF_BANDS[name]).astype(np.float32)
        nd = ds.nodata
    b[b == nd] = np.nan
    if footprint is not None:
        b[~footprint] = np.nan
    return b


def read_lidar(name: str) -> np.ndarray:
    """De-quantised LiDAR descriptor as float32; NaN where no 1 m lidar (q == 0)."""
    i = LIDAR_BANDS.index(name) + 1
    with rasterio.open(LIDAR) as ds:
        q = ds.read(i)
    xmax, t = LIDAR_QUANT[name]
    u = (q.astype(np.float32) - 1.0) / 254.0
    x = xmax * (u * u if t == "sqrt" else u)
    x[q == 0] = np.nan
    return x.astype(np.float32)


def lidar_valid() -> np.ndarray:
    with rasterio.open(LIDAR) as ds:
        q = ds.read(LIDAR_BANDS.index("valid") + 1)
    return q > 0


def read_dem10(name: str, footprint: np.ndarray) -> np.ndarray:
    """A 10 m 3DEP channel stored as a footprint-ordered vector -> 2-D float32 (NaN outside)."""
    man = json.loads((DEM10 / "manifest.json").read_text())
    assert man["vector_order"] == "np.nonzero(np.isfinite(sample_submission)) row-major"
    v = np.load(DEM10 / f"{name}.f32.npy")
    if v.size != int(footprint.sum()):
        raise ValueError(f"{name}: vector length {v.size} != footprint {int(footprint.sum())}")
    out = np.full(footprint.shape, np.nan, np.float32)
    out[footprint] = v
    return out


def read_h19_5_support() -> np.ndarray:
    """Positive support of the scored H19-5 line set (registry raster, used ONLY for the
    uniqueness split, never as a feature)."""
    with rasterio.open(H19_5) as ds:
        h = ds.read(1)
    return np.isfinite(h) & (h > 0)
