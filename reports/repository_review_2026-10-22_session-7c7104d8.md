# Repository review — Arena session `7c7104d8` — 2026-10-22

## Executive decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** At this session's branch baseline
(`9640ed3`), the canonical artifact was H79-NHR and already had a local
format-pass / duplicate-fail verdict. During PR preparation, successive updates
to `main` moved the canonical card through G79-THVC to H79-STEP. The current
H79-STEP TIFF
(`docs/downloads/gems79-h79-step-37654dots-20261022T043422Z-a99bb5c2-DO-NOT-SUBMIT.tif`,
SHA-256 `0c6782957e178a98b9f231b4386ef6796c083252a090351b0fb4f7f9a756a64c`)
was produced by an upstream parallel lane, not this review; its card remains
negative and marks registry uniqueness unexecuted because the full registry
cache was absent. This session's pinned universal-support witness independently
blocks every nonempty candidate under the literal rule. No new candidate TIFF,
model, holdout, final-dot placement, slot selection, or DrivenData upload was
performed in this session. The pinned registry witness was restored and
verified only in the ignored `.cache`; it is not a submission artifact.

The literal new-lane preflight was actually rerun with the pinned witness:

```text
state: impossible_under_literal_gate
start_new_lane: false
covered_allowed_fraction: 1.0
limit: 0.70
overlap for every nonempty candidate: 1.0 > 0.70
exit code: 2 (expected stop)
witness SHA-256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be
```

This is a **REGISTRY-MEASUREMENT**, not a score. Under the literal protocol,
there is no permitted nonempty submission to score or place in a weekly slot.
The separate matched-budget interpretation in archived work is not silently
adopted here. The historical H79-NHR file also exceeded the overlap threshold against
ordinary, non-space-filling registry dot fields, so resolving only the
universal-support witness would not promote that archived candidate.

## Answer to the H33 question

The checked-in byte forensics (`evidence/h33_forensics.json`) show H33 is not a
newly trained geological detector. Its positive pixels are exactly a subset of
the earlier D2.8 dot raster after removing dots within 200 m of the mapped
catalogue: 44,090 D2.8 dots became 37,654 H33 dots; 6,436 were removed and the
pixel-set disagreement is zero. These are **RASTER-MEASUREMENTS**, not scores.
The `0.2778` filename/score pairing in the prompt is an **UNVERIFIED HISTORICAL
REPORT**: no submission-page receipt binds that score to the H33 filename and
raster hash.

A plausible metric mechanism is improved emission efficiency. The competition
metric's TP credit is distance-weighted and saturates at each truth pixel,
whereas positive prediction mass away from truth adds FP. Removing redundant
near-catalogue dots can therefore improve the index if they add more FP than
lost credit. It is **not proven** that the removed dots were false positives:
only exact mapped-fault pixels are masked, and an unknown expert fault may lie
near a mapped trace. The byte relationship explains a plausible mechanism, not
a causal decomposition of the hidden test score.

The merged evidence register contains an official leaderboard fetch dated
2026-10-22 (IR-79-72/77): **PUBLIC-LEADERBOARD OBSERVATION** rank 1 is 0.4413;
no row among ranks 1–50 shows 0.3195, and the user-reported H33 value 0.2778 is
also absent from those 50 rows. This is a public-page observation, not an
artifact-linked submission receipt or ORGANIZER-CONFIRMED score. The H33 value
is not proof that the H33 bytes earned it. A higher leaderboard result is
possible in principle, but none of the offline evidence establishes that this
project can beat the public leader or the organizer's hidden test set. This
session did not refetch the leaderboard; the date and evidence source are
preserved in `reports/irregularities.md` and `reports/session_review_b79882e0.md`.

## Holdout evidence from checked-in run cards — not rerun this session

The latest-main canonical run card (`H79-STEP`; `evidence/holdout_edge_seed20.json`
and `evidence/holdout_edge_seed30.json`) reports these results from evaluator
`gems57-pooled-hide-v2`, using the pooled 300 m triangular DTI and buffered
whole-component hide-and-recover split. These are inherited, not rerun by
session 7c, not public leaderboard scores, and not organizer-confirmed:

| Seed | H79-STEP candidate HOLDOUT-DTI | Uniform-control HOLDOUT-DTI | Paired delta vs uniform HOLDOUT-DTI |
|---|---|---|---|
| 20 | 0.0949; 11,321 withheld positives; 95% CI [0.0735, 0.1161] | 0.0315; 11,321 withheld positives; 95% CI [0.0279, 0.0349] | +0.0635; 11,321 withheld positives; 95% CI [+0.0431, +0.0837] |
| 30 | 0.1087; 11,342 withheld positives; 95% CI [0.0858, 0.1293] | 0.0389; 11,342 withheld positives; 95% CI [0.0344, 0.0430] | +0.0698; 11,342 withheld positives; 95% CI [+0.0461, +0.0906] |

The card says H79-STEP did not beat its fold-fair H33-control point estimate on
seed 20; it does not report a paired confidence interval against that H33
control, so no robust H33 superiority claim is warranted. More importantly,
`correlation_overlap_vs_registry.gate_executed` is false because the full
registry cache was absent when this upstream candidate was built. That is
**not a uniqueness pass**. This session's pinned universal-support witness
still covers every allowed pixel and rejects every nonempty map under the
literal rule. Format/range validation alone cannot clear the candidate.

### Earlier G79-THVC results — superseded by H79-STEP

Before the latest main update, the G79-THVC card reported **HOLDOUT-DTI** from
the same evaluator and buffered whole-component split:

| Seed | G79-THVC candidate HOLDOUT-DTI | Matched fold-fair H33-control HOLDOUT-DTI |
|---|---|---|
| 20 | 0.1905; 11,321 withheld positives; 95% CI [0.1741, 0.2069] | 0.0961; 11,321 withheld positives; 95% CI [0.0831, 0.1090] |
| 30 | 0.1944; 11,342 withheld positives; 95% CI [0.1774, 0.2126] | 0.0989; 11,342 withheld positives; 95% CI [0.0854, 0.1128] |

Those stronger proxy results also were not organizer scores and did not clear
the literal all-registry overlap rule: sparse-only overlap summaries did not
override the continuous/blanket witnesses. No selector receipt or weekly slot
approval existed. The current canonical artifact is H79-STEP and remains
**OK TO SUBMIT: NO**.

### Historical H79-NHR run — superseded as current canonical card

The earlier H79-NHR run card reports the following **HOLDOUT-DTI** values. Each
is from evaluator `gems57-pooled-hide-v2`, the same whole-component buffered
catalogue hide-and-recover split, and includes the withheld-positive count and
95% CI:

| Seed | Candidate HOLDOUT-DTI | Fold-fair H33-control HOLDOUT-DTI |
|---|---|---|
| 20 | 0.1431; 11,321 withheld positives; 95% CI [0.1281, 0.1574] | 0.0961; 11,321 withheld positives; 95% CI [0.0837, 0.1086] |
| 30 | 0.1522; 11,342 withheld positives; 95% CI [0.1335, 0.1696] | 0.0989; 11,342 withheld positives; 95% CI [0.0842, 0.1120] |

The NHR result beat the fold-fair H33 control on this proxy, but its surface and
final dots failed registry novelty. This is not an ORGANIZER-CONFIRMED result,
not a leaderboard score, and not a projection. The leakage result is a separate
**LEAKAGE-CANARY**: 464 feature-alone tests cleared the 0.90 threshold, with
maximum symmetric AUC 0.8589. No canary or holdout was rerun in this review.

## Repository inspection and three passes

### Pass 1 — read and establish the current state

- Read the full README, including the preserved prompt; `AGENTS.md`; canonical
  `run_card.json`; active NHR and archived E1 preregistrations; irregularities;
  current status; source ledger; relevant uniqueness, holdout, validator,
  writer, build, test, and site code; and the prior hypothesis registers.
- Confirmed the request's single-method paragraph is not delimited, as already
  recorded under IR-79-02/IR-79-41. At this branch's entry, H79-NHR was already
  stopped; the latest-main H79-STEP artifact was imported later during PR sync.
- Installed the pinned Python environment from `requirements.lock` and reran
  `scripts/preflight_new_lane.py --restore`. It independently restored and
  verified the existing witness and returned exit 2. No experimental feature
  or candidate surface was built.
- Inspected current storage: `data/reference/existing_faults.tif`,
  `data/reference/sample_submission.tif`, and `data/restore_receipt.json` are
  present. The large training raster, reusable `.cache` feature stack,
  `data/external` files named in the merged GDR receipt, raw GeoDAWN line
  products, raw MT tensors, and raw 1 m DEM are absent from this checkout. The
  merged official-data receipt documents source hashes from the upstream run,
  but is not a substitute for bytes available here. The owner's hash pins verify
  mirror consistency, not organizer-origin authentication.
- During PR preparation, integrated the newer `origin/main` rather than leave a
  stale review branch. Its inherited IR-79-80/81 evidence adds a prompt-named
  sibling-raster audit and README publication-boundary tests; those are upstream
  records, not new experiments or scores from this session. The latest official
  leaderboard observation cited above is likewise inherited from the 2026-10-22
  source review, not fetched by this session.

### Pass 2 — identify and fix a repository defect; review hypotheses

- The branch baseline had two `scikit-image` declarations in `requirements.txt`
  (`>=0.25,<0.27` and `>=0.25,<1`). Although pip intersects them, duplication
  was unnecessary. During this review, current `main` independently consolidated
  the file to one `>=0.25,<1` line (the lock pins `0.26.0`); the merge preserves
  that upstream bound. This PR adds a regression test rejecting duplicate
  normalized package names in either manifest and records the branch-baseline
  finding as IR-79-86 after integrating newer main updates. No locked package version or scientific artifact changed.
- The previous shortlist in
  `research/hypotheses_preflight_a7d092d7.md` was checked against the archives.
  Its far-field idea is adjacent to archived H79-FF; its cross-scale scarp idea
  is adjacent to tested SDPT features; and its magnetic/scarp and clay-cap ideas
  overlap prior E1/STEPCO and hydrothermal family work. They cannot all be
  described as wholly untried across the family.
- Added a new, explicitly unvalidated three-hypothesis research shortlist to
  `research/hypotheses_session_7c7104d8.md` and the generated Research page:
  raw GeoDAWN flight-line residual coherence, raw MT phase-tensor anisotropy,
  and a process-based lidar scarp-profile fit. It names each data layer,
  physical signature, fault-omission rationale, method difference, non-fault
  mimic, official source link and data-availability check. All three are blocked
  in this checkout; the list is not an authorization to run them.
- No new official website was fetched. The source links and descriptions are
  inherited from `knowledge/official_sources.json` and earlier source reviews;
  direct DrivenData, USGS and GDR requests are outside this sandbox's host
  allowlist. The merged source-health feed's latest reachability attempt is
  2026-10-22T04:35Z and reports SSL failures; reachability checks do not refresh
  scientific claims. The public-leaderboard observation cited above came from
  an earlier research fetch recorded in the merged report, not a fetch by this
  session.

### Pass 3 — acceptance re-check and post-merge regression repair

- The first verification after merging the newer main exposed an integration
  regression: the canonical card had changed to H79-STEP, but the shared
  verifier, site builder, tests and active download directory still assumed
  G79-THVC. The site builder refused inconsistent evidence and the first full
  test run had 16 failures (239 passed). The old and new TIFFs were both in
  `docs/downloads/`, while the generated analysis page still presented THVC as
  current. This was a publication/verification mismatch, not a new scientific
  result.
- Archived the superseded G79-THVC TIFF, ZIP, receipt, run card and historical
  byte-recovery receipt under `archive/g79_thvc_20261021/`, with a SHA-256
  manifest. It is retained as historical evidence; `docs/downloads/` now holds
  only the current H79-STEP file. No prior artifact was overwritten or deleted.
- Updated the shared verifier to bind H79-STEP holdout and canary values to
  their checked-in evidence, validate the H33 comparison, and report the full
  registry uniqueness gate as **not run** rather than assuming a pass. The
  pinned universal-support witness and negative verdict remain fail-closed.
  Updated the site builder to render the current card dynamically and label
  G79-THVC/H79-NHR material historical. Repaired regression tests so current
  and archived artifacts are checked separately.
- Rebuilt the static site. It shows **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**,
  the inherited HOLDOUT-DTI evidence class, the unexecuted-registry limitation,
  and an explicit DO-NOT-SUBMIT decision without requiring human inspection.
  The H79-STEP TIFF was reopened through the format/range validator: one
  float32 band, EPSG:32611, shape 3730 × 3292, values in [0,1], zero NaNs,
  and 37,654 positive pixels. SHA-256:
  `0c6782957e178a98b9f231b4386ef6796c083252a090351b0fb4f7f9a756a64c`.
- A deterministic byte-reserialization check recovered the current TIFF and
  single-TIFF ZIP exactly (same SHA-256 values, 37,654 decoded pixels); it
  reports zero scientific experiments, holdouts, dot placements, and slots.
  This is a format/byte-integrity check, not a model run or scientific
  re-evaluation.
- Final verification after the repair: `verify_project.py` passed all checks;
  `check_site.py` passed 7 pages, 124 local links and 2 compatibility
  redirects; `pytest -q` passed 256 tests (3 Rasterio pending-deprecation
  warnings); `pip check` and `git diff --check` passed; and
  `submission_status.py` returned the expected negative-decision exit 2.
  These are software, evidence-consistency, format and publication checks—not
  a new scientific holdout or organizer acceptance result.

## New candidate shortlist: rank, cost, and blockers

The ranked list lives in
[`research/hypotheses_session_7c7104d8.md`](../research/hypotheses_session_7c7104d8.md)
and is published on the Research page. Ranking is qualitative, **not DTI and
not a score projection**:

1. **Raw GeoDAWN line-level anomaly coherence** — medium-high potential,
   high cost. It would test whether a basement anomaly persists across adjacent
   flight lines after tie-line and height effects are modeled. The official
   USGS release is the source lead; actual raw line files and footprint coverage
   are not verified in this checkout.
2. **Station-level MT phase-tensor anisotropy** — medium potential, high cost.
   It could add direction and frequency-depth structure beyond scalar
   `cond_surf`; the official DOE GDR submission is the source lead. Raw MT
   tensors/station coverage are absent and direct download was not checked.
3. **Process-based lidar scarp-profile inversion** — low-medium potential,
   medium-high cost. It would fit a fixed scarp diffusion profile rather than
   repeat an edge/curvature amplitude detector. Official USGS 3DEP is the source
   lead; raw DEM tiles and target-area availability are absent/unverified.

All current candidate sources therefore fail the user's availability gate for
this session. The top candidate was **not** evaluated on HOLDOUT-DTI: the
literal registry gate stops every nonempty candidate before holdout, and its raw
input is also missing. No weekly slot was touched. The next allowed scientific
step is not training; it is an explicit prospective protocol clarification and
verified source/data access.

## Limitations and manual-review links

- [DrivenData problem description / metric / format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition / leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DOE competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE GDR / INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [Official DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)

Claim-by-claim source dates, licensing notes and evidence limits are in
[`knowledge/official_sources.json`](../knowledge/official_sources.json). Links
are supplied for review; they do not mean those external hosts were fetched
again in this session. No claim here establishes a current leaderboard value,
submission receipt, remaining weekly capacity, geothermal vent, productive
reservoir, or commercial viability.
