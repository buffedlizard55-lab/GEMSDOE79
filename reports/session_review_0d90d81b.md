# Autonomous Repository Review, Post-`04:31Z` Sibling Forensics, and Untried Hypothesis Synthesis (`arena/0d90d81b-gemsdoe79`)

- **Review date (UTC):** `2026-10-22`
- **Branch:** `arena/0d90d81b-gemsdoe79`
- **Canonical downloadable artifact (`G79-THVC`):** `docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif` (`137,299 B`, `35,093` positive off-catalogue pixels, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`; companion `.zip` `102,628 B`, SHA-256 `dfee2552d9ba94bbb778f6da8e35b42ea7e5c55ff580dc5e9f9c809964b788f9`)
- **Automated decision status:** **OK TO DOWNLOAD: YES** (`15/15` local GeoTIFF format/range/CRS/transform checks PASS) · **OK TO SUBMIT: NO** (`scripts/submission_status.py` exit `2`; `scripts/select_submission.py` exit `2`; `scripts/preflight_new_lane.py --restore` exit `2` `STOP`; `0` weekly submission slots consumed)
- **Pinned forensic receipts:** `evidence/session_0d90d81b_audit.json` and `evidence/session_0d90d81b_run_card.json` (reproducible via `scripts/audit_session_0d90d81b.py`)

---

## 1. Execution of Previous-Session Next Steps & Defect Remediation

1. **Start-of-session protocol & prompt preservation:** Read `AGENTS.md`, `README.md` (including the verbatim `## Original project prompt`), `run_card.json`, `reports/irregularities.md` (`IR-79-01`..`IR-79-172`), and recent session reviews (`e4a4422d`, `f0d99a40`, `b40c0d45`, `1db538e6`). Fast-forwarded `arena/0d90d81b-gemsdoe79` onto concurrent `origin/main` (`7f5d6e3`, incorporating merged PRs `#89`–`#95`; open `PR #67` `H79-ARC` remains unmerged per `IR-79-164`).
2. **Autonomous data restoration & E1 feature reproduction (`IR-79-174`):** Executed `.venv/bin/python scripts/restore_data.py --preserve-receipt`, `bash scripts/download_competition_data.sh`, and `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/prepare_data.py --reproduce`. All `13/13` SHA-256-pinned competition and external files (`5` core GeoDAWN/fault rasters + `8` LiDAR/radiometric/GDR-1391/SGMC/TIGER inputs) restored cleanly and all `8/8` E1 normal bands reproduced byte-deterministically with `0` git-tracked files dirtied — refuting claims in `reports/session_review_b40c0d45.md` and `reports/review_20261022.md` that raw competition data cannot be restored in this sandbox.
3. **Hardened `scripts/measure_registry_halo.py` & reconciled `6,649 vs 6,514` (`IR-79-173`):** PR `#95` wrote `/home/user/GEMSDOE79/` into `footprint_path` in `evidence/halo_saturation_*_1db538e6.json` and measured `allowed_cells_finite_footprint = 5,167,373` without subtracting the `60,988` mapped catalogue pixels (`existing_faults > 0`). Adding `--catalogue` (`data/reference/existing_faults.tif`) and repo-relative path normalization reconciles the exact numbers: `5,167,373 - 60,988 = 5,106,385` allowed off-catalogue cells, and on `13GEMSDOE` spacing-5 lattice (`c12533bb...`), `6,649` uncovered finite-footprint cells minus `135` uncovered on-catalogue cells equals **`6,514` uncovered off-catalogue cells (`0.1276%`)**.
4. **Hardened `scripts/scan_tracked_rasters.py` (`IR-79-174`):** Separated `29` tracked prediction GeoTIFFs (`flagged_prediction_artifacts = []`, `0` `[0, 1]`/NaN/Inf errors) from `7` tracked reference input masks (`existing_faults.tif` / `labels.tif` carrying `-1.0` nodata).

---

## 2. Post-`04:31Z` Cross-Repository Census (`1,201` Blobs) & Sibling Byte Forensics (`IR-79-175`)

Scanning all `14` `GEMS*` repositories pushed on `2026-10-22` across `refs/heads/*`, `refs/tags/*`, and `refs/pull/*` via `scripts/registry_delta_git.py` identified **exact two** non-self prediction GeoTIFF blobs created after the frozen `registry/registry_delta.json` snapshot (`2026-10-22T04:31:19Z`, `207` blobs), both in `buffedlizard55-lab/GEMSDOE78`, raising verified non-self family prediction rasters to **`992 + 207 + 2 = 1,201`** across `93` accessible non-self `GEMS*` repos:

| Artifact | Repo & bucket | SHA-256 (prefix) | Bytes | Off-cat dots | `d_cat` `p10 / p50 / p90` (m) | `<= 500 m` / `> 2 km` | `G79-THVC -> B` `3 px` | `B -> G79-THVC` `3 px` | Spearman `rho` vs `G79-THVC` |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- | ---: | ---: | ---: |
| `H33` (`h33-2-b2`) | `GEMSDOE32` (`index`) | `c55bafc47005...` | `219,065` | `37,654` | `400.0 / 1964.7 / 6800.7` | `14.97% / 49.20%` | `0.3427` | `0.2841` | `0.0179` |
| `H78-SIGX` | `GEMSDOE78` (`index`) | `0b9cbb580dd8...` | `141,096` | `44,090` | `500.0 / 2119.0 / 7071.1` | `10.40% / 51.83%` | `0.1596` | `0.1771` | `0.0023` |
| `H78-GSC` | `GEMSDOE78` (`delta`) | `e2f21d496925...` | `147,599` | `40,000` | `412.3 / 761.6 / 2247.2` | `30.67% / 12.43%` | `0.6818` | `0.5857` | `0.0615` |
| `H78-MGHD` | `GEMSDOE78` (`post-04:31Z`) | `44429c439118...` | `158,254` | `44,090` | `316.2 / 670.8 / 2765.9` | `39.53% / 15.30%` | `0.6703` | `0.5161` | `0.0315` |
| `H78-GFV` | `GEMSDOE78` (`post-04:31Z`) | `0338383df9c3...` | `147,086` | `37,654` | `424.3 / 1140.2 / 6010.8` | `23.42% / 38.84%` | `0.5870` | `0.4320` | `0.0431` |

### Critical Methodological Finding: In-Quadrant Training Inflation vs Strict 3-Quadrant LOQO

- **`GEMSDOE78` (`H78-GFV`) headline vs strict LOQO:** `GEMSDOE78/run_card_h78_gfv.json` reports `0.2149` (Seed 20) and `0.2198` (Seed 30) from `scripts/run_gfv_matched_global_benchmark.py`, which trains its LightGBM ensemble **globally across all 4 quadrants including unhidden faults inside the evaluation quadrant** (`CTRL_A2 = 0.1826`), and modifies shared `emit.py` / `uniqueness.py`. In `GEMSDOE78`'s own strict 3-quadrant Leave-One-Quadrant-Out receipts (`evidence/h78gfv_holdout_seed{20,30}.json`), `H78-GFV` scores **`0.1700` `[0.1548, 0.1847]`** (Seed 20) and **`0.1778` `[0.1615, 0.1934]`** (Seed 30) — **`-0.0205` and `-0.0166` below canonical `GEMSDOE79` `G79-THVC` (`0.1905` / `0.1944` strict LOQO)**! Global 4-quadrant in-sample training inflates apparent `HOLDOUT-DTI` by `+0.0450` / `+0.0420` via intra-basin geophysical autocorrelation.
- **`GEMSDOE83` (`H83-GVCD`) genuine strict-LOQO improvement & gate block (`IR-79-176`):** `GEMSDOE83` achieved **`0.1999` `[0.1824, 0.2180]`** (Seed 20) and **`0.2138` `[0.1966, 0.2314]`** (Seed 30) under **strict 3-quadrant LOQO**, driven by two mathematically sound mechanisms missing from `G79-THVC`:
  1. **Scarp-flank negative decontamination:** In `src/gems79/thvc_model.py` line 92, `sim_active = footprint & ~sim_known` samples `y = 0, q = 0` training negatives at `100-300 m` (`1 <= d_vis <= 3 px`) from unhidden visible faults where physical fault-zone gradients remain strong; excluding `d_vis <= 3.0 px` from negative sampling prevents the classifier from suppressing near-fault flanks.
  2. **Exact Dinkelbach fractional-programming iteration:** Replacing fixed `lambda_fp = 0.0022` with outer Dinkelbach updates `lambda(theta_t) = 0.2 * theta_t / (1 - 0.2 * theta_t)` aligns greedy dot selection with the non-additive Distance-Weighted Tversky ratio (`alpha = 0.2`, `beta = 0.8`).
  However, `H83-GVCD` fails the shared novelty gate (`0.8514 > 0.70` forward `3 px` overlap against `coverage-v3-wide`) and relied on a private `OVERLAP_CAP = 0.650` fork (`IR-79-122`), so it cannot be promoted under unmodified shared rules.

---

## 3. PhD-Level Synthesis: Why `GEMSDOE32` (`H33`) Reported `0.2778` and How to Surpass `0.2778` / `0.4413`

1. **What `H33` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, SHA-256 `c55bafc4...`) actually is:**
   - **Provenance:** `0.2778` is an **UNVERIFIED HISTORICAL REPORT** (self-labelled `UNSCORED` on `GEMSDOE32`'s public site without an organizer submission-page receipt; `knowledge/h33_review_e4a4422d.md`).
   - **Exact byte algebra:** `H33` (`37,654` dots) is byte-for-byte identical to `GEMSDOE25/32` `D2.8` (`44,090` dots, spaced `>= 2.8 px` along ridge centerlines) minus the **`6,436` off-catalogue dots within `<= 2.0 px` (`200 m`) of `existing_faults.tif`** (`0` dots sat on `existing_faults > 0`).
   - **Conditional metric physics:** Under Distance-Weighted Tversky (`DTI = T / (T + 0.2 * F + 0.8 * G)`), truth credit `c_j = max_i y_i K(d_ij)` uses a `max` operator while false-positive cost `F = sum_i y_i (1 - max_j K(d_ij))` sums linearly. Pruning `6,436` near-catalogue (`<= 200 m`) dots improves `DTI` if and only if `0.2 * T * b > a * (0.2 * F + 0.8 * G)`, i.e., when the organizer's hidden test catalogue contains fewer immediate `<= 200 m` parallel halo pixels than `D2.8` emitted, while keeping `49.20%` of `H33`'s `37,654` dots at `d_cat > 2,000 m` across basin interiors (`p50 = 1,964.7 m`, vs `G79-THVC`'s `p50` concentrated near visible-fault tip cones!).
2. **Why `G79-THVC` (`0.1905 / 0.1944` `HOLDOUT-DTI`) beats `H33` (`0.0961 / 0.0989`) on catalogue holdout yet risks under-covering unmapped basin interiors:**
   - Catalogue holdout withholds whole spatial segments of `existing_faults.tif`, where visible-fault tip continuation (`net_tip_fwd_35px`, leakage canary `AUC = 0.8036`) carries high predictive power because segmented normal faults propagate along strike.
   - By contrast, expert-curated Phase 1 test faults (`DD-PROBLEM`, `USGS-QFAULTS` DOI `10.5066/P9BCVRCK`) also include **isolated intrabasinal, sub-alluvial, playa-buried, and volcanic-plateau faults (`d_cat > 2 km`)** lacking nearby mapped endpoints. Over-relying on `d_vis` continuation features starves isolated basins (`H78-GSC` placed only `12.43%` of dots beyond `2 km`), whereas combining **catalogue-free multi-physics/hydrothermal cues** with **scarp-flank decontamination (`d_vis > 3 px`) + exact Dinkelbach allocation** (`G79-SFGC` + `G79-UGBP` + `G79-MDSC` + `G79-PSDC` + `G79-MCST`, detailed in `research/hypotheses_0d90d81b.md`) targets both tip-bridging relays and isolated blind faults without in-quadrant leakage.
3. **What separates `0.2778` from live public `#1 xiaofanhu` (`0.4413` `PUBLIC-OBSERVATION`):**
   - At `alpha = 0.2, beta = 0.8`, moving from `DTI approx 0.28` to `0.44` requires simultaneously raising `300 m` buffered recall `R_w = T / (T + G)` from `~0.25-0.30` into the `0.42-0.52` regime while keeping buffered precision `P_w = T / (T + F)` high via (i) **2D spatial context segmentation** (multi-scale U-Net / Swin / ConvNeXt trained directly with differentiable soft-kernel Tversky loss rather than pixel-wise tubular summary statistics), (ii) **full-resolution 1-m 3DEP / NAIP / Sentinel-2 imagery & InSAR deformation products** across the `24.99%` Nevada LiDAR gap, and (iii) **1D thin-skeleton non-maximum suppression + exact Dinkelbach `2.8-3.2 px` spacing** so zero duplicate parallel dots waste `0.2 * F` denominator budget along any single predicted trace.

---

## 4. Audited Official Sources & Live Leaderboard (`2026-10-22`)

| Source ID | Official URL | Evidence / Access Status (`2026-10-22`) | Key Verified Fact |
| :--- | :--- | :--- | :--- |
| `DD-PROBLEM` | `https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/` | Verified via research fetch (`knowledge/official_sources.json`) | Single-band `float32` GeoTIFF, `EPSG:32611`, `100 m`, values in `[0, 1]`, DW-Tversky `alpha = 0.2`, `beta = 0.8`, `300 m` triangular kernel. |
| `DOE-RULES` | `https://docs.nlr.gov/docs/fy26osti/96647.pdf` | Verified via research fetch | Up to `3` scoring submissions/week; `1` final entry per participating entity; AI disclosure & full reproducibility required. |
| `DD-NEW-FAULT-DEF` | `https://community.drivendata.org/t/where-do-you-draw-the-line/11536/2` | Verified via research fetch (`4` staff threads) | Along-strike continuations, splays, and parallel strands not in USGS/INGENIOUS count as new faults; Phase 2 (`$250k`) updates labels via expert geological review. |
| `DD-LEADERBOARD` | `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/` | All `3` chunks re-read live on `2026-10-22` (`PUBLIC-OBSERVATION`) | `#1 xiaofanhu 0.4413` (`27` subs), `#2 cfld__ 0.3904`, `#3 Batik Shirt Brothers 0.3894`, `#21 kinghorton42 0.3261` (`21` teams `> 0.3195`), `#48 moongrega 0.2818`, `#49 arnofault 0.2817`, `#50 sam35 0.2804`. |
| `USGS-GEODAWN` | `https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and` | Verified (`DOI: 10.5066/P93LGLVQ`) | Airborne magnetic + gamma-ray (`K`, `Th`, `U`) + LiDAR surveys across NW Nevada / SE Oregon. |
| `GDR-1391` | `https://gdr.openei.org/submissions/1391` | Verified (`DOI: 10.15121/1881483`) | DOE INGENIOUS Great Basin dataset (`27,092` well/spring records, `2,782` 2-m temperature probes, `281` paleo-geothermal vents). |
| `USGS-QFAULTS` | `https://www.usgs.gov/programs/earthquake-hazards/faults` | Live-fetched on `2026-10-22` (`DOI: 10.5066/P9BCVRCK`) | Targets `M > 6` Quaternary surface-rupturing faults with simplified hazard traces — explaining blind/relay/playa omissions. |
| `UNR-NGL-MIDAS` | `https://geodesy.unr.edu/` | Live-fetched on `2026-10-22` (`DOI: 10.1029/2018EO104623`) | Open-access MAGNET/MIDAS North America GPS velocity field (`midas.NA.txt`); requires owner mirror staging for sandbox ingestion. |

---

## 5. Explicit Three-Pass Execution & Audit Log

- **Pass 1 (Implement & Verify):** Restored all `13/13` SHA-256-pinned inputs and reproduced `8/8` E1 normal bands; scanned all `14` `2026-10-22`-updated `GEMS*` repos (`1,201` total non-self prediction blobs); hardened `scripts/measure_registry_halo.py` (`--catalogue`, repo-relative paths) and `scripts/scan_tracked_rasters.py` (`role` classification); created `scripts/audit_session_0d90d81b.py` generating `evidence/session_0d90d81b_audit.json` and `evidence/session_0d90d81b_run_card.json`; updated source ledgers (`knowledge/official_sources.json`, `knowledge/review_e4a4422d_sources.json`, `docs/evidence/source_health.json`), authored `research/hypotheses_0d90d81b.md` and `IR-79-173`..`IR-79-177`, and wired `scripts/build_site.py` + `README.md`.
- **Pass 2 (Adversarial Bug, Assumption & Edge-Case Audit):** Caught and corrected `H33` blob alias ambiguity (`17a76895...` / SHA-256 `c55bafc4...` in `GEMSDOE32/docs/downloads` vs `bef89913...`), reconciled `G79-THVC` `official_evaluate_all` precision in `audit_session_0d90d81b.py`, verified zero `/home/user/GEMSDOE79` checkout leaks across all newly generated/modified JSON receipts, preserved `gems79/evidence_summary.py` `SOURCES` SHA-256 pins and `verify_project.py` `992 + 207 = 1,199` frozen-snapshot coupling, added adversarial unit tests (`tests/test_session_0d90d81b_audit.py`), and executed Playwright multi-viewport QA (`1440`, `390`, `320` px).
- **Pass 3 (Full Prompt & Gate Re-Verification):** Re-checked every requirement of the original prompt and `AGENTS.md` (`pytest -q`, `verify_project.py`, `submission_status.py`, `select_submission.py`, `check_site.py`, `preflight_new_lane.py --restore`, single `docs/downloads/` pair, byte-identical `4x run_card.json`, verbatim single `## Original project prompt` heading with zero trailing lines after `</details>`), opened and merged PR onto `main`, and verified post-merge `main`.

---

## 6. Remaining Limitations & Owner Decisions Required

1. **Novelty-gate obstruction (`IR-79-116`):** No candidate raster in `GEMSDOE79` or any sibling repo can pass the literal `1,201`-raster `<= 0.70` `3 px` forward-overlap gate because `17GEMSDOE:E-proba-multiscale` (`100%` support), the `budget-matched-v3` dense union (`100%`), and `13GEMSDOE` spacing-5 lattices (`99.87%` off-catalogue halo) saturate the footprint. Selecting a prospective gate amendment and assigning a delimited lane paragraph remain owner decisions.
2. **External portal boundaries:** DrivenData login-protected pages (`/data/`, `/submissions/`) cannot be accessed without account credentials; no artifact in this repository has an `ORGANIZER-CONFIRMED` portal score or live weekly slot count, and `UNR-NGL-MIDAS` (`midas.NA.txt`) + `USGS-HEAT-RESIDUALS` (`10.5066/P9BZPVUC`) require owner mirror staging before sandbox execution.
