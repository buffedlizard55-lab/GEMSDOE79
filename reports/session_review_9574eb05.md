# Session `9574eb05` Three-Pass Verification & Forensic Review (`arena/9574eb05-gemsdoe79`)

- **Date:** `2026-10-22` UTC
- **Active Branch:** `arena/9574eb05-gemsdoe79` (branched from `main` at `80550533de8e12f9a631ed928d50bcfc7f95e319`)
- **Prospective Lane Executed:** **`H79-PFSD`** (*Province-Normalized Flank-Decontaminated Subsurface-Surface Strike Concordance, Upward Probe Heat-Flux & Dual-Expert Equilibrated Allocator*)
- **Canonical Deliverable Disposition (`IR-79-120`):** [`docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif) (`SHA-256: d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`, `HOLDOUT-DTI` `0.1905` Seed 20 / `0.1944` Seed 30, `OK TO DOWNLOAD: YES`, `OK TO SUBMIT: NO`) preserved untouched; `H79-PFSD` (`SHA-256: 23cc11b49380e7e6eac772157b3b9538e3fc44559b871d69e1fe3fa2faa2bf84`, `39,250` binary pixels) archived byte-for-byte under [`archive/h79_pfsd_9574eb05/`](../archive/h79_pfsd_9574eb05/README.md).

---

## Pass 1 — Implementation & End-to-End Verification

1. **Repository & Previous-Run Continuation Audit:**
   - Verified `AGENTS.md` start-of-session checklist, restored all `13` manifest inputs (`--preserve-receipt` keeping `evidence/official_ingenious_receipt.json` clean), `13` 10-m USGS 3DEP vectors, `5` official DOE GDR-1391 archives (`DOI 10.15121/1881483`), `992` frozen registry rasters, `207` committed delta rasters, and `2` brand-new post-`04:31Z` `GEMSDOE78` rasters (`0338383df9c3…` & `44429c439118…`).
   - Verified live DrivenData public leaderboard (`#1 xiaofanhu = 0.4413`, confirming prompt's `0.3195` is superseded) and answered why `GEMSDOE32` `H33` (`0.2778` `ORGANIZER-CONFIRMED`, `0.0961 / 0.0989` `HOLDOUT-DTI`) led prompt-listed sites (`research/hypotheses_9574eb05.md`).
2. **Pre-Implementation Hypotheses & Sealed Preregistration:**
   - Authored 5 untried geological hypotheses (`H79-PFSD` + `H79-CAND-B..E`) in [`research/hypotheses_9574eb05.md`](../research/hypotheses_9574eb05.md) with zero projected scores.
   - Sealed [`registry/preregistration_pfsd.json`](../registry/preregistration_pfsd.json) (`SHA-256: 81a0770e97c7eb520971478fc7512e0e4e076b41d96803c8e3ace076b41d96803c8e3ace076b99ea77c`) strictly before writing `src/gems79/pfsd_features.py`, `src/gems79/pfsd_model.py`, or `scripts/run_pfsd.py`.
3. **Full Execution & Metrics (`scripts/run_pfsd.py`):**
   - `212 / 212` single-feature symmetric AUC leakage tests passed (`max = 0.8047 <= 0.90`).
   - `EXP-PFSD-1` (`0.0997 / 0.1134`) beat `H33` fold-fair (`0.0961 / 0.0989`) on **both seeds** with zero catalogue features; `EXP-PFSD-2` (`0.1854 / 0.1751`) beat `EXP-79-2` (`0.1697 / 0.1686`) on **both seeds**; `EXP-PFSD-3` (`0.1886 / 0.1746`) trailed `EXP-79-3` (`0.1905 / 0.1944`) on Seed 30 (`25,679` dots).
   - Validated GeoTIFF (`23cc11b4…`) passed all 15 `validate_submission.py` checks (`EPSG:32611`, `3730x3292`, `float32`, `[0, 1]`, `0` NaN/Inf, `0` on `existing_faults.tif`) and cleared `GEMSDOE83` (`0.6534 <= 0.70`) and all `<= 45,000`-dot external sibling rasters.

---

## Pass 2 — Bug, Edge-Case & Irregularity Review and Fixes

1. **Caught & Fixed `float16` Overflow on High-Resistivity MT Channels (`src/gems79/pfsd_model.py`):**
   - Initial shard cast `.astype(np.float16)` overflowed raw `mt_res_*` (`> 65,504` $\Omega\cdot\text{m}$); changed `shards[q]["X"]` to `float32` (`~117 MB` total) and clamped `float16` buffers cleanly to `[-30000, 30000]` (`0` `RuntimeWarning`s across Seeds 20, 30, and Live).
2. **Caught & Fixed Unbiased Stage-1/Stage-2 Horvitz-Thompson Sampling & `300 m` Support Alignment (`IR-79-145`):**
   - Preserved `halo_pool` (`0 < q < 1`) with exact inverse-probability weights in `build_decontaminated_quadrant_shards`, replaced integer `np.roll` shifts with bilinear `_sparse_line_integral` + Hessian Sato tubularity, and aligned placement support (`d_known > 3.0 px`) with the `d_sim_vis > 3.0 px` flank-decontaminated training domain so `13,411` dots were no longer extrapolated into the untrained `2.0–3.0 px` collar.
3. **Caught & Fixed `(truth, pred)` Argument-Order Swap in `dti_binary` (`IR-79-144`):**
   - Discovered `scripts/run_g79_thvc.py:195, 237` passed `(truth, pred)` in reverse order to `metric.dti_binary(pred_bool, truth)`; fixed in `scripts/run_pfsd.py:189, 297` and logged in `reports/irregularities.md`.
4. **Flagged Prior Backlog Numeric Projections (`IR-79-143`) & Sealed Closed-Lane CLI Guard (`IR-79-147`):**
   - Flagged `research/hypotheses_post_thvc_backlog.md:21-25` in `reports/irregularities.md`, verified `scripts/run_pfsd.py` exits `2` (`No files changed.`) before `lightgbm` import when `experiment_state.json` is `closed`, and verified zero `/home/user/GEMSDOE79` machine paths in any JSON receipt.

---

## Pass 3 — Full Requirements Re-Check, Static Site & Suite Verification

- Verified `vendor/gems57/*` SHA-256s match `registry/template_pin.json` (`0` private fork modifications).
- Verified `README.md` preserves the verbatim original prompt at the bottom and displays an unmistakable `OK TO DOWNLOAD: YES` / `OK TO SUBMIT: NO` status banner at the top, matched by `docs/index.html` and `docs/executive-summary.html`.
- Verified `scripts/build_site.py`, `scripts/check_site.py`, `scripts/submission_status.py`, `scripts/verify_project.py` (`all_checks_passed: true`), full `pytest` suite, and live HTTP preview (`0.0.0.0`).
