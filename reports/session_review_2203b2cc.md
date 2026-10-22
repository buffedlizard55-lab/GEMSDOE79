# Three-pass repository review — session 2203b2cc, 2026-10-22

## Outcome and non-negotiable submission decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The canonical H79-NHR research TIFF
already existed at session start. Its bytes, name, note, negative run card,
historical evaluator outputs, preregistration and duplicate verdict are unchanged.
This review did **not** generate a new protocol-unique TIFF, copy/rename a prior
submission, run a new scientific experiment, select a weekly slot, or upload to
DrivenData. A failed novelty gate cannot honestly be converted to a passing one
by another filename or an output-format check.

The user request's “single method paragraph below” is not a delimited new method
assignment. The repository's active NHR lane has already stopped as a duplicate;
AGENTS.md prohibits retuning it. The review therefore addressed the previous
session's unresolved workflow/reliability tasks rather than silently opening
another lane or weakening its thresholds.

## Pass 1 — inspect and implement

- Read the complete README including the preserved original prompt; AGENTS.md;
  canonical run card; active and archived preregistrations; irregularity log;
  evaluator/registry evidence and relevant scripts/tests. Retained the original
  prompt rather than duplicating its repetitions again.
- A clean virtual environment installed successfully from the old lockfile, but
  pytest **failed during collection**: `src/gems79b/features.py` imports
  `skimage.filters.sato`, and `scikit-image` was absent from both manifests.
  Added `scikit-image>=0.25,<1` to requirements.txt and pinned the installed
  release and its transitive dependencies in requirements.lock. This fixes the
  merged archived-lane tests and the Pages job that runs the whole suite.
- Confirmed NHR's scientific and packaging commands had no terminal-lane guard.
  They could attempt to load missing inputs, rerun a stopped model or replace
  evidence. Added `gems79.lifecycle.require_open_lane` at each mutating NHR entry
  point, before bulk inputs/output. Missing, malformed, mismatched, unknown or
  terminal cards fail closed; no force flag. CLI refusal exits 2.
- Replaced README commands that invited rerunning this stopped lane with safe
  verification/build commands. Historical runners remain auditable, not cleared
  for future experimentation. Their combined surface/placement stage is **not**
  approved as a template: a future preregistered runner must wait for a completed
  surface scan before placement (IR-79-54).
- Removed the unsupported “validated, unique GeoTIFF” metadata from all generated
  HTML pages. The negative home page and executive guide remain explicit.

## Pass 2 — scientific claims, failure paths and edge cases

- Corrected README, NHR analysis and both home-page rendering branches: exact
  catalogue pixels are masked, but their 200 m collar is not. The measured H33
  change (removing 6,436 D2.8 dots) is consistent with reduced redundant FP;
  it does not prove those dots all had zero TP on nearby unmapped strands.
  The user-reported 0.2600/0.2778 pair has no artifact-linked organizer receipt.
- Removed the unsupported claim that H33's dot count establishes an optimal
  break-even budget. Changed the homepage's 2.33 TP illustration to explicitly
  describe an ideal straight grid-aligned trace, not a measured bound or score.
- Corrected “same folds and budget” on the control tiles: the fold-fair legacy
  control uses its inherited budget, not the candidate allocator's exact count.
- Added tests covering missing/broken cards, lane mismatch, terminal and unknown
  verdicts, explicit stop flags/reasons and subprocess refusals. They verify
  canonical evidence/artifact bytes and the NHR cache remain unchanged. Added a
  regression test against the misleading website description.
- A preliminary concern about a shared-pin schema mismatch was **disproved**:
  the current template pin is a list of path/hash records and its current readers
  agree. No schema or shared mathematical implementation was changed.
- Restored **one** frozen registry witness through GitHub, verified SHA-256,
  Git-blob hash and size, and remeasured its literal universal overlap certificate
  without changing scientific evidence. Result: no uncovered allowed pixels;
  every nonempty map fails the literal >70% overlap rule against that raster.
  This is not a rescan of the full registry and does not resolve v3 novelty.
  NHR also fails against ordinary non-space-filling rasters, independently of
  this literal degeneracy. See the canonical card for those historical results.

## Pass 3 — recheck against the request

- The downloadable TIFF/ZIP, name and <=140-character note remain immediately
  accessible. Reopened TIFF validation confirms one float32 band, finite values
  in [0,1], no NaN inside the footprint (indeed none anywhere), sample CRS,
  shape and transform, and no positive predictions on catalogue pixels.
- The five ranked hypotheses already recorded **before** the NHR run remain in
  [hypotheses_nhr.md](../research/hypotheses_nhr.md). The top one was executed
  and stopped; the others are untested/deferred, not newly viable claims. Their
  historical “inputs present” statements describe that earlier restored cache,
  not this fresh checkout. No new external-data hypothesis was called obtainable
  without retrieving its data, and none was used to evade the lane stop.
- Historical NHR HOLDOUT-DTI remains 0.1431 [0.1281, 0.1574] / 0.1522
  [0.1335, 0.1696], evaluator `gems57-pooled-hide-v2`, with 11,321 / 11,342
  withheld positive pixels. These are saved evaluator outputs, **not newly rerun
  measurements**, organizer scores, or evidence of a leaderboard improvement.
- Existing source research is inherited evidence, not a new line-by-line review
  of every external website. This sandbox allows GitHub/npm/PyPI hosts only.
  Retrieved the official reference README at commit
  `aebe92f7c8a990f0e3443451b7a825d9afd6336b`: it explicitly supports CPU-only
  environments, so a GPU is not a universal prerequisite. Saved the small
  source snapshot and a scoped retrieval receipt.
- GitHub Pages API reports legacy publishing from main at `/`, status built.
  Local browser/format checks do not prove a fresh public deployment. No new
  DrivenData page, PDF, USGS release, GDR payload, Dropbox file, account capacity
  or organizer receipt was fetched or claimed verified this session.

## Verification

Final verification results are recorded in
[session_verification_2203b2cc.json](../evidence/session_verification_2203b2cc.json).
The source retrieval receipt is
[source_review_2203b2cc.json](../evidence/source_review_2203b2cc.json); the literal
witness remeasurement is
[session_witness_2203b2cc.json](../evidence/session_witness_2203b2cc.json).
These records describe software/source/registry checks, not a new experiment.
The final publication is rebuilt and checked after these fixes.

## Concurrent main updates integrated before PR

Main advanced through PRs #29/#30 during this review. Their changes independently
fixed the same dependency issue and safe README commands; they also hardened
selector evidence reconciliation and excluded `.venv*` directories from publication
scans. All were retained. Merge conflicts were resolved in source, then generated
HTML was rebuilt. New local irregularity IDs are 61/62; the dependency finding is
an independent rediscovery of IR-79-57, not a second issue. Final verification below
is rerun against the combined tree, not just the pre-merge test suite.

## Next session, in priority order

1. Resolve the registry-support policy prospectively with the protocol owner;
   do not exempt dense maps or cap overlap after seeing results. Even a
   clarified policy does **not** rescue NHR's ordinary-raster duplicate failure.
2. Preregister one genuinely different lane, one fixed model/allocator and a
   matched incumbent before evaluating it. Require canaries, buffered whole
   component recovery, paired spatial CIs, surface clearance **before** final
   placement, then final clearance. Never restart NHR or its archived predecessors.
3. Restore hash-pinned bulk features only when an authorized open lane needs
   them; ignored caches do not persist in this checkout. Reaudit registry deltas
   before any future clearance; this review remeasured only one rejection witness.
4. Keep raw official data provenance separate from owner-mirror integrity. The
   official data/receipt pages require an authorized DrivenData session; no
   account credentials or organizer acceptance are available here. The project
   cannot autonomously certify eligibility or the current signed-in weekly cap.
5. Check PR CI and the post-merge Pages deployment. GitHub Actions has broader
   network access than this sandbox, but reachability alone is not validation of
   scientific claims or proof that a private submission was accepted.

## Official links for review

- [Organizer reference README, pinned revision](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) — freshly retrieved here.
- [Competition problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — inherited source review, not refetched here.
- [Known-pixel masking clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) — inherited source review.
- [Competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — inherited source review.
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — inherited source review.

This session fixes actionable reliability issues; it does not claim that the
request for a new, unique, submission-ready high-scoring TIFF has been fulfilled.
