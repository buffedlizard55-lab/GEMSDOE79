#!/usr/bin/env python3
"""Close the registry scope for STEPCO: 3 late-restored + 6 grid-invalid files.

The main STEPCO scans covered 989/992 indexed rasters with the unmodified
vendor comparator. This script (a) runs the same vendor comparator on the 3
rasters restored after those scans started, and (b) for the 6 rasters the
vendor comparator rejects on grid/band/corruption grounds, records the exact
defect and, where the pixel shape at least matches, an array-level diagnostic
with the vendor's own surface_rho/dot_overlap primitives. Grid-invalid files
are never silently treated as comparable submissions.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared
from gems57.grid import load_grid
from gems79.lifecycle import LaneClosedError, require_open_lane
import run_stepco_experiment as s1

EV = s1.EV
LATE_BLOBS = ["6cd385159679f07dfdb69a2855096daa93c4f0ae",
              "6ebf1616e5761e9737a055c0ecea0c25058e6696",
              "92a89f2ae9e39c5eac7f2df7fbbf0483260a09f6"]


def candidates():
    out = {}
    grid = load_grid(ROOT / "data/reference")
    surface = np.asarray(np.load(s1.CACHE / "surface_s1_final.npy", mmap_mode="r"))
    out["s1_surface"] = np.where(grid.footprint & ~grid.catalogue, surface, 0.0).astype(np.float32)
    for key, state_name in (("s1_dots", "experiment_s1_state.json"),
                            ("s2_dots", "experiment_s2_state.json")):
        st = json.loads((EV / state_name).read_text())
        with rasterio.open(ROOT / st["submission_file"]) as ds:
            out[key] = ds.read(1).astype(np.float32)
    return grid, out


def main():
    require_open_lane(ROOT, "G79-STEPCO")
    grid, cand = candidates()
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    by_blob = {r["blob"]: r for r in index["rasters"]}
    late_records = []
    for blob in LATE_BLOBS:
        p = ROOT / ".cache/registry_extra" / f"{blob}.tif"
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        assert sha == pins[blob]["sha256"], blob
        row = by_blob[blob]
        late_records.append({"repo": row["repo"], "path": row["path"], "blob": blob,
                             "sha256": sha, "file": str(p),
                             "submission": row["repo"] + ":" + row["path"]})
    result = {"late_restored": {}, "grid_invalid": []}
    inv = s1.vendor_inventory(late_records, False)
    for name, arr in cand.items():
        raw = shared.compare_array_to_registry(
            arr, inv, grid.footprint, include_reverse=True,
            expected_grid=(grid.shape, grid.crs, grid.transform))
        result["late_restored"][name] = raw["rows"]

    main_scan = json.loads((EV / "uniqueness_s1_surface.json").read_text())
    errors = [r for r in main_scan["rows"] if "error" in r]
    for r in errors:
        p = Path(r["file"])
        item = {"submission": r["submission"], "file": str(p),
                "vendor_error": r["error"], "diagnostic": {}}
        try:
            with rasterio.open(p) as ds:
                item["grid"] = {"count": ds.count, "shape": list(ds.shape),
                                "crs": str(ds.crs), "transform": [float(v) for v in tuple(ds.transform)[:6]]}
                if ds.count == 1 and tuple(ds.shape) == grid.shape:
                    theirs = ds.read(1).astype(np.float32)
                    theirs = np.where(np.isfinite(theirs), theirs, 0.0)
                    theirs[~grid.footprint] = 0
                    for name, arr in cand.items():
                        sr = shared.surface_rho(arr, theirs, grid.footprint)
                        item["diagnostic"][name] = {
                            "spearman_full_footprint": None if np.isnan(sr["spearman_full_footprint"]) else sr["spearman_full_footprint"],
                            "forward_overlap_3px": shared.dot_overlap(arr, theirs),
                            "their_dots": int((theirs > 0).sum()),
                            "note": "array-level diagnostic only; file grid/CRS metadata is defective, so this is not a like-for-like registry comparison"}
        except Exception as exc:  # corrupt file: record, never guess
            item["grid"] = {"open_error": f"{type(exc).__name__}: {exc}"}
        result["grid_invalid"].append(item)
    result["scope"] = ("Main scans: 989 restored (983 grid-comparable + 6 grid-invalid). "
                       "This supplement adds the remaining 3 restored rasters, completing "
                       "992/992 indexed files accounted for: 986 grid-comparable + 6 grid-invalid documented.")
    s1.write_json(EV / "uniqueness_supplementary.json", result)
    print(json.dumps({k: [(x.get("submission"), x.get("spearman_full_footprint"),
                             x.get("my_dots_within_3px_of_theirs")) for x in v]
                      for k, v in result["late_restored"].items()}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
