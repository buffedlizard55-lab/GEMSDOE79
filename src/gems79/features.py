"""One preregistered, catalogue-independent magnetic-marker offset hypothesis.

The 19-band cached numerical feature stack is used directly; no replacement for
the unavailable historical 54-channel .npy stack is built. All arrays written by
this module are *new lane transforms*, not newly acquired observations.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata


FEATURE_NAMES = ('gravity_edge_rank', 'magnetic_contrast_rank', 'lag_gain_r3',
                 'lag_gain_r5', 'best_correlation_r3', 'best_correlation_r5',
                 'signed_lag_agreement', 'fabric_offset_surface', 'zero_lag_edge_control')


def unit_ranks(values, valid):
    """Footprint empirical mid-ranks; a constant field supplies no evidence."""
    out = np.zeros(values.shape, np.float32)
    v = np.asarray(values)[valid]
    if len(v) and np.ptp(v) > 0:
        out[valid] = ((rankdata(v, method='average') - 1) / max(len(v) - 1, 1)).astype(np.float32)
    return out


def registration(a, b, half_width=4, max_lag=3):
    """NCC tangent profiles: a has 9 samples; b has 15 samples.

    Returns positive nonzero-lag improvement, the selected signed lag, and its
    correlation. Ties prefer the smallest displacement, then negative before
    positive; no stochastic fitting or hidden-label parameters are involved.
    """
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
    # A displaced but anticorrelated marker is not a match.
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
        # Coordinates never wrap. The support erosion in build() makes every
        # interpolation stencil and Gaussian neighbourhood valid observations.
        return np.stack([
            ndi.map_coordinates(field, [y + side * radius * ny + k * ty,
                                        x + side * radius * nx + k * tx],
                                order=1, mode='constant', cval=0, prefilter=False)
            for k in ks], axis=1)
    return sample(1, range(-4, 5)), sample(-1, range(-7, 8))


def build(stack_path, footprint, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    magnetic, mv = _read(stack_path, 2, footprint)
    gravity, gv = _read(stack_path, 13, footprint)
    # 12 px gravity Gaussian support + <=10 px sample stencil, rounded up.
    support = ndi.minimum_filter((mv & gv).astype(np.uint8), size=47, mode='constant', cval=0) > 0
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
    contrast = np.zeros(footprint.shape, np.float32)
    for orient in range(8):
        y, x = np.nonzero(support & (direction == orient))
        if not len(y):
            continue
        print(f'Fabric-offset normal {orient + 1}/8: {len(y)} supported cells', flush=True)
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
    surface = (arrays['gravity_edge_rank'] * arrays['magnetic_contrast_rank']
               * np.sqrt(arrays['lag_gain_r3'] * arrays['lag_gain_r5'])
               * arrays['signed_lag_agreement'])
    arrays['fabric_offset_surface'] = surface.astype(np.float32)
    arrays['zero_lag_edge_control'] = (arrays['gravity_edge_rank']
                                       * arrays['magnetic_contrast_rank']).astype(np.float32)
    for name, arr in arrays.items():
        if not np.isfinite(arr).all():
            raise ValueError(f'nonfinite transform {name}')
        np.save(output_dir / (name + '.npy'), arr)
    np.save(output_dir / 'support.npy', support)
    return {'supported_pixels': int(support.sum()), 'footprint_pixels': int(footprint.sum()),
            'positive_surface_pixels': int((surface > 0).sum()),
            'surface_max': float(surface.max()), 'feature_names': list(arrays),
            'normal_bins': 8, 'full_stencil_support_erosion_px': 23,
            'imputed_output_pixels': 0,
            'note': 'Interpolation/filters use filled work arrays but every emitted surface cell has a complete valid-input stencil; unsupported cells abstain.'}
