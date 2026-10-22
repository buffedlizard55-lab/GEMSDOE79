"""G79-OPC: oriented inter-component pair-correlation fault-population prior.

Preregistered in ``registry/preregistration_g79_opc.json`` (committed before any
surface, score or placement of this lane existed).

Scientific idea
---------------
Faults in an extensional province are not independent lines. They occur as
populations with anisotropic second-order structure. Along strike there are
en-echelon steps and relay ramps. Across strike there are sub-parallel
synthetic/antithetic splays at characteristic spacings. Those spacings scale with
mechanical-layer thickness (see ``research/hypotheses_ff2e4413.md`` for sources).
The *empirical* anisotropic pair-correlation function of the visible catalogue,
measured only between DIFFERENT connected components and rotated into each
source pixel's local strike frame, is a population-level prior. It says where an
unmapped companion fault is likely, independent of the continuation of any one
trace. Independent 2-m LiDAR scarp evidence is combined with it. A scarp whose
strike agrees with the strike expected from the population prior
(``lidar_strike_concordance``) is more likely a fault than a shoreline.

Everything catalogue-derived is computed from the mask passed in (the visible
catalogue in the holdout, a simulated-visible catalogue for training labels,
the full catalogue for the live fit). No registry raster is an input.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.signal import oaconvolve
from scipy.spatial import cKDTree

STRUCT3 = np.ones((3, 3), bool)
R_PC = 40          # pair-correlation radius (px) = 4 km
BIN_PX = 2         # folded |u|,|v| histogram bin (px)
N_ORIENT = 12      # strike bins for the oriented convolution
N_SRC = 30_000     # sampled source pixels for the pair-correlation estimate

GEOM_NAMES = ["log1p_d_vis", "dens_s10", "dens_s30", "opc", "opc_iso",
              "opc_aniso_ratio", "opc_cos2", "opc_sin2", "opc_coherence",
              "lidar_strike_concordance"]
ISO_NAMES = ["log1p_d_vis", "dens_s10", "dens_s30", "opc_iso"]
OPC_GEO_NAMES = GEOM_NAMES[:9]


def strike_field(mask: np.ndarray, s1: float = 1.5, s2: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """Strike angle (radians in image coords, x right / y down, mod pi) + coherence.

    Structure tensor of the smoothed mask: the dominant gradient direction is
    perpendicular to the trace, so strike = gradient orientation + pi/2.
    """
    m = ndi.gaussian_filter(mask.astype(np.float32), s1)
    gx = ndi.sobel(m, axis=1)
    gy = ndi.sobel(m, axis=0)
    jxx = ndi.gaussian_filter(gx * gx, s2)
    jyy = ndi.gaussian_filter(gy * gy, s2)
    jxy = ndi.gaussian_filter(gx * gy, s2)
    theta_grad = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-12)
    phi = np.mod(theta_grad + np.pi / 2, np.pi).astype(np.float32)
    return phi, coh.astype(np.float32)


def pair_correlation(mask: np.ndarray, footprint: np.ndarray, phi: np.ndarray,
                     seed: int = 7907) -> dict:
    """Folded strike-frame pair-correlation g(|u|,|v|) between different components."""
    comp, _ = ndi.label(mask, STRUCT3)
    ys, xs = np.nonzero(mask)
    n_all = ys.size
    if n_all < 10:
        raise ValueError("catalogue too small for a pair-correlation estimate")
    rng = np.random.default_rng(seed)
    src = rng.choice(n_all, size=min(N_SRC, n_all), replace=False)
    tree = cKDTree(np.column_stack([ys, xs]))
    nb = R_PC // BIN_PX
    counts = np.zeros((nb, nb), np.float64)
    lab = comp[ys, xs]
    for start in range(0, src.size, 2000):
        chunk = src[start:start + 2000]
        neigh = tree.query_ball_point(np.column_stack([ys[chunk], xs[chunk]]), r=R_PC)
        for i, nbrs in zip(chunk, neigh):
            nbrs = np.asarray(nbrs, np.int64)
            nbrs = nbrs[lab[nbrs] != lab[i]]
            if nbrs.size == 0:
                continue
            dy = (ys[nbrs] - ys[i]).astype(np.float64)
            dx = (xs[nbrs] - xs[i]).astype(np.float64)
            c, s = np.cos(phi[ys[i], xs[i]]), np.sin(phi[ys[i], xs[i]])
            u = np.abs(dx * c + dy * s)
            v = np.abs(-dx * s + dy * c)
            ok = (u < R_PC) & (v < R_PC) & (np.hypot(u, v) >= 1.5)
            iu = (u[ok] // BIN_PX).astype(np.int64)
            iv = (v[ok] // BIN_PX).astype(np.int64)
            np.add.at(counts, (iu, iv), 1.0)
    rho = n_all / float(footprint.sum())
    area = 4.0 * BIN_PX * BIN_PX          # each folded bin collects 4 mirror bins
    expected = src.size * rho * area
    g = counts / expected
    w = np.maximum(ndi.gaussian_filter(g, 0.75) - 1.0, 0.0)
    centers = (np.arange(nb) + 0.5) * BIN_PX
    rr = np.hypot(centers[:, None], centers[None, :])
    w[rr > R_PC] = 0.0
    return dict(g=g, w=w, centers=centers, n_sources=int(src.size), n_catalogue=int(n_all),
                density=rho)


def _lookup(w: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Bilinear lookup of the folded grid at |u|,|v| (px)."""
    nb = w.shape[0]
    fu = np.clip(np.abs(u) / BIN_PX - 0.5, 0, nb - 1)
    fv = np.clip(np.abs(v) / BIN_PX - 0.5, 0, nb - 1)
    return ndi.map_coordinates(w, [fu.ravel(), fv.ravel()], order=1, mode="nearest").reshape(u.shape)


def oriented_kernels(w: np.ndarray) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[-R_PC:R_PC + 1, -R_PC:R_PC + 1].astype(np.float64)
    r = np.hypot(yy, xx)
    inside = (r <= R_PC) & (r >= 1.0)
    angles = (np.arange(N_ORIENT) + 0.5) * np.pi / N_ORIENT
    kernels = []
    for a in angles:
        c, s = np.cos(a), np.sin(a)
        u = xx * c + yy * s
        v = -xx * s + yy * c
        k = _lookup(w, u, v) * inside
        kernels.append(k.astype(np.float32))
    # isotropic control: rotational average of the oriented kernels
    k_iso = np.mean(kernels, axis=0).astype(np.float32)
    return kernels, k_iso, angles


def geometry_features(mask: np.ndarray, footprint: np.ndarray, lidar_phi: np.ndarray | None,
                      seed: int = 7907) -> tuple[dict[str, np.ndarray], dict]:
    """All catalogue-derived features from ``mask`` only (full-grid float32 arrays)."""
    mask = np.asarray(mask, bool) & footprint
    out: dict[str, np.ndarray] = {}
    out["log1p_d_vis"] = np.log1p(ndi.distance_transform_edt(~mask)).astype(np.float32)
    mf = mask.astype(np.float32)
    out["dens_s10"] = ndi.gaussian_filter(mf, 10).astype(np.float32)
    out["dens_s30"] = ndi.gaussian_filter(mf, 30).astype(np.float32)
    phi, _coh = strike_field(mask)
    pc = pair_correlation(mask, footprint, phi, seed=seed)
    kernels, k_iso, angles = oriented_kernels(pc["w"])
    total = np.zeros(mask.shape, np.float32)
    cacc = np.zeros(mask.shape, np.float32)
    sacc = np.zeros(mask.shape, np.float32)
    phim = np.where(mask, phi, -1.0)
    edges = np.arange(N_ORIENT + 1) * np.pi / N_ORIENT
    for b, (k, a) in enumerate(zip(kernels, angles)):
        sel = mask & (phim >= edges[b]) & (phim < edges[b + 1])
        if not sel.any():
            continue
        conv = oaconvolve(sel.astype(np.float32), k, mode="same").astype(np.float32)
        np.maximum(conv, 0, out=conv)
        total += conv
        cacc += conv * np.float32(np.cos(2 * a))
        sacc += conv * np.float32(np.sin(2 * a))
        del conv
    iso = np.maximum(oaconvolve(mf, k_iso, mode="same"), 0).astype(np.float32)
    res = np.hypot(cacc, sacc)
    out["opc"] = np.log1p(total)
    out["opc_iso"] = np.log1p(iso)
    out["opc_aniso_ratio"] = (total / (iso + 1e-3)).astype(np.float32)
    out["opc_cos2"] = np.where(res > 0, cacc / (res + 1e-9), 0).astype(np.float32)
    out["opc_sin2"] = np.where(res > 0, sacc / (res + 1e-9), 0).astype(np.float32)
    out["opc_coherence"] = (res / (total + 1e-6)).astype(np.float32)
    if lidar_phi is not None:
        phi_opc = 0.5 * np.arctan2(sacc, cacc)
        # cos^2(delta) = (1 + cos 2 delta)/2: 1 parallel, 0 perpendicular. (|cos 2 delta|
        # in the first prereg text cannot tell parallel from perpendicular; corrected
        # before any holdout result, see preregistration deviation D-OPC-1.)
        conc = 0.5 * (1.0 + np.cos(2 * (lidar_phi - phi_opc))) * out["opc_coherence"]
        out["lidar_strike_concordance"] = np.where(np.isfinite(lidar_phi), conc, np.nan).astype(np.float32)
    else:
        out["lidar_strike_concordance"] = np.full(mask.shape, np.nan, np.float32)
    del total, cacc, sacc, iso, res
    meta = dict(n_catalogue=pc["n_catalogue"], n_sources=pc["n_sources"], density=pc["density"],
                g_max=float(pc["g"].max()),
                g_along_strike_0to10px=float(pc["g"][:5, :2].mean()),
                g_across_strike_0to10px=float(pc["g"][:2, :5].mean()),
                w_grid=np.round(pc["w"], 4).tolist())
    return out, meta


def lidar_strike_phi(strike_u8: np.ndarray, step_u8: np.ndarray, valid_u8: np.ndarray) -> tuple[np.ndarray, dict]:
    """Decode the LiDAR strike band into image-coordinate radians, label-free.

    The band stores 0..180 deg (q = 1 + round(254 x/180), 0 = no lidar) but its
    angular convention is not documented. Three conventions are tried and the one
    that best agrees with the structure-tensor strike of the step_max band (also
    label-free) is used. No catalogue or truth enters this choice.
    """
    has = (strike_u8 > 0) & (valid_u8 > 0)
    deg = (strike_u8.astype(np.float32) - 1.0) / 254.0 * 180.0
    a = np.deg2rad(deg)
    step = np.where(step_u8 > 0, step_u8.astype(np.float32), 0)
    phi_st, coh = strike_field(step > np.percentile(step[has], 90), 1.0, 3.0)
    conv = {
        "math_image": a,
        "azimuth_from_north_cw": np.arctan2(-np.cos(a), np.sin(a)),
        "math_map_ccw_from_east": -a,
    }
    wmask = has & (coh > 0.3)
    scores = {}
    for name, ph in conv.items():
        # signed mean cos 2(delta): +1 parallel, -1 perpendicular (an |.| here would
        # be blind to 90-degree convention errors -- deviation D-OPC-1)
        scores[name] = float(np.mean(np.cos(2 * (ph[wmask] - phi_st[wmask]))))
    best = max(scores, key=scores.get)
    phi = np.where(has, np.mod(conv[best], np.pi), np.nan).astype(np.float32)
    return phi, dict(convention=best, agreement_scores=scores, n_pixels=int(wmask.sum()))
