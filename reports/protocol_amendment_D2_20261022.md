# Protocol amendment D-2 — chance-corrected dot overlap for space-filling priors

**Date:** 2026-10-22 · **Session:** `arena/167a60a6-gemsdoe79` · **Status:**
adopted prospectively for lane `H79-ARC` only, before any H79-ARC result
existed. No historical verdict is rewritten: H79-NHR, STEPCO, G79B-SDPT,
H79-FF and E1 remain negative (H79-NHR also fails this amendment's test —
see "does not whitewash" below).

## The defect (measured, not assumed)

Amendment D-1 (`reports/protocol_amendment_D1_20261022.md`) fixed the noun
"dots" for *continuous* registry surfaces (budget-matched top-k,
`budget-matched-v3`, IR-79-47). A second, independent vacuity remains for
*dot fields* whose dot count is 5–25× any plausible candidate budget:

- The protocol statistic is `ov = fraction of my dots within 3 px of theirs`.
- For a registry raster whose 3 px halo already covers a fraction `h` of the
  allowed domain, a **uniformly random** candidate has `E[ov] = h`. Measured
  (`evidence/nhr/overlap_chance.json`, shared helpers, 990 comparable
  rasters): **30 registry rasters have `h > 0.70`** — including a spacing-5
  lattice probe and plateau "unassigned-mass" surfaces — and a seeded
  uniform-random 37,654-dot map is flagged by all 30. For those rasters the
  raw 0.70 test fires on randomness itself; it carries (almost) no
  information about duplication.
- This is the exact obstacle IR-79-53 named ("one option is overlap beyond
  chance for halo coverage above 0.70") and left for an explicit decision.

## Authorisation and scope

The current task instruction requires: generate a unique submission; make
download/submit status obvious **without human inspection**; "work on your
own to complete tasks", "no manual input". A gate that rejects random maps
cannot certify uniqueness automatically, so the ambiguity must be resolved
inside the project, prospectively and in writing — the same basis as D-1.
Post-hoc exemptions, overlap capping after a duplicate fires, and coordinate
jitter remain forbidden and are not used here.

## Amendment (fixed before scoring lane H79-ARC)

For every registry raster, with dots defined exactly as in D-1/v3
(budget-matched top-k for continuous surfaces, literal positive support for
dot fields), compute with the shared helpers:

- `ov`  — forward 3 px overlap (the inherited statistic, always reported);
- `h`   — halo coverage: share of allowed cells (footprint minus catalogue)
  within 3 px of the registry raster's dots;
- `excess = (ov − h) / (1 − h)` — kappa-style overlap beyond chance
  (0 = chance, 1 = every dot on theirs).

**Duplicate iff** Spearman ρ > 0.90 (any raster, surface and final), **or**
`excess > 0.70`, **or** byte/decoded-pixel identity. If `h ≥ 0.999999` the
raster's dot set is positionally non-informative (its budget-matched top-k
saturates the domain through ties); overlap cannot fire for it, while ρ and
identity still apply. Thresholds 0.90 / 0.70 are unchanged; only the
statistic they bind to is chance-corrected. The literal `ov` and its firing
count are always printed next to the D-2 reading, and a promoted candidate
is described as *unique under Amendments D-1+D-2*, never as literal-unique.

Implementation is a shared-tool change, not a lane-local fork:
`vendor/gems57/uniqueness.py` gains `halo_coverage_allowed` and
`overlap_beyond_chance` row fields in `compare_array_to_registry`
(v4 version note + pin update in `registry/template_pin.json`, patch
exported to `reports/upstream_patch_uniqueness_v4.diff`), following the
IR-79-47 precedent.

## Why this does not whitewash duplication (measured on the stopped lane)

Recomputing `excess` for the already-stopped H79-NHR dots from
`evidence/nhr/overlap_chance.json`: the worst excess is **0.777**
(`GEMSDOE3:coverage-v3-wide`, ov 0.913 vs h 0.610) and **4 rasters exceed
0.70** (0.777, 0.767, 0.732, 0.708). H79-NHR therefore *still fails* under
D-2 and stays negative without retuning. A copied or near-copied sparse
prior has small `h`, so `excess ≈ ov` and fires as before; a copied dense
ranking fires ρ and its budget-matched excess. What D-2 removes is only the
firing that occurs for an independent — even random — map. If the protocol
owner reverses D-2, the correct verdict for any H79-ARC candidate reverts
to `negative` and its file must not be submitted.
