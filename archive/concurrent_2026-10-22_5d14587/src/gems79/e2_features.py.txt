"""E2 strain-weighted relay-ramp linkage surface.

Extends E1's opposite-side magnetic-marker displacement across a gravity edge
with extension-strain favourability from geodetic fields. No catalogue-distance
or borrowed-prediction features enter the surface.

Inputs are only the restored 19-band stack (training_features.tif) and the
footprint; every emitted cell has a complete 47-px support stencil.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

FEATURE_NAMES = (
    'gravity_edge_rank', 'magnetic_contrast_rank',
    'lag_gain_r3', 'lag_gain_r5',
    'best_correlation_r3', 'best_correlation_r5',
    'signed_lag_agreement', 'strain_favorability_rank',
    'fabric_offset_strain_surface', 'zero_lag_edge_control',
)

def unit_ranks(values, valid):
    out = np.zeros(values.shape, np.float32)
    v = np.asarray(values)[valid]
    if len(v) and np.ptp(v) > 0:
        out[valid] = ((rankdata(v, method='average') - 1) / max(len(v) - 1, 1)).astype(np.float32)
    return out

def registration(a, b, half_width=4, max_lag=3):
    a = np.asarray(a, np.float32)
    b = np.asarray(b, np.float32)
    width = 2 * half_width + 1
    if a.ndim != 2 or a.shape[1] != width or b.shape != (len(a), width + 2 * max_lag):
        raise ValueError('registration profile shape mismatch')
    ac = a - a.mean(axis=1, keepdims=True)
    an = np.sqrt((ac * ac).sum(axis=1))
    correlations = []
    for lag in range(-max_lag, max_lag + 1):
        bp = b[:, max_lag + lag:max_lag + lag + width]
        bc = bp - bp.mean(axis=1, keepdims=True)
        bn = np.sqrt((bc * bc).sum(axis=1))
        den = an * bn
        corr = np.divide((ac * bc).sum(axis=1), den,
                         out=np.zeros(len(a), np.float32), where=den > 1e-10)
        correlations.append(np.clip(corr, -1, 1))
    correlations = np.stack(correlations, axis=1)
    lags = np.array(sorted((l for l in range(-max_lag, max_lag + 1) if l),
                          key=lambda l: (abs(l), l)), dtype=np.int8)
    best_id = np.argmax(correlations[:, lags + max_lag], axis=1)
    best_lag = lags[best_id]
    best_corr = correlations[np.arange(len(a)), best_lag + max_lag]
    gain = np.maximum(best_corr - correlations[:, max_lag], 0) / 2
    gain *= np.clip((best_corr - .35) / .65, 0, 1)
    return gain.astype(np.float32), best_lag, best_corr.astype(np.float32)

def _read(path, band, footprint):
    with rasterio.open(path) as src:
        a = src.read(band).astype(np.float32)
        nodata = src.nodata
    valid = footprint & np.isfinite(a) & (a > -1e38)
    if nodata is not None and np.isfinite(nodata):
        valid &= a != nodata
    if not valid.any():
        raise ValueError(f'cached band {band} has no valid observations')
    filled = np.where(valid, a, np.median(a[valid])).astype(np.float32)
    return filled, valid

def _profiles(field, y, x, nx, ny, radius):
    tx, ty = -ny, nx
    def sample(side, ks):
        return np.stack([
            ndi.map_coordinates(field, [y + side * radius * ny + k * ty,
                                        x + side * radius * nx + k * tx],
                                order=1, mode='constant', cval=0, prefilter=False)
            for k in ks], axis=1)
    return sample(1, range(-4, 5)), sample(-1, range(-7, 8))

def build(stack_path, footprint, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Bands from training_features.tif (1-indexed)
    # 2=rTP, 13=iso_grav_anom, 4=geod_2ndinv, 8=geod_dilaterate
    magnetic, mv = _read(stack_path, 2, footprint)
    gravity, gv = _read(stack_path, 13, footprint)
    second_inv, sv = _read(stack_path, 4, footprint)
    dilate, dv = _read(stack_path, 8, footprint)
    # Support needs all four inputs valid for stencil
    support = ndi.minimum_filter((mv & gv & sv & dv).astype(np.uint8), size=47, mode='constant', cval=0) > 0
    # Magnetic gradient magnitude
    mgx = ndi.gaussian_filter(magnetic, 1.5, order=(0, 1), mode='nearest')
    mgy = ndi.gaussian_filter(magnetic, 1.5, order=(1, 0), mode='nearest')
    mag_grad = np.hypot(mgx, mgy).astype(np.float32)
    del mgx, mgy, magnetic
    gx = ndi.gaussian_filter(gravity, 3., order=(0, 1), mode='nearest')
    gy = ndi.gaussian_filter(gravity, 3., order=(1, 0), mode='nearest')
    g_edge = np.hypot(gx, gy).astype(np.float32)
    angle = np.mod(np.arctan2(gy, gx), np.pi)
    direction = np.mod(np.rint(angle * 8 / np.pi).astype(np.int16), 8)
    del gravity, gx, gy, angle
    arrays = {name: np.zeros(footprint.shape, np.float32) for name in FEATURE_NAMES[:7]}
    # strain favorability computed on valid support before orientation loop
    # Normalize second invariant (strain magnitude) and dilatation
    second_rank = unit_ranks(second_inv, support)
    dilate_rank = unit_ranks(dilate, support)
    # Extensional favourability: high strain magnitude * extensional dilatation
    # dilatation in Great Basin extensional setting: positive = extension
    # Use 0.5 + 0.5*rank to keep contribution non-zero even where dilatation low
    strain_fav = (second_rank * (0.5 + 0.5 * dilate_rank)).astype(np.float32)
    arrays['strain_favorability_rank'] = strain_fav
    contrast = np.zeros(footprint.shape, np.float32)
    for orient in range(8):
        y, x = np.nonzero(support & (direction == orient))
        if not len(y):
            continue
        print(f'E2 strain-weighted normal {orient + 1}/8: {len(y)} cells', flush=True)
        theta = orient * np.pi / 8
        nx, ny = np.cos(theta), np.sin(theta)
        gains, lags, corrs, stds = [], [], [], []
        for radius in (3, 5):
            a, b = _profiles(mag_grad, y, x, nx, ny, radius)
            gain, lag, corr = registration(a, b)
            gains.append(gain); lags.append(lag); corrs.append(corr)
            stds.append(np.minimum(a.std(axis=1), b.std(axis=1)))
        arrays['lag_gain_r3'][y, x], arrays['lag_gain_r5'][y, x] = gains
        arrays['best_correlation_r3'][y, x], arrays['best_correlation_r5'][y, x] = corrs
        arrays['signed_lag_agreement'][y, x] = ((lags[0] * lags[1]) > 0).astype(np.float32)
        contrast[y, x] = np.minimum(stds[0], stds[1])
        del a, b, gains, lags, corrs, stds
    arrays['gravity_edge_rank'] = unit_ranks(g_edge, support)
    arrays['magnetic_contrast_rank'] = unit_ranks(contrast, support)
    # E1 surface (no strain) for fair zero-lag control path compatibility
    e1_like = (arrays['gravity_edge_rank'] * arrays['magnetic_contrast_rank']
               * np.sqrt(arrays['lag_gain_r3'] * arrays['lag_gain_r5'])
               * arrays['signed_lag_agreement'])
    # E2 adds strain weighting
    surface = (e1_like * (0.4 + 0.6 * strain_fav)).astype(np.float32)
    arrays['fabric_offset_strain_surface'] = surface
    arrays['zero_lag_edge_control'] = (arrays['gravity_edge_rank']
                                       * arrays['magnetic_contrast_rank']).astype(np.float32)
    # Persist
    for name, arr in arrays.items():
        if not np.isfinite(arr).all():
            raise ValueError(f'nonfinite {name}')
        np.save(output_dir / (name + '.npy'), arr)
    np.save(output_dir / 'support.npy', support)
    return {'supported_pixels': int(support.sum()), 'footprint_pixels': int(footprint.sum()),
            'positive_surface_pixels': int((surface > 0).sum()),
            'surface_max': float(surface.max()),
            'feature_names': list(arrays),
            'normal_bins': 8, 'full_stencil_support_erosion_px': 23,
            'imputed_output_pixels': 0,
            'note': 'E2 strain-weighted extension of E1: same 47-px stencil, adds geodetic second invariant + dilatation favourability from bands 4 and 8; no catalogue-distance features.'}
