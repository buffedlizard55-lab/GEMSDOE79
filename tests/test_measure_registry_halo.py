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
