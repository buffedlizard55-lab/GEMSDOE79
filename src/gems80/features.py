"""H80 triple-concordance: det_elev_slope + iso_grav_anom_hg + tmi_hg

Uses only cached 19-band training_features.tif (sha256 4371c82e3b833...), no catalogue features.
All transforms are deterministic, no learned weights.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import rasterio
from scipy.stats import rankdata

FEATURE_NAMES = (
    'det_elev_slope_rank',
    'iso_grav_hg_rank',
    'tmi_hg_rank',
    'triple_concordance',
    'pairwise_scarp_grav_control',
)

def unit_ranks(values, valid):
    out = np.zeros(values.shape, np.float32)
    v = np.asarray(values)[valid]
    if len(v) and np.ptp(v) > 0:
        out[valid] = ((rankdata(v, method='average') - 1) / max(len(v) - 1, 1)).astype(np.float32)
    return out

def _read_band(path, band, footprint):
    with rasterio.open(path) as src:
        a = src.read(band).astype(np.float32)
        nodata = src.nodata
    # valid = footprint & finite & not sentinel
    valid = footprint & np.isfinite(a) & (a > -1e30)
    if nodata is not None and np.isfinite(nodata):
        # nodata is usually -3.4e38, already excluded by > -1e30
        pass
    if not valid.any():
        raise ValueError(f'band {band} has no valid observations')
    # fill outside valid with median for filtering (but we will mask later)
    filled = np.where(valid, a, np.median(a[valid])).astype(np.float32)
    return filled, valid

def build(stack_path, footprint, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # bands: 19 det_elev_slope, 18 iso_grav_anom_hg, 3 tmi_hg
    # descriptions: 19 det_elev_slope, 18 iso_grav_anom_hg, 3 tmi_hg
    slope, v1 = _read_band(stack_path, 19, footprint)
    grav_hg, v2 = _read_band(stack_path, 18, footprint)
    tmi_hg, v3 = _read_band(stack_path, 3, footprint)

    # support = intersection of all three valid + footprint
    # No additional erosion needed because we are not sampling offset stencils
    support = (v1 & v2 & v3 & footprint)
    # However to avoid edge artifacts from median-filled outside, we keep support as only footprint-valid
    # For safety, erode by 1 px to avoid boundary where median fill influences rank? Not needed for ranks.
    # Keep simple.

    # compute ranks within support
    arrays = {}
    arrays['det_elev_slope_rank'] = unit_ranks(slope, support)
    arrays['iso_grav_hg_rank'] = unit_ranks(grav_hg, support)
    arrays['tmi_hg_rank'] = unit_ranks(tmi_hg, support)

    # triple concordance: geometric mean of three ranks, keeps in [0,1]
    # Using cbrt to preserve rank scale
    r1 = arrays['det_elev_slope_rank']
    r2 = arrays['iso_grav_hg_rank']
    r3 = arrays['tmi_hg_rank']
    triple = np.cbrt(r1 * r2 * r3).astype(np.float32)
    # pairwise control: scarp + grav only (without magnetic) for matched comparison
    pairwise = np.sqrt(r1 * r2).astype(np.float32)

    arrays['triple_concordance'] = triple
    arrays['pairwise_scarp_grav_control'] = pairwise

    # sanity: ensure finite, in [0,1]
    for name, arr in arrays.items():
        if not np.isfinite(arr).all():
            raise ValueError(f'nonfinite {name}')
        if (arr < -1e-6).any() or (arr > 1.000001).any():
            raise ValueError(f'out of range {name} min {arr.min()} max {arr.max()}')
        # zero outside support already
        np.save(output_dir / (name + '.npy'), arr)

    np.save(output_dir / 'support.npy', support)

    return {
        'supported_pixels': int(support.sum()),
        'footprint_pixels': int(footprint.sum()),
        'positive_surface_pixels': int((triple > 0).sum()),
        'surface_max': float(triple.max()),
        'surface_mean': float(triple.mean()),
        'feature_names': list(arrays.keys()),
        'note': 'Triple concordance uses only training_features bands 19,18,3 footprint ranks; no catalogue features.'
    }
