"""Regression tests for the H80 pilots (session 842c8c7c). Synthetic data only, plus cheap artifact checks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_h80_drape_pilot as D  # noqa: E402


def test_greedy_place_enforces_300m_separation_and_budget():
    rng = np.random.default_rng(0)
    shape = (60, 60)
    order = rng.permutation(shape[0] * shape[1])
    dots = D.greedy_place(order, shape, budget=200, sep=D.SEP_PX)
    ys, xs = np.nonzero(dots)
    assert 0 < len(ys) <= 200
    pts = np.stack([ys, xs], 1).astype(float)
    d = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    assert d.min() >= D.SEP_PX - 1e-9


def test_greedy_place_stops_at_budget():
    order = np.arange(40 * 40)
    dots = D.greedy_place(order, (40, 40), budget=5, sep=3.0)
    assert int(dots.sum()) == 5


def test_notch_mask_is_boolean_and_nonempty():
    m = D.notch_mask((64, 48))
    assert m.shape == (64, 48) and m.dtype == bool
    assert 0 < int(m.sum()) < m.size


def test_tilt_edge_score_masks_nodata_sentinel():
    rng = np.random.default_rng(1)
    rtp = rng.normal(0, 1, (48, 48)).astype(np.float32)
    footprint = np.zeros((48, 48), bool)
    footprint[8:40, 8:40] = True
    rtp[10:12, 10:12] = -3.4028234663852886e38  # finite nodata sentinel inside the footprint
    for notch in (False, True):
        s = D.tilt_edge_score(rtp, footprint, notch=notch)
        assert np.isfinite(s).all()
        assert (s >= 0).all()
        assert s[~footprint].max() == 0


def test_run_card_is_negative_and_has_no_submission_fields():
    card = json.loads((ROOT / "run_card_h80_pilots.json").read_text())
    assert card["verdict"] == "negative"
    assert card["ok_to_submit_new_file"] is False
    assert card["submission_slots_used"] == 0
    assert card["raster_sha256"] is None and card["raster_sha256_reason"]
    assert len(card["submission_note"] or "") <= 140
    assert card["best_pilot_candidate_vs_bar"]["beats_bar_both_seeds"] is False
    assert card["leakage_canary"]["max_auc"] <= 0.90


def test_preregistrations_withdraw_hand_typed_timestamps():
    for name in ("drape", "radio"):
        pre = json.loads((ROOT / f"registry/preregistration_h80_{name}_pilot.json").read_text())
        assert pre["preregistered_utc"] is None
        assert "WITHDRAWN" in pre["preregistration_timestamp_status"]
        assert pre["clock_read_at_correction_utc"].endswith("Z")


def test_pilot_withheld_counts_match_project_receipts():
    for folder in ("h80_drape_pilot", "h80_radio_pilot"):
        for seed in (20, 30):
            d = json.loads((ROOT / f"evidence/{folder}/seed{seed}.json").read_text())
            assert d["withheld_positive_pixels"] == d["expected_receipt_withheld_positive_pixels"]


def test_overlap_check_is_per_seed_and_card_is_derived_from_it():
    ov = json.loads((ROOT / "evidence/h80_pilot_overlap_check.json").read_text())
    assert set(ov["per_seed"]) == {"20", "30"}
    assert ov["summary"]["max_within_3px"] <= 0.70 and ov["summary"]["max_abs_spearman"] <= 0.90
    assert ov["summary"]["result"] == "NOT DUPLICATES"
    card = json.loads((ROOT / "run_card_h80_pilots.json").read_text())
    assert str(ov["summary"]["max_within_3px"]) in card["correlation_overlap_result"]
    assert card["correlation_overlap_vs_registry"] == ov["per_seed"]
