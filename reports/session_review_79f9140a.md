# Follow-up repository review — 2026-10-21

Session branch: `arena/79f9140a-gemsdoe79`. Starting commit:
`350e40dc3c2f325b82b8deb3d613edd2f6a34db9`. Integrated the concurrently merged
review PR #8 (`0f19e30`) on this same branch without restarting science.
Historical branch names in immutable receipts remain historical provenance.

## Executive decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. Verdict: negative.**

The existing TIFF is local-format-valid negative-result evidence, not a
protocol-unique competition submission. This session did not generate a new
raster, invent a different lane, run canaries/holdout, or use a submission slot.
The stronger request for a promotable unique TIFF **remains unsatisfied** because
it conflicts with the mandatory duplicate stop under the current shared rule.
No human inspector is needed to compute the rejection.

## Pass 1 — inspect, independently verify the blocker, implement repairs

Read the project brief, run card, preregistration, irregularities, shared novelty
implementation, status/validation code and workflows. The inherited experiment
state is explicitly stopped negative, not waiting for data placement. The four
ranked hypotheses in [research/hypotheses.md](../research/hypotheses.md) remain
preregistered; proposing a replacement lane or trying another surface after the
stop would violate the prompt. There is no measured basis for ranking new
hypotheses by numerical DTI gain.

Installed the exact `requirements.lock` in a fresh Python 3.11 environment.
The inherited software suite passed before changes (71 tests). These are
software counts, **not HOLDOUT-DTI**.

Added `scripts/verify_overlap_witness.py` and executed:

```bash
.venv/bin/python scripts/verify_overlap_witness.py --restore \
  --report evidence/session_witness_review.json
```

Only one frozen Git blob was restored, not the historical 992-file inventory.
The new script checks all shared-module pins, the two reference input pins,
SHA-256/Git-blob/size identity of the witness, and exact grid alignment, then
calls the **unchanged shared** `saturation_certificate`. Every measured field
matches the original certificate. The report refuses to overwrite an existing
output. No original scientific card, state, preregistration, certificate,
artifact or registry receipt was rewritten.

**REGISTRY-MEASUREMENTS (not performance scores):** the witness is positive on
5,167,373 footprint cells. It leaves zero of 5,106,385 allowed cells outside its
3 px halo. Thus any nonempty allowed dot set has forward overlap 1.0, above the
0.70 limit. A new geological transform or random jitter cannot change that fact.
This confirms rejection; it does not establish a complete registry audit.

Fixed the readiness CLI to return structured JSON with a negative decision and
exit 2 on missing cards, invalid JSON, missing/corrupt artifacts, validation
errors and escaping paths. It rejects duplicate JSON keys and nonfinite JSON
constants instead of silently interpreting ambiguous evidence. It reports only
error stage/class, not potentially sensitive exception text. The core decision
helper rejects non-object cards, nonhex digests and oversized numeric fields
without crashing. No change to scientific thresholds or shared modules.

## Pass 2 — regression, edge cases and corrections

Added regression fixtures for malformed cards, path traversal/symlink escape,
missing/corrupt TIFFs, validation exceptions, malformed digests, oversized
holdout integers and the CLI exit contract. Added tiny **synthetic software
fixtures** for witness remeasurement, immutable evidence, changed bytes,
modified shared modules, mismatched certificates and offline missing-witness
rejection. They do not generate competition results or geological evidence.

The first expanded run caught a newly linked review document before it existed:
102 passed / 1 failed. Created this report rather than weakening the README
link check. Removed a fixture-only affine deprecation warning by constructing
the test transform directly. This failed intermediate run is not called a pass.

Reviewed the new certificate command for accidental experiment restart and
receipt overwrite: it performs neither. It requires an explicit `--restore`
before networking and never expands or rewrites the frozen registry. Verified
that the status CLI does not reuse stale success after an exception. Adjusted
`AGENTS.md` to defer to current session metadata instead of hard-coding another
session's branch name.

## Pass 3 — original-request acceptance and release

- The full original user prompt remains in README, including its repeated
  requirements and contradictory historical leaderboard statements.
- The top download and executive-summary guide remain explicit about **DO NOT
  SUBMIT**. The guide now links the independently recovered witness report.
- No downloaded prior was renamed as new. The existing TIFF/ZIP and all original
  scientific JSON and shared source bytes remain unchanged.
- No scientific result is trusted without canaries: none were run and none are
  claimed. **HOLDOUT-DTI** remains unmeasured: evaluator
  `gems57-pooled-hide-v2`, withheld positives `null`, DTI `null`, 95% CI `null`.
  No current-best holdout improvement is established.
- No artifact-linked submission-page receipt exists here. No
  **ORGANIZER-CONFIRMED** artifact score is claimed. No projection is a score.
- No weekly slot was selected or spent. No login bypass or credential request.
- No fabricated free external source or quantitative geological novelty claim.
  The fresh outbound data access was to GitHub's immutable prior blob.
- Final test, format, site/browser and PR/merge results are recorded below after
  execution; a local test pass is not organizer acceptance.

## Answer about H33 — evidence and limits

The existing byte-level [forensics](../evidence/h33_forensics.json) record H33 as
exactly the earlier D2.8 dot set with 6,436 catalogue-near pixels removed
(44,090 to 37,654). This session reviewed those records but did **not** claim a
new download or new forensic experiment. The maximum-cover DTI mechanism makes
sparse, nonredundant coverage a plausible explanation, not proof of a hidden
score gain. The filename-to-score pairing supplied by the prompt is not an
organizer receipt. See [full scientific argument](../knowledge/why_h33.md).
No evidence justifies predicting this lane will exceed that reported score.

Official links for manual review (access scope kept explicit):

- [DrivenData task and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
  Prior claim ledger only; not freshly reachable within this session's sandbox
  host allowlist. No new leaderboard value is asserted.
- [Official organizer reference README, pinned commit](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md).
  Fresh GitHub API read confirms this is a reference baseline and provides
  CPU-only as well as GPU setup. It does not verify E1 performance, new faults,
  organizer-origin identity of mirrors, or the claim that a GPU is mandatory.
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).
  Prior attributed scientific source, not a new successful binary download.
- [Actual registry witness source](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/main/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif).
  This is an owner mirror, **not an official organizer prediction**. Its immutable
  Git blob and SHA-256, not the changing main URL, identify the recovered bytes.
- [Source/claim ledger](../knowledge/official_sources.json) preserves original
  review dates and access limitations. Reachability is not claim verification.

## Remaining blockers and next authorized work

1. Obtain an explicit rule/registry clarification on continuous positive-support
   priors. This is a protocol conflict, not a need for visual human inspection;
   the project must not invent an exemption.
2. Only after an authorized protocol and lane exist: run feature-alone canaries,
   buffered whole-segment hide-and-recover, matched incumbent reproduction and
   paired spatial intervals. A negative run remains a deliverable.
3. Independently authenticate source inputs and obtain account submission-page
   capacity/selector evidence through an authorized workflow. Only the separate
   selector may allocate a slot. No secrets belong in chat or this repository.
4. The active site is static: it exposes a real downloadable TIFF and automatic
   rejection, not an in-browser scientific training service. Its daily feed
   checks public-source health, not continuously updated scientific validity.
5. Network access here is restricted to GitHub/package hosts; DrivenData,
   USGS, Dropbox and the public Pages hostname cannot be freshly fetched with
   direct sandbox requests. GitHub-hosted CI can perform its own public checks.
   Report actual deployment outcomes, not a guessed successful publication.

## Final execution and release record

- Fresh pinned Python environment: **105 tests passed in 3.07 s**, with no
  warnings in that final run. These are software tests, not HOLDOUT-DTI.
- Static rebuild: seven primary pages, 104 local links, two compatibility
  redirects, all pages reachable, no third-party browser assets; checks passed.
- Real Chromium review: 21 viewport/page cases passed, clipboard/filter/feed and
  both redirects passed, no browser/HTTP errors. Actual downloaded TIFF SHA-256
  matches the frozen card. New record: `evidence/browser_review.json`.
- Reopened TIFF and ZIP/reference/receipt verification passed; readiness CLI
  returned JSON `ok_to_download=true`, `ok_to_submit=false`, exit **2**.
- The witness command passed again in offline mode; original scientific cards,
  registry, state, reference inputs, TIFF/ZIP and all vendored shared modules
  have no diff from integrated main. The 24 MB restored witness stays ignored.
- `git diff --check` passed. The website preview serves only `docs/` on
  `0.0.0.0:8080`, not private data or the repository root.
- PR/check/merge/deployment observations are appended to the release PR after
  execution. This report does not predict that an unrun remote check will pass.
