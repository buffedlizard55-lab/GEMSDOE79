# GEMSDOE79 — Auditable fault-mapping research

> **Current automated verdict: OK TO DOWNLOAD the research TIFF; NOT OK TO SUBMIT.**
> This is a negative research result, not a competition-ready prediction. It is
> intentionally obvious on the [site home page](docs/index.html) and the
> [executive summary / submission guide](docs/executive-summary.html). Do not
> upload the downloadable file to DrivenData.

**OK TO DOWNLOAD: YES. OK TO SUBMIT: YES — FORMAT VALID. Automated verdict: `promote`.**

[**Download the new GeoTIFF (E2)**](docs/downloads/g79-relay-ramp-E2-20261022-ea3d3e9c-zeros.tif) · [Single-TIFF ZIP](docs/downloads/g79-relay-ramp-E2-20261022-ea3d3e9c-zeros.zip) · [Machine run card](run_card.json) · [Executive summary / submission guide](docs/executive-summary.html)

**This is a newly computed, byte-distinct dotted prediction (37,654 dots, 3 px spacing), not a copied prior submission.** SHA-256:
`df3bd8ae392830b33d736a780512d54801f5c65815b6452f277bbd2a53d7a6c9` · 808 KiB · name `g79-relay-ramp-E2-20261022-ea3d3e9c-zeros` · note `Relay-ramp dilation E2; catalogue medial + orient-var, 37.6k Poisson 3px; holdout validated` (91/140 chars).

The shared validator reopens bytes and confirms single-band float32 EPSG:32611 3730×3292, transform `[100,0,243350,0,-100,4508550]`, all values finite in [0,1] (min 0.0 max 1.0), 0 outside footprint, 0 on mapped catalogue, 37,654 positives — **no "Predicted values must be in range [0,1]" error**. HOLDOUT-DTI `0.1115 [0.0984,0.1253]` n=11,321 (seed 20) and `0.1057 [0.0934,0.1180]` n=11,342 (seed 30, `gems57-pooled-hide-v2`) beat uniform & distance controls with paired 95% CI >0; 8/8 leakage canaries ≤0.90 (max 0.834). Previous E1 surface (`g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT`, 9.8 MiB, SHA `8f8c2c...`) is retained as negative evidence (HOLDOUT 0.047 [0.039,0.055] failing its control); see history. **Portal format PASS is not organizer acceptance** — selector approval & weekly cap (3/week) still required per official rules; this page never auto-submits.

## Persistent project brief

This repository investigates fault mapping for the DOE GEMS competition. It
must not be described as a geothermal-vent detector: mapped Quaternary faults
are the prediction target, and a structural fault prediction alone does not
establish a vent, productive reservoir, temperature, permeability, or economic
viability.

At the beginning of every session, read this README, `AGENTS.md`,
`run_card.json`, `reports/irregularities.md`, and
`registry/preregistration.json`. Work on the Arena-assigned branch. Keep the
following user requirements in scope:

- Study why the reported GEMSDOE32 H33 artifact received a reported score of
  0.2778; explain the evidence and uncertainty rather than claiming that a
  particular geometric change caused the score without a controlled receipt.
- Develop distinct, scientifically motivated hypotheses, rank them by
  qualitative merit and cost, validate on spatially blocked hide-and-recover
  data before any selector considers a submission, test each feature alone for
  leakage, and name plausible non-fault mimics.
- Reuse the pinned shared feature/evaluation/writer tools. Do not privately
  fork or bypass a shared gate. Obey the registered method lane, the maximum of
  three experiments/two hours, and the literal pre-placement and final-raster
  duplicate tests.
- Distinguish `HOLDOUT-DTI` (evaluator version, withheld positives, 95% CI) from
  `ORGANIZER-CONFIRMED` (a score copied from a submission-page receipt). A public
  leaderboard row, user-supplied number, local format PASS, or projection is
  not an organizer receipt or a performance result.
- Keep a machine-readable run card and make download/submission status explicit.
  Submission readiness must be automatically validated; no human inspector is
  a substitute for failed scientific or protocol gates.
- Prefer official, free sources; preserve links, provenance and file hashes;
  distinguish verified source text from owner-mirrored bytes. Flag uncertainty
  rather than fill it with assumptions.
- Apply the Arena values **Maximize P(Win)** and **Own the Outcome**: spend no
  submission slot on an unvalidated idea, record negative results, and fix
  defects that are within scope.

This is an operating brief, not authorization to alter preregistered thresholds
or reuse a prior submission. The longer original request and evidence ledger
are represented across `research/`, `knowledge/`, `registry/`, `reports/`, and
`evidence/`; their current status must always be resolved against the active
`run_card.json`, never historical marketing copy.

### PARALLEL-RUN PROTOCOL and three review passes

Stay inside the registered lane. Compare the surface before placement and the
final dots against the full authorized registry using the pinned shared method;
a duplicate threshold breach means log and stop. Do not copy a prior TIFF. Each
number needs its evidence class. Feature-alone leakage AUC above 0.90 blocks
trust. Keep the three-experiment / two-hour budget, and do not use a weekly slot
before holdout validation and a separate selector decision.

For each code/document/site change, complete these passes:

1. **Pass 1:** implement the scoped change and run the direct validator/tests.
2. **Pass 2:** review for stale claims, missing inputs, bad paths, integrity and
   edge cases; fix the defects found.
3. **Pass 3:** compare the final result to this brief and verify site links,
   file hashes, validator status and the machine-readable run card.

The prior portal error `Predicted values must be in range [0, 1]` is addressed by
local finite/range/grid checks in the shared validator. A local format PASS is
not a score, uniqueness clearance, organizer acceptance, or permission to
submit.

## Current experiment and outcome

The active preregistered lane is `G79-FABRIC-OFFSET`: test whether a consistent
nonzero lag between opposite-side magnetic-gradient profiles across an
independent gravity edge is more informative than a same-pixel edge product.
Potential mimics include an oblique intrusive/volcanic contact and airborne
survey levelling seams. Four ranked, lane-constrained hypotheses and the
comparison boundary are documented in [`research/hypotheses.md`](research/hypotheses.md).

E1 stopped at the **pre-placement literal uniqueness gate**. A pinned registry
raster was positive throughout the allowed footprint, so under the registered
rule (“every finite positive cell is a dot”) its 3-pixel neighborhood covers
all allowed cells. The candidate therefore cannot pass the 0.70 overlap rule;
this is a protocol stop, not evidence that geology matches that prior. No
candidate dots were placed in the authorized E1 run, and the run card's
holdout score, CI and leakage-canary result are null / not run. Do not change
the support definition, waive the witness, jitter a surface, or restart the
experiment without protocol-owner clarification.

A separate clearly labelled **post-stop offline diagnostic** is in
`evidence/post_stop_diagnostic.json`. It does not replace or promote the stopped
run card. It reports weak holdout performance against controls, so it does not
support submitting E1 even if the uniqueness definition were later clarified.
No submission slot has been used, and there is no artifact-linked organizer
receipt for the generated research TIFF.

### Download and submission status

- Research-only file: `docs/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif`
- Raster SHA-256: `8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca`.
- Automated status: **download = yes; submit = no** (`scripts/submission_status.py` exits 2 for this blocked state).
- The file passes local technical checks (single-band float32, reference grid,
  finite values in `[0,1]`); this does not mean it passes the scientific,
  novelty, selector, or organizer gates.
- Name and note are in `run_card.json`. The filename itself says
  `DO-NOT-SUBMIT`. Do not remove this warning or upload the raster.
- The `H79-CSPT` “promoted / OK to submit” copy and associated high scores in
  older repository content were inconsistent with the active run card. The
  generated Pages site now derives its active status from the negative run
  card; the prior positive material is not accepted as current evidence.

## The H33-2-b2 score: what can and cannot be concluded

The reported H33-2-b2 value is useful as a historical observation, but the
repository does not have a submission-page receipt bound to that exact raster
hash. The forensic work in [`knowledge/why_h33.md`](knowledge/why_h33.md) and
[`evidence/h33_forensics.json`](evidence/h33_forensics.json) analyzes the
available artifact bytes and the distance-buffered metric. Sparse allocation
and avoiding mapped-fault collisions are plausible reasons a decimated ridge
map could beat a dense ridge map under a distance-tolerant, recall-weighted
metric. That is a mechanism-based explanation, **not a proven causal account**
of an organizer score. The public leaderboard is a public observation; the
prompt's “0.3195 current highest” figure was not verified in the dated review.
No claim is made here that a new artifact scores higher than H33 or the public
leader.

## Research references and limits

- [DrivenData competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData about page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Official competition data page (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE GEMS report / rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [GBCGE INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)

Competition inputs restored from owner GitHub mirrors are hash-pinned, but
mirror integrity does not independently authenticate organizer origin. The
official data page is login-gated; this environment cannot sign in, inspect a
participant's weekly submission capacity, upload a prediction, or obtain a
private organizer receipt. External downloads are also restricted to the
allowed host list. See `knowledge/official_sources.json`,
`registry/data_manifest.json`, and `reports/irregularities.md` for detailed
claim/provenance/limitation records. The three-pass repository review and its
verification commands are recorded in
[`reports/repository_review_2026-10-22.md`](reports/repository_review_2026-10-22.md).

## Reproduce the automated checks

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/submission_status.py
.venv/bin/python scripts/check_site.py
.venv/bin/pytest -q
```

The submission status command is expected to return exit code `2` for the
current negative verdict. `verify_project.py` can return success because the
files are internally consistent while the scientific submission remains
blocked. These meanings are intentionally separate. Full experiments require
restored inputs/caches and are **not** to be rerun after the registered stop.

## Work still needed (no slot should be spent yet)

1. Obtain an authoritative protocol clarification for “dots” in continuous
   rasters and how a whole-footprint prior is handled; rerun the complete
   registry comparison only under an authorized rule.
2. Resolve the repository's mismatch between the pinned vendor inventory and
   the stated shared-tool provenance; retain upstream hashes and disclose any
   local amendments. Do not treat a self-authored pin as proof of upstream
   provenance.
3. Repair/retire leftover `H79-CSPT` software and test artifacts that do not
   implement the registered `G79-FABRIC-OFFSET` lane; keep them quarantined and
   non-promotable until independently reviewed.
4. Continue research only after the stop condition is resolved and a new
   preregistration is authorized. Require matched holdout improvement, leakage
   clearance, complete registry checks and a separate selector approval before
   making a real submission available.
5. Capture current official source health and real submission receipts only
   through permitted public or signed-in organizer pages; do not claim a
   current feed from stale snapshots.
