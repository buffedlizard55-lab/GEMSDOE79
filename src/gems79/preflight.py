"""Compatibility with concurrently merged generic-grid format preflight.

Format API retained from origin/main a88c9ab; finite zero exterior is allowed,
NaN exterior is allowed for this generic validator only. Our actual export
policy/shared writer is stricter: finite everywhere. Registry diagnostics below
use only the unchanged shared template and can never certify a complete inventory.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
from typing import Any, Sequence
import numpy as np
import rasterio
from gems57 import uniqueness as shared

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
    inside must be finite and in [0,1]. Outside cells must be null/masked/NaN or finite zero;
    every raw finite sample anywhere in the TIFF must still be in [0,1] so that
    a numeric negative nodata sentinel cannot trigger the portal range error.
    """
    errors: list[str] = []
    with rasterio.open(template_path) as template, rasterio.open(submission_path) as pred:
        template_epsg = template.crs.to_epsg() if template.crs else None
        template_transform = template.transform
        template_100m = (
            math.isclose(template_transform.a, 100.0, abs_tol=1e-6)
            and math.isclose(template_transform.e, -100.0, abs_tol=1e-6)
            and math.isclose(template_transform.b, 0.0, abs_tol=1e-9)
            and math.isclose(template_transform.d, 0.0, abs_tol=1e-9)
        )
        grid_checks = {
            "template_single_band": template.count == 1,
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
            if np.any(outside_valid & (values[outside] != 0)):
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
            "nodata": float(pred.nodata) if pred.nodata is not None and math.isfinite(float(pred.nodata)) else None,
            "nodata_is_nan": bool(pred.nodata is not None and math.isnan(float(pred.nodata))),
            "all_raw_values_in_0_1_or_nan": raw_values_ok,
            "no_nan_inside_footprint": no_nan_inside,
            "values_in_0_1": values_in_range_inside,
            "crs_shape_transform_match": crs_shape_transform_match,
        }


def compare_registry(submission_path: Path, template_path: Path,
                     registry_paths: Sequence[Path]) -> dict[str, Any]:
    """Legacy API shape, canonical shared mathematics, diagnostic-only inventory."""
    if not registry_paths:
        return {'status': 'unverified', 'comparisons': [], 'inventory_complete': False,
                'reason': 'No registry supplied; no uniqueness clearance.'}
    with rasterio.open(template_path) as template, rasterio.open(submission_path) as pred:
        if pred.count != 1 or pred.shape != template.shape:
            return {'status': 'error', 'comparisons': [], 'inventory_complete': False}
        tv = template.read(1)
        fp = (template.read_masks(1) > 0) & np.isfinite(tv) & ~_nodata_mask(tv, template.nodata)
        raw = pred.read(1)
        # Only the ignored exterior is normalized for a comparison. The original
        # file is neither altered nor repaired; format checks remain separate.
        candidate = np.where(fp, raw, 0).astype(np.float32)
        expected = (template.shape, template.crs, template.transform)
    records = [{'file': str(Path(p).resolve()), 'submission': Path(p).name} for p in registry_paths]
    result = shared.compare_array_to_registry(candidate, records, fp,
                                              file_sha256=_sha256(Path(submission_path)),
                                              include_reverse=False, expected_grid=expected)
    comparisons = []
    for row in result['rows']:
        if 'error' in row:
            comparisons.append({'registry': row['file'], 'status': 'missing_or_invalid', 'reason': row['error']})
            continue
        duplicate = any(row.get(k) for k in ('duplicate_by_rho', 'duplicate_by_overlap',
                                             'identical_bytes', 'identical_decoded_predictions'))
        comparisons.append({'registry': row['file'], 'registry_sha256': row['sha256'],
                            'status': 'duplicate' if duplicate else 'compared',
                            'rank_correlation': row['spearman_full_footprint'],
                            'candidate_dots': result['my_dots'], 'registry_dots': row['their_dots'],
                            'candidate_dot_fraction_within_3px': row['my_dots_within_3px_of_theirs'],
                            'identical_decoded_predictions': row['identical_decoded_predictions'],
                            'duplicate_threshold_exceeded': bool(duplicate)})
    status = ('duplicate' if any(r['status'] == 'duplicate' for r in comparisons) else
              'incomplete' if any(r['status'] == 'missing_or_invalid' for r in comparisons) else 'diagnostic_only')
    return {'status': status, 'comparisons': comparisons, 'inventory_complete': False,
            'submission_approval': False, 'shared_tool': 'gems57.uniqueness.compare_array_to_registry',
            'reason': 'An explicit path list has no full-inventory certificate; it can reject but cannot clear uniqueness.'}
