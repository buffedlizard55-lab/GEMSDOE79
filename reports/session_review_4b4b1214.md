# Repository review — session 4b4b1214 — 2026-10-22

## Outcome

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**

The canonical `H79-NHR` research GeoTIFF (`docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif`, `sha256: abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`) remains **scientifically negative** (`verdict: "negative"`, `ok_to_download: true`, `ok_to_submit: false`). No new scientific experiment, retuning, overlap capping, or competition upload was performed in this session (`0` competition slots used).

Why `OK TO SUBMIT` is `NO` (enforced automatically by `scripts/submission_status.py`, exit code `2`, without human intervention):
1. **Literal universal witness (`IR-79-04`, `IR-79-53`):** Under `vendor/gems57/uniqueness.py`'s default `literal` dot definition, the hash-verified registry raster `17GEMSDOE:submissions/20261001T190707Z_E-proba-multiscale.tif` (`sha256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) covers `100.0%` (`5,106,385 / 5,106,385`) of allowed footprint cells within 3 px (`evidence/universal_overlap_certificate.json`), and `scripts/preflight_new_lane.py --restore --report evidence/preflight_4b4b1214.json` exits `2` (`impossible_under_literal_gate`).
2. **Ordinary dot-field duplicate saturation (`IR-79-55`):** Even under `budget-matched-v3` (`IR-79-47`), although `H79-NHR` (`X1`) beat the fold-fair `H33` control on `HOLDOUT-DTI` (`gems57-pooled-hide-v2`) across both spatial-block seeds (`0.1431 [0.1281, 0.1574]` vs `0.0961 [0.0837, 0.1086]` on seed 20, `11,321` withheld positives; `0.1522 [0.1335, 0.1696]` vs `0.0989 [0.0842, 0.1120]` on seed 30, `11,342` withheld positives) and cleared all 464 single-feature leakage canary tests (`max AUC = 0.8589 <= 0.90`), it exceeds `0.70` forward 3-px overlap against **26 ordinary non-space-filling dot fields** (worst: `GEMSDOE3:docs/downloads/coverage-v3-wide-20260925T054019Z-0ac095a7ed.tif` at `0.9130` vs `0.6097` chance halo coverage).

## Pass 1 — implementation and verification

1. Integrated all concurrent `main` merges (`9640ed3` through `99fd495`, PRs #37–#47) onto branch `arena/4b4b1214-gemsdoe79` without switching branches.
2. Remediated two concrete defects (`IR-79-80` and `IR-79-81`):
   - **IR-79-80 (`scripts/analyze_family_lineage.py` blobless-clone hang & newly listed prompt candidates):** Calling `git ls-tree -r -l FETCH_HEAD` on a `--filter=blob:none` clone forced `git` to lazily fetch every missing blob from the promisor remote just to compute object sizes, causing 60+ s timeouts. Removed `-l` from `git ls-tree -r FETCH_HEAD`, added explicit single-blob `git fetch --depth=1 origin <blob>` before `cat-file`, synced the verbatim prompt in `README.md`, and extended `evidence/family_lineage_forensics.json` (and `docs/evidence/family_lineage_forensics.json`) with pixel-byte measurements of all 6 newly listed prompt-named unscored candidates (`GEMSDOE76`, `GEMSDOE78`, `GEMSDOE80`..`GEMSDOE83`) plus the 5 empty siblings (`GEMSDOE84`..`GEMSDOE88`).
   - **IR-79-81 (`README.md` post-`</details>` publication contract escape):** Relocated the review section appended after `</details>` in commit `8d065ff` to above `## Original project prompt`, and hardened `scripts/verify_project.py` (`publication_contract_checks`) to reject any non-whitespace content after `</details>` in `README.md`.

### Byte-verified measurements of the 6 newly listed prompt-named unscored candidates

Measured directly from git blob bytes (`evidence/family_lineage_forensics.json`, `prompt_named_unscored_candidates`):

| Sibling repo | Prompt submission name | SHA-256 | Positive pixels | Within 200 m of catalogue | 200–300 m of catalogue | > 1 km from catalogue | 3-px overlap vs `H33` | Forward 3-px overlap vs `H79-NHR` | Reverse 3-px overlap from `H79-NHR` |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `GEMSDOE76` | `gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros` | `6316481da4a756f7...` | `39,200` | `0` | `6,348` | `64.61%` | `0.5799` | `0.4247` | `0.4241` |
| `GEMSDOE78` | `gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros` | `be2e7113b7236f6e...` | `44,090` | `0` | `15,436` | `44.97%` | `0.4401` | `0.3824` | `0.4794` |
| `GEMSDOE80` | `gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros` | `c853eb54ea5eb27a...` | `51,667` | `0` | `0` | `33.76%` | `0.3770` | `0.5018` | `0.5518` |
| `GEMSDOE81` | `gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros` | `9798fe7f4a68c7b8...` | `44,090` | `0` | `36,845` | `0.00%` | `0.1937` | `0.4667` | `0.5071` |
| `GEMSDOE82` | `gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros` | `fe13719986d60e8c...` | `37,654` | `0` | `4,877` | `57.42%` | `0.5259` | `0.4066` | `0.3884` |
| `GEMSDOE83` | `gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros` | `79f14dc84cd7760c...` | `37,654` | `0` | `0` | `36.77%` | `0.3183` | `0.4717` | `0.5901` |

`GEMSDOE84` through `GEMSDOE88` were also verified via `git ls-tree -r FETCH_HEAD`: all five currently have `0` published `.tif` files.

## Pass 2 — bug and edge-case review

- Added regression tests in `tests/test_publication_contract.py` verifying:
  - `publication_contract_checks` rejects any text appended after `</details>` in `README.md`;
  - `evidence/family_lineage_forensics.json` includes all 6 `prompt_named_unscored_candidates` and all 5 `empty_post_snapshot_siblings`, with `< 0.70` 3-px overlap against `H79-NHR`;
  - all 81 sequential irregularity IDs (`IR-79-01`..`IR-79-81`) are unique and in order.

## Pass 3 — final verification against user requirements

- Re-ran `.venv/bin/python scripts/verify_project.py`: all 29 checks passed (`all_checks_passed: true`).
- Re-ran `.venv/bin/python scripts/build_site.py` and `.venv/bin/python scripts/check_site.py`: all 7 HTML pages and local links passed.
- Re-ran `.venv/bin/python scripts/submission_status.py`: returned `ok_to_download: true`, `ok_to_submit: false`, `verdict: "negative"`, exit code `2`.
- Re-ran `.venv/bin/python scripts/preflight_new_lane.py --restore --report evidence/preflight_4b4b1214.json`: returned `start_new_lane: false`, `state: "impossible_under_literal_gate"`, exit code `2`.
- Re-ran `.venv/bin/python -m pytest -q`: all tests passed.
