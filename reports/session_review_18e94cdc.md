# Repository review — session 18e94cdc — 2026-10-22

## Outcome

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**

The canonical `H79-NHR` research GeoTIFF (`docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif`, `sha256: abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`) remains **scientifically negative** and stopped under the Parallel-Run Protocol. No new scientific experiment, retuning, overlap capping, or competition upload was performed (`0` competition slots used).

Although `H79-NHR` (experiment `X1`) beat the fold-fair `H33` control on `HOLDOUT-DTI` (`gems57-pooled-hide-v2`) across both spatial-block seeds (`0.1431 [0.1281, 0.1574]` vs `0.0961 [0.0837, 0.1086]` on seed 20, `11,321` withheld positives; `0.1522 [0.1335, 0.1696]` vs `0.0989 [0.0842, 0.1120]` on seed 30, `11,342` withheld positives) and cleared all 464 single-feature leakage canary tests (max AUC `0.8589 <= 0.90`), it failed the mandatory duplicate gate:
1. Under the literal positive-support reading (`vendor/gems57/uniqueness.py` default `literal`), the registry raster `17GEMSDOE:submissions/20261001T190707Z_E-proba-multiscale.tif` (`sha256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) covers `100.0%` (`5,106,385 / 5,106,385`) of allowed footprint cells within 3 px (`evidence/universal_overlap_certificate.json`), so `scripts/preflight_new_lane.py` exits 2 before any new lane can start.
2. Even under `budget-matched-v3` (`IR-79-47`), 30 registry rasters have 3-px halos covering `> 70%` of the allowed footprint (`IR-79-53`), and `H79-NHR` independently exceeds `0.70` forward 3-px overlap against **26 ordinary non-space-filling dot fields** (worst: `GEMSDOE3:docs/downloads/coverage-v3-wide-20260925T054019Z-0ac095a7ed.tif` at `0.9130` vs `0.6097` chance halo coverage, `evidence/nhr/overlap_chance.json`).

## Pass 1 — implementation and verification

1. Integrated all concurrent `main` merges (`3c62d2e` through `d9dfb85`, PRs #28–#34) onto branch `arena/18e94cdc-gemsdoe79` without switching branches.
2. Audited every script, evidence receipt, and archived lane in the repository and remediated four concrete software/CI/audit defects (`IR-79-63` through `IR-79-66`):
   - **IR-79-63 (Checkout-path independence):** `scripts/validate_submission.py` (`validate_path`) recorded machine-specific absolute paths (`/home/user/GEMSDOE79/docs/downloads/...`) inside `evidence/verification.json`, which would cause `verify_project.py` to rewrite `evidence/verification.json` on any other checkout directory. Normalized paths inside `ROOT` to repo-relative POSIX paths (`docs/downloads/...`) and stripped `/home/user/GEMSDOE79/` prefixes from `run_card_g79b.json`, `run_card_stepco.json`, `evidence/uniqueness_surface.json`, and `evidence/*g79b*.json`.
   - **IR-79-64 (`scripts/reproduce_artifact.py` failure on canonical `H79-NHR`):** `scripts/reproduce_artifact.py` crashed with `KeyError: 'surface_cache_sha256'` because it still assumed the archived `E1` schema and lacked `--help`. Updated it with `--help` and `--lane {nhr,e1}` (default `nhr`) to deterministically reserialize `H79-NHR` in a temporary directory via `gems57.submission_writer.write_submission` and verify bit-exact recovery of the GeoTIFF (`abbf5314...`), single-TIFF ZIP (`b882f55d...`), and decoded `dots_sha256` (`2a7ef64e...`), while preserving the archived `E1` recovery record in `evidence/artifact_reproduction.json`.
   - **IR-79-65 (`evidence/concurrent_lanes_audit.json` stale canonical reference & 9-lane completeness):** `scripts/audit_archived_concurrent_lanes.py` previously hardcoded `lane: "G79-FABRIC-OFFSET"` in `active_deliverable_unchanged` paired with `H79-NHR`'s SHA-256. Fixed it to bind dynamically to `run_card.json` (`H79-NHR`), added byte/uniqueness/status verification for all five preserved negative session lanes (`G79-FABRIC-OFFSET`, `G79-STEPCO-S1`, `G79-STEPCO-S2`, `G79B-SDPT-A3`, `H79-FF`), and computed read-only cross-lane spatial/overlap forensics across all six `GEMSDOE79` lanes.
   - **IR-79-66 (`main` CI failure from PR #34 / `H79-FF` in `docs/downloads/`):** PR #34 (`d9dfb85`, session `1de1617f`) broke `Verify research deliverable` (`39719939692`) and `Pages and public-source health` (`39719939693`) on `main` by adding a second `.tif`/`.zip` (`gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8.{tif,zip}`) directly into `docs/downloads/`, hand-editing `docs/index.html` and `docs/executive-summary.html` with a broken link (`reports/irregularities.html`), and overwriting `data/restore_receipt.json` with a 4-file subset. Quarantined `H79-FF` byte-for-byte to `archive/h79_ff_1de1617f/downloads/`, restored `data/restore_receipt.json` to all 7 verified files, added a stopped-lane guard to `scripts/build_ff_candidate.py`, and rebuilt `docs/` cleanly via `scripts/build_site.py`.

## Cross-lane spatial and overlap forensics across all `GEMSDOE79` lanes

Read-only comparison of the six frozen `GEMSDOE79` GeoTIFFs (`evidence/concurrent_lanes_audit.json`, `cross_lane_comparison`):

| Lane | Status | Positive pixels | 3-px halo fraction of allowed cells | Median distance to mapped catalogue | P90 distance to mapped catalogue | Forward 3-px overlap vs `H79-NHR` | Forward 3-px overlap vs `E1` surface |
|---|---|---:|---:|---:|---:|---:|---:|
| `H79-NHR` (`X1`, canonical) | Negative (duplicate vs 26 dot fields) | `37,654` | `0.1287` | `5.39 px` (`538.5 m`) | `12.65 px` (`1,264.9 m`) | `1.0000` | `0.8877` |
| `G79-STEPCO-S1` (archived) | Negative (tied control + duplicate) | `37,654` | `0.1127` | `12.00 px` (`1,200.0 m`) | `39.31 px` (`3,931.2 m`) | `0.3523` | `0.9012` |
| `G79-STEPCO-S2` (archived) | Negative (below control + duplicate) | `37,654` | `0.1115` | `13.00 px` (`1,300.0 m`) | `43.91 px` (`4,390.9 m`) | `0.3390` | `0.9040` |
| `G79B-SDPT-A3` (`E2`-capped, archived) | Negative (capped below control) | `37,654` | `0.1531` | `21.10 px` (`2,109.5 m`) | `73.01 px` (`7,300.7 m`) | `0.2502` | `0.8618` |
| `H79-FF` (2–8 km distal, archived) | Negative (un-evaluated + duplicate) | `37,654` | `0.1340` | `35.61 px` (`3,560.9 m`) | `63.60 px` (`6,360.0 m`) | `0.0153` | `0.9052` |
| `G79-FABRIC-OFFSET` (`E1` surface, archived) | Negative (stopped pre-placement) | `1,882,872` | `0.8957` | `23.77 px` (`2,377.0 m`) | `67.96 px` (`6,795.6 m`) | `0.1257` | `1.0000` |

Key takeaways from this cross-lane measurement:
- The four sparse 37,654-dot lanes (`H79-NHR`, `G79-STEPCO-S1`, `G79B-SDPT-A3`, `H79-FF`) span a monotonic sequence of distance-to-catalogue regimes (`538.5 m` -> `1,200.0 m` -> `2,109.5 m` -> `3,560.9 m` median catalogue distance) and have low pairwise 3-px overlaps with each other (`0.0138` to `0.3523`, all well below `0.70`).
- Even `H79-FF` (which places zero dots within 2 km of any mapped fault and has only `0.0153` overlap with `H79-NHR`) still has `0.8802` 3-px overlap with the ordinary dot field `GEMSDOE3:docs/downloads/coverage-v3-wide-20260925T054019Z-0ac095a7ed.tif` (`624,025` dots), `0.9976` with `13GEMSDOE` spacing-5 lattice, and `1.0000` with space-filling registry surfaces.

## Pass 2 — bug and edge-case review

- Added regression tests in `tests/test_publication_contract.py` covering:
  - `scripts/reproduce_artifact.py --help` and deterministic `H79-NHR` byte recovery;
  - repo-relative path normalization in `evidence/verification.json`;
  - sequential table-row enforcement across all 66 irregularity entries (`IR-79-01`..`IR-79-66`);
  - 9-lane archive completeness and consistency between `evidence/concurrent_lanes_audit.json` (`active_deliverable_unchanged`) and `run_card.json`.
- Verified `pip check` reports no broken requirements and `git diff --check` is clean.

## Pass 3 — final verification against user requirements

- Re-ran `.venv/bin/python scripts/verify_project.py`: all 29 checks passed (`all_checks_passed: true`).
- Re-ran `.venv/bin/python scripts/build_site.py` and `.venv/bin/python scripts/check_site.py`: all 7 HTML pages and 120 local links passed.
- Re-ran `.venv/bin/python scripts/submission_status.py`: returned `ok_to_download: true`, `ok_to_submit: false`, `verdict: "negative"`, exit code `2` (expected fail-closed negative exit).
- Re-ran `.venv/bin/pytest -q`: all 230 tests passed.
