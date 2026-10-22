# Why H33 scored highest, and whether H79-NHR can beat it

Session 337ac1e9, 2026-10-22. Evidence labels used in this document:
**HOLDOUT-DTI** is our spatially blocked hide-and-recover proxy (evaluator
`gems57-pooled-hide-v2`). **USER-REPORTED** is a filename-to-score pairing given
in the prompt that has no organizer receipt in this repo. **PUBLIC-LEADERBOARD**
is a value read from the official leaderboard page (it names teams, not files).
**ESTIMATE** is algebra on those inputs under stated assumptions. **RASTER-MEASUREMENT**
is a count measured from actual bytes; **REGISTRY-MEASUREMENT** is the same against the
992 registry rasters. Nothing here is ORGANIZER-CONFIRMED for a
file produced by this repo.

## 1. The metric rewards sparse dots, not probability maps

From the [official metric definition](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric),
with `k(d) = max(1 − d/300 m, 0)` on the 100 m grid:

```
TP  = Σ_truth   max_x p(x)·k(d)          (each truth pixel takes its best nearby prediction)
FP  = Σ_x       p(x)·(1 − max_truth k(d)) (every predicted unit pays unless it is on/near truth)
FN  = N_truth − TP
DTI = TP / (TP + 0.2·FP + 0.8·FN)
```

Known catalogue pixels are masked from scoring ([staff clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)),
and terms are pooled over the public chunks before the ratio
([aggregation clarification](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2)).

Two asymmetries follow directly:

1. **TP is a max, FP is a sum.** A single dot of value 1 sitting on a straight
   truth trace credits the pixels at 0, ±100 m and ±200 m with 1, 0.667 and 0.333.
   Repeating dots every 3 pixels along the trace gives each truth pixel its best
   kernel value, so each dot earns about `1 + 2×0.667 = 2.33` truth-pixel units of TP while
   paying at most 1 unit of FP. A continuous map pays FP on *every* positive pixel and
   earns no extra TP from neighbours that are already covered. Dotting is
   the reason almost every high GEMSDOE entry, H33 included, is a binary sparse field.
2. **Break-even probability.** Adding a dot with expected TP gain `A` and FP cost
   `B ≈ 1` improves the score `s` when `A > 0.2·s·(A + B)`, that is
   `A > 0.2s / (1 − 0.2s)`. With `A ≈ 2.33·P(dot lies on a truth trace)`:
   at `s = 0.28` a dot is worth placing if `P > ≈2.5 %`; at `s = 0.44` it must be `P > ≈4.1 %`.
   (ESTIMATE; it ignores partial-kernel hits and overlap between dots.)

A rigorous lower bound also follows. Write `c = TP/N` (the share of truth credit captured)
and `r = FP/N`. Then `c = s(0.2r + 0.8)/(1 − 0.2s) ≥ 0.8s/(1 − 0.2s)`, so a
public score of 0.2778 needs `c ≥ 23.5 %` and 0.4413 needs `c ≥ 38.7 %`.

## 2. What H33 actually is, and why it won inside the GEMSDOE family

RASTER-MEASUREMENT (`evidence/h33_forensics.json`, `knowledge/why_h33.md`):
H33 is **exactly** the D2.8 dot set (44,090 dots) minus the 6,436 dots within 200 m
(2 px) of a mapped fault. No dot was added or moved.

USER-REPORTED: D2.8 0.2600 and H33 0.2778.

Under the **unverified** assumption that the 6,436 removed dots had zero marginal TP,
only FP changed. Adjacency to masked catalogue pixels does not establish this: nearby
unmapped strands can still earn TP, and the 200 m collar itself is not masked. Then the ESTIMATE is
`TP·(1/0.2600 − 1/0.2778) = 0.2·6,436`. That gives TP ≈ 5.2 k truth-pixel units in the public set and
`N_truth ≈ 12.8–13.3 k`. H33 therefore captures **c ≈ 39–41 %** of public truth
credit with ≈35–37 k FP units.

H33 led the family for three reasons, ranked by our confidence:

1. **It deleted near-catalogue dots, plausibly reducing redundant FP.** This is
   the measured raster change, not proof that every deleted dot was a false positive.
   Exact mapped pixels are masked; the surrounding 200 m collar is not. Nearby
   unmapped splays could lose TP when those dots are removed. The reported score
   pair is consistent with a net gain, but artifact-linked organizer receipts and
   hidden labels are absent, so the causal explanation remains conditional.
2. **Its dots are already sparse and roughly at budget.** The measured budget is about 37.7 k dots. Whether its marginal dot is near
   break-even is unknown without hidden truth. Additional dots can either help or
   hurt according to their incremental TP and FP, not their count alone.
3. **Its ranking came from distance-to-fault structure plus scarps**, inherited from
   D2.x. RASTER-MEASUREMENT (`evidence/nhr/distance_to_catalogue.json`):
   - The median H33 dot lies 19.6 px (≈1.96 km) from the catalogue.
   - 69.8 % of its dots are more than 1 km away.
   - Only 15.0 % are within 500 m.
   
   It is a broad, moderately catalogue-aware field. It is not a tight halo.

None of this proves *why* the private labels favour H33; the leaderboard pairs
are user-reported and the public leaderboard names teams, not files.

## 3. How far the leader is ahead

PUBLIC-LEADERBOARD (fetched 2026-10-22,
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)):

| Team | Score |
|---|---:|
| xiaofanhu | 0.4413 |
| cfld__ | 0.3904 |
| Batik Shirt Brothers | 0.3894 |

The user's other target is 0.3195.

Using the same `N_truth` and a similar FP budget, ESTIMATE:

| Target | Required truth-credit share `c` | Ratio to H33's credit |
|---:|---:|---:|
| 0.4413 | ≈ 65–67 % | ≈ 1.6–1.7× |
| 0.3195 | ≈ 46–47 % | ≈ 1.2× |

The alternative to more credit is fewer false positives at equal coverage. Either way,
the gain must come from **better ranking of where unmapped faults are**, not from a format trick.

## 4. Can we beat H33? What H79-NHR measured

H79-NHR trains a gradient-boosted regressor on *nested* hide-and-recover data. Inside
each training fold it hides 20 % of catalogue components, buffers them by 3 px and
fits the official 300 m kernel credit of the hidden components. It uses 19 supplied
bands, multiscale terrain/gravity/magnetic derivatives, 10 lidar scarp bands,
8 radiometric bands and 6 geometry inputs computed only from the visible catalogue.
The target therefore *is* the quantity the dot allocator needs: expected kernel credit
for a fault that is missing from the map.

HOLDOUT-DTI (`gems57-pooled-hide-v2`, 4 leave-one-quadrant-out folds, 37,654-dot
budget, spacing 3; `evidence/nhr/x1_holdout_seed{20,30}.json`):

| Arm | Seed 20, n = 11,321 withheld px | Seed 30, n = 11,342 withheld px |
|---|---:|---:|
| **H79-NHR candidate** | **0.1431 [0.1281, 0.1574]** | **0.1522 [0.1335, 0.1696]** |
| H33 fold-fair control (legacy D2.8 dots > 2 px from the fold's visible faults) | 0.0961 [0.0837, 0.1086] | 0.0989 [0.0842, 0.1120] |
| Ablation, no geometry inputs | 0.0739 [0.0617, 0.0863] | 0.0751 [0.0612, 0.0898] |
| Uniform random control | 0.0484 [0.0432, 0.0537] | 0.0482 [0.0433, 0.0522] |
| Paired Δ vs H33 control | +0.0470 [0.0321, 0.0621] | +0.0533 [0.0369, 0.0704] |

Leakage canary: 58 features × 4 folds × 2 seeds = 464 single-feature AUC tests.
None exceeded 0.90. The worst was `geom_log_dist_visible_tip`, at 0.8514 and 0.8589.

The candidate beats the best previously recorded holdout control on both seeds,
and the paired 95 % CIs exclude zero. That clears the gate: **do not spend a slot on
an idea that has not beaten holdout best**.

**But the lane is a duplicate.** REGISTRY-MEASUREMENT (`evidence/nhr/overlap_chance.json`,
shared helpers, 990 comparable registry rasters):

- 26 ordinary registry dot fields each contain more than 70 % of the final dots within 3 px.
  These fields' 3 px halos cover only 20–68 % of the allowed area.
- The worst is `GEMSDOE3:coverage-v3-wide`: 0.913 against a chance level of 0.610.
- The most concentrated is `GEMSDOE53:gems53-h1-thin_bin_q0p1`: 0.814 against a chance level of 0.204.
- The surface top-k check fails the same way before placement (`evidence/nhr/surface_topk_vs_flagged.json`).

The protocol says: *"you have drifted into another lane: log it as a duplicate and stop."*
The lane stopped. We did not retune it, cap the overlap, or open a second lane.

**We do not convert +0.05 HOLDOUT-DTI into a leaderboard projection.** Absolute
holdout values are lower than public scores because whole components are withheld
behind a buffer.

## 5. The biggest risk: catalogue-proximity bias

The ablation shows that the gain comes mainly from the geometry inputs. RASTER-MEASUREMENT:

| Dot set | Median distance to catalogue | ≤ 500 m | > 1 km | ≤ 200 m |
|---|---:|---:|---:|---:|
| H79-NHR dots | 5.4 px, 539 m | 45.5 % | 17.6 % | 53 dots |
| H33 dots | 19.6 px | 15.0 % | 69.8 % | 0 dots |

Withheld *catalogue* components sit close to the visible catalogue, because faults
cluster in systems, and NHR learned that well. The organizer's labels are
*expert-identified faults absent from the USGS database*. If those faults are as
clustered around mapped systems as catalogue faults are (splays, step-overs and
range-front continuations), NHR should transfer. If experts mostly found isolated
structures far from mapped systems, H33's broader field may score better.

The holdout cannot measure this shift. But the registry gives indirect evidence.
The family's earlier near-fault dot fields, the very ones NHR duplicates, have
UNVERIFIED HISTORICAL public scores of 0.016–0.143 (`registry/score_ledger.csv`). They are
not like-for-like, because most used 56 k–985 k dots, but none came close to H33.
This is consistent with the shift being real.

## 6. What would most raise P(win) next

1. **Decide how to treat the 30 space-filling registry rasters.** The seeded uniformly
   random control is flagged by 30 registry rasters whose halos cover more than
   70 % of the allowed area. That statistic does not prove universal failure.
   The separate literal-support witness covers **every** allowed cell, which does
   prove every nonempty map has overlap 1.0 under that reading (IR-79-53). This needs an explicit user decision. One
   option: for those rasters, use overlap beyond chance, `(ov − halo)/(1 − halo)`,
   and keep the literal rule for all others.
2. **Target the far field explicitly.** H33's dots are mostly more than 1 km from the
   catalogue, and the near-fault band is crowded in the registry. A new lane should
   learn a ranking *within* H33-like distance bands, for example lidar and antislope
   evidence (hypothesis 2) restricted to more than 1 km from mapped faults. Check the
   surface for uniqueness **before** placement.
3. **Reweight the nested target by distance band**, so training mimics the spacing of
   expert faults rather than of catalogue faults. Preregister this before running it.
4. **Hypothesis 3 (Lahontan shoreline suppression)** needs the absolute 3DEP DEM, which
   is free from the [USGS National Map](https://apps.nationalmap.gov/downloader/).
