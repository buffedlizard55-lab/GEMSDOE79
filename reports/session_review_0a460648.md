# Repository review — session 0a460648 — 2026-10-22

## Outcome

The canonical H79-NHR result remains a scientifically **negative** result. The
newly computed, byte-distinct GeoTIFF is format-valid and easy to download, but
it failed the required registry-overlap gate; the automated decision therefore
remains **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**. No competition slot was used,
no score was projected, and no stopped lane was restarted.

The requested next scientific step cannot honestly be run under the literal
parallel-run protocol yet. Evidence already in `evidence/nhr/overlap_chance.json`
shows that 30 registry rasters have three-pixel halos covering more than 70% of
the allowed area and reject even the seeded uniform control. In addition, the
canonical NHR candidate overlaps 26 informative, non-space-filling registry dot
fields above 70%, so its negative verdict does not rely only on that systemic
problem. A new lane must be preregistered rather than retuning NHR.

## Pass 1 — implementation and verification

1. Read the complete persistent prompt, active run card, irregularity register,
   active and archived preregistrations, hypotheses, evidence and site contract.
2. Reopened the canonical TIFF through `scripts/verify_project.py`. All 26
   project checks passed, including grid/CRS/transform/range, finite values,
   TIFF/ZIP identity, SHA-256 binding, holdout evidence binding, canary clearance,
   novelty failure and fail-closed status.
3. Ran `scripts/check_site.py`: seven pages and 114 local links passed; all pages
   are reachable from home and the negative submission decision is preserved.
4. Ran `scripts/submission_status.py`: it returned the expected machine-readable
   negative decision and exit code 2, without requiring human inspection.
5. Found one reproducibility bug: a clean install from `requirements.lock` could
   not collect `tests/test_g79b.py` because active module
   `src/gems79b/features.py` imports `skimage.filters.sato`, while neither
   dependency file declared scikit-image.
6. Added `scikit-image>=0.24,<1` to `requirements.txt` and pinned scikit-image
   0.26.0 plus its direct missing runtime dependencies (`imageio`, `lazy-loader`,
   `networkx`, `tifffile`) in `requirements.lock`.

## Pass 2 — bug and edge-case review

- A second clean-environment check exposed an independent verifier bug:
  `scripts/verify_project.py` scanned `.venv-clean/` dependency templates as if
  they were repository publication files and falsely reported Git conflict
  markers. The scanner now excludes directories whose names start with `.venv`,
  with a regression test; real repository conflict markers still fail closed.
- `pip check` reports no broken requirements.
- The full test suite now collects and passes: **187 passed**.
- `git diff --check` passes.
- The dependency change does not touch shared evaluator/writer bytes, scientific
  evidence, raster bytes, the registry, placement, the run card or site output.
- The current artifact remains byte-distinct from the frozen registry but is not
  protocol-unique; these are deliberately separate claims.

## Pass 3 — original-request re-check

- A TIFF and one-TIFF ZIP are linked at the very top of README and Pages.
- The file name and 122-character note are provided, and all predicted values are
  exactly 0 or 1, within [0,1].
- Automated validation—not visual inspection—determines download/submission
  readiness.
- Five ranked hypotheses and their named non-fault mimics already precede the
  canonical experiment in `research/hypotheses_nhr.md`; the top candidate was
  tested with the shared spatially blocked holdout before selection.
- Every reported scientific number remains labelled HOLDOUT-DTI or as an
  unverified historical report; no organizer-confirmed score was invented.
- The one canonical JSON run card remains `run_card.json`; this software review
  does not create a competing card.
- No new experiment was justified after the mandatory duplicate stop. Producing
  another nominally different TIFF to satisfy appearance rather than the gate
  would violate the user's protocol and waste work; this review does not do so.

## Limitations and next action

1. Obtain a protocol-owner decision for IR-79-53 (how to treat registry rasters
   whose three-pixel halo itself covers more than 70% of the domain). An agent
   cannot silently relax the explicit threshold.
2. After that decision, preregister a genuinely new far-field lane, preferably
   the already ranked antislope or shoreline-suppressed hypothesis, and perform
   the surface uniqueness test before placement.
3. The sandbox cannot authenticate to DrivenData, inspect the account's current
   weekly capacity, upload a submission, or create an organizer receipt.

## Concurrent-main integration

While PR #30 checks were running, PR #29 merged the independently reviewed
selector hardening and the same missing scikit-image dependency fix. Main was
merged into this fixed Arena branch without switching branches. The duplicate
dependency declaration was collapsed to main's `scikit-image>=0.25,<1`; the
irregularity IDs were reconciled so the virtual-environment scanner defect is
IR-79-60. Post-integration verification: **203 passed**, `pip check` passed,
all project checks passed, and all seven site pages / 114 local links passed.
The canonical negative verdict and raster bytes remain unchanged.
