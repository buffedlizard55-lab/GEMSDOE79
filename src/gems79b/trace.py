"""Emission (family live-validated operating point) + SDPT-C trace objects.

Emission: binary dots, greedy rank order, 2.8 px min separation, >2 px from
the catalogue, fixed budget. `emit_dots_multi` is the preregistered cap
contingency (per-prior halo cap), reused from the archived H79 code.

Trace reranking (SDPT-C): 8-connected components of {rank(p) >= 0.98 and
step_rank >= 0.5}; per component, PCA elongation e = 1 - lmin/lmax and size
factor s = clip((n-2)/20, 0, 1); segment_score = e * (0.35 + 0.65*s);
pixels in no component get 0.08. Output S = sqrt(rank01(p) * segment_score).
Constants are fixed a priori (preregistration), never tuned on the holdout.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata


def _block_offsets(min_sep):
    r = int(np.ceil(min_sep))
    return [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if (dy * dy + dx * dx) ** 0.5 < min_sep]


def emit_dots(score, allowed, budget, *, min_sep=2.8, candidate_factor=40):
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
    n = scanned = 0
    for f in cand:
        if n >= budget:
            break
        scanned += 1
        y, x = divmod(int(f), W)
        if blocked[y, x]:
            continue
        out[y, x] = True
        n += 1
        for dy, dx in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                blocked[yy, xx] = True
    return out, {"dots": int(n), "budget": int(budget), "candidates_scanned": int(scanned),
                 "candidate_pool": int(len(cand)), "exhausted_candidates": bool(n < budget)}


def emit_dots_multi(score, allowed, budget, halo_bits, n_halos, cap_share=0.68, *,
                    min_sep=2.8, candidate_factor=60):
    """Greedy emission with at most cap_share*budget dots in any one prior halo."""
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
    n = skipped = scanned = 0
    for f in cand:
        if n >= budget:
            break
        scanned += 1
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
    return out, {"dots": int(n), "budget": int(budget), "cap_per_prior": int(cap),
                 "n_priors_capped": int(n_halos),
                 "max_share_in_any_capped_halo": float(counts.max() / max(n, 1)) if n_halos else 0.0,
                 "skipped_by_caps": int(skipped), "candidates_scanned": int(scanned),
                 "candidate_pool": int(len(cand)), "exhausted_candidates": bool(n < budget)}


def emit_dots_caps(score, allowed, budget, halo_sampler, n_priors, cap_share=0.68, *,
                   min_sep=2.8, candidate_factor=60):
    """Greedy emission with at most cap_share*budget dots in any one prior halo.

    ``halo_sampler(cand_flat)`` returns a boolean (n_priors, len(cand_flat))
    membership matrix for the candidate pixels only, so any number of priors
    can be capped without bit-packing limits.
    """
    H, W = score.shape
    key = np.where(allowed & (score > 0), score, -np.inf).astype(np.float32)
    flat = key.ravel()
    n_cand = int(min(flat.size, max(budget * candidate_factor, budget + 1000)))
    cand = np.argpartition(flat, -n_cand)[-n_cand:]
    cand = cand[np.argsort(-flat[cand], kind="stable")]
    cand = cand[np.isfinite(flat[cand])]
    memb = np.asarray(halo_sampler(cand), dtype=bool)
    assert memb.shape == (n_priors, len(cand))
    cap = int(round(cap_share * budget))
    counts = np.zeros(n_priors, np.int64)
    blocked = np.zeros((H, W), bool)
    out = np.zeros((H, W), bool)
    offs = _block_offsets(min_sep)
    n = skipped = scanned = 0
    for i, f in enumerate(cand):
        if n >= budget:
            break
        scanned += 1
        y, x = divmod(int(f), W)
        if blocked[y, x]:
            continue
        hit = memb[:, i]
        if hit.any():
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
    return out, {"dots": int(n), "budget": int(budget), "cap_per_prior": int(cap),
                 "n_priors_capped": int(n_priors),
                 "max_share_in_any_capped_halo": float(counts.max() / max(n, 1)) if n_priors else 0.0,
                 "skipped_by_caps": int(skipped), "candidates_scanned": int(scanned),
                 "candidate_pool": int(len(cand)), "exhausted_candidates": bool(n < budget)}


def halo_sampler_from_files(paths, shape):
    """Build a candidate-membership sampler from prior raster files."""
    import rasterio

    def sample(cand_flat):
        memb = np.zeros((len(paths), len(cand_flat)), bool)
        for j, p in enumerate(paths):
            with rasterio.open(p) as src:
                a = src.read(1)
            sup = np.isfinite(a) & (a > 0)
            memb[j] = halo(sup, 3.0).ravel()[cand_flat]
        return memb

    return sample


def allowed_domain(footprint, known, exclusion_px=2.0):
    d = ndi.distance_transform_edt(~known)
    return footprint & ~known & (d > exclusion_px)


def halo(mask, radius_px=3.0):
    return ndi.distance_transform_edt(~mask) <= radius_px


def _rank01(x, mask):
    out = np.zeros(x.shape, np.float32)
    v = x[mask].astype(np.float64)
    if v.size > 1 and np.ptp(v) > 0:
        out[mask] = ((rankdata(v, method="average") - 1) / (v.size - 1)).astype(np.float32)
    return out


def trace_surface(p, step_rank, footprint):
    """SDPT-C object reranking of a pixel likelihood surface."""
    p = np.where(footprint, np.clip(np.nan_to_num(p, nan=0.0), 0, 1), 0).astype(np.float32)
    pr = _rank01(p, footprint)
    sr = np.where(np.isfinite(step_rank), step_rank, 1.0)  # no-lidar cells: no step veto
    seeds = footprint & (pr >= 0.98) & (sr >= 0.5)
    lab, nlab = ndi.label(seeds, structure=np.ones((3, 3), int))
    seg = np.full(p.shape, 0.08, np.float32)
    if nlab:
        ys, xs = np.nonzero(seeds)
        ids = lab[ys, xs]
        n = np.bincount(ids, minlength=nlab + 1).astype(np.float64)
        sy = np.bincount(ids, weights=ys, minlength=nlab + 1)
        sx = np.bincount(ids, weights=xs, minlength=nlab + 1)
        syy = np.bincount(ids, weights=ys * ys, minlength=nlab + 1)
        sxx = np.bincount(ids, weights=xs * xs, minlength=nlab + 1)
        sxy = np.bincount(ids, weights=ys * xs, minlength=nlab + 1)
        with np.errstate(invalid="ignore", divide="ignore"):
            my, mx = sy / n, sx / n
            cyy, cxx, cxy = syy / n - my ** 2, sxx / n - mx ** 2, sxy / n - my * mx
            tr = cyy + cxx
            disc = np.sqrt(np.clip(0.25 * (cyy - cxx) ** 2 + cxy ** 2, 0, None))
            lmax, lmin = 0.5 * tr + disc, np.clip(0.5 * tr - disc, 0, None)
            elong = np.where(lmax > 1e-12, 1.0 - lmin / np.where(lmax > 1e-12, lmax, 1.0), 0.0)
        size_f = np.clip((n - 2) / 20.0, 0.0, 1.0)
        score = (elong * (0.35 + 0.65 * size_f)).astype(np.float32)
        score[n < 3] = 0.08
        seg = np.where(lab > 0, score[np.clip(lab, 0, nlab)], 0.08).astype(np.float32)
    out = np.sqrt(np.clip(pr, 0, 1) * seg)
    return np.where(footprint, out, 0).astype(np.float32), {
        "seed_pixels": int(seeds.sum()), "components": int(nlab)}
