import json
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.distance import pdist
from gems79.placement import place
from gems79.status import submission_decision

ROOT = Path(__file__).resolve().parents[1]


def test_poisson_boundary_no_wrap_and_fixed_budget():
    a = np.random.default_rng(1).random((20, 21)).astype("float32")
    allowed = np.ones_like(a, bool)
    allowed[:, 0] = False
    p, r = place(a, allowed, 20)
    assert p.sum() == 20 and not (p & ~allowed).any()
    assert pdist(np.argwhere(p)).min() >= 3
    q, _ = place(a, allowed, 20)
    assert np.array_equal(p, q)


def test_empty_surface_is_not_padded_with_fake_dots():
    p, r = place(np.zeros((5, 5)), np.ones((5, 5), bool), 10)
    assert not p.any() and r["exhausted"]


def test_invalid_surface_never_silently_clipped():
    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            place(np.full((5, 5), value), np.ones((5, 5), bool), 5)


def e1_card():
    # The archived negative E1 card is a real, fully measured negative fixture.
    return json.loads((ROOT/'evidence/e1/run_card_e1.json').read_text())

def test_format_green_never_means_submit_green():
    card = json.loads((ROOT / "run_card.json").read_text())
    result = submission_decision(card, actual_sha256=card["raster_sha256"], format_passed=True)
    assert result["ok_to_download"] and not result["ok_to_submit"]
    assert not result["human_inspection_required_for_this_decision"]


def test_edited_ok_flag_cannot_bypass_individual_gates():
    card = json.loads((ROOT / "run_card.json").read_text())
    card["ok_to_submit"] = True
    card["approved_for_weekly_slot"] = True
    card["verdict"] = "promote"
    result = submission_decision(card, actual_sha256=card["raster_sha256"], format_passed=True)
    assert not result["ok_to_submit"]
    assert "literal_novelty_not_cleared" in result["blockers"]
    assert "separate_selector_receipt_missing_or_unbound" in result["blockers"]
    assert "separate_selector_receipt_missing_or_unbound" in result["blockers"]

    card_unmeasured = dict(card, holdout_dti={"dti": None, "ci95": None})
    result2 = submission_decision(
        card_unmeasured, actual_sha256=card["raster_sha256"], format_passed=True
    )
    assert "holdout_dti_and_ci_not_measured" in result2["blockers"]


def _fully_gated_software_card():
    digest = "a" * 64
    return {
        "raster_sha256": digest,
        "protocol_unique": True,
        "leakage_canary": {
            "passed": True, "auc": 0.8, "features_cleared": 1,
            "required_threshold": 0.90,
        },
        "current_best_holdout_beaten": True,
        "holdout_dti": {
            "dti": 0.6, "ci95": [0.5, 0.7], "withheld_positive_pixels": 10,
            "evaluator_version": "gems57-pooled-hide-v2",
        },
        "source_provenance_verified": True,
        "verdict": "promote",
        "approved_for_weekly_slot": True,
        "selector_receipt": {
            "raster_sha256": digest, "selector": "scripts/select_submission.py",
            "all_automated_gates_passed": True, "source_url": "software-fixture",
            "observed_utc": "software-fixture",
        },
        "ok_to_submit": True,
    }


def test_official_portal_format_is_required_for_submission_not_research_download():
    # Synthetic software fixture only; values are not empirical holdout results.
    card = _fully_gated_software_card()
    rejected = submission_decision(
        card, actual_sha256=card["raster_sha256"], format_passed=True,
        official_format_passed=False,
    )
    assert rejected["ok_to_download"] is True
    assert rejected["official_format_passed"] is False
    assert rejected["ok_to_submit"] is False
    assert "official_submission_format_not_cleared" in rejected["blockers"]

    accepted_fixture = submission_decision(
        card, actual_sha256=card["raster_sha256"], format_passed=True,
        official_format_passed=True,
    )
    assert accepted_fixture["ok_to_submit"] is True


def test_official_portal_format_requires_literal_boolean_pass():
    card = _fully_gated_software_card()
    result = submission_decision(
        card, actual_sha256=card["raster_sha256"], format_passed=True,
        official_format_passed="yes",
    )
    assert result["ok_to_download"] is True and not result["ok_to_submit"]
    assert "official_submission_format_not_cleared" in result["blockers"]


def test_corrupt_bytes_disable_download_and_submission():
    card = json.loads((ROOT / "run_card.json").read_text())
    result = submission_decision(card, actual_sha256="bad", format_passed=True)
    assert not result["ok_to_download"] and not result["ok_to_submit"]
