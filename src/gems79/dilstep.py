"""H79-DILSTEP: Faulds step-over / tip / intersection ridges.

Closed-form score. Every numeric parameter is read from the preregistration.
Catalogue geometry is a function of the mask the caller passes as visible, so
a holdout fold cannot leak withheld pixels through this module.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

FEATURE_NAMES = (
    "z_tmi_hg",
    "z_grav_hg",
    "z_dilate",
    "z_thk",
    "horsetail",
    "stepover",
    "intersection",
    "shoreline_flag",
    "candidate_surface",
)


def robust_z(values: np.ndarray, valid: np.ndarray, *, clip: float, sentinel_below: float) -> np.ndarray:
    """Median/MAD z-score. Sentinel and non-finite cells stay 0, not a fake extreme."""
    out = np.zeros(values.shape, np.float32)
    mask = np.asarray(valid, bool) & np.isfinite(values) & (values > sentinel_below)
    sample = values[mask]
    if sample.size < 100:
        return out
    med = float(np.median(sample))
    mad = float(np.median(np.abs(sample - med))) * 1.4826
    if not np.isfinite(mad) or mad < 1e-8:
        mad = float(np.std(sample)) or 1.0
    z = (values.astype(np.float64) - med) / mad
    out[mask] = np.clip(z[mask], -clip, clip).astype(np.float32)
    return out


def tip_outward(catalogue: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Degree-1 catalogue pixels and the outward angle (away from the single neighbor).

    Angle is atan2(row_offset, col_offset), image coordinates (row increases south).
    """
    cat = np.asarray(catalogue, bool)
    kernel = np.ones((3, 3), np.uint8)
    kernel[1, 1] = 0
    degree = ndi.convolve(cat.astype(np.uint8), kernel, mode="constant")
    ys, xs = np.nonzero(cat & (degree == 1))
    angs = np.zeros(ys.size, np.float64)
    height, width = cat.shape
    for i, (y, x) in enumerate(zip(ys, xs)):
        y0, y1 = max(0, int(y) - 1), min(height, int(y) + 2)
        x0, x1 = max(0, int(x) - 1), min(width, int(x) + 2)
        patch = cat[y0:y1, x0:x1]
        py, px = np.nonzero(patch)
        keep = ~((py == int(y) - y0) & (px == int(x) - x0))
        if not np.any(keep):
            continue
        ny = int(py[keep][0]) - (int(y) - y0)
        nx = int(px[keep][0]) - (int(x) - x0)
        angs[i] = np.arctan2(-ny, -nx)
    return ys.astype(np.int32), xs.astype(np.int32), angs


def paint_cones(ys, xs, angs, shape, *, rmin: int, rmax: int, half_deg: float, samples: int) -> np.ndarray:
    """Rasterize fixed tip cones. Empty tip sets return an all-false mask."""
    mask = np.zeros(shape, np.uint8)
    if len(ys) == 0:
        return mask.astype(bool)
    radii = np.arange(int(rmin), int(rmax) + 1, dtype=np.float64)
    offsets = np.linspace(-np.deg2rad(half_deg), np.deg2rad(half_deg), int(samples))
    height, width = shape
    for start in range(0, len(ys), 400):
        stop = min(len(ys), start + 400)
        y = ys[start:stop, None, None].astype(np.float64)
        x = xs[start:stop, None, None].astype(np.float64)
        ang = angs[start:stop, None, None]
        yy = np.rint(y + radii[None, :, None] * np.sin(ang + offsets[None, None, :])).astype(np.int32)
        xx = np.rint(x + radii[None, :, None] * np.cos(ang + offsets[None, None, :])).astype(np.int32)
        ok = (yy >= 0) & (yy < height) & (xx >= 0) & (xx < width)
        mask[yy[ok], xx[ok]] = 1
    return mask.astype(bool)


def _angle_diff_deg(a: float, b: float) -> float:
    """Smallest undirected angular difference in degrees, in [0, 90]."""
    d = abs((a - b + np.pi) % (2 * np.pi) - np.pi)
    d = min(d, np.pi - d)
    return float(np.degrees(d))


def stepover_mask(ys, xs, angs, catalogue: np.ndarray, params: dict) -> np.ndarray:
    """Open corridors between nearby, similarly striking tips with a lateral offset."""
    mask = np.zeros(catalogue.shape, bool)
    if len(ys) < 2:
        return mask
    tree = cKDTree(np.column_stack([ys, xs]))
    pairs = tree.query_pairs(r=float(params["stepover_max_sep_px"]))
    tol = float(params["stepover_strike_tol_deg"])
    across_min = float(params["stepover_across_min_px"])
    across_max = float(params["stepover_across_max_px"])
    cat = np.asarray(catalogue, bool)
    height, width = cat.shape
    for i, j in pairs:
        if _angle_diff_deg(angs[i], angs[j]) > tol:
            continue
        dy = float(ys[j] - ys[i])
        dx = float(xs[j] - xs[i])
        along = dy * np.sin(angs[i]) + dx * np.cos(angs[i])
        across = dy * np.cos(angs[i]) - dx * np.sin(angs[i])
        if not (across_min <= abs(across) <= across_max):
            continue
        if abs(along) > float(params["stepover_max_sep_px"]):
            continue
        n = int(max(abs(dy), abs(dx))) + 1
        yy = np.rint(np.linspace(ys[i], ys[j], n)).astype(np.int32)
        xx = np.rint(np.linspace(xs[i], xs[j], n)).astype(np.int32)
        inside = (yy >= 0) & (yy < height) & (xx >= 0) & (xx < width)
        yy, xx = yy[inside], xx[inside]
        # Endpoints sit on the tips. Only the open gap between them may be painted.
        if yy.size < 3 or int(cat[yy[1:-1], xx[1:-1]].sum()) > 0:
            continue
        mask[yy[1:-1], xx[1:-1]] = True
    if mask.any():
        mask = ndi.binary_dilation(mask, structure=np.ones((3, 3), bool))
    return mask & ~cat


def intersection_mask(catalogue: np.ndarray, mag_z: np.ndarray, params: dict) -> np.ndarray:
    """Cells beside a visible strand where the magnetic gradient cuts the strand at a high angle."""
    cat = np.asarray(catalogue, bool)
    if not cat.any():
        return np.zeros(cat.shape, bool)
    dist = ndi.distance_transform_edt(~cat)
    smooth = ndi.gaussian_filter(dist.astype(np.float32), 1.0)
    gy, gx = np.gradient(smooth)
    fault_normal = np.arctan2(gy, gx)
    mag_smooth = ndi.gaussian_filter(np.nan_to_num(mag_z, nan=0.0), 1.5)
    my, mx = np.gradient(mag_smooth)
    mag_dir = np.arctan2(my, mx)
    delta = np.abs((mag_dir - fault_normal + np.pi) % (2 * np.pi) - np.pi)
    delta = np.minimum(delta, np.pi - delta)
    near = (dist >= float(params["intersection_dist_min_px"])) & (
        dist <= float(params["intersection_dist_max_px"])
    )
    return near & (np.degrees(delta) >= float(params["intersection_angle_min_deg"])) & (
        mag_z >= float(params["intersection_mag_z_min"])
    ) & ~cat


def shoreline_flag(elev: np.ndarray, mag_z: np.ndarray, step: np.ndarray, valid: np.ndarray,
                   params: dict) -> np.ndarray:
    """Contour-parallel high lidar steps. Angle is between elevation and magnetic gradients."""
    filled = np.where(valid & np.isfinite(elev) & (elev > float(params["sentinel_below"])), elev, np.nan)
    med = np.nanmedian(filled)
    filled = np.where(np.isfinite(filled), filled, med).astype(np.float32)
    ey, ex = np.gradient(ndi.gaussian_filter(filled, 2.0))
    my, mx = np.gradient(ndi.gaussian_filter(np.nan_to_num(mag_z, nan=0.0), 1.5))
    elev_ang = np.arctan2(ey, ex)
    mag_ang = np.arctan2(my, mx)
    delta = np.abs((elev_ang - mag_ang + np.pi) % (2 * np.pi) - np.pi)
    delta = np.minimum(delta, np.pi - delta)
    positive = step[step > 0]
    if positive.size == 0:
        return np.zeros(elev.shape, bool)
    thresh = float(np.percentile(positive, float(params["shoreline_step_percentile"])))
    return (np.degrees(delta) <= float(params["shoreline_angle_max_deg"])) & (step >= thresh) & valid


def structural_fields(visible: np.ndarray, mag_z: np.ndarray, elev: np.ndarray, step: np.ndarray,
                      footprint: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    """Favourable-setting masks from the visible catalogue only."""
    vis = np.asarray(visible, bool) & np.asarray(footprint, bool)
    ys, xs, angs = tip_outward(vis)
    horse = paint_cones(
        ys, xs, angs, vis.shape,
        rmin=int(params["tip_cone_rmin_px"]),
        rmax=int(params["tip_cone_rmax_px"]),
        half_deg=float(params["tip_cone_half_angle_deg"]),
        samples=int(params["tip_cone_angle_samples"]),
    )
    horse &= footprint & ~vis
    stepover = stepover_mask(ys, xs, angs, vis, params) & footprint
    inter = intersection_mask(vis, mag_z, params) & footprint
    shore = shoreline_flag(elev, mag_z, step, footprint, params)
    return {
        "horsetail": horse,
        "stepover": stepover,
        "intersection": inter,
        "shoreline_flag": shore,
        "n_tips": int(ys.size),
    }


def score_surface(z_mag, z_grav, z_dil, z_thk, fields: dict, footprint: np.ndarray,
                  blocked: np.ndarray, params: dict, *, use_structure: bool) -> np.ndarray:
    """Nonnegative closed-form score. Blocked cells (mapped faults) are exactly zero."""
    floor = float(params["base_floor"])
    base = (floor + np.maximum(z_mag, 0)) * (floor + np.maximum(z_grav, 0))
    base = base * (1.0 + (z_dil > 0).astype(np.float32))
    base = base * (1.0 + float(params["thk_weight"]) * np.maximum(z_thk, 0))
    if use_structure:
        struct = (
            1.0
            + float(params["weight_horsetail"]) * fields["horsetail"]
            + float(params["weight_stepover"]) * fields["stepover"]
            + float(params["weight_intersection"]) * fields["intersection"]
        ).astype(np.float32)
    else:
        struct = np.ones(z_mag.shape, np.float32)
    shore = np.where(
        fields["shoreline_flag"] & ~fields["stepover"],
        float(params["shoreline_weight"]),
        1.0,
    ).astype(np.float32)
    out = (base * struct * shore).astype(np.float32)
    out[~footprint | blocked] = 0
    out[~np.isfinite(out)] = 0
    return out


def normalize_unit(score: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Min-max on allowed positive cells. Rank order is unchanged. Zeros stay zero."""
    out = np.zeros(score.shape, np.float32)
    vals = score[allowed]
    if vals.size == 0 or float(np.ptp(vals)) == 0:
        return out
    lo = float(vals.min())
    hi = float(vals.max())
    out[allowed] = ((score[allowed] - lo) / (hi - lo)).astype(np.float32)
    return out
