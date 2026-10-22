#!/usr/bin/env python3
"""Protocol rule 1 for H79-NHR: surface (pre-placement) and final-dot duplicate gates.

All novelty mathematics is the shared template's
``gems57.uniqueness.compare_array_to_registry`` with ``dot_definition=
'budget-matched-v3'`` (shared fix, see reports/irregularities.md IR-79-47).
Thresholds are unchanged: Spearman > 0.90 or > 70 % of my dots within 3 px of
one registry raster's dots => duplicate => stop.

Phases
------
surface  rank correlation of the continuous pre-placement surface with every
         registry raster, plus 3 px overlap of the surface's provisional top-k
         cells (k = 37,654) with every raster's dots.
final    rank correlation and 3 px overlap of the final placed dots.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import uniqueness as shared        # noqa: E402
from gems57.grid import load_grid              # noqa: E402
from gems79.lifecycle import LaneClosedError, require_open_lane  # noqa: E402

BUDGET = 37654


def inventory():
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    delta = json.loads((ROOT / "registry/registry_delta.json").read_text())
    verified = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    rasters, errors = [], []
    for row in index["rasters"]:
        if row["blob"] not in verified:
            errors.append("unverified frozen blob " + row["blob"])
            continue
        rasters.append({"repo_first": row["repo"], "sources": row.get("aliases", [row["path"]]),
                        "cache_file": str(ROOT / ".cache/registry" / (row["blob"] + ".tif")),
                        "sha256": verified[row["blob"]]["sha256"]})
    for row in delta["rasters"]:
        rasters.append({"repo_first": row["repo"], "sources": row["aliases"],
                        "cache_file": str(ROOT / ".cache/registry" / (row["blob"] + ".tif")),
                        "sha256": row["sha256"]})
    errors += [s["repo"] + ": " + s.get("error", "") for s in delta["repositories"] if s["status"] != "ok"]
    return ({"rasters": rasters, "complete_accessible_scan": not errors, "errors": errors},
            len(index["rasters"]) + len(delta["rasters"]))


def compact(res, keys=("my_dots_within_3px_of_theirs", "spearman_full_footprint")):
    rows = [r for r in res["rows"] if "error" not in r]
    def worst(k):
        vals = [r for r in rows if r.get(k) is not None]
        return max(vals, key=lambda r: r[k]) if vals else None
    out = {}
    for k in keys:
        w = worst(k)
        out["worst_" + k] = None if w is None else dict(value=w[k], submission=w["submission"],
                                                         representation=w.get("representation"),
                                                         their_dots=w.get("their_dots"))
    out.update(checked=len(rows), errors=[r for r in res["rows"] if "error" in r],
               complete=res["complete_accessible_scan"])
    return out


def run(phase, lane="H79-NHR", cache=None, out_dir=None):
    """Shared-tool duplicate gate for one lane. Defaults reproduce H79-NHR exactly.

    ``cache`` holds final_surface.npy and final_dots.npy; ``out_dir`` receives
    uniqueness_<phase>.json. The shared comparison is unchanged.
    """
    require_open_lane(ROOT, lane)
    grid = load_grid(ROOT / "data/reference")
    inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    cache = Path(cache) if cache else ROOT / ".cache/nhr"
    out_dir = Path(out_dir) if out_dir else ROOT / "evidence/nhr"
    result = dict(schema_version=1, lane=lane, phase=phase,
                  evidence_class="REGISTRY-MEASUREMENT",
                  generated_utc=datetime.now(timezone.utc).isoformat(),
                  shared_tool="gems57.uniqueness.compare_array_to_registry",
                  shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
                  dot_definition="budget-matched-v3", rho_limit=shared.RHO_LIMIT,
                  overlap_limit=shared.OVERLAP_LIMIT, registry_rasters_expected=expected)
    if phase == "surface":
        surface = np.load(cache / "final_surface.npy")
        r_s = shared.compare_array_to_registry(surface, inv, grid.footprint, include_reverse=False,
                                               expected_grid=eg, dot_definition="budget-matched-v3")
        prov = shared.budget_matched_dots(surface, grid.footprint & ~grid.catalogue, BUDGET).astype(np.float32)
        r_p = shared.compare_array_to_registry(prov, inv, grid.footprint, include_reverse=False,
                                               expected_grid=eg, dot_definition="budget-matched-v3")
        s_c, p_c = compact(r_s, ("spearman_full_footprint",)), compact(r_p, ("my_dots_within_3px_of_theirs", "spearman_full_footprint"))
        rho = s_c["worst_spearman_full_footprint"]["value"]
        ov = p_c["worst_my_dots_within_3px_of_theirs"]["value"]
        result.update(surface_rank_check=s_c, provisional_topk_check=p_c,
                      provisional_cells=int(prov.sum()),
                      surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest())
        complete = s_c["complete"] and p_c["complete"] and not s_c["errors"] and not p_c["errors"] \
            and s_c["checked"] == p_c["checked"] == expected
    else:
        dots = np.load(cache / "final_dots.npy").astype(np.float32)
        r_f = shared.compare_array_to_registry(dots, inv, grid.footprint, include_reverse=True,
                                               expected_grid=eg, dot_definition="budget-matched-v3")
        f_c = compact(r_f, ("my_dots_within_3px_of_theirs", "spearman_full_footprint", "jaccard_dot_sets"))
        rho = f_c["worst_spearman_full_footprint"]["value"]
        ov = f_c["worst_my_dots_within_3px_of_theirs"]["value"]
        lit = [r for r in r_f["rows"] if "error" not in r and r.get("representation") == "continuous_surface"]
        result.update(final_check=f_c, my_dots=int(dots.sum()),
                      dots_sha256=hashlib.sha256(np.load(cache / "final_dots.npy").tobytes()).hexdigest(),
                      continuous_surface_rasters=len(lit),
                      dot_field_rasters=f_c["checked"] - len(lit),
                      top10_overlap=sorted(({"submission": r["submission"], "overlap": r["my_dots_within_3px_of_theirs"],
                                             "spearman": r["spearman_full_footprint"], "representation": r["representation"],
                                             "their_dots": r["their_dots"]} for r in r_f["rows"] if "error" not in r),
                                           key=lambda d: -d["overlap"])[:10])
        complete = f_c["complete"] and not f_c["errors"] and f_c["checked"] == expected
    duplicate = bool((rho is not None and rho > shared.RHO_LIMIT) or ov > shared.OVERLAP_LIMIT)
    result.update(worst_spearman=rho, worst_forward_overlap_3px=ov, complete_comparison=complete,
                  duplicate=duplicate, passed=bool(complete and not duplicate))
    out = out_dir / f"uniqueness_{phase}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n")
    print(json.dumps({k: result[k] for k in ("phase", "worst_spearman", "worst_forward_overlap_3px",
                                             "complete_comparison", "duplicate", "passed")}, indent=2))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["surface", "final"])
    try:
        run(ap.parse_args().phase)
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
