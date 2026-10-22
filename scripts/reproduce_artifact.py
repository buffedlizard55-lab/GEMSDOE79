#!/usr/bin/env python3
"""Deterministic private reserialization check for the canonical H79-NHR or archived E1 artifact.

No experiment, canary, holdout, placement, registry re-audit or card rewrite.
"""
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


def reproduce_nhr(root: Path = ROOT) -> dict:
    card = json.loads((root / 'run_card.json').read_text())
    build = json.loads((root / 'evidence/nhr/x1_final_build.json').read_text())
    if card['verdict'] != 'negative' or card['ok_to_submit']:
        raise ValueError('This command only recovers the existing stopped negative artifact')
    original = root / card['submission_file']
    original_receipt = json.loads(original.with_suffix('.json').read_text())
    grid = load_grid(root / 'data/reference')
    with rasterio.open(original) as ds:
        decoded = ds.read(1).astype(np.float32)
    dots = (decoded > 0) & grid.footprint & (~grid.catalogue)
    dots_sha256 = hashlib.sha256(dots.tobytes()).hexdigest()
    if dots_sha256 != build['dots_sha256']:
        raise ValueError('Decoded dots_sha256 does not match evidence/nhr/x1_final_build.json')
    cache_dots = root / '.cache/nhr/final_dots.npy'
    if cache_dots.exists():
        if hashlib.sha256(np.load(cache_dots).tobytes()).hexdigest() != dots_sha256:
            raise ValueError('Cached .cache/nhr/final_dots.npy does not match decoded dots_sha256')
    prediction = np.where(dots, np.float32(1.0), np.float32(0.0))
    with tempfile.TemporaryDirectory(prefix='g79-nhr-byte-recovery-') as tmp:
        receipt = write_submission(
            Path(tmp) / original.name,
            prediction,
            root / 'data/reference/sample_submission.tif',
            grid.footprint,
            catalogue=grid.catalogue,
            name=card['submission_name'],
            note=card['submission_note'],
            metadata=original_receipt['metadata'],
        )
        if receipt['sha256'] != card['raster_sha256'] or receipt['zip_sha256'] != original_receipt['zip_sha256']:
            raise ValueError('Recovered TIFF/ZIP bytes differ; originals and scientific receipts remain unchanged')
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
        'scope': (
            'Private deterministic reserialization of the canonical stopped H79-NHR field '
            '(with archived E1 reserialization preserved); not a new candidate or scientific evaluation.'
        ),
    }


def reproduce_e1(root: Path = ROOT) -> dict:
    card = json.loads((root / 'archive/g79_fabric_offset_e1/run_card.json').read_text())
    state = json.loads((root / 'evidence/experiment_state.json').read_text())
    if card['verdict'] != 'negative' or card['ok_to_submit'] or not state['stopped']:
        raise ValueError('This command only recovers the existing stopped negative E1 artifact')
    cache_path = root / '.cache/g79/fabric_offset_surface.npy'
    if not cache_path.exists():
        raise FileNotFoundError(
            f'Missing {cache_path.relative_to(root)}; run scripts/prepare_data.py --reproduce first'
        )
    expected = card['surface_cache_sha256']
    if hashlib.sha256(cache_path.read_bytes()).hexdigest() != expected:
        raise ValueError('Pinned feature cache changed; no new surface is authorized')
    original = root / 'archive/g79_fabric_offset_e1/downloads' / Path(card['submission_file']).name
    original_receipt = json.loads(original.with_suffix('.json').read_text())
    grid = load_grid(root / 'data/reference')
    prediction = np.load(cache_path).astype(np.float32, copy=True)
    prediction[~grid.footprint | grid.catalogue] = 0
    with tempfile.TemporaryDirectory(prefix='g79-e1-byte-recovery-') as tmp:
        receipt = write_submission(
            Path(tmp) / original.name,
            prediction,
            root / 'data/reference/sample_submission.tif',
            grid.footprint,
            catalogue=grid.catalogue,
            name=card['submission_name'],
            note=card['submission_note'],
            metadata=original_receipt['metadata'],
        )
        if receipt['sha256'] != card['raster_sha256'] or receipt['zip_sha256'] != original_receipt['zip_sha256']:
            raise ValueError('Recovered E1 TIFF/ZIP bytes differ; originals remain unchanged')
    return {
        'verified_utc': datetime.now(timezone.utc).isoformat(),
        'lane': 'G79-FABRIC-OFFSET',
        'exact_tiff_recovery': True,
        'exact_single_tiff_zip_recovery': True,
        'raster_sha256': receipt['sha256'],
        'zip_sha256': receipt['zip_sha256'],
        'scientific_experiments': 0,
        'holdouts': 0,
        'dot_placements': 0,
        'slots_used': 0,
        'original_artifacts_and_run_card_not_overwritten': True,
        'scope': 'Private deterministic reserialization of the archived E1 field; not a new candidate.',
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--lane',
        choices=('nhr', 'e1'),
        default='nhr',
        help='Which stopped artifact to reserialize in a temporary directory (default: nhr).',
    )
    parser.add_argument(
        '--no-write-evidence',
        action='store_true',
        help='Print verification JSON without updating evidence/artifact_reproduction.json.',
    )
    args = parser.parse_args(argv)
    report = reproduce_nhr(ROOT) if args.lane == 'nhr' else reproduce_e1(ROOT)
    if args.lane == 'nhr' and not args.no_write_evidence:
        (ROOT / 'evidence/artifact_reproduction.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
