# Three-pass repository review — a26add66

Date: 2026-10-22. Session branch: `arena/a26add66-gemsdoe79`.

## Executive outcome

**OK TO DOWNLOAD: YES (inherited research file). OK TO SUBMIT: NO.**
The requested new unique submission is **not achieved**. No scientific lane,
feature canary, holdout evaluation, candidate surface, dot placement, new candidate
TIFF, selector approval or competition upload was performed. No slot was used.
Synthetic malformed rasters written only in pytest temporary directories are
software fixtures, not scientific candidates or published submission artifacts.

The [fresh preflight](../evidence/preflight_a26add66.json) exits 2: one
SHA-verified registry witness covers every allowed cell with positive support.
Every nonempty candidate would have literal forward overlap 1.0, greater than
0.70. This is an obstruction to the requested validation, not a low model score.
No sparse-only exemption, witness deletion, jitter or renamed old TIFF was used.
The prompt also lacks its promised single method paragraph; none was invented.

## Pass 1 — inspect, reproduce, implement

Read the project brief, canonical card, required preregistrations and irregularity
history. Re-read the official problem/metric/format page in both chunks, the first
leaderboard chunk, USGS GeoDAWN release and H33 source page. The
[source ledger](../evidence/source_review_a26add66.json) distinguishes official
claims, observations, owner claims, historical measurements and missing receipts.
This is not a fresh all-sibling-site census or an assertion of line-by-line
verification of every historical report in this large repository.

Found and reproduced four validator defects with failing tests:

1. A ZIP containing one **two-band** TIFF could return PASS: the inner R1 result
   was discarded after checking archive member count.
2. A ZIP containing unreadable TIFF bytes could raise instead of refusing.
3. A missing input could raise before the validator returned a report.
4. GDAL could read a non-GeoTIFF renamed `.tif`; R1 checked band count, not driver.

Fixed once in `src/gems79/portal_spec.py`, version
`gems79-portal-format-v2`. The archive and inner raster checks are combined;
actual driver must be `GTiff`; every outcome has all eight rule results;
missing/unreadable inputs are failures. The shared scientific evaluator, writer,
pins, archived rasters and canonical card were not changed or privately forked.

Restored all thirteen SHA-pinned owner-mirror inputs under ignored `data/raw` with
`restore_data.py --preserve-receipt`. [Current availability evidence](../evidence/runtime_data_status_a26add66.json)
verifies all thirteen hashes. Then `prepare_data.py --reproduce` recovered all
historical E1 cache hashes, preserving its original receipt. This is deterministic
cache recovery, not restarting E1 or creating a new scientific feature surface.
Mirror integrity does not authenticate organizer origin or licenses/semantics.

## Pass 2 — adversarial review and fixes

Added corruption/CRC, missing-template and CLI batch-continuation tests, plus
explicit handling of truncated and invalid deflate streams. CLI batch validation
continues after an invalid file, writes strict JSON, and exits 2 if any input
fails. Removed unnecessary ENVI creation options from its negative-test fixture.

The first whole-suite run found two stale build-time runtime-data assertions after
input restoration. Rebuilding the site regenerated its live availability report;
this was not hidden by changing test expectations. The expanded intermediate
suite then passed **605 tests** before the final four regressions were added.

Homepage wording had said local format PASS despite the official exterior-rule
failure. It now says **Official format FAIL R6**, distinguishing legacy
range/grid checks. The guide explains archive/inner-TIFF validation. Removed an
unjustified assertion on the generated CJX page that its writer could never be
associated with a portal range message. Actual portal rejection causality remains
unknown without the rejected bytes and organizer receipt.

The [official-format recheck](../evidence/portal_validation_a26add66.json) records:

- Official-template mirror: all eight rules PASS.
- Canonical inherited THVC TIFF and identical-inner-TIFF ZIP: FAIL R6 only.
- In-footprint values: finite and within [0,1]; matching CRS/shape/transform.
- Exterior: zero in all 7,111,787 outside cells rather than the required NaN/null.

No stopped TIFF was rewritten solely to obtain new bytes or a different hash.

## Pass 3 — full-request reconciliation

Added landing-page/guide regression tests and rechecked the original requirements.
An initial final sweep caught links to this not-yet-created report; the report was
created before the final rerun rather than suppressing link validation. Final
command outcomes are recorded in
[`verification_a26add66.json`](../evidence/verification_a26add66.json).
Checks include the full Python suite, project verifier, site links/evidence,
JavaScript downloaded-file identity tests, expected blocked submission status,
strict format refusal and whitespace diff checks. The installed package freeze
matched `requirements.lock` exactly; no dependency change was required.

The existing site already provides a direct TIFF/ZIP research download and an
executive-summary submission guide. Their **NO SUBMIT** decision remains automated
and unchanged. No claim is made that a positive performance gate, full novelty
scan on a new raster, or portal acceptance happened. No hidden or local score is
invented. The original full prompt remains in the README; this review adds a
clearly scoped current summary without replacing the preserved brief.

## Why H33 could help, and why a higher score is not demonstrated

The source site explicitly says H33 is **UNSCORED**. Its reported 0.2778 is not
ORGANIZER-CONFIRMED. This review's public-board observation is 0.4413 for
`xiaofanhu`, not our score; the prompt's 0.3195 is a different historical report.

Inherited byte-lineage evidence shows H33 as the D2.8 dot set minus a two-pixel
catalogue collar (44,090 to 37,654 dots, 6,436 deletions). That evidence was not
remeasured here and does not establish the organizer's truth.

From the official metric, with T = weighted TP, F = weighted FP and G = scored
truth count, `FN = G-T` gives:

`DTI = T / (0.2 T + 0.2 F + 0.8 G + epsilon)`.

Removing predictions that lose `a` credit and remove `b` FP cost improves DTI
exactly when `0.2 T b > a (0.2 F + 0.8 G + epsilon)`, for fixed truth/masks and
positive denominators. Redundant predictions can therefore hurt even when
geologically plausible. Deleting useful coverage can instead lower DTI. The
unknown `a` and `b` prohibit attributing a precise score improvement to collar
pruning or promising a higher leaderboard result. See the inherited
[full analysis](../knowledge/h33_review_e4a4422d.md).

## Conditional next research and limitations

[Three ranked, repository-scope unimplemented tests](../research/hypotheses_a26add66.md)
name layers, physical signatures, omission rationale, prior-method differences,
non-fault mimics, falsifiers and qualitative value/cost. No projected score is
provided. They use restored feature families and need no new external source for
an initial test, but their physical interpretations and skill remain unvalidated.

The highest conditional priority is a local magnetic–gravity spectral-admittance
change-point test. It is not executed because the preflight stops before
experimentation. This explicitly leaves the requested top-candidate holdout and
new-TIFF requirements unmet, rather than claiming they passed.

Next steps, in order:

1. Resolve the comparator definition prospectively and consistently across all
   lanes. Do not rescue a finished negative result or discard dense witnesses
   locally. Assign a single method paragraph and preregister a new lane.
2. Preserve a genuinely untouched spatial reserve; repeated historical holdout
   comparisons create selection bias. Run feature-alone canaries, matched pooled
   holdout comparisons with counts/CIs, surface novelty then final-dot novelty.
3. For an independently eligible future candidate, fix the shared writer once
   against the official NaN-exterior convention and update its tests/pins with
   documented provenance. Do not infer portal acceptance from local validation.
4. Only the separate selector can consider a real slot after every gate passes;
   account eligibility, remaining capacity and artifact-linked receipts remain
   account-side conditions. No DrivenData login or private labels were available.
5. Runtime/cache inputs are intentionally ignored and may need restoration in a
   fresh workspace; current local availability is not permanent tracked data.
6. GitHub Pages already exists. At review time its API reported legacy `main:/`
   publishing. Local build success is not proof this exact revision is live;
   keep deployment and research evidence separate.

The terminal [JSON card](../evidence/run_card_a26add66.json) is negative and uses
nulls for unmeasured candidate quantities. Core values are served by not spending
a slot on an impossible novelty gate, fixing an actual automated-validation bug,
and stating unmet requirements rather than manufacturing a success.
