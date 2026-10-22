#!/usr/bin/env python3
"""Verify reusable cached inputs, then compute the preregistered E1 transforms."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems57.grid import load_grid
from gems79.features import build


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reproduce', action='store_true', help='Verify/recover the exact deterministic E1 cache without reopening the stopped experiment')
    args = ap.parse_args()
    prereg = ROOT / 'registry/preregistration.json'
    assert digest(prereg) == (ROOT / 'evidence/preregistration_sha256.txt').read_text().strip(), 'preregistration drift'
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    used = {'training_features', 'existing_faults', 'sample_submission'}
    for row in manifest['files']:
        if row['id'] in used:
            p = ROOT / 'data/raw' / row['dest']
            if digest(p) != row['sha256']:
                raise ValueError(f'cached input hash mismatch: {p}')
    out = ROOT / '.cache/g79'
    receipt_path = ROOT / 'evidence/feature_cache.json'
    previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
    if previous and not args.reproduce:
        raise FileExistsError('E1 cache already exists; do not silently retune an experiment')
    if args.reproduce and not previous:
        raise FileNotFoundError('No pinned E1 cache receipt to reproduce')
    if previous and all((out / (r['name'] + '.npy')).exists() and
                        digest(out / (r['name'] + '.npy')) == r['sha256'] for r in previous['files']):
        print('All deterministic E1 cache bytes match the existing receipt; no experiment restarted.')
        return
    grid = load_grid(ROOT / 'data/raw')
    result = build(ROOT / 'data/raw/training_features.tif', grid.footprint, out)
    result['generated_utc'] = datetime.now(timezone.utc).isoformat()
    result['source_feature_stack_sha256'] = digest(ROOT / 'data/raw/training_features.tif')
    result['preregistration_sha256'] = digest(prereg)
    result['files'] = [{'name': p.stem, 'sha256': digest(p), 'bytes': p.stat().st_size}
                       for p in sorted(out.glob('*.npy'))]
    if previous:
        expected = {r['name']: r['sha256'] for r in previous['files']}
        actual = {r['name']: r['sha256'] for r in result['files']}
        if actual != expected:
            raise ValueError('Reproduced transform hashes differ: no new receipt or experiment is authorized')
        print('Recovered exact deterministic E1 cache bytes. Existing scientific receipt preserved.')
        return
    receipt_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
