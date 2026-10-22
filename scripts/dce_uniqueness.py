#!/usr/bin/env python3
"""Protocol rule 1 for H79-DCE: final-dot duplicate gate with the v4 shared tool.

All novelty mathematics is the shared template's
``gems57.uniqueness.compare_array_to_registry`` with ``dot_definition=
'budget-matched-v3'`` (IR-79-47) plus the v4 amendments (IR-79-57/58):

* ``uniform_chance`` from the frozen measured uniform control
  (evidence/nhr/overlap_chance.json, seed 79, budget 37,654 = this lane's
  budget) adjudicates rasters whose literal overlap test is vacuous;
* registry files that cannot be decoded or do not sit on the competition grid
  are excluded as ``not_comparable`` with objective reasons.

Thresholds are unchanged: Spearman > 0.90, or > 70 % of my dots within 3 px of
one *ordinary* registry raster's dots, or beyond-chance overlap against a
*vacuous* raster => duplicate => stop.

Phase ``final`` is the binding gate on the placed dots. The pre-placement
surface check is covered by the hash-verified identity of this lane's surface
with the frozen H79-NHR X1 surface (see evidence/dce/surface_build.json and
evidence/nhr/uniqueness_surface.json) plus the at-risk scan in
evidence/dce/atrisk_build.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared        # noqa: E402
from gems57.grid import load_grid              # noqa: E402
from gems79 import dce                         # noqa: E402
from run_dce import r_blob                     # noqa: E402

BUDGET = 37654
FIX_DCE = json.loads((ROOT / "registry/preregistration_dce.json").read_text())["fixed_parameters"]


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


def compact(res):
    rows = [r for r in res["rows"] if "error" not in r and not r.get("not_comparable")]
    def worst(k):
        vals = [r for r in rows if r.get(k) is not None]
        return max(vals, key=lambda r: r[k]) if vals else None
    out = {}
    for k in ("my_dots_within_3px_of_theirs", "spearman_full_footprint", "jaccard_dot_sets"):
        w = worst(k)
        out["worst_" + k] = None if w is None else dict(value=w[k], submission=w["submission"],
                                                        representation=w.get("representation"),
                                                        their_dots=w.get("their_dots"))
    out.update(checked=len(rows),
               errors=[r for r in res["rows"] if "error" in r],
               not_comparable=res.get("not_comparable_rasters", []),
               complete=res["complete_accessible_scan"])
    return out


def run_final():
    grid = load_grid(ROOT / "data/reference")
    inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    chance_rows = json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())["rows"]
    chance = {r["sha256"]: r["overlap_uniform"] for r in chance_rows
              if "error" not in r and r.get("overlap_uniform") is not None}
    ordinary = {r["sha256"] for r in chance_rows
                if "error" not in r and r.get("overlap_uniform") is not None
                and r["overlap_uniform"] <= 0.70}
    trigger = json.loads((ROOT / "registry/preregistration_dce.json").read_text())["fixed_parameters"][
        "collision_ceiling"]

    def scan(dots):
        r_f = shared.compare_array_to_registry(dots.astype(np.float32), inv, grid.footprint,
                                               include_reverse=True, expected_grid=eg,
                                               dot_definition="budget-matched-v3",
                                               uniform_chance=chance)
        return r_f

    def violators(r_f):
        return [r for r in r_f["rows"] if "error" not in r and not r.get("not_comparable")
                and r["sha256"] in ordinary and r.get("my_dots_within_3px_of_theirs") is not None
                and r["my_dots_within_3px_of_theirs"] > trigger]

    iterations = 0
    additions = []
    converged = False
    while iterations < 5:
        iterations += 1
        dots = np.load(ROOT / ".cache/dce/final_dots.npy")
        r_f = scan(dots)
        bad = violators(r_f)
        already = set(dce.load_atrisk_halos())
        new = [r for r in bad if r["sha256"] not in already]
        if not new:
            converged = True
            break
        # preregistered fixed point: extend the capped set and re-place
        halos = dce.load_atrisk_halos()
        for r in new:
            p = ROOT / ".cache/registry" / (r_blob(r) + ".tif")
            import rasterio
            with rasterio.open(p) as src:
                theirs = src.read(1).astype(np.float32)
            theirs = np.where(np.isfinite(theirs), theirs, 0.0)
            theirs[~grid.footprint] = 0
            support = (theirs > 0) & grid.footprint
            if r.get("representation") == "continuous_surface":
                support = shared.budget_matched_dots(theirs, grid.footprint, int(dots.sum()))
            halos[r["sha256"]] = dce.pack_halo(dce.three_px_halo(support))
            additions.append(dict(sha256=r["sha256"], submission=r["submission"],
                                  overlap=r["my_dots_within_3px_of_theirs"],
                                  iteration=iterations))
        np.savez_compressed(ROOT / ".cache/dce/atrisk_halos.npz", **halos)
        surface = np.load(ROOT / ".cache/dce/final_surface.npy")
        d_cat = ndi.distance_transform_edt(~grid.catalogue)
        collar = FIX_DCE["collar_px"]
        allowed = grid.footprint & (d_cat > collar)
        new_dots, info = dce.place_capped(surface, allowed, int(dots.sum()), halos,
                                          ceiling=FIX_DCE["collision_ceiling"])
        np.save(ROOT / ".cache/dce/final_dots.npy", new_dots)
        print(f"[fixed-point] iteration {iterations}: added {len(new)} rasters, re-placed "
              f"{int(new_dots.sum())} dots", flush=True)
    (ROOT / "evidence/dce/cap_convergence.json").write_text(json.dumps(dict(
        lane="H79-DCE", iterations=iterations, converged=converged, additions=additions,
        trigger=trigger,
        note=("Preregistered fixed point: ordinary rasters above the ceiling join the capped "
              "set and placement re-runs. Post-holdout additions would invalidate the measured "
              "candidate arm (monotone credit loss), so promotion additionally requires "
              "converged=True with no additions, or a holdout re-run.")), indent=2) + "\n")

    dots = np.load(ROOT / ".cache/dce/final_dots.npy")
    f_c = compact(r_f)
    rho = f_c["worst_spearman_full_footprint"]["value"]
    ov = f_c["worst_my_dots_within_3px_of_theirs"]["value"]
    # worst beyond-chance among vacuous rasters
    vac = [r for r in r_f["rows"] if "error" not in r and r.get("vacuous_overlap_test")]
    worst_bc = max((r for r in vac if r.get("overlap_beyond_chance") is not None),
                   key=lambda r: r["overlap_beyond_chance"], default=None)
    bc = None if worst_bc is None else dict(value=worst_bc["overlap_beyond_chance"],
                                            submission=worst_bc["submission"],
                                            chance=worst_bc["overlap_chance"],
                                            overlap=worst_bc["my_dots_within_3px_of_theirs"],
                                            margin=shared.beyond_chance_margin(
                                                worst_bc["overlap_chance"], int(dots.sum())))
    lit_flagged = [r for r in r_f["rows"] if "error" not in r and not r.get("not_comparable")
                   and r.get("duplicate_by_overlap") and not r.get("vacuous_overlap_test")]
    result = dict(schema_version=1, lane="H79-DCE", phase="final",
                  evidence_class="REGISTRY-MEASUREMENT",
                  generated_utc=datetime.now(timezone.utc).isoformat(),
                  shared_tool="gems57.uniqueness.compare_array_to_registry",
                  shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
                  dot_definition="budget-matched-v3", rho_limit=shared.RHO_LIMIT,
                  overlap_limit=shared.OVERLAP_LIMIT, registry_rasters_expected=expected,
                  my_dots=int(dots.sum()),
                  dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
                  cap_fixed_point=dict(iterations=iterations, converged=converged,
                                       additions=additions),
                  comparable_rasters=r_f.get("comparable_rasters"),
                  not_comparable_rasters=r_f.get("not_comparable_rasters", []),
                  final_check=f_c, worst_beyond_chance_among_vacuous=bc,
                  ordinary_rasters_flagged_literal=len(lit_flagged),
                  ordinary_flagged_submissions=[r["submission"] for r in lit_flagged][:20],
                  chance_reference="evidence/nhr/overlap_chance.json (uniform control seed 79, budget 37654)",
                  amendments=["IR-79-47 budget-matched-v3", "IR-79-57 beyond-chance vacuous test",
                              "IR-79-58 not-comparable exclusion"])
    complete = (f_c["complete"] and not f_c["errors"]
                and f_c["checked"] + len(result["not_comparable_rasters"]) == expected)
    duplicate = bool((rho is not None and rho > shared.RHO_LIMIT)
                     or ov > shared.OVERLAP_LIMIT
                     or (bc is not None and bc["value"] > bc["margin"])
                     or not r_f.get("unique", False))
    result.update(worst_spearman=rho, worst_forward_overlap_3px=ov,
                  complete_comparison=complete, shared_unique_verdict=bool(r_f.get("unique")),
                  duplicate=duplicate, passed=bool(complete and not duplicate))
    out = ROOT / "evidence/dce/uniqueness_final.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n")
    print(json.dumps({k: result[k] for k in ("phase", "worst_spearman", "worst_forward_overlap_3px",
                                             "comparable_rasters", "not_comparable_rasters",
                                             "ordinary_rasters_flagged_literal",
                                             "shared_unique_verdict", "complete_comparison",
                                             "duplicate", "passed") if k in result}, indent=2))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["final"])
    run_final()
