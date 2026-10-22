import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from affine import Affine
from gems57 import uniqueness
from gems57.submission_writer import write_submission
from verify_project import verify

ROOT = Path(__file__).resolve().parents[1]


def test_dense_witness_is_not_exempted(tmp_path):
    path = tmp_path / "dense.tif"
    fp = np.ones((12, 12), bool)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=12,
        height=12,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100, 0, 1000, 0, -100, 2000),
    ) as dst:
        dst.write(np.full((12, 12), 0.1, np.float32), 1)
    cert = uniqueness.saturation_certificate(path, fp)
    assert cert["universal_overlap_blocker"] and cert["covered_allowed_fraction"] == 1
    mine = np.zeros((12, 12), np.float32)
    mine[5, 5] = 1
    result = uniqueness.compare_array_to_registry(
        mine, [{"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}], fp
    )
    assert result["rows"][0]["duplicate_by_overlap"] and result["stop_required"]
    assert result["rows"][0]["my_dots_within_3px_of_theirs"] == 1


def test_writer_rejects_range_and_nan_without_output(tmp_path):
    for bad in (-0.01, 1.01, float("nan"), float("inf")):
        p = np.zeros((4, 4), np.float32)
        p[2, 2] = bad
        path = tmp_path / "bad.tif"
        with pytest.raises(ValueError):
            write_submission(
                path,
                p,
                ROOT / "data/reference/sample_submission.tif",
                np.ones((4, 4), bool),
                name="fixture",
                note="software test only",
            )
        assert not list(tmp_path.iterdir())


def test_writer_rejects_invalid_name_and_note(tmp_path):
    for name, note in (("", "valid"), ("a" * 141, "valid"), ("valid", "b" * 141), ("valid", " ")):
        with pytest.raises(ValueError):
            write_submission(
                tmp_path / "bad.tif",
                np.zeros((2, 2)),
                ROOT / "data/reference/sample_submission.tif",
                np.ones((2, 2), bool),
                name=name,
                note=note,
            )


def test_committed_deliverable_offline_end_to_end():
    assert verify()["all_checks_passed"]


def test_archived_e1_stop_remains_unmeasured_and_active_thvc_card_is_honest():
    e1_card = json.loads(
        (ROOT / "archive/g79_fabric_offset_f61b17a2/run_card_f61b17a2.json").read_text()
    )
    assert e1_card["holdout_dti"]["dti"] is None and e1_card["holdout_dti"]["ci95"] is None
    assert e1_card["leakage_canary"]["auc"] is None and e1_card["verdict"] == "negative"

    card = json.loads((ROOT / "run_card.json").read_text())
    assert card["holdout_dti"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert card["holdout_dti"]["dti"] > card["holdout_dti"]["matched_h33_analogue_dti"]
    assert card["secondary_holdout_dti"]["dti"] > card["secondary_holdout_dti"]["matched_h33_analogue_dti"]
    assert card["leakage_canary"]["passed"] and card["leakage_canary"]["auc"] <= 0.90
    assert card["sparse_comparable_unique"] is True and card["protocol_unique"] is False
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["submission_slots_used"] == 0 and card["organizer_submission_receipt"] is None
