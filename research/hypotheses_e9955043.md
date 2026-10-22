# Candidate Geological Hypotheses for Unmapped Geothermal Fault Discovery (Session e9955043)

## Research Context & Objectives
The DOE GEMS prize challenge focuses on predicting previously unmapped hidden faults in northwestern Nevada (GeoDAWN footprint, EPSG:32611, 100 m grid) to accelerate hidden geothermal resource discovery. The evaluation metric is the Distance-Weighted Tversky Index ($\alpha=0.2, \beta=0.8$, 300 m triangular kernel, mapped catalogue masked out).

Below are five prospective geological hypotheses targeting unmapped fault systems, ranked by expected DTI improvement and implementation feasibility.

---

### Candidate Hypothesis 1: Dilatational Relay-Ramp Stepover and Tip-Zone Kinematic Strain Lobes (STEP-RELAY)
- **Specific Layers Involved**: USGS 3DEP LiDAR 1 m & 10 m DEM derivatives (profile curvature, topographic openness, aspect-slope residuals), USGS QFaults & INGENIOUS mapped fault vector traces.
- **Physical Signature Targeted**: Tensor strain localization in overlapping normal fault tip zones. High-resolution second-order topographic curvature and step-height scarps along relay ramps connecting en-echelon normal fault segments (0.5–2.5 km offset corridors).
- **Missing Fault Rationale**: In Basin-and-Range extensional tectonics, normal faults propagate and transfer displacement across relay ramps and stepovers. The published catalogue frequently maps the major range-bounding segments but omits breached relay strands, connecting transfer faults, and wing cracks due to partial burial by alluvial fan deposits or short trace lengths.
- **Differences from Existing Implementations**: Existing implementations (e.g., simple distance buffers or isotropic Poisson disc sampling) treat fault proximity isotropically. STEP-RELAY explicitly evaluates relay geometry (overlapping fault segments, stepover width/length ratio) and directs anisotropic dot placement along kinematically favored transfer corridors.
- **Expected DTI Improvement**: High (+0.025 to +0.045 over baseline).
- **Implementation Cost**: Low–Medium (uses existing LiDAR DEM and catalogue geometry).
- **Rank**: 1

---

### Candidate Hypothesis 2: Blind Basement Fault Horizon via Geothermal Potential-Field Derivative Concordance (MAG-GRAV-BLIND)
- **Specific Layers Involved**: GeoDAWN airborne magnetics (reduced-to-pole [RTP], first vertical derivative [1VD], tilt derivative [TDR]), USGS/INGENIOUS isostatic residual Bouguer gravity horizontal gradient magnitude (HGM).
- **Physical Signature Targeted**: Lateral density and magnetic susceptibility contrast boundaries representing deep-seated basement fault steps that do not reach the surface or are buried under hundreds of meters of Quaternary pluvial Lake Lahontan lacustrine silt.
- **Missing Fault Rationale**: Surface mapping (geologic maps, LiDAR scarps) is fundamentally blind to pre-Lahontan basement faults buried beneath alluvium. However, these deep basement faults are primary geothermal fluid conduits (upwelling thermal plumes).
- **Differences from Existing Implementations**: Uses multi-scale potential field edge detection (Blakely local maxima + tilt angles) rather than superficial topographic scarp filters alone.
- **Expected DTI Improvement**: High (+0.030 to +0.055 over baseline).
- **Implementation Cost**: Medium (requires potential field gradient computation from GeoDAWN magnetic & gravity rasters).
- **Rank**: 2

---

### Candidate Hypothesis 3: Multi-Scale Topographic Scarp Coherence & Shoreline Discrimination (TOPO-SCARP-COH)
- **Specific Layers Involved**: USGS 3DEP LiDAR 10 m and 1 m DEMs, directional shaded relief, multi-scale topographic position index (TPI at 30 m, 100 m, 300 m).
- **Physical Signature Targeted**: Multi-scale linear break-in-slope persistence that distinguishes true tectonic fault scarps from non-tectonic mimics (specifically pluvial Lake Lahontan highstand shoreline benches/terraces, agricultural canals, and mining benches).
- **Missing Fault Rationale**: Standard single-scale edge detection catches pluvial shoreline terraces because their topographic step profile resembles a 2–10 m fault scarp. Evaluating scarp aspect relative to terrain contour direction allows suppressing contour-parallel lacustrine risers while preserving cross-contour tectonic scarps.
- **Differences from Existing Implementations**: Explicitly integrates shoreline-terrace suppression filters and cross-scale persistence metrics.
- **Expected DTI Improvement**: Medium (+0.020 to +0.040).
- **Implementation Cost**: Low–Medium.
- **Rank**: 3

---

### Candidate Hypothesis 4: Hydrothermal Alteration & Radiometric Potassium-Depletion Lineaments (RAD-HYDRO-LINE)
- **Specific Layers Involved**: GeoDAWN airborne radiometric spectrometry (Potassium $K$, Thorium $Th$, Uranium $U$ ternary ratios, $K/Th$ ratio), ASTER/Sentinel-2 shortwave infrared (SWIR) alteration mineral indices.
- **Physical Signature Targeted**: Preferential leaching or potassium metasomatism and clay/silica alteration halos along permeable fault-controlled geothermal fluid upflow pathways.
- **Missing Fault Rationale**: Even where structural scarps are eroded or covered by thin colluvium, hydrothermal fluid circulation along active/fossil geothermal fault pathways produces identifiable surface geochemical and radiometric alteration anomalies.
- **Differences from Existing Implementations**: Utilizes geochemical/radiometric signatures rather than purely structural or geomorphological features.
- **Expected DTI Improvement**: Medium (+0.015 to +0.030).
- **Implementation Cost**: Medium (radiometric ratioing and halo segmentation).
- **Rank**: 4

---

### Candidate Hypothesis 5: Choquet Fuzzy Integral / Submodular Joint Evidence Fusion (CHOQUET-FUSE)
- **Specific Layers Involved**: Multi-layer stack including LiDAR scarp curvature, potential-field tilt derivatives, radiometric anomalies, and catalogue continuation priors.
- **Physical Signature Targeted**: Non-linear, super-additive evidence aggregation where coincident anomalies across orthogonal physical domains (e.g., potential field + topographic scarp) receive super-additive weight, while single-source artifacts are suppressed.
- **Missing Fault Rationale**: Single-source false positives (e.g., roads in LiDAR, unmineralized volcanic dikes in magnetics) rarely coincide across orthogonal physical domains; genuine geothermal fault conduits exhibit coincident potential field, topographic, and thermal/alteration signatures.
- **Differences from Existing Implementations**: Replaces simple linear logistic regression / additive weighting with a Choquet fuzzy integral combined with submodular greedy dot placement.
- **Expected DTI Improvement**: High (+0.035 to +0.060).
- **Implementation Cost**: Medium–High.
- **Rank**: 5

---

## Validation Strategy
All candidate hypotheses must be evaluated against the frozen spatially-blocked hide-and-recover evaluator (`gems57-pooled-hide-v2`) with seeds 20 and 30 across 4 spatial folds, ensuring:
1. Candidate HOLDOUT-DTI strictly beats the control baseline on both seeds.
2. Single-feature leakage canary AUC remains $\le 0.90$.
3. Format validation passes with 0 NaNs and range in $[0, 1]$.
4. Novelty and uniqueness gates are satisfied prior to touching any weekly submission slot.
