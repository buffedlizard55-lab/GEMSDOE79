# Three-pass repository review — session `a23a7367`

Date: **2026-10-22 UTC**. Branch: `arena/a23a7367-gemsdoe79`.
Scientific verdict remains **negative / DO NOT SUBMIT**. This document records a
repository and release-safety review; it is not a new experiment, score, upload,
or selection of a weekly submission slot.

## Executive decision

The repository already contains one E1 research GeoTIFF. It is download-enabled
for research use, but its run card and automatic status checker both say
**OK TO SUBMIT: NO**. It is byte-distinct from the verified registry bytes, but
it is **not protocol-unique** and does not pass the literal novelty gate. I did
not generate a new TIFF, change the candidate, place dots, run a new holdout,
or upload anything: the preregistered lane had already stopped negative, and
its shared universal-overlap witness blocks every nonempty candidate under the
current literal rule. A fresh filename or re-serialization would not fix that.

The root `run_card.json` retains null primary HOLDOUT-DTI and confidence
interval fields because the authorized run stopped before scoring. A separate,
previously stored post-stop diagnostic is not a substitute for the run card or a
promotion receipt. There is no `ORGANIZER-CONFIRMED` submission score in this
repository. The prompt's `0.2778` is an **unverified historical filename/score
report**, not proof that those exact TIFF bytes earned the value. The byte-level
analysis in `knowledge/why_h33.md` shows that the H33 raster is a pruned subset
of D2.8; reducing redundant or false-positive emissions is a plausible metric
mechanism, but the bytes alone cannot establish why a remote score changed.

The existing research download is not a newly validated entry for this session.
The current decision is automated, does not require a human inspector, and
remains clearly **DO NOT SUBMIT** on the home and executive-summary pages.

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
- Source freshness limitation: the latest stored fetch attempt in
  `docs/evidence/source_health.json` is dated 2026-10-21 and records failed
  requests for the monitored sources. This review did not relabel that feed as
  current; the prompt's conflicting descriptions of the current high are recorded
  as IR-79-39. No fresh leaderboard observation is claimed. The official-source
  ledger records the source URLs, prior review date and claim limits.

## Pass 3 — verification against the request

The persistent brief is still present in `README.md`; the submission decision
is prominent; the executive summary explains how a future **approved** TIFF
would be submitted; the automatic status decision requires no human
inspection; local validation checks the downloaded TIFF bytes, range, CRS,
shape and transform; and no slot is selected or consumed. The brief's request
for a **new protocol-unique, promotable TIFF cannot be satisfied** under the
mandatory stop rule and current registry definition. We do not relabel the
existing negative research surface as a competition submission.

Software-only verification after rebuilding the site:

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
2. **No validated candidate:** no new file in this session passed uniqueness,
   leakage, matched spatial holdout, or separate selection. The only file
   available for download is research-only and must not be submitted.
3. **No current leaderboard or account receipt:** the latest saved source
   observation is stale, the DrivenData account/submission pages require
   authentication, and no signed-in weekly-capacity or organizer receipt is
   available in this repository.
4. **Provenance:** SHA-256 pins establish consistency of owner-mirrored input
   bytes, not organizer-origin authentication or redistribution rights.
5. **Scientific scope:** the competition target is fault mapping; a fault
   prediction does not prove a geothermal vent, reservoir temperature,
   permeability, or an economic well.
6. **Hypothesis scope:** the four ranked ideas in `research/hypotheses.md` are
   prior project work, not four freshly invented ideas in this review. The
   request's referenced single method paragraph is absent from the preserved
   prompt, so the active lane remains a recorded autonomous declaration, not a
   user-assigned method.
7. **No slot usage:** no account capacity was read and no submission slot was
   used. Candidate promotion belongs to the separate selector after gates pass.

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

## Next work

First obtain the authorized protocol decision for the universal-overlap
witness and, through an authorized account workflow, current submission-page
capacity and receipt access. Then re-preregister a lane explicitly, measure
each feature alone on the permitted spatially blocked holdout, compare against a
reproduced incumbent with paired spatial intervals, run the shared surface and
final-dot novelty checks, and let the separate selector decide whether a slot
is justified. Until those prerequisites are met, the correct result is a
negative decision—not a newly named or copied TIFF.
