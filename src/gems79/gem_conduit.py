"""Novel GEMSDOE79 lane: concealed-geothermal-conduit surface.

Hypothesis (single method paragraph, this lane).
  Layers: training_features band 18 ``iso_grav_anom_hg`` (isostatic gravity
  anomaly horizontal gradient -- an edge/density-contrast detector that
  highlights fault-controlled basin margins and blind faults) and band 1
  ``mag_anom`` (total magnetic anomaly; low values mark hydrothermal
  demagnetization / smectite-clay alteration above a geothermal system).
  Physical signature: a concealed conduit fault produces BOTH a strong local
  gravity gradient (subsurface density contrast) AND a magnetic low
  (hydrothermal demagnetization), with neither expression requiring a mapped
  surface trace. Score surface = gravity-edge rank x (1 - magnetic-anomaly
  rank), zeroed on the mapped catalogue and outside the scored footprint.
  Why it catches catalogue-missing faults: the USGS/INGENIOUS catalogue maps
  surface traces; geothermal upwelling faults are commonly blind (no surface
  rupture) but still displace density (gravity gradient) and demagnetize host
  rock (magnetic low). A gravity-edge x magnetic-low coincidence therefore
  targets concealed conduits absent from the catalogue.
  How it differs from existing repo lanes: G79-THVC is an 84-channel ensemble
  with crack-tip lobes; G79-DZD is a damage-zone distance decay anchored to
  mapped traces; G79-FF1 (features.py) is a strike-parallel fabric-offset
  registration. This lane uses exactly two channels, no strike registration,
  no catalogue anchoring, and explicitly excludes the catalogue -- a
  catalogue-independent concealed-fault detector.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from gems57 import grid as G, metric as M

BAND_GRAV_HG = 18   # iso_grav_anom_hg
BAND_MAG = 1        # mag_anom


def unit_ranks(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.zeros(values.shape, np.float32)
    v = np.asarray(values)[np.asarray(valid, bool)]
    if len(v) and np.ptp(v) > 0:
        out[np.asarray(valid, bool)] = (
            (rankdata(v, method="average") - 1) / max(len(v) - 1, 1)
        ).astype(np.float32)
    return out


def read_band(stack_path: Path, band: int, footprint: np.ndarray):
    import rasterio

    with rasterio.open(stack_path) as src:
        a = src.read(band).astype(np.float32)
        nodata = src.nodata
    valid = np.asarray(footprint, bool) & np.isfinite(a) & (a > -1e38)
    if nodata is not None and np.isfinite(nodata):
        valid &= a != nodata
    if not valid.any():
        raise ValueError(f"cached band {band} has no valid observations")
    filled = np.where(valid, a, np.median(a[valid])).astype(np.float32)
    return filled, valid


def build_conduit_surface(stack_path: Path, footprint: np.ndarray,
                          catalogue: np.ndarray) -> dict:
    footprint = np.asarray(footprint, bool)
    catalogue = np.asarray(catalogue, bool)
    grav, gv = read_band(stack_path, BAND_GRAV_HG, footprint)
    mag, mv = read_band(stack_path, BAND_MAG, footprint)
    valid = gv & mv
    g_edge_rank = unit_ranks(grav, valid)        # high = strong gravity gradient
    mag_low = 1.0 - unit_ranks(mag, valid)       # high = strong demagnetization
    surface = (g_edge_rank * mag_low).astype(np.float32)
    surface = np.where(footprint & ~catalogue, surface, 0.0).astype(np.float32)
    mx = float(surface.max())
    if mx > 0:
        surface = (surface / mx).astype(np.float32)
    return {
        "surface": surface,
        "g_edge_rank": g_edge_rank,
        "mag_low": mag_low,
        "valid": valid,
        "positive_pixels": int((surface > 0).sum()),
        "surface_max": float(surface.max()),
    }


def sym_auc(feature: np.ndarray, pos_idx: np.ndarray, neg_idx: np.ndarray) -> float:
    """Mann-Whitney AUC of ``feature`` separating pos vs neg (no sklearn)."""
    from scipy.stats import rankdata
    f = np.asarray(feature).ravel()
    vals = np.concatenate([f[pos_idx], f[neg_idx]])
    y = np.concatenate([np.ones(pos_idx.size), np.zeros(neg_idx.size)])
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(vals.size, np.float64)
    ranks[order] = rankdata(vals, method="average")
    n_pos = int(pos_idx.size)
    n_neg = int(neg_idx.size)
    sum_ranks_pos = ranks[:n_pos].sum()
    auc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


__all__ = ["build_conduit_surface", "sym_auc", "unit_ranks", "BAND_GRAV_HG", "BAND_MAG"]
