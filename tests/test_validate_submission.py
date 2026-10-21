import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.validate_submission import validate


class SubmissionValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.template = self.root / "sample_submission.tif"
        self.candidate = self.root / "candidate.tif"
        self.transform = from_origin(500000, 4300000, 100, 100)
        self.footprint = np.zeros((4, 5), dtype=bool)
        self.footprint[1:3, 1:4] = True
        self._write(self.template, np.where(self.footprint, 0.0, np.nan))

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, path, values, *, width=5, crs="EPSG:32611", dtype="float32", nodata=np.nan):
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=width,
            height=4,
            count=1,
            dtype=dtype,
            crs=crs,
            transform=self.transform,
            nodata=nodata,
        ) as dst:
            dst.write(np.asarray(values, dtype=dtype), 1)

    def test_valid_probabilities_and_nan_outside_pass(self):
        values = np.where(self.footprint, 0.4, np.nan)
        self._write(self.candidate, values)
        result = validate(self.candidate, self.template)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["footprint_pixels"], 6)
        self.assertEqual(result["valid_prediction_pixels"], 6)
        self.assertAlmostEqual(result["prediction_min"], 0.4, places=6)

    def test_out_of_range_value_inside_fails(self):
        values = np.where(self.footprint, 0.4, np.nan)
        values[1, 1] = 1.01
        self._write(self.candidate, values)
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIn("prediction outside [0, 1] inside the template footprint", result["errors"])

    def test_finite_value_outside_footprint_fails(self):
        values = np.where(self.footprint, 0.4, np.nan)
        values[0, 0] = 0.2
        self._write(self.candidate, values)
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIn("finite, unmasked predictions found outside the template footprint", result["errors"])

    def test_nan_inside_footprint_fails(self):
        values = np.where(self.footprint, 0.4, np.nan)
        values[1, 1] = np.nan
        self._write(self.candidate, values)
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIn("non-finite prediction inside the template footprint", result["errors"])

    def test_wrong_crs_fails(self):
        values = np.where(self.footprint, 0.4, np.nan)
        self._write(self.candidate, values, crs="EPSG:32610")
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIn("crs_match failed", result["errors"])

    def test_nodata_zero_inside_footprint_fails(self):
        values = np.where(self.footprint, 0.4, np.nan)
        values[1, 1] = 0.0
        self._write(self.candidate, values, nodata=0.0)
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIn("masked or nodata prediction inside the template footprint", result["errors"])

    def test_wrong_grid_shape_fails_closed(self):
        values = np.full((4, 4), 0.4, dtype="float32")
        self._write(self.candidate, values, width=4)
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["footprint_pixels"])
        self.assertIn("width_match failed", result["errors"])


if __name__ == "__main__":
    unittest.main()
