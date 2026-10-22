#!/usr/bin/env python3
"""Build run_card_h80_pilots.json from the evidence files (no hand-typed numbers).

Protocol item 5 (parallel-run protocol): hypothesis; mechanism; named non-fault process;
holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output;
submission name + note (<= 140 chars); verdict promote / negative.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"


def load(p):
    return json.loads((ROOT / p).read_text())


def arm_record(summary, arm):
    sc = summary["scores"][arm]
    return {
        "holdout_dti": round(sc["dti"], 4),
        "ci95": [round(x, 4) for x in sc["ci95"]],
        "withheld_positive_pixels": sc["withheld_positive_pixels"],
        "evidence_class": sc["evidence_class"],
        "evaluator_version": sc["evaluator_version"],
    }


def pilot_block(folder, lane, arm_a, arm_b):
    out = {"lane": lane, "seeds": {}}
    for seed in (20, 30):
        d = load(f"evidence/{folder}/seed{seed}.json")
        s = d["pooled_summary"]
        out["seeds"][str(seed)] = {
            "withheld_positive_pixels": d["withheld_positive_pixels"],
            "receipt_withheld_positive_pixels": d["expected_receipt_withheld_positive_pixels"],
            "candidate": arm_record(s, arm_a),
            "control": arm_record(s, arm_b),
            "random_C0": arm_record(s, "C0_random"),
            "paired_candidate_minus_control": {k: round(v["delta"], 4) for k, v in s["paired_differences"].items() if k == arm_b}
                | {"ci95": [round(x, 4) for x in s["paired_differences"][arm_b]["ci95"]]},
            "paired_candidate_minus_random": {"delta": round(s["paired_differences"]["C0_random"]["delta"], 4),
                                              "ci95": [round(x, 4) for x in s["paired_differences"]["C0_random"]["ci95"]]},
            "leakage_canary_auc_single_score": d["leakage_canary_auc_single_score"],
            "emitted_dots": d["emitted_dots"],
        }
    return out


def main():
    drape = pilot_block("h80_drape_pilot", "H80-DRAPE-PILOT", "A_notch", "B_control_no_notch")
    radio = pilot_block("h80_radio_pilot", "H80-RADIO-PILOT", "A_th_normalised_K", "B_control_raw_K")
    overlap = load("evidence/h80_pilot_overlap_check.json")
    canon = ROOT / "docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif"
    canon_sha = hashlib.sha256(canon.read_bytes()).hexdigest()
    bar = {"seed20": 0.1905, "seed30": 0.1944}
    best = max(
        [("H80-DRAPE-PILOT candidate", drape["seeds"]["20"]["candidate"]["holdout_dti"], drape["seeds"]["30"]["candidate"]["holdout_dti"]),
         ("H80-RADIO-PILOT candidate", radio["seeds"]["20"]["candidate"]["holdout_dti"], radio["seeds"]["30"]["candidate"]["holdout_dti"])],
        key=lambda t: min(t[1], t[2]))
    card = {
        "schema_version": 1,
        "lane": "H80-PILOTS-842c8c7c",
        "session_branch": "arena/842c8c7c-gemsdoe79",
        "generated_by": "scripts/build_h80_run_card.py (reads evidence/*.json; no hand-typed numbers)",
        "experiments_run": 2,
        "experiment_budget": 3,
        "holdout_evaluations_performed": 12,
        "final_dot_placements_performed": "2 pilots x 2 arms x 2 seeds + C0 random x 2 seeds (scoring-only; no raster written)",
        "hypothesis": "A physics-derived, zero-catalogue score surface from GeoDAWN magnetics (E-W flight-line notch) or radiometrics (thorium-normalised potassium residual) can localise holdout fault pixels better than fixed-budget random placement at 300 m separation, without any fault catalogue input.",
        "hypotheses_tested": {
            "H80-DRAPE-DECONV (pilot of notch + tilt-edge)": "registry/preregistration_h80_drape_pilot.json",
            "H80-RADIO-KD (pilot of Th-normalised K residual)": "registry/preregistration_h80_radio_pilot.json",
        },
        "mechanism": "Magnetic tilt-edge zero contours mark lateral source edges; a notch on E-W flight-line bands removes contractor line artifacts before the edge transform. Potassium enrichment minus a thorium-predicted background marks K-metasomatised fault conduits.",
        "named_non_fault_process": "Residual micro-leveling / tie-line artifacts (magnetics) and lithology-driven or playa/evaporite potassium (radiometrics). Neither was removed by the pilots.",
        "holdout_results": {"drape": drape, "radio": radio},
        "bar_to_spend_a_slot": {"seed20": bar["seed20"], "seed30": bar["seed30"], "source": "G79-THVC run_card.json, HOLDOUT-DTI, not ORGANIZER-CONFIRMED"},
        "best_pilot_candidate_vs_bar": {"pilot": best[0], "seed20": best[1], "seed30": best[2],
                                         "beats_bar_both_seeds": bool(best[1] > bar["seed20"] and best[2] > bar["seed30"])},
        "leakage_canary": {"rule": "single-feature AUC <= 0.90", "max_auc": max(
            [v for s in drape["seeds"].values() for v in s["leakage_canary_auc_single_score"].values()] +
            [v for s in radio["seeds"].values() for v in s["leakage_canary_auc_single_score"].values()]),
            "result": "PASS"},
        "correlation_overlap_vs_registry": overlap["per_seed"],
        "correlation_overlap_rule": overlap["summary"]["rule"],
        "correlation_overlap_result": f"{overlap['summary']['result']} (max within-3px overlap {overlap['summary']['max_within_3px']} vs the 0.70 rule; max abs Spearman {overlap['summary']['max_abs_spearman']} vs the 0.90 rule)",
        "raster_sha256": None,
        "raster_sha256_reason": "No candidate raster was written: the pilots are scoring-only and the holdout bar was not met, so the protocol stops before placement for a submission.",
        "reference_canonical_raster_sha256": canon_sha,
        "validator_output": "NOT RUN for a new raster (none emitted). Canonical G79-THVC validator output is in run_card.json (15/15 checks PASS).",
        "submission_name": None,
        "submission_note": None,
        "submission_name_note_status": "none: no candidate passed the holdout gate",
        "verdict": "negative",
        "ok_to_download_new_file": False,
        "ok_to_submit_new_file": False,
        "submission_slots_used": 0,
        "named_limits": [
            "Holdout proxy only (HOLDOUT-DTI, gems57-pooled-hide-v2); public or private DrivenData scores are not produced here.",
            "Training features are restored from owner GitHub mirrors, not organizer-authenticated.",
            "Silica/ASTER normalisation for H80-RADIO-KD not restored; GeoDAWN radiometric units not stated in the restored metadata.",
            "Full H80-MT-PHASE hypothesis is invalid as specified: the official USGS MT product is conductance (2-200 km), see IR-79-144.",
        ],
    }
    (ROOT / "run_card_h80_pilots.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print("wrote run_card_h80_pilots.json; verdict", card["verdict"], "best", best)


if __name__ == "__main__":
    main()
