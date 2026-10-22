#!/usr/bin/env python3
"""Deterministic private reserialization check for the current artifact or archived H79-NHR."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
from gems57.grid import load_grid
from gems57.submission_writer import write_submission

ARCHIVED_E1_REPRODUCTION = {
    'lane': 'G79-FABRIC-OFFSET',
    'verified_utc': '2026-10-22T01:27:30.932955+00:00',
    'exact_tiff_recovery': True,
    'exact_single_tiff_zip_recovery': True,
    'raster_sha256': '8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca',
    'zip_sha256': '51e27e9d484fbb45b75cfb4cbd9c2d1d0dfde0717584668ff4f140a70c623c2c',
}


def reproduce_current(root: Path = ROOT) -> dict:
    card = json.loads((root / 'run_card.json').read_text())
    if card['verdict'] != 'negative' or card['ok_to_submit']:
        raise ValueError('This command only recovers the existing stopped/fail-closed negative artifact')
    original = root / card['submission_file']
    original_receipt = json.loads(original.with_suffix('.json').read_text())
    grid = load_grid(root / 'data/reference')
    with rasterio.open(original) as ds:
        decoded = ds.read(1).astype(np.float32)
    dots = (decoded > 0) & grid.footprint & (~grid.catalogue)
    dots_sha256 = hashlib.sha256(dots.tobytes()).hexdigest()
    prediction = np.where(dots, np.float32(1.0), np.float32(0.0))
    with tempfile.TemporaryDirectory(prefix='gems79-current-byte-recovery-') as tmp:
        receipt = write_submission(
            Path(tmp) / original.name,
            prediction,
            root / 'data/reference/sample_submission.tif',
            grid.footprint,
            catalogue=grid.catalogue,
            name=card['submission_name'],
            note=card['submission_note'],
            metadata=original_receipt.get('metadata'),
        )
        if receipt['sha256'] != card['raster_sha256'] or receipt['zip_sha256'] != original_receipt['zip_sha256']:
            raise ValueError('Recovered TIFF/ZIP bytes differ; originals remain unchanged')
    return {
        'verified_utc': datetime.now(timezone.utc).isoformat(),
        'lane': card['lane'],
        'exact_tiff_recovery': True,
        'exact_single_tiff_zip_recovery': True,
        'exact_decoded_dots_recovery': True,
        'raster_sha256': receipt['sha256'],
        'zip_sha256': receipt['zip_sha256'],
        'dots_sha256': dots_sha256,
        'positive_pixels': int(dots.sum()),
        'scientific_experiments': 0,
        'holdouts': 0,
        'dot_placements': 0,
        'slots_used': 0,
        'original_artifacts_and_run_card_not_overwritten': True,
        'archived_e1_reproduction': ARCHIVED_E1_REPRODUCTION,
    }


def reproduce_nhr(root: Path = ROOT) -> dict:
    build = json.loads((root / 'evidence/nhr/x1_final_build.json').read_text())
    original = root / 'archive/concurrent_downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif'
    original_receipt = json.loads(original.with_suffix('.json').read_text())
    grid = load_grid(root / 'data/reference')
    with rasterio.open(original) as ds:
        decoded = ds.read(1).astype(np.float32)
    dots = (decoded > 0) & grid.footprint & (~grid.catalogue)
    dots_sha256 = hashlib.sha256(dots.tobytes()).hexdigest()
    if dots_sha256 != build['dots_sha256']:
        raise ValueError('Decoded dots_sha256 does not match evidence/nhr/x1_final_build.json')
    prediction = np.where(dots, np.float32(1.0), np.float32(0.0))
    with tempfile.TemporaryDirectory(prefix='g79-nhr-byte-recovery-') as tmp:
        receipt = write_submission(
            Path(tmp) / original.name,
            prediction,
            root / 'data/reference/sample_submission.tif',
            grid.footprint,
            catalogue=grid.catalogue,
            name=original_receipt['submission_name'],
            note=original_receipt['note'],
            metadata=original_receipt['metadata'],
        )
        if receipt['sha256'] != original_receipt['sha256'] or receipt['zip_sha256'] != original_receipt['zip_sha256']:
            raise ValueError('Recovered NHR TIFF/ZIP bytes differ')
    return {
        'verified_utc': datetime.now(timezone.utc).isoformat(),
        'lane': 'H79-NHR',
        'exact_tiff_recovery': True,
        'exact_single_tiff_zip_recovery': True,
        'exact_decoded_dots_recovery': True,
        'raster_sha256': receipt['sha256'],
        'zip_sha256': receipt['zip_sha256'],
        'dots_sha256': dots_sha256,
        'positive_pixels': int(dots.sum()),
        'scientific_experiments': 0,
        'holdouts': 0,
        'dot_placements': 0,
        'slots_used': 0,
        'original_artifacts_and_run_card_not_overwritten': True,
        'archived_e1_reproduction': ARCHIVED_E1_REPRODUCTION,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lane', choices=('current', 'nhr'), default='current')
    parser.add_argument('--no-write-evidence', action='store_true')
    args = parser.parse_args(argv)
    report = reproduce_current(ROOT) if args.lane == 'current' else reproduce_nhr(ROOT)
    if args.lane == 'current' and not args.no_write_evidence:
        (ROOT / 'evidence/artifact_reproduction.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
