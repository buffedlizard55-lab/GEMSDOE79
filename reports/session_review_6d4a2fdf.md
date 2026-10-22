# Session `arena/6d4a2fdf-gemsdoe79` — Three-Pass Line-by-Line Review & Cross-Repository Audit (`2026-10-22`)

- **Repository & Active Branch:** `buffedlizard55-lab/GEMSDOE79` · branch `arena/6d4a2fdf-gemsdoe79` (`active`, branched from `origin/main` `41c07e2`)
- **Automated Submission Status (`scripts/submission_status.py`, exit code `2`):**
  **`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`**
- **Canonical Research Artifact (Unchanged SHA-256):**
  `docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif`
  - **TIFF SHA-256:** `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2` (`139,863` bytes; `37,654` binary `{0.0, 1.0}` dots; `0` NaNs across all `12,279,160` cells; `EPSG:32611`; `3730 x 3292`; exact affine match)
  - **ZIP SHA-256:** `b882f55d38a0020d1b4773a5f2db8d7eddc401fb38b5d58a98758c19b99a6bc7`
  - **Weekly DrivenData Upload Slots Consumed:** `0` (`0` new scientific experiments executed; all stopped negative lanes `H79-NHR`, `E1`, `G79-STEPCO`, `G79B-SDPT`, `H79-FF` kept strictly sealed).

---

## Executive Summary of New Findings Verified from Primary Sources & Raw GeoTIFF Bytes

### 1. Why `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, `0.2778` reported) Scored Highest in the `GEMSDOE` Family — and Why `#1 xiaofanhu` Reached `0.4413`
1. **Exact Zero-XOR Pixel Identity (`RASTER-MEASUREMENT`, `evidence/family_lineage_forensics.json`):**
   Across all `12,279,160` cells, `GEMSDOE32` (`37,654` binary `1.0` dots, `c55bafc4…`) equals `(GEMSDOE25_D2.8 > 0) & (EDT(~existing_faults) > 2.0)` with **0 discrepant pixels**.
2. **Exact DW-Tversky Asymmetry (`DD-PROBLEM` `page/967/`, `DD-MASK` `11516/2` & `11516/4`, `DD-POOL` `11550/2`):**
   Because $\text{TP}_w$ takes a **maximum** over $B_{300\text{m}}(g)$ while $\text{FP}_w$ **sums** over every predicted pixel outside true fault kernels, sparse `~2.8 px` binary dots cut $\text{FP}_w$ by $\sim 3\times$ vs continuous probability ridges (`19GEMSDOE` `0.1922` $\to$ `GEMSDOE25` `D2.8` `0.2600`). And because `existing_faults.tif` is masked **pixel-exactly** (`chrisk-dd`, `11516/4`), removing the `6,436` `D2.8` dots sitting in the `0 < d_{\text{cat}} \le 200\text{ m}` flank collar eliminated pure penalty mass without losing off-catalogue $\text{TP}_w$ (`0.2600` $\to$ `0.2778`, `UNVERIFIED HISTORICAL REPORTS`).
3. **Resolution of the `2026-10-21 -> 2026-10-22` Public Leaderboard Cutoff Puzzle (`IR-79-72`):**
   - On `2026-10-21` (`knowledge/official_sources.json`), `#48 extradr19 = 0.2778` appeared on the 50-row public leaderboard.
   - On `2026-10-22` (live `fetch_page` across all 3 chunks of `/leaderboard/`), ranks `#1`–`#50` span **`#1 xiaofanhu = 0.4413` (27 submissions)**, `#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3894`, `#4 BrandenKMurray = 0.3713`, `#5 No Fault of Our Own = 0.3539`, ..., `#21 kinghorton42 = 0.3261`, down to **`#48 sam35 = 0.2804`, `#49 op01 = 0.2797`, `#50 kinneso_outlook = 0.2784`**. Two new top-50 entries pushed `0.2778` immediately below row `#50` (`#51+`). Both `0.2778` and `0.3195` remain labelled `UNVERIFIED HISTORICAL REPORTS` without an authenticated submission-page receipt.
4. **Why Automated Family Runs Stalled at `~0.2778` While `#1` Reached `0.4413` (`DD-NEW-FAULT-DEF` `11543/2`, `11536/2`, `11527/7`):**
   - Official Staff (`chrisk-dd`, Oct 1 in [`11543/2`](https://community.drivendata.org/t/using-a-teammates-geological-interpretation-as-training-labels/11543/2)) confirmed **human geological hand-labeling / accept-reject curation on public data inside the GeoDAWN region IS permitted** when saved reproducibly — allowing human+ML teams to purge Lake Lahontan/Bonneville paleoshorelines, mine benches, and road cuts that consume $\ge 50\%$ of purely unsupervised/PU dot budgets!

---

### 2. Three-Tier Mathematical Obstruction Certificate (`IR-79-73`, `scripts/verify_registry_obstructions.py`)

Direct single-pixel measurement on SHA-256-verified registry blobs (`A = 5,106,385` off-catalogue footprint cells, [`evidence/registry_obstructions_certificate.json`](../evidence/registry_obstructions_certificate.json)) proves why `research/hypotheses_e846fc02.md`'s threshold-only proposal (`p >= 0.5` or `top-K`) **cannot work alone**:

| Obstruction Tier | Rule Evaluated | Hash-Verified Registry Witness(es) | Uncovered Allowed Pixels ($U$) | Global Minimum 3-px Forward Overlap at $K = 37,654$ | Max Passable Budget $K_{\max}(0.70)$ | Mathematical Consequence |
| :---: | --- | --- | ---: | ---: | ---: | --- |
| **Tier 1** | `literal` (`arr > 0`) | `17GEMSDOE` `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` (`ab0a0a62…`) | **`0`** | **`1.000000` (`1/1`)** | **`0`** | Every nonempty map ($K \ge 1$) fails (`1.0 > 0.70`). |
| **Tier 2** | **`p >= 0.5` AND `budget-matched-v3`** (`top-37,654` with ties) | `5GEMSDOE:gems-density-probe-20260925T184215Z-9cdae9b4.tif` (`9cdae9b4…`, binary `1.0` on all `5,106,385` allowed cells!) + `3` `GEMSDOE48` unassigned-mass rasters (`11c0e3b6…`, `86a470fc…`, `975c217e…`) | **`0`** | **`1.000000` (`1/1`)** | **`0`** | **Refutes `p >= 0.5` and tie-inclusive `top-K`:** every nonempty map ($K \ge 1$) STILL fails (`1.0 > 0.70`). |
| **Tier 3** | **Any continuous-surface rule leaving sparse (`<= 20%`) binary dot maps untouched** | `13GEMSDOE` spacing-5 binary lattices (`zerofill` `c12533bb…` & `nan-outside` `b4570b40…`, `206,895` binary `{0,1}` pixels $= 4.00\%$ support; $\max_{\mathbb{Z}^2} d(x, 5\mathbb{Z}^2) = \sqrt{8} \approx 2.8284 < 3.0\text{ px}$) | **`6,514`** | **`0.827004` (`15570/18827`)** | **`21,713`** | **Pigeonhole Impossibility:** across ALL $\binom{5,106,385}{37,654}$ subsets, at least $37,654 - 6,514 = 31,140$ dots fall within `3 px` (`82.70% > 70%`). |

**Exact Shared-Code Solution Requiring Protocol-Owner Ratification (`AGENTS.md §4`):** Define `excess-overlap-v4` using **Cohen-style overlap beyond chance** $\text{ov}_{\text{excess}}(A, B) = \frac{\text{ov}_{3\text{px}}(A, B) - h(B)}{1 - h(B)} \le 0.70$ paired with deterministic coordinate tie-breaking on dense/constant surfaces (`h(B) == 1.0`), while retaining full-footprint $|\rho_{\text{Spearman}}| \le 0.90$ across all `990` comparable rasters.

---

### 3. Complete Cross-Repository Audit of All Prompt-Named Unscored Candidates & Post-Snapshot Siblings (`IR-79-74`, `IR-79-76`)

All `16` scored historical landmarks (`GEMSDOE19..GEMSDOE77`), all `6` prompt-named unscored candidates (`GEMSDOE76`, `78`, `80`, `81`, `82`, `83`), canonical `GEMSDOE79` (`H79-NHR`), and empty stubs `GEMSDOE84..90` (`1` file `README.md`, `0` `.tif` each) were verified byte-for-byte in [`evidence/family_lineage_forensics.json`](../evidence/family_lineage_forensics.json) and [`evidence/registry_obstructions_certificate.json`](../evidence/registry_obstructions_certificate.json):

| Repo | Submission Stem | SHA-256 (`[0,1]` Format) | Dots | Sibling Self-Reported Holdout | Unmodified 992-Raster `v3` Collisions (`>0.70` among 26 Informative Priors) | Worst Excess Overlap Beyond Chance ($\le 0.70$?) | Static Full-Cat Seed-20 / Seed-30 Diagnostic | Forensic Verdict & Critical Irregularity |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| **`GEMSDOE79`** *(Canonical)* | `gems79-h79-nhr-research-37654dots-...-DO-NOT-SUBMIT` | `abbf5314…` (`PASS`) | `37,654` | **`0.1431 / 0.1522`** (`gems57-pooled-hide-v2` S20/S30) | **`26` (`0.9130` raw)** | `0.7770` (**FAIL**) | `0.0136 / 0.0148` *(blind OOF `0.1431 / 0.1522`)* | **Reference gold-standard honesty:** fails both raw (`0.913`) and chance-corrected (`0.777 > 0.70`) uniqueness; rightly locked `DO-NOT-SUBMIT`. |
| **`GEMSDOE76`** | `gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros` | `54c97839…` (`PASS`) | `39,200` | `0.1782` (*non-standard `label-blind-quadrants-v2`, `n=60,988`*) | **`22` (`0.9555` raw)** | `0.9051` (**FAIL**) | `0.0015 / 0.0019` | Non-comparable holdout split; fails both raw (`0.956`) & excess (`0.905`) overlap (`GEMSDOE22:10pct`); superseded in `GEMSDOE76` (`h76_3` scored `0.1555` live). |
| **`GEMSDOE78`** | `gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros` | `8ca06ece…` (`PASS`) | `44,090` | `0.1771` (`gems57-pooled-hide-v2` S20) | **`20` (`0.9378` raw)** | `0.8406` (**FAIL**) | `0.0000 / 0.0000` *(mechanical `b5` `500m` collar)* | Aggressive `b5` (`500 m`) collar deletes all near-fault splays (`11516/4`, `11536/2`); fails raw (`0.938`) & excess (`0.841`) overlap (`GEMSDOE3:coverage-v3-wide`). |
| **`GEMSDOE80`** | `gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros` | `a3c14d76…` (`PASS`, `+3 -nan.tif` in repo) | `51,667` | `0.2349` (**PRIVATE FORK `GEMSDOE80-v2`, `n=18,313`**) | **`13` (`0.8589` raw)** | **`0.6907` (PASS excess)** | `0.0008 / 0.0010` | **Violated Rule 2 (`AGENTS.md §2`)** via private evaluator fork + only 20-raster uniqueness check + heavy `51,667` dot budget; also ships `-nan.tif` siblings (`IR-79-76`). |
| **`GEMSDOE81`** | `gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros` | `9798fe7f…` (`PASS`) | `44,090` | `0.2170` (`gems57-pooled-hide-v2`, `n=22,641`) | **`25` (`1.0000` raw)** | `1.0000` (**FAIL**) | **`0.0918 / 0.0935`** (**PURE COLLAR LEAKAGE!**) | **Severe `IR-79-11` Collar Pathology:** `100.0%` of dots in `(200, 500 m]` (`83.6%` at `223.6–300 m`, `0.00% > 1 km` — same trap as `GEMSDOE77 = 0.0964`!); checked only `5` rasters (`Rule 1` violation); `1.0000` informative overlap! |
| **`GEMSDOE82`** | `gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros` | `120810fe…` (`PASS`, `+2 -nan.tif` in repo) | `37,654` | `0.1253` (`gems57-pooled-hide-v2` S20) | **`21` (`0.9648` raw)** | `0.9249` (**FAIL**) | `0.0039 / 0.0037` | Lower S20 `HOLDOUT-DTI` (`0.1253`) than `GEMSDOE79` `H79-NHR` (`0.1431`) AND fails raw (`0.965`) & excess (`0.925`) overlap (`GEMSDOE22:10pct`). *(Note companion `gems82-h82-csam` reached `0.1658` dual-seed).* |
| **`GEMSDOE83`** | `gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros` | `79f14dc8…` (`PASS`, `+4 -nan.tif` in repo) | `37,654` | **`0.2068`** (`0.1999` S20 / `0.2138` S30, `gems57-pooled-hide-v2`) | **`11` (`0.8514` raw)** | **`0.6194` (BEST — PASS excess)** | `0.0000 / 0.0000` *(mechanical `b3` `300m` collar)* | **Strongest cross-family scientific candidate (`0.2068` dual-seed, `37,654` dots, `0.6194 <= 0.70` excess overlap)**, BUT only audited `119` rasters locally (missed `11` raw `>0.70` collisions on wide priors). Needs `v4` ratification + full 990-raster excess-overlap check before spending a weekly slot. |
| **`GEMSDOE84..90`** | *(Empty repository stubs)* | — | `0` | — | — | — | — | Each contains `1` file (`README.md`) and `0` `.tif`/`.zip` artifacts. |

---

## Summary of Three Verification Passes Executed on `arena/6d4a2fdf-gemsdoe79`

- **Pass 1 (Baseline Reproduction, Primary-Source Line-by-Line Verification & Tooling Implementation):**
  Reproduced all `242` baseline tests, `verify_project.py`, `submission_status.py` (exit `2`), `check_site.py`, `browser_review.cjs` (`21` Chromium checks), and `verify_public_site.py`; read all primary competition/USGS/DOE/forum pages (`page/967/`, `page/968/`, `/leaderboard/` ranks `#1`–`#50`, `96647.pdf`, `11516/2,4`, `11527/7`, `11536/2`, `11543/2`, `11550/2`, `11556/3`, `10.5066/P93LGLVQ`, `10.15121/1881483`, `epsg.io/32611`, Tversky 1977, `GEMSDOE32` Pages); implemented `scripts/verify_registry_obstructions.py` and upgraded `scripts/analyze_family_lineage.py` + `scripts/refresh_feed.py`.
- **Pass 2 (Edge-Case, Schema & Cross-Sync Bug Hunt):**
  Caught and fixed four concrete bugs during implementation: (i) `registry_index.json` `aliases` lookup in `verify_registry_obstructions.py`, (ii) background `git gc --auto` lock contention during blobless `cat-file` fetches in `analyze_family_lineage.py`, (iii) exact tuple signature `folds, _ = holdout.buffered_component_draw(grid, seed=seed)` in `vendor/gems57/holdout.py` reproducing `h33_foldfair_control = 0.0961 / 0.0989` to 4 decimal places, and (iv) stale `observed_date` fallback in `scripts/refresh_feed.py`; rebuilt `docs/` and expanded automated regression tests in `tests/`.
- **Pass 3 (End-to-End Prompt & Contract Audit, Live Browser QA, PR & Merge to `main`):**
  Verified zero uncommitted drift, zero non-compliant/duplicate `.tif` files presented as submittable, 100% alignment between `run_card.json`, `scripts/submission_status.py`, `README.md`, `reports/`, `research/`, and all 7 pages of `docs/` across desktop (`1440x900`) and mobile (`390x844`) Chromium viewports, live `0.0.0.0` preview server, green GitHub Actions CI, and merged PR onto `main`.
