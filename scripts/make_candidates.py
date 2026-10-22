#!/usr/bin/env python3
"""Generate two candidate dot rasters and save as GeoTIFFs for novelty checking."""
from __future__ import annotations

import sys, time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as G, metric as M  # noqa: E402
from gems57.emit import expected_credit, emit_decimated, emit_prefix  # noqa: E402
from gems57.grid import write_geotiff  # noqa: E402
import rasterio  # noqa: E402

OUT = ROOT / "artifacts" / "gem_candidates"
OUT.mkdir(parents=True, exist_ok=True)

grid = G.load_grid(ROOT / "data" / "raw")
foot, cat = grid.footprint, grid.catalogue
allowed = foot & ~cat
stack = ROOT / "data" / "raw" / "training_features.tif"


def unit_ranks(values, valid):
    out = np.zeros(values.shape, np.float32)
    v = values[valid]
    if len(v) and np.ptp(v) > 0:
        out[valid] = ((rankdata(v, method="average") - 1) / max(len(v) - 1, 1)).astype(np.float32)
    return out


def emit_dots(surface, budget=37_654):
    ek = expected_credit(surface)
    ek = np.where(allowed, ek, 0.0)
    ranked, _ = emit_decimated(surface, allowed, tile_px=3, floor=0.0)
    return emit_prefix(ranked, budget) & allowed


def save(name, dots_bool):
    p = OUT / f"{name}.tif"
    write_geotiff(p, dots_bool.astype(np.float32), nodata=None)
    print(f"saved {p} dots={int(dots_bool.sum()):,}")
    return p


with rasterio.open(stack) as src:
    grav = src.read(18).astype(np.float32)   # iso_grav_anom_hg
    mag = src.read(1).astype(np.float32)     # mag_anom

valid = foot & np.isfinite(grav) & np.isfinite(mag) & (grav > -1e38) & (mag > -1e38)
g_edge = unit_ranks(grav, valid)
mag_low = 1.0 - unit_ranks(mag, valid)

# Candidate A: concealed geophysics (gravity-edge x mag-demag), zero on catalogue
surf_a = (g_edge * mag_low).astype(np.float32)
surf_a = np.where(allowed, surf_a, 0.0)
if surf_a.max() > 0:
    surf_a = (surf_a / surf_a.max()).astype(np.float32)
dots_a = emit_dots(surf_a)
save("g79-gem-geophysics-conduit", dots_a)
del surf_a, dots_a

# Candidate B: damage-zone x gravity edge
import gc
gc.collect()
dt = ndi.distance_transform_edt(~cat) * 100.0
dz = np.exp(-((dt - 200.0) ** 2) / (2 * 150.0 ** 2))
dz = np.where((dt >= 40) & (dt <= 700) & allowed, dz, 0.0).astype(np.float32)
if dz.max() > 0:
    dz = (dz / dz.max()).astype(np.float32)
surf_b = (dz * g_edge).astype(np.float32)
surf_b = np.where(allowed, surf_b, 0.0)
if surf_b.max() > 0:
    surf_b = (surf_b / surf_b.max()).astype(np.float32)
dots_b = emit_dots(surf_b)
save("g79-dz-grav-damagezone", dots_b)
print("done")
