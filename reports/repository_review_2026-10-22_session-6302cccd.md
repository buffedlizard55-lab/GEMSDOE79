# Repository review — Arena session `6302cccd`

**Scope:** repository/code/test/release-state review on the assigned branch. This is not a new scientific experiment, not a submission selection, and not an organizer result. The complete persistent project brief in `README.md`, `AGENTS.md`, current `run_card.json`, active NHR preregistration, archived E1 preregistration, and irregularity log were reviewed. Repository-wide automated consistency checks supplement (but do not prove) a formal line-by-line audit of every historical file.

## Decision and current artifact

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The sole current download in `docs/downloads/` is the binary H79-NHR research TIFF. It is locally format-valid, byte-distinct from the pinned registry files, but fails the prescribed uniqueness gate. It must not be uploaded. The lane's duplicate finding and stop (IR-79-55) are binding; this session did not rerun, tune, overlap-cap, select, or upload it. The existing negative decision remains machine-generated and does not require an inspector.

The canonical run card records these values as **HOLDOUT-DTI (`gems57-pooled-hide-v2`)**, not organizer scores:

- Seed 20: 0.1431, 95% CI [0.1281, 0.1574], 11,321 withheld positives.
- Seed 30: 0.1522, 95% CI [0.1335, 0.1696], 11,342 withheld positives.
- H33 fold-fair control: 0.0961 [0.0837, 0.1086] and 0.0989 [0.0842, 0.1120] on the same seeds; paired candidate-minus-control CIs are positive in both draws.
- These results do not establish performance on organizer labels, and do not establish that the reported GEMSDOE32 `0.2778` was organizer-confirmed. No submission-page receipt is present.

The uniqueness evidence is a hard negative: final-dot forward overlap within 3 px reaches 0.913 against an ordinary registry dot field (chance halo coverage 0.610); 26 ordinary fields exceed the 0.70 threshold. Maximum rank-correlation is 0.633 on the tested surface and 0.112 on final dots, both below 0.90. The surface pre-check also failed the overlap threshold. This session therefore makes no claim that the candidate is protocol-unique.

The card's format validator reports a single-band float32 EPSG:32611 raster, 3730 × 3292, exact sample transform, all finite, min 0 and max 1, no NaN in the footprint. These are **local format checks only**, not a DrivenData acceptance receipt.

## Pass 1 — inspect and restore reproducible testability

- Reviewed the active card, decision/status tools, preregistration and stop state, publication contract, registry pin records, site checker, tests, dependency manifests, current downloads, and existing candidate-hypothesis record.
- Ran the pinned-lock environment checks. `verify_project.py` and `check_site.py` passed. The full pytest collection initially failed because `tests/test_g79b.py` imports `skimage` through the retained `src/gems79b` implementation, but neither `requirements.txt` nor `requirements.lock` installed scikit-image.
- Fixed the concrete dependency omission: declared `scikit-image>=0.22,<0.27` and pinned `scikit-image==0.26.0` plus its required transitive packages in `requirements.lock`. No feature, result, run card, registry pin, or TIFF bytes were changed.

## Pass 2 — defect/edge-case review

- Re-ran the suite after the dependency correction and caught an unrelated test-fixture freshness issue: `verify_project()` refreshes the evidence copy, while the Pages copy had not yet been rebuilt. Ran the standard site builder to synchronize both copies; did not weaken the assertion.
- A temporary venv placed inside the scanned repository also caused the conflict-marker scanner to inspect package test data. Removed that temporary directory and ran the clean environment outside the repository; the project code was not changed for this temporary harness artifact.
- Re-ran all gates in that clean environment: **186 tests passed**; `verify_project.py` passed every recorded integrity/evidence/status check; `check_site.py` passed with **7 pages, 114 local links, all reachable, two compatibility redirects**.
- `submission_status.py` returned `ok_to_download=true`, `ok_to_submit=false`, `verdict=negative`; exit code **2 is the expected fail-closed result**. `git diff --check` passed. The output directory still contains exactly the canonical TIFF/ZIP pair plus its receipt; no competing upload artifact was added.
- The already-stopped H79-NHR lane cannot be used to run one of its exploratory alternatives: its preregistration reserves X2/X3 for a defect fix only, and IR-79-55 requires stop after a duplicate. A new scientific experiment would require a new, prospective lane registration and a resolution of the registry-overlap policy; neither is part of this review.

## Pass 3 — requirements and scientific-candidate re-check

The existing preregistered candidate study (`research/hypotheses_nhr.md`) contains four untested ideas (ranks 2–5) beyond the already-run nested hide-to-recover model. They remain **hypotheses only**, are not approved experiments under the stopped lane, and have no measured HOLDOUT-DTI:

| Priority for a future separately authorized lane | Layers and targeted signature | Why it could target faults absent from the map / distinction from this repo | Cost, data viability, and principal mimic |
|---|---|---|---|
| 1 | Lidar `upface_max`, `downface_max`, `coh100`, strike plus gravity horizontal gradient; ratio/coherence of opposing scarp-face asymmetry | Tests uphill-facing/antithetic scarp morphology, rather than NHR's individual scarp-channel inputs or the earlier general multiscale feature learner. | Low cost; existing lidar stack. Mimic: landslide headscarps or sackung. Qualitative gain only; novelty gate must be checked before placement. |
| 2 | Lidar step/face channels plus absolute elevation; suppress contour-parallel steps near Lahontan shoreline levels | A shoreline/facies prior can distinguish shorelines from fault scarps; this explicit absolute-altitude rule is absent from the current input stack. | Medium cost; requires absolute DEM, not the detrended elevation band. The recorded free official source is USGS 3DEP / The National Map: https://www.usgs.gov/3d-elevation-program . Availability for the full footprint has not been checked in this session. Mimic/risk: real faults parallel to shorelines could be suppressed. |
| 3 | Visible-catalogue tips/strike plus lidar scarp evidence; directional continuation cone beyond mapped fault tips | Targets unmapped along-strike continuations beyond truncated mapped endpoints. NHR has distance-to-tip geometry but no explicit directional cone search. | Low cost; existing inputs. Mimic: bedding-parallel ridges or drainage lineaments. This is close to NHR and needs strict novelty review. |
| 4 | RTP/TMI magnetic gradients plus airborne flight-line geometry; lineament response after modeling/removing survey azimuths | Could isolate buried basement structures from survey levelling lineaments; differs from a generic magnetic-edge detector. | Medium cost; official GeoDAWN source is recorded at https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and . Flight-line geometry has not been restored/availability-checked in this session, so this is not validated as immediately viable. Mimic: dykes and residual levelling seams. |

These are repackaged summaries of the checked-in hypotheses record, not new geological findings or score promises. The historical 3DEP source reference and GeoDAWN landing page are source leads, not evidence that the needed exact data are already obtainable here. Keep candidate ranking qualitative; do not infer a leaderboard score from the catalogue holdout.

## Irregularities, blockers, and next work

1. **Duplicate-gate blocker (IR-79-53 / IR-79-55):** space-filling registry priors can cause broad overlaps; NHR additionally overlaps above threshold with ordinary sparse-family dot fields. Do not silently exempt, cap, or redefine these after seeing results. A future run requires an authoritative protocol/registry definition and a new preregistration.
2. **Generalization risk (IR-79-51):** the holdout recovers withheld catalogue components, while the contest labels are expert faults absent from that catalogue. NHR's near-catalogue concentration may not transfer. Only an organizer-confirmed score can answer this.
3. **Input provenance:** input hashes match the repository's pins, but owner mirrors are not organizer authentication. Private DrivenData account state, weekly capacity and upload receipts are inaccessible to this automated local review.
4. **Candidate-data gaps:** absolute 3DEP elevation and GeoDAWN flight-line geometry are not validated as obtainable in this sandbox. Do not make them prerequisites for a new lane until endpoint/coverage and licensing are verified.
5. **Code scope:** the dependency fix makes the currently retained `gems79b` test path installable; it does not reactivate or endorse that archived scientific method.

Suggested next actions, in order: (a) resolve the uniqueness rule and registry representation policy without reference to candidate outcomes; (b) after authorization, preregister one new method that can pass a surface novelty screen before dot placement; (c) test each feature's single-feature leakage canary before trusting it; (d) require both seeds to beat the current matched HOLDOUT-DTI comparator with paired 95% CIs above zero; (e) only then invoke the separate selector and check the live submission cap. No competition slot should be spent before those gates pass.

## Official/source links already used by the project

- DrivenData competition overview and data access: https://www.drivendata.org/competitions/306/competition-doe-gems/
- DrivenData problem description: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- DrivenData about page: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- DOE/NREL GEMS technical report: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Official USGS GeoDAWN data landing page: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- USGS 3DEP landing page: https://www.usgs.gov/3d-elevation-program
- Reference implementation: https://github.com/drivendataorg/gems-prize-reference-solution

These links are recorded for review; this session's checks were local repository checks and do not imply that every external page or data endpoint was fetched live.
