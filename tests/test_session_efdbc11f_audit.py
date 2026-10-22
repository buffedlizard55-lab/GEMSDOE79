"""End-to-end verification tests for session efdbc11f deliverables and receipts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_session_efdbc11f_receipts_strict_json_and_path_hygiene():
    ev_dir = ROOT / "evidence" / "review_efdbc11f"
    expected = {
        "halo_reconciliation.json",
        "post_delta_sibling_check.json",
        "tracked_raster_scan.json",
        "verification_receipt.json",
    }
    present = {p.name for p in ev_dir.glob("*.json")}
    assert expected <= present
    for p in sorted(ev_dir.glob("*.json")):
        raw = p.read_text(encoding="utf-8")
        assert "/home/user/GEMSDOE79" not in raw, f"Checkout path leaked into {p}"
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)


def test_session_efdbc11f_verification_and_halo_receipts_match_bytes():
    card = json.loads((ROOT / "run_card.json").read_text(encoding="utf-8"))
    vr = json.loads((ROOT / "evidence/review_efdbc11f/verification_receipt.json").read_text(encoding="utf-8"))
    assert vr["canonical_lane"] == "G79-THVC"
    assert vr["canonical_verdict"] == "negative"
    assert vr["ok_to_download"] is True
    assert vr["ok_to_submit"] is False
    assert vr["submission_slots_used"] == 0
    assert vr["canonical_tif_sha256"] == card["raster_sha256"] == _sha256(ROOT / card["submission_file"])
    assert vr["canonical_zip_sha256"] == card["zip_sha256"] == _sha256(ROOT / card["zip_file"])
    assert vr["commands"]["verify_project"]["exit_code"] == 0
    assert vr["commands"]["verify_project"]["all_checks_passed"] is True
    assert vr["commands"]["submission_status"]["exit_code"] == 2
    assert vr["commands"]["select_submission"]["exit_code"] == 2
    assert vr["commands"]["preflight_new_lane"]["exit_code"] == 2
    assert vr["commands"]["validate_submission"]["format_passed"] is True

    halo = json.loads((ROOT / "evidence/review_efdbc11f/halo_reconciliation.json").read_text(encoding="utf-8"))
    r13 = halo["r13_lattice_s5_13GEMSDOE"]
    assert r13["allowed_cells_finite_footprint"] == 5_167_373
    assert r13["catalogue_cells_in_footprint"] == 60_988
    assert r13["allowed_cells_off_catalogue"] == 5_106_385
    assert r13["uncovered_off_catalogue_cells"] == 6_514
    assert r13["pigeonhole_min_overlap_at_37654_dots"] > 0.82


def test_post_delta_sibling_check_and_leaderboard_refresh():
    sib = json.loads((ROOT / "evidence/review_efdbc11f/post_delta_sibling_check.json").read_text(encoding="utf-8"))
    assert sib["repositories_scanned"] == sib["repositories_ok"] == 92
    assert sib["base_frozen_blobs"] == 992
    assert sib["base_delta_blobs"] == 207
    assert sib["new_unique_prediction_blobs_on_default_branches"] == 2
    blobs = {b["blob"]: b for b in sib["verified_new_blobs"]}
    assert set(blobs) == {
        "2016b3dce36d3e25e2630a569434e7d1db08b615",
        "d6adb232c81ab8f609f391f9741edb3432210f45",
    }
    for b in blobs.values():
        assert b["git_blob_sha1_verified"] is True
        assert b["all_format_checks_passed"] is True
        assert b["thvc_forward_overlap_3px_onto_sibling"] < 0.70
        assert b["sibling_forward_overlap_3px_onto_thvc"] < 0.70
        assert b["sibling_forward_overlap_3px_onto_13gemsdoe_lattice"] > 0.99

    sources = json.loads((ROOT / "knowledge/official_sources.json").read_text(encoding="utf-8"))
    health = json.loads((ROOT / "docs/evidence/source_health.json").read_text(encoding="utf-8"))
    dd_lb = next(s for s in sources["sources"] if s["id"] == "DD-LEADERBOARD")
    assert dd_lb["observation"]["public_dti"] == health["leaderboard_observation"]["public_dti"] == 0.4413
    assert dd_lb["observation"]["rank_50_participant"] == health["leaderboard_observation"]["rank_50_participant"] == "sam35"
    assert dd_lb["observation"]["rank_50_public_dti"] == health["leaderboard_observation"]["rank_50_public_dti"] == 0.2804


def test_hypotheses_and_irregularities_efdbc11f_documented():
    hyp = (ROOT / "research/hypotheses_efdbc11f.md").read_text(encoding="utf-8")
    for hid in ("G79-EF1", "G79-EF2", "G79-EF3", "G79-EF4", "G79-EF5"):
        assert hid in hyp
    ir = (ROOT / "reports/irregularities.md").read_text(encoding="utf-8")
    found_ids = set(re.findall(r"\|\s*(IR-79-\d+)\s*\|", ir))
    assert {"IR-79-191", "IR-79-192", "IR-79-193"} <= found_ids
