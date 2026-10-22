# Session review — 337ac1e9 (2026-10-22), lane H79-NHR

**Outcome: OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The research GeoTIFF is
`gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT`, with SHA-256
`abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`.
- It beat the H33 holdout control on both seeds.
- It failed the protocol's duplicate gate before and after placement.
- No slots were used. Budget used: 1 of 3 experiments, about 70 of 120 min.

## Pass 1 — implement and verify

**Inputs**
- Restored the inputs and all 992 registry rasters by SHA-256, using git so that no REST quota is needed (IR-79-49).
- Rescanned branches, tags and pull refs: 0 new rasters.

**Experiment X1**
- Wrote five hypotheses (`research/hypotheses_nhr.md`) and preregistered hypothesis 1 (`registry/preregistration_nhr.json`).
- Ran X1 holdout seeds 20 and 30 with the shared evaluator `gems57-pooled-hide-v2`:

  | Arm | Seed 20 | Seed 30 |
  |---|---|---|
  | Candidate | 0.1431 [0.1281, 0.1574] | 0.1522 [0.1335, 0.1696] |
  | H33 control | 0.0961 | 0.0989 |

  - Leakage canary: 464 single-feature AUC tests, max 0.8589.

**Uniqueness**
- Ran surface and final-dot uniqueness with the shared `uniqueness.py` and the v3 dot definition (IR-79-47).
- Ran a per-raster audit of overlap against chance (`scripts/nhr_overlap_chance.py`, 990 comparable rasters, 2 invalid files listed).
- 26 ordinary dot fields each hold more than 70 % of the dots within 3 px. The worst is 0.913, against 0.610 expected by chance. This is a duplicate, so the lane stopped (IR-79-55).

**Packaging**
- The research artifact was written by the shared writer, with a DO-NOT-SUBMIT name and a note that states the failure.
- The card was composed from evidence (`scripts/finalize_nhr.py`).
- The separate selector (`scripts/select_submission.py`) refused and recorded its decision.

**Checks run**
- `verify_project.py`: all 27 checks passed.
- `pytest`: 157 passed.
- `check_site.py`: passed.
- `browser_review.cjs`: 21 page/width cases at 1440, 390 and 320 px; download SHA, clipboard, redirects and filter verified.

## Pass 2 — bug review (found and fixed)

- `rasterio` cannot read with `Resampling.max`. The map preview now uses numpy max-pooling.
- A KeyError in the first version of the overlap audit was caught before the full run, by a smoke test on 6 rasters.
- The verifier needed `docs/run-card.json` before the site build wrote it. `finalize_nhr.py` and `select_submission.py` now write all three card copies.
- Absolute sandbox paths appeared in published JSON. They were stripped, and `nhr_uniqueness.py` now writes relative paths.
- The panel overflowed horizontally at 320 px. Fixed with `minmax(0,1fr)` grid columns.
- The status text cited unverified rule section numbers. They were removed.
- `AGENTS.md` and `evidence/browser_review.json` had merge-conflict markers; the JSON was invalid (IR-79-48). Both resolved.
- The "Paste into the submission form" heading appeared on a negative artifact. It is now conditional.
- The IR number IR-79-30 was already taken. The new entries are renumbered IR-79-47 to IR-79-55.

## Pass 3 — requirement recheck

| Requirement | Status |
|---|---|
| Unique newly generated TIF, not a copy | New bytes (SHA not in the registry). **Not protocol-unique**: duplicate lane, reported plainly. |
| Obvious OK to download / submit | README top, Pages hero, `status.json`, and the CLI exit code (2) all say YES / NO. |
| Automated validation, no human inspector | Shared validator plus reopened-TIFF and ZIP checks. The status decision is automatic. |
| Grid, range and NaN rules | EPSG:32611, 3730×3292, sample transform, values {0, 1}, no NaN anywhere. |
| Name and note ≤ 140 characters | Name is 73 characters, note is 122. |
| Why H33 scored highest; can we beat it | `reports/nhr_analysis.md`: metric algebra, byte forensics, bounds, leader gap. |
| 3–5 hypotheses ranked by gain and cost | 5, in `research/hypotheses_nhr.md`. |
| Top hypothesis validated on a blocked holdout before any slot | Done. It beat the holdout best; the slot is still withheld because it is a duplicate. |
| Free official data sources | 3DEP via the USGS National Map, and GeoDAWN flight lines (USGS release), both cited. |
| Protocol | One lane; duplicate checked on the surface and on the final dots; shared tools reused; one shared fix with pin and patch; every number labelled; leakage canary; run card. |
| Budget | 1 experiment, about 70 min. |
| README prompt; executive-summary page with the download at top; official links | Done. |
| PR and merge; next steps and limitations | README, `reports/nhr_analysis.md` section 6, this file. |

## Unresolved

- **IR-79-53.** 30 space-filling registry rasters flag even a uniformly random map, so any future lane needs an explicit user decision.
- **IR-79-54.** The final placement was run before the surface scan finished. No decision depended on this.
- **Proxy limits.** HOLDOUT-DTI is not a leaderboard projection; catalogue and expert faults may differ (IR-79-51).

## Merge with concurrent `main` (PR #22 to #26)

While this lane was running, 49 commits landed on `main`. The largest was G79-STEPCO (PR #26), which is also negative because its holdout tied H33.

**How the merge was resolved**
- **Canonical card.** H79-NHR is the canonical card, because its holdout evidence is stronger.
- **STEPCO.**
  - The S1 TIFF, ZIP and receipt moved byte-for-byte to `archive/g79_stepco_s1/`.
  - Its card and evidence are unchanged, and the research page links to them.
  - `tests/test_stepco.py` now reads `run_card_stepco.json` and the archived path.
- **E1.** The archive is unified at `archive/g79_fabric_offset_e1/`, the location `main` uses; the bytes were confirmed identical with `cmp`.
- **Irregularities.** This session's IDs were renumbered from IR-79-36..44 to IR-79-47..55, and IR-79-56 records the merge.
- **Verifier.** `main`'s conflict-marker and strict-JSON checks were added to `verify_project.py`, along with its rule that `md()` rejects broken links.
- **README.** The prompt section is taken from `main`, which includes the user-supplied GEMSDOE73–77 scores. The STEPCO status section is preserved in `reports/readme_history_through_9417f4e.md`.
- **Pages URL.** Verified with `gh api repos/buffedlizard55-lab/GEMSDOE79/pages`: `https://buffedlizard55-lab.github.io/GEMSDOE79/`.

**Checks after the merge**
- `verify_project.py`: all checks passed.
- `pytest`: 179 passed.
- `check_site.py`: 114 links.
- Browser review: 21 cases passed.
