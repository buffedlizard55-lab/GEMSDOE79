# Three-Pass Comprehensive Review & Cross-Repository Audit — Session `070af0b6` (`2026-10-22`)

- **Branch:** `arena/070af0b6-gemsdoe79` (`status: active`)
- **Canonical Artifact (`docs/downloads/`):** `g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif` (`137,299 B`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`) · Single-TIFF `.zip` (`102,628 B`, SHA-256 `dfee2552d9ba94bbb778f6da8e35b42ea7e5c55ff580dc5e9f9c809964b788f9`)
- **Automated Machine Gate Verdict:** **`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`** (`scripts/submission_status.py` exit `2`, `scripts/select_submission.py` exit `2`, `0` weekly slots spent, `0` new scientific experiments run in this review session)

---

## 1. Executive Summary of Live Bugs Caught & Reconciled on `main`

1. **Emergency CI Restoration after PR #53 (`4b38bfa`, `H79-STEP`, `IR-79-120`):** Commit `4b38bfa` merged onto `main` over `G79-THVC` (`f66f90d`, `HOLDOUT-DTI = 0.1905 / 0.1944`) while its own CI checks were failing (`39724074871`, `39724077730`, `39724077661`), leaving two competing `.tif`/`.zip`/`.json` pairs in `docs/downloads/`, breaking four `verify_project.py` invariants (`readme_matches_card_decision`, `only_canonical_upload_artifacts_published`, `holdout_card_equals_evaluator_output`, `uniqueness_card_matches_evidence`) and `check_site.py`, replacing `G79-THVC` (`0.1905 / 0.1944`) with inferior `H79-STEP` (`0.0949` Seed 20 `< H33 = 0.0961`), and misstating its own formula (`run_card_step.json` claimed `annulus_window(D, 200 m-2 km) * complexity`, whereas `scripts/run_edge_lane.py:68-73` discarded `complexity` and emitted uniform `1.0` over `[100 m, 1 km]`). All `H79-STEP` files were preserved byte-for-byte in `archive/h79_step_21642326/` with a stopped-lane guard (`SystemExit(2)`) in `scripts/run_edge_lane.py`.
2. **Missing Dependencies in `requirements.txt` (`IR-79-124`):** `src/gems79/thvc_model.py` imports `lightgbm` unconditionally at line 19, crashing `pytest` collection in environments installed from `requirements.txt`. Synchronized `requirements.txt` (`lightgbm>=4.5,<5`, `matplotlib>=3.9,<4`) with `requirements.lock` (`lightgbm==4.7.0`, `matplotlib==3.11.2`).
3. **Path Portability, Prompt Preservation, Byte Count, `AGENTS.md`, and Executive Summary Fixes (`IR-79-121`):** Normalized `/home/user/GEMSDOE79/...` paths in `run_card.json` (`validator.file`, `validator_output.file`) to repo-relative POSIX paths across all four synced copies; restored PR #49 (`931256d`)'s verbatim updated prompt (`GEMSDOE78`, `GEMSDOE80`–`GEMSDOE88`) that PR #51 had overwritten; fixed ZIP size (`102,600 B` -> `102,628 B`); updated `AGENTS.md` to name canonical `G79-THVC` plus all 10 archived lanes; and updated `executive_negative()` in `scripts/build_site.py` to surface `IR-79-69`, `IR-79-84`/`IR-79-123`, `IR-79-122`, and DOE Rules §§ 3.2 & 3.4.

---

## 2. Exact Mathematical Analysis of `H33` (`0.2778`), `0.3195`, and `0.4413`

Under the official Distance-Weighted Tversky Index (`https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/`):
$$\text{DTI}(P, G) = \frac{\text{TP}_w}{\text{TP}_w + 0.2\,\text{FP}_w + 0.8\,\text{FN}_w}, \qquad k(d) = \max\!\left(1 - \frac{d}{300\text{ m}},\, 0\right), \qquad \text{FN}_w = N_{\text{truth}} - \text{TP}_w.$$
Writing $c = \text{TP}_w / N_{\text{truth}} \in [0, 1]$ and $r = \text{FP}_w / N_{\text{truth}} \ge 0$:
$$s = \frac{c}{0.8 + 0.2\,c + 0.2\,r} \implies c = \frac{s(0.8 + 0.2\,r)}{1 - 0.2\,s} \ge \frac{0.8\,s}{1 - 0.2\,s}.$$

| Benchmark Score $s$ | Evidence Class | Zero-FP Minimum Truth Capture $c_{\min} = \frac{0.8s}{1 - 0.2s}$ | Required Capture $c$ at $r = \text{FP}_w / N_{\text{truth}} = 0.5$ | Required Capture $c$ at $r = 1.0$ |
|---|---|---|---|---|
| **`0.1847`** (`#103 doegemsDrivendata`) | `PUBLIC-OBSERVATION` (`2026-10-22`) | **`15.34%`** | `17.26%` | `19.18%` |
| **`0.2778`** (`H33` prompt report; `#52 extradr19`) | `UNVERIFIED REPORT` / `PUBLIC-OBSERVATION` | **`23.53%`** | `26.47%` | `29.41%` |
| **`0.3195`** (prompt text claim; absent in `#1–#200`) | `UNVERIFIED HISTORICAL CLAIM` | **`27.30%`** | `30.72%` | `34.13%` |
| **`0.4413`** (`#1 xiaofanhu`) | `PUBLIC-OBSERVATION` (`2026-10-22`) | **`38.72%`** | `43.56%` | `48.40%` |

Why `H33` (`c55bafc4...`, `37,654` binary `1.0` dots = `D2.8 \ {d_cat <= 200 m}`) outperformed earlier dense family rasters (`0.0286`–`0.2478`):
1. **Asymmetric max-vs-sum kernel operator:** `TP_w` applies a spatial $\max$ within $300\text{ m}$, whereas `FP_w` sums every positive pixel linearly outside true fault halos. Discretizing a continuous probability field into `~35k–44k` `300 m`-spaced `{0.0, 1.0}` impulses collapses `FP_w` by `> 10×` while retaining `~85–92%` of local `TP_w` credit.
2. **Known-fault masking echo removal:** Because organizer evaluation masks exact `existing_faults.tif` pixels (`DD-MASK`), `D2.8`'s `6,436` dots inside $d_{\text{cat}} \le 200\text{ m}$ largely duplicated adjacent unmasked splay credit while incurring full `FP_w` penalty where single-strand mapped faults lacked parallel splays.
3. **Why `G79-THVC` (`0.1905 / 0.1944 HOLDOUT-DTI`) nearly doubles `H33` (`0.0961 / 0.0989`) — and what still separates it from `0.4413`:** `G79-THVC` solves the `24.99%` Nevada LiDAR blind gap (`3.29×` regime gain), integrates GDR `1391` 2-m temperature probes + Quaternary sinter + spring geothermometry + volcanic vents, adds anisotropic Mode-II/III fault-tip mechanics, and replaces uniform `3 px` spacing with exact Charnes-Cooper fractional optimization (`35,093` dots). Its remaining ceiling is spatial concentration near mapped faults (`median d_cat = 565.7 m`, only `2.42%` of dots beyond `2 km` vs `49.20%` in `H33`), motivating the five far-field subsurface/tectonic hypotheses in [`research/hypotheses_post_thvc_backlog.md`](../research/hypotheses_post_thvc_backlog.md).

---

## 3. Complete Byte & 990-Registry Audit of Newly Added Prompt Entries (`GEMSDOE76`–`GEMSDOE88`)

Full machine-verifiable receipts are saved in [`evidence/post_index_sibling_audit_20261022.json`](../evidence/post_index_sibling_audit_20261022.json).

| Repository & Candidate | SHA-256 (`HEAD`) | Dots | `d_cat` p50 (`>2 km`) | Shared `gems57` Holdout | Max Sparse (`<=50k`) Overlap | Overlap vs `G79-THVC` | Audit Findings & Irregularities (`IR-79-122`) |
|---|---|---:|---|---|---:|---:|---|
| **`GEMSDOE79` (`G79-THVC`)** | `d3db2e95...fee2` | `35,093` | `565.7 m` (`2.4%`) | **`0.1905` / `0.1944`** | **`0.6844` PASS** | — | Sole canonical file in `docs/downloads/`; honest `ok_to_submit: false` (`DO-NOT-SUBMIT`). Collides `0.7139 > 0.70` with `GEMSDOE83`. |
| **`GEMSDOE76` (`ptcf-tiltworm`)** | `54c97839...c514` | `39,200` | `984.9 m` (`27.1%`) | Not primary (`E76-3 = 0.1580`) | **`0.7140` FAIL** (`GEMSDOE28`) | `0.4861` | **Sparse duplicate (`0.7140 > 0.70`)**; `5` `.tif` files co-published in `docs/downloads/`. |
| **`GEMSDOE77` (`H85` / archive)** | `6c363745d8` (HEAD) | — | — | Negative (`RESEARCH-ONLY`) | — | — | `109` `.tif` files and `129` run cards tracked in repo. |
| **`GEMSDOE78` (`h78sigx-fuse-b5`)** | `8ca06ece...1786` | `44,090` | `1,081.7 m` (`24.5%`) | **`0.1771`** (`seed=20`) | **`0.6122` PASS** | **`0.4041` PASS** | Strong orthogonal far-field signal (`0.0% <= 500 m`), **but** `16` `.tif`s sit in `docs/downloads/` and custom `uniqueness.py` (`IR-78-22-03`) unratified (`22` medium-density overlaps `> 0.70`). |
| **`GEMSDOE80` (`h80g-choquet`)** | `a3c14d76...5ede` | `51,667` | `800.0 m` (`16.3%`) | `0.2349` **private** (`0.1172` shared `macs61`) | **`0.5772` PASS** | `0.6064` | **Protocol Rule #2 violation:** headline `0.2349` uses private `GEMSDOE80-evaluate_holdout`, not shared `gems57`; `10` `.tif`s in `docs/downloads/`. |
| **`GEMSDOE81` (`cont-poisson`)** | `9798fe7f...5508` | `44,090` | **`223.6 m` (`0.0%`)** | `0.2170` (`mode all`) | **`0.9203` FAIL** (`15` sparse dups) | `0.4076` | **DO NOT SUBMIT:** prompt filename mismatch (`gemsdoe81-...` vs `gems81-...`); **`1.0000` (`100%`) overlap on 4 non-space-filling registry rasters**; `100%` pure `224–412 m` collar ring! |
| **`GEMSDOE82` (`h82-punoisyor`)** | `120810fe...a131` | `37,654` | `894.4 m` (`27.3%`) | `0.1253` (`seed=20`) | **`0.6770` PASS** | `0.4861` | Lower holdout than `G79-THVC`/`GEMSDOE83`/`GEMSDOE78`; `9` `.tif`s in `docs/downloads/`; `60` medium-density overlaps `> 0.70`. |
| **`GEMSDOE83` (`h83-gvcd-dink300`)** | `79f14dc8...82a2` | `37,654` | `761.6 m` (`13.1%`) | **`0.1999` / `0.2138`** | **`0.5700` PASS** | `0.5749` (`0.7139` rev.) | **Highest shared dual-seed holdout (`0.2068` pooled)**, **but** prompt filename drift (`gemsdoe83-...` vs `gems83-...`), only `119` rasters checked in-repo (`11` medium-density overlaps `> 0.70`), `7` `.tif`s in `docs/downloads/`, and **`0.7139 > 0.70` collision from `G79-THVC`**. |
| **`GEMSDOE84`–`GEMSDOE92`** | `4a7ccf..b99296` | `0` | — | None | — | — | **All 9 (`GEMSDOE84`..`GEMSDOE92`) are empty `README.md` stub repositories** with `0` `.tif` files and `HTTP 404` GitHub Pages URLs (`GEMSDOE93+` do not exist). |

---

## 4. Official Trusted Sources Verified Line-by-Line (`2026-10-22`)

- **DrivenData Overview & Metric Specification:** <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> — confirms $DTI(\alpha=0.2, \beta=0.8, R=300\text{ m})$, worked `0.60` example, `EPSG:32611` `100 m` `float32` `[0, 1]`, and `"data outside the bounds is null or nan"`.
- **DrivenData About / Background:** <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/> — confirms `$50,000` Initial + `$250,000` Final Prize Rounds (`$300,000` pool).
- **DrivenData Public Leaderboard (Pages 1–4, Ranks `#1–#200`, read `2026-10-22`):** <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> — `#1 xiaofanhu = 0.4413`, `#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3894`, `#21 kinghorton42 = 0.3261`, `#22 li002666 = 0.3183`, `#52 extradr19 = 0.2778`, `#57 wbg1 = 0.2750`, `#69 SDCF9 = 0.2600`, `#103 doegemsDrivendata = 0.1847` (`PUBLIC-OBSERVATION`, never `ORGANIZER-CONFIRMED`).
- **DOE / NLR Official Rules PDF (September 2026):** <https://docs.nlr.gov/docs/fy26osti/96647.pdf> — `15 U.S.C. § 3719`, §3.2 (`<= 3` submissions/week + mandatory AI-use narrative disclosure), §3.4 (**one final selected submission per participating entity** across both rounds), §3.5 reproducible code delivery.
- **Official Reference Benchmark Repo:** <https://github.com/drivendataorg/gems-prize-reference-solution> (commit `aebe92f`, Prof. John Lipor) — Monte Carlo CV U-Net writing finite `[0, 1]` GeoTIFFs without outside NaN mask (`IR-79-69`).
- **USGS GeoDAWN Airborne Magnetic & Radiometric Release:** <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> (`doi:10.5066/P93LGLVQ`, CC0 1.0).
- **DOE OpenEI GDR Submission 1391 (INGENIOUS):** <https://gdr.openei.org/submissions/1391> (`doi:10.15121/1881483`, CC-BY-4.0) & <https://gbcge.org/current-projects/ingenious/> (`DE-EE0009254`).
- **Primary Scientific References:** Mattéo et al. (2021), <https://doi.org/10.1029/2020JB021269>; Hermant et al. (2025), <https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf>; Tversky (1977) / <https://en.wikipedia.org/wiki/Tversky_index>; WGS 84 / UTM Zone 11N <https://epsg.io/32611>.

---

## 5. Three-Pass Verification Ledger & Remaining Limitations

- **Pass 1 (Implementation & CI Repair):** Archived `H79-STEP` (`4b38bfa`, `0c678295...`) byte-for-byte to `archive/h79_step_21642326/`, restored canonical `G79-THVC` (`d3db2e95...`, `0.1905 / 0.1944 HOLDOUT-DTI` — #1 across all **17** `GEMSDOE79` lanes) with portable repo-relative paths across all 4 `run_card.json` copies, added `lightgbm` and `matplotlib` to `requirements.txt`, guarded `scripts/run_edge_lane.py`, synced `AGENTS.md`, `knowledge/official_sources.json` (`2026-10-22`), `scripts/refresh_feed.py`, `README.md` (including verbatim `931256d` updated prompt through `GEMSDOE88` and exact `102,628 B` ZIP byte size), `reports/irregularities.md` (`IR-79-120`..`IR-79-125`), `research/hypotheses_post_thvc_backlog.md`, and `scripts/build_site.py`.
- **Pass 2 (Self-Audit for Concurrent Merges, Edge Cases, Bugs & Assumptions):** Merged concurrent `origin/main` commits `4b38bfa..bd02274` (`PRs #50, #52, #54, #55, #56, #57, #58`), archiving `H79-DILSTEP` (`8497da98...`, `0.0721 / 0.0689`) byte-for-byte in `archive/h79_dilstep_6444be2d/`, adding fail-closed `require_open_lane` (`exit 2`, `no files changed`) guards to **8** unguarded concurrent scripts across `H79-COV`, `H79-DILSTEP`, and `H79-FGR` (**36** total guarded scientific CLI invocations in `tests/test_lane_lifecycle.py`, `IR-79-121`), fixing `audit_archived_concurrent_lanes.py` and `refresh_feed.py` `tmp_path` behavior, repairing a corrupted inline-code merge splice on `origin/main:README.md` (`IR-79-125`), extending sibling byte forensics through `GEMSDOE92`, verifying `IR-79-01`..`IR-79-125` (`110` strictly unique IDs), and passing **`303 / 303` `pytest` tests + `14 / 14` `unittest` checks**.
- **Pass 3 (End-to-End Clean Re-Verification & Live Browser Audit):** Full clean re-run of `scripts/refresh_feed.py`, `scripts/verify_project.py` (`all_checks_passed: true`, all 27 checks `true`), `scripts/build_site.py` (`7` pages), `scripts/check_site.py` (`passed: true`, `124` links), `scripts/submission_status.py` (`exit 2`), `scripts/select_submission.py` (`exit 2`), `scripts/reproduce_artifact.py` (`exact_tiff_recovery: true`), `.venv/bin/pytest -q` (`303 passed, 0 failed`), and headless Chromium `node scripts/browser_review.cjs` across desktop + mobile viewports against a live `0.0.0.0:8080` preview server.
- **Remaining Limitations Requiring Human / Protocol-Owner Action:**
  1. **DrivenData Authentication & Weekly Slot Check:** Login-gated `/submissions/` and `/data/` cannot be inspected from the sandbox; a human participant must verify available weekly capacity (`<= 3/week`) and single-entity compliance (`96647.pdf` §3.4).
  2. **Protocol Owner Decision on `IR-79-123` (`13GEMSDOE` Pigeonhole Obstruction):** Ratifying $\kappa_{\text{ov}} = (\text{ov} - \text{halo})/(1 - \text{halo}) \le 0.70$ or `<= 50,000`-dot budget class in shared `vendor/gems57/uniqueness.py` is required before any future `35k–44k`-dot candidate can flip `ok_to_submit: true` automatically.
  3. **Outside-Footprint Convention (`IR-79-69`):** Confirm whether DrivenData's live scorer prefers `0.0` outside footprint (matching `gems-prize-reference-solution` and `H33`) or `NaN` outside footprint (matching `sample_submission.tif`).
