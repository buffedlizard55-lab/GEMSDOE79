#!/usr/bin/env python3
"""H79-ASYM surface diagnostic (reporting only; does NOT change the gate verdict).

The literal surface gate in scripts/run_asym.py stopped the lane on one registry raster.
This script records every per-raster overlap so the user can decide IR-79-53 on evidence.

For each registry raster it reruns the shared comparison (gems57.uniqueness,
budget-matched-v3, identical inputs to the gate) and joins the result with the
per-raster halo coverage measured for H79-NHR (evidence/nhr/overlap_chance.json).
Halo coverage is the share of footprint cells within 3 px of the raster's own dots,
i.e. the chance level for a random 37,654-dot placement. A raster is labelled
space-filling when its halo coverage is above 0.70.

Outputs evidence/asym/surface_diagnostic.json (summary) and surface_diagnostic_rows.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared            # noqa: E402
from gems57.grid import load_grid                  # noqa: E402
import nhr_uniqueness                              # noqa: E402

BUDGET = 37654
CACHE = ROOT / ".cache" / "asym"
OUT = ROOT / "evidence" / "asym"
SPACE_FILLING = 0.70


def main():
    grid = load_grid(ROOT / "data/reference")
    inv, expected = nhr_uniqueness.inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    surface = np.load(CACHE / "final_surface.npy")
    prov = shared.budget_matched_dots(surface, grid.footprint & ~grid.catalogue, BUDGET).astype(np.float32)
    res = shared.compare_array_to_registry(prov, inv, grid.footprint, include_reverse=False,
                                           expected_grid=eg, dot_definition="budget-matched-v3")
    halo = {r["submission"]: r for r in json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())["rows"]}
    rows, errors = [], []
    for r in res["rows"]:
        if "error" in r:
            errors.append(dict(submission=r.get("submission"), error=r["error"]))
            continue
        h = halo.get(r["submission"])
        hc = None if h is None else h["halo_coverage"]
        ov = float(r["my_dots_within_3px_of_theirs"])
        rows.append(dict(submission=r["submission"], representation=r["representation"],
                         their_dots=r["their_dots"], overlap=ov,
                         spearman=r["spearman_full_footprint"], halo_coverage=hc,
                         space_filling=None if hc is None else bool(hc > SPACE_FILLING),
                         beyond_chance=None if hc is None or hc >= 1 else (ov - hc) / (1 - hc)))
    informative = [r for r in rows if r["space_filling"] is False]
    dense = [r for r in rows if r["space_filling"] is True]
    flagged_all = [r for r in rows if r["overlap"] > shared.OVERLAP_LIMIT]
    flagged_inf = [r for r in informative if r["overlap"] > shared.OVERLAP_LIMIT]
    worst_inf = max(informative, key=lambda r: r["overlap"]) if informative else None
    summary = dict(
        schema_version=1, lane="H79-ASYM", evidence_class="REGISTRY-MEASUREMENT (diagnostic, not a gate)",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest(),
        provisional_dots=int(prov.sum()), registry_rasters_expected=expected,
        compared=len(rows), errors=errors,
        space_filling_halo_gt_0_70=len(dense), informative_halo_le_0_70=len(informative),
        flagged_by_literal_gate_all=len(flagged_all),
        flagged_by_informative_only=len(flagged_inf),
        flagged_by_space_filling_only=len(flagged_all) - len(flagged_inf),
        worst_informative=worst_inf,
        worst_all=max(rows, key=lambda r: r["overlap"]) if rows else None,
        literal_rule_note="The literal gate fails when ANY raster exceeds 0.70. A space-filling raster (halo > 0.70) flags any dot set, so the literal rule rejects every submission (IR-79-53). This diagnostic does not change the verdict.",
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "surface_diagnostic_rows.json").write_text(json.dumps(rows, indent=1, default=float) + "\n")
    (OUT / "surface_diagnostic.json").write_text(json.dumps(summary, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n")
    print(json.dumps({k: summary[k] for k in ("compared", "space_filling_halo_gt_0_70", "informative_halo_le_0_70",
                                              "flagged_by_literal_gate_all", "flagged_by_informative_only")}, indent=2))
    print("worst informative:", worst_inf)


if __name__ == "__main__":
    main()
