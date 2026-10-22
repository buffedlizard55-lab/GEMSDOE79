"""H79-ASYM: antislope excess surface from the USGS 3DEP lidar scarp product.

Preregistered in registry/preregistration_asym.json (commit 365b727). No learning, no
catalogue input, no registry input. The surface is label-independent, so it can be
checked for uniqueness before any holdout placement.

Decoding follows the product's own quantisation rule (lidar_scarp_features.json):
    q = 1 + round(254 * t),  t = sqrt(clip(x / xmax, 0, 1))  (sqrt bands)
    q = 1 + round(254 * t),  t = clip(x / xmax, 0, 1)        (linear bands)
and q = 0 means no lidar. So for sqrt bands x = xmax * ((q - 1) / 254) ** 2.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
LIDAR = ROOT / "data" / "raw" / "external" / "lidar_scarp_features_u8.tif"


def _decode_sqrt(q: np.ndarray, xmax: float) -> np.ndarray:
    t = (q.astype(np.float32) - 1.0) / 254.0
    return (xmax * t * t).astype(np.float32)


def _decode_linear(q: np.ndarray, xmax: float) -> np.ndarray:
    return (xmax * (q.astype(np.float32) - 1.0) / 254.0).astype(np.float32)


def build(footprint: np.ndarray, lidar_path: Path = LIDAR) -> dict:
    """Return the decoded bands, the antislope excess surface S and its validity mask."""
    fp = np.asarray(footprint, bool)
    with rasterio.open(lidar_path) as src:
        names = list(src.descriptions)
        qu = src.read(names.index("upface_max") + 1)
        qd = src.read(names.index("downface_max") + 1)
        qc = src.read(names.index("coh100") + 1)
    valid = (qu > 0) & (qd > 0) & (qc > 0) & fp
    U = np.where(valid, _decode_sqrt(qu, 1.0), 0).astype(np.float32)
    D = np.where(valid, _decode_sqrt(qd, 1.0), 0).astype(np.float32)
    C = np.where(valid, _decode_linear(qc, 1.0), 0).astype(np.float32)
    excess = np.where(valid, np.maximum(U - D, 0.0) * C, 0.0).astype(np.float32)
    pos = excess[valid]
    p999 = float(np.percentile(pos, 99.9)) if pos.size else 1.0
    if not p999 > 0:
        p999 = 1.0
    S = np.clip(excess / p999, 0.0, 1.0).astype(np.float32)
    S[~valid] = 0.0
    return dict(S=S, U=U, D=D, C=C, valid=valid, p999=p999, names=names)
