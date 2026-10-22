# Repository Review — Active Arena Session `fca42104` (2026-10-22)

## Executive decision

The repository is internally healthy for its **offline artifact checks**, but this checkout cannot reproduce the training/inference pipeline: the ignored `data/raw/` feature stack is absent. The canonical G79-THVC artifact remains **OK TO DOWNLOAD: YES; OK TO SUBMIT: NO**. No new candidate, TIFF, score, selector approval, account-side slot, or organizer receipt was created or inferred in this review.

Do **not** spend a competition slot or generate another submission from this session. The frozen lane has already used its three-experiment budget, and the repository's literal novelty preflight is unsatisfiable for every nonempty candidate under its current rule. A protocol-owner decision is required before any new lane or interpretation of uniqueness can be authorized.

## Scope and evidence boundary

Reviewed the complete `README.md` including the preserved project prompt, `AGENTS.md`, canonical root `run_card.json` and its `docs/run-card.json` copy, the active and archived preregistrations named by `AGENTS.md`, the current protocol/preflight evidence, the H33 forensic report, the post-THVC hypothesis backlog, the pinned input manifest/restore receipt, submission and site validation scripts, and the test suite.

This is a local repository review. Official source pages were **not freshly fetched** in this pass. Links below are retained for independent review; facts about those sources are limited to the existing `knowledge/official_sources.json` source inventory. No statement in this report is an organizer score or a new geological result.

## Three review passes

### Pass 1 — state, provenance, and requested artifact

- Confirmed the branch is `arena/fca42104-gemsdoe79`; working tree was clean at review start. No branch switching occurred.
- The canonical research artifact is `docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`. Its adjacent ZIP is a single-TIFF package.
- `run_card.json` and `docs/run-card.json` are byte-identical. Both preserve `verdict: negative`, `ok_to_download: true`, and `ok_to_submit: false`.
- The local run card labels its experimental values as `HOLDOUT-DTI` (`gems57-pooled-hide-v2`), reports withheld-positive counts and confidence intervals, and distinguishes public leaderboard observations from organizer receipts. No organizer receipt is present for the candidate.
- The H33 forensic file establishes a **raster measurement**, not a score: H33 has 37,654 positive pixels and equals the D2.8 set after pruning the 6,436 pixels within 2 grid pixels of the catalogue. The reported H33 public score remains unverified as a filename-to-artifact pairing without an organizer submission-page receipt. The geometry offers a plausible mechanism under a DTI metric whose false-positive term accumulates predicted mass, but does not prove the causal source of the reported score.

### Pass 2 — tests, local validation, and defects

Pinned environment setup:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock
```

Results:

- `.venv/bin/python -m pytest -q`: **355 passed**.
- `PYTHONPATH=src:vendor:scripts .venv/bin/python scripts/verify_project.py`: **all 31 checks passed**; artifact hash and card decision agree.
- `PYTHONPATH=src:vendor:scripts .venv/bin/python scripts/check_site.py`: passed; 7 pages, 146 local links, all reachable, 2 compatibility redirects, no external assets, `submit: false`.
- `scripts/submission_status.py`: **expected fail-closed exit 2**, `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` Blockers include literal novelty not cleared, negative verdict, no selector receipt, and no explicit approval.
- `git diff --check`: passed; Python compile check passed.

**Important reproducibility issue:** `data/restore_receipt.json` lists 13 pinned files as `present`, but filesystem inspection found only `data/reference/existing_faults.tif`, `data/reference/sample_submission.tif`, and the receipt itself. There is no `data/raw/` directory or `training_features.tif` in this checkout. The manifest receipt is historical/pinned provenance; it does **not** prove that ignored large files currently exist. The offline verifier validates the receipt against the manifest, not file availability. Therefore the full feature-backed holdout/inference pipeline cannot be rerun here until the ignored input stack is restored. Do not claim this pass reproduced the model training or scientific holdout.

### Pass 3 — protocol, hypotheses, and user requirements

- The preflight witness `evidence/new_lane_preflight_a7d092d7.json` records a registry positive-support raster covering 100% of the allowed cells. Under the literal `>70% within 3 px` rule, every nonempty map has overlap 1.0 and fails. The preflight says `start_new_lane: false`, `state: impossible_under_literal_gate`, and exit 2. This does not authorize silently changing the dot definition or adopting a different uniqueness interpretation.
- The G79-THVC run card records the allowed budget as exhausted: 3 experiments. All requested protocol constraints—shared evaluator/writer, leakage canaries, pre/post novelty checks, no organizer-score inference, no slot selection—were respected in this review.
- The existing `research/hypotheses_post_thvc_backlog.md` is useful as a list of research questions, but it is **not an evidence-ready experiment plan**. Its precise projected DTI gains, runtime/RAM estimates, and several prevalence/coverage assertions are not accompanied there by evaluator receipts, runtime benchmarks, or a source-specific verification record. MT/ASTER/GPS inputs are not in the pinned 13-file manifest. Treat all of those quantities and availability claims as **unverified hypotheses**, not measured improvements or proven obtainable data. No external-source obtainability check was possible in this pass; non-GitHub egress is restricted in this environment.
- The README already contains the preserved original prompt and a prominent download/submission status. The current banner and status script agree. The file is explicitly named `DO-NOT-SUBMIT`; the review does not promote it.

## Candidate research shortlist — triage only, not a fresh lane

These concepts are copied from the existing post-THVC backlog and are **not asserted to be novel across all external repositories or empirically untried**. The ranking is a qualitative triage by potential distinctness and data risk; expected DTI improvement is **unknown for every candidate**. No submission-slot or experiment is recommended until the novelty protocol is resolved and a new lane is prospectively authorized.

| Triage rank | Candidate / layers | Physical signature and missed-fault rationale | Difference from existing G79-THVC formulation | Data / effort disposition |
|---:|---|---|---|---|
| 1 | `H80-DRAPE-DECONV`: GeoDAWN RTP magnetics plus terrain/drape or flight-line metadata and DEM relief | Remove acquisition-direction/height effects before looking for sub-alluvial basement-edge discontinuities that could continue beneath concealed piedmont cover, rather than treating every gridded magnetic edge as geological. | A measurement-process correction before edge extraction, rather than THVC's multi-physics learner and visible-fault crack-tip features. | GeoDAWN is an official USGS source ([data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and); DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)). The required flight-line/drape products are not in the checked-in manifest; availability and suitability are unverified. Do not call viable yet. |
| 2 | `H80-SLIP-DEFICIT`: DEM-derived relief, range-front geometry, and visible-only catalogue context | A persistent range-front relief signal across a trace gap could indicate displacement transfer to an unmapped piedmont strand, instead of simply extending a mapped fault tip. | Tests geomorphic displacement continuity rather than THVC's coupled geophysical/thermal features and elastic tip propagation. | Uses the competition DEM and visible-only catalogue in principle, but the necessary raw stack is absent from this checkout. It could be validated without new external data only after exact required bands/files are restored and prospectively approved. |
| 3 | `H80-MT-PHASE`: GDR-1391 magnetotelluric resistivity-depth structure plus gravity/basement depth | A depth-persistent electrical boundary under a conductive cap could indicate a concealed upflow conduit away from surface scarps. | Adds 3-D electrical-depth structure; THVC used GDR thermal/well/vent layers, not the proposed MT tensor/slices. | DOE GDR record: [submission 1391](https://gdr.openei.org/submissions/1391), DOI [10.15121/1881483](https://doi.org/10.15121/1881483). Specific MT files/slices, licensing, footprint, and downloadability were not checked and are absent from the pinned manifest. Blocked pending verification. |
| 4 | `H80-RADIO-KD`: GeoDAWN K/eTh/eU and a documented lithologic/alteration covariate | A cross-fitted potassium residual conditional on immobile thorium could isolate alteration response from primary lithology and identify a concealed hydrothermal structure. | Conditional lithology residualization, not THVC's multi-physics stack. | Existing GeoDAWN radiometric bands are in the data manifest, but the proposed ASTER alteration inputs are not. No source acquisition check was made. A reduced version using only pinned bands would be a different hypothesis and needs preregistration. |
| 5 | `H80-COULOMB-CFS`: visible-only fault geometry, focal mechanisms / regional strain, and elastic stress transfer | Coulomb stress lobes and shadows may identify relay structures while suppressing stress-relieved flanks; a non-fault mimic is stress-driven fracture or model-boundary effects. | Signed stress shadow calculation, not THVC's heuristic forward crack-tip lobes. | The specific geodetic/stress inputs and spatial coverage are not pinned or verified. The named sources and data retrieval path need to be specified before this is viable. |

For **all five** concepts, the proposal's expected DTI gains and compute costs remain unmeasured. No number in the source backlog should be interpreted as a score or projection. A valid future trial must be preregistered and must test each feature alone on the pinned spatially blocked holdout before trusting a combined result.

## Findings and next actions

1. **Blocking: uniqueness protocol.** Obtain a prospective protocol-owner ruling on how continuous/space-filling registry rasters are treated under the existing literal gate. Do not retune, cap, jitter, or locally exempt candidates. The shared preflight must pass before any lane begins.
2. **Blocking: missing raw data.** Restore exact pinned inputs from `registry/data_manifest.json` into ignored `data/raw/`; verify SHA-256 for each file and then separately verify file existence. The competition data page is organizer-hosted and login-protected ([DrivenData data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)); the repository's public mirrors are integrity-pinned mirrors, not organizer-authenticated originals.
3. **Research integrity:** revise the post-THVC backlog before relying on it: remove or explicitly quarantine unsupported projected gains, runtime/RAM estimates, and unreferenced prevalence claims; record source links and per-file availability evidence for external data. Do not present third-party-source ideas as viable unless obtainability has been checked.
4. **Submission discipline:** retain the current artifact as research-only. Any future upload decision requires the separate selector, a bound approval receipt, official account eligibility/capacity, and exact artifact linkage. Local format validation alone is not permission to submit.
5. **Official manual-review links:** [competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), and [DOE GDR-1391](https://gdr.openei.org/submissions/1391).

## Review conclusion

The checked-in **candidate TIFF** is structurally valid according to the local validator, but uniqueness and promotion gates fail; it is **not cleared to submit**. The full modelling pipeline is **not reproducible from the current checkout** because the raw stack is absent. The next best action is governance and data restoration—not another experiment, a fabricated leaderboard projection, or a new TIFF.
