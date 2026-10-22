# Candidate hypotheses after G79-CJX-DIR (2026-10-22, this session)

> Naming note: this lane was registered as G79-CJX and renamed G79-CJX-DIR at merge
> after a parallel session merged a different, also-negative G79-CJX implementation
> first (measured non-duplicate; `evidence/cjxdir/collision_measurement.json`).

Scope rule (unchanged): every number below is **HOLDOUT-DTI**
(`gems57-pooled-hide-v2`, buffered whole-component hide-and-recover, seeds
20/30, n = 11,321 / 11,342 withheld positives) or a **registry measurement**;
none is a leaderboard score or a projection of one. Novelty statements are
relative to executable code in this repo and the 25-raster restored subset in
`evidence/cjxdir/uniqueness_restored_subset.json`, not a full-registry census.

## Tested this session: G79-CJX-DIR — NEGATIVE, lane closed

**Layers:** cached `training_features.tif` band 2 (`rtp`) and band 13
(`iso_grav_anom`) only. **Signature:** persistent (σ = 1/2/4 px) edge-weighted
director dispersion `rank(<m>)·(1−C)` required in both fields — a buried
multi-strike junction. **Why it might have caught uncatalogued faults:**
intersections/terminations juxtapose density and susceptibility contrasts even
without a surface scarp, and the statistic is catalogue-free, so it cannot
redraw mapped traces. **Difference from prior lanes:** no implemented lane used
a persistence-qualified doubled-angle coherence statistic; THVC learns a
multi-feature ensemble, E1/fabric-offset measures cross-field lag, G79-MAG is a
plain magnetic edge lane.

**Measured result:** candidate EXP2 HOLDOUT-DTI **0.0256 / 0.0319**, below EDGE
(0.0259 / 0.0338) and UNIFORM (0.0310 / 0.0335); paired deltas ≈ 0 or negative.
The preregistered phase-randomized null **beats** the real single-scale
surface on both seeds (0.0338/0.0324 vs 0.0225/0.0230; paired CI excludes 0 on
seed 20 and nearly on seed 30). Interpretation: in this stack, multi-strike
potential-field junctions are dominated by the named mimics (pluton/caldera
contacts, survey seams) and withheld catalogue strands are predominantly
single-strike, where junction-ness is low by construction. **Do not retune,
re-place or restart this lane** (`run_card_cjxdir.json`, IR-79-172).

## Remaining ranked candidates (not run; each needs its own preregistration and a protocol decision on the literal novelty gate first)

| Priority | Hypothesis | Layers | Signature | Why uncatalogued? | Difference from implemented lanes | Mimic / falsification | Expected value vs cost |
|---|---|---|---|---|---|---|---|
| 1 | **G79-BLC bilateral lithology-contrast change-point** (from `research/hypotheses_e4a4422d.md`) | Same cached stack + `geodawn_rad_u8` / `geodawn_extensions_u8` (rank-only radiometrics) | Along a data-derived potential-field ridge, an abrupt along-strike swap of the two flanks' joint multichannel distributions | A transfer fault offsetting pre-existing contacts under alluvium | Not an edge magnitude, not E1 lag, not a junction (CJX, now falsified) | Facies changes, lava-flow fronts; require gravity concordance + leave-one-survey-block replication | Uncertain/low–moderate; moderate-high cost; data already hash-pinned |
| 2 | **G79-RSS relief-screened structural saddle** (from same backlog) | Bands 12, 19, 13, 18 | Multi-scale detrended-elevation saddles crossed (not followed) by a gravity contrast | Low-relief transfer zones between range segments are under-mapped vs range-front scarps | Starts from terrain topology, not from catalogue endpoints (relay/tip lanes) | Stream capture, wind gaps, landslides; terrain-only ablation must fail | Low/uncertain; moderate cost; cached data |
| 3 | **Anti-junction control surface (new, suggested by the CJX null result — diagnostic only)** | Bands 2, 13 | The complement statistic `rank(<m>)·C` (single-strike coherence) | Tests whether the CJX failure is specifically the multi-strike requirement rather than potential-field edges per se | EDGE control already covers raw magnitudes; this isolates coherence sign | Same seams/plutons; if it merely matches EDGE, coherence adds nothing | Low cost (features cached); value is interpretive, not a submission candidate by itself |
| 4 | **G79-HFR paired heat-flow residuals** (backlog, data-blocked) | USGS Great Basin heat-flow release DOI 10.5066/P9BZPVUC well-point residuals + quality fields | Spatially paired warm/cool residuals about the published conductive background, aligned with an independently inferred corridor | Advective upflow along buried permeable faults with no scarp | Prior lanes used raw temperatures/springs, not background-subtracted paired residuals | Groundwater flow, pumping, borehole corrections; leave-whole-well-clusters-out | Scientifically promising but **not viable until the ZIP is actually acquired and QA'd** (metadata-only access verified previously; binary ingest unverified in this sandbox) |

## Why H33 (reported 0.2778, unverified) sits at the top of the family ladder — and what would be required to beat it

Verified byte lineage (`evidence/h33_remeasurement.json`, re-restored and
hash-checked again this session): H33 = D2.8 (44,090 dots) minus exactly the
6,436 dots within 2 px of the catalogue → 37,654 dots, zero rule disagreements.
The prompt's own score ladder is monotone along this lineage (continuous
H19-5 0.1922 → dotted D2.8 0.2600 → buf-2 H33 0.2778; all unverified historical
reports). The mechanism is DTI arithmetic, not new geology: TP credit is a
**max** over dots per truth cell while FP cost is a **sum** over dots
(`vendor/gems57/metric.py`), and dots near already-mapped faults earn no
organizer credit. Binarizing to spaced dots and pruning the near-catalogue
shell therefore remove pure cost. Every family score above ~0.24 in the ladder
belongs to this lineage or a same-budget off-catalogue re-emission; independent
geometries (Euler, worms, lattices, scarp ML, and now CJX junctions) cluster
far below. Two consequences follow. (1) Beating 0.2778 credibly requires
*marginal-credit-aware placement on a strong corroborated surface*, not a new
weak surface — but close variants of that lineage are duplicates under the
novelty gate by construction, so this session may not simply re-emit them.
(2) Holdout rank does not predict public rank (H33 fold-fair holdout analogue
≈ 0.096–0.099 vs G79-THVC 0.1905/0.1944, never submitted): the holdout rewards
recovering *catalogued* strand geometry, the organizer scores *uncatalogued*
truth. CJX fails even the weaker holdout test and its own null, so there is no
honest basis to project it above 0.2778 — and per protocol a projection is
never written as a score.
