# Repository review — session `2364b96e`

**Date:** 2026-10-22 UTC  
**Branch:** `arena/2364b96e-gemsdoe79`  
**Starting commit:** `268c86424ef2a7837302953cb3cb1a4b9abe923d`  
**Disposition:** negative / review-only. No geological experiment, holdout evaluation, feature canary, candidate surface, final-dot placement, new TIFF, upload, or weekly submission slot was used.

## Executive finding

A new, unique, scientifically defensible, portal-ready GeoTIFF cannot be produced in this checkout without violating the supplied stop rules. The user's method-specific lane paragraph is missing, the pinned literal-novelty witness covers every allowed cell, and the runtime checker finds 0 of 13 required inputs present. We stopped before candidate construction rather than relabel an inherited raster or invent results.

This review did make one non-scientific safety improvement: submission readiness now requires the complete local official-format R1–R8 report in addition to the existing shared checks. The unchanged canonical THVC raster remains downloadable for research only, not eligible to submit. Its in-bounds range is valid, but it fails official R6 because its exterior is zero-filled. This R6 deviation is **not** established as the cause of the user's earlier portal range error; the rejected upload and receipt are unavailable.

## Three review passes

### Pass 1 — project contract, state, and stop conditions

- Re-read `AGENTS.md`, the latest canonical run-card evidence, and the complete original prompt preserved in `README.md` (`## Original project prompt`).
- The prompt refers to a “single method paragraph below,” but no actual lane paragraph is supplied. No lane was assigned by inference.
- `scripts/preflight_new_lane.py --restore` returned the expected refusal (exit 2, `impossible_under_literal_gate`). The verified witness, SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, covers 100% of allowed cells. Under the literal positive-support/3-pixel definition, every nonempty candidate would have forward overlap 1.0, greater than the 0.70 limit. This is a gate obstruction, not a holdout score.
- `scripts/data_status.py` reported `blocked_missing_inputs` at `2026-10-22T20:10:40.667076Z`: 0/13 verified, 13 missing, 0 mismatched. No competition-data restore was attempted; a restore would not resolve the independent novelty stop or supply a missing method paragraph.
- The canonical `G79-THVC` card is inherited, negative, and bound to SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`. It remains `OK TO DOWNLOAD: YES` for research and `OK TO SUBMIT: NO`.

### Pass 2 — reproduce the format discrepancy and close the readiness gap

Reopened the pinned official sample and the exact inherited TIFF with the rule-by-rule validator:

- Official `sample_submission.tif`: PASS R1–R8.
- Inherited THVC TIFF: FAIL R6 only. It has one float32 band, EPSG:32611, the exact template grid, no nodata tag, finite in-bounds values, and no in-bounds values outside [0,1]. In-bounds minimum/maximum are 0.0/1.0. All 7,111,787 outside-footprint cells are finite zero, whereas the official sample uses NaN there.
- The shared local validator still passes that file. Before this change, both `submission_status.py` and the selector used that shared result but did not require the separate official R1–R8 result. That left a latent path by which a future card might clear submission readiness despite the known R6 failure.

**Fix made:** `validate_path()` now returns both the shared local result and the official R1–R8 report, and verifies that the shared, reference-grid, and official validators inspected identical TIFF bytes. The status CLI and final selector bind that validated SHA-256 to the card's raster snapshot. `submission_decision()` requires an explicit official-format pass to allow submission; the new argument defaults to false. Research download remains distinct from submit approval. The project verifier and published status JSON carry the strict result and failed rule IDs. Regression tests prove that an otherwise-cleared synthetic card cannot submit when the official-format flag is false or merely truthy, or when validators report bytes different from the snapshotted artifact.

No shared writer, raster, run card, holdout receipt, novelty definition, or scientific code was changed. The strict R6 check is fail-closed pending the unresolved outside-footprint convention; it does not claim that R6 caused the earlier portal error.

### Pass 3 — independent regression, publication, and consistency review

- `scripts/verify_project.py`: exit 0, all checks passed, including the complete R1–R8 report, explicit R6 finding, exact card/raster hashes, and a submission refusal on official-format failure.
- `scripts/validate_portal_spec.py`: sample PASS; canonical TIFF FAIL R6 only (expected exit 2). `scripts/validate_submission.py` reports shared local `format_passed=true`, `official_format_passed=false`, failed rule `R6`; strict default CLI exit 1 (expected).
- `scripts/submission_status.py`: `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` and blocker `official_submission_format_not_cleared` (expected exit 2). `scripts/select_submission.py` returned selected false, card unchanged, with official R6 and literal novelty blockers (expected exit 2).
- Full test suite: **601 passed**. Static-site check: **passed**, 13 pages, 339 local links, all pages reachable from home. The generated JSON status reports official format false, failed rule R6, and submit false.
- These checks exercise software and frozen evidence only; they do not run a scientific experiment.

## Pre-implementation geological shortlist

The following five repository-scope ideas are carried forward from the ranked backlog in [`research/hypotheses_1f9d2dc9.md`](../research/hypotheses_1f9d2dc9.md). They are proposals, not measured results, and none was implemented or tested in this review. “Untried” means the exact signature was not found as an executable lane in the prior source audit; it does not mean globally novel. Rankings are qualitative scientific priority/cost only—**no numeric DTI uplift is projected**.

| Rank | Candidate signature and layers | Why it might add faults missed by the catalogues / key mimic | Readiness and cost |
|---|---|---|---|
| 1 | **Conjugate-strike accommodation / Riedel transfer zones:** fold-visible fault traces, magnetic RTP, gravity anomaly/gradient, and any verified geodetic-strain layer; score regional orientation-transition zones rather than local endpoints. | Targets short oblique transfer structures that may be simplified out of regional traces. Main mimics: inherited joints, caldera rings, pluton margins, and catalogue orientation bias. Exact relation to earlier tip/relay/junction lanes needs a source-code overlap audit before preregistration. | Lowest data cost if the supplied stack is restored; moderate implementation and fold-strict recomputation cost. Official problem/features page: [DrivenData description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). Not executable now: training inputs absent and literal preflight blocks a lane. |
| 2 | **Fan-apex, multi-drainage knickpoint collinearity:** absolute USGS 3DEP elevation, hydrologically valid channels, upstream-area-normalized longitudinal-profile curvature; independent scarp coherence only as corroboration. | Tests aligned profile breaks across several catchments, rather than a local scarp or vent-proximity signal. Main mimics: lithologic knickpoints, stream capture, transient incision, landslides, roads, and fan-head trenching. | Potentially useful but high processing/data cost. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) is the official source, but exact tile coverage, resolution and local bytes were **not** verified here; do not call this viable until those are checked. |
| 3 | **Relief-screened structural saddles crossed by an independent gravity gradient:** detrended elevation/slope plus isostatic gravity anomaly/gradient; multiscale Hessian saddle persistence with gravity crossing terrain contours. | Could target buried transfer zones between range segments missed by continuous range-front mapping. Main mimics: wind gaps, drainage divides, stream capture, landslides, and resistant-bedrock passes. | Low-to-moderate potential, moderate cost; supplied rasters are absent. The official [DrivenData feature description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) lists relevant feature families; channel tags and masks still need byte-level audit after restore. |
| 4 | **Paired well/spring geothermometer disequilibrium projected up-gradient:** official INGENIOUS temperature/chemistry observations, schema-confirmed geothermometer fields, defensible terrain flow paths, and independent gravity structure. | Tests fluid-chemistry/temperature residuals and transport direction rather than broad thermal proximity. Main mimics: shallow aquifer outflow, water mixing, well-depth bias, analytical error, and clustered sampling. | Uncertain and basin-limited; high QA cost. The [DOE GDR INGENIOUS page](https://gdr.openei.org/submissions/1391) lists a public resource, but its ZIP bytes and schema are not present or hash-verified here. |
| 5 | **Signed well heat-flow residuals along independently inferred structural corridors:** USGS Great Basin heat-flow observations relative to the source's conductive-background model, with well-quality/depth controls. | Could test local advective departures that broad thermal maps smooth away. Main mimics: non-fault groundwater flow, borehole corrections, depth bias, and uneven sampling. | Very high acquisition/QA cost and uncertain value. [USGS ScienceBase item 10.5066/P9BZPVUC](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28) lists a supporting ZIP; the binary, schema, license and target-area coverage were not verified in this checkout. |

The official source listings above establish where to investigate, not local acquisition, coverage, license for an uninspected binary, prediction skill, or organizer acceptance. No candidate is declared data-ready. Before any of these can be tested, resolve the shared novelty definition, restore and hash-check the pinned inputs, audit the raw band tags/masks, then pre-register one method and run its feature-alone canaries and spatially blocked holdout. Do not touch a weekly slot unless it beats the current matched holdout best and every independent gate clears.

## H33 result and potential improvement

The `0.2778` attached to H33 is an **unverified historical report**, not an `ORGANIZER-CONFIRMED` score in this repository: there is no file-linked submission-page receipt. The repository's latest 2026-10-22 source review records public leaderboard #1 as `0.4413`; that is a `PUBLIC-OBSERVATION`, not H33's score or a score for this project, and it was not freshly re-fetched in this review.

The inherited byte-forensics record says D2.8 has 44,090 positive pixels and H33 has 37,654, with 6,436 removed; H33 is a subset of D2.8. The documented rule was distance-to-catalogue thinning at `d_cat <= 2 px`. That geometry alone does not identify the hidden labels or establish why a portal score changed. Under the task's weighted metric, removing low-value/redundant predictions can improve the TP/FP/FN trade-off, while removing predictions near hidden truths can worsen it. The 300 m triangular kernel and α=0.2, β=0.8 do not let us infer a score from dot count alone.

**Can a future method exceed 0.2778?** It is possible in principle, but this checkout contains no new validation that demonstrates it. The historical local `HOLDOUT-DTI` values are not comparable to organizer leaderboard scores, and the current literal novelty/data stops prevent testing. No projected score is offered.

## Official references and evidence limits

- [Official DrivenData problem and submission-format page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — source URL embedded in the validator and reviewed in the repository's source ledger on 2026-10-22. The page was not freshly fetched during this code-review pass.
- [Official competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — linked from the repository source ledger; no account capacity, eligibility, or organizer receipt was checked here.
- [USGS 3DEP program](https://www.usgs.gov/3d-elevation-program), [DOE GDR INGENIOUS listing](https://gdr.openei.org/submissions/1391), and [USGS ScienceBase heat-flow listing](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28) — sources cited by the existing hypothesis backlog; not newly fetched, and no new third-party binary was acquired.
- The current checkout has no authenticated competition account view. It cannot verify remaining weekly slots or organizer acceptance. A download/readiness PASS is not an upload receipt.

## Remaining blockers and safe next steps

1. Provide the missing method paragraph or keep the current no-lane state; do not infer a lane.
2. Resolve the literal novelty comparator for continuous, all-support registry rasters prospectively. Do not change the threshold, jitter a candidate, cap dots, or use a private fork to evade the present stop.
3. Restore all 13 manifest inputs through the documented, hash-pinned process and confirm `data_status.py` reports 13/13 before model work.
4. Resolve the official outside-footprint convention with a prospective shared-writer decision or authoritative clarification. The current strict validator blocks R6; the legacy rejected file is still unavailable, so the earlier range error remains unexplained.
5. Re-run the ranked shortlist's source/tag audit against actual inputs, then pre-register one candidate and evaluate leakage canaries plus the buffered, spatially blocked `gems57-pooled-hide-v2` holdout. Only a measured, paired improvement over the current matched holdout best can justify a separate selector review.
6. Do not upload or spend a competition slot until the exact TIFF passes shared and official validators, novelty and scientific gates, and the participant's submission page independently shows a free slot.

## Reproducibility

The machine-readable negative review card is [`evidence/session_2364b96e_run_card.json`](../evidence/session_2364b96e_run_card.json). The strict portal-rule implementation is [`src/gems79/portal_spec.py`](../src/gems79/portal_spec.py); readiness logic is [`src/gems79/status.py`](../src/gems79/status.py); the historical format observation is [`evidence/portal_spec_calibration.json`](../evidence/portal_spec_calibration.json). The card intentionally has no candidate raster hash, holdout value, confidence interval, submission name, or organizer receipt because none exists for this review.
