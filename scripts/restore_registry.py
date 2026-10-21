#!/usr/bin/env python3
"""Restore the frozen registry exactly; never rescan/rewrite scientific evidence."""
from __future__ import annotations
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def restore_blob(root, row, pin):
    dest = Path(root) / '.cache/registry' / (row['blob'] + '.tif')
    dest.parent.mkdir(parents=True, exist_ok=True)
    downloaded = not dest.exists()
    tmp = dest.with_suffix('.restoring') if downloaded else dest
    if downloaded:
        try:
            with tmp.open('wb') as out:
                subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github.raw',
                                f'repos/buffedlizard55-lab/{row["repo"]}/git/blobs/{row["blob"]}'],
                               stdout=out, check=True)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        data = tmp.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
        if digest != pin['sha256'] or blob != row['blob'] or len(data) != row['size']:
            raise ValueError('Frozen registry SHA-256/Git-blob/size mismatch: ' + row['blob'])
        if downloaded:
            tmp.replace(dest)
        return {'blob': row['blob'], 'sha256': digest, 'verified': True, 'downloaded': downloaded}
    finally:
        if downloaded:
            tmp.unlink(missing_ok=True)


def main():
    index = json.loads((ROOT / 'registry/registry_index.json').read_text())
    receipt = json.loads((ROOT / 'registry/registry_receipt.json').read_text())
    pins = {r['blob']: r for r in receipt['files'] if r['status'] == 'verified'}
    if set(pins) != {r['blob'] for r in index['rasters']}:
        raise ValueError('Incomplete original registry receipt; no new inventory is authorized')
    with cf.ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(lambda row: restore_blob(ROOT, row, pins[row['blob']]), index['rasters']))
    report = {'registry_files_verified': len(rows), 'downloaded': sum(r['downloaded'] for r in rows),
              'scientific_index_and_receipt_preserved': True, 'scientific_comparisons_performed': 0}
    (ROOT / '.cache/registry_restore.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
