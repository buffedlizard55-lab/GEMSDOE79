#!/usr/bin/env python3
"""Restore frozen registry blobs over the git protocol (no REST API quota).

Same verification contract as scripts/restore_registry.py: every file must match
its pinned SHA-256, its Git blob id and its byte size, otherwise it is deleted
and the script fails.  Uses blobless partial clones under .cache/registry_git/;
missing blobs are fetched lazily by ``git cat-file``.  Added in session
337ac1e9 because parallel sessions exhausted the shared REST API quota.
"""
from __future__ import annotations
import concurrent.futures as cf
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"


def verify(data: bytes, row: dict, pin: dict) -> None:
    digest = hashlib.sha256(data).hexdigest()
    blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if digest != pin["sha256"] or blob != row["blob"] or len(data) != row["size"]:
        raise ValueError("Frozen registry SHA-256/Git-blob/size mismatch: " + row["blob"])


def restore_repo(repo: str, rows: list[dict], pins: dict) -> dict:
    gitdir = ROOT / ".cache/registry_git" / (repo + ".git")
    if not gitdir.exists():
        gitdir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none",
                        f"https://github.com/{OWNER}/{repo}.git", str(gitdir)], check=True)
    done = 0
    for row in rows:
        dest = ROOT / ".cache/registry" / (row["blob"] + ".tif")
        if dest.exists():
            continue
        data = subprocess.run(["git", "--git-dir", str(gitdir), "cat-file", "blob", row["blob"]],
                              check=True, capture_output=True).stdout
        verify(data, row, pins[row["blob"]])
        tmp = dest.with_suffix(".restoring")
        tmp.write_bytes(data)
        tmp.replace(dest)
        done += 1
    return {"repo": repo, "restored": done}


def main() -> None:
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    (ROOT / ".cache/registry").mkdir(parents=True, exist_ok=True)
    by_repo: dict[str, list[dict]] = {}
    for row in index["rasters"]:
        if not (ROOT / ".cache/registry" / (row["blob"] + ".tif")).exists():
            by_repo.setdefault(row["repo"], []).append(row)
    print(f"missing blobs: {sum(map(len, by_repo.values()))} in {len(by_repo)} repos", flush=True)
    errors = []
    with cf.ThreadPoolExecutor(4) as pool:
        futs = {pool.submit(restore_repo, r, rows, pins): r for r, rows in by_repo.items()}
        for f in cf.as_completed(futs):
            try:
                print(json.dumps(f.result()), flush=True)
            except Exception as e:  # report and continue; final check fails closed
                errors.append(f"{futs[f]}: {e}")
                print("ERROR", futs[f], e, flush=True)
    present = sum((ROOT / ".cache/registry" / (r["blob"] + ".tif")).exists() for r in index["rasters"])
    # re-verify every file on disk, including ones restored by other tools
    bad = []
    for row in index["rasters"]:
        p = ROOT / ".cache/registry" / (row["blob"] + ".tif")
        if p.exists():
            try:
                verify(p.read_bytes(), row, pins[row["blob"]])
            except ValueError as e:
                bad.append(str(e)); p.unlink()
    report = {"registry_rasters": len(index["rasters"]), "present_and_verified": present - len(bad),
              "errors": errors, "hash_failures": bad}
    (ROOT / ".cache/registry_restore_git.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if errors or bad or present - len(bad) != len(index["rasters"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
