# Research shortlist — Arena session `7c7104d8` (not executed)

**Status:** no new scientific lane was opened. This is a prospective shortlist,
not a preregistration, score, or promotion recommendation. “Expected DTI
improvement” is a qualitative research prior only; no number is projected.
The current request still does not delimit a single method paragraph. More
importantly, the pinned literal-overlap witness rejects every nonempty candidate
before feature construction, holdout, or placement. See
[`evidence/new_lane_preflight_a7d092d7.json`](../evidence/new_lane_preflight_a7d092d7.json)
and the session review.

The candidate comparisons below are deliberately scoped to **method-level
novelty in this checkout and its archived code**, not a claim that nobody in the
GEMSDOE family or scientific literature has tried similar work. Related prior
art is named in each row. Every candidate needs a fresh, complete surface
novelty preflight before any holdout under an authorized protocol.

| Rank / expected DTI potential / cost | Exact layers and physical signature | Why it could locate a fault absent from the USGS/INGENIOUS catalogue | Difference from this repository and nearest prior art | Named non-fault mimic | Official source and availability check |
|---|---|---|---|---|---|
| **1 · medium-high potential · high cost** | **Flight-line-resolved GeoDAWN anomaly coherence.** Original magnetic/radiometric line observations, flight-path geometry, aircraft-height and tie-line metadata, with the existing gravity/RTP grids as context. Remove regional and line/tie-line levelling components, then require a signed cross-line anomaly to persist on adjacent flight lines and at independent crossovers. | A basement fault under basin cover may have no mapped scarp; a subsurface magnetic/contact offset can persist across several flight lines even where the gridded product smooths it. This targets structural evidence, not geothermal temperature directly. | The active E1 used *gridded* magnetic/gravity profile registration; prior family work includes grid-level seam correction (for example the `GEMSDOE73` seam-free potential-field result). The proposed distinction is the line-level observation/height/tie-line residual model, not another raster edge or a new name for E1. Family-wide novelty is unproven. | Tie-line or microlevelling residual, flight-height variation, an intrusive contact or dyke. | [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI `10.5066/P93LGLVQ`. The checked-in source ledger previously records line data and flight paths as release products. This checkout has gridded/uint8 derivatives only: no raw line observations or flight-path files in `registry/data_manifest.json`, `data/raw/`, or `.cache/`. The USGS host is outside this session's egress allowlist, so exact file coverage and direct download were **not** verified now. **Not viable for this session.** The recorded 400 m flight-line spacing also makes a 300 m scoring kernel a serious localization constraint; a 100 m grid is not 100 m independent measurement spacing. |
| **2 · medium potential · high cost** | **Station-level magnetotelluric phase-tensor anisotropy.** Raw complex MT impedance tensors and frequencies from the DOE GDR compilation, with `cond_surf`, `depth_to_base_surf`, and gravity only as contextual rasters. Extract phase-tensor strike, skew/ellipticity, and cross-station directional coherence; test a coherent conductive corridor rather than a scalar conductivity maximum. | A fault-controlled fluid/alteration pathway can be structurally important without a surface lineament, and its directional electrical response could mark a fault not represented in the public fault map. The prediction target remains a fault, not a geothermal reservoir. | The supplied stack contains a smooth scalar `cond_surf` band; archived family methods include scalar conductivity, clay-cap and hydrothermal-proxy surfaces. No active/archived runner in this checkout was found using the **raw frequency-dependent impedance/phase tensor** as its feature. This is a method-level distinction, not evidence of family-wide novelty. | Conductive clay cap, saline basin fill, graphite-bearing lithology, or hydrothermal alteration without a discrete fault trace. | [DOE Geothermal Data Repository submission 1391](https://gdr.openei.org/submissions/1391). The previously reviewed official source description includes MT among the compilation products. The local manifest has selected derivative well/spring/vent files but no MT station tensor or impedance file; no direct GDR binary was obtained here, and the host is outside the allowlist. Coverage, station spacing, and downloadability for this footprint are **unverified**. **Not viable for this session.** |
| **3 · low-medium potential · medium-high cost** | **Process-based lidar scarp-profile inversion.** Raw 1 m DEM elevations, with the existing lidar `step_max`, `lapneg/lappos`, `upface/downface`, `cross_max`, and `coh100` channels for transect proposals. Fit a fixed linear-diffusion scarp-profile family across perpendicular transects and score profile-shape consistency along strike, rather than ranking amplitude alone. | Subdued or degraded Quaternary fault scarps can retain a characteristic cross-scarp shape after their peak slope falls below a hand-mapping threshold. A spatially coherent profile family may recover short traces missing from the catalogue. | NHR and SDPT tested multiscale scarp amplitudes, curvature dipoles, facing and persistence; the proposed statistic is an explicit process-profile fit. This is adjacent to existing terrain work, and its incremental value is uncertain. | Lahontan shoreline/terrace riser, alluvial-fan lobe boundary, landslide headscarp, or channel bank. | [USGS 3D Elevation Program](https://www.usgs.gov/3d-elevation-program). The project has only the derived uint8 lidar-scarp stack in its manifest, not raw 1 m elevations; no `1m_DEM_links.csv` or raw DEM is present in the current checkout. The USGS host is outside the allowlist and tile coverage was not verified in this session. **Not viable for this session.** |

## Decision and required gates

1. The strongest *scientific* candidate in this qualitative ranking is the
   flight-line-resolved GeoDAWN method, but its raw source files are not in the
   checkout and were not verified downloadable. It is **not** an authorized or
   executable top candidate here. The other ideas also lack the named raw data.
2. Before attempting any candidate, resolve the missing method-paragraph
   assignment and the literal continuous-raster definition through a
   prospective protocol clarification. The verified whole-footprint witness
   gives every nonempty candidate overlap `1.0 > 0.70`; changing a method,
   filename, or data source cannot make that gate pass. Do not silently adopt a
   top-k interpretation or exclude a prior.
3. If those blockers are resolved, preregister one exact method, then use the
   pinned feature stack, shared `evaluate_holdout.py`, and shared submission
   writer. Complete the surface novelty check **before placement**, run every
   single-feature leakage canary, and compare buffered whole-component
   HOLDOUT-DTI against the matched incumbent with paired spatial CIs. A new
   HOLDOUT-DTI must include evaluator version, withheld-positive count, and 95%
   CI. A weekly slot remains a separate selector/account decision.

No holdout was run for these hypotheses, no score is inferred, no TIFF was
created from them, and no submission slot was used. Negative feasibility is the
current result, not a reason to bypass a gate.

## Manual-review sources

These URLs are official source leads already recorded in
[`knowledge/official_sources.json`](../knowledge/official_sources.json) or the
prior hypothesis register. They were **not** refetched during this session;
source-claim freshness is limited to the dated ledger, and exact new product
availability is not established by a landing-page link.

- [DrivenData problem description and scoring rules](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE GDR submission 1391 / INGENIOUS](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [Competition reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution)
