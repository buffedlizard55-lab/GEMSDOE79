# Session review — 2026-10-22 (`arena/2f4b0aa9-gemsdoe79`)

## Outcome and scope

This was a repository review, not a new experiment. No experimental surface, placement, candidate TIFF or competition slot was created/used. The active repo policy closes existing lanes and requires shared-registry pre-placement and final-dot uniqueness plus holdout superiority before a selector can approve a submission. The shared feature stack is not available in the runtime: `python scripts/data_status.py` reports 0/13 expected inputs verified, `training_supervision_ready=false`, and `core_pipeline_inputs_ready=false`. Thus no new holdout score or leakage canary can honestly be produced in this checkout. This is a hard validation limitation, not a reason to synthesize a score or bypass a gate.

## Candidate hypotheses and disposition

The repo already records source-grounded prospective concepts in `research/hypotheses_e4a4422d.md`. They are research backlog, not verified gains; this review does not promote or newly implement them. Ranked qualitatively there:

1. **Cross-scale potential-field contact junction (CJX family):** `training_features.tif` bands `rtp` and `iso_grav_anom`; scale-persistent director winding plus signed cross-contact contrast. It might flag buried intersections/terminations lacking obvious scarps. Pluton margins, caldera contacts and survey seams mimic it. **Important:** CJX has already been tested in this repository and stopped negative; it is not eligible to restart under the active policy. This entry is cited as an example of the earlier roadmap, not a new proposal.
2. **Bilateral lithology-contrast change point (G79-BLC):** potential-field ridges plus GeoDAWN radiometric rank layers; cross-flank joint-distribution shift along a ridge. Potential for transfer faults under alluvium; facies boundaries, lava contacts, and drainage changes mimic it. Its specified external rasters are missing and one has a recorded hash/size conflict (IR-79-99), so it is not presently viable.
3. **Relief-screened structural saddle (G79-RSS):** `det_elev`, `det_elev_slope`, and isostatic gravity bands; terrain saddle plus independent gravity contrast, not a visible-fault-tip continuation. Stream capture, erosional gaps, landslides and resistant bedrock mimic it. Requires the absent pinned stack; no score claim.
4. **Paired hydrothermal recharge/upflow residual (G79-HFR):** official USGS heat-flow well residual and quality attributes with gravity/magnetic context; paired warm/cool departures could reflect advective flow along buried permeability. Groundwater circulation, pumping, well corrections and sampling bias mimic it. Official metadata/listing is documented, but raw contents/coverage are not acquired; not currently testable.

Expected DTI improvements cannot be ranked numerically from the available evidence. Repository policy and the cited research review explicitly treat these as qualitative, uncertain proposals. The old H80-MT-PHASE concept is specifically disqualified as written: the linked official product is depth-integrated conductance, not the cited shallow resistivity slices. See the source correction in `research/hypotheses_e4a4422d.md` and `reports/irregularities.md`.

## Three review passes

**Pass 1 — implementation and verification:** No new code/artifact implementation was safe without a runnable data-backed holdout. Read repo policy and checked availability. `python scripts/data_status.py` returned exit 2 and explicitly lists all 13 runtime inputs absent from `data/raw`.

**Pass 2 — defect/assumption review:** Installed the repository's pinned-range dependencies into the ignored `.venv` (no tracked dependency changes). Executed `.venv/bin/python scripts/verify_project.py`: `all_checks_passed=true`. It confirms run-card/evidence agreement, TIFF/ZIP bytes and format, registry evidence reconciliation, leakage canary receipts, and the fail-closed negative submission status. Executed `.venv/bin/python scripts/check_site.py`: passed, 13 pages reachable, 339 local links checked, scientific tables/gates consistent, submit false. Ran `.venv/bin/pytest -q`: **597 passed**.

**Pass 3 — original-request and publication review:** Confirmed the active branch remains `arena/2f4b0aa9-gemsdoe79`; the pre-existing README contains the original mission prompt, explicit download-vs-submit decisions, and historical evidence corrections. `verify_project.py` verifies only the pinned historical artifact and explicitly reports `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` Its rejection reasons include literal novelty failure, negative scientific verdict, missing selector receipt, and absent explicit approval. It is not an organizer receipt and no leaderboard result is being represented as such. There is no basis to create or label a newly validated competition submission this session.

## Official review links

- Competition overview/rules and task description: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Competition about page: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Data tab (participant login required): https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- DrivenData reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- DOE/NLR GEMS technical report: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- DOE GDR submission 1391: https://gdr.openei.org/submissions/1391
- USGS GeoDAWN release: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- USGS Great Basin heat-flow source cited by the research backlog: https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28
- Official USGS conductance source (important correction to the unsupported MT-resistivity proposal): https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b
- EPSG:32611: https://epsg.io/32611

## Remaining blockers / next work

1. Obtain the participant-gated competition package through an authorized participant account on a machine where the download is permitted; place it in `data/raw/`, then verify the manifest hashes. Current status is 0/13; no access credentials were requested or stored.
2. Only after data restoration and an authorized, preregistered lane with a valid pre-placement novelty gate: reuse the shared cached stack, shared evaluator/writer, buffered whole-segment hide/recover split, visible-fault-only catalogue features, exact visible-fault mask, 300 m triangular kernel and pooled DTI. Run feature-alone leakage canaries before considering combined features.
3. Surface and final-dot scans must both pass the declared thresholds against the full available registry; report incomplete registry coverage honestly. Then compare matched holdout DTI with confidence intervals against the frozen incumbent, without selecting on the public leaderboard. Selector/weekly-slot decision remains separate.
4. Maintain the README / Pages mirror and automated feed only from verifiable artifacts/receipts; do not turn a download-ready research raster into a submit-ready result.

## Run card

```json
{
  "hypothesis": "No new candidate tested; review-only. Existing prospective ideas remain unvalidated.",
  "mechanism": "No experiment or placement. Audited existing evidence and fail-closed release status.",
  "named_non_fault_process_that_could_mimic_it": "Not applicable to this review; individual candidate mimics are recorded above and in research/hypotheses_e4a4422d.md.",
  "holdout_dti": {"evidence_class": "NOT_MEASURED_THIS_SESSION", "evaluator_version": null, "withheld_positives": null, "ci95": null},
  "correlation_overlap_vs_registry": {"evidence_class": "EXISTING_REPO_RECEIPTS_ONLY", "new_measurement": false, "active_release_gate": "FAIL / NOT CLEARED"},
  "raster_sha256": null,
  "validator_output": {"new_raster": "not generated", "current_pinned_artifact": "verify_project.py passed historical receipt; single-band grid, finite/range/CRS/shape/transform and byte checks verified there", "submit_approval": false},
  "submission_name": null,
  "submission_note": "Review only; no new candidate or submission slot.",
  "verdict": "negative"
}
```
