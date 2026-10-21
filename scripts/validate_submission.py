#!/usr/bin/env python3
"""Audit a candidate GeoTIFF against the official grid contract and registry rasters.

This is a format/duplicate gate only; it neither creates predictions nor validates geology.
Requires rasterio, numpy, and scipy. All spatial comparisons require exact grid alignment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path,
                        help="Official sample/training GeoTIFF defining grid metadata")
    parser.add_argument("--footprint", required=True, type=Path,
                        help="Single-band raster whose valid-data mask defines scored footprint")
    parser.add_argument("--registry", action="append", default=[], type=Path,
                        help="Aligned registry raster; repeat for every known registry raster")
    parser.add_argument("--report", type=Path, help="Write machine-readable JSON report")
    args = parser.parse_args()

    try:
        import numpy as np
        import rasterio
        from scipy.ndimage import distance_transform_edt
        from scipy.stats import spearmanr
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Install rasterio, numpy, scipy.", file=sys.stderr)
        return 2

    report: dict[str, Any] = {
        "submission": str(args.submission),
        "sha256": None,
        "format": {"valid": False},
        "registry_comparison": {"status": "unverified", "comparisons": []},
        "promotion_gate": "blocked",
        "errors": [],
        "warnings": [],
    }

    try:
        if not args.submission.is_file():
            raise FileNotFoundError(f"Submission not found: {args.submission}")
        if not args.reference.is_file():
            raise FileNotFoundError(f"Reference not found: {args.reference}")
        if not args.footprint.is_file():
            raise FileNotFoundError(f"Footprint not found: {args.footprint}")
        report["sha256"] = sha256(args.submission)

        with rasterio.open(args.reference) as reference, \
                rasterio.open(args.footprint) as footprint_ds, \
                rasterio.open(args.submission) as candidate:
            expected = {
                "crs": reference.crs,
                "width": reference.width,
                "height": reference.height,
                "transform": reference.transform,
            }
            reference_epsg_ok = (reference.crs is not None and
                                 reference.crs.to_epsg() == 32611)
            reference_resolution_ok = (
                math.isclose(abs(reference.transform.a), 100.0, abs_tol=1e-6) and
                math.isclose(abs(reference.transform.e), 100.0, abs_tol=1e-6) and
                math.isclose(reference.transform.b, 0.0, abs_tol=1e-9) and
                math.isclose(reference.transform.d, 0.0, abs_tol=1e-9))
            if not reference_epsg_ok:
                report["errors"].append("Reference CRS is not EPSG:32611")
            if not reference_resolution_ok:
                report["errors"].append("Reference pixel grid is not north-up 100 m")
            if footprint_ds.count != 1:
                report["errors"].append("Footprint must contain exactly one band")
            if (footprint_ds.crs != expected["crs"] or
                    footprint_ds.width != expected["width"] or
                    footprint_ds.height != expected["height"] or
                    footprint_ds.transform != expected["transform"]):
                report["errors"].append("Footprint grid does not exactly match reference grid")
            if candidate.count != 1:
                report["errors"].append("Submission must contain exactly one band")
            if candidate.dtypes != ("float32",):
                report["errors"].append(f"Submission dtype must be float32; got {candidate.dtypes}")
            checks = {
                "reference_epsg_32611": reference_epsg_ok,
                "reference_pixel_size_100m": reference_resolution_ok,
                "crs_matches": candidate.crs == expected["crs"],
                "shape_matches": (candidate.width, candidate.height) ==
                                (expected["width"], expected["height"]),
                "transform_matches": candidate.transform == expected["transform"],
            }
            for label, passed in checks.items():
                if not passed:
                    report["errors"].append(f"Submission {label.replace('_', ' ')} reference")

            if report["errors"]:
                # Do not read an incompatible candidate grid for value checks.
                report["format"].update(checks)
            else:
                values = candidate.read(1)
                candidate_mask = candidate.read_masks(1) != 0
                footprint_mask = footprint_ds.read_masks(1) != 0
                inside = footprint_mask
                outside = ~inside
                inside_valid = candidate_mask & np.isfinite(values)
                outside_null = (~candidate_mask) | np.isnan(values)
                finite_inside = values[inside]
                range_ok = bool(np.all(np.isfinite(finite_inside)) and
                                np.all((finite_inside >= 0.0) & (finite_inside <= 1.0)))
                # The portal may inspect raw stored samples rather than honor a
                # numeric nodata sentinel. Require every raw finite value, including
                # outside the footprint, to remain within [0,1]; NaN is permitted only
                # outside by the separate footprint check below.
                raw_range_ok = bool(np.all(np.isnan(values) |
                                           ((values >= 0.0) & (values <= 1.0))))
                nan_inside = bool(np.any(np.isnan(values[inside])))
                outside_ok = bool(np.all(outside_null[outside]))
                report["format"].update({
                    **checks,
                    "single_band": candidate.count == 1,
                    "dtype": candidate.dtypes[0],
                    "no_nan_inside_footprint": not nan_inside,
                    "all_inside_values_finite": bool(np.all(inside_valid[inside])),
                    "values_in_0_1": range_ok,
                    "every_stored_value_in_0_1_or_nan": raw_range_ok,
                    "outside_is_nodata_or_nan": outside_ok,
                    "footprint_pixels": int(inside.sum()),
                })
                for name in ("no_nan_inside_footprint", "all_inside_values_finite",
                             "values_in_0_1", "every_stored_value_in_0_1_or_nan",
                             "outside_is_nodata_or_nan"):
                    if not report["format"][name]:
                        report["errors"].append(f"Format check failed: {name}")

                comparisons = []
                duplicate = False
                for registry_path in args.registry:
                    if not registry_path.is_file():
                        report["errors"].append(f"Registry raster not found: {registry_path}")
                        continue
                    with rasterio.open(registry_path) as registry:
                        same_grid = (registry.count >= 1 and registry.crs == expected["crs"] and
                                     registry.width == expected["width"] and
                                     registry.height == expected["height"] and
                                     registry.transform == expected["transform"])
                        if not same_grid:
                            report["errors"].append(
                                f"Registry raster is not exactly aligned: {registry_path}")
                            continue
                        reg_values = registry.read(1)
                        reg_valid = (registry.read_masks(1) != 0) & np.isfinite(reg_values)
                        valid = inside & inside_valid & reg_valid
                        if not bool(valid.any()):
                            report["errors"].append(
                                f"No common valid footprint with registry: {registry_path}")
                            continue
                        candidate_rank_values = values[valid]
                        registry_rank_values = reg_values[valid]
                        candidate_constant = bool(np.all(candidate_rank_values == candidate_rank_values[0]))
                        registry_constant = bool(np.all(registry_rank_values == registry_rank_values[0]))
                        if candidate_constant or registry_constant:
                            # Spearman is undefined for a constant input; identical constant
                            # rasters are still exact duplicates and must not evade the gate.
                            rho = (1.0 if candidate_constant and registry_constant and
                                   np.array_equal(candidate_rank_values, registry_rank_values)
                                   else None)
                        else:
                            rho_raw = spearmanr(candidate_rank_values, registry_rank_values).statistic
                            rho = float(rho_raw) if math.isfinite(float(rho_raw)) else None
                        reg_dots = inside & reg_valid & (reg_values > 0)
                        pred_dots = inside & inside_valid & (values > 0)
                        dot_count = int(pred_dots.sum())
                        if dot_count and bool(reg_dots.any()):
                            distance = distance_transform_edt(~reg_dots)
                            overlap_fraction = float(np.count_nonzero(
                                pred_dots & (distance <= 3.0)) / dot_count)
                        elif dot_count == 0:
                            overlap_fraction = 0.0
                        else:
                            overlap_fraction = 0.0
                        this_duplicate = ((rho is not None and rho > 0.90) or
                                          overlap_fraction > 0.70)
                        duplicate = duplicate or this_duplicate
                        comparisons.append({
                            "registry": str(registry_path),
                            "registry_sha256": sha256(registry_path),
                            "rank_correlation": rho,
                            "candidate_dots": dot_count,
                            "registry_dots": int(reg_dots.sum()),
                            "candidate_dot_fraction_within_3px": overlap_fraction,
                            "duplicate_threshold_exceeded": this_duplicate,
                        })
                report["registry_comparison"]["comparisons"] = comparisons
                if args.registry and len(comparisons) == len(args.registry):
                    report["registry_comparison"]["status"] = (
                        "duplicate" if duplicate else "passed")
                elif args.registry:
                    report["registry_comparison"]["status"] = "incomplete"
                else:
                    report["warnings"].append(
                        "No registry rasters supplied; duplicate gate is unverified")

                report["format"]["valid"] = not report["errors"]
                if report["format"]["valid"] and report["registry_comparison"]["status"] == "passed":
                    report["promotion_gate"] = "format_and_similarity_passed_only"
                elif report["format"]["valid"] and report["registry_comparison"]["status"] == "duplicate":
                    report["promotion_gate"] = "blocked_duplicate"
                else:
                    report["promotion_gate"] = "blocked_incomplete_or_format_failure"

    except Exception as exc:  # capture filesystem/GeoTIFF errors in the audit record
        report["errors"].append(f"{type(exc).__name__}: {exc}")

    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["format"].get("valid") and \
        report["registry_comparison"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
