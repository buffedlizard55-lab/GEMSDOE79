#!/usr/bin/env python3
"""Repackage the exact stopped E1 field privately and verify identical bytes.

No experiment, canary, holdout, placement, registry re-audit or card rewrite.
Requires the frozen feature cache restored with prepare_data.py --reproduce.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
from gems57.grid import load_grid
from gems57.submission_writer import write_submission


def main():
    card = json.loads((ROOT / 'run_card.json').read_text())
    state = json.loads((ROOT / 'evidence/experiment_state.json').read_text())
    if card['verdict'] != 'negative' or card['ok_to_submit'] or not state['stopped']:
        raise ValueError('This command only recovers the existing stopped negative artifact')
    cache_path = ROOT / '.cache/g79/fabric_offset_surface.npy'
    expected = card['surface_cache_sha256']
    if hashlib.sha256(cache_path.read_bytes()).hexdigest() != expected:
        raise ValueError('Pinned feature cache changed; no new surface is authorized')
    original = ROOT / card['submission_file']
    original_receipt = json.loads(original.with_suffix('.json').read_text())
    grid = load_grid(ROOT / 'data/reference')
    prediction = np.load(cache_path).astype(np.float32, copy=True)
    prediction[~grid.footprint | grid.catalogue] = 0
    with tempfile.TemporaryDirectory(prefix='g79-byte-recovery-') as tmp:
        receipt = write_submission(Path(tmp) / original.name, prediction,
                                   ROOT / 'data/reference/sample_submission.tif', grid.footprint,
                                   catalogue=grid.catalogue, name=card['submission_name'],
                                   note=card['submission_note'], metadata=original_receipt['metadata'])
        if receipt['sha256'] != card['raster_sha256'] or receipt['zip_sha256'] != original_receipt['zip_sha256']:
            raise ValueError('Recovered TIFF/ZIP bytes differ; originals and scientific receipts remain unchanged')
    report = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'exact_tiff_recovery': True,
              'exact_single_tiff_zip_recovery': True, 'raster_sha256': receipt['sha256'],
              'zip_sha256': receipt['zip_sha256'], 'scientific_experiments': 0,
              'holdouts': 0, 'dot_placements': 0, 'slots_used': 0,
              'original_artifacts_and_run_card_not_overwritten': True,
              'scope': 'Private deterministic reserialization of the existing stopped field; not a new candidate or scientific evaluation.'}
    (ROOT / 'evidence/artifact_reproduction.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
