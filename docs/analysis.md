# GEMSDOE79 — H33 score analysis: why 0.2778, and can we beat it?

## What H33 actually reported

The GEMSDOE32 site reports a single submission:

> `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`: **0.2778**

Source: https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html

## Critical caveats (verified from the repo evidence)

1. **0.2778 is an unverified historical report.** GEMSDOE32 labels this entry
   UNSCORED. The number appears on a project Pages site, not on the DrivenData
   organizer submission page, and no organizer submission receipt is on file in
   this repository. It is therefore not ORGANIZER-CONFIRMED.

2. **The public leaderboard observation 0.4413** (cited in the user prompt) is
   also not this project's score, not a ceiling, and not a target we can promise
   to beat. It is a third-party observation without an organizer receipt in this
   checkout.

3. **0.3195** (also cited in the prompt) is a different historical report with
   the same evidential status.

4. **H33's method (from the filename):** `h33-h33-2-b2` suggests an
   H33-family submission with parameters "2" and "b2", emitted as binary zeros
   (`-zeros`). The naming convention across GEMSDOE sites indicates `-zeros`
   submissions are binary 0/1 masks. H33 likely emitted ~37,654 dots (the
   recurring dot count in this family) as a binary mask.

## Why H33 may have scored relatively well (PhD-level assessment)

The GEMS prize metric is a distance-weighted Tversky Index (DTI) with
α = 0.2 (FP penalty), β = 0.8 (FN penalty), 300 m triangular kernel. Because
β >> α, the metric heavily penalizes missed truth (FN) and lightly penalizes
false positives (FP). A submission that emits a **dense, broadly distributed
binary mask** covering much of the footprint can achieve a moderate DTI simply
by being near many truth pixels:

- With ~37,654 dots spread across ~5.17 million footprint pixels (~0.73%
  coverage), a binary mask places dots within 300 m of a large fraction of
  truth pixels.
- The triangular kernel gives partial credit up to 300 m, so dots don't need to
  be exact — they just need to be *near* truth.
- β = 0.8 means each missed truth pixel costs 4× a false positive, so emitting
  more dots (accepting FP) is usually better than missing truth (FN).

H33's 0.2778 is plausibly explained by: (a) a well-distributed dot field that
captures many truth pixels within the 300 m kernel, (b) the β-heavy metric
rewarding recall over precision, and (c) dots placed near known geothermal
structures where truth is concentrated. It is NOT evidence of a breakthrough
method — it is consistent with a dense, informed prior that happens to align
with truth at kernel scale.

## Can we generate a submission that scores higher than 0.2778?

**Honest answer: possibly, but not provable without organizer truth.**

The competition truth labels are not public. Holdout-DTI (the shared buffered
hide-and-recover evaluator) is the only offline proxy, and it requires
DrivenData training data (login-gated, not in this checkout). Without holdout
measurements, any claim of beating 0.2778 is speculation.

What we *can* do:

1. **Generate a unique, format-valid TIF** — done (G79-DZD, 12,000 sparse
   damage-zone dots, max |ρ| = 0.0212 vs local rasters, max overlap = 0.2456).
   This passes all local format gates and is unique vs locally available
   rasters.

2. **Measure holdout-DTI** — blocked offline. Needs training_features.tif and
   labels.tif from DrivenData.

3. **Run leakage canaries** — blocked offline (AUC > 0.90 would indicate
   leakage).

4. **Complete the full 992-raster registry uniqueness scan** — blocked offline
   (registry rasters not cached locally; GitHub TLS unavailable).

**Bottom line:** We cannot truthfully claim to beat 0.2778. The G79-DZD
submission is a legitimate, unique, format-valid candidate, but its leaderboard
score is unknown until it is uploaded and scored by the organizers — which
cannot happen until the missing gates (holdout-DTI, leakage canary, selector
approval) are cleared with DrivenData access.

## What would be needed to claim a score > 0.2778

| Requirement | Status |
|---|---|
| DrivenData login + training data download | Not available in this sandbox |
| Holdout-DTI measured vs incumbent on both seeds, paired 95% CI excludes 0 | Blocked |
| Leakage canary: max feature-alone AUC ≤ 0.90 | Blocked |
| Full 992-raster registry uniqueness scan (ρ ≤ 0.90, overlap ≤ 0.70) | Partial only (36 local rasters) |
| Separate selector approval (scripts/select_submission.py) | Not run |
| Organizer submission receipt (ORGANIZER-CONFIRMED score) | None |

Until all of the above are complete, the correct label for any generated TIF is:

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**
