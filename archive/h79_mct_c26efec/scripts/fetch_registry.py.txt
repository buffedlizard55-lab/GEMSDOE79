#!/usr/bin/env python3
"""Fetch every prior-submission raster listed in registry/registry_index.json.

The index (inherited from the GEMSDOE77 template, built 2026-10-21T02:30Z from the
GitHub git-tree API over every buffedlizard55-lab repo whose name contains GEMSDOE)
lists 812 de-duplicated candidate rasters by git blob sha.  Each blob is fetched
through the GitHub *git blobs* API with the raw media type and stored under
``data/registry/<repo>__<basename>``; a blob whose SHA-1 does not match the index
is deleted and reported.  Files are gitignored (≈450 MB).

Usage:  python scripts/fetch_registry.py [--workers 4] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "registry"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()


def fetch_one(entry: dict, tok: str | None) -> dict:
    repo, path, blob = entry["repo"], entry["path"], entry["blob"]
    # Blob-unique local name: the same repo can hold two different rasters with the
    # same basename in different folders (found once: 812 entries -> 811 files).
    dest = OUT / f"{repo}__{blob[:10]}__{Path(path).name}"
    legacy = OUT / f"{repo}__{Path(path).name}"
    if not dest.exists() and legacy.exists() and git_blob_sha1(legacy) == blob:
        legacy.rename(dest)
    if dest.exists() and git_blob_sha1(dest) == blob:
        return {"repo": repo, "path": path, "status": "present", "file": dest.name}
    url = f"https://api.github.com/repos/buffedlizard55-lab/{repo}/git/blobs/{blob}"
    hdr = ["-H", "Accept: application/vnd.github.raw"]
    if tok:
        hdr += ["-H", f"Authorization: Bearer {tok}"]
    tmp = dest.with_suffix(dest.suffix + ".partial")
    err = None
    for attempt in range(4):
        try:
            with tmp.open("wb") as fh:
                subprocess.run(["curl", "-sSL", "--fail", *hdr, url], stdout=fh, check=True, timeout=300)
            got = git_blob_sha1(tmp)
            if got != blob:
                err = f"blob sha mismatch {got} != {blob}"
                tmp.unlink(missing_ok=True)
                break
            tmp.replace(dest)
            return {"repo": repo, "path": path, "status": "fetched", "file": dest.name,
                    "bytes": dest.stat().st_size}
        except Exception as exc:  # pragma: no cover - network
            err = str(exc)
            time.sleep(3 * (attempt + 1))
        finally:
            tmp.unlink(missing_ok=True)
    return {"repo": repo, "path": path, "status": "error", "error": err}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", default=str(ROOT / "registry" / "registry_index.json"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    idx = json.loads(Path(args.index).read_text())
    rasters = idx["rasters"]
    if args.limit:
        rasters = rasters[: args.limit]
    OUT.mkdir(parents=True, exist_ok=True)
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    results = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_one, e, tok): e for e in rasters}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            results.append(r)
            if i % 25 == 0 or r["status"] == "error":
                n_err = sum(1 for x in results if x["status"] == "error")
                print(f"[{i}/{len(rasters)}] {r['status']:8s} {r.get('file', r['path'])}  errors={n_err}  {time.time()-t0:.0f}s", flush=True)
    receipt = {
        "index_built_utc": idx.get("built_utc"),
        "index_method": idx.get("method"),
        "n_index": len(rasters),
        "n_ok": sum(1 for r in results if r["status"] in ("present", "fetched")),
        "n_error": sum(1 for r in results if r["status"] == "error"),
        "errors": [r for r in results if r["status"] == "error"],
        "storage": str(OUT),
        "seconds": round(time.time() - t0, 1),
    }
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "registry_fetch_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "errors"}, indent=2))
    if receipt["n_error"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
