# Session review — H79-ASYM (2026-10-22)

**Outcome: OK TO DOWNLOAD: NO FILE PRODUCED. OK TO SUBMIT: NO.** No protocol-unique file exists in this
repo. The canonical download is still the H79-NHR DO-NOT-SUBMIT file, which failed the duplicate gate.

## What was done

| Step | Result | Evidence |
|---|---|---|
| Environment and inputs | Hash-pinned inputs (13 files) and 992 registry rasters restored | `data/restore_receipt.json`, `.cache/registry/` |
| Baseline tests | 186 passed, after the `scikit-image` pin (IR-79-58) | `requirements.lock` |
| Official facts | Metric, submission format and leaderboard fetched and cited | `README.md`, IR-79-60 |
| Metric bound arithmetic | 0.2778 needs c ≥ 23.5 %; 0.4413 needs c ≥ 38.7 % (corrected) | IR-79-59 |
| H33 forensics | D2.8 minus 6,436 dots within 200 m, exact at 2 px | `evidence/h33_forensics.json` |
| Preregistration (before results) | H79-ASYM, commit 365b727 | `registry/preregistration_asym.json` |
| Surface build | Lidar decoding per product rule; 62.1 % of footprint valid; 1,320,612 positive cells | `evidence/asym/surface_build.json` |
| Surface gate (rule 1) | **Duplicate.** Worst top-k overlap 1.0 with `GEMSDOE48` (continuous, all 5,167,373 cells). Worst Spearman 0.185 | `evidence/asym/uniqueness_surface.json` |
| Diagnostic (reporting only) | 30 space-filling and 956 informative rasters. Literal flags 62 (30 + 32). Chance-corrected informative flags 14 | `evidence/asym/surface_diagnostic.json` |
| Holdout, final dots | Not run. A duplicate stops the lane before placement | `run_card_asym.json` |

## Checks against the protocol

- Lane: stayed in H79-ASYM. The lane paragraph and the hypothesis are preregistered.
- Reuse: the shared uniqueness module (`gems57.uniqueness`), the shared placement and the shared canary are reused.
  The one change is that `scripts/nhr_uniqueness.py` takes lane, cache and output parameters, with defaults that keep
  H79-NHR's behaviour. The shared comparison is unchanged.
- Labels: no holdout number exists for this lane. Every number here is REGISTRY-MEASUREMENT or RASTER-MEASUREMENT.
- Leakage canary: not run (no holdout). A label-independent lidar surface cannot leak labels by construction, but that is not a substitute for the canary.
- Budget: 1 of 3 experiments used. About 50 minutes of 2 hours. A second experiment on the strain channel was considered and rejected, because 16 registry rasters already use strain or geodesy.

## Corrections made during the session

- `reports/nhr_analysis.md`, `README.md` and `docs/analysis.html`: the metric bounds changed to 23.5 % and 38.7 % (IR-79-59).
- `requirements.lock` and `requirements.txt`: the missing `scikit-image` dependency was declared (IR-79-58).

## Unresolved

- **IR-79-53** (space-filling registry rasters). Needs a user decision. Even the chance-corrected reading flags H79-ASYM, so the decision alone does not unblock this lane.
- **IR-79-61** (6 registry rasters not comparable). Reported; does not change the verdict.
- **IR-79-62** (NaN outside bounds in the organizer's wording versus zero-fill here). Flagged for organizer clarification.
