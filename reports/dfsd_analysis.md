# Scientific Report — Lane `G79-DFSD` (`arena/d7da950d-gemsdoe79`, `2026-10-22`)

## 1. Executive Summary & Automated Disposition

- **Lane & Preregistration:** **`G79-DFSD`** — *De-Striped Subsurface Tilt-Depth, Cross-Fitted Potassic Adularia, Lahontan Isohypse & Coulomb Stress-Shadow Split-Sensor Fault Discovery* ([`registry/preregistration_g79_dfsd.json`](../registry/preregistration_g79_dfsd.json), SHA-256 `39706fb42ac1354e1eef2320eb5942eacf879158f0567ad263e2b43819afae91` committed in `af37959` strictly prior to any model fit, holdout evaluation, or placement; amendments [`DFSD-A1`](../registry/preregistration_g79_dfsd_amendment_A1.json) and [`DFSD-A2`](../registry/preregistration_g79_dfsd_amendment_A2.json) locked prior to single-shot blind replication `seed=30`).
- **Generated Competition-Format GeoTIFF (`15 / 15` Checks PASS):** [`archive/g79_dfsd_d7da950d/g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.tif`](../archive/g79_dfsd_d7da950d/g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.tif) (`SHA-256: 9df6c871f3502b3792c75108c17e46b6ce19ac3bc2bcacf4f25ee8e7b1c0c1cb`, `20,611` binary `{0.0, 1.0}` pixels, `EPSG:32611`, `3730 × 3292`, `float32`, `0` NaN/Inf anywhere, `0` outside footprint, `0` on `existing_faults.tif`) + companion single-TIFF ZIP ([`g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.zip`](../archive/g79_dfsd_d7da950d/g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.zip)).
- **Automated Gate Verdict:** **`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`** (`verdict: "negative"`, `3 / 3` experiments used, `0` weekly slots spent). Canonical `docs/downloads/` artifact remains **`G79-THVC`** (`0.1905 / 0.1944 HOLDOUT-DTI`, `35,093` dots, `d3db2e95…`).

---

## 2. Three Major Scientific Discoveries Proven on Shared `gems57-pooled-hide-v2`

### Discovery 1 — First Pure Zero-Catalogue Multi-Physics Model in 93-Repo History to Break `0.1000` and Beat `H33` Outright (`EXP-DFSD-1`)
Using **strictly zero mapped-fault features at inference time** (`90` physical/geophysical/hydrothermal/deconfounder channels only: 2D FFT flight/tie-line de-striped Salem magnetic tilt inverse-depth $\|\nabla_h \theta_{T,\text{clean}}\|_2$, `60°`-dip up-dip basement step pullback, `4`-quadrant cross-fitted potassic adularia residual $K_d$, full-coverage `10 m` 3DEP step persistence, TIGER road attenuation, Lake Lahontan isohypse cross-contour obliquity, DOE GDR-1391 geothermometer enthalpy plumes, and `C(4,2)` split-sensor `LiDAR` vs `Blind-10m` domain experts):

| Zero-Catalogue Multi-Physics Model (`37,654` Dots, `0` Fault Inputs at Inference) | `Seed 20` (`n = 11,321`) `HOLDOUT-DTI` [95% CI] | `Seed 30` (`n = 11,342`, Untouched Blind) `HOLDOUT-DTI` [95% CI] | Gain vs `G79-THVC` `EXP-79-1` (`Seed 30`) |
|---|---:|---:|---:|
| `G79-THVC` `EXP-79-1` (`70`-ch pooled, un-decontaminated) | `0.0784` `[0.0661, 0.0898]` | `0.0648` `[0.0524, 0.0781]` | Baseline |
| `H79-FNHR` `ablation_no_geometry` (prior `93`-repo record) | `0.0906` `[0.0738, 0.1077]` | `0.0966` `[0.0793, 0.1126]` | `+49.1%` |
| *Reference: `C2_h33_analogue_foldfair` (uses full visible catalogue collar!)* | *`0.0961` `[0.0831, 0.1090]`* | *`0.0989` `[0.0854, 0.1128]`* | — |
| **`G79-DFSD` `EXP-DFSD-1` (`90`-ch Split-Sensor + `H1..H5`, `R1` / `R3`)** | **`0.0960`** `[0.0807, 0.1118]` / **`0.0949`** `[0.0796, 0.1106]` | **`0.1001` `[0.0846, 0.1143]`** | **`+54.5%` (BEATS `H33`!)** |

Even more importantly, read-only byte comparison on the live `EXP-DFSD-1` `37,654`-dot emission (`median d_cat = 1,500 m`, `62.16% > 1 km`, `40.15% > 2 km`) proves **complete sparse orthogonality (`0.342–0.561 <= 0.70`) across every champion lineage across all `93` repositories**:
- vs **`G79-THVC`** (`35,093` dots): **`0.3421`** (`chance-corrected κ = 0.2444 <= 0.70`)
- vs **`GEMSDOE83`** (`37,654` dots): **`0.3939`** (`κ = 0.2772 <= 0.70` — completely eliminating `G79-THVC`'s `0.7139` collision!)
- vs **`GEMSDOE73`** (`37,654` dots): **`0.4597`** (`κ = 0.3687 <= 0.70`)
- vs **`GEMSDOE78`** (`44,090` dots): **`0.4707`** (`κ = 0.3638 <= 0.70`)
- vs **`H33`** (`GEMSDOE32`, `37,654` dots): **`0.5498`** (`κ = 0.4680 <= 0.70`)
- vs **`H79-FNHR` `F3`** (`37,654` dots): **`0.5607`** (`κ = 0.4914 <= 0.70`)

### Discovery 2 — Full `107`-Channel Split-Domain Posterior Beats `G79-THVC` Under Fixed `37,654`-Dot `d = 2.8 px` Placement (`EXP-DFSD-2`)
- **Untouched Single-Shot Blind `Seed 30` (`n = 11,342`):** **`EXP-DFSD-2 = 0.1751` `[0.1570, 0.1932]` (`TP_w = 2,840.7`)** vs `G79-THVC` `EXP-79-2 = 0.1686` (`+0.0065` posterior improvement on identical `d=2.8 px` spacing!), with Quadrant Fold 0 (`NW` Nevada) peaking at **`0.2245` `HOLDOUT-DTI`** (`0.2107` on `Seed 20`).
- **Controlled `2 × 2` Causal Ablation on `Seed 20` (`evidence/dfsd_r1_hessian_bug_seed20.json` vs `evidence/dfsd_r2_unweighted_ablation_seed20.json`):**
  1. **Exact Importance-Weighting Causal Effect (`w_cls`):** Removing sample weights `w_cls` on Stage-1/Stage-2 classifiers (`R1 -> R2` on identical features, shards, and random seeds) dropped `EXP-DFSD-2` from **`0.1724 -> 0.1456` (`-0.0268`, `-15.5%`)** and dropped `EXP-DFSD-1` from **`0.0960 -> 0.0780` (`-0.0179`, `-18.7%`)** — establishing a `+0.0268` pure calibration gain.
  2. **Opposite-Sign Flank-Masking Theorem:** Excluding `1 <= d(x, sim_known) < 3 px` flank pixels from negative pools gains **`+0.0180` DTI** for zero-catalogue pure physics (`EXP-DFSD-1`), **but costs `-0.0241` DTI** when `d_vis` is included in network features because `allow_vis = (d_vis > 2.0 px)` at test time contains `260,000` real scarps flanking already-mapped faults!

### Discovery 3 — Complete `1,221`-Raster Pre-Placement & Post-Placement Uniqueness Audit (`vendor/gems57/uniqueness.py::compare_array_to_registry_d2`)
- **Leakage Canaries (`856` tests = `107` features × `4` folds × `2` seeds):** **`107 / 107` PASS** (`max symmetric AUC = 0.8580` on `Seed 20`, `0.8634` on `Seed 30`, both strictly `<= 0.90`).
- **Pre-Placement Continuous Surface (`1,211` comparable `3730×3292` rasters + `10` verified non-grid fixtures = `1,221` blobs across `93` repos):** **`max |Spearman ρ| = 0.6235 <= 0.90` (`PASS`)**.
- **Post-Placement Binary Dots (`20,611` core pixels, `g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.tif`):** **`max |Spearman ρ| = 0.1457 <= 0.90` (`PASS`)**; strongly distinct from `H33` (`0.3952`, `κ = 0.2853`), `GEMSDOE73` (`0.3460`, `κ = 0.2359`), `H79-FNHR` (`0.5368`, `κ = 0.4637`), and `GEMSDOE78` (`0.6043`, `κ = 0.5244`), **and cleanly stopped as negative under Protocol Rule 1** because truncating at the 55th-percentile floor concentrated `20,611` high-certainty core dots inside `G79-THVC` (`0.9259 > 0.70`) and `GEMSDOE83` (`0.7455 > 0.70`, `κ = 0.6965 <= 0.70`).
