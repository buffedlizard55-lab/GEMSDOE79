#!/usr/bin/env python3
"""Find prediction rasters published after the frozen registry index (git protocol).

The frozen index (registry/registry_index.json, built 2026-10-21T21:46Z) is never
rewritten. This script scans all accessible non-self GEMS* owner repositories
(including newly created repositories beyond the original 84-repo snapshot),
walks unique root Git trees reachable from any branch, tag, or pull-request ref
via `git ls-tree -r -z` (avoiding the `--filter=blob:none` +
`git rev-list --all --objects --missing=allow-promisor` pitfall where missing
promisor blobs are emitted as `?<oid>` without file paths), batch-fetches any
new prediction blobs over Git Smart-HTTP (zero REST API quota), verifies both
Git blob SHA-1 and SHA-256 digests, caches bytes under `.cache/registry/`, and
writes `registry/registry_delta.json`.
"""
from __future__ import annotations
import concurrent.futures as cf
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from index_registry import is_prediction  # noqa: E402  (same path filter as the frozen index)

OWNER = "buffedlizard55-lab"
SELF_REPO = "GEMSDOE79"


def git(gitdir: Path, *args: str, binary: bool = False):
    r = subprocess.run(["git", "--git-dir", str(gitdir), *args], check=True, capture_output=True)
    return r.stdout if binary else r.stdout.decode()


def discover_owner_repos(index: dict, extra: list[str] | set[str] = ()) -> list[str]:
    repos = {r["repo"] for r in index["repositories"] if r["repo"] != SELF_REPO}
    repos |= {r for r in extra if r and r != SELF_REPO}
    try:
        out = subprocess.check_output(
            [
                "gh",
                "api",
                "--paginate",
                f"users/{OWNER}/repos?per_page=100",
                "--jq",
                ".[].name",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        for line in out.splitlines():
            name = line.strip()
            if name and "GEMS" in name.upper() and name != SELF_REPO:
                repos.add(name)
    except Exception:
        pass
    return sorted(repos)


def scan_gitdir(gitdir: Path, repo: str, known: set[str], cache_dir: Path | None = None) -> dict:
    """Scan an already-fetched bare/blobless Git repository for prediction blobs not in `known`."""
    cache_dir = cache_dir if cache_dir is not None else (ROOT / ".cache/registry")
    cache_dir.mkdir(parents=True, exist_ok=True)
    heads = [
        h for h in git(gitdir, "for-each-ref", "--format=%(refname) %(objectname)").splitlines() if h
    ]
    if not heads:
        return {"repo": repo, "status": "ok", "refs": 0, "new": []}

    # Walk unique root trees across ALL commits/refs. Unlike
    # `git rev-list --all --objects --missing=allow-promisor` (which prints
    # missing promisor blobs as `?<oid>` with NO file path!), tree objects are
    # always present in `--filter=blob:none` clones and expose every `(sha, path)`
    # across all branches, tags, and pull-request heads.
    root_trees = list(dict.fromkeys(
        t.strip() for t in git(gitdir, "rev-list", "--all", "--format=%T").splitlines()
        if len(t.strip()) == 40
    ))
    candidates: dict[str, set[str]] = {}
    seen_paths_by_tree = set(root_trees)
    for tree_sha in seen_paths_by_tree:
        raw = git(gitdir, "ls-tree", "-r", "-z", tree_sha, binary=True)
        for entry in raw.split(b"\0"):
            if not entry:
                continue
            meta, path_bytes = entry.split(b"\t", 1)
            parts = meta.decode().split()
            if len(parts) < 3 or parts[1] != "blob":
                continue
            blob_sha = parts[2]
            rel_path = path_bytes.decode("utf-8", errors="replace")
            if not is_prediction(rel_path) or blob_sha in known:
                continue
            candidates.setdefault(blob_sha, set()).add(rel_path)

    new = []
    for sha in sorted(candidates):
        dest = cache_dir / f"{sha}.tif"
        if dest.is_file():
            data = dest.read_bytes()
        else:
            try:
                data = git(gitdir, "cat-file", "blob", sha, binary=True)
            except subprocess.CalledProcessError:
                subprocess.run(
                    [
                        "git", "--git-dir", str(gitdir), "-c", "gc.auto=0",
                        "fetch", "-q", "--no-write-fetch-head", "origin", sha,
                    ],
                    check=True,
                    capture_output=True,
                )
                data = git(gitdir, "cat-file", "blob", sha, binary=True)
        actual_blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if actual_blob != sha:
            return {"repo": repo, "status": "error", "error": f"blob id mismatch {sha}", "new": []}
        if not dest.is_file():
            tmp = dest.with_suffix(".delta.tmp")
            tmp.write_bytes(data)
            tmp.replace(dest)
        paths_sorted = sorted(candidates[sha])
        new.append({
            "repo": repo,
            "path": paths_sorted[0],
            "blob": sha,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "aliases": [f"{repo}:{p}" for p in paths_sorted],
        })
    return {"repo": repo, "status": "ok", "refs": len(heads), "new": new}


def scan(repo: str, known: set[str], remote_url: str | None = None, cache_dir: Path | None = None) -> dict:
    gitdir = ROOT / ".cache/registry_git" / (repo + ".git")
    url = remote_url or f"https://github.com/{OWNER}/{repo}.git"
    try:
        if not (gitdir / "HEAD").exists():
            gitdir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "-q", "--bare", "--filter=blob:none", url, str(gitdir)],
                check=True,
                capture_output=True,
            )
        git(
            gitdir, "-c", "gc.auto=0", "fetch", "-q", "--filter=blob:none", "origin",
            "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*", "+refs/pull/*:refs/pull/*",
        )
        return scan_gitdir(gitdir, repo, known, cache_dir=cache_dir)
    except subprocess.CalledProcessError as e:
        return {"repo": repo, "status": "error", "error": (e.stderr or b"").decode()[-300:], "new": []}


def restore_pinned_delta(delta_path: Path | None = None, cache_dir: Path | None = None) -> dict:
    """Restore and SHA-256/blob-SHA1 verify all pinned rasters in registry/registry_delta.json."""
    delta_path = delta_path or (ROOT / "registry/registry_delta.json")
    cache_dir = cache_dir or (ROOT / ".cache/registry")
    cache_dir.mkdir(parents=True, exist_ok=True)
    delta = json.loads(delta_path.read_text())
    by_repo: dict[str, list[dict]] = {}
    for row in delta["rasters"]:
        dest = cache_dir / f"{row['blob']}.tif"
        if not dest.is_file():
            by_repo.setdefault(row["repo"], []).append(row)
    errors: list[str] = []
    for repo, rows in sorted(by_repo.items()):
        gitdir = ROOT / ".cache/registry_git" / f"{repo}.git"
        try:
            if not (gitdir / "HEAD").exists():
                gitdir.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ["git", "clone", "-q", "--bare", "--filter=blob:none",
                     f"https://github.com/{OWNER}/{repo}.git", str(gitdir)],
                    check=True,
                    capture_output=True,
                )
            git(
                gitdir, "-c", "gc.auto=0", "fetch", "-q", "--filter=blob:none", "origin",
                "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*", "+refs/pull/*:refs/pull/*",
            )
            for row in rows:
                data = git(gitdir, "cat-file", "blob", row["blob"], binary=True)
                if hashlib.sha256(data).hexdigest() != row["sha256"]:
                    raise ValueError(f"SHA-256 mismatch for {row['blob']}")
                dest = cache_dir / f"{row['blob']}.tif"
                tmp = dest.with_suffix(".delta.tmp")
                tmp.write_bytes(data)
                tmp.replace(dest)
        except Exception as exc:
            errors.append(f"{repo}: {exc}")
    verified = 0
    for row in delta["rasters"]:
        p = cache_dir / f"{row['blob']}.tif"
        if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == row["sha256"]:
            verified += 1
    return {"delta_rasters": len(delta["rasters"]), "verified": verified, "errors": errors}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--restore-only" in argv:
        res = restore_pinned_delta()
        print(json.dumps(res, indent=2))
        return 1 if res["errors"] or res["verified"] != res["delta_rasters"] else 0
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    known = {r["blob"] for r in index["rasters"]}
    repos = discover_owner_repos(index, argv)
    rows, statuses = [], []
    with cf.ThreadPoolExecutor(6) as pool:
        for res in pool.map(lambda r: scan(r, known), repos):
            statuses.append({k: v for k, v in res.items() if k != "new"})
            rows.extend(res["new"])
            print(res["repo"], res["status"], len(res["new"]), flush=True)
    dedup = {}
    for r in rows:
        if r["blob"] in dedup:
            merged_aliases = sorted(set(dedup[r["blob"]]["aliases"]) | set(r["aliases"]))
            dedup[r["blob"]]["aliases"] = merged_aliases
        else:
            dedup[r["blob"]] = dict(r)
    delta = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "base_index_built_utc": index["built_utc"],
        "method": (
            "blobless git clones across all accessible non-self GEMS* owner repositories "
            "incl. refs/heads, refs/tags, refs/pull; unique root-tree ls-tree -r -z traversal "
            "(fixing promisor ?<oid> path omission in rev-list --missing=allow-promisor); "
            "batched Git Smart-HTTP blob verification; same is_prediction() filter"
        ),
        "repositories": statuses,
        "n_repositories_scanned": len(statuses),
        "n_new_rasters": len(dedup),
        "rasters": sorted(dedup.values(), key=lambda r: (r["repo"], r["path"], r["blob"])),
    }
    (ROOT / "registry/registry_delta.json").write_text(json.dumps(delta, indent=2) + "\n")
    errs = [s for s in statuses if s["status"] != "ok"]
    print(json.dumps({
        "n_repositories_scanned": len(statuses),
        "new_rasters": len(dedup),
        "repo_errors": errs,
    }, indent=2))
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
