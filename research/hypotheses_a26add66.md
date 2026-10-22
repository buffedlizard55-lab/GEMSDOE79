# Conditional shortlist — review a26add66, 2026-10-22

**No scientific lane assigned or opened. No candidate evaluated.** These are
proposals, not measured improvements, new discoveries, or globally novel methods.
The literal preflight [refuses a new lane](../evidence/preflight_a26add66.json).
Ranking is qualitative expected research value under DTI and implementation cost,
not a numeric score projection. All three use existing feature families: no new
external dataset is necessary for an initial falsification test.

## Source and implementation boundary

The official [DrivenData description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
was read in both chunks during this review. It verifies the input families,
metric, task and format—not the physical hypotheses below. The
[USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
explains that magnetics constrain subsurface structure and radiometrics inform
surface geology; it also explicitly warns about variable terrain clearance.
That supports using independent nuisance controls, not a claim of fault detection.

All thirteen manifest inputs were restored and SHA-256 checked in this workspace
([receipt](../evidence/runtime_data_status_a26add66.json)). These are owner mirrors,
**not newly organizer-authenticated downloads**. The historical cache was recovered
with `prepare_data.py --reproduce` without modifying its receipt. Raw tags are not
authoritative scientific definitions: do not use ambiguous band 6 `tc`, band 10's
misleading distance tag, or interpret band 15 as sediment thickness without source
reconciliation. No proposal needs those bands or electrical conductivity semantics.

A source-text search of `src/gems79`, `scripts`, `research`, and `knowledge` found
no implementation of the exact spectral-admittance, gravity/terrain partial-
coherence, or excursion-set-persistence tests below. Related edge, cross-scale,
terrain and contact detectors certainly exist (THVC, DFSD, CJX, CJX-DIR, MDSC,
TDW); this is a limited repository-scope distinction, not proof of global novelty.
Prior backlog proposals can overlap conceptually. No registry novelty clearance is
claimed merely because the mathematical transform has a different name.

| Rank | Hypothesis, layers and physical signature | Why potentially missing from the catalogue | Difference from executed methods | Named non-fault mimic and falsifier | Expected DTI research value / cost |
|---|---|---|---|---|---|
| 1 | **Local magnetic–gravity spectral-admittance change point.** RTP (band 2) and isostatic gravity (13). In fixed, tapered windows, estimate cross-spectral transfer amplitude and phase in resolvable wavelength bands; identify a spatial change of that transfer relationship that persists across adjacent windows, rather than a high raw gradient. | A buried boundary juxtaposing rocks of different density and magnetization might yield a relationship change without a prominent surface scarp. It is not inherently a fault; independent corroboration is required. | CJX/CJX-DIR use spatial gradient coincidence/director junctions; MDSC uses magnetic depth/curvature. The proposed discriminant is a change of the *joint spectral relationship*, not either field's edge amplitude or a junction. | **Pluton or volcanic-unit contact**, flight-block seam and variable aircraft clearance. Require a gain over each field alone and phase-scrambled/cross-window nulls; reject survey-aligned changes and unstable phase estimates. | **Moderate but highly uncertain value; moderate cost.** Local spectra need enough support that 100 m pixels must not be confused with independent survey resolution. |
| 2 | **Terrain-conditioned gravity discontinuity.** Isostatic gravity (13), detrended elevation (12), elevation slope (19). Use local cross-spectra to remove only the gravity component coherent with terrain, with coefficients estimated on training blocks; detect persistent edges in the remaining component. | A density discontinuity under low-relief alluvium could persist after a terrain-correlated nuisance contribution is suppressed, potentially revealing a weakly expressed strand. This does not establish motion or permeability. | Existing terrain/geophysics ensembles combine features or suppress stripes. This is an explicit terrain-conditioned *partial-coherence residual*, evaluated against the same edge detector before conditioning. Isostatic correction is already applied: extra removal may harm real signal. | **Residual topographic correction**, lithologic contact or erosional basin margin. Require an improvement over unconditioned gravity; fail the idea if the residual is less stable across windows or simply erases real range-front signal. | **Low-to-moderate uncertain value; moderate cost.** No new DEM is needed for this exploratory residual; detrended elevation must not be used for hydrologic routing. |
| 3 | **Persistent open-versus-closed anomaly topology.** RTP (2) and gravity (13). Build excursion sets through predeclared quantiles; measure persistence of enclosed loops and open elongated boundaries, then test whether persistent open boundaries corroborated by the other sensor outperform closed contacts. | Some elongated buried discontinuities may be under-mapped relative to exposed range fronts. The hypothesis is a population-level discriminator, not the false rule that every open boundary is a fault. | Existing lineament/junction detectors use local derivatives and orientation. This proposal tests nonlocal excursion-set connectivity and threshold persistence. It is different from the already proposed terrain-saddle detector, but its predictive output might still duplicate a prior map. | **Caldera rims, pluton margins and clipped map edges.** Reject boundaries touching invalid-data/window edges; use synthetic closed-contact and sensor-independent nulls. Falsify if performance is entirely attributable to ordinary elongation or edge strength. | **Low uncertain value; moderate-to-high cost.** Connectivity and footprint-edge censoring are more complex than a gradient transform. |

## Validation plan — blocked, not performed

1. First resolve the literal registry rule prospectively for *all* lanes. Current
   finite-positive support of a registry witness covers every allowed cell; every
   nonempty proposal would have forward overlap 1.0, exceeding 0.70. Do not
   delete the witness, alter the rule locally, jitter dots, or restart a closed lane.
2. Assign one method paragraph and freeze window scales, features, controls and
   stopping criterion before results. Use the shared cache, evaluator and writer.
   An untouched geographical reserve is needed because this repository has already
   made many selections against its historical holdout.
3. Recompute all fitted nuisance/cross-spectral parameters on visible/training
   blocks only. Withhold whole fault segments with the shared buffer, derive any
   catalogue feature only from visible traces, mask visible pixels exactly.
4. Test each feature alone with the required AUC canary. Above 0.90 blocks trust.
   Check full surface novelty before dot placement; stop immediately on failure.
5. Use pooled HOLDOUT-DTI, `gems57-pooled-hide-v2`, alpha 0.2, beta 0.8, triangular
   300 m support. Report withheld-positive counts and spatial-bootstrap 95% CIs.
   Compare the incumbent and proposal on identical splits and budget; a convenient
   H33 control is not sufficient. No holdout number exists for these proposals.
6. Only after the predeclared performance gate passes: check final-dot novelty,
   official format including NaN exterior, file hashes and a <=140-character note.
   A separate selector, not this research review, can consider a slot. Maximum
   three experiments or two hours; this review ran zero experiments and used zero
   competition slots.
