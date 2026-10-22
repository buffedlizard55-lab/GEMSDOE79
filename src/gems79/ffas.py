"""H79-FFAS: far-field polarity-aware antislope scarp (closed-form rank surface).

Lane paragraph (preregistered in registry/preregistration_ffas.json)
-------------------------------------------------------------------
Uphill-facing and intra-basin fault scarps more than a few hundred metres from
the public catalogue are the structures regional compilers under-map. From the
USGS 3DEP lidar scarp stack only, form a fixed (not learned) polarity-aware
scarp score (downface + 2*upface) times step, slope-excess, along-strike
coherence and cross-strike expression, then multiply by a logistic far-field
weight of distance to the visible catalogue (centre 8 px = 800 m, scale 3 px).
Rank the product on the footprint, mask mapped pixels exactly, apply a 2 px
visible-echo collar, and emit 37,654 binary dots with 3 px Poisson spacing.

Every catalogue-derived input is computed from the visible catalogue only; no
registry raster or prior submission is an input. Nothing here is tuned on the
evaluation holdout.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
LIDAR_PATH = RAW / "external" / "lidar_scarp_features_u8.tif"
LIDAR_SHA256 = "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568"

BANDS = ("upface_max", "downface_max", "step_max", "ex_max", "coh100", "cross_max", "valid")
FEATURE_NAMES = (
    "upface_max", "downface_max", "step_max", "ex_max", "coh100", "cross_max",
    "polarity_boosted", "logistic_farfield", "ffas_raw",
)

UPFACE_BOOST = 2.0
LOGISTIC_D0_PX = 8.0
LOGISTIC_SCALE_PX = 3.0
MIN_DISTANCE_TO_VISIBLE_PX = 2
BUDGET = 37654
SPACING_PX = 3


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_lidar() -> tuple[dict[str, np.ndarray], dict]:
    """Read the pinned lidar u8 product. 0 = no lidar on every band."""
    if not LIDAR_PATH.is_file():
        raise FileNotFoundError(f"missing lidar product: {LIDAR_PATH}")
    digest = _sha(LIDAR_PATH)
    if digest != LIDAR_SHA256:
        raise ValueError(f"lidar SHA-256 mismatch: {digest} != {LIDAR_SHA256}")
    with rasterio.open(LIDAR_PATH) as src:
        descr = list(src.descriptions)
        missing = [n for n in BANDS if n not in descr]
        if missing:
            raise ValueError(f"lidar bands missing {missing}; have {descr}")
        bands = {n: src.read(descr.index(n) + 1).astype(np.float32) for n in BANDS}
    return bands, {"path": str(LIDAR_PATH.relative_to(ROOT)), "sha256": digest, "bands": list(BANDS)}


def logistic_farfield(visible: np.ndarray, d0: float = LOGISTIC_D0_PX,
                      scale: float = LOGISTIC_SCALE_PX) -> np.ndarray:
    """1 / (1 + exp(-(d - d0)/s)) of Euclidean distance to visible catalogue."""
    vis = np.asarray(visible, bool)
    d = ndi.distance_transform_edt(~vis).astype(np.float32)
    return (1.0 / (1.0 + np.exp(-(d - float(d0)) / float(scale)))).astype(np.float32)


def polarity_product(bands: dict[str, np.ndarray], upface_boost: float = UPFACE_BOOST) -> np.ndarray:
    up = bands["upface_max"]
    down = bands["downface_max"]
    step = bands["step_max"]
    ex = bands["ex_max"]
    coh = bands["coh100"]
    cross = bands["cross_max"]
    valid = bands["valid"] > 0
    raw = ((down + float(upface_boost) * up) * step
           * (coh / 255.0) * (cross / 255.0) * (ex / 255.0))
    return np.where(valid, raw, 0.0).astype(np.float32)


def rank01(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Footprint mid-ranks in [0, 1]; a constant field is all zeros (no evidence)."""
    out = np.zeros(values.shape, np.float32)
    m = np.asarray(mask, bool)
    v = np.asarray(values, np.float64)[m]
    if v.size == 0 or np.ptp(v) <= 0:
        return out
    out[m] = ((rankdata(v, method="average") - 1.0) / max(len(v) - 1, 1)).astype(np.float32)
    return out


def surface(bands: dict[str, np.ndarray], visible: np.ndarray, footprint: np.ndarray,
            catalogue: np.ndarray, *, upface_boost: float = UPFACE_BOOST,
            farfield: bool = True) -> np.ndarray:
    """Closed-form [0,1] rank surface. Catalogue pixels are zero."""
    raw = polarity_product(bands, upface_boost=upface_boost)
    if farfield:
        raw = raw * logistic_farfield(visible)
    fp = np.asarray(footprint, bool)
    cat = np.asarray(catalogue, bool)
    valid = (bands["valid"] > 0) & fp
    ranked = rank01(raw, valid)
    ranked[cat] = 0
    ranked[~fp] = 0
    if not np.isfinite(ranked).all() or (ranked < 0).any() or (ranked > 1).any():
        raise ValueError("FFAS surface left [0,1] or became non-finite")
    return ranked.astype(np.float32)


def allowed_mask(footprint: np.ndarray, visible: np.ndarray, catalogue: np.ndarray,
                 region: np.ndarray | None = None) -> np.ndarray:
    """Pixel-exact catalogue mask plus the preregistered 2 px visible-echo collar."""
    fp = np.asarray(footprint, bool)
    vis = np.asarray(visible, bool)
    cat = np.asarray(catalogue, bool)
    d = ndi.distance_transform_edt(~vis)
    allow = fp & ~cat & (d > MIN_DISTANCE_TO_VISIBLE_PX)
    if region is not None:
        allow &= np.asarray(region, bool)
    return allow


def feature_maps(bands: dict[str, np.ndarray], visible: np.ndarray,
                 footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Full-grid maps for leakage canaries (NaN where lidar is missing)."""
    fp = np.asarray(footprint, bool)
    valid = (bands["valid"] > 0) & fp
    out = {}
    for name in ("upface_max", "downface_max", "step_max", "ex_max", "coh100", "cross_max"):
        a = bands[name].astype(np.float32)
        out[name] = np.where(valid, a, np.nan).astype(np.float32)
    pol = polarity_product(bands)
    out["polarity_boosted"] = np.where(valid, pol, np.nan).astype(np.float32)
    w = logistic_farfield(visible)
    out["logistic_farfield"] = np.where(fp, w, np.nan).astype(np.float32)
    raw = pol * w
    out["ffas_raw"] = np.where(valid, raw, np.nan).astype(np.float32)
    return out
