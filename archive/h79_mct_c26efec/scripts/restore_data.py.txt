#!/usr/bin/env python3
"""Restore SHA-256-pinned competition mirrors listed in registry/data_manifest.json.

The DrivenData files are login-walled (https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
and the Dropbox mirrors in the brief are unreachable from this sandbox, so the only working route
is the project owner's public GitHub mirrors.  Every file is integrity-pinned (sha256 computed from
restored bytes, inherited from the GEMSDOE77 template manifest) but NOT organizer-authenticated.
Fails closed on any hash mismatch.

Usage:  python scripts/restore_data.py [--ids core|all|id1,id2] [--target-dir data/raw]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_IDS = {"training_features", "labels", "existing_faults", "sample_submission"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def fetch(repo: str, ref: str, path: str, dest: Path, retries: int = 4) -> None:
    """Download one blob through the GitHub contents API (raw media type)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    hdr = ["-H", "Accept: application/vnd.github.raw"]
    tok = _token()
    if tok:
        hdr += ["-H", f"Authorization: Bearer {tok}"]
    last = None
    for attempt in range(retries):
        try:
            with tmp.open("wb") as out:
                subprocess.run(["curl", "-sSL", "--fail", "--retry", "2", *hdr, url],
                               stdout=out, check=True)
            tmp.replace(dest)
            return
        except subprocess.CalledProcessError as exc:  # pragma: no cover - network
            last = exc
            time.sleep(2 * (attempt + 1))
        finally:
            tmp.unlink(missing_ok=True)
    raise SystemExit(f"download failed for {repo}:{path}: {last}")


def restore_entry(entry: dict, root: Path) -> dict:
    dest = root / entry["dest"]
    if dest.exists() and sha256_file(dest) == entry["sha256"]:
        return {"id": entry["id"], "dest": entry["dest"], "status": "present",
                "bytes": dest.stat().st_size, "sha256": entry["sha256"]}
    if "parts" in entry:
        tmp = dest.with_suffix(".assembling")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("wb") as out:
            for part in entry["parts"]:
                p = root / "raw_parts" / Path(part).name
                fetch(entry["repo"], entry["ref"], part, p)
                with p.open("rb") as src:
                    shutil.copyfileobj(src, out, 1 << 20)
                p.unlink()
        got = sha256_file(tmp)
        if got != entry["sha256"]:
            tmp.unlink(missing_ok=True)
            raise SystemExit(f"HASH MISMATCH {entry['id']}: {got} != {entry['sha256']}")
        tmp.replace(dest)
    else:
        fetch(entry["repo"], entry["ref"], entry["path"], dest)
        got = sha256_file(dest)
        if got != entry["sha256"]:
            dest.unlink(missing_ok=True)
            raise SystemExit(f"HASH MISMATCH {entry['id']}: {got} != {entry['sha256']}")
    return {"id": entry["id"], "dest": entry["dest"], "status": "restored",
            "bytes": dest.stat().st_size, "sha256": entry["sha256"]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ids", default="all", help="'core', 'all' or comma-separated manifest ids")
    ap.add_argument("--manifest", default=str(ROOT / "registry" / "data_manifest.json"))
    ap.add_argument("--target-dir", default=str(ROOT / "data" / "raw"))
    args = ap.parse_args()
    man = json.loads(Path(args.manifest).read_text())
    root = Path(args.target_dir)
    root.mkdir(parents=True, exist_ok=True)
    if args.ids == "all":
        want = None
    elif args.ids == "core":
        want = CORE_IDS
    else:
        want = set(args.ids.split(","))
    results = []
    for e in man["files"]:
        if want is None or e["id"] in want:
            r = restore_entry(e, root)
            results.append(r)
            print(f"{r['status']:>8}  {e['dest']:70s} {r['bytes']:>11,d} B  sha256={r['sha256'][:12]}…", flush=True)
    receipt = {"schema_version": 1, "evidence_class": "INPUT-INTEGRITY",
               "organizer_authenticated": False,
               "caveat": "SHA-256-pinned public owner mirrors of login-walled DrivenData files; "
                         "pins prove mirror consistency, not organizer authentication.",
               "verified_files_count": len(results), "storage_root": str(root), "files": results}
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "restore_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Verified {len(results)} files -> data/restore_receipt.json")


if __name__ == "__main__":
    main()
