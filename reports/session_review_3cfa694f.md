# Three-Pass Audit & Reconciliation Report — Session `3cfa694f` (2026-10-22)

**Branch:** `arena/3cfa694f-gemsdoe79`  
**Canonical Active Lane:** `G79-THVC` ([`run_card.json`](../run_card.json), `verdict: "negative"`, `ok_to_download: true`, `ok_to_submit: false`, `HOLDOUT-DTI = 0.1905 / 0.1944`)  
**Canonical Research GeoTIFF:** [`docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif) (`sha256: d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`)  
**Automated Submission Readiness:** `scripts/submission_status.py` exits with code `2` (`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`)  
**NewLane Preflight:** `scripts/preflight_new_lane.py --restore` exits with code `2` (`start_new_lane: false`, `state: "impossible_under_literal_gate"`, `covered_allowed_fraction: 1.0`)

---

## 1. Executive Summary of Session `3cfa694f`

Per [`AGENTS.md`](../AGENTS.md) and the Parallel-Run Protocol:
- All lanes (`G79-THVC`, `H79-NHR`, `G79-FABRIC-OFFSET` `E1`, `G79-STEPCO` `S1`/`S2`, `G79B-SDPT` `A3`, `H79-FF`, `H79-ASYM`, `H79-STEP`) remain in their terminal **stopped negative** state (`ok_to_submit: false`). No stopped lane was resumed, retuned, jittered, or overlap-capped, and zero weekly submission slots were spent.
- Re-running `scripts/preflight_new_lane.py --restore` against the SHA-256-pinned `17GEMSDOE` universal overlap witness (`ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) confirmed `covered_allowed_fraction = 1.0` (`exit 2`), forbidding any new nonempty candidate under the literal positive-support reading without an explicit owner decision on `Decision D-1` (`IR-79-53`).
- We audited all newly added prompt lines (`GEMSDOE76`..`GEMSDOE88`), fixed `select_sibling_tifs()` and the `spearmanr` constant-array NaN guard in [`scripts/analyze_family_lineage.py`](../scripts/analyze_family_lineage.py), documented the `GEMSDOE76` score discrepancy (`0.1555` vs `0.2194`, both `UNVERIFIED HISTORICAL REPORT`; `IR-79-86`) and sibling protocol irregularities (`IR-79-87`), reconciled the concurrent PR #53 (`4b38bfa`, `H79-STEP`) merge regression on `main` (`IR-79-88`, archiving `H79-STEP` under [`archive/h79_step_21642326/`](../archive/h79_step_21642326/README.md)), and added fail-closed `require_open_lane` terminal-lane guards to all 17 remaining historical/archived runner and packaging scripts (`IR-79-89`).

---

## 2. Pass-by-Pass Engineering & Scientific Verification Log

### Pass 1 — Implement & Verify
1. **Fixed `git ls-tree -r -l` promisor-fetch hang and `tifs[:3]` truncation (`IR-79-67`):**
   - `scripts/analyze_family_lineage.py` previously called `git ls-tree -r -l FETCH_HEAD` on `--filter=blob:none` bare clones. The `-l` (`--long`) flag forced Git to lazily fetch every missing blob in the repository one by one via `--stdin` to compute blob sizes, causing `GEMSDOE78` (`b7a3e5b09d`, 19 `.tif` files) to hang and time out after 120 seconds.
   - Removed `-l` from `git ls-tree -r FETCH_HEAD` so tree enumeration reads only tree objects (~4.5 s across all 11 sibling repositories), added `select_sibling_tifs()` so prompt-named `docs/downloads/` candidates are explicitly selected rather than truncated by `tifs[:3]`, precomputed 3-px reference halos (`near_h33`, `near_d28`, `near_nhr`), and regenerated [`evidence/family_lineage_forensics.json`](../evidence/family_lineage_forensics.json).
2. **Audited `GEMSDOE76`..`GEMSDOE88` prompt updates (`IR-79-68`, `IR-79-69`):**
   - Documented why `GEMSDOE76`'s `gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros` (`0.1555` in prompt `18e94cdc` vs `0.2194` in prompt `3cfa694f` alongside `gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros: ?`) remains strictly `UNVERIFIED HISTORICAL REPORT (NO ORGANIZER SUBMISSION-PAGE RECEIPT)`.
   - Measured exact byte hashes, positive pixel counts, catalogue-distance histograms, and bidirectional 3-px overlaps against both `H33` and `H79-NHR` for all prompt-named candidates across `GEMSDOE76`, `GEMSDOE78`, and `GEMSDOE80`..`GEMSDOE83`, and verified that `GEMSDOE84`..`GEMSDOE88` contain only 14-byte `README.md` stubs (`0` `.tif` files) on `HEAD`:

| Sibling Repo (`HEAD`) | Prompt-Named / Audited GeoTIFF | SHA-256 (prefix) | Positive px | `200 < d_cat <= 300 m` | `> 1 km` frac | Fwd 3-px vs `H33` | Fwd 3-px vs `H79-NHR` | Protocol Audit Note |
|---|---|---|---:|---:|---:|---:|---:|---|
| `GEMSDOE76` (`97f3dd5a81`) | `gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros.tif` | `d706807d42d1b21f` | 37,654 | 378 | 0.6600 | 0.5220 | 0.4036 | Prompt reports `0.1555` (`18e94cdc`) vs `0.2194` (`3cfa694f`); no organizer receipt (`IR-79-68`) |
| `GEMSDOE76` (`97f3dd5a81`) | `gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros.tif` | `54c978399d0a875b` | 39,200 | 1,775 | 0.4890 | 0.5799 | 0.4247 | Second promoted lane in `docs/downloads/` (5 `.tif` files total) |
| `GEMSDOE78` (`b7a3e5b09d`) | `gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros.tif` | `8ca06ece44285ca2` | 44,090 | 0 | 0.5359 | 0.4401 | 0.3824 | Promoted at overall `HOLDOUT-DTI = 0.1771` below repo control `0.1826`; unratified local exemption (`0.6988` vs `H78-A`; `IR-79-69`) |
| `GEMSDOE80` (`02f8fd64be`) | `gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros.tif` | `a3c14d76d1f58802` | 51,667 | 942 | 0.3806 | 0.3770 | 0.5018 | Uses custom evaluator (`GEMSDOE80-evaluate_holdout.py-v2`); 10 `.tif` files in `docs/downloads/` (`IR-79-69`) |
| `GEMSDOE81` (`15bf850cfd`) | `gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros.tif` | `9798fe7f4a68c7b8` | 44,090 | 36,845 | 0.0000 | 0.1937 | 0.4667 | 100 % of `44,090` dots lie within `200 < d_cat <= 500 m` (`0 %` `> 1 km`; `IR-79-69`) |
| `GEMSDOE82` (`4fb7df6f65`) | `gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros.tif` | `120810feffb4688c` | 37,654 | 2,529 | 0.4564 | 0.5259 | 0.4066 | Promoted using mutual overlap (`0.6062`) rather than literal forward overlap; 10 `.tif` files in `docs/downloads/` (`IR-79-69`) |
| `GEMSDOE82` (`4fb7df6f65`) | `artifacts/surface_h82.tif` | `1aa005ff3a03d3bd` | 4,862,825 | 140,246 | 0.7934 | 0.1537 | 0.1213 | Continuous surface (`94.1 %` of footprint positive; `rev_3px = 1.0000` vs `H33` and `H79-NHR`) |
| `GEMSDOE83` (`da9ec5a3b4`) | `gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros.tif` | `79f14dc84cd7760c` | 37,654 | 0 | 0.3677 | 0.3183 | 0.4717 | Checks only 119 registry rasters (`115 discriminating priors`); 7 `.tif` files in `docs/downloads/` (`IR-79-69`) |
| `GEMSDOE84`..`88` | *(none)* | — | 0 | — | — | — | — | 14-byte `README.md` template stubs on `main` (`0` `.tif` files, `0` `docs/` pages; `IR-79-69`) |

3. **Added fail-closed terminal-lane guards (`IR-79-70`):**
   - Added `require_open_lane` (exiting with code 2 on `LaneClosedError` before reading bulk data or writing any file) to `finalize_nhr.py`, `nhr_uniqueness.py`, `nhr_overlap_chance.py`, `nhr_surface_flagged.py` (also wrapped in `def main():` so importing does not execute top-level code), `nhr_distance_profile.py`, `run_stepco_experiment.py`, `run_stepco_s2.py`, `build_stepco_run_card.py`, `supplementary_uniqueness_stepco.py`, `run_holdout_g79b.py`, `build_submission_g79b.py`, and `cap_cost_g79b.py`.

### Pass 2 — Review for Bugs, Edge Cases & Regressions
1. **Verified all historical/archived scripts fail closed without side effects:**
   - Added subprocess regression tests in [`tests/test_lane_lifecycle.py`](../tests/test_lane_lifecycle.py) covering all 16 historical/archived entry points (`run_nhr.py`, `nhr_uniqueness.py`, `build_nhr_submission.py`, `finalize_nhr.py`, `nhr_overlap_chance.py`, `nhr_surface_flagged.py`, `nhr_distance_profile.py`, `run_stepco_experiment.py`, `run_stepco_s2.py`, `build_stepco_run_card.py`, `supplementary_uniqueness_stepco.py`, `run_holdout_g79b.py`, `build_submission_g79b.py`, `cap_cost_g79b.py`, `build_ff_candidate.py`).
2. **Verified `evidence/family_lineage_forensics.json` schema and web mirror parity:**
   - Added assertions in [`tests/test_publication_contract.py`](../tests/test_publication_contract.py) verifying that all 11 post-snapshot sibling repositories (`GEMSDOE76`, `GEMSDOE78`, `GEMSDOE80`..`GEMSDOE88`) and the `GEMSDOE76` prompt-score discrepancy note are present in `evidence/family_lineage_forensics.json` and mirrored byte-for-byte to `docs/evidence/family_lineage_forensics.json`.

### Pass 3 — Full Requirements Re-Check & Final Verification
- Rebuilt the GitHub Pages site (`scripts/build_site.py`), refreshed `evidence/verification.json` (`scripts/verify_project.py --refresh`), and verified idempotency (`scripts/verify_project.py` without `--refresh`), `scripts/check_site.py` (7 HTML pages, 120 local links), `scripts/submission_status.py` (`exit 2`), and the full `pytest` suite.
