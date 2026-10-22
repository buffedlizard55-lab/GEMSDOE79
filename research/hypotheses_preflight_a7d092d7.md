# Next-lane research backlog — 2026-10-22 (not executed)

**Pre-experiment shortlist, not measured performance.** The current request does not
contain a delimited single-method lane paragraph. No new scientific lane was
implicitly assigned. The inherited H79-NHR lane already stopped as a duplicate;
we will not retune it. Priority and cost below are qualitative research judgments,
**not DTI scores or leaderboard projections**. "Not tried" means not implemented
as a stand-alone *surface* in the active `src/gems79/` pipeline; some inputs and
related hypotheses have appeared in archived/sibling experiments. In particular,
SDPT already computed a facing-polarity feature, so that alone is not novel.

| Priority / cost | Layers and physical test | Why an unlisted fault, not only a mapped one? | Difference and named non-fault mimic | Inputs |
|---|---|---|---|---|
| 1 / medium-high | **Far-field conditional fault recovery:** `training_features.tif` (`det_elev`, `rtp`, `iso_grav_anom`) + lidar scarp descriptors + *visible-only* catalogue distance. Learn separate hide-and-recover rankings in distance bands, with a preregistered far-field >1 km validation arm rather than applying NHR's near-catalogue target everywhere. | The organizer's expert test faults are **not** in the catalogue; NHR's 300 m–2 km near-fault concentration is already occupied by older dot fields. An independent geomorphic/geophysical lineament far from the map could be a missed short piedmont fault. | NHR fits one pooled target, not distance-band-specific selection; unlike a dot jitter, this changes the geological conditional model. **Mimic:** Pluvial Lahontan shorelines and alluvial fan margins. Input mirrors are SHA-pinned; no new external data. |
| 2 / medium | **Cross-scale crest migration:** lidar `lapneg/lappos`, `step_max`, `coh100` + `det_elev` multiscale curvature; require a coherent scarp crest stable under 100–500 m smoothing while local signed curvature moves minimally along strike. | Short, degraded scarps omitted from compiled regional linework may persist at multiple scales where amplitude thresholds fail. | SDPT used crest-base dipoles and `step_max3`, but not displacement of a crest *between scales* as a continuity discriminator. **Mimic:** long terrace risers and abandoned shorelines. Cached lidar available through pinned public mirror; original USGS derivative provenance cannot be independently certified here. |
| 3 / medium | **Magnetic-marker break with an independent scarp:** `rtp`, `tmi_hg`, lidar `cross_max`, `upface/downface`; compare across-trace *termination* of magnetic marker and the existence of a narrow morphologic step, without fitting the gravity-edge registration lag used by E1. | Covered strands may disrupt basement fabric despite weak surface expression and therefore escape map digitizing. | Not E1's across-gravity *nonzero lag*, nor NHR's generic HGB feature stack; explicit marker termination and scarp coincidence. **Mimic:** intrusive contact or airborne levelling seam. GeoDAWN flight-line spacing is coarser than the grid; avoid claiming 100 m independent magnetic observations. |
| 4 / low | **Clay-cap/permeability discordance:** `cond_surf`, `depth_to_base_surf`, `iso_grav_anom`, lidar scarp; find local conductivity-edge departures crossing a gravity structural boundary, not a conductivity maximum. | Unmapped faults may change fluid pathways beneath cover even if map-visible stratigraphic contacts are absent. | STEPCO proposed cap *breaches*, not a cross-boundary discordance; conductivity resolution makes this speculative. **Mimic:** saline playa or lithologic conductor. Existing provided bands only, but no direct permeability observation. |

**Gate before any test:** Re-measured SHA-256-pinned public registry witness
[`evidence/witness_review_20261022_a7d092d7.json`](../evidence/witness_review_20261022_a7d092d7.json)
shows all 5,106,385 allowed cells covered by the literal positive support of a
prior raster. Therefore *any nonempty candidate* would have 3-pixel overlap
1.0 > 0.70, regardless of hypothesis. This is the mathematical reason we
**stopped before implementation / placement / holdout**: testing the top idea
would break the requested stop rule, and no winner can be selected. If the
protocol owner prospectively defines what counts as "dots" in continuous
surfaces, preregister a *new* single-method lane, run the surface and final
registry checks, individual-feature leakage canaries and shared buffered
hide-and-recover DTI on both seeds. Do not silently exempt a prior raster.

Sources (claims, not candidate scores):
[organizer problem, data and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[organizer reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution),
[local input provenance limits](../registry/data_manifest.json),
[existing experimental findings](../reports/nhr_analysis.md).
These are fault-detection proposals, **not** claims of geothermal-vent or reservoir discovery.
