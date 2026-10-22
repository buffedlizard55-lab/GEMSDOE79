# Three-pass review — 2026-10-22, branch arena/a7d092d7-gemsdoe79

## Pass 1: repo and evidence

Read the complete README (including original request), active and archived
preregistrations, run card, irregularities, code, source ledger and verifier.
Confirmed from the [organizer problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
that the task is **mapping previously unlisted faults**, not directly finding
vents; the 100 m EPSG:32611 single-band float32 [0,1] format and the 300 m
triangular Tversky kernel (alpha .2, beta .8) match the repo's metric assumptions.
[Organizer data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
redirected to sign-in on this fetch, so mirrored hashes are *not* organizer
authentication. The official reference implementation is
[DrivenData's GitHub repository](https://github.com/drivendataorg/gems-prize-reference-solution).

Re-restored and SHA-256/Git-blob/size-verified **one** 17GEMSDOE historical
registry TIFF (no new experimental data). Shared `saturation_certificate`
reproduced the frozen certificate field-for-field, excluding provenance-only
path and URL: 5,167,373 positive footprint pixels, all 5,106,385 allowed
candidate cells covered, witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`.
[Measurement](../evidence/witness_review_20261022_a7d092d7.json) and
[original certificate](../evidence/universal_overlap_certificate.json).
This proves any nonempty candidate has overlap 1.0 > 0.70 under **literal**
positive-support dots. Preflight exit 2
([JSON](../evidence/new_lane_preflight_a7d092d7.json)); stopped without
implementing an experimental surface, holdout, new submission TIFF or upload.
The prior canonical research TIFF remains downloadable and negatively gated.

Prepared four qualitative [geological hypotheses](../research/hypotheses_preflight_a7d092d7.md)
for a future separately preregistered lane, identifying layers, signatures,
missing-catalogue rationale, implementation differences and mimics. None is a
measured DTI or an approved experiment. Did not copy another submission.

## Pass 2: bug and assumption review

- Clean `pip install -r requirements.lock; pytest` originally failed collection
  because `src/gems79b/features.py` imports `skimage.filters.sato` while
  scikit-image was missing. Pinned `scikit-image==0.26.0` and its transitive
  dependencies, and added its source range to `requirements.txt`.
- Website claimed any >70% halo coverage logically blocks *every* map. This
  is false: a map can deliberately select the uncovered <30%. Replaced that
  claim with the independently remeasured **100%** witness and a link to its
  certificate, while explaining random-map expectation separately.
- README/analysis called every dot removed near the catalogue a "pure false
  positive". The mask applies to *mapped pixels*, not all possible expert
  faults within 200 m; corrected causal language and labelled historical
  filename-score pairings user-reported (no submission receipt).
- Website asserted the earlier portal range error "cannot recur". The
  rejected bytes and remote acceptance were not available; changed wording
  to a local numerical guarantee for **this** research TIFF only.
- Added fail-closed new-lane CLI, software regression tests and a verifier
  consistency check tying the public witness/preflight files to the old pinned
  certificate. No vendor metric, writer, novelty definition or pin was changed.

## Pass 3: acceptance check and remaining blockers

Rebuilt the seven-page site and checked all local links, verified reopened
TIFF, ZIP, hashes, run-card identity and generated status. Tested the
negative preflight, tampered report failure, missing witness failure, and
non-saturation failure. `pip check` reports no broken requirements;
`pytest` is green (208 tests after integrating concurrent main PRs #29 and #30);
`verify_project.py` checks the displayed proof and the current artifact,
but does **not** authenticate an organizer score. The concurrent review also
hardened the selector independently; duplicate dependency pins introduced by
the merge were removed before retesting. The
current file remains `OK TO DOWNLOAD: YES / OK TO SUBMIT: NO`, with a
unique byte hash, format PASS, duplicate FAIL, selector refusal and 0 slots.

**Unresolved:** The owner's literal parallel-run rule is infeasible for any
nonempty file while this continuous registry raster remains in scope.
Reinterpreting continuous prior surfaces as matched-budget top-k dots has
precedents in archived work, but is *not* authorized in this review; moreover
NHR independently duplicates 26 ordinary dot fields. An account-side weekly
slot and organizer acceptance cannot be verified here. Next separate lane,
once rules are clarified, must use shared buffered holdout and single-feature
canaries and beat the matched current best *before* considering selection.
No honest claim of outperforming the user-reported H33 0.2778 or the public
leader 0.4413 follows from the present offline evidence.
