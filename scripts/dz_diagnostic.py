#!/usr/bin/env python3
"""Diagnostic: does a catalogue damage-zone surface score on the holdout?

Distance-to-catalogue Gaussian centred at 200 m (sigma 150 m), zero on the
catalogue and outside the footprint, top-k dots -> hide-and-recover holdout.
This tells us whether catalogue-proximal methods recover withheld segments.
"""
from __future__ import annotations

import sys, time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as G, holdout as HO, metric as M, evaluate_holdout as EH  # noqa: E402

t0 = time.time()
grid = G.load_grid(ROOT / "data" / "raw")
foot, cat = grid.footprint, grid.catalogue
allowed = foot & ~cat
dt = ndi.distance_transform_edt(~cat) * 100.0  # metres
# damage-zone score: gaussian centred 200 m sigma 150 m, taper to 0 at 0 and 700 m
dz = np.exp(-((dt - 200.0) ** 2) / (2 * 150.0 ** 2))
dz = np.where((dt >= 40) & (dt <= 700) & allowed, dz, 0.0).astype(np.float32)
if dz.max() > 0:
    dz = (dz / dz.max()).astype(np.float32)

from gems57.emit import expected_credit, emit_decimated, emit_prefix  # noqa: E402

ek = expected_credit(dz)
ek = np.where(allowed, ek, 0.0)
ranked, _ = emit_decimated(dz, allowed, tile_px=3, floor=0.0)
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
print(f"damage-zone seed20 pooled DTI={dti:.4f} withheld={int(totals[3])} dots={int(dots.sum())}"
      f" runtime={time.time()-t0:.0f}s")
