"""G79-CJX-DIR: cross-scale potential-field contact-junction statistic.

Registered 2026-10-22 as "G79-CJX"; renamed at merge time because a parallel
session merged a different lane with the same backlog nickname first
(measured non-duplicate: evidence/cjxdir/collision_measurement.json).

Preregistered in registry/preregistration_cjxdir.json (2026-10-22T15:36:01Z),
implementing research/hypotheses_e4a4422d.md priority 1.  Pure array
functions only; the experiment driver is scripts/run_cjxdir.py.  No catalogue
information is used anywhere in this module.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

SIGMAS = (1.0, 2.0, 4.0)
NEIGH_SIGMA = 2.0
BASE_SIGMA = 2.0


def fill_invalid(a: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, float]:
    """Median-fill invalid cells (documented gradient support, not data)."""
    a = np.asarray(a, dtype=np.float32)
    valid = np.asarray(valid, bool)
    if a.shape != valid.shape:
        raise ValueError("array/valid shape mismatch")
    if not valid.any():
        raise ValueError("no valid cells to fill from")
    med = float(np.median(a[valid]))
    return np.where(valid, a, med).astype(np.float32), med


def percentile_rank(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Footprint percentile rank in (0, 1] on ``mask``, exactly 0 outside.

    Ties receive the average rank (scipy rankdata 'average' semantics,
    implemented directly so the behaviour is pinned here).
    """
    a = np.asarray(a)
    mask = np.asarray(mask, bool)
    if a.shape != mask.shape:
        raise ValueError("array/mask shape mismatch")
    out = np.zeros(a.shape, np.float32)
    vals = a[mask].astype(np.float64)
    n = vals.size
    if n == 0:
        return out
    order = np.argsort(vals, kind="stable")
    sorted_vals = vals[order]
    ranks = np.empty(n, np.float64)
    # average ranks for ties
    starts = np.flatnonzero(np.r_[True, sorted_vals[1:] != sorted_vals[:-1], True])
    for lo, hi in zip(starts[:-1], starts[1:]):
        ranks[order[lo:hi]] = 0.5 * (lo + hi - 1) + 1.0
    out[mask] = (ranks / n).astype(np.float32)
    return out


def junction_at_scale(filled: np.ndarray, mask: np.ndarray, sigma: float,
                      neigh_sigma: float = NEIGH_SIGMA):
    """Edge-weighted director-dispersion junction statistic at one scale.

    Returns ``(J, smoothed_edge_magnitude)`` as float32 arrays where
    ``J = percentile_rank(<m>) * (1 - C)`` and ``C`` is the doubled-angle
    director coherence in a Gaussian neighbourhood.  A single straight
    contact has C ~ 1 (J ~ 0); a flat area has <m> ~ 0 (J ~ 0); several
    strong strikes meeting give C << 1 with large <m> (J large).
    The doubled-angle of the along-strike director differs from the
    doubled gradient angle by pi in both components, which leaves the
    coherence magnitude unchanged, so gradient angles are used directly.
    """
    f = ndi.gaussian_filter(np.asarray(filled, np.float32), sigma, mode="nearest")
    gy, gx = np.gradient(f)
    del f
    m = np.hypot(gx, gy).astype(np.float32)
    # m * cos(2phi) = (gx^2 - gy^2)/m ; m * sin(2phi) = 2*gx*gy/m  (0 when m == 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        wx = np.where(m > 0, (gx * gx - gy * gy) / np.where(m > 0, m, 1.0), 0.0).astype(np.float32)
        wy = np.where(m > 0, (2.0 * gx * gy) / np.where(m > 0, m, 1.0), 0.0).astype(np.float32)
    del gx, gy
    sx = ndi.gaussian_filter(wx, neigh_sigma, mode="nearest"); del wx
    sy = ndi.gaussian_filter(wy, neigh_sigma, mode="nearest"); del wy
    sm = ndi.gaussian_filter(m, neigh_sigma, mode="nearest"); del m
    coh = np.clip(np.hypot(sx, sy) / (sm + np.float32(1e-12)), 0.0, 1.0).astype(np.float32)
    del sx, sy
    j = (percentile_rank(sm, mask) * (np.float32(1.0) - coh)).astype(np.float32)
    del coh
    return j, sm


def geomean2(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    if a.shape != b.shape:
        raise ValueError("geomean shape mismatch")
    return np.sqrt(np.clip(a, 0, None) * np.clip(b, 0, None)).astype(np.float32)


def phase_randomized(filled: np.ndarray, seed: int) -> np.ndarray:
    """Power-spectrum-matched phase randomization (nuisance null).

    Random phases are applied to the rFFT half-spectrum; irfft2 rebuilds a
    real field with (up to the half-spectrum convention) the same periodogram
    magnitudes but destroyed phase alignment, so genuine multi-strike
    junctions - a phase phenomenon - cannot survive it.
    """
    x = np.asarray(filled, np.float64)
    x = x - x.mean()
    spec = np.fft.rfft2(x)
    rng = np.random.default_rng(seed)
    phases = rng.uniform(0.0, 2.0 * np.pi, size=spec.shape)
    phases[0, 0] = 0.0
    out = np.fft.irfft2(spec * np.exp(1j * phases), s=x.shape)
    return out.astype(np.float32)
