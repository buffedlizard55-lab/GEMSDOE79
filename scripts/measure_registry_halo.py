#!/usr/bin/env python3
"""Measure how much of the allowed footprint a single registry raster's 3-px halo covers.

Why this exists: the inherited novelty gate (forward overlap <= 0.70 within 3 px of ONE
registry raster's dots) can be made non-informative by a dense registry raster. This script
re-measures that property from raw bytes so the claim is auditable, instead of trusting a
stored certificate. It is a diagnostic only: it never approves a submission and never
changes the gate.

Usage:
  python3 scripts/measure_registry_halo.py REGISTRY.tif [--footprint data/reference/sample_submission.tif]
                                           [--catalogue data/reference/existing_faults.tif]
                                           [--radius-px 3] [--json OUT.json]

Definitions (stated, not assumed):
  * registry dots   = cells with value > 0 AND finite (NaN = outside, not a dot)
  * footprint       = cells that are finite in the sample_submission grid (5,167,373 cells)
  * catalogue       = mapped USGS/INGENIOUS fault cells (existing_faults > 0; 60,988 cells),
                      masked from scoring and novelty per DD-MASK and vendor/gems57/uniqueness.py
  * off-catalogue   = footprint & ~catalogue (5,106,385 allowed evaluation cells)
  * halo            = every cell within Euclidean distance <= radius_px of a registry dot
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]


def _rel_path(path: Path) -> str:
    resolved = path.resolve()
    root_resolved = ROOT.resolve()
    if resolved.is_relative_to(root_resolved):
        return resolved.relative_to(root_resolved).as_posix()
    return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def disk_structure(radius_px: int) -> np.ndarray:
    r = int(radius_px)
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    return (xx * xx + yy * yy) <= r * r


def measure(
    registry_path: Path,
    footprint_path: Path,
    radius_px: int = 3,
    catalogue_path: Path | None = None,
) -> dict:
    with rasterio.open(registry_path) as reg, rasterio.open(footprint_path) as fp:
        if reg.shape != fp.shape or tuple(reg.transform) != tuple(fp.transform) or reg.crs != fp.crs:
            raise ValueError("registry raster grid (shape/transform/CRS) does not match the footprint grid")
        reg_a = reg.read(1)
        fp_a = fp.read(1)
        fp_grid = (fp.shape, tuple(fp.transform), fp.crs)
    footprint = np.isfinite(fp_a)
    dots = np.isfinite(reg_a) & (reg_a > 0)
    halo = ndimage.binary_dilation(dots, structure=disk_structure(radius_px))
    covered = int((halo & footprint).sum())
    n_allowed = int(footprint.sum())
    out = {
        "registry_path": _rel_path(registry_path),
        "registry_sha256": sha256_file(registry_path),
        "footprint_path": _rel_path(footprint_path),
        "footprint_sha256": sha256_file(footprint_path),
        "radius_px": int(radius_px),
        "allowed_cells_finite_footprint": n_allowed,
        "registry_dot_cells_in_footprint": int((dots & footprint).sum()),
        "registry_dot_cells_total": int(dots.sum()),
        "halo_covered_allowed_cells": covered,
        "halo_coverage_fraction": covered / n_allowed if n_allowed else None,
        "uncovered_allowed_cells": n_allowed - covered,
        "uncovered_fraction": (n_allowed - covered) / n_allowed if n_allowed else None,
        "gate_limit_forward_overlap": 0.70,
        "interpretation": (
            "If halo_coverage_fraction > 0.70, a candidate can satisfy forward overlap <= 0.70 "
            "against this raster only by placing > 30% of its dots on the uncovered cells. "
            "This is a measurement of the gate, not a novelty approval."
        ),
    }
    if catalogue_path is not None:
        with rasterio.open(catalogue_path) as cat_ds:
            if (cat_ds.shape, tuple(cat_ds.transform), cat_ds.crs) != fp_grid:
                raise ValueError("catalogue raster grid (shape/transform/CRS) does not match the footprint grid")
            cat_a = cat_ds.read(1)
        catalogue = footprint & np.isfinite(cat_a) & (cat_a > 0)
        allowed_off_cat = footprint & ~catalogue
        n_off_cat = int(allowed_off_cat.sum())
        cov_off_cat = int((halo & allowed_off_cat).sum())
        out.update({
            "catalogue_path": _rel_path(catalogue_path),
            "catalogue_sha256": sha256_file(catalogue_path),
            "catalogue_cells_in_footprint": int(catalogue.sum()),
            "allowed_off_catalogue_cells": n_off_cat,
            "halo_covered_off_catalogue_cells": cov_off_cat,
            "halo_coverage_off_catalogue_fraction": cov_off_cat / n_off_cat if n_off_cat else None,
            "uncovered_off_catalogue_cells": n_off_cat - cov_off_cat,
            "uncovered_off_catalogue_fraction": (n_off_cat - cov_off_cat) / n_off_cat if n_off_cat else None,
        })
    return out


def main() -> None:
    default_cat = ROOT / "data" / "reference" / "existing_faults.tif"
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("registry", type=Path)
    ap.add_argument("--footprint", type=Path, default=ROOT / "data" / "reference" / "sample_submission.tif")
    ap.add_argument("--catalogue", type=Path, default=default_cat if default_cat.is_file() else None)
    ap.add_argument("--no-catalogue", action="store_true", help="Omit mapped-catalogue subtraction")
    ap.add_argument("--radius-px", type=int, default=3)
    ap.add_argument("--json", type=Path, help="write the result here (refuses to overwrite)")
    args = ap.parse_args()
    cat_path = None if args.no_catalogue else args.catalogue
    result = measure(args.registry, args.footprint, args.radius_px, catalogue_path=cat_path)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json:
        if args.json.exists():
            raise SystemExit(f"refusing to overwrite {args.json}")
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
