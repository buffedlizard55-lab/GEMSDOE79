# Candidate hypotheses — session 167a60a6 (written before any new holdout result)

Scope checked against `src/`, `scripts/`, `vendor/gems57/`, `archive/` and the
measured registry lineage in `knowledge/why_h33.md`. "Untried" means not
implemented as a lane in **this** repo; family-wide first-ever claims are not
made — the objective arbiter is the registry duplicate gate (992 rasters,
Amendment D-2). Ranks are qualitative expected-DTI/cost judgements, not scores.

## What the measured evidence already establishes (inputs to ranking)

- **H33 = D2.8 minus its 6,436 dots within 200 m of the catalogue**
  (RASTER-MEASUREMENT, `evidence/h33_forensics.json`): 44,090 → 37,654 binary
  dots, median catalogue distance 1.96 km. USER-REPORTED 0.2600 → 0.2778.
  Sparse binary emission + near-catalogue collar pruning is therefore a
  *measured* component of the family best, not a hypothesis.
- **The metric** (official, alpha 0.2 / beta 0.8, 300 m triangular kernel):
  TP is a per-truth-pixel **max**, FP is a **sum** over predicted mass. A dot
  on a straight trace earns ≈2.33 TP units per FP unit at 3 px spacing;
  break-even on-trace probability ≈2.5 % at score 0.28, ≈4.1 % at 0.44
  (ESTIMATE, `reports/nhr_analysis.md` §1). Score 0.2778 needs ≥23.6 % of
  truth credit; the verified public leader 0.4413 needs ≥38.4 % (rigorous
  bound) and ≈65–67 % at H33-like FP (ESTIMATE). The gap is ranking quality,
  not format.
- **H79-NHR** (HOLDOUT-DTI 0.1431/0.1522 vs H33 control 0.0961/0.0989) shows
  nested-hide kernel-credit learning works on the proxy, but its gain is
  driven by catalogue-proximity inputs (no-geometry ablation 0.0739/0.0751),
  its median dot is 539 m from a mapped fault, it duplicates 26 ordinary
  registry dot fields, and earlier near-fault fields scored only
  0.016–0.143 live (UNVERIFIED HISTORICAL). Conclusion used below:
  **proximity is a holdout shortcut and a live/distribution-shift and
  duplication risk; the next lane must rank by physical evidence, not by
  nearness to the map.**
- Genuinely non-duplicate family lanes exist and score: GEMSDOE70 dual-OOF
  supervised + 300 m submodular cover 0.2478 (4.8 % exact overlap with H33),
  GEMSDOE49 orthogonal-gated 0.2376, GEMSDOE73 Blakely worms 0.1917
  (RASTER-MEASUREMENT + UNVERIFIED HISTORICAL scores, `knowledge/why_h33.md`).
  Two partially independent rankings each capture substantial truth credit —
  better physical ranking has headroom above 0.2778 in principle. No
  projection is made for this session's candidate.

## Ranked hypotheses

| Rank | Hypothesis, exact layers | Physical signature / transform | Why it should catch a fault *missing* from USGS/INGENIOUS | Difference from this repo | Expected gain / cost | Named non-fault mimic | Data viability |
|---|---|---|---|---|---|---|---|
| **1 (chosen, lane H79-ARC)** | **Ridge-concordance credit learning without proximity.** 19 `training_features` bands; 10 lidar scarp bands + strike/coherence; 8 radiometric/extension bands; new transforms of `det_elev`, `rtp`, `iso_grav_anom`, `tmi_hg`, lidar `step_max/upface/downface` | Structure-tensor line-coherent edge strength (gradient magnitude × tensor coherence) at σ∈{1,2,4}; magnetic worm persistence (HG local-max across scales); Hessian ridge anisotropy of detrended elevation; antislope asymmetry `upface−downface` and ratio; nested-hide kernel-credit target; **submodular max-cover emission** (expected-TP greedy) at fixed budget, >200 m off catalogue | Expert-only faults must be *mappable from evidence* — a scarp, a basement edge, an alteration line — or experts could not have drawn them. Antithetic (uphill-facing) piedmont scarps and buried basement edges are systematically under-represented in regional compilations that privilege main range-front traces. Line-coherent transforms respond to *traces*, which is what the max-kernel metric rewards, instead of per-pixel anomaly blobs | NHR used per-pixel features + proximity geometry + Poisson thinning; E1 was a hand-built magnetic-lag rule; STEPCO a fixed step-concordance rule. No lane here combines ridge-steered features, a no-proximity credit learner and max-cover emission | Highest / medium (reuses cached NHR stack; CPU) | Pluvial Lake Lahontan shoreline/terrace risers (contour-parallel ridges; predominantly downslope-facing, so antislope terms + magnetic concordance are the learned suppressors); incised channel banks; roads/mine benches | All inputs already restored & SHA-256-verified this session (`registry/data_manifest.json`) |
| 2 | **DEM10 one-sided step + shoreline suppression.** 13 USGS 3DEP 1/3-arc-second DEM derivative vectors (`onesided`, `onesided3`, `hgm20/50/200`, `curv_absmax`, …) mirrored at `GEMSDOE10` tag `ext/dem10-36343078537` | One-sided elevation step across a candidate trace (fault throw) vs two-sided ridge (shoreline/terrace) | A normal-fault scarp is a *one-sided* step; the dominant mimic (shoreline riser) is a two-sided ridgelet on a contour. The sign structure separates them where amplitude cannot | DEM10 vectors are not inputs to any lane here (restore script exists, unused by NHR/STEPCO/E1) | Medium / medium (≈640 MB restore via `gh api`; source free & official: USGS 3DEP via ScienceBase item `4f70aa9fe4b058caae3f8de5`, named in `scripts/restore_dem10.py`; obtainable — checked against the tag manifest design, hashes pinned there) | Fluvial terrace edges are also one-sided steps | Viable, deferred: rank 1 extracts related signal from already-pinned lidar bands without a new 640 MB dependency |
| 3 | **Strike-propagated tip continuation cones.** Visible-catalogue tips + local strike; lidar step bands | ±15° along-strike search cone past each mapped tip, scored by lidar step evidence inside the cone only | Compilation traces are truncated at cover/map boundaries; continuations under thin cover are expert-mappable | Only a scalar `log_dist_visible_tip` input exists (NHR); no cone search | Low–medium / low — but **high duplication risk**: tip halos are exactly where earlier near-fault fields concentrated (IR-79-55), so P(win) after the duplicate gate is poor | Bedding strike ridges, linear drainages | Inputs present; not chosen on duplication grounds |
| 4 | **Radiometric alteration worms.** GeoDAWN `K, Th, U, TC` + ratios `ThK, UK, UTh` + `iso_grav_anom_hg` | Ratio-gradient ridge lines coincident with gravity HG edges (permeable fault → hydrothermal K/U mobility) | Alteration can trace a *covered, scarp-less* fault that topography and magnetics miss — precisely the class absent from a topography-led compilation | Radiometrics were only minor per-pixel inputs in NHR; no ratio-worm transform exists here | Low–medium / low. Standalone family evidence is weak: 15GEMSDOE alteration conjunction 0.0782 live (UNVERIFIED HISTORICAL) | Lithologic contacts, playa evaporite margins, felsic intrusions | Inputs present |
| 5 | **Geodetic strain-localization ridges.** `geod_2ndinv`, `geod_shearrate`, `geod_dilaterate` | Ridge maxima of strain-rate invariants (active localization hosts unmapped active faults) | An actively straining, unmapped structure is a geothermal-relevant target compilations can miss | Only raw per-pixel inputs in NHR | Low / low: geodetic fields are smoothed at ≫100 m, so trace-level precision (which the 300 m kernel demands) is implausible | Regional strain gradients, volcanic deformation | Inputs present |

## Decision

Execute rank 1 only, as preregistered in
`registry/preregistration_arc.json`, under protocol Amendment D-2
(`reports/protocol_amendment_D2_20261022.md`). Validate on the shared
spatially-blocked holdout (`gems57-pooled-hide-v2`, seeds 20/30) against the
H33 fold-fair control before any submission decision; spend no slot unless
every preregistered gate passes and the separate selector re-derives them.
