# Session review — 2026-10-22, lane G79B-SCARP-DIPOLE-GEOAND

Branch `arena/e2f3892f-gemsdoe79`. One preregistered experiment, zero
competition slots, verdict **negative**. All performance numbers below are
**HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, spatially blocked
hide-and-recover on the visible catalogue) unless labelled otherwise.
No number here is a leaderboard score or projection.

## What was asked vs what the evidence supports

The owner required a *new unique* TIF, an obvious download/submit verdict,
a PhD-level explanation of the family-best H33 file (0.2778, unverified),
3–5 ranked new hypotheses, holdout validation of the top candidate before
any slot is spent, and a JSON run card. All were delivered. The honest
scientific outcome is that the new candidate **does not beat the current
holdout best**, so the site verdict is **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**.

## Why H33 leads the family (re-verified from bytes this session)

- H33 = D2.8 with dots ≤2 px from the catalogue deleted: 44,090 → 37,654
  isolated binary dots, 0 disagreements with the rule, 0 adjacent pairs
  (`scripts/analyze_h33.py`, `evidence/h33_forensics.json`). It is an
  emission refinement of an existing surface, not a new model.
- Mechanism under the official metric (α=0.2, β=0.8, 300 m triangular
  kernel, max-over-kernel TP, summed FP): isolated 1.0 dots cover truth
  without paying FP for redundant neighbouring mass; catalogue-hugging
  dots mostly echo already-mapped faults (exact known pixels are masked
  in scoring) so their marginal TP credit is low and deleting them helps.
- The 0.2778 figure remains an **UNVERIFIED HISTORICAL REPORT** (no
  submission-page receipt links it to these bytes). The live public
  leaderboard read 2026-10-22 is led by 0.4413 (PUBLIC-OBSERVATION).

## Experiment 1 (the only experiment run)

Surface: `sqrt(geomean(rank lapneg, rank lappos, rank step) × max(rank
gravity HG, rank TMI HG)) × road factor` on lidar-supported cells;
37,654 dots, spacing 3 px, >2 px from (visible) catalogue. Preregistered
in `registry/preregistration_g79b.json` (SHA-256 pinned before compute).

| Arm (HOLDOUT-DTI) | Seed 20 (n=11,321) | Seed 30 (n=11,342) |
|---|---:|---:|
| **Candidate** | 0.0530 | 0.0449 |
| lidar_only control | 0.0568 | 0.0456 |
| geo_only control | 0.0340 | 0.0366 |
| uniform-random control | 0.0538 | 0.0504 |
| fold-fair H33 control | 0.0961 | 0.0989 |

Candidate − H33 control: −0.0431 [−0.0603, −0.0244] and −0.0540
[−0.0698, −0.0380] (paired 95% CIs exclude 0). Leakage canaries: 72/72
pass (max symmetric AUC 0.6553 ≤ 0.90). The preregistered Experiment-2
contingency condition was **not** met (candidate−lidar_only CIs include 0),
so no second experiment was run.

**Physical interpretation.** The lidar dipole bands do carry fault signal
(pixel AUC ≈ 0.58; mean rank 0.46 on catalogue vs 0.36 far away), but at
100 m aggregation their upper tail is dominated by ordinary high-relief
texture — every ridge crest/gully base pair, shoreline benches and channel
banks — so per-pixel top-ranked dots recover hidden faults at chance. The
supplied gravity/TMI horizontal-gradient ranks are at chance (AUC ≈
0.49–0.51) and the AND with them only dilutes. This reproduces, with a new
mechanism, the pattern across 110 family submissions: **per-pixel surfaces
fail; lineament-level corroboration is what survives** (the h19-5/D2.8
lineage). A secondary caveat: the fold-fair H33 control's *surface* was
derived historically with full-catalogue knowledge (only its pruning is
redone per fold), so 0.096–0.099 is an optimistic bar; the candidate still
fails against the unbiased uniform control, so the negative verdict does
not depend on that asymmetry.

## Uniqueness (scoped, operative definitions)

Surface before placement: max |Spearman| = 0.1093 vs 18 restored top
family rasters (limit 0.90). Final dots: max 3 px forward overlap 0.4147
(Option B and C; limit 0.70), max |Spearman| of the final raster 0.0192.
The literal >0-support rule still returns 1.0 vs the full-footprint
E-proba witness for *any* candidate (Decision D-1, IR-79-24/31);
`protocol_unique` therefore remains **false** and the 992-raster registry
was not fully re-scanned this session.

## Artifact

`g79b-scarpdipole-geoand-E1-20261022-5cb0eb8f-DO-NOT-SUBMIT.tif`,
SHA-256 `16a6e07f97441b6b5431ca24b7481658cdb7b7f59daec0e69070f7d5fc8cf795`
(single-band float32, EPSG:32611, 3730×3292, values in {0,1}, 37,654 dots,
min spacing 3.0 px, no dots on catalogue or outside footprint; shared
validator PASS). Prior lane E1 preserved byte-identically
(`evidence/run_card_g79_e1.json`, artifact in `archive/g79_e1_fabric_offset/`).

## Recommended next lane (requires fresh owner authorization + preregistration)

**Strike-coherent lineament aggregation before emission.** The one
quantitative clue this session produced — weak but real pixel AUC ≈ 0.58
for scarp-dipole bands — combined with the family-wide success of
"multiline-corroborated" surfaces points to aggregating scarp evidence
along locally straight, strike-consistent line segments (e.g. Radon/Hough
accumulation over 0.5–2 km windows using the lidar `coh100`/`strike`
bands), then corroborating *lines* (not pixels) against an independent
potential-field lineament set, and only then dotted max-cover emission.
Expected cost: medium (CPU, cached bands only). Named mimic: contour-
parallel Lahontan shoreline segments and road/canal alignments, which are
also line-coherent — a contour-parallelism penalty using detrended
elevation would need preregistration as part of the design.

## Limitations that remain

1. No ORGANIZER-CONFIRMED score exists for any artifact here; the account's
   weekly capacity and eligibility are not observable from this sandbox.
2. Inputs are SHA-256-pinned owner GitHub mirrors of the competition data;
   organizer origin is not independently authenticated (login-walled).
3. Uniqueness was checked against 18 restored comparators, not all 992
   registry rasters; Decision D-1 needs a protocol-owner ruling.
4. Lidar support covers 3,892,984 of 5,167,373 footprint cells; any
   lidar-based lane is blind in the remaining ~25%.
5. Public-site deployment state is verified by the repo's Actions
   workflow after merge; this sandbox cannot fetch github.io.
