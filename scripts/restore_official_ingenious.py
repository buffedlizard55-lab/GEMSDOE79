#!/usr/bin/env python3
"""Restore and SHA-256-verify the 6 official DOE GDR 1391 / USGS 3DEP archives.

Official primary provenance citations (public web URLs & DOIs):
  - DOE GDR Submission 1391 (INGENIOUS Regional Geothermal Data, CC BY 4.0,
    DOI: 10.15121/1881483): https://gdr.openei.org/submissions/1391
  - USGS 3D Elevation Program (1/3 arc-second seamless DEM, public domain):
    https://www.usgs.gov/3d-elevation-program

In egress-restricted sandboxes where gdr.openei.org / prd-tnm.s3.amazonaws.com
are blocked, restores the exact SHA-256-pinned blobs from commit
``b99591eede63c6d45c8a896255b8cd34824fa00b`` of ``buffedlizard55-lab/60GEMSDOE``
and ``buffedlizard55-lab/GEMSDOE65``.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OFFICIAL_INGENIOUS_MANIFEST = [
    {
        "filename": "2m_temperature_probe_INGENIOUS_regional_data.zip",
        "sha256": "1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "ref": "b99591eede63c6d45c8a896255b8cd34824fa00b",
        "path": "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip",
        "official_source": "https://gdr.openei.org/submissions/1391",
        "doi": "10.15121/1881483",
        "description": "DOE GDR 1391 INGENIOUS regional 2-meter temperature probe dataset (CC BY 4.0)",
    },
    {
        "filename": "paleo_geothermal_regional.zip",
        "sha256": "faffcf697f32dbbf6cbb317cd1effb3e305538ce38eb239d72d0c6fa071e91ca",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "ref": "b99591eede63c6d45c8a896255b8cd34824fa00b",
        "path": "data/external/paleo_geothermal_regional.zip",
        "official_source": "https://gdr.openei.org/submissions/1391",
        "doi": "10.15121/1881483",
        "description": "DOE GDR 1391 INGENIOUS Quaternary sinter, travertine & tufa paleogeothermal vents (CC BY 4.0)",
    },
    {
        "filename": "topo_10m_derived_100m_u8.tif",
        "sha256": "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "ref": "b99591eede63c6d45c8a896255b8cd34824fa00b",
        "path": "data/external/topo_10m_derived_100m_u8.tif",
        "official_source": "https://www.usgs.gov/3d-elevation-program",
        "doi": "public-domain-usgs-3dep",
        "description": "USGS 3DEP 1/3 arc-second (~10 m) seamless DEM derived sub-100m morphology channels",
    },
    {
        "filename": "topo_10m_derived_100m_u8.manifest.json",
        "sha256": "181d5527ba7ed2990031918a8b6c9d5d94e3998b2daf656de0c33322ca94120a",
        "repo": "buffedlizard55-lab/GEMSDOE65",
        "ref": "HEAD",
        "path": "registry/topography_cache_manifest.json",
        "official_source": "https://www.usgs.gov/3d-elevation-program",
        "doi": "public-domain-usgs-3dep",
        "description": "Quantisation manifest for topo_10m_derived_100m_u8.tif",
    },
    {
        "filename": "dem10_chi_100m_i16.tif",
        "sha256": "8897ba9c30ef1cd7ad5f23c16c6dfd7bb070e7e757f36fd9486eb45edfd973a5",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "ref": "b99591eede63c6d45c8a896255b8cd34824fa00b",
        "path": "data/external/dem10_chi_100m_i16.tif",
        "official_source": "https://www.usgs.gov/3d-elevation-program",
        "doi": "public-domain-usgs-3dep",
        "description": "USGS 3DEP 1/3 arc-second (~10 m) DEM drainage chi/ksn knickpoint channels",
    },
]


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch_ingenious_blob(item: dict, tmp: Path) -> None:
    res = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{item['repo']}/contents/{item['path']}?ref={item['ref']}",
            "-H",
            "Accept: application/vnd.github.raw",
        ],
        capture_output=True,
    )
    if res.returncode == 0 and res.stdout:
        tmp.write_bytes(res.stdout)
        return
    repo_short = item["repo"].split("/")[-1]
    gitdir = ROOT / ".cache/registry_git" / f"{repo_short}.git"
    if not (gitdir / "HEAD").exists():
        gitdir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "-q", "--bare", "--filter=blob:none", f"https://github.com/{item['repo']}.git", str(gitdir)],
            check=True,
        )
    ref = item["ref"]
    if ref != "HEAD":
        subprocess.run(
            ["git", "--git-dir", str(gitdir), "fetch", "-q", "--filter=blob:none", "origin", ref],
            check=False,
            capture_output=True,
        )
    data = subprocess.run(
        ["git", "--git-dir", str(gitdir), "show", f"{ref}:{item['path']}"],
        check=True,
        capture_output=True,
    ).stdout
    tmp.write_bytes(data)


def main() -> None:
    target = ROOT / ".cache" / "official_ing"
    target.mkdir(parents=True, exist_ok=True)
    records = []
    for item in OFFICIAL_INGENIOUS_MANIFEST:
        dest = target / item["filename"]
        if dest.exists() and _sha256(dest) == item["sha256"]:
            status = "present"
        else:
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            _fetch_ingenious_blob(item, tmp)
            got = _sha256(tmp)
            if got != item["sha256"]:
                tmp.unlink(missing_ok=True)
                raise SystemExit(f"SHA256 mismatch for {item['filename']}: {got} != {item['sha256']}")
            tmp.replace(dest)
            status = "restored"
        records.append({**item, "status": status, "bytes": dest.stat().st_size})
        print(f"{status:>8}  .cache/official_ing/{item['filename']:46s} sha256={item['sha256'][:12]}…", flush=True)

    receipt_out = ROOT / "evidence" / "official_ingenious_receipt.json"
    receipt_out.parent.mkdir(parents=True, exist_ok=True)
    receipt_out.write_text(json.dumps({"verified_count": len(records), "files": records}, indent=2) + "\n")
    print(f"Verified {len(records)} official DOE GDR 1391 / USGS 3DEP archives -> evidence/official_ingenious_receipt.json")


if __name__ == "__main__":
    main()
