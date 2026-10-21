# Three-pass implementation and review record

Date: **2026-10-21 UTC**. Scientific verdict: **negative / DO NOT SUBMIT**.
This document distinguishes delivered infrastructure from blocked scientific
acceptance criteria. A completed review is not a claim that every requested
scientific objective was achieved.

## Pass 1 — implement and verify the feasible deliverable

- Reviewed the entire original brief (preserved in README), the initially empty
  checkout, sibling method records, official problem/rules/clarifications, data
  availability and H33/D2.8 bytes.
- Restored five pinned inputs and 992 prior blobs, registered four hypotheses,
  and computed one fixed magnetic-fabric-offset surface. Shared modules and
  preregistration are hash-pinned and unmodified.
- Corrected the initial rank-only gate before any holdout/placement. The literal
  shared gate and universal-coverage certificate force a duplicate stop.
- Exported the existing rejected field as a new, byte-distinct TIFF and an
  identical single-TIFF ZIP. Reopened both through automatic format/hash/grid
  checks. Created one negative JSON run card, copied identically for evidence.
- Implemented automatic status, offline verification, tests, source ledger,
  hypotheses/limitations, H33 explanation, irregularity register and seven-page
  site. Initial software suite: **34 passed**. These are software tests, not
  scientific experiments, AUC clearances or HOLDOUT-DTI measurements.

## Pass 2 — edge cases, bugs and incorrect assumptions

Reviewed the project-owned feature/placement/novelty/status code, orchestration,
restoration/validation/build scripts, tests, website and claim provenance. Shared
code was inspected where invoked and tested against a brute-force metric oracle;
no claim is made that every line of every inherited module has been formally
verified.

Corrections made:

1. Require literal **surface clearance**, not merely absence of a duplicate row,
   before canaries/holdout; incomplete/invalid inventories stop too.
2. Adapt a complete inventory to the shared tool's structured schema. An early
   witness subset remains explicitly incomplete. This software correction did
   **not** rerun the scientific audit or rewrite its existing evidence.
3. Prevent registry resnapshotting after E1 started. New `restore_registry.py`
   verifies the original SHA-256, Git blob and size pins without rewriting the
   frozen index/receipt. The data wrapper similarly preserves its receipt.
4. Make readiness reject truthy strings, boolean counts/CI values, nonfinite
   scores, unmatched evaluator versions, CIs that exclude the estimate, absent
   provenance, and unbound selector evidence. Merely inserting a receipt field
   cannot establish organizer acceptance. This is local fail-closed software,
   not an account-authentication service or automatic selector.
5. Remove an empty CSS import; calculate the actual **MiB** download size;
   connect orphan-prone history/irregularity pages; use one primary page heading;
   correct a title that could imply H33's reported score was causally explained.
6. Make source freshness explicit. All six direct sandbox probes failed with
   TLS/network errors; none is reported as a newly verified claim. The dated
   research-browser leaderboard observation remains dated, not refreshed.
   The parser requires an unambiguous first-place **public** score column.
7. Clarify that restored external K/Th are labelled **uint8 derivatives**, not
   newly authenticated calibrated USGS measurements. No concentrations, raw
   radiometric ratios or physical error bars were inferred from them.
8. Read the complete Hermant et al. (2025) primary paper and official regional
   source descriptions. Record fault mimics, label incompleteness, metric/split
   differences and fault-versus-reservoir limitations without transferring paper
   metrics or silently implementing a second lane.
9. Exercise the default TIFF and ZIP validator CLIs, the status CLI (correct exit
   **2**), five-input wrapper and exact 992-blob frozen restoration. No new
   download was needed for those already restored inputs.
10. Test **cold** deterministic feature-cache reconstruction after moving the
    ignored cache aside: all ten array hashes reproduce exactly. Preregistration,
    state, cards, registry and original scientific receipts remain byte-identical.
    See `evidence/reproduction_check.json`. A separate private serialization
    recovery also regenerated the exact TIFF and ZIP hashes through the shared
    writer (`evidence/artifact_reproduction.json`) without overwriting original
    artifacts/cards. This is recovery, not a new experiment.
11. Run Chromium on all seven pages at **1440, 390 and 320 px** (21 rendered
    cases), with no horizontal overflow or browser/HTTP errors. Check clipboard,
    filter, health feed and the downloaded TIFF's actual SHA-256. Review actual
    desktop/mobile screenshots; use no fabricated geological image. Bundled
    serverless browser support was installed from pinned npm dependencies after
    resolving missing shared libraries; web-security bypass flags are removed.

## Pass 3 — entire-request acceptance and release review

The original brief was re-read in full. `reports/requirements_review.md` records
fulfilled, partial and blocked criteria rather than asserting universal success.
Final local tests, clean dependency install, workflow checks, PR/merge and public
Pages outcomes are recorded below **only after execution**. No new geological
run is authorized by finishing the software or by CI.

### Final local execution results

- Pinned clean environment installed successfully from `requirements.lock`.
- Full suite: **51 passed in 2.45 s** in the existing environment and **51 passed
  in 1.93 s** in the fresh environment. These timings/counts describe software
  tests, not HOLDOUT-DTI or geological performance.
- Static site: **7 pages, 103 local links checked**, every page reachable from
  home, no third-party browser assets, negative status preserved.
- Final real-browser rerun: **21 cases passed** at 1440/390/320 px, zero browser
  or HTTP errors; real TIFF download SHA-256 equals the run card.
- Staging review additionally caught CRLF-as-trailing-whitespace in the generated
  CSV ledger. Source and site copy were normalized to LF without changing
  values; cached `git diff --check` then passed. Prompt normalization changes
  trailing whitespace only.
- Input wrapper, frozen registry restoration, cold cache, exact TIFF/ZIP recovery
  and both format CLIs pass; readiness CLI correctly returns **2**.

### Concurrent-main integration and final regression review

PR #4 initially conflicted because main advanced to `a88c9ab` while this branch
was running. Inspected all incoming preflight code/tests/briefs, merged main into
the fixed session branch, and resolved conflicts explicitly. This is integration,
not a switch to the earlier proposed cross-sensor scientific lane.

- Retained the generic-grid format API and its useful unittest coverage. Added
  zero-exterior and signed north-up regression cases. The primary export remains
  strictly finite everywhere through the unchanged shared writer/validator.
- Removed the incoming independent similarity implementation in favor of a thin
  adapter to the canonical shared gate. Explicit path lists can reject, never
  certify a complete inventory. Corrected a constant-raster test: Spearman rho
  is undefined (`null`), while decoded identity / 100% overlap still rejects it.
- Preserve old briefs as clearly labelled historical snapshots. Replace stale
  “no file” HTML with two tested compatibility redirects and make the legacy
  hyphenated JSON path an identical alias of the actual current run card.
- Legacy unittest workflow now targets its unittest class explicitly (pytest
  fixtures need pytest's path bootstrap); the main pytest suite includes both
  legacy and current tests. No failed unittest import is called a passing test.
- Post-integration regression: **65 pytest tests passed in 1.99 s** in the
  fresh pinned environment; **14 legacy unittest cases passed** in 0.088 s.
  Browser rerun: 21 primary cases plus both old-bookmark redirects passed.
  Generic `--template` CLI accepts the real finite-zero exterior; shared default
  validation/status remain authoritative. Every original scientific pin stayed
  byte-identical.

### Evidence available now

- `evidence/verification.json`: actual committed TIFF/ZIP re-read, pin checks and
  fail-closed negative decision.
- `evidence/reproduction_check.json`: exact cold-cache recovery and unchanged
  scientific evidence.
- `evidence/browser_review.json`: 21 actual rendered cases and downloaded-byte
  hash check. Screenshots and browser binaries remain ignored.
- `scripts/check_site.py`: local asset/evidence/anchor links, all-page reachability,
  negative status and no third-party browser asset dependencies.
- CI verifies offline bytes/tests/site/browser. Daily public-source workflow
  refreshes reachability and attempts verified Pages artifact deployment; it
  never trains, changes scientific cards, makes a selector decision or uploads
  to DrivenData.

### Release / access record

- Attempt to change the existing legacy Pages setting to workflow mode returned
  **HTTP 403, Resource not accessible by integration**. The setting was not
  changed. Existing legacy main/root publishing has a `.nojekyll` root redirect;
  artifact deployment uses only `docs/`. No additional credential was requested.
- PR/check/merge/deployment results: **not yet executed at this checkpoint**.
  They must be replaced with observed outcomes before the final response.

## Remaining scientific limitations

No canary, HOLDOUT-DTI/CI, matched-incumbent improvement or final dots exist.
No trained neural network or top-leaderboard performance is claimed. The lane is
still stopped, not merely waiting for a human inspector. No slot was selected or
used. Every nonempty candidate fails the supplied literal witness; explicit
protocol/registry clarification is required before another authorized experiment.
