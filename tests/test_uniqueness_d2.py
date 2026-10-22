"""Amendment D-2 gate mathematics (vendor/gems57/uniqueness.py v4).

The worked cases are the ones in reports/protocol_amendment_D2_20261022.md,
including the frozen H79-NHR measurements: D-2 must keep NHR a duplicate,
keep an exact copy a duplicate at any halo coverage, and stop flagging
candidates whose overlap is forced by a halo-saturating prior alone.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.uniqueness import chance_corrected_overlap, d2_row_decision  # noqa: E402


def test_corrected_is_zero_under_independence_and_one_for_copy():
    for h in (0.0, 0.21, 0.61, 0.9):
        assert chance_corrected_overlap(h, h) == 0.0
        assert abs(chance_corrected_overlap(1.0, h) - 1.0) < 1e-12


def test_nhr_frozen_measurements_stay_duplicates():
    for ov, h in [(0.913, 0.610), (0.814, 0.204)]:  # evidence/nhr/overlap_chance.json
        d = d2_row_decision(forward_overlap=ov, halo_coverage=h, exact_overlap=0.0,
                            spearman=0.03, identical=False)
        assert d["duplicate_d2"] is True and d["chance_corrected_overlap"] > 0.70


def test_random_against_wide_halo_passes():
    d = d2_row_decision(forward_overlap=0.615, halo_coverage=0.610, exact_overlap=0.05,
                        spearman=0.01, identical=False)
    assert d["duplicate_d2"] is False


def test_raw_threshold_still_binds_below_corrected():
    # ov <= 0.70 can never fire, however small the halo.
    d = d2_row_decision(forward_overlap=0.70, halo_coverage=0.0, exact_overlap=0.7,
                        spearman=0.0, identical=False)
    assert d["duplicate_by_overlap_d2"] is False


def test_saturated_halo_uses_exact_cells():
    chance = d2_row_decision(forward_overlap=1.0, halo_coverage=0.9999995,
                             exact_overlap=0.042, spearman=0.0, identical=False)
    copy = d2_row_decision(forward_overlap=1.0, halo_coverage=1.0,
                           exact_overlap=1.0, spearman=0.0, identical=False)
    assert chance["duplicate_d2"] is False and chance["overlap_test"] == "exact_cell_halo_saturated"
    assert copy["duplicate_d2"] is True


def test_rho_and_identity_always_block():
    assert d2_row_decision(forward_overlap=0.0, halo_coverage=0.0, exact_overlap=0.0,
                           spearman=0.91, identical=False)["duplicate_d2"] is True
    assert d2_row_decision(forward_overlap=0.0, halo_coverage=0.0, exact_overlap=0.0,
                           spearman=0.0, identical=True)["duplicate_d2"] is True


def test_synthetic_copy_vs_independent_on_small_grid():
    from gems57.uniqueness import _near
    rng = np.random.default_rng(0)
    shape = (120, 120)
    prior = rng.random(shape) < 0.04
    allowed = np.ones(shape, bool)
    halo = float(_near(prior)[allowed].mean())
    copy = prior.copy()
    ov_copy = float(_near(prior)[copy].mean())
    assert d2_row_decision(forward_overlap=ov_copy, halo_coverage=halo,
                           exact_overlap=1.0, spearman=1.0, identical=True)["duplicate_d2"] is True
    indep = rng.random(shape) < 0.04
    ov_indep = float(_near(prior)[indep].mean())
    corr = chance_corrected_overlap(ov_indep, halo)
    assert corr is not None and corr < 0.35  # near chance, far below the 0.70 gate
