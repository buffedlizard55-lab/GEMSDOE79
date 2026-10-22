# Session review `9340b31a` — official-rule validator, executive-summary check, H33 answer, and what is blocked (`arena/9340b31a-gemsdoe79`)

**Decision (unchanged, machine-derived):** OK TO DOWNLOAD: YES (research artifacts only). OK TO SUBMIT: NO.
**No new candidate GeoTIFF was generated and no competition slot was used.** Reason in §3.

## 1. What was built and verified

| Item | Evidence |
|---|---|
| Official-rule validator R1–R8, transcribed from the official Submission-format section (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/, fetched 2026-10-22) | `src/gems79/portal_spec.py`, `scripts/validate_portal_spec.py` |
| Tests: 14 rule-by-rule cases incl. calibration (template passes; project TIFF fails exactly R6) | `tests/test_portal_spec.py` (14 passed) |
| Calibration evidence, sha256-bound | `evidence/portal_spec_calibration.json` |
| Executive-summary page: generated “Official-rule validator” panel and the new command in “Recheck automatically” | `scripts/build_site.py` → `docs/executive-summary.html` (only generated page that changed) |
| Irregularities IR-79-207 and IR-79-208 | `reports/irregularities.md` |

Calibration results (measured, not projected):

| File | R1–R8 result | Note |
|---|---|---|
| `data/reference/sample_submission.tif` (official template) | PASS all 8 | 7,111,787 NaN outside; 5,167,373 inside, all 0/1 |
| `docs/downloads/g79-thvc-…-DO-NOT-SUBMIT.tif` | FAIL R6 only | 7,111,787 of 7,111,787 outside cells = 0, not NaN |
| `artifacts/cjx/g79-cjx-…tif` | FAIL R6 only | same |
| `artifacts/dzd/g79-dzd-…-DO-NOT-SUBMIT.tif` | FAIL R6 only | same |

The three project TIFFs' SHA-256 values match those recorded in the README (THVC `d3db2e95…`, DZD `42a87578…`), so the validator read the same bytes the project publishes.

## 2. The “Predicted values must be in range [0, 1]” error — what we can and cannot say

- **Measured:** every project TIFF has all in-footprint values in [0, 1] (R8 PASS). A value-range check on these bytes therefore cannot reproduce the portal message.
- **Measured:** every project TIFF writes 0 outside the bounds, where the official text says “null or nan” (R6 FAIL).
- **Unverified:** whether R6 caused the earlier message. The rejected upload and its receipt are not available. A plausible mechanism is a portal that evaluates NaN as out of range, but the official template itself uses NaN outside, so NaN exterior cannot be ruled in or out from here. No cause is claimed.
- **Owner decision:** the shared writer's all-finite zero policy (`vendor/gems57/grid.py`, documented as “the only submission-compatible mode”) directly conflicts with the official sentence and the official template. Resolving it requires a decision and a sample-matching test on a real candidate, not a validator edit. No file was regenerated.

## 3. Why no new unique TIFF was generated this session

- `scripts/preflight_new_lane.py` returns exit 2 (`impossible_under_literal_gate`): one hash-verified registry raster (`ab0a0a62…`) covers 100% of allowed cells, so any nonempty candidate has 3-px overlap 1.0 > 0.70 (`evidence/preflight_e4a4422d.json`).
- The earlier unique files (CJX, CJX-DIR, DZD) were all generated and each was blocked or left unmeasured under these same gates (DZD's holdout and full-registry novelty were never measured because its inputs are absent). Making a fourth file with the same outcome would add clutter, not progress.
- The validator now makes any future candidate's format checkable in one command. That is what the request “never get that error again” needs. The uniqueness question is an owner decision (§6).
- Note on the user's request: “DO NOT COPY A PREVIOUS SUBMISSION”. A zero→NaN re-encoding of an existing candidate would be a copy of the same surface. It was not produced.

## 4. Why H33 (`0.2778`) may have scored well — PhD-level reading, with the limits

Verified algebra (from the organizer's definitions on the official page): with `T = TP_w`, `F = FP_w`, `G` = number of scored truth pixels, and `FN_w = G − T`,

`DTI = T / (0.2·T + 0.2·F + 0.8·G + ε)`.

Consequences, checked line by line:
1. The `0.8·G` term is a fixed denominator. Recall (`T`) is the only way to raise the numerator. Extra dots help only if they add coverage of truth pixels.
2. A prediction's false-positive contribution is `p·[1 − max_g k(d)]`, so a dot inside the 300 m kernel of truth costs little and a dot far from truth costs about `0.2·p` in the denominator. Deleting a redundant off-catalogue dot therefore raises DTI with no coverage loss. This is exactly the pattern in the repo's measurement: H33 = D2.8 minus 6,436 nearby off-catalogue pixels (44,090 → 37,654), with 0 pixels removed from the catalogue and 0 H33 pixels absent from D2.8 (`knowledge/h33_review_e4a4422d.md`).
3. The gain is therefore an efficiency gain (less redundant prediction mass at equal coverage), not a discovery of new faults. Whether it actually raised the organizer score is **unknown**: the organizer's truth is hidden and the 0.2778 is an unverified historical report (GEMSDOE32 labels it UNSCORED).

Can we beat 0.2778? **Not demonstrated.** The public leaderboard leader is 0.4413 (`xiaofanhu`, `#1`, observed 2026-10-22 at https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). The repo's best internal HOLDOUT-DTI is G79-THVC `0.1905 [0.1741, 0.2069]` (seed 20, n = 11,321) and `0.1944 [0.1774, 0.2126]` (seed 30, n = 11,342). These are **HOLDOUT-DTI** from the shared evaluator, not organizer scores, and are not on the same scale as the leaderboard.

## 5. Hypotheses (3–5 requested) — status, not new validation

The repo already holds five ranked, untried hypotheses (`research/hypotheses_0d90d81b.md`, IR-79-173…177). I did not validate any of them this session:
1. `G79-SFGC` — signed scarp-facing polarity + gravity concordance (input `lidar_scarp_features_u8.tif`). Ranked first. Its document says “DATA-READY”, but in **this checkout `data/raw/` and `external/` are absent**, so the input is not available here until restoration is run and hash-checked.
2. `G79-UGBP` — up-gradient kinetic geothermometer back-projection.
3. `G79-MDSC` — multi-altitude magnetic upward-continuation depth screening.
4. `G79-PSDC` — playa-subcrop cementation lineaments.
5. `G79-MCST` — GPS-velocity principal-strain Mohr-Coulomb slip tendency.

Protocol says none may run until the owner resolves the novelty-gate policy (IR-79-116), so validating the top one would violate the lane rules. Running it is the next step **only after** that decision.

## 6. Three review passes (required by AGENTS.md item 8)

- **Pass 1 — implement and verify.** Validator + CLI + tests + calibration + site panel. 14/14 validator tests; `build_site.py` deterministic; `check_site.py` PASS.
- **Pass 2 — bugs and edge cases.** Found and fixed: test fixtures picking an exterior pixel (R8 tests); deprecated `*` on affine transforms (now `@`); a shifted-grid file correctly marks R6–R8 unevaluated. The calibration evidence first recorded an absolute sandbox path; it now stores repo-relative paths (verified: no `/home/user` string remains). The site anchor edits failed twice on quoting; each attempt was verified by reading the file bytes, not assumed.
- **Pass 3 — requirements re-check.** The request's “unique TIF” and “download to submit” items remain **unmet by design** (§3). The “never get the range error again” item is met only as a local format gate; it cannot see the portal's own check. The “executive summary at the top” item already exists (`docs/executive-summary.html`, download panel first); the new validator panel is added below it. The README already contains the full original prompt (search “THE FOLLOWING IS THE HIGHEST URGENCY”), so it does not need a second copy.

## 7. Owner decisions and limits (not resolved here)

1. **Zero vs NaN outside the bounds.** Official text and template say NaN; shared writer forces zeros. Decide, then add a sample-matching writer mode and a real candidate test.
2. **Novelty gate.** The literal rule is unsatisfiable against the 100%-footprint witness; the chance-corrected D-2 reading exists in shared code. The owner must choose and document a prospective rule (IR-79-116). No silent change.
3. **Portal feedback.** Only the submission page's receipt can show the portal's actual check. The user should save the exact message and file name for any future rejection.
4. **Data.** `data/raw/` is absent (login-gated; mirrors are hash-pinned but not organizer-authenticated). Holdout re-runs need restoration first.

## 8. Next steps (suggested)

- Owner decides items 1–2 above; then implement the NaN-exterior writer mode once in shared code with an IR entry.
- Only then run `G79-SFGC` on the frozen holdout under its preregistration.
- Keep `scripts/validate_portal_spec.py` as a required gate before any future upload.
