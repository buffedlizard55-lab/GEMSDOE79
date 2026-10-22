#!/usr/bin/env python3
"""Re-measure the frozen stop witness, never restart the stopped experiment.

Only --restore uses the network, fetching one hash-pinned historical Git blob.
No inventory rescan, feature generation, placement, holdout, or receipt rewrite.
Output is a new software-review record, not a scientific run card or clearance.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems57.grid import load_grid
from gems57.uniqueness import saturation_certificate
from gems79.novelty import UNIVERSAL_WITNESS_BLOB
from restore_registry import restore_blob


def require_unique_rows(rows, key, required, label):
    """Reject missing/duplicate trust anchors before inspecting scientific bytes."""
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f'{label} must be a list of objects')
    for identity in required:
        if sum(row.get(key) == identity for row in rows) != 1:
            raise ValueError(f'{label} requires exactly one {identity}')


def verify_witness(root=ROOT, *, restore=False):
    root = Path(root)
    pins = json.loads((root / 'registry/template_pin.json').read_text())
    require_unique_rows(pins['files'], 'path',
                        ('vendor/gems57/grid.py', 'vendor/gems57/uniqueness.py'),
                        'Shared template pins')
    for row in pins['files']:
        if hashlib.sha256((root / row['path']).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Shared template pin mismatch')
    inputs = json.loads((root / 'registry/data_manifest.json').read_text())
    require_unique_rows(inputs['files'], 'id',
                        ('existing_faults', 'sample_submission'), 'Reference grid pins')
    for row in inputs['files']:
        if row['id'] in ('existing_faults', 'sample_submission'):
            # Pin the files load_grid actually reads, not an arbitrary alternate
            # file supplied by a malformed manifest (including path traversal).
            if row.get('dest') != row['id'] + '.tif':
                raise ValueError('Reference grid pin destination mismatch')
            path = root / 'data/reference' / row['dest']
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('Reference grid pin mismatch')
    index = json.loads((root / 'registry/registry_index.json').read_text())
    receipt = json.loads((root / 'registry/registry_receipt.json').read_text())
    row, = [r for r in index['rasters'] if r['blob'] == UNIVERSAL_WITNESS_BLOB]
    pin, = [r for r in receipt['files'] if r['blob'] == UNIVERSAL_WITNESS_BLOB and r['status'] == 'verified']
    if restore:
        restore_blob(root, row, pin)
    path = root / '.cache/registry' / (row['blob'] + '.tif')
    data = path.read_bytes()
    if (hashlib.sha256(data).hexdigest() != pin['sha256'] or len(data) != row['size'] or
            hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest() != row['blob']):
        raise ValueError('Frozen witness SHA-256/Git-blob/size mismatch')
    grid = load_grid(root / 'data/reference')
    measured = saturation_certificate(path, grid.footprint, grid.catalogue,
                                    expected_grid=(grid.shape, grid.crs, grid.transform))
    original = json.loads((root / 'evidence/universal_overlap_certificate.json').read_text())
    # Path serialization differs by checkout; compare every other measured field.
    keys = set(measured) - {'witness_file'}
    checks = {key: measured[key] == original.get(key) for key in sorted(keys)}
    return {'reviewed_utc': datetime.now(timezone.utc).isoformat(),
            'evidence_class': 'REGISTRY-MEASUREMENT',
            'all_checks_passed': all(checks.values()), 'checks': checks,
            'measured_certificate': measured,
            'scientific_experiments_performed': 0,
            'submission_slots_used': 0,
            'scope': 'Recovery and re-measurement of one frozen rejection witness, not a complete inventory audit, new experiment or organizer acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--report', type=Path, help='New output only; refuses to overwrite any evidence')
    args = parser.parse_args()
    report = verify_witness(restore=args.restore)
    text = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.report:
        with args.report.open('x') as stream:
            stream.write(text)
    print(text, end='')
    return 0 if report['all_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
