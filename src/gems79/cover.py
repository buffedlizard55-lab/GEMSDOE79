"""Greedy submodular max-cover emission under the official 300 m kernel.

The competition's TP term credits each truth pixel with the *maximum*
kernel-weighted prediction within 300 m, while FP is charged per predicted
unit.  Descending-rank Poisson thinning (`gems79.placement.place`) ignores
how much of a candidate dot's kernel footprint is already covered by earlier
dots.  This allocator instead maximises the expected-coverage objective

    F(S) = sum_c p(c) * max_{x in S} k(d(x, c)),   k(d) = max(1 - d/3px, 0)

greedily (F is monotone submodular in S, so lazy greedy with stale upper
bounds is exact for the greedy order).  A 3 px minimum spacing (Euclidean,
same rule as `gems79.placement`) is enforced on top, the budget is fixed by
the caller, and ties break row-major.  No hidden label is consulted: ``p`` is
the model's predicted kernel-credit surface.
"""
from __future__ import annotations

import heapq

import numpy as np
from scipy import ndimage as ndi

RADIUS = 3.0


def _kernel():
    yy, xx = np.mgrid[-2:3, -2:3]
    d = np.hypot(yy, xx)
    k = np.maximum(1.0 - d / RADIUS, 0.0)
    return k.astype(np.float32)          # all 25 cells have d < 3, hence k > 0


KERNEL = _kernel()
KF = KERNEL.ravel()


def place_cover(surface, allowed, budget, spacing=3, pool=None):
    surface = np.asarray(surface)
    allowed = np.asarray(allowed, bool)
    if surface.shape != allowed.shape or surface.ndim != 2:
        raise ValueError("surface/placement grid mismatch")
    if not np.isfinite(surface).all() or np.any(surface < 0):
        raise ValueError("placement requires finite nonnegative values")
    if budget < 0 or spacing <= 0 or (pool is not None and pool <= 0):
        raise ValueError("invalid placement parameters")
    if pool is None:
        # 40 candidates per requested dot: each emitted dot blocks its 5x5
        # neighbourhood, so a fixed 400k pool starves the full-grid budget
        # (observed: 34,350/37,654 emitted).  Fold budgets (~10k) still get
        # the original 400k pool, so recorded holdout placements are unchanged.
        pool = max(400_000, 40 * int(budget))
    h, w = surface.shape
    p = np.where(allowed, surface, 0.0).astype(np.float32)
    gain0 = ndi.convolve(p, KERNEL, mode="constant")
    gain0[~allowed] = -1.0
    n_allowed = int(allowed.sum())
    k_pool = int(min(pool, n_allowed))
    if k_pool <= 0 or budget == 0:
        return np.zeros(surface.shape, bool), dict(
            requested=int(budget), emitted=0, spacing_px=spacing,
            exhausted=budget > 0, pool=0, expected_cover=0.0)
    flat_gain = gain0.ravel()
    if k_pool < flat_gain.size:
        cand = np.argpartition(flat_gain, flat_gain.size - k_pool)[-k_pool:]
    else:
        cand = np.arange(flat_gain.size)
    cand = cand[flat_gain[cand] > 0]
    heap = [(-float(flat_gain[i]), int(i)) for i in cand]
    heapq.heapify(heap)
    del gain0, flat_gain, cand

    # padded views make every 5x5 neighbourhood an in-bounds slice
    pp = np.pad(p, 2)
    cover = np.zeros((h + 4, w + 4), np.float32)
    blocked = np.ones((h + 4, w + 4), bool)
    blocked[2:-2, 2:-2] = ~allowed
    emitted = np.zeros(surface.shape, bool)
    total = 0.0
    n = 0

    def local_gain(py, px):
        c = cover[py - 2:py + 3, px - 2:px + 3].ravel()
        return float(np.dot(np.maximum(KF - c, 0.0), pp[py - 2:py + 3, px - 2:px + 3].ravel()))

    while heap and n < budget:
        neg_g, idx = heapq.heappop(heap)
        y, x = divmod(idx, w)
        py, px = y + 2, x + 2
        if blocked[py, px]:
            continue
        g = local_gain(py, px)
        if heap and g < -heap[0][0] - 1e-9:
            heapq.heappush(heap, (-g, idx))
            continue
        if g <= 0.0:
            break
        emitted[y, x] = True
        total += g
        n += 1
        sub = cover[py - 2:py + 3, px - 2:px + 3]
        np.maximum(sub, KERNEL, out=sub)
        blocked[py - 2:py + 3, px - 2:px + 3] = True   # d < 3 px exclusion (5x5)
    return emitted, dict(requested=int(budget), emitted=int(n), spacing_px=spacing,
                         exhausted=n < budget, pool=int(k_pool),
                         expected_cover=float(total))
