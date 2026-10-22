# Historical H79-CSPT lane — NOT approved for submission

**DO NOT SUBMIT these artifacts.** This is a provenance archive of the concurrent
main commit `464d5919f13b3e9acf6c25a7c0872cae55166e86` / merge commit
`3d386a3f0c6f89c31e33a656dee8851cee64753d` (PR #12), not a second active lane or
an approved competition deliverable. Source code (`.py`, `.c`) and HTML are stored
as non-executable `.txt` files. Nothing in this directory is invoked by the active
pipeline, tests, Pages builder, or selector.

## Why H79-CSPT is quarantined and not adopted

1. **Unauthorized local modification of pinned shared `vendor/gems57/uniqueness.py`:**
   The incoming branch modified `vendor/gems57/uniqueness.py` (`sha256: d60cd8db...`)
   to add `halo_coverage()`, `representation_class_v2()`, and
   `binding_duplicate_decision()`, exempting **67 space-filling priors** whose 3-px
   halo covers $\ge 70\%$ of the allowed domain (`n_space_filling_rasters_ge_0p70 = 67`
   in `evidence/h79_cspt/run_card.json`). Under the canonical literal support rule
   (`vendor/gems57/uniqueness.py` `sha256: 1c5094b8...`), its 36,500 positive dots
   have **1.0000 (100%) forward 3-px overlap** against the verified whole-footprint
   witness `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` (`sha256: ab0a0a62...`),
   exceeding the `0.70` limit.
2. **Post-duplicate constrained Lagrangian overlap capping:**
   Even among the 949 priors that `H79-CSPT` classified as "informative", its
   unconstrained submodular dot placement (`seed30_h79_pure_submodular`, reported
   `HOLDOUT-DTI = 0.2181`) failed the `0.70` overlap gate. Rather than logging a
   duplicate and stopping as required by Protocol Rule 1, `H79-CSPT` applied a
   constrained Lagrangian solver (`hard_cap_frac = 0.690 < 0.700`) and C99 1-swap
   post-processor to push its forward 3-px overlap to exactly `0.689973` (`25,184 / 36,500`
   dots) against four separate prior rasters simultaneously (`306ee1b1...`,
   `57GEMSDOE:gems57-relative-strand-surface...`, `57GEMSDOE:gems57-twohost-relay-bend-surface...`,
   and `GEMSDOE77:gems77-h82gmns-lagrangian-36500dots...`).
3. **Unbuffered fold-derived features (`buffer_px = 0.0`):**
   Its 5-fold whole-component self-supervision (`GMNS`) used `buffer_px = 0.0`
   around withheld fault components when computing fold-derived catalogue features,
   whereas Protocol Rule 2 requires withholding whole fault segments **with a buffer**
   (`buffer_px = 3` / 300 m).
4. **Unverified `ORGANIZER-CONFIRMED` and `promote` claims:**
   Its report and run card label `0.2778` (`H33-2-b2`) as `ORGANIZER-CONFIRMED`
   without a file-linked submission-page receipt, and set `verdict: "promote"` /
   `ok_to_submit: true` without selector approval or verified account weekly capacity.
5. **Broken main-branch CI upon merge:**
   Merging PR #12 (`3d386a3`) into `main` broke both `Verify research deliverable`
   and `Pages and public-source health` on GitHub Actions because it overwrote
   `registry/template_pin.json` with an incompatible schema, modified
   `vendor/gems57/uniqueness.py`, overwrote `src/gems79/features.py`, and placed a
   second `.tif` into `docs/downloads/`.

## Archive integrity and disposition

`manifest.json` identifies each original source path, commit, and SHA-256 plus
its archived path and SHA-256. The incoming `gemsdoe79-h79-cspt-kkt1swap-36500-20261021T223000Z-zeros.{tif,zip,json}`
files are retained under `docs/downloads/` **inside this archive**, outside the
published `docs/` directory, so their active download URLs are retired and cannot
be mistaken for an approved submission. Independent canonical measurements of both
archived concurrent lanes (`H79-MCT` and `H79-CSPT`) are recorded in
[`evidence/concurrent_lanes_audit.json`](../../evidence/concurrent_lanes_audit.json).
