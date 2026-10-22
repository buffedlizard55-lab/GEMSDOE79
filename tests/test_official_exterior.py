"""Shared v4: the official NaN-exterior writer mode (IR-79-232).

The official problem page requires null/NaN outside the submission bounds, and
the official ``sample_submission.tif`` carries 7,111,787 NaN cells outside the
footprint. Before this amendment the shared writer could only emit zeros, so no
artifact could pass rule R6 of ``gems79.portal_spec``. These tests pin both the
new mode and the unchanged default.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import grid as g57grid  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.validate import validate  # noqa: E402
from gems79.portal_spec import validate_portal_file  # noqa: E402

SAMPLE = ROOT / "data" / "reference" / "sample_submission.tif"


@pytest.fixture(scope="module")
def grid():
    return load_grid(ROOT / "data" / "reference")


def _dots(grid):
    v = np.zeros(grid.shape, np.float32)
    v[grid.footprint] = 0.0
    # A handful of isolated dots inside the footprint, none on the catalogue.
    free = np.flatnonzero((grid.footprint & ~grid.catalogue).ravel())[::50_000][:12]
    v.ravel()[free] = 1.0
    return v


def test_nan_exterior_writes_nan_outside_and_finite_inside(tmp_path, grid):
    v = _dots(grid)
    out = tmp_path / "candidate.tif"
    info = g57grid.write_geotiff(out, v, footprint=grid.footprint, exterior="nan")
    assert info["nodata_repr"] in {"nan", "NaN"}
    with rasterio.open(out) as src:
        a = src.read(1)
        assert np.isnan(src.nodata)
    assert np.isnan(a[~grid.footprint]).all()
    assert np.isfinite(a[grid.footprint]).all()
    assert a[grid.footprint].min() >= 0.0 and a[grid.footprint].max() <= 1.0
    # Exact arithmetic: outside cells are NaN, and the dot count is preserved.
    assert int(np.isnan(a).sum()) == int((~grid.footprint).sum())
    assert int((a > 0).sum()) == int((v > 0).sum())


def test_nan_exterior_passes_the_official_rules(tmp_path, grid):
    out = tmp_path / "candidate.tif"
    g57grid.write_geotiff(out, _dots(grid), footprint=grid.footprint, exterior="nan")
    report = validate_portal_file(out, template=SAMPLE)
    assert report["ok"] is True, report["failed_rules"]
    assert [r["pass"] for r in report["rules"]] == [True] * 8


def test_nan_exterior_rejects_nan_inside(tmp_path, grid):
    v = _dots(grid)
    v[grid.footprint] = np.where(v[grid.footprint] > 0, np.nan, 0.0)
    with pytest.raises(ValueError, match="finite"):
        g57grid.write_geotiff(tmp_path / "bad.tif", v, footprint=grid.footprint, exterior="nan")


def test_nan_exterior_requires_footprint(tmp_path, grid):
    with pytest.raises(ValueError, match="footprint"):
        g57grid.write_geotiff(tmp_path / "bad.tif", _dots(grid), exterior="nan")


def test_zeros_default_is_unchanged(tmp_path, grid):
    v = _dots(grid)
    out = tmp_path / "zeros.tif"
    g57grid.write_geotiff(out, v)
    with rasterio.open(out) as src:
        a = src.read(1)
    assert np.isfinite(a).all()
    assert (a[~grid.footprint] == 0).all()


def test_validator_still_rejects_zeros_under_the_nan_policy(tmp_path, grid):
    v = _dots(grid)
    out = tmp_path / "zeros.tif"
    g57grid.write_geotiff(out, v)
    receipt = validate(out, footprint=grid.footprint, exterior="nan")
    assert receipt["checks"]["outside_footprint_nan"] is False
    assert receipt["all_checks_passed"] is False


def test_mode_must_be_known(tmp_path, grid):
    with pytest.raises(ValueError, match="exterior"):
        g57grid.write_geotiff(tmp_path / "x.tif", _dots(grid), footprint=grid.footprint,
                              exterior="null")


def test_receipt_is_strict_json(tmp_path, grid):
    """The NaN nodata must never leak into a strict-JSON receipt (it crashed before)."""
    out = tmp_path / "candidate.tif"
    g57grid.write_geotiff(out, _dots(grid), footprint=grid.footprint, exterior="nan")
    receipt = validate(out, footprint=grid.footprint, exterior="nan")
    text = json.dumps(receipt, allow_nan=False)   # must not raise
    assert '"nan"' in text
