# Candidate hypotheses for the 2026-10-22 session (lane selection)

Written before implementing or scoring anything in this session, as required.
"Not tried yet" is verifiable only against this repository (which contains one
closed lane, `G79-FABRIC-OFFSET`) and the 98-row score ledger of sibling
GEMSDOE sites (`registry/score_ledger.csv`, all values UNVERIFIED HISTORICAL
REPORTS). No global novelty claim is made. Expected-DTI column is a qualitative
prior for ranking, **not** a projected score. Only rank 1 is implemented
(preregistered in `registry/preregistration_g79stepco_20261022.json`).

## What the ledger already teaches (evidence for the ranking)

- The group's best lineage is one supervised ranking surface (H19-5:
  multi-line corroborated stack of DEM/lidar scarps, geopotential worms,
  thermal/geochemical points and power-law budgeting) whose organiser results
  improved mainly through **emission geometry**: continuous 0.1922 → dotted
  d1.5 0.2477 → dotted d2.8 0.2600 → 200 m catalogue-flank prune ("H33",
  user-reported 0.2778, no receipt; the GEMSDOE32 page itself labels the file
  UNSCORED with a 0.2747 *projection*). Forensics in this repo prove H33 is
  exactly `D2.8 & (distance to catalogue > 2 px)`: 44,090 → 37,654 isolated
  dots, 0 disagreement (`knowledge/why_h33.md`).
- Dozens of single-physics exotic detectors (Euler deconvolution, worms,
  Radon, relay ramps, strain gauges, radiometric halos) scored 0.0009–0.16.
  This repo's own single-physics lane scored HOLDOUT-DTI 0.0474/0.0466 —
  below uniform random placement (0.0504/0.0496). Single-layer pattern
  matching is a measured dead end in this study area at 100 m.
- The metric pays for *credit density*: TP saturates per truth pixel (max, not
  sum), FP is charged per emitted pixel at α = 0.2. Thick ridges and dense
  probability mass waste budget; isolated dots spaced ≈300 m along a good
  ranking are the measured optimum form. Any new lane must therefore be a
  **ranking** improvement emitted as matched-mass binary dots, not a new
  emission gimmick on a borrowed ranking (that would also fail uniqueness).

## Ranked candidates

| # | Hypothesis, layers, signature | Why it should catch a fault missing from the catalogue | Difference from this repo / ledger | Expected DTI effect (prior) & cost | Named non-fault mimic |
|---|---|---|---|---|---|
| **1 (chosen)** | **Corroborated step-dipole ranking (G79-STEPCO).** Layers: `det_elev`, `iso_grav_anom`, `depth_to_base_surf`, `rtp`, `cond_surf` (training bands 12/13/15/2/17) + all provided derivative/strain/seismic bands + 1 m-derived lidar scarp channels + GeoDAWN radiometrics. Signature: antisymmetric **step dipole** across a trace (field at +300 m minus field at −300 m, 8 normals) plus gradient/Laplacian at fixed scales; a fixed HistGradientBoosting model learns which multi-field step combinations the *visible* catalogue exhibits, per hide-and-recover draw. | Regional mapping misses short piedmont/basin-margin faults whose scarps are subdued at mapping scale but which still step topography, basement depth and density. Catalogue bias is toward long, exposed range-front traces; a step detector is length-blind and relief-tolerant. | This repo has only the offset-*registration* lane (profile lag across a gravity edge — a displacement of fabric, not a step in field level). Ledger ML entries used raw bands or single-field edges; none in the ledger is a preregistered multi-field step-dipole transform set with per-draw refits and fold-fair incumbent control on this evaluator. Overlap risk vs H19-5 lineage is measured, not assumed. | Highest prior: supervised rankings are the only family above 0.24 in the ledger; step features target their known weakness (single-field edges). Medium cost (CPU transforms + 3 HGB fits). All inputs already restored and hash-verified — no new external data. | Sedimentary facies pinch-out / paleochannel margin (steps gravity + basement together); alluvial-fan lobe boundary (steps topography); flight-line levelling seam (steps magnetics/radiometrics). |
| 2 | **Blind basin-margin step in low relief.** Layers: `iso_grav_anom` + `depth_to_base_surf` steps gated to low `det_elev_slope` cells. Signature: co-directed gravity/basement step where topography is flat. | Fully buried faults under basin fill have no scarp to map; experts found hidden faults precisely where surface mapping fails. | Standalone basin-step entries exist in the ledger (`h61a-basement-step` 0.0009) but without the low-relief gate and corroboration; as a *regime* it is inside candidate 1's feature space, so a separate lane would duplicate it. | Low as a standalone: catalogue holdout truth is mostly exposed faults, so this regime is structurally under-rewarded by the mandated gate (distribution shift). Medium cost. No new data needed. | Basin facies change / buried paleo-shoreline. |
| 3 | **Radiometric marker offset.** Layers: GeoDAWN K/Th/U/TC (uint8 derivatives) + RTP/gravity. Signature: shared cross-trace registration lag of magnetic and K–Th profiles (rank-4 in the previous session's register, never tested). | A young fault can offset surface composition and bedrock fabric together before a scarp develops. | Distinct from sibling radiometric *halo* lanes (alteration proximity), but inherits the previous lane's measured weakness: 100–300 m lags on grids interpolated from 400 m flight lines responded to gridding artefacts (HOLDOUT-DTI below uniform). | Low prior after the E1 measurement; medium cost. Viable only as pattern analysis — the restored radiometrics are uint8 derivatives, not calibrated USGS products; calibrated grids are free from USGS GeoDAWN (DOI 10.5066/P93LGLVQ) but were not byte-verified in this sandbox, so quantitative use is **not** proposed. | Fan sediment draping offsetting compositional boundaries without slip. |
| 4 | **Seismicity-density edge aligned to a geophysical boundary.** Layers: `deq_n100a15`, `ieq_n100a15`, strain bands (4/7/8). Signature: linear earthquake-density gradient whose strike matches a gravity/magnetic step. | Unmapped but active structures can organise microseismicity before they are mapped geologically. | Not implemented in this repo; strain-only ledger entries are low (≤0.19 with heavy stacking). Earthquake *density* at 100 km smoothing (band names) is far coarser than 300 m emission, so localisation must come from the geophysical edge — the seismicity adds little independent precision. | Low prior, low-medium cost, no new data. | Network detection/completeness gradients; geothermal production-induced seismicity clusters. |
| 5 | **Clay-cap breach lineament.** Layers: `cond_surf` + `depth_to_base_surf`. Signature: narrow conductive-base shallowing (breach) linear in plan, crossing a gravity step. | Upflow along a permeable unmapped fault can breach the conductive clay cap; directly geothermal, not just structural. | Conceptually adjacent to ledger MT/clay-cap and hydro-conduit entries (0.0558–0.1223); the provided conductivity is a smooth regional surface — narrow breaches are at/below its resolution. | Low prior, low cost, no new data. | Lithologic conductor (graphitic horizon), saline playa brine geometry. |

## Decision

Implement **rank 1 only**, exactly as preregistered. Ranks 2–5 are recorded so
that a negative S1 cannot be quietly replaced by lane-hopping inside the same
budget: S2 is allowed only as the preregistered canary-failure ablation, S3 is
reserved. No candidate requires new external data; the free official sources
for every input family are already cited in `knowledge/official_sources.json`
(DrivenData problem page, USGS GeoDAWN DOI 10.5066/P93LGLVQ, DOE rules PDF,
official reference solution).
