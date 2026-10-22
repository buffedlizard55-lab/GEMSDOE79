"""Fixed-budget descending-rank Poisson spacing, not tuned on hidden labels."""
from __future__ import annotations
import numpy as np


def place(surface, allowed, budget, spacing=3):
    surface = np.asarray(surface)
    allowed = np.asarray(allowed, bool)
    if surface.shape != allowed.shape or surface.ndim != 2:
        raise ValueError('surface/placement grid mismatch')
    if not np.isfinite(surface).all() or np.any(surface < 0):
        raise ValueError('placement requires finite nonnegative values')
    if budget < 0 or spacing <= 0:
        raise ValueError('invalid placement parameters')
    indices = np.flatnonzero(allowed & (surface > 0))
    # Stable tie-break: row-major. No coordinate/random jitter for novelty.
    indices = indices[np.argsort(-surface.ravel()[indices], kind='stable')]
    h, w = surface.shape
    blocked = ~allowed.copy()
    emitted = np.zeros(surface.shape, bool)
    yy, xx = np.mgrid[-spacing:spacing + 1, -spacing:spacing + 1]
    dy, dx = yy[yy * yy + xx * xx < spacing * spacing], xx[yy * yy + xx * xx < spacing * spacing]
    n = 0
    for index in indices:
        if n >= budget:
            break
        y, x = divmod(int(index), w)
        if blocked[y, x]:
            continue
        emitted[y, x] = True
        n += 1
        ny, nx = y + dy, x + dx
        good = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
        blocked[ny[good], nx[good]] = True
    return emitted, dict(requested=int(budget), emitted=n, spacing_px=spacing,
                         exhausted=n < budget, eligible_positive_pixels=len(indices))


def place_banded(band_surfaces, band_allowed, quotas, spacing=3):
    """G79-BER placement: per-band quotas under one global spacing mask.

    Bands are processed in the order given (preregistered: nearest to
    farthest catalogue-distance band).  Each band is ranked by its own
    surface only; a single blocked mask shared across bands guarantees the
    >= ``spacing`` px separation also across band boundaries.  Unspent quota
    in an exhausted band is never redistributed to another band.
    Returns (emitted_mask, per-band info list).
    """
    if not (len(band_surfaces) == len(band_allowed) == len(quotas)):
        raise ValueError("banded placement inputs must have equal lengths")
    if spacing <= 0 or any(int(q) < 0 for q in quotas):
        raise ValueError("invalid banded placement parameters")
    shapes = {np.asarray(s).shape for s in band_surfaces} | {np.asarray(a).shape for a in band_allowed}
    if len(shapes) != 1:
        raise ValueError("banded placement grid mismatch")
    shape = shapes.pop()
    h, w = shape
    yy, xx = np.mgrid[-spacing:spacing + 1, -spacing:spacing + 1]
    keep = yy * yy + xx * xx < spacing * spacing
    dy, dx = yy[keep], xx[keep]
    blocked = np.zeros(shape, bool)
    emitted = np.zeros(shape, bool)
    infos = []
    for surface, allowed, quota in zip(band_surfaces, band_allowed, quotas):
        surface = np.asarray(surface)
        allowed = np.asarray(allowed, bool)
        if not np.isfinite(surface).all() or np.any(surface < 0):
            raise ValueError("banded placement requires finite nonnegative surfaces")
        indices = np.flatnonzero(allowed & (surface > 0))
        indices = indices[np.argsort(-surface.ravel()[indices], kind="stable")]
        n = 0
        quota = int(quota)
        for index in indices:
            if n >= quota:
                break
            y, x = divmod(int(index), w)
            if blocked[y, x] or not allowed[y, x]:
                continue
            emitted[y, x] = True
            n += 1
            ny, nx = y + dy, x + dx
            good = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
            blocked[ny[good], nx[good]] = True
        infos.append(dict(requested=quota, emitted=n, spacing_px=spacing,
                          exhausted=n < quota, eligible_positive_pixels=len(indices)))
    return emitted, infos
