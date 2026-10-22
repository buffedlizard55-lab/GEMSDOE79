#!/usr/bin/env python3
"""Novelty check: compare a candidate dot/raster against all local historical TIFs.

Reports max |Spearman| rank correlation (over finite footprint cells) and max
forward 3-px overlap (fraction of candidate dots within 3 px of a reference
raster's positive pixels). Lane rule: |rho| <= 0.90 AND forward overlap <= 0.70
vs EVERY reference raster.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as G  # noqa: E402


def refs():
    hits = []
    for p in sorted(ROOT.rglob("*.tif")):
        if p.is_symlink():
            continue
        sp = p.as_posix()
        if "/.git/" in sp or "/.cache/" in sp:
            continue
        hits.append(p)
    return hits


def forward_overlap(cand_bool: np.ndarray, ref_bool: np.ndarray) -> float:
    if not cand_bool.any():
        return 0.0
    dist = ndi.distance_transform_edt(~ref_bool)
    # candidate dot at (y,x) is within 3 px of a ref dot if dist[y,x] <= 3
    near = dist[cand_bool]
    return float((near <= 3.0).mean())


def main(cand_path: Path):
    cand_path = cand_path.resolve()
    grid = G.load_grid(ROOT / "data" / "raw")
    foot = grid.footprint
    with rasterio.open(cand_path) as src:
        cand = src.read(1).astype(np.float64)
    cand_bool = cand > 0
    print(f"candidate {cand_path.name}: {int(cand_bool.sum()):,} positive pixels")
    results = []
    for p in refs():
        if p.resolve() == cand_path:
            continue  # skip self-comparison
        try:
            with rasterio.open(p) as src:
                ref = src.read(1).astype(np.float64)
            ref_bool = (ref > 0) & np.isfinite(ref)
            ref_finite = np.isfinite(ref)
            # spearman over finite cells of both
            mask = foot & ref_finite & np.isfinite(cand)
            if mask.sum() > 100:
                rho, _ = spearmanr(cand[mask], ref[mask])
                rho = float(rho)
            else:
                rho = float("nan")
            fov = forward_overlap(cand_bool, ref_bool)
            results.append((p.as_posix(), rho, fov, int(ref_bool.sum())))
        except Exception as e:
            print(f"SKIP {p}: {e}")
    results.sort(key=lambda r: -r[2])
    print(f"\n{'forward_overlap':>16} {'|rho|':>8} {'ref_positive':>12}  reference")
    for p, rho, fov, npos in results:
        flag = "  <-- FAIL" if (abs(rho) > 0.90 or fov > 0.70) else ""
        print(f"{fov:16.4f} {abs(rho) if rho==rho else float('nan'):8.4f} {npos:12,}  {p}{flag}")
    worst_rho = max((abs(r) for _, r, _, _ in results if r == r), default=0.0)
    worst_fov = max((f for _, _, f, _ in results), default=0.0)
    print(f"\nMAX |rho| = {worst_rho:.4f} (limit 0.90) | MAX forward 3px overlap = {worst_fov:.4f} (limit 0.70)")
    print(f"LANE NOVELTY vs local refs: {'PASS' if worst_rho <= 0.90 and worst_fov <= 0.70 else 'FAIL'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
