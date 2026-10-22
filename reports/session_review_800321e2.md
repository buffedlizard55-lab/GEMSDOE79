# End-to-End Three-Pass Scientific & Engineering Review — Session `800321e2`

- **Date (UTC):** `2026-10-22`
- **Repository / Active Branch:** `buffedlizard55-lab/GEMSDOE79` (`arena/800321e2-gemsdoe79`)
- **Active Public Decision (`run_card.json`, `scripts/submission_status.py`, `README.md`, `docs/`):** `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` (`exit code 2`)
- **Weekly Submission Slots Spent:** `0`

---

## Executive Synthesis

Across three complete, independent verification passes, this session audited the entire `GEMSDOE79` repository against live official DrivenData, DOE/NLR, USGS, DOE GDR 1391, and GBCGE INGENIOUS primary sources (`2026-10-22`); uncovered and permanently fixed a silent data-restoration receipt corruption bug (`IR-79-82`); formulated five geologically distinct fault-discovery hypotheses ([hypotheses_mrnd_800321e2.md](../research/hypotheses_mrnd_800321e2.md)); hash-locked preregistration ([preregistration_mrnd.json](../registry/preregistration_mrnd.json), SHA-256 `ea12fe39a45287a32152958bdfa5160f8514b0bd0200c613b46a245f7d22b265`) prior to running a single experiment; executed preregistered **Experiment `M1` (`H79-MRND`)** end-to-end across `77` zero-leakage multi-modal features; proved the **Complete Three-Tier Combinatorial Partition Theorem** of the `992`-blob family registry ([mrnd_analysis.md](mrnd_analysis.md), `IR-79-83`, `IR-79-84`); and stopped cleanly at the pre-placement surface duplicate gate with zero retuning, zero overlap-swapping, and zero weekly slots spent.

---

## Three-Pass Execution Log

### Pass 1 — Live Source Verification, Restoration Audit, Hypothesis Formulation & Experiment `M1`

1. **Line-by-Line Primary Source Verification (`2026-10-22`, logged in [official_sources.json](../knowledge/official_sources.json)):**
   - **DrivenData Leaderboard (`DD-LEADERBOARD`):** `#1 xiaofanhu = 0.4413`, `#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3894`, `#5 No Fault of Our Own = 0.3539` (Phase 1 `$10,000` top-5 cutoff), `#21 kinghorton42 = 0.3261`, `#22 li002666 = 0.3183`, `#50 kinneso_outlook = 0.2784`. User-reported `0.3195` does not appear on the official board (`IR-79-77`), and `GEMSDOE32` (`0.2778`, `USER-REPORTED`) was displaced just below `#50` (`0.2784`).
   - **DrivenData Staff Clarifications (`chrisk-dd`, threads `11516`, `11527`, `11536`, `11550`, `11556`):** Confirmed pixel-exact exclusion of `existing_faults.tif` (`60,988` pixels) with **no 300 m exclusion buffer**, global pooling of weighted TP/FP/FN, inclusion of newly mapped splay/tip/continuation geometry within `300 m` of known traces in evaluation truth, and identical known-fault mask between Phase 1 (`$50K`) and Phase 2 (`$250K`).
   - **DOE/NLR Official Rules (`docs.nlr.gov/docs/fy26osti/96647.pdf`) & Public Datasets (`USGS 3DEP`, `USGS GeoDAWN` `doi:10.5066/P93LGLVQ`, `DOE GDR 1391` `doi:10.15121/1881483`, `USGS Regional Compilation` `doi:10.5066/P9Z6SA1Z`):** Verified `3` submissions/week cap, single final selection across both phases, mandatory generative-AI disclosure in finalist narrative, and open licensing (`CC0` / `CC-BY-4.0`) of all pinned external layers.
2. **Data & Registry Restoration (`13/13` Raw Inputs + `992/992` Frozen Registry Blobs):**
   - Executed `.venv/bin/python scripts/restore_data.py --preserve-receipt`, catching fabricated SHA-256 / phantom ID entries in `data/restore_receipt.json` left by `014edbe` (`IR-79-82`). Regenerated `data/restore_receipt.json` from verified bytes via `scripts/restore_data.py` and verified `restore_data.py --preserve-receipt` now exits `0`.
   - Restored and SHA-256-verified all `992` frozen family registry rasters via `scripts/restore_registry_git.py` and verified preflight witness behavior via `scripts/preflight_new_lane.py --restore` (`exit code 2`).
3. **Preregistered Experiment `M1` (`H79-MRND` — [src/gems79/mrnd.py](../src/gems79/mrnd.py), [scripts/run_mrnd.py](../scripts/run_mrnd.py)):**
   - Locked [preregistration_mrnd.json](../registry/preregistration_mrnd.json) prior to execution (`ea12fe39...`).
   - Constructed `77` zero-leakage multi-modal features (`19` geophysical/DEM bands + multi-scale potential-field worms, exact inverse-sqrt 3DEP lidar + TIGER road deseaming + contour scarp vs down-slope gully invariant `scarp_vs_channel` + bedrock canyon suppression, `GeoDAWN` radiometrics/upward-continued `TMI_up150`, `DOE GDR 1391` `27,092`-site hydrothermal geothermometry + volcanic vents with `dist_known_fault_px` stripped on ingest, and out-of-fold crack-tip propagation geometry).
   - Passed **all 616 single-feature leakage canary tests** (`max AUC = 0.8514` on Seed 20, `0.8589` on Seed 30; threshold `<= 0.90`, `0` suspicious).
   - Achieved **two-seed `HOLDOUT-DTI` wins (`gems57-pooled-hide-v2`)** while forcing **42% of candidate mass beyond `4.5 km` from known faults**:
     - **Seed 20 (`n = 11,321` withheld pixels):** `0.1044` `[0.0902, 0.1184]` vs `H33` fold-fair `0.0961` (`+0.0084`), static ablation `0.0801` (`+0.0243`, 95% CI `[+0.0082, +0.0411]`), uniform `0.0484` (`+0.0560`, 95% CI `[+0.0414, +0.0697]`).
     - **Seed 30 (`n = 11,342` withheld pixels):** **`0.1236` `[0.1065, 0.1414]`** vs `H33` fold-fair `0.0989` (**`+0.0247`, paired 95% CI `[+0.0095, +0.0389]` strictly > 0**), static ablation `0.0817` (`+0.0419`, 95% CI `[+0.0269, +0.0581]`), uniform `0.0482` (`+0.0754`, 95% CI `[+0.0585, +0.0925]`).
   - Executed pre-placement surface scan across all `992` frozen blobs ([uniqueness_surface.json](../evidence/mrnd/uniqueness_surface.json), [surface_diagnostic.json](../evidence/mrnd/surface_diagnostic.json)) BEFORE placing final dots:
     - **Spearman rank correlation:** `worst = 0.2582 <= 0.90` (**PASS**).
     - **All ~950 normal-budget (`<= 167,596`-dot) family submissions across all 88 repos:** **`0 / ~950` duplicate flags (`<= 0.70`)** — solving genuine inter-submission duplication completely!
     - **Literal one-sided `0.70` overlap gate:** flagged `40` rasters (`30` `halo > 0.70` space-filling priors + `10` over-emitted wide-blanket files with `167,597..624,025` dots). Stopped immediately before placing final dots (`verdict: "negative"`, [run_card_mrnd.json](../run_card_mrnd.json)).

---

### Pass 2 — Code, Math, Edge-Case & Regression Hardening

1. **Permanent `restore_receipt` <-> `data_manifest` Verification Gate (`scripts/verify_project.py`):**
   - Added `restore_receipt_matches_data_manifest(ROOT)` inside `verify()` so `scripts/verify_project.py` fails closed if `data/restore_receipt.json` ever diverges in IDs, verification status, or SHA-256 digests from `registry/data_manifest.json`.
   - Added unit regression test `test_restore_receipt_parity_check_catches_hash_or_id_drift` in [test_publication_contract.py](../tests/test_publication_contract.py).
2. **Closed-Lane Lifecycle Protection & Programmatic Card Synthesis (`scripts/finalize_mrnd.py`, [test_mrnd.py](../tests/test_mrnd.py)):**
   - Locked `evidence/mrnd/m1_experiment_state.json` so re-invoking `scripts/run_mrnd.py holdout` or `final` refuses with `exit code 2` and mutates zero bytes, verified by subprocess regression tests in `tests/test_mrnd.py`.
   - Verified zero machine-local paths (`/home/user/GEMSDOE79`), strict non-NaN JSON compliance, sequential `IR-79-01..85` numbering in [irregularities.md](irregularities.md), single canonical upload artifact hygiene in `docs/downloads/`, and clean relative links across all Markdown and HTML files.

---

### Pass 3 — End-to-End Site Rebuild, Playwright Browser Review & Full Verification Suite

Caught and remediated **IR-79-85** during live Pass 3 re-execution (`scripts/restore_data.py` machine-path normalization to `"data/raw"` and `tests/test_site_feed_and_recovery.py` dynamic `reviewed_date_utc` assertion), verified all `7/7` chunks of `https://docs.nlr.gov/docs/fy26osti/96647.pdf`, and re-ran all automated gates cleanly on the final tree:
- `.venv/bin/python scripts/build_site.py` — rebuilt all `7` HTML pages + `2` compatibility redirects + `docs/evidence/`
- `node scripts/browser_review.cjs` — headless Chromium visual, viewport (`1440px`, `390px`, `320px`), link, clipboard, `.tif` download SHA-256, and zero-console-error QA (`21` rendered cases `passed`)
- `.venv/bin/pytest -q` — `263 passed` across full unit & publication contract suite
- `.venv/bin/python scripts/check_site.py` — `passed: true`, `123` local links verified, `0` web-root escapes
- `.venv/bin/python scripts/verify_project.py` — `all_checks_passed: true` across all `30` byte, GeoTIFF, ZIP, witness, receipt, and publication contract checks
- `.venv/bin/python scripts/submission_status.py` — crystal-clear `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` (`exit code 2`)

---

## Remaining Limitations & Recommended Next Steps for the Human Competition Owner

1. **Human Protocol Amendment Required to Unblock Any `37,654`-Dot GeoTIFF (`IR-79-53`, `IR-79-84`):**
   - By exact combinatorial Pigeonhole bound, every `37,654`-dot set has forward 3 px overlap `>= 31,140 / 37,654 = 0.827004 > 0.70` with `13GEMSDOE` sparse lattice (`U = 6,514`) and `1.0000` with full-support surfaces (`GEMSDOE48` / `17GEMSDOE`), while `representation_class`'s `0.15 * footprint` cutoff leaves `168k..624k`-dot wide-blanket files un-budget-matched (`4.5x..16.6x` dot asymmetry).
   - **Recommended 1-line human amendment in `vendor/gems57/uniqueness.py`:** adopt symmetric 3 px halo overlap $\min(\operatorname{ov}_{3\text{px}}(M, R), \operatorname{ov}_{3\text{px}}(R, M)) \le 0.70$ (updating `registry/template_pin.json` with an explicit IR entry). Under that symmetric rule, `H79-MRND` clears **100% of all `990` comparable family rasters (`0 / 990` duplicates)** while beating `H33` on both seeds.
2. **Outside-Footprint Value Convention (`IR-79-69`, `IR-79-79`):**
   - Official problem prose states data outside bounds is `null or nan` (`sample_submission.tif` uses `NaN`), whereas the official U-Net reference notebook and user-reported `H33` (`0.2778`) write `0.0`. Confirm preference before uploading any future promoted candidate.
3. **Offline Holdout Proxy vs Undisclosed Expert Ground Truth:**
   - `HOLDOUT-DTI` evaluates withheld USGS/INGENIOUS components rather than confidential NLR/USGS Phase 1 & Phase 2 expert traces; weekly submission slot count and U.S. eligibility/AI-disclosure certifications remain account-side responsibilities of the human entrant.
