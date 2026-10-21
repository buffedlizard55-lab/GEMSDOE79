---
title: Submission guide
---

# Competition submission guide

## Current answer: there is no file to download

**Do not submit a file from this repository yet.** This checkout has no input rasters, shared prediction writer, completed holdout result, or validated candidate TIFF. The landing page intentionally does not offer an empty/borrowed TIFF. A candidate must first beat the incumbent on the project holdout, pass the duplicate and format gates, and be approved by a separate selector. This repository cannot access the organizer's private test labels or submit to DrivenData on your behalf.

## Official competition file contract

Per the [official task page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), submit a single-band GeoTIFF containing predictions for the region:

- CRS: projected UTM zone 11N, EPSG:32611;
- pixel size: 100 m;
- same bounds, shape, and geotransform as the training raster;
- one 32-bit floating point band;
- predictions between 0 and 1 inclusive;
- pixels outside the bounds null/NaN.

The competition data page requires an authenticated account. It redirects unauthenticated requests to login: [data download](https://www.drivendata.org/competitions/306/competition-doe-gems/data/). The challenge provides `training_features.tif`, fault label data and a sample submission; use the actual downloaded sample/training raster as the metadata reference. Do not hard-code dimensions or copy a third-party prediction as a model output.

## Automatic checks before a real submission

From an environment with `rasterio`, `numpy`, and `scipy` installed:

```bash
python scripts/validate_submission.py \
  --submission path/to/candidate.tif \
  --reference data/sample_submission.tif \
  --footprint data/sample_submission.tif \
  --registry path/to/registry_surface.tif \
  --report reports/validation.json
```

`--registry` may be repeated for every available registry raster. The validator checks that the reference is EPSG:32611 at north-up 100 m, one float32 band, exact CRS/shape/transform against the reference, finite [0,1] values within the footprint, null/NaN outside, and requires every raw finite sample—including outside the footprint—to remain in [0,1] to guard against a portal rejecting a numeric nodata sentinel. It also checks rank correlation and the share of nonzero candidate pixels within 3 pixels of each registry's nonzero pixels. Correlation >0.90 or overlap >0.70 blocks validation. The registry checks are not a substitute for the experiment's pre-placement/final-placement gate; registry inputs must be complete, identified, and hashed. Without registry rasters, the report records duplicate status as unverified.

This validator is only a format/similarity gate. It does not generate a prediction, verify geology, score the official hidden set, replace the shared holdout evaluator, or prove that a submission improves the public/private leaderboard. **No file is marked ready unless the scientific holdout gate is separately passed.**

## Naming and note

On eventual approval, use a unique run identifier plus a short method label and UTC date, e.g. `gems79-cand1-cond-grav-strain-YYYYMMDD-HHMM-<short-hash>`. This example is a naming convention only, not an existing submission. Keep the portal's note at or below 140 characters and include the method/holdout reference, without calling a projection a score. Do not choose or promote a slot from this page; check the live submission page and weekly cap at selection time.

## Manual portal steps (when a valid file exists)

1. Open the competition's New submission page while signed in.
2. Choose the single validated `.tif` file. The New submission form text quoted in the project brief also permits a `.zip` containing exactly one GeoTIFF; recheck the live portal instructions before upload.
3. Enter the approved unique name and short note in the portal fields if requested.
4. Submit and preserve the organizer receipt. Only the receipt makes an online score **ORGANIZER-CONFIRMED**.

A fully unattended portal submission is intentionally not implemented: the account requires authentication, and selecting a scarce weekly slot must remain a separately governed action.
