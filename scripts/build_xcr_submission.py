#!/usr/bin/env python3
"""Emit the G79-XCR candidate GeoTIFF with the official NaN exterior.

The surface is the two-channel composite that the two instruments actually
support (see ``evidence/xcr/*``):

* ``dens_visible_40`` -- catalogue corridor density: symmetric AUC 0.72-0.79 on
  instrument I1 (hidden catalogue faults).
* ``rugged`` -- rank of ``det_elev_relief_s5 x elev_step_s2``: symmetric AUC
  0.75-0.79 on instrument I2 (SGMC faults absent from the catalogue).  The
  catalogue-proximity channels measured ~0.50 on the same instrument, so they
  are deliberately down-weighted here.

Nothing is copied from a previous submission: the surface, the dot set, the
bytes and the SHA-256 are computed here.  The output path states the verdict,
and the receipt repeats it.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import grid as g57grid  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems79 import xcr  # noqa: E402
from gems79.placement import place  # noqa: E402

OUT = ROOT / "evidence" / "xcr"
DOWNLOADS = ROOT / "docs" / "downloads" / "research"
BUDGET = 37_654
NAME = "gems79-xcr-corridor-rugged-20261022"


def rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    v = a[mask]
    order = np.argsort(v, kind="stable")
    q = np.empty_like(v)
    q[order] = np.linspace(0.0, 1.0, v.size, dtype=np.float32)
    out = np.zeros(a.shape, np.float32)
    out[mask] = q
    return out


def main() -> int:
    grid = load_grid(ROOT / "data" / "reference")
    fp = grid.footprint
    mat = np.load(ROOT / ".cache" / "xcr" / "static.npy", mmap_mode="r")
    names = list(xcr.STATIC_NAMES)
    relief = np.asarray(mat[names.index("det_elev_relief_s5")], np.float32)
    step = np.asarray(mat[names.index("elev_step_s2")], np.float32)
    dens = ndi.uniform_filter(grid.catalogue.astype(np.float32), 40)
    rugged = relief * step
    surface = 0.5 * rank01(dens, fp) + 0.5 * rank01(rugged, fp)
    surface[~fp] = 0.0
    surface = surface.astype(np.float32)

    allowed = fp & ~grid.catalogue
    dots, placement = place(surface, allowed, BUDGET, spacing=3)
    values = np.where(dots, 1.0, 0.0).astype(np.float32)
    values[~fp] = 0.0  # writer replaces this with NaN under exterior='nan'

    target_tif = DOWNLOADS / f"{NAME}-DO-NOT-SUBMIT.tif"
    for stale in (target_tif, target_tif.with_suffix(".zip"), target_tif.with_suffix(".json")):
        if stale.exists():
            stale.unlink()
    receipt = write_submission(
        target_tif, values, ROOT / "data" / "reference" / "sample_submission.tif", fp,
        name=NAME, note="G79-XCR corridor+ruggedness dots; holdout below incumbent",
        catalogue=grid.catalogue, exterior="nan",
        metadata={
            "lane": "G79-XCR",
            "surface": "0.5*rank(dens_visible_40) + 0.5*rank(det_elev_relief_s5*elev_step_s2)",
            "budget": BUDGET, "placement": placement,
            "preregistration": "registry/preregistration_g79_xcr.json",
            "official_exterior": "NaN outside footprint, nodata=NaN (rule R6)",
        })
    with rasterio.open(target_tif) as src:
        a = src.read(1)
        meta = dict(crs=str(src.crs), shape=list(src.shape), dtype=src.dtypes[0],
                    nodata=repr(src.nodata), transform=list(tuple(src.transform)[:6]))
    official = dict(
        path=str(target_tif.relative_to(ROOT)),
        sha256=hashlib.sha256(target_tif.read_bytes()).hexdigest(),
        bytes=target_tif.stat().st_size,
        meta=meta,
        nan_outside_footprint=int(np.isnan(a[~fp]).sum()),
        finite_inside_footprint=int(np.isfinite(a[fp]).sum()),
        footprint_cells=int(fp.sum()),
        outside_cells=int((~fp).sum()),
        min_inside=float(np.nanmin(a[fp])), max_inside=float(np.nanmax(a[fp])),
        emitted_positive_pixels=int((a > 0).sum()),
        on_catalogue=int((dots & grid.catalogue).sum()),
        generated_utc=datetime.now(timezone.utc).isoformat(),
        receipt=receipt,
    )
    xcr.dump(OUT / "official_convention_receipt.json", official)
    print(json.dumps({k: official[k] for k in
                      ("path", "sha256", "bytes", "nan_outside_footprint",
                       "emitted_positive_pixels", "on_catalogue")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
