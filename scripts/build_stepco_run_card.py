#!/usr/bin/env python3
"""Assemble the G79-STEPCO session run card from experiment evidence only.

Primary artifact = S1 (the preregistered first experiment). S2-COVER is
reported in full as the second, also-negative experiment. No number is
computed here that was not measured by the experiment scripts; validator
output is re-read from the writer receipts written by the shared writer.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
EV = ROOT / "evidence/stepco"
BUDGET = 37654


def load(p):
    return json.loads(Path(p).read_text())


def sparse_worst(rows):
    sub = [r for r in rows if "error" not in r and r["their_dots"] <= 2 * BUDGET]
    if not sub:
        return None
    w = max(sub, key=lambda r: r["my_dots_within_3px_of_theirs"])
    return {"n_comparable_sparse": len(sub),
            "worst_forward_overlap_3px": w["my_dots_within_3px_of_theirs"],
            "worst_submission": w["submission"], "worst_their_dots": w["their_dots"],
            "note": "Diagnostic subset: registry dot fields whose emitted mass is within 2x the candidate budget, i.e. the sparse emissions a copy would actually resemble. This subset view is reported alongside - never instead of - the literal and like-for-like readings."}


def holdout_block(exp_prefix):
    out = {}
    for seed in (20, 30):
        s = load(EV / f"holdout_{exp_prefix}_seed{seed}.json")
        out[f"seed_{seed}"] = {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": s["evaluator_version"],
            "candidate": s["scores"]["candidate"],
            "controls": {k: s["scores"][k] for k in
                         ("uniform_control", "dem_step_only_control", "h33_foldfair_control")},
            "paired_candidate_minus_h33_foldfair": s["paired_differences"]["h33_foldfair_control"],
        }
    return out


def main():
    prereg = load(ROOT / "registry/preregistration_g79stepco_20261022.json")
    s1 = load(EV / "experiment_s1_state.json")
    s2 = load(EV / "experiment_s2_state.json")
    feat = load(EV / "feature_receipt.json")
    can = {seed: load(EV / f"canaries_s1_seed{seed}.json") for seed in (20, 30)}
    uni_surf = load(EV / "uniqueness_s1_surface.json")
    uni_s1 = load(EV / "uniqueness_s1_final.json")
    uni_s2 = load(EV / "uniqueness_s1_final_s2.json")
    sup = load(EV / "uniqueness_supplementary.json")
    records = load(ROOT / ".cache/stepco/registry_records.json")
    pin = load(ROOT / "registry/template_pin.json")

    template_files = {r["path"]: hashlib.sha256((ROOT / r["path"]).read_bytes()).hexdigest()
                      for r in pin["files"]}
    card = {
        "schema_version": "gems79-run-card-v2-stepco",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "session_branch": "arena/220dabc8-gemsdoe79",
        "lane": "G79-STEPCO",
        "hypothesis": prereg["hypothesis"],
        "mechanism": prereg["mechanism"],
        "named_non_fault_process": prereg["named_non_fault_mimic"],
        "method_paragraph": prereg["method_paragraph"],
        "preregistration": "registry/preregistration_g79stepco_20261022.json",
        "preregistration_sha256": hashlib.sha256(
            (ROOT / "registry/preregistration_g79stepco_20261022.json").read_bytes()).hexdigest(),
        "protocol_amendment_D1": "reports/protocol_amendment_D1_20261022.md",
        "experiment_count": 2,
        "max_experiments": 3,
        "experiments": {
            "S1": {"description": "Fixed STEPCO surface/model; dots ranked by model probability p.",
                   "verdict": s1["verdict"], "raster_sha256": s1["raster_sha256"],
                   "submission_file": s1["submission_file"]},
            "S2_COVER": {"description": "Identical surface; dots ranked by shared expected_credit(p) (kernel-cover). Preregistered amendment before running.",
                         "verdict": s2["verdict"], "raster_sha256": s2["raster_sha256"],
                         "submission_file_as_written": s2["submission_file"],
                         "published_path": "archive/g79_stepco_s2/downloads/" + Path(s2["submission_file"]).name,
                         "archive_move_note": "Moved byte-identical (SHA-256 re-verified) so exactly one canonical artifact is published in docs/downloads/."},
            "S3": "Not run. Reserved by preregistration; no holdout-outcome tuning. A lidar-regime diagnostic showed no regime collapse that a structural variant would clearly repair, so the third experiment was deliberately not spent on search.",
        },
        "leakage_canary": {
            "passed": all(can[s]["passed"] for s in can),
            "auc": max(can[s]["max_symmetric_auc"] for s in can),
            "required_threshold": 0.90,
            "features_cleared": sum(len(can[s]["rows"]) for s in can),
            "per_seed": {f"seed_{s}": {"max_symmetric_auc": can[s]["max_symmetric_auc"],
                                        "worst_feature": can[s]["worst"]["feature"],
                                        "worst_fold": can[s]["worst"]["fold"],
                                        "tests": len(can[s]["rows"])} for s in can},
            "evidence_class": "LEAKAGE-CANARY",
        },
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-pooled-hide-v2",
            "instrument": "buffered whole-component hide-and-recover, buffer 3 px, quadrant erosion 12 px, pooled DTI alpha=0.2 beta=0.8, 300 m triangular kernel, 20 km spatial-cluster bootstrap (1000 draws)",
            "S1": holdout_block("s1"),
            "S2_COVER": holdout_block("s2"),
            "primary_seed20_candidate_for_status_gate": load(EV / "holdout_s1_seed20.json")["scores"]["candidate"],
            # flat mirror of the primary measurement for the generic status gate
            "dti": load(EV / "holdout_s1_seed20.json")["scores"]["candidate"]["dti"],
            "ci95": load(EV / "holdout_s1_seed20.json")["scores"]["candidate"]["ci95"],
            "withheld_positive_pixels": load(EV / "holdout_s1_seed20.json")["scores"]["candidate"]["withheld_positive_pixels"],
        },
        "holdout_gates": {"S1": s1["holdout_gates"], "S2_COVER": s2["holdout_gates"],
                          "promotion_gate": prereg["holdout"]["promotion_gate"],
                          "passed": False},
        "current_best_holdout_beaten": False,
        "correlation_overlap_vs_registry": {
            "indexed_rasters": records["indexed_total"],
            "accounted_for": "992/992: 986 grid-comparable vendor comparisons + 6 grid-invalid documented in evidence/stepco/uniqueness_supplementary.json",
            "surface_before_placement": {
                "worst_spearman_full_footprint": uni_surf["literal_summary"]["worst_spearman_full_footprint"],
                "worst_spearman_submission": uni_surf["literal_summary"]["worst_rho_submission"],
                "rho_limit": 0.90, "duplicate_by_rho": False,
                "checked_in_main_scan": 989},
            "final_dots_S1": {
                "literal_worst_forward_overlap": uni_s1["two_phase_summary"]["literal_reading"]["worst_forward_overlap"],
                "like_for_like_dotfield_worst_overlap": uni_s1["two_phase_summary"]["like_for_like_reading"]["worst_forward_overlap_dot_fields"],
                "like_for_like_worst_submission": uni_s1["two_phase_summary"]["like_for_like_reading"]["worst_forward_overlap_dot_field_submission"],
                "like_for_like_duplicate": uni_s1["two_phase_summary"]["like_for_like_reading"]["duplicate"],
                "matched_budget_dense_worst_overlap": uni_s1["matched_budget_worst_overlap"],
                "worst_final_spearman": uni_s1["two_phase_summary"]["literal_reading"]["worst_spearman_full_footprint"],
                "comparable_sparse_diagnostic": sparse_worst(uni_s1["rows"])},
            "final_dots_S2": {
                "like_for_like_duplicate": uni_s2["two_phase_summary"]["like_for_like_reading"]["duplicate"],
                "matched_budget_dense_worst_overlap": uni_s2["matched_budget_worst_overlap"],
                "comparable_sparse_diagnostic": sparse_worst(uni_s2["rows"])},
            "supplementary_late_restored_max_overlap": max(
                r["my_dots_within_3px_of_theirs"] for rows in sup["late_restored"].values() for r in rows),
            "interpretation": ("No rank-correlation duplication anywhere (surface worst rho 0.518 < 0.90; "
                               "final worst rho 0.086). The 70%/3 px overlap test nevertheless fires under both the literal "
                               "reading and the shared tool's like-for-like reading because the registry contains space-filling "
                               "priors (a 206,895-dot 5 px lattice and 49 continuous surfaces, one positive on every footprint cell) "
                               "whose 3 px halos cover the study area: any nonempty candidate overlaps them. Against comparable "
                               "sparse emissions the S1 worst overlap is below 0.70 and S2's is 0.70003. No reading is hidden; "
                               "under amendment D-1 as preregistered the candidate is NOT certified protocol-unique."),
        },
        "raster_sha256": s1["raster_sha256"],
        "surface_sha256": s1["surface_sha256"],
        "byte_distinct_from_all_992_pins": bool(s1["byte_distinct_from_all_992_pins"] and s2["byte_distinct_from_all_992_pins"]),
        "protocol_unique": False,
        "protocol_unique_scope": "False under amendment D-1 as preregistered (like-for-like dot-field reading fires on the space-filling lattice prior). Byte-distinct from all 992 pinned registry files; rank-correlation clear against all 986 grid-comparable rasters.",
        "validator_output": {
            "shared_validator": s1["writer_receipt"]["validator"],
            "reference_grid_validator": s1["writer_receipt"]["template_report"],
            "S2_shared_validator_all_passed": s2["writer_receipt"]["validator"]["all_checks_passed"],
            "validation_class": "local format/range preflight by re-reading written bytes; not organizer acceptance",
        },
        "positive_pixels": s1["writer_receipt"]["validator"]["emitted_positive_pixels"],
        "placement": s1["placement"],
        "submission_name": s1["submission_name"],
        "submission_note": s1["submission_note"],
        "submission_note_chars": len(s1["submission_note"]),
        "submission_file": s1["submission_file"],
        "zip_file": str(Path(s1["submission_file"]).with_suffix(".zip")),
        "artifact_kind": "newly computed binary dot GeoTIFF from an independently fitted surface; not a copy of any registry raster; not cleared for competition submission",
        "features": {"n_features": feat["n_features"], "names": feat["feature_names"],
                     "support_pixels": feat["support_pixels"], "input_sha256": feat["input_sha256"]},
        "source_provenance_verified": False,
        "source_provenance_note": "Inputs restored from immutable owner GitHub mirrors and SHA-256 verified against registry/data_manifest.json pins; mirror consistency is not organizer authentication (DrivenData data page requires login).",
        "ok_to_download": True,
        "ok_to_submit": False,
        "human_intervention_needed_for_this_verdict": False,
        "promoted": False,
        "approved_for_weekly_slot": False,
        "submission_slots_used": 0,
        "organizer_submission_receipt": None,
        "leaderboard_improvement_established": False,
        "verdict": "negative",
        "stop_reason": "holdout_tie_with_incumbent_and_uniqueness_not_certified",
        "blockers": [
            "Preregistered promotion gate failed in both experiments: candidate HOLDOUT-DTI statistically ties the fold-fair H33-lineage incumbent (S1 paired -0.0015 [-0.0153,+0.0110] seed 20; -0.0041 [-0.0191,+0.0111] seed 30) instead of beating it with CI above 0.",
            "Protocol uniqueness is not certified: under amendment D-1's like-for-like reading the 70%/3 px test still fires on space-filling registry priors (206,895-dot lattice; dense dot fields up to the shared tool's 20% support cut).",
            "Catalogue hide-and-recover measures recovery of mapped faults, not discovery of the organizer's hidden new faults; no leaderboard projection is made.",
            "Mirrored input provenance is hash-consistent but not organizer-authenticated; account weekly capacity and selector approval are unavailable to this pipeline.",
        ],
        "shared_template_commit": pin["commit"],
        "shared_template_files_sha256_verified": template_files == {r["path"]: r["sha256"] for r in pin["files"]},
        "prior_lane": "G79-FABRIC-OFFSET E1 remains a closed negative lane; its run card is preserved at archive/g79_fabric_offset_e1/run_card.json and its evidence is unchanged.",
    }
    payload = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "run_card_stepco.json").write_text(payload)
    (ROOT / "run_card.json").write_text(payload)          # canonical card (site + status)
    (ROOT / "evidence/run_card.json").write_text(payload)  # canonical evidence copy
    (EV / "run_card.json").write_text(payload)
    print(json.dumps({"verdict": card["verdict"], "raster_sha256": card["raster_sha256"],
                      "submission_file": card["submission_file"],
                      "note_chars": card["submission_note_chars"],
                      "canary_max_auc": card["leakage_canary"]["auc"]}, indent=2))


if __name__ == "__main__":
    main()
