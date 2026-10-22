# Repository review — session 2747f26f, 2026-10-22

## Executive decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** No new scientific raster was
created, no stopped lane was restarted, and no competition slot was used.
The user's requirement for a newly generated protocol-unique submittable TIFF
remains **unfulfilled**, rather than falsely certified. The existing canonical
research TIFF remains available at the top of README and Pages.

## Pass 1 — inventory, evidence and feasibility

Read the project brief in README, AGENTS, both preregistrations, canonical card,
prior analysis and irregularities. Installed the pinned environment; the initial
system Python had no pytest. Baseline: 230 tests passed.

Re-fetched the pinned public registry witness through the existing shared restore
path and ran `preflight_new_lane.py --restore`: **exit 2**, saved in
[`evidence/preflight_2747f26f.json`](../evidence/preflight_2747f26f.json).
REGISTRY-MEASUREMENT: positive support covers every allowed cell; therefore any
nonempty candidate has forward overlap 1.0, exceeding the protocol's 0.70 limit.
This is a universal obstruction under the *literal* support definition, not
proof that geological discovery is impossible. It cannot be repaired by jitter,
a different scientific hypothesis, another TIFF encoding or an agent's exemption.
The canonical NHR candidate independently fails ordinary-dot comparisons too.

No new lane paragraph was supplied. No scientific hypothesis was implemented.
The existing [four ranked proposals](../research/hypotheses_preflight_a7d092d7.md)
remain conditional research backlog, **not newly invented or newly validated**:
far-field conditional recovery (priority 1, medium-high cost); cross-scale crest
migration (2, medium); magnetic-marker termination plus scarp (3, medium); and
conductivity/gravity discordance (4, low). That table specifies exact layers,
physical signatures, differences from prior code, catalogue-discovery rationale
and named non-fault mimics. These are qualitative priorities, not predicted DTI.
The top proposal cannot proceed until the novelty protocol is prospectively
clarified; it was not tested or selected in this session.

## Pass 2 — reliability defect and fix

**IR-79-68:** `selection_evidence()` already refused malformed measurement data,
but the selector CLI subsequently dereferenced malformed gate/card fields outside
that adapter. Missing files, invalid JSON, null/list cards, and absent/non-dict
gates could produce a traceback instead of a machine-readable refusal.

Added a CLI boundary that reports `selected: false`, `ok_to_submit: false`, and
exit 2 for expected input/read errors. It does not grant gates or replace frozen
measurements with partial evidence. Ordinary refusals now classify nonliteral
boolean gate values as failures, consistent with the existing strict adapter.
Ten regression cases cover missing/malformed cards and gate receipts, asserting
that input and scientific evidence bytes remain unchanged. The scientific shared
evaluator, writer, novelty definition and their hash pins were **not modified**.

## Pass 3 — full requirements recheck

- Full suite: **240 passed**, one upstream Rasterio/Affine deprecation warning.
  These are software test counts, not scientific scores.
- `build_site.py`: seven evidence-driven pages rebuilt, no readiness change.
- `verify_project.py`: all checks passed, including shared pins, reference pins,
  TIFF/ZIP byte identity, decoded format, card/evaluator agreement and refusal.
- `check_site.py`: seven pages, 120 local links checked, all reachable from home.
- Fresh official GitHub reference README review recorded in
  [`evidence/source_review_2747f26f.json`](../evidence/source_review_2747f26f.json),
  pinned to organizer commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`.
- No organizer receipt acquired; historical H33 score 0.2778 remains user-reported.
  No current leaderboard score was freshly verified or projected.
- Prompt already preserved in README; not appended repeatedly.

## Scientific answer and limits

[Existing forensic analysis](nhr_analysis.md) finds H33 is precisely the older
D2.8 dot set minus dots within a 200 m catalogue collar. The metric's maximum
truth-credit versus summed false-positive penalty can favor sparse, nonredundant
placements. That makes pruning a plausible explanation, **not** a demonstrated
causal attribution: the collar is not itself masked and deleted dots could also
credit unmapped faults. Historical score pairs lack artifact-bound organizer
receipts. NHR improved on the matched H33 holdout control, but duplicate failure
and catalogue-proximity distribution shift prevent a claim of leaderboard gain.
This task detects faults potentially indicative of geothermal systems; it does
not certify vents, temperature or reservoir productivity.

## Next-session work, in order

1. Obtain a prospective protocol definition of dots for continuous registry
   priors. Until then, preserve the universal stop; do not silently change it.
2. Under an authorized new definition, preregister one lane, complete surface
   novelty before placement, run each feature canary and buffered holdout, then
   final novelty. Preserve paired controls and spatial confidence intervals.
3. Only after all gates pass may the separate selector act. Weekly slots and
   eligibility require the account-side submission page; this sandbox has no
   authenticated DrivenData access and does not upload files.
4. Original scientific-data provenance is not proved by mirror hashes. Network
   access here is restricted to GitHub and package hosts; USGS, DrivenData, NLR
   and Dropbox could not be freshly authenticated/reviewed. Existing dated source
   reviews are not fresh receipts. External-data ideas are not declared newly
   obtainable merely because a URL exists.

PR creation/merge is an authorized repository operation, not a competition
submission or scientific promotion. Its actual result is reported separately.

### Concurrent-main reconciliation

Main advanced during review. Merged its maintenance changes on the assigned
branch, preserving both independent fixes and renumbering this selector finding
to IR-79-68 because IR-79-67 was allocated concurrently to preflight typing.
