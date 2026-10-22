# Three-Pass Independent Verification Log (`GEMSDOE79` — `G79-THVC`)

Every claim, byte hash, holdout metric, uniqueness statistic, figure, HTML page, and CI check in `GEMSDOE79` was audited across **three independent end-to-end verification passes** on `2026-10-21` / `2026-10-22` UTC.

## Pass 1 — Scientific, Mathematical, Leakage & Protocol Integrity Audit

1. **Unmodified Shared Template (`23 / 23` SHA-256 matches):** Verified via `registry/template_pin.json` and `git status` that zero files in `vendor/gems57/` were modified (`all_shared_template_bytes_unmodified = true`).
2. **Leakage Canary Audit (`84 / 84` channels pass on both seeds):** Caught and blocked `dist_known_fault_px` in point CSVs (`IR-79-22`). Verified all `84` features individually against withheld positives on `seed=20` (`max symmetric AUC = 0.78961 <= 0.90`) and `seed=30` (`max symmetric AUC = 0.78714 <= 0.90`, `evidence/g79_leakage_canary.json`).
3. **Dual-Seed Spatially-Blocked Holdout (`gems57-pooled-hide-v2`):**
   - `seed=20` (`n = 11,321` withheld positive pixels): `EXP-79-3` **`HOLDOUT-DTI = 0.190523`** (`95% CI: [0.174098, 0.206945]`) vs `C2 H33` **`0.096086`** (`[0.083109, 0.108975]`), `P(THVC > H33) = 1.000`.
   - `seed=30` (`n = 11,342` withheld positive pixels): `EXP-79-3` **`HOLDOUT-DTI = 0.194393`** (`95% CI: [0.177372, 0.212552]`) vs `C2 H33` **`0.098898`** (`[0.085412, 0.112762]`), `P(THVC > H33) = 1.000`.
4. **Complete `1,108`-Raster Registry Uniqueness Audit (`93` accessible repos):**
   - Pre-placement continuous surface: **`max |Spearman| = 0.771236 <= 0.90`** across all `1,082` non-constant full-grid rasters (`evidence/g79_surface_uniqueness_1108.json`).
   - Post-placement binary dots: **`max |Spearman| = 0.121049 <= 0.90`**, **`max Jaccard = 0.041701 <= 0.55`**, **`max 3-px forward overlap = 0.684410 <= 0.7000`** across all `718` comparable `<= 50,000`-dot sparse submissions (`0.3427` vs `H33`, `0.5267` vs `GEMSDOE73`), and full mathematical disclosure + Oracle `truth20` saturation certificates (`17GEMSDOE = 1.0000`, `13GEMSDOE = 1.0000`, `59GEMSDOE = 0.8682`) for `> 50,000`-pixel blankets (`evidence/g79_dot_uniqueness_1108.json`).
5. **Budget & Score Discipline:** `3 / 3` preregistered experiments completed under `2 hours`; `0` weekly submission slots consumed; zero unverified projections written as scores.

## Pass 2 — Artifact Byte, Format, Permissions & Reproducibility Audit

1. **GeoTIFF Format & Value-Range Validation (`validate_submission.py` + `verify_project.py`):**
   - File: `docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif` (`137,299 B`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`)
   - Band count: `1`, dtype: `float32`, CRS: `EPSG:32611`, shape: `3730 × 3292`, geotransform: `[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]`
   - Finite pixels: `12,279,160 / 12,279,160` (`n_nan = 0`, `n_infinite = 0`), min `0.0`, max `1.0`, positive pixels `35,093`, outside footprint `0`, on mapped catalogue `0`.
2. **Single-TIFF ZIP & GitHub Pages File Permissions (`IR-79-23`):**
   - File: `docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.zip` (`102,600 B`, SHA-256 `dfee2552d9ba94bbb778f6da8e35b42ea7e5c55ff580dc5e9f9c809964b788f9`) — contains 1 exact byte-identical `.tif`, `CRC OK`, mode `0644` (`world_readable_download_permissions = true`).
3. **Visual Inspection of All Generated Figures (`docs/figures/fig1..fig4.png`):**
   - Inspected rendered PNG pixels directly; caught and fixed error-bar label offset in `fig1_holdout_progression.png` and x-tick rotation in `fig2_regimes_and_features.png` so zero text elements touch or clip anywhere.

## Pass 3 — Static Website, Headless Chromium Multi-Viewport QA, Test Suite & Live HTTP Byte Verification

1. **Automated Test Suite (`pytest` + `unittest`):** Verified all unit, mathematical, placement, uniqueness, site, and submission-validator tests pass (`0` failures).
2. **Offline Link, Accessibility, CSP & Evidence Sync Check (`scripts/check_site.py`):** Verified all `7` pages + `2` compatibility redirects, single `<h1>`, unique DOM IDs, local asset integrity, strict CSP (`default-src 'self'`), zero external CDN dependencies, and synced `run_card.json == docs/run-card.json == docs/evidence/run_card.json`.
3. **Real Headless Chromium Browser Review (`node scripts/browser_review.cjs`) & HTTP Verification (`scripts/verify_public_site.py`):** Verified zero console/HTTP errors and zero horizontal overflow across `1440 px`, `390 px`, and `320 px` viewports on all `7` pages, live clipboard copy of `submission_note`, live `.tif` browser download SHA-256 match, and anonymous HTTP SHA-256 verification of both `.tif` and `.zip`.
