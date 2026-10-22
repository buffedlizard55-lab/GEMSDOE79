# Session review — G79-CJX-DIR (2026-10-22, branch arena/d36b74f0-gemsdoe79)

## What was asked vs what was delivered

Asked: generate a **unique** TIF submission, easy to download, machine-validated
for submittability without a human inspector; explain why H33's reported 0.2778
leads the family and whether it can be beaten; 3–5 ranked new hypotheses;
validate the top candidate on the blocked holdout before any slot; README/site
updates; three review passes; PR + merge.

Delivered:
- A genuinely new GeoTIFF, `gems79-cjx-junction-20000dots-20261022T154845Z-7ee99228b5-zeros.tif`
  (SHA-256 `5bdebaafc7c15bd6f9de6092398c86618986d19d4d06075acf92386948563e47`, 96,603 bytes,
  20,000 dots), built only with shared tools (`gems57.submission_writer`,
  `gems57.evaluate_holdout`, `gems57.holdout`, `gems79.placement`). Independent
  re-validation (`scripts/validate_submission.py`): **PASS** — single float32 band,
  EPSG:32611, 3730×3292, sample transform, min 0.0 / max 1.0, 0 NaN/Inf, zeros outside
  the footprint, 0 dots on the catalogue. The portal error *"Predicted values must be in
  range [0, 1]"* cannot be produced by these bytes; the shared writer rejects any
  non-finite or out-of-range array before writing (no silent clipping). Which earlier
  file the user uploaded is unknown, so no stronger diagnosis is claimed.
- Automated decision, no human step: **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**
  (`run_card_cjxdir.json` gates). Three independent blockers: candidate does not beat
  controls, does not beat the current holdout best, literal novelty fails.
  Format PASS ≠ approval; the lane never selects itself (protocol rule 6) and
  `select_submission.py` has no CJX adapter, so `ok_to_submit` stays false.
- Ranked hypotheses with the required fields: `research/hypotheses_cjxdir_20261022.md`
  (CJX tested; BLC, RSS, anti-junction diagnostic, HFR data-blocked, ranked).
- H33 analysis: same file, bottom section. Short version: H33's lead is DTI
  arithmetic on the H19-5 lineage (spaced binarization + 2-px catalogue-shell
  pruning), all family scores >0.24 are that lineage, and beating it needs
  marginal-credit-aware placement on a strong corroborated surface — which for
  near-lineage variants collides with the novelty gate by construction.
- Competition slots used: **0**. Experiments used: **3/3 preregistered arms**
  (EXP1 CJXJ, EXP2 CJXFULL candidate, EXP3 budget sensitivity) + EDGE/UNIFORM
  controls and the preregistered phase-null diagnostic.

## Measured results (all HOLDOUT-DTI, gems57-pooled-hide-v2)

| Arm | Seed 20 (n=11,321) | Seed 30 (n=11,342) |
|---|---|---|
| EXP2 CJXFULL @20k | 0.0256 [0.0181, 0.0338] | 0.0319 [0.0224, 0.0418] |
| EXP1 CJXJ @20k | 0.0248 [0.0189, 0.0315] | 0.0220 [0.0152, 0.0291] |
| EXP3 CJXFULL @37,654 | 0.0335 [0.0253, 0.0418] | 0.0387 [0.0293, 0.0479] |
| EDGE control | 0.0259 | 0.0338 |
| UNIFORM control | 0.0310 | 0.0335 |
| REAL σ=2 junction | 0.0225 | 0.0230 |
| PHASE-NULL σ=2 | 0.0338 | 0.0324 |
| Canonical G79-THVC (reference) | 0.1905 | 0.1944 |

Leakage canaries (17 features × 2 seeds): max symmetric AUC 0.5526 / 0.5710 ≤ 0.90 — pass.
Novelty (25-raster restored subset; vendor EDT cross-check vs H33 agrees exactly):
final-dot forward overlap vs H33 = 0.2503, exact = 0.0132, surface ρ = 0.0243 — distinct
from the winning lineage and from every restored dot-field final (worst 0.5219 ≤ 0.70,
worst |ρ| = 0.0832 ≤ 0.90). The pre-placement surface top-20k reaches 0.7593 vs G79-MAG,
and the literal positive-support reading fails (subset worst 0.8252; full-inventory
witness covers 100% of allowed cells). D-2 chance-corrected worst = 0.4651 on the subset.

## Three passes

**Pass 1 — implement & verify.** Preregistration frozen before any holdout
(`registry/preregistration_cjxdir.json`, SHA in card). Restored pinned inputs
(`training_features` 4371c82e…, labels/sample hashes match manifest). Features →
holdout → final TIF → novelty → phase-null → run card → site page. Unit tests
(`tests/test_cjx.py`, synthetic crossing vs straight edge) pass.

**Pass 2 — bug/assumption review (fixes applied).**
1. `enforce_open_lane` guards the *canonical* card; using it for a non-canonical
   lane would have dead-locked the runner — replaced with a lane-local equivalent
   that fails closed once `run_card_cjxdir.json` exists (verified: re-run exits 2).
2. First novelty scan compared the candidate against **itself** (its own TIF lives
   under `archive/`) giving a spurious 1.0 — excluded `archive/g79_cjxdir/` and re-ran;
   all published novelty numbers are from the corrected scan.
3. HTML template typo (`meta` tag missing `<`) fixed before generation.
4. Writer output files were mode 0600 — chmod 0644 (bytes/hash unchanged).
5. Verified: per-fold budgets/emitted exact; withheld counts equal the canonical
   draws (11,321/11,342); H33/D2.8 restored hashes equal the pinned remeasurement;
   vendor `dot_overlap` vs in-loop EDT agree to <1e-9; surfaces finite, rank range
   (0,1], zero outside footprint-band-valid cells (3,061 invalid in-footprint cells
   per band median-filled, recorded in `evidence/cjxdir/feature_receipt.json`).

**Pass 3 — requirements re-check & quality.** Canonical `run_card.json`, registry
index/receipt, score ledger, shared `vendor/` code and the THVC artifact are
byte-untouched; CJX lives in `archive/g79_cjxdir/` + `run_card_cjxdir.json` +
`evidence/cjxdir/` per sibling-lane precedent, because the publication contract
allows only canonical artifacts under `docs/downloads/`. README gains a clearly
labelled CJX section (canonical decision line untouched, contradicted nowhere);
`docs/g79-cjxdir.html` is receipt-generated (no hand-typed numbers) with the
download/decision box at the top; AGENTS.md and IR-79-172 record the closed lane.
Every label distinguishes HOLDOUT-DTI from (absent) ORGANIZER-CONFIRMED scores.

## Limitations & next work (for a future session)

1. **Literal novelty gate is unsatisfiable for any nonempty candidate** (pinned
   witness covers 100% of allowed cells). Until a prospective shared protocol
   decision (the D-3 saturated-branch question) is taken by the owner, *no* lane
   in this program can honestly reach OK-TO-SUBMIT — this, not inspection, is the
   binding constraint. CJX would fail on holdout skill anyway.
2. Novelty scope is a 25-raster restored subset, not the frozen 1,108-raster
   inventory; a full re-scan needs the registry restore (large) and only matters
   for a lane that first passes holdout gates.
3. No DrivenData auth in-sandbox: data came from SHA-pinned public mirrors
   (consistency ≠ organizer authentication); no slot/eligibility visibility.
4. Best next scientific step per the ranked backlog is G79-BLC (bilateral
   contrast change-point) — only after limitation 1 is resolved prospectively,
   with its own preregistration. HFR additionally requires actually acquiring
   USGS DOI 10.5066/P9BZPVUC binaries outside this sandbox's egress allowlist.
5. Leaderboard figures in the prompt (0.2778 / 0.3195 / 0.4413) remain unverified
   historical reports / public observations, not artifact-linked receipts.

## Merge-time addendum: parallel-lane name collision (not a duplicate)

At PR time, `main` already contained a different lane also nicknamed G79-CJX
(parallel session, PR #102: tip-steered mag+grav coincidence, 37,654 dots,
`artifacts/cjx/...6a9bf2a2...tif`, sha256 `a422d9a0...`, also verdict negative).
Protocol rule 1 measurement of this lane against that raster
(`evidence/cjxdir/collision_measurement.json`): final-dot forward 3-px overlap
0.3474 (reverse 0.2139), surface top-20k 0.4456, exact shared dots 665 (3.3%),
Spearman ρ = 0.0657 (surface) / 0.0242 (dots) — all inside the 0.70 / 0.90
limits, so this is **not** a duplicate lane; it is a namespace collision between
two distinct implementations of the same backlog nickname. Because theirs
merged first, this lane is renamed **G79-CJX-DIR**; preregistration and
generated-evidence bytes are unchanged (files moved only), the TIF/ZIP bytes
and filenames are unchanged, and the original run card is preserved at
`evidence/cjxdir/run_card_as_generated_20261022.json`. The irregularity entry
for this session is renumbered at merge to the first free ID on the merged
main. Nothing about the scientific verdict changes.
