from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_etp_artifacts_are_archived_and_not_published_as_current_downloads():
    card = json.loads((ROOT / "run_card_etp.json").read_text())
    assert card == json.loads((ROOT / "docs/evidence/run_card_etp.json").read_text())
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is False
    assert card["ok_to_submit"] is False
    assert card["protocol_unique"] is False
    assert card["correlation_overlap_vs_registry"]["complete_registry_scan"] is False
    assert card["correlation_overlap_vs_registry"]["dots_all_1088_literal_unchanged_uniqueness_py"][
        "literal_overlap_vs_17GEMSDOE_blanket"
    ] == 1.0
    assert card["custom_proxy_report"]["evidence_class"] == "CUSTOM_PROXY_NOT_COMPARABLE"
    assert card["secondary_custom_proxy_report"]["evidence_class"] == "CUSTOM_PROXY_NOT_COMPARABLE"
    assert "holdout_dti" not in card
    audit = json.loads((ROOT / "evidence/etp_post_merge_audit_6515acc4.json").read_text())
    estimate = audit["historical_etp_disposition"]["elastic_tip_estimate"]
    assert estimate["evidence_class"] == "PROJECTION_NOT_RESULT"
    assert estimate["shared_holdout_run"] is False
    assert estimate["withheld_positive_count"] is None and estimate["ci95"] is None
    assert "projection only" in (ROOT / "archive/g79_etp_v2/README.md").read_text()

    tif = ROOT / card["submission_file"]
    zip_path = ROOT / card["zip_file"]
    assert tif.is_file() and _sha(tif) == card["raster_sha256"]
    assert zip_path.is_file() and _sha(zip_path) == card["zip_sha256"]
    assert card["original_generation_path"].startswith("docs/downloads/")

    relocation = json.loads((ROOT / "archive/g79_etp_v2/relocation_receipt.json").read_text())
    assert relocation["byte_preserving_moves"] is True
    assert len(relocation["files"]) == 6
    for item in relocation["files"]:
        archived = ROOT / item["to"]
        assert archived.is_file() and _sha(archived) == item["sha256"]
    active_files = sorted(p.name for p in (ROOT / "docs/downloads").iterdir() if p.is_file())
    canonical = "g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT"
    assert active_files == [f"{canonical}.{suffix}" for suffix in ("json", "tif", "zip")]


def test_archived_etp_generators_fail_closed_without_writing_files():
    active_dir = ROOT / "docs/downloads"
    before = {p.name: _sha(p) for p in active_dir.iterdir() if p.is_file()}
    for script in ("scripts/generate_etp_submission.py", "scripts/generate_etp_v2.py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 2, (script, result.stdout, result.stderr)
        assert "REFUSED" in result.stderr
        assert "no files changed" in result.stderr
    after = {p.name: _sha(p) for p in active_dir.iterdir() if p.is_file()}
    assert after == before


def test_source_audit_does_not_overstate_freshness_or_data_availability():
    audit = json.loads((ROOT / "evidence/official_source_audit_6515acc4.json").read_text())
    assert "No official website was freshly fetched" in audit["method"]
    aria = next(x for x in audit["claims"] if "NASA/JPL ARIA" in x["claim"])
    assert aria["status"].startswith("UNVERIFIED")
    assert "not treated as available or viable" in aria["status"]
    mt = next(x for x in audit["claims"] if "GDR 1391" in x["claim"])
    assert "not viable now" in mt["availability_check"]
    memo = (ROOT / "research/hypotheses_6515acc4.md").read_text()
    assert "No numeric DTI lift is forecast" in memo
    assert "not freshly fetched this session" in memo


def test_session_run_card_is_explicitly_preflight_blocked_not_a_score():
    card = json.loads((ROOT / "evidence/run_card_6515acc4.json").read_text())
    assert card["decision_class"] == "PREFLIGHT_BLOCKED_NO_EXPERIMENT"
    assert card["holdout_dti"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["status"].startswith("NOT RUN")
    assert card["holdout_dti"]["result"] is None
    assert card["leakage_canary"]["status"].startswith("NOT RUN")
    assert card["leakage_canary"]["auc_warning_threshold"] == 0.90
    assert card["raster_sha256"] is None
    assert card["new_candidate_submission_name"] is None
    assert card["new_candidate_submission_note"] is None
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is False
    assert card["ok_to_submit"] is False
    assert card["submission_note_character_limit"] == 140
    assert card["submission_slots_used"] == 0
    decision = card["automated_submission_decision"]
    assert decision["message"] == "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO."
    assert decision["ok_to_download"] is True and decision["ok_to_submit"] is False
    assert decision["verdict"] == "negative" and decision["exit_code"] == 2
    assert "literal_novelty_not_cleared" in decision["blockers"]
    witness = card["registry_correlation_overlap"]["preflight_witness"]
    receipt = json.loads((ROOT / card["registry_correlation_overlap"]["preflight_receipt"]).read_text())
    assert witness["state"] == receipt["state"] == "impossible_under_literal_gate"
    assert witness["registry_witness_sha256"] == receipt["witness_sha256"]
    assert witness["registry_witness_sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert witness["forced_overlap_3px"] == 1.0 and witness["limit"] == 0.70
    assert card == json.loads((ROOT / "docs/evidence/run_card_6515acc4.json").read_text())
