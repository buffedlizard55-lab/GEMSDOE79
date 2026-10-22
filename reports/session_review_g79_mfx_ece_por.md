# Three-pass review — G79-MFX, G79-ECE, G79-POR

Branch `arena/36514e3d-gemsdoe79`, 2026-10-22. Every number below is copied from a JSON
receipt written by the script named next to it.

## What this session was asked to do, and what it did

The standing request is a **unique, downloadable, submittable GeoTIFF** plus an honest answer to
"why did H33 score 0.2778, and can we beat it". This session:

1. restored all 13 SHA-256-pinned inputs (they were absent from this checkout),
2. preregistered and ran three genuinely new lanes,
3. published exactly one new artifact as a labelled **probe** with an explicit
   download / upload / promotion table,
4. recorded three terminal negatives instead of promoting a file that failed its own gates.

No submission slot was used. No canonical byte, card or decision line was altered.

## Pass 1 — implement and verify

| Step | Evidence | Result |
|---|---|---|
| Input restoration | `data/restore_receipt.json`, `python scripts/restore_data.py --preserve-receipt` | 13/13 restored, every SHA-256 matches `registry/data_manifest.json`; `training_features.tif` re-verified inside every runner before use |
| EXP-1 G79-MFX | `evidence/mfx_experiment1.json`, `run_card_mfx.json` | HOLDOUT-DTI 0.0504 / 0.0492 vs uniform 0.0505 / 0.0515 → negative |
| EXP-2 G79-ECE | `evidence/ece_experiment2.json`, `run_card_ece.json` | HOLDOUT-DTI 0.0443 / 0.0441 vs uniform 0.0688 / 0.0642; enrichment 1.06× / 1.22× → negative |
| EXP-3 G79-POR | `evidence/por_experiment3.json`, `run_card_por.json` | collar 0.0509 / 0.0564, corridor 0.0049 / 0.0031, hybrid 0.0440 / 0.0468 vs uniform 0.0450 / 0.0491 → negative |
| Probe packaging | `registry/published_probes.json`, `docs/downloads/gems79-PROBE-…-20261022.{tif,zip,json}` | 15/15 official format checks pass; SHA-256 `738e5e50…926b5b1` |
| Novelty | `evidence/novelty_gems79-por-…json` | max 3-px forward overlap **0.513** against 70 informative priors (limit 0.70); Jaccard vs H33 and D2.8-class files ≤ 0.0043 |
| Unit tests | `tests/test_mfx.py` | 4/4 pass (template normalisation, dedup, translation invariance, prior algebra, distance geometry) |
| Project contract | `python scripts/verify_project.py` | passes, including the new `declared_probes_are_labelled_and_hash_pinned` |

## Pass 2 — bugs found and fixed (all before the numbers they would have corrupted)

1. **`gems79/mfx.py::ncc_score`** contained a dead `if False else` expression left from a draft,
   and `template_bank`'s greedy de-duplication updated its similarity vector with a meaningless
   `np.maximum(sims, |corr| * np.sign(sims))`. Both were rewritten to the explicit accepted-set
   form before EXP-1 ran; `tests/test_mfx.py` now pins the unit-norm, zero-mean and
   `< 0.70` mutual-correlation properties.
2. **`scripts/run_ece.py::tilt_angle`** silently degraded to `atan2(hgm, hgm) = π/4`, i.e. a
   constant, whenever band 9 was absent from the loaded stack. That would have made the corridor
   prior depend on a constant. Fixed to raise, and the runner now loads band 9 explicitly.
3. **`scripts/measure_candidate_novelty.py`** carried an invalid walrus expression in its shape
   check; fixed to a plain comparison.
4. **`scripts/build_probe_cards.py`** had a walrus assignment inside a dict literal (SyntaxError);
   fixed, and every card number is now read from evidence rather than typed.
5. **`scripts/run_mfx.py::fetch_top_priors`** passed bare site names (`GEMSDOE32`) to `gh api`,
   so all 12 top-scoring prior fetches failed silently and the first novelty measurement covered
   only local rasters (48 priors). Fixed by prefixing the organisation; the published novelty
   numbers come from the post-fix re-measurement over 72 rasters, which is what
   `evidence/novelty_*.json` and both cards use. The stale pre-fix `novelty` block inside
   `evidence/mfx_experiment1.json` (48 priors, `fetches` all errored) is retained as-is and is
   **not** the number quoted anywhere else.
6. **`write_submission` refuses to overwrite**, so the probe had to be written to a new name
   rather than edited in place. The probe TIFF is byte-identical to the EXP-3 raster
   (`738e5e50…`), which is why `artifacts/` was used to retire the two falsified candidates
   instead of deleting their receipts.

## Pass 3 — re-check against the original request

* **"Unique TIF submission"** — yes, generated here, uniqueness measured against 70 informative
  priors and the 12 highest-scoring predecessors, including the 0.2778 H33 file (3-px forward
  overlap 0.161, Jaccard 0.0043).
* **"Obvious whether it is ok to download and submit"** — yes, a five-row decision table on
  `docs/probe-submission.html` and a four-metric block at the top of `docs/index.html`. Download
  YES, upload YES, duplicate NO, promotion NO, final pick NO.
* **"The inspection needs to be validated without human intervention"** — all gates are
  automated and reproducible: `scripts/run_por.py`, `scripts/measure_candidate_novelty.py`,
  `scripts/verify_project.py`, `pytest tests/`.
* **"Explain why H33 scored 0.2778 and whether we can beat it"** — answered in
  `docs/probe-submission.html` §4 and `research/hypotheses_g79_mfx_ece_por.md`: H33 is D2.8 minus
  its inner 2 px ring, the metric is coverage-dominated at 0.23% prevalence, and the family's
  plateau is a property of its single bet (catalogue-adjacent placement). Nothing measured in
  this session closes the ~0.16 gap to the public leader at 0.4413.

## Remaining limitations (flagged, not hidden)

1. **The instrument cannot certify discovery.** Its truth is 100% catalogue geometry; the
   organiser's truth is, by construction, faults absent from the catalogue. A lane that scores
   well here is scoring extrapolation. This is the top-priority gap (IR-79-235).
2. **Uniqueness scope.** 70 informative priors plus 12 predecessors, not the full 992-raster
   registry, which is not re-restored in this workspace. One saturated 1.88 M-pixel
   continuous-surface prior covers any candidate at ≥ 0.70 forward overlap; that prior is the
   documented unsatisfiable witness, not evidence about this file.
3. **Data provenance.** Pinned owner mirrors, not organizer-authenticated downloads. Hashes prove
   consistency, not authorship.
4. **No organizer receipt.** Every score in this repository other than a submission-page receipt
   stays UNVERIFIED, including the 0.2778 and 0.4413 figures quoted from the prompt and the
   public board.
5. **Two hypotheses remain unexecuted** (G79-FLT, G79-KNP) because their free official inputs sit
   outside this sandbox's egress allowlist. The exact sources are named in the backlog.
