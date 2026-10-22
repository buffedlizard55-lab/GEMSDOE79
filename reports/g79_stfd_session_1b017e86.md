# Session Report (`arena/1b017e86-gemsdoe79`) — PhD Forensics of `H33`, Five Ranked Geological Hypotheses, Prospective `G79-STFD` (`0.2021` Dual-Seed Strict `LOQO` `HOLDOUT-DTI`), `1,273`-Raster `196`-Repo Audit, and Three-Pass Verification

**Date:** `2026-10-22` (UTC) | **Branch:** `arena/1b017e86-gemsdoe79` | **Active Lane:** `G79-STFD` (`status: closed`, `verdict: negative`)
**Canonical Repository Decision Line (`run_card.json`):** `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`
**Archived `G79-STFD` Decision Line (`run_card_stfd.json`):** `OK TO DOWNLOAD (RESEARCH ARCHIVE): YES. OK TO SUBMIT: NO.`

---

## 1. Evidence-Class Discipline & PhD Forensic Analysis of `H33` (`0.2778` `ORGANIZER-CONFIRMED`)

Every score reported in this document carries an explicit, non-interchangeable evidence label:
- **`ORGANIZER-CONFIRMED` / `PUBLIC-OBSERVATION`:** Live public DrivenData #306 competition scores evaluated on the organizers' undisclosed hidden Nevada geothermal fault test set (`https://www.drivendata.org/competitions/306/gems-geothermal-faults/leaderboard/`):
  - **`0.2778` (`ORGANIZER-CONFIRMED`):** Achieved identically by `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`GEMSDOE32`, `37,654` non-zero `100 m` pixels = `0.7287%` of the `5,167,373`-cell active footprint; SHA-256 `61f2da65...`) and replicated identically wherever those exact `37,654` coordinates were re-uploaded.
  - **`0.4413` (`PUBLIC-OBSERVATION`):** Verified `#1` public leaderboard score (`xiaofanhu`, `#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3894`, `#50 sam35 = 0.2804` as of `2026-10-22`).
  - **`0.3195` (`TARGET BENCHMARK`):** Intermediate competition milestone cited in the project prompt (`+0.0417` above `H33`'s `0.2778`, `~25th` place on the live leaderboard).
- **`HOLDOUT-DTI` (`gems57-pooled-hide-v2`):** Strict 4-fold Leave-One-Quadrant-Out (`LOQO`) spatial cross-validation on `data/raw/training_features.tif` + `known_faults` with `22%` withheld fault components (`11,321` withheld positive pixels on Seed 20; `11,342` on Seed 30; `300 m` triangular kernel, $\alpha = 0.2$, $\beta = 0.8$).

### Why `H33` Reaches `0.2778` (`ORGANIZER-CONFIRMED`) — And Why ItPlateaus Below `0.3195`–`0.4413`

1. **Exact alignment with the asymmetric DTI objective (`alpha = 0.2`, `beta = 0.8`, `r = 300 m`):**
   $$\text{DTI} = \frac{\text{TP}_w}{\text{TP}_w + 0.2\,\text{FP}_w + 0.8\,\text{FN}_w}$$
   Because false negatives are penalized $4\times$ more heavily than false positives ($\beta / \alpha = 4$) and every hit within $300\text{ m}$ receives linear distance weight $w(d) = \max(0, 1 - d / 300\text{ m})$, emitting dense continuous probabilities across `5.17M` cells destroys `DTI` via $0.2\,\text{FP}_w$, while ultra-conservative maps collapse via $0.8\,\text{FN}_w$. `H33` selects `37,654` spaced `1.0` dots (`~205 m` minimum separation) right near the stationary fractional trade-off point where marginal $\Delta \text{TP}_w / \Delta \text{FP}_w \approx \lambda(\theta) = \frac{0.2\,\theta}{1 - 0.2\,\theta}$.
2. **Tip-bridge and step-over concentration around mapped traces (`USGS Qfaults`, DOI `10.5066/P9BCVRCK`; `INGENIOUS`, DOI `10.15121/1881483`):**
   Direct spatial inspection of `H33`'s `37,654` dots reveals that **`86.4%` lie within `1.5 km` (`15 px`) of mapped faults**, capturing unmapped relay ramps, en-echelon step-overs, and range-front along-strike continuations where surface alluvial fans obscure short trace segments.
3. **Why `H33` is identical (`0.2778`) across sibling `GEMSDOE` listings:**
   `H33` is a deterministic fixed GeoTIFF (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`); re-uploading identical pixel coordinates (with external `NaN` replaced by `0.0` outside footprint) produces the exact same `TP_w`, `FP_w`, and `FN_w` against the fixed hidden organizer ground truth (`IR-79-191`).
4. **The three physical ceilings trapping `H33` at `0.0961 / 0.0989` strict `LOQO` `HOLDOUT-DTI` (`0.2778` `ORGANIZER-CONFIRMED`):**
   - **Zero seismic-swarm vs background mainshock separation:** `H33` ignores the joint ratio between INGENIOUS declustered/independent seismicity (`ieq_n100a15`) and dependent/swarm seismicity (`deq_n100a15`) coupled with GPS transtensional dilatation (`geod_dilaterate > 0` $\times$ `geod_shearrate`, UNR NGL MIDAS DOI `10.1029/2018EO104623`) that illuminates blind geothermal fluid conduits under playa fill (Faulds & Hinz, 2015).
   - **Unpolarized symmetric fault halos & survey seam artifacts:** `H33` places symmetric halos on both footwall and hanging wall instead of projecting dip-slip normal splays into the deepening alluvial hanging wall ($+\nabla\text{depth\_to\_base\_surf}$), and suffers cross-block amplitude shifts across USGS GeoDAWN radiometric/magnetic acquisition boundaries (DOI `10.5066/P93LGLVQ`) and 1 m LiDAR vs 10 m 3DEP coverage seams (`lidar_present`).
   - **Pleistocene shoreline & mine-blast false positives:** Unvetoed scarp extractors fire heavily along equipotential Lake Lahontan (`~1,330 m`) / Lake Bonneville highstand benches and open-pit mining benches (`BLM MLRS`).

---

## 2. Summary of the Five Untried Geological Hypotheses (`research/hypotheses_1b017e86.md`)

Full mathematical derivations, layer tables, non-fault mimics, and official data citations are recorded in [`research/hypotheses_1b017e86.md`](../research/hypotheses_1b017e86.md):

| Rank | Code | Physical Hypothesis & Target Transform | Expected Gain vs Cost | Status |
|---:|---|---|---|---|
| **1** | **`H1-STFD` (`G79-STFD`)** | **Seismo-Tectonic Fluid-Dilatancy, Hanging-Wall Throw Polarity & Survey-Quantile Domain-Debiased Dinkelbach Stack (`119` features: `97` static + `22` mechanics)** — `seis_swarm_log_excess`, `geod_transtension_obliquity`, `grav_bdepth_concordance`, `scarp_modality_qnorm`, `net_tip_x_swarm_strain`, `net_hangingwall_dip_proj`, `net_junction_hydro_conduit` + observable order-statistic quadrant calibration + unit-consistent Dinkelbach emission. | **Highest (`+0.095` to `+0.115` `HOLDOUT-DTI` over `H33`; breaks `0.200` strict `LOQO` barrier)** | **Implemented & Sealed (`0.1928 / 0.2114`, Mean `0.2021` — #1 in `GEMSDOE79`)** |
| 2 | `H2-EULER3D` | 3D Potential-Field Euler Deconvolution Structural Index ($N \in [0, 0.5]$ contact vs $N \ge 1.5$ pipe/sill) & Upward-Continuation Depth-Persistence Ratio across `iso_grav_anom` + notched `tmi` (`GeoDAWN`, DOI `10.5066/P93LGLVQ`). | High (`+0.008`–`+0.015` incremental `HOLDOUT-DTI`), Medium cost | Deferred (clean next orthogonal physics module) |
| 3 | `H3-KNICK-STREAM` | Tectonic Stream-Profile Steepness Jump ($\Delta k_{sn}$) & Drainage Divide Asymmetry across 3DEP 10 m `dem10` channels (`DOI 10.5066/P937PN4Z`) detecting blind range-front uplift across eroded alluvial fans without preserved surface scarps. | Moderate-High (`+0.006`–`+0.012`), Medium cost | Deferred |
| 4 | `H4-MT-UPFLOW` | 3D Magnetotelluric Phase-Tensor Skew & Sub-Clay Conductive Upflow Plume Edge (`USGS/USArray MT` + `cond_surf`) separating sub-vertical hydrothermal fault feeders ($<10\ \Omega\cdot\text{m}$ roots) from flat smectite playa lakes. | Moderate (`+0.005`–`+0.011`), Medium-High cost | Deferred |
| 5 | `H5-INSAR-CREEP` | ARIA/OPERA Sentinel-1 Ascending/Descending LOS Vertical Subsidence vs Horizontal Transtensional Creep Decomposition (`NASA ASF OPERA`). | Speculative-Moderate, High external ingest cost (`~2.5 GB`) | Deferred |

---

## 3. Prospective `G79-STFD` Results (`run_card_stfd.json`, `gems57-pooled-hide-v2`)

### 3.1 Single-Feature Leakage Canary (`evidence/stfd/canary_238_tests.json`)
- **Features tested:** `119` (`97` domain-debiased static physics + `22` fold-visible network mechanics) $\times$ `2` seeds = **`238` single-feature tests**.
- **Result:** **PASSED (`238 / 238 <= 0.90`)** — maximum symmetric ROC-AUC = `0.789678` on Seed 20 and `0.804721` on Seed 30 (`net_tip_fwd_35px`). Top zero-catalogue standalone features include `grav_hgm_block_qnorm` (`0.5732`), `scarp_modality_qnorm` (`0.5717`), `grav_bdepth_concordance` (`0.5650`), `piedmont_rel_height_4km` (`0.5520`), and `geod_transtension_obliquity` (`0.5491`).

### 3.2 Dual-Seed Strict 4-Fold `LOQO` `HOLDOUT-DTI` Progression (`<= 3` Experiments)

| Experiment / Control | Placed Dots | Seed 20 `HOLDOUT-DTI` (95% CI, `11,321` px) | Seed 30 `HOLDOUT-DTI` (95% CI, `11,342` px) | Dual-Seed Mean | Paired $\Delta$ vs `H33` (Seed 20 / Seed 30) |
|---|---:|---:|---:|---:|---:|
| **`EXP-STFD-3` (`G79-STFD` Dinkelbach)** | `39,867 / 39,930` | **`0.1928` (`[0.1737, 0.2117]`)** | **`0.2114` (`[0.1914, 0.2306]`)** | **`0.2021`** | **`+0.0967` / `+0.1125` (`CI > 0`)** |
| **`EXP-STFD-2` (`119`-ch Uniform `37,654`)** | `37,654` | **`0.1923` (`[0.1755, 0.2082]`)** | **`0.2110` (`[0.1909, 0.2303]`)** | **`0.2016`** | **`+0.0962` / `+0.1121` (`CI > 0`)** |
| **`EXP-STFD-1` (`97`-ch `100%` Zero-Catalogue Physics)** | `37,654` | **`0.1090` (`[0.0865, 0.1314]`)** | **`0.1276` (`[0.1066, 0.1500]`)** | **`0.1183`** | **`+0.0129` / `+0.0287`** |
| Canonical `G79-THVC` (`run_card.json`) | `35,093` | `0.1905` (`[0.1743, 0.2063]`) | `0.1944` (`[0.1782, 0.2102]`) | `0.1924` | `+0.0944` / `+0.0955` |
| Archived `G79-CSKD` (`IR-79-200`) | `42,000` | `0.1781` (`[0.1605, 0.1950]`) | `0.2145` (`[0.1965, 0.2323]`) | `0.1963` | `+0.0820` / `+0.1156` |
| Archived `G79-CSMD` (`IR-79-203`) | `35,600` | `0.1629` (`[0.1476, 0.1781]`) | `0.1749` (`[0.1585, 0.1909]`) | `0.1689` | `+0.0669` / `+0.0760` |
| `C2_h33_analogue_foldfair` (`H33`) | `38,802 / 38,829` | `0.0961` (`[0.0828, 0.1095]`) | `0.0989` (`[0.0852, 0.1130]`) | `0.0975` | `0.0000` / `0.0000` |
| `C1_fabric_offset_E1_placed` | `37,654` | `0.0441` (`[0.0375, 0.0511]`) | `0.0440` (`[0.0364, 0.0518]`) | `0.0441` | `-0.0520` / `-0.0549` |
| `C0_random_B37654` | `37,654` | `0.0425` (`[0.0374, 0.0473]`) | `0.0463` (`[0.0415, 0.0506]`) | `0.0444` | `-0.0535` / `-0.0526` |

- **Detached strand recovery (`>= 400 m` isolated from all visible traces):** `0.0394` on Seed 20 (`+62.8%` over `H33`'s `0.0242`) and `0.0417` on Seed 30 (`+80.1%` over `H33`'s `0.0232`).
- **Live full-catalogue importance share:** New `STFD` seismo-tectonic channels contribute **`15.49%` of total Stage-1 split gain**, led by **`net_tip_x_swarm_strain` (`#5` overall at `6.27%`)**, **`piedmont_rel_height_4km` (`#11` at `1.88%`)**, and **`geod_transtension_obliquity` (`1.11%`)**.

### 3.3 `1,273`-Raster Uniqueness Audit Across All `196` `buffedlizard55-lab` Repositories (`evidence/stfd/novelty_196repos_audit.json`)
- **Pre-placement surface max `|Spearman|`:** **`0.6218 <= 0.90`** (`GEMSDOE82:artifacts/surface_h82.tif`) — **PASS**.
- **Post-placement dots max `|Spearman|`:** **`0.1092 <= 0.90`** (`57GEMSDOE:gems57-relative-strand-surface`) — **PASS**.
- **External cross-repo sparse `<= 75,308 px` 3-px overlap (`957` external sparse rasters across all `195` non-self repos):** **`0` duplicates `> 0.70` (`max = 0.6981 <= 0.70` on `60GEMSDOE:calib_h28ridge_01839.tif`; `GEMSDOE83 = 0.6544 <= 0.70`; `GEMSDOE78 dualcover = 0.6004 <= 0.70`; `GEMSDOE78 dink = 0.5673 <= 0.70`; `H33 = 0.4316 <= 0.70`)**!
- **Why `verdict = "negative"` / `OK TO SUBMIT: NO` is strictly maintained:**
  1. Unamended literal `vendor/gems57/uniqueness.py` evaluates `1.0000 > 0.70` against pinned `5,167,373`-pixel dense surfaces (`17GEMSDOE:E-proba-multiscale`) and `0.9983 > 0.70` against `13GEMSDOE:r13-lattice-s5` (`chance_corrected_overlap = +0.0416` and `-0.3575`, non-duplicates under `D2`), AND
  2. Within `GEMSDOE79`'s own local research archives, three unsubmitted `DO-NOT-SUBMIT` sibling maps (`G79-CSMD` `0.8274`, `G79-CSKD` `0.7600`, `G79-THVC` `0.7388`) share core strict-`LOQO` tip-bridge loci. Under `AGENTS.md` §3–§6, local agents never self-grant exemptions without human coordinator sign-off.

---

## 4. Three-Pass Verification Log (`Pass 1`, `Pass 2`, `Pass 3`)

### Pass 1 — Full Prospective Implementation, Execution & Packaging
- Restored and SHA-256 verified all competition inputs, external official datasets, and `1,316` unique `.tif` files across all `196` `buffedlizard55-lab` GitHub repositories (`161` live post-delta sibling rasters added to `.cache/live_sibling_delta/`).
- Locked `registry/preregistration_g79_stfd.json` (`SHA-256 = 4d62ae4c25c638fe5e24a40f279623e05c995503a1684cb81f47f56ce4e90a75`), ran all `238` single-feature leakage canary checks (`passed`), completed prospective Seed 20 (`0.1928`), blind Seed 30 (`0.2114`), and full-catalogue `live` inference (`41,000` dots), audited uniqueness across all `1,273` comparable rasters, packaged `gems79-stfd-dinkelbach-41000dots-20261022-6e022dbe-zeros-DO-NOT-SUBMIT.{tif,zip,json}` via `vendor/gems57/submission_writer.py`, validated format (`all_checks_passed: true`) via `vendor/gems57/validate.py`, sealed `run_card_stfd.json`, and confirmed `scripts/run_stfd.py` exits with code `2` (`LaneClosedError`).

### Pass 2 — Forensic Bug & Edge-Case Audit and Remediation
- **Bug 2A (`IR-79-208` — `training_features.tif` interior `FLT_MAX` overflow):** Caught `RuntimeWarning: overflow encountered in multiply` during initial static feature construction caused by `3,061` interior `-3.4028235e38` sentinels inside `footprint`; fixed via `_clean_tf` (`np.isfinite(raw) & (np.abs(raw) < 1e10)`) + `float64` unit-vector normalization (`0` runtime warnings across all stages).
- **Bug 2B (`IR-79-199` / OOM mitigation):** Caught `0 B`-swap cgroup RSS pressure (`3.8 GiB`) during 4-draw Stage-1/Stage-2 transition; offloaded inner draw mechanics matrices to disk `.npy`, converted pairwise OOF cache to `float16`, and freed training shards in place prior to Stage 2 (`peak RSS = 2,386.8 MB` on live run).
- **Bug 2C (`IR-79-209` — Collar support mismatch & background-sum calibration inversion):** First Seed-20 pass revealed `raw_p2 = 0.1278` (`F0 = 2,411` dots vs `F2 = 15,243` dots) because filtering `d_sim_fp > 3.0` in Stage 1 while keeping `act_fp` (`d_sim_fp > 0`) in Stage 2 caused collar blowup, and summing `p_2d` over all `1.29M` background noise cells inverted quadrant calibration. Preserved the pre-bugfix diagnostic receipt in `evidence/stfd/diagnostic_pre_collar_tail_bugfix_seed20.json`, restored Stage-1/Stage-2 domain identity and observable order-statistic tail calibration, re-verified Seed 20 (`0.1928`), and ran `Seed 30` (`0.2114`) completely blind with zero edits.
- **Bug 2D (`IR-79-210` — ZIP SHA-256 desynchronization in `run_csmd.py`):** Avoided `run_csmd.py`'s post-writer ZIP rewrite bug so `zip_sha256` (`30891159...`) in sidecar `.json`, `run_card_stfd.json`, and `docs/run-card-stfd.json` matches on-disk `.zip` byte-for-byte with `0644` permissions.
- **Bug 2E (Figure clipping & colormap inversion):** Visual inspection of rendered PNGs caught inverted `Greys` dark background on `stfd_live_discovery_map.png` and edge title clipping on `stfd_novelty_and_features.png`; fixed and re-verified visually.

### Pass 3 — End-to-End Prompt & Governance Compliance Polish
- Verified all `vendor/gems57/` files (`template_pin.json`), canonical `run_card.json` / `docs/downloads/` (`d3db2e95...`), verbatim `## Original project prompt` in `README.md`, single-line 4-pipe `IR-79-*` rows in `reports/irregularities.md` with HTML parity in `docs/irregularities.html`, zero `/home/user` host paths across tracked files, `0644` artifact permissions, full `pytest` suite, `scripts/verify_project.py`, `scripts/check_site.py`, and Node browser QA tests (`tools/browser-qa/download-check.test.cjs`).
