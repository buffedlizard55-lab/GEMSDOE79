#!/usr/bin/env python3
"""Protocol rule 1 for H79-ARC: surface (pre-placement) and final-dot gates.

Uses the shared `gems57.uniqueness.compare_array_to_registry` v4 with
`dot_definition='budget-matched-v3'` (Amendment D-1) and `allowed=` =
footprint minus catalogue so every row carries halo coverage and
chance-corrected excess overlap (Amendment D-2,
reports/protocol_amendment_D2_20261022.md).

D-2 duplicate rule: Spearman rho > 0.90, OR excess (ov-h)/(1-h) > 0.70,
OR byte/decoded-pixel identity.  The literal forward overlap and its firing
count are always reported alongside; nothing is exempted silently.
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
from nhr_uniqueness import inventory           # noqa: E402

BUDGET = 37654
CACHE = ROOT / ".cache" / "arc"
OUT = ROOT / "evidence" / "arc"
ROW_KEYS = ("submission", "sha256", "representation", "their_dots",
            "my_dots_within_3px_of_theirs", "halo_coverage_allowed",
            "overlap_beyond_chance", "spearman_full_footprint",
            "identical_bytes", "identical_decoded_predictions")


def compact_rows(res):
    rows = [r for r in res["rows"] if "error" not in r]
    errors = [r for r in res["rows"] if "error" in r]
    slim = [{k: r.get(k) for k in ROW_KEYS} for r in rows]

    def worst(key):
        vals = [r for r in rows if r.get(key) is not None]
        return max(vals, key=lambda r: r[key]) if vals else None

    w_rho, w_ov, w_exc = worst("spearman_full_footprint"), worst("my_dots_within_3px_of_theirs"), worst("overlap_beyond_chance")
    literal_firings = [r for r in rows if r["my_dots_within_3px_of_theirs"] > 0.70]
    excess_firings = [r for r in rows if (r.get("overlap_beyond_chance") or 0) > 0.70]
    rho_firings = [r for r in rows if (r.get("spearman_full_footprint") or 0) > 0.90]
    identity = [r for r in rows if r.get("identical_bytes") or r.get("identical_decoded_predictions")]
    sat = [r for r in rows if r.get("overlap_beyond_chance") is None and r.get("halo_coverage_allowed") is not None]
    return dict(
        checked=len(rows), errors=errors, complete=res["complete_accessible_scan"],
        worst_spearman=(w_rho or {}).get("spearman_full_footprint"),
        worst_spearman_submission=(w_rho or {}).get("submission"),
        worst_forward_overlap_3px_literal=(w_ov or {}).get("my_dots_within_3px_of_theirs"),
        worst_literal_overlap_submission=(w_ov or {}).get("submission"),
        worst_overlap_beyond_chance=(w_exc or {}).get("overlap_beyond_chance"),
        worst_excess_submission=(w_exc or {}).get("submission"),
        worst_excess_halo_coverage=(w_exc or {}).get("halo_coverage_allowed"),
        literal_overlap_firings=len(literal_firings),
        excess_firings=len(excess_firings),
        rho_firings=len(rho_firings),
        identity_matches=len(identity),
        saturated_noninformative=len(sat),
        rows=slim)


def run(phase):
    grid = load_grid(ROOT / "data/reference")
    inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    allowed_domain = grid.footprint & ~grid.catalogue
    result = dict(schema_version=1, lane="H79-ARC", phase=phase,
                  evidence_class="REGISTRY-MEASUREMENT",
                  generated_utc=datetime.now(timezone.utc).isoformat(),
                  shared_tool="gems57.uniqueness.compare_array_to_registry (v4, Amendment D-2)",
                  shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
                  dot_definition="budget-matched-v3", rho_limit=shared.RHO_LIMIT,
                  overlap_limit=shared.OVERLAP_LIMIT, registry_rasters_expected=expected,
                  amendments=["D-1 budget-matched dots for continuous surfaces",
                              "D-2 duplicate iff rho>0.90 or excess (ov-h)/(1-h)>0.70 or identity"])
    if phase == "surface":
        surface = np.load(CACHE / "final_surface.npy")
        allowed = np.load(CACHE / "final_allowed.npy")
        r_s = shared.compare_array_to_registry(surface, inv, grid.footprint, include_reverse=False,
                                               expected_grid=eg, dot_definition="budget-matched-v3",
                                               allowed=allowed_domain)
        s_c = compact_rows(r_s)
        prov = shared.budget_matched_dots(surface, allowed, BUDGET).astype(np.float32)
        r_p = shared.compare_array_to_registry(prov, inv, grid.footprint, include_reverse=False,
                                               expected_grid=eg, dot_definition="budget-matched-v3",
                                               allowed=allowed_domain)
        p_c = compact_rows(r_p)
        complete = (s_c["complete"] and p_c["complete"] and not s_c["errors"] and not p_c["errors"]
                    and s_c["checked"] == p_c["checked"] == expected)
        passed = bool(complete and (s_c["worst_spearman"] or 0) <= 0.90
                      and p_c["excess_firings"] == 0 and p_c["rho_firings"] == 0
                      and p_c["identity_matches"] == 0)
        result.update(surface_rank_check={k: v for k, v in s_c.items() if k != "rows"},
                      provisional_topk_check=p_c,
                      provisional_cells=int(prov.sum()),
                      worst_spearman=s_c["worst_spearman"],
                      worst_forward_overlap_3px=p_c["worst_forward_overlap_3px_literal"],
                      worst_overlap_beyond_chance=p_c["worst_overlap_beyond_chance"],
                      surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest(),
                      passed=passed, passed_d2=passed)
    else:
        dots = np.load(CACHE / "final_dots.npy")
        mine = (dots & grid.footprint).astype(np.float32)
        r_f = shared.compare_array_to_registry(mine, inv, grid.footprint, include_reverse=False,
                                               expected_grid=eg, dot_definition="budget-matched-v3",
                                               allowed=allowed_domain)
        f_c = compact_rows(r_f)
        complete = f_c["complete"] and not f_c["errors"] and f_c["checked"] == expected
        passed = bool(complete and f_c["excess_firings"] == 0 and f_c["rho_firings"] == 0
                      and f_c["identity_matches"] == 0)
        result.update(final_check=f_c,
                      worst_spearman=f_c["worst_spearman"],
                      worst_forward_overlap_3px=f_c["worst_forward_overlap_3px_literal"],
                      worst_overlap_beyond_chance=f_c["worst_overlap_beyond_chance"],
                      dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
                      n_dots=int(dots.sum()), passed=passed, passed_d2=passed)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"uniqueness_{phase}.json"
    path.write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(json.dumps({k: result[k] for k in ("phase", "passed_d2", "worst_spearman",
                                             "worst_forward_overlap_3px",
                                             "worst_overlap_beyond_chance")}, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=["surface", "final"])
    raise SystemExit(run(ap.parse_args().phase))
