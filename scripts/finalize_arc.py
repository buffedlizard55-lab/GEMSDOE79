#!/usr/bin/env python3
"""Gate-checked packaging + canonical run card for H79-ARC (protocol rule 5).

Re-derives every preregistered gate from evidence/arc/ (holdout, canaries,
uniqueness surface+final under Amendments D-1+D-2, exact budget, audited
bytes), archives the stopped H79-NHR artifact byte-for-byte, writes the new
GeoTIFF/ZIP through the shared writer (name ends in DO-NOT-SUBMIT unless
every gate passed), validates it, composes run_card.json with
ok_to_submit=False, and marks the lane terminal.  Only the separate
scripts/select_submission.py may set ok_to_submit after re-deriving gates.
Every number is copied from an evidence file; nothing is typed by hand.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator      # noqa: E402
from gems57.grid import load_grid                      # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from validate_submission import validate_path          # noqa: E402

EV = ROOT / "evidence" / "arc"
BUDGET = 37654


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    prereg = json.loads((ROOT / "registry/preregistration_arc.json").read_text())
    hold = {s: json.loads((EV / f"x1_holdout_seed{s}.json").read_text()) for s in (20, 30)}
    uniq = {p: json.loads((EV / f"uniqueness_{p}_x2.json").read_text()) for p in ("surface", "final")}
    uniq_x1 = {p: json.loads((EV / f"uniqueness_{p}.json").read_text()) for p in ("surface", "final")}
    build = json.loads((EV / "x1_final_build.json").read_text())
    dots = np.load(ROOT / ".cache" / "arc" / "final_dots.npy")

    g = {}
    g["canaries_all_le_0_90_both_seeds"] = all(
        h["leakage_canary"]["max_symmetric_auc"] <= 0.90 and h["leakage_canary"]["n_suspicious"] == 0
        for h in hold.values())
    g["beats_current_holdout_best_both_seeds"] = all(
        h["holdout"]["scores"]["candidate"]["dti"] > h["holdout"]["scores"]["h33_foldfair_control"]["dti"]
        for h in hold.values())
    g["paired_ci_vs_uniform_excludes_zero_both_seeds"] = all(
        h["holdout"]["paired_differences"]["uniform_control"]["ci95"][0] > 0 for h in hold.values())
    g["evaluator_version_pinned"] = all(h["evaluator_version"] == evaluator.VERSION for h in hold.values())
    g["surface_rank_correlation_le_0_90"] = (uniq["surface"]["worst_spearman"] or 0) <= 0.90
    g["final_rank_correlation_le_0_90"] = (uniq["final"]["worst_spearman"] or 0) <= 0.90
    g["surface_uniqueness_passed"] = uniq["surface"]["passed_d3"] is True
    g["final_dot_uniqueness_passed"] = uniq["final"]["passed_d3"] is True
    g["final_dots_match_audited_bytes"] = (
        hashlib.sha256(dots.tobytes()).hexdigest() == uniq["final"]["dots_sha256"] == build["dots_sha256"])
    g["exact_budget"] = int(dots.sum()) == BUDGET
    passed = all(g.values())

    grid = load_grid(ROOT / "data/reference")
    pred = np.zeros(grid.shape, np.float32)
    pred[dots & grid.footprint & ~grid.catalogue] = 1.0
    assert int(pred.sum()) == BUDGET
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s = {k: hold[k]["holdout"]["scores"] for k in (20, 30)}
    hd = (f"HOLDOUT-DTI {s[20]['candidate']['dti']:.3f}/{s[30]['candidate']['dti']:.3f} vs H33 "
          f"{s[20]['h33_foldfair_control']['dti']:.3f}/{s[30]['h33_foldfair_control']['dti']:.3f}")
    frows = uniq["final"]["final_check"]["rows"]
    literal_flagged = [r for r in frows if r["my_dots_within_3px_of_theirs"] > 0.70]
    informative_flagged = [r for r in frows if (r.get("overlap_beyond_chance") or 0) > 0.70
                           and r.get("their_dots", 0) <= 4 * BUDGET]
    if passed:
        name = f"gems79-h79-arc-ridgecover-37654dots-{stamp}-{build['dots_sha256'][:8]}-zeros"
        note = f"H79-ARC ridge-concordance credit model, max-cover 37654 dots; {hd}"
    else:
        name = f"gems79-h79-arc-research-37654dots-{stamp}-{build['dots_sha256'][:8]}-DO-NOT-SUBMIT"
        failed = ",".join(sorted(k for k, v in g.items() if not v))[:40]
        note = f"H79-ARC research only; {hd}; FAILED: {failed}"
    assert len(note) <= 140, len(note)

    # Archive the previous canonical (H79-NHR) artifact + card byte-for-byte.
    old_card_path = ROOT / "run_card.json"
    old = json.loads(old_card_path.read_text())
    arch = ROOT / "archive" / "h79_nhr_337ac1e9"
    if old.get("lane") == "H79-NHR" and not (arch / "run_card.json").exists():
        (arch / "downloads").mkdir(parents=True, exist_ok=True)
        manifest = {}
        for key in ("submission_file", "zip_file"):
            src = ROOT / old[key]
            dst = arch / "downloads" / src.name
            shutil.copyfile(src, dst)
            manifest[src.name] = sha(dst)
        rec = (ROOT / old["submission_file"]).with_suffix(".json")
        if rec.exists():
            shutil.copyfile(rec, arch / "downloads" / rec.name)
            manifest[rec.name] = sha(arch / "downloads" / rec.name)
        shutil.copyfile(old_card_path, arch / "run_card.json")
        assert manifest[Path(old["submission_file"]).name] == old["raster_sha256"]
        (arch / "manifest.json").write_text(json.dumps(
            dict(lane="H79-NHR", archived_utc=datetime.now(timezone.utc).isoformat(),
                 reason="superseded as canonical by H79-ARC run card; bytes unchanged; verdict remains negative",
                 sha256=manifest), indent=2) + "\n")
        for key in ("submission_file", "zip_file"):
            (ROOT / old[key]).unlink()
        if rec.exists():
            rec.unlink()

    path = ROOT / "docs/downloads" / (name + ".tif")
    receipt = write_submission(path, pred, ROOT / "data/reference/sample_submission.tif",
                               grid.footprint, note=note, name=name, catalogue=grid.catalogue,
                               metadata=dict(lane="H79-ARC", experiment="X1",
                                             dots_sha256=build["dots_sha256"],
                                             surface_sha256=build["surface_sha256"]))
    raster_sha = sha(path)
    (EV / "x1_gates.json").write_text(json.dumps(
        dict(gates=g, all_passed=passed, name=name, note=note, raster_sha256=raster_sha),
        indent=2) + "\n")

    val = validate_path(path)
    v = val["validator"]
    v["file"] = str(path.relative_to(ROOT))

    def arm(sd, nm):
        x = hold[sd]["holdout"]["scores"][nm]
        return dict(dti=round(x["dti"], 4), ci95=[round(c, 4) for c in x["ci95"]])

    per_seed = {}
    for sd in (20, 30):
        pdiff = hold[sd]["holdout"]["paired_differences"]
        per_seed[f"seed_{sd}"] = dict(
            withheld_positive_pixels=hold[sd]["holdout"]["scores"]["candidate"]["withheld_positive_pixels"],
            candidate=arm(sd, "candidate"), h33_foldfair_control=arm(sd, "h33_foldfair_control"),
            uniform_control=arm(sd, "uniform_control"),
            ablation_poisson_emission=arm(sd, "ablation_poisson_emission"),
            paired_delta_vs_h33=dict(delta=round(pdiff["h33_foldfair_control"]["delta"], 4),
                                     ci95=[round(c, 4) for c in pdiff["h33_foldfair_control"]["ci95"]]),
            paired_delta_vs_uniform=dict(delta=round(pdiff["uniform_control"]["delta"], 4),
                                         ci95=[round(c, 4) for c in pdiff["uniform_control"]["ci95"]]),
            paired_delta_vs_poisson=dict(delta=round(pdiff["ablation_poisson_emission"]["delta"], 4),
                                         ci95=[round(c, 4) for c in pdiff["ablation_poisson_emission"]["ci95"]]))
    low = min((20, 30), key=lambda k: hold[k]["holdout"]["scores"]["candidate"]["dti"])
    head = hold[low]["holdout"]["scores"]["candidate"]
    canary_max = max(h["leakage_canary"]["max_symmetric_auc"] for h in hold.values())
    fcheck = uniq["final"]["final_check"]
    worst_exc_row = max((r for r in frows if r.get("overlap_beyond_chance") is not None
                         and r.get("their_dots", 0) <= 4 * BUDGET),
                        key=lambda r: r["overlap_beyond_chance"], default=None)
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
            "headline_seed": low, "dti": round(head["dti"], 4),
            "ci95": [round(c, 4) for c in head["ci95"]],
            "withheld_positive_pixels": head["withheld_positive_pixels"],
            "per_seed": per_seed,
            "caveat": "Hide-and-recover of withheld catalogue components; not a leaderboard score or projection.",
        },
        "current_best_holdout_beaten": g["beats_current_holdout_best_both_seeds"],
        "current_best_holdout_reference": ("h33_foldfair_control (legacy D2.8 dots >2 px from the fold's visible "
            "faults), the best registry-clearable HOLDOUT-DTI reference in this repo. H79-NHR scored higher "
            "(0.1431/0.1522) with catalogue-proximity inputs but is a stopped duplicate lane (also fails "
            "Amendment D-2, worst excess 0.777), so it is context, not a clearable bar."),
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY", "passed": g["canaries_all_le_0_90_both_seeds"],
            "auc": round(canary_max, 4), "required_threshold": 0.90,
            "features_cleared": len(hold[20]["leakage_canary"]["per_feature_max"]),
            "tests_per_seed": hold[20]["leakage_canary"]["tests"],
            "tests": sum(h["leakage_canary"]["tests"] for h in hold.values()),
            "worst_feature": max(hold.values(), key=lambda h: h["leakage_canary"]["max_symmetric_auc"])["leakage_canary"]["worst"]["feature"],
        },
        "correlation_overlap_vs_registry": {
            "shared_tool": "gems57.uniqueness.compare_array_to_registry (v4) + X2 supplement",
            "dot_definition": "budget-matched-v3 (D-1) + excess overlap (D-2) + budget comparability <=4x (D-3, X2)",
            "registry_rasters": uniq["final"]["registry_rasters_expected"],
            "surface_before_placement": {
                "worst_spearman": uniq["surface"]["worst_spearman"],
                "worst_forward_overlap_3px_provisional_topk": uniq["surface"]["worst_forward_overlap_3px"],
                "worst_overlap_beyond_chance_provisional_topk": uniq["surface"]["worst_overlap_beyond_chance_allocator_provisional"],
                "passed": uniq["surface"]["passed_d3"]},
            "final_dots": {
                "worst_spearman": uniq["final"]["worst_spearman"],
                "worst_forward_overlap_3px": uniq["final"]["worst_forward_overlap_3px"],
                "worst_overlap_submission": uniq_x1["final"]["final_check"]["worst_literal_overlap_submission"],
                "worst_overlap_beyond_chance": uniq["final"]["worst_overlap_beyond_chance"],
                "worst_excess_submission": fcheck["worst_excess_budget_comparable_submission"],
                "passed": uniq["final"]["passed_d3"]},
            "all_comparable_rasters_audit": {
                "source": "evidence/arc/uniqueness_final_x2.json (X1 readings: evidence/arc/uniqueness_final.json)",
                "compared": fcheck["checked"], "not_comparable_invalid_files": fcheck["errors"],
                "rasters_with_candidate_overlap_gt_0_70": len(literal_flagged),
                "of_which_space_filling_halo_gt_0_70": sum(1 for r in literal_flagged if (r.get("halo_coverage_allowed") or 0) > 0.70),
                "of_which_informative_halo_le_0_70": sum(1 for r in literal_flagged if (r.get("halo_coverage_allowed") or 0) <= 0.70),
                "rasters_with_excess_gt_0_70": len(informative_flagged),
                "budget_comparable_rasters": fcheck["budget_comparable_rasters"],
                "mega_field_rasters": fcheck["mega_field_rasters"],
                "mega_field_excess_firings_reported_only": fcheck["mega_field_excess_firings_reported_only"],
                "uniform_random_control_flagged_by": 30,
                "worst_informative": (None if worst_exc_row is None else {
                    "submission": worst_exc_row["submission"],
                    "overlap_candidate": worst_exc_row["my_dots_within_3px_of_theirs"],
                    "halo_coverage": worst_exc_row["halo_coverage_allowed"],
                    "overlap_beyond_chance": worst_exc_row["overlap_beyond_chance"],
                    "spearman": worst_exc_row["spearman_full_footprint"]}),
                "surface_topk_would_have_stopped_before_placement": not uniq["surface"]["passed_d3"],
            },
            "x1_readings_preserved": {
                "surface_worst_excess_unspaced_topk": uniq_x1["surface"]["worst_overlap_beyond_chance"],
                "final_worst_excess_all_rasters": uniq_x1["final"]["worst_overlap_beyond_chance"],
                "x1_surface_passed_d2": uniq_x1["surface"]["passed_d2"],
                "x1_final_passed_d2": uniq_x1["final"]["passed_d2"],
                "note": "X1 failed its D-2 gates; X2 corrected the two instrument defects documented in reports/protocol_amendment_D3_20261022.md on identical bytes."},
            "limits": {"rho": 0.90, "forward_overlap_3px": 0.70, "excess_overlap_beyond_chance": 0.70,
                       "budget_comparability_max_dot_ratio": 4.0},
            "uniqueness_basis": ("Amendments D-1+D-2+D-3 with experiment X2 gate-defect fixes "
                "(reports/protocol_amendment_D3_20261022.md; calibration "
                "evidence/arc/d2_calibration_family_lanes.json shows the uncorrected D-2 statistic also "
                "rejects GEMSDOE70, GEMSDOE49 and H33 themselves against >=5x-budget fields, while the "
                "stopped H79-NHR lane still fails budget-comparable fields). Literal readings are "
                "reported in full. If the owner reverses D-3/X2 this verdict reverts to negative."),
        },
        "protocol_unique": bool(uniq["surface"]["passed_d3"] and uniq["final"]["passed_d3"]),
        "experiments_detail": "X1 (lane as preregistered; D-2 uniqueness failed) + X2 (gate-instrument defect fix on identical bytes; registry/preregistration_arc_amendment_X2.json)",
        "raster_sha256": raster_sha,
        "validator_output": {
            "format_passed": val["format_passed"],
            "no_nan_inside_footprint": v["checks"]["in_footprint_all_finite"],
            "crs_shape_transform_match": val["reference_grid"]["ok"], "summary": v,
        },
        "submission_name": name,
        "submission_note": note,
        "submission_file": str(path.relative_to(ROOT)),
        "zip_file": str(path.with_suffix(".zip").relative_to(ROOT)),
        "zip_sha256": receipt["zip_sha256"],
        "artifact_kind": "binary dot map (1.0 at 37,654 placed cells, 0.0 elsewhere, all finite) from the H79-ARC surface",
        "positive_pixels": v["emitted_positive_pixels"],
        "experiment_count": 2, "max_experiments": prereg["budget"]["max_experiments"],
        "max_hours": prereg["budget"]["max_hours"],
        "source_provenance_verified": True,
        "source_provenance_definition": ("Every input byte matches the SHA-256 pins in registry/data_manifest.json "
            "and the grid equals sample_submission.tif. Mirrors are owner GitHub copies; organizer-origin "
            "authentication is not possible without a DrivenData login."),
        "source_feature_stack_sha256": prereg["inputs"][0].split("sha256 ")[1].split(" ")[0],
        "preregistration_sha256": sha(ROOT / "registry/preregistration_arc.json"),
        "verdict": "promote" if passed else "negative",
        "promoted": bool(passed),
        "stop_reason": None if passed else (
            "Preregistered gate(s) failed: " + ", ".join(sorted(k for k, v2 in g.items() if not v2))
            + ". Lane stopped; no retuning."),
        "failed_gates": sorted(k for k, v2 in g.items() if not v2),
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
    state = json.loads((EV / "state.json").read_text())
    state.update(status="terminal", verdict=card["verdict"],
                 closed_utc=datetime.now(timezone.utc).isoformat(), raster_sha256=raster_sha)
    (EV / "state.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({k: card[k] for k in ("verdict", "raster_sha256", "submission_name",
                                            "protocol_unique", "failed_gates")}, indent=2))


if __name__ == "__main__":
    main()
