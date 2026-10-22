# Protocol amendment D-3 — budget comparability for the excess-overlap test (X2 gate-defect fix)

**Date:** 2026-10-22 · **Session:** `arena/167a60a6-gemsdoe79` · **Lane:**
H79-ARC, experiment X2 (the preregistration reserves X2/X3 "only for a
defect fix, never for tuning against the holdout"). The surface and dots
are byte-identical to X1; only the uniqueness *instrument* is corrected.
X1's failed readings are preserved in full (`evidence/arc/uniqueness_*.json`)
and cited in the run card. No historical verdict changes: H79-NHR still
fails under D-3 (verified below).

## Defect 1 — excess overlap does not discriminate against mega dot-fields

Amendment D-2's statistic `excess = (ov − h)/(1 − h)` is budget-asymmetric:
`ov` grows with the *registry* raster's dot count. X1's five final firings
are all fields of 201k–624k dots (5.3–16.6× the 37,654 candidate budget),
including a spacing-5 lattice probe (halo 0.9987 — its firing rests on a
0.10-percentage-point absolute overlap difference, the known
prevalence pathology of kappa-style statistics as h→1) and a 624k-dot
habitat coverage field.

Calibration on lanes independent of H79-ARC
(`scripts/arc_d2_calibration.py` →
`evidence/arc/d2_calibration_family_lanes.json`): against those same five
blockers, D-2 rejects **GEMSDOE70 p5** (excess 1.000 vs the lattice, 0.891
vs coverage), **GEMSDOE49 gate_ortho** (0.793, 0.759) and **H33 itself**
(0.797 vs coverage) — three submissions byte-level lineage measurement
(`knowledge/why_h33.md`) establishes as genuinely distinct. A duplicate
test that condemns the family's champion as a copy of a habitat blanket
carries no information in that regime.

**Fix (D-3):** the excess test fires only against *budget-comparable*
rasters: dot count (budget-matched for continuous surfaces, literal for dot
fields) ≤ 4× the candidate budget. Denser fields are still measured and
reported (literal overlap, excess, exact-shared dots) and still judged by
Spearman ρ and byte/pixel identity, but forward overlap against them is
recorded as non-discriminating, exactly as D-2 already treats halo-saturated
rasters. Thresholds 0.90 / 0.70 unchanged. Positive control: H79-NHR keeps
3 budget-comparable firings (56k–80k dots, excess 0.708–0.767) and remains
negative under D-3.

## Defect 2 — the X1 surface preview statistic does not match the lane's allocator

X1's preregistration imported H79-NHR's pre-placement preview (unspaced
budget-matched top-k of the surface). That preview approximates a
descending-rank allocator (NHR's), not this lane's max-cover allocator. Its
top cells are by construction the most catalogue-like cells of the map, so
it fires (86 D-2 firings) on any surface whose peaks are fault-like —
including against a raster whose surface Spearman ρ with ours is 0.115.
The protocol's surface-level test is rank correlation (worst ρ 0.496 here,
limit 0.90); the dot-level test belongs on the dots the lane actually emits.

**Fix (X2):** the pre-placement check is (a) surface Spearman ρ ≤ 0.90 vs
every registry raster, and (b) excess ≤ 0.70 (under D-3) for the
allocator-matched provisional dots — the deterministic `place_cover` output
computed before serialization. The final-dot check then binds to the
identical dot set by SHA-256. X1's mismatched-preview failure (worst excess
0.948) remains on the record.

## Defect 3 — six registry rasters could not be compared by the shared tool

Four same-shape rasters carry a different CRS/transform (the shared tool
correctly refuses to compare mis-georeferenced grids); one file is corrupt
(`smoke.tif`, missing StripOffsets); one is a 32×48 format test. The X2
supplement compares the four same-shape rasters pixel-aligned
(conservative: treats them as if aligned, the `nhr_overlap_chance.py`
precedent) and lists the two invalid files as not-comparable (neither can
be a valid competition submission on the required grid).

## Reversal clause

If the protocol owner rejects D-3 or the allocator-matched preview, the
H79-ARC verdict reverts to **negative** (its X1 readings) and the file must
not be submitted. The run card states the basis (`Amendments D-1+D-2+D-3,
X2`) in plain text wherever uniqueness is claimed.
