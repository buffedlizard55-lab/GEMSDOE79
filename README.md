# GEMSDOE79 — evidence-first GEMS Prize research

> **Submission status: NOT READY — do not download or submit a TIFF from this repository.**
> This checkout contains no competition rasters, no cached feature stack, no segment-holdout evaluator, and no submission writer. Therefore there is no validated candidate raster here. The website does not offer a placeholder or copied submission as if it were a usable deliverable.

This README is the standing project brief. Read it before every project change; update it when verified evidence changes.

## Mission and operating rules

Build an auditable, automated research and submission workflow for the DOE Geologic Enhanced Mapping System (GEMS) Prize. The target is accurate identification of fault traces beyond the incomplete USGS/INGENIOUS catalogue, with scientifically defensible discoveries and strong competition performance. A legal one-band GeoTIFF should eventually be one obvious download at the top of the project site, accompanied by a unique submission name and a note of no more than 140 characters.

**Core values:**

- **Maximize P(Win):** use evidence and risk-aware experiments; a weekly submission slot is not a lottery ticket.
- **Own the Outcome:** identify, document, and fix defects end to end; do not claim success when prerequisites are absent.

**Research integrity / parallel-run protocol:**

1. Work in one clearly stated method lane. Before placement and again on final dots, compare candidate raster rank-correlation and 3-pixel dot overlap to every available registry raster. If any correlation is above 0.90 or more than 70% of candidate dots fall within 3 pixels of a registry raster's dots, flag duplication and stop. Never claim a check ran when the registry rasters are unavailable.
2. Reuse the common cached feature stack, shared `evaluate_holdout.py`, and shared `submission_writer.py`; repair shared tools rather than maintaining private forks. Holdout is hide-and-recover: withhold complete fault segments with a buffer; derive catalogue-dependent features only from visible segments; mask visible fault pixels exactly; score pooled DTI using alpha 0.2, beta 0.8, and the 300 m triangular kernel. Test each feature alone first; AUC > 0.90 is a leakage warning until explained.
3. Label every score as either **HOLDOUT-DTI** (evaluator version, withheld-positive count, and 95% CI) or **ORGANIZER-CONFIRMED** (copied from a submission receipt). A projection is not a score.
4. End experiments with the prescribed JSON run card: hypothesis, mechanism, named non-fault mimic, holdout result and CI, registry similarity, raster SHA-256, format-validator result, submission name/note, and promote/negative verdict. Negative findings are useful deliverables.
5. Stop after three experiments or two hours. Do not select a real submission; promotion is a separate selector step subject to the live weekly cap.

**No hallucinations:** use official sources for factual claims, preserve direct source links, distinguish verified facts from user-supplied history and hypotheses, record limitations, and do not fabricate data, scores, receipts, validation, or raster files. Do not access or infer private labels. Any external data must have a verified public source and a license permitting competition use and sharing with the sponsor.

## Competition facts verified from primary sources

- The official task is to identify geological faults in the GeoDAWN area; the known public fault data is incomplete and expert-identified additional faults form the test target. [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- Official scoring is distance-weighted Tversky with alpha 0.2, beta 0.8, and a 300 m triangular kernel. The official submission format is one float32 prediction band, values in [0,1], EPSG:32611, 100 m, same bounds as training data, null/NaN outside the bounds. [Metric and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- Live public leaderboard observation (2026-10-21, not a GEMSDOE79 score or submission receipt): the official page displayed 0.4413 at rank 1. The user's earlier 0.3195 and the user-provided GEMSDOE site numbers are historical/contextual claims. The linked GEMSDOE32 page calls H33 unscored and says no organizer score exists for its artifacts; its user-pasted 0.2778 is not verified here. [Live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- The GEMSDOE32 page describes H33 as a candidate and explicitly says no organizer score exists for its artifacts. Its reported/projection numbers must not be presented as organizer-confirmed results. [GEMSDOE32 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)
- USGS describes GeoDAWN airborne magnetic and radiometric surveys and the associated airborne lidar effort; the public data release is CC0. [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [ScienceBase release](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)

## Current blocker (checked in this checkout)

At initial review this checkout contained only a README. It still has no `data/`, no `scripts/download_competition_data.sh`, no `scripts/prepare_data.py`, no cached stack, no shared `evaluate_holdout.py`, and no shared `submission_writer.py`. The official competition data URL redirects to DrivenData login. No DrivenData session or local data files are available to this workspace. As a result, a unique TIFF cannot be responsibly generated or validated here, and no hypothesis can be holdout-tested. **Do not submit a blank, copied, or untested file.**

The next legitimate step is to place authorized competition inputs in `data/` in a future authenticated environment, then establish the shared evaluator/writer and baseline before any model experiment. See [research plan](docs/research-plan.md), [submission guide](docs/submission-guide.md), and the [project page](docs/index.html).

## Repository guide

- [`index.html`](index.html) — root GitHub Pages redirect to the project site.
- [`docs/index.html`](docs/index.html) — landing page and explicit submission-readiness status.
- [`docs/executive-summary.md`](docs/executive-summary.md) — end-to-end upload instructions and current blockers.
- [`docs/research-plan.md`](docs/research-plan.md) — ranked candidate hypotheses, mechanisms, mimics, costs, and validation gates.
- [`docs/submission-guide.md`](docs/submission-guide.md) — submission format and automatic checks.
- [`docs/sources.md`](docs/sources.md) — verified primary sources and evidence limits.
- [`reports/run-card.json`](reports/run-card.json) — current negative run card (no experiment or raster was run).
- [`scripts/validate_submission.py`](scripts/validate_submission.py) — local GeoTIFF format/similarity validator; it does not generate predictions or assert scientific validity.

## Limitations to keep visible

This environment cannot bypass the competition's login requirement or inspect organizer-private labels, and this checkout has neither competition data nor the shared pipeline requested by the project brief. GPU access is not the immediate blocker: data, a reusable evaluator/writer, and the feature stack are absent. Public leaderboard values measure only the public set and do not certify private-round or final-round performance. Geological evidence that predicts a known mapped fault is not automatically evidence of a new hidden fault.
