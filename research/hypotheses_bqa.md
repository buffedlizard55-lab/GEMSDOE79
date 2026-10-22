# Candidate hypotheses — session 0bd0e0b2 (written before any H79-BQA result)

Ranks are qualitative research judgements of expected DTI improvement and
implementation cost. **They are not scores.** Only hypothesis 1 is executed in
this session (preregistration: [`registry/preregistration_bqa.json`](../registry/preregistration_bqa.json)).

## What the evidence already in this repo says (inputs to the ranking)

| Fact | Evidence class | Source |
|---|---|---|
| H33 = D2.8 dot set minus the 6,436 dots within 200 m of a mapped fault; nothing added or moved | RASTER-MEASUREMENT | [`evidence/h33_forensics.json`](../evidence/h33_forensics.json) |
| D2.8 0.2600 → H33 0.2778 after that deletion | USER-REPORTED (no organizer receipt in this repo) | project brief |
| H33 dots: median 19.6 px (1.96 km) from the catalogue; 70 % > 1 km; footprint background median 23.5 px | RASTER-MEASUREMENT | [`evidence/nhr/distance_to_catalogue.json`](../evidence/nhr/distance_to_catalogue.json) |
| H79-NHR dots: median 5.4 px (539 m); HOLDOUT-DTI 0.1431 / 0.1522 vs H33 control 0.0961 / 0.0989 | HOLDOUT-DTI `gems57-pooled-hide-v2` | [`evidence/nhr/`](../evidence/nhr/) |
| Near-catalogue registry fields occupied by NHR have user-reported scores 0.016–0.143 | USER-REPORTED | [`reports/nhr_analysis.md`](../reports/nhr_analysis.md) |

**Interpretation (hypothesis, not proof).** The hide-and-recover holdout withholds
*catalogue* components. Fault networks cluster, so a withheld component is usually
close to a visible one, and the holdout rewards proximity. The organizer's labels
are expert faults *absent* from the catalogue ([problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).
The only organizer-side signal we have (H33 > D2.8 after deleting the collar
dots; near-catalogue fields scoring low) points the other way: the scored truth
appears to live mostly **away** from the mapped traces. A proxy that is biased
toward proximity will promote near-catalogue maps that the organizer does not
reward. Hence the top hypothesis below decouples **where** (distance-band budget,
anchored to the best organizer-scored distance profile) from **which cell within
a band** (learned on simulated discoveries).

## Ranked candidates

| Rank | Hypothesis and exact layers | Physical signature / transform | Why it should catch a fault missing from the USGS/INGENIOUS catalogue | How it differs from what this repo already implemented | Expected gain / cost | Named non-fault mimic | Data |
|---|---|---|---|---|---|---|---|
| **1 (executed)** | **H79-BQA — band-quota allocation of a band-reweighted nested hide-and-recover model.** Same 58 label-independent + visible-geometry inputs as the shared NHR stack (19 `training_features.tif` bands with multiscale gradient / LoG of `det_elev`, `iso_grav_anom`, `rtp`; 10 lidar scarp bands + 500 m maxima; 8 radiometric bands; 6 visible-catalogue geometry inputs) | Nested-hide regression of the 300 m kernel credit with **sample weights that equalise each distance-to-visible band**, so splits are spent on within-band discrimination (scarp morphometry, geophysical edges, strike alignment) rather than on re-learning "close to a mapped fault". Dots are then placed under **fixed per-band quotas** equal to H33's measured band fractions, 3 px Poisson spacing | Most of the budget is forced into the 1–5 km+ far field where unlisted piedmont and intrabasin faults must be, and the learned within-band ranking is trained on "a fault that is not on the visible map" | NHR used one pooled, unweighted target and a single global ranking (median 539 m). H33/D2.8 used hand-built scarp ridges, no learning. No module here weights by distance band or allocates by band quota | Highest / low (reuses shared stack, evaluator, writer; 2 fits per fold) | Pluvial Lake Lahontan shoreline and terrace risers, alluvial-fan heads and incised channel banks (contour-parallel 2–10 m steps) | All inputs SHA-pinned and restored this session |
| 2 | **Antislope-scarp asymmetry in the far field.** Lidar `upface_max` vs `downface_max`, `coh100`, `strike`; `det_elev` slope aspect | Ratio of uphill-facing to downhill-facing band-passed step, coherent along strike, restricted to > 1 km from mapped traces | Uphill-facing (antithetic) scarps are diagnostic of faulting; shorelines, fan toes and channel banks face downslope | `upface_max` is one of 58 inputs elsewhere; no surface uses the asymmetry itself | Medium / low | Sackung and landslide head scarps (also uphill-facing) | Inputs present |
| 3 | **Lahontan shoreline suppression.** Lidar `step_max` + strike + **absolute elevation** | Down-weight contour-parallel steps within ±15 m of pluvial highstand altitudes (~1330 m, [USGS, Benson & Thompson 1987](https://pubs.usgs.gov/publication/70015223); [USGS Circular 1267](https://pubs.usgs.gov/circ/2004/1267/)) | Removes the dominant false-positive population of every scarp detector in the basin | Not implemented anywhere here | Medium / medium | Real faults parallel to a shoreline would be suppressed | **Needs absolute elevation.** `det_elev` is detrended. Free official source: USGS 3DEP 1/3 arc-second DEM via [The National Map](https://www.usgs.gov/3d-elevation-program). Not reachable from this sandbox's network allowlist; obtainable through a GitHub Actions workflow. **Not viable this session.** |
| 4 | **Cross-scale crest persistence.** Lidar `lapneg_max/lappos_max`, `step_max`, `coh100` + `det_elev` LoG at 100–500 m | Require a crest stable across smoothing scales with minimal along-strike migration | Short degraded scarps omitted from regional linework persist across scales where amplitude thresholds fail | SDPT used crest-base dipoles but not cross-scale migration | Low–medium / medium | Long terrace risers | Inputs present |
| 5 | **Survey-seam-aware magnetic lineaments.** `rtp`, `tmi_hg`, GeoDAWN flight-line geometry | Lineaments after removing azimuths parallel to flight / tie lines | Buried basement offsets invisible in topography | E1 used magnetic profiles but no seam model | Low / medium | Levelling seams, dykes | Flight-line files are in the [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) but not mirrored; not fetched |

## Why hypothesis 1 first

It is the cheapest test of the single most important unresolved question in the
project — whether the proxy's proximity bias is what separates holdout winners
from organizer winners — and it re-uses audited shared code end to end. It also
directly targets the measured duplicate problem: NHR's near-catalogue band is
occupied by older registry dot fields, while the quota moves most dots out of it.

## Gate before any slot (preregistered)

Canary ≤ 0.90; candidate > H33 fold-fair control on the standard holdout on both
seeds with paired CI above zero; candidate ≥ H33 control on the far-field (> 1 km)
arm on both seeds; chance-corrected uniqueness (IR-79-68) on the surface before
placement and on the final dots; format validator; separate selector. A failure at
any gate is a negative result and is published as such.
