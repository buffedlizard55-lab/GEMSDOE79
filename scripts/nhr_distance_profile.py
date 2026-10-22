#!/usr/bin/env python3
"""RASTER-MEASUREMENT: distance-to-catalogue profile of the final NHR dots vs H33.

Diagnostic for the stated distribution-shift risk (expert faults may lie
farther from mapped traces than withheld catalogue components). Not a score.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57.grid import load_grid   # noqa: E402
import analyze_h33                  # noqa: E402

H33 = "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
BINS_PX = [0, 2, 3, 5, 10, 20, 50, 10**6]


def profile(dist, mask):
    d = dist[mask]
    hist = np.histogram(d, bins=BINS_PX)[0]
    return dict(dots=int(mask.sum()), median_px=float(np.median(d)), mean_px=float(d.mean()),
                fraction_le_5px=float((d <= 5).mean()), fraction_gt_10px=float((d > 10).mean()),
                histogram={f"({BINS_PX[i]},{BINS_PX[i+1]}] px" if i else f"[0,{BINS_PX[1]}] px": int(h)
                           for i, h in enumerate(hist)})


def main():
    g = load_grid(ROOT / "data/reference")
    dist = ndi.distance_transform_edt(~g.catalogue)
    dots = np.load(ROOT / ".cache/nhr/final_dots.npy")
    h33, src = analyze_h33.locate(H33)
    h33 = np.where(np.isfinite(h33), h33, 0) > 0
    h33 &= g.footprint
    out = dict(evidence_class="RASTER-MEASUREMENT", pixel_m=100,
               nhr_dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
               nhr=profile(dist, dots & g.footprint), h33=profile(dist, h33),
               footprint=profile(dist, g.footprint & ~g.catalogue),
               note="Distances to the nearest mapped catalogue pixel (EDT, pixels of 100 m). Not a score.")
    (ROOT / "evidence/nhr/distance_to_catalogue.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: {kk: v[kk] for kk in ("dots", "median_px", "fraction_le_5px", "fraction_gt_10px")}
                      for k, v in out.items() if isinstance(v, dict)}, indent=2))


if __name__ == "__main__":
    main()
