#!/usr/bin/env python3
"""Measure how every local GeoTIFF compares with the OFFICIAL sample submission.

Session 2026-10-22 audit. Read-only: writes one new evidence file, never a
score, never a submission receipt, never a selector decision.

Official reference (verified 2026-10-22):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  "Your submission has the same bounds as the training data, and data outside
   the bounds is null or nan."  "float32 ... values between 0 and 1".
The official sample (data/reference/sample_submission.tif, SHA-256 pinned in
registry/data_manifest.json) uses NaN outside the footprint.  Local artifacts
use 0.0 outside the footprint (shared writer policy), so this script records
the convention difference explicitly rather than assuming it is harmless.

Also measures the novelty-gate witness: the pinned registry raster
UNIVERSAL_WITNESS_BLOB is re-read from .cache (restore with
scripts/preflight_new_lane.py --restore) and its positive-support fraction
inside the footprint is recorded.  A witness with positive support on 100 %
of the footprint makes the literal "dot" definition degenerate.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]

from gems57.grid import EPSG, TRANSFORM, SHAPE  # noqa: E402
from gems79.novelty import UNIVERSAL_WITNESS_BLOB  # noqa: E402

OUT = ROOT / 'evidence' / 'official_format_audit_20261022.json'
OFFICIAL = ROOT / 'data/reference/sample_submission.tif'
ARTIFACT_GLOBS = ('docs/downloads/*.tif', 'artifacts/*/*.tif')


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def describe(path: Path, footprint: np.ndarray | None = None) -> dict:
    """Return format facts for one single-band GeoTIFF; never repairs values."""
    with rasterio.open(path) as src:
        a = src.read(1)
        crs = src.crs.to_epsg() if src.crs else None
        out = dict(
            file=path.relative_to(ROOT).as_posix(),
            sha256=sha256(path),
            bytes=path.stat().st_size,
            bands=src.count,
            dtype=src.dtypes[0],
            epsg=crs,
            shape=[src.height, src.width],
            transform_matches_pin=tuple(src.transform)[:6] == tuple(TRANSFORM)[:6],
            nodata=None if src.nodata is None else str(src.nodata),
        )
    nan = ~np.isfinite(a)
    finite = a[~nan]
    out.update(
        nan_pixels=int(nan.sum()),
        min=float(finite.min()) if finite.size else None,
        max=float(finite.max()) if finite.size else None,
        in_range_0_1=bool(finite.size and finite.min() >= 0.0 and finite.max() <= 1.0),
        positive_pixels=int(((a > 0) & ~nan).sum()),
    )
    if footprint is not None:
        outside = ~footprint
        out.update(
            nan_outside_footprint=int((nan & outside).sum()),
            zero_outside_footprint=int(((a == 0) & outside).sum()),
            nonzero_outside_footprint=int(((a != 0) & ~nan & outside).sum()),
            nan_inside_footprint=int((nan & footprint).sum()),
        )
        out['fill_convention'] = (
            'nan_outside' if out['nan_outside_footprint'] == int(outside.sum()) and out['nan_inside_footprint'] == 0
            else 'zero_outside' if out['zero_outside_footprint'] == int(outside.sum()) and out['nan_pixels'] == 0
            else 'other'
        )
    return out


def witness_fraction(footprint: np.ndarray) -> dict:
    """Positive-support fraction of the pinned registry witness inside the footprint."""
    path = ROOT / '.cache/registry' / (UNIVERSAL_WITNESS_BLOB + '.tif')
    if not path.is_file():
        return {'status': 'not_cached', 'hint': 'python scripts/preflight_new_lane.py --restore'}
    with rasterio.open(path) as src:
        a = src.read(1)
    support = np.isfinite(a) & (a > 0)
    return {
        'status': 'measured',
        'blob': UNIVERSAL_WITNESS_BLOB,
        'footprint_cells': int(footprint.sum()),
        'positive_support_cells_in_footprint': int((support & footprint).sum()),
        'fraction_of_footprint_with_positive_support': float((support & footprint).sum() / footprint.sum()),
        'positive_support_outside_footprint': int((support & ~footprint).sum()),
        'unique_values_sampled': int(np.unique(a[np.isfinite(a)][:100000]).size),
    }


def main() -> int:
    with rasterio.open(OFFICIAL) as src:
        footprint = np.isfinite(src.read(1))
    official = describe(OFFICIAL, footprint)
    # Footprint is the official sample's finite cells; prove it matches the pinned grid loader.
    from gems57.grid import load_grid
    grid = load_grid(ROOT / 'data/reference')
    footprint_matches_loader = bool(np.array_equal(grid.footprint, footprint))
    official.update(
        epsg_matches_pin=official['epsg'] == EPSG,
        shape_matches_pin=tuple(official['shape']) == tuple(SHAPE),
        footprint_cells=int(footprint.sum()),
        footprint_matches_grid_loader=footprint_matches_loader,
    )
    files = []
    for pattern in ARTIFACT_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            files.append(describe(path, footprint))
    witness = witness_fraction(footprint)
    report = dict(
        evidence_class='REPOSITORY-MEASUREMENT',
        generated_utc=datetime.now(timezone.utc).isoformat(),
        official_reference=('https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/'),
        official_sample=official,
        local_artifacts=files,
        novelty_witness=witness,
        scope=('Format and gate-definition facts only. Not portal acceptance, not organizer '
               'receipt, not holdout DTI, not a slot approval.'),
    )
    text = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if '--write' in sys.argv:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        # Mode 'x': refuse to replace an existing evidence file (never silent overwrite).
        try:
            with OUT.open('x') as stream:
                stream.write(text)
        except FileExistsError:
            sys.stderr.write(f'refusing to overwrite existing evidence: {OUT}\n')
            return 2
    print(text, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
