"""G79-BER band utilities (preregistered rules, not scientific results)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems79.ber import (BANDS_PX, band_ids, largest_remainder,  # noqa: E402
                        provisional_topk, within_band_ranks)


def test_largest_remainder_exact_and_proportional():
    counts = [410131, 637102, 1022690, 1790643, 1069816]
    q = largest_remainder(37654, counts)
    assert sum(q) == 37654 and len(q) == 5
    frac = np.array(counts) / sum(counts)
    assert np.all(np.abs(np.array(q) / 37654 - frac) < 0.001)
    assert largest_remainder(10, [1, 1, 1]) == [4, 3, 3]  # stable tie-break
    assert largest_remainder(0, [5, 5]) == [0, 0]
    with pytest.raises(ValueError):
        largest_remainder(5, [0, 0])


def test_band_ids_exclude_200m_collar():
    d = np.array([[0, 1, 2, 2.5, 5, 7, 10, 15, 20, 30, 50, 80]], float)
    b = band_ids(d)
    assert b.tolist() == [[-1, -1, -1, 0, 0, 1, 1, 2, 2, 3, 3, 4]]
    assert len(BANDS_PX) == 5


def test_provisional_topk_exact_quotas_and_tiebreak():
    rank = np.array([[0.9, 0.9, 0.1, 0.0], [0.5, 0.4, 0.3, 0.2]], np.float32)
    bands = np.array([[0, 0, 0, 0], [1, 1, 1, 1]], np.int8)
    allowed = np.ones((2, 4), bool)
    dots = provisional_topk(rank, bands, allowed, [1, 2, 0, 0, 0])
    assert dots.sum() == 3
    assert dots[0, 0] and not dots[0, 1]          # tie -> row-major first
    assert dots[1, 0] and dots[1, 1] and not dots[1, 2]


def test_within_band_ranks_are_per_band_percentiles():
    s0 = np.array([[10.0, 0.0], [0.0, 0.0]], np.float32)
    s1 = np.array([[0.0, 0.01], [0.0, 0.0]], np.float32)  # band-1 cells are (0,1),(1,0),(1,1)
    bands = np.array([[0, 1], [1, 1]], np.int8)
    allowed = np.array([[True, True], [True, True]])
    out = within_band_ranks([s0, s1, s0, s0, s0], bands, allowed)
    # The only band-0 cell ranks 1.0 inside its band; band-1 max also 1.0
    # even though its raw value is 1000x smaller: bands never compete.
    assert out[0, 1] == pytest.approx(1.0)  # band-1 maximum, raw value only 0.01
    assert out[1, 0] == pytest.approx(0.25) and out[1, 1] == pytest.approx(0.25)  # tied mid-ranks
