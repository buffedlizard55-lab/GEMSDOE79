# Ranked future hypotheses — review `bab8f374` (2026-10-22)

**Disposition: research slate only; no lane was selected or run.** The request did not
supply a delimited single-method lane paragraph, and the required literal novelty
preflight stops every non-empty map. This file is not a preregistration, not an
experiment card, and not evidence of a score. The qualitative priority column is a
judgment about potential to improve **HOLDOUT-DTI** relative to cost and data risk;
it is not a numerical prediction. No DTI delta is estimated.

“Untried” here means no matching implementation/holdout receipt was found in the
active code and the reviewed local archives. Several ideas have appeared as prior
research proposals; this is not a claim that they are new to all 93 repositories,
the broader competition, or the literature. The raster registry audit can compare
outputs but cannot establish method-level novelty from every sibling repository's
source code.

## Ranked, unexecuted candidates

| Rank | Hypothesis; inputs and test | Why it might find a missing fault | Named non-fault mimic and rejection test | Qualitative HOLDOUT-DTI potential / cost / availability | Novelty and decision status |
|---:|---|---|---|---|---|
| **1** | **Depth-resolved magnetotelluric (MT) boundary, tested independently of the existing shallow-conductivity feature.** First verify that DOE GDR submission 1391 actually supplies georeferenced, depth-resolved MT products over the competition footprint. If so, compute a spatially cross-validated lateral log-resistivity contrast and its persistence across verified depth slices; test each slice/derived feature alone, then require agreement with an independent gravity-basement edge. Do not treat `cond_surf` as a substitute for an unverified MT model. | A buried damage zone or fluid pathway could juxtapose resistive host rock and conductive alteration beneath cover, where a surface scarp is absent. This is a hypothesis about some geothermal faults, not all Quaternary faults. | **Saline playa brines and clay/evaporite-rich basin fill** can make strong conductors without a fault. Reject isolated shallow conductors; require a depth-persistent boundary and an independent structural edge, with all thresholds selected inside training folds. | **Potential: medium–high, conditional and uncertain. Cost: high** because resource contents, CRS, spatial coverage, and usable resolution must first be verified. No raw MT layers are present in this checkout. | Related to the existing `cond_surf` / `hydro_demag_clay_conj` channels and the archived CSPT conductivity work; a depth-resolved MT product is not in the active feature list, but was proposed in an earlier backlog. **Not globally novel; not tested here.** |
| **2** | **Multi-temporal Sentinel-1 InSAR displacement discontinuity with coherence and seasonal controls.** Only after verifying public scene coverage and a reproducible velocity product, test persistent line-of-sight displacement gradients across candidate structures; separate seasonal deformation and decorrelation, and use static gravity/terrain only as independent corroboration. | Persistent creep or interseismic deformation could reveal an active, covered fault lacking a mapped scarp. This will not detect most inactive or very slowly deforming Quaternary faults. | **Groundwater-pumping subsidence, geothermal production/injection, and volcanic inflation** can create deformation bowls or sharp gradients. Test temporal stability, hydrologic seasonality, and association with known production areas before treating a signal as tectonic. | **Potential: medium for the active subset; low-to-medium overall recall expected. Cost: high** (scene selection, time-series processing, atmospheric/topographic correction). No InSAR data or velocity grid is restored locally. | No InSAR implementation or receipt was found in the reviewed active code. Similar ideas occur in prior research notes, so this is **unexecuted, not a new global claim**. |
| **3** | **Three-dimensional relocated microseismicity-plane geometry, rather than another smoothed seismic-density band.** Obtain an authoritative event catalogue with locations, depth, time, and quality metadata; fit robust local planes to persistent event clusters and project plausible fault planes to the surface, requiring independent geophysical boundary support. Recompute any catalogue-derived features using only visible faults within each holdout fold. | A sufficiently active blind fault may organize hypocentres on a planar structure even without a surface expression. Sparse or dormant faults will be invisible to this test. | **Mine blasts, geothermal-operation-induced sequences, and network-detection/relocation artifacts** can resemble clusters or planes. Use event-time/site metadata, quality limits, temporal replication, and an independent structural check. | **Potential: medium–low and coverage-limited. Cost: medium–high** for catalog harmonization, quality control, and spatial clustering. Raw event points are not present; the supplied `deq_n100a15` / `ieq_n100a15` bands are not equivalent to event-plane geometry. | Event-density and seismicity ideas exist in prior notes, but no matching raw-event plane model or holdout result was found in the reviewed active code. **Method-level global novelty remains unverified.** |
| **4** | **Flight-line-aware re-leveling of GeoDAWN magnetic profiles using the original survey observations and navigation metadata.** If the USGS release provides suitable line-level data for the footprint, estimate traverse/tie-line and terrain-clearance residuals from the original observations; compare corrected magnetic contacts to independent gravity and basement-depth structure. Do not apply a hand-picked notch to the final grid and call the result a recovered fault. | Correcting survey artifacts may preserve real, covered basement discontinuities that are blurred or confused with line-direction striping in a gridded product. | **Dike swarms, intrusive contacts, and residual micro-leveling seams** can all produce linear magnetic responses. Require cross-line support and an independent gravity/depth signature; recognize that an artifact can be removed but a fault cannot be inferred from magnetic contrast alone. | **Potential: low–medium; cost: medium–high** because raw line observations, navigation, processing metadata, and coverage are prerequisites. Only gridded/derived GeoDAWN layers are represented in the local manifest; raw line data are not restored. | Existing magnetic gradients and profile-registration experiments make this a related, not orthogonal, family. The flight-line correction itself was proposed previously but was not validated here. **Not globally novel; not tested.** |

### Screened out as repeats or unsupported

- **Radiometric K/Th residuals:** the active feature code already computes `rad_k_th_alteration` and `hydro_demag_clay_conj`; a new ratio/residual without a separately justified measurement is not a distinct hypothesis.
- **Catalog-near relay, crack-tip, or Coulomb-stress variants:** the active stack includes tip/relay interactions; archived G79-CSPT and sibling work already explore stress/strain and network geometry. Do not restart or rename a stopped lane.
- **Scarp crest, drainage/knickpoint, absolute-elevation shoreline, and far-field distance-band variants:** these overlap active features or prior archived/sibling experiments and proposals, including explicit Lahontan/datum work. Their earlier failure to run, lack of absolute elevation, or weak holdout does not make them novel.
- **A 3DEP shoreline veto, by itself:** a useful potential confounder control, but prior 62GEMSDOE work tested closely related datum/shoreline ideas. Do not present it as an untried new method.

## Required gate before any future work

The latest restored-witness preflight is recorded at
[`evidence/preflight_bab8f374.json`](../evidence/preflight_bab8f374.json):
`start_new_lane: false`, state `impossible_under_literal_gate`, exit code `2`.
The SHA-256-pinned positive-support witness covers **all allowed cells** (fraction
`1.0` against a `0.70` limit). Under the currently required literal definition,
any non-empty candidate has `3 px` forward overlap `1.0`; this stops every item in
the table before implementation, surface analysis, placement, or holdout. No
candidate is exempted and no local overlap rule was changed.

If and only if the protocol owner prospectively resolves that gate, the next
candidate would still need a preregistration and verified data receipt, the shared
feature stack/evaluator/writer, whole-segment buffered hide-and-recover with
visible-only catalogue features and pixel-exact visible-fault masking, pooled
DTI (`alpha = 0.2`, `beta = 0.8`, `300 m` triangular kernel), per-feature leakage
canaries (`AUC > 0.90` is leakage until explained), and registry checks on the
continuous surface **before placement** and final dots **after placement**. A
separate selector decision is required before any weekly slot. This review ran
none of those scientific tests.

## Official sources and provenance limits

These are links from the repository's claim-by-claim source ledger. They were not
freshly fetched in this review; source access and specific claims must be checked
again before a new method uses them.

- [DrivenData problem, data, submission format, and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData staff clarification on masking known mapped-fault pixels](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)
- [USGS GeoDAWN airborne magnetic and radiometric data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE Geothermal Data Repository submission 1391](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP program](https://www.usgs.gov/3d-elevation-program)
- [USGS ComCat FDSN event API](https://earthquake.usgs.gov/fdsnws/event/1/)
- [NASA/JPL ARIA](https://aria-share.jpl.nasa.gov/) and [Alaska Satellite Facility](https://asf.alaska.edu/)
- [DOE / National Laboratory of the Rockies official competition rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- Project source-access notes and evidence classes: [`knowledge/official_sources.json`](../knowledge/official_sources.json); local input pins and missing files: [`registry/data_manifest.json`](../registry/data_manifest.json).

The current checkout does not contain `training_features.tif` or `data/raw/`;
its manifests record owner-mirror hashes, not organizer authentication. A previous
reported score, a local raster validator, and a public leaderboard observation
are not a submission-page receipt. No leaderboard improvement is claimed for any
candidate in this slate.
