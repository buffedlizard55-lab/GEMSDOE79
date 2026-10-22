"""Synthetic checks for scripts/measure_registry_halo.py (no competition data needed)."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("measure_registry_halo", ROOT / "scripts" / "measure_registry_halo.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _write(path, arr):
    profile = dict(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                   dtype="float32", crs="EPSG:32611", transform=from_origin(0, 100, 100, 100), nodata=None)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype("float32"), 1)


def test_single_dot_halo_matches_disk_count(tmp_path):
    fp = np.ones((21, 21), dtype="float32")
    reg = np.full((21, 21), np.nan, dtype="float32")
    reg[10, 10] = 1.0  # one dot in the centre
    _write(tmp_path / "fp.tif", fp)
    _write(tmp_path / "reg.tif", reg)
    out = mod.measure(tmp_path / "reg.tif", tmp_path / "fp.tif", radius_px=3)
    # Euclidean disk of radius 3 has 29 integer lattice points (|dx|^2+|dy|^2 <= 9).
    assert out["halo_covered_allowed_cells"] == 29
    assert out["uncovered_allowed_cells"] == 21 * 21 - 29
    assert out["registry_dot_cells_total"] == 1


def test_nan_outside_is_not_a_dot_and_zero_is_not_a_dot(tmp_path):
    fp = np.ones((5, 5), dtype="float32")
    reg = np.zeros((5, 5), dtype="float32")  # zeros are background, not dots
    reg[0, 0] = np.nan
    _write(tmp_path / "fp.tif", fp)
    _write(tmp_path / "reg.tif", reg)
    out = mod.measure(tmp_path / "reg.tif", tmp_path / "fp.tif", radius_px=3)
    assert out["registry_dot_cells_total"] == 0
    assert out["halo_covered_allowed_cells"] == 0


def test_grid_mismatch_fails_closed(tmp_path):
    _write(tmp_path / "fp.tif", np.ones((4, 4), dtype="float32"))
    _write(tmp_path / "reg.tif", np.ones((5, 5), dtype="float32"))
    with pytest.raises(ValueError):
        mod.measure(tmp_path / "reg.tif", tmp_path / "fp.tif")


def test_off_catalogue_accounting_and_repo_relative_paths(tmp_path):
    fp = np.ones((11, 11), dtype="float32")
    cat = np.zeros((11, 11), dtype="float32")
    cat[0, 0] = 1.0  # 1 catalogue pixel outside the centre dot's 3-px halo
    cat[5, 5] = 1.0  # 1 catalogue pixel inside the centre dot's 3-px halo
    reg = np.zeros((11, 11), dtype="float32")
    reg[5, 5] = 1.0
    _write(tmp_path / "sample_submission.tif", fp)
    _write(tmp_path / "existing_faults.tif", cat)
    _write(tmp_path / "reg.tif", reg)
    out = mod.measure(tmp_path / "reg.tif", tmp_path / "sample_submission.tif", radius_px=3)
    assert out["allowed_cells_finite_footprint"] == 121
    assert out["halo_covered_allowed_cells"] == 29
    assert out["uncovered_allowed_cells"] == 92
    assert out["catalogue_positive_cells_in_footprint"] == 2
    assert out["off_catalogue_allowed_cells"] == 119
    assert out["off_catalogue_halo_covered_cells"] == 28
    assert out["off_catalogue_uncovered_cells"] == 91
    assert out["uncovered_cells_on_catalogue"] == 1
    assert out["uncovered_allowed_cells"] - out["uncovered_cells_on_catalogue"] == out["off_catalogue_uncovered_cells"]

    # Repo-relative path helper strips ROOT prefix
    assert mod._rel_path(ROOT / "data/reference/sample_submission.tif") == "data/reference/sample_submission.tif"
    for fname in ("halo_saturation_13GEMSDOE_1db538e6.json", "halo_saturation_17GEMSDOE_Eproba_1db538e6.json"):
        import json
        doc = json.loads((ROOT / "evidence" / fname).read_text(encoding="utf-8"))
        assert doc["footprint_path"] == "data/reference/sample_submission.tif"
        assert doc["allowed_cells_finite_footprint"] - doc["catalogue_positive_cells_in_footprint"] == doc["off_catalogue_allowed_cells"] == 5106385
        assert doc["uncovered_allowed_cells"] - doc["uncovered_cells_on_catalogue"] == doc["off_catalogue_uncovered_cells"]
