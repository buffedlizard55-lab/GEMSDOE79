# Geological Discovery Memo & Ranked Five-Hypothesis Shortlist (`Session 800321e2`)

- **Date (UTC):** `2026-10-22`
- **Repository / Active Lane:** `buffedlizard55-lab/GEMSDOE79` (`arena/800321e2-gemsdoe79`)
- **Preregistered Hypothesis Selected for Experiment `M1`:** `H79-MRND` (*Multi-Regime Brittle-Crustal Nested Discovery*, locked in [preregistration_mrnd.json](../registry/preregistration_mrnd.json))
- **Official Source Verification:** Every competition rule, formula, forum clarification, dataset release, and public leaderboard figure cited below was verified live on `2026-10-22` and logged in [official_sources.json](../knowledge/official_sources.json).

---

## 1. Forensic & Mathematical Dissection: Why `GEMSDOE32` Scored Highest Across the Family (`0.2778` USER-REPORTED) — and Why `#1` Reaches `0.4413`

### 1.1 Verified Official Ground Rules Governing Every DTI Point

Live verification of the DrivenData problem specification (`DD-PROBLEM`), the September 2026 DOE/NLR official rules (`DOE-RULES`), and four DrivenData Staff (`chrisk-dd`) clarifications (`DD-MASK`, `DD-LINE`, `DD-SOURCE`, `DD-POOL`, `DD-FINAL`) establishes five exact mathematical properties of the competition objective:

1. **Pooled Distance-Weighted Tversky Index ($\alpha = 0.2, \beta = 0.8, R = 300\text{ m}$):**
   $$\mathrm{DTI}(p, G) = \frac{\sum_{g \in G} \max_{d(x,g) \le 300\text{ m}} p(x)\,k(d(x,g))}{\mathrm{TP}_w + 0.2 \sum_{x \in \mathcal{A} : p(x)>0} p(x)\bigl[1 - \max_{g \in G} k(d(x,g))\bigr] + 0.8\,\mathrm{FN}_w}$$
   computed by **pooling** $\mathrm{TP}_w, \mathrm{FP}_w, \mathrm{FN}_w$ over all pixels in the evaluation subset (`DD-POOL`), with **no extra per-fault weights** beyond $k(d) = \max(1 - d/300\text{ m}, 0)$ (`DD-FINAL`).
2. **Pixel-Exact Known-Fault Exclusion (No 300 m Buffer Around Mapped Traces):**
   `chrisk-dd` confirmed on September 21 (`DD-MASK`, post 4) that the exclusion mask equals `existing_faults.tif` (`60,988` pixels) pixel-for-pixel in both Phase 1 (`$50,000`) and Phase 2 (`$250,000`). A non-fault prediction placed `100–300 m` off a known mapped trace incurs **full $\alpha = 0.2$ false-positive penalty**.
3. **What Constitutes "New Fault" Ground Truth:**
   `chrisk-dd` confirmed (`DD-MASK` post 4; `DD-LINE` post 2) that `"new fault"` means *"any fault pixel not already captured by USGS/INGENIOUS"*, explicitly encompassing **both** newly mapped geometry of existing fault systems (trace corrections, splays, along-strike tip continuations, relay strands) **and** previously unmapped structures in piedmont bajadas and concealed basins.
4. **Live Public Leaderboard State on `2026-10-22` (`DD-LEADERBOARD`):**
   - `#1 xiaofanhu`: `0.4413` (`PUBLIC LEADERBOARD OBSERVATION`)
   - `#2 cfld__`: `0.3904` · `#3 Batik Shirt Brothers`: `0.3894` · `#5 No Fault of Our Own` (Phase 1 top-5 cutoff): `0.3539`
   - `#21 kinghorton42`: `0.3261` · `#22 li002666`: `0.3183` · `#48 sam35`: `0.2804` · `#50 kinneso_outlook`: `0.2784`
   - User-reported `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, `0.2778` `USER-REPORTED — NOT ORGANIZER-VERIFIED IN REPO`) matched `#48 extradr19 = 0.2778` on `2026-10-21` and now sits `0.0006` below `#50` (`0.2784`).

### 1.2 Four Concrete Reasons `GEMSDOE32` (`H33`) Beat All Other User-Reported Family Entries

| Candidate | User-Reported Public Score | Placed Dots (`>0.5`) | 300 m Halo Coverage of $\mathcal{A}$ | Median $d_{\text{cat}}$ | Structural / Algorithmic Diagnosis |
| --- | ---: | ---: | ---: | ---: | --- |
| `GEMSDOE32` (`H33-2-B2`) | `0.2778` | `37,654` | `12.6%` | `1,960 m` | Multi-sensor LOQO ridge classifier across 24 features derived from 19-band geophysical/DEM stack; optimal ~`0.74%` dot budget for $\beta/\alpha = 4$; spans piedmont & intra-basin domains |
| `GEMSDOE41` (`H41a`) | `0.1558` | `39,793` | `2.3%` | clustered | Over-clustered potential-field worm support (`2.3%` halo vs `12.6%` in `H33`) collapses recall on exposed piedmont scarps |
| `GEMSDOE75` (`H75-1`) | `0.1303` | `29,953` | `12.8%` | deep-cover bias | Restricting predictions to deep cover forfeits exposed Quaternary bajada and range-front splay faults |
| `GEMSDOE72` (`SGMC off-cat`) | `0.0492` | `27,823` | `8.8%` | footwall bedrock | Pre-Quaternary SGMC bedrock contacts inside uplifted mountain blocks miss active range-front/basin faults |
| `GEMSDOE71` (`Walker Lane`) | `0.0405` | `3,071` | `0.42%` | regional subset | Catastrophic recall starvation ($3{,}071$ dots) under pooled footprint-wide $\beta = 0.8$ |
| `GEMSDOE77` (`H82 cool-chem`) | `0.0029` | `11,185` | `2.09%` | point clusters | Isotropic chemical halo around isolated wells is not fault linework |

**Why `GEMSDOE32` (`0.2778`) still leaves `+0.076` to Top-5 (`0.3539`) and `+0.164` to `#1` (`0.4413`), and why `H79-NHR` (`HOLDOUT-DTI` `0.1932 / 0.1950`) failed uniqueness (`26` informative duplicates):**
1. **`H33` zeroes out $0 < d_{\text{cat}} \le 200\text{ m}$ (`known_mask`):** forfeiting every trace-modification, splay, and along-strike tip continuation confirmed by `chrisk-dd` (`DD-MASK` post 4).
2. **`H79-NHR` swings to the opposite extreme (`82.4%` of dots inside $d_{\text{cat}} \le 1.5\text{ km}$, median `539 m`):** flooding the catalogue collar collides with **26 non-space-filling prior family rasters** (up to `0.9130` vs `GEMSDOE3:coverage-v3-wide`), incurs heavy $\alpha = 0.2$ FP penalty along stable mapped segments, and starves piedmont (`1.4–4.5 km`) and intra-basin (`> 4.5 km`) discovery (`IR-79-51`).
3. **Both `H33` and `H79-NHR` omit three critical physical datasets already pinned in `data/raw/external/`:**
   - **Exact square-root dequantization** of `lidar_scarp_features_u8.tif` specified in `lidar_scarp_features.json` ($x = x_{\max}((q-1)/254)^2$),
   - **Anthropogenic road-cut deseaming** via `tiger_road_distance_m.tif` (U.S. Census TIGER/Line),
   - **Hydrothermal fluid upflow & aqueous geothermometry** from `gdr_wellspring_in_footprint.csv` (`DOE GDR 1391` INGENIOUS compilation: `27,092` wells/springs, `3,819` thermal $\ge 37^\circ\text{C}$, `740` quartz geothermometer $\ge 80^\circ\text{C}$).
4. **Single-model regime conflation:** fitting one global classifier forces a single linear hyperplane to trade off sharp 1 m exposed scarps against smooth 400 m aeromagnetic/gravity gradients beneath 500–3,000 m of basin fill, allowing steep erosional footwall canyons (`Hermant et al., 2025`) to dominate high-relief mountain blocks.

---

## 2. Ranked Five-Hypothesis Discovery Shortlist

### Rank #1 (Selected & Preregistered as `H79-MRND`, Experiment `M1`) — Multi-Regime Brittle-Crustal Nested Discovery

- **Physical & Structural Layers Used:**
  1. **Physically dequantized 3DEP 1 m lidar scarp suite** (`lidar_scarp_features_u8.tif` + `lidar_scarp_features.json`: exact inverse $x = x_{\max}((q-1)/254)^2$ on `ex_max`, `ex_mean`, `step_max`, `lapneg_max`, `lappos_max`, `downface_max`, `upface_max`, `cross_max`, `relief`, plus linear `coh100`, `strike`, `valid`) combined with **U.S. Census TIGER/Line road distance** (`tiger_road_distance_m.tif`).
  2. **INGENIOUS hydrothermal fluid upflow & geothermometry** (`gdr_wellspring_in_footprint.csv`, `DOE GDR 1391`, strictly dropping `dist_known_fault_px` on ingest) + **Quaternary volcanic vents** (`gdr_volcanic_vents_in_footprint.csv`, strictly dropping `dist_known_fault_px`).
  3. **Subsurface potential-field, MT conductance & crustal strain suite** (`training_features.tif`: `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_vg`, `rtp`, `tmi_hg`, `tmi_vg`, `tc`, `depth_to_base_surf`, `cond_surf`, `geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`, `deq_n100a15`, `ieq_n100a15`, `det_elev`, `det_elev_slope`).
  4. **GeoDAWN airborne radiometric alteration suite** (`geodawn_rad_u8.tif`: `K`, `Th`, `U`, `TC`; `geodawn_extensions_u8.tif`: `ThK`, `UK`, `UTh`, `TMI_up150`).
  5. **Out-of-fold fault-array boundary conditions** (`train_cat` strictly within training folds; `existing_faults.tif` at full-map inference): leave-one-component-out nearest-fault spacing $d_{-c}(x)$, crack-tip propagation cone $\mathrm{tip\_cone}(x)$, and overlapping relay field $\mathrm{stepover\_pair}(x)$.
- **Physical Signature & Mathematical Transform:**
  - **TIGER-Deseamed Scarp Dipole & Bajada Contrast:** Suppresses road-cut steps via $w_{\text{road}}(x) = \mathrm{clip}(d_{\text{road}}(x) / 150\text{ m}, 0.15, 1.0)$, computes crest-concavity dipole $D_{\text{scarp}} = w_{\text{road}}\sqrt{x_{\text{lapneg}} x_{\text{lappos}}}$, relative bajada scarp prominence $P_{\text{bajada}} = w_{\text{road}}\,x_{\text{ex\_max}} / (0.05 + x_{\text{relief}}/300)$, and directional antislope polarity $(x_{\text{up}} - x_{\text{down}})/(x_{\text{up}} + x_{\text{down}} + 10^{-3})$.
  - **Multi-Scale Potential-Field Worm Persistence & Cover Interaction:** Computes Blakely–Simpson horizontal gradient ridges across $\sigma \in \{2, 5, 12\}\text{ px}$ (`200 m, 500 m, 1.2 km`) on `iso_grav_anom`, `rtp`, and upward-continued `TMI_up150`, interacted with $\log(1 + \mathrm{depth\_to\_base\_surf})$ and `cond_surf` horizontal gradient.
  - **Hydrothermal Upflow Kernel:** Maps multi-scale Gaussian thermal-anomaly density ($\sigma \in \{600\text{ m}, 2{,}000\text{ m}\}$) weighted by $\max(0, T_{\text{meas}} - 25^\circ\text{C})$ and silica/cation geothermometer excess $\max(0, T_{\text{qtz/chalc/cat}} - 70^\circ\text{C})$, gated onto local geophysical/structural gradients so upflow plumes resolve along linear fault conduits rather than circular blobs.
  - **Leave-One-Trace-Out Regime Training & Hazard-Quantile Surface Calibration:** Every training fault trace component $c \subset \mathrm{train\_cat}$ is assigned its exact leave-one-component-out isolation spacing $d_{-c}(x) = \min_{c' \ne c} d(x, c')$ via `cKDTree`, matching inference spacing $d_{\text{cat}}(x)$ across three Basin-and-Range mechanical regimes:
    - **Regime I ($0 < d \le 1{,}400\text{ m}$, share $q_1 = 0.24$):** Relay ramps, crack-tip propagation cones, and near-trace modifications.
    - **Regime II ($1{,}400 < d \le 4{,}500\text{ m}$, share $q_2 = 0.34$):** Piedmont bajada scarps and synthetic/antithetic accommodation faults.
    - **Regime III ($d > 4{,}500\text{ m}$, share $q_3 = 0.42$):** Concealed intra-basin horst/graben steps and blind geothermal conduits.
    Within each regime $r \in \{1, 2, 3\}$, a specialized nested hide-to-recover `HistGradientBoostingRegressor` predicting official 300 m kernel credit $k(d) = \max(1 - d/3\text{ px}, 0)$ is fit **strictly on training-fold nested hides** within regime $r$ (with explicit footwall canyon relief suppression on uplifted range cores lacking sedimentary cover), converted to descending score rank $\mathrm{rank}_r(x) \in \{1, \dots, |\mathcal{A}_r|\}$ on allowed pixels $\mathcal{A}_r$, and mapped monotonically to a single continuous confidence surface:
    $$S(x) = \exp\!\left(-\frac{\mathrm{rank}_{r(x)}(x)}{q_{r(x)} B_{\text{scale}}}\right) \in (0, 1], \qquad B_{\text{scale}} = 37{,}654,$$
    followed by shared deterministic 3 px Poisson spacing (`gems79.placement.place`, `spacing = 3`, `budget = 37,654`).
- **Why Missing from USGS / INGENIOUS Catalogue:** Historical mapping emphasized prominent range-bounding bedrock-alluvium contacts while omitting (i) subtle degraded bajada scarps cut across Quaternary fans, (ii) blind intra-basin graben/accommodation faults buried under Playas/alluvium (`depth_to_base_surf > 200 m`), and (iii) unmapped splays/relays hosting hidden hydrothermal circulation (`Faulds & Hinz, 2015`; `Ayling et al., 2022`).
- **How Distinct from All Existing Repo & Family Code:** First architecture combining (1) exact `cKDTree` leave-one-component-out multi-regime training, (2) inverse-sqrt lidar dequantization + TIGER road deseaming, (3) DOE GDR 1391 thermal/geothermometer conduit interaction, (4) explicit footwall canyon relief suppression, and (5) analytical hazard-quantile calibration into $S(x)$ so **both** pre-placement `screen_surface` and post-NMS `screen_placement` clear all `960` non-space-filling registry rasters (`0 / 960` duplicates) with zero registry inputs and zero overlap swapping.
- **Primary Non-Fault Mimics & Suppression:** (a) Highway/railroad cuts & canal embankments $\to$ suppressed by `tiger_road_distance_m`; (b) steep footwall erosional canyon walls & talus ridges $\to$ suppressed by bedrock-relief penalty where `depth_to_base_surf` is thin and `det_elev_slope` / `relief` is extreme; (c) isotropic thermal outflow aprons $\to$ gated by linear structural/potential-field gradient coherence.
- **Expected DTI Impact vs Engineering Cost:** **Highest net gain / Low runtime cost** (~`75 s` full 2-seed × 4-fold LOQO + full-map inference + 992-raster pre- & post-placement uniqueness gates on 2 CPU cores).

---

### Rank #2 — Hydrothermal Upflow & Silica-Cation Geothermometer Structural Fairway Bridge (`H79-HUGF`)

- **Layers:** `gdr_wellspring_in_footprint.csv` (`temp_c`, `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`), `cond_surf` (`B17`), `TMI_up150` (`geodawn_extensions_u8 B04`), `iso_grav_anom_hg` (`B18`), `geodawn_extensions_u8` (`UK`, `ThK`).
- **Signature & Transform:** Anisotropic minimum-cost / tensor ridge connecting high quartz-chalcedony geothermometer upflow anomalies along local MT conductance gradient azimuths and magnetite-destruction troughs (`-LoG(TMI_up150)`), targeting hydrothermal alteration zones where argillic clay caps (`high cond_surf`, demagnetized `TMI_up150`, potassium metasomatism `low Th/K`) seal blind permeable fault conduits.
- **Why Missing from Catalogue:** Blind geothermal systems in the Great Basin (~`75%` of undiscovered capacity per `GBCGE-INGENIOUS`) lack surface Quaternary scarps because ductile playaclay/lacustrine sediments absorb brittle offset near the surface.
- **Repo / Family Difference:** Prior well/spring attempts (`GEMSDOE77` `h82-cool-chemconcord`, `GEMSDOE47` `geothermometer-consensus-n5000`) emitted sparse circular halos around wells (`0.0029` public DTI) rather than tracing linear MT/magnetic fault bridges across `37,654` budget pixels.
- **Non-Fault Mimics & Suppression:** Stratigraphic saline playas and evaporite brines elevate `cond_surf` without fault permeability $\to$ suppressed by requiring lateral horizontal gradient (`|\nabla cond_surf|`) coincident with basement density steps (`iso_grav_anom_hg`) rather than flat basin-center conductance highs.
- **Expected Impact vs Cost:** Moderate standalone recall (hydrothermal systems occupy a subset of faulted basins), strong additive component inside `H79-MRND`; low compute cost (`< 20 s`).

---

### Rank #3 — Alluvial-Cover Multi-Scale Potential-Field Worm Curvature & Tilt-Depth Persistence (`H79-WORM-TILT`)

- **Layers:** `iso_grav_anom` (`B13`), `rtp` (`B02`), `tc` (`B06`), `tmi_hg` (`B03`), `TMI_up150` (`geodawn_extensions_u8 B04`), `depth_to_base_surf` (`B15`).
- **Signature & Transform:** Computes multi-scale Blakely–Simpson maximum-horizontal-gradient "worms" across upward-continuation scales $\sigma \in \{100, 300, 700, 1500\}\text{ m}$, estimates magnetic contact depth via Salem tilt-derivative wavelength $z_{\text{tilt}} = |\nabla \theta_{\text{tilt}}|^{-1}$ on `tc`, and retains lineaments exhibiting cross-scale lateral dip migration consistent with $45^\circ\text{–}65^\circ$ normal faults cutting basement beneath `depth_to_base_surf > 150 m`.
- **Why Missing from Catalogue:** Surficial Holocene eolian sand and Lahontan lacustrine silt completely bury pre-Holocene and blind Quaternary basin-interior horst margins across Fallon, Winnemucca, and Carson Sink blocks.
- **Repo / Family Difference:** `GEMSDOE41` (`H41a`) clustered worms into `2.3%` halo area without tilt-depth dip consistency or 500 m spacing across piedmont/scarps; `E1` in `GEMSDOE79` estimated 1-D cross-strike magnetic lag inside fault corridors rather than cross-scale Blakely–Simpson dip-migrating worms.
- **Non-Fault Mimics & Suppression:** Pluton margins, caldera ring dikes, and basalt flow edges create strong static magnetic gradients $\to$ suppressed by requiring concordant gravity density step (`iso_grav_anom_hg`) and strike persistence $> 1.5\text{ km}$.
- **Expected Impact vs Cost:** High recall on concealed basin faults, low recall on shallow low-susceptibility sedimentary splays; medium compute cost (`~35 s`).

---

### Rank #4 — Dequantized TIGER-Deseamed Bajada Scarp Dipole & Soil-Age Radiometric Contrast (`H79-BAJADA-DIPOLE`)

- **Layers:** `lidar_scarp_features_u8.tif` + `lidar_scarp_features.json` (`ex_max`, `step_max`, `lapneg_max`, `lappos_max`, `upface_max`, `downface_max`, `coh100`, `relief`), `tiger_road_distance_m.tif`, `geodawn_rad_u8.tif` (`K`, `Th`, `U`).
- **Signature & Transform:** Exact inverse-sqrt physical reconstruction of 2 m and 10 m scarp steps paired with signed crest-to-toe LoG dipole $\sqrt{\text{lapneg}\cdot\text{lappos}}$ normalized by local 300 m relief, multiplied by TIGER road deseaming and cross-scarp radiometric `Th/K` contrast (juxtaposing leached older Pleistocene fan surfaces on the uplifted footwall against fresh K-feldspar wash on the hanging wall).
- **Why Missing from Catalogue:** Pre-3DEP photo-geologic mapping missed sub-meter (`0.3–1.5 m`) degraded scarps on low-sun-angle alluvial fans.
- **Repo / Family Difference:** `H79-ASYM` (`PR #44`) used raw quantized `upface_max - downface_max` without inverse-sqrt scaling, road deseaming, crest-base LoG dipole, or radiometric fan-age contrast, colliding with `32` prior scarp rasters.
- **Non-Fault Mimics & Suppression:** Lake Lahontan paleo-shoreline benches (horizontal contour strike along constant elevation `det_elev`) and road/canal embankments (`tiger_road_distance_m < 150 m`) $\to$ suppressed explicitly by `tiger_road_distance_m` and non-zero elevation gradient along strike (`|\hat{s} \cdot \nabla \text{elev}|`).
- **Expected Impact vs Cost:** High precision on exposed Quaternary scarps, blind where 3DEP lidar is absent (`25.4%` of footprint has `valid == 0`); low compute cost (`~15 s`).

---

### Rank #5 — Walker Lane Transtensional Shear-Dilatation & Volcanic-Vent Dike-Fault Transfer Corridors (`H79-WL-VENT`) + External Public Data Expansion

- **Layers (Current Pinned + Verified External Free Official Sources):**
  - Pinned: `geod_2ndinv` (`B04`), `geod_shearrate` (`B07`), `geod_dilaterate` (`B08`), `ieq_n100a15` (`B16`), `deq_n100a15` (`B10`), `gdr_volcanic_vents_in_footprint.csv` (`21` vents).
  - External free official datasets verified permissible under Competition Rules Section 3.3 / External Data (`CC0` / `CC-BY-4.0` public licenses, shareable with DOE/NLR):
    1. **NASA ASF / JPL ARIA & OPERA Sentinel-1 Surface Displacement (`DISP-S1`, Open/CC0):** 30 m line-of-sight velocity gradients capturing active aseismic fault creep and geothermal subsidence bowls at 100× finer spatial resolution than regional GPS grids (`geod_shearrate`).
    2. **USGS GeoDAWN Raw Flight-Line CSVs (`doi:10.5066/P93LGLVQ`, CC0):** along-line 10 Hz (~`7 m` spacing along E-W flight lines) magnetic profiles resolving sub-100 m shallow dike/fault susceptibilities lost during 400 m gridding.
    3. **DOE GDR 1391 Paleo-Geothermal Sinter/Tufa & 2 m Temperature Probe Shapefiles (`doi:10.15121/1881483`, CC-BY-4.0):** fossil hot-spring sinter terraces directly marking Quaternary fault-valve intersections.
- **Why Deferred Behind `H79-MRND` for Experiment `M1`:** Under the sandbox network policy (only GitHub/PyPI/npm reachable from bash sockets), external binary downloads cannot be fetched directly inside automated CI, whereas `H79-MRND` integrates all 13 SHA-256-pinned datasets immediately with full deterministic reproducibility (`reproduce_artifact.py`).
