# Three-pass review — session 84124ba0

## Outcome

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The existing download is inherited
research, not a unique new candidate. No TIFF was generated, copied, renamed or
uploaded in this session. No scientific experiment or competition slot was used.
The user's unique-submission requirement remains **unmet**, rather than bypassed.

The independent [preflight](../evidence/preflight_84124ba0.json) returned exit 2.
The [remeasurement](../evidence/review_84124ba0/witness.json) verifies the frozen
witness's bytes and confirms its positive support covers every allowed cell.
Under the existing literal definition, every nonempty eligible prediction set
therefore overlaps it by 1.0, above the 0.70 limit. This is a deterministic
registry measurement, not a score, and does not require trying three models.
An all-zero raster or new filename would not solve the scientific requirement.
No delimited method assignment appears in this session's prompt.

## Pass 1 — inspect and reproduce

- Read the README brief, canonical card, shared modules, archived-lane contracts,
  H33 analysis and prior research backlog. Preserve their stopped status.
- Installed the exact dependency lock. Baseline suite: **477 passed**.
- Restored the two pinned reference files through existing GitHub-mirror recovery
  with `--preserve-receipt`; these are owner mirrors, not authenticated organizer
  downloads. Recovered the single frozen witness using existing shared recovery.
- Re-ran project verification, automated submission status and separate selector.
  Selector refused with three failed uniqueness gates and left the card unchanged.
- Reopened and validated the inherited TIFF: finite values, range [0,1], single
  band, CRS/shape/transform matching the pinned sample. See the new
  [local validator receipt](../evidence/review_84124ba0/validator.json). This does
  not diagnose the unknown previously rejected file or prove portal acceptance.

## Pass 2 — defect and edge-case review

Found a concrete provenance defect: `verify_overlap_witness.py` iterated over
whatever pins existed, without requiring the two reference entries. Missing
entries could silently omit hash checks; a changed destination could hash a
file other than the one `load_grid` actually reads. The template-pin loop had
an analogous missing-entry weakness for grid and uniqueness modules.

Fixed the review wrapper once: require exactly one pin for each reference and
both directly used shared modules; require the reference filenames actually
loaded. Add missing, duplicate, malformed-container and alternate/path-traversal
destination regression tests. Synthetic fixtures are software tests only.
No shared scientific module, hash pin, evaluator, writer or threshold changed.
This strengthens rejection evidence; the defect was not a demonstrated upload
approval bypass. Also corrected preflight help text: it never returns exit 0.

Full suite after changes: **492 passed**. Static site build/check: **7 pages,
128 local links, passed**, with full failed novelty gates still visible. These
are software QA counts, not HOLDOUT-DTI.

## Pass 3 — requirements and evidence review

- Canonical TIFF/ZIP, card and scientific receipts remain unchanged. The latest
  [review card](../evidence/review_84124ba0/run_card.json) uses null for unrun
  holdout and ungenerated raster, not a fabricated zero score.
- The prompt remains in README; its new validation-gate wording is recorded as
  a session addendum rather than silently replacing historical prompt bytes.
- Existing executive-summary instructions and direct download links remain
  available. Automated refusal requires no human scientific inspection. Account
  eligibility/capacity and organizer acceptance are not locally observable.
- Reviewed the official reference README at a pinned upstream commit: it supports
  CPU-only execution, so a categorical GPU requirement is not established. It
  does not prove this repository's stopped pipeline is ready to restart. See
  [source ledger](../evidence/review_84124ba0/sources.json).
- No fresh full-family inventory, official leaderboard receipt, external binary
  acquisition, vent discovery or hidden-test improvement is claimed. Direct
  network access here is limited to GitHub/package hosts. Prior official-source
  readings remain dated evidence, not newly refreshed verification.

## H33: defensible scientific answer

The [existing byte analysis](../knowledge/h33_review_e4a4422d.md) records H33 as
D2.8 with off-catalogue dots within two pixels of the known catalogue removed.
The useful conditional mechanism is that the distance-tolerant metric takes
maximum local recovery credit but accumulates false-positive cost. Removing
redundant predictions can improve efficiency; removing predictions that uniquely
recover a fault can worsen it. Hidden truth is unavailable, so this cannot prove
why an organizer assigned the user-reported result. The owner page fetched via
GitHub still contains UNSCORED. No historical reported number is upgraded to
ORGANIZER-CONFIRMED. A higher leaderboard result is possible, not demonstrated
or predictable from this audit.

## Ranked untried research and next steps

Do not open another lane or retry stopped candidates while the universal blocker
holds. Continue the existing [four unimplemented proposals](../research/hypotheses_e4a4422d.md),
not four extra experiments:

1. **Contact-junction persistence** — RTP and isostatic gravity; multi-scale ridge
   director winding plus signed contrasts. Potential buried intersections rather
   than catalogue continuations; pluton margins are the nuisance control.
   Moderate, uncertain incremental value; moderate cost.
2. **Bilateral lithology change points** — potential fields plus rank-only
   radiometrics; along-contact changes in opposite-flank joint distributions.
   Potential offset buried contacts; depositional facies are a mimic.
   Low/moderate, uncertain value; moderate/high cost.
3. **Relief-screened saddles** — detrended elevation, slope and gravity;
   multi-scale saddles with crossing gravity contrasts. Potential concealed basin
   connectors; stream capture is a mimic. Low/uncertain value; moderate cost.
4. **Paired heat-flow residuals** — USGS heat-flow well residuals, DOI
   [10.5066/P9BZPVUC](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28).
   Paired recharge/upflow signals may indicate buried fluid paths; ordinary
   groundwater circulation is a mimic. Unquantified value; high acquisition cost.
   **Not currently viable:** metadata was previously inspected but the binary
   dataset/schema/coverage were not acquired here. Do not infer availability
   from a landing page or substitute integrated conductance for resistivity.

These are prior deferred proposals, not newly invented or evaluated in this
session. Their full layer definitions and differences from implemented lanes
are in the linked backlog. No numerical improvement prediction is justified.
Before any future implementation: prospective shared protocol/lane definition,
complete registry scope, untouched spatial validation partition, feature-alone
canaries, matched incumbent holdout with confidence intervals, both novelty
stages, local format validation, then a separate selector. Do not change gates
post hoc to rescue this or any prior file.

**Maximize P(Win):** preserve scarce slots, not a known duplicate.
**Own the Outcome:** deliver the measured negative result and fix the audit bug,
while explicitly retaining the unmet new-TIFF requirement.

## Concurrent-main reconciliation

PR #97 initially conflicted with concurrently merged review notes. Merged
`origin/main` at `7f5d6e3` into the assigned session branch, preserved incoming
reports/tools, and assigned this session's irregularities the next unused IDs
IR-79-173 and IR-79-174. Rebuilt the site; the combined suite passes **495 tests**.
The canonical scientific files and refusal remain unchanged.
