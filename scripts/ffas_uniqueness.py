#!/usr/bin/env python3
"""Protocol rule 1 for H79-FFAS: surface (pre-placement) and final-dot duplicate gates.

All novelty mathematics is the shared template's
``gems57.uniqueness.compare_array_to_registry`` with
``dot_definition='budget-matched-v3'`` and
``overlap_mode='informative-halo-v4'`` (shared IR-79-53 fix).
Thresholds are unchanged: Spearman > 0.90, or > 70 % of my dots within 3 px of
one *informative* registry raster's dots (halo coverage <= 0.70) => duplicate.

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
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared        # noqa: E402
from gems57.grid import load_grid              # noqa: E402
from nhr_uniqueness import inventory, compact, BUDGET  # noqa: E402


def run(phase: str):
    grid = load_grid(ROOT / "data/reference")
    inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    allowed = grid.footprint & ~grid.catalogue
    cache = ROOT / ".cache/ffas"
    result = dict(
        schema_version=1, lane="H79-FFAS", phase=phase,
        evidence_class="REGISTRY-MEASUREMENT",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        shared_tool="gems57.uniqueness.compare_array_to_registry",
        shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
        dot_definition="budget-matched-v3",
        overlap_mode="informative-halo-v4",
        rho_limit=shared.RHO_LIMIT, overlap_limit=shared.OVERLAP_LIMIT,
        registry_rasters_expected=expected,
    )
    kwargs = dict(include_reverse=False, expected_grid=eg,
                  dot_definition="budget-matched-v3",
                  overlap_mode="informative-halo-v4", allowed=allowed)
    if phase == "surface":
        surface = np.load(cache / "final_surface.npy")
        r_s = shared.compare_array_to_registry(surface, inv, grid.footprint, **kwargs)
        prov = shared.budget_matched_dots(surface, allowed, BUDGET).astype(np.float32)
        r_p = shared.compare_array_to_registry(prov, inv, grid.footprint, **kwargs)
        s_c = compact(r_s, ("spearman_full_footprint",))
        p_c = compact(r_p, ("my_dots_within_3px_of_theirs", "spearman_full_footprint"))
        rho = s_c["worst_spearman_full_footprint"]["value"]
        ov = p_c["worst_my_dots_within_3px_of_theirs"]["value"]
        # v4: a firing is a duplicate only if the shared tool marked duplicate_by_overlap
        # or duplicate_by_rho on the *provisional* (overlap) / *surface* (rho) rows.
        rho_dup = any(r.get("duplicate_by_rho") for r in r_s["rows"] if "error" not in r)
        ov_dup = any(r.get("duplicate_by_overlap") for r in r_p["rows"] if "error" not in r)
        result.update(
            surface_rank_check=s_c, provisional_topk_check=p_c,
            provisional_cells=int(prov.sum()),
            surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest(),
            duplicate_by_rho=rho_dup, duplicate_by_overlap=ov_dup,
        )
        complete = (s_c["complete"] and p_c["complete"] and not s_c["errors"] and not p_c["errors"]
                    and s_c["checked"] == p_c["checked"] == expected)
        duplicate = bool(rho_dup or ov_dup)
    else:
        kwargs["include_reverse"] = True
        dots = np.load(cache / "final_dots.npy").astype(np.float32)
        r_f = shared.compare_array_to_registry(dots, inv, grid.footprint, **kwargs)
        f_c = compact(r_f, ("my_dots_within_3px_of_theirs", "spearman_full_footprint", "jaccard_dot_sets"))
        rho = f_c["worst_spearman_full_footprint"]["value"]
        ov = f_c["worst_my_dots_within_3px_of_theirs"]["value"]
        lit = [r for r in r_f["rows"] if "error" not in r and r.get("representation") == "continuous_surface"]
        rho_dup = any(r.get("duplicate_by_rho") for r in r_f["rows"] if "error" not in r)
        ov_dup = any(r.get("duplicate_by_overlap") for r in r_f["rows"] if "error" not in r)
        informative = [r for r in r_f["rows"] if "error" not in r
                       and r.get("halo_coverage") is not None and r["halo_coverage"] <= shared.OVERLAP_LIMIT]
        worst_inf = max(informative, key=lambda r: r["my_dots_within_3px_of_theirs"]) if informative else None
        result.update(
            final_check=f_c, my_dots=int(dots.sum()),
            dots_sha256=hashlib.sha256(np.load(cache / "final_dots.npy").tobytes()).hexdigest(),
            continuous_surface_rasters=len(lit),
            dot_field_rasters=f_c["checked"] - len(lit),
            duplicate_by_rho=rho_dup, duplicate_by_overlap=ov_dup,
            worst_informative_overlap=(None if worst_inf is None else dict(
                submission=worst_inf["submission"],
                overlap=worst_inf["my_dots_within_3px_of_theirs"],
                halo_coverage=worst_inf["halo_coverage"],
                spearman=worst_inf["spearman_full_footprint"],
                representation=worst_inf.get("representation"),
                their_dots=worst_inf.get("their_dots"))),
            top10_overlap=sorted(
                ({"submission": r["submission"], "overlap": r["my_dots_within_3px_of_theirs"],
                  "halo_coverage": r.get("halo_coverage"), "spearman": r["spearman_full_footprint"],
                  "representation": r["representation"], "their_dots": r["their_dots"],
                  "duplicate_by_overlap": r.get("duplicate_by_overlap"),
                  "overlap_vacuous": r.get("overlap_vacuous")}
                 for r in r_f["rows"] if "error" not in r),
                key=lambda d: -d["overlap"])[:10],
        )
        complete = f_c["complete"] and not f_c["errors"] and f_c["checked"] == expected
        duplicate = bool(rho_dup or ov_dup)
    result.update(
        worst_spearman=rho, worst_forward_overlap_3px=ov,
        complete_comparison=complete, duplicate=duplicate,
        passed=bool(complete and not duplicate),
    )
    out = ROOT / "evidence/ffas" / f"uniqueness_{phase}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n")
    print(json.dumps({k: result[k] for k in (
        "phase", "worst_spearman", "worst_forward_overlap_3px",
        "complete_comparison", "duplicate", "passed")}, indent=2))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["surface", "final"])
    run(ap.parse_args().phase)
