# Candidate hypotheses — session 4f80e0d0 (lane G79-BER)

Written **before any G79-BER holdout result existed** (preregistration:
[`registry/preregistration_ber.json`](../registry/preregistration_ber.json), 2026-10-22).
Ranks are qualitative judgements of expected DTI improvement and implementation
cost, **not scores**. No leaderboard score is projected anywhere in this file.
"Not tried" was checked against `src/`, `scripts/`, `vendor/gems57/`, the
archived lanes in `archive/`, `research/hypotheses*.md` and the family lineage
audit (`evidence/family_lineage_forensics.json`, `knowledge/why_h33.md`).
The objective novelty arbiter remains the registry gate against the 992
hash-verified sibling-repository rasters (amendment D-2,
[`reports/protocol_amendment_D2_20261022.md`](../reports/protocol_amendment_D2_20261022.md)).

## What the byte-level family evidence establishes first (inputs to the ranking)

1. Every user-reported family score above 0.2478 is a subset/superset/re-dot of
   one root surface, `h19-5` multiline-corroborated lines (**RASTER-MEASUREMENT**,
   `evidence/h33_forensics.json`, `evidence/family_lineage_forensics.json`).
   H33 (user-reported 0.2778) is *exactly* D2.8 (44,090 dots) minus the 6,436
   dots within 200 m of the catalogue. Across D2.8 → h33d → h27-4 → h36-1 → H33
   the ≤200 m dot count falls monotonically (6,436 → 3,894 → 2,545 → 2,353 → 0)
   while the user-reported score rises monotonically
   (0.2600 → 0.2632 → 0.2708 → 0.2710 → 0.2778). No artifact-bound organizer
   receipt exists for any of these pairings, so this is a strong
   quasi-experimental pattern, not a causal proof about hidden truth.
2. The best *genuinely independent* family lanes are supervised OOF learners
   with 300 m submodular/cover emission: GEMSDOE70 0.2478 (forward 3 px
   overlap vs H33 only 0.548) and GEMSDOE49 0.2376 (0.434). A dot field that
   shares barely half its halo with H33 still scoring 0.2478 proves the expert
   truth contains substantial mass **off** the h19-5 lines. Single-operator
   geophysics lanes (Blakely worms 0.1917, Radon 0.1627, tilt worms 0.1555)
   form the next tier (**UNVERIFIED HISTORICAL REPORT** scores,
   `registry/score_ledger.csv`; overlaps are **RASTER-MEASUREMENT**).
3. This repo's pooled hide-and-recover instrument rewards catalogue proximity:
   H79-NHR (median dot 539 m from the catalogue) beat the H33 fold-fair control
   by +0.047/+0.053 HOLDOUT-DTI but duplicated 26 ordinary prior dot fields,
   whose unverified historical public scores are only 0.016–0.143; H33's dots
   sit at median 1.96 km with 69.8 % beyond 1 km — close to the
   area-proportional distance profile of the allowed footprint itself
   (`evidence/nhr/distance_to_catalogue.json`). Optimising the pooled
   instrument alone therefore re-enters occupied, publicly weak terrain.
4. Metric algebra (`reports/nhr_analysis.md` §1–3): at H33-like FP mass,
   0.3195 needs ≈1.2× H33's truth credit and the public leader's 0.4413
   (**PUBLIC-LEADERBOARD**, read 2026-10-22) needs ≈1.6–1.7×, or the same
   credit at much lower FP. The gain must come from better *ranking of where
   unmapped faults are*, spread over the full distance profile — not from a
   format trick.

| Rank | Hypothesis, exact layers | Physical signature / transform | Why it should catch a fault *missing* from the USGS/INGENIOUS catalogue | Difference from what this repo already implements | Expected gain / cost | Named non-fault mimic | Data viability |
|---|---|---|---|---|---|---|---|
| **1 (executed as G79-BER)** | **Distance-banded evidence recovery.** All 19 `training_features.tif` bands + NHR static stack; **new**: FFT upward-continuation (h = 200/500/1000/2000 m) horizontal-gradient-magnitude and tilt "worms" of RTP (band 2) and isostatic gravity (band 13) + cross-height persistence; 8-normal step dipoles of `depth_to_base_surf` (15) and `cond_surf` (17); lidar antislope/dipole interactions (`upface_max`, `downface_max`, `lapneg/lappos`, `step_max`, `cross_max`, `coh100`); visible-only tip-distance / strike-alignment / strike-coherence geometry. Distance-to-catalogue is a **stratifier only** (5 bands), never a within-band ranking feature | Separate nested hide-to-recover HGB regressors per distance band, target = official 300 m kernel credit to whole withheld components; fixed budget allocated across bands in proportion to allowed area | A pooled learner spends its budget where the *catalogue* base rate is highest (≤1 km halos) — exactly the terrain the catalogue's mappers and 26 prior dot fields already worked. Expert-only faults must, by construction, be the ones that mapping missed: far-field range fronts, buried basin strands with no scarp, and antislope piedmont scarps. Banding forces the budget into those populations while the new worms/step dipoles give far bands a *buried-fault* signal that does not need a surface scarp | NHR = one pooled model with raw distance/density features (near-collapse measured). STEPCO = hand-built co-location surface, no learning, no banding. G79B-SDPT = terrain-only, no geophysics, no banding, then overlap-capped (cost −0.018/−0.020). No module here computes upward-continuation worms/tilt, stratifies training *and* allocation by distance band, or excludes raw distance from ranking | Highest / medium (CPU; reuses cached NHR static stack and shared evaluator/writer) | Pluvial Lake Lahontan shoreline/terrace risers; lithologic (non-fault) basement contacts produce identical gravity/magnetic worms | All inputs already restored and SHA-256-verified against `registry/data_manifest.json` this session. No new external data |
| 2 | **Basin-buried intrabasinal faults only.** `depth_to_base_surf`, `iso_grav_anom(_hg/_vg)`, `cond_surf`, RTP worms; explicitly restricted to low-relief basin interiors (lidar `relief` low, `det_elev_slope` low) | Co-located step in depth-to-basement + gravity HGM ridge persisting through upward continuation, where *no* lidar scarp exists | Faults under Quaternary basin fill have no surface trace for photo/lidar mapping to catalogue, but offset basement and density; geothermal upflow in the Great Basin is commonly along such buried structures | STEPCO required a topographic step as one of its co-located fields, so truly blind basin faults were excluded by construction; no lane here is basin-restricted | Medium–high if expert labels include geophysically-drawn buried traces; **holdout risk**: withheld catalogue components are mostly surface traces, so the pooled instrument may under-reward it / medium | Buried lithologic contacts and basin-margin onlap edges; survey levelling seams | Inputs present. Viable, but as a *standalone* lane it cannot be validated to beat the pooled holdout best without assuming the very distribution shift under test — hence folded into rank 1's far bands instead of run alone |
| 3 | **Antislope-scarp lane with absolute-elevation shoreline suppression.** Lidar `upface/downface/step/coh100/strike` + absolute DEM | Require uphill-facing (antislope) step dominance along a coherent strike; suppress contour-parallel downslope steps within ±15 m of pluvial Lake Lahontan highstand altitudes (≈1330 m, USGS Benson & Thompson 1987; ≈1335 m, USGS Circular 1267) | Antithetic normal faults face uphill, opposite to shorelines, fan toes and channel banks; regional compilations under-draw short antithetic piedmont scarps | `upface_max` exists only as one raw input (NHR) / one polarity interaction among terrain channels (G79B); no lane requires antislope dominance or does elevation-banded shoreline suppression | Medium / low–medium | Ridge-top sackung and landslide head scarps (also uphill-facing) | **Not viable this session as specified**: needs *absolute* elevation. `det_elev` is detrended; the mirrored DEM10 product (GEMSDOE10 tag `ext/dem10-36343078537`) contains only derivative channels, no elevation vector. Free official source: **USGS 3DEP 1/3 arc-second seamless DEM** (ScienceBase <https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5>; program page <https://www.usgs.gov/3d-elevation-program>). Checked 2026-10-22: the source exists and is public-domain, but this sandbox's egress allowlist (github.com / pypi only) cannot fetch it directly; it would need a GitHub-Actions-style mirror workflow, as prior DEM10/lidar mirrors were made. The antislope *interaction features* (no absolute elevation) are included in rank 1; the shoreline-suppression rule is **not** claimed |
| 4 | **Tip-relay process zones.** Visible catalogue tips + local strike field; lidar scarp bands; gravity worms | Score only (a) ±15° along-strike cones beyond mapped tips and (b) relay zones between overlapping en-échelon tips, with a lateral exclusion so trace-parallel halos get nothing | Compilation traces are truncated at cover/map boundaries; experts re-connect and extend them, and step-overs are a documented Great Basin geothermal structural setting (Faulds-style play fairway) | NHR used `log_dist_visible_tip` as a pooled feature (its worst canary, 0.859) but still dotted laterally; no explicit cone/relay geometry or lateral exclusion exists here. Family tip lanes exist (h33d 0.2632 as a D2.8 derivative; standalone tip-relay 0.0159 at 80 k dots) — lineage suggests tip logic helps only as a modifier, not as the whole map | Low–medium standalone / low | Bedding strike ridges and linear drainages continuing a tip direction by chance | Inputs present. Kept as features inside rank 1, not as the lane |
| 5 | **2-D spatial encoder (U-Net-style) with soft-kernel DTI loss.** 19-band stack + lidar rasters as image channels, multi-km patches | End-to-end spatial context: trace continuity, en-échelon pattern and range-front morphology learned at 1–5 km scale, trained directly on a differentiable 300 m-kernel Tversky surrogate | Experts draw *traces*, integrating kilometre-scale context that per-pixel tabular models cannot see; the official reference solution is a U-Net, and the 0.4413 leader's required truth credit (≈65 % at H33-like FP) is far above every tabular family lane | Nothing in this repo trains a convolutional model; all lanes are per-pixel HGB or hand-built surfaces | Potentially highest ceiling / **not feasible here**: this sandbox has 2 CPUs, ≈3.8 GB RAM and no GPU (measured this session); reference-solution training is GPU-oriented. Proposing it as this session's lane would be proposing an unvalidatable idea | Same scarps/shorelines, now with larger receptive field to overfit them | Data obtainable (same mirrored stack), compute is not. Named here so the ranking is honest about the likely leader mechanism and the local limitation |

## Why rank 1 is the lane

It is the only candidate that simultaneously (i) follows the repo's own
recorded next steps (far-field banded ranking, distance-band reweighting of the
nested target, surface uniqueness checked *before* placement), (ii) can be
validated on the existing spatially-blocked holdout against the same H33
fold-fair control every prior lane used, (iii) adds a physical signal
(upward-continuation worms + basement/conductivity steps) for the buried-fault
population that scarp-and-proximity lanes cannot see, and (iv) is
*structurally* incapable of collapsing into the occupied ≤1 km halo, because
raw catalogue distance never ranks a cell — it only decides which band's
budget the cell competes for. Uniqueness is therefore a consequence of the
geological design, checked before placement — never achieved by capping,
jittering or exempting priors after the fact.

## Known limitations, stated before results

- Withheld *catalogue* components are not the organizer's *expert* faults.
  Banding corrects the measured proximity collapse, but if expert faults are
  in fact as catalogue-clustered as withheld components, banding will *lose*
  pooled HOLDOUT-DTI relative to NHR. The gate bar is therefore the H33
  fold-fair control (the lineage that actually scored publicly), with NHR's
  pooled numbers reported as a reference, not as the bar — see preregistration.
- Far-band (>5 km) nested-hide positives may be too few to fit a stable
  band model; the preregistered fallback merges training with the adjacent
  nearer band and records it. No post-hoc band redefinition is allowed.
- Upward continuation is computed by FFT on median-filled, edge-tapered
  100 m grids. The GeoDAWN flight-line spacing is coarser than 100 m, so
  worm features are *interpolated-field transforms*, not independent 100 m
  observations; canaries and the holdout — not physical intuition — decide
  whether they help.

## Outcome addendum (2026-10-22, after X1 — numbers from `run_card_ber.json` / `evidence/ber/`)

Hypothesis 1 (G79-BER) was run exactly as preregistered
(`registry/preregistration_ber.json`) and is **negative**:

- HOLDOUT-DTI (`gems57-pooled-hide-v2`): seed 20 **0.0788** [0.0684, 0.0889]
  (n = 11,321), seed 30 **0.0882** [0.0739, 0.1011] (n = 11,342) vs the H33
  fold-fair control 0.0961 / 0.0989. Paired Δ vs the control: −0.0173
  [−0.0287, −0.0055] and −0.0106 [−0.0245, +0.0044]. The candidate beats
  uniform placement decisively (paired CIs exclude 0 on both seeds) but does
  not beat the current holdout best on either seed, so the promotion gate
  failed and no submission slot may be spent.
- The distance-stratified diagnostic shows the mechanism: the banded models
  match the control within 1 km of the catalogue but lose in every farther
  band, and catastrophically beyond 5 km (credit per withheld truth pixel
  0.077 vs 0.163 on seed 20; 0.003 vs 0.216 on seed 30, on only 185 / 99
  truth pixels). Multi-height worms did not substitute for the multiline
  evidence encoded in the H19-5 lineage on this instrument.
- Uniqueness under amendment D-2: worst Spearman ρ 0.314 and worst
  chance-corrected overlap 0.654 against every informative comparable
  registry raster — the most registry-distinct surface this repo has
  measured — but the lane is recorded **not unique under D-2**, because 4
  full-footprint diagnostic surfaces fire the saturated-halo exact test
  (IR-79-68) and the gate was not modified after seeing the result.

Hypotheses 2–5 were not run (2 folded into 1; 3 not viable without absolute
elevation in this sandbox; 4 included as features; 5 infeasible on this
hardware). Full analysis: `reports/ber_analysis.md`.
