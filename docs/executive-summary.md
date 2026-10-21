---
title: Executive summary
---

# Executive summary

## One-click submission status

**Not ready: there is no GeoTIFF in GEMSDOE79 to download or submit.** The repository has no competition data, no cached feature stack, no shared spatial holdout evaluator, and no project submission writer. No unique candidate was generated, and no score was measured. The project will not substitute a blank raster or a third-party/sister-site submission for a verified model output.

The top of the [project page](index.html) makes this status explicit. A submission download link should only be activated after all scientific, duplicate, and file-format gates pass.

## What is the GEMS task?

DrivenData asks teams to predict geological faults in the GeoDAWN study region. The competition states that the existing USGS/INGENIOUS fault data is incomplete and the hidden evaluation includes additional expert-identified faults. The official performance measure is a distance-weighted Tversky index (alpha 0.2, beta 0.8, triangular kernel with 300 m support). See the [official task page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [source ledger](sources.html).

**Live public leaderboard observation (2026-10-21; not a GEMSDOE79 score and not copied from a submission receipt):** the [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) displayed 0.4413 at rank 1. This conflicts with the older user-provided 0.3195 snapshot. The linked GEMSDOE32 page calls H33 an unscored candidate and says no organizer score exists for its artifacts, despite the page's own inconsistent description of an “already-scored” fallback. Therefore the user-pasted 0.2778 is not verified as an organizer-confirmed score, and we cannot truthfully explain why the organizer assigned it. The page describes H33-2-B2 as a thinning/pruning variant; a plausible mechanism is fewer false-positive pixels while retaining weighted coverage, since the official metric penalizes false positives less than false negatives and gives partial credit within 300 m. That is a scientific interpretation, not a proven explanation of the claimed value.

## Exact steps to submit once a validated file exists

1. **Sign in to DrivenData** and download the official competition files from the [data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/). The data page redirects to login when unauthenticated. Place files only in a local ignored `data/` folder; do not commit them.
2. **Establish a reproducible baseline** using the common project feature stack, segment-blocked holdout evaluator, and submission writer. None of those shared tools is currently present in this checkout, so they must be added/reused before experiments.
3. **Test candidate methods without a live submission slot.** Hide complete fault segments plus a spatial buffer. Derive catalogue-based features from visible faults only; mask visible faults pixel-exactly; calculate pooled distance-weighted Tversky at alpha 0.2, beta 0.8 and 300 m support. Run each feature alone as a leakage canary. Record evaluator version, withheld positives, and a segment/fold-bootstrap 95% interval. Never describe a projection as a score.
4. **Run duplicate checks before placement and on final dots** against every available registry raster. Stop if rank correlation exceeds 0.90 or more than 70% of candidate dots are within 3 pixels of a registry raster's dots. Missing registry data means this check is unverified and promotion is blocked.
5. **Create a unique candidate name and short note** (140 characters maximum) only for an experiment that has cleared the holdout and duplication gates. Have the shared writer create the GeoTIFF. Use `scripts/validate_submission.py` to check format and registry similarity against the actual official reference grids.
6. **Upload only the validated `.tif`** on the competition's New submission page. The portal allows one single-band GeoTIFF or a ZIP containing one GeoTIFF. Enter the candidate name and note, submit, and retain the receipt. The receipt alone establishes an **ORGANIZER-CONFIRMED** score.
7. **Keep slot selection separate** from scientific model work. Check the current submission cap on the portal and promote only through the designated selector step.

## Submission raster contract

The official format requires EPSG:32611, 100 m resolution, same bounds as training raster, one float32 prediction band, values in [0,1], and null/NaN outside the bounds. Use the real official sample/training raster as metadata reference; never hard-code shape or geotransform from an unrelated repository. The validator checks format and similarity only; it cannot prove geology or predict leaderboard performance.

## Current recommendation and limitations

Candidate 1 in the [research plan](research-plan.html) is a proposed joint edge/coherence experiment using conductivity-base depth, isostatic gravity, and strain-tensor features. It is not tested. Before this can be measured, the project needs authorized local competition files and the common evaluator/writer. The official competition requires login for downloads; this workspace has no authenticated data session and cannot access private test labels or submit on the user's behalf.

The project site is presently static. It links to the official live leaderboard but does not yet automatically refresh a feed or run retraining. An automated scheduled feed can be added only with stable official endpoints and tests; it must not imply that public leaderboard ranks are a private/final score.
