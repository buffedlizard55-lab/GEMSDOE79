"""G79-CJX unit tests: synthetic geometry only, no geological scores."""
import numpy as np
import pytest

from gems79.cjx import fill_invalid, geomean2, junction_at_scale, percentile_rank


def test_percentile_rank_bounds_and_ties():
    a = np.array([[1.0, 2.0], [2.0, 4.0]], np.float32)
    mask = np.ones((2, 2), bool)
    r = percentile_rank(a, mask)
    assert r[0, 1] == r[1, 0]  # tied values share the average rank
    assert 0 < r[0, 0] < r[0, 1] < r[1, 1] == 1.0
    r2 = percentile_rank(a, np.array([[True, False], [False, False]]))
    assert r2[0, 0] == 1.0 and (r2[~np.array([[True, False], [False, False]])] == 0).all()


def test_fill_invalid_uses_valid_median():
    a = np.array([[1.0, np.nan], [3.0, 5.0]], np.float32)
    valid = np.isfinite(a)
    filled, med = fill_invalid(a, valid)
    assert med == 3.0 and filled[0, 1] == 3.0 and np.isfinite(filled).all()
    with pytest.raises(ValueError):
        fill_invalid(a, np.zeros((2, 2), bool))


def test_junction_fires_at_crossing_not_on_straight_edge():
    n = 41
    cross = np.zeros((n, n), np.float32)
    cross[:, n // 2:] += 1.0     # vertical step
    cross[n // 2:, :] += 1.0     # horizontal step -> crossing at centre
    mask = np.ones((n, n), bool)
    j, sm = junction_at_scale(cross, mask, sigma=1.0)
    centre = j[n // 2, n // 2]
    straight = j[5, n // 2]      # on the vertical step, far from the crossing
    flat = j[5, 5]
    assert centre > 5 * max(straight, 1e-9)
    assert centre > flat
    assert sm[n // 2, n // 2] > 0

    straight_only = np.zeros((n, n), np.float32)
    straight_only[:, n // 2:] = 1.0
    j2, _ = junction_at_scale(straight_only, mask, sigma=1.0)
    assert j2[n // 2, n // 2] < centre


def test_geomean2_requires_both_fields():
    a = np.array([[0.0, 1.0]], np.float32)
    b = np.array([[1.0, 0.25]], np.float32)
    g = geomean2(a, b)
    assert g[0, 0] == 0.0 and abs(g[0, 1] - 0.5) < 1e-6
    with pytest.raises(ValueError):
        geomean2(a, np.zeros((3, 3), np.float32))
