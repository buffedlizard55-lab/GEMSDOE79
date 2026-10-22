# Candidate hypotheses — session 2026-10-22 (lane G79B)

Written BEFORE computing any new surface. Evidence base: this repo's score
ledger (110 family submissions, all `UNVERIFIED HISTORICAL REPORT` — no
organizer receipts), `knowledge/why_h33.md` raster forensics, the post-stop
holdout diagnostic (`evidence/post_stop_diagnostic.json`), and the live public
leaderboard read 2026-10-22 (#1 = 0.4413 PUBLIC-OBSERVATION; the prompt's
"0.3195 highest" is stale — it would rank ≈22nd today).

## What the family score pattern actually proves

1. **Emission geometry dominates.** Every family score ≥ 0.23 is a sparse,
   isolated, binary dot field (≈37–44k dots, no 8-neighbour duplicates,
   pruned away from the catalogue). Continuous probability fields of the
   SAME parent surfaces score far lower (h19-5 continuous 0.1922 → dotted
   D2.8 0.2600). Reason: the official metric takes a **max** over the 300 m
   triangular kernel for TP but **sums** p(x)·(1−k) for FP — redundant
   nearby mass is pure FP cost. Isolated 1.0 dots at ≥300 m spacing are the
   near-optimal emission for a given ranking surface.
2. **H33 (0.2778, user-reported, unverified) is not a new model.** Byte
   forensics in this repo show H33 ≡ D2.8 with the 6,436 dots within 200 m
   of the known catalogue deleted (44,090 → 37,654; 0 disagreements).
   Its gain is consistent with removing catalogue-echo dots whose marginal
   TP credit is low: hidden test faults are NEWLY mapped faults, so dots
   hugging known traces mostly re-find what is already mapped (scoring
   masks exact known pixels) while paying FP on the 1–2 px halo.
3. **Single-physics novel lanes repeatedly fail live** (Euler depth 0.03–0.10,
   worm persistence 0.058, SGMC off-catalogue 0.05, basement step 0.0009,
   supervised HGB 0.029–0.042, lidar-scarp-only 0.04–0.16). The surfaces
   that survive are **multi-evidence corroboration** surfaces (h19-4/h19-5
   "multiline-corroborated" lineage) — agreement of independent evidence
   suppresses each sensor's characteristic false positives.
4. **This repo's own holdout instrument** (gems57-pooled-hide-v2, seeds
   20/30, 37,654 dots, spacing 3) gives: uniform random 0.0504/0.0496,
   E1 fabric-offset 0.0474/0.0466 (dead lane), fold-fair H33 control
   0.0961/0.0989. The bar for any new lane is beating the fold-fair H33
   control on the same instrument — not a leaderboard projection.

## Candidates (ranked by expected DTI gain ÷ implementation cost)

| Rank | Hypothesis (layers) | Physical signature | Why it can catch an UNCATALOGUED fault | Difference from prior art | Cost | Named non-fault mimic |
|---|---|---|---|---|---|---|
| **1 — selected** | **Scarp-dipole × potential-field edge AND-consensus.** Lidar 1 m-DEM derivatives `lapneg_max`+`lappos_max`+`step_max` (100 m aggregates) AND max(isostatic-gravity horizontal gradient band 18, TMI horizontal gradient band 3); TIGER road-distance suppression | A degraded normal-fault scarp has a paired crest-convexity / base-concavity Laplacian dipole plus a short-wavelength step; the same fault at depth juxtaposes density/susceptibility contrasts → gravity OR magnetic edge. Surface = sqrt(lidar-dipole geomean × edge-rank max) × road factor, rank-based, no fitted parameters | The public catalogue predates systematic 1 m lidar mapping; sub-2 m basin scarps are invisible on 10 m DEMs but produce a LoG dipole at 1–2 m. New expert test labels were mapped with modern data, so they should be enriched exactly in such scarps. The AND with a subsurface edge rejects purely surficial lineaments | Prior lidar lanes used scarp strength/top-% ridges ALONE; prior geophysics lanes used edges ALONE; r11f fused scarp+radiometrics (not dipole pairing, not potential-field AND, no road suppression). The lapneg×lappos×step triple geomean gated by an independent-physics edge is not in this repo or the inspected sibling records | Low: rank transforms of hash-pinned cached bands, CPU minutes, no new external data | **Lake Lahontan paleo-shoreline benches** (wave-cut crest/base dipoles along contour-parallel terraces), canal/levee embankments, mine benches |
| 2 | Strike-continuation + relay-stepover geometry from the visible catalogue only (fault-tip extrapolation along local strike, stepover bridges between en-échelon tips) | Geometric: dots along strike-projected rays beyond mapped tips, weighted by tip density | Catalogue traces end where mapping stopped (cover, access), not where faults end | Tried repeatedly in family (continuation 0.046, tiprelay 0.016); the one high score (analog-tip-stepover 0.2632) sat on the D28 base surface, so its independent value is unproven. Catalogue-derived → must be recomputed per fold from visible faults only | Medium-high | Projected rays crossing unfaulted ground; curved range fronts violate straight-strike assumption |
| 3 | Geodetic strain localization (bands 4/7/8: 2nd invariant, shear, dilatation) × seismicity intensity (band 16), dotted | Interseismic strain-rate maxima localized on active structures | An actively straining blind fault can lack both scarp and catalogue entry | Not tried as a primary surface in the ledger; but strain grids are smoothed over km–10s km, so 100 m dot precision is mostly illusory — expected precision too low for the 300 m kernel | Low | **Groundwater-extraction subsidence** in agricultural basins; volcanic inflation (Long Valley fringe) |
| 4 | Depth-to-basement step (band 15 gradient) AND gravity edge | Fault offsets basement → step in sediment thickness | Buried basin-bounding faults with no surface expression | Family h61a basement-step scored 0.0009 live. Also depth-to-basement is itself inverted from gravity → the "AND" is partially circular, not independent evidence | Low | Depositional pinch-outs, buried paleochannels, gravity-inversion non-uniqueness |
| 5 | PU-learned ranker (gradient boosting, catalogue positives vs unlabeled, spatial CV, catalogue-distance features excluded) on all 19+12+8 bands | Learned multivariate ranking | Could combine weak evidence nonlinearly | Family HGB/supervised lanes scored 0.029–0.042 live despite dotted emission — supervised-on-catalogue learns mapper bias ("looks like a mapped fault's neighbourhood"), which anti-correlates with unmapped-fault discovery. Rejected as primary on that evidence | Medium | Mapper-bias leakage; flight-line and DEM-tile artifacts learned as signal |

## Decision

Implement **Rank 1 (G79B-SCARP-DIPOLE-GEOAND)** exactly as preregistered in
`registry/preregistration_g79b.json`. No fitted model, no catalogue-based
features (catalogue is used only as a placement exclusion mask, derived from
visible faults only inside each holdout fold), no prior prediction raster
enters the surface. Emission: 37,654 isolated binary dots, min spacing 3 px,
placement excluded within 2 px of the (visible) catalogue — the H33 emission
lesson applied fold-fairly to every placed control arm too.

Promotion gate (fixed in advance): pooled HOLDOUT-DTI must beat the
fold-fair H33 control and every matched control (lidar-only, geo-only,
uniform) with paired 95% CI lower bound > 0 on both seeds 20 and 30.
Anything less = verdict **negative**, TIF still generated and clearly
labelled DO NOT SUBMIT. No leaderboard score is projected from holdout.

No new external data is required: all inputs are the SHA-256-pinned cached
stack restored this session (`registry/data_manifest.json`, 13/13 verified).
The free official sources behind them are USGS GeoDAWN
(https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
USGS 3DEP 1 m DEMs (via the competition's `1m_DEM_links.csv`), and Census
TIGER roads — all already mirrored as pinned derivatives; no new download is
on the critical path.
