# Session review — `arena/c04e5e27-gemsdoe79` / H79-FFAS

Three review passes (implement → bugfix → requirements) before PR.

## Pass 1 — implement

- Ranked five untried hypotheses in `research/hypotheses_ffas.md` **before** any holdout.
- Preregistered H79-FFAS (`registry/preregistration_ffas.json`, 2026-10-22T03:49:08Z).
- Fixed IR-79-53 once in shared `vendor/gems57/uniqueness.py` as `informative-halo-v4` (IR-79-57).
- Restored lidar + 992 registry rasters; ran X1 holdout seeds 20/30, surface uniqueness, place, final uniqueness, overlap-chance, shared writer.

## Pass 2 — bugs / edge cases

- Surface uniqueness is checked before placement (IR-79-54 lesson).
- v4 does not fire on space-filling priors (unassigned-mass, s=5 lattice) and **does** fire on `62GEMSDOE` scarp-crosscut (0.986 vs chance 0.231).
- `verify_project.evidence_checks` now checks that the holdout-beaten *flag matches evidence*, so a negative holdout can still publish.
- `test_g79b.py` skips if `skimage` is absent (not in `requirements.lock`).
- Canonical download is a single FFAS pair; NHR bytes archived.

## Pass 3 — original request

- Unique TIF generated (not a copy of H33/NHR); SHA-256 `13ba929b…`.
- Obvious decision: **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** Site, README, `submission_status.py` (exit 2) agree; no human inspector.
- Format: float32, [0,1], all finite, EPSG:32611, sample grid. Portal range error cannot recur.
- Unique name + ≤140-char note.
- Executive summary / how-to-submit page present.
- Prompt preserved in README.
- Negative result is the deliverable; 0 weekly slots used.

## Limitations remaining

- Catalogue-holdout vs expert-unmapped labels (distribution shift).
- Uniqueness inventory is 992 public sibling rasters, not every competitor upload.
- Absolute 3DEP DEM still not on the sandbox allowlist (shoreline suppression, hyp. 4).
- DrivenData login still required for official training files and remaining weekly slots.
