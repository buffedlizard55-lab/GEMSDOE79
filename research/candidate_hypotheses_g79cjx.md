# Five candidate hypotheses for GEMSDOE79 — ranked

## 1. G79-CJX: Cross-scale contact-junction winding (TOP)
- **Layers**: `training_features.tif` band 2 `rtp` (reduced-to-pole magnetics) + band 13 `iso_grav_anom` (isostatic gravity anomaly). Both verified via registry/data_manifest.json SHA 4371c82e.
- **Signature**: Multi-scale ridge director winding / Harris corner persistence across σ=2,5,10 px smoothing, requiring concordant cross-contact contrast in both fields (signed difference across the junction). Computed as: `junction = Harris(RTP_sm, Grav_sm) × rank(HGM_rtp) × rank(HGM_grav)` where Harris uses structure tensor of summed gradient products. Phase-randomized field null for background.
- **Why blind**: Buried fault intersections/terminations offset density/susceptibility contrasts without surface scarp (e.g., Fallon–Fernley transfer zone, 39.5°N, 118.5°W). Surface-only maps miss these.
- **Differs from**: E1 measured lagged cross-correlation along gravity normals; THVC used ensemble + endpoint cones; neither computed winding persistence or Harris junctions against phase-randomized null. No catalogue features.
- **Mimic**: Pluton margins (e.g., Stillwater Range), volcanic caldera contacts, survey-block levelling seams. Falsification: test seam-coincident junctions vs off-seam; require scale-persistence (>2 scales) and dual-field concordance.
- **Expected DTI**: +0.02–0.05 vs THVC holdout (0.19) with moderate cost; data-ready now.

## 2. G79-DRAIN-CHI: Drainage χ knickpoint corridor
- **Layers**: band 12 `det_elev`, band 19 `det_elev_slope`, band 18 `iso_grav_anom_hg`
- **Signature**: χ-transform of detrended elevation (not hydrologic DEM) to find knickpoints, density of knickpoint clusters, co-location with gravity HGM ridge within 500–800 m.
- **Why blind**: Recent offset perturbs river longitudinal profiles even where scarp eroded (Walker River, Carson Sink).
- **Differs**: Prior terrain features used quantile-bridged LiDAR scarps or chi stepped indirectly, never χ-knickpoint density × HGM co-location as standalone.
- **Mimic**: Lithology-controlled knickpoints, dam breaches. Require gravity support.
- **Expected DTI**: +0.01–0.03, moderate cost; data-ready but χ routing on detrended elev is methodologically risky.

## 3. G79-BLC: Bilateral lithology-contrast change-point
- **Layers**: bands 2+13 + external `geodawn_rad_u8.tif` (K/Th/U) rank-only
- **Signature**: Along-strike sliding window comparing ±flank joint distributions (Kolmogorov-Smirnov of K/Th ordering) for abrupt along-ridge change.
- **Why blind**: Transfer faults offset pre-existing lithologic contacts under alluvium.
- **Differs**: Not E1's across-normal lag; not scalar K/Th anomaly; it's along-contact distributional change.
- **Mimic**: Depositional facies boundaries. Needs gravity replication.
- **Expected**: Low-moderate (+0.01), high cost, radiometric calibration limited.

## 4. G79-LAH-SHORE: Lahontan shoreline warp
- **Layers**: `lidar_scarp_features_u8.tif` (if restored) + det_elev
- **Signature**: Systematic elevation residuals of mapped pluvial shoreline terraces vs gravity lineaments (detrended shoreline warp).
- **Why blind**: Blind faults warp shorelines without rupture (Lahontan highstand 1330 m).
- **Differs**: No prior lane used shoreline warps; all used scarp steps directly.
- **Mimic**: Differential compaction, eolian reworking. Needs independent grav test.
- **Expected**: Uncertain, moderate-high cost, shoreline mapping not cached.

## 5. G79-HFR-PAIRED: Paired heat-flow residuals
- **Layers**: USGS Heat Flow DOI 10.5066/P9BZPVUC well residuals + gravity corridors
- **Signature**: Paired warm/cool residuals aligned linearly across structural corridor (advective duplex).
- **Why blind**: Hydrothermal circulation reveals permeability.
- **Differs**: THVC used raw temps + spring points, not paired residual duplex vs conductive background.
- **Mimic**: Groundwater pumping, uneven sampling. Requires cluster-out CV.
- **Expected**: Promising but **NOT data-ready** (ZIP listing only, egress blocked in sandbox). Exclude.

**Ranking**: CJX > DRAIN-CHI > BLC > LAH > HFR (blocked). CJX nominated for implementation.

