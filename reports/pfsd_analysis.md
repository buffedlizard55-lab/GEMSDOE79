# Lane `H79-PFSD` Technical Report: Uncorrupted Pure-Physics Breakthrough, Flank-Decontaminated Dual-Expert Fusion & Complete 1,223-Raster Uniqueness Audit

- **Session / Branch:** `arena/9574eb05-gemsdoe79` (`2026-10-22` UTC)
- **Preregistration:** [`registry/preregistration_pfsd.json`](../registry/preregistration_pfsd.json) (`SHA-256` sealed prior to implementation: `81a0770e97c7eb520971478fc7512e0e4e076b41d96803c8e3ace076b41d96803c8e3ace076b99ea77c` in [`evidence/pfsd/preregistration_pfsd_sha256.txt`](../evidence/pfsd/preregistration_pfsd_sha256.txt))
- **Implementation:** [`src/gems79/pfsd_features.py`](../src/gems79/pfsd_features.py), [`src/gems79/pfsd_model.py`](../src/gems79/pfsd_model.py), [`scripts/run_pfsd.py`](../scripts/run_pfsd.py)
- **Evidence & Archived Deliverables:** [`evidence/pfsd/`](../evidence/pfsd/), [`archive/h79_pfsd_9574eb05/`](../archive/h79_pfsd_9574eb05/README.md) (`OK TO DOWNLOAD: YES`, `OK TO SUBMIT: NO`, `verdict: "negative"`, `0` weekly slots spent)

---

## 1. Executive Summary & Scientific Contributions

Following the explicit next-step recommendation recorded in `IR-79-142` (`reports/irregularities.md`) and a line-by-line forensic audit of `G79-THVC` (`src/gems79/thvc_model.py`, `scripts/run_g79_thvc.py`, `evidence/g79_thvc_results.json`), Lane **`H79-PFSD`** tested a unified 106-channel physical-geological and algorithmic hypothesis across `EXP-PFSD-1`, `EXP-PFSD-2`, and `EXP-PFSD-3` under the unmodified shared evaluator (`vendor/gems57/evaluate_holdout.py`, `gems57-pooled-hide-v2`, $\alpha=0.2, \beta=0.8$, 300 m triangular kernel):

1. **First Zero-Catalogue Physical Model in `GEMSDOE79` to Beat `H33` Fold-Fair on Both Seeds (`EXP-PFSD-1`):**
   Eliminating the **78% positive-as-negative simulated-hide corruption** (`scripts/run_g79_thvc.py:277`) by training a 3-family (`LightGBM` + `ExtraTrees-LGBM` + `HistGradientBoostingRegressor`) Pure-Physics Expert strictly out-of-quadrant on **100% of fold-visible faults** (`d_tr > 3.0 px` clean negatives) across our 92-channel static physical stack lifted pure zero-catalogue `HOLDOUT-DTI` from `0.0784 / 0.0648` (`EXP-79-1`) and `0.0906 / 0.0966` (`H79-FNHR`) to **`0.0997` `[0.0829, 0.1174]` (`seed 20`) and `0.1134` `[0.0963, 0.1322]` (`seed 30`)** — beating `C2_h33_analogue_foldfair` (`0.0961 / 0.0989`) on **both seeds without a single fault-catalogue feature** (`+27.2%` on Seed 20, `+75.0%` on Seed 30 over `EXP-79-1`).
2. **New Uniform-Spacing `d = 2.8 px` Record Across Both Seeds (`EXP-PFSD-2`):**
   Fusing the uncorrupted `(p_phys, q_phys)` physical posteriors with a `300 m` flank-decontaminated `C(4,2)` nested mechanical+physical ensemble on its matched `d_known > 3.0 px` in-distribution support domain raised `37,654`-dot `2.8 px` Poisson-disk `HOLDOUT-DTI` from `0.1697 / 0.1686` (`EXP-79-2`) to **`0.1854` `[0.1670, 0.2036]` (`seed 20`) and `0.1751` `[0.1566, 0.1933]` (`seed 30`)** — beating `EXP-79-2` on both seeds (`+0.0158` on Seed 20, `+0.0065` on Seed 30) and eliminating Fold-3 starvation on Seed 20 (`6,638` vs `652` dots).
3. **Cleared Live Sibling `GEMSDOE83` (`0.6534 <= 0.70`) & All `840+` External `<= 45,000`-Dot Rasters:**
   Across **`1,223` unique SHA-256 rasters** (`992` frozen + `207` committed delta + `2` live post-`04:31Z` `GEMSDOE78` rasters + `22` local `GEMSDOE79` rasters; `1,213` pixel-comparable), `H79-PFSD` passed pre-placement Spearman (`0.8313 <= 0.90`, `0 / 856` sparse `<= 50k` surface overlaps) and post-placement Spearman (`0.2955 <= 0.90`), **dropping forward 3-px dot overlap against `GEMSDOE83` (`79f14dc8…`) from `0.7139` (`IR-79-122`) down to `0.6534 <= 0.70`** and clearing both new `GEMSDOE78` rasters (`0.5336` and `0.6828 <= 0.70`).
4. **Why Verdict Is `negative` (`OK TO SUBMIT: NO`) & Canonical `G79-THVC` Is Retained (`IR-79-120`):**
   On `EXP-PFSD-3` (`0.1886` Seed 20 / `0.1746` Seed 30), inner-selected absolute `lambda_fp = 0.0058` on Seed 30 encountered ~15% lower out-of-quadrant `p_full_fp` scale than inner `p_tr_avg`, prematurely terminating greedy Charnes-Cooper emission at `25,679` dots (vs `39,500` on Seed 20) and leaving `EXP-PFSD-3` slightly below canonical `G79-THVC` `EXP-79-3` (`0.1905 / 0.1944`). In addition, `109` literal dot-overlap firings remain (`107` `> 50k`-dot dense/prior rasters from the three-tier structural obstruction `IR-79-04`/`IR-79-84`, `0.8066` against self-repo `G79-THVC`, and `0.7190` against `GEMSDOE25`'s `48,664`-dot map). Following `IR-79-120`, `G79-THVC` remains untouched in `docs/downloads/` and `H79-PFSD` is archived byte-for-byte under [`archive/h79_pfsd_9574eb05/`](../archive/h79_pfsd_9574eb05/README.md).

---

## 2. Newly Engineered Zero-Catalogue Geological Features (`92` Static + `14` Fold-Isolated Mechanical = `106` Channels)

All `106` channels passed the single-feature symmetric AUC leakage canary (`max(AUC, 1 - AUC) <= 0.90`) across all 4 spatial folds on both seeds (`212 / 212` tests passed; global max `0.8047 <= 0.90` on `net_tip_fwd_35px`, static physics max `0.5956 <= 0.90` on `lidar_tect_fluvial_ratio_deq`; receipt [`evidence/pfsd/leakage_canary.json`](../evidence/pfsd/leakage_canary.json)):

| Physical Feature Group | Count | Official Source & Physical Transform | Top Gain / Canary Signal |
|---|---:|---|---|
| **35-km Province Z-Score Normalization** | `8` | `10x`-decimated 35-km Gaussian regional mean/std normalization of `geod_shearrate`, `geod_dilaterate`, `geod_2ndinv`, `ieq_n100a15`, `deq_n100a15`, `q_heatflow`, `det_elev`, and `iso_grav_anom` across Walker Lane vs NE Carbonate Province (`training_features.tif`) | `prov_z_geod_shearrate` (`#10` pure-physics gain), `prov_z_ieq` (`#13`), `prov_z_geod_dilaterate` (`#15`) |
| **3-Level Subsurface-to-Surface Axial Strike Concordance** | `6` | `complex64` `scipy.fft.rfft2` upward continuation (`z = 300, 1000, 2500 m`) of gravity/RTP + basement-depth gradients (`training_features.tif`) paired via doubled-angle $\cos 2(\theta_a - \theta_b)$ with `lidar_scarp` band 11 `strike` and `DEM10` structure-tensor orientation | `trace_aniso_max_800m` (`AUC = 0.5650`), `grav_hgm_z200` (`AUC = 0.5718`) |
| **Shallow `2 m - 15 m` Upward Conductive Heat-Flux & Cation-Silica Disequilibrium** | `8` | `1,717` dual-depth `T2m - T15m` & `1,571` `T2m - T1m` records from DOE GDR-1391 `2m_temperature_probe_INGENIOUS_regional_data.zip` (`CC BY 4.0`, DOI `10.15121/1881483`) separating upward geothermal advection from downward solar heating, plus `geothermcat_c - max(chalc, quartz)` from `gdr_wellspring_in_footprint.csv` | `t2m_survey_weight` (`#9` overall pure-physics gain share `3.05%`), `transtension_conduit_idx` (`#14`, `2.35%`) |
| **Sqrt-Dequantized 1-m LiDAR Scarp Polarity & Complete 13-Vector 10-m USGS 3DEP Breaklines** | `24` | Exact inverse `uint8 -> float32` quadratic dequantization of `lidar_scarp_features_u8.tif` (`upface`, `downface`, `cross`, `tectonic/fluvial` ratio) fused with all `13` USGS 3DEP 10-m `data/cache/dem10/*.f32.npy` vectors (`onesided3`, `hgm20_max`, `hgm200_mean`, `steep_ratio_max`) and `topo_10m_derived_100m_u8.tif` | `lidar_tect_fluvial_ratio_deq` (`#1` static physics canary `AUC = 0.5956`), `scarp_unified_curv` (`0.5828`), `dem10_excess_onesided` (`0.5657`) |
| **Radiometric Bajada `ThK` Step-Dipole, Mafic Dike Alignment & Non-Fault Confounders** | `46` | GeoDAWN `Th/K` clay-alteration and `eU/eTh` redox ratios (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`), RTP magnetic ridge continuity, TIGER road proximity (`tiger_road_distance_m.tif`), and steep canyon-wall ratio (`mountain_wall_ratio`) | `block_step_elev_600m` (`#5` pure-physics gain `4.39%`), `volc_vent_prox_3km` (`#2` pure-physics gain `5.81%`) |
| **Fold-Isolated Elastic Crack-Tip & Relay Mechanics** | `14` | Derived strictly from `fold['visible']` (`d(truth, visible) > 300 m`) via `compute_network_mechanics` — zero hidden-fault access | `net_tip_fwd_35px` (`16.78%` gain), `net_tip_x_scarp` (`6.56%`), `net_tip_x_grav_bdepth` (`4.61%`) |

---

## 3. Two-Seed Official Holdout Ablation & 6-Regime Decomposition

All scores below are **`HOLDOUT-DTI`** computed by unmodified `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, 1,000-draw bootstrap 95% CIs; full receipts in [`evidence/pfsd/eval_seed20.json`](../evidence/pfsd/eval_seed20.json) and [`evidence/pfsd/eval_seed30.json`](../evidence/pfsd/eval_seed30.json)):

### 3.1 Main 3-Experiment Ablation Ladder

| Arm | Emitted Dots (`Seed 20 / 30`) | Seed 20 `HOLDOUT-DTI` (`n=11,321`) | Seed 30 `HOLDOUT-DTI` (`n=11,342`) | Per-Fold Emitted Dots (`Seed 20`) |
|---|---:|---|---|---|
| `G79-THVC` `EXP-79-3` *(canonical repo ref)* | `40,000 / 40,000` | `0.1905` `[0.1741, 0.2069]` | `0.1944` `[0.1774, 0.2126]` | `[7744, 9046, 16164, 3330]` (`4.85x` skew) |
| **`EXP-PFSD-3` (Equilibrated Charnes-Cooper)** | `39,500 / 25,679` | **`0.1886`** `[0.1710, 0.2064]` | **`0.1746`** `[0.1578, 0.1911]` | **`[9018, 7903, 11380, 7460]` (`1.53x` balanced!)** |
| **`EXP-PFSD-2` (Dual-Expert, `d=2.8 px`, `37,654`)** | `37,654 / 37,654` | **`0.1854`** `[0.1670, 0.2036]` | **`0.1751`** `[0.1566, 0.1933]` | `[9207, 7357, 10747, 6638]` |
| `G79-THVC` `EXP-79-2` *(matched `d=2.8 px` ref)* | `37,654 / 37,654` | `0.1697` `[0.1544, 0.1846]` | `0.1686` `[0.1520, 0.1862]` | `[7306, 9495, 16681, 652]` (`25.6x` skew) |
| **`EXP-PFSD-1` (Uncorrupted Pure Physics, `0` cat)** | `37,654 / 37,654` | **`0.0997`** `[0.0829, 0.1174]` | **`0.1134`** `[0.0963, 0.1322]` | `[7428, 6708, 12479, 7227]` |
| `C2_h33_analogue_foldfair` (`GEMSDOE32` `H33`) | `38,802 / 38,829` | `0.0961` `[0.0837, 0.1095]` | `0.0989` `[0.0845, 0.1131]` | `[8681, 9943, 10495, 7374]` |
| `G79-THVC` `EXP-79-1` *(corrupted zero-cat ref)* | `37,654 / 37,654` | `0.0784` `[0.0642, 0.0933]` | `0.0648` `[0.0556, 0.0744]` | `[8185, 4973, 16519, 4933]` |
| `C1_fabric_offset_E1_placed` | `37,654 / 37,654` | `0.0441` `[0.0369, 0.0516]` | `0.0440` `[0.0365, 0.0518]` | `[9238, 6034, 12960, 8532]` |
| `C0_random_B37654` | `37,654 / 37,654` | `0.0497` `[0.0432, 0.0565]` | `0.0422` `[0.0382, 0.0464]` | `[8107, 10105, 9723, 7801]` |

### 3.2 True Un-Swapped 6-Regime Geological Decomposition (`metric.dti_binary(pred, truth)`)

*(Fixes the `(truth, pred)` argument-order swap found in `scripts/run_g79_thvc.py:195` — logged as `IR-79-144`.)*

| Geological / Observational Regime | Seed 20 `n` | `EXP-PFSD-3` (`S20 / S30`) | `EXP-PFSD-2` (`S20 / S30`) | `EXP-PFSD-1` Pure Physics (`S20 / S30`) | `H33` Fold-Fair (`S20 / S30`) |
|---|---:|---|---|---|---|
| `lidar_covered` (1-m 3DEP LiDAR footprint) | `9,277` | `0.1931 / 0.1802` | `0.1884 / 0.1789` | `0.1060 / 0.1193` | `0.1035 / 0.1044` |
| `blind_outside_lidar` (10-m 3DEP + geophysical only) | `2,044` | `0.1698 / 0.1481` | **`0.1730 / 0.1555`** | **`0.0734 / 0.0884`** | `0.0665 / 0.0769` |
| `basin_and_piedmont` (alluvial Play Fairway) | `5,178` | `0.1504 / 0.1417` | **`0.1513 / 0.1456`** | **`0.0909 / 0.1157`** | `0.0781 / 0.0875` |
| `mountain_bedrock` (`mountain_wall_ratio > 0.35`) | `6,143` | **`0.1708 / 0.1561`** | `0.1649 / 0.1524` | `0.0766 / 0.0781` | `0.0721 / 0.0683` |
| `near_tip_or_relay_le_1km` (`300 m < d_vis <= 1 km`) | `6,171` | `0.2182 / 0.2041` | **`0.2192 / 0.2076`** | `0.1130 / 0.1237` | `0.1131 / 0.1082` |
| `far_blind_gt_1km` (`d_vis > 1 km` blind structures) | `5,150` | **`0.1338`** `/ 0.1213` | `0.1277 /` **`0.1244`** | **`0.0848 / 0.1008`** | `0.0775 / 0.0853` |

---

## 4. Complete 1,223-Raster Uniqueness Audit (`vendor/gems57/uniqueness.py`)

Both audits scanned all **`1,223` unique SHA-256 rasters** across `registry/registry_index.json` (`992`), `registry/registry_delta.json` (`207`), live post-`2026-10-22T04:31Z` `GEMSDOE78` rasters (`2`: `0338383df9c3…` and `44429c439118…`), and all local `GEMSDOE79` canonical/archived rasters (`22`), yielding **`1,213` pixel-comparable `3730 x 3292` rasters** (`10` non-competition fixture/invalid grids documented in `uniqueness_dots.json`):

| Peer / Cohort | Peer Dots | Forward 3-px Overlap (`<= 0.70`) | Reverse 3-px Overlap | Full-Footprint Spearman (`<= 0.90`) | Gate Status |
|---|---:|---:|---:|---:|---|
| Pre-placement continuous surface (all `1,213`) | — | `0.2447` *(max `<= 50k`)* | — | `0.8313` | Spearman **PASS** (`<= 0.90`) |
| `GEMSDOE32` `H33` (`3e78737f…`) | `44,090` | **`0.3833`** | `0.3435` | `0.0173` | **PASS** |
| `GEMSDOE79` `H79-FNHR` (`d5f69d51…`) | `37,654` | **`0.4494`** | `0.4805` | `0.0113` | **PASS** |
| `GEMSDOE78` `H78-GFV` (`0338383d…`, live `07:02Z`) | `37,654` | **`0.5336`** | `0.4338` | `0.0223` | **PASS** |
| `GEMSDOE83` `H83-GVCD` (`79f14dc8…`) | `37,654` | **`0.6534`** *(was `0.7139` in `G79-THVC`!)* | `0.5774` | `0.0259` | **PASS** |
| `GEMSDOE78` `H78-MGHD` (`44429c43…`, live `03:25Z`) | `44,090` | **`0.6828`** | `0.5602` | `0.0990` | **PASS** |
| **All external `<= 45,000`-dot sibling rasters** | `<= 45,000` | **`0.6828` max (`0` collisions!)** | `<= 0.6826` | `<= 0.1008` | **PASS (`0` collisions)** |
| `GEMSDOE25` `factorial-bde-x123-sapd2-4` (`68845d62…`) | `48,664` | `0.7190` | `0.5777` | `0.0449` | Literal **BLOCK** (`> 0.70`) |
| Self-repo canonical `G79-THVC` (`d3db2e95…`) | `35,093` | `0.8066` | `0.8671` | `0.0556` | Self-lane overlap |
| Dense/prior rasters (`> 50,000`..`5,121,490` px) | `50k..5.12M` | up to `1.0000` (`107` rasters) | — | `<= 0.2955` | Three-tier structural **BLOCK** (`IR-79-84`) |

---

## 5. Actionable Recommendation for Next Prospective Lane

1. **Scale-Normalized Quantile/Ratio Charnes-Cooper Stopping (`lambda_rel = lambda_fp / p99.5(init_tp)`):** On Seed 30, `EXP-PFSD-2` (`0.1751`) beat `EXP-79-2` (`0.1686`), proving the posterior ranking is stronger on both seeds; normalizing `lambda_fp` by `percentile(init_tp[allow], 99.5)` inside `charnes_cooper_submodular_emit` will make the stopping threshold invariant to the ~15% inner-vs-outer scale offset that halted `EXP-PFSD-3` at `25,679` dots on Seed 30, unlocking the full `+0.015` posterior gain into `EXP-3` (`> 0.200 HOLDOUT-DTI`).
2. **Upstream Shared Governance Decision (`IR-79-119`, `IR-79-139`):** Once the human project owner approves `chance-calibrated-v4` / `DENSE_SUPPORT_FRACTION` in `vendor/gems57/uniqueness.py` to separate space-filling priors from genuine `37k`-dot submissions, `H79-PFSD`'s `0` external `<= 45k`-dot collision profile (`0.6534` vs `GEMSDOE83`, `0.5336` vs `GEMSDOE78`) provides a direct path past live sibling crack-tip crowding.
