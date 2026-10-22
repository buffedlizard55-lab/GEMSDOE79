#!/usr/bin/env python3
"""Find prediction rasters published after the frozen registry index (git protocol).

The frozen index (registry/registry_index.json, built 2026-10-21T21:46Z) is never
rewritten. This script lists every prediction-path blob reachable from any ref of
every indexed owner repository (plus any extra repo names given on the command
line, excluding self repo GEMSDOE79), downloads blobs that are not in the frozen
index into .cache/registry/, and writes registry/registry_delta.json with Git blob
ids and SHA-256 values.

IR-79-59 fix: ``git rev-list --all --objects --missing=allow-promisor`` on a
blobless ``--filter=blob:none`` clone silently skips unhydrated blobs and returns
zero new rasters even when branches/PRs contain new ``.tif`` predictions. Instead,
enumerate unique root trees across all refs/commits via ``git rev-list --all
--format=%T`` and run ``git ls-tree -r`` per unique tree (hydrating only tree
objects), then fetch each newly discovered prediction ``.tif`` blob individually.
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
from index_registry import is_prediction  # noqa: E402

OWNER = "buffedlizard55-lab"
RAW_INPUT_NAMES = {
    "existing_faults.tif",
    "labels.tif",
    "sample_submission.tif",
    "training_features.tif",
    "lidar_scarp_features_u8.tif",
    "geodawn_rad_u8.tif",
    "geodawn_extensions_u8.tif",
    "derived_sgmc_faults_100m_u8.tif",
    "tiger_road_distance_m.tif",
}


def is_candidate_tif(path: str) -> bool:
    name = Path(path).name.lower()
    if name in RAW_INPUT_NAMES:
        return False
    if is_prediction(path):
        return True
    p = "/" + path.lower()
    return p.endswith((".tif", ".tiff")) and any(
        x in p for x in ("/archive/", "/outputs/", "/candidates/", "/e2_downloads/", "/public/", "/site/")
    )


def git(gitdir, *args, binary=False):
    r = subprocess.run(["git", "--git-dir", str(gitdir), *args], check=True, capture_output=True)
    return r.stdout if binary else r.stdout.decode()


def scan(repo: str, known: set[str]) -> dict:
    gitdir = ROOT / ".cache/registry_git" / (repo + ".git")
    try:
        if not gitdir.exists():
            gitdir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "-q", "--bare", "--filter=blob:none",
                 f"https://github.com/{OWNER}/{repo}.git", str(gitdir)],
                check=True, capture_output=True,
            )
        git(gitdir, "fetch", "-q", "--filter=blob:none", "origin",
            "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*", "+refs/pull/*:refs/pull/*")
        heads = [h for h in git(gitdir, "for-each-ref", "--format=%(refname) %(objectname)").splitlines() if h]
        if not heads:
            return {"repo": repo, "status": "ok", "refs": 0, "unique_trees": 0, "new": []}
        trees = sorted({
            line.strip()
            for line in git(gitdir, "rev-list", "--all", "--format=%T").splitlines()
            if line and not line.startswith("commit ")
        })
        entries: list[tuple[str, str]] = []
        for tree in trees:
            for line in git(gitdir, "ls-tree", "-r", tree).splitlines():
                meta, sep, path = line.partition("\t")
                if not sep or not is_candidate_tif(path):
                    continue
                parts = meta.split()
                if len(parts) == 3 and parts[1] == "blob":
                    entries.append((parts[2], path))
    except subprocess.CalledProcessError as e:
        return {"repo": repo, "status": "error", "error": (e.stderr or b"").decode()[-300:], "new": []}
    seen: dict[str, set[str]] = {}
    first_path: dict[str, str] = {}
    for sha, path in entries:
        if sha in known:
            continue
        seen.setdefault(sha, set()).add(f"{repo}:{path}")
        first_path.setdefault(sha, path)
    new = []
    for sha, aliases in sorted(seen.items()):
        dest = ROOT / ".cache/registry" / (sha + ".tif")
        if dest.exists():
            data = dest.read_bytes()
        else:
            data = git(gitdir, "cat-file", "blob", sha, binary=True)
            dest.write_bytes(data)
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if blob != sha:
            return {"repo": repo, "status": "error", "error": f"blob id mismatch {sha}", "new": []}
        new.append({
            "repo": repo,
            "path": first_path[sha],
            "blob": sha,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "aliases": sorted(aliases),
        })
    return {"repo": repo, "status": "ok", "refs": len(heads), "unique_trees": len(trees), "new": new}


def main():
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    known = {r["blob"] for r in index["rasters"]}
    repos = sorted(
        ({r["repo"] for r in index["repositories"]} | set(sys.argv[1:])) - {"GEMSDOE79"}
    )
    rows, statuses = [], []
    with cf.ThreadPoolExecutor(4) as pool:
        for res in pool.map(lambda r: scan(r, known), repos):
            statuses.append({k: v for k, v in res.items() if k != "new"})
            rows.extend(res["new"])
            if res["new"] or res["status"] != "ok":
                print(res["repo"], res["status"], len(res["new"]), flush=True)
    dedup = {}
    for r in rows:
        if r["blob"] in dedup:
            dedup[r["blob"]]["aliases"] = sorted(set(dedup[r["blob"]]["aliases"]) | set(r["aliases"]))
        else:
            dedup[r["blob"]] = r
    delta = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "base_index_built_utc": index["built_utc"],
        "method": "blobless git clones incl. refs/heads, refs/tags, refs/pull; rev-list --all --format=%T + ls-tree -r; prediction + archive .tif filter (IR-79-59 fix)",
        "repositories": statuses,
        "n_new_rasters": len(dedup),
        "rasters": sorted(dedup.values(), key=lambda r: (r["repo"], r["path"])),
    }
    (ROOT / "registry/registry_delta.json").write_text(json.dumps(delta, indent=2) + "\n")
    errs = [s for s in statuses if s["status"] != "ok"]
    print(json.dumps({"n_repos": len(repos), "new_rasters": len(dedup), "repo_errors": errs}, indent=2))
    if errs:
        sys.exit(1)


if __name__ == "__main__":
    main()
