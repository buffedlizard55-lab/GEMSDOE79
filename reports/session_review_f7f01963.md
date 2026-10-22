# Session review `f7f01963` — repository, gate, and publication audit

**Decision: negative. OK TO DOWNLOAD: YES (inherited research only). OK TO SUBMIT: NO.** No new scientific surface, experiment, holdout evaluation, placement, TIFF, selector action, upload, or competition slot was created. This review did not try to get around the literal novelty stop.

## Pass 1 — inspect the project and evidence

- Read the complete project README and the applicable start-of-session contract, current review/run card, irregularities ledger, lane preregistrations and H33 analysis. The full prompt's assigned method paragraph is absent; existing lanes are explicitly closed.
- Re-ran `scripts/preflight_new_lane.py --restore`. It returned exit **2**, `impossible_under_literal_gate`. The pinned witness SHA-256 is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`; it covers 100% of allowed cells, so any nonempty prediction has literal forward 3-pixel overlap 1.0, greater than the 0.70 limit. The stop applies before both surface trust and final placement. This is a **REGISTRY-MEASUREMENT**, not a model score.
- Re-ran `scripts/data_status.py`: **13/13** local manifest inputs are present and SHA-256 match their owner-mirror pins. These bytes are ignored runtime data; pin agreement establishes mirror integrity, not DrivenData provenance, licensing, or semantics.
- The official template passes `scripts/validate_portal_spec.py` R1–R8. The inherited downloadable THVC TIFF fails **R6**: all 7,111,787 exterior cells contain zero instead of null/NaN. This confirms the documented export-format mismatch; it does not establish the cause of a different historical upload's range error.
- The root README's first block incorrectly described TIPSTEP as the current session and linked an unregistered orphan page that made `check_site.py` fail. Corrected the README to the current negative decision and removed only the stale HTML page; the TIPSTEP raster, ZIP, receipts, and research remain preserved under `artifacts/tipstep/`, `run_card_tipstep.json`, and `evidence/`.

## H33 and the leaderboard: evidence boundary

The reported H33 `0.2778` is not tied to an organizer submission receipt in this repository; treat it as an **UNVERIFIED HISTORICAL REPORT**, not an official score. Byte lineage in `evidence/review_e4a4422d/h33_remeasurement.json` shows the 37,654-pixel map is a subset of a 44,090-pixel base with 6,436 pixels removed by the two-pixel catalogue-distance rule. This can reduce redundant false-positive cost under the organizer's distance-weighted Tversky metric, but the hidden truth determines how much useful coverage was also removed. Pixel lineage is not proof of why a leaderboard score occurred.

The archived public leaderboard observation of 0.4413 is a **PUBLIC-LEADERBOARD OBSERVATION**, not this project's result or an H33 receipt. No score projection is made. The relevant exact algebra and limitations are in [`knowledge/h33_review_e4a4422d.md`](../knowledge/h33_review_e4a4422d.md).

## Pass 2 — identify and correct review defects

- Found that the homepage already stated the current `a201fa92` rejection, but the README's first screen and a stale TIPSTEP detail page contradicted that state. Updated the README lead to the current card-backed status and removed the orphan page, without changing any TIFF bytes or research receipts.
- The first independent check run caught the orphan page: `scripts/check_site.py` failed its exact page-inventory assertion. After the correction, it passed with 14 pages, 382 local links, all pages reachable, and the scientific tables/gates matching receipts.
- The shared writer still emits finite zeros outside the footprint, while the official-format validator requires null/NaN outside (R6). This mismatch is already tracked as IR-79-224. It was **not** patched here: the current lane authorization is absent and the new-lane preflight stops before scientific work. A writer change must be a prospective shared-tool migration, fully tested and version-pinned; it must not rewrite or relabel historical artifacts.
- The old upload's “Predicted values must be in range [0, 1]” cause remains unverified because the rejected bytes and submission receipt are not available. Do not state that NaN caused it or that current research artifacts were portal accepted.

## Pass 3 — final verification

- `scripts/verify_project.py`: **PASS**; all project/card/artifact integrity checks pass.
- `scripts/check_site.py`: **PASS** after correcting the orphan; 14 pages, 382 links, all reachable.
- Full test suite: **634 passed**.
- `scripts/data_status.py`: **13/13** current local inputs verified (runtime-only owner mirrors).
- `scripts/submission_status.py`: exit **2** as expected, machine decision **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO**; blockers include official-format failure, literal novelty, negative scientific verdict and missing selector approval.
- `scripts/validate_portal_spec.py data/reference/sample_submission.tif`: **PASS**; inherited THVC TIFF: **FAIL R6** only.
- `scripts/preflight_new_lane.py --restore`: exit **2** as expected; no lane, feature, holdout or output created.

## Ranked candidate hypotheses (proposals only; no experiment authorization)

The existing [`research/hypotheses_a201fa92.md`](../research/hypotheses_a201fa92.md) contains five ranked ideas. Their rankings are qualitative, not predicted scores:

1. **Relief-screened saddle × gravity crossing** — bands 12 `det_elev`, 19 `det_elev_slope`, 13 `iso_grav_anom`, and 18 `iso_grav_anom_hg`; multi-scale Hessian saddle persistence crossed by a gravity gradient. It could flag low-relief transfer structure missed by scarp-led maps. Distinct from single-channel edges, existing junctions, and visible-tip relays. Mimics: drainage divides, resistant lithology, inherited passes. Inputs are locally mirrored; detrended elevation is not an absolute DEM and cannot establish flow direction. Lowest implementation cost of the shortlist.
2. **Conjugate-strike accommodation** — visible-only fault orientations plus bands 7, 8, 4, 13, and 2; test a spatial change in strain direction co-located with an independent potential-field crossing. Could identify short R/R′ connectors omitted from major-trace compilations, unlike existing scalar strain magnitude or tip cones. Mimics: pluton/caldera margins and geodetic smoothing. Not data-ready: current bands are scalar summaries, not the tensor components needed to recover principal-direction rotation.
3. **Fan-apex multi-catchment knickpoint alignment** — absolute USGS 3DEP DEM, catchment area, channel curvature and aligned breaks across separate drainage networks. Independent catchment evidence could detect weak piedmont strands beyond current scarp products. Mimics: incision, lithologic contacts and stream capture. Specific 1-m tiles/coverage/license are not locally acquired or verified; official source starting point: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program).
4. **Paired well–spring thermal/chemistry disequilibrium** — INGENIOUS well/spring temperatures, geothermometry and verified hydraulic-gradient attributes paired with gravity structure. This differs from proximity kernels by testing a transport pattern. Mimics: lateral groundwater outflow, mixed waters and sampling/depth bias. The official [DOE GDR 1391 listing](https://gdr.openei.org/submissions/1391) is a metadata lead, not verification that required schema/measurements are present in the local table.
5. **Quality-stratified well heat-flow residuals** — USGS point residuals against conductive background, with borehole quality/depth and independent structural edges. Could expose advection around buried permeability pathways. Mimics: ordinary groundwater flow and borehole corrections. [USGS ScienceBase DOI 10.5066/P9BZPVUC](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28) lists a product; its binary, schema, coverage and license have not been acquired/validated here.

The top idea cannot be validated now: the literal pre-placement registry theorem rejects every nonempty surface, before canaries or holdout. No submission slot was touched. If a protocol owner prospectively resolves the comparator and assigns a lane, validate the top candidate with the shared cached stack/evaluator/writer, per-feature leakage canaries, whole-component buffered hide-and-recover, visible-only catalogue derivations and exact visible-pixel masking; require a same-seed paired 95% CI against the current incumbent before a separate selector considers any slot.

## Next work and limitations

1. Resolve the novelty comparator prospectively in shared governance; do not apply a local exemption or modify the witness/threshold to rescue a stopped candidate.
2. Once authorized, preregister one method paragraph and stay within its three-experiment/two-hour budget.
3. Migrate the shared writer and validators to official NaN-exterior semantics without permitting any non-finite in-footprint value; update pins, tests, site wording, and selector checks. Do not rewrite archived results.
4. Acquire organizer-authenticated data/receipts if needed. Owner mirrors are not organizer authentication; signed-in account capacity and a submission-page acceptance receipt are not accessible here.
5. Preserve independent spatial validation. Catalogue hide-and-recover can reward recovery of already mapped structure and may not generalize to expert-added uncatalogued faults or geothermal production.

Primary official references: [DrivenData problem, metric and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), and [USGS heat-flow product metadata](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28). Links establish source records, not unseen measurements or organizer-confirmed scores.
