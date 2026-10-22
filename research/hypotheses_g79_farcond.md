# G79-FARCOND: Far-field conditional fault discovery — 5 ranked hypotheses (2026-10-22)

**Scope:** Candidate geological hypotheses not tried as a standalone surface in this repo's active src/gems79/ pipeline. "Not tried" checked against src/, scripts/, vendor/gems57/, and archived lanes (G79-FABRIC-OFFSET, H79-NHR, G79-STEPCO, G79B-SDPT, H79-FF, H79-MCT, H79-CSPT). No claim about wider GEMSDOE family. Ranks are qualitative expected DTI improvement vs cost, not leaderboard projections.

**Requirement from prompt:** Each hypothesis names specific layer(s), physical signature (e.g., edge/curvature transform), why it should catch a fault missing from USGS/INGENIOUS catalogue, and how it differs from existing implementation.

## Ranked candidates

### 1. Far-field conditional fault recovery (distance-stratified nested hide-and-recover)
- **Layers:** `training_features.tif` bands `det_elev` (detrended elevation), `iso_grav_anom` (isostatic gravity anomaly), `rtp` (reduced-to-pole magnetics) — multiscale `gradmag` (sigma 1/3 px for det_elev, 2/5 px for gravity/RTP) and `LoG`; `external/lidar_scarp_features_u8.tif` bands `step_max` (1m scarp step 2–8m), `ex_max` (extended elevation), `lapneg_max/lappos_max` (concavity/convexity), `downface_max/upface_max`, `cross_max`, `coh100` (100m coherence), plus `external/geodawn_rad_u8.tif` (K, Th, U) and geometry from visible catalogue only (`log_dist_visible`, `visible_density_s5/s20`, `log_dist_visible_tip`, `lidar_strike_alignment`, `strike_field_coherence`).
- **Physical signature:** Basin-and-Range normal faults are multi-strand: synthetic/antithetic subsidiaries, step-overs, and tip continuations lie 0.3–3 km from mapped traces and share regional strike (N-S to NNE). Where they offset Quaternary pediments they leave 10–50 m lidar-resolvable scarps (slope excess, 10–50 m step, crest convexity/base concavity). Signature is **conditional ranking P(kernel credit | visible geometry, distance band, terrain/geophysics)** learned via nested hide-and-recover (withhold 20% whole 8-connected components, 3 px collar, recompute geometry from visible only, target = 300 m triangular kernel credit `max(1-d/3px,0)` toward withheld component). Stratified by distance band (>1 km far-field vs 0.3–1 km near-field) to avoid pooled model over-weighting near-catalogue mimics.
- **Why missing, not mapped:** Organizer's expert test faults are *by definition* absent from public USGS database (problem description). Short (<5 km) piedmont faults far from range fronts are omitted from compiled regional linework due to limited Quaternary field mapping in pediments and thin alluvial cover hiding subtle scarps. Far-field independent lineaments are more likely to be unmapped short faults than near-catalogue splay rediscovery.
- **Difference:** H79-NHR already did pooled nested learning with same inputs but single global model; its dots fell at median 539 m from catalogue (vs H33's 1.96 km) and duplicated 26 near-fault dot fields. This lane adds **distance-band stratification** and preregistered far-field validation arm; emission masked to >1 km from catalogue to force novelty. Not E1's magnetic-lag fabric offset, not STEPCO's multi-field step dipole.
- **Named mimic:** Pluvial Lake Lahontan shoreline/terrace risers (contour-parallel steps at ~1330 m, incised channel banks, roads/mine benches) — same 2–10 m step scale near range fronts.
- **Expected DTI / Cost:** Medium-high / Medium-high (nested replicates 3×, HGB Regressor max_iter 250, need to build static stack ~400M).
- **Viability:** All inputs pinned SHA-256 and restorable via GitHub mirror (checked: training_features.tif 4371c82e..., lidar_scarp_features_u8.tif d580bb..., geodawn_rad_u8.tif c22420f..., geodawn_extensions_u8.tif a35a..., existing_faults.tif 7ba308c...). No new external data needed.

### 2. Cross-scale crest migration stability (lidar multi-scale coherence)
- **Layers:** `lidar_scarp_features_u8.tif` `lapneg_max`, `lappos_max`, `step_max`, `coh100` + `training_features.tif` `det_elev` multiscale curvature (Gaussian LoG sigma 1,3,5 px). No catalogue geometry.
- **Physical signature:** True fault scarp has coherent crest line stable under 100–500 m Gaussian smoothing; signed curvature (`lapneg` concave base, `lappos` convex crest) displaces minimally along strike between scales (<50 m migration). Terrace risers and shorelines show large cross-scale crest migration and decorrelate. Signature = **crest persistence + low cross-scale LoG displacement** (structure-tensor coherence across scales).
- **Why missing:** Degraded short scarps (1–2 m, eroded) fail single-scale amplitude threshold (`step_max`) but persist at multiple scales; mappers digitizing at 1:24k miss them.
- **Difference:** SDPT used `step_max3` and dipole magnitudes but not *crest displacement between scales* as continuity discriminator. NHR used multiscale LoG as generic inputs, not explicit crest-migration feature.
- **Mimic:** Long fluvial terrace risers, abandoned Lahontan shorelines (contour-parallel, extensive).
- **Expected / Cost:** Medium / Medium (requires Gaussian pyramid, no training, but need to compute displacement field).
- **Viability:** Cached lidar available (d580bb...); 10 m 3DEP derivatives synthesizable; no new data.

### 3. Magnetic fabric-break with independent lidar scarp (terminator model)
- **Layers:** `training_features.tif` `rtp`, `tmi_hg` (magnetic horizontal gradient); `lidar_scarp_features_u8.tif` `cross_max`, `upface_max/downface_max`. Optional `geodawn_extensions_u8.tif` `TMI_up150`.
- **Physical signature:** Buried normal fault offsets magnetic basement, terminating linear magnetic marker (RTP lineament) with abrupt **across-trace decorrelation** (>0.4 drop in along-strike correlation within 300 m) + coincident narrow morphologic step (<20 m wide) not parallel to flight lines. Transform = normalized cross-correlation of RTP profiles across candidate trace normals, thresholded, then gated by lidar scarp presence.
- **Why missing:** Covered strands under 2–5 m alluvium have weak surface expression but offset highly magnetic Miocene volcanics/basement; not digitized from aerial photos.
- **Difference:** Not E1's gravity-gradient registration lag (nonzero lag across gravity edge), nor NHR's generic HGB stack; explicit *magnetic marker termination* + scarp coincidence. STEPCO used step-dipole across many fields, not terminator logic.
- **Mimic:** Intrusive dike contact, airborne levelling seam (flight-line artifact; GeoDAWN 400 m lines, 4 km ties).
- **Expected / Cost:** Medium-low / Medium (need to handle levelling geometry, but inputs present).
- **Viability:** All bands present; flight-line geometry in USGS GeoDAWN publication (not mirrored) but not required for first test (azimuth filter approximated).

### 4. Antislope drainage-terrace discordance (hydro-geomorphic)
- **Layers:** USGS 3DEP 1 m DEM (derived hydrologic: flow accumulation, curvature, chi) + `lidar_scarp_features_u8.tif` `step_max`, `ex_max` + `existing_faults.tif` (mask). DEM links via `Digital-elevation-model-links-JSON.pdf` (free USGS The National Map).
- **Physical signature:** Fault scarp deflects drainage: knickpoint in `chi` (channel steepness), antislope terrace riser where drainage incises across scarp at high angle (>60°), offset terrace treads. Transform = chi anomaly + terrace tread offset measured orthogonal to scarp strike.
- **Why missing:** Drainage integrates 10 kyr cumulative offset, recording faults with no single-event scarp but cumulative drainage diversion; mappers focus on range-front scarps, not piedmont drainage anomalies.
- **Mimic:** Lithologic knickpoint (bedrock change), road culvert / canal.
- **Expected / Cost:** Low-medium / Medium-high (need hydrologic processing from 1 m DEM mosaic; links available but large download).
- **Viability:** Free official source: USGS 3DEP via National Map (https://www.usgs.gov/3d-elevation-program) — obtainable, but not on allowlist GitHub; need unrestricted machine with `data/1m_DEM_links.csv`. Not yet cached here → **not viable this session without new external download**.
- **Difference:** No prior lane used hydrologic topology; previous used only scarp amplitude.

### 5. Clay-cap conductivity-gravity discordance (permeability proxy)
- **Layers:** `training_features.tif` `cond_surf` (surface conductivity), `depth_to_base_surf`, `iso_grav_anom`; lidar scarp.
- **Physical signature:** Geothermal-favorable fault breaches clay cap: local conductivity edge that **crosses** a gravity structural boundary (discordance angle >30°) rather than paralleling it. Transform = gradient orientation difference between conductivity and gravity, high where they diverge, then scored by nearby lidar scarp.
- **Why missing:** Unmapped faults affect permeability beneath cover without stratigraphic contact; geothermal relevance.
- **Difference:** STEPCO proposed cap *breaches* as conductivity maxima, not cross-boundary discordance.
- **Mimic:** Saline playa / lithologic conductor (parallel to structure).
- **Expected / Cost:** Low / Low (speculative; conductivity resolution 100 m >> fault width).
- **Viability:** Existing bands only, but no direct permeability observation.

## Ranking

| Priority | Hypothesis | Expected DTI gain vs H33 control (qualitative) | Cost | Viability now | Rationale |
|---|---|---|---|---|---|
| 1 | Far-field conditional (#1) | Highest (targets unmapped population, fixes NHR's near-field duplicate, 0.047 Δ already shown pooled) | Medium-high | Yes (all SHA-pinned, restorable) | Directly addresses duplicate blocker (26/30 halos) by moving median from 0.5 km to >1 km; retains proven nested target; far-field validation arm is new. |
| 2 | Cross-scale crest migration (#2) | Medium | Medium | Yes | Amplitude-threshold failure is documented; coherence across scales is orthogonal to H19-5's single-scale stack; no training needed. |
| 3 | Magnetic terminator (#3) | Medium-low | Medium | Yes | Buried faults are classic missing population; magnetic data is independent of topography used by H33 family. |
| 4 | Hydro-geomorphic (#4) | Low-medium | Medium-high | No (needs 1m DEM download) | Requires new USGS 3DEP mosaic (official, free, but >10 GB, needs allowlist exception). |
| 5 | Clay-cap discordance (#5) | Low | Low | Yes but speculative | Conductivity is too smooth for 100 m fault detection; prior STEPCO already tried cap idea with low holdout. |

## Validation plan for #1 before weekly slot

- Use shared `gems57-pooled-hide-v2` buffered whole-component hide-and-recover (buffer 3 px, erosion 12 px, seeds 20/30, 1000-draw paired 20 km spatial-cluster bootstrap).
- Leakage canary: every static + geometry feature alone, symmetric AUC ≤0.90 on both seeds (464 tests).
- Surface Spearman ≤0.90 and dot forward 3 px overlap ≤0.70 vs all 992 registry rasters under `budget-matched-v3` dot definition (continuous surfaces top-k). Check *before* placement (surface top-k) and *after* (final dots).
- Must beat H33 fold-fair control (0.0961/0.0989) on both seeds with paired CI excluding 0 vs uniform control.
- Only after all gates pass may selector promote; otherwise negative deliverable.

Sources: [organizer problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) (flight lines 400 m), [organizer reference baseline](https://github.com/drivendataorg/gems-prize-reference-solution), [local provenance limits](../registry/data_manifest.json), [H33 forensics](../evidence/h33_forensics.json), [NHR analysis](../reports/nhr_analysis.md).
