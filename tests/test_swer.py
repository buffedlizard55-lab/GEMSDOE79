"""G79-SWER fixed-transform and frozen-evidence integrity tests."""
from __future__ import annotations

import hashlib
import json
import stat
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems79.swer import quantile01, structure_coherence  # noqa: E402


def test_quantile01_masks_invalid_and_clamps_fixed_percentiles():
    a = np.arange(100, dtype=np.float32).reshape(10, 10)
    valid = np.ones_like(a, dtype=bool)
    valid[0, 0] = False
    out, (p10, p90) = quantile01(a, valid)
    assert out.dtype == np.float32
    assert out[0, 0] == 0.0
    assert 9.0 < p10 < 11.0 and 88.0 < p90 < 90.0
    assert out[valid].min() == 0.0 and out[valid].max() == 1.0
    assert np.isfinite(out).all()


def test_structure_coherence_is_bounded_and_line_exceeds_isotropic_blob():
    valid = np.ones((81, 81), bool)
    line = np.zeros((81, 81), np.float32)
    line[:, 39:42] = 1.0
    blob = np.zeros_like(line)
    yy, xx = np.ogrid[:81, :81]
    blob[(yy - 40) ** 2 + (xx - 40) ** 2 <= 8 ** 2] = 1.0
    c_line = structure_coherence(line, valid)
    c_blob = structure_coherence(blob, valid)
    assert c_line.shape == line.shape
    assert np.isfinite(c_line).all()
    assert c_line.min() >= 0.0 and c_line.max() <= 1.0
    assert c_line[40, 40] > c_blob[40, 40]


def test_structure_coherence_zeros_invalid_outputs_even_though_boundary_halo_is_audited():
    edge = np.zeros((51, 51), np.float32)
    edge[:, 25:] = 1.0
    valid = np.ones_like(edge, bool)
    valid[20:31, 20:31] = False
    coherence = structure_coherence(edge, valid)
    assert np.all(coherence[~valid] == 0.0)
    assert np.isfinite(coherence).all()


def test_swer_preregistration_is_hash_locked():
    prereg = ROOT / "registry/preregistration_g79_swer.json"
    lock = (ROOT / "evidence/preregistration_g79_swer_sha256.txt").read_text().strip()
    assert hashlib.sha256(prereg.read_bytes()).hexdigest() == lock
    data = json.loads(prereg.read_text())
    assert data["lane"] == "G79-SWER"
    assert data["branch"] == "arena/778c4a96-gemsdoe79"
    assert data["literal_novelty"]["known_result_before_lane"].startswith("impossible_under_literal_gate")


def test_swer_run_card_and_artifact_when_present():
    card_path = ROOT / "run_card_swer.json"
    if not card_path.exists():
        return
    card = json.loads(card_path.read_text())
    tif = ROOT / card["submission_file"]
    zip_path = ROOT / card["zip_file"]
    receipt_path = ROOT / card["receipt_file"]
    assert card["lane"] == "G79-SWER"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True and card["ok_to_submit"] is False
    assert "DO-NOT-SUBMIT" in tif.name
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o644 for path in (tif, zip_path, receipt_path))
    assert card["protocol_unique"] is False
    assert card["correlation_overlap_vs_registry"]["final_prediction_support"]["forward_overlap_3px"] == 1.0
    assert card["post_run_implementation_diagnostic"]["invalid_8px_halo_enrichment"] > 1.0
    official = card["post_run_official_format_audit"]
    assert official["validator_exit_code"] == 2
    assert official["output"]["sha256"] == card["raster_sha256"]
    assert official["output"]["failed_rules"] == ["R6"]
    assert official["output"]["ok"] is False
    assert official["output"]["cells"]["outside_non_nan"] == official["output"]["cells"]["outside_cells"]
    assert card["submission_note_chars"] <= 140
