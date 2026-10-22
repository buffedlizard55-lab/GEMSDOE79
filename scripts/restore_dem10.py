#!/usr/bin/env python3
"""Restore the 13 DEM10 float32 vectors from GEMSDOE10 tag
ext/dem10-36343078537 (orphan tag; owner CI run 36343078537) and verify every
vector's sha256/size against the tag's own manifest.json. Source per that
manifest: USGS 3DEP 1/3 arc-second seamless DEM (public domain),
https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5
Hash pins prove mirror consistency, not organizer authentication."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "cache" / "dem10"
REPO = "buffedlizard55-lab/GEMSDOE10"
REF = "ext/dem10-36343078537"
FILES = ["manifest.json"] + [f"dem10_{c}.f32.npy" for c in
         ["slope_max", "slope_mean", "slope_std", "hgm20_max", "hgm50_max", "hgm200_mean",
          "steep_ratio_max", "resid_std", "resid_range", "curv_absmax", "onesided",
          "onesided3", "valid_frac"]]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch_dem10_file(name: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    res = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github.raw", f"repos/{REPO}/contents/{name}?ref={REF}"],
        capture_output=True,
    )
    if res.returncode == 0 and res.stdout:
        tmp.write_bytes(res.stdout)
        tmp.replace(dest)
        return
    gitdir = ROOT / ".cache/registry_git/GEMSDOE10.git"
    if not (gitdir / "HEAD").exists():
        gitdir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "-q", "--bare", "--filter=blob:none", f"https://github.com/{REPO}.git", str(gitdir)],
            check=True,
        )
    subprocess.run(
        ["git", "--git-dir", str(gitdir), "fetch", "-q", "--filter=blob:none", "origin", f"+refs/tags/{REF}:refs/tags/{REF}"],
        check=True,
    )
    data = subprocess.run(
        ["git", "--git-dir", str(gitdir), "show", f"refs/tags/{REF}:{name}"],
        check=True,
        capture_output=True,
    ).stdout
    tmp.write_bytes(data)
    tmp.replace(dest)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        dest = DEST / name
        if not dest.exists():
            _fetch_dem10_file(name, dest)
        print(f"{name:34s} {dest.stat().st_size}")
    man = json.loads((DEST / "manifest.json").read_text())
    ok = True
    for ch, st in man["channel_stats"].items():
        p = DEST / f"{ch}.f32.npy"
        good = sha256_file(p) == st["sha256"] and p.stat().st_size == st["bytes"]
        print(f"{ch:26s} verified={good}")
        ok = ok and good
    if not ok:
        raise SystemExit("DEM10 verification FAILED")
    print("DEM10: 13/13 vectors verified against manifest")


if __name__ == "__main__":
    main()
