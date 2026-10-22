#!/usr/bin/env python3
"""Diagnostic: damage-zone x gravity-gradient edge surface on holdout seed 20.

Unique vs pure damage-zone (G79-DZD): requires a gravity-gradient edge (subsurface
density contrast / fault expression), so dots cluster in the damage zone AND at
geophysically-expressed faults -- concealed-but-real conduits rather than every
metre of mapped trace.
"""
from __future__ import annotations

import sys, time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as G, holdout as HO, metric as M, evaluate_holdout as EH  # noqa: E402
from gems57.emit import expected_credit, emit_decimated, emit_prefix  # noqa: E402

t0 = time.time()
grid = G.load_grid(ROOT / "data" / "raw")
foot, cat = grid.footprint, grid.catalogue
allowed = foot & ~cat

stack = ROOT / "data" / "raw" / "training_features.tif"
import rasterio  # noqa: E402
with rasterio.open(stack) as src:
    grav = src.read(18).astype(np.float32)   # iso_grav_anom_hg

valid = foot & np.isfinite(grav) & (grav > -1e38)
g_edge = unit = None


def unit_ranks(values, valid):
    out = np.zeros(values.shape, np.float32)
    v = values[valid]
    if len(v) and np.ptp(v) > 0:
        out[valid] = ((rankdata(v, method="average") - 1) / max(len(v) - 1, 1)).astype(np.float32)
    return out


g_edge = unit_ranks(grav, valid)
dt = ndi.distance_transform_edt(~cat) * 100.0
dz = np.exp(-((dt - 200.0) ** 2) / (2 * 150.0 ** 2))
dz = np.where((dt >= 40) & (dt <= 700) & allowed, dz, 0.0).astype(np.float32)
if dz.max() > 0:
    dz = (dz / dz.max()).astype(np.float32)

surface = (dz * g_edge).astype(np.float32)
surface = np.where(allowed, surface, 0.0)
if surface.max() > 0:
    surface = (surface / surface.max()).astype(np.float32)
print("surface positive", int((surface > 0).sum()), "max", float(surface.max()))

ek = expected_credit(surface)
ek = np.where(allowed, ek, 0.0)
ranked, _ = emit_decimated(surface, allowed, tile_px=3, floor=0.0)
dots = emit_prefix(ranked, 37_654) & allowed

folds, _ = HO.buffered_component_draw(grid, seed=20, hide_frac=0.20, buffer_px=3)
terms = []
for f in folds:
    res, t = EH.evaluate(dots.astype(np.float32), f, valid=foot)
    terms.append(t)
    print(f['name'], "dti", round(float(res["dti"]), 4), "truth", int(res["n_truth"]),
          "emitted", int(res["n_emitted"]))
terms = np.concatenate(terms, axis=0)
totals = terms.sum(axis=0)
dti = totals[0] / (totals[0] + M.ALPHA * totals[1] + M.BETA * totals[2] + M.EPS)
print(f"DZxGRAV seed20 pooled DTI={dti:.4f} withheld={int(totals[3])} dots={int(dots.sum())}"
      f" runtime={time.time()-t0:.0f}s")
