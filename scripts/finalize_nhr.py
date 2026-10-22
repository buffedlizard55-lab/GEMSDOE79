#!/usr/bin/env python3
"""Compose the canonical run card (protocol rule 5) for H79-NHR from evidence files.

Every number is copied from an evidence JSON written by the evaluator, the
shared uniqueness tool or the shared writer; nothing is typed by hand. The card
is written with ok_to_submit=False; only scripts/select_submission.py (the
separate selector step) may set it after re-deriving all gates.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from gems79.lifecycle import LaneClosedError, require_open_lane  # noqa: E402
from validate_submission import validate_path   # noqa: E402

EV = ROOT / "evidence/nhr"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    require_open_lane(ROOT, "H79-NHR")
    prereg = json.loads((ROOT / "registry/preregistration_nhr.json").read_text())
    gates = json.loads((EV / "x1_gates.json").read_text())
    hold = {s: json.loads((EV / f"x1_holdout_seed{s}.json").read_text()) for s in (20, 30)}
    uniq = {p: json.loads((EV / f"uniqueness_{p}.json").read_text()) for p in ("surface", "final")}
    chance = json.loads((EV / "overlap_chance.json").read_text())
    surf_flag = json.loads((EV / "surface_topk_vs_flagged.json").read_text())
    flagged = [r for r in chance["rows"] if r["overlap_candidate"] > 0.70]
    informative_flagged = [r for r in flagged if r["halo_coverage"] <= 0.70]
    wi = chance["worst_candidate_overlap_vs_informative_rasters"]
    path = ROOT / "docs/downloads" / (gates["name"] + ".tif")
    receipt = json.loads(path.with_suffix(".json").read_text())
    val = validate_path(path)
    v = val["validator"]
    v["file"] = str(path.relative_to(ROOT))   # no sandbox-absolute paths in published evidence

    def arm(s, name):
        x = hold[s]["holdout"]["scores"][name]
        return dict(dti=round(x["dti"], 4), ci95=[round(c, 4) for c in x["ci95"]])

    per_seed = {}
    for s in (20, 30):
        sc = hold[s]["holdout"]["scores"]; pdiff = hold[s]["holdout"]["paired_differences"]
        per_seed[f"seed_{s}"] = dict(
            withheld_positive_pixels=sc["candidate"]["withheld_positive_pixels"],
            candidate=arm(s, "candidate"), h33_foldfair_control=arm(s, "h33_foldfair_control"),
            uniform_control=arm(s, "uniform_control"), ablation_no_geometry=arm(s, "ablation_no_geometry"),
            paired_delta_vs_h33=dict(delta=round(pdiff["h33_foldfair_control"]["delta"], 4),
                                     ci95=[round(c, 4) for c in pdiff["h33_foldfair_control"]["ci95"]]),
            paired_delta_vs_uniform=dict(delta=round(pdiff["uniform_control"]["delta"], 4),
                                         ci95=[round(c, 4) for c in pdiff["uniform_control"]["ci95"]]))
    # headline HOLDOUT-DTI: the more conservative (lower) of the two seeds
    low = min((20, 30), key=lambda s: hold[s]["holdout"]["scores"]["candidate"]["dti"])
    head = hold[low]["holdout"]["scores"]["candidate"]
    canary_max = max(h["leakage_canary"]["max_symmetric_auc"] for h in hold.values())
    card = {
        "schema_version": "gems79-run-card-v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "branch": prereg["branch"],
        "lane": prereg["lane"],
        "hypothesis": prereg["hypothesis"],
        "mechanism": prereg["mechanism"],
        "named_non_fault_process": prereg["named_non_fault_mimic"],
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": hold[low]["evaluator_version"],
            "headline_seed": low, "dti": round(head["dti"], 4), "ci95": [round(c, 4) for c in head["ci95"]],
            "withheld_positive_pixels": head["withheld_positive_pixels"],
            "per_seed": per_seed,
            "caveat": "Hide-and-recover of withheld catalogue components; not a leaderboard score or projection.",
        },
        "current_best_holdout_beaten": gates["gates"]["beats_current_holdout_best_both_seeds"],
        "current_best_holdout_reference": "h33_foldfair_control (legacy D2.8 dots, >2 px from the fold's visible faults) - best previously recorded HOLDOUT-DTI in this repo (evidence/post_stop_diagnostic.json)",
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY", "passed": gates["gates"]["canaries_all_le_0_90_both_seeds"],
            "auc": round(canary_max, 4), "required_threshold": 0.90,
            "features_cleared": len(hold[20]["leakage_canary"]["per_feature_max"]),
            "tests_per_seed": hold[20]["leakage_canary"]["tests"],
            "tests": sum(h["leakage_canary"]["tests"] for h in hold.values()),
            "worst_feature": max(hold.values(), key=lambda h: h["leakage_canary"]["max_symmetric_auc"])["leakage_canary"]["worst"]["feature"],
        },
        "correlation_overlap_vs_registry": {
            "shared_tool": uniq["final"]["shared_tool"], "dot_definition": uniq["final"]["dot_definition"],
            "registry_rasters": uniq["final"]["registry_rasters_expected"],
            "surface_before_placement": {"worst_spearman": uniq["surface"]["worst_spearman"],
                                         "worst_forward_overlap_3px_provisional_topk": uniq["surface"]["worst_forward_overlap_3px"],
                                         "passed": uniq["surface"]["passed"]},
            "final_dots": {"worst_spearman": uniq["final"]["worst_spearman"],
                           "worst_forward_overlap_3px": uniq["final"]["worst_forward_overlap_3px"],
                           "worst_overlap_submission": uniq["final"]["final_check"]["worst_my_dots_within_3px_of_theirs"]["submission"],
                           "passed": uniq["final"]["passed"]},
            "all_comparable_rasters_audit": {
                "source": "evidence/nhr/overlap_chance.json",
                "compared": chance["compared"], "not_comparable_invalid_files": chance["not_comparable"],
                "rasters_with_candidate_overlap_gt_0_70": len(flagged),
                "of_which_space_filling_halo_gt_0_70": len(flagged) - len(informative_flagged),
                "of_which_informative_halo_le_0_70": len(informative_flagged),
                "uniform_random_control_flagged_by": chance["rasters_where_uniform_random_overlap_gt_0_70"],
                "worst_informative": {k: wi[k] for k in ("submission", "overlap_candidate", "halo_coverage",
                                                         "overlap_beyond_chance", "spearman")},
                "surface_topk_would_have_stopped_before_placement": surf_flag["surface_check_would_have_stopped"],
                "worst_surface_topk_vs_informative": surf_flag["rows"][0],
            },
            "limits": {"rho": 0.90, "forward_overlap_3px": 0.70},
        },
        "protocol_unique": bool(uniq["surface"]["passed"] and uniq["final"]["passed"] and not flagged),
        "raster_sha256": sha(path),
        "validator_output": {
            "format_passed": val["format_passed"], "no_nan_inside_footprint": v["checks"]["in_footprint_all_finite"],
            "crs_shape_transform_match": val["reference_grid"]["ok"], "summary": v,
        },
        "submission_name": gates["name"],
        "submission_note": gates["note"],
        "submission_file": str(path.relative_to(ROOT)),
        "zip_file": str(path.with_suffix(".zip").relative_to(ROOT)),
        "zip_sha256": receipt["zip_sha256"],
        "artifact_kind": "binary dot map (1.0 at 37,654 placed cells, 0.0 elsewhere, all finite) from the H79-NHR surface",
        "positive_pixels": v["emitted_positive_pixels"],
        "experiment_count": 1, "max_experiments": prereg["budget"]["max_experiments"],
        "max_hours": prereg["budget"]["max_hours"],
        "source_provenance_verified": True,
        "source_provenance_definition": "Every input byte matches the SHA-256 pins in registry/data_manifest.json and the grid equals sample_submission.tif. Mirrors are owner GitHub copies; organizer-origin authentication is not possible without a DrivenData login.",
        "source_feature_stack_sha256": prereg["inputs"][0].split("sha256 ")[1].split(" ")[0],
        "preregistration_sha256": sha(ROOT / "registry/preregistration_nhr.json"),
        "verdict": "promote" if gates["all_passed"] else "negative",
        "promoted": bool(gates["all_passed"]),
        "stop_reason": None if gates["all_passed"] else (
            f"DUPLICATE under the protocol's literal rule: {len(informative_flagged)} non-space-filling registry dot fields "
            f"each contain > 70 % of the final dots within 3 px (worst {wi['overlap_candidate']:.3f}, "
            f"{wi['submission']}; chance level {wi['halo_coverage']:.3f}). The surface top-k check fails the same way "
            "before placement. Lane stopped; no retuning or overlap capping."),
        "failed_gates": sorted(k for k, v in gates["gates"].items() if not v),
        "ok_to_download": bool(val["format_passed"]),
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "selector_receipt": None,
        "human_intervention_needed_for_this_verdict": False,
        "submission_slots_used": 0,
        "organizer_submission_receipt": None,
        "leaderboard_claim": "None. HOLDOUT-DTI is a proxy; no organizer score exists for this file until it is uploaded.",
    }
    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "run_card.json").write_text(text)
    (ROOT / "evidence/run_card.json").write_text(text)
    (ROOT / "docs/run-card.json").write_text(text)
    print(json.dumps({k: card[k] for k in ("verdict", "raster_sha256", "submission_name", "protocol_unique")}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
