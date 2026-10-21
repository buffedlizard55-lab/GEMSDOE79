"""Mapper-continuity enhancement and constrained dot emission (lane H79-MCT).

Continuity surface
------------------
``S = sqrt(p * V01)`` where ``p`` is the pixel scarp likelihood and ``V01`` the Sato
bright-ridge (tubularity) response of ``p`` at sigma 1 and 2 px, scaled by its 99.9th
footprint percentile.  Isolated blobs of high ``p`` (hilltops, road cuts, terrace
corners) have no ridge support and are suppressed; collinear fragments that a mapper
would join into one trace are reinforced.  ``mix=0`` recovers ``p`` itself (the
pixel-detector baseline used as the paired control in the holdout).

Emission
--------
Binary dots (optimal for the Tversky-DTI metric, see research/why_02778.md) placed
greedily in decreasing ``S`` order with a 2.8 px minimum separation (the organizer's
300 m triangular kernel is zero beyond 3 px, so 3-px spacing covers a true trace
almost continuously while each dot's false-positive cost stays unit).  Dots are never
placed on or within 2 px of the known catalogue (organizer-confirmed: catalogue pixels
are masked, and the live lineage shows truth near the catalogue is rare).

Uniqueness quota (protocol rule 1): at most ``on_share`` of the dots may fall inside
the 3 px halo of the H19-5 line set that every >= 0.26 scorer re-dots; the remainder
is the best *off-halo* evidence by rank.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .features import tiled_sato


def continuity_surface(p: np.ndarray, footprint: np.ndarray, mix: float = 0.5) -> np.ndarray:
    p = np.where(footprint, np.clip(np.nan_to_num(p, nan=0.0), 0, 1), 0).astype(np.float32)
    if mix <= 0:
        return p
    v = tiled_sato(p, sigmas=(1.0, 2.0))
    hi = float(np.percentile(v[footprint], 99.9))
    v01 = np.clip(v / max(hi, 1e-9), 0, 1).astype(np.float32)
    s = np.power(p, 1.0 - mix) * np.power(v01, mix)
    return np.where(footprint, s, 0).astype(np.float32)


def _block_offsets(min_sep: float):
    r = int(np.ceil(min_sep))
    return [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if (dy * dy + dx * dx) ** 0.5 < min_sep]


def emit_dots(score: np.ndarray, allowed: np.ndarray, budget: int, *, min_sep: float = 2.8,
              quota_mask: np.ndarray | None = None, quota_share: float = 1.0,
              candidate_factor: int = 12) -> tuple[np.ndarray, dict]:
    """Greedy rank-ordered min-separation dots with an optional per-pool quota.

    ``quota_mask`` marks the pool (e.g. the H19-5 3-px halo) in which at most
    ``round(quota_share*budget)`` dots may be placed; the rest must come from outside.
    """
    H, W = score.shape
    key = np.where(allowed & (score > 0), score, -np.inf).astype(np.float32)
    flat = key.ravel()
    n_cand = int(min(flat.size, max(budget * candidate_factor, budget + 1000)))
    cand = np.argpartition(flat, -n_cand)[-n_cand:]
    cand = cand[np.argsort(-flat[cand], kind="stable")]
    cand = cand[np.isfinite(flat[cand])]
    blocked = np.zeros((H, W), bool)
    out = np.zeros((H, W), bool)
    offs = _block_offsets(min_sep)
    q = quota_mask.ravel() if quota_mask is not None else None
    q_cap = int(round(quota_share * budget)) if quota_mask is not None else budget
    n = n_q = skipped_q = 0
    for f in cand:
        if n >= budget:
            break
        y, x = divmod(int(f), W)
        if blocked[y, x]:
            continue
        in_q = bool(q[f]) if q is not None else False
        if in_q and n_q >= q_cap:
            skipped_q += 1
            continue
        out[y, x] = True
        n += 1
        n_q += in_q
        for dy, dx in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                blocked[yy, xx] = True
    info = {"dots": int(n), "budget": int(budget), "in_quota_pool": int(n_q),
            "quota_cap": int(q_cap), "candidates_scanned": int(len(cand)),
            "skipped_by_quota": int(skipped_q), "exhausted_candidates": bool(n < budget)}
    return out, info


def allowed_domain(footprint: np.ndarray, known: np.ndarray, exclusion_px: float = 2.0) -> np.ndarray:
    """Footprint cells strictly farther than ``exclusion_px`` (Euclidean) from any known fault."""
    d = ndi.distance_transform_edt(~known)
    return footprint & ~known & (d > exclusion_px)


def halo(mask: np.ndarray, radius_px: float = 3.0) -> np.ndarray:
    return ndi.distance_transform_edt(~mask) <= radius_px


def emit_dots_multi(score: np.ndarray, allowed: np.ndarray, budget: int, halo_bits: np.ndarray,
                    n_halos: int, cap_share: float = 0.68, *, min_sep: float = 2.8,
                    candidate_factor: int = 20) -> tuple[np.ndarray, dict]:
    """Greedy rank-ordered min-separation dots under one cap per prior raster.

    ``halo_bits`` is an int64 grid whose bit ``j`` marks the 3-px halo of prior ``j``
    (``j < n_halos <= 63``).  At most ``round(cap_share * budget)`` dots may fall inside any
    single prior's halo, which enforces the parallel-run duplicate rule (<= 70 % of dots within
    3 px of one registry raster's dots) *by construction* instead of post hoc.
    """
    H, W = score.shape
    key = np.where(allowed & (score > 0), score, -np.inf).astype(np.float32)
    flat = key.ravel()
    n_cand = int(min(flat.size, max(budget * candidate_factor, budget + 1000)))
    cand = np.argpartition(flat, -n_cand)[-n_cand:]
    cand = cand[np.argsort(-flat[cand], kind="stable")]
    cand = cand[np.isfinite(flat[cand])]
    bits = halo_bits.ravel()
    cap = int(round(cap_share * budget))
    counts = np.zeros(n_halos, np.int64)
    masks = np.array([1 << j for j in range(n_halos)], np.int64)
    blocked = np.zeros((H, W), bool)
    out = np.zeros((H, W), bool)
    offs = _block_offsets(min_sep)
    n = skipped = 0
    for f in cand:
        if n >= budget:
            break
        y, x = divmod(int(f), W)
        if blocked[y, x]:
            continue
        b = int(bits[f])
        if b:
            hit = (masks & b) != 0
            if (counts[hit] >= cap).any():
                skipped += 1
                continue
            counts[hit] += 1
        out[y, x] = True
        n += 1
        for dy, dx in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                blocked[yy, xx] = True
    info = {"dots": int(n), "budget": int(budget), "cap_per_prior": cap, "n_priors_capped": int(n_halos),
            "max_share_in_any_capped_halo": float(counts.max() / max(n, 1)) if n_halos else 0.0,
            "skipped_by_caps": int(skipped), "candidates_scanned": int(len(cand)),
            "exhausted_candidates": bool(n < budget)}
    return out, info


def halo_bits_from_rasters(paths, footprint: np.ndarray, radius_px: float = 3.0) -> tuple[np.ndarray, int]:
    """Bit-packed 3-px halos of prior rasters' positive supports (max 63)."""
    import rasterio
    paths = list(paths)
    if len(paths) > 63:
        raise ValueError("at most 63 priors can be bit-packed")
    bits = np.zeros(footprint.shape, np.int64)
    for j, p in enumerate(paths):
        with rasterio.open(p) as src:
            a = src.read(1)
        sup = np.isfinite(a) & (a > 0) & footprint
        bits |= (halo(sup, radius_px).astype(np.int64) << j)
    return bits, len(paths)
