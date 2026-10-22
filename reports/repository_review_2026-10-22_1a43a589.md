# Repository Review — Session `arena/1a43a589-gemsdoe79`

**Review date:** 2026-10-22 UTC  
**Branch/base:** `arena/1a43a589-gemsdoe79` / `80550533de8e12f9a631ed928d50bcfc7f95e319`  
**Decision:** **OK TO DOWNLOAD: YES · OK TO SUBMIT: NO**  
**Scope:** Three review passes, source/evidence audit, fail-closed preflight, card/verifier/site correction. **No experiment, holdout run, dot placement, new TIFF, weekly slot, or submission choice was made.**

## Executive disposition

The canonical downloadable artifact is unchanged: [`g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif), SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`. Its local file-format evidence and existing two-seed holdout evidence remain recorded, but the literal novelty gate is impossible under the current rule, the scientific verdict is negative for promotion, and the separate selector receipt/explicit approval are absent. No status was promoted or relaxed.

The new-lane preflight was run with the hash-verified registry witness restored. It returned `exit_code: 2`, state `impossible_under_literal_gate`, witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, and `covered_allowed_fraction: 1.0`. Under the literal positive-support definition, any nonempty candidate therefore has 3-pixel overlap `1.0 > 0.70`; the pipeline stopped before an experiment. The exact machine receipt is [`evidence/new_lane_preflight_1a43a589.json`](../evidence/new_lane_preflight_1a43a589.json). This is a registry-witness result, **not** a measurement of a candidate that was never generated.

## Review pass 1 — H33 score provenance and byte-forensic explanation

The repository's byte-level H33 audit establishes the raster relationship, not a score receipt:

- The H33 raster contains `37,654` positive pixels and is a strict subset of D2.8's `44,090` pixels. Exactly `6,436` D2.8 pixels at Euclidean distance `<= 2 px` (`200 m`) from the mapped catalogue are absent from H33; no H33 pixels lie outside D2.8.
- The same audit records no 8-neighbour positive adjacencies in H33, median catalogue distance `19.6469 px`, and `69.83%` of H33 dots farther than `1 km` from the catalogue.
- The official DTI structure makes sparse predictions and removing nearby redundant emissions a **plausible metric-efficiency mechanism**: weighted TP uses a local maximum while weighted FP sums prediction mass. Those raster facts do not prove that this pruning caused the reported score change, nor do they establish private-test precision or geological correctness.

**The `0.2778` value remains unverified for the H33 bytes.** The H33 site labels its file unscored and no organizer submission-page receipt binds `0.2778` to that filename and SHA-256. The full-board audit recorded a public entry with the same decimal, but a matching number does not identify the H33 artifact. The `0.3195` claim is stale/unmatched in the recorded leaderboard snapshot; the official public-leader observation recorded for 2026-10-22 is `0.4413` for `xiaofanhu`, not for H33 or this repository's TIFF. These are public observations and historical reports, not `ORGANIZER-CONFIRMED` scores. See [`knowledge/why_h33.md`](../knowledge/why_h33.md), [`evidence/h33_forensics.json`](../evidence/h33_forensics.json), and [`knowledge/official_sources.json`](../knowledge/official_sources.json).

### Seed-30 interval provenance discrepancy

The previous card had two different seed-30 intervals without identifying their bootstrap sources. The difference is now resolved as provenance, not as an established numerical error:

- `holdout_dti.per_seed.seed_30.candidate.ci95` is rounded from `evidence/g79_thvc_results.json#/seed30/official_evaluate_all/scores/EXP-79-3_thvc_charnes_cooper/ci95`: `[0.1773715346, 0.2125517694]`, displayed as `[0.1774, 0.2126]`. This is the pinned evaluator's paired physical spatial-cluster percentile bootstrap (`159` clusters, `1,000` draws).
- `secondary_holdout_dti.ci95` is `[0.17688, 0.211578]` from the separate `seed30.spatial_bootstrap_20km` result produced by `scripts/run_g79_thvc.py::_spatial_block_bootstrap` (`159` 20-km blocks, `1,000` draws).

Both intervals refer to the same `HOLDOUT-DTI` point `0.1943932569` and `11,342` withheld positives. The canonical card now labels both sources, and `scripts/verify_project.py` checks each interval and provenance independently. The full recorded holdout values remain labelled **HOLDOUT-DTI (`gems57-pooled-hide-v2`)**: seed 20, `n=11,321`, `0.1905`, 95% CI `[0.1741, 0.2069]`; seed 30, `n=11,342`, `0.1944`, 95% CI `[0.1774, 0.2126]`. They are catalogue hide-and-recover proxy results, not leaderboard scores.

## Review pass 2 — geological hypotheses and official-data audit

The previous backlog contained unsupported numeric gain ranges and described MT inputs as shallow resistivity/phase-tensor slices. Those assertions were removed or corrected. The revised [`research/hypotheses_post_thvc_backlog.md`](../research/hypotheses_post_thvc_backlog.md) ranks five **qualitative, unscored, unexecuted** hypotheses by target complementarity, data readiness, uncertainty, and cost:

| Rank | Hypothesis | Why it might reveal an uncatalogued fault / expected qualitative benefit | Main cost/readiness limitation |
|---:|---|---|---|
| 1 | **H80-RANGEFRONT-RELAY** | Terrain and drainage organization that persists beyond a visible trace end could indicate a concealed basinward relay or step-out; potentially adds a network-scale cue to local tip/scarp features. | Medium cost; requires the competition feature stack plus AOI-checked USGS 3DEP coverage. |
| 2 | **H80-DRAPE-DECONV** | A corrected cross-line magnetic edge could expose a buried source boundary with no mapped surface trace; benefit would be improved independent geophysical corroboration, not a fault label. | Medium cost; official GeoDAWN line products are listed, but required per-sample altitude fields are not confirmed. |
| 3 | **H80-RADIO-KD** | A line-like alteration residual may follow a concealed fault-controlled hydrothermal conduit missed by the catalogue; expected benefit is an orthogonal cue, subject to strong non-fault controls. | Low–medium cost; channel names/units and raster alignment require source-metadata and byte checks. |
| 4 | **H80-MT-CONDUCTANCE** | A broad conductance boundary under basin cover may supply context for concealed basin/basement structures; it is not expected to locate individual 100 m traces. | Low compute after acquisition; grid resolution/coverage and alignment are unverified. The earlier “H80-MT-PHASE” sketch is not supported by the published product. |
| 5 | **H80-COULOMB-CFS** | Visible-only stress concentrations/shadows may prioritize secondary relay candidates absent from the map; this is a directional physical prior with high parameter and leakage uncertainty. | High modeling and leakage risk; official catalogue-derived slip/dilation data are not a hidden-fault stress raster. |

For each proposal the revised backlog names the input layers, target signature, a non-fault mimic and guard, method differences from repository lanes, official data links, and data/computation prerequisites. It does not assign DTI gains or use projections as scores. This ranking is a research priority only; **the top candidate was not validated on holdout** because the preflight stopped before experiment by design.

Official listings reviewed for this pass:

- [DOE GDR 1391, INGENIOUS compilation](https://gdr.openei.org/submissions/1391) lists MT conductance, geodetic shear/dilation, heat-flow, fault, thermal, and other inputs. Its linked [USGS Electrical Conductance Maps release](https://doi.org/10.5066/P9TWT2LU) publishes depth-integrated products at `2–12`, `12–20`, `20–50`, `50–90`, and `90–200 km`; it does not substantiate the earlier 500 m/1.5 km/3 km phase-tensor proposal.
- The [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) lists magnetic/radiometric grids, flight-line CSVs, metadata/report, and flight-path products. Its description documents nominal survey layouts and warns that actual terrain clearance can vary; availability of every altitude field needed by H80-DRAPE-DECONV remains unconfirmed.
- The [USGS ASTER-derived hydrothermal-alteration map](https://doi.org/10.5066/F7CR5RK7) is a thematic alteration/mineral-group product, not raw ASTER reflectance or a fault inventory. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services) makes public elevation products available but requires an AOI coverage check. The [USGS slip/dilation tendency release](https://doi.org/10.5066/P9YL58W6) contains catalogue-derived fault geometry and stress data, so any holdout use must filter/recompute from visible segments only.

**Data readiness remains a blocker.** The official local receipt lists five files and no MT raster. The raw competition training feature stack is absent from this checkout and `.cache` was empty before the review. Public source listings are not proof that bytes have been obtained, that their grids align, or that a candidate is executable. No feature download or data restoration was attempted for a new lane.

## Review pass 3 — guardrails, verifier, site, and automated checks

- Installed the repository's pinned `requirements.lock` into the ignored `.venv` because the system Python had no NumPy. This changed no tracked files.
- Ran `scripts/preflight_new_lane.py --restore --report evidence/new_lane_preflight_1a43a589.json`; it verified the pinned witness and refused to start a lane with exit 2. No model, placement, or holdout command was run.
- Added bootstrap-source fields to `run_card.json`, made `thvc_evidence_checks()` compare both seed-30 intervals to their distinct result paths, and added regression assertions to `tests/test_current_run_integrity.py`.
- Corrected the scientific report's ZIP byte count, replaced unsupported gain estimates in the hypothesis backlog, refreshed the official-source ledger, corrected stale site wording, and added a current-review page to the generated site. The README no longer advertises a rerun command for the closed G79-THVC lane.
- Final project, test-suite, static-site, and headless-browser verification receipts are summarized in the section below.

## Limitations and next steps

1. The literal novelty gate remains fail-closed. Only the protocol owner can decide whether the operative gate changes; this review does not authorize a substitute definition.
2. No experiment, new candidate raster, submission name/note for a new file, holdout result for H80-RANGEFRONT-RELAY, or submission slot was produced. The review card records explicit `NOT_RUN` fields and a negative verdict: [`reports/session_run_card_1a43a589.json`](session_run_card_1a43a589.json).
3. Before any future lane, restore and hash-verify the shared feature stack, verify official data bytes/metadata and coverage, preregister exactly one hypothesis, run feature-alone leakage canaries, and follow hide-and-recover with whole fault segments buffered and visible-fault-only catalogue features. Apply the same pooled DTI (`alpha=0.2`, `beta=0.8`, 300 m triangular kernel) and shared evaluator/writer.
4. Run surface correlation and 3-pixel overlap before placement and repeat dot-overlap checks on final dots. Stop and log duplicates at the existing thresholds. Do not jitter, cap, exempt, or switch novelty definitions after observing results.
5. Respect the three-experiment/two-hour ceiling. Do not choose a submission or spend a weekly slot as part of this review. A unique GeoTIFF may be written only if every automated gate supports it; the current file remains **downloadable for research, not approved for submission**.

## Final verification receipts

- **Preflight:** `scripts/preflight_new_lane.py --restore --report evidence/new_lane_preflight_1a43a589.json` returned expected exit `2` (`impossible_under_literal_gate`; lane not started).
- **Project verifier:** `scripts/verify_project.py` passed **34/34 checks**, including both official CI provenance paths, the separate custom-bootstrap interval, frozen witness, TIFF/ZIP integrity, and fail-closed submission status.
- **Test suite:** `.venv/bin/python -m pytest -q` — **355 passed**.
- **Site build/link audit:** `scripts/build_site.py` built **8 pages**. `scripts/check_site.py` passed for **8 pages / 170 local links**, all pages reachable, **2** compatibility redirects, and **0** external assets.
- **Headless browser QA:** [`evidence/browser_review.json`](../evidence/browser_review.json) records **24/24** page/viewport cases (8 pages at 1440, 390, and 320 px), no horizontal overflow, no browser/HTTP errors, verified TIFF download SHA-256, clipboard copy, feed rendering, redirects, and history filtering. The QA is local static-site verification, not organizer acceptance or geological evaluation.
- **Submission status:** `scripts/submission_status.py` reports **OK TO DOWNLOAD: YES · OK TO SUBMIT: NO** and returns expected exit `2` because the scientific verdict, literal novelty gate, selector receipt, and explicit approval remain blocked/missing. No slot was used.
