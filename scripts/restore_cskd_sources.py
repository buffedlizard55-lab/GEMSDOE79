#!/usr/bin/env python3
"""Restore and SHA-256-verify official USGS GeoDAWN DEM/survey-block and US BLM mining-claim rasters for G79-CSKD.

All three layers are 100% label-free public-domain US government datasets:
  1. geodawn_dem_a2_100m.tif (USGS GeoDAWN 22103_dem_a2.tif, doi:10.5066/P93LGLVQ)
  2. acquisition_block_id_100m.tif (USGS GeoDAWN Area 1 / Area 2 flight-block polygons, doi:10.5066/P93LGLVQ)
  3. blm_closed_claim_distance_m.tif (US BLM Mining Claims MapServer/2 Euclidean distance in meters)

Fails closed on any byte-count or SHA-256 mismatch and writes repo-relative provenance to
`evidence/cskd_sources_receipt.json` without modifying `registry/data_manifest.json` or `data/restore_receipt.json`.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from restore_data import _fetch_via_git_smart_http, sha256_file  # noqa: E402

PINNED_CSKD_SOURCES = [
    {
        "id": "geodawn_dem_a2_100m",
        "dest": ".cache/cskd_sources/geodawn_dem_a2_100m.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "ref": "b99591eede63c6d45c8a896255b8cd34824fa00b",
        "path": "data/geodawn_dem_a2_100m.tif",
        "bytes": 49531304,
        "sha256": "d32762a38222764389e948da423ebc6cadd00ac617ad3938d3dd79c6cfe14431",
        "official_source": "https://doi.org/10.5066/P93LGLVQ",
        "official_catalog": "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7",
        "label_free": True,
    },
    {
        "id": "acquisition_block_id_100m",
        "dest": ".cache/cskd_sources/acquisition_block_id_100m.tif",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "ref": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "path": "data/external/audit_sources/acquisition_block_id_100m.tif",
        "bytes": 85031,
        "sha256": "2c0785c4b3ec46c734d1be7a7aedbb3e816201100ab358033a3af074418c894a",
        "official_source": "https://doi.org/10.5066/P93LGLVQ",
        "official_catalog": "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7",
        "label_free": True,
    },
    {
        "id": "blm_closed_claim_distance_m",
        "dest": ".cache/cskd_sources/blm_closed_claim_distance_m.tif",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "ref": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "path": "data/external/audit_sources/blm_closed_claim_distance_m.tif",
        "bytes": 5752587,
        "sha256": "a88356423c03fc8b6510a84f77cee2b1d38c4ccbd7761bc95c1ca8332a2e166a",
        "official_source": "https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2",
        "official_catalog": "https://gbp-blm-egis.hub.arcgis.com/",
        "label_free": True,
    },
]


def restore_cskd_sources(root: Path = ROOT) -> dict:
    results = []
    for entry in PINNED_CSKD_SOURCES:
        dest = root / entry["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        status = "present"
        if not dest.is_file() or sha256_file(dest) != entry["sha256"] or dest.stat().st_size != entry["bytes"]:
            tmp = dest.with_suffix(".partial")
            try:
                with tmp.open("wb") as out:
                    _fetch_via_git_smart_http(entry["repo"], entry["ref"], entry["path"], out)
                got_sha = sha256_file(tmp)
                got_bytes = tmp.stat().st_size
                if got_sha != entry["sha256"] or got_bytes != entry["bytes"]:
                    raise RuntimeError(
                        f"CSKD source integrity mismatch for {entry['id']}: "
                        f"got ({got_bytes} B, {got_sha}) != expected ({entry['bytes']} B, {entry['sha256']})"
                    )
                tmp.replace(dest)
                status = "restored"
            finally:
                tmp.unlink(missing_ok=True)
        results.append(
            {
                "id": entry["id"],
                "dest": entry["dest"],
                "status": status,
                "bytes": dest.stat().st_size,
                "sha256": entry["sha256"],
                "official_source": entry["official_source"],
                "official_catalog": entry["official_catalog"],
                "mirror_repo": entry["repo"],
                "mirror_ref": entry["ref"],
                "mirror_path": entry["path"],
                "label_free": entry["label_free"],
            }
        )
        print(f"{status:>8}  {entry['dest']:52s} sha256={entry['sha256'][:12]}…", flush=True)
    receipt = {
        "schema_version": 1,
        "lane": "G79-CSKD",
        "verified_files_count": len(results),
        "files": results,
    }
    rec_path = root / "evidence" / "cskd_sources_receipt.json"
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    rec_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    restore_cskd_sources()
