"""Current H79-STEP and archived-lane artifact integrity checks."""
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


def current_card():
    return json.loads((ROOT / "run_card.json").read_text())


def test_card_copies_agree_and_carry_protocol_fields():
    card = current_card()
    assert card == json.loads((ROOT / "evidence/run_card.json").read_text())
    assert card == json.loads((ROOT / "docs/run-card.json").read_text())
    for key in ("hypothesis", "mechanism", "named_non_fault_process", "holdout_dti",
                "correlation_overlap_vs_registry", "raster_sha256", "validator_output",
                "submission_name", "submission_note", "verdict", "leakage_canary"):
        assert key in card, key
    assert card["lane"] == "H79-STEP"
    assert card["verdict"] == "negative" and card["promoted"] is False
    assert card["protocol_unique"] is False
    assert card["correlation_overlap_vs_registry"]["gate_executed"] is False
    assert card["experiment_count"] <= card["max_experiments"] == 3
    assert card["submission_slots_used"] == 0 and card["organizer_submission_receipt"] is None


def test_holdout_numbers_are_copied_from_evaluator_output():
    card = current_card()
    h = card["holdout_dti"]
    assert h["evidence_class"] == "HOLDOUT-DTI" and h["evaluator_version"] == "gems57-pooled-hide-v2"
    prior = json.loads((ROOT / "evidence/g79_thvc_results.json").read_text())
    canary_max = 0.0
    for seed in (20, 30):
        evidence = json.loads((ROOT / f"evidence/holdout_edge_seed{seed}.json").read_text())
        row = h["per_seed"][f"seed_{seed}"]
        for arm in ("candidate", "uniform_control"):
            for key in ("evidence_class", "evaluator_version", "dti", "ci95", "withheld_positive_pixels"):
                assert row[arm][key] == evidence["scores"][arm][key]
        paired = evidence["paired_differences"]["uniform_control"]
        for key in ("evidence_class", "evaluator_version", "delta", "ci95", "withheld_positive_pixels"):
            assert row["paired_delta_vs_uniform"][key] == paired[key]
        h33 = prior[f"seed{seed}"]["official_evaluate_all"]["scores"]["C2_h33_analogue_foldfair"]["dti"]
        assert h[f"h33_foldfair_control_seed_{seed}"] == round(h33, 4)
        canaries = json.loads((ROOT / f"evidence/canaries_edge_seed{seed}.json").read_text())
        assert canaries["passed"] is True and canaries["threshold"] == 0.90
        canary_max = max(canary_max, *(r["symmetric_auc"] for r in canaries["rows"]))
    headline = h["per_seed"]["seed_20"]["candidate"]
    assert (h["dti"], h["ci95"], h["withheld_positive_pixels"]) == (
        headline["dti"], headline["ci95"], headline["withheld_positive_pixels"])
    assert card["leakage_canary"]["passed"] is True
    assert card["leakage_canary"]["auc"] == canary_max <= 0.90
    assert card["current_best_holdout_beaten"] is False
    assert h["per_seed"]["seed_20"]["candidate"]["dti"] < h["h33_foldfair_control_seed_20"]


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
    assert int((a == 1).sum()) == 37654 == card["positive_pixels"]


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
        assert not submission_decision(tampered, actual_sha256="0" * 64, format_passed=True)["ok_to_submit"]


def test_superseded_g79_thvc_artifact_is_preserved_outside_active_downloads():
    archive = ROOT / "archive/g79_thvc_20261021"
    card = json.loads((archive / "run_card.json").read_text())
    assert card["lane"] == "G79-THVC" and card["verdict"] == "negative"
    tif = archive / "downloads" / Path(card["submission_file"]).name
    receipt = json.loads(tif.with_suffix(".json").read_text())
    zip_path = tif.with_suffix(".zip")
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"] == receipt["sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["zip_sha256"] == receipt["zip_sha256"]
    with zipfile.ZipFile(zip_path) as z:
        assert z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes()
    manifest = json.loads((archive / "manifest.json").read_text())
    for row in manifest["files"]:
        assert hashlib.sha256((ROOT / row["archive_path"]).read_bytes()).hexdigest() == row["sha256"]


def test_archived_e1_card_remains_the_stopped_negative_lane():
    e1 = json.loads((ROOT / "archive/g79_fabric_offset_e1/run_card.json").read_text())
    assert e1["lane"] == "G79-FABRIC-OFFSET"
    assert e1["verdict"] == "negative" and e1["ok_to_submit"] is False
    assert e1["holdout_dti"]["dti"] is None and e1["leakage_canary"]["auc"] is None
    tif = ROOT / "archive/g79_fabric_offset_e1/downloads" / Path(e1["submission_file"]).name
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == e1["raster_sha256"]


def test_archived_stepco_s1_bytes_preserved():
    st = json.loads((ROOT / "run_card_stepco.json").read_text())
    assert st["lane"] == "G79-STEPCO" and st["verdict"] == "negative" and st["ok_to_submit"] is False
    tif = ROOT / "archive/g79_stepco_s1/downloads" / Path(st["submission_file"]).name
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == st["raster_sha256"]
