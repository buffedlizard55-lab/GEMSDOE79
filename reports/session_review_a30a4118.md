# Session `a30a4118` Three-Pass Scientific, Forensic & Engineering Review (`arena/a30a4118-gemsdoe79`)

- **Review date (UTC):** `2026-10-22`
- **Active canonical lane:** `G79-DCMS` (*Dip-Coupled Multi-Scale Scarp, Bedrock Reactivation & Hydrothermal Conduit Network*)
- **Automated decision:** **`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`** (`verdict: "negative"`, `submission_slots_used: 0`)
- **Canonical GeoTIFF:** [`docs/downloads/g79-dcms-dipcoupled-20261022-59a36344-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/g79-dcms-dipcoupled-20261022-59a36344-zeros-DO-NOT-SUBMIT.tif) (`140,260` bytes, `36,404` positive pixels = `0.7045%` of footprint, SHA-256 `d281189e16ae24f344dfcd15c58a051ae6f57cd964c34808ff2eb6e65d85eba9`)
- **Canonical single-TIFF ZIP:** [`docs/downloads/g79-dcms-dipcoupled-20261022-59a36344-zeros-DO-NOT-SUBMIT.zip`](../docs/downloads/g79-dcms-dipcoupled-20261022-59a36344-zeros-DO-NOT-SUBMIT.zip) (`105,863` bytes, SHA-256 `9875adb70a81a6a5d0b956b853e1c4f8d2dda6c78dda491a194918320e673c02`)
- **Submission name (59/140 chars):** `g79-dcms-dipcoupled-20261022-59a36344-zeros-DO-NOT-SUBMIT`
- **Submission note (96/140 chars):** `GEMSDOE79 G79-DCMS DO-NOT-SUBMIT: dip-coupled+10m3DEP+SGMC+hydro 2-stage + Dinkelbach (36404 px)`
- **Prior canonical lane preserved byte-for-byte:** [`archive/g79_thvc_33e1f8ec/run_card_thvc.json`](../archive/g79_thvc_33e1f8ec/run_card_thvc.json) and [`archive/g79_thvc_33e1f8ec/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`](../archive/g79_thvc_33e1f8ec/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif) (`SHA-256: d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`)

---

## Pass 1 — Scientific, Geological & Mathematical Integrity Audit

### 1.1 Exact Metric Forensics: Reconciling `0.2778`, `0.3195`, and `0.4413`
Under the official DOE Geothermal Exploration Machine-learning Challenge (GEMS) Distance-Tolerant Intersection metric (`DTI(alpha=0.2, beta=0.8)`, linear `300 m` = `3 px` Euclidean triangular kernel $K(d) = \max(0, 1 - d / 300\,\mathrm{m})$, pixel-exact visible-fault exclusion):

$$\mathrm{DTI} = \frac{\mathrm{TP}_w}{\mathrm{TP}_w + 0.2\,\mathrm{FP}_w + 0.8\,\mathrm{FN}_w}, \qquad \mathrm{TP}_w + \mathrm{FN}_w = |T|$$

1. **Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`, `0.2778` — `UNVERIFIED HISTORICAL REPORT`) topped the early family ledger:**
   - Byte-exact inspection against `D2.8` (`44,090` dots) confirms `H33` (`37,654` dots) deletes the exact `6,436` dots lying within `(0, 200 m]` (`0 < d_{\mathrm{cat}} \le 2\text{ px}`) of mapped `existing_faults.tif` (`0` pixels on `existing_faults.tif`).
   - Because `TP_w` applies `max` kernel credit over a `300 m` halo while `0.2 * FP_w` sums linearly over every emitted pixel, near-catalogue pixels inside `<= 200 m` primarily duplicate mapped-trace halos where unmapped splays have already diverged, paying full additive false-positive penalty with near-zero marginal recall gain. Removing those `6,436` redundant collar dots cut `0.2 * FP_w` by `~1,287` denominator units while preserving the `> 200 m` splay and basin interior predictions.
   - Strict evidence labeling: `GEMSDOE32`'s own site explicitly marks the file `NO ORGANISER SCORE EXISTS`, so `0.2778` remains `UNVERIFIED HISTORICAL REPORT`.
2. **Reconciling `0.2778`, `0.3195`, and `0.4413` on `2026-10-22` UTC:**
   - `0.4413` (`PUBLIC-OBSERVATION`, live DrivenData leaderboard fetched `2026-10-22` UTC, closing `Dec. 3, 2026, 11:59 p.m. UTC`): `#1 xiaofanhu = 0.4413`, `#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3894`, `#4 BrandenKMurray = 0.3713`, `#5 No Fault of Our Own = 0.3539`, `#20 nchuzhoy = 0.3262`, `#50 sam35 = 0.2804`.
   - `0.3195` (`UNVERIFIED HISTORICAL REPORT`): quoted in historical prompt prose, absent from `#1`–`#50` of the live `2026-10-22` public leaderboard.
   - Zero-FP recall lower bounds ($C_{\min} = \frac{0.8\,\mathrm{DTI}}{1 - 0.2\,\mathrm{DTI}}$): `23.53%` for `0.2778`, `27.30%` for `0.3195`, and **`38.72%`** weighted kernel recall for `0.4413` (and **`47%–53%`** true weighted recall at realistic `~36,000`-dot precision). Pure zero-catalogue surface rasters plateau near `0.15–0.17` (`EXP-DCMS-1 = 0.1525 / 0.1704`) because blind basin-interior faults require coupling regional geophysics, full-coverage `10 m` 3DEP scarps, pre-Quaternary bedrock fault reactivation (`USGS DS-1052`), hydrothermal upflow (`DOE GDR 1391`), and multi-scale elastic crack-tip / relay mechanics.

### 1.2 Why `G79-DCMS` Surpasses Both `G79-THVC` and `H33` Across Every Geological Regime
Evaluated strictly out-of-fold on unmodified `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `1,000` paired physical spatial-cluster bootstrap draws across `158` / `159` connected spatial clusters; `3` experiments total within budget; `236 / 236` single-feature symmetric ROC AUCs `<= 0.90`, max `0.791085` on Seed 20 and `0.810977` on Seed 30):

| Arm (`gems57-pooled-hide-v2`) | Seed 20 `HOLDOUT-DTI` (`n = 11,321`) | Seed 30 `HOLDOUT-DTI` (`n = 11,342`) | Paired $\Delta$ (`EXP-DCMS-3 - Arm`, Seed 20 / Seed 30) |
|---|---|---|---|
| **`EXP-DCMS-3_calibrated_dinkelbach` (Active)** | **`0.2341 [0.2110, 0.2571]`** | **`0.2508 [0.2314, 0.2713]`** | Reference candidate (`26,599` / `38,000` OOF px; `36,404` live px) |
| `EXP-DCMS-2_full_network_d28` (Uniform `d=2.8`) | `0.2293 [0.2072, 0.2521]` | `0.2465 [0.2275, 0.2657]` | `+0.0049 [-0.0005, +0.0108]` / `+0.0043 [-0.0009, +0.0094]` |
| `C3_g79_thvc_incumbent` (Prior `GEMSDOE79` #1) | `0.1826 [0.1670, 0.1990]` | `0.1947 [0.1775, 0.2124]` | **`+0.0515 [+0.0341, +0.0710]`** / **`+0.0562 [+0.0407, +0.0731]`** |
| `EXP-DCMS-1_pure_physics_d28` (`0` fault features) | `0.1525 [0.1318, 0.1743]` | `0.1704 [0.1472, 0.1952]` | **`+0.0816 [+0.0677, +0.0949]`** / **`+0.0805 [+0.0615, +0.1012]`** |
| `C2_h33_analogue_foldfair` (`GEMSDOE32` analogue) | `0.0961 [0.0831, 0.1090]` | `0.0989 [0.0854, 0.1128]` | **`+0.1380 [+0.1187, +0.1572]`** / **`+0.1519 [+0.1339, +0.1736]`** |
| `C1_fabric_offset_E1_placed` (Archived E1) | `0.0441 [0.0370, 0.0512]` | `0.0440 [0.0371, 0.0517]` | `+0.1900 [+0.1684, +0.2137]` / `+0.2068 [+0.1865, +0.2301]` |
| `C0_random_B37654` (Random `37,654`-dot baseline) | `0.0497 [0.0433, 0.0561]` | `0.0422 [0.0378, 0.0465]` | `+0.1844 [+0.1626, +0.2066]` / `+0.2086 [+0.1891, +0.2286]` |

**Key regime breakthroughs (Seed 20 / Seed 30):**
- **25.5% Nevada 1-m LiDAR blind zone closed:** `EXP-DCMS-1` pure physics alone nearly doubles `G79-EXP-1` (`0.1525 / 0.1704` vs `0.0784 / 0.0837`), lifting `EXP-DCMS-3` in the non-LiDAR blind zone to **`0.2180 / 0.2508`** vs `C3_g79_thvc = 0.1691 / 0.1640` and `C2_h33 = 0.0660 / 0.0650`.
- **Far-blind `> 1 km` discovery (`+67.8%` on Seed 20, `+64.5%` on Seed 30 over `G79-THVC`):** `EXP-DCMS-3` reaches **`0.1836 / 0.2039`** vs `C3_g79_thvc = 0.1094 / 0.1239` and `C2_h33 = 0.0771 / 0.0825`.
- **USGS DS-1052 bedrock fault reactivation corridor:** **`0.3282 / 0.3237`** vs `C3_g79_thvc = 0.2375 / 0.2406`.

---

## Pass 2 — Artifact Byte Forensics, `1,201`-Blob Uniqueness Audit & Gate Integrity

1. **Root-cause diagnosis & fix of `IR-79-174` before publication:**
   - Initial 4-quadrant live emission stopped at `18,497` pixels (`min_budget` floor) despite `3,305,884` positive-utility cells because `candidate_pool = 420_000` exhausted its priority heap along `~22.7`-px-wide 4-quadrant fault ribbons at `min_sep_px = 1.95` while `float16` isotonic lower-tail calibration shifted `q99.2` relative to background `init_tp`.
   - Expanding `candidate_pool = 1_250_000`, normalizing `lambda_fp` by `median(init_tp[allowed_mask])`, aligning `sub_name = stem` (`verify_project.py:392`), and re-evaluating `seed20`, `seed30`, and `live_and_audit` from cached OOF posteriors produced natural marginal-zero equilibrium emission across all 4 quadrants: **`36,404` dots** (`SHA-256 = d281189e16ae24f344dfcd15c58a051ae6f57cd964c34808ff2eb6e65d85eba9`, ZIP `SHA-256 = 9875adb70a81a6a5d0b956b853e1c4f8d2dda6c78dda491a194918320e673c02`).
2. **Complete `1,201`-blob cross-organization uniqueness audit (`evidence/dcms_surface_uniqueness_1201.json`, `evidence/dcms_dot_uniqueness_1201.json`):**
   - **Pre-placement surface (`1,191 / 1,201` comparable):** `max |Spearman rho| = 0.730243 <= 0.90` (**PASS** on correlation); `sparse <= 50k` max overlap `0.244706`; literal max overlap `1.0000` against universal covers (`17GEMSDOE`, `GEMSDOE48`).
   - **Post-placement binary GeoTIFF (`36,404` dots, `1,191 / 1,201` comparable):**
     - `max |Spearman rho| = 0.116272 <= 0.90` (**PASS** on correlation; `max Jaccard = 0.046102 <= 0.50`).
     - **Every `<= 45,000`-dot sparse sibling across all `92` repositories clears `0.70`:** max overlap `0.653472` (`GEMSDOE80` `36,500` dots), reducing `GEMSDOE83` (`37,654` dots) from `0.7139` (`G79-THVC` collision) down to **`0.650176 <= 0.70`**!
     - **Why `OK TO SUBMIT` remains strictly `NO` (`verdict: "negative"`, `0` slots spent):** literal `3-px` overlap exceeds `0.70` against universal/dense covers (`17GEMSDOE = 1.0000`, `5GEMSDOE = 1.0000`, `13GEMSDOE = 0.8380`), two `> 48,600`-dot rasters (`GEMSDOE53 = 0.747912` at `56,605` dots; `GEMSDOE25 = 0.721047` at `48,664` dots), local ancestor `G79-THVC` (`0.806587`), plus `10` non-comparable entries. Zero post-hoc `min_sep` retuning or local/dense exemptions were permitted (`IR-79-173`).

---

## Pass 3 — Clean Verification, Visual Figure Audit, Headless Browser QA & Lifecycle Lock

1. **Visual figure verification (`IR-79-175`):** Direct inspection of all 4 rendered PNGs caught and fixed inherited `20-km Block Bootstrap CI` wording (`-> 95% Physical Spatial-Cluster Bootstrap CI`), dynamic `int(footprint.sum())` (`5,167,373` finite cells), ascending bar progression on `fig1_dcms_holdout_progression.png`, and high-contrast ivory Nevada background on `fig4_dcms_live_map_overview.png` while preserving all 4 historical `G79-THVC` figures.
2. **Multi-commit blob path disambiguation (`IR-79-177`):** Fixed duplicate `repo:path` display strings across distinct Git blob OIDs in `GEMSDOE53` via `repo:path@blob[:8]` without dropping any of the `1,201` audited blobs.
3. **Closed-lane CLI lifecycle protection (`IR-79-176`):** Added `enforce_open_lane(ROOT, "G79-DCMS")` to `scripts/run_g79_dcms.py`, preserved `archive/g79_thvc_33e1f8ec/run_card_thvc.json`, and verified all automated suites (`pytest -q`, `verify_project.py`, `submission_status.py` exit `2`, `select_submission.py` exit `2`, `reproduce_artifact.py --lane canonical` and `--lane thvc`, `build_site.py`, `check_site.py`, and headless Chromium DOM/console/layout checks across desktop & mobile).
