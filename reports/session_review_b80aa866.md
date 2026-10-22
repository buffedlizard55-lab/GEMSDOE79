# Session Review `b80aa866` — Three-Pass Scientific & Repository Audit (`arena/b80aa866-gemsdoe79`)

**Date:** 2026-10-22 (UTC)  
**Branch:** `arena/b80aa866-gemsdoe79`  
**Canonical Research Deliverable:** `docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`  
- **TIFF SHA-256:** `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2` (`137,299` bytes, `35,093` positive pixels `{0.0, 1.0}`, `EPSG:32611`, `3730 × 3292`, affine `[100, 0, 243350, 0, -100, 4508550]`, `0` NaN, `nodata=None`)
- **ZIP SHA-256:** `dfee2552d9ba94bbb778f6da8e35b42ea7e5c55ff580dc5e9f9c809964b788f9` (`102,628` bytes, 1 member matching TIFF SHA-256)
- **Automated Gate Disposition:** **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** (`verdict: "negative"`, `ok_to_download: true`, `ok_to_submit: false`, `submission_slots_used: 0`)

---

## 1. Executive Summary & Answers to the Research Brief

### 1.1 Can a new unique GeoTIFF with `OK TO SUBMIT: YES` be generated under the literal protocol?
**No.** Both the pre-lane preflight (`scripts/preflight_new_lane.py --restore`, exit `2`) and the post-export selector (`scripts/select_submission.py`, exit `2`) fail closed for two independent reasons:
1. **No lane-specific method paragraph:** The session prompt contains the shared six-rule `PARALLEL-RUN PROTOCOL` header (`1. LANE. Your lane is the single method paragraph below. Stay inside it.`) without a delimited lane method paragraph below it (`AGENTS.md` §3).
2. **Three-tier mathematical obstruction under the unchanged literal 3-px forward-overlap gate (`forward_overlap_3px <= 0.70`):**
   - **Tier 1 (Continuous space-filling prior):** `17GEMSDOE:docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` (blob `374c88b1da2b803e2ed160de467fd71ae114010d`, SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) is strictly positive (`0.00046`–`0.98412`) on all `5,167,373` finite footprint cells (`5,106,385` off-catalogue allowed cells), forcing `forward_overlap_3px = 1.0000 > 0.70` for every nonempty candidate.
   - **Tier 2 (Discrete dot-field prior):** Even under `budget-matched-v3` (which reduces only continuous surfaces with support fraction `> 0.20`), `13GEMSDOE:docs/downloads/13gems_20261001_r13-lattice-s5_v2_zerofill.tif` (blob `5c1a159439735522659ee78969df3f34efddcdde`, SHA-256 `c12533bb980234c3a706af641d4f1d514bbbe482714b2ebcac3b10f3e72a7a3f`) is a discrete dot field (`206,895` positive pixels, support fraction `0.04004 <= 0.20`) whose Euclidean 3-px halo covers **`5,099,871 / 5,106,385 = 0.998724`** of off-catalogue allowed cells (and `5,160,724 / 5,167,373 = 0.998713` of all finite footprint cells), leaving only **`6,514`** uncovered off-catalogue cells (`6,649` including `135` on-catalogue cells). Any candidate with `K >= 21,714` off-catalogue dots (including `K = 35,093` or `K = 37,654`) satisfies $\text{overlap} \ge (K - 6{,}514)/K > 0.70$ by the Pigeonhole Principle (`evidence/review_b80aa866/halo_domain_reconciliation.json`).
   - **Tier 3 (Sparse-prior crowding vs holdout skill):** Across the 18+ evaluated `GEMSDOE79` lanes (including `G79-CJX`, `0.1041 / 0.1063`), post-hoc uniqueness capping (`G79B-SDPT`) cost `-0.0180` to `-0.0196` `HOLDOUT-DTI`, dropping below the `H33` fold-fair control, while lanes clearing Amendment D-2 (`H79-MRND`, `HOLDOUT-DTI` `0.1044 / 0.1236`) remain `-0.0861 / -0.0708` below canonical `G79-THVC` (`0.1905 / 0.1944`).

### 1.2 Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778`, `USER-REPORTED`) outperformed prior GEMSDOE submissions
Re-verified directly from restored registry blobs in `evidence/review_b80aa866/h33_lineage_verification.json`:
- `D2.8` (`GEMSDOE25__dotted-h19-5-d2-8.tif`, blob `bfb7e86d046dd178c3d6ab60522861b5464dd420`, SHA-256 `3e78737f0da8dd2ca66cc6caac0ce8eeefcd6715707f8d1bd3091845cd9bcc30`) has **`44,090`** binary dots inside the footprint.
- `H33` (`GEMSDOE32__h33-2-b2-zeros.tif`, blob `17a76895f68174cc93f3cb1597d25686f6d6bc67`, SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) has **`37,654`** binary dots inside the footprint.
- Set difference: `H33` equals `D2.8` after deleting the **`6,436`** off-catalogue dots within Euclidean distance $0 < d_{\text{cat}} \le 2\text{ px}$ (`200 m`) of the visible catalogue (`existing_faults.tif`), with **`0` pixel disagreements** across all `12,279,160` raster cells.
- Under the competition's asymmetric distance-weighted Tversky index ($\alpha = 0.2$ on false positives $F$, $\beta = 0.8$ on false negatives $G$, triangular kernel $k(d) = \max(0, 1 - d/300\text{ m})$), deleting near-catalogue dots removes false-positive mass $b = \Delta F$ while losing minimal true-positive mass $a = \Delta T$, increasing DTI whenever $0.2\,T\,b > a\,(0.2\,F + 0.8\,G + \varepsilon)$. Note that `0.2778` (like `0.3195` in the prompt and `0.4413` observed on the public leaderboard) is not linked to local bytes by an organizer submission-page receipt (`knowledge/h33_review_e4a4422d.md`).

### 1.3 Canonical `G79-THVC` Holdout Evidence (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`)
All holdout numbers are inherited from `evidence/g79_thvc_results.json` (`official_evaluate_all`, 1,000-draw 20 km spatial-cluster bootstrap; zero new experiments run in this session):

| Seed | Withheld Positives | `G79-THVC` `HOLDOUT-DTI` [95% CI] | `H33` Fold-Fair Control `HOLDOUT-DTI` [95% CI] | Paired $\Delta$ (`G79-THVC - H33`) [95% CI] | Max Single-Feature Canary AUC (84 features, gate $\le 0.90$) |
|---|---:|---|---|---|---|
| **20** | `11,321` | `0.1905` `[0.1741, 0.2069]` | `0.0961` `[0.0831, 0.1090]` | `+0.0944` `[+0.0784, +0.1098]` | `0.78961` (**PASS**) |
| **30** | `11,342` | `0.1944` `[0.1774, 0.2126]` | `0.0989` `[0.0854, 0.1128]` | `+0.0955` `[+0.0778, +0.1133]` | `0.80360` (**PASS**) |

### 1.4 Ranked Prospective Geological Hypotheses (`research/hypotheses_e4a4422d.md`)
1. **Rank 1 — `G79-CJX` (Cross-Scale Contact-Junction Localization, Tested Negative in `PR #102`):** Pairs GeoDAWN reduced-to-pole magnetic gradient (`rtp`, band 2) with INGENIOUS isostatic gravity horizontal gradient (`iso_grav_anom`, band 13) to detect buried basin-bounding contact junctions (mimic: undeformed intrusive stocks/caldera ring dikes). Tested in `PR #102` (`run_card_cjx.json`): pure catalogue-free edges/junctions (Exps 1–2) scored `0.0046 / 0.0056` and `0.0045 / 0.0053` (below random), while tip-steered `CJX_v3_tip` (Exp 3) scored `0.1041 / 0.1063` `HOLDOUT-DTI` (`-0.0864 / -0.0881` below `G79-THVC`), failing `G3_holdout` and `G4_novelty` (`verdict: "negative"`, `ok_to_submit: false`).
2. **Rank 2 — `G79-BLC` (Bilateral Lithology-Contrast Change-Point):** Measures cross-strike step-change asymmetry across SGMC lithologic unit contacts (`derived_sgmc_faults_100m_u8.tif`) paired with radiometric K/eTh/eU ratios (`geodawn_rad_u8.tif`) to capture unmapped range-front and intrabasin contacts obscured by thin alluvial veneers (mimic: depositional alluvial-fan aprons).
3. **Rank 3 — `G79-RSS` (Relief-Screened Structural Saddle):** Combines 100 m topographic saddle curvature with gravity gradient (`cba_grav_anom` / `iso_grav_anom`) across low-relief relay zones where scarp-only detectors (`H33`) have zero sensitivity (mimic: fluvial drainage divides and pediment passes).
4. **Rank 4 — `G79-HFR` (Paired Hydrothermal Recharge/Upflow Residuals, Data-Blocked):** Uses Great Basin conductive heat-flow residuals (USGS ScienceBase DOI `10.5066/P9BZPVUC`, metadata verified in `knowledge/review_e4a4422d_sources.json`; dataset ZIP not mirrored in `registry/data_manifest.json`) to locate blind range-front/playa hydrothermal upflow conduits (mimic: lateral shallow aquifer outflow plumes).

---

## 2. Three-Pass Audit & Code Remediation Performed in Session `b80aa866`

### Pass 1 — Autonomous Data Restoration, Feature Reproduction, and Baseline Verification
- Merged `origin/main` (`9469cf1`, through PR #102) into `arena/b80aa866-gemsdoe79`.
- Restored and SHA-256-verified all **13/13** pinned manifest inputs via `bash scripts/download_competition_data.sh` and `.venv/bin/python scripts/restore_data.py --preserve-receipt` without mutating `data/restore_receipt.json`.
- Reproduced and SHA-256-verified all **10/10** deterministic `.cache/g79/*.npy` feature arrays via `.venv/bin/python scripts/prepare_data.py --reproduce` matching `evidence/feature_cache.json` bit-for-bit (`evidence/review_b80aa866/agents_and_lifecycle_audit.json`).
- Independently restored registry blobs `374c88b1da2b803e2ed160de467fd71ae114010d` (`17GEMSDOE`), `5c1a159439735522659ee78969df3f34efddcdde` (`13GEMSDOE`), `17a76895f68174cc93f3cb1597d25686f6d6bc67` (`H33`), and `bfb7e86d046dd178c3d6ab60522861b5464dd420` (`D2.8`) and re-verified `H33` vs `D2.8` byte lineage (`evidence/review_b80aa866/h33_lineage_verification.json`).

### Pass 2 — Defect Discovery & Remediation (`IR-79-188`..`IR-79-190`)
1. **`IR-79-188` (`AGENTS.md` broken paths & mismatched IR citations):**
   - Fixed `AGENTS.md` line 14 (`run_card_etp.json` and `IR-79-151` $\rightarrow$ `archive/g79_etp_incoming_45998a01/run_card_etp_root.json` & `archive/g79_etp_incoming_45998a01/evidence/run_card_etp.json`, `IR-79-147 / IR-79-158`).
   - Fixed `AGENTS.md` line 17 (`IR-79-152` $\rightarrow$ `IR-79-155 / IR-79-162` for `G79-CFSKD`).
   - Fixed `AGENTS.md` non-existent `archive/h79_ff/` and `archive/g79b_sdpt_a3/` $\rightarrow$ `archive/h79_ff_1de1617f/` (`evidence/ff/`) and `archive/g79b_sdpt_67557396/` (`run_card_g79b.json`), and added omitted closed lanes `H80-PILOTS`, `H79-FF1`, and `H79-BQA`.
2. **`IR-79-189` (Remaining unguarded closed-lane CLI scripts: `audit_g79b.py` and `build_cjx_page.py`):**
   - Added `enforce_open_lane` (`src/gems79/lifecycle.py`) to `scripts/audit_g79b.py` (`G79B-SDPT`) and `scripts/build_cjx_page.py` (`G79-CJX`).
   - Registered both scripts in `tests/test_lane_lifecycle.py` (`69` parametrized CLI commands / `87` lifecycle tests passing).
3. **`IR-79-190` (Forensic audit of `G79-CJX` in `local_gems79_concurrent_lanes_audit` and `novelty_sparse_diagnostic.json` halo-domain reconciliation):**
   - Added `G79-CJX_archived` (`artifacts/cjx/g79-cjx-tipjunction-37654dots-20261022T153333Z-6a9bf2a2-zeros.tif`, SHA-256 `a422d9a0...`, `overlap_vs_g79_thvc_canonical = 0.511871`, `overlap_vs_13gemsdoe_r13_lattice_s5 = 0.989085`) to `LOCAL_GEMS79_LANE_SPECS` in `scripts/audit_post_snapshot_siblings.py` and synchronized `evidence/post_snapshot_sibling_audit.json` and `docs/evidence/post_snapshot_sibling_audit.json`.
   - Documented in `evidence/review_b80aa866/halo_domain_reconciliation.json` why `evidence/cjx/novelty_sparse_diagnostic.json` reported `halo_coverage_allowed = 0.998713` (`5,160,724 / 5,167,373` full finite footprint instead of `5,099,871 / 5,106,385 = 0.998724` off-catalogue allowed domain) and unclamped `chance_corrected_overlap = -7.482897`.

### Pass 3 — Full Verification & Regression Suite
- Added `tests/test_session_b80aa866_audit.py` and rebuilt `docs/` via `.venv/bin/python scripts/build_site.py`.
- All pytest tests pass (`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q`).
- `.venv/bin/python scripts/verify_project.py` exits `0` (`all_checks_passed: true`, 35/35 checks).
- `.venv/bin/python scripts/check_site.py` exits `0` (`passed: true`, `submit: false`).
- `.venv/bin/python scripts/submission_status.py`, `.venv/bin/python scripts/select_submission.py`, and `.venv/bin/python scripts/preflight_new_lane.py --restore` all exit `2` (`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`).
