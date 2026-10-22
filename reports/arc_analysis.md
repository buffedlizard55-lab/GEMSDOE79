# Why H33 scored highest in the family — and what H79-ARC does differently

Session 167a60a6, 2026-10-22. Evidence classes: **HOLDOUT-DTI** (shared
evaluator `gems57-pooled-hide-v2`), **USER-REPORTED** (prompt filename→score
pairings, no organizer receipt in this repo), **PUBLIC-LEADERBOARD** (read
2026-10-22 from the official leaderboard; names teams, not files),
**RASTER-MEASUREMENT** / **REGISTRY-MEASUREMENT** (counts on actual bytes),
**ESTIMATE** (algebra under stated assumptions). Nothing for a file from
this session is ORGANIZER-CONFIRMED; no leaderboard number is projected.

## 1. Why H33 (USER-REPORTED 0.2778) leads the GEMSDOE family

Re-measured this session on the restored registry bytes
(`scripts/analyze_h33.py`, `evidence/h33_forensics.json`): **H33 is exactly
the D2.8 dot set (44,090 dots) minus its 6,436 dots within 200 m of the
mapped catalogue** — no dot added or moved. D2.8 itself is a Poisson
thinning (d≈2.8 px) of the h19-5 multiline ridge surface (121,131 px,
USER-REPORTED 0.1922 → 0.2600 after thinning → 0.2778 after collar pruning).

The mechanism is the metric's asymmetry (official definition, α=0.2, β=0.8,
300 m triangular kernel): TP credits each truth pixel with the *maximum*
neighbouring prediction, FP *sums* over predicted mass. A dot on a straight
trace earns ≈2.33 TP units per FP unit at 3 px spacing, so sparse binary
dots dominate continuous maps, and deleting dots that mostly duplicate
already-credited trace neighbourhoods (the ≤200 m catalogue collar — exact
catalogue pixels are masked by the organizer) raises the ratio. Under the
*unverified* assumption that the deleted dots had zero marginal TP, the
0.2600→0.2778 pair implies ≈12.8–13.3k public truth pixels and H33 capturing
≈39–41 % of truth credit (ESTIMATE, `reports/nhr_analysis.md` §2). The
public leader (PUBLIC-LEADERBOARD 0.4413, verified 2026-10-22; 21 teams
≥0.3261) needs ≈65–67 % credit at a similar FP budget — the remaining gap
is ranking quality: finding more of the experts' traces.

## 2. Why proximity learning (H79-NHR) was the wrong hill

H79-NHR beat the H33 holdout control (0.1431/0.1522 vs 0.0961/0.0989) by
learning that withheld *catalogue* components sit near visible ones
(median dot 539 m from a mapped fault). It duplicated 26 ordinary registry
dot fields and stopped. The organizer's labels are expert faults *absent*
from the catalogue — if they clustered like catalogue strands do, the
family's many near-fault fields would not have scored 0.016–0.143 live
(UNVERIFIED HISTORICAL, `registry/score_ledger.csv`). Proximity is a
holdout shortcut with a live distribution-shift cost.

## 3. H79-ARC: physical ridge-concordance, no proximity, cover emission

Lane paragraph and preregistration: `registry/preregistration_arc.json`.
Design choices, each tied to the evidence above:

- **No catalogue-proximity input at all** (no distance/density/tip terms —
  the NHR failure mode). Only the regional strike field of the visible
  catalogue (alignment/coherence) is used.
- **Line-steered transforms** added to the pinned feature stack:
  structure-tensor coherent edge strength of elevation/magnetics/gravity,
  Hessian ridge anisotropy, magnetic worm persistence, lidar antislope
  (uphill-facing) asymmetry — targeting antithetic piedmont scarps and
  buried basement edges that a topography-led compilation under-maps.
- **Nested hide-to-recover kernel-credit target** (as NHR): the regressor
  estimates expected 300 m-kernel credit for a fault missing from the map.
- **Max-cover emission** instead of Poisson thinning: greedy submodular
  maximization of expected covered credit under the official kernel, 3 px
  spacing, fixed 37,654 budget, >200 m off catalogue (the measured H33
  collar). On identical surfaces this emission alone was worth
  +0.0094/+0.0099 HOLDOUT-DTI over Poisson (paired CIs exclude 0).

HOLDOUT-DTI (`gems57-pooled-hide-v2`, 4 spatial folds, seeds 20/30):

| Arm | Seed 20 (n=11,321) | Seed 30 (n=11,342) |
|---|---:|---:|
| **H79-ARC candidate** | **0.1020 [0.0883, 0.1174]** | **0.1005 [0.0853, 0.1155]** |
| H33 fold-fair control | 0.0961 [0.0837, 0.1086] | 0.0989 [0.0842, 0.1120] |
| Ablation: Poisson emission | 0.0926 [0.0794, 0.1083] | 0.0906 [0.0752, 0.1066] |
| Uniform control | 0.0487 | 0.0489 |
| Paired Δ vs H33 control | +0.0059 [−0.0063, +0.0193] | +0.0016 [−0.0122, +0.0168] |
| Paired Δ vs uniform | +0.0533 [+0.0398, +0.0669] | +0.0516 [+0.0373, +0.0663] |

Read this honestly: **parity-or-better** against the H33-class ranking on
withheld catalogue faults — point estimates ahead on both seeds, intervals
against H33 including zero — from a completely different input philosophy
(no proximity). Leakage canary: 560 single-feature AUC tests, max 0.6866
≤ 0.90. RASTER-MEASUREMENT: median catalogue distance 894 m (NHR 539 m,
H33 1.96 km); only 948 of 37,654 dots coincide exactly with H33 dots;
forward excess overlap vs H33 = 0.219, vs NHR = 0.407. The candidate
therefore samples a different habitat than both the champion lineage and
the stopped proximity lane — the property that gives an independent ranking
option value against expert labels neither proxy can see.

## 4. Uniqueness: X1 failed, X2 fixed the instrument (identical bytes)

Under Amendments D-1+D-2 as first applied (X1), the lane **failed**:
surface provisional top-k excess 0.948; final worst excess 0.807 (5
firings, all against 201k–624k-dot fields). Calibration on independently
lineage-measured distinct family lanes showed the same statistic also
rejects GEMSDOE70 (1.000), GEMSDOE49 (0.793) and H33 (0.797) against those
mega-fields — it measures habitat coincidence, not duplication, at
≥5× budget asymmetry (`evidence/arc/d2_calibration_family_lanes.json`).
Experiment X2 (reserved defect-fix) corrected the instrument
(Amendment D-3: budget-comparability ≤4×; allocator-matched surface
preview; completeness supplement) **without changing any byte**. Under the
corrected gates: worst surface ρ 0.496, worst final ρ 0.089, worst
budget-comparable excess 0.664 (`GEMSDOE37` 80k physics dots), over 990
comparable rasters (+2 invalid files listed). The stopped H79-NHR lane
still fails the corrected gate (3 comparable firings, 0.708–0.767), so the
fix does not whitewash it. All literal readings remain in the evidence;
if the owner reverses D-3/X2 the verdict reverts to negative.

## 5. Can it beat 0.2778 live? What would raise P(win) next

Unknown, and not projected anywhere in this repo. The case for spending
one slot: it is the first candidate here that (i) matches-or-beats the
H33-class control on the blocked holdout without proximity inputs,
(ii) is registry-distinct under a calibrated, discriminating gate, and
(iii) covers habitat (median 894 m, ridge-concordant lines) that neither
H33's broad field nor NHR's tight halo sampled the same way. The case
for caution: holdout margins are thin, shoreline-riser mimics leak through
any ridge detector, and expert-fault geography may still favour H33's
broader field. Either way the organizer receipt from this upload is the
only measurement that resolves it — record it in
`registry/score_ledger.csv` with the raster SHA-256 when it exists.
