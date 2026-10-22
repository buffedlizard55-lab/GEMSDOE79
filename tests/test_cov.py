"""H79-COV channel mathematics on synthetic fields (no experiment re-run)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems79.covanti import step_dipole_sigma  # noqa: E402
from gems79.features import unit_ranks  # noqa: E402


def test_step_dipole_is_zero_on_constant_field_and_peaks_on_step():
    const = np.full((41, 41), 3.0, np.float32)
    assert step_dipole_sigma(const, 1.5).max() == 0.0
    field = np.zeros((41, 41), np.float32)
    field[:, 21:] = 10.0                      # sharp N-S basement step at col 20/21
    resp = step_dipole_sigma(field, 1.5)
    cols = resp[20]
    assert cols[18:24].max() > 5.0            # response localises at the step
    assert cols[2] < 0.5 and cols[38] < 0.5   # ... and not far away


def test_two_scale_persistence_requires_both_scales():
    rng = np.random.default_rng(0)
    field = rng.normal(0, 1, (61, 61)).astype(np.float32)
    field[:, 31:] += 8.0                       # through-going step survives smoothing
    fp = np.ones(field.shape, bool)
    s_small = unit_ranks(step_dipole_sigma(field, 1.5), fp)
    s_large = unit_ranks(step_dipole_sigma(field, 6.0), fp)
    persist = np.minimum(s_small, s_large)
    # persistence can never exceed either single-scale rank (definition)
    assert (persist <= s_small + 1e-6).all() and (persist <= s_large + 1e-6).all()
    # the step column ranks in the top decile of persistence
    assert persist[30, 28:34].max() > 0.9


def test_preregistered_channel_list_matches_evidence():
    meta = json.loads((ROOT / "evidence/cov/c1_holdout_seed20.json").read_text())
    names = meta["feature_names"]
    assert len(names) == 25 and len(set(names)) == 25
    assert {"anti_asym", "anti_step", "anti_coh", "log_depth_persist",
            "depth_persist_x_cover", "grav_persist_x_cover", "cover_rank"} <= set(names)
    # catalogue-free by construction: no distance/density/tip geometry inputs
    assert not any(("dist" in n or "tip" in n or "visible" in n) for n in names)
    for seed in (20, 30):
        ev = json.loads((ROOT / f"evidence/cov/c1_holdout_seed{seed}.json").read_text())
        assert ev["lane"] == "H79-COV" and ev["evaluator_version"] == "gems57-pooled-hide-v2"
        assert ev["leakage_canary"]["max_symmetric_auc"] <= 0.90
        assert ev["leakage_canary"]["n_suspicious"] == 0


def test_card_stop_reason_and_gates_agree_with_evidence():
    card = json.loads((ROOT / "run_card_cov.json").read_text())
    gates = json.loads((ROOT / "evidence/cov/c1_gates.json").read_text())
    assert card["verdict"] == "negative" and gates["all_passed"] is False
    assert "DO-NOT-SUBMIT" in card["submission_name"]
    assert card["current_best_holdout_beaten"] is False
    assert card["protocol_unique"] is False
    b1 = card["correlation_overlap_vs_registry"]["amendment_B1"]
    assert b1["worst_discriminating_forward_overlap"]["forward_overlap"] > 0.70
