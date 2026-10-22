"""G79B-SCARP-DIPOLE-GEOAND: preregistered rank-only surface (2026-10-22).

Implements registry/preregistration_g79b.json exactly. Rank transforms of
hash-pinned cached bands only; no fitted parameters, no prior prediction
values, no catalogue-derived scientific features. The catalogue enters later
only as a placement exclusion mask.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from .features import unit_ranks

FEATURE_NAMES = (
    'rank_lapneg', 'rank_lappos', 'rank_step',
    'rank_grav_hg', 'rank_tmi_hg',
    'lidar_triple', 'geo_or', 'road_factor',
    'scarp_dipole_surface', 'lidar_only_surface', 'geo_only_surface',
)

STACK = 'training_features.tif'
LIDAR = 'external/lidar_scarp_features_u8.tif'
ROADS = 'external/tiger_road_distance_m.tif'

# Band indices verified from embedded descriptions on 2026-10-22.
BAND_TMI_HG = 3        # tmi_hg
BAND_GRAV_HG = 18      # iso_grav_anom_hg
BAND_STEP = 3          # step_max
BAND_LAPNEG = 4        # lapneg_max
BAND_LAPPOS = 5        # lappos_max
BAND_COH = 10          # coh100 (Exp2 contingency only)
BAND_VALID = 12        # valid (fraction of valid lidar samples, u8 linear)
LIDAR_VALID_MIN_U8 = 128  # >= ~50% lidar coverage in the 100 m cell


def _read_float_band(path, band, footprint):
    with rasterio.open(path) as src:
        a = src.read(band).astype(np.float32)
        nodata = src.nodata
    valid = footprint & np.isfinite(a) & (a > -1e38)
    if nodata is not None and np.isfinite(nodata):
        valid &= a != nodata
    if not valid.any():
        raise ValueError(f'band {band} of {path} has no valid observations')
    return a, valid


def _read_u8_band(path, band):
    with rasterio.open(path) as src:
        return src.read(band)


def build(raw_dir, footprint, output_dir, *, include_coherence=False):
    """Write .npy feature arrays + support.npy; return counts for the receipt."""
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    footprint = np.asarray(footprint, bool)

    counts = {'footprint_cells': int(footprint.sum())}

    # --- lidar support and dipole components (0 = no lidar, per sidecar JSON)
    valid_u8 = _read_u8_band(raw_dir / LIDAR, BAND_VALID)
    lidar_ok = footprint & (valid_u8 >= LIDAR_VALID_MIN_U8)
    del valid_u8
    counts['lidar_supported_cells'] = int(lidar_ok.sum())

    ranks = {}
    for name, band in (('rank_lapneg', BAND_LAPNEG), ('rank_lappos', BAND_LAPPOS),
                       ('rank_step', BAND_STEP)):
        q = _read_u8_band(raw_dir / LIDAR, band)
        # Quantisation is monotonic (sidecar JSON), so u8 ranks == physical ranks.
        ranks[name] = unit_ranks(q.astype(np.float32), lidar_ok & (q > 0))
        del q
    if include_coherence:
        q = _read_u8_band(raw_dir / LIDAR, BAND_COH)
        ranks['rank_coh100'] = unit_ranks(q.astype(np.float32), lidar_ok & (q > 0))
        del q

    # --- potential-field edges from the 19-band stack
    geo_valid = footprint.copy()
    for name, band in (('rank_grav_hg', BAND_GRAV_HG), ('rank_tmi_hg', BAND_TMI_HG)):
        a, v = _read_float_band(raw_dir / STACK, band, footprint)
        ranks[name] = unit_ranks(a, v)
        geo_valid &= v
        counts[f'valid_cells_band{band}'] = int(v.sum())
        del a, v

    support = lidar_ok & geo_valid
    counts['support_cells'] = int(support.sum())
    del lidar_ok, geo_valid

    # --- road suppression (missing road evidence inside footprint -> factor 1)
    road, road_valid = _read_float_band(raw_dir / ROADS, 1, footprint)
    road_factor = np.ones(footprint.shape, np.float32)
    road_factor[road_valid] = np.clip(road[road_valid] / 300.0, 0.1, 1.0).astype(np.float32)
    counts['road_valid_cells'] = int(road_valid.sum())
    counts['road_suppressed_below_1_cells'] = int((road_factor < 1).sum())
    del road, road_valid

    lidar_triple = (ranks['rank_lapneg'] * ranks['rank_lappos'] * ranks['rank_step']) ** (1.0 / 3.0)
    geo_or = np.maximum(ranks['rank_grav_hg'], ranks['rank_tmi_hg'])
    lidar_triple = np.where(support, lidar_triple, 0).astype(np.float32)
    geo_or = np.where(support, geo_or, 0).astype(np.float32)

    surface = np.where(support, np.sqrt(lidar_triple * geo_or) * road_factor, 0).astype(np.float32)
    lidar_only = np.where(support, lidar_triple * road_factor, 0).astype(np.float32)
    geo_only = np.where(support, geo_or * road_factor, 0).astype(np.float32)
    counts['surface_positive_cells'] = int((surface > 0).sum())

    arrays = dict(ranks)
    arrays.update({
        'lidar_triple': lidar_triple, 'geo_or': geo_or, 'road_factor': road_factor,
        'scarp_dipole_surface': surface, 'lidar_only_surface': lidar_only,
        'geo_only_surface': geo_only,
    })
    for name, arr in arrays.items():
        arr = np.asarray(arr, np.float32)
        if not np.isfinite(arr).all() or (arr < 0).any() or (arr > 1).any():
            raise ValueError(f'feature {name} escaped finite [0,1]')
        np.save(output_dir / f'{name}.npy', arr)
    np.save(output_dir / 'support.npy', support)
    return counts
