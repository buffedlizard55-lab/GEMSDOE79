#!/usr/bin/env python3
"""H79-FF1 duplicate gate (shared gems57.uniqueness, budget-matched-v3).
Phases: surface (rank corr + provisional band-placed dots, BEFORE final-dots
stage) | final (placed dots). Thresholds: rho>0.90 or >70% dots within 3px."""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared
from gems57.grid import load_grid
from gems79.placement import place
from nhr_uniqueness import inventory, compact
BUDGET = 37654
CACHE = ROOT / ".cache" / "ff1"; OUT = ROOT / "evidence" / "ff1"
def run(phase):
    grid = load_grid(ROOT / "data/reference"); inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    result = dict(schema_version=1, lane="H79-FF1", phase=phase, evidence_class="REGISTRY-MEASUREMENT",
                  generated_utc=datetime.now(timezone.utc).isoformat(), dot_definition="budget-matched-v3",
                  registry_rasters_expected=expected)
    if phase == "surface":
        surf = np.load(CACHE / "final_surface.npy"); band = np.load(CACHE / "final_band.npy")
        r = shared.compare_array_to_registry(surf, inv, grid.footprint, include_reverse=False, expected_grid=eg, dot_definition="budget-matched-v3")
        sc = compact(r, ("spearman_full_footprint",))
        prov, info = place(surf, band, BUDGET)
        np.save(CACHE / "provisional_dots.npy", prov)
        rp = shared.compare_array_to_registry(prov.astype(np.float32), inv, grid.footprint, include_reverse=False, expected_grid=eg, dot_definition="budget-matched-v3")
        pc = compact(rp, ("my_dots_within_3px_of_theirs", "spearman_full_footprint"))
        rho = sc["worst_spearman_full_footprint"]["value"]; ov = pc["worst_my_dots_within_3px_of_theirs"]["value"]
        result.update(surface_rank_check=sc, provisional_check=pc, provisional_dots=int(prov.sum()), placement=info,
                      worst_spearman=rho, worst_forward_overlap_3px=ov,
                      complete_comparison=bool(sc["complete"] and pc["complete"] and not sc["errors"] and not pc["errors"]))
    else:
        dots = np.load(CACHE / "final_dots.npy")
        r = shared.compare_array_to_registry(dots.astype(np.float32), inv, grid.footprint, include_reverse=True, expected_grid=eg, dot_definition="budget-matched-v3")
        fc = compact(r, ("my_dots_within_3px_of_theirs", "spearman_full_footprint"))
        rho = fc["worst_spearman_full_footprint"]["value"]; ov = fc["worst_my_dots_within_3px_of_theirs"]["value"]
        result.update(final_check=fc, my_dots=int(dots.sum()), dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
                      worst_spearman=rho, worst_forward_overlap_3px=ov,
                      top10_overlap=sorted(({"submission": x["submission"], "overlap": x["my_dots_within_3px_of_theirs"], "spearman": x["spearman_full_footprint"]} for x in r["rows"] if "error" not in x), key=lambda d: -d["overlap"])[:10],
                      complete_comparison=bool(fc["complete"] and not fc["errors"]))
    result.update(duplicate=bool((result["worst_spearman"] or 0) > shared.RHO_LIMIT or result["worst_forward_overlap_3px"] > shared.OVERLAP_LIMIT),
                  passed=bool(result["complete_comparison"] and not ((result["worst_spearman"] or 0) > shared.RHO_LIMIT or result["worst_forward_overlap_3px"] > shared.OVERLAP_LIMIT)))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"uniqueness_{phase}.json").write_text(json.dumps(result, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n")
    print(json.dumps({k: result[k] for k in ("phase","worst_spearman","worst_forward_overlap_3px","complete_comparison","duplicate","passed")}, indent=2))
if __name__ == "__main__":
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "H79-FF1",
        reason="H79-FF1 is stopped and archived; uniqueness receipts in evidence/ff1/ are frozen.",
    )
    ap = argparse.ArgumentParser(); ap.add_argument("phase", choices=["surface","final"]); run(ap.parse_args().phase)
