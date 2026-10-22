# Repository review — 2026-10-22 — active Arena branch

## Executive decision

**No new experiment or submission TIFF was generated.** The repository's enforced start-of-session contract has no currently assigned, authorized method paragraph for this session; the shared new-lane preflight is an explicit stop because its literal 3-pixel overlap rule has a full-footprint registry witness. Generating a fresh raster without a permitted lane would violate the checked-in protocol and would not make it eligible to submit.

The existing canonical research artifact remains explicitly **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**. It is inherited G79-THVC, not a newly generated unique submission. Its local format is valid, but the full-registry novelty gate and separate selector block submission. No organizer receipt exists in the repository for this file. This review does not claim a new leaderboard result or a score above 0.2778, 0.3195, or 0.4413.

## Scope and current branch

Reviewed the full `README.md` (including the preserved original prompt), `AGENTS.md`, canonical `run_card.json`, irregularities, G79-THVC and archived lane preregistrations, current evidence, the four-hypothesis research backlog, the H33 analysis, and repository scripts/tests/site. The working branch is `arena/f652f0b3-gemsdoe79`. The repository was clean before this report was added.

The prose in `reports/repository_review_2026-10-22_active-branch.md` identifies a different branch and an NHR/X1 control state; that text is a historical report and must not be presented as this branch's execution. Active branch metadata, current `AGENTS.md` and root README state G79-THVC as the canonical artifact. Numeric historical evidence is not re-measured merely by this review.

## Three review passes

### Pass 1 — requirements, provenance, and artifact status

- Confirmed the prominent root README warning: existing TIFF is downloadable but **not for submission**.
- Confirmed the canonical G79-THVC card is marked negative, and its full literal novelty check fails with maximum 3-px forward overlap `1.0 > 0.70`; rank correlation alone does not clear it. The checked scan reports 1,108 expected registry entries, 1,088 comparable and 20 non-comparable. Do not reinterpret the sparse-only comparison as full clearance.
- Confirmed README carries four prospective research hypotheses in `research/hypotheses_e4a4422d.md`; G79-CJX is the nominated top candidate, but its own text says the shared preflight blocks execution. It is a backlog hypothesis, not a validated experiment or score projection. G79-HFR requires official USGS heat-flow data not acquired in this checkout, so it is not currently testable here.
- Reviewed H33 source note: `0.2778` is described as an unverified historical report and the GEMSDOE32 file as UNSCORED. The prompt's `0.3195` and public leaderboard observation `0.4413` are not artifact-linked organizer receipts. There is no defensible causal claim for why H33 received its reported value.
- The request to create a new competition-ready TIFF is not met by this repository state. The explicit refusal is safer than labelling a negative/inherited artifact as unique or ready.

### Pass 2 — automated verification and defects

Installed the exact checked-in `requirements.lock` into the ignored local `.venv` after discovering that system Python had no NumPy, pytest or BeautifulSoup; no dependency files were changed.

Commands and results:

- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q` — **477 passed**.
- `.venv/bin/python scripts/verify_project.py` — `all_checks_passed: true`; all 34 listed assertions passed, including hashes, TIFF/ZIP structure, format/range, card/evaluator consistency, preflight stop, publication inventory and README/status consistency. Raster SHA-256: `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`.
- `.venv/bin/python scripts/check_site.py` — passed: 7 pages, 128 local links, all reachable, 2 compatibility redirects, no external assets, `submit: false`.
- `.venv/bin/python scripts/submission_status.py` — returned the expected negative status: `ok_to_download=true`, `ok_to_submit=false`, `verdict=negative`; process exit 2 is intentional fail-closed behavior.

An initial attempt using system Python failed due to missing pinned dependencies. This environment issue was resolved locally with the lockfile; it was not an application test failure.

### Pass 3 — requested deliverable, scientific validity, and release safety

- The demanded “unique TIFF for the competition” cannot honestly be declared satisfied: the available file is inherited and fails the mandatory novelty gate. Do not upload it. No new TIF was generated because the preflight forbids proceeding under the literal overlap criterion.
- No HOLDOUT-DTI was computed in this review. Thus there is no new evaluator-version/withheld-positive/CI triplet and no claim that any candidate beats the current holdout best. Existing card values remain inherited evidence and must keep their `HOLDOUT-DTI` label.
- No ORGANIZER-CONFIRMED score exists without a submission-page receipt. No projections are scores.
- The project has a strong local audit pipeline and readable download/status warning, but does not fully automate current competition feed or authenticated DrivenData data downloads/account-side slot checks. The official account/login and receipt workflow cannot be inferred from local files.
- The root README embeds the long original prompt in an expandable section as requested. Its size and repeated requirements are maintenance risks; a future edit may add a concise canonical requirements index, but must preserve the original text and generated publication-contract checks.
- No official external URLs were freshly fetched in this review. Source claims are limited to the repository's prior evidence and official-source ledger; an old recorded check is not represented as a live/current external verification.

## Ranked next actions and blockers

1. **Resolve the shared protocol contradiction prospectively.** Obtain a documented, authoritative definition of how the overlap criterion applies to continuous full-footprint registry rasters and dot support. The current preflight has a universal witness; do not change thresholds, exempt dense priors or add local caps to get a pass. This is the direct blocker to a new candidate.
2. Once a valid protocol and authorized method paragraph exist, preregister one hypothesis and use cached features plus the shared holdout/evaluator/writer. Enforce the feature-alone leakage canary, surface novelty before placement and final-dot novelty after placement, and stop at the first failed gate. Stay within three experiments/two hours.
3. Test only on matched buffered whole-segment folds, visible-catalogue-derived features only, pixel-exact masking, pooled DTI (α=0.2, β=0.8, 300 m triangular kernel); report evaluator version, withheld-positive count and 95% CI. A promotion remains a separate selector decision and must beat the current holdout incumbent, not merely the H33 control.
4. Acquire only inputs available via a documented official/free source, then record actual checksums, license, schema, coverage and provenance. G79-HFR is not viable until the named USGS heat-flow residual product is actually accessible and validated. DrivenData authentication and actual account-side submission capacity remain external.
5. Keep the current TIFF plainly marked download-only/not-submit until every gate and selector receipt is re-derived. If a future artifact passes, make the TIF link the obvious download, but tie `OK TO SUBMIT` to the exact file hash and measured evidence.

## Limitations and evidence class

This is a repository/code/evidence review, not independent geological validation, a fresh full sibling-site census, a DrivenData upload, a leaderboard check, or confirmation of organizer acceptance. It does not establish hidden-test generalization, current weekly slot availability, participant eligibility, or score improvement. No “high-scoring” submission is produced because the extant gates explicitly prohibit one.
