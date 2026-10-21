"""Catalogue-free topographic feature stack for lane H79-MCT.

Design (pre-registered in registry/preregistration_h79.json)
-----------------------------------------------------------
The hidden "new fault" labels are, on the live evidence, dominated by topographic
scarps that the mapping experts traced on hillshades (see research/why_02778.md).
The lane therefore uses **only terrain descriptors** at three scales:

* 1 m USGS 3DEP lidar (2 m work grid aggregated to 100 m; cached u8 product, de-quantised),
* 10 m USGS 3DEP seamless DEM channels (cached float32 vectors),
* the competition's 100 m detrended elevation and its slope (training_features.tif bands 12 and 19).

plus **line-continuity transforms** of the strongest scarp descriptors (Sato tubular
ridge filter, sigma 1 and 2 px), which encode what a human mapper does: connect
collinear scarp fragments into a trace.  No geophysics, no catalogue-derived channel,
no prior-submission raster enters the stack.

Everything is written as one float32 memmap ``data/cache/features/stack.f32.npy`` of
shape (3730, 3292, C) so that training samples rows and prediction streams row blocks.
"""
from __future__ import annotations

import gc
import hashlib
import json
import time

import numpy as np
from scipy import ndimage as ndi
from skimage.filters import sato

from . import ROOT
from . import data as D

STACK = D.FEAT / "stack.f32.npy"
RECEIPT = ROOT / "evidence" / "features_receipt.json"

CHANNELS = [
    # 1 m lidar descriptors (NaN where no lidar)
    "lid_ex_max", "lid_ex_mean", "lid_step_max", "lid_lapneg_max", "lid_lappos_max",
    "lid_downface_max", "lid_upface_max", "lid_cross_max", "lid_relief", "lid_coh100",
    "lid_strike_cos2", "lid_strike_sin2", "lid_valid",
    # 10 m 3DEP channels (full footprint)
    "d10_slope_max", "d10_slope_std", "d10_hgm20_max", "d10_hgm50_max", "d10_steep_ratio_max",
    "d10_resid_std", "d10_curv_absmax", "d10_onesided3",
    # 100 m competition terrain bands
    "det_elev", "det_elev_slope",
    # line-continuity transforms ("mapper's eye")
    "line_lid_ex", "line_lid_step", "line_d10_hgm20", "line_d10_steep", "line_det_slope",
    # local support of the two strongest step descriptors
    "lid_step_sm", "d10_hgm20_sm",
]
IDX = {n: i for i, n in enumerate(CHANNELS)}


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def tiled_sato(img: np.ndarray, sigmas=(1.0, 2.0), strip=600, halo=24) -> np.ndarray:
    """Sato bright-ridge filter applied in overlapping horizontal strips (memory bound)."""
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


def robust01(x: np.ndarray, mask: np.ndarray, lo=1.0, hi=99.5) -> np.ndarray:
    """Clip to footprint percentiles and scale to [0,1] (keeps NaN)."""
    v = x[mask & np.isfinite(x)]
    p_lo, p_hi = np.percentile(v, [lo, hi])
    y = (x - p_lo) / max(p_hi - p_lo, 1e-9)
    return np.clip(y, 0.0, 1.0).astype(np.float32)


def build(force: bool = False) -> dict:
    if STACK.exists() and RECEIPT.exists() and not force:
        return json.loads(RECEIPT.read_text())
    D.FEAT.mkdir(parents=True, exist_ok=True)
    grid = D.load_grid()
    fp = grid.footprint
    H, W = fp.shape
    C = len(CHANNELS)
    stack = np.lib.format.open_memmap(STACK, mode="w+", dtype=np.float32, shape=(H, W, C))
    stats = {}

    def put(name: str, arr: np.ndarray):
        arr = arr.astype(np.float32, copy=False)
        arr = np.where(fp, arr, np.nan).astype(np.float32)
        stack[:, :, IDX[name]] = arr
        v = arr[fp & np.isfinite(arr)]
        stats[name] = {"finite_in_footprint": int(np.isfinite(arr[fp]).sum()),
                       "p01": float(np.percentile(v, 1)) if v.size else None,
                       "p50": float(np.percentile(v, 50)) if v.size else None,
                       "p99": float(np.percentile(v, 99)) if v.size else None}
        log(f"  {name:18s} finite={stats[name]['finite_in_footprint']:9d} p50={stats[name]['p50']}")

    log("lidar descriptors")
    lid_valid = D.lidar_valid()
    for b in ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
              "upface_max", "cross_max", "relief", "coh100"]:
        put(f"lid_{b}", D.read_lidar(b))
    strike = D.read_lidar("strike")
    th = np.deg2rad(2.0 * strike)
    put("lid_strike_cos2", np.cos(th)); put("lid_strike_sin2", np.sin(th)); del strike, th
    put("lid_valid", lid_valid.astype(np.float32))

    log("10 m 3DEP channels")
    for src, name in [("dem10_slope_max", "d10_slope_max"), ("dem10_slope_std", "d10_slope_std"),
                      ("dem10_hgm20_max", "d10_hgm20_max"), ("dem10_hgm50_max", "d10_hgm50_max"),
                      ("dem10_steep_ratio_max", "d10_steep_ratio_max"), ("dem10_resid_std", "d10_resid_std"),
                      ("dem10_curv_absmax", "d10_curv_absmax"), ("dem10_onesided3", "d10_onesided3")]:
        put(name, D.read_dem10(src, fp))

    log("100 m terrain bands")
    put("det_elev", D.read_tf_band("det_elev", fp))
    put("det_elev_slope", D.read_tf_band("det_elev_slope", fp))

    log("line-continuity transforms (Sato sigma 1,2 px)")
    for src, name in [("lid_ex_max", "line_lid_ex"), ("lid_step_max", "line_lid_step"),
                      ("d10_hgm20_max", "line_d10_hgm20"), ("d10_steep_ratio_max", "line_d10_steep"),
                      ("det_elev_slope", "line_det_slope")]:
        base = np.array(stack[:, :, IDX[src]])
        base01 = robust01(base, fp)
        put(name, tiled_sato(base01))
        del base, base01
        gc.collect()

    log("local support (gaussian sigma 1.5 px of 0/1-scaled step descriptors)")
    for src, name in [("lid_step_max", "lid_step_sm"), ("d10_hgm20_max", "d10_hgm20_sm")]:
        base = robust01(np.array(stack[:, :, IDX[src]]), fp)
        filled = np.nan_to_num(base, nan=0.0)
        put(name, ndi.gaussian_filter(filled, 1.5))
        del base, filled
        gc.collect()

    stack.flush()
    del stack
    gc.collect()
    receipt = {
        "evidence_class": "FEATURE-RECEIPT", "lane": "H79-MCT", "path": str(STACK.relative_to(ROOT)),
        "shape": [H, W, C], "dtype": "float32", "channels": CHANNELS,
        "catalogue_free": True, "geophysics_used": False, "prior_submission_rasters_used": False,
        "sources": {
            "lidar": "data/raw/external/lidar_scarp_features_u8.tif (USGS 3DEP 1 m tiles; GEMSDOE24 mirror, sha256 d580bb8b…)",
            "dem10": "data/cache/dem10/*.f32.npy (USGS 3DEP 1/3 arc-second; GEMSDOE10 tag ext/dem10-36343078537)",
            "det_elev": "data/raw/training_features.tif bands 12 and 19 (owner mirror sha256 4371c82e…)",
        },
        "channel_stats": stats,
        "stack_sha256_first_64MB": hashlib.sha256(open(STACK, "rb").read(64 << 20)).hexdigest(),
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    RECEIPT.parent.mkdir(exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    import sys
    build(force="--force" in sys.argv)
