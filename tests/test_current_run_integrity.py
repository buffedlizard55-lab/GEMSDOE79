"""Current canonical-lane (G79-THVC) and archived H79-DILSTEP integrity checks.

These tests re-read the published GeoTIFF and evidence files; they do not
re-run any experiment and they are not geological score tests.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from validate_submission import validate_path  # noqa: E402
from gems79.status import submission_decision  # noqa: E402
from verify_project import decision_line  # noqa: E402

THVC_BUDGET = 35093
DILSTEP_BUDGET = 37654


def current_card():
    return json.loads((ROOT / "run_card.json").read_text())


def test_card_copies_agree_and_carry_protocol_fields():
    card = current_card()
    assert card == json.loads((ROOT / "evidence/run_card.json").read_text())
    assert card == json.loads((ROOT / "docs/run-card.json").read_text())
    assert card == json.loads((ROOT / "docs/evidence/run_card.json").read_text())
    for key in ("hypothesis", "mechanism", "named_non_fault_process", "holdout_dti",
                "correlation_overlap_vs_registry", "raster_sha256", "validator_output",
                "submission_name", "submission_note", "verdict", "leakage_canary"):
        assert key in card, key
    assert card["lane"] == "G79-THVC"
    assert card["verdict"] in ("promote", "negative")
    assert card["experiment_count"] <= card["max_experiments"] == 3
    assert card["submission_slots_used"] == 0 and card["organizer_submission_receipt"] is None


def test_holdout_numbers_are_copied_from_evaluator_output():
    card = current_card()
    h = card["holdout_dti"]
    assert h["evidence_class"] == "HOLDOUT-DTI" and h["evaluator_version"] == "gems57-pooled-hide-v2"
    res = json.loads((ROOT / "evidence/g79_thvc_results.json").read_text())
    cand20 = res["seed20"]["official_evaluate_all"]["scores"]["EXP-79-3_thvc_charnes_cooper"]
    cand30 = res["seed30"]["official_evaluate_all"]["scores"]["EXP-79-3_thvc_charnes_cooper"]
    assert h["dti"] == round(cand20["dti"], 4) == 0.1905
    assert h["ci95"] == [round(c, 4) for c in cand20["ci95"]]
    assert h["withheld_positive_pixels"] == cand20["withheld_positive_pixels"] == 11321
    assert round(cand30["dti"], 4) == 0.1944
    canary = json.loads((ROOT / "evidence/g79_leakage_canary.json").read_text())
    assert canary["seed20"]["max_symmetric_auc"] <= 0.90
    assert canary["seed30"]["max_symmetric_auc"] <= 0.90

    # Also verify archived H79-DILSTEP holdout numbers remain byte-consistent
    dcard = json.loads((ROOT / "archive/h79_dilstep_6444be2d/run_card_dilstep.json").read_text())
    dh = dcard["holdout_dti"]
    for seed in (20, 30):
        ev = json.loads((ROOT / f"evidence/dilstep/holdout_seed{seed}.json").read_text())
        sc = ev["holdout"]["scores"]
        row = dh["per_seed"][f"seed_{seed}"]
        assert row["candidate"]["dti"] == round(sc["candidate"]["dti"], 4)
        assert row["candidate"]["ci95"] == [round(c, 4) for c in sc["candidate"]["ci95"]]
        assert row["withheld_positive_pixels"] == sc["candidate"]["withheld_positive_pixels"]
        assert row["h33_foldfair_control"]["dti"] == round(sc["h33_foldfair_control"]["dti"], 4)
        assert ev["leakage_canary"]["max_symmetric_auc"] <= 0.90


def test_geotiff_is_a_valid_binary_dot_map_on_the_sample_grid():
    card = current_card()
    path = ROOT / card["submission_file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == card["raster_sha256"]
    result = validate_path(path)
    assert result["format_passed"] is True
    with rasterio.open(path) as tif, rasterio.open(ROOT / "data/reference/sample_submission.tif") as ref:
        assert tif.count == 1 and tif.dtypes == ("float32",)
        assert tif.crs == ref.crs and tif.shape == ref.shape == (3730, 3292)
        assert tif.transform == ref.transform
        a = tif.read(1)
    assert np.isfinite(a).all()
    assert set(np.unique(a).tolist()) <= {0.0, 1.0}
    assert int((a == 1).sum()) == THVC_BUDGET == card["positive_pixels"]

    # Also verify archived H79-DILSTEP GeoTIFF remains intact
    dcard = json.loads((ROOT / "archive/h79_dilstep_6444be2d/run_card_dilstep.json").read_text())
    dpath = ROOT / dcard["submission_file"]
    assert hashlib.sha256(dpath.read_bytes()).hexdigest() == dcard["raster_sha256"]
    with rasterio.open(dpath) as dtif:
        da = dtif.read(1)
    assert int((da == 1).sum()) == DILSTEP_BUDGET == dcard["positive_pixels"]


def test_zip_contains_exactly_the_same_single_tiff():
    card = current_card()
    tif = ROOT / card["submission_file"]
    zip_path = ROOT / card["zip_file"]
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == [tif.name]
        assert archive.testzip() is None
        assert archive.read(tif.name) == tif.read_bytes()


def test_name_and_note_are_unique_and_short():
    card = current_card()
    assert len(card["submission_note"]) <= 140 and len(card["submission_name"]) <= 140
    assert Path(card["submission_file"]).stem == card["submission_name"]
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    names = {Path(a).stem for r in index["rasters"] for a in r.get("aliases", [r.get("path", "")])}
    assert card["submission_name"] not in names
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    assert card["raster_sha256"] not in {r.get("sha256") for r in receipt["files"]}


def test_status_tool_card_and_pages_tell_the_same_story():
    card = current_card()
    decision = submission_decision(card, actual_sha256=card["raster_sha256"], format_passed=True)
    assert decision["ok_to_submit"] is card["ok_to_submit"]
    assert decision["verdict"] == card["verdict"]
    assert decision["human_inspection_required_for_this_decision"] is False
    line = decision_line(card)
    assert line in (ROOT / "README.md").read_text().split("## Original project prompt")[0]
    for page in ("docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / page).read_text()
        assert line in text and card["raster_sha256"] in text
    active = sorted(p.name for p in (ROOT / "docs/downloads").glob("*.tif"))
    assert active == [Path(card["submission_file"]).name]


def test_selector_receipt_is_bound_to_the_exact_bytes_when_promoted():
    card = current_card()
    if card["ok_to_submit"]:
        receipt = card["selector_receipt"]
        assert receipt["selector"] == "scripts/select_submission.py"
        assert receipt["raster_sha256"] == card["raster_sha256"]
        tampered = dict(card, raster_sha256="0" * 64)
        assert not submission_decision(tampered, actual_sha256=card["raster_sha256"], format_passed=True)["ok_to_submit"]


def test_current_review_and_h33_evidence_classes_are_published_honestly():
    readme = (ROOT / "README.md").read_text()
    current_readme = readme.split("## Original project prompt", 1)[0]
    why_h33 = (ROOT / "knowledge/why_h33.md").read_text()
    review = (ROOT / "reports/repository_review_2026-10-22_bab8f374.md").read_text()
    slate = (ROOT / "research/hypotheses_bab8f374.md").read_text()
    preflight = json.loads((ROOT / "evidence/preflight_bab8f374.json").read_text())
    home = (ROOT / "docs/index.html").read_text()
    analysis = (ROOT / "docs/analysis.html").read_text()
    research = (ROOT / "docs/research.html").read_text()

    assert "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO." in current_readme
    assert "No new model, holdout run, candidate TIFF" in current_readme
    assert "D2.8 `0.2600`" in current_readme and "0.2768" not in current_readme
    assert "UNVERIFIED HISTORICAL REPORTS" in why_h33
    assert "do **not** establish a competition leaderboard score" in why_h33
    assert "0.2768" not in why_h33 and "Yes, decisively" not in why_h33
    assert "documentation error" in review and "D2.8 `0.2600`" in review
    assert "no new candidate" in review.lower()
    assert "No DTI delta is estimated" in slate and "not a claim that they are new" in slate
    assert preflight["start_new_lane"] is False and preflight["exit_code"] == 2
    assert "Not submission-approved." in home and "no new candidate or holdout run" in home.lower()
    assert "Do not read archived causal explanations as confirmed score mechanisms." in analysis
    assert "CURRENT REVIEW / FOUR UNEXECUTED CONCEPTS" in research
    assert json.loads((ROOT / "docs/evidence/preflight_bab8f374.json").read_text()) == preflight

    review_card = json.loads(review.split("```json\n", 1)[1].split("\n```", 1)[0])
    canonical = current_card()
    assert review_card["raster_sha256"] == canonical["raster_sha256"]
    assert review_card["raster_role"].startswith("pre-existing canonical G79-THVC")
    assert review_card["holdout_dti"]["measured_in_this_review"] is False
    assert review_card["holdout_dti"]["existing_canonical_card"]["seed_20"]["dti"] == 0.1905
    assert review_card["holdout_dti"]["existing_canonical_card"]["seed_30"]["dti"] == 0.1944
    assert review_card["submission_name"] == canonical["submission_name"]
    assert review_card["submission_note"] == canonical["submission_note"]
    assert review_card["ok_to_download"] is True and review_card["ok_to_submit"] is False
    assert review_card["new_candidate_tiff_generated"] is False
    assert review_card["weekly_slots_used_in_this_review"] == 0
