# Ranked Unimplemented Candidate Geological Hypotheses (`session 87f53313`)

**Review date (UTC):** `2026-10-22`
**Evidence & gate constraint (`AGENTS.md`):** Every candidate below is **prospective and unimplemented** on `main` (`095c9f0`, after `G79-CJX` closed negative in `PR #102`). Under the verified 3-tier registry novelty obstruction (`evidence/review_87f53313/three_tier_obstruction_summary.json`; `scripts/preflight_new_lane.py` exit `2`), **no candidate lane may run or spend a competition slot** until a prospective shared-protocol decision resolves how non-informative dense diagnostic blobs (`17GEMSDOE`, `GEMSDOE48`, `5GEMSDOE`) and near-space-filling geometric calibration lattices (`13GEMSDOE` `r13-lattice-s5`) are handled. All historical `HOLDOUT-DTI` figures cited below are measured outputs from `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, $\alpha=0.2, \beta=0.8$, $R=300\text{ m}$); **zero projected DTI numbers are written anywhere in this document**.

**Mandatory input hygiene for any future lane (`IR-79-180..185`):** Every band read from `data/raw/training_features.tif` must be selected or verified against `ds.descriptions` (`evidence/review_87f53313/feature_stack_audit.json`) and masked with `valid = footprint & np.isfinite(band) & (band > -1e30)` (with `3,061` interior float32 `-3.4028235e+38` sentinels in Bands 1–5 and 7–19, and `3,073` in Band 6 `tc`) **before** any spatial derivative, structure tensor, or quantile normalization. Omitting that interior-sentinel mask in `PR #102` (`G79-CJX`, `IR-79-185`) clipped `3,061` interior sentinel cells to `-20.0` IQR cliffs and routed `29.73%` (`11,193 / 37,654`) of the top `cjx_v1_edge` pixels into the `0.5925%` 6-px sentinel halo (`50.2×` enrichment).

---

## Summary Ranking (Expected `HOLDOUT-DTI` Lift vs Implementation & Data Cost)

| Rank | ID | Candidate Hypothesis | Exact Input Layers & Availability | Implementation Cost | Expected `HOLDOUT-DTI` Lift vs Incumbent (`G79-THVC` `0.1905 / 0.1944`) |
|---:|---|---|---|---|---|
| **1** | **`G79-SWARM`** | **Dependent-to-Independent Seismicity Ratio (`deq / ieq`) Steered Along Geodetic Transtensional Corridors** | Cached `training_features.tif` Band 10 (`deq_n100a15`), Band 16 (`ieq_n100a15`), Band 7 (`geod_shearrate`), Band 8 (`geod_dilaterate`), Band 15 (`depth_to_base_surf`) + INGENIOUS `Seismicity.zip` (`doi:10.15121/1881483`, CC-BY-4.0, cached locally) | **Low** (100% cached locally; zero external downloads; fast vector-to-grid + smooth algebraic transform) | **Highest marginal lift per unit cost** on blind intrabasin transfer/accommodation faults where fluid-driven earthquake swarms occur beneath zero-scarp playa/alluvial cover |
| **2** | **`G79-BLC`** | **Bilateral Lithology-Contrast Change-Point Across Potential-Field & Radiometric Regimes** | Cached `training_features.tif` Band 2 (`rtp`), Band 13 (`iso_grav_anom`), Band 6 (`tc` = GeoDAWN radiometric Total Count), Band 12 (`det_elev`), Band 19 (`det_elev_slope`); optional external GeoDAWN `K / eU / eTh` channels (`doi:10.5066/P93LGLVQ`, CC0 1.0, sandbox-blocked) | **Moderate** (cached 3-channel `{rtp, iso_grav_anom, tc}` version runnable locally after protocol clearance; multi-window bilateral Wasserstein/energy distance along ridges) | **Moderate-to-high** on buried transverse/strike-slip faults offsetting pre-existing volcanic/plutonic contacts without range-front relief |
| **3** | **`G79-RSS`** | **Relief-Screened Detrended-Elevation Structural Saddle Crossed by Orthogonal Isostatic-Gravity Gradient** | Cached `training_features.tif` Band 12 (`det_elev`), Band 19 (`det_elev_slope`), Band 13 (`iso_grav_anom`), Band 5 (`iso_grav_anom_slope`), Band 18 (`iso_grav_anom_hg`), Band 15 (`depth_to_base_surf`) | **Moderate** (100% cached locally; multi-scale Hessian saddle-index $\lambda_1 < 0 < \lambda_2$ + cross-angle $|\sin\Delta\theta|$ against gravity-gradient strike) | **Low-to-moderate** on low-relief relay ramps and inter-range structural saddles systematically under-mapped by scarp-focused Quaternary compilations |
| **4** | **`G79-HFR`** | **Paired Signed Conductive Heat-Flow Residuals Along Basement-Depth Structural Corridors** | External USGS Great Basin Heat Flow release (`doi:10.5066/P9BZPVUC`, CC0 1.0 — **not cached locally; outbound host `sciencebase.gov` blocked in sandbox**) + cached Band 15 (`depth_to_base_surf`) & `TG_probes.zip` | **High / Data-Blocked** in current sandbox (`sciencebase.gov` unreachable; requires external download + well-depth QA screening) | **Uncertain / potentially high** on blind upflow/recharge fault dipoles, but strictly unrunnable in sandbox without verified raw release bytes |

*(Note on prior candidate `G79-CJX`: coincident multi-scale `rtp` + `iso_grav_anom` contact junctions were executed in concurrent `PR #102` (`095c9f0`), closing negative with Exp 1–2 below random due in part to unmasked interior sentinel cliffs (`IR-79-185`) and Exp 3 tip-steered `HOLDOUT-DTI` `0.1041 / 0.1063` below `G79-THVC` `0.1905 / 0.1944`. `G79-CJX` is therefore removed from the unimplemented backlog above.)*

---

## Detailed Physical & Algorithmic Specifications

### 1. `G79-SWARM` — Dependent-to-Independent Seismicity Ratio (`deq / ieq`) Steered Along Geodetic Transtensional Corridors

- **Exact layers & verified provenance:**
  - `data/raw/training_features.tif` **Band 10 (`deq_n100a15`)** and **Band 16 (`ieq_n100a15`)** (`sha256: 4371c82e...`, INGENIOUS compilation, Ayling et al. 2022, GDR #1391, `https://doi.org/10.15121/1881483`, CC-BY-4.0). Direct byte inspection in this review (`evidence/review_87f53313/feature_stack_audit.json`, logged as `IR-79-181`) proved that embedded GDAL text for Band 10 (`"Distance to earthquake"`) is a metadata mislabel: Band 10 values span `0.0` to `4,962,515.0` (median `622.8`) vs Band 16 `236.8` to `7,869.5` (median `755.5`), representing **dependent (clustered/swarm/foreshock-aftershock) vs independent (declustered background) earthquake density** (`n=100`, `a=1.5` kernel parameters in the INGENIOUS workflow).
  - `data/raw/Seismicity.zip` (`sha256: de94eb01...`, cached locally, verified `13/13` in `restore_data.py`), providing exact hypocentral point coordinates for fine-scale (<2 km) anisotropic azimuth estimation lost in the $n=100$ regional grid.
  - `data/raw/training_features.tif` **Band 7 (`geod_shearrate`)**, **Band 8 (`geod_dilaterate`)**, and **Band 15 (`depth_to_base_surf`)** (`doi:10.5066/P9Z6SA1Z`), all masked on `valid = footprint & (band > -1e30)`.
- **Physical signature & mathematical transform:**
  1. Mask all `3,061` interior float32 sentinels (`band <= -1e30`) before any smoothing or ratio calculation.
  2. Compute the stabilized log swarm-excess index on valid footprint pixels:
     $$S_{\text{swarm}}(x) = \log_{10}\!\left(\frac{\max(\text{deq\_n100a15}(x), 0) + 10}{\text{ieq\_n100a15}(x) + 10}\right)$$
     which isolates **fluid-driven seismic swarming** (characteristic of permeable geothermal fracture meshes in stepovers and accommodation zones) from background tectonic mainshock rates (`ieq`).
  3. Couple $S_{\text{swarm}}(x)$ with positive transtensional strain rate ($\text{geod\_shearrate}_+(x)\cdot \max(\text{geod\_dilaterate}(x), 0)$) and sedimentary cover thickness ($\text{depth\_to\_base\_surf}(x) > 400\text{ m}$), localized onto local anisotropic hypocentral lineament ridges extracted from `Seismicity.zip` via a multi-azimuth Radon/Hessian ridge filter (strictly fit per fold without touching `catalogue.npy`).
- **Why it catches faults omitted from USGS Qfaults / INGENIOUS rather than already-mapped faults:**
  USGS Quaternary fault mapping (`Qfaults`) and 3DEP lidar scarp compilations predominantly detect **cumulative surface-rupturing range-front normal faults** on bedrock-alluvium contacts ($\text{depth\_to\_base\_surf} \approx 0$–$300\text{ m}$). Blind geothermal permeability in the Great Basin (e.g., Brady–Desert Peak, Dixie Valley intrabasin relays, Humboldt House, McGinness Hills) is hosted by **sub-resolution accommodation/transfer fault swarms** buried beneath rapidly aggrading playa/alluvial cover ($\text{depth\_to\_base\_surf} > 400\text{ m}$) that repeatedly release microseismic swarms (`deq >> ieq`) without producing persistent surface scarps.
- **How it differs from existing repository implementations:**
  - `G79-THVC` (`src/gems79/thvc_features.py`) passed raw `deq_n100a15` and `ieq_n100a15` as separate un-ratioed tabular inputs into an 84-feature GBDT+MLP classifier trained directly on visible catalogue pixels (which teaches trees to down-weight intrabasin swarm zones wherever unmapped faults sit in the negative training pool) and did not extract anisotropic hypocentral lineaments from `Seismicity.zip`.
  - None of the closed lanes (`E1`, `STEPCO`, `NHR`, `FNHR`, `FFAS`, `COV`, `DILSTEP`, `FGR`, `MRND`, `FF`, `BQA`, `BER`, `CFSKD`, `H80`, `G79-CJX`) constructed the physical `deq/ieq` swarm-excess ratio or coupled it to `Seismicity.zip` hypocentral alignments under thick basin fill.
- **Named non-fault confounder & falsification criterion:**
  Mining blasts, reservoir/injection-induced seismicity near operating geothermal fields, and volcanic dike intrusions also elevate `deq/ieq`. Falsification: if `S_swarm` coupled with transtensional strain fails to beat both a pure `ieq_n100a15` control and `G79-THVC` (`0.1905 / 0.1944`) on `gems57-pooled-hide-v2` Seeds 20 & 30, or if single-channel symmetric canary AUC $> 0.90$, reject immediately.

---

### 2. `G79-BLC` — Bilateral Lithology-Contrast Change-Point Across Potential-Field & Radiometric Regimes

- **Exact layers & verified provenance:**
  - Cached locally in `data/raw/training_features.tif`: **Band 2 (`rtp`)**, **Band 13 (`iso_grav_anom`)**, **Band 6 (`tc` — GeoDAWN radiometric Total Count**, `2.953` to `88.567`, verified via `evidence/review_87f53313/feature_stack_audit.json` and organizer `gems_tc_tmi.png`, `IR-79-181`), **Band 12 (`det_elev`)**, and **Band 19 (`det_elev_slope`)**, masked on the intersection of valid non-sentinel pixels (`3,073` interior sentinels in Band 6 `tc`; `3,061` in the others).
  - Optional external enrichment (if outbound network to `sciencebase.gov` is available in a future environment): USGS GeoDAWN individual potassium (`K`), equivalent thorium (`eTh`), and equivalent uranium (`eU`) grids (Glen & Earney 2024, `https://doi.org/10.5066/P93LGLVQ`, CC0 1.0 Public Domain).
- **Physical signature & mathematical transform:**
  1. Rather than detecting a single-point gradient ridge along a contact (which fires on every intact pluton margin and lava-flow edge, as confirmed by `G79-CJX` Exp 1–2), define at each pixel $x$ and candidate fault strike $\theta \in \{0^\circ, 22.5^\circ, \dots, 157.5^\circ\}$ a **four-quadrant bilateral change-point operator** across paired $800\text{ m} \times 800\text{ m}$ blocks $(Q_{++}, Q_{+-}, Q_{-+}, Q_{--})$ in joint standardized feature space $z = (\tilde{\text{rtp}}, \tilde{\text{iso\_grav}}, \tilde{\text{tc}}) \in \mathbb{R}^3$.
  2. Score cross-fault truncation of an existing lithologic boundary via the multivariate energy distance:
     $$B(x,\theta) = \min\big(D(Q_{++}, Q_{-+}),\, D(Q_{+-}, Q_{--})\big) \cdot \mathbb{I}\!\left[\max\big(D(Q_{++}, Q_{+-}),\, D(Q_{-+}, Q_{--})\big) > \tau_{\text{contact}}\right]$$
     penalized where `det_elev_slope` exceeds range-front scarp thresholds so the detector specifically targets **low-relief transverse offsets of pre-existing lithologic contacts**.
- **Why it catches faults omitted from USGS Qfaults / INGENIOUS rather than already-mapped faults:**
  Strike-slip and oblique transfer faults cutting across Tertiary volcanic tuffs or Mesozoic pluton margins laterally offset magnetic/density/radiometric units beneath thin pediment veneer without creating vertical range-front scarps, so aerial-photo/lidar scarp mapping misses them while cross-quadrant multivariate lithology truncation detects the offset contact.
- **How it differs from existing repository implementations:**
  - `E1` (`gems79`) tested 1D scalar cross-fault offset along visible-catalogue fault normals; `G79-CJX` (`PR #102`) tested local coincident edge magnitude + orientation discordance on `rtp` and `iso_grav_anom` alone (and suffered from unmasked interior `-3.4028e38` sentinels, `IR-79-185`). `G79-BLC` requires **four-quadrant bilateral truncation** across three distinct physical modalities (`rtp` magnetic susceptibility, `iso_grav_anom` bulk density, and `tc` surface radioelement signature) with strict interior-sentinel masking.
- **Named non-fault confounder & falsification criterion:**
  GeoDAWN flight-block seam boundaries (Area 1 200 m drape vs Area 2 400 m drape) and alluvial fan-toe contacts crossing older bedrock ridges. Falsification: seam-parallel azimuths ($0^\circ$ E–W / $90^\circ$ N–S survey tie lines) must be audited via holdout canary (`AUC <= 0.90`), and `B(x)` must beat a single-modality edge baseline and `G79-THVC` on Seeds 20 & 30.

---

### 3. `G79-RSS` — Relief-Screened Detrended-Elevation Structural Saddle Crossed by Orthogonal Isostatic-Gravity Gradient

- **Exact layers & verified provenance:**
  - Cached locally in `data/raw/training_features.tif`: **Band 12 (`det_elev`)** (USGS detrended elevation, `doi:10.5066/P9MQRCBY`), **Band 19 (`det_elev_slope`)**, **Band 13 (`iso_grav_anom`)**, **Band 5 (`iso_grav_anom_slope`)**, **Band 18 (`iso_grav_anom_hg`)** (`doi:10.5066/P9Z6SA1Z`), and **Band 15 (`depth_to_base_surf`)**, all verified `13/13` present locally and masked on `valid = footprint & (band > -1e30)`.
- **Physical signature & mathematical transform:**
  1. Smooth `det_elev` (after interpolating across the `3,061` interior sentinel pixels) at $\sigma \in \{300\text{ m}, 600\text{ m}, 1200\text{ m}\}$ and compute the multi-scale **topographic saddle index** from the eigenvalues $\lambda_1 < 0 < \lambda_2$ of the smoothed elevation Hessian:
     $$\kappa_{\text{saddle}}(x,\sigma) = \sqrt{\max(-\lambda_1, 0)\cdot \max(\lambda_2, 0)} \cdot \exp\!\left(-\frac{|\lambda_1 + \lambda_2|}{|\lambda_1| + |\lambda_2| + \epsilon}\right)$$
     which fires specifically at structural passes, relay ramps, and range-crest cols rather than planar range-front scarps ($\lambda_2 \approx 0$).
  2. Multiply $\max_\sigma \kappa_{\text{saddle}}(x,\sigma)$ by `iso_grav_anom_slope(x)` weighted by the **orthogonality** $|\sin(\theta_{\text{ridge}}(x) - \theta_{\nabla g}(x))|$ between the topographic range-axis eigenvector and the isostatic-gravity horizontal gradient vector, screening out high-slope bedrock cliffs (`det_elev_slope > 15`).
- **Why it catches faults omitted from USGS Qfaults / INGENIOUS rather than already-mapped faults:**
  Quaternary fault maps trace continuous high-relief range fronts on either side of an accommodation zone or relay ramp, but systematically break or terminate across low-relief structural saddles where displacement is distributed across en-echelon oblique stepover faults that govern deep geothermal fluid upflow (Faulds & Hinz 2015 structural inventory).
- **How it differs from existing repository implementations:**
  - Catalogue-endpoint continuation lanes (`STEPCO`, `NHR`, `FNHR`, `FFAS`, `G79-CJX` Exp 3) require **visible catalogue endpoints** (`d_tip`) to locate stepovers and therefore collapse whenever both bounding faults are withheld or unmapped. `G79-RSS` locates relay saddles purely from **catalogue-free multi-scale terrain Hessian topology crossed by orthogonal gravity gradients**.
- **Named non-fault confounder & falsification criterion:**
  Erosional wind/water gaps (e.g., antecedent river canyons cutting across ranges) and caldera rim passes. Falsification: must pass single-channel holdout leakage canary (`AUC <= 0.90`) and beat both pure `det_elev` saddle topology (without gravity cross-angle) and `G79-THVC` (`0.1905 / 0.1944`) on Seeds 20 & 30.

---

### 4. `G79-HFR` — Paired Signed Conductive Heat-Flow Residuals Along Basement-Depth Structural Corridors *(Data-Blocked in Sandbox)*

- **Exact layers & verified provenance:**
  - External primary dataset: **USGS Great Basin Heat Flow measurements & conductive background model** (`https://doi.org/10.5066/P9BZPVUC`, CC0 1.0 Public Domain, linked from INGENIOUS GDR #1391 `https://gdr.openei.org/submissions/1391`). **Obtainability status:** **NOT obtainable inside the current sandbox** because outbound network access is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org` (`sciencebase.gov` and `gdr.openei.org` binary endpoints are unreachable here). Obtainable without fee or registration in an unrestricted environment.
  - Cached companion layers: `data/raw/TG_probes.zip` (`2m_temp` points, cached locally) and `training_features.tif` **Band 15 (`depth_to_base_surf`)** + **Band 5 (`iso_grav_anom_slope`)**.
- **Physical signature & mathematical transform:**
  Compute signed well-level heat-flow residuals $r_i = q_i - \hat{q}_{\text{conductive}}(x_i, z_i)$ relative to depth-screened regional conductive heat flow, and detect **paired positive/negative hydrothermal advection dipoles** ($r_+ > +25\text{ mW m}^{-2}$ upflow paired within $1.5$–$6\text{ km}$ of $r_- < -15\text{ mW m}^{-2}$ recharge along a `depth_to_base_surf` gradient corridor).
- **Why it catches faults omitted from USGS Qfaults / INGENIOUS rather than already-mapped faults:**
  Blind convective geothermal systems circulate along permeable subsurface fault conduits beneath impermeable clay-rich playa caps with zero surface fault scarp and zero surface hot-spring/sinter expression (`Paleo.zip` empty), leaving only subsurface borehole heat-flow dipoles.
- **How it differs from existing repository implementations:**
  `G79-THVC` used `2m_temp` Band 4 and unsigned proximity to `TG_probes.zip` / `Geochem.zip` / `Paleo.zip`; no lane in the repository has acquired `doi:10.5066/P9BZPVUC` or modeled signed upflow–recharge heat-flow dipoles along basement-depth corridors.
- **Named non-fault confounder & falsification criterion:**
  Shallow lateral outflow plumes in permeable alluvial aquifers (`<150 m` wells) displaced down-gradient from the upflow fault, plus clustered drilling bias around known prospects (`leakage_canary` mandatory on well density alone!). Strictly deferred until raw `doi:10.5066/P9BZPVUC` bytes are acquired, checksum-pinned in `data/manifest.json`, and screened for well-depth bias.
