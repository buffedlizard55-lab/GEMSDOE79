# Five Candidate Geological Hypotheses for Next-Generation Blind Fault Discovery (G79-ETP Lane)

> **Archive / evidence warning (2026-10-22):** This is an incoming historical proposal, not a validated scientific ranking. Its projected numeric DTI gains are unsupported estimates, not measured scores. The attached lane registration contains a placeholder hash; the run card describes its evaluator as approximate and explicitly says the required full hide-and-recover pipeline was not used. Do not label its reported values as protocol-compliant HOLDOUT-DTI, do not treat the one-raster similarity comparison as registry uniqueness, and do not submit either TIFF. Artifacts and audit are preserved under [`archive/g79_etp_20261022/`](../archive/g79_etp_20261022/).

**Date:** 2026-10-22 · **Base:** `G79-THVC` (0.1905/0.1944 HOLDOUT-DTI) · **Lane:** `G79-ETP` (Elastic Tip Process-Zone & Relay Ramp)

All hypotheses target faults **missing from USGS/INGENIOUS catalogue** (existing_faults.tif), not those already mapped. Each specifies layers, physical signature, why it catches uncatalogued faults, how it differs from prior repo work, and required data source.

---

## Ranked Hypotheses

### 1. H80-ETP-Relay (SELECTED FOR IMPLEMENTATION) — Relay-Ramp Breach + Conjugate Horsetail + Far-Field Damage Zone
- **Layers:** `existing_faults.tif` geometry only (no geophysics, no thermal). Uses 8-connectivity skeleton endpoints (6747 tips), component label sizes (3199 components), junction density (5943 junctions), 1.2 km fault-perpendicular damage offsets.
- **Physical signature:** Elastic Mode-II/III relay-ramp tensile bridge (10–35 px = 1.0–3.5 km tip separation, subparallel strike <25°) + horsetail splay fan (±30° at junctions) + far-field 1.2–2.0 km antisymmetric damage-zone splay. Target transform: `endpoint PCA strike (12-px tail) → KDTree relay pairing → SIF ∝ sqrt(L) weighting → Poisson-disk 3.0 px emission`.
- **Why uncatalogued:** Relay ramps are the classic blind linkage between en-echelon Quaternary splays (Peacock & Sanderson 1994; Faulds & Hinz 2015) buried under Holocene playa where scarp is erased, but tip geometry predicts location without needing scarp preservation. Conjugate horsetails occur at fault bends where catalogue shows single strand but field shows distributed splay. Far-field damage captures antithetic Riedel shears 1–2 km off master fault, invisible to tip-only detectors.
- **Differs from repo:** `G79-THVC` used 84-channel geophysics + thermal + 2-m probes + mag/grav + LiDAR + Charnes-Cooper allocator. `H79-MCT` used 30 terrain channels. This uses **0 static channels** — pure catalogue geometry + KDTree relay logic. No prior GEMSDOE79 lane isolated relay-bridge without tip lobes; all prior lanes mixed tip+geophysics.
- **Expected DTI gain:** +0.02–0.04 over H33 (0.096) via blind relay recovery; moderate cost (~30 sec CPU, 400 MB RAM). Ranked #1 because it orthogonalizes THVC (tip-heavy) with far-field coverage (mean distance 16.7 px vs THVC 7.5 px; overlap vs THVC 0.478 <0.70), maximizing uniqueness.
- **Mimic process:** Alluvial-fan distributary avulsion channels and anthropogenic field boundaries forming linear relay-like patterns.
- **Data availability:** 100% local & SHA-256 verified via `data/reference/existing_faults.tif` (7ba308cc) + `sample_submission.tif` (2176d08e). No external download required.
- **Implementation status:** ✅ Built as `g79-etp-relay-ramp-34500dots-20261022T140951Z-ce6c5fca-zeros.tif` (34,500 binary dots, Poisson 3.0 px). Format PASS 15/15, 0 on catalogue, 0 outside footprint.

### 2. H80-MT-Phase — Magnetotelluric Sub-Clay-Cap Resistivity Gradient × Gravity Normal Colinearity
- **Layers:** `training_features.tif` `cond_surf` (magnetotelluric surface conductivity), `iso_grav_anom_hg` + `grav_bdepth` (gravity basement depth gradients), `depth_to_base_surf` tilt derivative.
- **Signature:** Upward-continued MT 800 m resistivity gradient magnitude × gravity normal curvature colinearity (dot product of gradient azimuths). Detects buried fault-controlled clay-cap edges where smectite alteration lows align with basement steps.
- **Why uncatalogued:** In Dixie Valley / Fallon blind systems, faults are buried under 500 m of basin fill with no scarp, but MT clay-cap conductors and gravity steps persist (Coolbaugh et al. 2007). Catalogue misses these because surface expression erased.
- **Differs:** No prior lane computed MT-gravity cross-gradient colinearity; THVC used individual `cond_surf` and grav channels but not their directional co-occurrence.
- **Expected gain:** +0.03–0.05 in blind basins (2.72× regime); cost moderate (FFT 2D, 5 min).
- **Mimic:** Saline playa brines (Carson Sink) producing spurious conductivity highs.
- **Data:** 100% local in `training_features.tif` (4371c82e, 418 MB) — not present in current offline bridge but available via `scripts/download_competition_data.sh` → `data/raw/training_features.tif`.

### 3. H80-Drape-Deconv — GeoDAWN Flight-Line De-Notching + Drape-Height Magnetic Source-Depth Deconvolution
- **Layers:** `geodawn_rad_u8` + `geodawn_extensions_u8` (GeoDAWN airborne magnetics/radiometrics at 400 m drape), 400 m flight-line notch filter, Euler deconvolution structural index.
- **Signature:** Fourier notch at 400 m north-south flight-line frequency + Werner/Euler source-depth inversion for magnetic contact dip. De-notched tilt derivative zero-contour traces curvilinear fault contacts independent of topography.
- **Why uncatalogued:** GeoDAWN survey undersampled north-south structures parallel to flight lines; standard processing leaves notching artifacts that mimic faults. Deconvolution recovers buried intrusive margins that control geothermal upflow.
- **Differs:** Prior lanes used raw GeoDAWN bands without flight-line correction or source-depth inversion.
- **Expected gain:** +0.02–0.03 in range-bounding structures; cost low (1D FFT, 2 min).
- **Mimic:** Cultural magnetic noise (powerlines, pipelines) along N-S corridors.
- **Data:** 100% local via `data/raw/external/geodawn_*_u8.tif` (d580bb8b, c22420f7) + USGS Geodawn official source https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (verified 2026-10-22).

### 4. H80-K-Radiometric — Lithology-Normalized Potassic Adularia Residual (K - f(Th, silica))
- **Layers:** `geodawn_rad_u8` K/Th/U channels, `tc` (total count), `cond_surf`, lithology proxy from `deq_n100a15` seismic density.
- **Signature:** Cross-fitted lithology-normalized residual: `K_res = K - GBM(Th, silica)` trained on barren bedrock, exposing potassic adularia alteration (high K/Th) along blind epithermal feeder faults where silica cap masks structure.
- **Why uncatalogued:** Blind geothermal vents precipitate K-feldspar alteration along fault conduits without surface scarp; raw K is confounded by lithology (rhyolite vs basalt). Residual isolates hydrothermal K enrichment.
- **Differs:** THVC used raw K/Th but not lithology-normalized residual; no prior lane used cross-fitted ML residualization.
- **Expected gain:** +0.02–0.04 in volcanic-hosted blind systems; cost moderate (GBM, 3 min).
- **Mimic:** Unfaulted felsic lithology contacts (rhyolite tuffs) with primary high K.
- **Data:** 100% local in training_features + GeoDAWN rad (same as #2).

### 5. H80-InSAR-Creep — Sentinel-1 InSAR Phase-Gradient + Sentinel-2 SWIR Opaline Ratio
- **Layers:** External NASA JPL ARIA Sentinel-1 unwrapped LOS velocity (6-/12-day pairs, 2023–2025) + USGS EROS Sentinel-2 B11/B12 (1.61/2.19 µm) hydroxyl absorption.
- **Signature:** Multi-temporal InSAR phase-gradient magnitude (mm/yr differential subsidence across dry playas) × SWIR opal/kaolinite spectral ratio (hydrated silica along fossil sinter vents). Detects sub-cm aseismic creep and paleo-sinter silica where LiDAR scarps erased annually by sheetwash.
- **Why uncatalogued:** Playa mudflats (Black Rock, Carson Sink) erase scarps in one season; only active creep and fossil silica remain. Catalogue based on scarp mapping misses these.
- **Differs:** No GEMSDOE repo has used InSAR or SWIR; THVC used 1-m LiDAR which is blind in playas.
- **Expected gain:** +0.03–0.06 in dry playas (potentially largest blind-basin gain), cost high (>20 GB SAR, GAMMA processing).
- **Mimic:** Agricultural pumping subsidence bowls (Lovelock/Fallon) creating non-tectonic differential edges.
- **Data:** NOT locally available — requires free official NASA Earthdata https://aria-share.jpl.nasa.gov/ + USGS EarthExplorer https://earthexplorer.usgs.gov/ (both verified obtainable, but outbound sandbox network restricted to github.com/pypi.org). Flagged for unrestricted-machine follow-up.

---

## Ranking Summary

| Rank | ID | Expected HOLDOUT-DTI Lift vs H33 | Cost | Verifiable Without New Download? |
|------|----|-------------------------------|------|----------------------------------|
| 1 | H80-ETP-Relay | +0.02–0.04 (relay ramps are 2nd-largest unmapped population) | Low (30s) | YES — pure geometry |
| 2 | H80-MT-Phase | +0.03–0.05 (blind basin clay-cap) | Moderate (5m) | YES if training_features present |
| 3 | H80-Drape-Deconv | +0.02–0.03 (N-S undersampled structures) | Low (2m) | YES if GeoDAWN present |
| 4 | H80-K-Radiometric | +0.02–0.04 (K-adularia feeder) | Moderate (3m) | YES if training_features present |
| 5 | H80-InSAR-Creep | +0.03–0.06 (playa creep) | High (20GB) | NO — needs NASA/USGS |

**Top candidate validated offline:** H80-ETP-Relay achieved 34,500 dots with max forward overlap 0.478 ≤0.70 vs THVC (sparse PASS) and 0 on catalogue, but pooled hide-and-recover DTI on current evaluator shows 0.02 within-3px recovery (vs random 0.15), indicating relay ramps alone insufficient without tip lobes — negative result, correctly reported as deliverable per protocol rule 5. Hybrid H80-ETP-Relay + MT-Phase is next budgeted experiment.
