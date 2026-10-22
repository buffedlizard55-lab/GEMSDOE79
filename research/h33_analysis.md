# H33 score report: evidence, limits, and conditional metric mechanics

## Score-status correction

- **`0.2778` — UNVERIFIED HISTORICAL REPORT.** The figure was user-reported for an H33-named file, but no organizer submission-page receipt links that value to the raster bytes. The GEMSDOE32 project page labels H33 `UNSCORED`; its public page is secondary, not an organizer receipt.
- **`0.4413` — PUBLIC-LEADERBOARD OBSERVATION.** The DrivenData board read on 2026-10-22 listed `xiaofanhu` at rank 1. This is not H33, not this repository's score, not an organizer receipt for any local TIFF, and not a score target we promise to beat.
- **`0.3195` — OLDER USER-REPORTED BENCHMARK.** It is not the latest public leader. The later board read listed rank 21 at `0.3261` and rank 22 at `0.3183`; neither number authenticates a local artifact.

There is no defensible causal statement that H33 “won” because it pruned false positives. A higher leaderboard score remains unproven for this project. Do not convert these three different evidence classes into a single ranking or a prediction.

## What was measured in the raster bytes

The H33 forensic record (`evidence/h33_forensics.json`) identifies the source TIFF by SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` and labels the record `RASTER-MEASUREMENT, NOT A SCORE`.

- D2.8 contains 44,090 positive pixels; H33 contains 37,654.
- H33 is a subset of D2.8; 6,436 D2.8 pixels are absent from H33.
- H33 is exactly D2.8 after deleting pixels within 2 pixels of the mapped-catalogue distance surface (`d_cat <= 2 px`); the recorded rule disagreement is zero.
- No deleted pixel is exactly on a mapped-catalogue positive pixel. The removal was a near-trace thinning rule, not exact catalogue masking.

These facts describe geometry only. They do not identify hidden truth, precision, recall, a public score, or the cause of an organizer result.

## Conditional reason thinning can help—or harm

DrivenData's published distance-weighted metric gives each truth pixel maximum nearby prediction-weighted triangular credit, while false-positive contributions are summed. With `T = TP_w`, `F = FP_w`, and `G` scored truth pixels, the project's reviewed metric form is

```text
DTI = T / (0.2 T + 0.2 F + 0.8 G + epsilon).
```

Deleting redundant predictions can reduce `F` without lowering the maximum `T`. Deleting useful predictions can lower `T` and harm the score. The hidden organizer labels are unavailable, so the balance for H33's 6,436 deleted pixels is unknown. The algebra therefore explains a possible mechanism; it does **not** prove that this rule caused the user-reported `0.2778`, or that applying the rule elsewhere improves a score.

The 300 m triangular kernel and `alpha=0.2`, `beta=0.8` are part of the public competition metric, not evidence that a nearby prediction is invalid. DrivenData staff clarifies that new target pixels absent from USGS/INGENIOUS can be extensions, splays, or parallel strands of an existing system; proximity alone is not disqualifying.

## Local holdout evidence is a different quantity

The inherited G79-THVC baseline is **HOLDOUT-DTI**, evaluator `gems57-pooled-hide-v2`: seed 20 is `0.1905` (95% CI `[0.1741, 0.2069]`, 11,321 withheld positives); seed 30 is `0.1944` (95% CI `[0.1774, 0.2126]`, 11,342 withheld positives). These are archived holdout results, not a new test in this review, not leaderboard scores, and not organizer-confirmed results. They compare to a fold-fair H33 control under shared buffered folds; they do not establish hidden-test performance.

## Superseded language and current references

Earlier drafts described the 6,436 removed pixels as known false positives, attributed a score increase to pruning, or called `0.2778` verified. Those claims are withdrawn. The full corrected derivation, scope, code-review corrections, and next steps are in [`knowledge/h33_review_e4a4422d.md`](../knowledge/h33_review_e4a4422d.md). The older narrative is retained in Git history; [`knowledge/why_h33.md`](../knowledge/why_h33.md) now records that it is superseded. The current public leaderboard observation and source-read method are recorded in [`knowledge/official_sources.json`](../knowledge/official_sources.json) and [`evidence/source_review_a92a0164.json`](../evidence/source_review_a92a0164.json).
