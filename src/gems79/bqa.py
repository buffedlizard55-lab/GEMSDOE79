"""H79-BQA: band-quota allocation of a band-reweighted nested hide-and-recover model.

Preregistered in registry/preregistration_bqa.json before any result. Two pieces
are new here; everything else (feature stack, nested hides, regressor, evaluator,
writer, novelty tool) is the shared code reused unchanged.

1. ``band_weights``: equal total weight per distance-to-visible band, so the
   regressor spends its splits on within-band discrimination instead of
   re-learning proximity to mapped faults (the proxy's known bias).
2. ``place_with_quotas``: fixed per-band dot quotas equal to H33's measured
   distance profile, greedy descending score with 3 px Euclidean spacing; any
   unfilled quota is then filled by a second global descending pass.
"""
from __future__ import annotations

import numpy as np

# (lo, hi] in pixels of distance to the visible catalogue; [0, 2] never eligible.
PLACEMENT_BANDS = ((2, 3), (3, 5), (5, 10), (10, 20), (20, 50), (50, 1_000_000))
# RASTER-MEASUREMENT of H33 dots (evidence/nhr/distance_to_catalogue.json).
H33_BAND_COUNTS = (1611, 3237, 6292, 7908, 11077, 7529)
H33_TOTAL = 37654
WEIGHT_EDGES = (0, 2) + tuple(hi for _, hi in PLACEMENT_BANDS)  # 7 weighting bands


def band_of_distance(d: np.ndarray) -> np.ndarray:
    """Placement band index 0..5 for distance ``d`` (px); -1 for d <= 2 px."""
    d = np.asarray(d, np.float64)
    out = np.full(d.shape, -1, np.int8)
    for b, (lo, hi) in enumerate(PLACEMENT_BANDS):
        out[(d > lo) & (d <= hi)] = b
    return out


def distance_from_log_feature(log_dist: np.ndarray) -> np.ndarray:
    """Invert the shared geometry input ``log_dist_visible = log1p(min(d, 200))``."""
    return np.expm1(np.asarray(log_dist, np.float64))


def band_weights(dist_px: np.ndarray) -> tuple[np.ndarray, dict]:
    """w = n / (B * n_band): each of the B = 7 weighting bands has equal total weight."""
    d = np.asarray(dist_px, np.float64)
    wb = np.full(d.shape, 0, np.int8)            # band 0 = [0, 2]
    wb[d > 2] = 1 + band_of_distance(d[d > 2])
    n = d.size
    counts = np.bincount(wb, minlength=7)
    present = counts > 0
    w = np.zeros(n, np.float64)
    for b in np.flatnonzero(present):
        w[wb == b] = n / (present.sum() * counts[b])
    return w.astype(np.float32), dict(rows_per_weighting_band=[int(c) for c in counts],
                                      weighting_band_edges_px=list(WEIGHT_EDGES))


def quotas(budget: int) -> list[int]:
    """Per-band quotas proportional to H33's band counts (largest-remainder rounding)."""
    raw = np.asarray(H33_BAND_COUNTS, np.float64) * budget / H33_TOTAL
    q = np.floor(raw).astype(int)
    rem = int(budget - q.sum())
    for i in np.argsort(-(raw - q), kind="stable")[:rem]:
        q[i] += 1
    return [int(x) for x in q]


def place_with_quotas(surface, allowed, band, budget, spacing=3):
    """Greedy descending placement with per-band quotas and Euclidean spacing.

    ``band`` holds the placement band (0..5) of each cell, -1 = ineligible.
    Pass 1 accepts a dot only while its band's quota is open; pass 2 fills any
    shortfall from the remaining eligible cells in global descending order.
    Stable row-major tie-break, no jitter (same convention as gems79.placement).
    """
    surface = np.asarray(surface)
    allowed = np.asarray(allowed, bool)
    band = np.asarray(band)
    if surface.shape != allowed.shape or band.shape != surface.shape or surface.ndim != 2:
        raise ValueError("surface/allowed/band grid mismatch")
    if not np.isfinite(surface).all() or np.any(surface < 0):
        raise ValueError("placement requires finite nonnegative values")
    if budget < 0 or spacing <= 0:
        raise ValueError("invalid placement parameters")
    q = quotas(budget)
    eligible = allowed & (band >= 0) & (surface > 0)
    indices = np.flatnonzero(eligible)
    indices = indices[np.argsort(-surface.ravel()[indices], kind="stable")]
    h, w = surface.shape
    blocked = ~allowed.copy()
    emitted = np.zeros(surface.shape, bool)
    yy, xx = np.mgrid[-spacing:spacing + 1, -spacing:spacing + 1]
    disk = yy * yy + xx * xx < spacing * spacing
    dy, dx = yy[disk], xx[disk]
    used = [0] * len(q)
    flat_band = band.ravel()
    n = 0

    def accept(index):
        y, x = divmod(int(index), w)
        emitted[y, x] = True
        ny, nx = y + dy, x + dx
        good = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
        blocked[ny[good], nx[good]] = True

    for index in indices:
        if n >= budget:
            break
        b = int(flat_band[index])
        if used[b] >= q[b] or blocked.flat[index]:
            continue
        accept(index)
        used[b] += 1
        n += 1
    second = 0
    if n < budget:
        for index in indices:
            if n >= budget:
                break
            if blocked.flat[index]:
                continue
            accept(index)
            used[int(flat_band[index])] += 1
            n += 1
            second += 1
    return emitted, dict(requested=int(budget), emitted=n, spacing_px=spacing, quotas=q,
                         emitted_per_band=used, second_pass_dots=second,
                         exhausted=n < budget, eligible_positive_pixels=int(indices.size),
                         bands_px=[list(b) for b in PLACEMENT_BANDS])
