# Repository review — 2026-10-22 (session `68182759`)

## Decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** Do not upload the research GeoTIFF. This is the repository's automated negative decision, not a request for human inspection. No new experiment or submission slot was used in this review.

## Pass 1 — inspect the project state

Read `AGENTS.md`, the README (including its embedded original request and lane protocol), the current run card, preregistrations, evidence, and irregularity log. The current `run_card.json` identifies lane `H79-NHR`, records `verdict: negative`, and sets `ok_to_submit: false`. Its output files in `docs/downloads/` are explicitly named `DO-NOT-SUBMIT`. The historical DTI is not an organizer-confirmed score absent a submission-page receipt.

The negative gate is supported by `evidence/new_lane_preflight_a7d092d7.json`: a hash-verified registry raster covers all allowed candidate cells under the stated literal positive-support overlap rule, so any nonempty candidate has measured overlap 1.0, above the 0.70 ceiling. The preflight is fail-closed (`start_new_lane: false`, exit 2). The active NHR lane is already terminal/stopped; this review did not restart it or evade the gate. The corresponding scientific holdout results and uniqueness evidence are preserved in the run card/evidence; this review did not generate a fresh TIFF.

The README already contains the requested persistent project brief, competition context, submission workflow, parallel-run constraints, and Arena values. It explicitly distinguishes downloadability from permission to submit.

## Pass 2 — run the checks and inspect failure modes

The initial system Python environment lacked NumPy, pytest and BeautifulSoup. Installed the pinned `requirements.lock` into an ignored `.venv/` and reran checks there; no tracked dependency changes were needed.

- `.venv/bin/python -m pytest -q`: **230 passed**, one upstream rasterio pending-deprecation warning.
- `.venv/bin/python scripts/verify_project.py`: **all 29 consistency/format/status checks passed**; raster SHA-256 `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`.
- `.venv/bin/python scripts/check_site.py`: passed, 7 pages and 120 local links checked, all reachable, 2 compatibility redirects, no external assets.
- `.venv/bin/python scripts/submission_status.py`: explicitly returns `ok_to_download=true`, `ok_to_submit=false`, `verdict=negative`, and no human intervention required for this decision (exit 2 is expected for a blocked artifact).
- `git status` remained clean after verification.

## Pass 3 — requirements and scientific judgment

No evidence in this checkout establishes that the new artifact is both protocol-unique and ready for leaderboard submission. In particular, a format-valid TIFF and a strong holdout result are not sufficient when the novelty gate fails and the selector has not authorized a slot. The reported H33 score (0.2778) and leaderboard values in the prompt are not treated as organizer-confirmed artifact-linked measurements. A leaderboard projection is not inferred from holdout DTI.

The apparent conflict between the user request for a fresh uploadable file and the lane protocol's hard duplicate rule is resolved conservatively: preserve the reproducible, clearly labelled negative artifact and do not relabel it as safe to submit. This meets the automated-validation requirement without human judgment and avoids spending a competition slot on a failed candidate.

## Next work and limitations

1. Obtain an explicit, authoritative protocol-owner decision for how continuous probability/support rasters are converted to “dots” for comparison. Do not locally weaken thresholds or exempt dense surfaces. Re-run complete registry coverage and the shared uniqueness checks only under that documented rule.
2. The four candidate geological hypotheses in `research/hypotheses_preflight_a7d092d7.md` are ideas, not measured experiments. After the gate is clarified and a new lane is preregistered, validate one at a time using shared buffered whole-segment hide-and-recover, feature-alone leakage canaries, paired confidence intervals, and the fixed experiment/time budget. Do not spend a slot unless the prespecified holdout gate is beaten.
3. Confirm the current account-side weekly allowance and participant eligibility on the DrivenData submission page. This environment does not have authenticated account access and cannot provide an organizer receipt.
4. Reconcile legacy/incompatible runner and feature APIs only through a separately tested, shared-code change; do not restart stopped lanes through legacy entry points.
5. Continue to label external mirror consistency separately from organizer provenance and label public/user-reported scores separately from submission-page receipts.

## Sources for manual review

- [Competition problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)

The repository's source ledger and local evidence identify which claims were verified from these public sources; links themselves are provided for independent review, not as proof that every linked source was reachable in this environment.
