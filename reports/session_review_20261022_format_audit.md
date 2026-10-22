# Session review — 2026-10-22 — official-format and gate audit

Branch: `arena/a1183e85-gemsdoe79` (fixed). Scope: review, restore, verify, audit.
**No new candidate TIFF was generated, no holdout experiment was run, no slot was used.**
Reasons are in §4. Every number below is labelled by evidence class.

Evidence classes used: `REPOSITORY-MEASUREMENT` (re-measured from bytes in this checkout),
`OFFICIAL-SOURCE` (read from an official page this session), `USER-REPORTED` (not verified),
`PUBLIC-LEADERBOARD-OBSERVATION` (seen on the DrivenData page on 2026-10-22; not an organizer receipt),
`HOLDOUT-DTI` (not produced this session).

## 1. Sources checked this session (official, with links)

| Claim | Source | Result |
|---|---|---|
| Metric = distance-weighted Tversky, alpha 0.2, beta 0.8, 300 m triangular kernel | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Confirmed (formula block on page). |
| Format: EPSG 32611, 100 m, same bounds, one float32 band, values in [0,1]; "data outside the bounds is null or nan" | same page, "Submission format" | Confirmed. |
| Top of leaderboard: #1 xiaofanhu 0.4413 | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | Confirmed. |
| #48 jgaines 0.2820; #50 arnofault 0.2817 | same page | Confirmed (top-50 snapshot). |
| 0.2778 (H33) appears on the leaderboard | same page, all 50 rows | **Not found.** |
| 0.3195 appears on the leaderboard | same page, all 50 rows | **Not found.** |

`knowledge/why_h33.md` states that 0.2778 matches "public Rank #48 `extradr19`". On the snapshot fetched today,
rank #48 is `jgaines` at 0.2820 and no `extradr19` row exists in the top 50. **Irregularity IR-S1 (flagged, not corrected).**

## 2. Restoration and verification (Pass 1)

- `bash scripts/download_competition_data.sh` restored 5 SHA-pinned inputs from the owner mirrors
  (`training_features.tif`, `existing_faults.tif`, `sample_submission.tif`, two GeoDAWN rasters). Hashes match `registry/data_manifest.json`.
  Restoration is integrity-pinned, **not organizer-authenticated** (per the script's own docstring).
- `labels.tif` is listed in the manifest with the same SHA-256 as `existing_faults.tif` (`7ba308cc…`), but the default
  restore id list does not fetch it. Not needed for the audit. **IR-S2 (note).**
- `pytest`: 560 passed. `scripts/verify_project.py`: exit 0; decision remains `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`
- `scripts/preflight_new_lane.py --restore`: exit 2, `impossible_under_literal_gate`, witness SHA-256
  `ab0a0a62…`. Re-measured, not copied from the card.

## 3. New measurements this session

Script: `scripts/audit_submission_format.py` → `evidence/official_format_audit_20261022.json` (tests: `tests/test_audit_submission_format.py`, 2 passing).

| Item | Measured value |
|---|---|
| Official sample fill outside footprint | **NaN** (7,111,787 cells), footprint = 5,167,373 finite cells, matches `load_grid` footprint |
| Official sample values | float32, {0, 1}, EPSG 32611, shape 3730×3292, pinned transform |
| Official sample positive pixels | 60,988 — **identical** to the USGS catalogue mask (`existing_faults` positives) |
| Local artifacts (G79-THVC, G79-CJX, G79-DZD) fill | **0.0** outside footprint (`zero_outside`), 0 NaN, values in [0,1], EPSG/transform match |
| Novelty witness (registry blob `374c88b1…`, GEMSDOE17 `E-proba-multiscale`) | Continuous probability surface, **positive support on 100.0 % (5,167,373 / 5,167,373) footprint cells**, 0 outside |

Implications, stated carefully:

- The repo's writer uses an **all-finite export policy** (`vendor/gems57/grid.py::write_geotiff`). The official text permits
  NaN outside the bounds. This is a deliberate local choice, not a format violation the portal is proven to reject.
  **IR-S3.** Whether zero fill causes any portal error is **unverified** (no portal receipt was available).
- The official sample is described as predicting "total fault absence", yet its 1-pixels are exactly the mapped catalogue.
  **IR-S4.** This is a documentation/data inconsistency for organizer review.
- The literal novelty rule treats any positive support as a "dot". A continuous witness covering 100 % of the footprint
  therefore gives overlap 1.0 for every nonempty candidate. This reproduces the repo's standing refusal (`preflight` exit 2).
  The repo already records this as the saturated-branch question (protocol item D-3, "needs a prospective owner decision").
  **IR-S5. Not changed here; changing it would be a post-hoc edit to pass a gate.**

## 4. Why no new TIFF was generated this session

1. Every nonempty candidate fails the literal novelty gate by construction (IR-S5). A new file would carry the same
   `OK TO SUBMIT: NO` verdict and would not be "unique" in the sense the gate measures.
2. The lifecycle guard refuses the DZD generator now: `require_open_lane('G79-DZD')` → "canonical lane missing or
   mismatched" (`run_card.json` is the closed `G79-THVC` card). A new lane needs its own prospective registration (`src/gems79/lifecycle.py`). **IR-S6.**
3. The unique artifacts that already exist are listed in the README with their gate verdicts. The DZD holdout (G3)
   is now *measurable* because training features restored, but only under a new registration.

## 5. Answers to the user's questions (evidence-labelled)

- **Why did 0.2778 score well?** Per the repo's analysis (`knowledge/why_h33.md`, not re-derived this session), H33 is a
  sparse binary dot set: a D2.8 Poisson set with 6,436 dots within 200 m of the catalogue removed, leaving 37,654 isolated 1-pixels.
  The mechanism is consistent with the official formula: TP_w takes a max over truth neighbourhoods, while FP_w sums p over
  every positive pixel, so sparse binary emission limits false-positive mass. **The 0.2778 value itself is `USER-REPORTED`**
  and not on the top-50 snapshot (IR-S1).
- **Can we beat 0.2778?** Not established. The best local holdout numbers are internal `HOLDOUT-DTI` values
  (G79-THVC 0.1905 / 0.1944, seeds 20/30, from the repo's frozen receipts), which do not transfer to organizer scores.
  Leaderboard context: #1 0.4413, #50 0.2817 (public observations).
- **Unique TIF?** Existing unique files are in `docs/downloads/` and `artifacts/`. Each is `OK TO SUBMIT: NO`.

## 6. Pass 2 — review of this session's own work

Defects found and fixed in the same session:

- `audit_submission_format.py` computed the official fill without the footprint, so the evidence had no
  `fill_convention` for the official sample. Fixed (footprint computed first).
- The `--write` branch silently replaced an existing evidence file. Now uses mode `x` and exits 2 with a message.
- A first draft test asserted an always-true expression and a no-op "does not clobber" test. Both removed; the remaining tests
  assert measured facts.

## 7. Pass 3 — re-check against the request

| Request | Status |
|---|---|
| Review repo | Done (§1–3). |
| Generate unique TIF now | **Not done** — §4 explains why; no bypass attempted. |
| "OK to download / submit" obvious | Existing files: `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` (README, `run_card.json`, `verify_project`). |
| Verify against official sources, links | §1 links. |
| Flag irregularities | IR-S1…IR-S6 (below). |
| Leaderboard 0.3195 / 0.2778 | Not on current top-50; user-reported only. |

Unresolved, needing an owner decision or external action:

1. **IR-S5 / D-3 (decision needed):** whether the literal "any positive support = dot" overlap rule should be replaced by an
   owner-approved chance-corrected or density-aware rule. Until then, no nonempty file can clear the gate.
2. **IR-S3 (decision + test):** whether to write official-convention NaN outside the footprint. This needs a shared-writer change
   and validator tests, and does not change any score in principle (p = 0 outside the footprint contributes nothing).
3. **IR-S4:** ask organizers which convention the sample actually encodes (catalogue vs absence).
4. **IR-S1:** the repo's rank-#48 cross-reference should be corrected or marked unverifiable.
5. **Portal receipt:** only a submission-page receipt can establish organizer acceptance. Not available here.

## Irregularities for review (summary)

| ID | Issue | Evidence | Action |
|---|---|---|---|
| IR-S1 | 0.2778 / 0.3195 not on the leaderboard; "#48 extradr19" cross-reference not reproducible | leaderboard fetch 2026-10-22 | Flag; no change to historical text |
| IR-S2 | `labels.tif` in manifest but not in default restore list | `scripts/download_competition_data.sh` | Note |
| IR-S3 | Zero fill vs official NaN fill | `evidence/official_format_audit_20261022.json` | Decision |
| IR-S4 | Official sample 1-pixels = catalogue, though page says "absence" | same | Ask organizers |
| IR-S5 | Witness covers 100 % of footprint → literal gate degenerate | same; `preflight` exit 2 | Owner decision D-3 |
| IR-S6 | DZD generator refused by its own lane guard under the current card | `require_open_lane` output | Frozen; new registration needed for any new lane |
| IR-S7 | `main` contains `artifacts/stepover/g79-stepover-tip-dilation-11500dots-20261022T190822Z.tif` (commit 66ae38a) with local format PASS and `approved_for_weekly_slot: false`, but no novelty or holdout measurement and no README/report section. Its receipt says 'research only; not submitted' | `artifacts/stepover/*.json` on main | Flag: needs a novelty measurement and a README entry before anyone treats it as a candidate. Not audited here |
