"""G79-MFX: catalogue-template matched filtering (learned fault-signature transfer).

Idea
----
Every fault that *is* in the USGS/INGENIOUS catalogue gives us a labelled example of
what a fault looks like in the drilled 19-band geophysical stack.  This module cuts
small (15x15 px = 1.5 x 1.5 km) multi-channel templates **from visible catalogue
pixels only**, keeps a de-duplicated bank of them, and transfers them over the whole
study area with normalized cross-correlation (NCC, i.e. a matched filter).  A strand
that was never mapped is then detected by its own texture, not by how far it sits
from a neighbouring mapped trace.

That is the difference from every lane already in this repository: pointwise
gradient-boosting lanes (H79-NHR, G79-CSKD, G79-DFSD, G79-CSMD) score a pixel from
its own feature vector; analytic-signal lanes (H78-MPC) use phase congruency with no
learned template; geometry lanes (G79-TIPSTEP, G79-TDW) hand-build the search
geometry.  Here the *shape* of the fault signature is learned non-parametrically
from the catalogue and matched convolutionally.

Nothing in this module reads a label raster, the hidden truth, or any file outside
``registry/data_manifest.json``.  Every catalogue-derived quantity is a function of
the ``visible`` mask it is handed, so hide-and-recover folds cannot leak.

Memory discipline
-----------------
The sandbox has 3 GB RAM and 2 cores.  Channels are float32, temporaries are freed
explicitly, and the FFT denominateur is accumulated band by band rather than
materialised for all bands at once (see ``ncc_score``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.signal import fftconvolve

NODATA_CUT = -1.0e30

# 1-based band numbers of data/raw/training_features.tif (verified from the file's
# own band descriptions, not from memory):
#   2  Reduced to pole magnetic data
#   3  TMI horizontal gradient
#   6  Tilt angle / total curvature (magnetic edge detector)
#   12 Detrended elevation
#   13 Isostatic gravity anomaly
#   15 Depth to basement surface
#   17 Conductivity surface
#   19 Detrended elevation slope
MODEL_BANDS: tuple[int, ...] = (2, 3, 6, 12, 13, 15, 17, 19)
# Templates are cut from three physically complementary channels only: a magnetic
# gradient texture, a density (gravity) texture and a topographic-slope texture.
TEMPLATE_BANDS: tuple[int, ...] = (2, 13, 19)

TEMPLATE_SIZE = 15
SECOND_SCALE_SIZE = 21
N_TEMPLATES = 32
DEDUP_CORR = 0.70


@dataclass
class ChannelStack:
    """Standardized float32 channels plus the finite-coverage mask they share."""

    data: dict[int, np.ndarray] = field(default_factory=dict)
    footprint: np.ndarray | None = None

    def __getitem__(self, band: int) -> np.ndarray:
        return self.data[band]


def _standardize(a: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Robust z-score over the footprint; nodata becomes NaN (never 0 silently)."""
    a = a.astype(np.float32, copy=True)
    a[a < NODATA_CUT] = np.nan
    vals = a[footprint & np.isfinite(a)]
    if vals.size < 1000:
        raise ValueError("band has too few finite footprint cells to standardize")
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826
    if not np.isfinite(mad) or mad <= 0:
        mad = float(np.std(vals)) or 1.0
    return (a - med) / mad


def load_channels(path: Path, footprint: np.ndarray,
                  bands: tuple[int, ...] = MODEL_BANDS) -> ChannelStack:
    """Read the requested bands of the drilled feature stack, robustly standardized."""
    out: dict[int, np.ndarray] = {}
    with rasterio.open(path) as src:
        available = src.count
        for b in bands:
            if not 1 <= b <= available:
                raise ValueError(f"band {b} not present in {path} (has {available})")
            out[b] = _standardize(src.read(b), footprint)
    return ChannelStack(data=out, footprint=np.asarray(footprint, bool))


def coverage(chan: ChannelStack, sigma: float = 7.0) -> np.ndarray:
    """Smoothed fraction of template channels that are finite in the neighbourhood."""
    cover = np.zeros(chan.footprint.shape, np.float32)
    for b in TEMPLATE_BANDS:
        cover += np.isfinite(chan[b]).astype(np.float32)
    cover /= float(len(TEMPLATE_BANDS))
    return ndi.gaussian_filter(cover, sigma).astype(np.float32)


def _filled(a: np.ndarray) -> np.ndarray:
    """NaN -> 0 after standardization (i.e. the band median), copying only once."""
    out = np.array(a, dtype=np.float32, copy=True)
    out[~np.isfinite(out)] = 0.0
    return out


def template_bank(chan: ChannelStack, visible: np.ndarray, *, count: int = N_TEMPLATES,
                  size: int = TEMPLATE_SIZE, dedup: float = DEDUP_CORR,
                  candidates: int = 800, seed: int = 79) -> np.ndarray:
    """Zero-mean, unit-norm multi-channel templates cut from **visible** faults.

    Returns an array of shape ``(K, C, size, size)``.  Templates come only from the
    mask handed in, so a hide-and-recover fold cannot leak a withheld strand into
    the filter bank.
    """
    visible = np.asarray(visible, bool)
    bands = [_filled(chan[b]) for b in TEMPLATE_BANDS]
    finite = np.ones(visible.shape, bool)
    for b in TEMPLATE_BANDS:
        finite &= np.isfinite(chan[b])
    centres = np.argwhere(visible & finite)
    if centres.shape[0] < count * 5:
        raise ValueError("not enough visible catalogue pixels to cut templates")
    rng = np.random.default_rng(seed)
    take = rng.choice(centres.shape[0], size=min(candidates, centres.shape[0]),
                      replace=False)
    r = size // 2
    H, W = visible.shape
    raw: list[np.ndarray] = []
    for k in take:
        y, x = centres[k]
        if not (r <= y < H - r and r <= x < W - r):
            continue
        patch = np.stack([b[y - r:y + r + 1, x - r:x + r + 1] for b in bands])
        v = patch.ravel().astype(np.float64)
        v -= v.mean()
        n = np.linalg.norm(v)
        if not np.isfinite(n) or n <= 1e-8:
            continue
        raw.append((v / n).reshape(patch.shape).astype(np.float32))
        if len(raw) >= 4 * count:
            break
    if len(raw) < count:
        raise ValueError(f"only {len(raw)} usable template candidates")
    # Greedy de-duplication on the flattened correlation of the whole patch vector:
    # keep a candidate only if it is less than ``dedup`` correlated with every
    # template already accepted, so the bank spans distinct signature shapes.
    flat = np.stack([t.ravel() for t in raw]).astype(np.float64)
    keep: list[int] = [0]
    corr = np.abs(flat @ flat[0])
    for i in range(1, flat.shape[0]):
        if corr[i] < dedup:
            keep.append(i)
            corr = np.maximum(corr, np.abs(flat @ flat[i]))
            if len(keep) >= count:
                break
    return np.stack([raw[i] for i in keep[:count]])


def ncc_score(chan: ChannelStack, templates: np.ndarray, *, size: int,
              footprint: np.ndarray) -> np.ndarray:
    """Max-over-templates normalized cross-correlation of the channel patch.

    ``NCC(x) = max_t  sum_c <patch_c(x), t_c> / ||patch(x)||``.  Because every
    template is zero-mean and unit-norm, the numerator is the matched-filter
    response and the denominator makes the score invariant to local amplitude
    (a dim magnetic texture scores like a bright one).
    """
    footprint = np.asarray(footprint, bool)
    bands = [_filled(chan[b]) for b in TEMPLATE_BANDS]
    ones = np.ones((size, size), np.float32)
    den = np.zeros(footprint.shape, np.float32)
    for a in bands:
        den += fftconvolve(a * a, ones, mode="same")
    np.sqrt(np.maximum(den, np.float32(1e-6)), out=den)
    best = np.full(footprint.shape, -1.0, np.float32)
    num = np.zeros(footprint.shape, np.float32)
    for t in templates:
        num.fill(0.0)
        for c, a in enumerate(bands):
            num += fftconvolve(a, np.ascontiguousarray(t[c, ::-1, ::-1]),
                               mode="same")
        np.maximum(best, num / den, out=best)
    best[~footprint] = np.nan
    return best


def structure_coherence(chan: ChannelStack, band: int = 2,
                        inner: float = 1.0, outer: float = 3.0) -> np.ndarray:
    """Structure-tensor coherence in [0,1]; high on lineaments, low on blobs."""
    a = _filled(chan[band])
    s = ndi.gaussian_filter(a, inner)
    gy, gx = np.gradient(s)
    jxx = ndi.gaussian_filter(gx * gx, outer)
    jyy = ndi.gaussian_filter(gy * gy, outer)
    jxy = ndi.gaussian_filter(gx * gy, outer)
    tr = jxx + jyy
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    coh = np.where(tr > 1e-6, disc / np.maximum(tr, 1e-6), 0.0)
    return coh.astype(np.float32)


def catalogue_geometry(visible: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fold-derived distance to the visible catalogue (px) and its local density."""
    visible = np.asarray(visible, bool)
    dist = ndi.distance_transform_edt(~visible).astype(np.float32)
    dens = ndi.gaussian_filter(visible.astype(np.float32), 5.0).astype(np.float32)
    return dist, dens


def feature_matrix(channels: dict[str, np.ndarray]) -> tuple[np.ndarray, list[str]]:
    """Stack named channels into a (n_pixels, n_features) float32 design matrix."""
    names = list(channels)
    shape = channels[names[0]].shape
    X = np.empty((shape[0] * shape[1], len(names)), np.float32)
    for j, n in enumerate(names):
        a = channels[n]
        if a.shape != shape:
            raise ValueError("channel shape mismatch")
        col = np.asarray(a, np.float32).ravel()
        col[~np.isfinite(col)] = 0.0
        X[:, j] = col
    return X, names


def build_channels(chan: ChannelStack, visible: np.ndarray, *, footprint: np.ndarray,
                   ncc_small: np.ndarray, ncc_big: np.ndarray, coh: np.ndarray,
                   include_catalogue_geometry: bool = True) -> dict[str, np.ndarray]:
    """The pointwise model channels used by the fold-wise LightGBM."""
    ch: dict[str, np.ndarray] = {}
    for b in MODEL_BANDS:
        ch[f"band{b}"] = chan[b]
    ch["ncc15"] = ncc_small
    ch["ncc21"] = ncc_big
    ch["coherence"] = coh
    ch["cover"] = coverage(chan)
    if include_catalogue_geometry:
        dist, dens = catalogue_geometry(visible)
        ch["dist_visible_px"] = np.minimum(dist, 40.0)
        ch["catalogue_density"] = dens
    return ch


def prior_correct(p: np.ndarray, sample_pi: float, true_pi: float) -> np.ndarray:
    """Map a class-balanced model probability onto the population prior."""
    p = np.clip(np.asarray(p, np.float64), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p))
    logit += np.log(true_pi / (1 - true_pi)) - np.log(sample_pi / (1 - sample_pi))
    return (1.0 / (1.0 + np.exp(-logit))).astype(np.float32)
