# Independent repository review — session 43963905

**Review date:** 2026-10-22 UTC  
**Branch:** `arena/43963905-gemsdoe79`  
**Scope:** independent code/evidence/site recheck of the inherited GEMSDOE79 state. This review did not authorize or run a new geological experiment.

## Decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The sole download exposed by the site is the inherited G79-THVC research artifact. It is not a new candidate. The current literal novelty protocol makes every nonempty prediction surface fail: after restoring the pinned witness, its positive support covers 100% of the allowed footprint, so any allowed positive dot has 3-pixel forward overlap 1.0, above the 0.70 limit. The gate is a protocol-level impossibility, not evidence that any candidate would score well or poorly.

No new surface, feature, holdout score, final-dot placement, or TIFF was created. No competition slot was used. I did not manufacture a zero raster, rename a prior raster, or claim a projection as a score.

## Three review passes

### Pass 1 — Read and trace the project contract

- Read the complete `README.md` including its preserved original prompt, `AGENTS.md`, canonical `run_card.json`, the three required lane preregistrations, the irregularities report, the H33 review, and the four-hypothesis research backlog.
- Confirmed the current home page and run card declare `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`; the file name itself is marked `DO-NOT-SUBMIT`.
- Confirmed the requested original prompt is already preserved in the README and the standing project instructions require reading it at session start.
- Reviewed the recorded evidence limitations: H33's reported 0.2778 is not artifact-linked organizer confirmation; the public leaderboard's 0.4413 is a public observation, not a local result or attainable ceiling.

### Pass 2 — Re-run software, local artifact, and publication checks

Commands were executed from the repository root after installing the exact packages in `requirements.lock` into an ignored `.venv/`:

```text
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q
477 passed in 57.39s

.venv/bin/python scripts/verify_project.py
all_checks_passed: true

.venv/bin/python scripts/validate_submission.py docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif
format_passed: true; does_not_approve_submission: true

.venv/bin/python scripts/build_site.py
Built 7 pages; OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.

.venv/bin/python scripts/check_site.py
passed: true; 7 pages; 128 local links; all pages reachable; scientific tables and gates match receipts
```

The TIFF re-opened as one float32 band, EPSG:32611, shape 3730 × 3292, transform `[100, 0, 243350, 0, -100, 4508550]`, with no NaN or infinity and values in `[0,1]`. Its SHA-256 remains `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`. This proves the local format/range contract only; it does not establish organizer acceptance, scientific promotion, novelty, or permission to submit.

### Pass 3 — Challenge the stop condition and check for accidental changes

- `scripts/preflight_new_lane.py` without `--restore` returned an **unverified exit 3**, because the pinned registry blob is stored in the ignored local cache and was absent at first. This is fail-closed; it is not clearance.
- `scripts/preflight_new_lane.py --restore` then fetched and hash-verified the single pinned witness and returned the expected **exit 2**: `impossible_under_literal_gate`, witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, covered allowed fraction `1.0`, limit `0.70`.
- Rechecked the registry measurement and current card. No new experiment or placement was performed; the existing experiment budget is already exhausted at three.
- Rebuilt and rechecked the static site. `git diff --check` passed and the original artifact bytes remained unchanged.

The `--restore` detail matters: use the documented command for a reproducible stop check. An un-restored cache miss is “unverified,” never “unique.”

## Candidate research backlog (not tested in this review)

The repo already records four prospective mechanisms in [`research/hypotheses_e4a4422d.md`](../research/hypotheses_e4a4422d.md). Relative rank/cost below is a qualitative research queue, not an expected DTI estimate:

1. **G79-CJX — cross-scale gravity/magnetic contact-junction topology.** Cached RTP magnetic band 2 and isostatic gravity band 13; persistence of orientation winding/branch points plus compatible signed cross-contact contrasts. Could expose buried structural intersections without a mapped scarp. Pluton margins, caldera contacts, and survey seams mimic it. Moderate implementation cost; blocked by current novelty protocol.
2. **G79-BLC — bilateral lithology-contrast change point.** Gravity/magnetic plus cached radiometric ordinal derivatives; test along-contact changes in opposite-flank joint distributions. A transfer fault may juxtapose existing units under cover. Facies boundaries, lava contacts, and drainage redistribution mimic it. Moderate-to-high cost; not tested.
3. **G79-RSS — relief-screened structural saddle.** Detrended elevation/slope bands 12/19, with gravity bands 13/18 as independent corroboration. Catalogue-free terrain topology may reveal low-relief transfer zones. Stream capture, wind gaps, landslides, and resistant-bedrock saddles mimic it. Moderate cost; not tested.
4. **G79-HFR — paired heat-flow residuals.** Official USGS well-point heat-flow residuals with quality fields, DOI `10.5066/P9BZPVUC`. The official metadata describes potentially hydrothermal/groundwater-influenced residuals, but the release bytes, schema, coverage, and quality fields have not been acquired here. It is **not data-ready** and high-cost, so it is not a viable immediate validation candidate.

No rank in this list is permission to bypass the preflight. The first three depend on the pinned cache, but even a completed holdout would not cure a mathematically unavoidable registry collision under the present gate. A prospective protocol amendment/owner decision is prerequisite before any new lane can run.

## H33 and official-source interpretation

The H33 inspection in the repository measured geometry, not leaderboard performance: 44,090 prior dots became 37,654 after deleting 6,436 points within two pixels of the mapped catalogue. This supports a plausible precision-efficiency explanation under a metric that trades off weighted TP against summed weighted false positives, but it does **not** prove causation or authenticate the reported 0.2778. The sibling GEMSDOE32 page labels the artifact UNSCORED. Therefore there is no verified basis to say H33 was actually the highest-scoring submission or that this project can beat 0.2778, 0.3195, or 0.4413.

Primary-source links already catalogued claim-by-claim in [`knowledge/review_e4a4422d_sources.json`](../knowledge/review_e4a4422d_sources.json):

- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — competition task, metric, and output grid contract.
- [DrivenData rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — submission limits and competition terms.
- [USGS GeoDawn release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — airborne magnetic/radiometric data release.
- [DOE GDR / INGENIOUS compilation 1391](https://gdr.openei.org/submissions/1391) — regional public data compilation and cited license.
- [Official USGS heat-flow release](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28) — metadata for well residuals; binary/schema/coverage remain unverified here.

This review used the repository's source ledger rather than claiming that restricted external sites were freshly checked during this turn. The current source-health feed is a dated reachability log, not a fresh score or organizer receipt.

## Remaining work and limitations

1. Obtain an explicit prospective protocol decision that reconciles the literal 3-pixel overlap rule with the universal-support witness. Do not invent a local exemption.
2. Only after that decision, pre-register one method, test all feature canaries, run the shared buffered hide-and-recover evaluator, and compare against the current incumbent before a separate selector reviews a real slot.
3. Do not mark the existing file submit-ready: the selector has not approved it and no artifact-linked organizer receipt exists.
4. Preserve a true untouched spatial validation set; current mapped-fault holdout performance is a proxy and the seeds share geography/catalogue.
5. For HFR, acquire and validate actual official bytes, schema, quality metadata, spatial coverage, and license before proposing it as executable.
6. The reported portal `[0,1]` error has no established diagnosis without its rejected artifact and submission receipt. Local validation passes; portal acceptance is not proven.

**Disposition:** negative; inherited artifact may be downloaded for research only; no new competition TIFF was generated because every nonempty candidate is blocked by the current verified novelty gate.
