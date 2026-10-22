# Session `6da2620c` Scientific Report — PhD Forensic Reconciliation of `H33` (`0.2778`–`0.4413`) and Execution of Lane `G79-CSKD`

**Session branch:** `arena/6da2620c-gemsdoe79` · **Date:** `2026-10-22` UTC  
**Preregistered lane:** `G79-CSKD` ([`registry/preregistration_g79_cskd.json`](../registry/preregistration_g79_cskd.json))  
**Archived artifact (`DO-NOT-SUBMIT`):** [`archive/g79_cskd_6da2620c/downloads/g79-cskd-ccsubmod-20261022-cdfdd16f-zeros-DO-NOT-SUBMIT.tif`](../archive/g79_cskd_6da2620c/downloads/g79-cskd-ccsubmod-20261022-cdfdd16f-zeros-DO-NOT-SUBMIT.tif) (`151,998 B`, SHA-256 `91ffc11017f7d7ff1d6f77feb8be3734560e295e2f1067a463d89185c4ac37e7`, `42,000` dots)  
**Canonical repository artifact (preserved unchanged in `docs/downloads/`):** `G79-THVC` (`g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`, `35,093` dots, **`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`**)

---

## 1. Why `H33` (`GEMSDOE32`, Reported `0.2778`) Scored Highest in the Historical Family & Full Benchmark Reconciliation

### 1.1 Exact Metric Algebra of Pooled Distance-Weighted Tversky Index (`DW-DTI`)

Per official DrivenData competition rules ([Problem Description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)) and staff clarifications ([Thread 11516/2](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2), [Thread 11550/2](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2)), predictions $p(\mathbf{x}) \in [0, 1]$ on the `EPSG:32611` `100 m` GeoDAWN grid (`3730 × 3292`, `5,167,373` active footprint pixels; `60,988` mapped USGS/INGENIOUS catalogue pixels masked out) are scored globally across the evaluation domain $E$ against unmapped expert-identified faults $T \subset E$ using the pooled Distance-Weighted Tversky Index ($\alpha = 0.2$, $\beta = 0.8$, triangular kernel $K(\mathbf{x}, \mathbf{y}) = \max(0, 1 - \|\mathbf{x} - \mathbf{y}\|_2 / 300\text{ m})$):

$$\operatorname{TP}_w(p, T) = \sum_{\mathbf{y} \in T} \max_{\mathbf{x} \in E} \big[p(\mathbf{x})\, K(\mathbf{x}, \mathbf{y})\big], \qquad \operatorname{FP}_w(p, T) = \sum_{\mathbf{x} \in E} p(\mathbf{x}) \Big(1 - \max_{\mathbf{y} \in T} K(\mathbf{x}, \mathbf{y})\Big),$$

$$\operatorname{FN}_w(p, T) = |T| - \operatorname{TP}_w(p, T), \qquad \operatorname{DTI}(p, T) = \frac{\operatorname{TP}_w(p, T)}{(1 - \beta)\, \operatorname{TP}_w(p, T) + \alpha\, \operatorname{FP}_w(p, T) + \beta\, |T|}.$$

Three non-obvious mathematical consequences explain the entire 103-entry family score hierarchy (`registry/score_ledger.csv`):

1. **Asymmetric `MAX`-TP vs `SUM`-FP Duality (Anti-Ribbon Theorem):** Because $\operatorname{TP}_w$ applies a **pointwise $\max$** over all predictions within $300\text{ m}$ ($3\text{ px}$) of a truth pixel $\mathbf{y} \in T$, whereas $\operatorname{FP}_w$ **sums** $p(\mathbf{x})$ linearly over every off-fault pixel, painting a continuous $5\text{ px}$-wide probability ribbon along a fault increases $\operatorname{FP}_w$ $5\times$–$15\times$ while contributing **zero** marginal $\operatorname{TP}_w$ once one binary $p(\mathbf{x}) = 1$ dot sits within the $300\text{ m}$ kernel. Conversely, isolated binary $\{0, 1\}$ dots spaced every $\Delta s \approx 2.8\text{–}3.0\text{ px}$ along a 1-px fault trace harvest $\sum_{\Delta k = -2}^{2} (1 - |\Delta k|/3) = \mathbf{2.333}$ weighted TP units per single unit of prediction mass.
2. **Fractional-Threshold Collapse of Calibrated Posteriors:** Replacing a binary dot $p(\mathbf{x}_0) = 1$ by calibrated probabilities $p \approx 0.15$ across a $10\text{ px}$ halo slashes peak $\operatorname{TP}_w$ by $85\%$ while leaving integrated $\sum p(\mathbf{x}) \approx 1.5$ nearly unchanged, collapsing $\operatorname{DTI}$ from $\sim 0.27$ to $< 0.08$ (`17GEMSDOE` `0.0725`, `12GEMSDOE` `0.0680`).
3. **Byte-Exact Forensics of `H33` (`c55bafc4...`):** Direct raster diffing ([`evidence/h33_forensics.json`](../evidence/h33_forensics.json)) proves that `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`37,654` binary `1.0` pixels, `0.0` outside footprint) is **pixel-for-pixel identical** to `GEMSDOE29` `D2.8` (`44,090` Poisson-disk dots at $r = 2.8\text{ px}$ ranked by an unsupervised multi-sensor tectonic composite) **minus the `6,436` dots lying at Euclidean distance $0 < d_{\text{cat}} \le 2.0\text{ px}$ ($200\text{ m}$) from mapped USGS/INGENIOUS faults**. Because mapped faults are pixel-masked (`60,988` px) and geologically flanked by unmapped parallel splays or digitization offsets only beyond $\sim 200\text{–}300\text{ m}$, pruning the $6,436$ near-collar dots eliminated pure $\alpha \cdot \operatorname{FP}_w = 0.2 \times 6{,}436 \approx 1{,}287$ denominator penalty at near-zero $\operatorname{TP}_w$ loss, lifting the user-reported score from `0.2600` (`D2.8`) to `0.2778` (`H33`).

### 1.2 Rigorous Reconciliation of `0.2778`, `0.3195`, and `0.4413`

| Benchmark / Number | Strict Evidence Class | Verified Source & Exact Forensics |
|---|---|---|
| **`0.4413`** (`#1 xiaofanhu`) | `PUBLIC-OBSERVATION` (`2026-10-22T10:10Z`) | Verified live #1 score on the [DrivenData Public Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (`#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3894`, `#4 BrandenKMurray = 0.3713`). Demonstrates that ~`+0.1635` headroom exists above `H33` (`0.2778`) via high-precision fault-trace & step-over localization rather than heuristic geophysical thresholding. |
| **`0.3195`** (prompt reference) | `UNVERIFIED PROMPT REFERENCE` (absent on live board; `IR-79-123`) | Live 200-row public leaderboard audit (`2026-10-22`) shows `#21 kinghorton42 = 0.3261` and `#22 li002666 = 0.3183`, with **no `0.3195` entry currently on the leaderboard** (consistent with an earlier transient team best later superseded by a higher submission). |
| **`0.2778`** (`GEMSDOE32` `H33`) | `UNVERIFIED HISTORICAL REPORT` + `#52 extradr19 = 0.2778` `PUBLIC-OBSERVATION` | Highest score in the 103-row prompt table; matches `#52 extradr19 = 0.2778` on the live public leaderboard, though `GEMSDOE32`'s own site labels `h33-h33-2-b2-...-zeros.tif` (`c55bafc4...`) `UNSCORED` without an authenticated portal receipt. |
| **`0.1847`** (`#103 doegemsDrivendata`) | `PUBLIC-OBSERVATION` (official organizer baseline) | DrivenData reference solution by Prof. John Lipor ([`drivendataorg/gems-prize-reference-solution`](https://github.com/drivendataorg/gems-prize-reference-solution)), writing finite `0.0` outside the footprint (`aebe92f`). |
| **`0.1944 / 0.2145`** (`G79-THVC` / `G79-CSKD` Seed 30) | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, $n = 11{,}342$ withheld px) | Offline spatially blocked hide-and-recover proxy on withheld USGS/INGENIOUS segments (`H33` scores `0.0961 / 0.0989` on the exact same folds). **Never projected to a public leaderboard number.** |

---

## 2. Pre-Implementation Candidate Hypotheses & Selection of `G79-CSKD`

Before writing model code, five untried geological/geophysical hypotheses were formulated and ranked in [`research/hypotheses_6da2620c.md`](../research/hypotheses_6da2620c.md):

| Rank | ID & Short Title | Core Untried Layers & Physical Transform | Expected Holdout Uplift & Cost |
|---|---|---|---|
| **1 (Executed)** | **`G79-CSKD`** — Coulomb Shadow + Lahontan/BLM Deconfounded Scarp + GeoDAWN FFT Notch + Adularia $K_d$ + Counterfactual Charnes–Cooper | `geodawn_dem_a2_100m.tif` ($Z(\mathbf{x})$ isohypse veto), `blm_closed_claim_distance_m.tif` (open-pit/tailings suppressor), `acquisition_block_id_100m.tif` + 2D FFT E-W flight-line notch, `(Th, TC)`-regressed potassic residual $K_d$, decontaminated $d_{\text{vis}} > 3.0\text{ px}$ + Crider–Pollard Coulomb shadow $\Delta\text{CFS} < 0$, counterfactual pure-physics blend | High uplift, moderate cost (~45 min CPU, `< 2.9 GiB` RAM) |
| **2** | **`H2-MTCS`** — Magnetotelluric/Gravity Basin-Floor Detachment + Curvature Step-Over | Gravity horizontal-gradient worms + tensor curvature invariant + basin-depth inflection | Moderate-high uplift, low-moderate cost |
| **3** | **`H3-PALEO-HYDRO`** — Paleogeothermal Sinter/Travertine Structural Trend + Upflow Conduit Alignment | GDR-1391 sinter/travertine azimuth alignment with local aeromagnetic tilt zero-contours | Moderate uplift, low cost (sparse spatial coverage) |
| **4** | **`H4-DRAINAGE-KNICK`** — Tectonic Piedmont Knickpoint & Alluvial Fan Apex Lineament | Regional elevation profile convexity across range-front bajada apices | Low-moderate uplift, moderate cost |
| **5** | **`H5-ANISO-MARKOV`** — Anisotropic Strike-Propagating Geodesic Tube Allocation | Fast-marching geodesic fault-strand completion between crack tips | Moderate uplift, higher combinatorial runtime |

---

## 3. Physical & Mathematical Design of `G79-CSKD` (`src/gems79/cskd.py`)

`G79-CSKD` addresses the two structural failure modes discovered in `G79-THVC` (`IR-79-122`, `IR-79-140`):
1. **Scarp-Flank Label Contamination (`IR-79-140`):** In `G79-THVC`, training shards sampled pixels at $0 < d_{\text{vis}} \le 3\text{ px}$ ($100\text{–}300\text{ m}$) from visible faults with label $y = 0$. Because real fault scarps and magnetic contacts span $200\text{–}400\text{ m}$, this taught Stage-1 trees to suppress physical scarp signatures unless accompanied by isotropic distance-to-catalogue (`52.8%` of `G79-THVC`'s total GBDT gain), crowding `G79-THVC` into the `300–500 m` collar (`median = 316 m`, `0.21% > 2 km`) and causing a `0.7139 > 0.70` overlap collision with `GEMSDOE83` (`h83-gvcd-dink300`).
2. **Non-Fault Geomorphic & Survey Confounders:** Pure-physics models elevate false positives along Pleistocene Lake Lahontan (`~1,200–1,345 m` ASL) and Lake Bonneville (`~1,552 m` ASL) wave-cut shoreline terraces, open-pit mine haul roads/tailings piles (`US BLM Mining Claims`), and GeoDAWN E-W flight-line levelling corrugations (`200 m` spacing in Area 1 vs `400 m` spacing in Area 2).

`G79-CSKD` builds an **84-channel static label-free stack** (`cskd_static_fp84.f32.mmap`) plus **18 fold-recomputed fracture/Coulomb channels** (`102` total channels):

- **Pleistocene Shoreline Equipotential Veto & Along-Scarp Climb (`geodawn_dem_a2_100m.tif`):** Wave-cut pluvial shorelines follow gravitational equipotentials ($\nabla Z \perp \hat{\mathbf{t}}_{\text{scarp}} \implies |\hat{\mathbf{t}}_{\text{scarp}} \cdot \nabla Z| \approx 0$ inside `[1185, 1355] m` and `[1535, 1570] m`), whereas segmented normal faults climb elevation toward range-front structural culminations and plunge toward relay tips ($|\hat{\mathbf{t}}_{\text{scarp}} \cdot \nabla Z| > 0$). Note: `1,729` edge `-999999.0` sentinels inside the active footprint and a `(0.03 m, 0.09 m)` float32 origin offset in `geodawn_dem_a2_100m.tif` were detected and cleaned via Euclidean nearest-neighbor infill (`IR-79-198`).
- **US BLM Mining-Claim Deconfounder (`blm_closed_claim_distance_m.tif`):** Encodes proximity to historical mining disturbance (`exp(-d_claim / 500 m)` and `scarp * (1 - exp(-d_claim / 500 m))`) to separate natural tectonic scarps and hydrothermal adularia from open-pit benches and cyanide-heap-leach pads.
- **Survey-Aware 2D FFT E-W Flight-Line Notch & Thurston–Smith Local Wavenumber (`acquisition_block_id_100m.tif`):** Applies a Gaussian directional notch around $k_x \approx 0, \lambda_y \in [200, 600]\text{ m}$ to `tmi_rtp` before computing analytic-signal amplitude $A(\mathbf{x})$, tilt angle $\theta_{\text{tilt}}$, and shallow-contact local wavenumber $k_{\text{loc}}(\mathbf{x}) = \|\nabla \theta_{\text{tilt}}(\mathbf{x})\|_2$ conditioned on GeoDAWN survey block spacing.
- **Lithology-Regressed Potassic Adularia Residual $K_d(\mathbf{x})$:** Regresses GeoDAWN `K` linearly against `(Th, TC)` across the active footprint so felsic tuffs and K-feldspar arkoses cancel ($K_d \approx 0$), isolating hydrothermal adularia/illite upflow zones where $K_d > 0$ coincides with hydrothermal magnetite-destruction troughs.
- **Decontaminated Shards + Crider–Pollard Normal-Fault Coulomb Shadow ($\Delta\text{CFS}$):** Excludes $d_{\text{vis}} \le 3.0\text{ px}$ from all training shards and computes an explicit broadside stress-drop shadow (`net_coulomb_shadow`: perpendicular offset $3\text{–}14\text{ px}$ alongside long fault interiors without tip support) paired with along-range `net_slip_deficit` (`3.5 km` smoothed fault density minus `700 m` local fault density).
- **Counterfactual Pure-Physics + Structural OOF Blend & Charnes–Cooper 300-m Allocation:** Trains both a 102-feature structural 2-stage ensemble (LightGBM + HistGBDT + Ridge meta-stacker) and an 84-feature **zero-catalogue** pure-physics OOF ensemble inside nested LOQO folds, mass-calibrating the zero-catalogue head and blending $q_{\text{cf}}(\mathbf{x}) = (1 - w(\mathbf{x})) q_{\text{full}}(\mathbf{x}) + w(\mathbf{x}) \tilde{q}_{\text{zero}}(\mathbf{x})$ with distance-ramped Hill weight $w(\mathbf{x}) = w_{\text{base}} + w_{\text{far}}\, d_{\text{vis}}^2 / (d_{\text{vis}}^2 + d_0^2)$ ($d_0 = 18\text{ px}$; `w_base=0.05, w_far=0.25` selected strictly on inner folds) before lazy-greedy Charnes–Cooper fractional programming (`max_dots = 42,000`, `min_sep = 2.6 px`, `d_cat > 3.0 px`).

---

## 4. Measured Experimental Results (`HOLDOUT-DTI` & `1,221`-Raster Uniqueness)

### 4.1 102-Feature Single-Feature Leakage Canary (`evidence/g79_cskd_leakage_canary.json`)
All `102` features (84 static + 18 fold-recomputed mechanics) were tested individually on both Seed 20 and Seed 30 (`204` tests total):
- **Seed 20 max symmetric AUC:** `0.789071 <= 0.90` (`net_log_dist`) — **PASS (`0` violations)**
- **Seed 30 max symmetric AUC:** `0.805165 <= 0.90` (`net_log_dist`) — **PASS (`0` violations)**
- **Max static label-free feature AUC:** `0.692857` (Seed 20) / `0.715575` (Seed 30) (`lidar_ coverage / scarp`).

### 4.2 Official Dual-Seed `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `evidence/g79_cskd_results.json`)

| Arm / Candidate | Budget (Dots) | Seed 20 `HOLDOUT-DTI` [95% CI] ($n=11{,}321$) | Seed 30 `HOLDOUT-DTI` [95% CI] ($n=11{,}342$) | 2-Seed Mean `HOLDOUT-DTI` ($n=22{,}663$) | Dots `> 2 km` from Visible |
|---|---|---|---|---|---|
| **`EXP-CSKD-3` (`G79-CSKD` Counterfactual + Charnes–Cooper)** | **`42,000`** | `0.178129` `[0.161835, 0.194433]` | **`0.214488`** `[0.196592, 0.232188]` (**#1 `GEMSDOE79` Record**) | **`0.196308`** (**#1 `GEMSDOE79` Mean**) | **`12.96%` (S20) / `8.84%` (S30)** |
| `G79-THVC` (`EXP-79-3`, Canonical Baseline) | `35,093` | **`0.190517`** `[0.174082, 0.206932]` | `0.194366` `[0.177400, 0.212627]` | `0.192442` | `0.21%` (live) |
| `EXP-CSKD-2` (`G79-CSKD` Uniform `d=2.8 px`, `37,654` dots) | `37,654` | `0.149307` `[0.133514, 0.166028]` | **`0.211781`** `[0.191327, 0.231608]` | `0.180544` | `1.13%` / `0.76%` |
| `C2` (`H33` Fold-Fair Champion Control) | `37,654` | `0.096086` `[0.082774, 0.109514]` | `0.098898` `[0.085412, 0.112762]` | `0.097492` | ~`49%` |
| `EXP-CSKD-1` (Pure Zero-Catalogue 84-Ch Multi-Physics) | `37,654` | `0.076289` `[0.062322, 0.089525]` | `0.069605` `[0.053984, 0.086325]` | `0.072947` | `78.79%` / `78.57%` |
| `C0` (Uniform Random Footprint Control) | `37,654` | `0.044670` `[0.039968, 0.049392]` | `0.049097` `[0.043424, 0.055134]` | `0.046884` | ~`75%` |

### 4.3 Decontamination Physics Shift & `1,221`-Raster Uniqueness Audit

1. **Collapse of Isotropic Distance Shortcut (`52.8% -> 9.7%`):** Removing false-negative flank pixels ($0 < d_{\text{vis}} \le 3\text{ px}$) slashed Stage-1 GBDT gain on isotropic fault distance (`net_log_dist` + `net_exp_near_600` + `net_exp_mid_1800` + `net_exp_far_4500`) from **`52.8%` in `G79-THVC` down to `9.7%` in `G79-CSKD`**, shifting **`90.3%` of model gain** onto directional fracture-mechanics and physical observables: `net_tip_fwd_35px` (`17.96%`), `net_tip_x_scarp` (`7.96%`), `det_elev_prom_600m` (`3.65%`), `volc_vent_prox_3km` (`2.45%`), and `net_coulomb_shadow` (`1.47%`).
2. **Broader Off-Fault Discovery Reach:** On the full-footprint live map (`42,000` dots, strictly $d_{\text{cat}} \ge 3.162\text{ px} = 316.2\text{ m}$), `G79-CSKD` places **`2.85%` (`1,198` dots) beyond `2 km`** (`90th percentile = 1.28 km`) versus only `0.21%` (`74` dots, `90th percentile = 632 m`) in `G79-THVC`.
3. **Complete De-Collision Against `GEMSDOE83` & All Valid `-zeros.tif` Cross-Repo Sparse Maps (`1,221` rasters audited):**
   - **Pre-placement continuous surface:** `max |Spearman ρ| = 0.6409 <= 0.90` (`0` Spearman collisions); `0` cross-repo `<= 50k` surface collisions (`max = 0.2437`).
   - **Post-placement binary dots (`42,000` px):** `max |Spearman ρ| = 0.4246 <= 0.90`; **`GEMSDOE83` (`h83-gvcd-dink300`) forward 3-px overlap drops from `0.7139` (`G79-THVC` collision) to `0.6137 <= 0.70` (`G79-CSKD` PASS)**! Across **100% of valid all-finite `-zeros.tif` cross-repo sparse maps (`<= 50k` dots)**, max 3-px overlap is **`0.6796 <= 0.70` (`0` collisions)**. Only a single invalid NaN-outside file (`GEMSDOE25:...5e4b5a98d2c7-nan.tif`, `48,664` dots) edges to `0.7062` (`IR-79-200`), alongside self-repo `G79-THVC` (`0.7626`) and the universal pigeonhole witnesses (`17GEMSDOE = 1.0000`, `13GEMSDOE = 0.9982`).

### 4.4 Preregistered Gate Verdict & Portfolio Recommendation
Per [`registry/preregistration_g79_cskd.json`](../registry/preregistration_g79_cskd.json), replacing `G79-THVC` as canonical artifact required beating `G79-THVC` on **both** Seed 20 and Seed 30 individually AND clearing the literal `uniqueness.py` gate. Because `G79-CSKD` set the all-time `GEMSDOE79` record on Seed 30 (`0.2145` vs `0.1944`, `+0.0201`) and 2-seed mean (`0.1963` vs `0.1924`), but trailed `G79-THVC` on Seed 20 (`0.1781` vs `0.1905`, `-0.0124`) where inner-fold selection chose a higher far-field weight (`w_far = 0.25`, placing `12.96%` of dots `> 2 km` vs `8.84%` on Seed 30), we strictly honor the preregistration:
- **`G79-THVC` remains canonical** in `docs/downloads/` and `run_card.json` (`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`, `0` slots spent).
- **`G79-CSKD` is preserved byte-intact** in `archive/g79_cskd_6da2620c/` with its complete Run Card (`archive/g79_cskd_6da2620c/run_card_cskd.json`). Notably, if a human participant has already tested or plans to test `GEMSDOE83`, `G79-CSKD` (`0.6137 <= 0.70` overlap vs `GEMSDOE83`) provides a genuinely orthogonal counterfactual alternative whereas `G79-THVC` (`0.7139 > 0.70`) collides with `GEMSDOE83`.
