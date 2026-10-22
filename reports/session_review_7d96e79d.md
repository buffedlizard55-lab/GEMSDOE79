# Session 7d96e79d — three-pass repository review

Date: 2026-10-22. Branch: `arena/7d96e79d-gemsdoe79`.

## Decision first

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The existing THVC download is an
inherited negative research artifact, not a newly generated unique submission.
No scientific lane was started, no new TIFF was generated, and no competition
slot was used. The highest-priority request for a new unique submission remains
**unfulfilled**, rather than being disguised by renaming an old file.

## Pass 1 — implementation and measurement

Read the full README/project brief, AGENTS contract, canonical card, required
preregistrations, irregularities, H33 analysis and prospective hypothesis table.
Installed the exact requirements lock in a fresh Python 3.11 environment.

- `pytest -q`: **477 passed**, no failures.
- `preflight_new_lane.py --restore`: **exit 2**, measured impossibility under the
  literal gate; see [new receipt](../evidence/review_7d96e79d/preflight.json).
- `validate_submission.py`: **exit 0**, local format PASS; see
  [new byte inspection](../evidence/review_7d96e79d/format.json).
- `verify_project.py`: exit 0.
- `submission_status.py` and `select_submission.py`: both exit 2 (expected
  refusal, not a software failure). No manual-upload override was introduced.
- `check_site.py`: exit 0, seven pages and 128 local links checked.

These are software/registry/raster measurements, not competition scores.
The pinned registry witness SHA-256 is
`ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`.
Its positive-support halo covers every eligible cell. Consequently **any
nonempty candidate** has forward overlap 1.0, violating the literal 0.70 limit.
An empty prediction would not resolve the scientific requirement for a useful
new discovery submission. No sparse-only exception or post-hoc amendment is used.

## Pass 2 — scientific and source review

Freshly read both chunks of the official [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
It confirms the prediction target is **faults**, not demonstrated geothermal
vents or economically producible reservoirs. The initial test contains expert
faults absent from the public catalogue. Hiding public segments is therefore a
proxy with distribution-shift risk, not equivalent organizer ground truth.

The official metric takes maximum triangular-kernel coverage per truth pixel,
but sums false-positive cost over predictions. Thus redundant dots may add cost
without benefit. This explains why thinning *can* help; it does not establish why
a particular artifact received a reported organizer score. H33's byte lineage
and conditional deletion inequality remain in the
[existing forensic analysis](../knowledge/h33_review_e4a4422d.md).
The prompt's 0.2778, 0.3195 and 0.4413 are not new artifact-linked
ORGANIZER-CONFIRMED measurements from this session. No leaderboard improvement
is claimed or projected.

The official format requires one float32 band, confidence in [0,1], EPSG:32611,
100 m resolution and matching bounds, and says data outside bounds is null/NaN.
The current local validator measures finite binary values, matching shape and
transform, and zero exterior footprint fill. This verifies the downloaded bytes,
not portal acceptance or an interpretation of the exterior wording. Without
the rejected file/receipt, the historical range-error cause is unknown.

Freshly retrieved the organizer's [reference README at commit
aebe92f7c8a990f0e3443451b7a825d9afd6336b](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md)
through GitHub's API. It explicitly supports CPU-only execution. Therefore the
prompt's blanket statement that a GPU is needed for training is not a verified
requirement of the organizer reference. A GPU can improve runtime; this session
makes no runtime claim for a future experiment. API retrieval does not authenticate
owner-mirrored competition rasters or provide account-side competition access.

## Pass 3 — original-request and readiness review

The full original prompt is already preserved in README and required reading in
AGENTS. The homepage and executive-summary subpage already expose the download
and the explicit submission refusal. Existing tests verify publication contracts,
validator error cases, evidence aliases, selector refusals and stopped-lane guards.
No defect found in this review justified changing the pinned scientific tools.

The [ranked four-hypothesis backlog](../research/hypotheses_e4a4422d.md) remains
prospective, not four new experiments:

1. **CJX:** cross-scale director-winding junctions in RTP magnetics and isostatic
   gravity; buried structural intersections, with pluton/caldera/seam controls.
   Moderate uncertain value; moderate cost; pinned inputs previously restored.
2. **BLC:** along-contact bilateral multichannel distribution change-points in
   potential fields and rank-only radiometrics; possible offset contacts rather
   than endpoint continuation. Facies/lava/drainage controls. Low-to-moderate
   uncertain value; moderate/high cost.
3. **RSS:** detrended-terrain saddles crossed by independent gravity contrasts;
   catalogue-free transfer-zone hypothesis, unlike visible-tip relay features.
   Erosional wind-gap and terrain-only controls. Low uncertain value; moderate cost.
4. **HFR:** paired warm/cool well heat-flow residuals along an independent
   structural corridor, unlike temperature proximity alone. Groundwater/pumping
   controls. Unquantified value; high acquisition/QA cost. Official USGS product
   DOI [10.5066/P9BZPVUC](https://doi.org/10.5066/P9BZPVUC) is identified in prior
   source evidence, but binary contents, quality schema and coverage have **not**
   been acquired here. Not data-ready or nominated as executable.

These are inherited unimplemented proposals, not newly proven unique geological
ideas. A rank is qualitative judgment, not a DTI projection. The top proposal
was **not validated** because the prerequisite novelty preflight fails, and the
prompt supplies no distinct assigned method paragraph. Do not restart a stopped
lane, choose a private method, bypass the preflight, or spend a slot to fill that
gap. New experiments performed: zero, within the requested experiment cap.

### Next session, in dependency order

1. Resolve the universal positive-support registry obstruction with a prospective
   shared comparability definition. This needs a protocol decision; no algorithm
   can satisfy the unchanged literal rule with a nonempty eligible prediction.
2. Freeze one assigned mechanism and reserve untouched spatial validation data.
   Restore any required cached inputs with manifest hashes; checksum agreement
   alone does not establish licensing or organizer authentication.
3. Only if preflight permits: test individual-feature leakage canaries, then the
   surface novelty gate, buffered whole-segment hide-and-recover using shared
   evaluator/writer, and final-dot novelty. Compare against the current THVC
   incumbent on matched folds, not only the older H33 control. Report pooled
   HOLDOUT-DTI, evaluator version, withheld positives and paired spatial CI.
4. Separate selector approval from experiment results. Account eligibility,
   remaining weekly capacity and an artifact-linked organizer receipt are still
   unavailable here. Automation cannot honestly infer these from a public page.

This review does not claim a complete fresh crawl of all sibling websites,
new external-data acquisition, full registry census, new canary results, a new
holdout run, or public deployment success. Prior receipts remain historical.
