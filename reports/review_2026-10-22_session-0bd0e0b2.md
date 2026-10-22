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
- Full suite after the merge: see the PR description (re-run on the merged tree). `scripts/verify_project.py` → all checks passed. `scripts/check_site.py` → passed
  (7 pages, every local link resolves).
- `run_bqa.py` fails closed once `evidence/bqa/state.json` records a terminal verdict. `place-x2` also refuses any
  surface without a passing uniqueness receipt for the same SHA-256.
- The shared `vendor/gems57/uniqueness.py` v4 is pinned in `registry/template_pin.json`. The upstream patch is in
  `reports/upstream_patch_uniqueness_v4.diff`.
- Integration code written for a possible promotion (canonical-card switch, lane-dispatching selector and verifier) was
  removed again after the stop, so this lane never touches the canonical card.

## Pass 3: publication
- This lane does not change the canonical deliverable (`run_card.json` and `docs/downloads/`); at merge time that is
  main's H79-DILSTEP DO-NOT-SUBMIT file. The site and README still say **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**
- The README and research page carry the H79-BQA outcome, and the analysis page carries the BQA tables. All of them
  are read from the evidence files.

## Merge with main (168 concurrent commits)
- Main had independently fixed the delta scanner (IR-79-105) and recorded the receipt conflict (IR-79-99). It also
  added a different v4 overlap mode (IR-79-86) and moved the canonical lane to H79-DILSTEP. Main's versions of the
  shared files were kept, including `vendor/gems57/uniqueness.py`, whose hash main's sibling audit pins. The tool that
  produced BQA's evidence is frozen in `archive/h79_bqa/`, and a test checks its hash against the evidence. The X2
  duplicate also fires under main's `informative-halo-v4` (raw 0.950, halo coverage 0.129), so the verdict does not
  depend on which reading is used.
- This session's in-session IR-79-67…70 were renumbered to IR-79-111…114, because main had reached IR-79-110.
  Frozen preregistration files keep their original numbers; the mapping is in `reports/irregularities.md`.
- Main's scanner found 5 blobs that this session's scan missed. BQA's verdict (duplicate) cannot change from extra
  rasters. This lane's 1,207-raster inventory is kept in `evidence/bqa/registry_delta_0bd0e0b2.json`.
