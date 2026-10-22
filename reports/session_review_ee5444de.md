# Repository review — 2026-10-22

Session branch: `arena/ee5444de-gemsdoe79`; starting commit `b1f27dc43eb2b5fe61ccfcb6303672cb8adaa772`. This is a repository/release-readiness review only. It did not resume the stopped scientific run, generate a TIFF, make final dot placements, use a competition slot, upload a file, or claim live organizer acceptance.

## Decision

**Existing artifact: OK TO DOWNLOAD for research inspection; DO NOT SUBMIT. Automated verdict: `negative`.** The artifact is clearly named `DO-NOT-SUBMIT`. The shared literal novelty gate has a recorded full-footprint witness, so a nonempty candidate cannot meet the required 70% forward-overlap limit under the current support definition. The experiment remains stopped. No exception, thresholding workaround, jitter, or second method lane was introduced.

## Three review passes

### Pass 1 — read the project contract and inspect current state

- Read the complete `README.md` including the preserved user prompt, `AGENTS.md`, canonical `run_card.json`, `reports/irregularities.md`, `registry/preregistration.json`, the hypothesis table, and the latest prior review.
- Confirmed the active branch from the checkout is `arena/ee5444de-gemsdoe79`; historic branch names inside immutable receipts are provenance, not current branch instructions.
- Confirmed the experiment state remains stopped negative after E1; its official run card retains null HOLDOUT-DTI and canary values because the authorized run stopped before those evaluations. No new surface or final placements were generated.
- Confirmed four ranked hypotheses and their layer/signature/missing-catalogue rationale/differences/cost/mimic are already documented in `research/hypotheses.md` and preregistration. E1's post-stop diagnostic is negative and does not qualify as a promotion result.

### Pass 2 — test, verify artifact/evidence and inspect fail-closed status

The system Python initially lacked `pytest` and `numpy`; this was an environment issue, not a repository test failure. Created ignored `.venv/` and installed the exact versions in `requirements.lock`. Then:

- `.venv/bin/python -m pytest -q`: **108 passed**.
- `.venv/bin/python scripts/verify_project.py`: `all_checks_passed: true`; pinned shared code, preregistration, reference input hashes, receipt/card copies, TIFF/ZIP, byte distinction, duplicate certificate consistency, non-fabricated null metrics and negative verdict all checked.
- `.venv/bin/python scripts/check_site.py`: passed; **7 pages**, **107 local links**, all pages reachable, **2 compatibility redirects**, no external browser assets, submission remains disabled.
- `.venv/bin/python scripts/submission_status.py`: returned JSON `verdict: negative`, `ok_to_download: true`, `ok_to_submit: false`, `human_inspection_required_for_this_decision: false`; exit code **2**, the expected negative-status code.
- Canonical TIFF SHA-256 verified by the project integrity check: `8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca`.

These are local reproducibility/format checks, not organizer acceptance. The numerical score fields in the current canonical run card remain **not measured**; the already recorded post-stop diagnostic is separately classified and does not establish promotion. No new live-page/source/leaderboard fetch, browser rendering, or DrivenData request was made in this review.

### Pass 3 — requirements and next-step safety review

- Verified README still preserves the user's full prompt, leads with an unambiguous download/submission decision, and links to the executive guide, TIFF and ZIP.
- Kept the generated raster available for download while marking it **DO NOT SUBMIT** in its name and automated decision. This avoids implying that byte validity establishes uniqueness or scientific value.
- Confirmed H33 forensics, score evidence classes, official source ledger, four preregistered hypotheses, irregularity log and post-stop diagnostics are linked; user-reported/public scores are not converted into ORGANIZER-CONFIRMED receipts.
- Did not generate another TIFF or try to validate a fresh method: doing so would conflict with the active stop condition. The historical hypothesis candidates cannot be treated as successful simply because they are documented.
- Confirmed local site integrity and status. Public Pages freshness, organizer account capacity, a submission receipt, and source reachability were not checked here.

## Remaining work and limitations

1. Obtain an explicit authorized protocol-owner ruling on the meaning of “dots”/support for a continuous raster and the saturated registry witness. Update the shared template protocol once if approved; do not implement a private exception.
2. Only after that ruling and a complete registry comparison clears novelty, preregister a permitted run and execute individual-feature leakage canaries, then buffered whole-segment holdout with the shared evaluator and matched incumbent/control. The existing E1 does not beat its recorded controls.
3. Reproduce the incumbent holdout with matching evaluator/withheld-positive counts/95% CI before asserting an improvement. No leaderboard projection or success claim is justified.
4. Keep the TIFF quarantined. A separate selector must approve any weekly slot; account capacity and an organizer receipt are not available in this checkout.
5. No evidence here establishes geothermal vents, temperature, permeability or viable wells. The competition task is fault mapping; this distinction is documented in the source ledger.

## Run card for this review

```json
{
  "hypothesis": "G79-FABRIC-OFFSET: opposite-side magnetic-marker displacement across an independent gravity edge",
  "mechanism": "Compare tangent magnetic-gradient profiles across a gravity edge and score coherent nonzero registration lag over zero lag at two offsets.",
  "named_non_fault_process": "An unfaulted oblique intrusive or lava-flow contact, or an airborne survey levelling seam, can mimic a displacement lag.",
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": "gems57-pooled-hide-v2",
    "status": "NOT MEASURED in the authorized pre-placement run; no new score or CI in this review",
    "withheld_positive_pixels": null,
    "dti": null,
    "ci95": null
  },
  "correlation_overlap_vs_registry": {
    "evidence_class": "REGISTRY-MEASUREMENT",
    "surface_and_final_artifact": "Candidate rejected; shared literal-rule witness reports forward overlap 1.0 (> 0.70). No full-registry clearance claimed.",
    "rank_correlation_limit": 0.90
  },
  "raster_sha256": "8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca",
  "validator_output": {
    "local_format": "PASS",
    "nan_inside_footprint": false,
    "values_in_0_1": true,
    "crs": "EPSG:32611",
    "shape": [3730, 3292],
    "transform_matches_sample": true,
    "qualification": "Local format only; not organizer acceptance or novelty clearance."
  },
  "submission_name": "g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT",
  "submission_note": "Negative research artifact; literal registry-overlap and post-stop holdout gates do not support submission.",
  "verdict": "negative"
}
```
