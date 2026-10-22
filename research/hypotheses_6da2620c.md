# Pre-Implementation Ranked Geological Hypotheses (`arena/6da2620c-gemsdoe79`, `2026-10-22`)

> **Protocol & Ordering Receipt:** Authored and committed prior to restoring bulk feature stacks or running any holdout/canary computation on branch `arena/6da2620c-gemsdoe79`. All `20` prior `GEMSDOE79` lanes (`G79-THVC`, `H79-NHR`, `H79-FNHR`, `H79-BQA`, `H79-MRND`, `H79-STEP`, `H79-FF1`, `G79-BER`, `H79-DILSTEP`, `H79-COV`, `H79-FF`, `H79-ML-STRAIN-RELAY`, `G79-STEPCO`, `H79-FFAS`, `G79B-SDPT`, `H79-FGR`, `G79-MAG`, `E1 G79-FABRIC-OFFSET`, `H79-ASYM`/`H79-MCT`/`H79-CSPT`/`G79B-GEOAND`) and sibling lanes (`GEMSDOE32` `H33`, `GEMSDOE80` `H80G`, `GEMSDOE83` `H83-GVCD`) were audited before drafting these five untried hypotheses.

---

## Executive Diagnosis of What All 20 Prior `GEMSDOE79` Lanes Missed

1. **Absolute Elevation $Z(x)$ Was Missing From Every Feature Matrix (`det_elev` Only):**
   `training_features.tif` provides only *detrended* elevation (`det_elev`, band 12) and *detrended* slope (`det_elev_slope`, band 19). Consequently, despite every `GEMSDOE79` Run Card naming **Pleistocene pluvial Lake Lahontan (`~1,330–1,340 m` ASL Sehoo highstand) and recessional wave-cut shoreline benches (`1,190–1,350 m` ASL)** as the #1 non-fault physical mimic of Quaternary scarps, **zero prior lanes ever loaded absolute elevation $Z(x)$** (`geodawn_dem_a2_100m.tif` = USGS GeoDAWN `22103_dem_a2.tif`, `doi:10.5066/P93LGLVQ`, `100%` footprint coverage including the `24.99%` Nevada 1-m LiDAR gap) to test whether a scarp is a horizontal lacustrine equipotential contour ($\hat{t}_{\text{scarp}} \cdot \nabla Z \approx 0$) vs. a contour-transgressive bajada fault scarp ($|\hat{t}_{\text{scarp}} \cdot \nabla Z| > 0$).
2. **Anthropogenic Open-Pit Mining Benches & Potassic Tailings Were Unmodeled:**
   Western and central Nevada host hundreds of open-pit gold/epithermal mines, waste-rock dumps, heap-leach pads, and exploration trenches whose `10–30 m` haul-road benches mimic fault scarps on LiDAR/3DEP and whose exposed argillic/potassic pits mimic radiometric `K/Th` alteration. Official US Bureau of Land Management mining-claim geometry (`blm_closed_claim_distance_m.tif`, derived from `https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2`) was never ingested in `GEMSDOE79`.
3. **Training-Shard Flank Contamination (`IR-79-140`) + `2.0 < d <= 3.0 px` Dead-Zone Collar Emission:**
   In `gems57-pooled-hide-v2` (`holdout.buffered_component_draw`, `buffer_px = 3`), `visible = cat & ~(EDT(~hidden) <= 3.0)`, so `EDT(~visible)[hidden].min() = 3.1623 px > 3.0 px`. Yet `G79-THVC`:
   - Sampled tens of thousands of `1.0 <= d(x, sim_vis) <= 3.0 px` unhidden fault-scarp flank pixels as `y = 0` negatives in Stage 1 and Stage 2, simultaneously attenuating physical scarp weights and creating an artificial `y = 0` cliff at `d_vis <= 3.0 px`; and
   - Emitted dots down to `d_cat > 2.0 px`, wasting dot budget in the `2.0 < d <= 3.0 px` dead collar where `gems57-pooled-hide-v2` contains **zero** withheld positives and where live submissions sit inside the `300 m` mapping halo of already-mapped faults.
4. **Catalogue-Perimeter Collapse (`97.58%` of `G79-THVC` Dots `< 2 km` From Catalogue -> `0.7139 > 0.70` Collision With `GEMSDOE83`):**
   `G79-THVC` placed `52.8%` of Stage-1 tree gain on isotropic distance to `visible` (`net_exp_d18`, `net_log_d_vis`, `net_exp_d6`, `net_exp_d45`), lacked an elastic **Coulomb stress-drop shadow ($\Delta\text{CFS} < 0$)** on broadside fault flanks, and discarded its zero-catalogue pure-physics posterior (`p_zero_2d`) before Charnes-Cooper allocation.

---

## Five Untried Candidate Geological Hypotheses

### Hypothesis 1 (`H81-LAHMINE`): Pluvial Shoreline Equipotential Isohypse Veto & BLM Open-Pit Deconfounded Scarp-Transgression Mechanics
- **Specific Layers & Transform:**
  - Official USGS GeoDAWN 100-m Airborne Radar/GPS Digital Elevation Model `geodawn_dem_a2_100m.tif` (`22103_dem_a2.tif`, `doi:10.5066/P93LGLVQ`, `100%` footprint coverage), 1-m LiDAR scarp stack (`lidar_scarp_features_u8.tif`), 10-m USGS 3DEP stack (`topo_10m_derived_100m_u8.tif`), US BLM Mining Claims distance (`blm_closed_claim_distance_m.tif`), and US Census TIGER roads (`tiger_road_distance_m.tif`).
  - Computes dominant local scarp strike unit tangent $\hat{t}_{\text{scarp}}(x)$ across 8 azimuths, evaluates the **along-scarp absolute-elevation climb rate** $C_{\parallel}(x) = |\hat{t}_{\text{scarp}}(x) \cdot \nabla Z_{300\text{m}}(x)|$ and **isohypse contour parallelism** $I_{\text{iso}}(x) = 1 - \frac{|\hat{t}_{\text{scarp}}(x) \cdot \nabla Z|}{\|\nabla Z\| + \epsilon}$ gated by the Pleistocene Lake Lahontan shoreline elevation envelope $\exp\!\left(-\frac{(Z - 1332\text{ m})^2}{2\,(48\text{ m})^2}\right) + 0.7\exp\!\left(-\frac{(Z - 1245\text{ m})^2}{2\,(45\text{ m})^2}\right)$ (Adams & Wesnousky 1998; Reheis et al. 2014), plus anthropogenic open-pit/haul-road attenuation $\exp(-d_{\text{BLM}} / 350\text{ m})$ and $\exp(-d_{\text{road}} / 150\text{ m})$.
- **Why It Catches Unmapped Faults Rather Than Mapped Ones:**
  Subtle Holocene–late Pleistocene piedmont fault scarps (`0.5–3 m` throw) cutting obliquely across coalescing alluvial bajada fans in Carson Sink, Dixie Valley, Winnemucca Lake, and Walker Basin were systematically omitted by photo-interpreters who could not separate them from dense flights of Lake Lahontan wave-cut shorelines at `1,200–1,340 m` ASL. Because lacustrine shorelines are gravitational equipotentials ($\hat{t} \cdot \nabla Z = 0$) whereas piedmont normal faults climb `20–150 m` across fan apexes ($|\hat{t} \cdot \nabla Z| > 0$), $C_{\parallel}$ recovers genuine bajada-cutting scarps while suppressing thousands of shoreline and open-pit false positives (`FP_w`).
- **How It Differs From All Prior Implementations in `GEMSDOE79`:**
  No prior lane in `GEMSDOE79` ever loaded absolute elevation $Z(x)$ (`geodawn_dem_a2_100m.tif`) or BLM mining-claim distance (`blm_closed_claim_distance_m.tif`), and no prior lane computed the inner product between scarp strike $\hat{t}_{\text{scarp}}$ and $\nabla Z$.
- **Named Non-Fault Mimic:**
  Incised alluvial-fan channel margins / debris-flow levees that climb radially upslope (mitigated by cross-strike one-sided terrace step asymmetry vs symmetric channel banks and subsurface gravity/magnetic step co-support).
- **Obtainable Official Free External Sources:**
  USGS GeoDAWN `doi:10.5066/P93LGLVQ` (`geodawn_dem_a2_100m.tif`, SHA-256 `b574...` verified on fetch from `60GEMSDOE` @ `b99591eede63c6d45c8a896255b8cd34824fa00b`) and US BLM Nationalrid Mining Claims REST service (`https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2`, `blm_closed_claim_distance_m.tif` verified from `GEMSDOE24` @ `07345ea0604953d7efb858d9cfbc21e20c7aca0b`).

---

### Hypothesis 2 (`H81-COULOMB-SLIP`): Elastic Coulomb Stress-Shadow ($\Delta\text{CFS} < 0$), Conjugate Relay Lobe & Along-Range Footwall Slip-Deficit Mechanics
- **Specific Layers & Transform:**
  - Fold-visible fault network (`visible_mask`), `geodawn_dem_a2_100m.tif` ($Z$), `iso_grav_anom` (band 6), `depth_to_base_surf` (band 11), `geod_dilaterate` (band 13), and `geod_shearrate` (band 14).
  - Decomposes every connected `visible_mask` strand of length $L \ge 15\text{ px}$ into oriented dislocation elements with unit strike $\hat{t}$ and normal $\hat{n}$; evaluates:
    1. **Broadside Normal-Fault Elastic Stress-Drop Shadow** $S_{\text{CFS}}^-(x)$ ($|\hat{n} \cdot \hat{u}| > 0.72$, $3 < d_{\text{vis}} < 18\text{ px}$, weighted by strand length $\min(L/40, 1.5)$), capturing the classic Crider & Pollard (1998) / Hodgkinson et al. (1996) extensional stress-relief zone perpendicular to major range-front faults;
    2. **Oblique Relay & Dilatational Step-Over Stress Concentration** $S_{\text{CFS}}^+(x)$ at overlapping/underlapping strand tips and $\pm 22^\circ\text{–}38^\circ$ conjugate fault bends; and
    3. **Along-Range Structural Slip-Deficit** $D_{\text{slip}}(x) = \text{Quantile}(\Delta Z_{2\text{km}} \cdot \|\nabla g_{\text{iso}}\|) \cdot \exp(-G_{2.5\text{km}}(\text{visible}) / \tau_0)$, firing where cumulative footwall-to-basin structural relief is large (`> 250 m` + steep Bouguer/isostatic basin-margin gradient) yet mapped fault density within `2.5 km` vanishes.
- **Why It Catches Unmapped Faults Rather Than Mapped Ones:**
  Displacement conservation along Basin-and-Range normal fault systems requires cumulative throw to transfer across seeming "gaps" in surface mapping (where Holocene landslide aprons, talus cones, or young fan lobes bury the range-front trace, or where throw partitions onto an unmapped outboard piedmont fault). Simultaneously, $\Delta\text{CFS} < 0$ prevents the allocator from wasting dots on mechanically unloaded parallel flanks of already-mapped master faults.
- **How It Differs From All Prior Implementations in `GEMSDOE79`:**
  `G79-THVC` computed only *positive* tip cones (`net_tip_fwd_1500m`, `net_tip_fwd_3500m`, `net_tip_wing_28deg`, `net_colinear_gap`, `net_relay_overlap`) and isotropic distance decays (`net_exp_d6/18/45`). It had **zero** broadside stress-shadow inhibition ($S_{\text{CFS}}^-$) and **zero** footwall-relief minus mapped-trace slip-deficit conservation ($D_{\text{slip}}$).
- **Named Non-Fault Mimic:**
  Erosional non-tectonic Miocene volcanic escarpments or granitic pluton contacts with steep gravity gradients and no Quaternary slip (mitigated by requiring geodetic strain-rate / 1m-10m scarp or hydrothermal co-support).
- **Obtainable Official Free External Sources:**
  Uses competition `training_features.tif` + `existing_faults.tif` (fold-visible only) + USGS GeoDAWN `geodawn_dem_a2_100m.tif`.

---

### Hypothesis 3 (`H81-RADIO-KD`): Quadrant-Cross-Fitted Lithology-Normalized Potassic Adularia-Illite Residual $K_d(x)$ & Magnetite-Destruction Conduit Index
- **Specific Layers & Transform:**
  - All 4 verified channels of `geodawn_rad_u8.tif` (`["K", "Th", "U", "TC"]` = `%K`, `ppm eTh`, `ppm eU`, and `TC` Corrected Total Count `nGy/hr`, `doi:10.5066/P93LGLVQ`) + `geodawn_extensions_u8.tif` (`["ThK", "UK", "UTh", "TMI_up150"]`) + upward-continued `rtp` demagnetization trough + `cond_surf` + `blm_closed_claim_distance_m.tif` + `geodawn_dem_a2_100m.tif`.
  - Regresses mobile potassium $K$ against immobile lithologic thorium $\text{Th}$ and total radiometric activity $\text{TC}$ via a smooth quadratic ridge regression $\hat{K}(\text{Th}, \text{TC})$ (cross-fitted so lithologic felsic tuff/granite background cancels out), forming the **potassic hydrothermal metasomatism residual** $K_d(x) = \max(K - \hat{K}(\text{Th}, \text{TC}), 0)$ (Galbraith & Saunders 1983; Dickson & Scott 1997), then attenuates closed alkali-playa sinks (local basin-floor minima of $Z$) and `< 400 m` BLM mine tailings, and couples $K_d(x)$ with magnetite-destructive `rtp` demagnetization troughs and 2-m temperature probe / paleo-sinter anomalies.
- **Why It Catches Unmapped Faults Rather Than Mapped Ones:**
  Blind epithermal and geothermal upflow zones (`150–260 °C`) boil and precipitate adularia + illite/sericite while altering host-rock magnetite to pyrite/hematite along permeable damage zones whose surface scarps are completely beveled or buried beneath thin eolian/alluvial veneer — leaving zero topographic scarp for USGS/NBMG mappers, but a crisp `K_d + demagnetization + 2m-probe` ribbon.
- **How It Differs From All Prior Implementations in `GEMSDOE79`:**
  `G79-THVC` used only a raw heuristic ratio `rad_k / (rad_th + 0.08)`, never loaded Band 4 (`TC` Corrected Total Count, whose identity was previously unresolved in `IR-79-13` until verified from official `geodawn_rad.json`), never cross-regressed $K$ on $(\text{Th}, \text{TC})$, and never deconfounded BLM mine tailings or closed-basin playas using absolute $Z$.
- **Named Non-Fault Mimic:**
  Unaltered high-silica potassic ash-flow tuffs, potassic mine waste/tailings piles, and evaporative illite/K-feldspar playa muds (explicitly removed by $(\text{Th}, \text{TC})$ regression, `blm_closed_claim_distance_m.tif`, and basin-floor $Z$ closure).
- **Obtainable Official Free External Sources:**
  USGS GeoDAWN `doi:10.5066/P93LGLVQ` (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`, `geodawn_dem_a2_100m.tif`) + BLM `blm_closed_claim_distance_m.tif` + DOE GDR-1391 (`2m_temperature_probe`, `paleo_geothermal_regional`).

---

### Hypothesis 4 (`H81-DRAPE-NOTCH`): GeoDAWN Survey-Block Flight-Line Fourier Notch & Local-Wavenumber Magnetic Contact Sharpness
- **Specific Layers & Transform:**
  - `rtp` (band 2), `tmi_hg` (band 3), `geodawn_extensions_u8.tif` band 4 (`TMI_up150`), `geodawn_dem_a2_100m.tif`, and official USGS GeoDAWN `acquisition_block_id_100m.tif` (`Area 1` `50 m` grid / `200 m` E–W flight lines vs `Area 2` `100 m` grid / `400 m` E–W flight lines across Winnemucca, Fallon, Hawthorne, and Tonopah blocks).
  - Applies a 2D FFT narrow directional stop-band notch along the N–S wavenumber axis ($|k_y| \in [0.65\,k_{\text{fl}}, \pi/\Delta y]$, $|k_x| < 0.18\,|k_y|$) to strip E–W airborne survey tie/flight-line micro-leveling corrugations without blurring NNE–NNW or ENE Humboldt-zone faults, then computes **Thurston & Smith (1997) local wavenumber** $k_{\text{loc}}(x) = \|\nabla \theta_{\text{tilt}}(x)\|$ (which equals $1 / z_{\text{top}}$ over a vertical magnetic fault contact!) conditioned on `acquisition_block_id_100m.tif` resolution (`Area 1` vs `Area 2`).
- **Why It Catches Unmapped Faults Rather Than Mapped Ones:**
  Sub-alluvial Quaternary faults offsetting buried Tertiary volcanic layers beneath `20–150 m` of basin fill have zero surface scarp, AND E–W / ENE transfer and accommodation faults (e.g., Humboldt structural zone, Walker Lane sinistral domain) were historically under-detected in raw GeoDAWN `tmi_hg` because `400 m` E–W flight-line leveling corrugations contaminated E–W horizontal gradients.
- **How It Differs From All Prior Implementations in `GEMSDOE79`:**
  `G79-THVC` applied isotropic upward continuation (`z = 200, 600, 800 m`) with zero directional flight-line notch, never ingested `acquisition_block_id_100m.tif`, and never calibrated for the `2x` spatial-resolution jump between `Area 1` (`50 m`) and `Area 2` (`100 m`).
- **Named Non-Fault Mimic:**
  Buried paleochannels filled with vesicular Quaternary basalt flows or shallow plutonic dike swarms (mitigated by requiring gravity-step / geodetic dilation or scarp/thermal co-support).
- **Obtainable Official Free External Sources:**
  USGS GeoDAWN `doi:10.5066/P93LGLVQ` (`acquisition_block_id_100m.tif`, SHA-256 `2c0785c4b3ec46c734d1be7a7aedbb3e816201100ab358033a3af074418c894a`, verified from `GEMSDOE24`).

---

### Hypothesis 5 (`H81-MT-PHASE`): 3-D Magnetotelluric Multi-Depth Conductance Ratio ($\nabla \log(\sigma_{\text{mid}} / \sigma_{\text{surf}})$) Across Electrically Screened Conductive Playas
- **Specific Layers & Transform:**
  - `cond_surf` (band 16) and external 3-D MT depth slices (`1–3 km` brittle hydrothermal reservoir vs `0–200 m` hypersaline playa clay cap) from USGS ScienceBase / DOE GDR GREAT BASIN MT models.
  - Targets deep vertical sub-playa feeder faults whose shallow electrical signature is shorted out by `< 2 Ω·m` saline evaporite pans.
- **Why Deferred Relative to Coupled Top Choice:**
  In `training_features.tif`, only `cond_surf` (shallow surface conductance) is gridded at `100 m`, whereas regional 3-D MT inversions have `5–15 km` station spacing (`> 50x` coarser than the competition's `300 m` triangular kernel), limiting standalone localization precision inside the `300 m` DTI halo compared to `100 m` GeoDAWN DEM + LiDAR/3DEP + radiometrics + flight-notched magnetics + elastic Coulomb/slip-deficit mechanics.

---

## Quantitative Pre-Implementation Ranking

| Rank | Hypothesis ID | Physical / Structural Mechanism | Expected `HOLDOUT-DTI` Gain Over `G79-THVC` (`0.1905 / 0.1944`) | Expected Cross-Repo Portfolio Overlap Benefit (vs `GEMSDOE83` `0.7139`) | Implementation & Compute Cost | Selection Decision |
|---:|---|---|---|---|---|---|
| **1 (Selected Coupled Lane `G79-CSKD`)** | **`H81-COULOMB-SLIP` + `H81-LAHMINE` + `H81-RADIO-KD` + `H81-DRAPE-NOTCH` + Decontaminated `d > 3 px` Counterfactual Charnes-Cooper** | Unifies decontaminated `d_vis > 3.0 px` training/placement, Lahontan isohypse + BLM mine deconfounding (`Z`, `d_BLM`), flight-notched `k_loc` magnetics (`acquisition_block_id`), $(\text{Th},\text{TC})$-regressed potassic adularia $K_d$, broadside Coulomb stress shadow ($\Delta\text{CFS} < 0$) + along-range slip deficit, and counterfactual zero-catalogue + full-mechanics OOF fusion into Charnes-Cooper submodular kernel allocation | **`+0.008` to `+0.025` DTI** (eliminates `2 < d <= 3 px` dead-collar waste, removes `4:1` unhidden-flank false negatives, suppresses Lahontan/mine `FP_w`, and recovers intra-basin blind hydrothermal/piedmont strands) | **High — directly reduces `< 2 km` isotropic collar crowding (`97.58%` in `G79-THVC`) to pull 3-px dot overlap with `GEMSDOE83` below `0.70`** | **Low–Moderate** (`~14 min` end-to-end on 2 vCPUs, `< 1.35 GB` RSS; 100% SHA-verified official files) | **IMPLEMENT & VALIDATE (`G79-CSKD`)** |
| 2 | `H81-LAHMINE` (standalone) | Lahontan `1,200–1,345 m` equipotential isohypse veto + BLM open-pit/haul-road deconfounder on 1m LiDAR + 10m 3DEP scarps | `+0.004` to `+0.011` DTI | Moderate | Low (`~4 min`) | Integrated into `G79-CSKD` Group A/C |
| 3 | `H81-COULOMB-SLIP` (standalone) | Broadside normal-fault elastic stress shadow ($\Delta\text{CFS} < 0$) + along-range footwall relief slip-deficit | `+0.004` to `+0.010` DTI | High (suppresses redundant broadside flank dots) | Low (`~5 min`) | Integrated into `G79-CSKD` Group D |
| 4 | `H81-RADIO-KD` (standalone) | Cross-regressed `K` on `(Th, TC)` potassic adularia-illite residual + demagnetization trough | `+0.002` to `+0.006` DTI | Moderate (adds intra-basin epithermal conduits) | Low (`~3 min`) | Integrated into `G79-CSKD` Group B |
| 5 | `H81-MT-PHASE` | Deep-to-shallow 3-D MT conductance gradient across conductive playas | `+0.0005` to `+0.002` DTI (`5–15 km` MT station spacing limits `300 m` localization) | Low | High (external 3-D MT regridding) | Deferred to post-`G79-CSKD` backlog |
