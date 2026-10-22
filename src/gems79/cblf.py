"""CBLF -- Continuous Curvilinear Lineament Field (lane for session `6b4acb33`).

Why this lane exists
--------------------
Every archived lane in this repository emits a **point field** ("dots").  Under
the official Distance-Weighted Tversky Index the credit a truth pixel receives
is ``max_x p(x) * k(d(x, g))`` with ``k(d) = max(1 - d/3px, 0)``.  A point placed
uniformly inside the 3-px tube around a fault therefore earns, in expectation,

    E[k | inside the tube] = (2/9) * integral_0^3 r (1 - r/3) dr = 1/3,

and pays a false-positive cost ``0.2 * (1 - k)`` on the other two thirds.
A **1-px continuous curve** whose alignment error is sub-pixel along its length
earns ``k ~ 1`` on every one of its pixels and pays ~0.  At an identical pixel
budget a curve is therefore strictly more efficient whenever the predicted trace
is locally accurate -- which is what a thresholded, skeletonised structural
probability field provides.

Lane hypothesis (H-CBLF)
------------------------
Skeletonising a calibrated structural probability field yields a thin,
*continuous* network that dominates a point field of the same pixel budget on a
held-out fault set, because it removes the ``E[k] = 1/3`` placement penalty and
the duplicated mass that point fields spend on already-covered truth pixels.

Everything catalogue-derived is computed from the **visible** mask only; the
shared buffered whole-component LOQO split (`gems57.holdout`) supplies the folds
and the shared evaluator (`gems57.evaluate_holdout`) supplies the score.  No
private metric and no private writer are introduced here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Band descriptions verified from the metadata of data/raw/training_features.tif
# (``rasterio`` band descriptions; ``scripts/run_cblf.py describe`` prints them).
BAND_NAMES = (
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15",
    "iso_grav_anom_vg", "det_elev", "iso_grav_anom", "tmi",
    "depth_to_base_surf", "ieq_n100a15", "cond_surf", "iso_grav_anom_hg",
    "det_elev_slope",
)
SENTINEL = -3.0e38          # values <= SENTINEL are the float32 nodata sentinel
DET_ELEV_BAND = 12          # 1-based band index of ``det_elev``

BASE_FEATURES = tuple(f"band_{i:02d}_{n}" for i, n in enumerate(BAND_NAMES, start=1))
GEOMORPH_FEATURES = ("ridge_s2", "ridge_s5", "coherence_s3")
CONTEXT_FEATURES = ("log_dist_visible", "log_dens_visible")
FEATURE_NAMES = BASE_FEATURES + GEOMORPH_FEATURES + CONTEXT_FEATURES


# --------------------------------------------------------------------------- #
# raster helpers
# --------------------------------------------------------------------------- #
def _gauss(a: np.ndarray, sigma: float) -> np.ndarray:
    from scipy import ndimage as ndi
    return ndi.gaussian_filter(a, sigma, mode="nearest")


def curvature_response(dem: np.ndarray, sigma: float) -> np.ndarray:
    """Negative Laplacian of a Gaussian-smoothed surface (ridge/scarp detector).

    ``-laplacian`` is positive on topographic ridge crests and on the convex
    break at the base of a fault scarp, so it marks linear topographic breaks.
    """
    from scipy import ndimage as ndi
    sm = _gauss(np.asarray(dem, np.float64), sigma)
    return (-ndi.laplace(sm, mode="nearest")).astype(np.float32)


def structure_coherence(dem: np.ndarray, sigma: float) -> np.ndarray:
    """Orientation coherence ``(l1 - l2) / (l1 + l2)`` of the structure tensor.

    High values mark linear features (scarp bases, ridge crests) rather than
    isotropic texture, which is the property that distinguishes a fault trace
    from rough topography.
    """
    a = np.asarray(dem, np.float64)
    gy, gx = np.gradient(_gauss(a, 1.0))
    jxx = _gauss(gx * gx, sigma)
    jyy = _gauss(gy * gy, sigma)
    jxy = _gauss(gx * gy, sigma)
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    l1 = tr / 2.0 + disc
    l2 = tr / 2.0 - disc
    return ((l1 - l2) / np.maximum(l1 + l2, 1e-9)).astype(np.float32)


def robust_scale(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Median/IQR standardisation computed on the valid footprint only."""
    v = np.asarray(a, np.float32)[valid]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros_like(a, dtype=np.float32)
    med = float(np.median(v))
    q1, q3 = np.percentile(v, [25.0, 75.0])
    iqr = float(q3 - q1)
    if not np.isfinite(iqr) or iqr <= 0:
        iqr = float(np.std(v)) or 1.0
    return np.clip((np.asarray(a, np.float32) - med) / iqr, -5.0, 5.0).astype(np.float32)


def context_features(visible: np.ndarray) -> dict:
    """Catalogue *context* features derived only from a visible mask."""
    from scipy import ndimage as ndi
    dist = ndi.distance_transform_edt(~visible).astype(np.float32)
    dens = ndi.uniform_filter(visible.astype(np.float32), size=11) * 121.0
    return {
        "log_dist_visible": np.log1p(dist).astype(np.float32),
        "log_dens_visible": np.log1p(dens).astype(np.float32),
    }


def sentinel_to_nan(raw: np.ndarray) -> np.ndarray:
    out = np.asarray(raw, np.float32).copy()
    out[out <= SENTINEL] = np.nan
    return out


# --------------------------------------------------------------------------- #
# feature stack
# --------------------------------------------------------------------------- #
@dataclass
class FeatureStack:
    """Ordered feature planes; each plane is ``[H, W]`` float32.

    Planes are stored as a list so that a memory-mapped static cache can be
    combined with per-fold context planes without copying the whole cube.
    """
    planes: list
    names: tuple

    @property
    def shape(self) -> tuple:
        return tuple(self.planes[0].shape)

    def flat(self, i: int) -> np.ndarray:
        return np.asarray(self.planes[i]).reshape(-1)

    def at(self, name: str) -> np.ndarray:
        return np.asarray(self.planes[self.names.index(name)])

    def subset(self, keep: tuple) -> "FeatureStack":
        idx = [self.names.index(k) for k in keep]
        return FeatureStack(planes=[self.planes[i] for i in idx], names=tuple(keep))

    @staticmethod
    def from_cube(cube: np.ndarray, names: tuple) -> "FeatureStack":
        return FeatureStack(planes=[cube[i] for i in range(cube.shape[0])], names=names)


def build_stack(tif_path: Path, footprint: np.ndarray, visible: np.ndarray) -> FeatureStack:
    """Build the feature cube.

    ``visible`` is the catalogue mask the catalogue-derived features may look
    at.  For a holdout fold this is that fold's visible mask, so no withheld
    pixel leaks into any context feature.
    """
    import rasterio

    with rasterio.open(tif_path) as src:
        if src.count != len(BAND_NAMES):
            raise ValueError(f"expected {len(BAND_NAMES)} bands, found {src.count}")
        raw = sentinel_to_nan(src.read().astype(np.float32))

    feats = []
    for i, name in enumerate(BAND_NAMES):
        band = raw[i]
        if not np.isfinite(band[footprint]).all():
            vals = band[footprint]
            fill = float(np.nanmedian(vals)) if np.isfinite(vals).any() else 0.0
            band = np.where(np.isfinite(band), band, fill)
        feats.append(robust_scale(band, footprint))
    del raw

    dem = feats[DET_ELEV_BAND - 1]
    feats.append(robust_scale(curvature_response(dem, 2.0), footprint))
    feats.append(robust_scale(curvature_response(dem, 5.0), footprint))
    feats.append(robust_scale(structure_coherence(dem, 3.0), footprint))
    ctx = context_features(visible)
    feats.append(robust_scale(ctx["log_dist_visible"], footprint))
    feats.append(robust_scale(ctx["log_dens_visible"], footprint))

    return FeatureStack.from_cube(np.stack(feats).astype(np.float32), FEATURE_NAMES)


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
def sample_training_rows(train_area: np.ndarray, positives: np.ndarray, *,
                         seed: int = 0, pos_cap: int = 50_000,
                         neg_cap: int = 350_000):
    """Flat indices of positives and negatives drawn from ``train_area``."""
    rng = np.random.default_rng(seed)
    pos_idx = np.flatnonzero(positives.ravel())
    neg_all = train_area.ravel() & ~positives.ravel()
    neg_idx = np.flatnonzero(neg_all)
    if pos_idx.size > pos_cap:
        pos_idx = rng.choice(pos_idx, pos_cap, replace=False)
    if neg_idx.size > neg_cap:
        neg_idx = rng.choice(neg_idx, neg_cap, replace=False)
    idx = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate([np.ones(pos_idx.size, np.int8), np.zeros(neg_idx.size, np.int8)])
    order = rng.permutation(idx.size)
    return idx[order], y[order]


def fit_model(stack: FeatureStack, train_area: np.ndarray, positives: np.ndarray,
              *, seed: int = 0, pos_cap: int = 50_000, neg_cap: int = 350_000,
              max_iter: int = 200, learning_rate: float = 0.06):
    """Fit a gradient-boosted classifier on sampled pixels.

    ``train_area`` must already exclude every withheld pixel and its collar.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier

    idx, y = sample_training_rows(train_area, positives, seed=seed,
                                  pos_cap=pos_cap, neg_cap=neg_cap)
    X = np.stack([stack.flat(i)[idx] for i in range(len(stack.names))], axis=1)
    model = HistGradientBoostingClassifier(
        max_iter=max_iter, learning_rate=learning_rate, max_leaf_nodes=31,
        min_samples_leaf=80, l2_regularization=1.0, early_stopping=False,
        random_state=seed,
    )
    model.fit(X, y)
    return model, dict(n_train=int(idx.size), n_pos=int(y.sum()),
                       n_neg=int(idx.size - y.sum()))


def predict(model, stack: FeatureStack, row_chunk: int = 512) -> np.ndarray:
    """Full-grid ``P(fault)`` prediction in float32, computed in row chunks."""
    h, w = stack.shape
    out = np.empty((h, w), np.float32)
    for r0 in range(0, h, row_chunk):
        r1 = min(h, r0 + row_chunk)
        cols = np.arange(r0 * w, r1 * w)
        X = np.stack([stack.flat(i)[cols] for i in range(len(stack.names))], axis=1)
        out[r0:r1] = model.predict_proba(X)[:, 1].astype(np.float32).reshape(r1 - r0, -1)
        del X
    return out


# --------------------------------------------------------------------------- #
# emission
# --------------------------------------------------------------------------- #
def skeleton_lines(candidate: np.ndarray) -> np.ndarray:
    """1-px medial skeleton of a boolean candidate field (continuous curves)."""
    from skimage.morphology import skeletonize
    return skeletonize(np.asarray(candidate, bool))


def emit_curves(prob: np.ndarray, allowed: np.ndarray, *, budget: int,
                max_oversample: float = 6.0, iterations: int = 12) -> tuple:
    """Emit a continuous 1-px curve network with at most ``budget`` pixels.

    The candidate set is the top-``B`` allowed pixels by probability.  Because a
    skeleton is a subset of its candidate set, ``B = budget`` can never overshoot
    the budget, so ``B`` is grown until the skeleton fills at least 90 % of it.
    This avoids threshold bisection, which stalls on flat probability fields.
    """
    idx = np.flatnonzero(allowed.ravel())
    if idx.size == 0:
        raise ValueError("empty allowed domain")
    vals = np.asarray(prob, np.float32).ravel()[idx]
    order = np.argsort(-vals, kind="stable")
    best = None
    b = int(budget)
    limit = min(idx.size, int(max_oversample * budget))
    while b <= limit:
        sel = idx[order[:b]]
        cand = np.zeros(prob.size, bool)
        cand[sel] = True
        cand = cand.reshape(prob.shape)
        sk = skeleton_lines(cand)
        n = int(sk.sum())
        if n <= budget and (best is None or n > best[2]):
            best = (float(vals[order[b - 1]]), sk, n)
        if 0.90 * budget <= n <= budget:
            break
        b = int(b * 1.35) + 1
    if best is None:
        raise RuntimeError("could not reach the requested curve budget")
    tau, sk, n = best
    return sk, dict(tau=float(tau), pixels=int(n), budget=int(budget),
                    emitter="skeleton-curves")


def emit_dots(prob: np.ndarray, allowed: np.ndarray, *, budget: int) -> tuple:
    """Control arm: the same field emitted as ``budget`` isolated top-probability pixels."""
    idx = np.flatnonzero(allowed.ravel())
    if budget >= idx.size:
        raise ValueError("budget must be smaller than the allowed domain")
    vals = np.asarray(prob, np.float32).ravel()[idx]
    keep = idx[np.argpartition(vals, vals.size - budget)[vals.size - budget:]]
    out = np.zeros(prob.size, bool)
    out[keep] = True
    out = out.reshape(prob.shape)
    return out, dict(pixels=int(out.sum()), budget=int(budget), emitter="top-k-dots")


def dilate1(mask: np.ndarray) -> np.ndarray:
    """4-neighbour dilation (used only by the ``curve_plus`` sensitivity arm)."""
    from scipy import ndimage as ndi
    return ndi.binary_dilation(mask, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))
