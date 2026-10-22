# Candidate hypotheses — session e23d5371 (lane H79-COV)

Written before any H79-COV result existed. Preregistration:
[`registry/preregistration_g79cov_20261022.json`](../registry/preregistration_g79cov_20261022.json).
Ranks are qualitative judgements, not scores. Only hypothesis 1 is executed.

## Why previous lanes cannot simply be repeated (verified from this repo)

| Lane | HOLDOUT-DTI (gems57-pooled-hide-v2, seeds 20/30) | Why it stopped |
|---|---|---|
| H79-NHR (catalogue-geometry nested-hide HGB) | 0.1431 / 0.1522 vs H33 control 0.0961 / 0.0989 | Duplicate: 26 ordinary registry dot fields each contain >70% of its dots within 3 px (IR-79-55). Dots sit at median 5.4 px from the catalogue (`evidence/nhr/distance_to_catalogue.json`). |
| G79B-SDPT (terrain-only dipole/trace) | 0.111 / 0.121 unconstrained | 99 dot-field priors >0.70 forward overlap; the registry-unique capped emission fell below its A1 control on both seeds. |
| G79-STEPCO (multi-field step dipoles + HGB) | 0.0946 / 0.0948 | Tied the H33 control; uniqueness fired on space-filling priors. |
| G79-FABRIC-OFFSET E1 (magnetic marker lag) | 0.047 / 0.047 (post-stop diagnostic) | Below uniform random; stopped at the literal gate. |

Lesson, measured not assumed: any detector whose ranking is dominated by
catalogue proximity or by downhill-facing range-front scarp amplitude lands on
the same cells as 26–99 earlier family dot fields. A lane that is both
registry-unique **and** holdout-competitive must rank a fault population those
fields systematically underweight.

## Ranked candidate hypotheses (untried in this repo)

| Rank | Hypothesis and exact layers | Physical signature / transform | Why it should catch a fault *missing* from USGS/INGENIOUS | Difference from everything in `src/`, `scripts/`, `vendor/`, `archive/` | Expected gain / cost | Named non-fault mimic | Data viability |
|---|---|---|---|---|---|---|---|
| **1 (executed)** | **H79-COV — antithetic scarps + buried basement steps under cover.** Lidar `upface_max`, `downface_max`, `step_max`, `coh100`, `relief`; potential fields `depth_to_base_surf` (b15), `iso_grav_anom` (b13), `rtp` (b2), `cond_surf` (b17), plus `tmi_hg`, `iso_grav_anom_hg`, strain/earthquake bands | (a) Facing-polarity asymmetry `up/(up+down)` × step rank × coherence; (b) two-scale step-dipole **persistence** `min(rank(step σ1.5), rank(step σ6))` per potential field, interacted with cover thickness rank; fixed HGB on the nested-hide 300 m kernel-credit target, **no catalogue-geometry inputs** | Catalogue mappers draw downhill-facing range-front scarps. Antithetic (uphill-facing) graben strands and graben margins buried under basin fill have weak/no conventional scarp but still step basement depth, gravity and magnetics. Expert test faults were specifically identified as absent from the public USGS database ([official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)) | NHR used catalogue geometry (proximity) — excluded here by construction. STEPCO used single-scale dipoles of all fields including topography amplitudes with a classifier on mapped pixels. G79B was terrain-only with trace objects. Nobody here used facing-polarity asymmetry as the primary signal (it was hypothesis 2, untested, in `research/hypotheses_nhr.md`) or cover-interacted two-scale potential-step persistence, and nobody combined them in one catalogue-free population | Highest / medium (reuses NHR stack/evaluator) | Sackung/landslide head scarps (also uphill-facing); unfaulted sedimentary pinch-outs step basement+gravity; paleochannel margins | All inputs already SHA-256-pinned in `registry/data_manifest.json`; viable now |
| 2 | **Wellspring/vent alignment corridors.** `external/gdr_wellspring_in_footprint.csv`, `gdr_volcanic_vents_in_footprint.csv` (pinned in the data manifest) + lidar step | Collinearity density of thermal springs/vents along candidate lineaments (Hough-style accumulation) | Geothermal upflow localises on permeable fault intersections that may lack scarps; alignments of springs are a classic blind-fault indicator | No module in this repo uses point-feature collinearity; the CSVs are restored but unused | Medium / low–medium | Spring lines along lithologic contacts or range-front water tables without through-going faults | Viable (pinned CSVs); point counts are small, so power is uncertain |
| 3 | **Drainage-deflection lineaments.** 10 m DEM flow routing | Systematic same-sense deflection/knickpoint alignment of channels crossing a line | Strike-slip/oblique components offset drainages even where scarps are eroded | No flow-routing anywhere in this repo | Medium / high | Lithologic strike ridges deflect drainage without faulting | **Not viable this session**: needs USGS 3DEP 10 m DEM tiles (free, official: <https://www.usgs.gov/3d-elevation-program>), unreachable from this sandbox allowlist; obtainable via a GitHub Actions workflow as sibling repos did |
| 4 | **Seismicity lineation anisotropy.** Earthquake point catalogue | Anisotropic (lineated) clustering of hypocentres vs isotropic background | Active blind faults generate microseismic lineations before/without surface rupture | The stack's `deq/ieq` bands are pre-smoothed densities; no point-pattern anisotropy exists here | Low–medium / medium | Mining blasts and geothermal production seismicity cluster isotropically around fields | **Not viable this session**: needs the USGS ComCat event catalogue (free, official: <https://earthquake.usgs.gov/earthquakes/search/>), not mirrored here and unreachable |
| 5 | **Radiometric K-depletion lineaments.** GeoDAWN K/Th/U bands | Linear K/Th lows (hydrothermal leaching) parallel to structures | Fault-hosted alteration can mark covered faults | Family-wide radiometric fusions exist (GEMSDOE46, user-reported 0.1589); in-repo the bands are inputs but never an alteration-lineament surface | Low / low | Playa evaporites and lithologic K variation | Viable, but ranked last: high duplicate-gate risk vs radiometric family fields |

## Why hypothesis 1 maximises P(win)

1. **Uniqueness by population, not by capping.** Its top-ranked cells are
   antithetic piedmont scarps and covered basement steps — terrain that
   amplitude-ranked scarp fields and proximity-ranked fields place low. No
   post-hoc overlap cap is used or needed; the registry gate is a check, not
   an input.
2. **Holdout-honest training.** Same nested whole-component hide-and-recover
   and metric-native kernel target as NHR, but with catalogue geometry removed,
   so any holdout gain cannot be proximity memorisation (the failure mode that
   made NHR both strong and duplicated).
3. **Final-round value.** The Final Prize Round rescores against expert-expanded
   labels ([official structure](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#competition-structure)):
   a map of genuinely unmapped antithetic/buried structures is exactly what an
   expert panel can verify and add, whereas near-catalogue strand duplicates
   add little new geology.

## Stated-before-results limitation

Withheld catalogue components are catalogue-like (mostly mappable scarps), so
the holdout is *biased against* a covered/antithetic detector: it may score
only modestly even if it finds real blind faults. The preregistered bar
(beat the H33 fold-fair control on both seeds) is kept anyway; if it is not
met, the verdict is negative and the file is labelled DO-NOT-SUBMIT. No
leaderboard score is projected from holdout numbers.
