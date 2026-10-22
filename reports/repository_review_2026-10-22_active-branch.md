# Repository review — 2026-10-22 (active branch audit)

## Scope and decision

Reviewed the full 992-line `README.md`, `AGENTS.md`, active H79-NHR preregistration, canonical `run_card.json`, `reports/irregularities.md`, current evidence, source/build scripts, tests, and static Pages content. The controlling state is the active H79-NHR/X1 lane: it is stopped negative. The generated research TIFF is **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**. No new scientific experiment, TIFF, selector decision, submission slot, or upload was made in this review.

The mandated lane stop is decisive: NHR/X1 failed surface and final-dot novelty checks; the separate literal-witness preflight also certifies that any nonempty candidate fails the present 3-px-overlap rule. Do not evade either check, restart X1, or turn the stopped lane's existing HOLDOUT-DTI into an organizer score. This review does not select a submission.

## Three review passes

### Pass 1 — map state and verify reproducibility

- Confirmed the working branch is `arena/dda58355-gemsdoe79`, clean before this review, with no branch switching.
- Read the complete README and the active protocol documents. The README points to the canonical artifact and clearly says not to submit it.
- Installed the repository's pinned Python requirements into the local ignored `.venv` (no tracked dependency or scientific-data changes).
- Ran `PYTHONPATH=src:vendor:scripts .venv/bin/python scripts/verify_project.py`: all 29 current consistency, provenance, format, holdout, uniqueness, and status assertions passed. Raster SHA-256: `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`.
- Ran `scripts/submission_status.py`: returned `ok_to_download=true`, `ok_to_submit=false`, `verdict=negative`; exit 2 is the expected fail-closed result.

### Pass 2 — test for defects and contradictory states

- `.venv/bin/pytest -q`: **230 passed**, one non-failing Rasterio `PendingDeprecationWarning`.
- `scripts/check_site.py`: passed; 7 pages, 120 local links, all pages reachable from home, 2 compatibility redirects, 0 external assets; submit remains false.
- Compared the active README, status tool, canonical card, and current evidence. Their artifact identity and negative submit decision agree. Local format validity is not conflated with organizer acceptance.
- Recorded a documentation discrepancy for maintainers: `reports/repository_review_2026-10-22.md` is explicitly an older review snapshot that describes E1/FABRIC-OFFSET and old file counts. Its own date/context marks it historical; do not quote it as the current active state. The current state is in `AGENTS.md`, README, `run_card.json`, and the current evidence.
- Old branch names and run cards are provenance, not active instructions; archived lane materials are not activated.

### Pass 3 — requirement and safety check

- Unique TIFF requirement: existing file is newly generated relative to registry bytes, but it is **not unique under the prescribed gate**, so its prominent `DO-NOT-SUBMIT` status is correct.
- Score hygiene: only HOLDOUT-DTI is reported as a holdout proxy with evaluator version, withheld-positive counts and CIs. No ORGANIZER-CONFIRMED score exists for this artifact because no submission-page receipt exists. Public/reported scores are not represented as verified artifact scores.
- Hypotheses: pre-registered research ranks alternatives and names the non-fault mimics; the active stopped lane is not restarted. New-lane preflight forbids a nonempty candidate under the literal universal witness rule. Do not spend any slot until a proper prospective protocol clarification and independent selector authorization exist.
- Range/CRS/shape/transform validator checks are PASS for the available file, but they do not override scientific or novelty failures.
- No source-access, competition-login, account eligibility, remaining slot, private test-label, or organizer receipt capability was established here.

## Authoritative current run card

The JSON card remains [`../run_card.json`](../run_card.json); its fields include hypothesis, mechanism, named mimic, seed-level HOLDOUT-DTI/95% CIs and withheld counts, registry correlation/overlap, raster hash, validator checks, unique name/note, and negative verdict. This review intentionally does not duplicate rounded score values or manufacture a new card.

## Next work / blockers

1. Obtain an authoritative, prospective definition of “dots” for continuous full-footprint registry rasters. The literal overlap rule and certified full-footprint witness currently make every nonempty submission impossible to clear; do not silently reinterpret it.
2. Reconcile the older repository review's dated narrative with current history only if maintainers need a single navigation index; preserve the underlying historical report unchanged.
3. Only after blocker 1 is resolved, preregister a distinct lane and evaluate each feature alone with the pinned hide-and-recover evaluator, then surface and final-dot novelty checks, respecting the 3-experiment/2-hour budget.
4. DrivenData authentication, official data downloads/account state, submission capacity and organizer receipts remain external. Do not claim a leaderboard result without a receipt tied to the submitted artifact.

## Verification boundary

These checks establish local test and artifact consistency only. They are not an organizer upload, test-set score, leaderboard improvement, uniqueness clearance, external-source freshness check, or permission to submit. No pull request or merge is implied by this review document.