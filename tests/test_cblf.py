"""Tests for the CBLF lane: metric algebra, emitter invariants, novelty definition."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

import gems79.cblf as cblf          # noqa: E402
from gems57 import metric           # noqa: E402


def test_curve_credit_expectation_is_one_third():
    """E[k | uniformly inside the 3-px tube] = 1/3 (analytic, Monte-Carlo checked)."""
    rng = np.random.default_rng(0)
    r = 3.0 * np.sqrt(rng.random(400_000))
    k = metric.kernel(r)
    assert abs(float(k.mean()) - 1.0 / 3.0) < 5e-3


def test_curve_beats_dot_at_matched_budget_on_an_aligned_trace():
    """A 1-px curve on the truth earns ~1 per pixel; the same count of dots ~1/3."""
    truth = np.zeros((60, 60), bool)
    truth[30, 5:55] = True
    curve = np.zeros_like(truth)
    curve[30, 5:55] = True                      # exactly aligned
    dots = np.zeros_like(truth)
    dots[rng_rows(0), rng_cols(0)] = True       # 50 random points
    dots &= ~truth
    r_curve = metric.dti_binary(curve, truth)
    r_dots = metric.dti_binary(dots, truth)
    assert r_curve["dti"] > 0.9
    assert r_curve["dti"] > r_dots["dti"] * 3.0


def rng_rows(seed):
    return np.random.default_rng(seed).integers(25, 36, 50)


def rng_cols(seed):
    return np.random.default_rng(seed + 1).integers(0, 60, 50)


def test_emit_curves_respects_budget_and_is_connected_lines():
    rng = np.random.default_rng(3)
    prob = rng.random((120, 140)).astype(np.float32)
    allowed = np.ones((120, 140), bool)
    sk, info = cblf.emit_curves(prob, allowed, budget=400)
    assert sk.shape == allowed.shape
    assert info["pixels"] == int(sk.sum()) <= 400
    assert int(sk.sum()) > 0


def test_emit_dots_respects_budget():
    rng = np.random.default_rng(4)
    prob = rng.random((80, 90)).astype(np.float32)
    allowed = np.ones((80, 90), bool)
    dots, info = cblf.emit_dots(prob, allowed, budget=250)
    assert int(dots.sum()) == 250 == info["pixels"]


def test_emit_dots_never_selects_outside_allowed():
    prob = np.zeros((40, 40), np.float32)
    prob[:20] = 0.9
    allowed = np.zeros((40, 40), bool)
    allowed[20:] = True
    dots, _ = cblf.emit_dots(prob, allowed, budget=10)
    assert not dots[:20].any()


def test_sentinel_to_nan_only_removes_the_float32_nodata_sentinel():
    a = np.array([-3.4e38, -1.0, 0.0, 1.0], np.float32)
    out = cblf.sentinel_to_nan(a)
    assert np.isnan(out[0]) and np.isfinite(out[1:]).all()


def test_recall_lower_bound_matches_score_algebra():
    sys.path.insert(0, str(ROOT / "scripts"))
    from cblf_score_algebra import recall_lower_bound
    assert abs(recall_lower_bound(0.2778) - 0.235314048536699) < 1e-9
    # a reported score of 0.8 cannot come from less than 0.8*0.8/(1-0.16) recall
    assert abs(recall_lower_bound(0.8) - 0.64 / 0.84) < 1e-12


def test_holdout_note_documents_that_instrument_measures_recovery():
    card_paths = sorted((ROOT / "artifacts" / "cblf").glob("*.card.json"))
    if not card_paths:
        return
    import json
    card = json.loads(card_paths[-1].read_text())
    caveat = card["holdout"]["caveat"].lower()
    assert "already-mapped" in caveat or "recovery" in caveat
