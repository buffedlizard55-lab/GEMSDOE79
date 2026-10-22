"""End-to-end automated regression & integrity tests for G79-CSHD (session e8afe252)."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems79.portal_spec import validate_portal_file
from validate_submission import validate_path

ROOT = Path(__file__).resolve().parents[1]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_cshd_preregistration_and_98_feature_canary():
    prereg = ROOT / "registry/preregistration_g79_cshd.json"
    sha_txt = (ROOT / "evidence/preregistration_g79_cshd_sha256.txt").read_text().strip()
    assert _sha(prereg) == sha_txt
    pdoc = json.loads(prereg.read_text())
    assert len(pdoc["feature_names"]) == 98
    assert pdoc["total_feature_count"] == 98

    canary = json.loads((ROOT / "evidence/g79_cshd_single_feature_auc.json").read_text())
    assert canary["n_features_checked"] == 98
    assert canary["all_features_passed"] is True
    assert canary["max_symmetric_auc"] <= 0.90
    assert len(canary["features"]) == 98
    assert all(f["sym_auc_seed20"] <= 0.90 and f["sym_auc_seed30"] <= 0.90 for f in canary["features"])


def test_cshd_two_seed_holdout_records_and_monotonic_ablation():
    card = json.loads((ROOT / "run_card_cshd.json").read_text())
    res = json.loads((ROOT / "evidence/g79_cshd_results.json").read_text())

    for seed_key in ("seed20", "seed30"):
        ev = res[seed_key]["official_evaluate_all"]["scores"]
        assert res[seed_key]["evaluator_version"] == "gems57-pooled-hide-v2"
        c0 = ev["C0_random_B37654"]["dti"]
        h33 = ev["C2_h33_analogue_foldfair"]["dti"]
        exp1 = ev["EXP-CSHD-1_pure_zero_catalogue"]["dti"]
        exp2 = ev["EXP-CSHD-2_cshd_uniform_d28"]["dti"]
        exp3 = ev["EXP-CSHD-3_dual_regime_cc"]["dti"]
        # Pure zero-catalogue physics surpasses H33 on BOTH seeds, with strict monotonicity
        assert c0 < h33 < exp1 < exp2 < exp3

    s20 = res["seed20"]["official_evaluate_all"]["scores"]["EXP-CSHD-3_dual_regime_cc"]["dti"]
    s30 = res["seed30"]["official_evaluate_all"]["scores"]["EXP-CSHD-3_dual_regime_cc"]["dti"]
    # Beats canonical G79-THVC on BOTH seeds AND beats prior repo two-seed mean record
    assert s20 > 0.190523
    assert s30 > 0.194393
    assert 0.5 * (s20 + s30) > 0.196306
    assert card["holdout_dti"]["beats_g79_thvc_both_seeds"] is True


def test_cshd_both_format_validators_and_fail_closed_verdict():
    card = json.loads((ROOT / "run_card_cshd.json").read_text())
    nan_tif = ROOT / card["submission_file"]
    nan_zip = ROOT / card["zip_file"]
    zeros_tif = ROOT / card["artifacts"]["shared_writer_zeros_exterior"]["tif"]

    assert _sha(nan_tif) == card["raster_sha256"]
    assert _sha(nan_zip) == card["zip_sha256"]
    assert _sha(zeros_tif) == card["zeros_raster_sha256"]
    assert "DO-NOT-SUBMIT" in nan_tif.name and "DO-NOT-SUBMIT" in zeros_tif.name
    assert len(card["submission_note"]) <= 140

    # Official R1-R8 portal format check (8/8 PASS on BOTH .tif and .zip!)
    p_tif = validate_portal_file(nan_tif)
    p_zip = validate_portal_file(nan_zip)
    assert all(r["pass"] is True for r in p_tif["rules"]), p_tif
    assert all(r["pass"] is True for r in p_zip["rules"]), p_zip
    assert p_tif["cells"]["inside_nonfinite"] == 0
    assert p_tif["cells"]["inside_out_of_range"] == 0
    assert p_tif["cells"]["outside_non_nan"] == 0
    assert p_tif["cells"]["inside_positive"] == 39747

    with zipfile.ZipFile(nan_zip) as zf:
        assert zf.namelist() == [nan_tif.name]
        assert zf.read(nan_tif.name) == nan_tif.read_bytes()

    # Shared local validator check (15/15 PASS on zeros-exterior .tif!)
    v_loc = validate_path(zeros_tif)
    assert v_loc["format_passed"] is True
    assert v_loc["validator"]["emitted_positive_pixels"] == 39747

    # Fail-closed honest gate decision
    assert card["protocol_unique"] is False
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert card["submission_slots_used"] == 0
    assert card["decision_line"] == "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO."
    assert (ROOT / "docs/g79-cshd.html").is_file()
