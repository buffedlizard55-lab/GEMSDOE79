#!/usr/bin/env python3
"""Convert registry/registry_index.json (GitHub blob inventory) into the inventory schema the
shared template's ``gems57.uniqueness.compare_array_to_registry`` consumes:

    {"rasters": [{"repo_first", "sources", "cache_file", "sha256"}], "complete_accessible_scan", "errors"}

Every local file is re-hashed (git blob SHA-1 must equal the index blob; SHA-256 recorded)
so the uniqueness audit is pinned byte-for-byte.  Output: registry/registry_inventory.json
"""
from __future__ import annotations
import hashlib, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_registry import git_blob_sha1  # noqa: E402

IDX = ROOT / "registry" / "registry_index.json"
OUT = ROOT / "registry" / "registry_inventory.json"
STORE = ROOT / "data" / "registry"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> None:
    idx = json.loads(IDX.read_text())
    rasters, errors = [], []
    scored = {s["blob"]: s for s in idx.get("scored", []) if "blob" in s}
    t0 = time.time()
    for e in idx["rasters"]:
        f = STORE / f"{e['repo']}__{e['blob'][:10]}__{Path(e['path']).name}"
        if not f.exists():
            errors.append(f"missing {f.name}")
            continue
        if git_blob_sha1(f) != e["blob"]:
            errors.append(f"blob mismatch {f.name}")
            continue
        row = {"repo_first": e["repo"], "sources": e.get("aliases") or [f"{e['repo']}:{e['path']}"],
               "cache_file": str(f.relative_to(ROOT)), "sha256": sha256(f), "git_blob": e["blob"],
               "bytes": f.stat().st_size}
        if e["blob"] in scored:
            sc = scored[e["blob"]]
            row["organizer_confirmed_public_score"] = sc.get("public_score")
            row["scored_as"] = sc.get("submission_name")
            row["scored_site_repo"] = sc.get("site_repo")
        rasters.append(row)
    inv = {"schema": "gems57-uniqueness-inventory-v1", "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "source_index": str(IDX.relative_to(ROOT)), "source_index_built_utc": idx.get("built_utc"),
           "method": idx.get("method"), "rasters": rasters,
           "complete_accessible_scan": not errors and len(rasters) == len(idx["rasters"]),
           "errors": errors, "n_rasters": len(rasters), "seconds": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(inv, indent=1) + "\n")
    print(json.dumps({k: v for k, v in inv.items() if k != "rasters"}, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
