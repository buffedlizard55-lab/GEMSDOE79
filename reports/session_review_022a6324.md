# Repository review — session `022a6324` (2026-10-22)

## Decision and scope

**Negative; no new TIFF, surface, placement, holdout, or submission slot.** The mandatory literal novelty preflight was independently rerun and returned `impossible_under_literal_gate` (exit `2`) before any candidate work. Its pinned registry witness covers every allowed prediction cell; any nonempty map has measured forward 3-px overlap `1.0`, above the required `0.70`. This is a registry-geometry obstruction, not a geological score. Generating or renaming a raster after that stop would violate the lane protocol. The current project artifact remains **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** It is an inherited research file, not this session's new unique submission.

This session reviewed the repository, refreshed the official public-page checks, and verified the stop. It did **not** spend a competition slot. All results below distinguish historical HOLDOUT-DTI, public leaderboard observations, user-reported values, and raster/registry measurements; none is an organizer submission-page receipt.

## Three review passes

### Pass 1 — task, scientific evidence, and candidate hypotheses

Read the full README (including its preserved original prompt), `AGENTS.md`, canonical `run_card.json`, irregularities, the three named preregistrations, and the existing source-grounded research backlog. The repo already contains a ranked far-field backlog in [`research/hypotheses_2669a0a3.md`](../research/hypotheses_2669a0a3.md). I checked the proposed method names against local scripts and run cards; the following four are not implemented as executable lanes in this checkout. This is not a fresh exhaustive audit of all sibling repositories, so I do not claim global novelty. These are inherited proposals, not hypotheses newly validated in this session.

| Rank | Candidate and physical signature | Specific inputs | Why it could target faults missing from USGS/INGENIOUS | Difference from executable lanes here | Mimic / falsification | Relative potential and cost; data readiness |
|---:|---|---|---|---|---|---|
| 1 | **G79-RFTD — along-range relief/throw-deficit piedmont step-out.** Detect a persistent range-front relief and gravity boundary across a gap in mapped traces, then seek a basinward topographic break. | Cached `training_features.tif`: bands 12 `det_elev`, 19 `det_elev_slope`, 13 `iso_grav_anom`, 18 `iso_grav_anom_hg`; `ext_tiger_road_distance_m`; visible-only catalogue. | A secondary piedmont strand can be buried or subdued while regional relief and a density boundary persist across the mapped trace gap. | Starts from relief continuity across along-strike gaps, not from visible endpoints, a scarp-only ranker, or a multi-feature model trained to continue visible segments. | Lahontan/Bonneville shoreline benches, resistant-bedrock hogbacks, road/rail embankments. Falsify if the effect follows contour-parallel shorelines, roads, or closed topographic boundaries rather than an independently oriented gravity boundary. | **Moderate, uncertain** potential; **moderate** engineering cost. The research backlog's earlier “ready now” statement is not true for this checkout: `data/raw/` is absent. Needed raster inputs have a historical hash receipt, not present bytes or a fresh DrivenData download. Not runnable now. |
| 2 | **G79-MTHD — multi-altitude potential-field gradient-migration back-projection.** Track horizontal-gradient maxima across upward continuation levels, fit a dip-consistent trajectory, and back-project toward a source trace. | Cached magnetic bands 2 `rtp`, 9 `tmi_vg`, 13 `iso_grav_anom`, 11 `iso_grav_anom_vg`, 18 `iso_grav_anom_hg`; GeoDAWN extension band 4 `TMI_up150`. | Buried dipping faults may produce displaced geophysical gradient crests under basin fill even where surface scarps are absent. | Uses systematic cross-altitude crest migration and a source-depth/dip geometry, rather than a single-scale lineament, local gradient, or endpoint relay. | Dikes, lithologic contacts, volcanic margins, and flight-line artifacts. Falsify with direction/phase randomization and independent gravity/magnetic consistency; a signal confined to one survey seam or one altitude fails. | **Low-to-moderate, uncertain** potential; **moderate** compute/QA cost. Required rasters are not present in this checkout; restoration is blocked by the same lane preflight before any experiment. Not runnable now. |
| 3 | **G79-RSS — relief-screened structural saddle.** Identify catalogue-independent multi-scale saddles and require a cross-saddle gravity step. | Bands 12 `det_elev`, 19 `det_elev_slope`, 13 `iso_grav_anom`, 18 `iso_grav_anom_hg`; no catalogue-derived feature in the candidate surface. | Low-relief transfer structures between ranges may be missed where mapped inventories emphasize obvious range-front scarps. | Starts from terrain topology with independent potential-field corroboration, not mapped fault tips or a lineament-score ensemble. | Stream capture, wind gaps, landslides, drainage divides, resistant rock. Falsify if saddle likelihood has no independent cross-saddle geophysical support or follows drainage alone. | **Low, uncertain** potential; **moderate** cost. Only pinned cached layers are needed scientifically, but the stack is absent locally. Not runnable now. |
| 4 | **G79-HFR — well heat-flow residuals paired with hydrothermal up-gradient paths.** Separate local residuals from broad conductive background and test coherent positive/negative departures along a structural corridor. | USGS *Heat flow maps and supporting data for the Great Basin*, DOI [`10.5066/P9BZPVUC`](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28); quality-controlled well residual attributes plus cached gravity/topography. | Convective groundwater can perturb heat flow above blind permeability pathways that lack a mapped surface break. | Tests well residuals and flow direction, rather than point proximity to springs/vents or the existing 2-m probe features. | Ordinary groundwater circulation, pumping, borehole correction errors, and uneven well placement. Falsify with leave-one-well-cluster-out tests and quality/coverage stratification. | **Potential unknown; high acquisition and QA cost.** Official USGS metadata is available at the cited ScienceBase record, but the binary data, schema, coverage, and quality fields have not been acquired/verified in this checkout. Therefore it is **not a viable immediate candidate** and has no holdout result. |

The ranking is a qualitative experiment-priority judgment, not a numeric DTI forecast. `G79-CJX` was excluded from “untested” candidates because this repository already records CJX/CJX-DIR experiments and negative results. The older `H80-MT-PHASE` suggestion was excluded because the cited official product is depth-integrated conductance, not the shallow resistivity slices specified in that proposal; see the documented correction in `research/hypotheses_post_thvc_backlog.md` and `IR-79-149`.

### Pass 2 — data, H33, metric, registry, and publication safeguards

**H33 (`0.2778`) explanation, with provenance limits.** The exact value in the user's list is **USER-REPORTED HISTORICAL SCORE**, not `ORGANIZER-CONFIRMED`: no submission-page receipt links that score to the H33 raster hash in this repo. Raster forensics (`evidence/h33_forensics.json`; corroborating remeasurement `evidence/h33_remeasurement_3ca6c6a6.json`) establish a narrower result: H33 contains exactly the surviving pixels of the related D2.8 raster after removing pixels within 2 px of the existing-fault catalogue. The measurements are **RASTER-MEASUREMENT, not scores**: H33 has 37,654 positive pixels; D2.8 has 44,090; 6,436 were deleted; H33 contains no positive pixels absent from D2.8; and the deletion rule has zero measured disagreements. This is consistent with a metric-efficiency hypothesis: removing predictions that add little new nearest-truth credit may reduce false-positive mass. It does **not** prove the hidden truth, confirm the historical score-to-file mapping, or establish a causal score gain.

The official metric page describes a 300 m triangular distance kernel and false-positive/false-negative weights `alpha=0.2`, `beta=0.8`, with prediction probabilities constrained to `[0,1]`: [DrivenData problem, metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). This supports the qualitative thinning explanation, not a guarantee that H33 or any candidate generalizes. A local format PASS cannot diagnose the user's earlier portal error without the rejected bytes and portal receipt.

**Leaderboard reconciliation.** On 2026-10-22 I fetched the official public leaderboard directly: [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). Its displayed first-place public DW-Tversky result was **0.4413 (`PUBLIC-LEADERBOARD OBSERVATION`, not an artifact-linked submission receipt)**. This contradicts the prompt's “0.3195 is highest” as a current-leader claim. The H33 value remains user-reported absent its receipt. No claim is made that this repo's candidate reaches or exceeds either value.

**Historical internal comparator (not a new experiment).** The canonical G79-THVC values remain prior-run **HOLDOUT-DTI (`gems57-pooled-hide-v2`; each count is withheld positive pixels; each interval is 95% CI)**: seed 20, 11,321 positives, `0.1905` [0.1741, 0.2069]; seed 30, 11,342 positives, `0.1944` [0.1774, 0.2126]. These are frozen holdout outputs, not public leaderboard scores, not independent evidence from a new session, and not results for any of the four proposed candidates.

**Automated novelty stop.** `.venv/bin/python scripts/preflight_new_lane.py --restore` reverified the pinned witness and exited `2`: `covered_allowed_fraction=1.0`, `overlap_limit=0.70`, witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`. Under the protocol's literal positive-support/dot interpretation, every nonempty candidate is blocked before surface evaluation, canaries, holdout, or placement. This does not establish that all alternative definitions of overlap are impossible; changing the interpretation requires a prospective shared protocol-owner amendment, not a lane-local exception.

**Data availability irregularity.** `data/restore_receipt.json` records earlier SHA-verified restore measurements, but the current checkout has only `data/reference/existing_faults.tif`, `data/reference/sample_submission.tif`, and that receipt. The large `data/raw/` stack and external feature rasters are absent. Thus the old backlog's `G79-RFTD` “ready now” claim is stale for this checkout. It is not evidence of current file access, fresh organizer authentication, or a new experiment.

**No slot/no approval.** `scripts/submission_status.py` returned exit `2`, `ok_to_submit=false`, and blockers `literal_novelty_not_cleared`, `negative_scientific_verdict`, and missing selector approval/receipt/explicit approval. No manual upload overrides the automated refusal. The account-specific weekly-slot state is not visible from this repository.

### Pass 3 — execution and final requirements cross-check

To avoid mistaking missing system packages for project defects, installed the pinned `requirements.lock` into ignored `.venv/` and reran the commands there. No dependencies were changed in tracked files.

- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q`: **560 passed**.
- `.venv/bin/python scripts/verify_project.py`: **all checks passed**, including card/hash/TIFF/ZIP agreement, frozen evidence integrity, publication contract and negative status.
- `.venv/bin/python scripts/check_site.py`: **passed**, 11 pages, 259 local links, all pages reachable from home, evidence-derived status consistent.
- `.venv/bin/python scripts/submission_status.py`: **exit 2 expected**, because no submission is approved.
- `.venv/bin/python scripts/preflight_new_lane.py --restore`: **exit 2 expected**, because of the pinned universal literal-overlap witness.
- Current tracked worktree before this report: clean on the Arena-assigned branch. The report and navigation link are the only intended tracked changes; no canonical run card, raster, registry receipt, training feature, model, or slot state was changed.

## Official references for manual review

- [DrivenData problem, metric, data and GeoTIFF format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS Great Basin heat-flow data, DOI 10.5066/P9BZPVUC](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28)
- [DOE GDR 1391 / INGENIOUS](https://gdr.openei.org/submissions/1391)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)

Official source pages document products and challenge rules; they do not validate any proposed geological signature or promise a score increase.

## Remaining work and limitations

1. Resolve the literal novelty-rule obstruction through a prospective, shared protocol decision that applies uniformly to all candidates. Until then, do not generate a candidate or TIFF.
2. Only after that stop is lifted: restore and re-hash the required official/pinned feature inputs; freeze one method and its parameters before any holdout; run feature-alone leakage canaries; use the shared whole-segment buffered holdout and shared evaluator; compare both seeds and paired 95% CIs to the current best; check surface novelty before placement and final-dot novelty after; invoke the separate selector only if every gate passes.
3. Reconcile the absent current `data/raw/` files against the historical restore receipt. DrivenData's competition data page requires authorized access; a mirror hash match is not proof of organizer authentication.
4. Acquire and inspect the official USGS heat-flow ZIP/schema only if the HFR proposal is reconsidered; metadata availability alone is insufficient.
5. Do not claim H33's 0.2778 as artifact-linked without the corresponding submission-page receipt. A portal receipt for a future selected candidate and account-side slot/eligibility confirmation remain outside this offline review.
6. Refresh the public leaderboard snapshot periodically, keeping it separately labelled from HOLDOUT-DTI and from organizer submission receipts.

## Run card — this repository review (not a submission)

```json
{
  "hypothesis": "G79-RFTD was the highest-priority untested backlog proposal: range-front relief continuity plus independent gravity boundary may indicate unmapped piedmont strands; not evaluated because mandatory novelty preflight stopped new lane work.",
  "mechanism": "Proposed use of detrended elevation/slope, isostatic gravity anomaly/horizontal gradient, a road-distance nuisance screen, and catalogue-visible-only holdout features. No surface, feature stack, or candidate was generated.",
  "named_non_fault_process_that_could_mimic_it": "Pluvial shoreline benches, resistant-bedrock hogbacks, drainage captures, road or rail embankments.",
  "holdout_dti": null,
  "holdout_dti_status": "NOT RUN for this hypothesis. No evaluator result, withheld-positive count, or 95% CI exists. Historical canonical comparator only: HOLDOUT-DTI (gems57-pooled-hide-v2), seed20 n=11321, 0.1905 [0.1741,0.2069]; seed30 n=11342, 0.1944 [0.1774,0.2126].",
  "correlation_overlap_vs_registry": "No candidate surface or final dots were generated, so candidate correlation/overlap is not measured. Preflight registry witness SHA-256 ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be covers all allowed cells under literal support; any nonempty map has measured overlap 1.0 > 0.70. REGISTRY-MEASUREMENT, not score.",
  "raster_sha256": null,
  "validator_output": "NOT APPLICABLE: no TIFF generated this session. Existing inherited artifact's machine decision remains OK TO DOWNLOAD: YES; OK TO SUBMIT: NO. No NaN/range/CRS/shape/transform result is claimed for a new file.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative"
}
```
