# Session `842c8c7c` review — H80 pilots, official-rules verification, and blocked-holdout run card

Branch `arena/842c8c7c-gemsdoe79`, based on `main` `847a4a0f`. Date 2026-10-22 (UTC). This document records three passes: implement, review for bugs, and re-check requirements.

**Decision: no new file is submitted.** OK TO DOWNLOAD: YES (canonical G79-THVC only). OK TO SUBMIT: NO. Slots used: `0`. Experiments: `2 of 3`. Both pilots are negative.

## Pass 1 — implementation

| Built | Path | Result |
|---|---|---|
| DRAPE pilot (notch + tilt edge, zero-catalogue) | `scripts/run_h80_drape_pilot.py`, `registry/preregistration_h80_drape_pilot.json`, `evidence/h80_drape_pilot/` | Negative. Notch minus control `-0.0002` / `-0.0018`. |
| RADIO pilot (thorium-normalised K residual) | `scripts/run_h80_radio_pilot.py`, `registry/preregistration_h80_radio_pilot.json`, `evidence/h80_radio_pilot/` | Negative. Candidate `0.0206` / `0.0318` vs raw-K control `0.0274` / `0.0294`. |
| Overlap check (protocol step 1) | `scripts/h80_pilot_overlap_check.py` → `evidence/h80_pilot_overlap_check.json` | Not duplicates. Max within-3 px overlap `0.2038` (rule `> 0.70`). Max abs Spearman `0.045` (rule `> 0.90`). |
| Run card (protocol step 2 and 5) | `scripts/build_h80_run_card.py` → `run_card_h80_pilots.json` | Verdict negative. Raster SHA `null`, with reason. Submission name and note `null`. All numbers read from evidence files. |
| Ranked hypotheses (3 to 5, ranked by DTI gain and cost) | `research/hypotheses_842c8c7c_ranked.md` | Four candidates. Top H-A (FNHR physics head + THVC placer) is **not validated**. Gains are estimates. |
| Tests | `tests/test_h80_pilots.py` (8 tests) | All pass. Covers 300 m separation, budget, notch mask, nodata sentinel, run-card gate, timestamps, receipt match, overlap link. |
| Irregularities | `reports/irregularities.md` rows `IR-79-143`..`IR-79-151` | Appended. |
| README | Section `Session 842c8c7c` added before the H79-FNHR lane section. The top gate is unchanged. | Official links included. |
| AI disclosure | `knowledge/ai_disclosure.md` dated entry | Required by rules §3.2. |
| Verifiers | `scripts/verify_project.py` (exit 0, all 33 checks true after restore) and `scripts/submission_status.py` (exit 2, fail-closed as expected) | Re-run after the restore, which the earlier pre-restore run could not cover. |

Preregistration items are protocol-compliant except the timestamp breach (IR-79-143). `scikit-learn==1.9.1` is in `requirements.lock` (line 35). The import worked, and the lock file is now confirmed.

## Pass 2 — bug review (defects found and fixed in this session)

| # | Defect | Severity | Fix | Disclosure |
|---|---|---|---|---|
| 1 | **Overlap check used the wrong RADIO arm.** `build_scores` returns `(th-normalised residual, raw K)`. The first version took the second value and labelled it as arm A. | High (it would have mislabelled the overlap evidence) | Rewritten: arm A and arm B are both taken, labelled correctly. | Disclosed here. |
| 2 | **Overlap check used the full-catalogue mask.** The pilots use each seed's own `footprint & (d_visible > 2)`, so the first version measured dots the pilots never placed. | High | Rewritten: uses each seed's own mask from `holdout.buffered_component_draw`. | Disclosed here. The diagnostic was re-run. This is not a holdout experiment and used no slot. |
| 3 | **Run card had a hand-typed overlap string** (`0.1963`, `0.0453`) left over from the wrong run. | Medium | Builder now derives the string from `evidence/h80_pilot_overlap_check.json`. A test pins the link. | Disclosed here. |
| 4 | **RADIO preregistration timestamp `14:40:00Z` was later than the clock** (`14:26:36Z` at correction). Both timestamps were hand-typed. | High (protocol) | Withdrawn to `null`; status and clock read recorded. | `IR-79-143`. |
| 5 | **Irregularity row IR-79-145 had extra pipes** (`|f_x|`), which breaks the single-line table rule. | Low | Replaced with `abs(f_x)`. | Fixed before commit. |
| 6 | **Holdout-evaluation count was a bare expression** (`2*2*3`). | Low | Replaced with `12`. | Fixed before commit. |
| 7 | **Frozen IR count in an earlier-session test** (`== 142`) failed once the 9 new rows were added. | Medium (test) | Relaxed to a floor (`>= 142`), with a comment. The log only grows; uniqueness is the invariant. | Disclosed here. Relaxation of a prior-session pin, not a deletion. |
| 8 | **Broken link to the review file** from the irregularity log and README. | Low | This file now exists. | Fixed. |
| 9 | **Stale sentinel count**: first draft said `7,113,308` total. The correct figure is `7,113,308` per band across 19 bands (`135,152,864` total). | Low | Corrected in `IR-79-148`. | Fixed before commit. |
| 10 | **Leaderboard-check claim** that `0.2778` and `0.3195` are absent from the top 50. Verified against all three live chunks. | Verification | Confirmed (rank 21 = `0.3261`, rank 22 = `0.3183`, rank 48 = `0.2818`, rank 50 = `0.2804`). | `IR-79-149`. |

No defect was found in the shared code (`vendor/gems57`, `src/gems79`). The metric, fold reconstruction (`11,321` / `11,342`), and canary logic were re-checked. No shared-code change was made.

## Pass 3 — requirement re-check

| # | Requirement (from the user's messages) | Status | Evidence |
|---|---|---|---|
| R1 | Study why `h33-…-zeros` (GEMSDOE32, `0.2778`) scored highest among prior submissions. | Done in prior sessions. Reproduced this session. The `0.2778` value is **not** on the live top-50 board. | `evidence/h33_forensics.json` (byte-identical); `IR-79-149`. |
| R2 | Can a unique TIF beat it? | **Not established this session.** No new candidate passed the blocked-holdout bar. The canonical G79-THVC beats the H33 control on holdout (`0.1905` / `0.1944` vs `0.0961` / `0.0989`), HOLDOUT-DTI. | `run_card.json`; README §1–§2. |
| R3 | Unique downloadable single-band GeoTIFF, values in `[0,1]`, EPSG:32611, validated automatically by the project. | Canonical G79-THVC passes the project's automated gate (`15 / 15` format checks, no human inspection). No new file was produced. | `scripts/verify_project.py` exit 0; `scripts/submission_status.py` exit 2 (download YES, submit NO). |
| R4 | Unique name plus note of 140 characters or fewer. | Canonical name `43` chars, note `98` chars. No new name required (no new file). | README gate table. |
| R5 | Do not copy a prior submission. | Compliant. The pilots use their own scores and placement, and no registry raster was used as input. The overlap check uses registry rasters only as comparators. | `IR-79-150` / overlap check. |
| R6 | Parallel-run protocol: one method lane. | **Flag.** The two pilots are both single-feature, zero-catalogue physics scores with the same placer and evaluator. They are two arms of one family, not two independent lanes. They are reported as separate pilots. | `IR-79-145`, `IR-79-146`. |
| R7 | Rank correlation `> 0.90` and `> 70 %` of dots within 3 px are duplicate tests. | Done. Neither triggered. | `evidence/h80_pilot_overlap_check.json`. |
| R8 | Every number labelled HOLDOUT-DTI or ORGANIZER-CONFIRMED. | Holdout numbers: HOLDOUT-DTI. Leaderboard values (`0.4413`, `0.3904`) come from the organizer's platform for the public split, so they are labelled ORGANIZER-CONFIRMED (public split). `0.2778` and `0.3195` are USER-REPORTED and labelled that way. Raster-level counts are RASTER-MEASUREMENT. | README; `IR-79-149`. |
| R9 | Leakage canary AUC `> 0.90` means leakage. | Pilots: max `0.5316`. Canonical G79-THVC: max `0.8036`. Both pass. | run card; `evidence/g79_leakage_canary.json`. |
| R10 | End with a JSON run card. | Done. | `run_card_h80_pilots.json`. |
| R11 | At most 3 experiments and 2 hours. | `2` experiments used. The third is not used. Time: about 14:13 to 14:50 UTC against a budget ending about 16:13 UTC. | This review. |
| R12 | No automatic slot picking. | Compliant. `0` slots used. Promotion stays a separate selector step. | `submission_status.py`. |
| R13 | Put the full prompt into the README and read it each session. | Present in README under "Original project prompt". | README. |
| R14 | Executive summary and submission guide at the top of the site. | Present (`docs/executive-summary.html`), with official rules facts: three per week, mandatory AI disclosure, one final submission. | `docs/executive-summary.html`. |
| R15 | GitHub Pages site. | Exists from prior sessions. Rebuilt this session: 7 pages, `OK TO SUBMIT: NO`. Only `docs/irregularities.html` and `docs/research.html` changed. | `scripts/build_site.py` exit 0. |
| R16 | 3–5 untried hypotheses, ranked by DTI gain and cost. | Done (four). | `research/hypotheses_842c8c7c_ranked.md`. |
| R17 | Validate the top candidate on a spatially blocked holdout before using a slot. | **Not done.** H-A is not run. No slot was used, so the gate holds, but the top candidate is unvalidated. Listed as the first remaining item. | `research/hypotheses_842c8c7c_ranked.md`. |
| R18 | Create a PR and merge to `main`. | Pending (next step). | See end of session. |
| R19 | Multi-pass review, remaining work, and limitations. | Done here (Pass 1–3, sections below). | This file. |
| R20 | Official links for manual review. | Included in README and below. | Below. |
| R21 | Flag irregularities. | `IR-79-143`..`IR-79-151`. | `reports/irregularities.md`. |
| R22 | Eligibility and account conditions. | Not verifiable from the sandbox. Owner must confirm (rules §1.3; verifier's account-side conditions). | `IR-79-150`. |

## Official links for manual review

- DrivenData problem and DTI metric (page 967): https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- DrivenData leaderboard (public split): https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- DrivenData rules page (points to HeroX): https://www.drivendata.org/competitions/306/competition-doe-gems/rules/
- HeroX resource 2274 (official rules link): https://www.herox.com/GEMSPrize/resource/2274
- Official Rules PDF, Sept 2026: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- GeoDAWN (USGS, doi:10.5066/P93LGLVQ): https://doi.org/10.5066/P93LGLVQ
- GDR 1391 / MT conductance (doi:10.5066/P9TWT2LU): https://doi.org/10.5066/P9TWT2LU
- ScienceBase item 62979746d34ec53d276c113b: https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b
- INGENIOUS Great Basin compilation (doi:10.15121/1881483): https://doi.org/10.15121/1881483
- GDR submission 1391: https://gdr.openei.org/submissions/1391

## Remaining work (ordered)

1. **Validate H-A** (FNHR zero-catalogue physics head placed by the THVC Charnes-Cooper placer) on the quadrant-blocked holdout, seeds 20 and 30. Pre-register and **commit first**, then run, then compare with the `0.1905` / `0.1944` bar. This uses the third experiment. Only a pass lets a slot be considered. Expect a wiring step: the physics stack needs the GDR channels (`data/raw/external/gdr_*.csv` are present).
2. **Owner decisions.** (a) Eligibility and account conditions (rules §1.3). (b) Whether to pursue H-C (the MT conductance product is a 117 MB file at gdr.openei.org, which is outside this sandbox's outbound allowlist, so the owner must download it). (c) The source of the `0.2778` and `0.3195` values, which are not on the live board.
3. **Blind slot choice.** Rules §3.6.2 require the final submission to be chosen without knowledge of private-set scores. That choice belongs to the separate selector step, not to any automated run.
4. **Reconcile the seed-30 comparator gap** (IR-79-147). The pilot's C0 (`0.0490`) differs from the recorded receipt C0 (`0.0422`).
5. **Restore ASTER silica** if H-B is ever tested (IR-79-146). Low priority, because the signal is at or below chance.
6. **Annotate the old MT backlog.** The backlog in `research/hypotheses_post_thvc_backlog.md` still contains the invalid 500 m / 1.5 km / 3 km resistivity spec. A banner was added pointing to IR-79-144 and to the re-scoped ranking.
7. **Pages rebuild after any further edit.** The site was rebuilt cleanly this session (7 pages). Re-run `scripts/build_site.py` after any change to the README, the irregularity log, or the run card.

## Limitations

- **HOLDOUT-DTI is an offline proxy.** It uses quadrant-blocked hide-and-recover on the training catalogue with a 20 km block bootstrap. It is not the DrivenData private set. Phase 2 uses expert-revised labels, which this proxy does not model.
- **Two seeds only.** The bar is two seeds with the 95 % CI, not a full distribution.
- **Public and private splits differ.** Public leaderboard values are not private-split values (rules §3.6.1).
- **GeoDAWN radiometric values are uint8 without stated units** (`IR-79-152`). The K and Th signals are ordinal in this session.
- **Restored inputs come from owner mirrors**, not organizer-authenticated downloads (`IR-79-151`). Organizer checksums were not available.
- **Generative-AI disclosure.** The rules require it in the narrative (§3.2). The disclosure entry is in `knowledge/ai_disclosure.md`. It is not an authorship or eligibility certification.
- **Judging is human.** Automated scoring does not decide awards. A DOE judge makes the final determination (§3.6.4).

## Irregularities (this session)

`IR-79-143` timestamps (protocol breach) · `IR-79-144` MT backlog spec invalid · `IR-79-145` DRAPE negative · `IR-79-146` RADIO negative · `IR-79-147` C0 scatter / seed-30 receipt gap · `IR-79-148` nodata sentinel · `IR-79-149` unverified user-reported leaderboard values · `IR-79-150` official rules verified and eligibility unverifiable · `IR-79-151` owner-mirror inputs and identical label files.

Pass 2 defects (overlap arm mislabel, full-catalogue mask, hand-typed overlap string, IR pipe breakage, frozen count pin) are listed above and fixed.

## Verification log

- `scripts/verify_project.py`: exit 0, `all_checks_passed: true` (33 checks), including `readme_matches_card_decision`, `irregularities_table_rows_single_line`, `all_repo_json_strictly_valid`, and `only_canonical_upload_artifacts_published`.
- `scripts/submission_status.py`: exit 2, `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` (fail-closed).
- `pytest -q`: 363 passed (final run, after all edits).
- `scripts/h80_pilot_overlap_check.py`: exit 0, `NOT DUPLICATES`.
- `scripts/build_h80_run_card.py`: exit 0, verdict `negative`.
