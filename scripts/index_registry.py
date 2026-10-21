#!/usr/bin/env python3
"""Snapshot accessible sibling prediction rasters; never change novelty thresholds.

Uses immutable Git blobs, including withdrawn and dense predictions. Historical
entries are retained even when current default branches no longer publish them.
Large datasets go to ignored .cache/, not Git. Scores in inherited metadata are
not imported as verified organizer results.
"""
from __future__ import annotations
import concurrent.futures as cf
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/registry'


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path]))


def is_prediction(path):
    p = '/' + path.lower()
    return p.endswith(('.tif', '.tiff')) and (
        any(x in p for x in ('/downloads/', '/submissions/', '/artifacts/', '/registry/rasters/'))
        or any(x in p for x in ('/evidence/lane-', '/quarantine/')))


def main():
    if (ROOT / 'evidence/experiment_state.json').exists():
        raise SystemExit('Registry snapshot is frozen for E1. Use scripts/restore_registry.py; do not rewrite scientific evidence.')
    historical_path = ROOT / 'registry/historical_index.json'
    historical = json.loads(historical_path.read_text())['rasters']
    by_blob = {}
    for row in historical:
        by_blob[row['blob']] = {**row, 'historical': True}
    text = subprocess.check_output([
        'gh', 'api', '--paginate', 'users/buffedlizard55-lab/repos?per_page=100',
        '--jq', '.[] | [.name,.default_branch] | @tsv'], text=True)
    repos = [line.split('\t') for line in text.splitlines()
             if 'GEMSDOE' in line.split('\t')[0].upper()
             and line.split('\t')[0] != 'GEMSDOE79']
    tree_dir = ROOT / '.cache/registry_trees'
    tree_dir.mkdir(parents=True, exist_ok=True)

    def scan(pair):
        repo, branch = pair
        try:
            tree = api(f'repos/buffedlizard55-lab/{repo}/git/trees/{branch}?recursive=1')
            (tree_dir / (repo + '.json')).write_text(json.dumps(tree))
            if tree.get('truncated'):
                raise ValueError('truncated tree: scope incomplete')
            rows = [{'repo': repo, 'path': r['path'], 'size': r['size'],
                     'blob': r['sha'], 'aliases': [repo + ':' + r['path']]}
                    for r in tree['tree'] if r['type'] == 'blob' and is_prediction(r['path'])]
            return {'repo': repo, 'default_branch': branch, 'tree_sha': tree['sha'],
                    'status': 'ok', 'prediction_paths': len(rows)}, rows
        except Exception as exc:
            return {'repo': repo, 'status': 'unavailable', 'error': str(exc)}, []

    receipts = []
    with cf.ThreadPoolExecutor(6) as pool:
        for rec, rows in pool.map(scan, repos):
            receipts.append(rec)
            for row in rows:
                if row['blob'] in by_blob:
                    old = by_blob[row['blob']]
                    old['aliases'] = sorted(set(old.get('aliases', []) + row['aliases']))
                else:
                    by_blob[row['blob']] = row
    result = {
        'built_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Union of historical GEMSDOE77 registry and current accessible GEMSDOE owner default-branch prediction paths; no size/density exclusions.',
        'limitations': ['Unpublished/private/removed blobs not in the historical index are not observable.',
                       'The historical index excluded some unscored files >5 MB; current snapshot does not.',
                       'New parallel runs after this timestamp are outside this snapshot.'],
        'historical_registry_sha256': hashlib.sha256(historical_path.read_bytes()).hexdigest(),
        'repositories': receipts, 'n_rasters': len(by_blob),
        'rasters': sorted(by_blob.values(), key=lambda x: x['blob'])}
    (ROOT / 'registry/registry_index.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Indexed {len(by_blob)} immutable rasters across {len(receipts)} repositories', flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    def fetch(row):
        blob = row['blob']
        dest = CACHE / (blob + '.tif')
        try:
            if not dest.exists():
                tmp = dest.with_suffix('.part')
                with tmp.open('wb') as f:
                    subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github.raw',
                                    f'repos/buffedlizard55-lab/{row["repo"]}/git/blobs/{blob}'],
                                   stdout=f, check=True)
                tmp.replace(dest)
            data = dest.read_bytes()
            got = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
            if got != blob or len(data) != row['size']:
                raise ValueError(f'Git-blob/size mismatch: {got}, {len(data)}')
            return {'blob': blob, 'status': 'verified', 'sha256': hashlib.sha256(data).hexdigest(),
                    'bytes': len(data)}
        except Exception as exc:
            return {'blob': blob, 'status': 'unavailable', 'error': str(exc)}

    rows = []
    with cf.ThreadPoolExecutor(6) as pool:
        for i, rec in enumerate(pool.map(fetch, result['rasters']), 1):
            rows.append(rec)
            if i % 100 == 0:
                print(f'Restored {i}/{len(by_blob)} registry files', flush=True)
    receipt = {'built_utc': datetime.now(timezone.utc).isoformat(),
               'files': rows, 'verified': sum(r['status'] == 'verified' for r in rows),
               'unavailable': sum(r['status'] != 'verified' for r in rows)}
    (ROOT / 'registry/registry_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'Registry restore: {receipt["verified"]} verified, {receipt["unavailable"]} unavailable', flush=True)


if __name__ == '__main__':
    main()
