"""Current-lane artifact integrity checks; these are not geological score tests."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from validate_submission import validate_path  # noqa: E402
from gems79.status import submission_decision  # noqa: E402


def current_card():
    return json.loads((ROOT / "run_card.json").read_text())


def test_active_run_card_is_negative_and_matches_evidence_copy():
    # Current lane (2026-10-22): G79B, measured and negative.
    card = current_card()
    assert card["lane"] == "G79B-SCARP-DIPOLE-GEOAND"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["holdout_dti"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["current_best_holdout_beaten"] is False
    assert card["submission_slots_used"] == 0
    assert card == json.loads((ROOT / "evidence/run_card.json").read_text())
    assert card == json.loads((ROOT / "docs/run-card.json").read_text())
    # Prior lane E1 remains preserved in its unmeasured stopped state.
    e1 = json.loads((ROOT / "evidence/run_card_g79_e1.json").read_text())
    assert e1["lane"] == "G79-FABRIC-OFFSET" and e1["verdict"] == "negative"
    assert e1["holdout_dti"]["dti"] is None and e1["leakage_canary"]["auc"] is None
    assert e1["final_dot_placements_performed"] == 0


def test_current_research_geotiff_passes_format_but_not_submission_gate():
    card = current_card()
    path = ROOT / card["submission_file"]
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == card["raster_sha256"]
    result = validate_path(path)
    assert result["format_passed"] is True
    assert result["does_not_approve_submission"] is True
    with rasterio.open(path) as tif, rasterio.open(ROOT / "data/reference/sample_submission.tif") as ref:
        assert tif.count == 1 and tif.dtypes == ("float32",)
        assert tif.crs == ref.crs and tif.shape == ref.shape
        assert tif.transform == ref.transform
        assert tif.nodata is None
        checks = card["validator_output"]["shared_validator"]["checks"]
        assert checks["no_nan_anywhere"] is True
        assert checks["min_ge_0"] is True
        assert checks["max_le_1"] is True
    decision = submission_decision(card, actual_sha256=card["raster_sha256"], format_passed=True)
    assert decision["ok_to_download"] is True
    assert decision["ok_to_submit"] is False
    assert decision["human_inspection_required_for_this_decision"] is False


def test_zip_contains_exactly_the_same_single_research_tiff():
    card = current_card()
    tif = ROOT / card["submission_file"]
    zip_path = tif.with_suffix(".zip")
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == [tif.name]
        assert archive.testzip() is None
        assert archive.read(tif.name) == tif.read_bytes()


def test_current_pages_have_matching_negative_verdict_and_no_legacy_download():
    card = current_card()
    assert card["raster_sha256"] in (ROOT / "README.md").read_text()
    for page in (ROOT / "docs/index.html", ROOT / "docs/executive-summary.html"):
        text = page.read_text()
        assert "OK TO DOWNLOAD: YES." in text
        assert "OK TO SUBMIT: NO." in text
        assert "DO NOT SUBMIT" in text
    active_tifs = sorted(p.name for p in (ROOT / "docs/downloads").glob("*.tif"))
    assert active_tifs == [Path(card["submission_file"]).name]
