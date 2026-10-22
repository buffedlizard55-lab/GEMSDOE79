"""Input loading for lane G79B-SDPT. All inputs SHA-256 pinned (see
registry/data_manifest.json, registry/preregistration_g79b.json, and the
DEM10 manifest inside data/cache/dem10/). Nothing here touches the catalogue
except load_grid(), which returns it as a separate mask. Every feature
channel is catalogue-free by construction (protocol rule 2).

Adapted from the archived H79-MCT data.py (same de-quantisation), extended
with the TIGER road-distance raster.
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
FEAT = CACHE / "features_g79b"
DEM10 = CACHE / "dem10"
TRAINING_FEATURES = RAW / "training_features.tif"
LIDAR = RAW / "external" / "lidar_scarp_features_u8.tif"
ROAD_DIST = RAW / "external" / "tiger_road_distance_m.tif"

# Band numbers (1-based) in training_features.tif, re-verified this session
# from the file's own band descriptions (2026-10-22).
TF_BANDS = {"det_elev": 12, "det_elev_slope": 19}

LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "strike", "valid"]
LIDAR_QUANT = {
    "ex_max": (1.5, "sqrt"), "ex_mean": (0.3, "sqrt"), "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"), "lappos_max": (0.05, "sqrt"), "downface_max": (1.0, "sqrt"),
    "upface_max": (1.0, "sqrt"), "cross_max": (1.0, "sqrt"), "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"), "strike": (180.0, "linear"), "valid": (1.0, "linear"),
}

DEM10_CHANNELS = ["dem10_slope_max", "dem10_slope_mean", "dem10_slope_std", "dem10_hgm20_max",
                  "dem10_hgm50_max", "dem10_hgm200_mean", "dem10_steep_ratio_max",
                  "dem10_resid_std", "dem10_resid_range", "dem10_curv_absmax",
                  "dem10_onesided", "dem10_onesided3", "dem10_valid_frac"]


def load_grid() -> G.Grid:
    return G.load_grid(ROOT / "data" / "reference")


def read_tf_band(name: str, footprint: np.ndarray | None = None) -> np.ndarray:
    with rasterio.open(TRAINING_FEATURES) as ds:
        b = ds.read(TF_BANDS[name]).astype(np.float32)
        nd = ds.nodata
    b[b == nd] = np.nan
    if footprint is not None:
        b[~footprint] = np.nan
    return b


def read_lidar(name: str) -> np.ndarray:
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
    man = json.loads((DEM10 / "manifest.json").read_text())
    assert man["vector_order"] == "np.nonzero(np.isfinite(sample_submission)) row-major"
    v = np.load(DEM10 / f"{name}.f32.npy")
    if v.size != int(footprint.sum()):
        raise ValueError(f"{name}: vector length {v.size} != footprint {int(footprint.sum())}")
    out = np.full(footprint.shape, np.nan, np.float32)
    out[footprint] = v
    return out


def read_road_logdist(footprint: np.ndarray) -> np.ndarray:
    """log1p(distance to nearest TIGER road, metres). Finite exactly on the
    footprint in the pinned file (verified this session: 5,167,373 finite)."""
    with rasterio.open(ROAD_DIST) as ds:
        a = ds.read(1).astype(np.float32)
    out = np.full(a.shape, np.nan, np.float32)
    m = footprint & np.isfinite(a)
    out[m] = np.log1p(np.clip(a[m], 0, None))
    return out
