"""G79-STEPCO transforms, canary mask logic and run-card consistency."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems79 import stepco  # noqa: E402


def _step_field() -> np.ndarray:
    a = np.zeros((31, 31), np.float32)
    a[:, 16:] = 2.0
    return a


def test_step_dipole_peaks_at_the_step_and_is_nonnegative():
    d = stepco.step_dipole(_step_field())
    # The trace plateau (step at col 16, offsets ±3) dominates far-field.
    assert d[15, 13:19].mean() > 10 * (d[15, 2] + d[15, 28] + 1e-6)
    assert d[15, 2] == pytest.approx(0.0, abs=0.05)
    assert d.min() >= 0.0
    assert np.isfinite(d).all()


def test_step_dipole_ignores_flat_and_ramp_fields():
    flat = np.ones((31, 31), np.float32)
    ramp = np.tile(np.linspace(0, 1, 31, dtype=np.float32), (31, 1))
    assert stepco.step_dipole(flat).max() == 0.0
    # A pure ramp is the named mimic: directional dipoles respond, but far
    # less than the same total relief concentrated in one step.
    step = stepco.step_dipole(_step_field() / 62.0).max()
    assert stepco.step_dipole(ramp / 31.0).max() < step


def test_gradient_and_laplacian_are_finite_and_shape_preserving():
    g = stepco.grad_mag(_step_field(), 1.0)
    lap = stepco.abs_laplacian(_step_field())
    assert g.shape == lap.shape == (31, 31)
    assert np.isfinite(g).all() and np.isfinite(lap).all()
    assert g.max() > 0 and lap.max() > 0


def test_nan_handling_propagates_as_nonfinite_not_silently_zeroed():
    a = _step_field(); a[10, 10] = np.nan
    d = stepco.step_dipole(a)
    # NaN inside a shifted window must surface as non-finite (callers mask
    # via the validity support mask), never be quietly treated as signal 0.
    assert not np.isfinite(d[8:13, 8:13]).all()


def test_run_card_matches_measured_stepco_evidence():
    # STEPCO is an archived concurrent negative lane; its card lives beside the canonical one.
    card = json.loads((ROOT / "run_card_stepco.json").read_text())
    assert card["lane"] == "G79-STEPCO" and card["verdict"] == "negative"
    s1 = json.loads((ROOT / "evidence/stepco/holdout_s1_seed20.json").read_text())
    assert card["holdout_dti"]["dti"] == s1["scores"]["candidate"]["dti"]
    assert card["holdout_dti"]["ci95"] == s1["scores"]["candidate"]["ci95"]
    assert card["holdout_gates"]["passed"] is False
    assert card["current_best_holdout_beaten"] is False
    can = json.loads((ROOT / "evidence/stepco/canaries_s1_seed20.json").read_text())
    assert card["leakage_canary"]["per_seed"]["seed_20"]["max_symmetric_auc"] == can["max_symmetric_auc"]
    assert card["leakage_canary"]["passed"] is True
    assert card["leakage_canary"]["features_cleared"] == 464
    sup = json.loads((ROOT / "evidence/stepco/uniqueness_supplementary.json").read_text())
    uniq = card["correlation_overlap_vs_registry"]
    assert uniq["indexed_rasters"] == 992 and uniq["accounted_for"].startswith("992/992")
    assert len(sup["grid_invalid"]) == 6
    assert card["protocol_unique"] is False
    assert uniq["surface_before_placement"]["duplicate_by_rho"] is False
    assert uniq["final_dots_S1"]["like_for_like_duplicate"] is True
    assert uniq["final_dots_S1"]["comparable_sparse_diagnostic"]["worst_forward_overlap_3px"] < 0.70
    assert uniq["final_dots_S2"]["comparable_sparse_diagnostic"]["worst_forward_overlap_3px"] > 0.70


def test_s1_artifact_bytes_match_run_card_and_are_byte_unique_vs_archive():
    card = json.loads((ROOT / "run_card_stepco.json").read_text())
    tif = ROOT / "archive/g79_stepco_s1/downloads" / Path(card["submission_file"]).name
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    s2 = ROOT / card["experiments"]["S2_COVER"]["published_path"]
    assert s2.is_file()
    assert hashlib.sha256(s2.read_bytes()).hexdigest() == card["experiments"]["S2_COVER"]["raster_sha256"]


def test_only_one_canonical_tif_is_published():
    tifs = sorted((ROOT / "docs/downloads").glob("*.tif"))
    assert len(tifs) == 1
    card = json.loads((ROOT / "run_card.json").read_text())
    assert tifs[0].name == Path(card["submission_file"]).name
    # Filename warning iff the canonical verdict is not promote.
    assert ("DO-NOT-SUBMIT" in tifs[0].name) == (card["verdict"] != "promote")
