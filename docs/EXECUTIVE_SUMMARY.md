# Executive summary & submission guide (updated 2026-10-22)

## ✅ THE FILE TO SUBMIT (only this one)
- **File:** `submissions/gemsdoe79-h79-cspt-kkt1swap-36500-20261021T223000Z-zeros.tif` (also `docs/downloads/…`)
- **ZIP (upload either .tif or this .zip):** `submissions/gemsdoe79-h79-cspt-kkt1swap-36500-20261021T223000Z-zeros.zip`
- **SHA-256 (.tif):** `388d86783e743a7f1a466e5f2cc58e5a694da12908a3ffe14bb8e55409cf75fc` · 36,500 binary dots · values strictly {0,1} ⊂ [0,1] · 0 NaN/Inf · EPSG:32611 · 3730×3292 · 0 dots on catalogue
- **Submission name:** `gemsdoe79-h79-cspt-kkt1swap-36500-20261021T223000Z-zeros.tif`
- **Note (≤140 chars):** `H79-CSPT: 130ch Stress-Perm+GMNS+Stage2 Filament+KKT 1-Swap B=36500 (HOLDOUT-DTI 0.1936 S30 / 0.1718 S20, 0/949 ov>0.70)`
- **Steps:** DrivenData → DOE GEMS → Submit → upload .tif (or .zip with single .tif) → paste note → Create. No human inspection needed: `python3 scripts/validate_submission.py submissions/gemsdoe79-h79-cspt-kkt1swap-36500-20261021T223000Z-zeros.tif` re-verified PASS on 2026-10-22. The old *"Predicted values must be in range [0, 1]"* error cannot occur with this file (binary {0,1}, zeros outside footprint, no NaN).

## ⛔ DO NOT SUBMIT
- `gemsdoe79-tiprelay-e1-35963-20261022-zeros.tif` (new 2026-10-22, unique, format-valid): HOLDOUT-DTI 0.1634 < H79 best 0.1827 → **negative result, research only** (`evidence/tiprelay_run_card.json`).
- `g79-fabric-offset-surface-E1-…-DO-NOT-SUBMIT.tif`: stopped as duplicate-risk before holdout (root `run_card.json`).

## Scores — labelled, no projections
All local numbers are **HOLDOUT-DTI** (`gems57-pooled-hide-v2`, α=0.2 β=0.8, 300m kernel). `0.2778` (H33) and `0.4413` (leaderboard top) are **ORGANIZER-CONFIRMED / owner-reported** figures copied from receipts/pages, never projected onto our files. Beating them can only be confirmed by a DrivenData submission receipt.
