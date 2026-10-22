# Repository review — session `c273c7a3` (2026-10-22)

## Outcome

**Negative; no new experiment, surface, placement, TIFF, or competition slot.** The request's non-negotiable novelty rule cannot be satisfied under the literal interpretation currently recorded in the repository. The automated preflight independently returned `impossible_under_literal_gate` with exit code 2. Generating a newly named or randomly perturbed TIFF would not make a valid unique submission and would violate the stop rule.

The existing canonical TIFF remains **OK TO DOWNLOAD: YES; OK TO SUBMIT: NO**. It is inherited G79-THVC research, not a new artifact. Its root run card, checksum, validator receipt, and negative selector state were not changed.

## Three review passes

### Pass 1 — scope, evidence, and hypotheses

Read the full README and the start-of-session contract, canonical run card, irregularities report, and preregistration records. The prompt's requested ranked hypothesis backlog already exists in [`research/hypotheses_e4a4422d.md`](../research/hypotheses_e4a4422d.md); it contains four candidate mechanisms and explicitly says they are unimplemented and unscored. The current top candidate is **G79-CJX**, a prospective cross-scale gravity/magnetic contact-junction statistic using the pinned training-feature stack (band 2 RTP and band 13 isostatic gravity anomaly). Its proposed physical signal is persistent orientation winding/branch structure across smoothing scales with compatible cross-contact contrasts. It could respond to buried intersections without requiring a surface scarp or catalogue linework. Its named mimics are pluton margins, caldera contacts, and survey seams. This is a hypothesis, not an established fault detector.

The existing work therefore satisfies the requested *proposal and ranking* step, but not the requested validation step. Validation was not attempted because the preflight's hard stop must precede all new lane work. No HOLDOUT-DTI result is claimed for G79-CJX.

### Pass 2 — novelty, inputs, and safeguards

The literal preflight witness is the hash-verified positive-support raster `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, whose 3-pixel halo covers all allowed cells. A separate certificate strengthens the finding for the ordinary 37,654-dot budget even under budget-matched comparison: a binary spacing-5 lattice leaves only 6,514 of 5,106,385 allowed cells outside its 3-pixel halo, so at least 31,140 of 37,654 candidate dots must overlap. The resulting lower bound is `31,140 / 37,654 = 0.827003771...`, above the stipulated 0.70 limit. This is a deterministic registry-geometry bound, not a geological score. The newer post-snapshot audit accounts for 1,199 verified prediction blobs, of which 1,189 are grid-comparable; this is a separate inventory from the canonical THVC run card's frozen 1,108-row scan and must not be substituted into its historical numbers. Receipts: [`evidence/registry_obstructions_certificate.json`](../evidence/registry_obstructions_certificate.json), [`evidence/post_snapshot_sibling_audit.json`](../evidence/post_snapshot_sibling_audit.json), [`evidence/post_index_sibling_audit_20261022.json`](../evidence/post_index_sibling_audit_20261022.json), and [`evidence/new_lane_preflight_a7d092d7.json`](../evidence/new_lane_preflight_a7d092d7.json).

Input availability was not overstated. This checkout has the two reference rasters and restore receipt, but not `data/raw/training_features.tif` or the other large raw inputs. The pinned manifest and earlier byte-verification receipt record a GitHub-hosted mirror for those inputs, but that is not the same as bytes currently present or a fresh organizer download. The prospective G79-CJX method needs the official competition feature stack; no new external scientific dataset is required. The separate G79-HFR idea in the backlog would require the USGS Great Basin heat-flow release (ScienceBase DOI `10.5066/P9BZPVUC`); earlier review verified the public metadata/listing, not ingestion of its binary data here. It is not the top candidate and is not ready for validation.

A separate unresolved input irregularity remains relevant to the lower-ranked radiometric idea: the `ext_geodawn_rad_u8` restore receipt conflicts with the manifest hash/size (`IR-79-99`). Do not use that band until the pin discrepancy is resolved. This does not affect the canonical artifact's already-recorded result.

### Pass 3 — implementation and publication verification

Created an isolated `.venv` and installed the repository's pinned `requirements.lock` so the project commands could be executed reproducibly; the environment is ignored and no dependency file changed.

- Before upstream reconciliation, `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q` — **477 passed**.
- After the first upstream reconciliation, the same suite — **480 passed**.
- After the latest `origin/main` updates were merged into this fixed branch, the final Python suite — **502 passed**; all added upstream tests were included.
- `node --test tools/browser-qa/download-check.test.cjs` — **12 passed** for selected-file SHA-256/size checking (no upload or submission approval).
- `.venv/bin/python scripts/verify_project.py` — all repository, frozen-evidence, status, TIFF/ZIP, and publication checks passed; current canonical decision remains negative.
- `.venv/bin/python scripts/check_site.py` — passed: 7 pages, 130 local links, all pages reachable, evidence-derived tables match receipts.
- `.venv/bin/python scripts/submission_status.py` — **exit 2**, correctly refused: literal novelty, negative scientific verdict, and missing selector approval/receipt/explicit approval.
- `.venv/bin/python scripts/preflight_new_lane.py --restore` — **exit 2**, `start_new_lane: false`; the expected literal-gate stop was reproduced.

No training, holdout, leakage canary, placement, scoring-slot selection, or upload was run. The existing G79-THVC holdout figures remain historical HOLDOUT-DTI outputs from `gems57-pooled-hide-v2`, not results from this review; their two seeds are not independent datasets. H33's reported public-site score is not linked here to an organizer submission-page receipt, so it is not called ORGANIZER-CONFIRMED. The official public leaderboard observation in the repository is a dated public observation, not a receipt for H33 or for this project's artifact.

## H33 interpretation and remaining work

The byte-level H33 forensic record establishes that its raster retains all 37,654 D2.8 dots and removes 6,436 other dots; the removed cells are within two pixels of catalogue traces, but are not exact catalogue pixels. The organizer's metric rewards nearby truth credit while also summing prediction false-positive cost. Consequently, thinning can improve the metric when it removes predictions that add little marginal truth credit, but this arithmetic does **not** establish that H33's particular deletions caused its reported score. The original score is not receipt-linked, and no causal or leaderboard claim is made. See [`knowledge/h33_review_e4a4422d.md`](../knowledge/h33_review_e4a4422d.md) and the official [competition metric description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric).

Before any future experiment or submission, the project needs a prospective owner-approved shared interpretation of the registry duplicate rule that is actually satisfiable, applied consistently to every lane and encoded in the shared tool—not a per-candidate exception. Then restore the pinned inputs, freeze one method, run feature-alone leakage canaries and matched buffered holdout against the best control, run the surface novelty gate before placement, and let the independent selector decide whether a slot is eligible. A local format PASS is not submission approval. The competition's login-protected account page and slot state remain inaccessible to this offline project.

## Source review links

- [Competition problem, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Official USGS GeoDAWN data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [Official USGS Great Basin heat-flow product metadata](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28)
- [Project's dated source ledger](../knowledge/review_e4a4422d_sources.json)

## Run card — this review (not a submission)

```json
{
  "hypothesis": "G79-CJX: persistent cross-scale magnetic/gravity contact-junction structure may reveal buried omitted faults; proposed, not tested.",
  "mechanism": "Multiscale ridge-director winding plus compatible signed contrast in pinned training-feature bands; no candidate surface was generated.",
  "named_non_fault_process_that_could_mimic_it": "Pluton margins, volcanic caldera contacts, and survey-block seams.",
  "holdout_dti": null,
  "holdout_dti_status": "NOT RUN: preflight stopped all new lane work. No evaluator version, withheld-positive count, or confidence interval exists for this hypothesis.",
  "correlation_overlap_vs_registry": "NOT MEASURED for a candidate surface or dots. Existing registry certificates prove that the stated overlap rule is unsatisfiable for a nonempty 37,654-dot map; see evidence/registry_obstructions_certificate.json.",
  "raster_sha256": null,
  "validator_output": "NOT APPLICABLE: this review generated no TIFF. Existing canonical TIFF passes local format/range checks but remains blocked from submission.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative"
}
```
