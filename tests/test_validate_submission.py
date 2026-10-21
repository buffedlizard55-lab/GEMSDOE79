import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine

from scripts.validate_submission import compare_registry, validate


class SubmissionValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.template = self.root / "sample_submission.tif"
        self.candidate = self.root / "candidate.tif"
        self.transform = Affine(100, 0, 500000, 0, -100, 4300000)
        self.footprint = np.zeros((4, 5), dtype=bool)
        self.footprint[1:3, 1:4] = True
        self._write(self.template, np.where(self.footprint, 0.0, np.nan))

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, path, values, *, width=5, crs="EPSG:32611", dtype="float32",
               nodata=np.nan, transform=None):
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=width,
            height=4,
            count=1,
            dtype=dtype,
            crs=crs,
            transform=transform or self.transform,
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
        self.assertEqual(len(result["sha256"]), 64)
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

    def test_non_100m_reference_grid_fails(self):
        wrong_transform = Affine(50, 0, 500000, 0, -50, 4300000)
        wrong_template = self.root / "wrong-resolution-template.tif"
        values = np.where(self.footprint, 0.0, np.nan)
        self._write(wrong_template, values, transform=wrong_transform)
        candidate_values = np.where(self.footprint, 0.4, np.nan)
        self._write(self.candidate, candidate_values, transform=wrong_transform)
        result = validate(self.candidate, wrong_template)
        self.assertFalse(result["ok"])
        self.assertIn("template_north_up_100m failed", result["errors"])

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

    def test_negative_nodata_sentinel_outside_fails_range_guard(self):
        sentinel = np.float32(-3.4028235e38)
        values = np.full((4, 5), sentinel, dtype="float32")
        values[self.footprint] = 0.4
        self._write(self.candidate, values, nodata=float(sentinel))
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIn("raw stored finite value outside [0, 1] (including possible nodata sentinel)",
                      result["errors"])

    def test_registry_similarity_flags_exact_copy(self):
        values = np.where(self.footprint, 0.4, np.nan)
        self._write(self.candidate, values)
        registry = self.root / "registry.tif"
        self._write(registry, values)
        result = compare_registry(self.candidate, self.template, [registry])
        self.assertEqual(result["status"], "duplicate")
        self.assertTrue(result["comparisons"][0]["duplicate_threshold_exceeded"])
        self.assertIsNone(result["comparisons"][0]["rank_correlation"])
        self.assertTrue(result["comparisons"][0]["identical_decoded_predictions"])

    def test_missing_registry_is_unverified(self):
        result = compare_registry(self.candidate, self.template, [])
        self.assertEqual(result["status"], "unverified")

    def test_registry_file_missing_blocks_similarity_gate(self):
        self._write(self.candidate, np.where(self.footprint, 0.4, np.nan))
        result = compare_registry(self.candidate, self.template,
                                  [self.root / "missing-registry.tif"])
        self.assertEqual(result["status"], "incomplete")

    def test_wrong_grid_shape_fails_closed(self):
        values = np.full((4, 4), 0.4, dtype="float32")
        self._write(self.candidate, values, width=4)
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["footprint_pixels"])
        self.assertIn("width_match failed", result["errors"])


    def test_zero_exterior_is_valid_abstention(self):
        self._write(self.candidate, np.where(self.footprint, 0.4, 0.0))
        result = validate(self.candidate, self.template)
        self.assertTrue(result["ok"], result["errors"])

    def test_flipped_reference_is_not_north_up(self):
        wrong = Affine(-100, 0, 500000, 0, 100, 4300000)
        values = np.where(self.footprint, 0.4, np.nan)
        self._write(self.template, values, transform=wrong)
        self._write(self.candidate, values, transform=wrong)
        result = validate(self.candidate, self.template)
        self.assertFalse(result["ok"])
        self.assertIn("template_north_up_100m failed", result["errors"])


if __name__ == "__main__":
    unittest.main()
