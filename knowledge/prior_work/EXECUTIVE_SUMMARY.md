> **HISTORICAL PREFLIGHT SNAPSHOT — SUPERSEDED.** Imported from origin/main `a88c9ab` during concurrent integration on 2026-10-21. Its missing-data/no-artifact statements describe that earlier checkout, not the current project. Read the current root README and negative run card. It does not authorize switching the fixed E1 lane.

# Executive summary: making a GEMS competition submission

## Current status — STOP: no file is ready

**There is no TIF download here. Do not submit any artifact from this repository.** No competition data, sample grid, trained model, holdout evaluator, shared writer, registry rasters, or scored candidate was present in the checkout at review time. Creating a plausible-looking file without those inputs would risk an invalid upload and would not be a scientific prediction.

The required data are gated behind the DrivenData data page. The prior claim in the prompt that the training data can be downloaded without login is not supported here; the official competition data page is the source of truth and authentication is unavailable in this environment. [Competition data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)

## Steps that will make a file eligible for a submit button

1. Download the official `training_features.tif`, `labels.tif`, `sample_submission.tif`, and related files from the [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) into local `data/`; never commit restricted/large source data.
2. Reuse the canonical feature cache, holdout evaluator, and submission writer. Use whole-segment spatial holdouts with a buffer, train catalogue-based features only from visible faults, pixel-exactly mask visible fault labels, and evaluate with the official distance-weighted Tversky metric (alpha 0.2, beta 0.8, 300 m triangular kernel).
3. Run individual-feature leakage canaries first. Any AUC above 0.90 must be treated as leakage until disproven. Compare the final candidate with registry rasters and stop on the duplicate thresholds specified in [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md).
4. Require the candidate to beat the current holdout best before using a competition slot. Preserve the evaluator version, withheld-positive count, paired 95% confidence interval, file SHA-256, validator JSON report, a unique output filename, and a note (<=140 characters).
5. Write a single-band float32 GeoTIFF on the exact official grid. The official rules state EPSG:32611, 100 m resolution, same bounds, values in `[0,1]`, and null/NaN outside the bounds. Independently compare CRS, dimensions, transform, mask/footprint, and pixel values to `sample_submission.tif` before an “OK TO SUBMIT” download is exposed.
6. On DrivenData's submission page, choose the validated uniquely named `.tif` and paste the short method note into **Note (optional)**. Review and retain the portal receipt; only that receipt makes a result **ORGANIZER-CONFIRMED**.

## Competition TIF format and rejection prevention

The competition accepts a single-band GeoTIFF (or a ZIP containing one GeoTIFF) with the expected grid and float32 probabilities/confidences in `[0,1]`. A common reason for the error `Predicted values must be in range [0, 1]` is an out-of-range prediction value; a nodata sentinel encoded as a large negative float can also appear as an invalid numeric value if mishandled. Do not assume the error's cause: inspect values and nodata/mask metadata from the actual file. The local validator in `scripts/validate_submission.py` checks pixel values and grid compatibility; it is a format preflight, not a submission receipt.

Run the repository's format and registry preflight only after creating a genuine candidate and obtaining the official sample grid:

```bash
.venv/bin/python scripts/validate_submission.py candidate.tif \\
  --template data/sample_submission.tif \\
  --registry path/to/registry-raster.tif \\
  --report reports/candidate-audit.json
```

Repeat `--registry` for every available registry raster. A missing registry set leaves the duplicate gate unverified; even a format/similarity pass does not establish holdout performance or organizer acceptance.

Official references:

- [Problem description, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/)
- [Official sample data download page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)

<a id="score-check"></a>

## Why the cited score attribution needs correction

The GEMSDOE32 report describes `h33-h33-2-b2-...-zeros.tif` as an **unscored candidate**, and explicitly says no organizer score exists for that artifact. Its stated strategy prunes predicted dots near the known catalogue from a prior candidate; that could plausibly reduce redundant predictions of already-mapped faults while retaining nearby structure, but it can also discard true positives. The report's projections and internal proxy-holdout/model analyses are not competition scores, so they cannot explain the claimed score attribution. I could not verify that attribution from the linked page; a submission-page receipt would be needed. See [GEMSDOE32 report](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html). Separately, the live official leaderboard fetched on 2026-10-21 UTC has a leading public entry newer than the figures quoted in the prompt. Because the page is not a submission receipt, its displayed value is not included here as a qualifying score. [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)

## Present limitation

Without the authorized competition grid and labels, I cannot verify any candidate against a spatially blocked holdout, reproduce the claimed score, establish the competition-specific grid transform, generate a valid probability surface, or produce an “OK TO SUBMIT” download. No private authentication or tokens should be placed in this repository. See the [project brief](PROJECT_BRIEF.md) for the ranked hypotheses and current gates.
