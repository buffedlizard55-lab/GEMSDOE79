# Five candidate geological hypotheses — ranked before any holdout score (G79-UGBP session, 2026-10-22)

Status: written and frozen BEFORE running the holdout for the top candidate.
Scores below are qualitative expectations only — no number here is a measured
HOLDOUT-DTI or an ORGANIZER-CONFIRMED score. "Untried" means: not implemented
in this repository (`src/gems79/`, `scripts/run_*.py`, `run_card*.json` were
inventoried line by line for this session). Sibling-repo history is handled by
the registry novelty gate, not by this list.

Verified inputs (this checkout, SHA-256 pinned, `registry/data_manifest.json`,
restored 13/13 this session): `training_features.tif` (19 float32 bands,
EPSG:32611, 3730×3292, 100 m), `data/raw/external/gdr_wellspring_in_footprint.csv`
(27,092 rows; whitelist columns only — the `dist_known_fault_px` column is a
leakage column and is never read), `geodawn_rad_u8.tif` (K, Th, U, TC),
`geodawn_extensions_u8.tif` (ThK, UK, UTh, TMI_up150),
`lidar_scarp_features_u8.tif` (12 bands), `tiger_road_distance_m.tif`.
Official metric/format: DrivenData competition 306 problem page
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):
DTI α=0.2, β=0.8, triangular kernel R=300 m; single float32 band, EPSG:32611,
100 m, values in [0,1], outside bounds null or NaN (see portal note in the
run card — the local zeros-outside writer is the range-safe convention used
by every shipped file in this repo family).

## Rank 1 — G79-UGBP: kinetic geothermometer-disequilibrium up-gradient back-projection (IMPLEMENTED THIS SESSION)

- **Layers:** GDR well/spring chemistry (`geothermquartz_c`,
  `geothermchalc_c`, `geothermcat_c`, `temp_c`, `row`, `col` — cation column
  `geothermcat_c` is never read by THVC, verified at
  `src/gems79/thvc_features.py:484-485` which whitelists only
  `temp_c/geothermquartz_c/geothermchalc_c` and smooths them isotropically);
  `training_features.tif` band 12 `det_elev` (uphill direction field);
  band 18 `iso_grav_anom_hg` (basement-step gate).
- **Physical signature:** dissolved silica re-equilibrates quickly during
  shallow lateral flow while Na–K–Ca cation ratios retain deep reservoir
  temperatures (Fournier 1977; Giggenbach 1988 — cited as mechanism, not as a
  measured result here). Distal outflow sites
  (`Tcat−Tqtz ≥ 25 °C`, `Tqtz−Tout ≥ 40 °C`, `Tcat ≥ 110 °C`; thresholds frozen
  in `registry/preregistration_g79_ugbp.json` before holdout) therefore point
  **up-gradient** (`+∇ det_elev`, streamline-followed 3–80 px) to a blind
  conduit, gated by shallow basement-step concordance
  (`× (0.25 + 0.75·rank(iso_grav_anom_hg))`). Proximal near-equilibrated sites
  deposit a 900 m isotropic conduit kernel. Inventory (pre-holdout, allowed):
  526 unique chemistry sites; 49 meet the frozen distal rule — sparse by
  design, which is why the candidate fuses these features into the shared
  hide-and-recover learner instead of emitting from them alone (Exp1 still
  tests the pure surface as a falsification control).
- **Why it should catch catalogue-missing faults:** blind range-front
  step-over and intra-basin feeder faults under permeable piedmont fans have
  no surface scarp for the USGS/INGENIOUS compilation, but their upflow feeds
  exactly these laterally displaced hot springs/wells.
- **Difference from this repo:** every thermal lane here (THVC Group B,
  FNHR, CSKD) places radially symmetric kernels at the sample point or uses
  quartz temperature alone; none uses cation–quartz disequilibrium, conductive
  drop, or topographic streamline advection. TIPSTEP (0.0927/0.0928
  HOLDOUT-DTI) is catalogue-geometry only and uses no chemistry at all.
- **Named non-fault mimic:** lateral thermal groundwater plumes in alluvial-fan
  channels and agricultural irrigation-return wells. Falsification: if the
  up-gradient surface does not beat the distal-isotropic control feature on
  the holdout canary/Exp1, the advection mechanism is rejected.
- **Expected value / cost:** highest geothermal specificity and highest
  spatial orthogonality to near-catalogue dot fields (dots land 0.3–8 km from
  the thermal sample); low implementation cost (points + two rasters). Holdout
  leverage is uncertain because the catalogue holdout under-represents blind
  geothermal faults — stated, not hidden.

## Rank 2 — G79-BLC: bilateral lithology-contrast change-point along potential-field ridges

- **Layers:** band 2 `rtp`, band 13 `iso_grav_anom`,
  `geodawn_rad_u8.tif` K/Th/U (ordinal ranks only), `depth_to_base_surf` b15.
- **Signature:** along a data-derived (catalogue-free) ridge, a persistent
  abrupt change in the *joint distribution* of opposite-flank samples
  (two-sample statistic along strike), not edge magnitude at a point.
- **Why missing faults:** a transfer fault can offset pre-existing lithologic
  contacts under alluvium while its own trace has weak relief.
- **Difference:** E1/fabric-offset measures across-normal lag at a pixel;
  THVC/CSKD use local gradients, crests and Euler estimates. No along-strike
  bilateral change-point exists in this repo.
- **Mimic:** depositional facies changes and lava-flow margins. Control:
  require independent gravity support and leave-one-quadrant replication.
- **Value/cost:** low–moderate, uncertain; moderate–high cost (ridge tracking
  + along-track sampling is the most bug-prone build here). Data-ready.

## Rank 3 — G79-PSDC: playa phreatic redox-barrier lineaments

- **Layers:** `geodawn_extensions_u8.tif` UTh, rad U/Th, band 11
  `iso_grav_anom_vg`, band 17 `cond_surf`, CSV `spring_features` rows,
  `tiger_road_distance_m.tif` veto (>200 m from roads).
- **Signature:** collinear U/Th roll-front enrichment + spring alignments +
  gravity vertical-gradient zero-crossings *inside* zero-relief playa masks.
- **Why missing faults:** playa flooding/deflation erases scarps in centuries;
  intrabasinal transfer faults survive only as groundwater barriers.
- **Difference:** THVC uses `rad_u_th_redox` globally as a pixel feature; no
  playa-gated lineament collinearity or road-vetoed object test exists here.
- **Mimic:** lunette dunes, desiccation polygons, railroad/playa causeways
  (road veto + gravity persistence are the rejection filters).
- **Value/cost:** low–moderate; low–medium cost. Data-ready.

## Rank 4 — G79-RSS: relief-screened structural saddle with crossing gravity contrast

- **Layers:** band 12 `det_elev`, band 19 `det_elev_slope`, band 13
  `iso_grav_anom`, band 18 `iso_grav_anom_hg`.
- **Signature:** multi-scale detrended-elevation saddles between basins that
  are *crossed* (not followed) by a gravity contrast.
- **Why missing faults:** low-relief transfer zones are under-mapped next to
  long range-front scarps. Starts from terrain topology, not fault tips.
- **Difference:** TIPSTEP/THVC mechanics start from visible endpoints; no
  catalogue-free saddle field exists in this repo.
- **Mimic:** wind gaps, stream capture, resistant-bedrock saddles. Terrain-only
  ablation must fail where the gravity crossing is absent.
- **Value/cost:** low, uncertain; moderate cost. Limitation: `det_elev` is
  detrended topography, not a hydrologic DEM — no flow routing is claimed.

## Rank 5 — G79-MCST: GPS principal-strain dilation tendency on buried contacts (NOT VIABLE THIS SESSION)

- **Layers:** Nevada Geodetic Laboratory MIDAS velocities
  (`https://geodesy.unr.edu/gps_timeseries/IGS20/midas/midas.NA.txt`;
  Blewitt, Hammond & Kreemer 2018, DOI 10.1029/2018EO104623 — free, official
  source, manually checkable) + local strike of `rtp`/gravity ridges.
- **Signature:** dilation tendency `cos²(θ − (φext + 90°))` weighting buried
  contacts by alignment with the principal extension azimuth — the existing
  bands 4/7/8 are rotation-invariant scalars and carry no azimuth.
- **Why missing faults:** Walker Lane step-overs distribute 1–4 mm/yr over
  many short buried faults below paleoseismic compilation thresholds.
- **Difference:** DILSTEP multiplied scalar dilatation by gradients; no
  directional strain azimuth exists in this repo.
- **Mimic:** Mesozoic thrust contacts parallel to modern extension.
- **Availability gate (checked, failed for this sandbox):** the source is free
  and official, but this sandbox's egress allowlist (github.com / pypi.org /
  npmjs.org) cannot fetch `geodesy.unr.edu`. It needs an owner mirror +
  SHA-256 manifest entry before it is viable. Ranked last for that reason
  alone — not proposed as runnable now.

## Selection

Top candidate **G79-UGBP** is validated on the shared spatially-blocked
holdout (`gems57-pooled-hide-v2`) before any slot decision, per protocol.
Promotion requires beating the frozen incumbents G79-THVC
HOLDOUT-DTI 0.1905 (seed 20, n=11,321) and 0.1944 (seed 30, n=11,342) on
**both** seeds, plus novelty and format gates. Nothing here projects a
leaderboard score; the reported H33 0.2778 remains an unverified historical
report and 0.4413 a public-leaderboard observation for another entrant.
