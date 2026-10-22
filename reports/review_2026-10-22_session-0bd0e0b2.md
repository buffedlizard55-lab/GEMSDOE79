# Three-pass review — session `0bd0e0b2` (lane H79-BQA)

## Pass 1: evidence and claims
- Every BQA number in `README.md`, `reports/bqa_analysis.md`, `run_card_bqa.json`, `evidence/bqa/state.json` and the site
  is written by `scripts/close_bqa.py`, `scripts/report_bqa.py` or `scripts/build_site.py` from `evidence/bqa/*.json`.
  `tests/test_bqa.py::test_bqa_closure_is_rederived_from_evidence_and_wrote_no_file` re-derives the key values.
- The base preregistration (`registry/preregistration_bqa.json`, sha256 `5a09a8b7…`) is byte-identical to commit `69430a6`.
  Amendment A1 was committed in `70b9962` at 04:46:12Z. That was before any seed-30 or seed-40 score existed: the seed-30
  run had been stopped at its canary step. Two descriptive fields were edited afterwards; they are disclosed in the file.
- Reproducibility check: the `nhr_repro` arm reproduced the frozen NHR X1 HOLDOUT-DTI exactly on seeds 20 and 30
  (0.1431 and 0.1522), so the shared `fit(..., sample_weight=None)` path is unchanged.
- Labels: every score is HOLDOUT-DTI. No ORGANIZER-CONFIRMED number was created. Slots used: 0.

## Pass 2: code and tests
- Full suite: `pytest -q` → 239 passed. `scripts/verify_project.py` → all checks passed. `scripts/check_site.py` → passed
  (7 pages, every local link resolves).
- `run_bqa.py` fails closed once `evidence/bqa/state.json` records a terminal verdict. `place-x2` also refuses any
  surface without a passing uniqueness receipt for the same SHA-256.
- The shared `vendor/gems57/uniqueness.py` v4 is pinned in `registry/template_pin.json`. The upstream patch is in
  `reports/upstream_patch_uniqueness_v4.diff`.
- Integration code written for a possible promotion (canonical-card switch, lane-dispatching selector and verifier) was
  removed again after the stop, so the canonical NHR path is byte-for-byte unchanged.

## Pass 3: publication
- The canonical deliverable (`run_card.json`, H79-NHR, DO-NOT-SUBMIT) and `docs/downloads/` are unchanged. The site and
  README still say **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**
- The home page and executive summary now carry a data-driven H79-BQA section. Analysis and research pages include
  the BQA tables and hypothesis outcome.
- The stale "0 new rasters" statements were corrected (IR-79-69). IR-79-67…70 were added to `reports/irregularities.md`.
