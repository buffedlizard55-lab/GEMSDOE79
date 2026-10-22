#!/usr/bin/env python3
"""G79-CONJ amendment-D2 chance-corrected registry audit (shared tool only)."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from audit_conj_uniqueness import inventory  # noqa: E402

CACHE = ROOT / ".cache" / "g79_conj"
OUT = ROOT / "evidence" / "conj"


def main():
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    with rasterio.open(CACHE / "live_dots.tif") as ds:
        dots = ds.read(1) > 0
    with rasterio.open(CACHE / "live_surface.tif") as ds:
        surf = ds.read(1).astype(np.float32)
    allowed = grid.footprint & (ndi.distance_transform_edt(~grid.catalogue) > 2.0)
    file_sha = hashlib.sha256((CACHE / "live_dots.tif").read_bytes()).hexdigest()
    res = shared.compare_array_to_registry_d2(
        dots, inv, grid.footprint, allowed, candidate_surface=surf,
        file_sha256=file_sha, expected_grid=eg)
    rows = [r for r in res["rows"] if "error" not in r]
    sparse = [r for r in rows if (r.get("their_dot_equivalent_cells") or 10**18) <= 50_000]
    def worst_corr(rs):
        vals = [r for r in rs if r.get("chance_corrected_overlap") is not None]
        return max(vals, key=lambda r: r["chance_corrected_overlap"]) if vals else None
    def pack(r):
        return None if r is None else {
            "chance_corrected_overlap": r["chance_corrected_overlap"],
            "forward_overlap": r["my_dots_within_3px_of_dot_equivalent"],
            "halo_coverage_allowed": r["halo_coverage_allowed"],
            "their_dot_equivalent_cells": r["their_dot_equivalent_cells"],
            "submission": r["submission"]}
    summ = {
        "checked_rows": len(rows),
        "error_rows": len(res["rows"]) - len(rows),
        "d2_firings_all": int(sum(1 for r in rows if r["duplicate_d2"])),
        "d2_firing_submissions": sorted(r["submission"] for r in rows if r["duplicate_d2"]),
        "worst_chance_corrected_all": pack(worst_corr(rows)),
        "sparse_le_50k": {
            "count": len(sparse),
            "d2_firings": int(sum(1 for r in sparse if r["duplicate_d2"])),
            "worst_chance_corrected": pack(worst_corr(sparse)),
            "worst_forward_overlap": max((r["my_dots_within_3px_of_dot_equivalent"] for r in sparse), default=None),
        },
        "shared_unique_flag": res.get("unique"),
    }
    out = {"schema_version": 1, "lane": "G79-CONJ", "phase": "dots_d2",
           "evidence_class": "REGISTRY-MEASUREMENT",
           "generated_utc": datetime.now(timezone.utc).isoformat(),
           "shared_tool": "gems57.uniqueness.compare_array_to_registry_d2",
           "shared_tool_sha256": hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
           "registry_rasters_expected_dedup_sha256": expected,
           "audit_elapsed_seconds": round(time.time() - t0, 1),
           "summary": summ, "rows": res["rows"]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "uniqueness_d2.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summ, indent=2), flush=True)


if __name__ == "__main__":
    main()
