# GEMSDOE79 — auditable fault-discovery research for the DOE GEMS challenge

**Latest repository audit (2026-10-22):** [three-pass review, session 91a8c516](reports/repository_review_2026-10-22_session-91a8c516.md). Independently checked 242 tests, 29 integrity gates and the pinned universal-overlap witness. Current outcome remains **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**; no new experiment or competition slot was used. [Prior active-branch audit](reports/repository_review_2026-10-22_active-branch.md) is retained as history.

Current session review: [b79882e0 — three passes and automated preflight hardening](reports/session_review_b79882e0.md). The pinned registry witness was freshly restored and remeasured; it still blocks any nonempty new candidate under the literal overlap rule. No new scientific experiment or submission slot was used. Malformed-manifest/restore failures now return structured preflight refusals instead of tracebacks.

## Download and submission decision — start here

Latest independent repository review and three-pass verification: [2026-10-22 session review](reports/repository_review_2026-10-22_session-68182759.md). It records the current automated decision, exact checks run, limitations, and next steps. The decision remains **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**.


> **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**
>
> This is a newly generated, format-valid research GeoTIFF. It failed the protocol's duplicate gate,
> so **do not upload it**. The decision is automatic: `scripts/submission_status.py`
> exits with code 2, and no human inspection is needed.

| | |
|---|---|
| File | [`docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif`](docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif) · ZIP [`docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.zip`](docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.zip) |
| Unique name | `gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT` |
| Note (122/140) | `H79-NHR research only; HOLDOUT-DTI 0.143/0.152 vs H33 0.096/0.099; DUPLICATE: 0.91 of dots within 3px of a registry raster` |
| SHA-256 | `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2` |
| Format | single band float32, EPSG:32611, 3730 × 3292, transform identical to the sample, values exactly 0/1, no NaN anywhere: **PASS** |
| Lane / experiment | H79-NHR / X1 (1 of 3 allowed; about 70 min of 2 h) |
| HOLDOUT-DTI, candidate (`gems57-pooled-hide-v2`, 4 spatial folds) | seed 20: **0.1431** [0.1281, 0.1574], n = 11,321 · seed 30: **0.1522** [0.1335, 0.1696], n = 11,342 |
| HOLDOUT-DTI, H33 fold-fair control | 0.0961 [0.0837, 0.1086] · 0.0989 [0.0842, 0.112] |
| Paired Δ vs H33 control | +0.047 [0.0321, 0.0621] · +0.0533 [0.0369, 0.0704] |
| Leakage canary | 464 single-feature AUC tests, max 0.8589 ≤ 0.90 (`geom_log_dist_visible_tip`): **PASS** |
| Duplicate gate | **FAIL.** 26 ordinary registry dot fields each contain > 70 % of the dots within 3 px. Worst: `GEMSDOE3:docs/downloads/coverage-v3-wide-20260925T054019Z-0ac095a7ed.tif` at 0.913, against 0.610 expected by chance. Rank correlation is clear: worst ρ 0.112. |
| Verdict | **negative**. The lane stopped as the protocol requires, with no retuning and no overlap capping. The separate selector refused (`evidence/nhr/selector_decision.json`). |
| Slots used | 0 |

### Archived concurrent artifact (2026-10-22, lane H79-FF, session 1de1617f)

Session `1de1617f` generated an additional negative research GeoTIFF (`H79-FF`); to preserve the single-canonical-artifact publication contract in `docs/downloads/` (`IR-79-52`, `IR-79-66`), its bytes are archived under [`archive/h79_ff_1de1617f/`](archive/h79_ff_1de1617f/README.md):

| | |
|---|---|
| File | [`archive/h79_ff_1de1617f/downloads/gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8.tif`](archive/h79_ff_1de1617f/downloads/gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8.tif) · ZIP [`archive/h79_ff_1de1617f/downloads/gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8.zip`](archive/h79_ff_1de1617f/downloads/gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8.zip) |
| Unique name | `gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8` |
| Note (113/140) | `H79-FF far-field lidar-scarp discovery, 2000-8000m off catalogue, 37654 dots, step_max surface; research artifact` |
| SHA-256 | `b4dd75e03cb2b4949cb4f0c079ca40077d2bfcb2651f4f3837dd5fbd035d2ba9` |
| Format | single band float32, EPSG:32611, 3730 × 3292, transform identical to the sample, values exactly 0/1, no NaN anywhere: **PASS** |
| Method | far-field lidar scarp: dots placed 2–8 km off the mapped catalogue, ranked by USGS 3DEP lidar step_max, 3 px Poisson spacing, fixed budget; off-catalogue, zeros elsewhere |
| Uniqueness gate | **FAIL.** > 70 % of dots within 3 px of registry priors: 13GEMSDOE spacing-5 lattice 0.9976, GEMSDOE48 space-filling surface 1.0000, 5GEMSDOE density probe 1.0000, GEMSDOE3 coverage field 0.8802 (limit 0.70). |
| Verdict | **negative.** Unique by construction (new bytes, not copied) but not unique under the protocol gate and not evaluated on `HOLDOUT-DTI`; **do not upload**. See [`evidence/ff/ff_run_card.json`](evidence/ff/ff_run_card.json). |
| Slots used | 0 |

Website: [https://buffedlizard55-lab.github.io/GEMSDOE79/](https://buffedlizard55-lab.github.io/GEMSDOE79/). It has the download at the top, an [executive summary and
submission guide](https://buffedlizard55-lab.github.io/GEMSDOE79/executive-summary.html) and the [analysis](https://buffedlizard55-lab.github.io/GEMSDOE79/analysis.html).
The canonical card is [`run_card.json`](run_card.json); every number above is copied from it.

Current independent three-pass review for this branch: [`reports/repository_review_2026-10-22_session-14aaf1c8.md`](reports/repository_review_2026-10-22_session-14aaf1c8.md). It records no new experiment, TIFF, upload, or slot use.

## Follow-up preflight (2026-10-22, branch `arena/a7d092d7-gemsdoe79`)

Concurrent [repository and hypotheses review](reports/repository_review_2026-10-22_session-6302cccd.md)
confirmed no additional scientific experiment or submission slot was used.

**Automated decision is still OK TO DOWNLOAD: YES / OK TO SUBMIT: NO.**
The canonical GeoTIFF above is independently generated and locally format-valid,
but it is *not* protocol-unique. No extra GeoTIFF was issued with a misleading
"ready" label, and no weekly submission slot was spent.

A re-download and independent measurement of the pinned [17GEMSDOE registry
witness](evidence/witness_review_20261022_a7d092d7.json) confirmed that all
5,106,385 allowed cells are covered by the witness's positive support. With the
literal dot definition (any finite positive value), **every nonempty candidate
has forward 3 px overlap 1.0 > 0.70**. The automated
[new-lane preflight](evidence/new_lane_preflight_a7d092d7.json) returns exit 2
and forbids experiments under that rule. This is a mathematical impossibility
for a new *submittable* TIFF under the current literal protocol, not a missing
human inspection step. A byte-distinct file or a format PASS is not a solution.
The current NHR file fails even the more informative ordinary-dot comparison
(26 non-space-filling registry rasters); waiving the universal witness alone
would not promote it.

Four untested [ranked hypotheses](research/hypotheses_preflight_a7d092d7.md)
are documented for a *future, separately preregistered* lane. None received a
holdout score in this review; no score is projected. The obstacle must be
resolved *prospectively* by an explicit protocol definition of what constitutes
"dots" in continuous prior rasters; silently changing the rule would violate
the user's stop instruction. The [executive summary](docs/executive-summary.html)
and [automated status command](scripts/submission_status.py) continue to make
submission safety explicit. This review also fixed a clean-install test failure
(missing pinned `scikit-image`) and corrected overconfident wording about
near-catalogue false positives and the 70% halo proof.

Latest concurrent software review: [session `0c9f6bad`](reports/session_review_0c9f6bad.md).
It independently hardened selector evidence and fixed clean-install dependencies; no scientific slot was used.

## Repository review — session `2747f26f` (2026-10-22)

[Three-pass review and next steps](reports/session_review_2747f26f.md): the fresh
hash-pinned registry preflight still refuses any new lane under the literal
positive-support overlap rule. No new scientific raster or competition slot was
used. The selector CLI now emits a structured refusal for missing/malformed
inputs rather than a traceback; ten regression cases protect that path.
All 249 software tests (measured on the merged tree), format/evidence verification and site link checks passed.
The original request for a newly generated **protocol-unique submittable** TIFF
remains blocked, not silently marked complete. Official GitHub reference material
was freshly reviewed; non-GitHub scientific sites were not freshly verified here.

## What the previous session found (2026-10-22, session `337ac1e9`)

## Session 2026-10-22 (lane H79-ASYM): answers, evidence and what is blocked

**Plain answer.** No file in this repo is protocol-unique. The downloadable GeoTIFF is still
`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` The new lane (H79-ASYM) stopped at its surface duplicate
gate before any placement, so it produced no file. Its run card is [`run_card_asym.json`](run_card_asym.json),
and its evidence is in [`evidence/asym/`](evidence/asym/).

| Question | Answer | Evidence (line-checked) |
|---|---|---|
| Why did H33 (user-reported 0.2778) score highest in the GEMSDOE family? | Sparse dots and mapped-pixel masking. H33 is exactly the D2.8 dot set (44,090) minus 6,436 dots within 200 m of mapped faults, which were pure false positives. Its dots are sparse (37,654). TP is a per-truth max and FP is a per-pixel sum, so sparse dots win. | [`evidence/h33_forensics.json`](evidence/h33_forensics.json) (`h33_equals_d28_pruned_distance_le_2px: true`); [official metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| How much truth credit does a score need? | Exact bound from the official DTI: c ≥ 0.8s/(1−0.2s), where c is the share of truth credit. 0.2778 needs c ≥ 23.5 %. The public leader 0.4413 needs c ≥ 38.7 %. (Corrected from 23.6 % and 38.4 %, IR-79-76.) | [`reports/nhr_analysis.md`](reports/nhr_analysis.md) §1; the bound follows because FN_w = N_truth − TP_w |
| Can we beat 0.2778 on our own proxy? | Yes, on the holdout. H79-NHR beat the H33 fold-fair control on both seeds (HOLDOUT-DTI 0.1431 and 0.1522, against 0.0961 and 0.0989). That result is a proxy, not a leaderboard score. | Canonical card [`run_card.json`](run_card.json) |
| Is that file submittable? | No. Its dots duplicate 26 earlier families (worst 0.913 against a chance level of 0.610). | Canonical card, `correlation_overlap_vs_registry` |
| Did the new lane (H79-ASYM) produce a unique file? | No. It stopped at the surface gate. A continuous registry surface (`GEMSDOE48`) covers all 5,167,373 footprint cells, so its top-k overlap is 1.0. Separately, 32 informative fields exceed 0.70 overlap and 14 still do after chance correction. | [`evidence/asym/uniqueness_surface.json`](evidence/asym/uniqueness_surface.json), [`evidence/asym/surface_diagnostic.json`](evidence/asym/surface_diagnostic.json) (reporting only) |
| Is the strain-rate channel an unexplored signal? | No. 16 registry rasters are strain- or geodesy-named (for example GEMSDOE37, GEMSDOE39, GEMSDOE51, GEMSDOE69, 5GEMSDOE). It is not a free route to a unique file. | Registry names in `registry/registry_index.json` |
| Does the 0.3195 figure match the official leaderboard? | No. The official board shows #1 0.4413 and #5 0.3539. No row shows 0.3195 (IR-79-77). | [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (fetched 2026-10-22) |

**What blocks a unique submission (needs a user decision, IR-79-53).** The literal rule flags any dot set
whenever a space-filling registry raster exists. There are 30 such rasters, and a seeded uniform random map is flagged by
all 30. Even with those removed, the lidar-scarp channel is saturated: 32 informative fields exceed 0.70, and 14 still
do after chance correction (several are scarp families, for example GEMSDOE50, GEMSDOE62 and GEMSDOE66). So the decision
on IR-79-53 alone would not clear H79-ASYM. A future lane needs a channel the registry has not used. The option table
below is for the user to choose from.

**Options for the user (not decided by an agent):**
1. Keep the literal rule. Then no file in this repo can pass, and the next lanes need new channels.
2. Apply chance-corrected overlap, (ov − halo)/(1 − halo), to space-filling rasters only. That is the option the NHR analysis proposed. It is documented, not adopted.
3. Ask the organizer whether a near-uniform surface is a valid "same" submission, and get a ruling.

**Verification of this session (each item was checked against bytes or a fetched page):**
- Environment restored from the hash-pinned mirrors: 13 inputs on disk, each SHA-256 checked during restore. The tracked receipt of record lists 7 (IR-79-66, `data/restore_receipt.json`). All 992 registry rasters are in `.cache/registry`, each SHA-256 checked.
- `pytest`: 249 passed on the merged tree (186 before merging `main`); dependency fix in IR-79-75.
- `scripts/verify_project.py`: all checks passed, with the canonical H79-NHR card unchanged.
- Lidar decoding follows the product's own quantisation rule, and `upface_max` and `downface_max` match their metadata descriptions (`data/raw/external/lidar_scarp_features.json`).
- The antislope mechanism is documented as ambiguous in the literature, and the named mimic is preregistered: [Saint Elias, GSA Bulletin](https://pubs.geoscienceworld.org/gsa/gsabulletin/article-abstract/122/9-10/1585/125613/Origin-of-sackung-uphill-facing-scarps-in-the?redirectedFrom=fulltext), [Pyrenees, Geomorphology](https://www.sciencedirect.com/science/article/abs/pii/S0169555X0500036X), [USGS SIM 3430 (antithetic uphill-facing scarp)](https://pubs.usgs.gov/sim/3430/sim3430_pamphlet.pdf).

**Limits and irregularities (all logged):** IR-79-53 (decision needed); IR-79-74 (H79-ASYM stop); IR-79-75 (missing dependency fixed); IR-79-76 (bound corrected); IR-79-77 (0.3195 not on the official board); IR-79-78 (6 of 992 rasters not comparable); IR-79-79 (organizer's NaN-outside-bounds wording versus this repo's zero-fill, which matches the user-reported H33 file).

**Next steps (ranked by expected value and cost, not yet run):**
1. Get the IR-79-53 decision from the user (option table above). Cost: none. Value: unblocks everything else.
2. Hypothesis 3 (Lahontan shoreline suppression) needs an absolute elevation source. Candidate: the USGS 3DEP DEM from The National Map (<https://www.usgs.gov/3d-elevation-program>). Not yet checked for obtainability from this sandbox (a GitHub Actions route is the documented option). Cost: medium. Value: removes the dominant false-positive population in the basin.
3. Hypothesis 5 (survey-seam-aware magnetic lineaments) needs the GeoDAWN flight-line shapefiles from the [USGS release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). They are not mirrored here. Obtainability not checked.
4. Ask the organizer for a receipt that binds H33's 0.2778 to a specific file. Without it, the H33 explanation stays a hypothesis.

## What this session found (2026-10-22, session `337ac1e9`)

1. **Why H33 scored highest.** The metric's TP is a max over a 300 m kernel, while its FP is a per-pixel sum.
   Sparse placements can reduce redundant FP: on an ideal straight grid-aligned trace, dots
   spaced three pixels apart average about 2.33 TP units per dot. This is an illustrative calculation,
   not a measured performance bound or proof that all sparse maps win.
   H33 is exactly the D2.8 dot set minus 6,436 dots within 200 m of mapped faults. Mapped pixels are
   masked; nearby dots can still credit hidden traces, so the pruning is not proved to remove only
   false positives. The reported 0.2600 and 0.2778 values have no artifact-bound organizer receipts or
   causal demonstration. Algebra shows 0.2778 needs at least 23.5 % of truth credit, and
   0.4413 (the public leader) needs at least 38.7 %. Full derivation: [`reports/nhr_analysis.md`](reports/nhr_analysis.md).
2. **Can we beat it?** Five untried hypotheses were ranked in
   [`research/hypotheses_nhr.md`](research/hypotheses_nhr.md); the top one, nested hide-and-recover
   learning, was preregistered in [`registry/preregistration_nhr.json`](registry/preregistration_nhr.json)
   and run once. It **beat the H33 control on the holdout** on both seeds, with paired CIs above zero and no
   leakage. However, its dots fall in the 300 m–2 km band around mapped faults, which 26 earlier family
   dot fields already occupy. Those fields have unverified historical scores of 0.016–0.143. Under the protocol, that is a
   **duplicate lane → stop**.
3. **Systemic blocker (IR-79-53).** A verified literal-support witness covers every allowed cell,
   so every nonempty map has overlap 1.0 and fails. Separately, 30 registry halos cover more than
   70% of the area and flag the seeded uniform control; that statistic alone is NOT a proof of
   universal rejection. The next lane needs **a prospective protocol clarification**.

## Concurrent lane G79-STEPCO (session `220dabc8`): also negative, archived

Another session ran lane G79-STEPCO (multi-field step dipoles with a fixed HistGradientBoosting model) in
parallel, and it merged to `main` first, as PR #26.

| Experiment | Seed 20 | Seed 30 | H33 control (seed 20 / 30) |
|---|---|---|---|
| S1 | 0.0946 [0.0778, 0.1110] | 0.0948 [0.0782, 0.1115] | 0.0961 / 0.0989 |
| S2-COVER | 0.0935 | 0.0961 | |

- S1 **tied** the H33 control rather than beating it. S2-COVER tied as well.
- STEPCO's own uniqueness reading also fired, because of the same space-filling registry rasters.
- Its verdict is also **OK TO SUBMIT: NO**.

When the two lanes were merged, H79-NHR became the canonical card because its holdout evidence is stronger.
The STEPCO files are kept as they are:
- S1 TIFF, ZIP and receipt: moved byte-for-byte to [`archive/g79_stepco_s1/`](archive/g79_stepco_s1/README.md).
- S2: [`archive/g79_stepco_s2/`](archive/g79_stepco_s2/).
- Card and evidence, unchanged: [`run_card_stepco.json`](run_card_stepco.json) and [`evidence/stepco/`](evidence/stepco/).
- Review: [`reports/session_review_220dabc8.md`](reports/session_review_220dabc8.md).
- Its protocol amendment: [`reports/protocol_amendment_D1_20261022.md`](reports/protocol_amendment_D1_20261022.md).

The STEPCO lane's README section is preserved in [`reports/readme_history_through_9417f4e.md`](reports/readme_history_through_9417f4e.md).
The merge is recorded as IR-79-56.

## Concurrent lane G79B-SDPT (session `67557396`): also negative, archived

Scarp dipole-persistence + trace-object detector
([hypotheses](research/hypotheses_g79b.md),
[preregistration](registry/preregistration_g79b.json),
[run card](run_card_g79b.json)), archived under
[`archive/g79b_sdpt_67557396/`](archive/g79b_sdpt_67557396/README.md) —
**not** the canonical download; **DO NOT SUBMIT**. Unconstrained HOLDOUT-DTI
0.1211/0.1114 beat its control (0.1143/0.1087) and the archived best on both
seeds (canary worst AUC 0.600), but duplicated 99 prior dot fields; the
preregistered uniqueness cap (52 discriminating priors at 0.68,
[Amendments B1](registry/preregistration_g79b_amendment_B1.json)/[B2](registry/preregistration_g79b_amendment_B2.json))
cost −0.0176/−0.0203, leaving the registry-unique artifact **below** its
control (0.1036/0.0910) — verdict negative, 0 slots used. Reproduce:
`PYTHONPATH=src:vendor:scripts .venv/bin/python scripts/submission_status_g79b.py`
(exit 2). Same wall as STEPCO/NHR: the family's good scarp terrain is
already dotted, so uniqueness after the fact costs more than detector gains.

## Limitations and next steps

- HOLDOUT-DTI withholds *catalogue* faults; the organizer scores *expert* faults absent from the
  catalogue. This file's dots sit closer to mapped faults than H33's: median 539 m against 1.96 km
  (`evidence/nhr/distance_to_catalogue.json`).
- Uniqueness covers the 992 hash-verified public sibling-repository rasters (0 new on a rescan of
  branches, tags and pull refs), not every file other participants have uploaded.
- The v3 dot definition for continuous registry surfaces is a recorded interpretation (IR-79-47) and can be reversed.
- Next steps:
  1. Decide IR-79-53.
  2. Run a far-field lane that ranks within H33-like distance bands (more than 1 km from mapped faults), with
     antislope or lidar evidence, checking the surface for uniqueness before placement.
  3. Reweight the nested target by distance band.
  4. Add the absolute 3DEP DEM for shoreline suppression.

## Verify the frozen result (safe default)

The active lane is **stopped**. These commands inspect existing bytes and evidence;
they do not retrain, place dots, regenerate the scientific card or use a slot.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/python scripts/restore_data.py --ids existing_faults,sample_submission --target-dir data/reference --preserve-receipt
.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/submission_status.py  # expected exit 2: DO NOT SUBMIT
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

Historical experiment entry points (`run_nhr.py`, `nhr_uniqueness.py`,
`build_nhr_submission.py`, `finalize_nhr.py`) document reproduction, **not permission
to resume this lane**. Do not rerun them in routine verification. A new authorized
lane must complete the surface novelty gate **before** any final dot placement,
then clear final novelty, leakage and matched holdout gates before the separate
selector can approve it. The selector now checks the existing evaluator/novelty
evidence against the card as well as the complete literal gate receipt. This is
an evidence-consistency check, not a fresh scientific evaluation.

Historical experimental commands remain in source for audit, but `run_nhr.py holdout`,
`run_nhr.py final`, and `build_nhr_submission.py` now refuse a terminal lane before
loading bulk data or changing evidence. Reproduction of frozen outputs is not permission
to restart a stopped scientific lane. Any future runner must separate surface generation,
completed uniqueness clearance, and placement; the archived runner's sequencing is not a template.

Concurrent completed software reviews: [0c9f6bad](reports/session_review_0c9f6bad.md)
and [0a460648](reports/session_review_0a460648.md) independently fixed dependencies,
hardened selector evidence checks and excluded local virtual environments from scans.
Those changes were merged into this branch without changing scientific evidence.

## Latest repository review — session `2203b2cc` (2026-10-22)

- Fixed a clean-install test/Pages blocker: `scikit-image` was imported by the merged
  G79B tests but absent from both dependency manifests. It and its dependencies are now pinned.
- Added terminal-lane guards and regression tests; no new experiment, copied submission,
  uniqueness exemption, slot selection or competition upload occurred.
- Removed the website metadata's unsupported “validated, unique” assertion and corrected
  the H33 explanation: a known-fault pixel mask does not make the surrounding collar pure FP.
- The existing TIFF remains downloadable and format-valid, **not protocol-unique**.
  No file meeting all submission gates was generated this session.
- Review and next-session blockers: [three-pass report](reports/session_review_2203b2cc.md).

## Maintenance review — session `e846fc02` (2026-10-22, no new experiment)

- **Decision unchanged:** `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` — the canonical research GeoTIFF (`abbf5314…`, 37,654 dots, single band float32 EPSG:32611, values exactly 0/1, no NaN anywhere) remains locally format-valid (`Predicted values must be in range [0,1]` PASS) but duplicate-blocked (26 informative dot fields >70%, worst 0.913 vs 0.610 chance; surface also fails; universal whole-footprint witness still covers 100% of allowed cells, `preflight_new_lane.py` exits 2). No retraining, no dot placement, no weekly slot was used.
- **Fixes:** collapsed duplicate `scikit-image` constraints in `requirements.txt` to `>=0.25,<1` (lock pins 0.26.0; `pip install -r requirements.lock` verified); rebuilt the static site with the new backlog included (`build_site.py` now embeds `research/hypotheses_e846fc02.md`); `verify_project.py` 29/29 PASS, `check_site.py` 7 pages / 120 links PASS, `pytest` 230 PASS, `submission_status.py` exit 2.
- **New research inputs for a future preregistered lane:** five newly ranked, not-yet-tested hypotheses (`research/hypotheses_e846fc02.md`) — tip-pair stepover linkage, drainage-deflection scarps, antislope polarity, persistent basement-edge worms, radiometric alteration lineament — each with layers, transform, why it targets *uncatalogued* faults, difference from repo, cost/mimic/viability; ranked so a future lane can pick one, preregister, and validate on the spatially blocked HOLDOUT-DTI before touching a slot. A separate geothermal-vent synthesis (`knowledge/geothermal_vent_discovery.md`) consolidates all official sources line-by-line for reuse.
- **No protocol exemption was added.** The universal literal witness and its implications (IR-79-53) still require an explicit prospective decision before any nonempty map can pass the 0.70 gate; the site's `research.html` now surfaces this with the new backlog.
- Three-pass review: [`reports/session_review_e846fc02.md`](reports/session_review_e846fc02.md).

## Latest review — session `52bfa965` (2026-10-22)

- Full review with three passes, a verification ledger and a no-experiment card:
  [`reports/session_review_52bfa965.md`](reports/session_review_52bfa965.md).
- Reproduced: `verify_project.py` exit 0; `submission_status.py` exit 2 (OK TO DOWNLOAD: YES, OK TO SUBMIT: NO);
  `preflight_new_lane.py --restore` exit 2; 230 tests pass; independent GeoTIFF re-read matches the card sha256.
- Checked against official sources (fetched 2026-10-22): the metric (α 0.2, β 0.8, R 300 m), the three-per-week
  limit, and the leaderboard (leader 0.4413; no 0.3195 row in ranks 1–50).
- **No experiment, no new candidate and no slot were used.** The blocker is a protocol decision (IR-79-53).
- Irregularities added: IR-79-69 (the official page's "null or nan" outside-bounds text conflicts with the
  team's all-finite policy and the sample's NaN; the public Format line now states this conflict), IR-79-70 (preflight
  exit 3 vs 2 depends on `--restore`), IR-79-71 (92 index scopes vs 71 repositories), IR-79-72 (leaderboard re-read).

Earlier README status sections (E1 G79-FABRIC-OFFSET, which stopped negative, and the concurrent-lane audits) are
preserved verbatim in [`reports/readme_history_through_8ed5d89a.md`](reports/readme_history_through_8ed5d89a.md).
Generative AI assisted research, code, tests and prose. No source measurements or organizer receipts
were synthesized. See [`knowledge/ai_disclosure.md`](knowledge/ai_disclosure.md).

---

## Original project prompt — read at the start of every session

The following is preserved as the project brief (only trailing whitespace is normalized). Historical scores, availability
assertions and pipeline claims inside it are **requests/reports**, not newly
verified facts. `AGENTS.md` requires reading this README and the latest run card
before making changes.

<details>
<summary>Full original user prompt (including repetitions and historical links)</summary>

Review the repo.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.  DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION.  BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION.  IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt.  Read the entire prompt.  A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.

PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this same prompt.

1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.

2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_[holdout.py](http://holdout.py) and submission_[writer.py](http://writer.py). Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.

3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.

4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.

5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.

6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

The following sites should serve as a starting point for understanding how to generate TIF submissions.  These websites are researched, and tested and have generated TIF submissions.  But we need to generate high scoring submissions.

Here are the results from submissions into the competition, separated by ....:

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score:

0.4413

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score:

0.4413

[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html)

gems-submission-20260925T001403Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/)

gems6_hgb88-topk03_33cec71ff0: 0.0286

....

[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html)

pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193

pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830

pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html)

gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560

....

[https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/)

gems-submission-20260926T163915Z-237f0063: 0.0343

....

[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html)

gems-submission-20260926T175114Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/)

lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461

....

[https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/)

Hedge-v2_submission: 0.1563

....

[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html)

2314b599: 0.0107

....

[https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html)

gems-structural-area06-v1: 0.0202

....

[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html)

r7-nms3-dem10-scarp_0c9199f14e62:0.1294

r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294

....

[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html)

gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782

....

[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html)

GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020

....

[https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/)

17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187

....

[https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/)

H19-C_20260930T212401Z_c11e495e: 0.0297

....

[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html)

h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894

h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922

....

[https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/)

h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461

h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921

H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280

h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839

....

[https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/)

20261001_r13-lattice-s5_v2_nan-outside:0.0904

....

[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html)

h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855

h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976

h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360

....

[https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/)

h19-4-reference-20260930-691e4dfa: 0.1894

....

[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html)

h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890

h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan: 0.1859

....

[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html)

h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002

h23-b-dti-optimal-emission-10pct-20261002-86176698-nan: 0.0748

....

[https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/)

h30-arrangement-matched-habitat-20261002-0d4e02e8-nan: 0.1352

....

[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)

h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477

....

[https://buffedlizard55-lab.github.io/GEMSDOE25/](https://buffedlizard55-lab.github.io/GEMSDOE25/)

dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE26/](https://buffedlizard55-lab.github.io/GEMSDOE26/)

dilcond-oof-v1-20261003-47629f496133-nan: 0.1223

....

[https://buffedlizard55-lab.github.io/GEMSDOE27/](https://buffedlizard55-lab.github.io/GEMSDOE27/)

topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan: 0.2449

....

[https://buffedlizard55-lab.github.io/GEMSDOE30/](https://buffedlizard55-lab.github.io/GEMSDOE30/)

d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE31/docs/](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)

h27-4-solo-d28-20261004-8acb75e1-nan:0.2708

....

[https://buffedlizard55-lab.github.io/GEMSDOE33/](https://buffedlizard55-lab.github.io/GEMSDOE33/)

h33d-analog-tip-stepover-r30-20261004-cb490425926e: 0.2632

....

[https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html)

h34-scatter-q50-arr-matched-20261004T223317Z: 0.0778

....

[https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html)

h35-06-aaa86efb25-20261004T225420098147Z-candidate: 0.0418

....

[https://buffedlizard55-lab.github.io/GEMSDOE36/docs/](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)

anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros: 0.2750

....

[https://buffedlizard55-lab.github.io/GEMSDOE37/](https://buffedlizard55-lab.github.io/GEMSDOE37/)

h6-physics-dotted-80k-20261005T055000Z-0bef9211631c: 0.1193

....

[https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html)

D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48-zero: 0.0763

....

[https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html)

xscale-worm-persistence-20261006T000541Z-nan: 0.0581

....

[https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html)

sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan: 0.0424

....

[https://buffedlizard55-lab.github.io/GEMSDOE45/](https://buffedlizard55-lab.github.io/GEMSDOE45/)

h51-km-faultzone-20261006-zeros: 0.0106

....

[https://buffedlizard55-lab.github.io/GEMSDOE49/](https://buffedlizard55-lab.github.io/GEMSDOE49/)

gate_ortho_w0.25-40k-20261006T213721Z-nan: 0.2376

....

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

....

[https://buffedlizard55-lab.github.io/GEMSDOE28/](https://buffedlizard55-lab.github.io/GEMSDOE28/)

h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan: 0.2708

h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan: 0.2649

h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan: 0.2710

h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan: 0.2707

....

[https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html)

efd28-repro-20261003-1cc7dc534d51-nan: 0.2600

repo-c0-habitat-emission-20261003-a4d439b07426-nan: 0.0041

sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan: 0.0512

wormrank-d28-20261003-59dcaf6dd11d-zeros:0.2560

wormsurv-filter-20261003-921f10960d6e-zeros: 0.0532

xfit-c0-habitat-20261003-ca879db0089a-zeros:0.0439

xfit-h41-union-qfaults-20261003-9edb34b99e3a-zeros: 0.0356

....

[https://buffedlizard55-lab.github.io/GEMSDOE46/](https://buffedlizard55-lab.github.io/GEMSDOE46/)

r11f-scarp-radiometric-fusion-00e049b51218-zeros:0.1589

r12-scarp-rad-concordance-23e807e2de9f-zeros: 0.0843

....

[https://buffedlizard55-lab.github.io/GEMSDOE39/](https://buffedlizard55-lab.github.io/GEMSDOE39/)

h40-e-disc-h40e-30k-zeros: 0.0339

....

[https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html)

h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1: 0.0355

h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1-hard: 0.0397

h45-eulerdepthreadcluster-20261006-f28e5cff6826-zeros: 0.0984

....

[https://buffedlizard55-lab.github.io/GEMSDOE41/](https://buffedlizard55-lab.github.io/GEMSDOE41/)

h42-submission-primary: 0.0245

....

[https://buffedlizard55-lab.github.io/GEMSDOE44/docs/](https://buffedlizard55-lab.github.io/GEMSDOE44/docs/)

h46-twostageAB_20261006T160000Z_b0cfe956-zeros: 0.0715

....

[https://buffedlizard55-lab.github.io/GEMSDOE47/](https://buffedlizard55-lab.github.io/GEMSDOE47/)

h60-lidarscarp-s2p0-20261007-nanoutside: 0.0430

....

[https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html)

h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8: 0.2296

....

[https://buffedlizard55-lab.github.io/GEMSDOE50/](https://buffedlizard55-lab.github.io/GEMSDOE50/)

h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite: 0.0764

....

[https://buffedlizard55-lab.github.io/GEMSDOE51/](https://buffedlizard55-lab.github.io/GEMSDOE51/)

h53-twostage-20261008T040951Z-9a0b32c871: 0.1047

....

[https://buffedlizard55-lab.github.io/GEMSDOE52/](https://buffedlizard55-lab.github.io/GEMSDOE52/)

h97b-candidate: 0.0856

....

[https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html)

h8-tiprelay-ridgeconcord-pr2-n80000-20261009-49bec522-zeros: 0.0159

....

[https://buffedlizard55-lab.github.io/GEMSDOE54/docs/](https://buffedlizard55-lab.github.io/GEMSDOE54/docs/)

h54c-manifest-edge-20261009T025732Z-73454bc5:0.0449

....

[https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html)

tensor_full-n16000-sep3-20261009T211747Z-nan: 0.0290

....

[https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html)

h56-final-dotted-ridge-d2p8-20261009T190421Z:0.0658

....

[https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html)

h57r-joint-strata-38000-20261010T214547Z-00cf5b2066f1-zeros: 0.0254

....

[https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html)

ml-binary-ridge-20261012T000000Z: 0.0180

....

[https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html)

h59j-coherence-consensus-dotted-20261011T043000Z: 0.0499

....

[https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html)

h73-chi-coherent-corridor-12000-20261011T195818Z-zeros: 0.0351

....

[https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html)

h61a-basement-step-20000dots-20261011T012029Z-eb2ae4bb024b-zeros: 0.0009

h61o-vardepth-none-40000dots-20261011T160711Z-28d4fac611ea-zeros-zeros:0.0751

....

[https://buffedlizard55-lab.github.io/62GEMSDOE/](https://buffedlizard55-lab.github.io/62GEMSDOE/)

datum-lahontan-strain-gauge-defensible-440dots-zeros: 0.0000

....

[https://buffedlizard55-lab.github.io/GEMSDOE63/](https://buffedlizard55-lab.github.io/GEMSDOE63/)

cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4-zeros: 0.2303

....

[https://buffedlizard55-lab.github.io/GEMSDOE64/](https://buffedlizard55-lab.github.io/GEMSDOE64/)

h64-lidar-scarp-cv-20261011T220000Z:0.0383

....

[https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html)

sar-em-propensity-half-20261011T223500Z-5e4660cd-zeros:0.0431

....

[https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html)

gems66-lidar03-cvretrain-reliefdecile-37654dots-20261020T190152Z-zeros:0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE67/](https://buffedlizard55-lab.github.io/GEMSDOE67/)

h67a-orientip-lane-29447dots-20261012T021226Z-allfinite:0.0356

ovtr-ml-cover-tau3p0-20261012-nan:0.1426

....

[https://buffedlizard55-lab.github.io/GEMSDOE68/](https://buffedlizard55-lab.github.io/GEMSDOE68/)

gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-nan:0.0437

gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-zeros: 0.0437

....

[https://buffedlizard55-lab.github.io/GEMSDOE69/](https://buffedlizard55-lab.github.io/GEMSDOE69/)

h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5:0.0053

....

[https://buffedlizard55-lab.github.io/GEMSDOE70/](https://buffedlizard55-lab.github.io/GEMSDOE70/)

gems70-p5-dual-submod300-oof38k-20261020:0.2478

....

[https://buffedlizard55-lab.github.io/GEMSDOE71/](https://buffedlizard55-lab.github.io/GEMSDOE71/)

gems71-hydro-conduit-38800-20261020T120000Z-zeros: 0.0558

....

[https://buffedlizard55-lab.github.io/GEMSDOE72/](https://buffedlizard55-lab.github.io/GEMSDOE72/)

gemsdoe72-h72-1-sgmc-offcatalogue-20261020T195456Z-6e6525e5-zeros: 0.0492

....

[https://buffedlizard55-lab.github.io/GEMSDOE73/](https://buffedlizard55-lab.github.io/GEMSDOE73/)

gems73-h73-mcsc-seamfree-blakely-37654dots-20261021T073716Z-b27ac445-zeros: 0.1917

....

[https://buffedlizard55-lab.github.io/GEMSDOE74/](https://buffedlizard55-lab.github.io/GEMSDOE74/)

gemsdoe74-triregime-radon-piedmont-37654-20261021T051000Z-zeros: 0.0669

....

[https://buffedlizard55-lab.github.io/GEMSDOE75/](https://buffedlizard55-lab.github.io/GEMSDOE75/)

gems75-trlt-radon-loco-ridge-20261021-zeros: 0.1627

....

[https://buffedlizard55-lab.github.io/GEMSDOE76/](https://buffedlizard55-lab.github.io/GEMSDOE76/)

gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros: 0.1555

gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE77/](https://buffedlizard55-lab.github.io/GEMSDOE77/)

gems85-h85-edti-collar35-skel-r33-20261021-d97b248e-zeros: 0.0964

....

[https://buffedlizard55-lab.github.io/GEMSDOE78/](https://buffedlizard55-lab.github.io/GEMSDOE78/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE79/](https://buffedlizard55-lab.github.io/GEMSDOE79/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE80/](https://buffedlizard55-lab.github.io/GEMSDOE80/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE81/](https://buffedlizard55-lab.github.io/GEMSDOE81/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE82/](https://buffedlizard55-lab.github.io/GEMSDOE82/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE83/](https://buffedlizard55-lab.github.io/GEMSDOE83/)

:

....

The following is the leaderboard for the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)

See below for more links and information related to the competition:

[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)

[https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)

[https://gbcge.org/current-projects/ingenious/](https://gbcge.org/current-projects/ingenious/)

[https://epsg.io/32611](https://epsg.io/32611)

[https://en.wikipedia.org/wiki/Tversky_index](https://en.wikipedia.org/wiki/Tversky_index)

We need to quickly look at the results and results from the GEMSDOE websites above.

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above.  We need to come up with distinct and unique strategies to score higher in this competition leaderboard.  We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents.  We should store all of our information and knowledge that we can gather from official verified sources.  This will serve as a starting point for other projects as well.  We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for.  So it's important to be contrarian but be smart about it.  We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents.  We need to do deep research and critical thinking and come up with new hypothesis to test.

0.3195	is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website.  It should be unique, take unique approaches to generating a submission that can score higher than 0.3195.

Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use.  It should solve the problem of having to manually check everything ourselves and having an up to date current feed.

Review the repo.

The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.

Our Core Values

Maximize P(Win)

“Maximize the Probability of Winning”: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). “Maximize P(Win)” frees us from constraints and clarifies that we must put Arena first.

Own the Outcome

We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.



Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

We need to focus on being able to generate a submission into the competition.

The site should be able to generate a TIF file that is required for submission.  It should be as easy as download to click a File to submit into the competition.  This needs to be in the executive summary or the very beginning of the site.  it should be obvious when you visit the site.

I tried to submit the document that i downloaded from the site but it returned this error on the submission form:

"Predicted values must be in range [0, 1]"

Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Here is the submission page when i click submit file

New submission

File to submitNo file chosen

You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF, with your predictions. It must match the submission format's CRS, shape, and geotransform. You may wish to review the competition rules first.

Note (optional)

A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Create a executive summary subpage that explains exactly how to make a submission into the contest.

Work on the next steps from the previous sessions first.

The goal of this project is to place top of the leaderboard in this competition.  The following is the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)

We need to create a project that can compete and place top of the leaderboard.  We need to understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification.

This is the guidelines we need to follow.[https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/)

Get familiar with the problem through the overview and problem description,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). You might also want to reference additional resources available on the about page,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/).

Download the data from the data,[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), tab.

Create and train your own model. This reference solution,[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) implements a simple approach.

Use your model to generate predictions that match the submission format.

Tell me what are you limitations and what you need access to during this project.  We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.

this pdf outlines how submissions must be entered into the competition.

[https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

You must be able to do your own research, deep research, scientific literature research and organize the knowledge so that we can critically think through the problem and generate a solution through scientific and free publicly available information.  this must be done autonomously and must be constantly reviewed and improved upon.  Provide suggestions and improvements and implement them.

❌ No DrivenData auth → cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (verified redirect to login)

See below for links from the above site.  See attached files for links from the above site.

[https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)

Download competition data from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (requires login) to data/

See links below for competition data:

[https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&amp;st=wz4kofki&amp;dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0)

[https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&amp;st=8junzdyw&amp;dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0)

[https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&amp;st=rnino7ya&amp;dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0)

[https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&amp;st=zj1lag1r&amp;dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0)

[https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&amp;st=srhhir10&amp;dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

Site creation

Create a github page for this repo that has clean ui, user friendly, simple and easy to use.  It should be organized and clean.

It should include all relevant information in an easy to read format with official verified links as sources for review.  Work line by line verify everything no hallucinations.

**The single remaining blocker to training is data placement**: run `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready to run (GPU needed for training; metric/losses/validation all verified working here on CPU).

you need to complete the above task by yourself.  Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

Run this task through multiple passes.

Pass 1: Implement the task completely and verify the result.

Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find.

Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.

Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request.  Work line by line verify everything no hallucinations.

Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.  It should be worked on in this next session or the next session.  Work line by line verify everything no hallucinations.

</details>

## Latest software-only review (session 566bec0c, 2026-10-22)

[Three-pass review and limitations](reports/session_review_566bec0c.md): pinned
witness reproduced; no new experiments or slots used. Preflight now rejects
malformed certificate types and hashes explicitly. **OK TO DOWNLOAD: YES. OK TO
SUBMIT: NO.** The literal novelty blocker remains unresolved; no new TIFF is
presented as protocol-unique.
