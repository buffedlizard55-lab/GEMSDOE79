"""Geometry tests for H79-DILSTEP. No holdout scores and no registry reads."""
import numpy as np

from gems79.dilstep import paint_cones, robust_z, score_surface, stepover_mask, tip_outward


def test_tip_outward_points_away_from_the_only_neighbor():
    cat = np.zeros((7, 7), bool)
    cat[3, 2] = True
    cat[3, 3] = True  # tip on the east end; neighbor is west
    ys, xs, angs = tip_outward(cat)
    east = np.where((ys == 3) & (xs == 3))[0]
    assert east.size == 1
    # Outward is +x, atan2(0, +1) == 0.
    assert abs(angs[east[0]]) < 1e-6


def test_cone_lands_ahead_of_the_tip_and_not_behind_it():
    angs = np.array([0.0])
    mask = paint_cones(np.array([5]), np.array([5]), angs, (12, 12), rmin=2, rmax=4, half_deg=10, samples=3)
    assert mask[5, 8]
    assert not mask[5, 2]


def test_stepover_requires_a_lateral_gap_and_does_not_paint_the_catalogue():
    cat = np.zeros((20, 20), bool)
    cat[5, 2:6] = True
    cat[8, 8:12] = True
    ys, xs, angs = tip_outward(cat)
    params = {
        "stepover_max_sep_px": 12,
        "stepover_across_min_px": 2,
        "stepover_across_max_px": 8,
        "stepover_strike_tol_deg": 30,
    }
    mask = stepover_mask(ys, xs, angs, cat, params)
    assert not np.any(mask & cat)
    assert mask.any()


def test_score_is_zero_on_blocked_cells_and_sentinel_does_not_dominate():
    shape = (6, 6)
    fp = np.ones(shape, bool)
    blocked = np.zeros(shape, bool)
    blocked[0, 0] = True
    values = np.ones(shape, np.float32)
    values[1, 1] = -3.4e38
    z = robust_z(values, fp, clip=10, sentinel_below=-1e30)
    assert z[1, 1] == 0
    fields = {
        "horsetail": np.zeros(shape, bool),
        "stepover": np.zeros(shape, bool),
        "intersection": np.zeros(shape, bool),
        "shoreline_flag": np.zeros(shape, bool),
    }
    params = {"base_floor": 0.15, "thk_weight": 0.5, "weight_horsetail": 2, "weight_stepover": 3,
              "weight_intersection": 1.5, "shoreline_weight": 0.15}
    score = score_surface(z, z, z, z, fields, fp, blocked, params, use_structure=True)
    assert score[0, 0] == 0
    assert np.isfinite(score).all()
    assert (score >= 0).all()
