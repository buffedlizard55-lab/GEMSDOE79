#!/usr/bin/env python3
"""Fail-closed GEMS submission GeoTIFF preflight against the official sample grid."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


def _nodata_mask(values: np.ndarray, nodata: float | int | None) -> np.ndarray:
    """Return True where values encode the dataset's nodata sentinel."""
    if nodata is None:
        return np.zeros(values.shape, dtype=bool)
    try:
        if math.isnan(float(nodata)):
            return np.isnan(values)
    except (TypeError, ValueError):
        pass
    return values == nodata


def _grid_transform_matches(left: Any, right: Any, tolerance: float = 1e-9) -> bool:
    return all(abs(float(a) - float(b)) <= tolerance for a, b in zip(left, right))


def validate(submission_path: Path, template_path: Path) -> dict[str, Any]:
    """Validate a candidate against a supplied official sample/template GeoTIFF.

    The template's valid-data mask defines the in-footprint cells. On those cells,
    candidate values must be finite and in [0, 1]. Off-footprint values must be
    masked, non-finite, or the candidate's declared nodata sentinel.
    """
    errors: list[str] = []
    with rasterio.open(template_path) as template, rasterio.open(submission_path) as pred:
        grid_checks = {
            "crs_match": pred.crs == template.crs and template.crs is not None,
            "width_match": pred.width == template.width,
            "height_match": pred.height == template.height,
            "transform_match": _grid_transform_matches(pred.transform, template.transform),
            "single_band": pred.count == 1,
            "float32": pred.dtypes == ("float32",),
        }
        for check, passed in grid_checks.items():
            if not passed:
                errors.append(f"{check} failed")

        # An incompatible shape or band count cannot be read against the sample mask safely.
        if pred.width != template.width or pred.height != template.height or pred.count != 1:
            return {
                "ok": False,
                "submission": str(submission_path),
                "template": str(template_path),
                "checks": grid_checks,
                "errors": errors,
                "footprint_pixels": None,
                "valid_prediction_pixels": None,
                "prediction_min": None,
                "prediction_max": None,
            }

        template_values = template.read(1, masked=False)
        footprint = (template.read_masks(1) > 0) & np.isfinite(template_values)
        footprint &= ~_nodata_mask(template_values, template.nodata)
        values = pred.read(1, masked=False)
        output_mask = pred.read_masks(1) > 0
        output_nodata = _nodata_mask(values, pred.nodata)

        if not np.any(footprint):
            errors.append("template has no valid footprint pixels; cannot define submission domain")
        else:
            inside_finite = np.isfinite(values[footprint])
            if not np.all(inside_finite):
                errors.append("non-finite prediction inside the template footprint")
            inside_valid = output_mask[footprint] & ~output_nodata[footprint]
            if not np.all(inside_valid):
                errors.append("masked or nodata prediction inside the template footprint")
            inside_values = values[footprint]
            finite_values = inside_values[inside_finite]
            if np.any((finite_values < 0.0) | (finite_values > 1.0)):
                errors.append("prediction outside [0, 1] inside the template footprint")
            outside = ~footprint
            outside_valid = output_mask[outside] & np.isfinite(values[outside]) & ~output_nodata[outside]
            if np.any(outside_valid):
                errors.append("finite, unmasked predictions found outside the template footprint")

        valid_inside = footprint & output_mask & np.isfinite(values) & ~output_nodata
        if np.any(valid_inside):
            vmin = float(np.min(values[valid_inside]))
            vmax = float(np.max(values[valid_inside]))
        else:
            vmin = vmax = None

        return {
            "ok": not errors,
            "submission": str(submission_path),
            "template": str(template_path),
            "checks": grid_checks,
            "errors": errors,
            "footprint_pixels": int(np.count_nonzero(footprint)),
            "valid_prediction_pixels": int(np.count_nonzero(valid_inside)),
            "prediction_min": vmin,
            "prediction_max": vmax,
            "crs": pred.crs.to_string() if pred.crs else None,
            "shape": [int(pred.height), int(pred.width)],
            "transform": list(pred.transform),
            "dtype": pred.dtypes[0] if pred.count else None,
            "nodata": pred.nodata,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path, help="candidate single-band GeoTIFF")
    parser.add_argument("--template", required=True, type=Path,
                        help="official sample_submission.tif or equivalent official grid/mask")
    args = parser.parse_args()
    for path in (args.submission, args.template):
        if not path.is_file():
            print(json.dumps({"ok": False, "errors": [f"file not found: {path}"]}, indent=2))
            return 2
    try:
        report = validate(args.submission, args.template)
    except rasterio.errors.RasterioError as exc:
        print(json.dumps({"ok": False, "errors": [f"GeoTIFF read error: {exc}"]}, indent=2))
        return 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
