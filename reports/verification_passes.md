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

### Pre-integration local execution checkpoint

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

### Second concurrent-main safety integration

Main subsequently advanced to `c26efec` (H79-MCT PRs #5–#6), after the first
integration. Inspected incoming source/pins/card/audit before choosing a merge
resolution. Its own literal audit records overlap 1.0 / 43 firings; its binding
approval exempts 43 dense-halo priors using a local shared-module amendment and
its card records post-duplicate placement changes. These are not authorized by
the active user's literal protocol.

Preserve that branch's evidence and small artifacts in a SHA-256 manifest-backed
historical archive; store code/HTML/CSS as non-executable text, not an alternative
active pipeline. Do not copy its modified shared module as an executable private
fork; the source remains in the merge parent. Keep canonical upstream modules,
all E1 scientific pins, the current negative card and one active research TIFF.
Retire the old active artifact URLs and replace `docs/status.json` with a
fail-closed current-E1 alias. No incoming holdout score becomes an E1 result, no
new lane is run, and no competition slot is spent.

Final integration regression: **67 pytest tests passed in 2.02 s** (fresh
pinned environment), the legacy 14-case unittest suite passes, and 21 browser
cases plus both compatibility redirects pass. All 103 local links and the exact
HTTP TIFF/ZIP hashes pass. SHA-256 archive-manifest checks pass, all original E1
scientific pins are unchanged, and every active JSON status is negative. This is an
explicit safety review, not a claim that the archived methodology or claimed
performance was independently validated.

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
- Release tracking: [PR #4](https://github.com/buffedlizard55-lab/GEMSDOE79/pull/4)
  is the authoritative check/merge timeline. The final post-merge confirmation
  and any deployment limitation are recorded in its release-verification comment
  and the Pages workflow; this file is the pre-merge review, not a prediction of
  future success. The final response reports only observed outcomes.

## Remaining scientific limitations

No canary, HOLDOUT-DTI/CI, matched-incumbent improvement or final dots exist.
No trained neural network or top-leaderboard performance is claimed. The lane is
still stopped, not merely waiting for a human inspector. No slot was selected or
used. Every nonempty candidate fails the supplied literal witness; explicit
protocol/registry clarification is required before another authorized experiment.


### Release follow-up: publication consistency

PR #4 merged as `d1a14fb188a2b8373a1f840b7f9b0551b9ac60a1`; both PR checks and
main verification passed. Pages build/deploy actions succeeded, but the first
immediate public consistency step failed. Later public metadata was independently
fetched at the canonical root: correct frozen hashes, negative status and the
22:56:07 UTC feed (five reachable endpoints, one authentication-required; public
leaderboard parsing remained ambiguous and did not invent a fresh result).

Do not assert a root cause without the original error: log download is blocked
by the sandbox host allowlist. Tested the GITHUB_OUTPUT command separately; it
correctly emits a real newline, so it is not blamed. Add cache-bypassed requests,
bounded readiness retries without weakening any assertion, and API-readable
failure/success annotations. Pin the CI runner to Ubuntu 24.04 rather than its
migrating latest alias. The follow-up PR and public verification comments record
actual post-fix outcomes. These are release-software changes, not more science.


Publication follow-up local validation: **71 tests passed in 2.06 s** in the
fresh pinned environment, all 103 links and 21 browser cases (plus the two legacy
redirects) passed; both local HTTP artifact hashes match. All original E1
scientific pins remain unchanged. The deployment job also attempts Actions-only
publishing with its explicitly scoped Pages-write permission, records the actual
API-reported mode, and emits a warning if that optional configuration attempt is
denied. A successful website check is never presented as proof that a denied
settings change succeeded.

### Session review checkpoint — 2026-10-21

Re-read the complete 951-line README (including the preserved original prompt),
`run_card.json`, `reports/irregularities.md`, and `registry/preregistration.json`.
Confirmed the current Arena branch name against the checkout; corrected the
stale hard-coded branch name in `AGENTS.md` so future sessions start from the
actual assigned branch. Created a clean isolated Python environment from the
pinned lockfile. Fresh verification: **71 tests passed**; `verify_project.py`
passed every recorded integrity check; `check_site.py` passed seven pages, 103
local links and two compatibility redirects. The readiness CLI returned its
expected negative verdict and exit code 2 (`ok_to_download=true`,
`ok_to_submit=false`). Its verification timestamp was refreshed; all scientific
artifact hashes and preregistration remain unchanged. No new experiment, holdout,
submission, source-fetch claim, or slot selection was made. Browser QA and live
Pages/API verification were not rerun in this checkpoint. Public verification itself remains mandatory.

### Session 2026-10-21 three-pass post-stop diagnostic and code-integrity audit (`arena/70519113-gemsdoe79`)

- **Pass 1 (Restore pinned data, merge upstream PR #9, and measure post-stop diagnostics):**
  Merged `origin/main` (`7433391`, PR #9) into `arena/70519113-gemsdoe79`. Restored all 13 SHA-256-pinned
  competition and external files (`training_features.tif` `sha256: 4371c82e3b83…`, 418,912,844 bytes)
  and reproduced all 10 `.cache/g79/*.npy` feature arrays bit-for-bit (`scripts/prepare_data.py --reproduce`).
  Implemented [`scripts/post_stop_diagnostic.py`](../scripts/post_stop_diagnostic.py) to write
  [`evidence/post_stop_diagnostic.json`](../evidence/post_stop_diagnostic.json) without altering `run_card.json`
  or reviving the stopped E1 experiment. Verified that even if `Decision D-1` resolved to Option B
  (`top-37,654` of E-proba, 3-px overlap `0.0119`) or Option C (`p >= 0.5`, 3-px overlap `0.3046`), E1
  (`G79-FABRIC-OFFSET`) still fails the preregistered holdout gate (`gems57-pooled-hide-v2`, `0.0474 [0.0390, 0.0552]`
  on `seed=20` with `n=11,321`; `0.0466 [0.0388, 0.0543]` on `seed=30` with `n=11,342`), failing to beat
  the matched `zero_lag_edge_control` with a positive 95% CI, scoring below `uniform_control` (`0.0504` / `0.0496`),
  and trailing `h33_foldfair_control` (`0.0961` / `0.0989`) by `-0.0487` and `-0.0523` DTI, while clearing
  all 72 single-feature leakage canary tests (`max_symmetric_auc = 0.5872` on `seed=20`, `0.6162` on `seed=30`).
- **Pass 2 (Fix code bugs, edge cases, and documentation assumptions — IR-79-26..IR-79-29):**
  1. Updated `AGENTS.md` to reference `arena/70519113-gemsdoe79` (`IR-79-26`).
  2. Made `scripts/verify_project.py` idempotent on `evidence/verification.json` when verification payload fields
     are unchanged on disk (`IR-79-27`), preventing `pytest` from dirtying `git status` or desynchronizing
     `evidence/verification.json` from `docs/evidence/verification.json` after `scripts/build_site.py`.
  3. Fixed `scripts/restore_data.py --preserve-receipt` (`IR-79-28`) so restoring valid `registry/data_manifest.json`
     entries outside the 5-entry `data/restore_receipt.json` verifies against `data_manifest.json` without
     raising a false `ValueError`.
  4. Updated `evidence/session_verification_2026-10-21.json` and `README.md` (`IR-79-29`) to include the
     measured post-stop diagnostic results while keeping `run_card.json` untouched in its frozen pre-placement
     negative state (`holdout_dti.dti = null`, `verdict = "negative"`).
- **Pass 3 (Full verification against the original prompt and automated release gates):**
### Session 2026-10-22 three-pass concurrent-merge quarantine and canary-gate hardening (`arena/700397d4-gemsdoe79`)

- **Pass 1 (Start-of-session protocol audit, upstream PR #12/#13 inspection, and witness re-verification):**
  Read `AGENTS.md`, `run_card.json`, `README.md`, `reports/irregularities.md`, `registry/preregistration.json`,
  and all active codebase/test/workflow files. Restored and verified the frozen universal overlap witness
  `.cache/registry/374c88b1da2b803e2ed160de467fd71ae114010d.tif` (`sha256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`)
  via `scripts/verify_overlap_witness.py --restore` (`evidence/session_witness_700397d4.json`, `all_checks_passed: true`).
  Inspected `origin/main` commits `b1f27dc` (PR #13, `20eef10`) and `3d386a3` (PR #12, `464d591`, lane `H79-CSPT`),
  confirming why `3d386a3` failed both `Verify research deliverable` (`39702012362`) and `Pages and public-source health`
  (`39702012311`) on GitHub Actions.
- **Pass 2 (Quarantine concurrent `H79-CSPT`, harden `status.py`, and run independent forensic audit — IR-79-30..IR-79-32):**
  1. Merged `origin/main` (`3d386a3`) into `arena/700397d4-gemsdoe79`, restored `reports/session_review_9e23b44d.md` from PR #13,
      and quarantined all 55 incoming artifacts and non-executable `.txt` sources from `H79-CSPT` (`464d591`) under
      [`archive/h79_cspt_3d386a3/`](../archive/h79_cspt_3d386a3/README.md) with a complete SHA-256 `manifest.json`
      (`IR-79-31`), keeping canonical `vendor/gems57/uniqueness.py` (`1c5094b8…`) and `registry/template_pin.json` intact.
  2. Implemented [`scripts/audit_archived_concurrent_lanes.py`](../scripts/audit_archived_concurrent_lanes.py) and generated
      [`evidence/concurrent_lanes_audit.json`](../evidence/concurrent_lanes_audit.json), proving with unmodified
      `gems57.uniqueness` and `gems79.status` that both archived concurrent GeoTIFFs (`H79-MCT` `d1a4158a…` and
      `H79-CSPT` `388d8678…`) have `1.0000` literal 3-px forward overlap against `17GEMSDOE_E-proba-multiscale`,
      capped overlap at `0.6800` and `0.6900` against sparse/semi-dense registry priors after unconstrained placement failed,
      and return `ok_to_submit: false`, `verdict: "negative"`.
  3. Hardened `src/gems79/status.py` (`IR-79-30`) so `leakage_canary` requires numeric `0.5 <= auc <= 0.90`,
      `required_threshold == 0.90`, and positive `int` `features_cleared` in addition to `passed is True`, with
      19 new boundary/negative unit tests in `tests/test_readiness_errors.py`.
  4. Updated `AGENTS.md` and `knowledge/why_h33.md` (`IR-79-32`) to remove hardcoded session branch names and
      document the post-stop diagnostic and archived concurrent-lane audits.
- **Pass 3 (End-to-end verification against the original prompt and release gates):**
  Re-verified every requirement line by line against `README.md`. Rebuilt `docs/` via `scripts/build_site.py`,
  ran the expanded pytest suite (`130 passed`), `scripts/verify_project.py` (`all_checks_passed: true`),
  `scripts/check_site.py` (`7 pages, 108 local links`), `scripts/submission_status.py` (exit 2), and
  headless Chromium QA (`node scripts/browser_review.cjs`, 21/21 viewport checks).

### Session 2026-10-22 environment-portability and developer-ergonomics audit (`arena/9e8bac9e-gemsdoe79`)

- **Pass 1 (Restore pinned data, reproduce deterministic transforms, and run full test suite):**
  Restored all 5 primary competition inputs into `data/raw/` and `data/reference/` via `scripts/download_competition_data.sh`, matching all SHA-256 pins. Verified bit-for-bit reproduction of all 10 `.cache/g79/*.npy` feature arrays via `scripts/prepare_data.py --reproduce`. Executed full test suite (`pytest`), verifying all unit and integration tests pass without failure.
- **Pass 2 (Fix environment portability, CLI ergonomics, and branch metadata — IR-79-33..IR-79-35):**
  1. Updated `AGENTS.md` branch contract to reference branch-neutral metadata rule while preserving current session scope (`IR-79-33`).
  2. Fixed bare `pytest` invocation by configuring `pythonpath = ["."]` in `pyproject.toml` (`IR-79-34`), resolving `ModuleNotFoundError: No module named 'scripts'` during collection.
  3. Made `scripts/download_competition_data.sh` portable across environments by checking `.venv/bin/python` if present or defaulting to `python3` (`IR-79-35`).
  4. Added `argparse.ArgumentParser` to `scripts/post_stop_diagnostic.py` so `-h`/`--help` exits immediately with documentation instead of executing heavy holdout calculations (`IR-79-35`).
  5. Added unit tests for script help exit and syntax validity in `tests/test_site_feed_and_recovery.py`.
- **Pass 3 (End-to-end verification against prompt requirements, live preview, and headless browser QA):**
  Re-checked all requirements against the verbatim prompt in `README.md`. Verified that the static site clearly displays the download links and automated negative verdict (OK TO DOWNLOAD: YES, OK TO SUBMIT: NO) at the top of `index.html` and `executive-summary.html`. Launched live website server on `0.0.0.0:8080`, and executed headless Chromium QA (`node scripts/browser_review.cjs`), verifying all 21 viewport/page combinations pass, downloaded TIFF SHA-256 matches `run_card.json`, clipboard copy functions work, and no HTTP/console errors occur. Ran `scripts/verify_project.py` (all checks passed), `scripts/check_site.py` (all 7 pages and 108 local links passed), and `scripts/submission_status.py` (fail-closed negative verdict with exit code 2).

### Session 2026-10-22 conflict-marker remediation, Smart-HTTP blob recovery, and cross-family lineage audit (`arena/79e8e13e-gemsdoe79`)

- **Pass 1 (Full repository audit, Smart-HTTP cold data/artifact restoration, and cross-family byte forensics):**
  Read all active files line by line across `AGENTS.md`, `README.md`, `run_card.json`, `reports/`, `knowledge/`,
  `registry/`, `src/gems79/`, `vendor/gems57/`, `scripts/`, `docs/`, and `tests/`. Audited full Git history and
  detected four concrete repository defects (`IR-79-36`..`IR-79-39`). Upgraded `scripts/restore_data.py` and
  `scripts/restore_registry.py` with bare-Git Smart-HTTP object retrieval (`-c gc.auto=0`, zero GitHub REST quota,
  triple SHA-1/SHA-256/size verification), restored all 13/13 raw/external inputs, reproduced all 10 `.cache/g79/*.npy`
  feature arrays bit-for-bit (`scripts/prepare_data.py --reproduce`), cold-reproduced the exact GeoTIFF (`8f8c2cd1…`)
  and single-TIFF ZIP (`51e27e9d…`) (`scripts/reproduce_artifact.py`), re-verified the frozen universal overlap witness
  (`scripts/verify_overlap_witness.py --restore` → `evidence/session_witness_79e8e13e.json`), re-audited both archived
  concurrent lanes (`scripts/audit_archived_concurrent_lanes.py` → `evidence/concurrent_lanes_audit.json`), and implemented
  `scripts/analyze_family_lineage.py` → `evidence/family_lineage_forensics.json` across 16 scored family landmarks
  (`19GEMSDOE`..`GEMSDOE77`) and 5 post-snapshot siblings (`GEMSDOE78`, `GEMSDOE80`..`GEMSDOE83`).
- **Pass 2 (Defect remediation, site/verifier hardening, and expanded regression suite — `IR-79-36`..`IR-79-39`):**
  1. Resolved unresolved Git conflict markers in `AGENTS.md` and `evidence/browser_review.json` (`IR-79-36`).
  2. Fixed all broken links (`archive/h79_cspt_3d386a3/`, `knowledge/prior_work/README.md`, `docs/*.md`), deduplicated
     `IR-79-01`..`IR-79-39`, and corrected the `H79-CSPT` GeoTIFF SHA-256 prefix from `d55570bf…` to `388d8678…` (`IR-79-37`).
  3. Updated `registry/score_ledger.csv` to all 103 data entries (`GEMSDOE73`–`GEMSDOE77` added with `UNVERIFIED HISTORICAL REPORT`),
     synced the verbatim prompt in `README.md`, and documented the complete cross-family pixel lineage and `0.2778` vs `0.4413`
     architectural synthesis in `knowledge/why_h33.md` and `reports/session_review_79e8e13e.md` (`IR-79-39`).
  4. Hardened `scripts/verify_project.py` (`no_git_conflict_markers`, `all_tracked_json_strictly_valid`) and
     `scripts/build_site.py` (build-time Markdown relative-link existence validation + `docs/evidence/family_lineage_forensics.json`
     and `docs/evidence/session_witness_79e8e13e.json` publication), and added comprehensive unit tests in `tests/`.
- **Pass 3 (End-to-end verification, live preview & headless Chromium QA, PR creation, CI verification, and merge):**
  Re-verified every requirement line by line against `README.md`, rebuilt `docs/` via `scripts/build_site.py`,
  ran full `pytest` and legacy `unittest` suites, verified `scripts/verify_project.py`, `scripts/check_site.py`,
  `scripts/submission_status.py` (exit code 2), live preview server + `node scripts/browser_review.cjs` across
  all 21 responsive cases and downloaded GeoTIFF SHA-256 check, pushed `arena/79e8e13e-gemsdoe79`, verified GitHub Actions
  checks, merged the PR cleanly onto `main`, and verified public GitHub Pages consistency (`scripts/verify_public_site.py`).
