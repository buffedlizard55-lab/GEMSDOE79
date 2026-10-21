# GEMSDOE79

> **Read first on every project session:** [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md). It records the research question, hard validation gates, current evidence, and the no-slot-without-holdout rule. Do not treat old scores or predictions as verified facts.

## Current state — no submission is ready

**There is no downloadable submission GeoTIFF in this repository.** The checkout contains no competition data, no feature stack, no sample submission grid, no cached feature stack, no `evaluate_holdout.py`, no `submission_writer.py`, and no registry rasters. A legally formatted, scientifically meaningful submission cannot be generated or validated without the competition raster inputs. This project deliberately does not create a fabricated/zero-fill TIF and does not copy an earlier team's artifact.

**Do not download or submit any file from this repository as a competition entry.** The status changes only when the pipeline creates a unique raster from authorized inputs, the validator passes against the official sample grid, the spatially blocked holdout beats the preregistered baseline, and the run card is complete.

### Start here

- [Executive summary and submission guide](docs/EXECUTIVE_SUMMARY.md)
- [Project brief, evidence, candidate hypotheses, and stop rules](docs/PROJECT_BRIEF.md)
- [Current blocked run card (JSON)](docs/run-card.json)
- [Official competition problem and submission specification](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Official USGS GeoDAWN data release](https://doi.org/10.5066/P93LGLVQ)

### Local format preflight

After obtaining the competition's `sample_submission.tif` through an authorized account, validate a candidate with:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/validate_submission.py path/to/candidate.tif --template data/sample_submission.tif --registry path/to/registry.tif
.venv/bin/python -m unittest discover -s tests -v
```

The tool fails closed if the reference grid is not EPSG:32611 at 100 m, if CRS/dimensions/transform/band count/float32 type differ, if an in-footprint prediction is non-finite or outside `[0,1]`, or if finite predictions occur outside the template footprint. It rejects raw finite nodata sentinels outside `[0,1]` to guard against portal range-check behavior. With `--registry`, it also reports Spearman rank-correlation and the fraction of predicted dots within 3 pixels for each registry; thresholds above 0.90 correlation or 0.70 overlap block promotion. Without all registry rasters, similarity remains unverified. Passing the format preflight is **not** evidence of model quality or organizer acceptance.

## Project values

- **Maximize P(Win):** conserve submission slots; test spatially blocked, matched-budget candidates before considering a slot.
- **Own the Outcome:** publish uncertainty, leakage checks, limitations, negative results, reproducible artifacts, and source links.
- **No hallucinations:** distinguish official evaluator output from internal holdout results, projections, and user-provided reports.
