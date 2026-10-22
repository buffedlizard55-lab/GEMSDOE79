# Session `7fdf94b3` Three-Pass Forensic Review & Verification Report (2026-10-22)

- **Active branch:** `arena/7fdf94b3-gemsdoe79`
- **Canonical lane:** `G79-THVC` (*Two-Stage Cross-Fitted Calibrated Classifier + Fixed-Penalty Lazy-Greedy Weighted-Coverage Placement with Endpoint-Cone Modulation*)
- **Canonical artifact:** `docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif` (`137,299 B`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`; `.zip` `102,628 B`, SHA-256 `dfee2552d9ba94bbb778f6da8e35b42ea7e5c55ff580dc5e9f9c809964b788f9`)
- **Decision status:** **`verdict: "negative"` — `OK TO DOWNLOAD: YES` · `OK TO SUBMIT: NO`**
- **New experimental runs / competition slots spent in this session:** `0 / 3` experiments, `0` competition slots

---

## 1. Executive Decision & Protocol Compliance

1. **Why no new TIF candidate was generated in this session (`0 / 3` experiments used):**
   - **Missing lane assignment (`IR-79-02`, `IR-79-170`, `AGENTS.md`):** Rule 1 of the Parallel-Run Protocol requires staying inside the single assigned method paragraph. The prompt contains no method paragraph (retaining template placeholders `[0.90]`, `[70%]`, `[3]`). Inventing an unassigned method or restarting any of the 17+ stopped lanes is prohibited by `AGENTS.md`.
   - **Pre-flight novelty gate refusal (`exit 2`):** `.venv/bin/python scripts/preflight_new_lane.py --restore` fails closed with exit code `2` (`impossible_under_literal_gate`) before any feature extraction or placement can begin.
   - **Three-tier Pigeonhole obstruction across the 1,128-entry registry (`IR-79-42`, `IR-79-98`, `IR-79-106`, `IR-79-116`, `IR-79-175`):**
     - **Tier 1 (Literal gate `literal_positive_gt_zero`):** `17GEMSDOE:E-proba-multiscale` (`ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) is strictly positive on all `5,167,373 / 5,167,373` finite footprint pixels (`100%` coverage), forcing `3-px overlap = 1.0000 > 0.70` for every nonempty prediction.
     - **Tier 2 (`budget-matched-v3` continuous-surface plateau degeneracy):** Contrary to the suggestion in `reports/session_review_d52085f3.md` (§1 & §7) that adopting `budget-matched-v3` (`Decision D-1` top-`k`) alone would clear the registry, four continuous plateau surfaces (`5GEMSDOE:gems-density-probe` `9cdae9b4…` and 3 `GEMSDOE48` surfaces) have tie-inclusive `budget_matched_dots` covering all `5,167,373` footprint pixels (`uncovered_allowed_pixels = 0`), still forcing `1.0000 > 0.70` overlap under `budget-matched-v3`.
     - **Tier 3 (Sparse binary lattice `dot_field` Pigeonhole obstruction):** `13GEMSDOE:r13-lattice-s5` (`c12533bb980234c3a706af641d4f1d514bbbe482714b2ebcac3b10f3e72a7a3f`) has `206,895` binary `{0, 1}` pixels (`4.00387% < DENSE_SUPPORT_FRACTION = 0.20`), so `budget-matched-v3` classifies it as a sparse `dot_field` and leaves it unreduced. Its 3-px Euclidean halo covers `5,160,724 / 5,167,373` (`99.871327%`) of the finite footprint (`6,649` uncovered cells) and **`5,099,871 / 5,106,385` (`99.872434%`)** of the off-catalogue allowed domain (`footprint & ~catalogue`, leaving only **`6,514 = 6,649 - 135`** uncovered off-catalogue cells). By the Pigeonhole Principle, **any** off-catalogue dot map with `N = 35,093` dots (`G79-THVC`) must overlap `r13-lattice-s5` on at least `(35,093 - 6,514) / 35,093 = 28,579 / 35,093 = 0.814379 > 0.70`, and any `H33`-budget map (`N = 37,654` dots) must overlap on at least `(37,654 - 6,514) / 37,654 = 31,140 / 37,654 = 0.827004 > 0.70`.
     - Only a prospective rule that explicitly excludes or chance-corrects saturated-halo / lattice priors (`halo_coverage > 0.70`, e.g., `informative-halo-v4` / `Decision D-3`) — plus resolution of the post-snapshot sibling collision `GEMSDOE83` (`0.7139 > 0.70`) — can clear a sparse candidate.

---

## 2. Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778`) Scored Highest Among the User-Listed GEMSDOE Sites — and Whether Higher Is Achievable

### 2.1 Score Provenance & Leaderboard Audit
| Quantity | Value | Provenance Label | Verified Evidence |
|---|---:|---|---|
| Competition `#1` public leaderboard (`xiaofanhu`) | `0.4413` | `PUBLIC-OBSERVATION` | Public leaderboard snapshot (`evidence/leaderboard_top25_2026-10-21.json`, `knowledge/official_sources.json`); `#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3894`. |
| User-mentioned `0.3195` | `0.3195` | `UNVERIFIED HISTORICAL REPORT` | Absent from all 200 public leaderboard entries (`IR-79-05`). |
| `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`) | `0.2778` | `UNVERIFIED HISTORICAL REPORT` | `GEMSDOE32` site labels the file `UNSCORED` (`IR-79-08`); no organizer submission-page receipt exists in the workspace (`registry/score_ledger.csv`). |
| `G79-THVC` vs `H33` (Seed 20, `n = 11,321` withheld positive px) | `0.1905` `[0.1741, 0.2069]` vs `0.0961` `[0.0831, 0.1090]` (`Δ = +0.0944` `[+0.0784, +0.1098]`) | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`) | `evidence/g79_thvc_holdout_seed20.json`, `run_card.json`. |
| `G79-THVC` vs `H33` (Seed 30, `n = 11,342` withheld positive px) | `0.1944` `[0.1774, 0.2126]` vs `0.0989` `[0.0854, 0.1128]` (`Δ = +0.0955` `[+0.0778, +0.1133]`) | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`) | `evidence/g79_thvc_holdout_seed30.json`, `run_card.json`. |

### 2.2 Exact Byte-Lineage & Conditional Metric Algebra of `H33`
- **Exact byte lineage (`knowledge/h33_review_e4a4422d.md`, `evidence/review_e4a4422d/h33_remeasurement.json`):**
  - Parent `D2.8` (`e134e0a39dd04bc6e5aa7cc232c3d3f7510b1fa143066e5082709076bd784b68`) has **`44,090`** binary `{0, 1}` dots (`r >= 8 px` spacing).
  - `H33` (`b6f8de9381fa2fdbf3e1dc2fd3efbc94726b40dfcbce22be7e097b68a3789d79`) has **`37,654`** binary `{0, 1}` dots.
  - `H33` is an exact subset of `D2.8` (`0` added pixels) formed by deleting the **`6,436`** `D2.8` dots satisfying `0 < Euclidean distance to existing_faults.tif <= 2 px` (`0` pixel disagreements across all `12,279,160` cells; `0` deleted pixels lay directly on `existing_faults > 0` because `D2.8` already excluded `d == 0`).
- **Why sparse r-spaced dots with near-catalogue exclusion outperform continuous surfaces and denser grids under DW-Tversky (`DTI = T / (0.2T + 0.2F + 0.8G + ε)`):**
  1. **300 m (`3 px`) max-pooling saturation:** Under the competition's asymmetric Distance-Weighted Tversky index ($\alpha = 0.2$ on false positives $F$, $\beta = 0.8$ on false negatives $G$), a single `1.0` dot saturates truth-recall credit $T$ within its `3 px` radius. Continuous probability surfaces (`17GEMSDOE`, `18GEMSDOE`, `GEMSDOE48`) or dense corridors accumulate massive false-positive denominator penalty $0.2F$ across millions of background pixels without adding recall $T$.
  2. **Conditional effect of deleting `6,436` near-catalogue dots (`0 < d_cat <= 2 px`):** Deleting `6,436` predictions changes $(T, F, G)$ to $(T - \Delta T, F - \Delta F, G + \Delta T)$ with $\Delta T + \Delta F = 6,436$, which increases `DTI` if and only if the deleted dots had low hidden-truth hit rate $\Delta T / 6,436$. Because organizer hidden test labels are secret, that inequality is a conditional algebraic explanation, not an organizer-verified proof (`IR-79-169`).
- **Is a higher score achievable?**
  - **On the local two-seed pooled holdout (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`):** **Yes, already achieved and verified.** Canonical `G79-THVC` (`35,093` binary dots) nearly doubles `H33`'s fold-fair holdout DTI (`0.1905` vs `0.0961` on Seed 20; `0.1944` vs `0.0989` on Seed 30) by replacing `H33`'s fixed $r=8\text{ px}$ ridge spacing with a calibrated 84-feature out-of-fold probability surface and fixed-penalty lazy-greedy 3-px coverage placement with catalogue endpoint-cone modulation.
  - **On the external DrivenData leaderboard:** Unproven without an organizer submission receipt, and **blocked from upload (`OK TO SUBMIT: NO`)** until the novelty gate is prospectively resolved.

---

## 3. Ranked Candidate Geological Hypotheses (3–5 Required)

Detailed specifications, physical citations, non-fault mimics, and falsification criteria are maintained in [`research/hypotheses_e4a4422d.md`](../research/hypotheses_e4a4422d.md) (`knowledge/review_e4a4422d_sources.json`):

1. **Rank 1 — `G79-CJX` (*Cross-Scale Contact-Junction Localization*; data-ready):**
   - **Layers:** Cached 20-band `training_features.tif` (Bouguer/isostatic gravity, RTP magnetics, DEM relief, conductive basement depth) + `external/derived_sgmc_faults_100m_u8.tif` + `external/gdr_wellspring_in_footprint.csv`.
   - **Physical signature & why unmapped:** Co-located inflection of 100 m topographic slope/scarp gradient with 1–3 km potential-field horizontal-gradient modulus (`HGM`) along lithologic contact junctions, capturing range-front / relay segments buried under thin alluvial fans that lack continuous Quaternary scarp traces in the USGS/INGENIOUS surface compilation.
   - **Non-fault mimic:** Unfaulted differential erosion along welded/non-welded tuff contacts or pediments.
2. **Rank 2 — `G79-BLC` (*Bilateral Lithology-Contrast Change-Point*; data-ready):**
   - **Layers:** Gravity and magnetic bands (`0`–`5`, `7`–`12`, `16`–`18`) + SGMC lithologic boundaries (`external/derived_sgmc_faults_100m_u8.tif`) + radiometric ratios (`external/geodawn_rad_u8.tif`).
   - **Physical signature & why unmapped:** Paired step-change across strike in density (gravity) and magnetization (RTP magnetics) combined with radiometric (`K/eTh`) discontinuity, detecting concealed intrabasin normal faults beneath playal/alluvial cover.
   - **Non-fault mimic:** Intrusive pluton margins or caldera ring-fracture lithologic boundaries without Quaternary fault slip.
3. **Rank 3 — `G79-RSS` (*Relief-Screened Structural Saddle*; data-ready):**
   - **Layers:** DEM elevation & multi-scale curvature + gravity vertical derivative (`Band 16`) + road-distance screen (`external/tiger_road_distance_m.tif`).
   - **Physical signature & why unmapped:** Relay-ramp structural saddles and step-over breaches where displacement transfers between echelon fault tips without a single high-relief scarp, screened against road/embankment artifacts.
   - **Non-fault mimic:** Fluvial wind gaps, pediment passes, or highway cut/fill corridors.
4. **Rank 4 — `G79-HFR` (*Paired Hydrothermal Recharge Residuals*; data-blocked — USGS heat-flow ZIP not yet acquired):**
   - **Layers:** Thermal spring/well locations (`external/gdr_wellspring_in_footprint.csv`), USGS Great Basin heat-flow compilation (`DOI:10.5066/P99DM03C`, not yet downloaded in workspace), and basement-depth gradient.
   - **Physical signature & why unmapped:** Advective thermal anomalies aligned with structural permeability conduits along blind fault tips/intersections that lack surface rupture.
   - **Non-fault mimic:** Stratigraphic aquifer outflow or lateral shallow groundwater flow down hydraulic gradient.
- **Note on archived `H80-MT-PHASE` (`IR-79-168`):** Marked unsupported as originally drafted because official USGS release `DOI:10.5066/P9TWT2LU` provides depth-integrated electrical conductance (surface layer `2–12 km`), not shallow (`500 m–3 km`) resistivity slices.

---

## 4. Validation Gates & Remediation Completed in Session `7fdf94b3`

### 4.1 Hard Validation Gates Verified (`scripts/validate_submission.py`, `scripts/verify_project.py`)
| Gate | Threshold | Canonical `G79-THVC` Measured Value | Status |
|---|---|---|---|
| Value range `[0, 1]` | `0.0 <= min <= max <= 1.0` | `min = 0.0`, `max = 1.0`, `mean = 0.00285793`, binary `{0.0, 1.0}` (`35,093` ones) | **PASS** |
| Finite values (no `NaN`/`Inf`) | `n_nan = 0`, `n_inf = 0` | `n_finite = 12,279,160`, `n_nan = 0`, `n_infinite = 0` | **PASS** |
| Grid / CRS / Transform / Band | `EPSG:32611`, `3730x3292`, `float32`, 1 band | `EPSG:32611`, `3730x3292`, `float32`, `[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]` | **PASS** |
| Footprint & Catalogue masking | `outside_footprint = 0`, `on_catalogue = 0` | `mass_outside_footprint = 0.0`, `on_catalogue_positive_pixels = 0` | **PASS** |
| Single-feature leakage canary | Symmetric `ROC AUC <= 0.90` on all 84 features x 2 seeds | Max symmetric AUC = `0.8036 <= 0.90` across all `168` feature-seed pairs | **PASS** |
| Registry Spearman correlation | `max |rho| <= 0.90` (surface & final dots) | Surface `0.7712 <= 0.90`, Final dots `0.1210 <= 0.90` | **PASS** |
| Registry 3-px forward overlap | `<= 0.70` across full registry | Literal full-registry max = **`1.0000 > 0.70`** (comparable sparse `<=50k` dots = `0.6844 <= 0.70`; post-snapshot `GEMSDOE83` = `0.7139 > 0.70`) | **BLOCKED (`OK TO SUBMIT: NO`)** |

### 4.2 Three-Pass Audit & Code Remediations (`IR-79-175`..`IR-79-177`)
- **Pass 1 (Implement & Verify):**
  - Restored and verified all `13/13` SHA-256-pinned data inputs via `.venv/bin/python scripts/restore_data.py --preserve-receipt` and restored both blocking registry witnesses (`374c88b1da2b803e2ed160de467fd71ae114010d.tif` and `5c1a159439735522659ee78969df3f34efddcdde.tif`).
  - Remediated **`IR-79-175`** in `scripts/measure_registry_halo.py` and `evidence/halo_saturation_*_1db538e6.json`: stripped machine-specific `/home/user/GEMSDOE79/` paths and added exact off-catalogue (`existing_faults.tif`) accounting proving `5,167,373 - 60,988 = 5,106,385` allowed cells and `6,649 - 135 = 6,514` uncovered off-catalogue cells (`5,099,871 / 5,106,385 = 0.9987243422`).
- **Pass 2 (Review for Bugs, Missing Guards & Edge Cases):**
  - Remediated **`IR-79-176`**: added fail-closed `enforce_open_lane` (`exit 2`, `"No files changed."`) guards to the 3 remaining unguarded archived CLI scripts (`scripts/run_experiment.py`, `scripts/finalize_negative.py`, `scripts/build_site_g79b.py`), updated stale `(H79-NHR)` comments to `(G79-THVC)` in `scripts/build_site_g79b.py` and `scripts/submission_status_g79b.py`, and registered all 3 scripts in `tests/test_lane_lifecycle.py` (`79` lifecycle tests passing).
  - Remediated **`IR-79-177`**: removed the duplicate `scikit-image` line in `requirements.txt` and added a duplicate-package regression check in `tests/test_session_070af0b6_audit.py`.
- **Pass 3 (Full Verification Against Original Request):**
  - Executed `.venv/bin/python scripts/build_site.py`, `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q` (`499 passed`), `.venv/bin/python scripts/verify_project.py` (`all_checks_passed: true`), and `.venv/bin/python scripts/check_site.py` (`passed: true`, 7 pages, 128 local links, 0 external assets).
