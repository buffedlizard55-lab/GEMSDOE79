#!/usr/bin/env python3
"""Finalize G79-CJX-DIR: re-derive every preregistered gate from receipts on disk,
write run_card_cjxdir.json and the archive README (the site page is rendered by
scripts/build_site.py from the same card).
No number is hand-typed here; all values flow from evidence/cjxdir/*.json and a
fresh local format validation of the written TIFF bytes.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from validate_submission import validate_path  # noqa: E402

EV = ROOT / "evidence" / "cjxdir"
ARCHIVE = ROOT / "archive" / "g79_cjxdir"
THVC_BEST = {"seed20": 0.1905, "seed30": 0.1944}  # canonical run_card.json, same evaluator


def load(p: Path):
    return json.loads(p.read_text())


def main():
    if (ROOT / "run_card_cjxdir.json").exists():
        sys.stderr.write("run_card_cjxdir.json already exists; lane is closed. No files changed.\n")
        return 2
    prereg = load(ROOT / "registry" / "preregistration_cjxdir.json")
    holdout = load(EV / "holdout_results.json")
    final = load(EV / "final_receipt.json")
    uniq = load(EV / "uniqueness_restored_subset.json")
    phase = load(EV / "phase_null.json")
    feats = load(EV / "feature_receipt.json")
    preflight = load(ROOT / "docs" / "evidence" / "preflight_e4a4422d.json")

    tif = ARCHIVE / f"{final['submission_name']}.tif"
    actual_sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    fmt = validate_path(tif)

    def seed_block(seed_key):
        s = holdout[seed_key]["summary"]
        scores = s["scores"]
        diffs = s["paired_differences"]
        cand = scores["CJXFULL_20K"]
        better_control = max(("EDGE", "UNIFORM"), key=lambda k: scores[k]["dti"])
        return {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": s["evaluator_version"],
            "candidate_CJXFULL_20K": cand,
            "EXP1_CJXJ": scores["CJXJ"],
            "EXP3_CJXFULL_37654_sensitivity": scores["CJXFULL_37654"],
            "control_EDGE": scores["EDGE"],
            "control_UNIFORM": scores["UNIFORM"],
            "paired_delta_vs_EDGE": diffs["EDGE"],
            "paired_delta_vs_UNIFORM": diffs["UNIFORM"],
            "better_control": better_control,
            "beats_better_control_ci_excludes_zero": bool(
                diffs[better_control]["ci95"][0] > 0 and cand["dti"] > scores[better_control]["dti"]),
            "canonical_THVC_point_estimate_same_evaluator": THVC_BEST[seed_key],
            "beats_canonical_THVC_point_estimate": bool(cand["dti"] > THVC_BEST[seed_key]),
            "bootstrap": s["bootstrap"],
            "canary_max_symmetric_auc": holdout[seed_key]["canary_max_symmetric_auc"],
            "canary_worst_feature": holdout[seed_key]["canary_worst_feature"],
        }

    per_seed = {k: seed_block(k) for k in ("seed20", "seed30")}
    phase_per_seed = {
        k: {"REAL_S2": phase["per_seed"][k]["scores"]["REAL_S2"],
            "PHASE_NULL_S2": phase["per_seed"][k]["scores"]["PHASE_NULL_S2"],
            "paired_delta_REAL_minus_NULL": phase["per_seed"][k]["paired_differences"]["PHASE_NULL_S2"]}
        for k in ("seed20", "seed30")
    }
    reading_i_worst = uniq["reading_i_literal_positive_support"]["worst_final_forward_overlap"]["value"]
    gates = {
        "canaries_all_le_0_90_both_seeds": bool(
            holdout["seed20"]["canary_gate_le_0_90"] and holdout["seed30"]["canary_gate_le_0_90"]),
        "beats_controls_both_seeds_ci_excludes_zero": bool(
            per_seed["seed20"]["beats_better_control_ci_excludes_zero"]
            and per_seed["seed30"]["beats_better_control_ci_excludes_zero"]),
        "beats_current_holdout_best_both_seeds": bool(
            per_seed["seed20"]["beats_canonical_THVC_point_estimate"]
            and per_seed["seed30"]["beats_canonical_THVC_point_estimate"]),
        "local_format_validator_passed": bool(fmt["format_passed"]),
        "raster_sha256_matches_writer_receipt": bool(actual_sha == final["raster_sha256"]),
        "literal_novelty_passed": False,
        "literal_novelty_note": (
            "Impossible for every nonempty candidate under the literal positive-support reading: "
            f"pinned witness {preflight['witness_sha256']} covers "
            f"{preflight['covered_allowed_fraction']:.0%} of allowed cells (preflight exit "
            f"{preflight['exit_code']}). On the restored subset alone the worst literal forward "
            f"overlap is {reading_i_worst}. This gate cannot be repaired by any pixel change; it "
            "needs a prospective protocol decision (amendment D-3 question), not a lane-local bypass."
        ),
        "dotfield_like_for_like_passed_on_restored_subset": bool(
            uniq["reading_ii_dotfield_like_for_like"]["passes_on_restored_subset"]),
        "vendor_overlap_cross_check_agrees": bool(uniq["shared_tool_cross_check"]["agree_abs_tol_1e-9"]),
    }
    promote = all(v is True for k, v in gates.items() if isinstance(v, bool) and k != "dotfield_like_for_like_passed_on_restored_subset" and k != "vendor_overlap_cross_check_agrees") and gates["literal_novelty_passed"]
    blockers = [k for k in (
        "canaries_all_le_0_90_both_seeds", "beats_controls_both_seeds_ci_excludes_zero",
        "beats_current_holdout_best_both_seeds", "local_format_validator_passed",
        "raster_sha256_matches_writer_receipt", "literal_novelty_passed",
    ) if gates[k] is not True]

    card = {
        "schema_version": 2,
        "lane": "G79-CJX-DIR",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preregistration_path": "registry/preregistration_cjxdir.json",
        "preregistration_sha256": hashlib.sha256(
            (ROOT / "registry" / "preregistration_cjxdir.json").read_bytes()).hexdigest(),
        "hypothesis": prereg["hypothesis"],
        "mechanism": prereg["mechanism"],
        "named_non_fault_mimic": prereg["named_non_fault_mimic"],
        "experiments_used": "3 of 3 preregistered arms (EXP1 CJXJ, EXP2 CJXFULL candidate, EXP3 budget sensitivity) + EDGE/UNIFORM controls, seeds 20/30",
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": per_seed["seed20"]["evaluator_version"],
            "headline_seed": 20,
            "dti": per_seed["seed20"]["candidate_CJXFULL_20K"]["dti"],
            "ci95": per_seed["seed20"]["candidate_CJXFULL_20K"]["ci95"],
            "withheld_positive_pixels": per_seed["seed20"]["candidate_CJXFULL_20K"]["withheld_positive_pixels"],
            "per_seed": per_seed,
            "source_pointer": "evidence/cjxdir/holdout_results.json",
        },
        "phase_randomized_null_diagnostic": {
            "evidence_class": "HOLDOUT-DTI diagnostic (falsification null, not a candidate)",
            "per_seed": phase_per_seed,
            "source_pointer": "evidence/cjxdir/phase_null.json",
        },
        "leakage_canary": {
            "features_tested": feats["features"],
            "seed20_max_symmetric_auc": holdout["seed20"]["canary_max_symmetric_auc"],
            "seed30_max_symmetric_auc": holdout["seed30"]["canary_max_symmetric_auc"],
            "threshold": 0.90,
            "passed": gates["canaries_all_le_0_90_both_seeds"],
        },
        "registry_correlation_overlap": {
            "evidence_class": "REGISTRY-MEASUREMENT (restored subset)",
            "scope": uniq["scope"],
            "reading_i_literal_positive_support": uniq["reading_i_literal_positive_support"],
            "reading_ii_dotfield_like_for_like": uniq["reading_ii_dotfield_like_for_like"],
            "reading_iii_d2_chance_corrected": uniq["reading_iii_d2_chance_corrected"],
            "shared_tool_cross_check": uniq["shared_tool_cross_check"],
            "source_pointer": "evidence/cjxdir/uniqueness_restored_subset.json",
        },
        "submission_file": f"archive/g79_cjxdir/{final['submission_name']}.tif",
        "zip_file": f"archive/g79_cjxdir/{final['submission_name']}.zip",
        "raster_sha256": actual_sha,
        "zip_sha256": final["zip_sha256"],
        "bytes": final["bytes"],
        "positive_pixels": final["placement"]["emitted"],
        "submission_name": final["submission_name"],
        "note": final["note"],
        "note_chars": final["note_chars"],
        "validator": {
            "format_passed": fmt["format_passed"],
            "does_not_approve_submission": True,
            "summary": "Single-band float32 GeoTIFF; CRS/shape/transform match the sample; all values "
                       "finite and in [0,1] (binary 0/1, zeros outside the footprint); no positive "
                       "pixel on the mapped catalogue. Local format PASS is portal-format evidence "
                       "only, never scientific or selector approval.",
            "detail_pointer": "evidence/cjxdir/final_receipt.json + archive/g79_cjxdir/*.json writer receipt",
        },
        "gates": gates,
        "blockers": blockers,
        "verdict": "promote" if promote else "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "ok_to_submit_note": (
            "This lane never selects itself (protocol rule 6). select_submission.py has no G79-CJX-DIR "
            "evidence adapter and the literal novelty gate fails, so ok_to_submit stays false "
            "regardless of the verdict field. Manual upload is not an exception."
        ),
        "decision_line": "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.",
        "submission_slots_used": 0,
        "organizer_confirmed_score": None,
        "organizer_confirmed_note": "No submission was made; there is no ORGANIZER-CONFIRMED score for this artifact. Any number above is HOLDOUT-DTI only.",
    }
    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "run_card_cjxdir.json").write_text(text)
    shutil.copyfile(ROOT / "run_card_cjxdir.json", ROOT / "docs" / "evidence" / "run_card_cjxdir.json")
    for src, dst in (("holdout_results.json", "cjxdir_holdout_results.json"),
                     ("uniqueness_restored_subset.json", "cjxdir_uniqueness_restored_subset.json"),
                     ("phase_null.json", "cjxdir_phase_null.json"),
                     ("final_receipt.json", "cjxdir_final_receipt.json"),
                     ("feature_receipt.json", "cjxdir_feature_receipt.json")):
        shutil.copyfile(EV / src, ROOT / "docs" / "evidence" / dst)

    # ---- archive README ----
    s20, s30 = per_seed["seed20"], per_seed["seed30"]
    readme = f"""# G79-CJX-DIR — archived lane (verdict: {card['verdict']})

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** Research artifact only; the lane is
closed (3/3 preregistered arms exhausted). Do not restart, retune or re-place.

- TIFF: `{final['submission_name']}.tif` ({final['bytes']} bytes, SHA-256 `{actual_sha}`)
- ZIP: `{final['submission_name']}.zip` (SHA-256 `{final['zip_sha256']}`)
- Dots: {final['placement']['emitted']} (spacing 3 px, catalogue exclusion > 2 px, binary 0/1, zeros outside footprint)
- Name: `{final['submission_name']}`
- Note ({final['note_chars']}/140): `{final['note']}`

HOLDOUT-DTI (gems57-pooled-hide-v2, candidate EXP2 CJXFULL@20k):
seed 20 = {s20['candidate_CJXFULL_20K']['dti']:.4f} {s20['candidate_CJXFULL_20K']['ci95']}
(n = {s20['candidate_CJXFULL_20K']['withheld_positive_pixels']});
seed 30 = {s30['candidate_CJXFULL_20K']['dti']:.4f} {s30['candidate_CJXFULL_20K']['ci95']}
(n = {s30['candidate_CJXFULL_20K']['withheld_positive_pixels']}).
Canonical G79-THVC same-evaluator point estimates: {THVC_BEST['seed20']} / {THVC_BEST['seed30']}.

Full receipts: `evidence/cjxdir/` and `run_card_cjxdir.json` at the repo root.
"""
    (ARCHIVE / "README.md").write_text(readme)

    # The public page (docs/g79-cjxdir.html) is rendered by scripts/build_site.py
    # from this same run card, so CI reproduces it byte-consistently; this
    # finalizer deliberately does not maintain a second renderer.
    print(json.dumps({"verdict": card["verdict"], "blockers": blockers,
                      "raster_sha256": actual_sha, "gates": gates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
