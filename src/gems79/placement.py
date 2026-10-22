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
