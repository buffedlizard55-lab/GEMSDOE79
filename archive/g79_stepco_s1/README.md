# Archived concurrent lane: G79-STEPCO S1 (session 220dabc8, negative, DO NOT SUBMIT)

This lane was merged to `main` as PR #26 while session 337ac1e9 was running H79-NHR in parallel.
When the two were merged, H79-NHR became the canonical card because its holdout result was stronger:

| Lane | Seed 20 | Seed 30 | Comparison with H33 |
|---|---|---|---|
| H79-NHR | 0.143 | 0.152 | beat it |
| STEPCO S1 | 0.0946 | 0.0948 | tied it |

Both lanes are negative.

The S1 files were moved out of `docs/downloads/` without any change to their bytes, so the site still
publishes exactly one artifact. The STEPCO card stays at `run_card_stepco.json` and its evidence at
`evidence/stepco/`. Neither was edited, so `submission_file` inside that card still names the original
`docs/downloads/` path.

The S1 raster SHA-256 is `6ae07fbf14dfe2d169aa9f926c54ee5e74215d7c569ffcc325cb91da297e510a`.
`tests/test_current_run_integrity.py` checks it.
