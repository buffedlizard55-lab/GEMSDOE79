import numpy as np
import pytest

from gems79 import trace as T
from gems79 import data as D


def test_emit_dots_respects_budget_spacing_allowed_and_quota():
    rng = np.random.default_rng(0)
    H = W = 120
    s = rng.random((H, W), dtype=np.float32)
    allowed = np.ones((H, W), bool)
    allowed[:, :10] = False
    quota = np.zeros((H, W), bool)
    quota[:, 60:] = True
    dots, info = T.emit_dots(s, allowed, 300, min_sep=2.8, quota_mask=quota, quota_share=0.5)
    assert dots.sum() == 300 == info["dots"]
    assert not dots[:, :10].any()
    assert (dots & quota).sum() <= 150
    ys, xs = np.nonzero(dots)
    pts = np.stack([ys, xs], 1).astype(float)
    d2 = ((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1)
    np.fill_diagonal(d2, np.inf)
    assert np.sqrt(d2.min()) >= 2.8


def test_emit_dots_zero_score_cells_are_never_emitted():
    s = np.zeros((50, 50), np.float32)
    s[10, 10] = 0.9
    dots, info = T.emit_dots(s, np.ones_like(s, bool), 10)
    assert dots.sum() == 1 and dots[10, 10] and info["exhausted_candidates"]


def test_continuity_surface_bounds_and_identity():
    rng = np.random.default_rng(1)
    p = rng.random((200, 160), dtype=np.float32)
    foot = np.ones_like(p, bool)
    foot[:, :20] = False
    assert np.array_equal(T.continuity_surface(p, foot, mix=0.0), np.where(foot, p, 0))
    s = T.continuity_surface(p, foot, mix=0.5)
    assert s.dtype == np.float32 and s.min() >= 0 and s.max() <= 1
    assert not s[:, :20].any()


def test_allowed_domain_excludes_two_pixel_collar():
    foot = np.ones((30, 30), bool)
    known = np.zeros((30, 30), bool)
    known[15, 15] = True
    a = T.allowed_domain(foot, known, 2.0)
    assert not a[15, 15] and not a[15, 17] and not a[17, 15] and not a[16, 16]
    assert a[15, 18] and a[17, 16]  # sqrt(5) = 2.236 > 2 is allowed, like the 0.2778 file


def test_lidar_dequantisation_endpoints():
    for name, (xmax, t) in D.LIDAR_QUANT.items():
        u = (np.array([1, 255], np.float32) - 1) / 254.0
        x = xmax * (u * u if t == "sqrt" else u)
        assert x[0] == 0.0 and x[1] == pytest.approx(xmax)
