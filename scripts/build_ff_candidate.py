#!/usr/bin/env python3
"""H79-FF: far-field lidar-scarp discovery candidate (research artifact).

Builds a unique, format-valid binary dot GeoTIFF that is deliberately
*not* a copy of any prior submission:

* Domain: scored footprint, off the mapped catalogue, in the distal band
  2-8 km from any catalogue trace. Regional compilations are least complete
  here; organizer test labels are expert faults missing from the catalogue,
  so this is where a missing fault is most plausibly discoverable from lidar.
* Surface: USGS 3DEP lidar scarp step_max (slope excess of a fault scarp),
  normalized within the domain. A scarp is the physical signature of a
  Quaternary fault that offsets the surface.
* Placement: fixed budget 37,654 binary dots, greedy descending rank with
  3 px Poisson spacing (matches the metric's 300 m triangular TP kernel),
  all off-catalogue, zeros elsewhere, all finite in [0, 1].

This is a research artifact. The duplicate gate is expected to fail because
the registry contains space-filling surfaces and a dense spacing-5 lattice
whose 3 px halos cover essentially the whole footprint (IR-79-53); no 37,654
dot map can satisfy the literal 70 % / 3 px rule against them. The file is
therefore written with an unambiguous DO-NOT-SUBMIT status unless every gate
passes.
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
from gems57.grid import load_grid                       # noqa: E402
from gems79.placement import place                      # noqa: E402
from gems57.submission_writer import write_submission   # noqa: E402

DIST_LO_M = 2000.0  # distal band lower bound (m)
DIST_HI_M = 8000.0  # distal band upper bound (m)
BUDGET = 37654
OUT = ROOT / "docs/downloads"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    grid = load_grid(ROOT / "data/reference")
    fp, cat = grid.footprint, grid.catalogue

    # Distance to the nearest mapped catalogue trace (metres).
    dt = ndi.distance_transform_edt(~cat).astype(np.float64) * grid.transform.a
    dt[~fp] = np.nan

    # Distal domain: off-catalogue, between 2 and 8 km from mapped faults.
    domain = fp & ~cat & (dt >= DIST_LO_M) & (dt < DIST_HI_M)
    print(f"domain cells: {int(domain.sum())}", flush=True)

    # Lidar scarp step_max: slope excess across a scarp (USGS 3DEP product).
    with rasterio.open(ROOT / "data/raw/external/lidar_scarp_features_u8.tif") as src:
        descr = list(src.descriptions)
        step = src.read(descr.index("step_max") + 1).astype(np.float64)
    step[~fp] = 0.0

    surface = np.zeros(grid.shape, np.float32)
    if domain.sum():
        v = step[domain]
        lo, hi = float(v.min()), float(v.max())
        scale = max(hi - lo, 1e-9)
        surface[domain] = ((v - lo) / scale).astype(np.float32)

    dots, info = place(surface, domain, BUDGET)
    print("placement:", info, flush=True)
    if info["exhausted"]:
        print("WARNING: placement exhausted before budget", flush=True)

    pred = np.zeros(grid.shape, np.float32)
    pred[dots & domain & ~cat] = 1.0
    assert int(pred.sum()) == BUDGET
    assert not np.any(pred[cat] > 0)
    assert not np.any((pred > 0) & ~fp)
    assert np.isfinite(pred).all() and pred.min() >= 0 and pred.max() <= 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha256(pred.tobytes()).hexdigest()
    name = f"gems79-h79-ff-farfield-scarp-{BUDGET}dots-{stamp}-{digest[:8]}"
    note = (f"H79-FF far-field lidar-scarp discovery, {DIST_LO_M:.0f}-{DIST_HI_M:.0f}m "
            f"off catalogue, 37654 dots, step_max surface; research artifact")
    assert len(name) <= 140 and len(note) <= 140, (len(name), len(note))

    path = OUT / (name + ".tif")
    receipt = write_submission(
        path, pred, ROOT / "data/reference/sample_submission.tif", grid.footprint,
        note=note, name=name, catalogue=grid.catalogue,
        metadata=dict(lane="H79-FF", hypothesis="far-field lidar scarp",
                      domain_m=[DIST_LO_M, DIST_HI_M], dots_sha256=digest,
                      placement=info, surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest()),
    )
    print(json.dumps(dict(
        written=receipt["file"],
        sha256=sha(path),
        bytes=receipt["bytes"],
        submission_name=receipt["submission_name"],
        note=receipt["note"],
        note_chars=receipt["note_chars"],
        zip_sha256=receipt["zip_sha256"],
        validator=receipt["validator"],
    ), indent=2))


if __name__ == "__main__":
    main()
