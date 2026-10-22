"""H79-ARC ridge-concordance feature additions (preregistered, label-independent).

Extends the cached H79-NHR static stack (`gems79.nhr.build_static_stack`)
with line-steered transforms of the same SHA-256-pinned inputs:

* line-coherent edge strength: gaussian gradient magnitude x structure-tensor
  coherence of det_elev / rtp / iso_grav_anom (a fault *trace* response, where
  the NHR stack only carried isotropic gradient magnitude / LoG);
* Hessian ridge anisotropy of det_elev and rtp;
* magnetic horizontal-gradient "worm" persistence across scales;
* lidar antislope asymmetry (uphill-facing minus downhill-facing step);
* structure-tensor coherence of the lidar step field.

No catalogue-derived quantity is used here. Catalogue geometry of any kind
(distance, density, tips) is deliberately absent from the whole lane; the only
catalogue inputs elsewhere are the two visible-catalogue strike-field terms.
Robust scaling and the u8-valid convention reuse `gems79.nhr` unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from . import nhr

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CACHE = ROOT / ".cache" / "arc"


def _filled(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    med = float(np.median(a[valid])) if valid.any() else 0.0
    return np.where(valid, a, med).astype(np.float32)


def _tensor_coherence(f: np.ndarray, sigma: float):
    """Gradient magnitude and structure-tensor coherence of a filled field."""
    gy = ndi.gaussian_filter(f, sigma, order=(1, 0))
    gx = ndi.gaussian_filter(f, sigma, order=(0, 1))
    gmag = np.hypot(gx, gy)
    jxx = ndi.gaussian_filter(gx * gx, sigma)
    jyy = ndi.gaussian_filter(gy * gy, sigma)
    jxy = ndi.gaussian_filter(gx * gy, sigma)
    trace = jxx + jyy
    diff = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy ** 2, 0.0))
    coh = diff / (trace + 1e-12)
    return gmag.astype(np.float32), coh.astype(np.float32)


def _hessian_anisotropy(f: np.ndarray, sigma: float) -> np.ndarray:
    """|lambda1 - lambda2| of the scale-normalised Hessian (ridge anisotropy)."""
    s2 = float(sigma) ** 2
    hyy = ndi.gaussian_filter(f, sigma, order=(2, 0)) * s2
    hxx = ndi.gaussian_filter(f, sigma, order=(0, 2)) * s2
    hxy = ndi.gaussian_filter(f, sigma, order=(1, 1)) * s2
    return np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy ** 2, 0.0)).astype(np.float32)


def build_extra_stack(footprint: np.ndarray) -> tuple[np.ndarray, list[str], dict]:
    """Footprint-row matrix (float16 cache) of the ARC transform features."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "extra_stack_f16.npy"
    meta_path = CACHE / "extra_stack.json"
    if out.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return np.load(out, mmap_mode="r"), meta["names"], meta
    fp = np.asarray(footprint, bool)
    idx = np.flatnonzero(fp)
    cols: list[np.ndarray] = []
    names: list[str] = []
    inputs = {}

    def add(name, arr, valid):
        cols.append(nhr._robust(arr, valid & fp).ravel()[idx].astype(np.float16))
        names.append(name)

    p = RAW / "training_features.tif"
    inputs["training_features.tif"] = nhr._sha(p)
    fields = {}
    with rasterio.open(p) as src:
        descr = [d.split(" - ")[0] for d in src.descriptions]
        for short in ("det_elev", "rtp", "iso_grav_anom"):
            a = src.read(descr.index(short) + 1).astype(np.float32)
            valid = np.isfinite(a) & (a > -1e30)
            fields[short] = (_filled(a, valid), valid)
            del a
    for short, sigmas in (("det_elev", (1.0, 2.0)), ("rtp", (1.0, 2.0, 4.0)),
                          ("iso_grav_anom", (1.0, 2.0, 4.0))):
        f, valid = fields[short]
        for s in sigmas:
            gmag, coh = _tensor_coherence(f, s)
            add(f"arc_{short}_lineedge_s{s:g}", gmag * coh, valid)
            del gmag, coh
    for short, sigmas in (("det_elev", (1.0, 2.0)), ("rtp", (2.0, 4.0))):
        f, valid = fields[short]
        for s in sigmas:
            add(f"arc_{short}_hessaniso_s{s:g}", _hessian_anisotropy(f, s), valid)
    # magnetic worm persistence: HG local maxima reinforced across scales
    f, valid = fields["rtp"]
    worm = np.zeros(f.shape, np.float32)
    for s in (1.0, 2.0, 4.0):
        g = ndi.gaussian_gradient_magnitude(f, s).astype(np.float32)
        worm += g * (g == ndi.maximum_filter(g, size=3))
        del g
    add("arc_rtp_worm_persist", worm / 3.0, valid)
    del worm, fields

    p = RAW / "external" / "lidar_scarp_features_u8.tif"
    inputs["lidar_scarp_features_u8.tif"] = nhr._sha(p)
    with rasterio.open(p) as src:
        d = list(src.descriptions)
        up = src.read(d.index("upface_max") + 1).astype(np.float32)
        down = src.read(d.index("downface_max") + 1).astype(np.float32)
        step = src.read(d.index("step_max") + 1).astype(np.float32)
        valid_band = src.read(d.index("valid") + 1) > 0
    add("arc_antislope_diff", up - down, valid_band)
    add("arc_antislope_ratio", up / (up + down + 1.0), valid_band & ((up + down) > 0))
    _, coh = _tensor_coherence(_filled(step, valid_band), 2.0)
    add("arc_step_coherence_s2", coh, valid_band)
    del up, down, step, coh

    mat = np.stack(cols, axis=1)
    np.save(out, mat)
    meta = dict(names=names, n_footprint=int(idx.size), dtype="float16",
                normalisation="(x - median)/IQR over footprint; NaN where source invalid",
                inputs_sha256=inputs)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.load(out, mmap_mode="r"), names, meta
