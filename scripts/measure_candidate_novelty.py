#!/usr/bin/env python3
"""Measure a candidate raster's dot overlap against local priors and fetched top priors.

Reusable companion to ``scripts/run_mfx.novelty`` so a finished artifact can be
re-measured without rerunning an experiment.  Prints a JSON report to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57.grid import load_grid  # noqa: E402
import run_mfx  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    if not path.is_absolute():
        path = ROOT / path
    grid = load_grid(ROOT / "data" / "reference")
    with rasterio.open(path) as src:
        a = src.read(1).astype(np.float32)
    if a.shape != grid.footprint.shape:
        raise SystemExit(f"candidate shape {a.shape} != grid {grid.footprint.shape}")
    dots = a > 0
    extra, fetch_log = run_mfx.fetch_top_priors()
    report = {
        "candidate": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "dots": int(dots.sum()),
        "scope": "every local prior raster in this checkout plus the 12 highest-scoring "
                 "predecessor rasters fetched from their public GitHub mirrors; the full "
                 "992-raster registry is NOT re-restored here",
        "fetches": fetch_log,
    }
    report.update(run_mfx.novelty(dots, grid.footprint, extra, exclude={path}))
    print(json.dumps(report, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
