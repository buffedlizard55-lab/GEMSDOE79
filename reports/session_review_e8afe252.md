# Session `e8afe252` PhD-Level Forensic & Three-Pass Verification Review — Lane `G79-CSHD` (`2026-10-22`)

- **Active branch:** `arena/e8afe252-gemsdoe79`
- **Method lane:** `G79-CSHD` (*Concealed Subsurface Half-Graben + Hydrothermal Conduit + Wallace Throw-Deficit + Okada Relay*; preregistered in [`registry/preregistration_g79_cshd.json`](../registry/preregistration_g79_cshd.json), SHA-256 `ee4745070d8abb93c87065fcdf8f24bf4f68fdeb10c7dbfd8d5589c634bbb373`)
- **Automated machine verdict (`run_card_cshd.json`):** **`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`** (`verdict: "negative"`, `submission_slots_used: 0`, zero human inspection required)

---

## 1. Forensic Synthesis: Why `H33` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) Achieved `0.2778` Historical Score vs `0.4413` Top Public Leaderboard Score

1. **Exact Metric Geometry & Why `H33` Beat Continuous Probability Maps (`evidence/h33_forensics.json`, `vendor/gems57/metric.py`):**
   - Official competition scoring uses the asymmetric **Distance-Tolerant Intersection (`DTI`)** metric with `alpha = 0.2` (false-positive weight), `beta = 0.8` (false-negative weight), and a `300 m` (`3.0 px`) triangular distance-decay kernel $K(d) = \max(0, 1 - d/3.0)$:
     $$\mathrm{DTI}(P, T) = \frac{\mathrm{TP}_w}{\mathrm{TP}_w + 0.2\,\mathrm{FP}_w + 0.8\,\mathrm{FN}_w}.$$
   - Because any single binary dot at pixel $x$ covers a radius-`3 px` (`~29`-pixel) disk under $\min_{p \in P} \|y - p\|_2$, emitting a dense continuous probability surface incurs `~10–30x` redundant `0.2 * FP_w` penalty on every pixel inside the same 300-m halo without increasing $\max$-kernel $\mathrm{TP}_w$.
   - `H33` (`GEMSDOE32`, SHA-256 verified in `evidence/h33_forensics.json`) discovered the sparse **Poisson-disk / skeletonized dot-lattice geometry (`d = 2.8 px` spacing, `37,654` binary `1.0` dots)** — dividing `FP_w` by an order of magnitude for any given fault corridor. Its historical reported score of `0.2778` comes from narrative cross-repo history (unverified by an organizer upload receipt in this repository), while the public leaderboard top score of **`0.4413`** belongs to another entrant (`evidence/official_sources.json`).
2. **Why `H33` Plateaus at `HOLDOUT-DTI = 0.0961 / 0.0989` Under Whole-Fault Buffered Holdout (`gems57-pooled-hide-v2`):**
   - Under `vendor/gems57/evaluate_holdout.py` (`buffer_px = 3`, `boundary_px = 12`), entire connected fault systems are withheld. Pure catalogue-extrapolation and uniform-spacing (`d = 2.8 px`) methods fail in two ways:
     1. **Positive-flank contamination (`61%–78%` false-negative label noise):** Unmapped strands flanking mapped faults are labeled `y = 0` in naive training sets, suppressing predicted probabilities precisely on relay ramps and stepovers.
     2. **Zero blind-basin & non-LiDAR scarp physics:** `24.99%` of the Nevada study footprint lacks `1-m` 3DEP LiDAR coverage (`lidar_present == 0`), where unmapped range-front piedmont faults and concealed alluvial-basin half-grabens can only be detected via **upward-deconvolved potential fields (aeromagnetics + gravity), DOE GDR `1391` shallow `2-m` temperature probes, K/eU adularia alteration, and road-deconfounded `10-m` 3DEP Wallace throw-deficit steps**.

---

## 2. Preregistered `G79-CSHD` Experimental Results (`gems57-pooled-hide-v2`, Zero Leakage)

All scores below are measured **`HOLDOUT-DTI`** (`evaluator_version = "gems57-pooled-hide-v2"`, `1,000` `20 km` spatial-block bootstrap draws; **not** leaderboard projections or `ORGANIZER-CONFIRMED` receipts):

| Arm | Emitted Dots | Seed 20 `HOLDOUT-DTI` (`n = 11,321`) | Seed 30 `HOLDOUT-DTI` (`n = 11,342`) | 2-Seed Mean | Key Finding |
|---|---:|---|---|---:|---|
| **`EXP-CSHD-3` (`G79-CSHD` Dual-Regime CC)** | **39,747** (live) | **`0.1924` `[0.1760, 0.2078]`** | **`0.2040` `[0.1852, 0.2209]`** | **`0.1982`** | **#1 all-time 2-seed mean; beats canonical `G79-THVC` on BOTH seeds (`2.03x H33`)** |
| Canonical `G79-THVC` (incumbent bar) | 35,093 | `0.1905` `[0.1741, 0.2069]` | `0.1944` `[0.1774, 0.2126]` | `0.1925` | Prior canonical benchmark |
| Archived `G79-CSKD` (`session 6da2620c`) | 40,000 | `0.1781` `[0.1619, 0.1944]` | `0.2145` `[0.1965, 0.2330]` | `0.1963` | Trailed `G79-THVC` on Seed 20 (`-0.0124`) |
| `EXP-CSHD-2` (`CSHD` + uniform `d = 2.8 px`) | 37,654 | `0.1590` `[0.1419, 0.1763]` | `0.1791` `[0.1622, 0.1970]` | `0.1690` | Isolates submodular kernel-cover gain (`+0.0292`) |
| **`EXP-CSHD-1` (Pure 80-ch Zero-Catalogue Physics)** | 37,654 | **`0.0992` `[0.0809, 0.1176]`** | **`0.1095` `[0.0921, 0.1256]`** | **`0.1043`** | **Surpasses `H33` on BOTH seeds with ZERO fault catalogue pixels** |
| `C2` (`H33` Fold-Fair Control) | 38,802 / 38,829 | `0.0961` `[0.0831, 0.1090]` | `0.0989` `[0.0854, 0.1128]` | `0.0975` | `GEMSDOE32` structural baseline |
| `C1` (`E1` Fabric-Offset Placed) | 37,654 | `0.0441` `[0.0370, 0.0512]` | `0.0440` `[0.0371, 0.0517]` | `0.0441` | Prior isotropic fabric control |
| `C0` (Uniform Random `37,654` Dots) | 37,654 | `0.0497` `[0.0433, 0.0561]` | `0.0422` `[0.0378, 0.0465]` | `0.0460` | Chance baseline |

---

## 3. Summary of the Three Distinct Audit & Verification Passes

1. **Pass 1 — Code, Math, Data Provenance & Live `origin/main` Regression Audit (`IR-79-232..238`):**
   - Verified SHA-256 checksums across all `31` geospatial inputs + `1,223` cross-repo registry rasters (`93` GEMS repositories) and cleared all `98 / 98` single-feature leakage canaries (`max symmetric AUC = 0.8043 <= 0.90`).
   - Found and fixed six concrete numerical/statistical bugs in feature/model code (`-FLT_MAX` FFT sentinel corruption `IR-79-233`, inner `sim_vis` convolution `IR-79-234`, Horvitz-Thompson sample weight scaling `IR-79-235`, `[-6, 6]` scaler outlier saturation `IR-79-236`, flat-wash quantile floor `IR-79-237`, `float16` pre-clipping & `GDAL_CACHEMAX=32` `IR-79-238`).
   - Detected and repaired a live CI failure on `origin/main` (`6e3ca91`, `IR-79-232`) caused by unregistered `docs/tipstep-submission.html`.
2. **Pass 2 — Both-Validator Format Verification (`R1–R8` `NaN`-Exterior + `15/15` `0.0`-Exterior) & Visual Typography Audit (`IR-79-239..240`):**
   - Verified `g79-cshd-dualcc-20261022-8a4788c4-nan-DO-NOT-SUBMIT.{tif,zip}` passes **`8 / 8` rules (`R1–R8`)** of `src/gems79/portal_spec.py` (`gems79-portal-format-v2`), guaranteeing zero interior `NaN`/`Inf`, exact `[0.0, 1.0]` `float32` values inside the footprint, and exact `NaN` exterior matching `sample_submission.tif`.
   - Visually inspected `docs/figures/fig6_cshd_two_seed_record.png` and `docs/figures/fig7_cshd_map_and_uniqueness.png` and fixed error-bar label clearances and right-axis title framing (`0` text overlaps).
3. **Pass 3 — End-to-End Test Suite, Site Link Graph, Headless Browser QA & Git Cleanliness Verification:**
   - Full `pytest` suite, `scripts/verify_project.py`, `scripts/check_site.py`, `scripts/verify_public_site.py`, and headless Chromium `scripts/browser_review.cjs` all pass with zero warnings/errors.

---

## 4. Explicit Limitations & Concrete Next Steps

- **Why `OK TO SUBMIT` Remains `NO` (`verdict = negative`):** Although `G79-CSHD` clears `GEMSDOE83` (`0.6591 <= 0.70`), `GEMSDOE77` (`0.6952 <= 0.70`), `GEMSDOE80` (`0.6494 <= 0.70`), and `GEMSDOE78` (`0.6237 <= 0.70`) under Amendment D-2, it exceeds `0.70` on `16 / 1,209` legacy dense corridor rasters (worst external `0.8182` on `59GEMSDOE` `77,727` dots) and faces `1.0000` overlap on the full-footprint coverage witness under the unamended literal rule. We never post-hoc halo-cap or jitter dots to disguise overlap, and spend `0` weekly submission slots.
- **Concrete Next Steps:**
  1. Owner protocol decision on retiring saturated/corridor archive rasters (>50k dots) or adopting pure blind-basin geophysical evaluation where `EXP-CSHD-1` (`0.0992 / 0.1095`) already outperforms `H33` with zero catalogue input.
  2. Incorporate full 3D MT resistivity (`USArray` / `INGENIOUS` magnetotelluric conductors) and InSAR vertical velocity gradients to bridge `0.2040 -> 0.25+` `HOLDOUT-DTI` in blind alluvial basins.
