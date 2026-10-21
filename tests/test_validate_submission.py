"""Synthetic unit tests for the format/duplicate gate; not competition evidence."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from affine import Affine

from scripts.validate_submission import main


class ValidateSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.transform = Affine(100, 0, 1000, 0, -100, 2000)
        self.crs = "EPSG:32611"
        self.shape = (8, 8)
        self.footprint = np.full(self.shape, np.nan, dtype=np.float32)
        self.footprint[:6, :6] = 0.0
        self.reference = self.root / "reference.tif"
        self.write(self.reference, self.footprint)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, path: Path, values: np.ndarray, nodata: float = np.nan,
              transform: Affine | None = None, crs: str | None = None) -> None:
        profile = {
            "driver": "GTiff",
            "height": values.shape[0],
            "width": values.shape[1],
            "count": 1,
            "dtype": "float32",
            "crs": crs or self.crs,
            "transform": transform or self.transform,
            "nodata": nodata,
        }
        with rasterio.open(path, "w", **profile) as ds:
            ds.write(values.astype(np.float32), 1)

    def run_cli(self, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        with patch("sys.argv", ["validate_submission.py", *args]), \
                contextlib.redirect_stdout(output):
            code = main()
        return code, output.getvalue()

    def test_valid_grid_and_independent_registry_pass(self) -> None:
        candidate = np.full(self.shape, np.nan, dtype=np.float32)
        candidate[:6, :6] = 0.0
        candidate[0, 0] = 0.6
        candidate[2, 2] = 0.7
        candidate[4, 4] = 0.8
        registry_values = np.full(self.shape, np.nan, dtype=np.float32)
        registry_values[:6, :6] = 0.0
        registry_values[0, 5] = 0.5
        registry_values[5, 0] = 0.5
        candidate_path = self.root / "candidate.tif"
        registry_path = self.root / "registry.tif"
        self.write(candidate_path, candidate)
        self.write(registry_path, registry_values)

        code, stdout = self.run_cli(
            "--submission", str(candidate_path),
            "--reference", str(self.reference),
            "--footprint", str(self.reference),
            "--registry", str(registry_path),
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn('"status": "passed"', stdout)
        self.assertIn('"values_in_0_1": true', stdout)

    def test_grid_mismatch_fails(self) -> None:
        candidate = np.zeros((7, 8), dtype=np.float32)
        candidate_path = self.root / "wrong-grid.tif"
        self.write(candidate_path, candidate,
                   transform=Affine(100, 0, 1001, 0, -100, 2000))
        code, stdout = self.run_cli(
            "--submission", str(candidate_path),
            "--reference", str(self.reference),
            "--footprint", str(self.reference),
            "--registry", str(self.reference),
        )
        self.assertEqual(code, 1)
        self.assertIn('"shape_matches": false', stdout)
        self.assertIn('"transform_matches": false', stdout)

    def test_above_one_fails(self) -> None:
        candidate = np.full(self.shape, np.nan, dtype=np.float32)
        candidate[:6, :6] = 0.0
        candidate[1, 1] = 1.01
        candidate_path = self.root / "bad-range.tif"
        self.write(candidate_path, candidate)
        code, stdout = self.run_cli(
            "--submission", str(candidate_path),
            "--reference", str(self.reference),
            "--footprint", str(self.reference),
            "--registry", str(candidate_path),
        )
        self.assertEqual(code, 1)
        self.assertIn('"values_in_0_1": false', stdout)

    def test_nan_inside_footprint_fails(self) -> None:
        candidate = np.full(self.shape, np.nan, dtype=np.float32)
        candidate[:6, :6] = 0.0
        candidate[2, 2] = np.nan
        candidate_path = self.root / "nan-inside.tif"
        self.write(candidate_path, candidate)
        code, stdout = self.run_cli(
            "--submission", str(candidate_path),
            "--reference", str(self.reference),
            "--footprint", str(self.reference),
            "--registry", str(self.reference),
        )
        self.assertEqual(code, 1)
        self.assertIn('"no_nan_inside_footprint": false', stdout)

    def test_outside_footprint_must_be_null(self) -> None:
        candidate = np.full(self.shape, np.nan, dtype=np.float32)
        candidate[:6, :6] = 0.0
        candidate[7, 7] = 0.0  # finite outside the scoring footprint
        candidate_path = self.root / "outside-value.tif"
        self.write(candidate_path, candidate)
        code, stdout = self.run_cli(
            "--submission", str(candidate_path),
            "--reference", str(self.reference),
            "--footprint", str(self.reference),
            "--registry", str(candidate_path),
        )
        self.assertEqual(code, 1)
        self.assertIn('"outside_is_nodata_or_nan": false', stdout)

    def test_negative_nodata_sentinel_is_rejected_even_outside(self) -> None:
        sentinel = np.float32(-3.4028235e38)
        candidate = np.full(self.shape, sentinel, dtype=np.float32)
        candidate[:6, :6] = 0.0
        candidate_path = self.root / "sentinel-nodata.tif"
        self.write(candidate_path, candidate, nodata=float(sentinel))
        code, stdout = self.run_cli(
            "--submission", str(candidate_path),
            "--reference", str(self.reference),
            "--footprint", str(self.reference),
            "--registry", str(self.reference),
        )
        self.assertEqual(code, 1)
        self.assertIn('"every_stored_value_in_0_1_or_nan": false', stdout)

    def test_exact_copy_is_flagged_duplicate(self) -> None:
        candidate = np.full(self.shape, np.nan, dtype=np.float32)
        candidate[:6, :6] = 0.0
        candidate[1, 1] = 0.5
        candidate[3, 3] = 0.7
        candidate_path = self.root / "candidate.tif"
        self.write(candidate_path, candidate)
        code, stdout = self.run_cli(
            "--submission", str(candidate_path),
            "--reference", str(self.reference),
            "--footprint", str(self.reference),
            "--registry", str(candidate_path),
        )
        self.assertEqual(code, 1)
        self.assertIn('"status": "duplicate"', stdout)
        self.assertIn('"duplicate_threshold_exceeded": true', stdout)

    def test_missing_registry_blocks_gate(self) -> None:
        candidate = np.full(self.shape, np.nan, dtype=np.float32)
        candidate[:6, :6] = 0.0
        candidate[1, 1] = 0.5
        candidate_path = self.root / "candidate.tif"
        self.write(candidate_path, candidate)
        code, stdout = self.run_cli(
            "--submission", str(candidate_path),
            "--reference", str(self.reference),
            "--footprint", str(self.reference),
        )
        self.assertEqual(code, 1)
        self.assertIn('"status": "unverified"', stdout)
        self.assertIn("No registry rasters supplied", stdout)


if __name__ == "__main__":
    unittest.main()
