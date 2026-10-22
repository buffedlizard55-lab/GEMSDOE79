# H79-DILSTEP result

This is a negative result. It is not a leaderboard score and it is not permission to upload.

## What was tested

One preregistered closed-form score, frozen before any number below was computed. Positive robust-z dilatation, times horizontal magnetic gradient, times a basin term from GeoDAWN thickness, times fixed weights on three structural masks built only from the visible fault catalogue: tip cones, stepover gaps, and intersections. Playa shorelines, where lidar steps coincide with flat ground, are penalized. Dots are the top 37,654 ranks at 3-pixel spacing, never on a mapped fault.

The named non-fault mimic is a playa or shoreline scarp.

## HOLDOUT-DTI

Evaluator `gems57-pooled-hide-v2`. Four spatial folds. Whole fault segments hidden, with a 3-pixel buffer. Catalogue features use only the visible faults.

| Arm | Seed 20 | Seed 30 |
|---|---:|---:|
| Candidate | 0.0721 [0.0577, 0.0874], n = 11,321 | 0.0650 [0.0528, 0.0778], n = 11,342 |
| No-structure ablation | 0.0405 [0.0287, 0.0523] | 0.0371 [0.0286, 0.0464] |
| Uniform control | 0.0484 [0.0434, 0.0532] | 0.0523 [0.0459, 0.0586] |
| H33 fold-fair control | 0.0961 [0.0837, 0.1086] | 0.0989 [0.0842, 0.1120] |

Paired difference versus H33, seed 20: −0.0240 [−0.0418, −0.0050]. Seed 30: −0.0339 [−0.0526, −0.0159]. Both intervals are entirely below zero. The structure term beats the ablation on both seeds, so the geological masks are not empty, but they do not place the budget on the withheld faults well enough to match H33.

The recorded H79-NHR holdout best, not remeasured here, is 0.1431 / 0.1522. This experiment does not beat it.

Leakage canaries: 72 single-feature tests, maximum symmetric AUC 0.6981 (`horsetail`), threshold 0.90. Pass.

## Why this does not imply a higher organizer score

User-reported 0.2778 for the H33 zeros file is not an organizer receipt. The public leaderboard on 2026-10-22 showed 0.4413 at rank 1. Those figures are not this file's score. A method that loses to the H33 control on a catalogue holdout has no measured reason to expect a higher organizer score than H33. It might still differ on expert faults the catalogue does not contain. That possibility is not a projection, and it is not a reason to spend a weekly slot.

## Uniqueness

IR-79-67, applied before any submission placement. Spearman of the continuous surface against 986 comparable rasters: worst 0.6406, under 0.90. Six files were unreadable or on a different grid and are listed, not treated as passes. Forward 3-pixel overlap of the 37,654 check dots: 12 registry files exceed 0.70 and have a halo that covers at most 70% of allowed cells. Those 12 files are 7 distinct maps; nan and all-finite twins are counted separately. The worst is the 13GEMSDOE r6 ensemble at 0.8527, against a halo coverage of 0.6413. The weakest informative flag is 0.7030 against a halo of 0.4425, so the stop is not one marginal file. Thirty other rasters also exceed 0.70, but their own halos cover more than 70% of the allowed area, including a witness that covers every allowed cell. Those are recorded and do not fire the operative flag. Literal overlap is 1.0 and is not called uniqueness.

The surface gate failed. No submission dots were placed after that. The downloadable file is the check set, so the failure can be audited. Do not upload it.

## Stop

One experiment of three. No retune. No overlap cap. No second method in this lane. Slots used: 0.
