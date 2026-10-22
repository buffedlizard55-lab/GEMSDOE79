#!/usr/bin/env python3
"""G79-CONJ registry uniqueness audits (protocol rule 1), shared tool only.

Phases (run in this order):
  surface  pre-placement continuous surface (.cache/g79_conj/live_surface.tif),
           budget-matched-v3 dots for registry surfaces. If max |Spearman| > 0.90
           the finalize step must discard the cached dots.
  dots     final binary dots, budget-matched-v3 (operative, IR-79-47/D-1).
  dotslit  final binary dots, literal dot definition (disclosure: the
           space-filling witness makes this 1.0 for every nonempty candidate).

Inventory: frozen registry_index.json (992 verified blobs) + registry_delta.json
(207 blobs), deduplicated by SHA-256, bytes hash-verified in .cache/registry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import uniqueness as shared  # noqa: E402
from gems57.grid import load_grid  # noqa: E402

CACHE = ROOT / ".cache" / "g79_conj"
OUT = ROOT / "evidence" / "conj"


def inventory():
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    delta = json.loads((ROOT / "registry/registry_delta.json").read_text())
    verified = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    by_sha: dict[str, dict] = {}
    errors = []
    for row in index["rasters"]:
        if row["blob"] not in verified:
            errors.append("unverified frozen blob " + row["blob"])
            continue
        sha = verified[row["blob"]]["sha256"]
        rec = {"repo_first": row["repo"], "sources": row.get("aliases", [row["path"]]),
               "cache_file": str(ROOT / ".cache/registry" / (row["blob"] + ".tif")), "sha256": sha}
        if sha in by_sha:
            by_sha[sha]["sources"] = sorted(set(by_sha[sha]["sources"]) | set(rec["sources"]))
        else:
            by_sha[sha] = rec
    for row in delta["rasters"]:
        sha = row["sha256"]
        rec = {"repo_first": row["repo"], "sources": row["aliases"],
               "cache_file": str(ROOT / ".cache/registry" / (row["blob"] + ".tif")), "sha256": sha}
        if sha in by_sha:
            by_sha[sha]["sources"] = sorted(set(by_sha[sha]["sources"]) | set(rec["sources"]))
        else:
            by_sha[sha] = rec
    errors += [s["repo"] + ": " + s.get("error", "") for s in delta["repositories"] if s["status"] != "ok"]
    missing = [r["cache_file"] for r in by_sha.values() if not Path(r["cache_file"]).is_file()]
    if missing:
        errors.append(f"{len(missing)} registry cache files missing")
    inv = {"rasters": list(by_sha.values()), "complete_accessible_scan": not errors, "errors": errors}
    return inv, len(by_sha)


def summarize(res: dict, candidate_dots: int) -> dict:
    rows = [r for r in res["rows"] if "error" not in r]
    errs = [r for r in res["rows"] if "error" in r]

    def worst(key, subset=None):
        vals = [r for r in (subset if subset is not None else rows) if r.get(key) is not None]
        return max(vals, key=lambda r: abs(r[key]) if key == "spearman_full_footprint" else r[key]) if vals else None

    def pack(r, key):
        if r is None:
            return None
        return {"value": r[key], "abs_value": abs(r[key]), "submission": r["submission"],
                "their_dots": r.get("their_dots"), "representation": r.get("representation")}

    sparse = [r for r in rows if r.get("their_dots") is not None and r["their_dots"] <= 50_000]
    w_rho = worst("spearman_full_footprint")
    w_ov = worst("my_dots_within_3px_of_theirs")
    w_ov_sparse = worst("my_dots_within_3px_of_theirs", sparse)
    h33 = [r for r in rows if "h33-2-b2" in (r.get("submission") or "")]
    return {
        "checked_rows": len(rows),
        "error_rows": len(errs),
        "error_submissions": [r.get("submission") for r in errs],
        "candidate_dots": candidate_dots,
        "worst_abs_spearman": pack(w_rho, "spearman_full_footprint"),
        "worst_forward_overlap_3px": pack(w_ov, "my_dots_within_3px_of_theirs"),
        "sparse_le_50k": {"count": len(sparse),
                          "worst_forward_overlap_3px": pack(w_ov_sparse, "my_dots_within_3px_of_theirs")},
        "vs_h33": [{"submission": r["submission"], "forward_overlap_3px": r.get("my_dots_within_3px_of_theirs"),
                    "spearman": r.get("spearman_full_footprint"), "their_dots": r.get("their_dots")} for r in h33],
        "n_flags_rho_gt_0p90": int(sum(1 for r in rows
                                       if r.get("spearman_full_footprint") is not None
                                       and abs(r["spearman_full_footprint"]) > 0.90)),
        "n_flags_overlap_gt_0p70": int(sum(1 for r in rows
                                           if (r.get("my_dots_within_3px_of_theirs") or 0) > 0.70)),
        "flagged_overlap_submissions": sorted(
            r["submission"] for r in rows if (r.get("my_dots_within_3px_of_theirs") or 0) > 0.70),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", required=True, choices=("surface", "prov", "dots", "dotslit"))
    a = ap.parse_args()
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    tif = CACHE / ("live_surface.tif" if a.phase in ("surface", "prov") else "live_dots.tif")
    with rasterio.open(tif) as ds:
        arr = ds.read(1).astype(np.float32)
    if a.phase == "prov":
        # Provisional pre-placement dot check: the surface's own top-k cells
        # (k = final dot budget) under the shared budget-matched reading.
        with rasterio.open(CACHE / "live_dots.tif") as ds:
            k = int((ds.read(1) > 0).sum())
        arr = shared.budget_matched_dots(arr, grid.footprint & ~grid.catalogue, k).astype(np.float32)
    file_sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    dot_def = "literal" if a.phase == "dotslit" else "budget-matched-v3"
    # For the surface phase the candidate's provisional dot count for
    # budget-matching is the surface's own top-k behaviour inside the shared
    # tool (candidate support = surface > 0); dots phases use the binary map.
    res = shared.compare_array_to_registry(
        arr, inv, grid.footprint, file_sha256=file_sha,
        include_reverse=(a.phase != "surface"), expected_grid=eg, dot_definition=dot_def)
    cand_dots = int(res.get("my_dots") or int((arr[grid.footprint] > 0).sum()))
    summ = summarize(res, cand_dots)
    out = {
        "schema_version": 1, "lane": "G79-CONJ", "phase": a.phase,
        "evidence_class": "REGISTRY-MEASUREMENT",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "shared_tool": "gems57.uniqueness.compare_array_to_registry",
        "shared_tool_sha256": hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
        "dot_definition": dot_def, "rho_limit": shared.RHO_LIMIT, "overlap_limit": shared.OVERLAP_LIMIT,
        "registry_rasters_expected_dedup_sha256": expected,
        "candidate_file": str(tif.relative_to(ROOT)), "candidate_file_sha256": file_sha,
        "candidate_decoded_sha256": res.get("candidate_decoded_sha256"),
        "audit_elapsed_seconds": round(time.time() - t0, 1),
        "summary": summ,
        "shared_unique_flag": res.get("unique"),
        "rows": res["rows"],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"uniqueness_{a.phase}.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summ, indent=2), flush=True)
    print(f"wrote {dest} in {out['audit_elapsed_seconds']}s", flush=True)


if __name__ == "__main__":
    main()
