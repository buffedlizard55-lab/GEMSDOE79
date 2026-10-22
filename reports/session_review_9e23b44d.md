# Repository review — 2026-10-22

Session branch: `arena/9e23b44d-gemsdoe79`; starting commit `5e3067e186f3dcf7f511e8c81a44f7b32a7a0268`. This review was limited to repository integrity and release readiness. It did not start or continue the stopped scientific experiment, make new dot placements, generate another GeoTIFF, or use a competition slot.

## Decision

**Existing artifact: OK TO DOWNLOAD for research inspection; DO NOT SUBMIT. Automated verdict: `negative`.** The file is already present at [`docs/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif`](../docs/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif). It is not certified protocol-unique or scientifically promotable. Generating a second candidate would violate the active stop condition: the shared literal novelty rule finds a full-footprint prior whose positive support leaves no allowed pixel uncovered, so any nonempty candidate has forward 3-pixel overlap 1.0, greater than the 0.70 limit. No dense-raster exception was introduced.

## Three review passes

### Pass 1 — contract, repo and evidence inspection

- Confirmed the checkout is on the assigned branch and clean before review.
- Read all 1,012 lines of `README.md`, including the embedded original prompt; also read `AGENTS.md`, the run card, preregistration, irregularity log and scientific hypothesis table.
- Confirmed the inherited state is stopped negative after one experiment, with zero authorized holdout evaluations and zero final placements in its original run state. The subsequent archived post-stop diagnostic is explicitly not a promotion run.
- Reviewed the top-of-site download warning, validator/status path, novelty certificate, evidence boundary, and ranked four-hypothesis table. The table already names layers, physical signatures, catalogue-missing rationale, differences from reviewed approaches, cost, viability and mimics. The hypotheses are not new experiments or evidence of improved DTI.

### Pass 2 — execute checks and inspect edge-case behavior

Installed the exact pinned dependencies from `requirements.lock` into ignored `.venv/` after system Python showed `pytest` was absent. Results:

- **Software tests:** `.venv/bin/python -m pytest -q` — **108 passed**.
- **Offline artifact/evidence integrity:** `scripts/verify_project.py` — all recorded checks true. It reopened the committed artifact; checked template, preregistration, input, card, TIFF, ZIP and certificate consistency; and kept missing scientific results null.
- **Site integrity:** `scripts/check_site.py` — **7 pages**, **107 local links**, 2 compatibility redirects; all reachable; no external browser assets; `submit: false`.
- **Readiness CLI:** `scripts/submission_status.py` — JSON verdict `negative`, `ok_to_download: true`, `ok_to_submit: false`, expected exit code 2. This is deliberately not a format-only pass.

The raster hash verified by the integrity tool is `8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca`. TIFF and ZIP format checks are local-format checks only; they do not establish organizer acceptance or a score. No **ORGANIZER-CONFIRMED** receipt exists. Do not interpret absent scores as zero or projections.

### Pass 3 — requirements and safety re-check

- Kept the competition-download link explicit but paired with the top-level **DO NOT SUBMIT** callout.
- Did not generate another TIF: current stop rule and shared overlap measurement prohibit continuing under this protocol. The existing TIFF remains clearly quarantined by filename and readiness logic.
- Kept **HOLDOUT-DTI** figures, evaluator version, withheld-positive counts and confidence intervals distinct from public leaderboard results. Any post-stop values elsewhere in the repository retain their explicit post-stop/offline qualification; no new DTI is asserted in this review.
- No new registry scan, external scientific-source fetch, public leaderboard observation, browser visual QA, live Pages deployment check, PR, or organizer submission was performed here. Do not infer success for any of those from local tests.
- Removed the stale hard-coded Arena branch name in `AGENTS.md`; future sessions must follow their current session metadata.

## Scientific and process limitations

1. **Protocol conflict blocks promotion.** The literal finite-positive support definition is saturated by an accessible prior. An authorized protocol-owner clarification is necessary before another experiment. The agent must not silently redefine dots (e.g. top-K/thresholded support), bypass the gate, or scan more candidates after a mandatory stop.
2. **E1 is negative, not a candidate to polish.** The recorded post-stop diagnostics trail the fold-fair comparator, and paired improvement against the zero-lag control is not conclusive. See `evidence/post_stop_diagnostic.json`; its scores are not an authorized promotion result.
3. **No organizer-confirmed performance.** Public/user-listed scores are not receipts bound to this TIFF. Competition login/weekly submission capacity and a selector's authorization were not checked.
4. **Submission availability is intentionally distinct from eligibility.** The downloadable artifact validates locally but is blocked for submission. This directly avoids recurrence of the reported `[0,1]` form error, but format validity cannot ensure an organizer portal accepts the bytes.
5. **External provenance remains bounded.** The local reference files and sibling registry observations have documented hash provenance; mirror byte identity does not prove organizer-origin authenticity. Official research sources and scope are listed in `knowledge/official_sources.json` and `research/hypotheses.md`.
6. **Site publication is not re-verified here.** Local static-site integrity is verified; public Pages freshness is unknown in this review.

## Suggested next work

- Obtain a written, explicit protocol decision on the continuous-raster duplicate-gate support definition, then update the shared template protocol once—not via a local exemption—and rerun its complete pinned registry comparison before any new placements.
- Only if authorized and novelty clears: preregister a fresh permitted lane/experiment, execute feature-alone leakage canaries first, then buffered whole-segment spatial holdout with shared evaluator and paired uncertainty against the declared incumbent. Require a positive supported improvement before considering any selector/slot action.
- Keep current artifact quarantined. A new TIFF must be generated only after the above gates and a separate selector decision; confirm actual weekly capacity and organizer receipt before calling it submitted or scored.
- Refresh live-page and official-source checks in a future session when needed; retain URL, timestamp, content/hash and evidence class rather than presenting an attempted fetch as verification.

## Run card summary (current stopped run; no new measurement)

```json
{
  "hypothesis": "G79-FABRIC-OFFSET: opposite-side magnetic-marker displacement across an independent gravity edge",
  "mechanism": "A covered fault may offset a magnetic marker across a density boundary without a mapped surface scarp; an oblique intrusion/contact or survey levelling seam could mimic it.",
  "holdout_dti": null,
  "holdout_dti_label": "Not measured in the authorized pre-placement run; no new HOLDOUT-DTI or CI asserted in this review.",
  "correlation_overlap_vs_registry": "Prior overlap witness covers all allowed cells; literal 3-px forward overlap is 1.0 (>0.70). This blocks uniqueness; no full-registry novelty clearance claimed.",
  "raster_sha256": "8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca",
  "validator": "Local format PASS; no NaN in footprint, finite values in [0,1], EPSG:32611, 3730x3292, transform matches reference. Not organizer acceptance.",
  "submission_name": "g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT",
  "submission_note": "Negative research artifact; literal registry-overlap and post-stop holdout gates do not support submission.",
  "verdict": "negative"
}
```
