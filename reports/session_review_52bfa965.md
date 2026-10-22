# Session review 52bfa965 — 2026-10-22 (branch `arena/52bfa965-gemsdoe79`)

**Outcome: no new scientific lane, no new submission candidate, no slot used.**
The automated decision is unchanged: **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**
The blocker is a protocol decision that only the protocol owner can make (IR-79-53). It is not a missing
human inspection step.

## Why no experiment was run

- `scripts/preflight_new_lane.py --restore` exits 2 on this checkout (reproduced, see the ledger). The witness
  raster covers 100 % of the allowed cells, so any nonempty candidate has 3 px overlap 1.0 > 0.70 under the
  literal definition. The preflight says to stop before experiments.
- AGENTS.md and the protocol forbid restarting a stopped lane or retuning its outputs.
- Any new lane needs a preregistered, shared-gate decision first (IR-79-03 / IR-79-47 / IR-79-53). That
  decision belongs to the user, so this session did not make it.

## Pass 1 — implement and verify (what was run, with exit codes)

| Step | Command | Result |
|---|---|---|
| Environment | `python3 -m venv .venv && .venv/bin/pip install -r requirements.lock` | exit 0 |
| Pinned inputs | `scripts/restore_data.py --ids existing_faults,sample_submission --target-dir data/reference --preserve-receipt` | 2 exact inputs verified |
| Project verification | `scripts/verify_project.py` | exit 0, `all_checks_passed: true` |
| Decision | `scripts/submission_status.py` | exit 2, `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` |
| Preflight (frozen) | `scripts/preflight_new_lane.py --restore` | exit 2, `impossible_under_literal_gate` |
| Tests | `pytest -q` | 230 passed (after edits, see Pass 2) |
| Site | `scripts/build_site.py` then `scripts/check_site.py` | both exit 0; 7 pages built |

## Pass 2 — review for bugs, wrong assumptions and edge cases

1. **Format wording overstated (fixed).** The public Format line said “zero outside the footprint” as a PASS.
   The official competition page says outside-bounds data “is null or nan”. The line now states the
   conflict, and a limitation bullet explains it (`scripts/build_site.py`, IR-79-67).
2. **Official sources disagree (flagged, not changed).** The rules text and the sample use NaN outside the
   footprint. The official reference notebook writes finite values. The team's all-finite policy matches the
   notebook. A protocol-owner decision is needed (IR-79-67).
3. **Preflight exit 3 vs 2 (documented).** The bare command fails closed with exit 3 because the witness is
   absent. With `--restore` it reproduces exit 2 (IR-79-68).
4. **Registry counts (clarified).** 92 index scopes vs 71 distinct repositories; both correct (IR-79-69).
5. **Leaderboard (checked).** The user-reported “0.3195 highest” does not appear in ranks 1–50 (IR-79-70).
   This is a claim to verify, not a confirmed fact.
6. **Canonical GeoTIFF (independently re-read).** The file was not regenerated. Its sha256 matches the card.
   It is float32, EPSG:32611, shape 3730 × 3292, with the same transform as the sample, values exactly {0, 1},
   no NaN, and 37,654 positive cells, all inside the sample footprint. This is format-valid under the
   team's all-finite policy but has the outside-footprint convention issue above.

No code bugs were found in the shared tools. The only code change is the wording in `scripts/build_site.py`.

## Pass 3 — re-check against the original request

| Request | Status this session | Evidence |
|---|---|---|
| Unique TIF, OK-to-download/submit obvious | **Done.** The decision is automatic and visible on the site and in the README. The canonical file is a downloadable GeoTIFF, labelled DO-NOT-SUBMIT. | `scripts/submission_status.py` exit 2; site top section |
| Unique TIF that may be submitted | **Blocked** by the literal duplicate gate (IR-79-53). No submittable candidate exists under that rule. | `evidence/universal_overlap_certificate.json`; preflight exit 2 |
| Beat 0.2778 / 0.3195 / 0.4413 | **Not testable here.** No organizer-confirmed artifact score exists. HOLDOUT-DTI is proxy only. The leaderboard values are public observations. | IR-79-23, IR-79-45, IR-79-70 |
| Research and hypotheses (3–5, ranked, validated before a slot) | **Existing backlog.** Four untested hypotheses are ranked in `research/hypotheses_preflight_a7d092d7.md`. None was validated, because validation needs a lane the protocol does not yet allow. | `research/hypotheses_preflight_a7d092d7.md` |
| Verify line by line against official sources | **Done** for the rules, the metric, the leaderboard and the reference notebook. Login-only data pages were not re-fetched. | Ledger below |
| Flag irregularities | **Done.** IR-79-67 to IR-79-70 added. | `reports/irregularities.md` |
| Executive summary and README prompt | Present and retained. This review is linked from the README. | `README.md`, `docs/executive-summary.html` |
| PR and merge to main | Done as the last step in this session. | see the PR link in the final answer |

## Verification ledger (official sources, fetched 2026-10-22)

| Claim | Source | Result |
|---|---|---|
| Metric: distance-weighted Tversky, triangular kernel R = 300 m, α = 0.2, β = 0.8 | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Confirmed |
| Format: EPSG 32611, 100 m, float32, one layer, values in [0, 1], outside bounds “null or nan” | same page, “Submission format” | Confirmed. Conflicts with the all-finite policy (IR-79-67) |
| Up to three submissions per week | https://docs.nlr.gov/docs/fy26osti/96647.pdf, §3.2 Process overview | Confirmed. The account's remaining slots are not observable |
| Public leader 0.4413 (xiaofanhu); rank 21 0.3261; rank 22 0.3183; no 0.3195 in ranks 1–50 | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | Confirmed |
| Reference solution: U-Net, Tversky α = 0.2 β = 0.8, writes an all-finite GeoTIFF | https://github.com/drivendataorg/gems-prize-reference-solution (`unet-mc-cv-reference-solution.ipynb`, commit `aebe92f`) | Confirmed by cloning the repo |
| Canonical GeoTIFF sha256 `abbf5314…50ee7a2`, dots 37,654, zeros outside the footprint 7,111,787 | local file and sample (rasterio) | Confirmed locally |
| Witness sha256 `ab0a0a62…` covers 100 % of allowed cells | `scripts/preflight_new_lane.py --restore` | Confirmed (exit 2) |

Not verified: the DrivenData data page (login required, IR-79-11), the account's weekly slot count, and any
organizer score for any artifact.

## Run card — session 52bfa965 (no experiment)

```json
{
  "schema": "gems79-session-card-v1",
  "session_branch": "arena/52bfa965-gemsdoe79",
  "lane": "none opened",
  "experiments_used": 0,
  "hypothesis": "none tested; no new lane authorised",
  "mechanism": "not applicable",
  "named_non_fault_process": "not applicable",
  "holdout_dti": "NOT RUN (no experiment)",
  "leakage_canary": "NOT RUN (no experiment)",
  "correlation_overlap_vs_registry": {
    "literal_witness_sha256": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
    "literal_witness_covered_allowed_fraction": 1.0,
    "limit": 0.70,
    "preflight_exit_code": 2
  },
  "canonical_raster_sha256": "abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2",
  "validator_output": {
    "crs_shape_transform_match_sample": true,
    "dtype": "float32",
    "values_min_max": [0.0, 1.0],
    "nan_count": 0,
    "positive_cells": 37654,
    "outside_sample_footprint_finite_cells": 7111787,
    "outside_footprint_convention": "conflict, IR-79-67"
  },
  "submission_name": "gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT",
  "submission_note": "unchanged from the canonical card (122 of 140 characters)",
  "holdout_dti_label": "HOLDOUT-DTI (gems57-pooled-hide-v2): carried from the canonical card, not re-measured here",
  "verdict": "negative (blocked: protocol decision needed)",
  "ok_to_submit": false
}
```

## Decision needed from the protocol owner (IR-79-53, IR-79-67)

1. **Duplicate gate for continuous rasters.** Keep the literal rule (no submittable file can exist), or adopt
   a preregistered chance-corrected rule, or pause until the organizers define “dots” for continuous rasters.
   The chance-corrected threshold would need to be preregistered before any new lane.
2. **Outside-footprint convention.** Finite zeros (team policy, matches the reference notebook), or NaN
   (matches the sample and the requirement list).

Until these are decided, no new candidate is generated and the protocol's stop stands.
