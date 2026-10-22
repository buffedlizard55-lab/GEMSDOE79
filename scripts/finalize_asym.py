#!/usr/bin/env python3
"""Compose run_card_asym.json for H79-ASYM from evidence files only (no hand-typed numbers).

The card is archival for this lane. The canonical card stays run_card.json (H79-NHR).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence" / "asym"


def _load(p: Path):
    return json.loads(p.read_text())


def main():
    prereg_path = ROOT / "registry/preregistration_asym.json"
    prereg = _load(prereg_path)
    build = _load(EV / "surface_build.json")
    surf = _load(EV / "uniqueness_surface.json")
    diag_path = EV / "surface_diagnostic.json"
    diag = _load(diag_path) if diag_path.exists() else None

    worst = surf["worst_forward_overlap_3px"]
    worst_sub = surf["provisional_topk_check"]["worst_my_dots_within_3px_of_theirs"]
    rho_w = surf["surface_rank_check"]["worst_spearman_full_footprint"]
    card = dict(
        schema_version="gems79-run-card-asym-v1",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        branch="arena/4b1abd09-gemsdoe79",
        lane=prereg["lane"],
        registered_utc=prereg["registered_utc"],
        preregistration_sha256=hashlib.sha256(prereg_path.read_bytes()).hexdigest(),
        preregistration_commit="365b727",
        hypothesis=prereg["hypothesis"],
        mechanism=prereg["mechanism"],
        named_non_fault_process=prereg["named_non_fault_mimic"],
        experiment_count=1,
        max_experiments=prereg["budget"]["max_experiments"],
        max_hours=prereg["budget"]["max_hours"],
        stage_reached="surface duplicate gate (rule 1) failed before any placement",
        holdout_dti=dict(evidence_class="HOLDOUT-DTI", status="NOT RUN",
                         reason="The protocol stops a duplicate before placement; holdout placements were not run."),
        leakage_canary=dict(status="NOT RUN", reason="Depends on the holdout stage, which was not run."),
        surface=dict(
            surface_sha256=build["surface_sha256"],
            p999=build["p999"],
            valid_fraction_of_footprint=build["valid_fraction_of_footprint"],
            positive_cells=build["positive_cells"],
            surface_rank_check=dict(worst_spearman=rho_w["value"], worst_submission=rho_w["submission"],
                                    limit=0.90, passed=rho_w["value"] <= 0.90),
            provisional_topk_check=dict(worst_forward_overlap_3px=worst_sub["value"],
                                        worst_submission=worst_sub["submission"],
                                        worst_representation=worst_sub["representation"],
                                        worst_their_dots=worst_sub["their_dots"],
                                        limit=0.70, passed=worst_sub["value"] <= 0.70),
            complete_comparison=surf["complete_comparison"],
            registry_rasters_checked=surf["surface_rank_check"]["checked"],
            registry_rasters_expected=surf["registry_rasters_expected"],
        ),
        unexecuted_stages=["holdout", "final"],
        unexecuted_stages_note="scripts/run_asym.py holdout and final were not run; the surface gate stopped the lane first. They are a reviewed template only.",
        final_dots="NOT GENERATED (stopped before placement)",
        validator_output="NOT GENERATED (no raster was written)",
        raster_sha256=None,
        submission_name=None,
        submission_note=None,
        surface_diagnostic=None if diag is None else dict(
            evidence_class="REGISTRY-MEASUREMENT (diagnostic, not a gate)",
            compared=diag["compared"],
            space_filling_halo_gt_0_70=diag["space_filling_halo_gt_0_70"],
            informative_halo_le_0_70=diag["informative_halo_le_0_70"],
            flagged_by_literal_gate_all=diag["flagged_by_literal_gate_all"],
            flagged_by_informative_only=diag["flagged_by_informative_only"],
            worst_informative=diag["worst_informative"],
            errors=len(diag["errors"]),
        ),
        verdict="negative",
        promoted=False,
        ok_to_download=False,
        ok_to_submit=False,
        approved_for_weekly_slot=False,
        submission_slots_used=0,
        organizer_submission_receipt=None,
        leaderboard_claim="None. No holdout score and no artifact exist for this lane.",
        stop_reason=("DUPLICATE under the literal surface rule: a continuous registry surface "
                     f"({worst_sub['submission']}) has positive support on {worst_sub['their_dots']} "
                     "footprint cells, so any dot set overlaps it at 1.0. This is the space-filling "
                     "problem (IR-79-53), not a shared fabric. Lane stopped; no retuning or overlap capping."),
        irregularities=["IR-79-53", "IR-79-73", "IR-79-74", "IR-79-77"],
    )
    out = ROOT / "run_card_asym.json"
    out.write_text(json.dumps(card, indent=2, default=float) + "\n")
    print("wrote", out.name, card["verdict"], "ok_to_submit", card["ok_to_submit"])


if __name__ == "__main__":
    main()
