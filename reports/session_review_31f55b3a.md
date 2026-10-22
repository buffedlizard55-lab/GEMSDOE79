# Session review — 31f55b3a (2026-10-22), lane H79-DCE

**Outcome: OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The research GeoTIFF is
`gems79-h79-dce-cover-37654dots-20261022T053035Z-b5dd778c-DO-NOT-SUBMIT`, with SHA-256
`4df5f414dd223def9fd125e512f86dbd8b722fb0279719d8f5a32f358218f40d`.
- It cleared format, canaries, cap fixed point, surface determinism and the
  ordinary-raster duplicate rule (by construction).
- It failed the preregistered holdout gate g3 and uniqueness gate g5.
- No slots were used. Budget used: 1 of 3 experiments, about 110 of 120 min.

## Pass 1 — implement and verify

**Preregistration** (before any result, hash pinned in
`evidence/preregistration_dce_sha256.txt` = 54b55fde…f90d4)
- Hypothesis 1 of five ranked candidates (`research/hypotheses_dce.md`): reuse
  the H79-NHR X1 surface byte-identically under a decorrelated cover emission
  (200 m collar + 300 m tile-cover + per-raster 0.68 collision ceiling applied
  during placement), with the at-risk set scanned from this lane's own uncapped
  emission (freeze > 0.50) and a post-final fixed point (trigger 0.68, ≤ 5
  iterations).
- Amendments before pinning: atrisk seed rule and the fixed-point clause were
  added while the surface rebuild was running and before any holdout result
  existed.

**Shared-tool v4** (defects fixed once in the template, not a private fork)
- IR-79-57: vacuous-overlap rasters (measured uniform chance > 0.70) now block
  only on overlap beyond chance (one-sided 95 % binomial margin); missing
  chance entries keep the literal fail-closed reading.
- IR-79-58: undecodable / wrong-grid / wrong-CRS registry files are excluded as
  `not_comparable` with recorded reasons (6 files); all other errors fail closed.
- Pin updated in `registry/template_pin.json`; patch exported to
  `reports/upstream_patch_uniqueness_v4.diff`; tests in `tests/test_dce.py`.

**Surface determinism**
- The H79-DCE surface rebuild (static stack, nested rows, 3 replicates) exited
  0 and its SHA-256 matches the frozen H79-NHR X1 receipt exactly — the stopped
  lane's surface was reused without retuning.

**Experiment X1 (the only one)**
- At-risk scan: 960 ordinary rasters scanned against the uncapped emission;
  182 frozen into the capped set (worst uncapped overlap 0.926 vs 0.612 chance).
- Holdout seeds 20 and 30, shared evaluator `gems57-pooled-hide-v2`, six arms:

  | Arm | Seed 20 | Seed 30 |
  |---|---|---|
  | Candidate (capped cover) | 0.1019 [0.0888, 0.1153] | 0.1048 [0.0887, 0.1217] |
  | Cover, uncapped | 0.1210 | 0.1229 |
  | Top-k + collar | 0.1463 | 0.1524 |
  | X1 recipe reproduction | 0.1462 | 0.1522 |
  | H33 fold-fair control | 0.0961 | 0.0989 |
  | Uniform random | 0.0151 | 0.0151 |

  - Paired Δ vs H33: +0.0058 [−0.0100, +0.0214] / +0.0059 [−0.0102, +0.0215] —
    **g3 fails** (CIs include zero).
  - Paired Δ vs uniform: +0.0868 / +0.0897, CIs exclude zero (g4 passes).
  - Canaries: 464 tests, max 0.8589 (g2 passes).

**Uniqueness**
- Final placement: exactly 37,654 dots; every capped raster at ≤ 25,604
  in-halo dots (max fraction 0.68000); 254,286 tiles skipped by the ceiling;
  fixed point converged in 1 iteration with no post-holdout additions.
- Authoritative scan: 986 comparable + 6 not-comparable, 0 errors, worst
  Spearman 0.104, **0 ordinary rasters flagged** — but **11 of 30 space-filling
  rasters hold the dots beyond chance** (worst 13gems-r8-ensemble: overlap
  0.817 vs 0.756 chance, excess +0.0608 > margin 0.0036) — **g5 fails**.
- Verdict negative; no retuning, no post-hoc cap extension.

**Packaging**
- Research artifact written by the shared writer (DO-NOT-SUBMIT name; note
  states the failed gates). Card composed from evidence only
  (`scripts/finalize_dce.py`). Selector refused (`evidence/dce/selector_decision.json`).
- H79-NHR's research artifact moved byte-for-byte to
  `archive/g79_nhr_337ac1e9/` (publication policy: one artifact pair).

**Measurement-correctness re-run (IR-79-61)**
- Review found the first holdout had placed its surface arms from a per-fold
  normalized copy of the fold surface (not the X1 holdout form). The stage was
  corrected to the raw fold prediction and both seeds re-run: **every arm and
  paired CI is identical to 4 decimals**, so all published numbers stand; the
  evidence files now come from the corrected code. The final artifact bytes
  are unchanged (same raster SHA-256; only the timestamp in the file name).

**Checks run**
- `verify_project.py`: all checks passed.
- `pytest`: test_dce (11) + test_nhr (5) + shared suite — see below.
- `build_site.py` + `check_site.py`: 7 pages, 113 local links, passed.
- `submission_status.py`: exit code 2 (blocked), as required.

## What a future session should know

1. The uniqueness–signal tension is now measured twice (X1 literal duplicates;
   DCE beyond-chance duplicates). Any near-fault emission will be
   beyond-chance-similar to the family's near-fault ensembles. A promotable
   lane needs either a surface whose value comes from structure *far* from
   mapped faults, or an explicit user decision that beyond-chance similarity to
   space-filling ensembles is acceptable.
2. The cap machinery works and is reusable (`src/gems79/dce.py`: place_capped,
   packed halos, fixed point). Its two costs (tile-cover −0.028, ceiling
   −0.019) are the knobs; both were pre-registered at their current values and
   must not be re-tuned on this evidence.
3. Untried ranked hypotheses remain in `research/hypotheses_dce.md`
   (#2 strain corridors, #3 antislope asymmetry, #4 far-field reweighting,
   #5 Lahontan elevation banding — blocked on USGS 3DEP access).
