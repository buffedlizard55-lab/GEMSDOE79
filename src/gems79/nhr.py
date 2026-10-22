"""H79-NHR: nested hide-to-recover learning with a metric-native kernel target.

Lane paragraph (preregistered in registry/preregistration_nhr.json)
-------------------------------------------------------------------
A fault that is missing from a catalogue is, by construction, a fault that the
catalogue's mappers did not draw.  Instead of training a classifier to recognise
*mapped* fault pixels (which teaches the model to re-find the catalogue), we
simulate the discovery task itself: inside the catalogue that is visible to us
we repeatedly withhold whole 8-connected components (with a 3 px context
buffer), recompute every catalogue-derived feature from what remains, and train
a gradient-boosted regressor whose target is the official 300 m triangular
kernel credit ``k(d) = max(1 - d/3px, 0)`` towards the withheld component.  The
prediction is therefore an estimate of expected per-pixel kernel credit for an
*unmapped* fault, given label-independent geophysics, USGS 3DEP lidar scarp
morphometry and the geometry of the faults that ARE mapped.  Dots are placed
greedily on the predicted surface with 3 px Poisson spacing at a fixed budget.

Every catalogue-derived input is computed from the visible catalogue only; no
registry raster or prior submission is an input.  Nothing here is tuned on the
evaluation holdout.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CACHE = ROOT / ".cache" / "nhr"
STRUCT8 = np.ones((3, 3), bool)

TRAIN_BANDS = 19          # training_features.tif
LIDAR_BANDS = ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
               "downface_max", "upface_max", "cross_max", "relief", "coh100")
RAD_BANDS = ("K", "Th", "U", "TC")
EXT_BANDS = ("ThK", "UK", "UTh", "TMI_up150")
GEOMETRY_NAMES = ("log_dist_visible", "visible_density_s5", "visible_density_s20",
                  "log_dist_visible_tip", "lidar_strike_alignment",
                  "strike_field_coherence")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _robust(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """(x - median) / IQR on valid footprint cells; invalid -> NaN (HGB native)."""
    out = np.full(a.shape, np.nan, np.float32)
    v = a[valid]
    if v.size == 0:
        return out
    q25, q50, q75 = np.percentile(v, [25, 50, 75])
    scale = float(q75 - q25) or float(np.std(v)) or 1.0
    out[valid] = ((v - q50) / scale).astype(np.float32)
    return out


def build_static_stack(footprint: np.ndarray) -> tuple[np.ndarray, list[str], dict]:
    """Label-independent per-footprint-pixel features, cached as float16.

    Returns (matrix[n_fp, F], names, receipt).  Matrix rows follow
    ``np.flatnonzero(footprint)`` order.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "static_stack_f16.npy"
    meta_path = CACHE / "static_stack.json"
    if out.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return np.load(out, mmap_mode="r"), meta["names"], meta
    fp = np.asarray(footprint, bool)
    idx = np.flatnonzero(fp)
    cols: list[np.ndarray] = []
    names: list[str] = []
    inputs = {}

    def add(name, arr, valid):
        cols.append(_robust(arr, valid & fp).ravel()[idx].astype(np.float16))
        names.append(name)

    p = RAW / "training_features.tif"
    inputs["training_features.tif"] = _sha(p)
    with rasterio.open(p) as src:
        descr = src.descriptions
        for b in range(1, src.count + 1):
            a = src.read(b).astype(np.float32)
            valid = np.isfinite(a) & (a > -1e30)
            add("tf_" + descr[b - 1].split(" - ")[0], a, valid)
            short = descr[b - 1].split(" - ")[0]
            # multiscale edge/curvature transforms of the topographic, gravity and
            # magnetic potential fields (label-independent).
            if short in ("det_elev", "iso_grav_anom", "rtp"):
                filled = np.where(valid, a, np.nanmedian(np.where(valid, a, np.nan)))
                for s in ((1.0, 3.0) if short == "det_elev" else (2.0, 5.0)):
                    add(f"{short}_gradmag_s{s:g}",
                        ndi.gaussian_gradient_magnitude(filled, s), valid)
                    add(f"{short}_log_s{s:g}", ndi.gaussian_laplace(filled, s), valid)
                del filled
            del a, valid
    for fname, bands in (("lidar_scarp_features_u8.tif", LIDAR_BANDS),
                         ("geodawn_rad_u8.tif", RAD_BANDS),
                         ("geodawn_extensions_u8.tif", EXT_BANDS)):
        p = RAW / "external" / fname
        inputs[fname] = _sha(p)
        with rasterio.open(p) as src:
            descr = list(src.descriptions)
            for name in bands:
                a = src.read(descr.index(name) + 1).astype(np.float32)
                valid = a > 0          # 0 = no data in every u8 product
                add(name, a, valid)
                if fname.startswith("lidar") and name in ("step_max", "ex_max", "downface_max"):
                    # 500 m neighbourhood maximum: a scarp seen anywhere within
                    # one kernel diameter of the pixel.
                    mx = ndi.maximum_filter(np.where(valid, a, 0), size=5)
                    add(name + "_max5", mx, valid)
                del a, valid
    mat = np.stack(cols, axis=1)
    np.save(out, mat)
    meta = dict(names=names, n_footprint=int(idx.size), dtype="float16",
                normalisation="(x - median)/IQR over footprint; NaN where source invalid",
                inputs_sha256=inputs)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.load(out, mmap_mode="r"), names, meta


def read_lidar_orientation(footprint):
    """Lidar scarp strike (degrees, 0..180) and coherence; NaN where absent."""
    with rasterio.open(RAW / "external" / "lidar_scarp_features_u8.tif") as src:
        d = list(src.descriptions)
        s = src.read(d.index("strike") + 1).astype(np.float32)
        c = src.read(d.index("coh100") + 1).astype(np.float32)
    ok = (s > 0) & (c > 0) & footprint
    strike = np.where(ok, (s - 1) / 254.0 * 180.0, np.nan).astype(np.float32)
    coh = np.where(ok, (c - 1) / 254.0, np.nan).astype(np.float32)
    return strike, coh


def _endpoints(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.uint8)
    nb = ndi.convolve(m, np.ones((3, 3), np.uint8), mode="constant") - m
    return mask & (nb <= 1)


def geometry_features(visible: np.ndarray, footprint: np.ndarray,
                      lidar_strike: np.ndarray, lidar_coh: np.ndarray) -> dict:
    """Catalogue-geometry inputs computed from the VISIBLE catalogue only."""
    vis = np.asarray(visible, bool)
    d = ndi.distance_transform_edt(~vis).astype(np.float32)
    f = {"log_dist_visible": np.log1p(np.minimum(d, 200.0)).astype(np.float32)}
    vf = vis.astype(np.float32)
    f["visible_density_s5"] = ndi.gaussian_filter(vf, 5.0).astype(np.float32)
    f["visible_density_s20"] = ndi.gaussian_filter(vf, 20.0).astype(np.float32)
    tips = _endpoints(vis)
    dt = ndi.distance_transform_edt(~tips).astype(np.float32) if tips.any() else np.full(vis.shape, 200, np.float32)
    f["log_dist_visible_tip"] = np.log1p(np.minimum(dt, 200.0)).astype(np.float32)
    # Doubled-angle structure-tensor strike field of the visible catalogue,
    # diffused over ~2 km: the local orientation that mapped faults take.
    gy = ndi.sobel(vf, 0); gx = ndi.sobel(vf, 1)
    jxx = ndi.gaussian_filter(gx * gx, 20.0); jyy = ndi.gaussian_filter(gy * gy, 20.0)
    jxy = ndi.gaussian_filter(gx * gy, 20.0)
    tr = jxx + jyy + 1e-9
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / tr
    # gradient-normal angle (image coords) -> strike = normal + 90 deg; express as
    # compass-like 0..180 measured the same way the lidar product's 'strike' is
    # unknown, so we use only the *difference* of doubled angles, which is
    # invariant to a common rotation convention only if both use the same frame.
    # Both are derived in image row/col frame here: lidar strike is taken as given.
    theta_n = 0.5 * np.arctan2(2 * jxy, jxx - jyy)          # normal direction (rad)
    strike_vis = (np.degrees(theta_n) + 90.0) % 180.0
    ls = lidar_strike
    delta = np.radians(2.0 * (ls - strike_vis))
    align = np.where(np.isfinite(ls), np.cos(delta) * np.nan_to_num(lidar_coh), np.nan)
    f["lidar_strike_alignment"] = align.astype(np.float32)
    f["strike_field_coherence"] = coh.astype(np.float32)
    for k in f:
        f[k] = np.where(footprint, f[k], np.nan).astype(np.float32)
    return f


def nested_hide(context: np.ndarray, region: np.ndarray, rng, hide_frac=0.20, buffer_px=3):
    """Withhold whole components of the CONTEXT catalogue that lie inside region.

    Returns (hidden, remaining_visible).  Remaining visible excludes a buffer
    collar around the hidden components (as in the shared holdout split).
    """
    comp, n = ndi.label(context, STRUCT8)
    if n == 0:
        return np.zeros_like(context), context.copy()
    sizes = np.bincount(comp.ravel(), minlength=n + 1)
    inside = np.unique(comp[context & region])
    outside = np.unique(comp[context & ~region])
    elig = np.setdiff1d(inside[inside > 0], outside)
    perm = rng.permutation(elig)
    target = hide_frac * float((context & region).sum())
    k = int(np.searchsorted(np.cumsum(sizes[perm]), target)) + 1
    chosen = perm[:min(k, perm.size)]
    hidden = np.isin(comp, chosen) & context
    collar = ndi.distance_transform_edt(~hidden) <= buffer_px
    remaining = context & ~collar
    return hidden, remaining


def kernel_target(hidden: np.ndarray) -> np.ndarray:
    d = ndi.distance_transform_edt(~hidden)
    return np.maximum(1.0 - d / 3.0, 0.0).astype(np.float32)
