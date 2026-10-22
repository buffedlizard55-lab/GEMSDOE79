# Session review b40c0d45 — repo review, submission-gate audit, and the "unique TIF" request

Branch: `arena/b40c0d45-gemsdoe79` (from `main` @ `baee09e`). Run card: [`evidence/review_b40c0d45/run_card.json`](../evidence/review_b40c0d45/run_card.json).

## Bottom line

- **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** Unchanged from the canonical card.
- **No new unique TIF was generated, and none should be submitted from this session.** The reason is not a formatting problem. The repo has no raw feature stack in this sandbox, no delimited method paragraph for a new lane, and the only available raster (G79-THVC) is a negative, non-unique result. An unvalidated raster would break the lane protocol.
- **One real format discrepancy was found and is flagged for owner review:** the canonical TIF writes `0` outside the footprint. The official rules say data outside bounds must be `null or nan`. This does not explain the portal's "range [0, 1]" message, and the leaderboard names suggest both fills have been accepted (user-reported, see below). It is not fixed here because changing the fill changes every gate.
- Verification ran against the repo's own tests, gates and independent raster reads. Source claims were checked against official pages (links below).

## 1. What was verified (and how)

| Check | Result | Evidence |
|---|---|---|
| Git state | branch correct; `main` has no conflicting work | `git status`, `git log` |
| Canonical TIF SHA-256 | matches card `d3db2e95…ecfee2` (137,299 B) | `sha256sum docs/downloads/*.tif` |
| Canonical ZIP SHA-256 | matches card `dfee2552…b788f9` | same |
| Locked env install | OK (numpy 2.4.6, rasterio, tifffile) | `pip install -r requirements.lock` |
| Full test suite | **477 passed** | `pytest -q` |
| `scripts/verify_project.py` | exit 0; `ok_to_submit: false`; blockers listed | run |
| `scripts/submission_status.py` | exit 2 (BLOCKED) — the expected refusal | run |
| `scripts/select_submission.py` | exit 2; card left unchanged | run |
| Independent raster read | 12,279,160 px; float32; EPSG:32611; 100 m; transform matches template; 35,093 positives inside footprint; 0 positives outside | `scripts/scan_tracked_rasters.py` + manual rasterio check |
| Scan of all 36 tracked GeoTIFFs | 4 flagged, all catalogue/label templates with −1 fill (not submissions) | [`evidence/review_b40c0d45/tracked_raster_scan.json`](../evidence/review_b40c0d45/tracked_raster_scan.json) |

**Correction to my own intermediate arithmetic:** while checking, I first assumed the footprint was 12,279,160 px. That is the full 3730 × 3292 grid. The official template's footprint (finite pixels) is **5,167,373 px**, with 7,111,787 px NaN outside. The canonical file has finite values everywhere because it writes zeros outside. The 35,093 / 5,167,373 = 0.679 % footprint fraction in its receipt is consistent with this.

## 2. Official rules, quoted and linked

- Submission format — GeoTIFF, EPSG 32611, 100 m, same bounds as training data, "**data outside the bounds is null or nan**", single float32 layer, "values between 0 and 1". Source: DrivenData problem page [`page/967`](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ("Submission format" section).
- Metric — distance-weighted Tversky, α = 0.2, β = 0.8, triangular kernel R = 300 m (3 px). Same page, "Performance metric".
- Entries — "You can make multiple submissions, subject to the limits specified on the competition website (three submissions per week)." Official Rules §3.2, [NLR PDF 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf). The repo's README states DOE §3.4 allows one final submission per entity; that wording is in the PDF's later sections and was not re-read line-by-line in this session.
- Leaderboard — #1 public best **0.4413** (xiaofanhu), #2 0.3904, … #22 **0.3183**, #23 0.3160. Source: [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). **0.3195 does not appear in the ranks shown.** It is not verifiable from this source.

## 3. Irregularities for review

1. **Fill convention disagrees with the official text (IR-B40-01).** Official template `data/reference/sample_submission.tif`: NaN outside the 5,167,373-px footprint. Canonical `g79-thvc…tif`: `0.0` outside (7,111,787 px). The shared validator (`vendor/gems57/validate.py`) enforces the zero policy ("no NaN anywhere", "outside_footprint_zero"), citing the portal-error cause as unproven. Owner decision needed: switch the fill to NaN in the shared writer, once, with an IR entry and updated tests. Not changed here.
2. **The portal error text is still not diagnosed.** "Predicted values must be in range [0, 1]" would be produced by values outside [0,1] — none were found in any tracked submission-like raster. A NaN-vs-zero fill is a plausible cause only if the portal treats NaN or zero as predictions, which the official text does not say. Unknown without the rejected file and its receipt.
3. **The leaderboard in the prompt contains same-score pairs that differ only in fill suffix** (user-reported, not organizer receipts): `gems68-…-nan: 0.0437` and `…-zeros: 0.0437`; `r7-nms3-dem10-scarp_…: 0.1294` and `…_allfinite: 0.1294`. If accurate, both fills scored identically, which would argue against fill as the cause of the range rejection. Treat as HOLDOUT-DTI/user-reported only, not organizer-confirmed.
4. **Two conflicting "top" figures in the prompt:** 0.4413 (verified public #1) and 0.3195 (not found on the public board). The prompt also says "0.3195 is the highest score right now".
5. **H33 score 0.2778** is labelled UNSCORED/unverified in the repo's own GEMSDOE32 analysis. Not a verified baseline.
6. The **raw training data is absent** (`data/raw/` does not exist; `data/restore_receipt.json` describes a previous restoration from a different checkout). The sandbox can reach only GitHub, npm and PyPI, plus the official pages read through the fetch tool. DrivenData data downloads, Dropbox and OpenEI are not reachable from the shell.

## 4. Why no new TIF was generated

1. **The lane protocol requires holdout validation before any slot is spent.** Holdout DTI needs the feature stack, the catalogue, and the evaluator. None are present (see irregularity 6).
2. **The lane protocol requires a method paragraph.** The repo README records that none was assigned in this session. Inventing one would be a private fork, which the protocol forbids.
3. **The canonical raster is negative.** Its literal novelty gate fails (maximum forward overlap 1.0). A fill-only or re-encoded variant would have the same content and would fail the same gate. Presenting it as a new submission would misrepresent it.
4. **No holdout number exists to report.** Any DTI for a new raster would be invented. This repo's rules do not allow that.

## 5. Hypotheses (what is already on file)

I did not invent new hypotheses here. The repo already holds four ranked, unvalidated candidates: **G79-CJX** (gravity/magnetic contact-junction localization), **G79-BLC** (bilateral lithology-contrast change-point), **G79-RSS** (relief-screened structural saddle), and **G79-HFR** (paired heat-flow recharge residuals, USGS DOI 10.5066/P9BZPVUC). See [`research/hypotheses_e4a4422d.md`](../research/hypotheses_e4a4422d.md). Each names its data, its non-fault mimic and its falsification test. None has been validated. The G79-HFR data is metadata-verified only; acquisition has not been done.

**To validate any of them, you need:**
- the 13 manifest inputs in `registry/data_manifest.json` (training features, labels, and external GeoDAWN / LiDAR products) — obtained from DrivenData with a login, or from the free public sources they cite;
- a shared-protocol decision on the method paragraph for the new lane;
- the holdout harness run on both seeds, with canaries, before any placement.

## 6. Recommended next steps (for the next session)

1. **Owner decision on the fill convention** (irregularity 1). If NaN is adopted, change `vendor/gems57/submission_writer.py` and `validate.py` once, add an IR entry, and update the tests. Then re-run the canonical check.
2. **Obtain the rejected file and its portal receipt** to diagnose the range error (irregularity 2). Do not guess.
3. **Assign a method paragraph** for the next lane and run the preflight (`scripts/preflight_new_lane.py --restore`) before any training.
4. **Acquire the raw data** through a DrivenData login by the account owner. The sandbox cannot do this. The download command in the repo is `scripts/download_competition_data.sh`.
5. Keep the leaderboard numbers labelled as user-reported until an organizer receipt exists.

## 7. Limitations

- No raw training or feature data here; no holdout run; no canary; no new score of any kind.
- The DrivenData submission page and private leaderboard require login; their state is unverified.
- The fill-convention finding is based on the official text and the repo's own validator, not on the portal's behaviour.
- The repo's 477-test pass covers the shared gates, not the scientific claims.
