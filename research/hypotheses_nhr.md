# Candidate hypotheses — session 337ac1e9 (H79-NHR lane)

Written before any H79-NHR holdout result existed (preregistration:
[`registry/preregistration_nhr.json`](../registry/preregistration_nhr.json)).
Ranks are qualitative judgements of expected DTI improvement and cost, **not
scores**. Only hypothesis 1 was executed; its measured result is in
[`evidence/nhr/`](../evidence/nhr/) and the [run card](../run_card.json).

**Outcome, added after the results.** Hypothesis 1 beat the H33 holdout control on both
seeds, but its dots duplicate 26 earlier near-fault registry dot fields (IR-79-44), so
the lane stopped with a negative verdict. Hypotheses 2–5 remain untested.

"Not implemented in this repo" was checked against `src/`, `scripts/`,
`vendor/gems57/` and both archived lanes in `archive/`. A claim that nobody in
the wider GEMSDOE family ever tried something similar is **not** made; the
objective novelty arbiter is the shared registry duplicate gate (992 rasters).

| Rank | Hypothesis, exact layers | Physical signature / transform | Why it should catch a fault *missing* from the USGS/INGENIOUS catalogue | Difference from what this repo already implements | Expected gain / cost | Named non-fault mimic | Data viability |
|---|---|---|---|---|---|---|---|
| **1 (executed)** | **H79-NHR nested hide-to-recover learning.** 19 bands of `training_features.tif`; multiscale gradient magnitude + Laplacian-of-Gaussian of `det_elev`, `iso_grav_anom`, `rtp`; 10 lidar scarp bands (`ex_max`, `step_max`, `lapneg/lappos`, `downface/upface`, `cross`, `relief`, `coh100`) + 500 m maxima; 8 radiometric bands; 6 geometry inputs from the **visible** catalogue (distance, density at 0.5/2 km, distance to trace tips, lidar-strike alignment with the mapped strike field, strike-field coherence) | Gradient-boosted regression of the official 300 m triangular-kernel credit towards *simulated discoveries*: whole catalogue components withheld (3 px collar), features recomputed from the remainder | The training target is literally "a fault that is not in the map you can see". The model learns the conditional geometry of unmapped strands (offset parallel strands, step-overs, continuations beyond tips) jointly with scarp morphometry, instead of re-learning the marginal look of mapped traces | E1 (stopped) was a hand-built magnetic-lag transform with no learning and no catalogue geometry. Archived MCT/CSPT used submodular solvers over other surfaces. No module here trains on nested withheld components or uses a kernel-credit target | Highest expected / medium (CPU, ~25 min) | Pluvial Lake Lahontan shoreline and terrace risers, incised channel banks, roads and mine benches (steps of similar scale near range fronts) | All inputs restored and SHA-256 verified this session |
| 2 | **Antislope-scarp asymmetry.** Lidar `upface_max` vs `downface_max`, `coh100`, `strike`; `iso_grav_anom_hg` | Ratio of uphill-facing to downhill-facing band-passed step gradient, coherent along strike | Uphill-facing (antithetic) normal-fault scarps inside piedmonts and bedrock are under-represented in regional compilations, while shorelines, channel banks and fan toes face downslope, so the ratio suppresses the main mimics | `upface_max` is only one of 58 NHR inputs; no surface uses the asymmetry itself | Medium / low | Ridge-top sackung and landslide head scarps (also uphill-facing) | Inputs present |
| 3 | **Lahontan shoreline suppression.** Lidar `step_max`/`downface_max` + strike + **absolute elevation** | Down-weight steps that are contour-parallel and within ±15 m of pluvial shoreline altitudes (highstand ≈1330 m, [USGS Benson & Thompson 1987](https://pubs.usgs.gov/publication/70015223); ≈1335 m, [USGS Circular 1267](https://pubs.usgs.gov/circ/2004/1267/)) | Removes the dominant false-positive population that any scarp detector emits in the Lahontan basin, freeing budget for real faults | Not implemented anywhere in this repo | Medium / medium | Real faults that happen to parallel a shoreline would be suppressed | **Needs absolute elevation.** `det_elev` is detrended and the lidar u8 product stores relief, not altitude. Free official source: USGS 3DEP DEM via The National Map (<https://www.usgs.gov/3d-elevation-program>). Not reachable from this sandbox's allowlist; obtainable through a GitHub Actions workflow (as 7GEMSDOE did for the lidar product). **Not viable this session.** |
| 4 | **Strike-propagated tip continuation.** Visible-catalogue tips and local strike; lidar scarp bands | Search cone of ±15° along strike past each mapped tip, scored by lidar step evidence | Fault traces in compilations are often truncated at map-sheet or cover boundaries; continuations under thin cover are expert-mappable from lidar | Partially subsumed by NHR's `log_dist_visible_tip` input; no explicit cone search exists here | Low–medium / low | Bedding-parallel strike ridges, linear drainage | Inputs present |
| 5 | **Survey-seam-aware magnetic lineaments.** `rtp`, `tmi_hg`, GeoDAWN flight-line geometry | Lineament detection after removing azimuths parallel to 400 m flight lines / 4 km tie lines | Buried faults offsetting magnetic basement are invisible in topography | Not implemented here; E1 used magnetic profiles but no seam model | Low / medium | Levelling seams, dykes | Flight-line shapefiles are listed in the [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) but not mirrored here; not fetched |

## Why hypothesis 1 was chosen first

The organizer's test labels are expert-identified faults **absent** from the
public USGS database ([problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).
The only label-shaped information we have about "faults missing from a map" is
what happens when part of the map is removed. Nested hiding turns that into a
supervised target without touching the evaluation holdout. The kernel-credit
target matches the metric's distance weighting (TP uses `max p·k(d)`, FP uses
`1 − max k(d)`), so the regressor estimates exactly the quantity the dot
allocator needs.

## Known limitation, stated before results

Withheld *catalogue* components are not the organizer's *expert* faults. If
expert faults are less clustered around mapped traces than catalogue
components are, the geometry inputs will over-reward proximity on the real
test. The holdout cannot measure that shift; only an organizer score can.
