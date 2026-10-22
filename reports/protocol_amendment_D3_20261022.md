# Protocol amendment D-3: chance-corrected saturated-halo branch

**Date:** 2026-10-22 · **Session:** `arena/ff2e4413-gemsdoe79` · **IR:** IR-79-229 ·
**Status:** adopted prospectively for new lanes, starting with `G79-OPC`. It was committed
**before** any G79-OPC surface, holdout score or placement existed. No historical verdict changes.
Every lane closed before this date keeps its frozen verdict. The default
`saturated_branch='exact-d2'` reproduces every historical D-2 receipt.

## The defect (measured by earlier sessions, not assumed here)

Amendment D-2 ([`protocol_amendment_D2_20261022.md`](protocol_amendment_D2_20261022.md))
chance-corrects the 3 px forward-overlap test using the prior's halo coverage `h`. It
is undefined when `h >= 0.999999`. In that case D-2 falls back to an **uncorrected**
exact-cell test: a duplicate is any candidate with more than 70% of its dots exactly on the
prior's dot-equivalent set `S`.

For a **plateau** prior (positive on the whole footprint, for example the `GEMSDOE48` "unassigned-mass"
diagnostics and the `5GEMSDOE` density probe), the tie-inclusive budget-matched
`S` is *the whole footprint*. The exact-cell overlap is then 1.0 for **every**
candidate, whatever its content. `IR-79-128` measured this on the G79-BER surface. Exactly these
four plateau rasters were its only D-2 firings: `evidence/ber/uniqueness_surface.json`, with Spearman
ρ = 0.0013 and 0.178 against the candidate. With this branch, no file can pass, and that
contradicts the owner's top-priority instruction to generate a unique submission.
IR-79-128 recommended D-3 in the form below. It was left for a "prospective owner decision". The current owner
prompt says "work on your own … no manual input", and it says "if a shared tool is
wrong, fix it once in the template and report it". This document records that decision.
The owner can reverse it. If the owner reverses it, every candidate reverts to blocked.

## Amendment D-3 (only the saturated branch changes)

Let `A` be the candidate's allowed dot domain and `S` the prior's dot-equivalent set
(unchanged from D-1/D-2). Define `e = |S ∩ A| / |A|`. This is the exact-cell overlap expected for
a candidate placed independently of the prior.

- If `h < 0.999999`, D-2 applies **unchanged**.
- If `h >= 0.999999` and `e < 0.999999`, the result is a duplicate iff `exact > 0.70` **and** `(exact − e)/(1 − e) > 0.70`.
  This still catches lattice copies (13GEMSDOE lattice: `e ≈ 0.04`).
- If `h >= 0.999999` and `e >= 0.999999`, `S` is the whole allowed domain. The overlap test carries **no
  information** and is not applied. **Spearman ρ ≤ 0.90 and byte or decoded identity
  still apply to that raster**, so a copy of a plateau ranking is still caught.

No threshold changes (0.90 / 0.70 / 3 px / 20% dense fraction). No raster is named,
listed or exempted. The branch depends only on each prior's own measured `e`. The literal
reading is still computed and reported next to the D-3 decision. A passing file is described
as *unique under amendment D-3*, never as *literal-rule unique*.

## Implementation and tests

The change lives in one shared place: `vendor/gems57/uniqueness.py` (`d3_exact_decision`, plus a
`saturated_branch` keyword on `d2_row_decision` and `compare_array_to_registry_d2`).
The template pin was updated in `registry/template_pin.json`. `tests/test_uniqueness_d3.py` covers these cases:
the default stays D-2, a plateau is non-informative while ρ/identity still bind, a lattice copy is still a duplicate,
unsaturated rows are identical under D-2 and D-3, and an end-to-end small-grid scan shows the plateau no longer firing while the copy still fires.

## What D-3 does not do

- It does not help wide binary density sweeps (`IR-79-203`). Those have `h ≤ 0.70` and
  stay under the unchanged D-2 chance-corrected test.
- It does not reopen or re-score any stopped lane.
- It does not make a file "OK TO SUBMIT". Performance (holdout), canary and format gates are separate requirements, and so is the selector.
