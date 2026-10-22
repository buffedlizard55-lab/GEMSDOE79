# Repository review — 2026-10-22 continuation

## Decision at a glance

**No new eligible candidate or holdout lane.** The 2026-10-22 continuation
restored and hash-verified the recorded inputs/registry, refreshed the reviewed
public leaderboard snapshot, repaired stale-feed fallback behavior, ranked
four official-source hypotheses, and rebuilt the research site. This continuation
did not produce a new TIFF, preregister or execute a new experiment, access a
submission account, select a weekly slot, upload a file, or obtain an organizer
receipt.

The canonical H79-NHR GeoTIFF remains a research artifact with
`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` Its recorded holdout is positive versus
the H33 control, but H79-NHR is a **negative/stop** lane because its registered
novelty gate fails. A separate H79-FF artifact arrived on `main` through PR #34
after the initial pass; it has no HOLDOUT-DTI and also failed novelty. It is
preserved under `archive/h79_ff_pr34/`, not published beside the canonical
artifact. No local score is being promoted to a public score or
organizer-confirmed result.

## Pass 1 — repository, evidence, and science

1. Read the full `README.md` and traced its brief, claims, and links to the
   run card, preregistration, evaluator outputs, raster/format receipts,
   uniqueness audits, frozen registry, source-data manifest, status tool, and
   published pages. The README keeps the complete original user brief.
2. Reviewed active and archived experiment records without reopening a stopped
   lane. `run_card.json` identifies the H79-NHR raster, submission name/note,
   holdout method/version, two-seed results and confidence intervals, leakage
   canaries, and negative verdict.
3. Reconfirmed the local scientific comparison in `reports/nhr_analysis.md`:
   H79-NHR holdout DTI is 0.1431 / 0.1522 versus the fold-fair H33 control at
   0.0961 / 0.0989. The 58-feature × 4-fold × 2-seed leakage audit has 464
   tests; maximum AUC is 0.8589, below the 0.90 leakage trigger. H79-NHR still
   fails novelty: 26 non-space-filling registry dot fields exceed the 70%
   3-pixel rule, with a worst overlap of 0.913. The surface top-k gate also
   fails. No overlap cap, exclusion, or threshold change was introduced.
4. Restored **992/992** pinned registry Git blobs and verified **13/13** source
   manifest byte hashes; durable summaries are in
   `evidence/registry_restore_git_2026-10-22.json` and
   `evidence/data_restore_2026-10-22.json`. These are byte-integrity results,
   not CRS/pixel-grid comparability or independent organizer authentication.
5. Strict registry comparison remains **986/992 comparable**, with six errors
   recorded in the existing uniqueness evidence. Therefore no complete
   novelty certificate exists, even though all frozen bytes are present.
6. Independently recomputed the r13 lattice capacity bound. Of 5,106,385
   allowed pixels, only 6,514 are outside its 3-pixel halo. A 37,654-dot map
   must therefore place at least 31,140 dots (82.7004%) inside that halo, over
   the 70% stop threshold. This is specific to that raster and budget; it is
   not generalized to every smaller candidate.
7. Checked official sources for the follow-up ranking. USGS describes
   background-corrected heat-flow well residuals; the listed heat-flow ZIP is
   130,154,244 bytes but the direct binary fetch returned HTTP 500. The
   depth-banded MT files are listed publicly. The broad ComCat query was too
   large to estimate local focal-mechanism coverage; it is not cited as a
   coverage count. USGS fault slip/dilation is catalogue-conditioned and was
   ranked last as a leakage-prone lead. The four-item ranking and limits are
   in `research/hypotheses_followup_20261022.md`.
8. Verified the 2026-10-22 public leaderboard observation: first 0.4413,
   rank 22 0.3183, and rank 48 0.2804. The old rank-48 value 0.2778 is not
   current in that observation and is not linked to a local H33 artifact
   receipt. The values are **public leaderboard observations**, not scores for
   this branch or organizer receipts.

## Pass 2 — engineering, reproducibility, and documentation

1. Added the missing `scikit-image` dependency and pinned runtime dependency
   set so a clean install from `requirements.lock` succeeds. A clean lock
   environment installed and `pip check` returned no broken requirements.
2. Found a source-health freshness defect: on failed direct HTTP checks,
   `scripts/refresh_feed.py` kept any prior snapshot even when the source
   ledger contained a newer research-reviewed public page observation. Added
   date-aware fallback selection: fresh parsed public pages win a same-day
   tie; otherwise retain the newest dated direct, ledger, or prior observation.
   No request failure is treated as a score refresh, receipt, or slot check.
   Added regression tests for newer-ledger and newer-prior behavior.
3. Ran the refresh once. All six direct HTTP probes failed with `SSLError` in
   this environment. The dated 2026-10-22 source-ledger observation was
   correctly preserved in `docs/evidence/source_health.json`, and the attempt
   is explicitly marked as a fetch failure. The subsequent site build exposed
   listed official source downloads on the Sources page and the new prospective
   ranking on the Research page.
4. Reconciled `reports/requirements_review.md` with the latest evidence and
   replaced stale repository-review copy with this review. Updated README and
   irregularity records remain explicit about which work was not done.

## Pass 3 — acceptance and quality gates

The initial pre-integration run passed 187 tests and checked 114 local site links.
During PR #35 preparation, `origin/main` advanced through PR #34, so the fixed
branch was integrated with that newer main state before final validation.

## Integration with current `main`

- Preserved the upstream H79-FF run card and byte-distinct TIFF/ZIP/metadata,
  but moved its three download-directory files byte-for-byte to
  `archive/h79_ff_pr34/downloads/`. The canonical root `run_card.json` remains
  H79-NHR, and the repository publication contract requires `docs/downloads/`
  to contain only the canonical TIFF/ZIP pair. H79-FF remains negative, has no
  HOLDOUT-DTI, and is not an artifact from this continuation. Its SHA-256s and
  original paths are in `archive/h79_ff_pr34/manifest.json`.
- Retained the upstream literal-support witness/preflight evidence, terminal
  lane guards, selector hardening, and review records. Kept the literal support
  result distinct from the budget-matched-v3 r13 capacity result; neither
  changes the other or authorizes a threshold exception.
- Rehashed the final working-tree state after integration: **13/13** manifest
  inputs, **992/992** registry blobs, and **3/3** archived H79-FF files verified.
  The live `data/restore_receipt.json` was separately changed by PR #34; the
  durable 13-input summary records the earlier check and does not claim that the
  current receipt remains byte-identical to its earlier version.

## Final acceptance and quality gates (after integration)

- `.cache/venv-lock-check/bin/pip install -r requirements.lock` and `pip check`:
  successful; **no broken requirements**.
- `scripts/build_site.py`: built **7 pages**; canonical decision remains
  download YES / submit NO.
- `scripts/verify_project.py`: **all checks passed**, including the literal
  witness/preflight match, pinned registry inventory, strict JSON, canonical
  publication boundary, TIFF format, raster/card hash, holdout-evaluator
  agreement, leakage canary, and status consistency.
- `scripts/check_site.py`: **passed**, 7 pages and **117 local links**, every
  page reachable, 2 compatibility redirects, no external assets; source feed
  is not represented as a submission receipt.
- `python -m pytest -q`: **229 passed**.
- `scripts/submission_status.py`: returned its expected **exit 2** because
  submission is blocked. Output remains `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`
  with novelty, negative-verdict, selector/slot, and explicit-approval blockers.

These checks validate software, repository evidence, and local format; they
cannot make either artifact unique or infer organizer acceptance. The local
submission decision has no human-review gate.

## Remaining stop conditions

1. Resolve the six strict registry-comparability errors without dropping any
   indexed raster or changing the 70% / 3-pixel thresholds.
2. If continuing to the HFR-residual lead, retrieve the official source binary,
   record size/SHA-256 and fields, verify spatial compatibility, then write a
   separate preregistration before testing it on the blocked holdout.
3. Run that prospective lane only after its fixed surface passes novelty.
   Keep holdout experiments limited to three or two hours. Submit or select a
   weekly slot only after a separate selector receipt and account-only
   conditions are independently established.

This review is tracked in [PR #35](https://github.com/buffedlizard55-lab/GEMSDOE79/pull/35)
from the fixed branch. The pull request is a code/review artifact only; no
submission, slot allocation, or organizer-confirmed score is claimed.
