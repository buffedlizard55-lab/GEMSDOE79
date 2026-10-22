# Session 0a202578: H33, the leaderboard, and the G79-FSC result

## 1. Why GEMSDOE32 H33 scored 0.2778, and can we beat it?

**Evidence classes.** The 0.2778 for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is **USER-REPORTED**. On 2026-10-21 the public leaderboard showed the same number (0.2778) at rank 48. That match does not prove which file or account earned it (`knowledge/official_sources.json`, entry DD-LEADERBOARD). On 2026-10-22 the [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) showed **#1 xiaofanhu 0.4413**, #2 0.3904 and #3 0.3894 (PUBLIC LEADERBOARD OBSERVATION). The value 0.3195 in the prompt is not the current top score.

**What H33 is.** H33 is a 37,654-dot binary map. It is D2.8 (44,090 dots) with the 6,436 dots within 2 px of a mapped fault removed. We re-measured this from the pinned bytes; see `knowledge/h33_review_e4a4422d.md`. Here is how the [organizer's metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) works:

- Each truth pixel gets the *maximum* nearby kernel credit.
- Every predicted pixel adds false-positive mass.

With T = weighted TP, F = weighted FP and G = scored truth pixels:

`DTI = T / (0.2 T + 0.2 F + 0.8 G)`

A dot is worth adding only if its credit exceeds 0.2 × DTI. So sparse, well-placed dots beat dense maps. H33's 0.2778 is consistent with good **per-dot efficiency**. That explanation follows from the metric; it is not proof of what the hidden labels contain.

**Can we beat it?** On this project's spatially blocked holdout, the archived G79-THVC lane scores **HOLDOUT-DTI 0.1905 / 0.1944**. The H33 fold-fair analogue on the same split scores 0.0961 / 0.0989, so THVC is about 2× better. Both pairs of numbers are frozen, from evaluator gems57-pooled-hide-v2. This session's G79-FSC scores 0.1406–0.1580, which also beats the H33 analogue (point estimates only; no paired interval vs H33 was computed). HOLDOUT-DTI hides already-mapped faults, so these numbers **cannot be converted into leaderboard scores**. Whether any of these files would beat 0.2778 publicly is unknown until one is submitted.

## 2. G79-FSC: hypothesis, experiments, result

- **Hypothesis H1:** hidden Basin-and-Range faults are sub-parallel to the local mapped fault fabric. Physical edges whose strike agrees with that fabric are more often faults. The edges come from detrended topography, isostatic gravity, RTP magnetics and the LiDAR scarp strike band. The fabric is the structure tensor of the *visible* catalogue.
- **Mechanism:** fault populations in an extensional stress field share a strike set. Unmapped splays and buried continuations inherit that strike.
- **Named non-fault mimics:** pluvial Lake Lahontan shorelines and alluvial-fan toes, which parallel range fronts. Also NNE dikes in magnetics.
- **Preregistration:** `registry/preregistration_g79_fsc.json`, commit 49d2383, made before any feature or score existed. Amendment A1, `registry/preregistration_g79_fsc_amendment_A1.json`, commit fedd6c7. A1 was registered after the seed-20 result was seen and before seed 30 existed. That is one disclosed extra look at the holdout.

HOLDOUT-DTI, evaluator gems57-pooled-hide-v2, split `buffered_component_draw(seed, buffer_px=3, boundary_px=12)`. Withheld positive pixels: seed 20 n = 11,321; seed 30 n = 11,342. The 95% CI is a 1000-draw paired 20 km block bootstrap.

| Arm | Seed 20 | Seed 30 |
|---|---|---|
| EXP-FSC-1 candidate (45k dots) | 0.1406 [0.1265, 0.1551] | 0.1472 [0.1314, 0.1622] |
| EXP-FSC-2 ablation, no fabric family | 0.1344 [0.1205, 0.1483] | 0.1347 [0.1207, 0.1493] |
| EXP-FSC-3 amendment A1 (+ network-frame offsets) | 0.1469 [0.1322, 0.1600] | 0.1580 [0.1432, 0.1732] |
| Uniform random, same budget | 0.0471 [0.0413, 0.0529] | 0.0506 [0.0455, 0.0559] |
| **G79-THVC incumbent (bar to beat)** | **0.1905** | **0.1944** |

Paired differences on the same folds:

| Comparison | Seed 20 | Seed 30 |
|---|---|---|
| Fabric family (EXP-1 minus EXP-2) | +0.0062 [−0.0018, +0.0151], not significant | +0.0125 [+0.0046, +0.0197] |
| A1 minus EXP-1 | +0.0063 [−0.0020, +0.0142] | +0.0109 [+0.0036, +0.0189] |
| EXP-1 minus random | +0.0935 [+0.0791, +0.1076] | +0.0966 [+0.0821, +0.1112] |

**Leakage canary:** the maximum single-feature symmetric AUC was 0.778 (EXP-1, `log_d_end`) and 0.781 (A1, `end_across`). Both are below 0.90, so the canary passes.

**Verdict: NEGATIVE.**

- Every FSC arm is about 0.04–0.05 below THVC on both seeds. The preregistered promotion gate requires beating THVC on both seeds.
- The fabric idea carries some real but small signal: it is significant on one of the two seeds.
- The model's gain is dominated by smooth regional fields: surface conductance, earthquake density, geodetic strain. In other words, it learns *where fault-rich regions are* more than *where a missing strand lies*.
- At 45k dots it pays FP mass 41.6k for TP 2.5k. THVC pays 34.7k for 3.2k (seed 20).
- **Novelty** (amendment D-2, 1,216 comparable registry rasters, 0 invalid; this repository's own archived TIFFs included):
  - The *surface before placement* is a duplicate of 33 prior dot fields: chance-corrected overlap > 0.70, max 0.887.
  - The *final dots* clear every informative raster: max chance-corrected overlap 0.590, max ρ 0.110. They are still flagged against 4 rasters that are positive on every cell. Under D-2's saturated branch, *any* non-empty file fails against those 4 (IR-79-173).
- The published GeoTIFF is therefore research-only and labelled DO-NOT-SUBMIT. It fails gate G1 (holdout), gate G4 (surface novelty) and gate G5 (saturated-branch novelty).

## 3. What this teaches

1. Placement efficiency dominates. The incumbent's crack-tip continuation plus kernel-cover placement extracts more TP per dot than a classifier plus top-K NMS.
2. Orientation agreement alone does not localize faults at 100 m. Regional context explains most of the classifier's skill.
3. The budget rule (≤ 3 experiments) stopped a fourth try. This was the right call because each extra look at the same holdout inflates apparent gains.

## 4. Limitations

- The holdout hides catalogue faults. The organizer scores *new* expert-labelled faults, so gains may not transfer.
- The two seeds share geography and catalogue, so they are not independent datasets.
- No paired CI against THVC is possible because THVC's fold predictions were not cached.
- Novelty uses amendment D-2. The literal overlap rule is 1.0 for every non-empty file (`evidence/universal_overlap_certificate.json`), so it carries no information. The literal reading is still printed.
- **Structural blocker:** D-2's saturated branch has the same flaw (IR-79-173). Until the owner makes a prospective decision ("D-3") about rasters that are positive everywhere, no file from any lane can pass every gate.
