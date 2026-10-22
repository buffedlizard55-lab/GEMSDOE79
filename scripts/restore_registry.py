#!/usr/bin/env python3
"""Restore the frozen registry exactly; never rescan/rewrite scientific evidence."""
from __future__ import annotations
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]
_GH_API_BLOCKED = False
_REPO_LOCKS_GUARD = threading.Lock()
_REPO_LOCKS: dict[str, threading.Lock] = {}


def _repo_lock(repo: str) -> threading.Lock:
    with _REPO_LOCKS_GUARD:
        if repo not in _REPO_LOCKS:
            _REPO_LOCKS[repo] = threading.Lock()
        return _REPO_LOCKS[repo]


def _repo_remote_url(full_repo: str) -> str:
    return f'https://github.com/{full_repo}.git'


def _ensure_bare_repo(root: Path, full_repo: str) -> Path:
    safe = full_repo.replace('/', '__')
    bare = Path(root) / '.cache' / 'git_mirrors' / f'{safe}.git'
    if not (bare / 'HEAD').exists():
        bare.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init', '--bare', '-q', str(bare)], check=True)
        subprocess.run(
            ['git', '-C', str(bare), 'remote', 'add', 'origin', _repo_remote_url(full_repo)],
            check=True,
        )
    return bare


def _batch_prefetch_repo(root: Path, repo: str, rows: list[dict], pins: dict[str, dict]) -> int:
    """Batch-fetch all missing frozen blobs for one repository over Git Smart-HTTP (zero REST quota)."""
    missing = [
        r for r in rows
        if not (Path(root) / '.cache/registry' / f"{r['blob']}.tif").is_file()
    ]
    if not missing:
        return 0
    full_repo = repo if '/' in repo else f'buffedlizard55-lab/{repo}'
    cache_dir = Path(root) / '.cache/registry'
    cache_dir.mkdir(parents=True, exist_ok=True)
    with _repo_lock(full_repo):
        bare = _ensure_bare_repo(Path(root), full_repo)
        blobs = [r['blob'] for r in missing]
        for i in range(0, len(blobs), 64):
            chunk = blobs[i:i + 64]
            to_fetch = [
                b for b in chunk
                if subprocess.run(['git', '-C', str(bare), 'cat-file', '-e', b], capture_output=True).returncode != 0
            ]
            if to_fetch:
                subprocess.run(
                    ['git', '-C', str(bare), '-c', 'gc.auto=0', 'fetch', '-q', '--no-write-fetch-head', 'origin', *to_fetch],
                    check=True,
                    capture_output=True,
                )
        fetched = 0
        for row in missing:
            dest = cache_dir / f"{row['blob']}.tif"
            if dest.is_file():
                continue
            tmp = dest.with_suffix('.batch.restoring')
            try:
                with tmp.open('wb') as out:
                    subprocess.run(['git', '-C', str(bare), 'cat-file', 'blob', row['blob']], stdout=out, check=True)
                data = tmp.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                actual_blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
                if digest != pins[row['blob']]['sha256'] or actual_blob != row['blob'] or len(data) != row['size']:
                    raise ValueError('Frozen registry SHA-256/Git-blob/size mismatch: ' + row['blob'])
                tmp.replace(dest)
                fetched += 1
            finally:
                tmp.unlink(missing_ok=True)
        return fetched


def _fetch_blob_via_git_smart_http(root: Path, repo: str, blob: str, out) -> None:
    full_repo = repo if '/' in repo else f'buffedlizard55-lab/{repo}'
    with _repo_lock(full_repo):
        bare = _ensure_bare_repo(Path(root), full_repo)
        has_blob = subprocess.run(
            ['git', '-C', str(bare), 'cat-file', '-e', blob],
            capture_output=True,
        )
        if has_blob.returncode != 0:
            subprocess.run(
                ['git', '-C', str(bare), '-c', 'gc.auto=0', 'fetch', '-q', '--depth=1', 'origin', blob],
                check=True,
            )
    subprocess.run(['git', '-C', str(bare), 'cat-file', 'blob', blob], stdout=out, check=True)


def restore_blob(root, row, pin):
    global _GH_API_BLOCKED
    dest = Path(root) / '.cache/registry' / (row['blob'] + '.tif')
    dest.parent.mkdir(parents=True, exist_ok=True)
    downloaded = not dest.exists()
    tmp = dest.with_suffix('.restoring') if downloaded else dest
    if downloaded:
        try:
            used_api = False
            if not _GH_API_BLOCKED:
                with tmp.open('wb') as out:
                    res = subprocess.run(
                        ['gh', 'api', '-H', 'Accept: application/vnd.github.raw',
                         f'repos/buffedlizard55-lab/{row["repo"]}/git/blobs/{row["blob"]}'],
                        stdout=out,
                        stderr=subprocess.PIPE,
                    )
                if res.returncode == 0:
                    used_api = True
                else:
                    _GH_API_BLOCKED = True
            if not used_api:
                with tmp.open('wb') as out:
                    _fetch_blob_via_git_smart_http(Path(root), row['repo'], row['blob'], out)
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
    by_repo: dict[str, list[dict]] = {}
    for row in index['rasters']:
        by_repo.setdefault(row['repo'], []).append(row)
    with cf.ThreadPoolExecutor(6) as pool:
        downloaded_counts = list(pool.map(lambda item: _batch_prefetch_repo(ROOT, item[0], item[1], pins), by_repo.items()))
    with cf.ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(lambda row: restore_blob(ROOT, row, pins[row['blob']]), index['rasters']))
    report = {
        'registry_files_verified': len(rows),
        'downloaded': sum(downloaded_counts) + sum(r['downloaded'] for r in rows),
        'scientific_index_and_receipt_preserved': True,
        'scientific_comparisons_performed': 0,
    }
    (ROOT / '.cache/registry_restore.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
