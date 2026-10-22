#!/usr/bin/env python3
"""Gate-checked packaging + run card for G79-BER X1.

Re-derives every preregistered gate from evidence/ber/ (never from typed-in
numbers), writes the GeoTIFF through the shared submission_writer, validates
the written bytes, and composes run_card_ber.json (protocol rule 5).

Destination policy (keeps the repo's single-canonical-artifact publication
contract valid at every checkpoint):
  * the artifact is always written first to
    archive/g79_ber_4f80e0d0/downloads/;
  * a negative verdict keeps it there with a DO-NOT-SUBMIT name;
  * a promote verdict is only promote-to-selector: canonical publication
    (archiving the H79-NHR artifact byte-for-byte, moving this artifact into
    docs/downloads/, swapping the canonical card, running the separate
    selector) is scripts/publish_ber.py, a distinct reviewed step.

Refuses to run if run_card_ber.json already exists (terminal lane).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator      # noqa: E402
from gems57.grid import load_grid                      # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems79 import ber                                 # noqa: E402
from validate_submission import validate_path          # noqa: E402
import analyze_h33                                     # noqa: E402

EV = ROOT / "evidence" / "ber"
CACHE = ROOT / ".cache" / "ber"
BUDGET = 37654
DEST = ROOT / "archive" / "g79_ber_4f80e0d0" / "downloads"
CARD = ROOT / "run_card_ber.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


def main():
    if CARD.exists():
        raise SystemExit("G79-BER: terminal run card exists; refusing to repackage.")
    prereg = load_json(ROOT / "registry/preregistration_ber.json")
    hold = {s: load_json(EV / f"x1_holdout_seed{s}.json") for s in (20, 30)}
    uniq_s = load_json(EV / "uniqueness_surface.json")
    surf_build = load_json(EV / "x1_final_surface.json")
    placed = (CACHE / "final_dots.npy").exists() and (EV / "uniqueness_final.json").exists()
    uniq_f = load_json(EV / "uniqueness_final.json") if placed else None
    dots = np.load(CACHE / ("final_dots.npy" if placed else "provisional_dots.npy"))
    dots_sha = hashlib.sha256(dots.tobytes()).hexdigest()

    rs, rf = uniq_s["result"], (uniq_f["result"] if uniq_f else None)
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
    g["surface_rank_correlation_le_0_90"] = bool(
        rs["worst_spearman_full_footprint"] is not None and rs["worst_spearman_full_footprint"] <= 0.90)
    g["final_rank_correlation_le_0_90"] = bool(
        rf and rf["worst_spearman_full_footprint"] is not None and rf["worst_spearman_full_footprint"] <= 0.90)
    g["surface_uniqueness_passed"] = bool(rs.get("unique_under_D2") and rs.get("complete_accessible_scan"))
    g["final_dot_uniqueness_passed"] = bool(
        rf and rf.get("unique_under_D2") and rf.get("complete_accessible_scan"))
    audited_sha = (uniq_f["dots_sha256"] if uniq_f else uniq_s["dots_sha256"])
    g["final_dots_match_audited_bytes"] = bool(dots_sha == audited_sha)
    g["exact_budget"] = int(dots.sum()) == BUDGET
    passed = all(g.values())

    grid = load_grid(ROOT / "data/reference")
    dist = ndi.distance_transform_edt(~grid.catalogue)
    allowed = grid.footprint & ~grid.catalogue & (dist > 2)
    if (dots & ~allowed).any():
        raise SystemExit("dots outside the preregistered allowed domain; refusing to write")
    pred = np.zeros(grid.shape, np.float32)
    pred[dots] = 1.0
    if int(pred.sum()) != int(dots.sum()):
        raise SystemExit("dot count changed while building the prediction array")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s20 = hold[20]["holdout"]["scores"]
    s30 = hold[30]["holdout"]["scores"]
    hd = (f"HOLDOUT-DTI {s20['candidate']['dti']:.3f}/{s30['candidate']['dti']:.3f} vs H33 "
          f"{s20['h33_foldfair_control']['dti']:.3f}/{s30['h33_foldfair_control']['dti']:.3f}")
    if passed:
        name = f"gems79-ber-banded-evidence-37654dots-{stamp}-{dots_sha[:8]}-zeros"
        note = f"G79-BER banded nested-hide worms+scarps, 37654 dots s3; {hd}"
        stop_reason = None
    else:
        failed = [k for k, v in g.items() if not v]
        name = f"gems79-ber-banded-research-37654dots-{stamp}-{dots_sha[:8]}-DO-NOT-SUBMIT"
        worst_corr = (rf or rs)["worst_chance_corrected_overlap"]
        short = {"beats_current_holdout_best_both_seeds": "holdout<H33",
                 "surface_uniqueness_passed": "surface-uniqueness",
                 "final_dot_uniqueness_passed": "final-uniqueness",
                 "final_rank_correlation_le_0_90": "no-final-dots",
                 "canaries_all_le_0_90_both_seeds": "canary",
                 "paired_ci_vs_uniform_excludes_zero_both_seeds": "CI-vs-uniform"}
        note = f"G79-BER research only; {hd}; FAILED {','.join(short.get(f, f) for f in failed)}"[:139]
        stop_reason = ("Preregistered gate(s) failed: " + ", ".join(failed) +
                       f". Worst chance-corrected registry overlap {worst_corr}. "
                       "Lane stopped; no retuning, capping or jitter.")
    assert len(name) <= 140 and len(note) <= 140, (name, note)

    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / (name + ".tif")
    receipt = write_submission(path, pred, ROOT / "data/reference/sample_submission.tif",
                               grid.footprint, note=note, name=name, catalogue=grid.catalogue,
                               metadata=dict(lane="G79-BER", experiment="X1", dots_sha256=dots_sha,
                                             dots_source=("placed final dots" if placed
                                                          else "provisional surface top-quota dots (placement stopped)"),
                                             rank_surface_sha256=surf_build["rank_surface_sha256"]))
    # IR-79-63 class: the shared writer receipt embeds the path it was given;
    # normalise it to repo-relative so published evidence is machine-free.
    # (Applied to the X1 receipt on disk; the lane is terminal, see IR-79-129.)
    receipt_path = path.with_suffix(".json")
    receipt_doc = json.loads(receipt_path.read_text())
    def _rel(x):
        if isinstance(x, str):
            return x.replace(str(ROOT) + "/", "")
        if isinstance(x, dict):
            return {k: _rel(v) for k, v in x.items()}
        if isinstance(x, list):
            return [_rel(v) for v in x]
        return x
    receipt_path.write_text(json.dumps(_rel(receipt_doc), indent=2) + "\n")
    val = validate_path(path)
    v = val["validator"]
    raster_sha = sha(path)

    def arm(s, arm_name):
        x = hold[s]["holdout"]["scores"][arm_name]
        return dict(dti=round(x["dti"], 4), ci95=[round(c, 4) for c in x["ci95"]])

    per_seed = {}
    for s in (20, 30):
        sc = hold[s]["holdout"]["scores"]
        pdiff = hold[s]["holdout"]["paired_differences"]
        per_seed[f"seed_{s}"] = dict(
            withheld_positive_pixels=sc["candidate"]["withheld_positive_pixels"],
            candidate=arm(s, "candidate"),
            h33_foldfair_control=arm(s, "h33_foldfair_control"),
            uniform_control=arm(s, "uniform_control"),
            banded_uniform_control=arm(s, "banded_uniform_control"),
            paired_delta_vs_h33=dict(delta=round(pdiff["h33_foldfair_control"]["delta"], 4),
                                     ci95=[round(c, 4) for c in pdiff["h33_foldfair_control"]["ci95"]]),
            paired_delta_vs_uniform=dict(delta=round(pdiff["uniform_control"]["delta"], 4),
                                         ci95=[round(c, 4) for c in pdiff["uniform_control"]["ci95"]]),
            stratified_kernel_credit_by_truth_band=hold[s]["stratified_kernel_credit_by_truth_band"])
    low = min((20, 30), key=lambda s: hold[s]["holdout"]["scores"]["candidate"]["dti"])
    head = hold[low]["holdout"]["scores"]["candidate"]
    canary_max = max(h["leakage_canary"]["max_symmetric_auc"] for h in hold.values())

    def uniq_block(r):
        if r is None:
            return None
        return dict(unique_under_D2=r["unique_under_D2"],
                    complete_accessible_scan=r["complete_accessible_scan"],
                    registry_rasters_checked=r["registry_rasters_checked"],
                    worst_spearman=r["worst_spearman_full_footprint"],
                    worst_spearman_submission=r["worst_spearman_submission"],
                    worst_forward_overlap_dot_equivalent=r["worst_forward_overlap_dot_equivalent"],
                    worst_forward_overlap_submission=r["worst_forward_overlap_submission"],
                    worst_chance_corrected_overlap=r["worst_chance_corrected_overlap"],
                    worst_chance_corrected_submission=r["worst_chance_corrected_submission"],
                    worst_literal_forward_overlap=r["worst_literal_forward_overlap"],
                    worst_literal_submission=r["worst_literal_submission"],
                    literal_overlap_firings=r["literal_overlap_firings"],
                    duplicate_count_d2=r["duplicate_count_d2"],
                    d2_firings=r["d2_firings"][:10])

    # RASTER-MEASUREMENT diagnostics (not scores): distance + road profiles.
    bins = [0, 2, 3, 5, 10, 20, 50, 10 ** 6]
    def profile(mask):
        d = dist[mask]
        hist = np.histogram(d, bins=bins)[0]
        return dict(dots=int(mask.sum()), median_px=float(np.median(d)),
                    fraction_le_5px=float((d <= 5).mean()), fraction_gt_10px=float((d > 10).mean()),
                    histogram={f"({bins[i]},{bins[i+1]}] px" if i else "[0,2] px": int(hist[i])
                               for i in range(len(hist))})
    h33_arr, _ = analyze_h33.locate("gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    h33_dots = (np.isfinite(h33_arr) & (np.nan_to_num(h33_arr) > 0) & grid.footprint)
    distance_diag = dict(evidence_class="RASTER-MEASUREMENT", ber=profile(dots),
                         h33=profile(h33_dots), footprint=profile(grid.footprint & ~grid.catalogue))
    with rasterio.open(ROOT / "data/raw/external/tiger_road_distance_m.tif") as src:
        road = src.read(1).astype(np.float32)
    rv = np.isfinite(road) & (road >= 0)
    distance_diag["road_distance_m"] = dict(
        ber_median=float(np.median(road[dots & rv])) if (dots & rv).any() else None,
        footprint_median=float(np.median(road[grid.footprint & rv])),
        ber_fraction_within_100m=float((road[dots & rv] <= 100).mean()) if (dots & rv).any() else None,
        footprint_fraction_within_100m=float((road[grid.footprint & rv] <= 100).mean()))
    (EV / "distance_diagnostics.json").write_text(json.dumps(distance_diag, indent=2) + "\n")

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
            "nhr_reference_not_a_gate": {
                "evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2",
                "seed_20": 0.1431, "seed_30": 0.1522,
                "source": "run_card.json (H79-NHR X1, duplicate-stopped); reported for context only"},
            "caveat": "Hide-and-recover of withheld catalogue components; not a leaderboard score or projection.",
        },
        "current_best_holdout_beaten": g["beats_current_holdout_best_both_seeds"],
        "current_best_holdout_reference": ("h33_foldfair_control (legacy D2.8 dots >2 px from each fold's "
                                           "visible faults), the fold-fair bar used by H79-NHR/G79-STEPCO; "
                                           "see preregistration for why the duplicate-stopped pooled NHR "
                                           "candidate is a reference, not the bar"),
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY", "passed": g["canaries_all_le_0_90_both_seeds"],
            "auc": round(canary_max, 4), "required_threshold": 0.90,
            "features_cleared": len(hold[20]["leakage_canary"]["per_feature_max"]),
            "tests_per_seed": hold[20]["leakage_canary"]["tests"],
            "tests": sum(h["leakage_canary"]["tests"] for h in hold.values()),
            "worst_feature": max(hold.values(), key=lambda h: h["leakage_canary"]["max_symmetric_auc"])
            ["leakage_canary"]["worst"]["feature"],
        },
        "correlation_overlap_vs_registry": {
            "shared_tool": "gems57.uniqueness.compare_array_to_registry_d2",
            "gate": "amendment D-2 (reports/protocol_amendment_D2_20261022.md); literal reading reported, never claimed passed",
            "registry_rasters_expected": uniq_s["registry_rasters_expected"],
            "surface_before_placement": uniq_block(rs),
            "final_dots": uniq_block(rf),
            "limits": {"rho": 0.90, "forward_overlap_3px": 0.70, "chance_corrected_overlap": 0.70},
        },
        "protocol_unique": bool(g["surface_uniqueness_passed"] and g["final_dot_uniqueness_passed"]),
        "protocol_unique_scope": ("Unique under amendment D-2 only" if g["final_dot_uniqueness_passed"]
                                  else "Not unique under amendment D-2") +
                                 "; literal-support reading always reported in evidence/ber/uniqueness_*.json",
        "byte_distinct_from_registry_pins": bool(
            raster_sha not in {r["sha256"] for r in (rf or rs)["rows"] if "sha256" in r}),
        "raster_sha256": raster_sha,
        "dots_sha256": dots_sha,
        "validator_output": {
            "format_passed": val["format_passed"],
            "no_nan_inside_footprint": v["checks"]["in_footprint_all_finite"],
            "values_in_0_1": bool(v["checks"]["range_0_1_guaranteed"] and v["min"] >= 0.0 and v["max"] <= 1.0),
            "crs_shape_transform_match": val["reference_grid"]["ok"],
            "portal_range_preflight": {
                "min": v["min"], "max": v["max"], "n_nan": v["n_nan"], "n_infinite": v["n_infinite"],
                "nodata": v["meta"]["nodata"],
                "note": ("Written bytes are single-band float32, all finite, values exactly 0/1, no nodata "
                         "sentinel: the local conditions for the portal error 'Predicted values must be in "
                         "range [0, 1]' are absent. This is a local preflight, not organizer acceptance.")},
            "summary": v,
        },
        "submission_name": name,
        "submission_note": note,
        "submission_note_chars": len(note),
        "submission_file": str(path.relative_to(ROOT)),
        "zip_file": str(path.with_suffix(".zip").relative_to(ROOT)),
        "zip_sha256": receipt["zip_sha256"],
        "artifact_kind": ("binary dot map (1.0 at 37,654 placed cells, 0.0 elsewhere, all finite) "
                          "from the G79-BER per-band surfaces" if placed else
                          "binary provisional top-quota dot map serialised once as negative evidence; "
                          "placement was stopped by the surface gate"),
        "positive_pixels": int(dots.sum()),
        "band_quotas": surf_build["quotas"],
        "distance_diagnostics": distance_diag,
        "experiment_count": 1, "max_experiments": 3, "max_hours": 2,
        "source_provenance_verified": True,
        "source_provenance_definition": ("Every input byte matches the SHA-256 pins in "
                                         "registry/data_manifest.json (see evidence/ber/feature_receipt.json) "
                                         "and the grid equals sample_submission.tif. Mirrors are owner GitHub "
                                         "copies; organizer-origin authentication is not possible without a "
                                         "DrivenData login."),
        "source_feature_stack_sha256": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
        "preregistration": "registry/preregistration_ber.json",
        "preregistration_sha256": sha(ROOT / "registry/preregistration_ber.json"),
        "gates": g, "gates_all_passed": passed,
        "verdict": "promote" if passed else "negative",
        "promoted": False,
        "stop_reason": stop_reason,
        "failed_gates": [k for k, val_ in g.items() if not val_],
        "ok_to_download": bool(val["format_passed"]),
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "selector_receipt": None,
        "human_intervention_needed_for_this_verdict": False,
        "submission_slots_used": 0,
        "organizer_submission_receipt": None,
        "organizer_confirmed_score": None,
        "leaderboard_claim": ("No leaderboard score is claimed or projected. HOLDOUT-DTI above is the only "
                              "performance number established for this artifact."),
    }
    (EV / "x1_gates.json").write_text(json.dumps(
        dict(gates=g, all_passed=passed, name=name, note=note, raster_sha256=raster_sha),
        indent=2) + "\n")
    CARD.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(written=str(path.relative_to(ROOT)), sha256=raster_sha,
                          verdict=card["verdict"], failed=card["failed_gates"],
                          note=note, note_chars=len(note)), indent=2))


if __name__ == "__main__":
    main()
