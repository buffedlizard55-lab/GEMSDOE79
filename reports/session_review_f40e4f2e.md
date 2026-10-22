# Session review `f40e4f2e` — canonical selector completion, autonomous data/cache verification, and exact ETP forensic audit

Date: 2026-10-22 (UTC)  
Branch: `arena/f40e4f2e-gemsdoe79`  
Pull request: `https://github.com/buffedlizard55-lab/GEMSDOE79/pull/71`

## Executive decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The canonical GeoTIFF remains the byte-unique and pixel-unique `G79-THVC` research candidate (`docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`, `35,093` binary `{0.0, 1.0}` pixels, `0` NaN/Inf, `0` outside footprint, `0` on mapped catalogue). It is locally format-valid (`15 / 15` checks), clears all `84 / 84` single-feature leakage canaries (`max AUC = 0.8036 <= 0.90`), beats the fold-fair `H33` benchmark on both spatial holdout seeds (`HOLDOUT-DTI = 0.1905` `[0.1741, 0.2069]` vs `0.0961` on Seed 20 `n=11,321`; `0.1944` `[0.1774, 0.2126]` vs `0.0989` on Seed 30 `n=11,342`), and clears all `718` comparable sparse (`<= 50,000`-dot) registry submissions (`max forward 3-px overlap = 0.6844 <= 0.70`), **but it fails the unchanged literal 3-pixel registry-overlap gate** against space-filling / lattice registry witnesses (`1.0 > 0.70`).

No new raster was generated, no new scientific experiment was started, and **zero weekly DrivenData submission slots were spent** because the mandatory preflight (`scripts/preflight_new_lane.py --restore`, `exit 2`) proves that every nonempty raster fails the literal overlap gate. Under Protocol Rule 5, negative results are deliverables; the canonical terminal JSON card remains [`run_card.json`](../run_card.json).

---

## 1. Why a new “unique” TIFF cannot truthfully be produced under the unchanged literal rule

The hash-pinned registry witness `17GEMSDOE:E-proba-multiscale-20261001T000000Z-f2ef3065.tif` (`sha256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) has positive support on **every** `5,106,385` allowed off-catalogue footprint cell (`100.0%`), and sparse binary `dot_field` `13GEMSDOE:13gems_20261001_r13-lattice-s5_v2_zerofill.tif` (`sha256: c12533bb980234c3a706af641d4f1d514bbbe482714b2ebcac3b10f3e72a7a3f`, `206,895` dots) covers `5,099,871 / 5,106,385` allowed cells (`99.8724%`) within `3 px`, leaving only `6,514` uncovered allowed pixels across Nevada & California (Pigeonhole lower bound `>= 0.8144` for any `35,093`-dot map and `>= 0.8270` for any `37,654`-dot map). Changing model physics, features, spacing, or random seed cannot alter that mathematical bound; silently adopting a density-adjusted rule to approve a finished lane would violate the protocol.

Machine reproduction:

```bash
.venv/bin/python scripts/preflight_new_lane.py --restore  # exit 2
.venv/bin/python scripts/select_submission.py             # exit 2
.venv/bin/python scripts/submission_status.py              # exit 2
```

---

## 2. Why `H33` (`0.2778` historical report) outperformed dense maps — and why `"Predicted values must be in range [0, 1]"` occurred

1. **Exact byte forensics of `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`, [`evidence/h33_forensics.json`](../evidence/h33_forensics.json)):** `H33` (`37,654` binary `1.0` pixels) is pixel-identical to `D2.8` (`44,090` binary `1.0` pixels) after zeroing the `6,436` pixels at Euclidean distance `<= 200 m` (`2.0 px`) from `existing_faults.tif` (`0` pixels outside `D2.8`). Under the official Distance-Weighted Tversky Index (`DTI`, `alpha = 0.2`, `beta = 0.8`, `r = 300 m` triangular kernel; [NLR/DOE Prize Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [reference repo](https://github.com/drivendataorg/gems-prize-reference-solution)), weighted true positives take a point-wise **maximum** over nearby predictions (`k_300m * p`), whereas weighted false positives **sum** `(1 - q_300m) * p` across every emitted pixel. Converting diffuse probability surfaces into spaced binary `{0, 1}` impulses eliminates cumulative false-positive halo mass, and excising the `<= 200 m` collar around mapped faults removes redundant flank penalties where `existing_faults.tif` is masked at scoring.
2. **Evidence-class discipline:** `0.2778` is an **unverified historical filename-to-score report** in the prompt ledger (not `ORGANIZER-CONFIRMED`, because no submission-page receipt is bound to it); `0.3195` is an older snapshot inside one prompt paragraph; `0.4413` (`xiaofanhu`, Rank #1) is a verified **public leaderboard observation** on [DrivenData](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (`2026-10-22`, [`knowledge/official_sources.json`](../knowledge/official_sources.json)). Local `HOLDOUT-DTI` (`gems57-pooled-hide-v2`) proves `G79-THVC` beats fold-fair `H33` by `+98.3%` (`Seed 20`) and `+96.6%` (`Seed 30`) on local spatial holdout, which is **not** a projection or guarantee of a private/public organizer score above `0.2778` or `0.4413`.
3. **Root cause of DrivenData error `"Predicted values must be in range [0, 1]"`:** Historical `-nan.tif` variants filled out-of-footprint cells with `NaN` (or nodata sentinels such as `-9999`), which fail strict `0 <= x <= 1` array checks (`NaN >= 0` is `False`). Canonical `g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif` stores `12,279,160` finite `float32` pixels strictly in `{0.0, 1.0}` with `nodata = None` and `0` `NaN`/`Inf` anywhere (`15 / 15` format checks pass).

---

## 3. Five ranked untried geological hypotheses reviewed before implementation

Reviewed and verified against [`research/hypotheses_post_thvc_backlog.md`](../research/hypotheses_post_thvc_backlog.md) (no experiment run because preflight exited `2` before Experiment 1):

1. **`H80-MT-PHASE` (re-scoped to crust/upper-mantle conductance gradients per `IR-79-149`, medium cost):** Couples lateral magnetotelluric conductance gradients (`2–12 km` and `12–20 km` depth-integrated conductance layers on USGS ScienceBase `doi:10.5066/P9TWT2LU` / DOE INGENIOUS [GDR Submission 1391](https://gdr.openei.org/submissions/1391), `DOI: 10.15121/1881483`) with `training_features.tif` horizontal gravity gradient (`iso_grav_anom_hg`) normal colinearity to resolve blind range-front/playa conduits where surface scarps and shallow magnetic anomalies are muted. *Data verification:* `gdr_wellspring_in_footprint.csv` and `training_features.tif` are present in `registry/data_manifest.json`; the `2–12 km` MT conductance grids (`doi:10.5066/P9TWT2LU`) require external ScienceBase ingestion before testing.
2. **`H80-DRAPE-DECONV` (Rank #2 — medium-high gain across the `24.99%` non-LiDAR gap, low-medium cost):** Applies directional `400 m` E–W flight-line notch filtering + variable drape-height magnetic upward-continuation deconvolution on [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) (`training_features.tif` + `geodawn_extensions_u8.tif`) to separate `100–500 m` intrasedimentary fault offsets from `> 2 km` plutonic edges and terrain-clearance artifacts. *Data verification:* `training_features.tif` and `geodawn_extensions_u8.tif` are hash-pinned and verified (`evidence/data_and_pipeline_verification_f40e4f2e.json`); raw line-by-line radar-altimeter clearance channels from USGS ScienceBase (`doi:10.5066/P9XBBBUU`) would strengthen full drape inversion.
3. **`H80-RADIO-KD` (Rank #3 — medium gain on sealed/epithermal faults, low cost):** Cross-fitted lithology-normalized potassic adularia alteration residual $K - \hat{f}(\text{eTh}, \text{eU}, \text{elev}, \text{slope})$ on `geodawn_rad_u8.tif` (`%K`, `eTh`, `eU`) paired with localized magnetic demagnetization troughs (`rtp_demag_trough`), isolating potassium metasomatism along sealed paleo-conduits from felsic ash-flow tuff host rock (`high K + high Th`). *Data verification:* 100% obtainable from already-pinned `geodawn_rad_u8.tif` + `training_features.tif`.
4. **`H80-SLIP-DEFICIT` (Rank #4 — medium gain on unmapped piedmont transfer faults, low-medium cost):** Along-strike range-front footwall topographic relief vs fold-visible cumulative mapped fault trace density + `depth_to_base_surf` gradient inversion, targeting unmapped basinward piedmont faults carrying strain across mapped trace gaps. *Data verification:* 100% obtainable from `training_features.tif` + fold-visible `existing_faults.tif`.
5. **`H80-COULOMB-CFS` (Rank #5 — precision/FP-reduction gain, medium cost):** Elastic half-space Okada 3D normal/transtensional dislocation Coulomb failure stress (`ΔCFS`) computed strictly from fold-visible fault segments, suppressing lateral stress-shadow (`ΔCFS < 0`) false positives while sharpening off-axis relay/stepover lobes (`ΔCFS > 0`). *Data verification:* 100% obtainable from fold-visible `existing_faults.tif` + `training_features.tif` (`geod_shearrate`, `geod_dilaterate`).

---

## 4. Autonomous completion of data placement, cache reproduction, selector hardening & ETP forensic audit

1. **Autonomous competition data & deterministic feature-cache verification ([`evidence/data_and_pipeline_verification_f40e4f2e.json`](../evidence/data_and_pipeline_verification_f40e4f2e.json)):**
   - Executed `bash scripts/download_competition_data.sh`, `.venv/bin/python scripts/restore_data.py --preserve-receipt --ids all`, and `.venv/bin/python scripts/prepare_data.py --reproduce` end-to-end without manual intervention (staging raw binaries in `.cache/raw_data` outside Git/snapshot tracking).
   - Verified **`13 / 13`** SHA-256-pinned manifest inputs (`training_features.tif`, `labels.tif`, `existing_faults.tif`, `sample_submission.tif`, 3DEP LiDAR scarp features, GeoDAWN radiometrics/extensions, SGMC faults, TIGER road distances, and DOE INGENIOUS GDR-1391 thermal/vent/Qfault tables) and reproduced **`8 / 8`** deterministic E1 `.npy` feature transforms matching `evidence/feature_cache.json` byte-for-byte.
2. **Canonical `G79-THVC` selector evidence adapter (`scripts/select_submission.py`, `IR-79-157`):**
   - Previously, `scripts/select_submission.py` rejected `G79-THVC` as an unsupported lane before inspecting its receipts.
   - Added `canonical_thvc_evidence()` with strict finite/range/boolean guards (`_finite_number`) that re-derives `G79-THVC`'s raster SHA-256, on-disk GeoTIFF format, two-seed `84`-feature leakage canaries (`seed20` & `seed30`), holdout beat status, surface/dot Spearman limits (`<= 0.90`), and literal 3-px forward overlaps (`<= 0.70`), refusing cleanly (`exit 2`, card untouched) on `final_forward_overlap_le_0_70`, `surface_forward_overlap_le_0_70`, and `protocol_unique`.
3. **Exact `gems57-pooled-hide-v2` measurement & root cleanup of quarantined `G79-ETP` (`IR-79-158`, [`evidence/etp_forensic_audit_f40e4f2e.json`](../evidence/etp_forensic_audit_f40e4f2e.json)):**
   - Verified that leftover root `run_card_etp.json` and `registry/preregistration_etp.json` carried a fabricated hex digest (`a1b2c3d4e5f67890abcdef…` vs actual SHA-256 `bb325399fcc5091a75fd7bad78b44da5f55cec4c1b73cfc1a56f41baf40fd53c`), a broken `docs/downloads/…` path, and unmeasured `"dti": 0.021 / 0.019` (`withheld_positive_pixels: 20010 / 19949`) claims.
   - Evaluated `G79-ETP` on unmodified `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`): static ETP rasters scored `0.0000` (`tpw = 0.0`) because they enforced a `> 2 px` exclusion around the **full** `existing_faults.tif` (leaking withheld truth locations as exclusions), whereas **fold-fair `G79-ETP-v2`** (`34,500` dots derived strictly from `fold["visible"]`) scored **`HOLDOUT-DTI = 0.0968` `[0.0838, 0.1112]` (`Seed 20`, `n=11,321`)** and **`0.1061` `[0.0911, 0.1217]` (`Seed 30`, `n=11,342`)** — matching `H33` (`0.0961 / 0.0989`) and nearly `2×` below canonical `G79-THVC` (`0.1905 / 0.1944`).
   - Relocated leftover root `run_card_etp.json` and `registry/preregistration_etp.json` into `archive/g79_etp_incoming_45998a01/` and removed the redundant `2.02 MB` `data/bridge/{existing_faults,sample_submission}.tif` duplicates of `data/reference/`.

---

## 5. Three verification passes

### Pass 1 — implementation and direct verification
- Read full `README.md` (including original prompt), `AGENTS.md`, `run_card.json`, `reports/irregularities.md`, and required preregistrations.
- Verified `scripts/preflight_new_lane.py --restore` (`exit 2`), `scripts/submission_status.py` (`exit 2`), and `scripts/select_submission.py` (`exit 2`).
- Executed autonomous competition input restoration (`13 / 13` SHA-256 matches) and `scripts/prepare_data.py --reproduce` (`8 / 8` SHA-256 matches).
- Measured exact `gems57-pooled-hide-v2` `HOLDOUT-DTI` on fold-fair and static `G79-ETP`.

### Pass 2 — bugs, assumptions, merge reconciliation, and edge cases
- Hardened `canonical_thvc_evidence()` in `scripts/select_submission.py` with `_finite_number` so `NaN`, `-inf`, `+inf`, negative overlaps, booleans, and non-object JSON roots fail closed; added adversarial parametrized tests in `tests/test_selector_evidence.py`.
- Reconciled concurrent `origin/main` merges (`PR #70`..`#81`), catching and correcting leftover root `run_card_etp.json` / `registry/preregistration_etp.json`, duplicate `data/bridge/*.tif`, and verifying the exact SHA-256 (`bb325399…`) of `preregistration_etp.json` before recording `IR-79-158`.

### Pass 3 — end-to-end requirement, site, browser, and CI verification
- Rebuilt static Pages (`scripts/build_site.py`), verified all `7` pages and `146` local links (`scripts/check_site.py`), ran full offline deliverable verification (`scripts/verify_project.py`: `all_checks_passed = true`), ran the complete pytest suite, and executed headless Chromium QA (`scripts/browser_review.cjs`) across `1440 px`, `390 px`, and `320 px` viewports including live `.tif` download SHA-256 verification and clipboard note copy.

---

## 6. Remaining limitations & recommended next steps for the next session

1. **Prospective owner protocol decision required before any new lane (`IR-79-106`, `IR-79-128`, `IR-79-139`):** Because `17GEMSDOE` (`100%` footprint support) and sparse lattice `13GEMSDOE` (`99.8724%` 3-px halo coverage) mathematically force `> 0.70` literal forward overlap for every nonempty `>= 21,714`-dot map, a prospective protocol owner decision (e.g., adopting `chance-calibrated-v4` / `informative-halo-v4` in `vendor/gems57/uniqueness.py` with an updated `registry/template_pin.json`) is required before opening a new experimental lane.
2. **Next scientific combination once unlocked:** Pair `H79-FNHR`'s decontaminated zero-catalogue physics/geothermal head (`0.0906 / 0.0966` pure zero-catalogue `HOLDOUT-DTI`, `IR-79-140`) plus `H80-RADIO-KD` (`geodawn_rad_u8.tif` potassic alteration residual) and `H80-COULOMB-CFS` with `G79-THVC`'s Charnes-Cooper submodular placer (`0.1905 / 0.1944`).
3. **Cross-repo weekly slot discipline & DOE single-final-submission rule:** Do not spend separate weekly slots on both `G79-THVC` (`GEMSDOE79`) and `GEMSDOE83` (`0.7139` 3-px overlap); DrivenData login/slot availability (`<= 3/week`) and DOE Rules §3.4 (`1` final submission per participating entity) remain account-side checks outside repository automation.
