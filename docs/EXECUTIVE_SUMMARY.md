# Current executive summary and submission guide

**Download the generated research TIF here, but DO NOT SUBMIT it.**

The current generated artifact is **G79-TC** — a new unique, locally format-valid single-band GeoTIFF built from the measured Band-6 "tc" magnetic edge-detection channel:

- **TIFF:** `artifacts/g79_tc/g79-tc-edge-curvature-10000dots-20261022T204954Z-DO-NOT-SUBMIT.tif` (62,821 bytes, SHA-256 `64f4cccf5dbde7cd4e4bb60e9be5a3f908f514fe268c8306f48681d8ccb2e209`)
- **ZIP:** same TIFF inside a single-TIFF ZIP (11,262 bytes, SHA-256 `42054e979e36c8e84c2b04f018ecda4c09970cdb23d73c1da55f1c6593d4515f`)
- **Name:** `g79-tc-edge-curvature-10000dots-20261022T204954Z-DO-NOT-SUBMIT` (63 chars)
- **Note:** `G79-TC: Band 6 magnetic tilt/curvature edge surface, zero on mapped faults, 10000 sparse dots, [0,1]` (103/140 chars)

> **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**
>
> This is a new unique research raster, not a copy of any prior submission. Its local format passes, but the submission is **not approved**: holdout-DTI is measured (~0.0018), far below the incumbent; the literal novelty gate is blocked by the pinned full-footprint witness; no selector has approved a slot; no organizer receipt exists. Manual upload does not override the refusal.

Full decision page: [docs/g79-tc-submission.html](g79-tc-submission.html) · Full executive summary: [docs/executive-summary.html](executive-summary.html) · Latest review: [reports/session_review_c273c7a3.md](https://github.com/buffedlizard55-lab/GEMSDOE79/blob/main/reports/session_review_c273c7a3.md)

| Gate | Disposition |
|---|---|
| Local format and range ([0,1], no NaN, CRS/shape/transform match) | **PASS** (all checks) |
| Dot budget + zero on mapped catalogue | **PASS** (10,000 dots, 0 on catalogue) |
| Holdout-DTI (gems57-pooled-hide-v2) | **MEASURED NEGATIVE:** Seed 20 = 0.00178 [0.00025, 0.00359] (n=11,321); Seed 30 = 0.00062 [0.0, 0.00152] (n=11,342) |
| Leakage canary (single feature alone on holdout) | **PASS** (symmetric AUC 0.5289 / 0.5444, limit 0.90) |
| Literal novelty vs registry | **BLOCKED** (universal witness covers 100% of allowed cells; overlap 1.0000 > 0.70) |
| Selector / organizer receipt | **NOT APPROVED** |

**How to submit (when a future artifact is approved):** download the .tif/.zip, verify SHA-256, run `scripts/validate_submission.py` and `scripts/verify_project.py`, paste the name + ≤140-char note on the DrivenData submission page, and keep the organizer receipt. The "Predicted values must be in range [0, 1]" error cannot come from this writer — it rejects out-of-range values at build time and G1 re-verifies the bytes.

The canonical G79-THVC research artifact remains `docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif` (verdict negative, OK TO SUBMIT: NO). Slots used by this project: 0.
