# Three-pass repository review — session 91a8c516

Date: 2026-10-22. Branch: `arena/91a8c516-gemsdoe79`.

## Executive decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**

The [canonical TIFF](../docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif) is locally format-valid research output, not a competition-ready submission. The [submission guide](../docs/executive-summary.html) and [canonical run card](../run_card.json) correctly retain a negative verdict. No new raster, scientific experiment, selector approval, competition upload, or submission slot was generated/used during this review.

## Pass 1 — review and independently check the current state

Reviewed the start-of-session contract, README (including its retained original request), canonical card, irregularities, active and archived preregistrations, hypothesis shortlists, H33 forensic evidence, scripts, workflows and tests. The active H79-NHR/X1 experiment is stopped for duplication; historical positive decisions and branch names are not current authorization.

Installed the pinned `requirements.lock` in the ignored `.venv`. Ran:

- `.venv/bin/python -m pytest -q`: **242 passed**; one non-failing Rasterio/Affine pending-deprecation warning.
- `.venv/bin/python scripts/verify_project.py`: **29 checks passed**, including shared-template pins, reference hashes, TIFF/ZIP bytes, range/grid validation, holdout/card consistency, novelty evidence and refusal to promote.
- `.venv/bin/python scripts/check_site.py`: **PASS**, seven pages, 120 local links, two compatibility redirects, no external assets.
- `.venv/bin/python scripts/submission_status.py`: expected **exit 2**, download true, submit false.

Counts above are software checks, not scientific scores.

## Pass 2 — scientific and protocol review

Re-ran `.venv/bin/python scripts/preflight_new_lane.py --restore --report evidence/preflight_91a8c516.json`. Expected **exit 2**; [newly measured decision](../evidence/preflight_91a8c516.json) confirms the pinned witness covers every allowed cell under literal positive-support semantics. Any nonempty candidate therefore has overlap 1.0, exceeding the 0.70 gate. This is a registry measurement, not a score. No dense-prior exemption, jitter, private evaluator fork or retuning was introduced.

The current request does not delimit the promised single-method paragraph. Existing [four-candidate prospective shortlist](../research/hypotheses_preflight_a7d092d7.md) supplies layers, signatures, missing-fault rationale, differences, mimics and qualitative cost priorities; it is not evidence of four successful methods. Testing its top candidate now would contradict the preflight stop. Its first proposal also overlaps conceptually with archived far-field work, so a future lane must check the archived FF evidence before asserting novelty. Do not claim these are globally untried hypotheses.

### What the H33 evidence actually establishes

[Existing byte-level forensics](../evidence/h33_forensics.json) found H33 to be exactly the older D2.8 dot field with cells within two pixels of mapped faults removed, with no rule-disagreement pixels. Sparse, separated emissions and removing potentially unproductive near-catalogue dots plausibly improve false-positive efficiency. This does **not** establish a causal explanation of a private-test result: the private truth and an artifact-linked organizer receipt are absent. This session did not independently rerun that full historical two-raster comparison.

The user's 0.2778, 0.3195 and 0.4413 claims are **USER-REPORTED, unverified here**, not HOLDOUT-DTI or ORGANIZER-CONFIRMED scores. They disagree as to the current leaderboard maximum. No projection or promise of beating them is justified.

The canonical card's existing **HOLDOUT-DTI**, evaluator `gems57-pooled-hide-v2`, is 0.1431 (95% CI [0.1281, 0.1574], 11,321 withheld positive pixels) for seed 20 and 0.1522 ([0.1335, 0.1696], 11,342 positives) for seed 30. These are prior recorded results checked for consistency, **not retrained or rescored this session**, and not comparable directly with private leaderboard scores. They beat the fold-fair H33 control but do not override novelty failure.

## Pass 3 — final requirements and safety review

Re-ran the full tests, integrity checker and site checker after these documentation changes. Preserved the single canonical downloadable artifact, its original run card and name/note, all scientific evidence and the automatic negative decision. The original prompt remains in README; this session's request does not supersede its scientific stop gates. No implementation defect was found requiring scientific-code changes.

The reopened TIFF has one float32 band, EPSG:32611, shape 3730 × 3292, matching sample transform, values in [0,1], and no NaN/Inf anywhere. SHA-256: `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`. These are local measurements, not organizer acceptance. The previously reported range error cannot be diagnosed without the rejected bytes; the canonical research TIFF does not exhibit that defect.

## Source and access boundaries

Official links for review:

- [Organizer problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
- [Organizer leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- [Organizer reference repository](https://github.com/drivendataorg/gems-prize-reference-solution).
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).

The reference repository metadata and tree were reachable via GitHub API during this session. Other official domains, Dropbox and the supplied sibling Pages domains are outside this sandbox's outbound allowlist; their current contents, data availability, weekly cap and leaderboard were **not live verified**. Existing hash-pinned GitHub mirrors establish byte identity, not organizer-origin authentication. No DrivenData account session, submission-page receipt or remaining weekly capacity was available. This task predicts missing fault traces; it does not establish geothermal vent or reservoir discovery.

## Next-session priorities

1. Resolve the literal continuous-raster dot-definition contradiction prospectively with the protocol owner. Keep refusal automatic until then; this cannot be fixed by discarding inconvenient registry entries.
2. Once permitted, assign one explicit new method paragraph and preregister it, checking all active and archived methods first. Reuse the shared cache, buffered whole-segment hide/recover evaluator and writer; test individual feature canaries and both novelty stages within budget.
3. Require a better holdout result and a separate selector decision before slot promotion. Only an artifact-linked submission-page receipt can establish ORGANIZER-CONFIRMED performance.
4. CI must supply fresh official-source reachability and public deployment byte checks; local verification does not prove deployment freshness. Preserve the fail-closed download/submission distinction.

Machine-readable scientific conclusion: the unchanged [canonical JSON run card](../run_card.json). New software-review evidence: [preflight decision](../evidence/preflight_91a8c516.json). PR creation and merge are performed after this report's verification, not implied by it.
