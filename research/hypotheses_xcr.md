# Five new candidate hypotheses — G79-XCR session (2026-10-22)

Every earlier lane in this repository validates on the same instrument: hide mapped
catalogue faults and recover them. The competition truth is the **opposite
population** — expert faults that are *not* in that catalogue. This session
measured whether the two populations are driven by the same features. They are
not (numbers below, `evidence/xcr/canaries_seed20.json`). That measurement
re-orders the hypothesis list.

Instrument I2 is new and is the reason the ranking changed: truth = SGMC fault
pixels more than 3 px from the competition catalogue (62,122 px, measured in
`evidence/xcr/sgmc_overlap.json`). SGMC is a different mapping campaign and is
never a model feature.

## Measured single-feature separation (symmetric AUC, 4 folds, seed 20)

| Channel | I1 hidden catalogue faults | I2 SGMC off-catalogue faults |
|---|---|---|
| `dens_visible_40` (catalogue corridor density) | **0.72 – 0.79** | 0.47 – 0.55 |
| `log1p_d_visible` (distance to mapped fault) | 0.78 – 0.84 (inverted) | 0.43 – 0.53 |
| `det_elev_relief_s5` (detrended-elevation relief) | 0.53 – 0.68 | **0.75 – 0.79** |
| `elev_step_s2` (detrended-elevation step) | 0.55 – 0.68 | **0.75 – 0.78** |
| `strain2inv` (geodetic strain magnitude) | 0.51 – 0.55 | 0.54 – 0.67 |
| `ieq_density` (seismicity) | 0.48 – 0.52 | 0.37 – 0.67 |

Read the two columns together: the feature that wins I1 is the *worst* channel
class on I2, and the channels that win I2 are mediocre on I1. Any surface
optimised on I1 alone is therefore pushed toward catalogue proximity — which is
also exactly what all 937 archived registry dot fields look like.

## Ranked hypotheses

### H1 — Bedrock-scarp / range-front roughness targeting (implemented this session, G79-XCR)
- **Layers:** detrended elevation (band 12), detrended-elevation slope (19), plus
  catalogue corridor density as a weak prior.
- **Physical signature:** `relief × step` of detrended elevation — the geometric
  roughness that an active fault scarp imposes on a mountain front, independent
  of any mapped trace.
- **Why it catches unmapped faults:** it is measured from the surface, so a fault
  that was never drawn still shows its scarp and its footwall relief. On I2 the
  channel reaches AUC 0.79, the best transferable single channel measured here.
- **Difference from existing work:** `scarp_unified_*` (THVC group C) uses LiDAR
  scarps *with* catalogue context; `h20-dem10-scarp-thin` and `lidarscarp-ridge`
  threshold the same family on the catalogue instrument. This lane is the first
  to rank a surface against an **off-catalogue** truth set.
- **Cost:** low (bands already on disk). **Expected gain:** moderate on I2,
  little on I1. **Measured:** I1 0.1234 / 0.1211; I2 0.19–0.28 per fold, beating
  its uniform control 4/4 on seed 20. **Verdict: negative on promotion, because
  the catalogue-density half of the blend makes it a registry duplicate (18
  like-for-like firings).**

### H2 — Pure off-catalogue terrain surface (no catalogue term) — highest priority next
- **Layers:** 12, 19, plus 15 (depth to basement) and 13 (isostatic gravity).
- **Physical signature:** fault-controlled range fronts and basin-margin steps,
  with no distance-to-catalogue channel anywhere in the model.
- **Why it catches unmapped faults:** with the catalogue term removed the surface
  cannot reproduce the family's emission shape, so it satisfies the novelty rule
  by construction rather than by jitter, and its ranking is driven by the I2
  channels that actually transfer.
- **Difference:** every archived lane, including H1, mixes in catalogue
  proximity. H1's own failure is the evidence: remove the term and the duplicate
  disappears.
- **Cost:** low (re-run this pipeline with 14 → 12 channels and a fixed budget
  sweep). **Expected gain:** unclear on I1 (likely lower), potentially the only
  route to a non-duplicate leaderboard entry.

### H3 — Conjugate-transfer-zone prediction from strain-tensor rotation
- **Layers:** 4 (second strain invariant), 7 (shear rate), 8 (dilatation rate)
  with the local catalogue strike field.
- **Physical signature:** angular misfit between the geodetic maximum-shear
  direction and the mapped fault strike. High misfit = the mapped fabric is not
  accommodating present-day strain, so an unmapped structure must be.
- **Why it catches unmapped faults:** it is defined on the *mismatch*, so a
  well-mapped fault scores low by construction.
- **Difference:** THVC's `transtension_conduit_idx` and MRND's regime kernels use
  strain magnitude, not strike misfit. Measured AUC on I2 for `strain2inv` is
  only 0.54–0.67, so this is speculative.
- **Cost:** medium (needs a stable local strike field from the visible mask).
  **Expected gain:** unknown; not validated.

### H4 — Conductivity–basement triple conjunction for buried faults
- **Layers:** 15 (depth to base surface), 17 (conductivity surface), 12.
- **Physical signature:** a linear basement step that is *also* a conductivity
  lineament and has *no* topographic expression.
- **Why it catches unmapped faults:** a surface-geology catalogue systematically
  misses faults buried under basin fill; this is the signature of exactly that
  population.
- **Difference:** THVC uses `bdepth_hgm_*` and conductivity as separate members;
  the conjunction ("basement step AND conductive AND topographically blind") is
  not a member of any archived lane.
- **Cost:** low. **Expected gain:** unknown. Measured AUC on I2 is weak
  (`bdepth_grad_s3` 0.32–0.50), so this may not replicate.

### H5 — Fault-population spacing gap-filling from the mapped length distribution
- **Layers:** catalogue geometry only (no physics).
- **Physical signature:** fault spacing scales with mechanical-layer thickness and
  is log-normal; anomalously wide gaps in the local spacing sequence are where
  the population is incomplete.
- **Why it catches unmapped faults:** it predicts the *missing member* of a
  mapped population rather than extending a mapped trace.
- **Difference:** `GEMSDOE27 topo-gap-closure` and `GEMSDOE70` already exploit
  catalogue gaps and scored 0.2449 / 0.2478 on the real leaderboard, so this is
  the strongest *known* leaderboard direction — and also the most likely to be a
  duplicate.
- **Cost:** low. **Expected gain:** moderate on the leaderboard, near-zero
  novelty.

## Why H1 was implemented and why it failed

H1 was ranked first on implementation cost and on the strength of the only
channel that transfers to the off-catalogue population (AUC 0.79). It produced a
format-compliant, byte-unique GeoTIFF whose I2 score beats its own uniform control
in 4/4 folds. It still fails, because blending in catalogue corridor density
(needed to compete on I1) reproduces the family's dot geometry: 18 registry
rasters already contain more than 70% of its dots within 3 px. That is the
central negative result of this session, and it is the strongest argument for H2.
