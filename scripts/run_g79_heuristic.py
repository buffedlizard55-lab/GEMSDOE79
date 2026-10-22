#!/usr/bin/env python3
"""
G79-HEURISTIC: Zero-ML scarp+gravity+mag corridor — most memory-efficient path.

Heuristic surface: normalized iso_grav_anom_hg * gravity_coincidence * lidar_scarp
No LightGBM needed for first artifact.  Honest holdout on both seeds.
NaN exterior (R6 PASS).  3 experiments budget: this is EXP-1.
"""
from __future__ import annotations
import json, hashlib, time, zipfile, sys, gc
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57.grid import load_grid, write_geotiff
from gems57.holdout import build_holdout
from gems57.evaluate_holdout import evaluate as eval_fold, pooled_summary
from gems57 import metric as gems_metric

TARGET = {
    17: "iso_grav_anom_hg",
    11: "det_elev",
    2: "tmi_hg",
    12: "iso_grav_anom",
    1: "rtp",
    0: "mag_anom",
}

def load_band(path: Path, idx: int) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(idx + 1)

def clean(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    valid = (arr > -1e30) & fp
    if not valid.any():
        return np.zeros_like(arr, dtype=np.float32)
    med = float(np.median(arr[valid]))
    out = np.where(valid, arr, med).astype(np.float32)
    lo, hi = np.percentile(out[fp], [1, 99])
    out = np.clip(out, lo, hi)
    mu = float(out[fp].mean()); sd = float(out[fp].std()) + 1e-6
    out = (out - mu) / sd
    out[~fp] = 0
    return out.astype(np.float32)

def evaluate_surface(surface: np.ndarray, grid, seeds=(20, 30)) -> dict:
    """Pooled DTI across all holdout cells for given seeds."""
    ctx = build_holdout(grid, seeds=seeds)
    by_cell = {}
    for cell in ctx.cells:
        sy, sx = cell.bbox
        # crop surface to bbox
        surf_crop = surface[sy, sx]
        # active is cell.active already cropped
        # eval_fold expects prediction in crop coords? Check: it uses fold['region'] etc.
        # Actually eval_fold takes (prediction_2d_full_grid??) Let's check
        # From evaluate_holdout.py: evaluate(prediction, fold, valid, ...) where fold has region/known/truth
        # The fold's truth/active are already in crop coords with bbox offset
        # So we need to pass valid=cell.active but prediction must be crop-sized too? 
        # Actually holdout.py cells store active cropped to bbox, and truth_yx within crop.
        # But evaluate_holdout.evaluate in holdout.py takes (pred_cropped, cell, ...) 
        # Let's use the shared holdout evaluation path: vendor evaluation
        pass
    return {}

def pooled_dti_for_surface(surface: np.ndarray, grid, seed: int) -> dict:
    """Compute pooled DTI for a full-grid surface on one seed's holdout."""
    ctx = build_holdout(grid, seeds=(seed,))
    terms_all = []
    # evaluate each cell
    for cell in ctx.cells:
        if "detached" in cell.key:
            continue  # primary is "all" mode
        sy, sx = cell.bbox
        pred_crop = surface[sy, sx]
        # valid is cell.active's domain? For evaluate we need valid mask
        # evaluate() takes fold dict with region/visible/truth; valid is footprint
        # Construct fold dict from cell
        # Cell has: key, fold, seed, mode, bbox, active, truth_yx, k_dg, n_truth
        # But evaluate expects fold with region, visible, truth
        # Let's use the direct metric path instead: we have cell.active and cell.k_dg
        # Actually easier: use eval_fold directly with constructed fold
        # Look at how archive lanes did it: they used gems57.evaluate_holdout.evaluate on cropped windows
        # Let's just compute pooled via direct method
        pass
    return {}

# Simpler: use the test pattern for evaluation — direct pooled via holdout cells
# Actually easiest: replicate what evidence/g79_cskd_results.json did —
# use src/gems79/thvc_model style which has run_quadrant_nested_oof

# Quick check: let's just run the holdout evaluation the same way as cskd but inline
def run_holdout_eval(surface_full: np.ndarray, grid, seeds=(20, 30)) -> dict:
    """
    Run pooled DTI via iterating cells and calling gems57 metric directly.
    Simpler: for each cell, compute TP_w/FP_w/FN_w using metric.dti_exact on cropped active domain.
    """
    results = {}
    for seed in seeds:
        ctx = build_holdout(grid, seeds=(seed,))
        # Filter to "all" mode only for primary DTI
        cells_all = [c for c in ctx.cells if c.mode == "all"]
        # For pooled, we need to combine terms with spatial blocks
        # Use evaluate per cell then pooled_summary
        from gems57.evaluate_holdout import evaluate as eval_one
        terms_by_cell = []
        for cell in cells_all:
            sy, sx = cell.bbox
            pred_crop = surface_full[sy, sx].copy()
            # Build fold dict expected by evaluate: need region, visible, truth
            # But Cell doesn't have those keys - it has active, truth_yx, k_dg
            # Check Cell fields again: active, truth_yx, k_dg, n_truth
            # The evaluate() function signature is evaluate(prediction, fold, valid, block_side, origin, global_shape)
            # fold must have 'region', ('masked_known' or 'visible'), 'truth'
            # valid is the footprint/active domain
            # We can construct fold from cell:
            # region = cell.active | truth (i.e. the scored domain+truth)
            # But we need visible (known) mask - cell was built with some hidden logic
            # Actually holdout cells' active IS valid & region & ~known already
            # So we can invert: valid = grid.footprint cropped, but evaluate() recomputes active = valid & region & ~known
            # Let's just call evaluate with valid = grid.footprint cropped and fold with region=cell bbox full footprint etc.
            # This is getting complex - alternative: directly compute pooled DTI via metric.kernel
            pass
        results[seed] = None
    return results

# Actually simplest honest path: use existing thvc_model's evaluation helper if available
# Check what tools exist
if __name__ == "__main__":
    print("This script needs the proper holdout evaluation wiring. Checking existing lane code...")
    import inspect, pathlib
    # Look for how DFSD/CSKD eval works
    p = pathlib.Path("src/gems79/cskd.py")
    if p.exists():
        text = p.read_text()
        # Find eval pattern
        for i, line in enumerate(text.splitlines()):
            if "evaluate" in line.lower() or "pooled" in line.lower() or "holdout" in line.lower():
                if i < 100:
                    print(f"{i}: {line}")
        print("--- cskd.py head ---")
        print(text[:3000])
