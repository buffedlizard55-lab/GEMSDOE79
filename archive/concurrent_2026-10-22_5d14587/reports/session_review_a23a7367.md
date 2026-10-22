# Three-pass repository review — session `a23a7367`

Date: **2026-10-22 UTC**. Branch: `arena/a23a7367-gemsdoe79`.
Scientific verdict remains **negative / DO NOT SUBMIT**. This document records a
repository and release-safety review; it is not a new experiment, score, upload,
or selection of a weekly submission slot.

## Current-state addendum — upstream PR #22 integrated during review

After the original three-pass review, PR #22 advanced `main` to the G79B
scarp-dipole lane. This branch now incorporates that upstream state; the
original pass-by-pass findings below are explicitly the earlier E1 snapshot.
This session did **not** generate or rerun the G79B candidate, retune its
method, place dots, rerun its holdout, upload it, or use a slot.

The current mainline artifact is
`docs/downloads/g79b-scarpdipole-geoand-E1-20261022-5cb0eb8f-DO-NOT-SUBMIT.tif`
(SHA-256 `16a6e07f97441b6b5431ca24b7481658cdb7b7f59daec0e69070f7d5fc8cf795`).
It passes local GeoTIFF/ZIP format validation, but the current run card records
`verdict: negative`, `protocol_unique: false`, and `ok_to_submit: false`.
`ok_to_download: true` means only that the local bytes pass download integrity
checks; **it is not safe to submit**. Every current candidate/control score is
HOLDOUT-DTI and now carries the evaluator, withheld-positive count, and 95% CI
in the run card, evidence JSON, README table, and generated site. No
ORGANIZER-CONFIRMED receipt exists.

## Executive decision — pre-sync E1 snapshot

At the initial review snapshot, the active run was E1. Its research GeoTIFF was
download-enabled, but its run card and automatic status checker both said
**OK TO SUBMIT: NO**. It was byte-distinct from the verified registry bytes, but
was **not protocol-unique** and did not pass the literal novelty gate. I did
not generate a new TIFF, change the candidate, place dots, run a new holdout,
or upload anything: the preregistered lane had already stopped negative, and
its shared universal-overlap witness blocks every nonempty candidate under the
literal rule. A fresh filename or re-serialization would not fix that.

At that pre-sync snapshot the root `run_card.json` retained null primary
HOLDOUT-DTI and confidence-interval fields because E1 had stopped before
scoring. A separate, previously stored post-stop diagnostic was not a
substitute for the run card or a promotion receipt. There was no
`ORGANIZER-CONFIRMED` submission score in the repository. The prompt's `0.2778` is an **unverified historical filename/score
report**, not proof that those exact TIFF bytes earned the value. The byte-level
analysis in `knowledge/why_h33.md` shows that the H33 raster is a pruned subset
of D2.8; reducing redundant or false-positive emissions is a plausible metric
mechanism, but the bytes alone cannot establish why a remote score changed.

At that pre-sync snapshot, the existing E1 research download was not a newly
validated entry for this session. The automated decision did not require a
human inspector and displayed **DO NOT SUBMIT** on the home and executive pages.

## Pass 1 — inspect and repair

- Read the complete `README.md` (including its preserved original prompt),
  `run_card.json`, `reports/irregularities.md`, and
  `registry/preregistration.json` before editing, as required by `AGENTS.md`.
  Also reviewed the active status/validation path, site builder, site checker,
  workflows, tests, frozen registry/template pins, current pages, and source
  freshness record.
- Found literal unresolved merge-conflict markers in `AGENTS.md`; the file
  simultaneously pinned an old branch and required branch-neutral behavior.
  Replaced it with one branch-neutral contract that uses current Arena session
  metadata and preserves the stopped-lane rules.
- Added `startup_contract_checks()` to `scripts/verify_project.py` and software
  tests so later publishing rejects a missing startup contract, conflict
  markers, or a stale hardcoded Arena branch.
- Tightened the visible download wording in the site generator: the GeoTIFF and
  ZIP links now identify the file as research-only and **DO NOT SUBMIT**. The
  site-link checker and browser test assert that this warning is attached to
  the actual TIFF download control, not merely elsewhere on the page.
- Made the generated machine-readable site status and manifest use the verified
  local decision returned by `verify_project.py`, rather than independently
  hardcoding a download/submission status.
- Corrected the irregularity-log chronology sentence and duplicate issue
  references. The second canary note is explicitly supplemental evidence for
  its existing finding; the archived concurrent-lane audit now has a unique
  issue ID. No historical evidence was deleted.
- Preserved the four previously ranked hypotheses. No additional hypothesis
  or method lane was opened: the current lane is already stopped, and the
  literal duplicate stop is not permission to continue with another idea.

## Pass 2 — challenge assumptions and test edge cases

- Confirmed the start contract contains no merge markers or hardcoded prior
  branch. Regression tests exercise both failure cases.
- Confirmed the homepage and executive summary each display the explicit
  `OK TO DOWNLOAD: YES / OK TO SUBMIT: NO` decision, with **DO NOT SUBMIT** on
  the TIFF link itself. The current research artifact is not presented as a
  cleared competition candidate.
- Confirmed the generated status reports organizer acceptance as false and does
  not treat a local format pass as promotion.
- Kept `run_card.json`, the scientific preregistration, the shared `vendor/gems57`
  pins, the TIFF/ZIP bytes, and the stopped experiment-state file unchanged.
  The shared evaluator/writer/novelty tools were not modified.
- Reviewed the existing four-hypothesis table and its named confounders against
  the source ledger. Its highest-ranked E1 idea is not established as an
  improvement over the current best. Any scores in the prior diagnostic remain
  explicitly labelled there as HOLDOUT-DTI, with evaluator version, withheld
  positives and intervals; the primary run card correctly remains unscored.
- Source freshness limitation at the E1 snapshot: the scheduled source-health
  feed recorded failed requests on 2026-10-21. Upstream PR #22 later added a
  2026-10-22 public leaderboard observation in
  `evidence/session_verification_2026-10-22.json`; it remains
  `PUBLIC-OBSERVATION`, not an artifact-linked score or submission receipt.
  Conflicting user-supplied high-score assertions are documented in IR-79-39.
  The official-source ledger records URLs, review dates and claim limits.

## Pass 3 — verification against the request

The persistent brief is still present in `README.md`; the submission decision
is prominent; the executive summary explains how a future **approved** TIFF
would be submitted; the automatic status decision requires no human
inspection; local validation checks the downloaded TIFF bytes, range, CRS,
shape and transform; and no slot is selected or consumed. The brief's request
for a **new protocol-unique, promotable TIFF cannot be satisfied** under the
mandatory stop rule and current registry definition. We do not relabel the
existing negative research surface as a competition submission.

Pre-sync E1 software-only verification (snapshot at commit `1dafab5`):

- `pytest -q`: **152 passed**.
- `scripts/verify_project.py`: **24/24 integrity/status checks passed**; TIFF
  SHA-256 remains
  `8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca`.
- `scripts/check_site.py`: **7 pages and 110 local links passed**; all pages
  reachable, no third-party assets, correct negative decision.
- `scripts/submission_status.py`: JSON verdict `negative`,
  `ok_to_download=true`, `ok_to_submit=false`; exit code **2 is expected** for
  this blocked artifact.
- `python -m py_compile scripts/*.py src/gems79/*.py tests/*.py`: passed.
- Browser QA: **21 page/viewport cases** passed, including the warning on the
  actual download link, copied note, TIFF SHA-256, feed rendering, and history
  filtering.

These are software, byte-integrity, and website checks. They are **not** a new
HOLDOUT-DTI, a leaderboard score, organizer acceptance, or scientific
validation. No external source was refreshed in this pass.

## Scientific and operational limitations

1. **Protocol blocker:** the literal shared overlap rule detects a verified
   whole-footprint prior. The current run stopped on that witness. Obtain an
   explicit authorized protocol/registry clarification before any new
   experiment; do not add a local exemption.
2. **No validated candidate:** no file in this session passed all novelty,
   leakage, matched spatial-holdout, and separate-selector gates. The current
   G79B artifact is research-only and must not be submitted.
3. **No artifact-linked organizer receipt or account access:** the 2026-10-22
   public leaderboard observation is not this artifact's score. DrivenData
   submission/account pages require authentication, and no signed-in weekly
   capacity or submission receipt is available in this repository.
4. **Provenance:** SHA-256 pins establish consistency of owner-mirrored input
   bytes, not organizer-origin authentication or redistribution rights.
5. **Scientific scope:** the competition target is fault mapping; a fault
   prediction does not prove a geothermal vent, reservoir temperature,
   permeability, or an economic well.
6. **Hypothesis scope:** at the E1 snapshot, the four ranked ideas in
   `research/hypotheses.md` were prior project work, not four fresh ideas from
   this review. The later G79B list is separately documented in
   `research/hypotheses_g79b.md` and was produced in upstream PR #22, not by this
   review branch.
7. **No slot usage:** no account capacity was read and no submission slot was
   used. Candidate promotion belongs to the separate selector after gates pass.

## Post-sync three-pass review — current G79B-based mainline

### Pass 1 — integrate without changing science

Compared the session branch with the fetched `origin/main` that includes PR #22.
Resolved conflicts by keeping the current upstream G79B run card, its negative
artifact and evidence, and the archived E1 lane. No G79B compute script,
preregistration, raster, holdout result, or uniqueness result was rerun or
retuned in this review. The open protocol uniqueness blocker remains visible.

### Pass 2 — challenge status, score labels, and edge cases

Made site status and manifest flags derive from the verifier's decision rather
than hardcoded booleans; both file links now carry `DO NOT SUBMIT`, and a failed
local download gate renders no download link. The holdout renderer refuses a
score without its `HOLDOUT-DTI` class, evaluator version, withheld-positive
count, and 95% CI. Regression coverage exercises missing metadata and blocked
downloads. Browser QA exposed a 320-pixel horizontal overflow from the longer
audit text; responsive grid/wrapping rules fixed it, and the 21-case browser
review then passed.

### Pass 3 — re-check the user's acceptance criteria

The README still retains the full original prompt. The G79B TIFF is a new,
byte-distinct research artifact and passes local format validation, but the
literal novelty protocol is unresolved (`protocol_unique=false`) and its
preregistered holdout is negative. The machine verdict is download YES / submit
NO, with no human inspection, upload, organizer receipt, slot use, or new
scientific experiment claimed. The executive guide explains the future
submission workflow without authorizing this file.

## Post-sync software verification

Final current-branch checks after integration:

- `scripts/build_site.py`: built **7** evidence-driven pages; verified decision
  rendered as download YES / submit NO.
- `scripts/verify_project.py`: **30/30** integrity/status checks passed,
  including TIFF/ZIP bytes, hashes, range, CRS, dimensions, transform, frozen
  pins, negative holdout evidence, and publication boundaries.
- `scripts/check_site.py`: **7 pages / 112 local links** passed; all pages
  reachable, no third-party assets, and both TIFF/ZIP links visibly say
  **DO NOT SUBMIT**.
- `.venv/bin/pytest -q`: **162 passed**.
- `python -m py_compile scripts/*.py src/gems79/*.py tests/*.py`: passed.
- `node scripts/browser_review.cjs`: **21 page/viewport cases passed** at
  1440, 390, and 320 px, including clipboard, feed, history, and TIFF download;
  downloaded SHA-256 matched
  `16a6e07f97441b6b5431ca24b7481658cdb7b7f59daec0e69070f7d5fc8cf795`.
- `scripts/submission_status.py`: verdict negative, download true, submit false;
  **exit 2 is expected** for this blocked artifact.
- `git diff --check` and `git diff --cached --check`: passed.

The TIFF validator confirms one float32 band, EPSG:32611, shape 3730 × 3292,
exact sample transform, and finite values in [0,1]. These are local software,
format, byte-integrity, and evidence-consistency checks—not organizer
acceptance or a new scientific evaluation.

## Official references retained for manual review

These are links from the repository's source ledger; the links are not evidence
that the pages were refreshed during this session:

- [DrivenData problem description and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official submission-format / rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE Geothermal Data Repository / INGENIOUS entry](https://gdr.openei.org/submissions/1391)
- [Official organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Source claims, evidence classes, and limits](../knowledge/official_sources.json)

## Next work — no new run or slot in this review

The current G79B and prior E1 lanes are closed negative. Do not restart, retune,
or switch lanes. A future run would require explicit owner authorization, a
fresh preregistration, a protocol-owner ruling on the literal novelty blocker,
feature-alone leakage tests, buffered whole-component holdout with full
HOLDOUT-DTI metadata, the shared pre-placement/final-dot uniqueness gates, and
separate selector authorization. No submission slot is selected or used here.
