# Why H33 scored highest, and what H79-FFAS measured

Session `c04e5e27`, 2026-10-22. Evidence labels: **HOLDOUT-DTI** is the
spatially blocked hide-and-recover proxy (evaluator `gems57-pooled-hide-v2`).
**USER-REPORTED** is a filename-to-score pairing from the prompt with no
organizer receipt. **PUBLIC-LEADERBOARD** is a team score, not a file hash.
Nothing here is ORGANIZER-CONFIRMED for a file produced by this repo.

## 1. Why the named H33 file sits at the top of the family table

Byte forensics (`knowledge/why_h33.md`, `evidence/h33_forensics.json`):

- H33 is **exactly** D2.8 with every dot within 200 m (2 px) of the catalogue
  deleted: 44,090 → 37,654, zero H33 dots outside D2.8.
- The metric's TP is a **max** over a 300 m triangular kernel; FP is a **sum**.
  Sparse dots therefore dominate probability maps. One well-placed unit dot
  can credit ~2.33 truth pixels and pays at most 1 FP.
- Known-fault pixels are masked
  ([staff clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)),
  so catalogue-hugging dots are pure FP. Removing them is the 0.2600 → 0.2778
  USER-REPORTED step.
- Every USER-REPORTED score above 0.2478 in the family table is the same
  h19-5 root surface under different emission rules, not nine independent
  detectors. Genuinely non-duplicate landmarks max out near 0.2478 (GEMSDOE70).

A public score of 0.2778 needs at least ~23.6 % of truth credit; 0.4413 needs
~38.4 % (`reports/nhr_analysis.md`). Closing that gap is a better detector of
*expert-unmapped* faults, not another packing of the same range-front ridges.

## 2. Why a new near-field detector cannot be submitted

H79-NHR learned nested hide-and-recover and **beat** the H33 holdout control
(0.1431 / 0.1522 vs 0.0961 / 0.0989) with a clean canary. It still failed the
duplicate gate: 26 ordinary registry dot fields each contain > 70 % of its
dots within 3 px (worst 0.913 vs chance 0.610). Those fields occupy the
300 m–2 km halo around mapped faults — exactly where withheld catalogue
segments live. STEPCO and G79B hit the same wall.

The remaining spatial vacancy is **far-field** (H33's own median is 1.96 km
from the catalogue; 70 % of its dots are > 1 km away) *and/or* a polarity
the range-front detectors do not rank first (uphill-facing / antithetic).

## 3. H79-FFAS: the test

Preregistered closed-form lidar score, no learner:

```
raw = (downface_max + 2·upface_max) · step_max · coh100 · cross_max · ex_max
      · logistic(EDT(visible); d0=8 px, s=3 px)
```

then footprint mid-ranks, a 2 px visible-echo collar, 37,654 dots at 3 px
spacing. Inputs: the pinned USGS 3DEP lidar u8 stack only.

Leakage canaries (HOLDOUT, both seeds): max symmetric AUC **0.8387 / 0.8481**
on `logistic_farfield` (limit 0.90) — **PASS**.

HOLDOUT-DTI (`gems57-pooled-hide-v2`, 4 spatial folds):

| Arm | Seed 20 | Seed 30 |
|---|---|---|
| candidate (boosted antislope × far-field) | **0.0422** [0.0288, 0.0558] n=11,321 | **0.0367** [0.0279, 0.0452] n=11,342 |
| ablation: no far-field weight | 0.0579 [0.0438, 0.0731] | 0.0507 [0.0404, 0.0607] |
| ablation: equal polarity (boost=1) | 0.0408 [0.0275, 0.0543] | 0.0363 [0.0275, 0.0449] |
| uniform control | 0.0500 [0.0448, 0.0552] | 0.0498 [0.0449, 0.0541] |
| H33 fold-fair control | 0.0961 [0.0837, 0.1086] | 0.0989 [0.0842, 0.112] |

The candidate is **below** both the H33 control and the uniform control on both
seeds. The far-field logistic is the main cause: dropping it raises DTI by
about +0.016 / +0.014, still far below H33. Upface boosting vs equal polarity
is a wash (~0.001).

This is the distribution-shift predicted in `research/hypotheses_ffas.md`
before the run: the holdout's truth *is* withheld catalogue, which sits near
the remaining visible traces. A method that down-weights that band must lose
the proxy even if it would be the right prior for expert-unmapped faults.

X2/X3 were reserved for defect fixes, not holdout tuning. No second experiment.

## 4. Can we beat 0.2778?

Not with this artifact, and not by copying H33. A better public score needs a
detector that (a) is spatially unlike the 26 near-fault family fields **and**
(b) still covers the expert-unmapped traces the organiser scores. The
catalogue-holdout cannot certify (b). Only an ORGANIZER-CONFIRMED receipt can.
No weekly slot is used for a file that lost its holdout control.

## 5. IR-79-53

The 30 space-filling registry rasters are no longer a universal blocker for
this lane: the shared tool's `informative-halo-v4` overlap test fires only
when the prior's own 3 px halo covers ≤ 70 % of the allowed domain (IR-79-82).
Spearman, byte identity and decoded identity still apply to every raster.
Copies of H33 or of the 26 near-fault fields still fail.
