# Three-pass repository review — Arena session `414b11bf` (2026-10-22)

## Decision

**Fail closed before experiment. No candidate surface, holdout, placement, or new TIFF was created in this review; no submission slot was selected or used.** The user message did not include the referenced assigned method paragraph, and the fresh mandatory preflight independently stops every nonempty candidate under the unchanged literal novelty rule. No hypothesis was invented as an assigned lane and no exception was made for the witness.

**New artifact from this review:** none — there is no new file to download. **OK TO SUBMIT: NO.** Existing research files remain separate: the canonical G79-THVC card says **OK TO DOWNLOAD: YES; OK TO SUBMIT: NO**, and the previously committed `ventprox` TIFF is not work from this review and has no novelty or holdout clearance. Its separate official-format audit also fails R6 (zero fill outside bounds instead of null/NaN).

The active branch remained `arena/414b11bf-gemsdoe79`. This checkout began at `268c864`; after discovering that `origin/main` had advanced to `128aea4` (PR #130), I fast-forwarded that main history into this assigned branch without switching branches. The separate main-branch artifacts remain attributed to their own history.

## Pass 1 — instructions, runtime inputs, cache and preflight

- Read the preserved full prompt in `README.md`, `AGENTS.md`, canonical `run_card.json`, required preregistrations, source records, irregularities, and the earlier session reports. The request's “single method paragraph below” was absent. Existing preregistrations are historical records, not an assignment for this review.
- `.venv/bin/python scripts/data_status.py` reported **RUNTIME-LOCAL-AVAILABILITY** `all_manifest_inputs_verified`: all 13/13 manifest inputs were present under ignored `data/raw` and their pinned hashes matched at `2026-10-22T20:06:12.510691Z`. This proves local byte availability only; it does not authenticate organizer origin, license, or scientific meaning. The restored input files are not being added to Git.
- The feature-cache receipt `evidence/feature_cache.json` lists ten expected arrays, but none is present in `.cache`. At this check `.cache` contained only `.cache/input_restore.json` and the restored novelty-witness raster. I did **not** run `prepare_data.py`; a historical cache receipt is not a usable cache.
- Inspected `data/raw/training_features.tif` directly with Rasterio: it has 19 described bands, including `cond_surf` and `depth_to_base_surf`. It does **not** contain the backlog's claimed `cond_2km`–`cond_15km` layers. The separate official USGS conductance product is depth-integrated, with intervals beginning at 2–12 km and extending to 200 km; it is not the shallow resistivity stack claimed in the old backlog. That candidate cannot be evaluated as written.
- Fresh command: `.venv/bin/python scripts/preflight_new_lane.py --restore --report evidence/preflight_414b11bf.json`. **Exit 2**, `state=impossible_under_literal_gate`, `start_new_lane=false`; the pinned witness SHA-256 is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, and its positive support covers 1.0 of the allowed cells. The literal lower bound for any nonempty candidate's forward 3-px overlap is therefore `1.0 > 0.70`.
- No candidate surface was built, so no candidate-specific Spearman correlation or pre-placement overlap was measured. No final dots existed, so no final-dot overlap was measured. No leakage canary, holdout, or experiment was run; these are **NOT RUN**, not zero. No selector was called and no slot was used.

**Pass 1 result: PASS — the data-availability correction was recorded, the cache was not falsely claimed, and the novelty stop was preserved.**

## Pass 2 — H33, leaderboard evidence, backlog audit and ranked hypotheses

### H33 and score evidence

H33's reported `0.2778` remains an **UNVERIFIED HISTORICAL REPORT**: no submission-page receipt links that number to the H33 raster bytes. The GEMSDOE32 owner page labels H33 **UNSCORED** and separately labels `0.2747` as a projection; neither value is an organizer receipt. Byte forensics show H33 is a 37,654-pixel subset of D2.8's 44,090 pixels, with 6,436 removed by the near-catalogue thinning rule. That establishes pixel lineage, not hidden truth or causality.

The metric makes a plausible mechanism possible: redundant predictions can add false-positive cost without increasing max-covered true-positive credit, so thinning might help; deleting a useful detection can also hurt. Without the organizer's hidden labels and a receipt, it is not possible to infer which happened or attribute `0.2778` to the thinning.

The official public leaderboard page read on 2026-10-22 showed **0.4413 at rank 1**. This is a **PUBLIC-LEADERBOARD-OBSERVATION**, not a score for this repository's artifact, an organizer submission-page receipt, or a performance ceiling. `0.3195` remains an older user-reported number. No score projection is made.

For offline context only, the earlier frozen shared-evaluator results are:

| Lane | Evaluator | Seed 20 (11,321 withheld positives) | Seed 30 (11,342 withheld positives) |
|---|---|---|---|
| G79-THVC | `HOLDOUT-DTI`, `gems57-pooled-hide-v2` | `0.1905` [95% CI `0.1741, 0.2069`] | `0.1944` [95% CI `0.1774, 0.2126`] |
| G79-CSKD | `HOLDOUT-DTI`, `gems57-pooled-hide-v2` | `0.178129` [95% CI `0.161835, 0.194433`] | `0.214488` [95% CI `0.196592, 0.232188`] |

These are inherited spatial-holdout measurements, not organizer scores and not runs from this review. They use the shared pooled DTI with α=0.2, β=0.8, and a 300 m triangular kernel. Future candidate comparisons must check the strongest same-evaluator result for each seed, not compare a holdout value to a public leaderboard value. G79-CSKD remains a negative historical lane; its seed-30 value does not authorize a submission.

### Correction to the older “Five Untried” backlog

`research/hypotheses_4ddab9a1_untried.md` is a historical proposal file, not a current list of five untried methods. Its broad families overlap with later code/lanes, and one item assumes bands not present in the local raster:

| Old item | Current audit correction |
|---|---|
| H79-U1, magnetic tilt-depth worms | **Not a distinct untried family.** It materially overlaps the later G79-DFSD de-striped subsurface/tilt-depth work, G79-MDSC multialtitude magnetic depth screening, and the H80 drape pilot. Do not re-rank it as new without specifying and auditing a genuinely different operator. |
| H79-U2, fan-apex / multi-drainage knickpoints | **Not untried as a broad family.** G79-DFSD contains `dfsd_fan_knickpoint_bajada` and derived `chi_step`/`chi_ksn` channels. The precise Hough-collinearity variant was not established as an independent completed arm, but it is too overlapping to advertise as a clean new hypothesis. |
| H79-U3, MT depth-band edge × heat-flow residual | **Invalid as written and not data-ready.** The 19-band local training stack lacks `cond_2km`–`cond_15km`; the cited USGS conductance layers are depth-integrated at 2–200 km. Related conductance/gravity and heat-flow ideas also appear in later project/sibling lanes. |
| H79-U4, conjugate accommodation / Riedel transfer zones | **Not a fresh family.** Relay, conjugate, strain-relay, and Coulomb variants were already implemented or tested (including archived/quarantined negative lanes); the broad idea needs a materially different scoped test before it can be reconsidered. |
| H79-U5, shoreline/isohypse veto | **Already tried.** Lahontan shoreline/isohypse features are present in G79-CSKD, G79-DFSD, G79-DILSTEP and G79-STEPCO. |

The correction is also recorded in `reports/irregularities.md` (IR-79-220) and at the top of the historical backlog. Its old numeric gain ranges are speculative text, not measurements, and are not endorsed here.

### Four narrowly scoped future hypotheses

The table below consolidates the current source-checked backlog in `research/hypotheses_a92a0164.md`. Ranks are **qualitative investigation priority** by information gain, fault specificity, data readiness, and cost—not predicted DTI or leaderboard score. These exact signatures have no completed candidate-specific holdout found in this checkout; that is not a claim of global scientific novelty. All remain blocked from execution by the current preflight.

| Rank | Hypothesis, inputs and target signature | Why it could help; difference from tried work | Named non-fault mimic and falsifier | Expected priority / cost and source check |
|---:|---|---|---|---|
| 1 | **Event-level ComCat lineation + focal-plane coherence.** Event time, location, depth, magnitude and available focal-mechanism strike/dip/rake from USGS ComCat, combined with existing earthquake-density bands and independent RTP/gravity edges. Score repeatable, elongated clusters whose focal planes agree, rather than smoothed event density alone. | A buried active strand can host repeated subsurface events without a mapped Quaternary surface trace. THVC uses static density bands; no local event-time/focal-plane holdout implementation was found. **Family-overlap caution:** the shared registry contains a GEMSDOE75 raster named `H75-1 ... ComCat3D`; therefore ComCat is not globally untried. The proposed focal-plane/temporal signature is only an untested narrow variant here, and must face the full pre-placement registry gate. | **Mimics:** quarry blasts, induced geothermal seismicity, and aftershock clouds. Falsify with event-sequence/spatial-cluster holdouts, sequence declustering, mechanism-consistency tests, and density-only/geophysics-only controls. | **Medium priority / medium cost.** Official [USGS ComCat FDSN API](https://earthquake.usgs.gov/fdsnws/event/1/) documentation was retrieved. A prior same-day source audit recorded 5,886 M≥2.5 events and 2,249 focal-mechanism-product events for a sample-footprint/2000–2025 count query. These are remote availability counts only: no full catalogue or focal mechanisms were ingested or parsed locally. |
| 2 | **Gravity-supported magnetic decoupling.** Local training bands RTP (2), isostatic gravity anomaly (13), gravity horizontal gradient (18), and—if frozen in advance—magnetic horizontal gradient (3). Test whether a persistent density/contact ridge continues where a regularized magnetic edge weakens or breaks; do not treat every magnetic low as alteration. | A damaged/altered corridor could mute magnetic contrast while a density boundary remains. Existing CJX/CJX-DIR and related lanes emphasize coincident edges or junctions; this is a narrow discordant-signature test, not a new claim for gravity or magnetics broadly. | **Mimics:** nonmagnetic carbonate/quartzite contacts, basin-fill boundaries, and acquisition/processing seams. Falsify with gravity-only and magnetics-only controls, fixed scale regularization, and seam/lithology diagnostics. | **Low-to-medium priority / low incremental compute** if the verified local stack can be used; the ten-array feature cache is absent, so cached features cannot be assumed. No external binary is required. USGS Amargosa and magnetic-susceptibility reports are regional analogies, not target-area validation. |
| 3 | **Paired signed conductive heat-flow residuals.** USGS Great Basin heat-flow well residuals with uncertainty, depth, quality and well identity; fit/retain the source's conductive background, then test spatially paired positive/negative residual departures against independently derived gravity/magnetic corridors. | Advective upflow/recharge can create signed thermal departures near a concealed permeable structure. This is different from isotropic kernels around known probes/springs, but generic heat-flow features were used in prior sibling work; the proposed signed-pair operator is the narrow untested part. | **Mimics:** ordinary groundwater circulation, pumping, shallow well corrections, and clustered sampling. Falsify with quality/depth filters, leave-well-cluster-out validation, conductive-only and random-pair controls. | **Medium potential specificity / high cost and low data readiness.** Official [USGS ScienceBase record](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28) lists a public 130,154,244-byte ZIP and an advertised MD5; no archive was downloaded, hashed, schema-checked, or coverage-checked. The listing proves discoverability, not a viable local dataset yet. |
| 4 | **Sentinel-1 SLC interseismic deformation discontinuity.** Matched ascending/descending IW SLC scenes; derive phase/coherence and a repeated line-of-sight displacement discontinuity across independent interferograms. Do not use a single-scene amplitude edge. | Persistent creep or hydrothermal deformation could reveal an active blind strand without a mapped surface trace. No SLC bytes, interferogram, or time series exists in the local completed-lane record. InSAR cannot find dormant faults that do not deform during observations. | **Mimics:** groundwater-pumping subsidence, seasonal soil moisture, landslides and atmospheric delay. Falsify with repeat-pair persistence, ascending/descending consistency, stable-terrain controls, and seasonal/broad-signal nulls. | **Medium only for active faults / very high compute and data cost.** The official [Copernicus Sentinel-1 SLC catalogue](https://stac.dataspace.copernicus.eu/v1/collections/sentinel-1-slc) returned five metadata items in a prior sample-bbox/date query; some target-area intersection was observed, not full-footprint time-series coverage. Terms state free/open access, but download requires a registered account; no data asset was acquired. Not viable until coverage and pair suitability are established. |

No numeric DTI uplift is forecast. Only if the protocol owner resolves the literal novelty definition and a specific method is authorized should a future session pre-register one row, reacquire any required data, verify schema/coverage/license, and test the surface before placing dots. Then run each feature-alone leakage canary (AUC >0.90 blocks trust), hide whole fault segments with a buffer, derive catalogue-based features from visible faults only, mask visible faults pixel-exactly, and use the shared `evaluate_holdout.py` / `submission_writer.py` with pooled DTI α=0.2, β=0.8, 300 m triangular kernel. Compare against the best same-seed holdout control, with a 95% CI. Stop immediately on duplicate/failed novelty. No slot choice is implied.

**Pass 2 result: PASS — score evidence classes are separated, the stale backlog is corrected, and four candidates are ranked without score projections or false novelty claims.**

## Pass 3 — existing artifacts, official format, site and repository checks

- Main already contains a separate `ventprox` research TIFF (`artifacts/ventprox/...`, SHA-256 `ff9fbdae78db06ba609d4402229f0e53a90af39333336be2ee1b60dfaa837455`). Its prior receipt says local format/range validation passed, but also explicitly says novelty was not cleared and holdout was not measured. It was not generated by this review and is not a submission candidate. I independently ran `scripts/validate_portal_spec.py` on that inherited file: **FAIL R6**, exit 2, because all 7,111,787 outside-template cells are finite zeros rather than null/NaN. The shared writer's zero-exterior convention conflicts with the official problem text; see IR-79-212. No file was changed.
- The canonical download remains the inherited G79-THVC artifact, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`; its run card still says **OK TO DOWNLOAD: YES; OK TO SUBMIT: NO**. Local format PASS, where present, is not official acceptance, uniqueness, or a selector receipt.
- Updated the README current-session summary, marked the stale U1–U5 backlog as historical, added a dated irregularities entry, and surfaced the current preflight/review in the evidence-driven site. The website's build-time runtime count is kept distinct from the review-time local `13/13` snapshot; a clean GitHub Actions checkout does not contain ignored `data/raw` files.
- No Python feature or candidate-generation code was added. No experiment JSON run card was fabricated: the required experiment card applies to experiments, and none was run. A separate machine-readable review record is `evidence/review_414b11bf.json`.
- Verification: site build **PASS** (13 pages); `scripts/check_site.py` **PASS** (13 pages, 345 local links, all pages reachable); `scripts/verify_project.py` **PASS**; pytest **597 passed**; browser QA **PASS** (12 Node tests and 39 rendered page/viewport cases, exact canonical download hash matched); and `submission_status.py` returned its expected exit **2** with **OK TO SUBMIT: NO**. `git diff --check` is recorded after the final edit. No competition account or remaining weekly-slot check was attempted.

**Pass 3 result: PASS — documentation distinguishes this session from inherited artifacts, preserves the official-format mismatch, and leaves every submission decision negative.**

## Limitations and next work

1. A method paragraph is still absent. Do not infer one from a previous proposal.
2. The literal novelty witness is a mathematical stop, not a low score: any nonempty candidate fails the unchanged `>70%` 3-px-overlap condition. The appropriate protocol owner must resolve the shared definition prospectively; do not bypass it locally.
3. All 13 input bytes are present and hash-verified in this workspace, but the expected feature arrays are absent. Do not claim a cache or regenerate it before an authorized, gate-eligible method.
4. Remote API counts and catalog listings do not equal local usable data. The ComCat bulk catalogue, heat-flow archive, and Sentinel-1 time series still need acquisition and schema/coverage/quality/licence review if those rows are ever authorized.
5. All future experiment outcomes require one JSON run card with the scoped hypothesis/mechanism/mimic, `HOLDOUT-DTI` evaluator/count/95% CI, novelty measurements, raster hash, validator output, ≤140-character submission note, and promote/negative verdict. No organizer score can be claimed without a submission-page receipt.
6. The experiment budget remains unused. Any later selection is separate from the science gate and from account-side weekly capacity.

## Review artifacts

- [Current README and preserved original prompt](../README.md)
- [Fresh preflight receipt](../evidence/preflight_414b11bf.json)
- [Machine-readable review summary](../evidence/review_414b11bf.json)
- [Current source/score review and remote-availability limits](../evidence/source_review_a92a0164.json)
- [Updated ranked shortlist](../research/hypotheses_a92a0164.md)
- [Corrected historical U1–U5 backlog](../research/hypotheses_4ddab9a1_untried.md)
- [Irregularities register](irregularities.md)
