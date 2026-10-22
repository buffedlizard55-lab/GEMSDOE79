"""Numerical software fixtures for the legacy H79 helper module only.

These tests do not assert that H79-CSPT is the registered active lane or that
any feature has geological skill. The active experiment is G79-FABRIC-OFFSET.
"""
import numpy as np
from gems79.features import _blakely_simpson_normal_crest, _robust_z_pos


def test_normal_crest_is_finite_nonnegative_and_repeatable():
    yy, xx = np.mgrid[-20:20, -20:20]
    field = np.exp(-((xx - 3) ** 2) / 20).astype(np.float32)
    first = _blakely_simpson_normal_crest(field)
    second = _blakely_simpson_normal_crest(field)
    assert np.isfinite(first).all()
    assert (first >= 0).all()
    np.testing.assert_array_equal(first, second)
    assert np.count_nonzero(first) > 0


def test_robust_positive_transform_is_finite_and_bounded():
    values = np.array([-3, 0, 1, 2, 100, np.nan, np.inf], dtype=np.float32)
    transformed = _robust_z_pos(values)
    assert np.isfinite(transformed).all()
    assert transformed.min() >= -4
    assert transformed.max() <= 8


def test_constant_channel_has_zero_robust_deviation():
    assert not _robust_z_pos(np.ones(16, dtype=np.float32)).any()
