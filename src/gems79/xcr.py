"""G79-XCR: cross-catalogue recovery surface (label-blind structural model).

Two things here are new relative to every archived lane in this repository:

1. **A second, off-catalogue validation instrument.**  Every earlier lane scored
   only the QFDB/INGENIOUS *catalogue* hide-and-recover task.  The competition
   truth is the opposite population: expert faults *absent from* that catalogue.
   ``derived_sgmc_faults_100m_u8.tif`` is a fault set compiled from a different
   mapping campaign (State Geologic Map Compilation); 62,122 of its 83,593
   in-footprint pixels lie more than 3 px from the competition catalogue
   (measured, see ``evidence/xcr/sgmc_overlap.json``).  Recovering that
   off-catalogue population is a domain-matched proxy for the task, and it is
   *not* used to build any feature, so the instrument is independent of the
   model.

2. **Emission by exact marginal-DTI optimality** (``gems57.emit.greedy_allocate``)
   on the fitted surface instead of a hand-set dot budget with NMS spacing.
   The competition metric is asymmetric (alpha = 0.2, beta = 0.8), so the number
   of dots is a *decision*, not a constant.

No feature reads a prior prediction raster, the SGMC raster, or the SGMC-derived
columns; the frozen feature stack is the 19-band ``training_features.tif``.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

STRUCT3 = np.ones((3, 3), np.int8)

# Band indices are 0-based positions in training_features.tif (verified against
# the file's own band tags in evidence/xcr/band_verification.json).
BAND = {
    "mag_anom": 0, "rtp": 1, "tmi_hg": 2, "geod_2ndinv": 3,
    "iso_grav_slope": 4, "tc": 5, "geod_shear": 6, "geod_dilat": 7,
    "tmi_vg": 8, "deq": 9, "grav_vg": 10, "det_elev": 11,
    "iso_grav": 12, "tmi": 13, "bdepth": 14, "ieq": 15,
    "cond_surf": 16, "grav_hg": 17, "elev_slope": 18,
}

STATIC_NAMES = [
    "rtp_tilt_abs", "rtp_hgm_s4", "rtp_hgm_s12", "grav_hgm_s4", "grav_hgm_s12",
    "grav_tilt_abs", "bdepth_grad_s3", "cond_edge_s2", "elev_step_s2",
    "det_elev_relief_s5", "ieq_density", "strain2inv", "tmi_vg_abs",
    "grav_slope_abs",
]
GEOM_NAMES = ["log1p_d_visible", "dens_visible_15", "dens_visible_40",
              "d_visible_quantile"]


def _g(a: np.ndarray, sigma: float) -> np.ndarray:
    return ndi.gaussian_filter(a.astype(np.float32), sigma, mode="nearest")


def _grad_mag(a: np.ndarray, sigma: float) -> np.ndarray:
    s = _g(a, sigma)
    gy = ndi.sobel(s, 0, mode="nearest")
    gx = ndi.sobel(s, 1, mode="nearest")
    return np.hypot(gy, gx).astype(np.float32)


def _tilt_abs(a: np.ndarray, sigma: float) -> np.ndarray:
    """|tilt derivative| = |atan(VDR/HGM)|, amplitude-balanced edge detector.

    Miller & Singh (1994); Verduzco et al. (2004).  Bounded in [0, pi/2], so a
    single deep source cannot dominate the way a raw gradient magnitude does.
    """
    s = _g(a, sigma)
    gy = ndi.sobel(s, 0, mode="nearest")
    gx = ndi.sobel(s, 1, mode="nearest")
    hgm = np.hypot(gy, gx)
    vdr = _g(gy, sigma)  # vertical derivative proxy: derivative of the gradient
    tilt = np.arctan2(np.abs(vdr), hgm + 1e-6)
    return tilt.astype(np.float32)


def static_features(stack_path: Path, out: Path, bands: dict[str, int] | None = None) -> dict:
    """Compute the 14 label-blind physics channels once, as a float16 memmap.

    Float16 storage halves resident size; every consumer promotes to float32.
    NaNs from the source stack are filled with the channel median *for filtering
    only* and are marked unsupported, exactly like the inherited lanes.
    """
    import rasterio
    bands = bands or BAND
    with rasterio.open(stack_path) as src:
        h, w = src.height, src.width
        nodata = src.nodata
        arrays = {k: src.read(i + 1) for k, i in bands.items()}
    fp = np.isfinite(arrays["rtp"]) & np.isfinite(arrays["iso_grav"])
    if nodata is not None:
        for k in arrays:
            arrays[k] = np.where(arrays[k] <= -1e38, np.nan, arrays[k])
    out.parent.mkdir(parents=True, exist_ok=True)
    mat = np.lib.format.open_memmap(out, mode="w+", dtype=np.float16,
                                    shape=(len(STATIC_NAMES), h, w))
    for i, name in enumerate(STATIC_NAMES):
        if name == "rtp_tilt_abs":
            v = _tilt_abs(arrays["rtp"], 2.0)
        elif name == "rtp_hgm_s4":
            v = _grad_mag(arrays["rtp"], 4.0)
        elif name == "rtp_hgm_s12":
            v = _grad_mag(arrays["rtp"], 12.0)
        elif name == "grav_hgm_s4":
            v = _grad_mag(arrays["iso_grav"], 4.0)
        elif name == "grav_hgm_s12":
            v = _grad_mag(arrays["iso_grav"], 12.0)
        elif name == "grav_tilt_abs":
            v = _tilt_abs(arrays["iso_grav"], 2.0)
        elif name == "bdepth_grad_s3":
            v = _grad_mag(arrays["bdepth"], 3.0)
        elif name == "cond_edge_s2":
            v = _grad_mag(arrays["cond_surf"], 2.0)
        elif name == "elev_step_s2":
            v = _grad_mag(arrays["det_elev"], 2.0)
        elif name == "det_elev_relief_s5":
            m = _g(arrays["det_elev"], 5.0)
            v = np.sqrt(np.maximum(_g(arrays["det_elev"] ** 2, 5.0) - m * m, 0.0))
        elif name == "ieq_density":
            v = arrays["ieq"].astype(np.float32)
        elif name == "strain2inv":
            v = arrays["geod_2ndinv"].astype(np.float32)
        elif name == "tmi_vg_abs":
            v = np.abs(arrays["tmi_vg"]).astype(np.float32)
        elif name == "grav_slope_abs":
            v = np.abs(arrays["iso_grav_slope"]).astype(np.float32)
        else:  # pragma: no cover - guarded by the fixed name list
            raise KeyError(name)
        v = np.where(np.isfinite(v), v, np.nan).astype(np.float32)
        med = float(np.nanmedian(v)) if np.isfinite(v).any() else 0.0
        mat[i] = np.where(np.isfinite(v), v, med).astype(np.float16)
        del v
    mat.flush()
    del mat
    return {"path": str(out), "shape": [h, w], "names": STATIC_NAMES,
            "footprint_pixels": int(fp.sum()),
            "note": "label-blind static channels; SGMC never read here"}


def visible_geometry(visible: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Four catalogue-derived channels from the *visible* mask only."""
    vis = np.asarray(visible, bool) & np.asarray(footprint, bool)
    d = ndi.distance_transform_edt(~vis).astype(np.float32)
    dens15 = ndi.uniform_filter(vis.astype(np.float32), 15)
    dens40 = ndi.uniform_filter(vis.astype(np.float32), 40)
    v = d[footprint]
    # Rank transform: scale-free and fold-stable.
    order = np.argsort(v, kind="stable")
    q = np.empty_like(v)
    q[order] = np.linspace(0.0, 1.0, v.size, dtype=np.float32)
    dq = np.zeros(d.shape, np.float32)
    dq[footprint] = q
    return np.stack([np.log1p(d), dens15, dens40, dq]).astype(np.float32)


def credit_to(mask: np.ndarray, radius: float = 3.0) -> np.ndarray:
    """Official triangular kernel credit to ``mask`` (1 on the mask, 0 at 3 px)."""
    d = ndi.distance_transform_edt(~np.asarray(mask, bool))
    return np.maximum(1.0 - d / radius, 0.0).astype(np.float32)


def component_groups(visible: np.ndarray, groups: int = 4, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """Assign whole catalogue components to balanced inner groups."""
    comp, n = ndi.label(np.asarray(visible, bool), STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n + 1)
    rng = np.random.default_rng(seed)
    assign = np.zeros(n + 1, np.int8)
    loads = np.zeros(groups)
    for c in rng.permutation(n):
        if sizes[c + 1] == 0:
            continue
        g = int(np.argmin(loads))
        assign[c + 1] = g
        loads[g] += sizes[c + 1]
    return comp, assign


def oof_surface(x_get, visible: np.ndarray, footprint: np.ndarray, region: np.ndarray, *,
                groups: int = 4, seed: int = 0, max_iter: int = 80,
                learning_rate: float = 0.08) -> dict:
    """Out-of-fold structural surface: no pixel is predicted by a model that saw its fault.

    For inner group *g*, the model is trained on the other groups' kernel-credit
    target (pixels within 3 px of group *g* are withheld from training), and its
    prediction is kept only where the pixel's nearest catalogue component
    belongs to *g*.  That is the inner analogue of the outer holdout's
    component masking, so a surface fitted on the full catalogue is still a
    generalisation surface rather than a memorised one.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor

    vis = np.asarray(visible, bool) & np.asarray(footprint, bool)
    region = np.asarray(region, bool) & np.asarray(footprint, bool)
    comp, assign = component_groups(vis, groups, seed=7)
    _, (iy, ix) = ndi.distance_transform_edt(~vis, return_indices=True)
    pixel_group = assign[comp[iy, ix]]
    pixel_group[~np.asarray(footprint, bool)] = -1
    out = np.zeros(vis.shape, np.float32)
    fits = []
    for g in range(groups):
        own = np.isin(comp, np.flatnonzero(assign == g)) & vis
        keep = vis & ~own
        if not keep.any() or not own.any():
            continue
        target = credit_to(keep)
        near_own = ndi.distance_transform_edt(~own) <= 3
        sample = region & ~near_own
        # Predict everywhere this inner model owns; only *training* withholds the
        # 3 px collar.  Zeroing the collar (the earlier version) deleted the
        # exact band where the competition kernel has support.
        sel = region & (pixel_group == g)
        if not sel.any():
            continue
        surf = fit_predict(x_get, target, sample, sel, seed=seed + g,
                           max_iter=max_iter, learning_rate=learning_rate)
        out[sel] = surf[sel]
        fits.append({"group": g, "train_pixels": int(sample.sum()),
                     "predicted_pixels": int(sel.sum()),
                     "catalogue_pixels_in_group": int(own.sum())})
    covered = float((out[region] > 0).any())
    return {"surface": out, "pixel_group": pixel_group, "fits": fits,
            "region_covered_fraction": float((pixel_group[region] >= 0).mean()) if region.any() else 0.0,
            "note": "out-of-fold component-masked surface; zero where no inner model applies"}


def fit_predict(x_get, target, sample_mask, predict_mask, *, seed: int = 0,
                max_iter: int = 80, learning_rate: float = 0.08) -> np.ndarray:
    """HistGradientBoostingRegression of kernel credit; returns a full surface.

    ``x_get(flat_indices)`` returns a ``(channels, len(indices))`` float32 block,
    so a memmap-backed stack never has to be resident as one array.

    Sampling is deterministic: half the sampled pixels carry positive credit, so
    the fit sees the fault neighbourhoods rather than the basin background.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor

    t = np.asarray(target, np.float32)
    cand = np.flatnonzero(np.asarray(sample_mask, bool))
    pos = cand[t.ravel()[cand] > 0]
    neg = cand[t.ravel()[cand] <= 0]
    rng = np.random.default_rng(seed)
    n_pos = min(len(pos), 80_000)
    n_neg = min(len(neg), 80_000)
    if n_pos == 0 or n_neg == 0:
        raise ValueError("training sample needs both positive and background pixels")
    idx = np.r_[rng.choice(pos, n_pos, replace=False), rng.choice(neg, n_neg, replace=False)]
    model = HistGradientBoostingRegressor(
        loss="squared_error", max_iter=max_iter, learning_rate=learning_rate,
        max_leaf_nodes=31, min_samples_leaf=200, l2_regularization=1.0,
        early_stopping=False, random_state=seed)
    model.fit(np.asarray(x_get(idx), np.float32).T, t.ravel()[idx])
    out = np.zeros(t.shape, np.float32)
    pm = np.flatnonzero(np.asarray(predict_mask, bool))
    step = 400_000
    for start in range(0, pm.size, step):
        chunk = pm[start:start + step]
        out.ravel()[chunk] = model.predict(np.asarray(x_get(chunk), np.float32).T)
    out = np.clip(out, 0.0, 1.0)
    out[~np.asarray(predict_mask, bool)] = 0.0
    return out


def sgmc_offcatalogue(sgmc: np.ndarray, catalogue: np.ndarray, footprint: np.ndarray,
                      radius_px: float = 3.0) -> dict:
    """Fault pixels from the independent campaign that the catalogue misses.

    ``radius_px`` is the metric's own 300 m support: an SGMC pixel inside it is
    already represented by the catalogue, so only the rest is 'off-catalogue'.
    """
    s = np.asarray(sgmc, bool) & np.asarray(footprint, bool)
    c = np.asarray(catalogue, bool) & np.asarray(footprint, bool)
    d = ndi.distance_transform_edt(~c)
    off = s & (d > radius_px)
    comp, n = ndi.label(off, STRUCT3)
    sizes = np.bincount(comp.ravel())[1:]
    return {"sgmc_pixels": int(s.sum()), "catalogue_pixels": int(c.sum()),
            "offcatalogue_pixels": int(off.sum()),
            "offcatalogue_fraction_of_sgmc": float(off.sum() / max(1, s.sum())),
            "within_3px_of_catalogue": float((d[s] <= radius_px).mean()) if s.any() else 0.0,
            "offcatalogue_components": int(n),
            "components_ge_10px": int((sizes >= 10).sum()),
            "pixels_in_components_ge_10px": int(sizes[sizes >= 10].sum()),
            "off": off,
            "note": ("SGMC = State Geologic Map Compilation derivative already pinned in "
                     "data/raw/external; independent of the QFDB catalogue and never used "
                     "as a model feature")}


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=float) + "\n", encoding="utf-8")
