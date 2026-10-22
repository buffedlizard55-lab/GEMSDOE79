# Follow-up hypothesis shortlist — 2026-10-22

This shortlist was written after reviewing the full current project brief, the
active H79-NHR card, all current and archived lane code/hypothesis registers,
the 992-entry owner-mirror raster inventory, and the newly checked official
USGS / GDR / USGS ComCat pages. Ranks are **qualitative priors for expected
HOLDOUT-DTI gain versus implementation cost**, not scores or leaderboard
projections. No claim of novelty outside this repository is made.

The previously preregistered H79-NHR top hypothesis has already been tested
once. It is **not** revived or re-ranked here. H79-NHR remains stopped and
negative after failing both surface and final-dot uniqueness.

## Ranked new geological hypotheses

| Rank | Hypothesis, layers, physical signature | Why it could reveal faults missing from the catalogue | Difference from this repository's tested/archived lanes | Expected gain / cost (qualitative) | Named non-fault mimic | Official data status / eligibility |
|---|---|---|---|---|---|---|
| **1 — prospective top** | **Background-corrected heat-flow residual corridors.** Use the USGS 2022 Great Basin heat-flow point residual (well observation minus the locally estimated background conductive trend), retaining the release's measurement-quality fields. The candidate signal is a spatially coherent signed residual anomaly, not the absolute smoothed heat-flow map; compare it with the supplied conductivity, depth-to-basement, gravity-gradient and elevation context. | A blind fault that channels hydrothermal or groundwater flow can produce a local departure from background conductive heat flow even where no surface scarp or mapped trace exists. The USGS release specifically describes its residual field as potentially useful for identifying hydrothermal or groundwater influence. | The reviewed active/archived code uses shallow temperature probes, geothermometer values, radiometrics, conductivity, or geothermal point proximity, but no lane in this repository uses the USGS **well residual from a background-conductive heat-flow model**. This is a new data/mechanism, not a retuning of H79-NHR. | **Medium, high uncertainty / high**: the physical link to fluid pathways is strong, but the target is a fault map rather than a geothermal-resource map; point spacing, quality, and interpolation may dominate. | Topographic groundwater circulation, lateral aquifer flow, well-depth/completion effects, local lithology, and measurement-quality differences can create residual clusters without a fault. | USGS ScienceBase lists a public 124.12 MB ZIP (DOI [10.5066/P9BZPVUC](https://doi.org/10.5066/P9BZPVUC)) and documents the residual. Its attached-file MD5 is recorded in [`knowledge/official_sources.json`](../knowledge/official_sources.json). The binary was **not downloaded**; a `fetch_page` attempt returned HTTP 500. The release's use/reuse terms and native schema must be checked from the downloaded metadata before processing. **Not executable in this sandbox yet.** |
| **2** | **Depth-coherent MT conductance pathways.** Use the USGS conductance rasters at 2–12, 12–20, 20–50, 50–90, and 90–200 km depth, with the supplied conductivity, basement-depth, gravity-gradient and geodetic-dilation bands. Signature: a laterally continuous conductor that persists across crustal depth intervals and is spatially related to a shallow structural boundary. | Fault zones may connect deep conductive fluids to the upper crust, including under basin fill where surface expression is weak. Depth persistence could distinguish a through-going structure from a shallow lithologic edge. | No reviewed lane uses these **depth-sliced USGS 3D MT conductance maps**. The supplied `cond_surf` is not a substitute for depth-resolved conductance. Existing clay-cap / conductivity hypotheses use the supplied regional surface layer, not this depth sequence. | **Low–medium / high**: fluid pathways are physically relevant, but the inversion is regional and likely much coarser than 100 m; this may only rank broad corridors, not fault traces. | Graphitic/metamorphic units, saline basin fill, conductive alteration unrelated to a fault, and inversion smoothing. | Official USGS release [10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU) lists five 3.94 MB GeoTIFFs in native EPSG:4269, derived from >800 MT transfer functions. No binary downloaded; effective spatial support and alignment remain unverified. **Not executable until retrieved and screened.** |
| **3** | **Focal-mechanism stress compatibility of independent lineaments.** Use public USGS ComCat focal-mechanism / moment-tensor products to estimate a spatial stress-orientation field; compare it with lineament orientation inferred only from non-catalogue raster structure (magnetic/gravity/lidar), and the supplied geodetic strain bands. Do not use Qfault geometries or fault-segment tendency values. | Active, unmapped normal faults may be expressed by local seismic mechanisms and geodetic strain even where mapped inventories are incomplete. Stress compatibility could prioritize one of several raster-derived lineament orientations. | The supplied stack has earthquake distance/intensity summaries but no focal-mechanism tensors; reviewed lanes use lineament geometry and strain, not an independently estimated stress field from ComCat. | **Low–medium / medium–high**: mechanistically targeted but limited to active structures, potentially sparse mechanism coverage, and has additional inversion/uncertainty work. | Induced geothermal seismicity, non-fault seismicity, network detection/completeness, and stress heterogeneity. | Official [USGS ComCat overview](https://earthquake.usgs.gov/data/comcat/index.php) and [FDSN event service](https://earthquake.usgs.gov/fdsnws/event/1/) document public catalog products and product-type queries. An exploratory broad query returned features, but no regional catalog was saved or counted; coverage must be audited before eligibility. |
| **4 — rejected before implementation** | **USGS Quaternary-fault slip/dilation tendency.** The release contains stress-conditioned slip and dilation tendencies for mapped Quaternary fault segments. | Favorably oriented faults may be more likely to host hydrothermal processes. | The USGS release states that its segment geometries are based on a database modified after the USGS Qfault database. | The geology is plausible; the apparent gain could be high, but the leakage risk is unacceptable. | Regional stress heterogeneity and lithology may make a segment's computed tendency unrepresentative of nearby blind faults. | Official release [10.5066/P9YL58W6](https://doi.org/10.5066/P9YL58W6) is public and lists shapefile/KMZ resources. **Ineligible as a holdout feature:** rasterized fault-segment tendency would reintroduce target-catalogue geometry into the predictor and could trivially reveal withheld components. It is retained as source context only. |

## Decision: no new holdout lane is currently eligible

HFR is the top **prospective** hypothesis, not an active or executed lane. No
new lane was preregistered for holdout because two hard prerequisites are unmet:

1. The USGS heat-flow archive is listed publicly, but its binary was not
   retrieved, SHA-256 pinned, or checked for field names, units, quality
   categories, spatial coverage, and projection. No surrogate or copied value
   was substituted.
2. The existing uniqueness scan is incomplete: **986 of 992** registry rasters
   were comparable, with six TIFF/grid/transform errors. Restoring all 992
   byte blobs did not fix those comparison errors. A fail-closed scan cannot
   certify a new surface against an incomplete inventory.

There is also a decisive budget constraint for the currently used
**37,654-dot** emission. The verified 13GEMSDOE 5-pixel lattice's 3-pixel halo
leaves 6,514 allowed cells outside the halo. Even if every candidate dot were
placed in those cells first, at most 6,514 of 37,654 dots could avoid that
one registry raster; at least **82.70%** would overlap, above the protocol's
70% limit. This is a geometric upper bound, independent of the geology. It
applies to that budget and this registry raster; it does **not** prove that
all smaller-budget maps are impossible. We do not choose a smaller budget or
apply a chance correction after observing the result.

Therefore there is **no new preregistration, surface, holdout experiment, TIFF,
upload, or slot selection** in this continuation. The previously authorized
H79-NHR lane remains stopped; this is not permission to resume it. The next
scientific step requires a complete, comparable registry scan and a legitimate
source-data path, followed by one fixed preregistration and a surface-only
uniqueness gate before any holdout work.

## Newly verified official sources

- [USGS heat-flow release](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28), DOI
  [10.5066/P9BZPVUC](https://doi.org/10.5066/P9BZPVUC): background conductive
  heat-flow maps and well residuals; public 124.12 MB attachment listed.
- [USGS electrical conductance maps](https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b), DOI
  [10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU): five 2–200 km depth
  intervals from a 3D MT inversion; GeoTIFFs listed.
- [USGS slip/dilation tendency release](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d), DOI
  [10.5066/P9YL58W6](https://doi.org/10.5066/P9YL58W6): useful for geologic
  context but not an independent holdout predictor because it uses Qfault-based
  segment geometries.
- [USGS ComCat](https://earthquake.usgs.gov/data/comcat/index.php): public
  focal-mechanism/moment-tensor products and event-query documentation.
- [DOE GDR INGENIOUS compilation](https://gdr.openei.org/submissions/1391), DOI
  [10.15121/1881483](https://doi.org/10.15121/1881483): publicly accessible
  CC BY 4.0 resource listing; 116.98 MB across nine files. Listing availability
  is not a claim that a new archive was downloaded.
