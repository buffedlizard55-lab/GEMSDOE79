# Session review `f40e4f2e` — automated selector completion and literal-stop confirmation

Date: 2026-10-22 (UTC)  
Branch: `arena/f40e4f2e-gemsdoe79`

## Executive decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The canonical GeoTIFF remains the byte-unique and pixel-unique `G79-THVC` research candidate. It is locally format-valid, finite, and in `[0,1]`, but it is **not protocol-unique** under the user's unchanged literal 3-pixel overlap rule. No new raster was generated, no new scientific experiment was started, and no competition slot was used because the mandatory preflight proved that every nonempty raster must fail the literal gate.

This is a negative deliverable, not permission to submit. The canonical terminal JSON card remains [`run_card.json`](../run_card.json).

## Why a new “unique” TIFF cannot truthfully be produced in this lane

The pinned registry witness (`sha256 ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) has positive support on every allowed cell. Therefore, for any nonempty candidate dot set `C`, every dot in `C` is within 3 pixels of witness support and the one-sided overlap is exactly `|C| / |C| = 1.0`. The required limit is `0.70`. Changing model physics, ranks, spacing, or random seed cannot alter that proof. The protocol says to log a duplicate and stop; silently replacing the literal rule with a chance-corrected or budget-matched rule would violate the prompt.

Machine reproduction:

```bash
.venv/bin/python scripts/preflight_new_lane.py --restore  # exit 2
.venv/bin/python scripts/select_submission.py             # exit 2
.venv/bin/python scripts/submission_status.py              # exit 2
```

## H33 answer, evidence classes kept separate

The repository's byte-level forensic result remains unchanged: the historical `H33` file is the `D2.8` dot field with 6,436 pixels no farther than 200 m from mapped faults removed. Sparse binary impulses fit the organizer's 300 m triangular Distance-Weighted Tversky geometry better than diffuse probability mass because a nearby impulse can receive weighted true-positive credit while broad mass continues to add false-positive cost. `0.2778` remains an **unverified historical filename-to-score report** in this repository unless backed by a submission-page receipt; it is not relabelled as HOLDOUT-DTI or ORGANIZER-CONFIRMED.

The canonical candidate has **HOLDOUT-DTI** (`gems57-pooled-hide-v2`) `0.1905` with 95% CI `[0.1741, 0.2069]`, `n=11,321` withheld positives (seed 20), and `0.1944` with 95% CI `[0.1774, 0.2126]`, `n=11,342` (seed 30). A local holdout cannot establish that it will exceed an organizer score of `0.2778`, much less the public leaderboard observation of `0.4413`; no projection is represented as a score.

## Candidate hypotheses reviewed before implementation

The required ranked backlog already exists in [`research/hypotheses_post_thvc_backlog.md`](../research/hypotheses_post_thvc_backlog.md): MT phase/resistivity × gravity-gradient colinearity; magnetic drape-height/source-depth deconvolution; lithology-normalized K–Th radiometric residual; footwall-relief slip-deficit inversion; and Coulomb stress-shadow suppression. Each names layers, transform/signature, missing-fault rationale, novelty relative to implemented work, expected benefit, implementation cost, and official-data availability. No candidate was implemented because the lane preflight stopped before experiment 1, as required.

## Infrastructure defect found and fixed once

The separate selector claimed to be the only tool allowed to approve a slot, but it rejected canonical `G79-THVC` merely as an unsupported lane without re-deriving its evidence. `scripts/select_submission.py` now has a canonical evidence adapter which independently reads the frozen canary, holdout, surface-uniqueness, final-dot-uniqueness, hash, and format evidence. It reports the real failed gates (`surface_forward_overlap_le_0_70`, `final_forward_overlap_le_0_70`, and `protocol_unique`) and leaves the run card and raster unchanged. It grants no exception and does not upload.

## Three review passes

### Pass 1 — implementation and direct verification

- Read the complete project brief, terminal run card, irregularity log, and required preregistrations.
- Re-ran the literal preflight: deterministic stop, exit `2`.
- Re-ran local readiness: download `YES`, submit `NO`, exit `2`.
- Added canonical selector evidence re-derivation; selector refuses on measured scientific gates rather than adapter support.
- Added focused tests for literal-overlap refusal and missing-receipt fail-closed behavior.

### Pass 2 — bugs, assumptions, and edge cases

- Corrected the initial adapter implementation to read the actual nested two-seed canary schema (`seed20`/`seed30`, `max_symmetric_auc`) rather than a nonexistent aggregate field.
- Corrected overlap extraction to the frozen receipt's `worst_dot_overlap` field.
- Confirmed malformed or absent canonical receipts produce a refusal rather than approval.
- Removed misleading README wording that said “all” gates pass and that selector comparison was merely pending.

### Pass 3 — full requirement reconciliation

- Confirmed the canonical TIFF is single-band `float32`, EPSG:32611, `3730 × 3292`, exact sample transform, finite, and in `[0,1]`.
- Confirmed no generated file is advertised as safe to upload.
- Confirmed the prompt is preserved in the README.
- Confirmed no weekly slot was used and no organizer score was invented.
- Confirmed the terminal run card remains one JSON card with hypothesis, mechanism, mimic, HOLDOUT-DTI + CI, registry comparison, SHA-256, validator output, name/note, and negative verdict.

## Remaining limitation / next action

A protocol owner must prospectively resolve the mathematically unsatisfiable literal overlap rule (for example by adopting one already documented density-aware definition) before any new lane can legally run. That is not a model or data-access limitation. DrivenData account eligibility and remaining weekly capacity are also not observable by this repository. Until both issues are resolved, the correct automated outcome is **DO NOT SUBMIT**.
