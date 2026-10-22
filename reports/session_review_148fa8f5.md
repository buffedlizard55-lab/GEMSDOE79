# Three-pass repository review — 148fa8f5, 2026-10-22

## Outcome first

**OK TO DOWNLOAD inherited research TIFF: YES. OK TO SUBMIT: NO.**
**No new TIFF was generated.** This does not satisfy the requested new approved
submission; it records why that cannot honestly be achieved under the active
protocol. No experiment, feature canary, holdout, candidate surface, placement,
selector action, organizer upload or slot use occurred.

## Pass 1 — inspect, reproduce, implement

Read the project contract, README and archived prompt, canonical card, stopped
lane preregistrations, irregularity ledger, H33 analysis, site generator,
shared preflight and format validators. Preserved the historical scientific
cards and raster bytes. Current fresh receipts:

- [Runtime inventory](../evidence/runtime_data_status_148fa8f5.json): none of the
  thirteen pinned inputs exists under `data/raw`. Historical restore receipt
  metadata matches the manifest, but is not present-day data availability.
- [Preflight](../evidence/preflight_148fa8f5.json), restored and hash-verified:
  exit 2, `start_new_lane:false`. Witness SHA-256
  `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`.
  Positive support covers the entire allowed domain. Thus every nonempty dot
  set has forward overlap 1.0, exceeding 0.70. This is a mathematical rejection,
  not a measured candidate score or a full current registry census.
- [Official-reference source check](../evidence/source_review_148fa8f5.json):
  retrieved the organizer reference README at an immutable GitHub commit. CPU
  execution is supported; a GPU is faster, not an absolute prerequisite.
  Other official hosts are outside this sandbox's allowlist; no fresh
  DrivenData/USGS/GDR/NLR/Dropbox verification is claimed.
- [Three ranked proposals](../research/hypotheses_148fa8f5.md): deferred backlog,
  not new experiments. The new-lane paragraph is absent, and the inherited
  canonical lane has exhausted its experiment budget. Neither permits a restart.

Found a software defect in `src/gems79/portal_spec.py`: ZIP validation removed
its inner R1 result. A multi-band raster with valid first-band data therefore
could pass when archived even though the identical bare TIFF failed. Fixed
once in the existing shared project validator, not a lane-local fork. R1 now
combines archive layout and inner single-band GeoTIFF checks; the raster driver
must actually be GTiff. Missing files/templates and corrupt TIFF members now
return structured fail-closed reports instead of escaping with tracebacks.
No shared scientific evaluator/writer, template pins or raster bytes changed.

## Pass 2 — adversarial and regression checks

Added six small software-fixture cases (not competition predictions): multi-band
ZIP parity, valid one-band ZIP, missing input, corrupt archived TIFF, missing
template and VRT disguised as `.tif`. Tests use temporary directories only.

- Targeted format tests: **20 passed**.
- Full suite: **603 passed**.
- Missing-input CLI: expected exit **2**, JSON refusal, no traceback.
- [Inherited-file strict format check](../evidence/portal_format_148fa8f5.json):
  R1–R5, R7–R8 pass; R6 fails because exterior pixels are zero instead of NaN.
  This differs from the older shared writer's all-finite policy. Do not call
  that legacy PASS full official-contract conformity. The actual rejected
  upload/portal receipt is absent; the previous range error's cause is unknown.

## Why H33 may have helped, without claiming a score cause

The [pinned forensic analysis](../knowledge/h33_review_e4a4422d.md) finds H33 is
D2.8 with nearby off-catalogue pixels removed by a two-pixel collar. Those are
not exact known-fault pixels, which are already excluded from scoring.
Conditional on retaining recovery credit while reducing false prediction mass,
thinning raises DTI. With credit T, false mass F and truth mass G, the metric
is `T / (0.2 T + 0.2 F + 0.8 G)` (ignoring numerical epsilon). Removing credit a
and false mass b helps only if `0.2 T b > a (0.2 F + 0.8 G)`. Hidden truth is
unavailable, so this is an explanation of a possible mechanism, not proof of
why any organizer score occurred. Blind thinning need not improve performance.

H33's user-reported **0.2778 is not ORGANIZER-CONFIRMED** without an artifact-linked
submission-page receipt. The historical public-leader observation **0.4413** is
not this project's score; **0.3195** is another user-provided benchmark, not a
fresh leaderboard measurement. We have no new HOLDOUT-DTI or leaderboard result
and cannot substantiate a higher score. Predicting mapped/hidden faults is not
proof of geothermal vents, heat, permeability or commercial production.

## Pass 3 — publication, scope and original-request review

Rechecked project integrity, all tests and generated-site links after the fix.
The landing page and executive summary now link this audit and explicitly
separate numeric-range validity from strict exterior-mask conformity. Research
downloads remain available; submission approval remains false. The original
full prompt remains in README; this review is linked at its beginning rather
than appending another duplicate prompt.

No manual inspection is needed to see that submission is blocked. But software
cannot observe a signed-in account's remaining slots or manufacture an organizer
receipt. No new approved/unique TIFF, higher score, full external-source census,
or complete fresh scientific validation is claimed.

## Next steps and limitations

1. Resolve the literal novelty comparator prospectively for all lanes. The
   current full-support witness makes any nonempty submission impossible; do
   not exempt it locally, jitter dots or change the threshold after results.
2. Specify a single method paragraph and register a new lane only after that
   protocol decision. Do not revive the stopped lanes or exceed their budgets.
3. Restore pinned runtime inputs using the existing restoration tool while
   preserving historical receipts. Hash consistency is not official-origin or
   redistribution-license proof. No large data restore was needed for this
   rejection-only software review.
4. Reconcile the shared writer's exterior policy against the official template
   and rules in one prospective shared change, without mutating old artifacts.
5. Run canaries and the matched buffered holdout before any real selector step.
   The requested new approved TIFF remains unfulfilled, not silently waived.

## Review run card

See [the single JSON card](../evidence/run_card_148fa8f5.json). Null fields mean
not measured, never a zero score. Repository/software test counts and novelty
coverage are not competition scores.

### Concurrent-main synchronization

While PR #129 was open, main advanced through PRs #127 and #128. Merged
`origin/main` into the fixed session branch (no branch switch). Resolved only
generated-site conflicts by rebuilding with `scripts/build_site.py`; retained
concurrent history and research artifacts. Main's new `artifacts/ventprox/` TIFF
and its generator were produced by a different session, not this review; their
existence does not change this review's no-new-TIFF outcome or grant submission
approval. The generator's filename describes it as DO-NOT-SUBMIT. Rechecked the
merged tree before merge; no scientific claim is inferred from those new bytes.
