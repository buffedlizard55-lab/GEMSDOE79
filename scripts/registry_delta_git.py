#!/usr/bin/env python3
"""Find prediction rasters published after the frozen registry index (git protocol).

The frozen index (registry/registry_index.json, built 2026-10-21T21:46Z) is never
rewritten. This script lists every prediction-path blob reachable from any ref of
every indexed owner repository (plus any extra repo names given on the command
line), downloads blobs that are not in the frozen index into .cache/registry/,
and writes registry/registry_delta.json with Git blob ids and SHA-256 values.
It uses git (not the REST API), so a shared API quota cannot silently truncate it.
"""
from __future__ import annotations
import concurrent.futures as cf
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from index_registry import is_prediction  # noqa: E402  (same path filter as the frozen index)

OWNER = "buffedlizard55-lab"


def git(gitdir, *args, binary=False):
    r = subprocess.run(["git", "--git-dir", str(gitdir), *args], check=True, capture_output=True)
    return r.stdout if binary else r.stdout.decode()


def scan(repo: str, known: set[str]) -> dict:
    gitdir = ROOT / ".cache/registry_git" / (repo + ".git")
    try:
        if not gitdir.exists():
            gitdir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none",
                            f"https://github.com/{OWNER}/{repo}.git", str(gitdir)],
                           check=True, capture_output=True)
        # branches, tags AND pull-request heads (squash-merged branch blobs live there)
        git(gitdir, "fetch", "-q", "--filter=blob:none", "origin",
            "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*", "+refs/pull/*:refs/pull/*")
        heads = git(gitdir, "for-each-ref", "--format=%(refname) %(objectname)").split("\n")
        # IR-79-69: ``rev-list --objects --missing=allow-promisor`` silently OMITS
        # missing blobs in a blobless clone, so it never listed any raster. Trees
        # are present locally; ``log --raw`` reads (blob id, path) from them.
        out = git(gitdir, "log", "--all", "--raw", "--no-abbrev", "--no-renames", "--format=")
    except subprocess.CalledProcessError as e:
        return {"repo": repo, "status": "error", "error": (e.stderr or b"").decode()[-300:], "new": []}
    seen, new = set(), []
    for line in out.splitlines():
        if not line.startswith(":") or "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        fields = meta.split()
        if len(fields) < 5 or set(fields[3]) == {"0"} or not is_prediction(path):
            continue
        sha = fields[3]
        if sha in known or sha in seen:
            continue
        seen.add(sha)
        data = git(gitdir, "cat-file", "blob", sha, binary=True)
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if blob != sha:
            return {"repo": repo, "status": "error", "error": f"blob id mismatch {sha}", "new": []}
        dest = ROOT / ".cache/registry" / (sha + ".tif")
        dest.write_bytes(data)
        new.append({"repo": repo, "path": path, "blob": sha, "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(), "aliases": [repo + ":" + path]})
    return {"repo": repo, "status": "ok", "refs": len([h for h in heads if h]), "new": new}


def main():
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    known = {r["blob"] for r in index["rasters"]}
    repos = sorted({r["repo"] for r in index["repositories"]} | set(sys.argv[1:]))
    rows, statuses = [], []
    with cf.ThreadPoolExecutor(4) as pool:
        for res in pool.map(lambda r: scan(r, known), repos):
            statuses.append({k: v for k, v in res.items() if k != "new"})
            rows.extend(res["new"])
            print(res["repo"], res["status"], len(res["new"]), flush=True)
    dedup = {}
    for r in rows:
        if r["blob"] in dedup:
            dedup[r["blob"]]["aliases"] += r["aliases"]
        else:
            dedup[r["blob"]] = r
    delta = {"built_utc": datetime.now(timezone.utc).isoformat(),
             "base_index_built_utc": index["built_utc"],
             "method": "blobless git clones incl. refs/heads, refs/tags, refs/pull; git log --all --raw --no-abbrev --no-renames (IR-79-69: rev-list --missing=allow-promisor omitted missing blobs); same is_prediction() filter",
             "repositories": statuses, "n_new_rasters": len(dedup),
             "rasters": sorted(dedup.values(), key=lambda r: (r["repo"], r["path"]))}
    (ROOT / "registry/registry_delta.json").write_text(json.dumps(delta, indent=2) + "\n")
    errs = [s for s in statuses if s["status"] != "ok"]
    print(json.dumps({"new_rasters": len(dedup), "repo_errors": errs}, indent=2))
    if errs:
        sys.exit(1)


if __name__ == "__main__":
    main()
