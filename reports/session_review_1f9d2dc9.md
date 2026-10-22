# Repository review — Arena session `1f9d2dc9` (2026-10-22)

## Decision

**Negative; stop before new science. No new candidate surface, holdout score, placement, TIFF, or competition-slot selection was performed.** The repository's mandatory preflight confirms a literal novelty obstruction, and the canonical run card says the experimental budget has already been exhausted. Generating a differently named, perturbed, or sparse raster would not satisfy the configured novelty gate. The inherited public download remains explicitly **OK TO DOWNLOAD: YES; OK TO SUBMIT: NO**; it is not new work and must not be manually uploaded.

This decision is fail-closed, not a claim that competition submissions are impossible under every possible organizer interpretation. It follows the current prompt's literal threshold and current repository protocol. Resolving that contradiction requires a prospective shared protocol-owner decision; a candidate-specific exception would invalidate the review.

## Three review passes

### Pass 1 — request, repository, evidence and hypotheses

- Read the complete repository README including the embedded original prompt, `AGENTS.md`, canonical `run_card.json`, `reports/irregularities.md`, and required preregistration records.
- The requested assigned method paragraph is absent. The prompt therefore does not designate an experimental lane.
- Audited current tracked data placement: `data/reference/existing_faults.tif`, `data/reference/sample_submission.tif`, and `data/restore_receipt.json` are present; `data/raw/training_features.tif`, `labels.tif`, lidar derivatives and other large inputs are absent in this checkout. Historical source/restore receipts are not evidence that those raw files are present now.
- The H33 interpretation already in `knowledge/h33_review_e4a4422d.md` is appropriately cautious: the user-reported `0.2778` is **UNVERIFIED HISTORICAL REPORT** rather than an organizer receipt. The public leaderboard entry `0.4413` is a **PUBLIC-OBSERVATION**, not proof for H33 or this artifact. The thinning argument is metric algebra, not causal evidence for why H33 scored as reported. No claim that a new method beats either number is justified.
- Reviewed prior candidate notes and checked executable source for relevant named methods. `G79-CJX` has already been executed and is not represented as untried. A consolidated, strictly non-numeric research ranking is in [`research/hypotheses_1f9d2dc9.md`](../research/hypotheses_1f9d2dc9.md): signed scarp-polarity/gravity concordance; relief-screened saddles; bilateral multichannel contact change-points; paired USGS well heat-flow residuals. Their value rankings are qualitative judgments, not DTI projections. Earlier speculative numeric ranges in historical backlog documents are not new scores and were not reused.

### Pass 2 — safety gates, inputs, and assumptions

- `.venv/bin/python scripts/preflight_new_lane.py --restore` returned exit code **2**, state `impossible_under_literal_gate`, with `start_new_lane: false`. The machine output's witness SHA-256 is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`. The verified certificate records a full-coverage positive-support witness, so every nonempty candidate has forward overlap 1.0 against it; this exceeds the literal 0.70 limit. This is a **NOVELTY-GATE MEASUREMENT, not a score**. The preflight stopped before experiment work.
- The root run card records `experiment_count: 3` and `max_experiments: 3`; this review did not run a fourth experiment. There is no new HOLDOUT-DTI for any hypothesis, and no leakage canary was run.
- The official USGS ScienceBase [Great Basin heat-flow release](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28) was opened with the research fetch tool. The official metadata lists DOI `10.5066/P9BZPVUC`, describes a well-point residual attribute that may indicate hydrothermal or groundwater influence, and lists a 124.12 MB supporting ZIP. The binary was not downloaded or schema/license/coverage validated; HFR remains non-viable for immediate execution.
- The official [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and USGS [GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) were checked against the project source ledger. Official source metadata describes problem/data, but cannot establish that the absent local inputs are restored, a proposed transform is scientifically predictive, or a portal would accept an artifact.
- An existing irregularity remains: the repository documents conflicts in radiometric-band semantics/hash receipts (IR-79-13, IR-79-99). The proposal therefore excludes radiometric channels until a prospective reconciliation.

### Pass 3 — implementation and publication checks

Environment setup was isolated in ignored `.venv/`; no tracked dependency files or scientific bytes changed.

- `.venv/bin/python scripts/verify_project.py` — **PASS**; all frozen evidence, local format/range, ZIP, card/status, publication contract and stop-state checks reconciled. The canonical submission decision remains negative.
- `.venv/bin/python scripts/check_site.py` — **PASS**; 11 pages and 259 local links checked, all pages reachable, receipt-derived summaries consistent.
- `.venv/bin/pytest -q` — **560 passed**.
- `.venv/bin/python scripts/preflight_new_lane.py --restore` — expected exit **2**, no new lane.
- Initial bare system Python did not have project dependencies; a system-wide `pip install` was correctly rejected by the externally-managed-environment guard. A repo-local ignored virtual environment was created and `requirements.txt` installed there. No global package changes were made.

No training, canary, holdout, DTI calculation, candidate-surface comparison, placement, TIF writing, selector invocation, competition upload, or account-side slot inspection was performed.

## Main synchronization for PR review

GitHub main advanced while this documentation PR was open. To make the PR mergeable, the latest `origin/main` was merged into this fixed Arena branch; no branch switch occurred. That concurrent main update included the archived `H79-PFSD` TIFF/evidence bundle and the `G79-STPO` research TIFF under `artifacts/stepover/`. These were produced in parallel, not by this review. The PFSD README says its artifact was archived and not selected; the STPO JSON states `OK TO DOWNLOAD: YES`, `OK TO SUBMIT: NO`, and lists holdout, leakage, and complete novelty checks as absent. Neither artifact is endorsed or promoted by this report.

The merge also made an important historical evidence inconsistency more visible: `reports/session_review_9574eb05.md` calls H33's 0.2778 **ORGANIZER-CONFIRMED**, while `knowledge/h33_review_e4a4422d.md` and `knowledge/review_e4a4422d_sources.json` classify it as unverified and say the sibling page labels its artifact UNSCORED. No artifact-linked submission-page receipt is cited in that report. Treat the H33 numeric claim as **UNVERIFIED HISTORICAL REPORT** unless such a receipt is supplied; this review did not edit the historical report or manufacture one.

After syncing main, this review's changes remain documentation-only. The complete test, project-integrity, and site checks were rerun on the merged tree before PR merge.

## Flagged irregularities / unresolved limitations

1. **Mandatory novelty rule is unsatisfiable as written:** frozen full-coverage witness and literal forward-overlap threshold conflict. Do not silently amend it locally.
2. **Training stack absent from current checkout:** prior restores/mirrors in repository history do not equal current bytes on disk. Competition data download is account/login-gated; this review did not use credentials or an unverified mirror.
3. **No assigned paragraph:** prompt's “single method paragraph below” is not present. No lane can be inferred safely.
4. **H33 numeric claim:** `0.2778` remains unverified from a submission receipt; no causal attribution to thinning is established. Public leaderboard values are observations only.
5. **Heat-flow source:** official metadata/listing was obtainable; the listed 124.12 MB ZIP was not ingested or validated. Metadata accessibility must not be called data availability for modeling.
6. **Old speculative deltas:** historical proposal documents contain numerical expected gains. They are not observed evaluator output and should never be presented as scores. This review made no numerical score forecast.
7. **PR/merge state:** this review has no scientific approval to create or promote a TIFF. A documentation-only PR may carry this negative review; it cannot change lane authorization or the submission selector state.

## Source links for review

- [DrivenData competition problem, datasets, and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [Official USGS Great Basin heat-flow metadata / DOI 10.5066/P9BZPVUC](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28)
- [Official USGS Quaternary Fault and Fold Database](https://www.usgs.gov/programs/earthquake-hazards/faults)
- [Repository source ledger](../knowledge/review_e4a4422d_sources.json)

## Review run card (JSON; no submission artifact)

```json
{
  "hypothesis": "Ranked, unexecuted backlog: signed scarp-polarity/gravity concordance is the highest-priority conditional candidate; no candidate was authorized or tested.",
  "mechanism": "Preserve lidar scarp-face sign and test its normal-direction agreement with independent gravity change; this would be a feature-only test, not a new allocator or a copy of a prior raster.",
  "named_non_fault_process_that_could_mimic_it": "Pluvial shorelines, fluvial terraces, landslide scarps, lithologic contacts, survey seams, and shallow groundwater circulation.",
  "holdout_dti": null,
  "holdout_dti_status": "NOT RUN: preflight stopped before experiments; no evaluator output, withheld-positive count, or 95% CI exists for this candidate.",
  "correlation_overlap_vs_registry": {
    "evidence_class": "NOVELTY-GATE MEASUREMENT (not a score)",
    "candidate_surface_correlation": null,
    "candidate_final_dot_overlap": null,
    "frozen_witness_covered_allowed_fraction": 1.0,
    "literal_overlap_if_candidate_nonempty": 1.0,
    "literal_overlap_limit": 0.70,
    "result": "preflight stop; no candidate surface was made or measured"
  },
  "raster_sha256": null,
  "validator_output": "NOT APPLICABLE: no new TIFF was generated. The inherited canonical TIFF's local format passes but its submission verdict remains NO.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative"
}
```
