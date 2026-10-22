"""Unit tests for the G79-MFX matched-filter core (no competition data required)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems79 import mfx  # noqa: E402


def _synthetic(n: int = 160, seed: int = 3):
    """Three channels sharing one diagonal line, plus noise and a blob control."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0, 0.25, (n, n)).astype(np.float32)
    line = np.zeros((n, n), np.float32)
    for i in range(20, n - 20):
        line[i, i] = 1.0
        line[i, i + 1] = 0.6
    blob = np.zeros((n, n), np.float32)
    blob[100:118, 40:58] = 1.0
    chans = {}
    for b in mfx.TEMPLATE_BANDS:
        chans[b] = base + 1.0 * line - 0.8 * blob
    for b in mfx.MODEL_BANDS:
        chans.setdefault(b, base.copy())
    fp = np.ones((n, n), bool)
    return mfx.ChannelStack(data=chans, footprint=fp), line.astype(bool), blob.astype(bool)


def test_template_bank_is_unit_norm_and_deduplicated():
    chan, line, _ = _synthetic()
    bank = mfx.template_bank(chan, line, count=8, size=9, candidates=200, seed=1)
    assert bank.shape[0] == 8
    assert bank.shape[1] == len(mfx.TEMPLATE_BANDS)
    flat = bank.reshape(bank.shape[0], -1).astype(np.float64)
    norms = np.linalg.norm(flat, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)
    assert np.allclose(flat.mean(axis=1), 0.0, atol=1e-5)
    corr = np.abs(flat @ flat.T)
    np.fill_diagonal(corr, 0.0)
    assert corr.max() < 0.70 + 1e-6


def test_matched_filter_peaks_on_the_learned_line_and_not_on_the_blob():
    chan, line, blob = _synthetic()
    bank = mfx.template_bank(chan, line, count=6, size=9, candidates=200, seed=2)
    score = mfx.ncc_score(chan, bank, size=9, footprint=chan.footprint)
    assert np.isfinite(score).all()
    assert score[line].mean() > score[blob].mean() + 0.10
    # A matched filter is translation invariant: the score cannot carry an
    # absolute coordinate, only the local texture.
    assert score.argmax() // score.shape[1] > 10


def test_prior_correction_recovers_the_population_prior():
    p = np.full(1000, 0.5)
    out = mfx.prior_correct(p, sample_pi=0.25, true_pi=0.01)
    assert np.all(out < 0.5)
    mid = mfx.prior_correct(np.array([0.25]), sample_pi=0.25, true_pi=0.01)[0]
    assert mid == pytest.approx(0.01, abs=5e-3)


def test_catalogue_geometry_distance_is_zero_on_the_catalogue():
    cat = np.zeros((40, 40), bool)
    cat[5:35, 7] = True
    dist, dens = mfx.catalogue_geometry(cat)
    assert np.allclose(dist[5:35, 7], 0.0)
    assert dist[5:35, 8].max() == pytest.approx(1.0)
    assert dens[5:35, 7].min() > 0.0
