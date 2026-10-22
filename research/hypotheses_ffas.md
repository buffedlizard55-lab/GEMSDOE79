# Candidate hypotheses — session c04e5e27 (H79-FFAS lane)

Written **before** any H79-FFAS holdout result existed (preregistration:
[`registry/preregistration_ffas.json`](../registry/preregistration_ffas.json)).
Ranks are qualitative judgements of expected DTI improvement and cost, **not
scores**. Only hypothesis 1 is executed in this session (budget: 3 experiments
or 2 hours). Hypotheses 2–5 remain untested unless hypothesis 1 has a shared-tool
defect.

**Not implemented in this repo** was checked against `src/`, `scripts/`,
`vendor/gems57/` and archived lanes in `archive/`. A claim that nobody in the
wider GEMSDOE family ever tried something similar is **not** made; the
objective novelty arbiter is the shared registry duplicate gate.

Prior lanes in this repo and why they are not restarted:

| Lane | What it did | Why not this session |
|---|---|---|
| G79-FABRIC-OFFSET (E1) | Magnetic-marker lag across a gravity edge | HOLDOUT-DTI ~0.047, below uniform; stopped |
| H79-NHR | Nested hide-to-recover HGB on 58 inputs | Beat H33 control (0.143/0.152 vs 0.096/0.099) but **duplicate** vs 26 near-fault family fields (worst 0.913 vs chance 0.610) |
| G79-STEPCO | Multi-field step dipoles | Tied H33 control; uniqueness also fired |
| G79B-SDPT | Scarp dipole-persistence + traces | Unconstrained beat control; uniqueness cap then fell below control |
| H79-MCT / H79-CSPT | Archived concurrent; dense-prior exemptions **not adopted** | |

H33 forensics (this repo, `knowledge/why_h33.md`): the named file is exactly
D2.8 minus 6,436 dots within 200 m of the catalogue. Public scores above 0.2478
in the family table are the same root surface (`19GEMSDOE` h19-5) under different
emission rules. Genuinely non-duplicate family landmarks max out near 0.2478
(GEMSDOE70). NHR's dots sit at median 539 m from the catalogue; H33's at 1.96 km.
The holdout withholds *catalogue* segments, so near-field methods win the proxy
and lose uniqueness; far-field methods are the remaining unoccupied band.

## Ranked candidates

| Rank | Hypothesis, exact layers | Physical signature / transform | Why it should catch a fault *missing* from the USGS/INGENIOUS catalogue | Difference from what this repo already implements | Expected gain / cost | Named non-fault mimic | Data viability |
|---|---|---|---|---|---|---|---|
| **1 (execute)** | **H79-FFAS far-field polarity-aware antislope scarp.** USGS 3DEP lidar `upface_max`, `downface_max`, `step_max`, `ex_max`, `coh100`, `cross_max` (hash-pinned `lidar_scarp_features_u8.tif`); distance to the **visible** catalogue only | Fixed formula (not learned): `score = (down + 2·up) · step · coh · cross · ex · logistic(d; d0=8 px, s=3 px)`, then footprint mid-ranks. Dots: 37,654, 3 px Poisson, pixel-exact catalogue mask plus a preregistered 2 px visible-echo collar | Regional compilations map the obvious **downslope range-front** synthetic scarps. Antithetic (uphill-facing) and intra-basin scarps, and scarps more than ~1 km from drawn traces, are the structures expert mappers add later. The logistic far-field weight is the opposite of NHR's near-fault geometry prior | NHR used `upface_max` as 1 of 58 learned inputs with catalogue density/tip features; it did **not** emit the antislope ratio or a far-field weight. G79B used crest–base dipoles without a far-field prior. E1 used magnetics. No module here multiplies polarity by a logistic of visible-catalogue distance | Highest expected uniqueness / low (CPU seconds per seed; no HGB) | Ridge-top sackung and landslide headscarps (also uphill-facing); irrigation ditches; contour-parallel terrace risers | Lidar u8 product is in `registry/data_manifest.json` (sha256 `d580bb8b…`). Absolute elevation is **not** required |
| 2 | **Strike-propagated tip continuation.** Visible-catalogue endpoints + local strike; lidar `step_max`, `coh100` | Search cone ±15° along strike past each mapped tip, scored by lidar step | Traces in compilations are often truncated at map-sheet or cover boundaries | NHR had `log_dist_visible_tip` as an input, not an exclusive cone. Untested as a lane | Medium uniqueness, medium holdout / low | Bedding-parallel strike ridges, linear drainage | Inputs present |
| 3 | **Radiometric Th/K lineament with lidar corroboration.** GeoDAWN `K`,`Th` u8; lidar `coh100` | Horizontal-gradient ridges of Th/K, kept where lidar coherence is high | Hydrothermal fluid along unmapped faults can alter surface K relative to immobile Th even under thin cover | Not a primary surface in this repo. Family GEMSDOE15/46 tried related alteration fusions (unverified historical scores 0.078–0.159) | Medium uniqueness, uncertain holdout / low | Lithologic contacts, provenance changes in fans, survey seams | u8 radiometrics restored in the manifest; **units are not calibrated USGS concentrations** (IR-79-17) |
| 4 | **Lahontan shoreline suppression.** Lidar step + strike + **absolute elevation** | Down-weight contour-parallel steps within ±15 m of pluvial shoreline altitudes (~1330–1335 m; [USGS Benson & Thompson 1987](https://pubs.usgs.gov/publication/70015223); [USGS Circular 1267](https://pubs.usgs.gov/circ/2004/1267/)) | Removes the dominant scarp false-positive in the Lahontan basin | Not implemented here. `det_elev` is detrended; lidar u8 stores relief, not altitude | Medium / medium | Real faults that parallel a shoreline would be suppressed | **Needs absolute elevation.** Free official source: USGS 3DEP via The National Map. Not on this sandbox allowlist. **Not viable this session.** |
| 5 | **Drainage knickpoint / valley-floor offset alignment.** Flow accumulation + knickpoints | Along-stream slope breaks that align across neighbouring catchments | Youthful faults offset streams before a continuous scarp is compiled | Not implemented here | Uncertain / high | Lithologic nickpoints, fan-head trenching | Needs a hydrologically correct DEM (absolute). `det_elev` is detrended, so drainage is distorted. **Not viable this session.** |

## Why hypothesis 1 is executed first

1. **Uniqueness is the binding constraint.** NHR, STEPCO and G79B all found that
   *good scarp terrain within 2 km of the catalogue is already dotted*. A new
   near-field detector is a duplicate by construction. H33's own dots are 70 %
   farther than 1 km from the catalogue; that band is the remaining spatial
   vacancy, but only if the *ranking* inside it is not h19-5. Antislope
   (uphill-facing) is the opposite polarity of a typical range-front detector.
2. **Metric.** TP is a max over a 300 m kernel; FP is a sum. Sparse far-field
   dots that land on unmapped traces pay almost no catalogue-echo FP (the
   organiser masks exact known-fault pixels:
   [staff clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)).
3. **Cost.** No nested HGB, so two seeds fit in minutes, leaving budget for the
   registry uniqueness scan.
4. **IR-79-53.** The duplicate gate is currently vacuous against 30 space-filling
   rasters (a uniform-random map fails them). This session fixes that **once** in
   the shared tool (`informative-halo-v4`) rather than inventing a private fork.
   Sparse family fields (halo ≤ 0.70) still fire at 0.70, so NHR-style copies
   still stop.

## Known limitation, stated before results

Withheld *catalogue* components are not the organiser's *expert* faults. A
far-field method may **lose** the catalogue-holdout to NHR (0.143) even if it
would do better on expert labels. Promotion still requires beating the H33
fold-fair control on both seeds **and** uniqueness. Failure on either gate is a
negative deliverable; no weekly slot is used.

Official problem statement (fault mapping, not vents):
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>.
Lidar morphometry origin: USGS 3DEP
<https://www.usgs.gov/3d-elevation-program>.
GeoDAWN (not used in hypothesis 1):
<https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>.
