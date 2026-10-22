# H79-FF (Arena session 1de1617f) — archived negative lane. DO NOT SUBMIT.

Session `1de1617f` (PR #34, merged at `d9dfb85`) generated a far-field lidar-scarp dot map (`gems79-h79-ff-farfield-scarp-37654dots-20261022T035020Z-b899aac8.tif`, `sha256: b4dd75e03cb2b4949cb4f0c079ca40077d2bfcb2651f4f3837dd5fbd035d2ba9`) placing 37,654 binary dots strictly 2–8 km off the mapped fault catalogue (`existing_faults.tif`), ranked by USGS 3DEP lidar `step_max` with 3 px Poisson spacing.

## Why this artifact was moved from `docs/downloads/` to `archive/h79_ff_1de1617f/downloads/`
1. **Single-canonical-artifact publication contract (`IR-79-52`, `IR-79-66`):** `scripts/verify_project.py` (`only_canonical_upload_artifacts_published`) requires that `docs/downloads/` contain **only** the canonical `run_card.json` artifact pair (`H79-NHR`, `gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.{tif,zip}`). Leaving a second `.tif`/`.zip` in `docs/downloads/` (and without `-DO-NOT-SUBMIT` in its filename) broke `Verify research deliverable` and `Pages and public-source health` on `main`.
2. **Duplicate gate failure:** As recorded in [`evidence/ff/ff_run_card.json`](../../evidence/ff/ff_run_card.json), `H79-FF` failed the 3-px registry overlap gate (`1.0000` against `17GEMSDOE` E-proba, `GEMSDOE48` unassigned-mass, and `5GEMSDOE` density-probe; `0.9976` against `13GEMSDOE` spacing-5 lattice; `0.8802` against `GEMSDOE3` coverage-v3-wide).
3. **Unpreregistered / un-evaluated on `HOLDOUT-DTI`:** `H79-FF` was not preregistered in `registry/` and did not run `gems57-pooled-hide-v2` holdout evaluation (`holdout_dti` was marked `NOT-APPLICABLE` in `evidence/ff/ff_run_card.json`). Its verdict is `negative` (`ok_to_submit: false`, `0` slots used).

All original bytes (`.tif`, `.zip`, `.json`) are preserved unaltered in `downloads/` for auditability.
