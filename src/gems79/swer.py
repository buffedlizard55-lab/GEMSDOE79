"""G79-SWER: catalogue-free swarm-excess structural-ridge transform.

The closed equations are preregistered in
``registry/preregistration_g79_swer.json``.  This module has no holdout,
registry, placement, or submission I/O: it only turns seven pinned physical
bands into fixed, label-free surfaces while masking float32 sentinels before
any derivative or smoothing operation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np
import rasterio
from scipy import ndimage as ndi

BANDS: Mapping[str, int] = {
    "tmi_hg": 3,
    "geod_shearrate": 7,
    "geod_dilaterate": 8,
    "deq_n100a15": 10,
    "depth_to_base_surf": 15,
    "ieq_n100a15": 16,
    "iso_grav_anom_hg": 18,
}

CANARY_FEATURES = (
    "log_deq",
    "log_ieq",
    "swarm_excess",
    "mag_edge_rank",
    "grav_edge_rank",
    "edge_coherence",
    "transtension",
    "cover",
    "candidate",
)


@dataclass(frozen=True)
class SwerStack:
    """Fixed surfaces and their auditable transform metadata."""

    features: dict[str, np.ndarray]
    valid: np.ndarray
    metadata: dict

    @property
    def candidate(self) -> np.ndarray:
        return self.features["candidate"]


def _valid(a: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Organizer-footprint finite observations, excluding float sentinels."""
    return np.asarray(footprint, bool) & np.isfinite(a) & (a > -1e30)


def quantile01(a: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, tuple[float, float]]:
    """Prospectively fixed P10/P90 clamp; invalid and constant fields -> zero."""
    a = np.asarray(a, np.float32)
    valid = np.asarray(valid, bool)
    out = np.zeros(a.shape, np.float32)
    values = a[valid]
    if values.size == 0:
        raise ValueError("quantile transform has no valid observations")
    p10, p90 = (float(x) for x in np.percentile(values, [10.0, 90.0]))
    if not np.isfinite(p10) or not np.isfinite(p90):
        raise ValueError("quantile transform produced a non-finite endpoint")
    if p90 > p10:
        out[valid] = np.clip((values - p10) / (p90 - p10), 0.0, 1.0).astype(np.float32)
    return out, (p10, p90)


def masked_gaussian(a: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing without treating invalid/outside cells as zero data."""
    a = np.asarray(a, np.float32)
    valid = np.asarray(valid, bool)
    weight = ndi.gaussian_filter(valid.astype(np.float32), sigma, mode="constant", cval=0.0)
    num = ndi.gaussian_filter(np.where(valid, a, 0.0), sigma, mode="constant", cval=0.0)
    out = np.divide(num, weight, out=np.zeros_like(num, dtype=np.float32), where=weight > 1e-6)
    out[~valid] = 0.0
    return out.astype(np.float32, copy=False)


def structure_coherence(edge: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Preregistered sigma-1.5 gradient / sigma-4 structure-tensor coherence."""
    smooth = masked_gaussian(edge, valid, 1.5)
    gy, gx = np.gradient(smooth)
    weight = ndi.gaussian_filter(valid.astype(np.float32), 4.0, mode="constant", cval=0.0)

    def avg(v: np.ndarray) -> np.ndarray:
        num = ndi.gaussian_filter(np.where(valid, v, 0.0), 4.0, mode="constant", cval=0.0)
        return np.divide(num, weight, out=np.zeros_like(num, dtype=np.float32), where=weight > 1e-6)

    jxx = avg(gx * gx)
    jyy = avg(gy * gy)
    jxy = avg(gx * gy)
    coherence = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    coherence = np.divide(
        coherence,
        jxx + jyy + np.float32(1e-6),
        out=np.zeros_like(coherence, dtype=np.float32),
        where=valid,
    )
    coherence = np.clip(coherence, 0.0, 1.0).astype(np.float32)
    coherence[~valid] = 0.0
    return coherence


def _read_checked(src: rasterio.io.DatasetReader, name: str) -> np.ndarray:
    band = BANDS[name]
    desc = (src.descriptions[band - 1] or "").split(" - ", 1)[0]
    if desc != name:
        raise ValueError(f"band {band} identity mismatch: {desc!r} != {name!r}")
    return src.read(band).astype(np.float32)


def build_swer_stack(stack_path: str | Path, footprint: np.ndarray) -> SwerStack:
    """Build all preregistered G79-SWER canary features and primary surface."""
    footprint = np.asarray(footprint, bool)
    if footprint.ndim != 2 or not footprint.any():
        raise ValueError("footprint must be a nonempty 2-D mask")
    stack_path = Path(stack_path)

    # First pass establishes one shared validity mask exactly as preregistered.
    valid = footprint.copy()
    descriptions: dict[str, str] = {}
    with rasterio.open(stack_path) as src:
        if src.count != 19 or src.shape != footprint.shape:
            raise ValueError("training feature stack grid/count mismatch")
        for name in BANDS:
            a = _read_checked(src, name)
            valid &= _valid(a, footprint)
            descriptions[name] = src.descriptions[BANDS[name] - 1] or ""
            del a
    if not valid.any():
        raise ValueError("seven-band shared validity mask is empty")

    endpoints: dict[str, list[float]] = {}
    features: dict[str, np.ndarray] = {}

    with rasterio.open(stack_path) as src:
        deq = _read_checked(src, "deq_n100a15")
        ieq = _read_checked(src, "ieq_n100a15")
        log_deq_raw = np.log1p(np.maximum(deq, 0.0)).astype(np.float32)
        log_ieq_raw = np.log1p(np.maximum(ieq, 0.0)).astype(np.float32)
        features["log_deq"], ep = quantile01(log_deq_raw, valid)
        endpoints["log_deq"] = list(ep)
        features["log_ieq"], ep = quantile01(log_ieq_raw, valid)
        endpoints["log_ieq"] = list(ep)
        contrast = (log_deq_raw - log_ieq_raw).astype(np.float32)
        features["swarm_excess"], ep = quantile01(contrast, valid)
        endpoints["swarm_excess"] = list(ep)
        del deq, ieq, log_deq_raw, log_ieq_raw, contrast

        tmi_hg = _read_checked(src, "tmi_hg")
        grav_hg = _read_checked(src, "iso_grav_anom_hg")
        mag_raw = np.log1p(np.abs(tmi_hg)).astype(np.float32)
        grav_raw = np.log1p(np.abs(grav_hg)).astype(np.float32)
        features["mag_edge_rank"], ep = quantile01(mag_raw, valid)
        endpoints["mag_edge_rank"] = list(ep)
        features["grav_edge_rank"], ep = quantile01(grav_raw, valid)
        endpoints["grav_edge_rank"] = list(ep)
        edge = np.sqrt(features["mag_edge_rank"] * features["grav_edge_rank"]).astype(np.float32)
        coherence = structure_coherence(edge, valid)
        features["edge_coherence"] = (edge * coherence).astype(np.float32)
        del tmi_hg, grav_hg, mag_raw, grav_raw, edge, coherence

        shear = _read_checked(src, "geod_shearrate")
        dilate = _read_checked(src, "geod_dilaterate")
        shear_q, ep = quantile01(np.maximum(shear, 0.0), valid)
        endpoints["positive_shear"] = list(ep)
        dilate_q, ep = quantile01(np.maximum(dilate, 0.0), valid)
        endpoints["positive_dilatation"] = list(ep)
        features["transtension"] = np.sqrt(shear_q * dilate_q).astype(np.float32)
        del shear, dilate, shear_q, dilate_q

        depth = _read_checked(src, "depth_to_base_surf")
        features["cover"], ep = quantile01(np.log1p(np.maximum(depth, 0.0)), valid)
        endpoints["cover"] = list(ep)
        del depth

    swarm = features["swarm_excess"]
    edge_coh = features["edge_coherence"]
    candidate = (
        np.power(swarm, 1.5)
        * (0.20 + 0.80 * edge_coh)
        * (0.35 + 0.65 * features["transtension"])
        * (0.40 + 0.60 * features["cover"])
    ).astype(np.float32)
    support = valid & (swarm >= 0.60) & (edge_coh >= 0.35)
    candidate[~support] = 0.0
    max_value = float(candidate.max())
    if max_value <= 0.0 or not np.isfinite(max_value):
        raise ValueError("fixed G79-SWER support is empty or non-finite")
    candidate /= np.float32(max_value)
    candidate[~footprint] = 0.0
    features["candidate"] = np.clip(candidate, 0.0, 1.0).astype(np.float32)

    for name in CANARY_FEATURES:
        arr = features[name]
        if arr.shape != footprint.shape or not np.isfinite(arr).all():
            raise AssertionError(f"{name} is not a finite aligned surface")
        if arr.min() < 0.0 or arr.max() > 1.0:
            raise AssertionError(f"{name} escaped [0,1]")
        if np.any(arr[~footprint] != 0.0):
            raise AssertionError(f"{name} has mass outside the footprint")

    metadata = {
        "feature_names": list(CANARY_FEATURES),
        "band_descriptions": descriptions,
        "valid_pixels": int(valid.sum()),
        "footprint_pixels": int(footprint.sum()),
        "invalid_inside_footprint": int((footprint & ~valid).sum()),
        "candidate_positive_pixels": int((features["candidate"] > 0).sum()),
        "candidate_max_before_rescale": max_value,
        "p10_p90": endpoints,
        "formula": "swarm^1.5*(.20+.80*edge_coherence)*(.35+.65*transtension)*(.40+.60*cover)",
        "support": "valid & swarm>=.60 & edge_coherence>=.35",
    }
    return SwerStack(features=features, valid=valid, metadata=metadata)
