"""G79-TDW: flight-line de-striped magnetic tilt-depth worm surface.

Catalogue-independent (geophysics only) so the same surface is valid in every
hide-and-recover fold; folds differ only by which catalogue pixels are masked
at emission/scoring time. No prior prediction raster is read.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi

def _clean(a, fp):
    a = np.asarray(a, dtype=np.float64)
    ok = fp & np.isfinite(a) & (np.abs(a) < 1e30)
    med = float(np.median(a[ok])) if ok.any() else 0.0
    return np.where(ok, a, med), med

def _rank01(a, fp):
    out = np.zeros(a.shape, dtype=np.float64)
    v = a[fp]
    order = np.argsort(v, kind="mergesort")
    r = np.empty(v.size, dtype=np.float64)
    r[order] = np.arange(v.size, dtype=np.float64) / max(v.size - 1, 1)
    out[fp] = r
    return out

def _destripe_fft(a, fp):
    """Attenuate E-W flight-line energy: near-zero fy, |fx|>5 cycles/image."""
    x = a - a[fp].mean()
    x = np.where(fp, x, 0.0)
    F = np.fft.rfft2(x)
    fy = np.fft.fftfreq(x.shape[0])[:, None]
    fx = np.fft.rfftfreq(x.shape[1])[None, :]
    notch = (np.abs(fy) < 0.002) & (np.abs(fx) > 0.005)
    F2 = F.copy(); F2[notch] *= 0.1
    y = np.fft.irfft2(F2, s=x.shape)
    return np.where(fp, y + a[fp].mean(), a)

def build_tdw_features(bands: dict, fp: np.ndarray) -> dict:
    """bands: rtp, grav, tmi, depth, elev as float arrays. Returns named features + surface."""
    rtp, _ = _clean(bands["rtp"], fp)
    grav, _ = _clean(bands["grav"], fp)
    depth, _ = _clean(bands["depth"], fp)
    rtp_ds = _destripe_fft(rtp, fp)
    # vertical-derivative proxy: residual after ~200 m (2 px) smoothing
    smooth = ndi.gaussian_filter(rtp_ds, 2.0, mode="nearest")
    dz = (rtp_ds - smooth) / 2.0
    gy, gx = np.gradient(rtp_ds)
    hgm = np.hypot(gx, gy) + 1e-12
    tilt = np.arctan2(dz, hgm)
    worm = np.exp(-((tilt / 0.35) ** 2)) * hgm
    # half-width depth proxy: broader HGM (900 m smooth) vs sharp HGM ratio -> px, x100 m
    hgm_broad = np.hypot(*np.gradient(ndi.gaussian_filter(rtp_ds, 9.0, mode="nearest"))) + 1e-12
    depth_proxy_m = 100.0 * np.clip(hgm / (hgm_broad + 1e-12), 0.5, 12.0)
    shallow = np.exp(-((np.clip(depth_proxy_m, 0, 1200) / 600.0) ** 2))
    ggy, ggx = np.gradient(grav)
    hgm_g = np.hypot(ggx, ggy) + 1e-12
    # unilateral-step concordance: alignment of mag & grav gradient directions in [0,1]
    dot = (gx * ggx + gy * ggy) / (hgm * hgm_g)
    concord = 0.5 + 0.5 * np.clip(dot, -1, 1)
    feats = {
        "tdw_destriped_hgm": _rank01(hgm, fp),
        "tdw_tilt_worm": _rank01(worm, fp),
        "tdw_shallow_gate": _rank01(shallow * hgm, fp),
        "tdw_grav_hgm": _rank01(hgm_g, fp),
        "tdw_concordance": _rank01(worm * concord, fp),
    }
    surf = (feats["tdw_tilt_worm"] * feats["tdw_shallow_gate"]
            * (0.5 + 0.5 * feats["tdw_concordance"]) * (0.5 + 0.5 * feats["tdw_grav_hgm"]))
    surf = np.where(fp, surf, 0.0)
    feats["surface"] = surf.astype(np.float32)
    return feats

def greedy_emit(surface, allowed, budget, min_sep_px=2.8, rng_seed=0):
    """Descending-surface greedy emission with Euclidean min separation."""
    surf = np.asarray(surface, dtype=np.float64)
    allowed = np.asarray(allowed, dtype=bool)
    cand = np.flatnonzero((surf > 0) & allowed)
    if cand.size == 0 or budget <= 0:
        return np.zeros(surf.shape, dtype=bool)
    order = cand[np.argsort(-surf.ravel()[cand], kind="mergesort")]
    # limit greedy loop cost: consider at most 8x budget candidates
    order = order[: max(budget * 8, budget)]
    blocked = np.zeros(surf.shape, dtype=bool)
    r = int(np.ceil(min_sep_px))
    yy, xx = np.mgrid[-r:r+1, -r:r+1]
    disk = (yy*yy + xx*xx) <= min_sep_px * min_sep_px
    h, w = surf.shape
    picked = []
    flat_blocked = blocked.ravel()
    for idx in order:
        if flat_blocked[idx]:
            continue
        picked.append(int(idx))
        if len(picked) >= budget:
            break
        y, x = divmod(int(idx), w)
        y0, y1 = max(0, y-r), min(h, y+r+1); x0, x1 = max(0, x-r), min(w, x+r+1)
        blocked[y0:y1, x0:x1] |= disk[(y0-y+r):(y0-y+r)+(y1-y0), (x0-x+r):(x0-x+r)+(x1-x0)]
    out = np.zeros(surf.shape, dtype=bool)
    out.ravel()[picked] = True
    return out
