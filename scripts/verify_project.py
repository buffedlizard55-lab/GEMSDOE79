#!/usr/bin/env python3
"""Offline end-to-end integrity, format, ZIP, scientific evidence, uniqueness, and fail-closed status verification."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems79.status import submission_decision
from validate_submission import validate_path


def sha(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify() -> dict:
    checks: dict[str, bool] = {}

    # 1. Shared vendor/gems57 byte pins & preregistration seals
    pin = json.loads((ROOT / "registry/template_pin.json").read_text())
    checks["all_shared_template_bytes_unmodified"] = all(
        sha(ROOT / r["path"]) == r["sha256"] for r in pin["files"]
    )
    expected_prereg_e1 = (ROOT / "evidence/preregistration_sha256.txt").read_text().strip()
    expected_prereg_thvc = (ROOT / "evidence/preregistration_g79_thvc_sha256.txt").read_text().strip()
    checks["preregistrations_preserved"] = (
        sha(ROOT / "registry/preregistration.json") == expected_prereg_e1
        and sha(ROOT / "registry/preregistration_g79_thvc.json") == expected_prereg_thvc
    )

    # 2. Reference competition inputs
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    checks["reference_input_hashes_match_pins"] = all(
        sha(ROOT / "data/reference" / row["dest"]) == row["sha256"]
        for row in manifest["files"]
        if row["id"] in ("existing_faults", "sample_submission")
    )

    # 3. Run card, GeoTIFF, receipt, world-readable Pages permissions, and single-TIFF ZIP
    card = json.loads((ROOT / "run_card.json").read_text())
    checks["card_copies_equal"] = card == json.loads((ROOT / "evidence/run_card.json").read_text())
    path = ROOT / card["submission_file"]
    actual_sha = sha(path)
    receipt_path = path.with_suffix(".json")
    zip_path = path.with_suffix(".zip")
    receipt = json.loads(receipt_path.read_text())
    checks["raster_hash_card_receipt_agree"] = (
        actual_sha == card["raster_sha256"] == receipt["sha256"]
    )
    checks["world_readable_download_permissions"] = all(
        (p.stat().st_mode & 0o444) == 0o444 for p in (path, receipt_path, zip_path)
    )
    checks["name_and_note_valid"] = (
        0 < len(card["submission_name"]) <= 140
        and 0 < len(card["submission_note"]) <= 140
        and card["submission_name"] == receipt["submission_name"]
        and card["submission_note"] == receipt["note"]
        and path.stem == card["submission_name"]
    )

    result = validate_path(path)
    checks["reopened_tiff_format_all_passed"] = bool(result["format_passed"])
    checks["format_receipt_positive_count_agrees"] = (
        result["validator"]["emitted_positive_pixels"] == card["positive_pixels"]
        and card["positive_pixels"] > 0
    )

    with zipfile.ZipFile(zip_path) as z:
        checks["zip_exactly_one_identical_tiff"] = (
            z.namelist() == [path.name] and z.read(path.name) == path.read_bytes()
        )
        checks["zip_crc_valid"] = z.testzip() is None
    checks["zip_hash_matches_receipt"] = sha(zip_path) == receipt["zip_sha256"]

    # 4. Registry non-duplication, 84-channel leakage canaries, dual-seed HOLDOUT-DTI, & 1,108-raster audit
    registry = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    surf_u = json.loads((ROOT / "evidence/g79_surface_uniqueness_1108.json").read_text())
    dot_u = json.loads((ROOT / "evidence/g79_dot_uniqueness_1108.json").read_text())
    canary = json.loads((ROOT / "evidence/g79_leakage_canary.json").read_text())
    thvc_res = json.loads((ROOT / "evidence/g79_thvc_results.json").read_text())

    checks["new_bytes_not_copied_from_registry"] = (
        actual_sha not in {r.get("sha256") for r in registry["files"]}
        and actual_sha not in {r.get("sha256") for r in dot_u["rows"]}
    )
    checks["single_feature_leakage_canaries_passed"] = (
        canary["seed20"]["all_passed"]
        and canary["seed30"]["all_passed"]
        and canary["seed20"]["features_tested"] == 84
        and canary["seed20"]["max_symmetric_auc"] <= 0.90
        and canary["seed30"]["max_symmetric_auc"] <= 0.90
    )
    h20 = card["holdout_dti"]
    h30 = card["secondary_holdout_dti"]
    checks["dual_seed_holdout_dti_beats_h33"] = (
        h20["evidence_class"] == "HOLDOUT-DTI"
        and h20["evaluator_version"] == "gems57-pooled-hide-v2"
        and h20["withheld_positive_pixels"] == 11321
        and h20["dti"] > h20["matched_h33_analogue_dti"]
        and h20["prob_beats_h33"] >= 0.99
        and h30["evidence_class"] == "HOLDOUT-DTI"
        and h30["evaluator_version"] == "gems57-pooled-hide-v2"
        and h30["withheld_positive_pixels"] == 11342
        and h30["dti"] > h30["matched_h33_analogue_dti"]
        and h30["prob_beats_h33"] >= 0.99
        and abs(h20["dti"] - thvc_res["seed20"]["official_evaluate_all"]["scores"]["EXP-79-3_thvc_charnes_cooper"]["dti"]) < 1e-9
    )

    sparse_le50k = [
        r for r in dot_u["rows"] if "error" not in r and int(r.get("their_dots", 0)) <= 50_000
    ]
    certificate = json.loads((ROOT / "evidence/universal_overlap_certificate.json").read_text())
    checks["complete_1108_uniqueness_and_blanket_certificate_consistent"] = (
        surf_u["registry_rasters_expected"] == 1108
        and dot_u["registry_rasters_expected"] == 1108
        and dot_u["registry_rasters_checked"] == 1088
        and surf_u["max_abs_spearman"] <= 0.90
        and dot_u["max_abs_spearman"] <= 0.90
        and len(sparse_le50k) == 718
        and max(float(r["my_dots_within_3px_of_theirs"]) for r in sparse_le50k) <= 0.70
        and certificate["universal_overlap_blocker"]
        and certificate["covered_allowed_fraction"] == 1.0
    )

    # 5. Experiment budget, archived E1 provenance, and fail-closed live submission gate
    state = json.loads((ROOT / "evidence/experiment_state.json").read_text())
    archived_e1 = json.loads(
        (ROOT / "archive/g79_fabric_offset_f61b17a2/run_card_f61b17a2.json").read_text()
    )
    checks["budget_and_archive_honored"] = (
        1 <= state["experiment_count"] <= 3
        and state["stopped"]
        and archived_e1["holdout_dti"]["dti"] is None
    )
    decision = submission_decision(
        card, actual_sha256=actual_sha, format_passed=result["format_passed"]
    )
    checks["automatic_fail_closed_status"] = (
        decision["ok_to_download"] is True
        and decision["ok_to_submit"] is False
        and card["ok_to_submit"] is False
        and card["verdict"] == "negative"
        and card["protocol_unique"] is False
        and card["sparse_comparable_unique"] is True
        and card["submission_slots_used"] == 0
        and card["organizer_submission_receipt"] is None
    )

    report = {
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "all_checks_passed": all(checks.values()),
        "checks": checks,
        "raster_sha256": actual_sha,
        "format_report": result,
        "submission_decision": decision,
        "scope": "Offline byte, format, leakage-canary, dual-seed HOLDOUT-DTI receipt, 1,108-raster uniqueness, and fail-closed status verification. Never uploads or claims organizer acceptance.",
    }
    (ROOT / "evidence/verification.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    return report


if __name__ == "__main__":
    result = verify()
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "all_checks_passed",
                    "checks",
                    "raster_sha256",
                    "submission_decision",
                )
            },
            indent=2,
        )
    )
    raise SystemExit(0 if result["all_checks_passed"] else 1)
