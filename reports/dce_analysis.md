# H79-DCE analysis — what decorrelation costs

*Session `31f55b3a`, 2026-10-22. Lane preregistered in
`registry/preregistration_dce.json` before any result. Every number below is
copied from the evidence JSONs in `evidence/dce/`.*

## Question

The previous lane (H79-NHR X1) beat the H33 fold-fair control on the holdout
(0.1431 / 0.1522 vs 0.0961 / 0.0989) but stopped as a registry duplicate: 26
ordinary registry dot fields each held > 70 % of its dots within 3 px, worst
0.913. Two shared-tool amendments (IR-79-57 vacuous beyond-chance test,
IR-79-58 not-comparable exclusion) removed the *space-filling* part of that
blocker, but the ordinary-raster collisions remain — they can only be fixed by
changing where dots are placed. H79-DCE tested the placement-time fix: keep the
X1 surface byte-identically, but emit a 300 m tile-cover with a 200 m catalogue
collar under a per-raster 0.68 collision ceiling.

## Design (frozen before the result)

- Surface: the X1 stack rebuilt from the same seeds; the rebuilt surface
  SHA-256 matches the frozen X1 receipt, so no retuning of the stopped lane
  happened (gate g0 of the preregistration).
- At-risk set: scan this lane's own *uncapped* emission against all 960
  ordinary (chance ≤ 0.70) registry rasters before touching the holdout;
  freeze every raster with uncapped overlap > 0.50 as capped. Result: 182
  rasters frozen (worst uncapped overlap 0.926, chance 0.612 — the same
  coverage-v3-wide raster that topped X1's list).
- Emission: one dot per 300 m tile at the tile's argmax expected kernel
  credit, no dots within 200 m of the visible catalogue, a candidate tile is
  skipped when any capped raster containing it has spent
  `floor(0.68 × 37,654) = 25,604` in-halo dots; later-ranked tiles fill the
  budget. Deterministic stable order, per-raster receipts.
- Holdout: the shared evaluator (`gems57-pooled-hide-v2`, 4 quadrant folds,
  buffered hide-and-recover, seeds 20 and 30) with six arms per seed:
  candidate, cover-uncapped, top-k + collar, X1-recipe reproduction, H33
  fold-fair control, uniform control.

## Result

| arm | seed 20 | seed 30 |
|---|---|---|
| **candidate (capped cover)** | **0.1019** [0.0888, 0.1153] | **0.1048** [0.0887, 0.1217] |
| cover, uncapped | 0.1210 [0.1071, 0.1358] | 0.1229 [0.1060, 0.1405] |
| top-k + collar | 0.1463 | 0.1524 |
| X1 recipe reproduction | 0.1462 | 0.1522 |
| H33 fold-fair control | 0.0961 | 0.0989 |
| uniform random | 0.0151 | 0.0151 |

- The candidate beats the H33 control on the point estimate on both seeds
  (+0.0058 / +0.0059) but the paired 95 % CIs include zero (−0.0100, +0.0214)
  and (−0.0102, +0.0215): **not a statistically distinguishable improvement**.
  Frozen gate g3 requires the CI lower bound > 0 on both seeds, so the verdict
  is **negative**.
- Decomposition of the loss from the X1-class arm (0.1462 / 0.1522) to the
  candidate (0.1019 / 0.1048):
  - tile-cover decimation −0.0253 / −0.0295 (cover vs top-k + collar),
  - collision ceiling −0.0191 / −0.0181 (candidate vs uncapped cover).
  The pre-stated limitation (below) is confirmed almost exactly: the cap alone
  costs about what the G79B-SDPT post-hoc cap cost (−0.0176 / −0.0203), and
  the tile-cover costs nearly as much again.
- Sanity anchors: the X1-recipe reproduction arm lands within 0.004 of the
  frozen X1 holdout numbers on both seeds; the H33 and uniform controls
  reproduce the X1-run values to 4 decimals on seed 30; canaries pass
  (max AUC 0.8514 / 0.8589 ≤ 0.90).
- Placement receipts: exactly 37,654 dots, every capped raster at or below
  25,604 in-halo dots (max fraction 0.67998 ≤ 0.68), 254,286 candidate tiles
  skipped by the ceiling.

## What this means for the goal (a unique submittable TIF)

1. **Uniqueness is now a placement problem with a measured price.** The
   emission clears the ordinary-raster duplicate rule by construction, and the
   shared v4 amendments clear the vacuous (space-filling) rasters on measured
   chance. The final scan receipt is in `evidence/dce/uniqueness_final.json`.
   But the price is real: the two decorrelation mechanisms together consume
   the entire X1 gain over the H33 control on this holdout.
2. **The metric, not the model, is the binding constraint.** The X1 surface
   ranks hidden-fault habitat well (its top-k arm still reaches 0.146 / 0.152),
   but the metric pays truth credit per 300 m neighbourhood and charges a
   false positive per dot. Once cover emission forbids neighbouring crest
   pixels and the ceiling forbids the family's already-occupied high-credit
   tiles, the remaining freedom is worth ≈ +0.006 over legacy H33 dots —
   indistinguishable from zero at 95 %.
3. **Leaderboard context (user-cited, unverified):** own best is 0.2778 (H33);
   the public leader is 0.4413. A holdout-tied-with-H33 file has no expected
   leaderboard edge over H33, so spending a weekly slot on it cannot maximize
   P(Win). The negative verdict costs nothing; a slot spent on a
   zero-expected-gain file would.

## Remaining routes (ranked, for a future session)

1. **Hypothesis 2 (strain corridors)** and **3 (antislope asymmetry)** from
   `research/hypotheses_dce.md` — new *physics* that could raise the surface's
   ranking quality itself rather than re-spending the same credit on emission.
2. **Hypothesis 5 (Lahontan shoreline elevation banding)** needs USGS 3DEP
   DEM tiles (free, official, https://www.usgs.gov/3d-elevation-program);
   blocked this session by the outbound-network allowlist.
3. If a future surface beats H33 with CI > 0 *and* its uncapped emission
   already has low registry overlap, the DCE machinery (at-risk scan, capped
   tile-cover, fixed point) is reusable as-is; the 0.68 ceiling and 300 m
   tiles are the knobs the cap cost is most sensitive to.
