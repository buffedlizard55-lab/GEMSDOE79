# Why H33 scored 0.2778, whether >0.2778 is reachable, and the H79-COV test

Session `e23d5371`, 2026-10-22. Labels: **HOLDOUT-DTI** (evaluator
`gems57-pooled-hide-v2`, spatially blocked hide-and-recover), **USER-REPORTED**
(prompt filename→score pairs; no organizer receipt in this repo),
**RASTER-MEASUREMENT** (counts from actual bytes), **ESTIMATE** (algebra under
stated assumptions). No file in this repo has an ORGANIZER-CONFIRMED score.

## 1. Why H33 got the family's highest score (verified from bytes, not websites)

Full prior derivation: [`reports/nhr_analysis.md`](nhr_analysis.md) and
[`knowledge/why_h33.md`](../knowledge/why_h33.md); byte forensics in
`evidence/h33_forensics.json` (re-derived from the restored registry rasters).

1. **The metric pays for sparse dots.** Officially
   ([problem description, Performance metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric),
   re-read line-by-line this session and matched against
   `vendor/gems57/metric.py`): TP is a per-truth-pixel **max** over a 300 m
   triangular kernel; FP is a per-prediction **sum**; DTI = TP/(TP+0.2·FP+0.8·FN).
   One binary dot on a trace, spaced 3 px from its neighbours, earns ≈2.33
   truth units of TP and pays ≤1 unit of FP. Continuous probability maps pay
   FP on every positive cell for the same TP. Every top family entry is a
   binary dot field for this reason alone.
2. **H33 = D2.8 minus pure false positives** (RASTER-MEASUREMENT): H33's
   37,654 dots are *exactly* D2.8's 44,090 dots with the 6,436 dots within
   200 m of a mapped fault removed (0 added, 0 moved, 0 rule disagreements).
   Mapped pixels are masked from scoring, so collar dots could only pay FP.
   USER-REPORTED effect: 0.2600 → 0.2778 (+6.8% from deleting 14.6% of dots).
   ESTIMATE under zero-TP for removed dots: H33 captures ≈39–41% of public
   truth credit; a score of 0.2778 mathematically requires ≥23.6%, and the
   public leader's 0.4413 (USER-REPORTED) requires ≥38.4%.
3. **Its geography is broad, not a halo:** median dot 1.96 km from the
   catalogue; 69.8% of dots >1 km away. That matches a test set of
   expert-identified faults *absent* from the USGS database — by construction
   not re-traced catalogue strands.

## 2. Can a new submission beat 0.2778? What the evidence now says

Beating 0.2778 needs a ranking whose top ~37.7k dots capture **more than
~40% of expert-truth credit** at no worse FP cost, from structures the
catalogue missed. This repo has now tested four independent ways to rank,
all on identical folds/evaluator/budget:

| Lane (all HOLDOUT-DTI, seeds 20/30, n≈11,321/11,342) | Candidate | H33 control | Registry-unique? |
|---|---|---|---|
| H79-NHR — catalogue-geometry nested-hide HGB | 0.1431 / 0.1522 | 0.0961 / 0.0989 | **No** — 26 ordinary dot fields >0.70 overlap (median dot 0.54 km from catalogue) |
| G79B-SDPT — terrain-only dipole/trace | 0.111 / 0.121 | (A1 control 0.109/0.114) | No unconstrained (99 priors >0.70); unique-capped version fell below its control |
| G79-STEPCO — multi-field step dipoles | 0.0946 / 0.0948 | 0.0961 / 0.0989 | Fired on space-filling priors |
| **H79-COV (this session)** — antithetic polarity + covered basement-step persistence, catalogue-free | **0.0610 / 0.0581** | 0.0961 / 0.0989 | (measured in `evidence/cov/`) |

PhD-level judgement, with the confound stated plainly:

- **Hide-and-recover rewards proximity.** Withheld catalogue components
  cluster in mapped fault systems, so catalogue-geometry features win the
  proxy (NHR) — but those same dots duplicate 26 prior fields and, worse,
  target exactly the population the organizer's experts already mapped.
  Optimising the proxy harder moves *away* from the test population.
- **The genuinely off-catalogue signal tested here is weak.** H79-COV's
  paired Δ vs uniform is +0.0126 [0.0002, 0.0249] / +0.0099 [−0.0018, 0.0219):
  antithetic scarps and covered basement steps, as encoded in the pinned
  100 m stack + u8 lidar derivatives, carry little recoverable information
  about catalogue-like faults, and the seed-30 interval includes zero.
  Either the blind-fault population is largely invisible in these layers at
  100 m, or it needs the 1–10 m data (DEM drainage/scarp morphometry) that
  this sandbox cannot fetch.
- **Therefore: no lane in this repo has demonstrated a registry-unique
  surface plausibly above 0.2778, and this session does not claim one.**
  The honest paths that remain are (a) new *data* (USGS 3DEP 10 m DEM +
  1 m DEM links drainage-deflection and true scarp morphometry; USGS ComCat
  seismicity lineations; GDR wellspring/vent alignments — the CSVs are
  already pinned), and (b) a user decision on whether the selector may spend
  a slot on a Final-Round-oriented map (expert-expanded labels reward
  verifiable new structures even at modest Initial-Round DTI). Both are
  stated as next steps, not executed here: the lane budget for this session
  was one preregistered hypothesis, and C2/C3 were reserved for defect fixes.
  The H33/uniform controls reproduced the previous session to 4 decimals,
  so there is no defect to fix.

## 3. This session's artifact

A newly generated, format-valid, registry-measured GeoTIFF (see
`run_card_cov.json`). It **failed the preregistered holdout gate on both
seeds**, so the automated decision is **OK TO DOWNLOAD: YES — OK TO SUBMIT:
NO**. The file name carries `DO-NOT-SUBMIT`; `scripts/submission_status.py`
exits 2; no human inspection is involved in the decision. Negative results
are deliverables: H79-COV eliminates "facing polarity + covered-step
persistence at 100 m" as a route past H33, which redirects effort to the
data-limited hypotheses ranked in `research/hypotheses_g79cov.md`.
