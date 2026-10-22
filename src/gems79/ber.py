"""G79-BER new label-independent transforms and band utilities.

Preregistered in ``registry/preregistration_ber.json`` before any result.
Everything here is a transform of the SHA-256-pinned cached stacks
(``training_features.tif`` bands and the USGS 3DEP-derived lidar u8 product);
no registry raster, prior submission or catalogue-derived quantity enters
these features.  Catalogue geometry for the lane comes from
:mod:`gems79.nhr` (visible catalogue only), the static stack is the cached
``nhr.build_static_stack`` matrix, placement is ``gems79.placement`` and all
scoring/uniqueness/writing is the shared ``vendor/gems57`` code.

New transforms (fixed in the preregistration):

* FFT upward-continuation "worms" of RTP magnetics (band 2) and isostatic
  gravity (band 13): horizontal gradient magnitude and tilt angle at
  continuation heights 0/200/500/1000/2000 m, plus cross-height persistence
  (minimum footprint rank of HGM over heights).  A buried fault/contact edge
  keeps an HGM ridge that migrates systematically with height; a shallow
  noise edge dies by 500 m.
* 8-normal step dipoles (shared STEPCO transform) of log depth-to-basement
  (band 15) and surface conductivity (band 17) plus their sigma-3 gradient
  magnitudes: the buried intrabasin strand signature.
* Lidar antislope/dipole rank interactions from the u8 scarp bands:
  uphill-facing (antithetic) scarps vs downhill-facing shoreline/channel
  steps, crest-base curvature dipole, and coherence-weighted step.

The GeoDAWN flight-line spacing is coarser than the 100 m grid, so the worm
features are transforms of interpolated potential fields, not independent
100 m observations.  The leakage canary and the holdout decide their value.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import fft as spfft
from scipy import ndimage as ndi
from scipy.stats import rankdata

from .nhr import RAW, _robust
from .stepco import grad_mag, step_dipole

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "ber"

BANDS_PX = ((2, 5), (5, 10), (10, 20), (20, 50), (50, None))
TF_BAND = {"rtp": 2, "iso_grav_anom": 13, "depth_to_base_surf": 15, "cond_surf": 17}
WORM_HEIGHTS_PX = (0, 2, 5, 10, 20)
GEOMETRY_NAMES_BER = ("log_dist_visible_tip", "lidar_strike_alignment",
                      "strike_field_coherence")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def largest_remainder(total: int, counts) -> list[int]:
    """Allocate ``total`` proportional to ``counts`` (ties: earlier band)."""
    counts = np.asarray(counts, dtype=np.float64)
    if total < 0 or counts.ndim != 1 or (counts < 0).any() or counts.sum() <= 0:
        raise ValueError("invalid allocation inputs")
    raw = total * counts / counts.sum()
    base = np.floor(raw).astype(int)
    rem = int(total - base.sum())
    order = np.argsort(-(raw - base), kind="stable")
    for i in order[:rem]:
        base[i] += 1
    return [int(x) for x in base]


def band_ids(distance_px: np.ndarray) -> np.ndarray:
    """Band index per cell from distance-to-(visible)-catalogue in pixels.

    Bands are (lo, hi] with BANDS_PX bounds; cells at distance <= 2 px (and
    catalogue cells, distance 0) get -1: never eligible (measured H33 rule).
    """
    d = np.asarray(distance_px, dtype=np.float64)
    out = np.full(d.shape, -1, np.int8)
    for i, (lo, hi) in enumerate(BANDS_PX):
        m = d > lo if hi is None else (d > lo) & (d <= hi)
        out[m] = i
    return out


def _read_tf_band(band: int, footprint: np.ndarray):
    p = RAW / "training_features.tif"
    with rasterio.open(p) as src:
        a = src.read(band).astype(np.float32)
        nodata = src.nodata
    valid = footprint & np.isfinite(a) & (a > -1e30)
    if nodata is not None and np.isfinite(nodata):
        valid &= a != np.float32(nodata)
    if not valid.any():
        raise ValueError(f"training band {band} has no valid cells")
    filled = np.where(valid, a, np.median(a[valid])).astype(np.float32)
    return filled, valid


def _detrend_taper(field: np.ndarray, valid: np.ndarray, taper_px: int = 100) -> np.ndarray:
    """Remove a least-squares plane (fit on a deterministic subsample of valid
    cells) and cosine-taper the array edges for the FFT."""
    h, w = field.shape
    yy, xx = np.nonzero(valid)
    sel = np.arange(0, yy.size, max(1, yy.size // 200_000))
    A = np.stack([np.ones(sel.size), xx[sel] / w, yy[sel] / h], axis=1)
    coef, *_ = np.linalg.lstsq(A, field[yy[sel], xx[sel]].astype(np.float64), rcond=None)
    gy, gx = np.ogrid[:h, :w]
    plane = (coef[0] + coef[1] * gx / w + coef[2] * gy / h).astype(np.float32)
    out = field - plane
    ty = 0.5 - 0.5 * np.cos(np.pi * np.clip(np.minimum(np.arange(h), h - 1 - np.arange(h)) / taper_px, 0, 1))
    tx = 0.5 - 0.5 * np.cos(np.pi * np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / taper_px, 0, 1))
    out = out * np.outer(ty, tx).astype(np.float32)
    return out.astype(np.float32)


def _worms(field: np.ndarray, valid: np.ndarray, footprint: np.ndarray):
    """Upward-continuation HGM/tilt at WORM_HEIGHTS_PX + HGM rank persistence."""
    work = _detrend_taper(field, valid)
    h, w = work.shape
    F = spfft.rfft2(work, workers=2, overwrite_x=True)
    ky = (2 * np.pi * spfft.fftfreq(h, d=1.0)).astype(np.float32)
    kx = (2 * np.pi * spfft.rfftfreq(w, d=1.0)).astype(np.float32)
    kmod = np.sqrt(ky[:, None] ** 2 + kx[None, :] ** 2).astype(np.float32)
    ikx = (1j * kx[None, :]).astype(np.complex64)
    iky = (1j * ky[:, None]).astype(np.complex64)
    feats: dict[str, np.ndarray] = {}
    persist = np.full((h, w), np.inf, np.float32)
    fp_flat = footprint.ravel()
    for height in WORM_HEIGHTS_PX:
        Fh = F * np.exp(-kmod * float(height)) if height else F
        dx = spfft.irfft2(Fh * ikx, s=(h, w), workers=2)
        dy = spfft.irfft2(Fh * iky, s=(h, w), workers=2)
        dz = spfft.irfft2(Fh * kmod, s=(h, w), workers=2)
        hgm = np.hypot(dx, dy).astype(np.float32)
        del dx, dy
        feats[f"hgm_up{height}"] = hgm
        if height:
            feats[f"tilt_up{height}"] = np.arctan2(dz, hgm + 1e-12).astype(np.float32)
        del dz
        if height:
            r = np.full(h * w, np.float32(1.0), np.float32)
            v = hgm.ravel()[fp_flat].astype(np.float64)
            r[fp_flat] = ((rankdata(v, method="average") - 1) / max(v.size - 1, 1)).astype(np.float32)
            persist = np.minimum(persist, r.reshape(h, w))
            del r, v
    feats["hgm_persist"] = np.where(np.isfinite(persist), persist, 0.0).astype(np.float32)
    return feats


def _rank01(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.full(arr.shape, np.nan, np.float32)
    v = arr[valid].astype(np.float64)
    if v.size > 1 and np.ptp(v) > 0:
        out[valid] = ((rankdata(v, method="average") - 1) / (v.size - 1)).astype(np.float32)
    elif v.size:
        out[valid] = 0.5
    return out


def build_new_stack(footprint: np.ndarray):
    """Label-independent G79-BER features, cached as float16 rows like NHR's.

    Returns (matrix[n_fp, F] memmap, names, receipt).  Rows follow
    ``np.flatnonzero(footprint)`` order, matching ``nhr.build_static_stack``.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    out_path = CACHE / "new_stack_f16.npy"
    meta_path = CACHE / "new_stack.json"
    if out_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return np.load(out_path, mmap_mode="r"), meta["names"], meta
    fp = np.asarray(footprint, bool)
    idx = np.flatnonzero(fp)
    cols: list[np.ndarray] = []
    names: list[str] = []
    inputs = {}

    def add(name, arr, valid):
        cols.append(_robust(np.asarray(arr, np.float32), valid & fp).ravel()[idx].astype(np.float16))
        names.append(name)

    tf = RAW / "training_features.tif"
    inputs[tf.name] = _sha(tf)
    for short in ("rtp", "iso_grav_anom"):
        filled, valid = _read_tf_band(TF_BAND[short], fp)
        for sub, arr in _worms(filled, valid, fp).items():
            add(f"{short}_{sub}", arr, valid)
            del arr
        del filled, valid
    for short, band in (("log_depth", TF_BAND["depth_to_base_surf"]),
                        ("cond_surf", TF_BAND["cond_surf"])):
        filled, valid = _read_tf_band(band, fp)
        if short == "log_depth":
            filled = np.log1p(np.clip(filled, 0, None)).astype(np.float32)
        add(f"{short}_stepdipole", step_dipole(filled), valid)
        add(f"{short}_grad3", grad_mag(filled, 3.0), valid)
        del filled, valid

    lidar = RAW / "external" / "lidar_scarp_features_u8.tif"
    inputs[lidar.name] = _sha(lidar)
    wanted = ("upface_max", "downface_max", "lapneg_max", "lappos_max",
              "step_max", "cross_max", "coh100")
    ranks = {}
    with rasterio.open(lidar) as src:
        descr = list(src.descriptions)
        lidar_valid = src.read(descr.index("valid") + 1) > 0 if "valid" in descr else None
        raw = {}
        for name in wanted:
            raw[name] = src.read(descr.index(name) + 1).astype(np.float32)
    for name in wanted:
        v = (raw[name] > 0) & fp
        if lidar_valid is not None:
            v &= lidar_valid
        ranks[name] = _rank01(raw[name], v)
    both = np.isfinite(ranks["upface_max"]) & np.isfinite(ranks["downface_max"]) & fp
    add("lid_antislope", ranks["upface_max"] - ranks["downface_max"], both)
    add("lid_face_dom", np.fmax(ranks["upface_max"], ranks["downface_max"]), both)
    pair = np.isfinite(ranks["lapneg_max"]) & np.isfinite(ranks["lappos_max"]) & fp
    add("lid_dip_geo", np.sqrt(np.clip(ranks["lapneg_max"] * ranks["lappos_max"], 0, None)), pair)
    hi = np.fmax(ranks["lapneg_max"], ranks["lappos_max"])
    add("lid_dip_balance", np.fmin(ranks["lapneg_max"], ranks["lappos_max"]) / (hi + 1e-6), pair)
    sc = np.isfinite(ranks["step_max"]) & np.isfinite(ranks["cross_max"]) & fp
    add("lid_step_vs_cross", ranks["step_max"] - ranks["cross_max"], sc)
    cs = np.isfinite(ranks["coh100"]) & np.isfinite(ranks["step_max"]) & fp
    add("lid_coh_step", ranks["coh100"] * ranks["step_max"], cs)

    mat = np.stack(cols, axis=1)
    np.save(out_path, mat)
    meta = dict(names=names, n_footprint=int(idx.size), dtype="float16",
                normalisation="(x - median)/IQR over footprint-valid cells; NaN where source invalid",
                worm_heights_px=list(WORM_HEIGHTS_PX), taper_px=100,
                inputs_sha256=inputs)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.load(out_path, mmap_mode="r"), names, meta


def within_band_ranks(band_surfaces, band_id: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Combined [0,1] surface: percentile rank of each band's own surface."""
    out = np.zeros(band_id.shape, np.float32)
    for b, surf in enumerate(band_surfaces):
        m = allowed & (band_id == b)
        if not m.any():
            continue
        out[m] = _rank01(np.asarray(surf, np.float32), m)[m]
    return out


def provisional_topk(rank_surface: np.ndarray, band_id: np.ndarray,
                     allowed: np.ndarray, quotas) -> np.ndarray:
    """Surface-phase provisional dots: exact per-band top-quota cells (no spacing).

    Ranking is by descending rank-surface value with a stable row-major
    tie-break, matching the placement convention.
    """
    dots = np.zeros(rank_surface.shape, bool)
    flat_rank = rank_surface.ravel()
    flat_band = band_id.ravel()
    flat_allowed = allowed.ravel()
    flat_dots = dots.ravel()
    for b, quota in enumerate(quotas):
        if quota <= 0:
            continue
        cells = np.flatnonzero(flat_allowed & (flat_band == b) & (flat_rank > 0))
        if cells.size == 0:
            continue
        order = cells[np.argsort(-flat_rank[cells], kind="stable")]
        flat_dots[order[: int(quota)]] = True
    return dots
