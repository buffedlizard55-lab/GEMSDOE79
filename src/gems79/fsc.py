"""G79-FSC: Fabric-Steered Concordance (registry/preregistration_g79_fsc.json).

All arrays are on the competition grid (3730 x 3292, EPSG:32611, 100 m).  Feature
matrices are stored *flattened over the footprint* to keep resident memory low on
small machines.  Catalogue-derived features are always computed from the mask the
caller passes in (outer-visible, inner-visible or full catalogue) -- never from the
withheld truth.

Orientation convention (image coordinates, x = column, y = row):
``phi`` is the dominant GRADIENT direction of a structure tensor, i.e. the normal to
the linear features it describes.  Orientation is carried as the doubled-angle pair
(cos 2phi, sin 2phi) so 0 and 180 degrees are the same direction.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

EPS = 1e-12

STACK_NAMES = ['mag_anom', 'rtp', 'tmi_hg', 'geod_2ndinv', 'iso_grav_anom_slope', 'tc',
               'geod_shearrate', 'geod_dilaterate', 'tmi_vg', 'deq_n100a15', 'iso_grav_anom_vg',
               'det_elev', 'iso_grav_anom', 'tmi', 'depth_to_base_surf', 'ieq_n100a15',
               'cond_surf', 'iso_grav_anom_hg', 'det_elev_slope']
LIDAR_NAMES = ['ex_max', 'ex_mean', 'step_max', 'lapneg_max', 'lappos_max', 'downface_max',
               'upface_max', 'cross_max', 'relief', 'coh100', 'strike', 'valid']
RAD_NAMES = ['rad_K', 'rad_Th', 'rad_U', 'rad_TC', 'rad_ThK', 'rad_UK', 'rad_UTh', 'tmi_up150']
EDGE_SOURCES = ('topo', 'grav', 'mag', 'lidar')
GEOMETRY_NAMES = ['log_d_vis', 'log_d_end', 'cat_dens_10', 'cat_dens_30',
                  'fab_c2', 'fab_s2', 'fab_coh', 'fab_logE']
CONCORDANCE_NAMES = [f'conc_{s}' for s in EDGE_SOURCES]


def fill_nearest(a: np.ndarray) -> np.ndarray:
    """Replace NaN by the nearest finite value (only used to compute derivatives)."""
    bad = ~np.isfinite(a)
    if not bad.any():
        return a.astype(np.float32, copy=False)
    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
    out = a[tuple(idx)].astype(np.float32)
    del idx
    return out


def structure_tensor(a: np.ndarray, sigma_d: float, sigma_i: float):
    """Return (cos2phi, sin2phi, coherence, energy) of the gradient structure tensor."""
    a = a.astype(np.float32, copy=False)
    gx = ndi.gaussian_filter(a, sigma_d, order=(0, 1))
    gy = ndi.gaussian_filter(a, sigma_d, order=(1, 0))
    jxx = ndi.gaussian_filter(gx * gx, sigma_i)
    jyy = ndi.gaussian_filter(gy * gy, sigma_i)
    jxy = ndi.gaussian_filter(gx * gy, sigma_i)
    del gx, gy
    diff = jxx - jyy
    lam = np.sqrt(diff * diff + 4.0 * jxy * jxy)
    energy = jxx + jyy
    c2 = np.where(lam > EPS, diff / np.maximum(lam, EPS), 0.0).astype(np.float32)
    s2 = np.where(lam > EPS, 2.0 * jxy / np.maximum(lam, EPS), 0.0).astype(np.float32)
    coh = (lam / (energy + EPS)).astype(np.float32)
    return c2, s2, coh, energy.astype(np.float32)


def hessian_ridge(a: np.ndarray, sigma: float) -> np.ndarray:
    """Signed largest-magnitude Hessian eigenvalue (scale-normalised by sigma^2)."""
    hxx = ndi.gaussian_filter(a, sigma, order=(0, 2))
    hyy = ndi.gaussian_filter(a, sigma, order=(2, 0))
    hxy = ndi.gaussian_filter(a, sigma, order=(1, 1))
    tr = 0.5 * (hxx + hyy)
    disc = np.sqrt(0.25 * (hxx - hyy) ** 2 + hxy * hxy)
    l1, l2 = tr + disc, tr - disc
    return (np.where(np.abs(l1) >= np.abs(l2), l1, l2) * sigma * sigma).astype(np.float32)


def concordance(c2e, s2e, cohe, c2f, s2f, cohf):
    """coh_edge * coh_fabric * cos^2(phi_edge - phi_fabric) in doubled-angle form."""
    cos2 = 0.5 * (1.0 + c2e * c2f + s2e * s2f)
    return (cohe * cohf * cos2).astype(np.float32)


def endpoints(mask: np.ndarray) -> np.ndarray:
    m = np.asarray(mask, bool)
    nb = ndi.convolve(m.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - m
    return m & (nb == 1)


def geometry_features(visible: np.ndarray, footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Visible-catalogue geometry and fabric, flattened over the footprint."""
    vis = np.asarray(visible, bool)
    fp = np.asarray(footprint, bool)
    out = {}
    d = ndi.distance_transform_edt(~vis).astype(np.float32)
    out['log_d_vis'] = np.log1p(np.minimum(d, 400.0))[fp]
    del d
    ends = endpoints(vis)
    d = ndi.distance_transform_edt(~ends).astype(np.float32) if ends.any() else np.full(vis.shape, 400, np.float32)
    out['log_d_end'] = np.log1p(np.minimum(d, 400.0))[fp]
    del d, ends
    vf = vis.astype(np.float32)
    out['cat_dens_10'] = ndi.gaussian_filter(vf, 10)[fp]
    out['cat_dens_30'] = ndi.gaussian_filter(vf, 30)[fp]
    c2, s2, coh, e = structure_tensor(vf, 1.0, 20.0)
    out['fab_c2'], out['fab_s2'], out['fab_coh'] = c2[fp], s2[fp], coh[fp]
    out['fab_logE'] = np.log10(e[fp] + 1e-6)
    del c2, s2, coh, e, vf
    return {k: v.astype(np.float32) for k, v in out.items()}


def concordance_features(static_cols: dict[str, np.ndarray], geom: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    out = {}
    for s in EDGE_SOURCES:
        out[f'conc_{s}'] = concordance(static_cols[f'{s}_c2'], static_cols[f'{s}_s2'], static_cols[f'{s}_coh'],
                                       geom['fab_c2'], geom['fab_s2'], geom['fab_coh'])
    return out


# ----------------------------------------------------------------------------- placement

def fabric_normal_nms(prob: np.ndarray, phi_c2: np.ndarray, phi_s2: np.ndarray,
                      allowed: np.ndarray, radii=(1, 2)) -> np.ndarray:
    """Keep pixels that are maxima of ``prob`` along the steering normal direction.

    ``phi_c2, phi_s2`` give the doubled-angle normal direction per pixel (full grid).
    Neighbours are sampled by nearest-pixel rounding at +-r along that normal.
    """
    h, w = prob.shape
    phi = 0.5 * np.arctan2(phi_s2, phi_c2)
    ux, uy = np.cos(phi), np.sin(phi)
    yy, xx = np.nonzero(allowed & (prob > 0))
    v = prob[yy, xx]
    keep = np.ones(v.size, bool)
    uxs, uys = ux[yy, xx], uy[yy, xx]
    for r in radii:
        for sgn in (1, -1):
            ny = np.clip(np.rint(yy + sgn * r * uys).astype(np.int64), 0, h - 1)
            nx = np.clip(np.rint(xx + sgn * r * uxs).astype(np.int64), 0, w - 1)
            keep &= v >= prob[ny, nx]
    out = np.zeros(prob.shape, bool)
    out[yy[keep], xx[keep]] = True
    return out


def greedy_spaced_order(prob: np.ndarray, candidates: np.ndarray, spacing: float, kmax: int):
    """Indices (y, x) of up to ``kmax`` candidates in descending probability with
    pairwise Euclidean spacing >= ``spacing`` px (accept-order is a valid prefix for
    every smaller budget)."""
    yy, xx = np.nonzero(candidates)
    order = np.argsort(-prob[yy, xx], kind='stable')
    yy, xx = yy[order], xx[order]
    h, w = prob.shape
    r = int(np.ceil(spacing)) - 1 if float(spacing).is_integer() else int(np.floor(spacing))
    oy, ox = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (oy * oy + ox * ox) < spacing * spacing
    oy, ox = oy[disk], ox[disk]
    blocked = np.zeros((h + 2 * r + 2, w + 2 * r + 2), bool)
    acc_y, acc_x = [], []
    for y, x in zip(yy.tolist(), xx.tolist()):
        if blocked[y + r, x + r]:
            continue
        acc_y.append(y); acc_x.append(x)
        blocked[oy + y + r, ox + x + r] = True
        if len(acc_y) >= kmax:
            break
    return np.asarray(acc_y, np.int64), np.asarray(acc_x, np.int64)


def dots_from_order(shape, ys, xs, k):
    m = np.zeros(shape, bool)
    m[ys[:k], xs[:k]] = True
    return m


# ----------------------------------------------------------------------------- amendment A1

A1_NAMES = ['vis_along', 'vis_across', 'end_along', 'end_across',
            'tip_forward', 'tip_across', 'tip_cone']


def a1_features(visible: np.ndarray, footprint: np.ndarray, fab_c2_2d: np.ndarray,
                fab_s2_2d: np.ndarray) -> dict[str, np.ndarray]:
    """Network-frame offsets (amendment A1), flattened over the footprint.

    ``fab_c2_2d, fab_s2_2d`` are the doubled-angle fabric NORMAL directions on the
    full grid (from :func:`structure_tensor` of the visible mask).  The fabric
    STRIKE unit vector is the normal rotated by 90 degrees.
    """
    vis = np.asarray(visible, bool)
    fp = np.asarray(footprint, bool)
    yy, xx = np.nonzero(fp)
    phi = 0.5 * np.arctan2(fab_s2_2d[fp], fab_c2_2d[fp])
    sx, sy = -np.sin(phi), np.cos(phi)           # strike = normal rotated by +90 deg
    out = {}
    _, (iy, ix) = ndi.distance_transform_edt(~vis, return_indices=True)
    dy = (iy[fp] - yy).astype(np.float32); dx = (ix[fp] - xx).astype(np.float32)
    del iy, ix
    out['vis_along'] = np.minimum(np.abs(dx * sx + dy * sy), 400.0)
    out['vis_across'] = np.minimum(np.abs(dx * (-sy) + dy * sx), 400.0)
    ends = endpoints(vis)
    if not ends.any():
        for k in A1_NAMES[2:]:
            out[k] = np.full(yy.size, 400.0, np.float32)
        return out
    # tip axis: unit vector from the local 11x11 catalogue centroid to the endpoint
    vf = vis.astype(np.float32)
    gy, gx = np.mgrid[0:vis.shape[0], 0:vis.shape[1]].astype(np.float32)
    n = ndi.uniform_filter(vf, 11)
    cy = ndi.uniform_filter(vf * gy, 11) / np.maximum(n, 1e-9)
    cx = ndi.uniform_filter(vf * gx, 11) / np.maximum(n, 1e-9)
    ty, tx = gy - cy, gx - cx
    del gy, gx, cy, cx, n, vf
    norm = np.sqrt(ty * ty + tx * tx)
    ty = np.where(ends & (norm > 1e-6), ty / np.maximum(norm, 1e-6), 0.0).astype(np.float32)
    tx = np.where(ends & (norm > 1e-6), tx / np.maximum(norm, 1e-6), 0.0).astype(np.float32)
    del norm
    _, (ey, ex) = ndi.distance_transform_edt(~ends, return_indices=True)
    eyf, exf = ey[fp], ex[fp]
    del ey, ex
    dy = (yy - eyf).astype(np.float32); dx = (xx - exf).astype(np.float32)   # endpoint -> pixel
    out['end_along'] = np.minimum(np.abs(dx * sx + dy * sy), 400.0)
    out['end_across'] = np.minimum(np.abs(dx * (-sy) + dy * sx), 400.0)
    uy, ux = ty[eyf, exf], tx[eyf, exf]
    del ty, tx
    fwd = dx * ux + dy * uy
    acr = np.abs(dx * (-uy) + dy * ux)
    out['tip_forward'] = np.clip(fwd, -400.0, 400.0)
    out['tip_across'] = np.minimum(acr, 400.0)
    out['tip_cone'] = np.where(fwd > 0, np.exp(-acr * acr / 18.0) * np.exp(-np.maximum(fwd, 0) / 25.0), 0.0)
    return {k: v.astype(np.float32) for k, v in out.items()}
