# Three-Pass Scientific, Engineering & Forensic Review (`arena/79e8e13e-gemsdoe79`)

## Executive Summary & Automated Verdict

- **Automated readiness decision (`scripts/submission_status.py` / `run_card.json`):**
  - **`OK TO DOWNLOAD: YES` (`ok_to_download: true`)**
  - **`OK TO SUBMIT: NO` (`ok_to_submit: false`, `verdict: "negative"`, exit code `2`)**
- **Canonical downloadable research GeoTIFF:**
  - Path: [`archive/g79_fabric_offset_e1/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif`](../archive/g79_fabric_offset_e1/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif)
  - SHA-256: `8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca` (`19,531,598` bytes)
  - Single-TIFF ZIP SHA-256: `51e27e9d484fbb45b75cfb4cbd9c2d1d0dfde0717584668ff4f140a70c623c2c` (`18,125,085` bytes)
  - Format validation (`vendor/gems57/validate.py` + `scripts/validate_submission.py`): **PASS locally** (`float32`, single band, `EPSG:32611`, `3730 x 3292` at `100 m`, exact sample geotransform/bounds, all `12,279,160` cells finite and within `[0, 1]`, `0` positive cells outside the `5,167,373`-pixel footprint, `0` positive cells on `60,988` `existing_faults.tif` catalogue pixels). Local format validity is not organizer portal acceptance.
- **Why submission is strictly blocked under the Parallel-Run Protocol (`Decision D-1`):**
  1. **Universal literal overlap blocker:** Frozen registry prior `17GEMSDOE:docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` (commit `6fc71d198a3501c5877e9d72b13db1c9e821258e`, `sha256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) is finite and strictly positive on all `5,167,373 / 5,167,373` GeoDAWN footprint pixels (`min_positive_value = 0.00051689`). Under unmodified shared `vendor/gems57/uniqueness.py` (`sha256: 1c5094b8…`), `uncovered_allowed_pixels = 0`, so **every nonempty candidate set has `1.0000` (`100% > 70%`) literal forward 3-px overlap**. Post-snapshot sibling `GEMSDOE82` also published `surface_h82.tif` (`4,862,825` positive cells), independently creating a second space-filling blocker unless the protocol owner resolves **Decision D-1**.
  2. **Post-stop offline scientific diagnostic (`evidence/post_stop_diagnostic.json`):** Even under `Decision D-1` Option B (`top-37,654` of `E-proba`, 3-px overlap `0.0119`) or Option C (`p >= 0.5`, overlap `0.3046`), `G79-FABRIC-OFFSET` clears all 72 single-feature leakage canaries (`max_symmetric_auc = 0.5872` on `seed=20`, `0.6162` on `seed=30`, both `<= 0.90`) **but fails the preregistered buffered whole-segment holdout gate** (`HOLDOUT-DTI` via `gems57-pooled-hide-v2`: `0.0474 [0.0390, 0.0552]` on `seed=20`, `n=11,321`; `0.0466 [0.0388, 0.0543]` on `seed=30`, `n=11,342`), failing to beat `zero_lag_edge_control` (`0.0420` / `0.0455`), `uniform_control` (`0.0504` / `0.0496`), or `h33_foldfair_control` (`0.0961` / `0.0989`). Both archived concurrent lanes (`H79-MCT` `d1a4158a…` and `H79-CSPT` `388d8678…`) remain quarantined in `archive/` with `1.0000` literal witness overlap (`evidence/concurrent_lanes_audit.json`). Zero weekly competition slots were spent.

---

## Cross-Repository Byte Lineage Analysis: Why `H33-2-B2` Reached `0.2778` and Why `0.4413` Leads

All measurements below were computed directly on immutable GeoTIFF bytes fetched via Git Smart-HTTP by [`scripts/analyze_family_lineage.py`](../scripts/analyze_family_lineage.py) and recorded in [`evidence/family_lineage_forensics.json`](../evidence/family_lineage_forensics.json) (see full table in [`knowledge/why_h33.md`](../knowledge/why_h33.md)):

1. **All 9 highest-scoring historical family entries (`0.2600`–`0.2778`) plus `GEMSDOE63` (`0.2303`) and `GEMSDOE48` (`0.2296`) belong to a single pixel tree rooted in `19GEMSDOE` (`h19-5`):**
   - `19GEMSDOE` (`121,131` px, reported `0.1922`) contains **100%** of `D2.8`'s `44,090` pixels and **100%** of `H33`'s `37,654` pixels (`reverse_3px = 1.0000`), paying heavy `0.2 * FP` penalty for `83,477` extra contiguous ridge pixels.
   - `GEMSDOE25`/`30` (`D2.8`, `44,090` px, reported `0.2600`) thins `h19-5` into isolated pins at `d ≈ 2.8 px` (`280–300 m`), cutting `77,041` redundant pixels inside the `300 m` max-pool kernel (`+0.0678` gain).
   - Across `GEMSDOE25` (`44,090` px) → `GEMSDOE33` (`41,865` px) → `GEMSDOE31` (`40,199` px) → `GEMSDOE28` (`37,660` px) → `GEMSDOE32` (`H33`, `37,654` px), near-catalogue pin counts in `0 < d_cat <= 200 m` decrease monotonically (`6,436 -> 3,894 -> 2,545 -> 2,353 -> 0`) while reported public DTI increases monotonically (`0.2600 -> 0.2632 -> 0.2708 -> 0.2710 -> 0.2778`). Meanwhile, `H33` retains `2,171` pins in `200 < d_cat <= 300 m` (and `GEMSDOE70` retains `2,227`), whereas pruning all `d_cat <= 350 m` plus emitting `201,260` skeleton pixels in `GEMSDOE77` collapses score to `0.0964`.
   - `GEMSDOE36` (`anderson-geothermal-pinn-38854`, reported `0.2750`) is **not** an independent PINN: it contains all `37,654 / 37,654` exact pixels of `H33` (`reverse_3px = 1.0000`, `forward_3px = 0.9740 > 0.70`) plus `1,200` extra dots.
2. **Genuinely non-duplicate family leaderboard (`forward_3px <= 0.55` AND `reverse_3px <= 0.48` vs `H33`):**
   - **#1 Non-Duplicate:** `GEMSDOE70` (`gems70-p5-dual-submod300-oof38k`, `37,654` px, `4.8%` exact overlap with `H33`, reported `0.2478`) — dual out-of-fold supervised ML + 300 m submodular facility-location cover + `200 m` halo prune.
   - **#2 Non-Duplicate:** `GEMSDOE49` (`gate_ortho_w0.25-40k`, `40,000` px, `3.1%` exact overlap, reported `0.2376`).
   - **#3–#5 Non-Duplicate (pure physics operators):** `GEMSDOE73` seam-free multi-scale Blakely ridges (`0.1917`), `GEMSDOE75` LOCO Radon ridges (`0.1627`), `GEMSDOE76` tilt-axial submodular cover (`0.1555`).
3. **Why the public leaderboard leader (`xiaofanhu: 0.4413`, observed 2026-10-21) leads `H33` (`0.2778`) by `+0.1635`:**
   - Every model in `GEMSDOE1`–`GEMSDOE83` used pixel-local features or handcrafted potential/topographic operators, whereas the official reference architecture (`drivendataorg/gems-prize-reference-solution`) demonstrates end-to-end 2D multi-scale convolutional segmentation (`U-Net`) optimized directly with a **differentiable pooled Distance-Weighted Tversky Loss** over multi-kilometre spatial context (`3.2–12.8 km` receptive fields resolving fault continuity, basin-margin asymmetry, and step-over geometry simultaneously).

---

## Summary of Issues Found & Fixed Across Three Passes (`IR-79-36`..`IR-79-39`)

1. **`IR-79-36` — Git merge conflict markers left on `main` (`cdc93fb` / `1ece8d9`):** Fixed in `AGENTS.md` and `evidence/browser_review.json`; added permanent `no_git_conflict_markers` and `all_tracked_json_strictly_valid` gates in `scripts/verify_project.py`.
2. **`IR-79-37` — Broken links, duplicate `IR-79-*` IDs, and false `H79-CSPT` hash prefix:** Fixed `archive/h79_cspt_464d591/` → `archive/h79_cspt_3d386a3/`, `d55570bf…` → `388d8678…`, 4 links in `knowledge/prior_work/README.md`, `../` escapes in `docs/*.md`, and duplicate `IR-79-31..32` rows; enforced at build time in `scripts/build_site.py` and in `pytest`.
3. **`IR-79-38` — GitHub REST `403` rate limit & `raw.githubusercontent.com` TLS egress block in restore tools:** Added zero-REST-quota bare-Git Smart-HTTP object fetch (`git -c gc.auto=0 fetch --depth=1 origin <blob_sha>`) with triple SHA-1 + SHA-256 + byte-size verification in `scripts/restore_data.py` and `scripts/restore_registry.py`; executed live 13/13 input restoration, cold `.cache/g79/*.npy` reproduction, exact TIFF/ZIP reproduction, and witness verification (`evidence/session_witness_79e8e13e.json`).
4. **`IR-79-39` — Missing `GEMSDOE73`–`GEMSDOE77` score rows & unmeasured cross-repo byte lineage:** Updated `registry/score_ledger.csv` to 103 data rows, synced verbatim prompt in `README.md`, published `evidence/family_lineage_forensics.json` (mirrored to `docs/evidence/family_lineage_forensics.json`), and documented the complete lineage & next-session roadmap.
5. **`IR-79-40` — Concurrent PR #22/#23/#24 quarantine & byte-mismatch catch (`5d14587`):** Quarantined `G79B` (`16a6e07f…`, closed holdout-negative) and `H79-ML-STRAIN-RELAY` (`05038613…`) in [`archive/concurrent_2026-10-22_5d14587/`](../archive/concurrent_2026-10-22_5d14587/README.md) with full SHA-256 `manifest.json`, preserving canonical `vendor/gems57/uniqueness.py` (`1c5094b8…`) and proving on raw bytes that `5d14587` checked only `2 / 992` registry priors while hardcoding copied `E1` overlap numbers (`0.1978` / `0.0119` vs actual `0.2844` / `0.1620` and `1.0000` literal overlap; [`evidence/concurrent_lanes_audit.json`](../evidence/concurrent_lanes_audit.json)).

---

## Concrete Roadmap & Limitations for the Next Session

1. **Prerequisite protocol decision (`Decision D-1`, zero compute until resolved):** Obtain explicit protocol-owner selection among:
   - **Option B (recommended):** Evaluate dense continuous registry priors (`17GEMSDOE` `E-proba`, `GEMSDOE82` `surface_h82.tif`) via their `top-37,654` non-catalogue cells (or explicit probability threshold `p >= 0.50`, Option C), re-running the full frozen + `GEMSDOE78`–`GEMSDOE83` registry scan once under a version-pinned update to `vendor/gems57/uniqueness.py`.
2. **Next scientific lane once `Decision D-1` is authorized (GPU machine recommended):**
   - Preregister a **Multi-Scale Spatial `ConvNeXt-UNet` with Differentiable Pooled 300 m Distance-Tversky + PU Loss** trained with strict `5 km`-buffered spatial block cross-validation across all 19 GeoDAWN channels + pre-2026 USGS 3DEP 1 m scarp features (`ext_lidar_scarp_features_u8`), clearing single-channel leakage canaries (`AUC <= 0.90`), followed by `R = 300 m` submodular max-cover pin placement (`~37,500–41,000` pins) and exact `d_cat <= 200 m` catalogue pruning (retaining `200 < d_cat <= 300 m` splay linkages).
   - Require paired spatial-bootstrap `HOLDOUT-DTI` strictly beating both `h33_foldfair_control` (`0.0961` / `0.0989`) and `GEMSDOE70`'s OOF baseline with 95% CI excluding zero before touching a weekly competition submission slot.
3. **Remaining external limitations honestly disclosed:**
   - No live DrivenData session cookie/credential exists in this sandbox (cannot pull authenticated portal files directly or read organizer submission-page receipts; historical family scores remain `UNVERIFIED HISTORICAL REPORT`).
   - Training a full-resolution multi-scale 2D spatial encoder-decoder across `3730 x 3292` patches requires GPU hardware outside CPU-only CI.
