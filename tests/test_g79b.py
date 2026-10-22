"""Unit tests for lane G79B-SDPT primitives (synthetic, no data files)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from gems79b import features as F, trace as T  # noqa: E402


def test_channel_registry_consistent():
    assert len(F.CHANNELS) == len(set(F.CHANNELS)) == len(F.IDX)
    assert F.CHANNELS[:30] == F.BASE_CHANNELS
    assert set(F.NEW_CHANNELS) <= set(F.CHANNELS)


def test_rank01_monotonic_and_nan_preserving():
    x = np.array([[1.0, 2.0], [np.nan, 4.0]], np.float32)
    m = np.ones((2, 2), bool)
    r = F.rank01(x, m)
    assert np.isnan(r[1, 0])
    assert r[0, 0] < r[0, 1] < r[1, 1] == 1.0


def test_emit_dots_budget_spacing_exclusion():
    rng = np.random.default_rng(0)
    surf = rng.random((60, 60), dtype=np.float32)
    allowed = np.ones((60, 60), bool)
    allowed[:10, :] = False
    dots, info = T.emit_dots(surf, allowed, 50, min_sep=2.8)
    assert info["dots"] == 50
    assert not dots[:10].any()
    ys, xs = np.nonzero(dots)
    for i in range(len(ys)):
        d2 = (ys - ys[i]) ** 2 + (xs - xs[i]) ** 2
        assert (np.sort(d2)[1] >= 2.8 ** 2 - 1e-9)


def test_emit_multi_cap_respected():
    surf = np.ones((40, 40), np.float32)
    allowed = np.ones((40, 40), bool)
    bits = np.zeros((40, 40), np.int64)
    bits[:, :20] |= 1  # left half inside prior halo
    dots, info = T.emit_dots_multi(surf, allowed, 40, bits, 1, cap_share=0.5)
    assert dots[:, :20].sum() <= 20
    assert info["max_share_in_any_capped_halo"] <= 0.5 + 1e-9


def test_emit_caps_many_priors():
    surf = np.ones((40, 40), np.float32)
    allowed = np.ones((40, 40), bool)

    def sampler(cand):
        m = np.zeros((70, len(cand)), bool)  # > 63 priors: no bit-packing limit
        m[0] = (cand % 40) < 20
        return m

    dots, info = T.emit_dots_caps(surf, allowed, 40, sampler, 70, cap_share=0.5)
    assert dots[:, :20].sum() <= 20
    assert info["n_priors_capped"] == 70


def test_trace_surface_prefers_long_line_over_blob():
    p = np.zeros((100, 100), np.float32)
    p[50, 10:90] = 0.9          # long straight trace
    p[10:15, 10:15] = 0.9       # compact blob, same amplitude
    rng = np.random.default_rng(1)
    p += (rng.random(p.shape, dtype=np.float32) * 0.01)
    fp = np.ones((100, 100), bool)
    step = np.full(p.shape, 0.9, np.float32)
    s, info = T.trace_surface(p, step, fp)
    assert info["components"] >= 2
    assert s[50, 50] > s[12, 12]  # trace pixels reranked above blob pixels
    assert np.isfinite(s).all() and s.min() >= 0 and s.max() <= 1


def test_allowed_domain_excludes_catalogue_buffer():
    fp = np.ones((21, 21), bool)
    cat = np.zeros((21, 21), bool)
    cat[10, 10] = True
    a = T.allowed_domain(fp, cat, 2.0)
    assert not a[10, 10] and not a[10, 12] and a[10, 13]
