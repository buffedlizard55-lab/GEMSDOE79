"""Catalogue-free feature stack for lane G79B-SDPT.

Channels 0-29 reproduce the archived H79-MCT stack exactly (control arm A1):
1 m lidar descriptors, 8 DEM10 channels, det_elev(+slope), Sato line
transforms, two local-support smooths. Channels 30+ are the preregistered
G79B additions (registry/preregistration_g79b.json):

* SDPT-D: the five DEM10 channels H79 dropped;
* SDPT-A: crest-base curvature dipole + facing polarity interactions;
* SDPT-B: cross-scale and cross-sensor step persistence (rank min/geomean);
* strike-directional step support (both tensor directions, neutral naming);
* SDPT-E: log distance to TIGER roads (`road_logdist`).

Every channel is a transform of terrain/road inputs only - no catalogue
feature, no geophysics band, no prior-submission raster. Written as one
float32 memmap (3730, 3292, C).
"""
from __future__ import annotations

import gc
import hashlib
import json
import time

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata
from skimage.filters import sato

from . import ROOT
from . import data as D

STACK = D.FEAT / "stack.f32.npy"
RECEIPT = D.FEAT / "features_receipt_g79b.json"

BASE_CHANNELS = [
    "lid_ex_max", "lid_ex_mean", "lid_step_max", "lid_lapneg_max", "lid_lappos_max",
    "lid_downface_max", "lid_upface_max", "lid_cross_max", "lid_relief", "lid_coh100",
    "lid_strike_cos2", "lid_strike_sin2", "lid_valid",
    "d10_slope_max", "d10_slope_std", "d10_hgm20_max", "d10_hgm50_max", "d10_steep_ratio_max",
    "d10_resid_std", "d10_curv_absmax", "d10_onesided3",
    "det_elev", "det_elev_slope",
    "line_lid_ex", "line_lid_step", "line_d10_hgm20", "line_d10_steep", "line_det_slope",
    "lid_step_sm", "d10_hgm20_sm",
]
NEW_CHANNELS = [
    # SDPT-D: DEM10 channels H79 dropped
    "d10_slope_mean", "d10_hgm200_mean", "d10_resid_range", "d10_onesided", "d10_valid_frac",
    # SDPT-A: dipole / polarity interactions (rank-domain, NaN where lidar absent)
    "dip_min", "dip_geo", "dip_balance", "face_polarity", "face_dom", "step_vs_cross", "coh_step",
    # SDPT-B: persistence across scales and sensors
    "persist_min", "persist_geo", "xsensor_min",
    # strike-directional step support (both structure-tensor directions)
    "strike_dirA", "strike_dirB", "step_max3",
    # SDPT-E: road proximity
    "road_logdist",
]
CHANNELS = BASE_CHANNELS + NEW_CHANNELS
IDX = {n: i for i, n in enumerate(CHANNELS)}


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def tiled_sato(img, sigmas=(1.0, 2.0), strip=600, halo=24):
    H, W = img.shape
    out = np.zeros((H, W), np.float32)
    for r0 in range(0, H, strip):
        a, b = max(0, r0 - halo), min(H, r0 + strip + halo)
        blk = np.nan_to_num(img[a:b].astype(np.float64), nan=0.0)
        res = sato(blk, sigmas=sigmas, black_ridges=False, mode="reflect")
        out[r0:min(H, r0 + strip)] = res[r0 - a: r0 - a + min(strip, H - r0)].astype(np.float32)
        del blk, res
        gc.collect()
    return out


def robust01(x, mask, lo=1.0, hi=99.5):
    v = x[mask & np.isfinite(x)]
    p_lo, p_hi = np.percentile(v, [lo, hi])
    y = (x - p_lo) / max(p_hi - p_lo, 1e-9)
    return np.clip(y, 0.0, 1.0).astype(np.float32)


def rank01(x, mask):
    """Empirical mid-rank in [0,1] over finite cells of mask; NaN elsewhere."""
    out = np.full(x.shape, np.nan, np.float32)
    m = mask & np.isfinite(x)
    v = x[m].astype(np.float64)
    if v.size > 1 and np.ptp(v) > 0:
        out[m] = ((rankdata(v, method="average") - 1) / (v.size - 1)).astype(np.float32)
    elif v.size:
        out[m] = 0.5
    return out


def build(force: bool = False) -> dict:
    if STACK.exists() and RECEIPT.exists() and not force:
        return json.loads(RECEIPT.read_text())
    D.FEAT.mkdir(parents=True, exist_ok=True)
    grid = D.load_grid()
    fp = grid.footprint
    H, W = fp.shape
    stack = np.lib.format.open_memmap(STACK, mode="w+", dtype=np.float32, shape=(H, W, len(CHANNELS)))
    stats = {}

    def put(name, arr):
        arr = np.where(fp, arr.astype(np.float32, copy=False), np.nan).astype(np.float32)
        stack[:, :, IDX[name]] = arr
        v = arr[fp & np.isfinite(arr)]
        stats[name] = {"finite_in_footprint": int(v.size),
                       "p01": float(np.percentile(v, 1)) if v.size else None,
                       "p50": float(np.percentile(v, 50)) if v.size else None,
                       "p99": float(np.percentile(v, 99)) if v.size else None}
        log(f"  {name:18s} finite={v.size:9d}")

    def get(name):
        return np.array(stack[:, :, IDX[name]])

    log("lidar descriptors (base)")
    for b in ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
              "upface_max", "cross_max", "relief", "coh100"]:
        put(f"lid_{b}", D.read_lidar(b))
    strike = D.read_lidar("strike")
    th = np.deg2rad(2.0 * strike)
    put("lid_strike_cos2", np.cos(th)); put("lid_strike_sin2", np.sin(th))
    del th
    put("lid_valid", D.lidar_valid().astype(np.float32))

    log("DEM10 channels (base 8 + SDPT-D 5)")
    for src, name in [("dem10_slope_max", "d10_slope_max"), ("dem10_slope_std", "d10_slope_std"),
                      ("dem10_hgm20_max", "d10_hgm20_max"), ("dem10_hgm50_max", "d10_hgm50_max"),
                      ("dem10_steep_ratio_max", "d10_steep_ratio_max"),
                      ("dem10_resid_std", "d10_resid_std"), ("dem10_curv_absmax", "d10_curv_absmax"),
                      ("dem10_onesided3", "d10_onesided3"),
                      ("dem10_slope_mean", "d10_slope_mean"), ("dem10_hgm200_mean", "d10_hgm200_mean"),
                      ("dem10_resid_range", "d10_resid_range"), ("dem10_onesided", "d10_onesided"),
                      ("dem10_valid_frac", "d10_valid_frac")]:
        put(name, D.read_dem10(src, fp))

    log("100 m terrain bands")
    put("det_elev", D.read_tf_band("det_elev", fp))
    put("det_elev_slope", D.read_tf_band("det_elev_slope", fp))

    log("line-continuity transforms (Sato sigma 1,2)")
    for src, name in [("lid_ex_max", "line_lid_ex"), ("lid_step_max", "line_lid_step"),
                      ("d10_hgm20_max", "line_d10_hgm20"), ("d10_steep_ratio_max", "line_d10_steep"),
                      ("det_elev_slope", "line_det_slope")]:
        put(name, tiled_sato(robust01(get(src), fp)))
        gc.collect()

    log("local support smooths")
    for src, name in [("lid_step_max", "lid_step_sm"), ("d10_hgm20_max", "d10_hgm20_sm")]:
        put(name, ndi.gaussian_filter(np.nan_to_num(robust01(get(src), fp), nan=0.0), 1.5))
        gc.collect()

    log("G79B rank-domain interactions")
    r_lapneg = rank01(get("lid_lapneg_max"), fp)
    r_lappos = rank01(get("lid_lappos_max"), fp)
    r_step = rank01(get("lid_step_max"), fp)
    r_cross = rank01(get("lid_cross_max"), fp)
    put("dip_min", np.fmin(r_lapneg, r_lappos))
    put("dip_geo", np.sqrt(np.clip(r_lapneg, 0, 1) * np.clip(r_lappos, 0, 1)))
    put("dip_balance", 1.0 - np.abs(r_lapneg - r_lappos))
    del r_lapneg, r_lappos
    up, down = get("lid_upface_max"), get("lid_downface_max")
    den = np.where(np.isfinite(up) & np.isfinite(down), up + down, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        pol = np.where(den > 1e-12, (up - down) / np.where(den > 1e-12, den, 1.0), 0.0)
    pol[~np.isfinite(den)] = np.nan
    put("face_polarity", pol.astype(np.float32))
    r_up, r_down = rank01(up, fp), rank01(down, fp)
    put("face_dom", np.abs(r_up - r_down))
    del up, down, den, pol, r_up, r_down
    put("step_vs_cross", r_step - r_cross)
    put("coh_step", np.clip(r_step, 0, 1) * get("lid_coh100"))
    del r_cross

    r_ex = rank01(get("lid_ex_max"), fp)
    r_hgm = rank01(get("d10_hgm20_max"), fp)
    r_det = rank01(get("det_elev_slope"), fp)
    stack_min = np.fmin(np.fmin(r_ex, r_step), np.fmin(r_hgm, r_det))
    put("persist_min", stack_min); del stack_min
    with np.errstate(invalid="ignore"):
        geo = np.exp(0.25 * (np.log(np.clip(r_ex, 1e-6, 1)) + np.log(np.clip(r_step, 1e-6, 1))
                             + np.log(np.clip(r_hgm, 1e-6, 1)) + np.log(np.clip(r_det, 1e-6, 1))))
    geo[~(np.isfinite(r_ex) & np.isfinite(r_step) & np.isfinite(r_hgm) & np.isfinite(r_det))] = np.nan
    put("persist_geo", geo.astype(np.float32)); del geo, r_ex, r_det
    put("xsensor_min", np.fmin(r_step, r_hgm)); del r_hgm

    log("strike-directional step support")
    step01 = np.nan_to_num(r_step, nan=0.0)
    ang = np.deg2rad(np.nan_to_num(strike, nan=0.0))  # structure-tensor doubled-angle/2
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for name, (sy, sx) in [("strike_dirA", (np.sin(ang), np.cos(ang))),
                           ("strike_dirB", (np.cos(ang), -np.sin(ang)))]:
        acc = np.zeros((H, W), np.float32)
        for sgn in (1.0, -1.0):
            for d in (1.0, 2.0):
                acc += ndi.map_coordinates(step01, [yy + sgn * d * sy, xx + sgn * d * sx],
                                           order=1, mode="constant", cval=0.0, prefilter=False)
        acc /= 4.0
        acc[~np.isfinite(r_step)] = np.nan
        put(name, acc)
        del acc
    del yy, xx, ang
    put("step_max3", ndi.maximum_filter(step01, size=3, mode="nearest").astype(np.float32)
        * np.where(np.isfinite(r_step), 1.0, np.nan))
    del step01, r_step, strike

    log("road distance")
    put("road_logdist", D.read_road_logdist(fp))

    stack.flush()
    del stack
    gc.collect()
    receipt = {
        "evidence_class": "FEATURE-RECEIPT", "lane": "G79B-SDPT",
        "path": str(STACK.relative_to(ROOT)), "shape": [H, W, len(CHANNELS)], "dtype": "float32",
        "channels": CHANNELS, "base_channels": BASE_CHANNELS, "new_channels": NEW_CHANNELS,
        "catalogue_free": True, "geophysics_used": False, "prior_submission_rasters_used": False,
        "channel_stats": stats,
        "stack_sha256_first_64MB": hashlib.sha256(open(STACK, "rb").read(64 << 20)).hexdigest(),
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    import sys
    build(force="--force" in sys.argv)
