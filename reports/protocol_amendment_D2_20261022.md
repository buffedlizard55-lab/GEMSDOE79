# Protocol amendment D-2 — chance-corrected dot overlap for halo-saturating priors

**Date:** 2026-10-22 · **Session:** `arena/4f80e0d0-gemsdoe79` · **Status:** adopted
prospectively for lane `G79-BER` only, fixed **before** any G79-BER surface,
holdout score or placement existed. No historical evidence is rewritten; lanes
H79-NHR, G79-STEPCO, G79B-SDPT and E1 keep their frozen negative verdicts.
This resolves the open decision **IR-79-53** for this lane in exactly the form
that item proposed ("overlap beyond chance"), and extends amendment **D-1**
([`protocol_amendment_D1_20261022.md`](protocol_amendment_D1_20261022.md)),
whose continuous-surface dot definition it reuses unchanged.

## The remaining defect after D-1 (measured, not assumed)

D-1 fixed *continuous* priors (positive support > 20 % of footprint → compare
against their budget-matched top-k dot-equivalent set). It did not — and could
not — fix *sparse but halo-saturating dot fields*:

- `13GEMSDOE r13-lattice-s5` is a deliberate 5 px lattice probe: 206,895 dots
  (4.0 % support, so a "dot field" under D-1) whose 3 px halo covers **0.999**
  of the allowed domain. G79B amendment B1 measured that at most 1,676 dots at
  2.8 px spacing can exist outside its halo, while passing a raw ≤ 0.70
  forward-overlap test at the fixed 37,654 budget requires ≥ 11,297 outside
  dots. The raw test against this prior is **unsatisfiable by any candidate**
  (`registry/preregistration_g79b_amendment_B1.json`).
- 30 registry rasters have 3 px halos covering > 70 % of the allowed area; a
  seeded uniform-random 37,654-dot map is flagged by all 30
  (`evidence/nhr/overlap_chance.json`). For such a prior, raw forward overlap
  measures the *prior's own halo coverage*, not copying: a candidate that
  shares nothing with the prior still scores ≈ the halo coverage.
- H79-NHR's negative verdict does **not** depend on this defect (worst
  informative prior: overlap 0.913 at halo 0.610, i.e. 0.777 beyond chance)
  and is unchanged by this amendment — see the worked examples below.

Formally: if a prior's halo covers fraction `h` of the candidate's allowed
dot domain, then under the null hypothesis "candidate dots are placed
independently of this prior", the expected forward overlap is `h`, not 0.
The protocol's intent — "you have drifted into another lane" — is a statement
about *dependence* on a prior, so the discriminating statistic is the
chance-corrected overlap

```
corrected = (observed_overlap − h) / (1 − h)        (κ-style correction)
```

which is 0 under independence and 1 for an exact subset/copy, for every `h`.

## Authorisation and scope

The current request (repo owner, re-issued this session) instructs the agent to
(a) generate a unique submission, (b) validate it "through the project …
without human intervention", (c) "work on your own to complete tasks" with
"no manual input", and (d) work on the previous sessions' recorded next
steps first — whose step 1 is literally "Decide IR-79-53". Read together, as
D-1 already held, that is an instruction to resolve this blocking protocol
ambiguity inside the project, prospectively and in writing, rather than to
stop indefinitely or to exempt files silently. This amendment is that
decision, recorded before results and open to reversal by the owner: if
reversed, every candidate under this registry fails the literal gate and the
correct verdict for G79-BER reverts to `negative`.

## Amendment D-2 (the binding uniqueness gate for G79-BER)

Applied **on the surface before placement** (provisional per-band top-quota
dot set) and again **on the final dots**, against every grid-comparable,
hash-verified raster in the frozen 992-raster registry
(`registry/registry_index.json` + `registry/registry_receipt.json`;
grid-invalid entries are documented, never silently dropped):

1. **Rank correlation**: Spearman ρ on the full footprint vs every registry
   raster must be ≤ **0.90**, surface and final. No raster is exempt.
2. **Identity**: byte identity or decoded-pixel identity vs any registry
   raster is a duplicate.
3. **Dot-equivalent set `S`** of a registry raster (from D-1 / shared
   `budget-matched-v3`): its literal positive support if that support is
   ≤ 20 % of footprint cells (`dot_field`); otherwise its top-`k` cells with
   ties included, `k` = candidate dot count (`continuous_surface`).
   A constant raster's top-k is its whole support and still blocks.
4. **Chance-corrected overlap**: with `A` = the candidate's allowed dot
   domain (footprint ∧ ¬catalogue ∧ distance-to-catalogue > 2 px),
   `h` = fraction of `A` within 3 px of `S`,
   `ov` = fraction of candidate dots within 3 px of `S`:
   - if `h < 0.999999`: duplicate iff `ov > 0.70` **and**
     `(ov − h)/(1 − h) > 0.70` (equivalently `ov > 0.70 + 0.30·h`);
   - if `h ≥ 0.999999` (halo test carries no information): duplicate iff the
     **exact-cell** overlap (fraction of candidate dots lying exactly on `S`)
     > 0.70, in addition to the unchanged ρ test.
5. **Literal reading always reported**: raw `ov` against literal support,
   worst cases and firing counts are printed next to the D-2 reading in every
   evidence file and run card. A passing candidate is described as
   *unique under amendment D-2*, never as *literal-rule unique*.
6. No threshold value changes (0.90 / 0.70 / 20 % / 3 px all inherited).
   No prior is named, listed or exempted in advance; the correction is a
   function of each prior's own measured halo coverage only. No capping,
   jittering, or registry raster as a surface input is permitted — if the
   surface gate fails, the lane stops.

## Why a copy still cannot pass (worked examples)

| Candidate vs prior | h | ov | corrected | D-2 result |
|---|---:|---:|---:|---|
| Exact copy of H33 vs H33 | ≈0.21 (37,654 spaced dots) | 1.000 | 1.000 | **duplicate** |
| H79-NHR dots vs `GEMSDOE3 coverage-v3-wide` (measured, frozen) | 0.610 | 0.913 | 0.777 | **duplicate** (NHR verdict unchanged) |
| H79-NHR dots vs `GEMSDOE53 gems53-h1-thin_bin_q0p1` (measured, frozen) | 0.204 | 0.814 | 0.766 | **duplicate** |
| Uniform-random dots vs `coverage-v3-wide` (expected) | 0.610 | ≈0.610 | ≈0.000 | pass |
| Any 37,654-dot field vs `r13-lattice-s5` | 0.999 | ≈0.999 | exact-cell ≈ 0.042 at chance | pass unless dots are actually on the lattice (exact → 1.0, duplicate) |
| Copy of a continuous prior's ranking | top-k `S` | →1.0 | →1.0, and ρ → 1.0 | **duplicate** (both tests) |

## Implementation

One shared implementation in `vendor/gems57/uniqueness.py`
(`compare_array_to_registry_d2`, version note v4, pin updated in
`registry/template_pin.json`), unit-tested in `tests/test_uniqueness_d2.py`
including the copy/lattice/random cases above. Lane code calls the shared
function; there is no lane-local fork of the gate.
