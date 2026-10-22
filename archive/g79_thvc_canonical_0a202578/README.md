# Archived: G79-THVC canonical layer (moved in session 0a202578, 2026-10-22)

These files were moved here with `git mv`, so their bytes and history are unchanged. They are what the repository published while **G79-THVC** was the canonical research file.

- `downloads/`: THVC DO-NOT-SUBMIT TIFF, ZIP and receipt (SHA-256 `d3db2e95…fecfee2`).
- `run_card_thvc.json`: the THVC run card.
- `README_thvc.md`: the previous README, including the older preserved prompt.
- `docs/`: the previous Pages HTML, `status.json` and `run-card.json`.
- `scripts/`: the THVC-era `build_site.py`, `check_site.py`, `verify_project.py`, `submission_status.py` and `select_submission.py`.
- `tests/`: the test modules that assert THVC-canonical state. They are not collected by pytest (`testpaths = ["tests"]`).

THVC is still the **holdout incumbent** that new lanes must beat: HOLDOUT-DTI 0.1905 / 0.1944, frozen in `evidence/g79_thvc_results.json`. The novelty inventory (`scripts/fsc_novelty.py`) still scans every TIFF under `archive/`. See IR-79-200.
