# Repository review — 2026-10-22

Branch: `arena/05ad3d4c-gemsdoe79`; starting commit `5e3067e186f3dcf7f511e8c81a44f7b32a7a0268`.

## Executive outcome

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. Verdict: negative.**

The existing TIFF is newly computed historical E1 evidence, not a new artifact
created during this review and not protocol-unique. No new raster, scientific
experiment, placement, training, holdout evaluation, or competition upload was
performed here. The original prompt remains in README. Its request for a
promotable unique submission cannot be fulfilled while also honoring the
mandatory stop under the unchanged literal registry support rule.

## Pass 1 — audit and implementation

Reviewed README/project contract, frozen run card/preregistration, irregularities,
ranked hypotheses, status implementation, workflows and earlier review records.
The four preregistered hypotheses already cover the assigned offset lane;
proposing or implementing a different lane after a duplicate would violate the
stop, not advance this run.

Fixed a local readiness defect: `leakage_canary.passed=true` alone previously
cleared the canary gate even if AUC was absent, nonfinite, below the symmetric
AUC minimum, or above the mandatory threshold. Now require a numeric maximum
symmetric AUC in [0.5,0.90], the fixed numerical threshold 0.90, and a positive
integer feature count. This is a necessary consistency check, not independent
receipt authentication or proof all required features/folds were evaluated.
No shared template, evaluator or writer was modified.

Removed the hardcoded historical branch from AGENTS.md so later sessions follow
their actual Arena metadata. Updated the H33 explanation and generated analysis
page to distinguish original stopped-run nulls from the later recorded diagnostic.

## Pass 2 — independent verification and edge cases

- Installed the pinned Python requirements in an ignored virtual environment.
- **128 software tests passed**, including new missing/invalid/boolean/string,
  NaN/infinity, oversized-integer and threshold-boundary canary cases.
- Offline project verification: every check passed, including shared-template
  pins, reference-input hashes, TIFF/ZIP/receipt identity, exact reference grid,
  finite values in [0,1], and automatic negative readiness.
- Restored exactly one frozen registry witness from its immutable GitHub blob;
  fresh shared-tool measurement agrees with the historical certificate. See
  [`evidence/session_witness_05ad3d4c.json`](../evidence/session_witness_05ad3d4c.json).
  It has positive support over the entire footprint and leaves zero allowed
  cells uncovered by the 3-pixel halo. Every nonempty allowed candidate therefore
  fails the literal overlap gate. This is not a fresh full-registry scan.
- Rebuilt the seven-page site; 107 local links passed, two compatibility
  redirects passed, no external browser assets.
- Actual Chromium review: 21 page/viewport cases passed, clipboard/filter/feed
  and redirect behavior passed, actual downloaded TIFF hash matched. See
  [`evidence/browser_review.json`](../evidence/browser_review.json).
- Readiness CLI returned the expected exit 2 and JSON download=true/submit=false.

## Pass 3 — requirements and scientific claims

Cross-checked the newly documented diagnostic table against the JSON evidence,
not a projection. Both entries are **historical HOLDOUT-DTI**, evaluator
`gems57-pooled-hide-v2`, not freshly recomputed scores:

| Seed | Withheld positives | E1 DTI, 95% CI | Fold-fair H33 DTI, 95% CI |
|---|---:|---|---|
| 20 | 11,321 | 0.0474 [0.0390,0.0552] | 0.0961 [0.0827,0.1091] |
| 30 | 11,342 | 0.0466 [0.0388,0.0543] | 0.0989 [0.0835,0.1122] |

Source: [`evidence/post_stop_diagnostic.json`](../evidence/post_stop_diagnostic.json).
The official E1 card remains frozen with null holdout values. These diagnostic
results do not authorize bypassing the duplicate stop. There is no supported
claim of beating the reported H33 private score or any current leaderboard best.
The two seeds are not pooled here because overlapping hidden sets would need
explicit treatment.

The historical H33 forensic evidence shows deletion of 6,436 catalogue-near
points from D2.8's 44,090 to produce 37,654. Less redundant false-positive mass
is a plausible metric mechanism, not causal proof of the reported score.

### Source boundary and links

Fresh GitHub API access confirmed the organizer reference repository exists and
its main commit was `aebe92f7c8a990f0e3443451b7a825d9afd6336b`:
[official reference](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b).
This does not authenticate the mirrored competition inputs or a submission.

[Competition problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
[official data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/),
and [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
remain review links; they were **not freshly fetched in this session** because
sandbox network access is restricted to GitHub/package hosts. Historical source
observations retain their original dates. No current leaderboard/capacity or
ORGANIZER-CONFIRMED artifact score is asserted.

### Remaining requirements and next work

1. A protocol-owner clarification of continuous registry support and an explicit
   authorized lane are necessary before more science. Do not create an exemption
   or spend a weekly slot to bypass this conflict.
2. E1's recorded diagnostic fails matched controls; novelty clarification alone
   would not justify promoting it. A future authorized method must beat a
   reproduced matched incumbent with paired spatial intervals and canaries.
3. Source checksums need independent organizer authentication. Weekly capacity
   and selector approval need actual authorized account evidence; neither is
   available here. No secrets are requested or stored.
4. The site supplies a real research TIFF and automatic rejection, not an
   approved candidate or in-browser training service. The daily source feed is
   reachability monitoring, not continuous scientific validation.
5. Fault predictions are not discoveries of geothermal vents or productive wells.
6. Parallel PRs #12 and #13 were visible during review. They were not merged or
   treated as authorization to change this lane. Only this session's own PR is
   in scope for the requested merge; retain explicit provenance for other work.

The final request is **partially satisfied**, not declared complete: review,
software hardening, download and automated decision are verified; a promotable
unique competition TIFF is blocked. Negative results remain deliverables.

## Actual release outcome and concurrent-main conflict

Opened [PR #15](https://github.com/buffedlizard55-lab/GEMSDOE79/pull/15) from this
session branch. While review ran, PR #13 merged at 00:48:20 UTC and PR #12 at
00:49:31 UTC on 2026-10-22. Main advanced to
`3d386a3f0c6f89c31e33a656dee8851cee64753d`.
The earlier statement that those PRs were visible describes the initial audit;
it is not their final state.

Fetched main and attempted integration on this branch. It conflicted in README
and AGENTS. The concurrent main also changes `vendor/gems57/uniqueness.py` and
replaces the main README with a different H79-CSPT lane and a promotion claim.
Those changes were **not audited or adopted** here. Aborted the merge, preserving
this review's tested lane and receipts rather than overwriting concurrent work
or silently using different shared-tool bytes.

Explicit `gh pr merge 15 --merge` returned exit 1: GitHub cannot create a clean
merge commit. No auto-merge or force overwrite was used. No checks were reported
for PR #15 at that observation. Local test results apply to this branch's commit,
not to concurrent main or a deployed site. The PR remains open; reconciliation
of scientific lane/status/shared-tool conflicts is required before a safe merge.
The local preview serves this reviewed branch's `docs/`, not the new main site.
