# What H33 teaches us — and what it does not prove

## Answer to the competition question

**A better leaderboard result is possible in principle, but this repository has not demonstrated one.** The reported H33 result is **an unverified historical report**, not an artifact-linked organizer receipt. The GEMSDOE32 site itself still describes its file as **UNSCORED**. The public leader observed on 2026-10-22 is recorded separately as a **PUBLIC-OBSERVATION** in the [source ledger](review_e4a4422d_sources.json), never as this project's score. No numerical leaderboard projection is made here.

The useful lesson is **prediction efficiency**, not copying H33's pixels. Its apparent historical advantage is consistent with reducing redundant prediction mass while retaining coverage. That is a conditional metric explanation, not proof of why the organizer assigned a particular score.

## Re-measured byte lineage

We independently restored the two pinned Git blobs and inspected their pixels during this review. These are **RASTER-MEASUREMENTS, NOT SCORES**:

| Quantity | Measurement |
|---|---:|
| D2.8 positive pixels | 44,090 |
| H33 positive pixels | 37,654 |
| Deleted D2.8 pixels | 6,436 |
| H33 pixels absent from D2.8 | 0 |
| Disagreement with `D2.8 & (distance_to_catalogue > 2 px)` | 0 |
| Deleted pixels exactly on the catalogue | 0 |

The last row matters: these were **nearby off-catalogue pixels**, not exact catalogue pixels. An earlier FNHR narrative described a different deletion count and on-catalogue pruning; that description does not match the pinned H33/D2.8 pair. The new [re-measurement](../evidence/review_e4a4422d/h33_remeasurement.json) agrees with the original [forensic receipt](../evidence/h33_forensics.json).

A nearby prediction can still recover an unknown fault. A collar is therefore a model choice, not an organizer-mandated exclusion zone. Merely removing exact masked pixels cannot improve a metric that already excludes those pixels.

## Why thinning can help, precisely

The [organizer's metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric) gives each truth pixel the maximum nearby prediction-weighted triangular credit. False-positive contributions are summed over predictions. Additional predictions can therefore incur cost without increasing the maximum coverage of any truth pixel.

Write `T = TP_w`, `F = FP_w`, and `G = number of scored truth pixels`. Because `FN_w = G − T`, the metric is

```text
DTI = T / (0.2 T + 0.2 F + 0.8 G + epsilon).
```

Suppose deleting predictions loses `a` units of true-positive credit and removes `b` units of false-positive cost. For fixed truth and masks, the deletion improves DTI exactly when

```text
0.2 T b > a (0.2 F + 0.8 G + epsilon).
```

Thus a redundant false positive (`a = 0`, `b > 0`, `T > 0`) is worth removing. But a true-positive deletion can be harmful. Hidden organizer truth is unavailable, so the actual `a` and `b` for H33's deleted pixels are unknown. There is no theorem that arbitrary thinning, moving dots, or broad catalogue collars increases the competition score.

## What the current holdout can support

The website's table is generated directly from the frozen shared evaluator output: **HOLDOUT-DTI**, `gems57-pooled-hide-v2`, buffered whole-component hide-and-recover, pooled weighted components, paired spatial-block percentile intervals. Each seed displays its own withheld-positive count and confidence interval.

The historical G79-THVC candidate improves over the H33 *fold-fair control* in those receipts. This is **not** a new experiment beating today's incumbent, and the two seeds reuse the same geographical region and catalogue. They are not independent datasets and their positive counts must not be added and described as distinct faults. Confidence intervals are conditional on fitted models, selected settings, catalogue labels and the split; they do not account for all historical model selection or hidden-test distribution shift.

The holdout hides already mapped faults. The organizer asks for expert-identified faults absent from that catalogue. Geometry-dependent features can perform well on the former without generalizing to the latter. Passing single-feature leakage canaries is necessary under the project protocol, not sufficient proof that every leakage or distribution-shift risk has vanished.

## Code-review corrections, not new results

- The old run card mixed shared-evaluator intervals with a separate bootstrap under the same label. All active card views now reference the shared output consistently; the original card and both original result branches are preserved in the [metadata reconciliation](../evidence/review_e4a4422d/metadata_reconciliation.json).
- A bootstrap's observed fraction of positive resamples is not certainty of geological superiority. The live summary uses paired confidence intervals, not `P = 1.000` claims.
- `charnes_cooper_submodular_emit` is the historical function name. Its code uses fixed-penalty lazy-greedy weighted kernel cover, a candidate pool, exclusion spacing and budget limits. The parameter search enumerates a grid. It does **not** implement a certified exact Charnes–Cooper transformation or an iterative Dinkelbach optimality test. No claim of global optimality follows from it.
- Endpoint cones in `compute_network_mechanics` are geometric proxies. They are not a solved three-dimensional elastic stress field, and do not establish slip, permeability, fluid flow or a producing geothermal reservoir.
- Limited sparse-map overlap and low rank correlation are useful diagnostics, but do not clear the required full novelty test. The current file fails it and must not be submitted, even manually.

## What would genuinely improve the project

1. Set a prospective, shared definition of comparable registry dots. Do not change it to rescue a stopped candidate.
2. Reserve a genuinely untouched spatial validation partition before another search; keep the current shared holdout for required comparability, not unrestricted retuning.
3. Test an independently motivated physical mechanism with explicit nuisance-process controls and single-feature canaries. The [new backlog](../research/hypotheses_e4a4422d.md) makes no predicted-score claims.
4. Re-evaluate the candidate and incumbent under the same buffered folds, budgets and shared evaluator. Require the predeclared improvement gate and both novelty stages before the separate selector considers a slot.
5. Keep fault mapping distinct from geothermal-resource certification. Temperature, permeability, sustainable flow and economics require additional evidence.

Sources were re-read in this session and are listed claim-by-claim in the [primary-source ledger](review_e4a4422d_sources.json). Historical analyses remain available for audit, but are not approval or freshly verified results.
