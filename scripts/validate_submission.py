#!/usr/bin/env python3
"""Fail-closed GeoTIFF format and registry-similarity preflight for GEMS.

Format validity is not evidence of model quality or organizer acceptance. Registry
comparison requires every relevant registry raster to be supplied explicitly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(submission_path: Path, template_path: Path) -> dict[str, Any]:
    """Validate a candidate against an official sample/template GeoTIFF.

    The template's valid-data mask defines the in-footprint cells. Predictions
    inside must be finite and in [0,1]. Outside cells must be null/masked/NaN;
    every raw finite sample anywhere in the TIFF must still be in [0,1] so that
    a numeric negative nodata sentinel cannot trigger the portal range error.
    """
    errors: list[str] = []
    with rasterio.open(template_path) as template, rasterio.open(submission_path) as pred:
        template_epsg = template.crs.to_epsg() if template.crs else None
        template_transform = template.transform
        template_100m = (
            math.isclose(abs(template_transform.a), 100.0, abs_tol=1e-6)
            and math.isclose(abs(template_transform.e), 100.0, abs_tol=1e-6)
            and math.isclose(template_transform.b, 0.0, abs_tol=1e-9)
            and math.isclose(template_transform.d, 0.0, abs_tol=1e-9)
        )
        grid_checks = {
            "template_epsg_32611": template_epsg == 32611,
            "template_north_up_100m": template_100m,
            "crs_match": pred.crs == template.crs and template.crs is not None,
            "width_match": pred.width == template.width,
            "height_match": pred.height == template.height,
            "transform_match": _grid_transform_matches(pred.transform, template_transform),
            "single_band": pred.count == 1,
            "float32": pred.dtypes == ("float32",),
        }
        for check, passed in grid_checks.items():
            if not passed:
                errors.append(f"{check} failed")

        # An incompatible shape or band count cannot safely be compared with the template mask.
        if pred.width != template.width or pred.height != template.height or pred.count != 1:
            return {
                "ok": False,
                "submission": str(submission_path),
                "sha256": _sha256(submission_path),
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
            finite_inside = inside_values[inside_finite]
            if np.any((finite_inside < 0.0) | (finite_inside > 1.0)):
                errors.append("prediction outside [0, 1] inside the template footprint")
            outside = ~footprint
            outside_valid = output_mask[outside] & np.isfinite(values[outside]) & ~output_nodata[outside]
            if np.any(outside_valid):
                errors.append("finite, unmasked predictions found outside the template footprint")

        raw_values_ok = bool(np.all(np.isnan(values) | ((values >= 0.0) & (values <= 1.0))))
        no_nan_inside = bool(np.any(footprint) and np.all(~np.isnan(values[footprint])))
        inside_for_report = values[footprint]
        values_in_range_inside = bool(
            np.any(footprint) and np.all(np.isfinite(inside_for_report)) and
            np.all((inside_for_report >= 0.0) & (inside_for_report <= 1.0)))
        crs_shape_transform_match = bool(
            grid_checks["crs_match"] and grid_checks["width_match"] and
            grid_checks["height_match"] and grid_checks["transform_match"])
        if not raw_values_ok:
            errors.append("raw stored finite value outside [0, 1] (including possible nodata sentinel)")

        valid_inside = footprint & output_mask & np.isfinite(values) & ~output_nodata
        if np.any(valid_inside):
            vmin = float(np.min(values[valid_inside]))
            vmax = float(np.max(values[valid_inside]))
        else:
            vmin = vmax = None

        return {
            "ok": not errors,
            "submission": str(submission_path),
            "sha256": _sha256(submission_path),
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
            "all_raw_values_in_0_1_or_nan": raw_values_ok,
            "no_nan_inside_footprint": no_nan_inside,
            "values_in_0_1": values_in_range_inside,
            "crs_shape_transform_match": crs_shape_transform_match,
        }


def compare_registry(submission_path: Path, template_path: Path,
                     registry_paths: Sequence[Path]) -> dict[str, Any]:
    """Compare candidate raster rank-correlation and 3-pixel dot overlap to registries.

    Every raster must already be exactly aligned to the official template. Positive
    values are treated as dots. Correlation is Spearman's rho over shared valid
    footprint cells. A missing registry list returns `unverified`, never `passed`.
    """
    if not registry_paths:
        return {"status": "unverified", "comparisons": [],
                "reason": "No registry rasters supplied; duplication gate is unverified."}
    try:
        from scipy.ndimage import distance_transform_edt
        from scipy.stats import spearmanr
    except ImportError as exc:
        return {"status": "error", "comparisons": [],
                "reason": f"Registry comparison needs scipy: {exc}"}

    comparisons: list[dict[str, Any]] = []
    any_duplicate = False
    any_error = False
    with rasterio.open(template_path) as template, rasterio.open(submission_path) as pred:
        if pred.count != 1 or pred.shape != template.shape:
            return {"status": "error", "comparisons": [],
                    "reason": "Candidate grid cannot be compared to registry."}
        template_values = template.read(1, masked=False)
        footprint = ((template.read_masks(1) > 0) & np.isfinite(template_values)
                     & ~_nodata_mask(template_values, template.nodata))
        candidate = pred.read(1, masked=False)
        candidate_valid = ((pred.read_masks(1) > 0) & np.isfinite(candidate)
                           & ~_nodata_mask(candidate, pred.nodata) & footprint)
        candidate_dots = candidate_valid & (candidate > 0.0)

        for registry_path in registry_paths:
            if not registry_path.is_file():
                comparisons.append({"registry": str(registry_path), "status": "missing"})
                any_error = True
                continue
            try:
                with rasterio.open(registry_path) as registry:
                    aligned = (registry.count >= 1 and registry.crs == template.crs
                               and registry.shape == template.shape
                               and _grid_transform_matches(registry.transform, template.transform))
                    if not aligned:
                        comparisons.append({"registry": str(registry_path),
                                            "status": "grid_mismatch"})
                        any_error = True
                        continue
                    reference = registry.read(1, masked=False)
                    reference_valid = ((registry.read_masks(1) > 0) & np.isfinite(reference)
                                       & ~_nodata_mask(reference, registry.nodata) & footprint)
                    common = candidate_valid & reference_valid
                    if not np.any(common):
                        comparisons.append({"registry": str(registry_path),
                                            "status": "no_common_valid_pixels"})
                        any_error = True
                        continue
                    left, right = candidate[common], reference[common]
                    left_constant = bool(np.all(left == left[0]))
                    right_constant = bool(np.all(right == right[0]))
                    if left_constant or right_constant:
                        rho = (1.0 if left_constant and right_constant and
                               np.array_equal(left, right) else None)
                    else:
                        rho_result = spearmanr(left, right).statistic
                        rho = float(rho_result) if math.isfinite(float(rho_result)) else None
                    registry_dots = reference_valid & (reference > 0.0)
                    dot_count = int(candidate_dots.sum())
                    if dot_count and np.any(registry_dots):
                        distances = distance_transform_edt(~registry_dots)
                        overlap = float(np.count_nonzero(candidate_dots & (distances <= 3.0))
                                        / dot_count)
                    else:
                        overlap = 0.0
                    duplicate = ((rho is not None and rho > 0.90) or overlap > 0.70)
                    any_duplicate |= duplicate
                    comparisons.append({
                        "registry": str(registry_path),
                        "registry_sha256": _sha256(registry_path),
                        "status": "duplicate" if duplicate else "compared",
                        "rank_correlation": rho,
                        "candidate_dots": dot_count,
                        "registry_dots": int(registry_dots.sum()),
                        "candidate_dot_fraction_within_3px": overlap,
                        "duplicate_threshold_exceeded": duplicate,
                        "common_valid_pixels": int(common.sum()),
                    })
            except rasterio.errors.RasterioError as exc:
                comparisons.append({"registry": str(registry_path), "status": "read_error",
                                    "reason": str(exc)})
                any_error = True

    status = "duplicate" if any_duplicate else ("incomplete" if any_error else "passed")
    return {"status": status, "comparisons": comparisons}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path, help="candidate single-band GeoTIFF")
    parser.add_argument("--template", required=True, type=Path,
                        help="official sample_submission.tif or equivalent official grid/mask")
    parser.add_argument("--registry", action="append", default=[], type=Path,
                        help="aligned registry raster; repeat for every available registry")
    parser.add_argument("--report", type=Path, help="write JSON audit report")
    args = parser.parse_args()
    for path in (args.submission, args.template, *args.registry):
        if not path.is_file():
            print(json.dumps({"ok": False, "errors": [f"file not found: {path}"]}, indent=2))
            return 2
    try:
        report = validate(args.submission, args.template)
        registry_report = compare_registry(args.submission, args.template, args.registry)
    except rasterio.errors.RasterioError as exc:
        print(json.dumps({"ok": False, "errors": [f"GeoTIFF read error: {exc}"]}, indent=2))
        return 2
    report["registry_comparison"] = registry_report
    report["promotion_gate"] = (
        "blocked_format_failure" if not report["ok"] else
        "blocked_duplicate" if registry_report["status"] == "duplicate" else
        "format_and_similarity_passed_only" if registry_report["status"] == "passed" else
        "blocked_similarity_unverified_or_incomplete"
    )
    rendered = json.dumps(report, indent=2, allow_nan=False)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["ok"] and registry_report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
