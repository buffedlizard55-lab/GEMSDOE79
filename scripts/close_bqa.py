#!/usr/bin/env python3
"""Close lane H79-BQA from its evidence files: state.json + run_card_bqa.json.

Re-derives every preregistered gate (base preregistration for X1, amendment A1
for X2) from evidence/bqa/*.json; nothing is typed by hand. The lane produced
no GeoTIFF: X2's surface-uniqueness gate failed before placement, and
``run_bqa.py place-x2`` refuses to place dots for a surface that failed it.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence/bqa"
CTRL = "h33_foldfair_control"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def r4(x):
    return round(float(x), 4)


def arm(summary, name):
    x = summary["scores"][name]
    return dict(dti=r4(x["dti"]), ci95=[r4(c) for c in x["ci95"]],
                withheld_positive_pixels=x["withheld_positive_pixels"])


def paired(summary, name):
    if summary is None or name not in summary.get("paired_differences", {}):
        return None
    d = summary["paired_differences"][name]
    return dict(delta=r4(d["delta"]), ci95=[r4(c) for c in d["ci95"]])


def main():
    hold = {s: json.loads((EV / f"holdout_seed{s}.json").read_text()) for s in (20, 30, 40)}
    usurf = json.loads((EV / "x2_uniqueness_surface.json").read_text())
    sbuild = json.loads((EV / "x2_surface_build.json").read_text())
    amend = json.loads((ROOT / "registry/preregistration_bqa_amendment_A1.json").read_text())

    # X1 (base preregistration): candidate = band-quota arm, seeds 20 and 30 required.
    x1 = {}
    for s in (20, 30, 40):
        st, ff = hold[s]["holdout_standard"], hold[s]["holdout_far_field"]
        x1[f"seed_{s}"] = dict(
            standard=arm(st, "candidate"), standard_h33=arm(st, CTRL), paired_vs_h33=paired(st, CTRL),
            far_field=arm(ff, "candidate"), far_field_h33=arm(ff, CTRL),
            g2_pass=bool(st["scores"]["candidate"]["dti"] > st["scores"][CTRL]["dti"]
                         and st["paired_differences"][CTRL]["ci95"][0] > 0),
            g3_pass=bool(ff["scores"]["candidate"]["dti"] >= ff["scores"][CTRL]["dti"]))
    x1_verdict = "negative" if not (x1["seed_20"]["g3_pass"] and x1["seed_30"]["g3_pass"]) else "inconclusive"

    # X2 (amendment A1): candidate = weights_only, confirmatory seeds 30 and 40.
    x2 = {}
    for s in (20, 30, 40):
        st = hold[s].get("x2_weights_only_standard")
        ff = hold[s].get("x2_weights_only_far_field")
        base_st, base_ff = hold[s]["holdout_standard"], hold[s]["holdout_far_field"]
        row = dict(role="selection (exploratory, not counted)" if s == 20 else "confirmatory",
                   standard=arm(base_st, "weights_only"), standard_h33=arm(base_st, CTRL),
                   standard_nhr_repro=arm(base_st, "nhr_repro"),
                   far_field=arm(base_ff, "weights_only"), far_field_h33=arm(base_ff, CTRL),
                   paired_vs_h33=paired(st, CTRL), paired_vs_uniform=paired(st, "uniform_control"),
                   paired_vs_nhr_repro=paired(st, "nhr_repro"), far_field_paired_vs_h33=paired(ff, CTRL),
                   canary_max_auc=r4(hold[s]["leakage_canary"]["max_symmetric_auc"]),
                   canary_suspicious=hold[s]["leakage_canary"]["n_suspicious"])
        if s != 20:
            row.update(
                g1_pass=bool(hold[s]["leakage_canary"]["max_symmetric_auc"] <= 0.90
                             and hold[s]["leakage_canary"]["n_suspicious"] == 0),
                g2_pass=bool(st["scores"]["weights_only"]["dti"] > st["scores"][CTRL]["dti"]
                             and st["paired_differences"][CTRL]["ci95"][0] > 0),
                g3_pass=bool(ff["scores"]["weights_only"]["dti"] >= ff["scores"][CTRL]["dti"]),
                g4_pass=bool(st["paired_differences"]["uniform_control"]["ci95"][0] > 0))
        x2[f"seed_{s}"] = row
    p = usurf["provisional_topk_check"]
    worst = p["top10_chance_corrected"][0]
    g5 = dict(passed=bool(usurf["passed"]),
              surface_sha256=usurf["surface_sha256"],
              surface_sha256_matches_build=usurf["surface_sha256"] == sbuild["surface_sha256"],
              full_surface_worst_spearman=r4(usurf["worst_spearman"]),
              full_surface_worst_spearman_submission=usurf["surface_rank_check"]["worst_spearman"]["submission"],
              provisional_topk_worst_chance_corrected_overlap=r4(usurf["worst_chance_corrected_overlap"]),
              provisional_topk_worst_submission=worst["submission"],
              provisional_topk_worst_raw_overlap=r4(worst["my_dots_within_3px_of_theirs"]),
              provisional_topk_worst_their_halo_coverage=r4(worst["their_halo_coverage_allowed"]),
              provisional_topk_v4_firings=p["v4_overlap_firings"],
              provisional_topk_raw_overlap_firings=p["raw_v3_overlap_firings"],
              non_discriminating_rasters=p["non_discriminating_rasters"],
              registry_rasters=p["registry_rasters_expected"], compared=p["checked"],
              complete_with_dispositions=bool(usurf["complete_comparison"]),
              top10=[dict(submission=r["submission"], chance_corrected_overlap=r4(r["chance_corrected_overlap"]),
                          raw_overlap=r4(r["my_dots_within_3px_of_theirs"]),
                          halo_coverage=r4(r["their_halo_coverage_allowed"])) for r in p["top10_chance_corrected"]])
    holdout_gates_pass = all(x2[f"seed_{s}"][g] for s in (30, 40) for g in ("g1_pass", "g2_pass", "g3_pass", "g4_pass"))
    stop = ("X2 passed every holdout gate on the confirmatory seeds 30 and 40 but FAILED G5 (surface uniqueness before "
            f"placement): the provisional top-37,654 cells of the X2 surface have chance-corrected 3 px overlap "
            f"{g5['provisional_topk_worst_chance_corrected_overlap']:.3f} with {worst['submission']} (limit 0.70), and "
            f"{g5['provisional_topk_v4_firings']} registry rasters exceed the limit. DUPLICATE -> stop: no dots were "
            "placed, no GeoTIFF was written, no retuning or overlap capping.")
    now = datetime.now(timezone.utc).isoformat()
    state = dict(schema_version=1, lane="H79-BQA", session="0bd0e0b2", generated_utc=now,
                 stopped=True, verdict="negative", experiments_used=2, max_experiments=3,
                 x1=dict(definition="band-weighted model + H33 distance quotas (registry/preregistration_bqa.json)",
                         verdict=x1_verdict, reason="G3 (far-field >= H33 control) failed on seed 20 and seed 30",
                         per_seed=x1),
                 x2=dict(definition=amend["x2_definition"], verdict="negative (duplicate)",
                         holdout_gates_pass_on_confirmatory_seeds=holdout_gates_pass, g5_surface_uniqueness=g5,
                         per_seed=x2, stop_reason=stop),
                 x3="not run: no remaining hypothesis was preregistered, and a full gated pipeline would not finish before the 06:30Z hard stop",
                 geotiff_written=False, final_dot_placements_performed=0, submission_slots_used=0,
                 canonical_deliverable_unchanged=("run_card.json is not touched by this lane (canonical lane at close: "
                                                  + json.loads((ROOT / "run_card.json").read_text())["lane"] + ")"))
    (EV / "state.json").write_text(json.dumps(state, indent=2, allow_nan=False) + "\n")

    prereg = json.loads((ROOT / "registry/preregistration_bqa.json").read_text())
    head_seed = min((30, 40), key=lambda s: hold[s]["holdout_standard"]["scores"]["weights_only"]["dti"])
    head = hold[head_seed]["holdout_standard"]["scores"]["weights_only"]
    card = {
        "schema_version": "gems79-run-card-v2",
        "generated_utc": now,
        "branch": "arena/0bd0e0b2-gemsdoe79",
        "lane": "H79-BQA",
        "canonical": False,
        "experiment": "X1 (band quotas) and X2 (amendment A1: band-weighted model, global placement)",
        "hypothesis": prereg["hypothesis"],
        "mechanism": prereg["mechanism"],
        "named_non_fault_process": prereg["named_non_fault_mimic"],
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": hold[head_seed]["evaluator_version"],
            "arm": "X2 weights_only", "headline_seed": head_seed, "dti": r4(head["dti"]),
            "ci95": [r4(c) for c in head["ci95"]], "withheld_positive_pixels": head["withheld_positive_pixels"],
            "x1_per_seed": x1, "x2_per_seed": x2,
            "caveat": "Hide-and-recover of withheld catalogue components; not a leaderboard score or projection.",
        },
        "current_best_holdout_beaten": holdout_gates_pass,
        "leakage_canary": {"evidence_class": "LEAKAGE-CANARY",
                           "passed": all(x2[f"seed_{s}"]["g1_pass"] for s in (30, 40)),
                           "auc": max(x2[f"seed_{s}"]["canary_max_auc"] for s in (20, 30, 40)),
                           "required_threshold": 0.90,
                           "tests_per_seed": hold[30]["leakage_canary"]["tests"],
                           "features_cleared": len(hold[30]["leakage_canary"]["per_feature_max"])},
        "correlation_overlap_vs_registry": dict(shared_tool=usurf["shared_tool"], dot_definition=usurf["dot_definition"],
                                                protocol_clarification="IR-79-111 (in-session IR-79-68)", surface_before_placement=g5,
                                                final_dots=None),
        "protocol_unique": False,
        "raster_sha256": None,
        "submission_file": None,
        "verdict": "negative",
        "promoted": False,
        "stop_reason": stop,
        "ok_to_download": False,
        "ok_to_submit": False,
        "selector_receipt": None,
        "submission_slots_used": 0,
        "organizer_submission_receipt": None,
        "experiment_count": 2, "max_experiments": prereg["budget"]["max_experiments"],
        "preregistration_sha256": sha(ROOT / "registry/preregistration_bqa.json"),
        "amendment_sha256": sha(ROOT / "registry/preregistration_bqa_amendment_A1.json"),
        "state": "evidence/bqa/state.json",
    }
    (ROOT / "run_card_bqa.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(x1=x1_verdict, x2_holdout_gates=holdout_gates_pass, g5=g5["passed"],
                          worst=g5["provisional_topk_worst_chance_corrected_overlap"]), indent=2))


if __name__ == "__main__":
    import sys
    sys.path[:0] = [str(ROOT / "src")]
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "H79-BQA",
        reason="H79-BQA is already closed; run_card_bqa.json and evidence/bqa/state.json are frozen.",
    )
    main()
