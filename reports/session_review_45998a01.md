# Repository review — 2026-10-22, session 45998a01

## Executive decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**

[Existing research TIFF](../docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif)
· [Submission guide](../docs/executive-summary.html)
· [Fresh validator result](../evidence/validator_45998a01.json)
· [Fresh gate preflight](../evidence/preflight_45998a01.json)

**No new TIFF or new scientific result was generated in this session.** The
request for a newly unique submission remains unmet, not silently replaced by
renaming the old file. No competition slot was selected or used. The supplied
prompt lacks the promised single-method lane paragraph. More decisively, the
hash-verified registry witness covers all allowed cells under the literal
positive-support rule: every nonempty candidate must overlap that witness
completely. The existing shared preflight returned a duplicate/impossibility
refusal before any experiment. No local novelty exemption was introduced.

## Scientific answer: what H33 does and does not establish

The inherited [byte-forensics report](../evidence/h33_forensics.json) identifies
H33 as a subset of D2.8: it removes dots within two grid cells of mapped faults.
Under the shared triangular distance metric, redundant prediction mass can
increase false-positive penalty without a corresponding increase in maximum
truth coverage. Sparse emission and near-catalogue pruning are therefore a
plausible efficiency explanation. **This is not causal proof of the reported
organizer score.** The filename-to-score pairing in the prompt has no
submission-page receipt linking that file hash to that result.

The canonical historical **HOLDOUT-DTI**, evaluator `gems57-pooled-hide-v2`, is:

| Candidate | Seed / withheld positive pixels | HOLDOUT-DTI | 95% CI |
|---|---|---|---|
| G79-THVC | seed 20 / 11,321 | 0.1905 | [0.1741, 0.2069] |
| G79-THVC | seed 30 / 11,342 | 0.1944 | [0.1774, 0.2126] |
| Fold-fair H33 control | seed 20 / 11,321 | 0.0961 | [0.0831, 0.1090] |
| Fold-fair H33 control | seed 30 / 11,342 | 0.0989 | [0.0854, 0.1128] |

Source: canonical `run_card.json`, `holdout_dti.per_seed`. These are inherited
measurements, **not rerun here**, and cannot be compared numerically with the
prompt's private leaderboard thresholds to infer a future score. The report's
older scalar `secondary_holdout_dti` CI differs from its `per_seed` CI; retain
that discrepancy for review rather than inventing a reconciled interval.
Repeated use of the same partitions across many lanes also makes a fresh final
confirmation partition important. There is no new ORGANIZER-CONFIRMED score.

## Pass 1 — inspect, verify the blocker, implement reliability fixes

- Read the preserved request, AGENTS.md, canonical card, required archived
  preregistrations, irregularity log, shared validator and readiness code.
- Installed the pinned verification environment successfully.
- Restored only the single frozen rejection witness via the existing shared
  recovery path; preflight returned the expected blocked exit code.
- Reopened the existing TIFF through both shared format validators. All format
  checks passed, including finite values, range, footprint and reference grid.
  No training, feature generation, final placement or new registry sweep ran.
- Fixed the validator CLI boundary: missing/corrupt TIFFs, invalid ZIP layouts,
  unreadable defaults, and report-write errors now produce a JSON refusal and
  nonzero exit instead of a traceback or printing PASS before a report failure.
  The underlying shared validator/writer/evaluator remain unchanged.
- Added regression tests for corrupt archives, path-containing ZIP members,
  immutable report collisions and sanitized errors. Software byte fixtures and
  mocked PASS values are explicitly not scientific predictions or measurements.
- Prepared [three ranked prospective tests](../research/hypotheses_45998a01.md),
  naming exact layer families, mechanisms, mimics, costs and differences. They
  are not claimed as globally new or experimentally validated.

## Pass 2 — adversarial and publication review

- Found that the initial notice edit hit the inactive promoted-page template;
  removed it there and placed it on the actual negative home page and guide.
- Removed website wording that suggested a manual upload could bypass the
  required automated refusal.
- Corrected README's submission-name length; preserved the canonical filename,
  bytes, short note and all scientific cards.
- Corrected `knowledge/why_h33.md`: local holdout improvement does not prove a
  higher organizer score. Regenerated the dependent analysis page.
- Full initial suite passed: **369 software tests**. Fresh byte/format/evidence
  verification passed; the site checker passed with all pages reachable.

## Pass 3 — requirements and final validation

Final validation is recorded in `evidence/review_45998a01.json` after rebuilding
the site and rerunning tests. Download/submit decisions stay fail-closed and
agree with the canonical card. The existing TIFF and ZIP are unchanged. This
review does not claim new browser-rendering QA, external source freshness,
training reproduction or a new private competition score.

## Sources and access boundaries

| Source | Session observation / limit |
|---|---|
| [Organizer reference solution, pinned commit](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) | GitHub API retrieved README and HEAD. README confirms data placement and both CPU/GPU workflows; it does not authenticate our mirror bytes or results. |
| [Competition problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Original official link retained for review; not fetched in this session. |
| [Competition leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Not freshly observed; conflicting prompt snapshots must not become a new current-score claim. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) / [GDR 1391](https://gdr.openei.org/submissions/1391) | Original provenance links, not freshly fetched. |
| [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Retained source; no fresh account-side capacity or eligibility verification. |
| [Pinned data manifest](../registry/data_manifest.json) | Public owner mirror consistency is not organizer authentication; raw training cache is not present in this fresh checkout. |

Network egress is limited to GitHub and package registries. There is no
DrivenData account session here. No credentials were requested, no new external
dataset was advertised as verified, and no inaccessible page was labeled freshly
read. The original user prompt is already preserved in README; it was not
repeated again.

## Next session, in order

1. Resolve the literal overlap definition prospectively in the shared template,
   with an explicit owner-approved rule and pinned version. Do not adjust a
   completed lane's dot budget, jitter dots or exclude priors to make it pass.
2. Assign one new method lane. Preregister the head × allocator test; restore
   pinned cached inputs; retain per-feature canaries and fold-visible-only
   catalogue derivation. Evaluate against THVC, not merely H33.
3. Investigate the inherited CI discrepancy at the receipt generator, and add a
   fresh confirmation partition to limit adaptive holdout reuse.
4. Only after both surface and final novelty, measured holdout gain, canaries,
   byte/format checks and separate selector approval pass may a slot be used.
   Account-side capacity and organizer acceptance are not locally inferable.

## Merge reconciliation

Main advanced during this review. Merged `origin/main` at `eb3e3d5` on the
assigned session branch, preserving the other reviews and renumbering this
session's appended irregularities after the existing prefix. Incoming PR #70
published extra ETP uploads and scripts without the canonical publication
contract. Preserved those files byte-for-byte outside Pages under
`archive/g79_etp_incoming_45998a01/`; their approximate evaluator and one-raster
novelty comparison are not scientific clearance. No incoming TIFF is offered as
this session's newly generated result. Rebuilt the site and reran verification
on the reconciled tree before merging PR #78.
