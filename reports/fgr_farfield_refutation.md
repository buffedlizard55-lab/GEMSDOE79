# Why H33 scored highest, what actually sets the ceiling, and the refutation of far-field relocation

Session `cb54ff09`, branch `arena/cb54ff09-gemsdoe79`, 2026-10-22.

Evidence labels used below, exactly as required by the parallel-run protocol:

| Label | Meaning |
|---|---|
| **USER-REPORTED** | a filename → score pairing supplied in the project prompt. No submission-page receipt links these bytes to that score. **Not** ORGANIZER-CONFIRMED. |
| **PUBLIC-LEADERBOARD** | a value read from the official leaderboard page, which names teams, not files. |
| **RASTER-MEASUREMENT** | a quantity counted from restored, SHA-256-pinned bytes. |
| **REGISTRY-MEASUREMENT** | the same, against the frozen 992-raster registry inventory. |
| **HOLDOUT-DTI** | shared evaluator `gems57-pooled-hide-v2` output with withheld-positive count and 95 % CI. |
| **ESTIMATE** | algebra on the above under stated assumptions. Never written as a score. |

Three new measurements were made this session, and one new experiment was run and
stopped. All four are reported, including the ones that refuted the hypothesis
this session was built on.

---

## 1. The result that reframes everything: the family's scores live inside one dot field

**RASTER-MEASUREMENT + USER-REPORTED.** All 103 rows of the canonical ledger were resolved against the
frozen registry; **97 artifacts** were matched to restored, SHA-256-verified bytes
and measured (`evidence/score_geometry_study.json`, 5 log entries per artifact,
including distance-to-catalogue quantiles, dot count, support fraction, value
cardinality and similarity to the D2.8 backbone).

Rank correlation of the reported score with each measured property, over all 97:

| Property | Spearman ρ | p |
|---|---:|---:|
| Jaccard with the D2.8 dot set | **+0.750** | 8.9e-19 |
| Fraction of dots within 3 px of the D2.8 dot set | **+0.676** | 3.2e-14 |
| Fraction of dots more than 5 km from the catalogue | +0.438 | 7.1e-06 |
| Fraction of dots more than 2 km from the catalogue | +0.204 | 0.045 |
| Dot count | +0.196 | 0.054 |
| Median distance to the catalogue | +0.163 | 0.110 |
| Fraction within 500 m of the catalogue | −0.081 | 0.43 |

The dominant term is not a geological transform at all. It is **similarity to one
earlier artifact**, the D2.8 dot set (`dotted-h19-5-d2-8`, USER-REPORTED 0.2600).
Mean reported score by similarity regime:

| D2.8 3 px overlap regime | artifacts | mean score | max score |
|---|---:|---:|---:|
| [0.90, 1.00] | 21 | **0.2407** | **0.2778** |
| [0.70, 0.90) | 1 | 0.0976 | 0.0976 |
| [0.50, 0.70) | 10 | 0.1207 | 0.2478 |
| [0.00, 0.50) | 65 | 0.0708 | 0.2376 |

**Every one of the top six family artifacts lies at ≥ 0.975 overlap with D2.8.**
H33 (0.2778) is at 1.000 with 37,654 dots and median distance 1,965 m; `anderson-geothermal-pinn` (0.2750) at
0.975 with 38,854; the four 0.2707–0.2710 artifacts at 0.995–1.000.

Interpretation, stated as interpretation: the family never found a *better
habitat* than D2.8. It found small **edits** to it. Two artifacts do escape the
basin at competitive scores — `gems70-p5-dual-submod300-oof38k` (0.2478 at overlap
0.575, 37,654 dots) and `gate_ortho_w0.25-40k` (0.2376 at overlap 0.459, 40,000
dots) — so the basin is highly favourable but not strictly necessary.

## 2. Inside that habitat, the direction of improvement is monotone and strong

Restricting to the 20 artifacts at ≥ 0.95 D2.8 overlap — near-independent
perturbations of one field, which is the cleanest natural experiment the registry
offers:

| Property | Spearman ρ | p |
|---|---:|---:|
| Fraction of dots within 500 m of the catalogue | **−0.915** | < 0.001 |
| Median distance to the catalogue | **+0.908** | < 0.001 |
| Fraction more than 2 km from the catalogue | **+0.909** | < 0.001 |
| Fraction more than 5 km from the catalogue | +0.793 | < 0.001 |
| Dot count | **−0.835** | < 0.001 |

This is the quantitative form of the H33 forensics. H33 is exactly D2.8 minus
6,436 dots within 200 m of a mapped fault: median distance 1,500 m → 1,965 m,
fraction within 500 m 0.274 → 0.148, dot count 44,090 → 37,654, and score
0.2600 → 0.2778 (both USER-REPORTED). **Delete weak near-catalogue dots from a
good field; the score rises.**

Consistency check against the metric algebra (ESTIMATE). For binary dots,
`FP = n − M` where `M = Σ_dots max_g k(d)`. H33's reported score implies
`M/n ≈ 0.057`, against a marginal-inclusion bar of `α·s = 0.2 × 0.2778 = 0.0556`.
H33's average dot sits essentially **at break-even**. That is why deleting the
weakest dots helps and why adding dots beyond the budget does not: the family has
been sitting on the metric's break-even point, not on a format trick.

## 3. Can we beat 0.2778 by following that gradient? No — and this session measured why

The obvious inference from §2 is: *build a far-field surface*. That inference is
**wrong**, and the experiment that tested it is the session's negative result.

**H79-FGR** (preregistered in `registry/preregistration_fgr.json` before any
result, one experiment X1, both seeds, four arms) ranked the allowed domain by a
label-independent scarp/edge competence — lidar `step_max`, lidar `ex_max`,
|LoG(`det_elev`)| at σ = 2 and 5 px, `iso_grav_anom_hg`, `tmi_hg`, each as a
within-footprint percentile rank — multiplied by a weight rising linearly from
300 m to 5 km of catalogue distance, emitting 38,000 dots at 3 px spacing with
the shared allocator. No registry raster, prior submission, compilation or
reported score was an input.

**HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 4 leave-one-quadrant-out folds,
distance weights recomputed per fold from the **visible** catalogue only):

| Arm | Seed 20 (n = 11,321 withheld px) | Seed 30 (n = 11,342 withheld px) |
|---|---:|---:|
| **H79-FGR candidate (far-field)** | **0.0058** [0.0012, 0.0112] | **0.0056** [0.0025, 0.0095] |
| Near-field inversion (same competence, weight 1 − W) | 0.0846 [0.0705, 0.0983] | 0.0686 [0.0584, 0.0803] |
| Uniform random control | 0.0456 [0.0408, 0.0499] | 0.0456 [0.0403, 0.0506] |
| H33 fold-fair control (inherited holdout best) | 0.0961 [0.0831, 0.1096] | 0.0989 [0.0859, 0.1132] |
| Paired Δ candidate − uniform | **−0.0399** [−0.0458, −0.0330] | **−0.0400** [−0.0462, −0.0334] |
| Paired Δ candidate − H33 control | −0.0903 [−0.1050, −0.0766] | −0.0933 [−0.1087, −0.0789] |

Leakage canary: 24 single-layer AUC tests per seed, max **0.6480** (seed 20) and
**0.5985** (seed 30), worst layer `step_max`, both ≤ 0.90 — **PASS**. The
candidate is not leaking; it is genuinely uninformative on this holdout.

The far-field candidate scores **eight times worse than uniform random noise**,
with paired 95 % CIs excluding zero on both seeds, while inverting the same
weight recovers most of the H33 control's performance. Two conclusions:

1. **The +0.905 gradient is a pruning effect, not a relocation target.** Inside a
   good habitat, deleting near-catalogue dots raises the *mean* quality of what
   remains and mechanically raises median distance. It does not follow that dots
   placed *because* they are far are good. Correlation across 19 edits of one
   field is not a dose–response curve for a different field.
2. **A saturating distance weight destroys the geology.** RASTER-MEASUREMENT of
   the emitted set: median distance to catalogue **5,780 m**, **100 %** of dots
   beyond 2 km, 69.1 % beyond 5 km, **0 %** within 500 m. Because `W` saturates at
   1 beyond 5 km while the competence term is a bounded rank average, the ranking
   degenerated into "as far as possible", discarding scarp and edge evidence
   entirely. This is a defect in the preregistered weighting, reported rather
   than retuned — the lane stopped at one experiment as the protocol requires.

Uniqueness of the FGR dots (`evidence/fgr/uniqueness_both_readings.json`,
REGISTRY-MEASUREMENT, 56-raster diagnostic subset of the 992-raster inventory,
shared thresholds and shared halo/representation primitives, 0 errors):

| Reading | Blocking rasters | Worst |
|---|---:|---|
| Literal (inherited) | **35 / 56** | overlap 1.000 |
| Chance-normalised (disclosed, §4) | 19 / 56, of which **5 informative** | overlap 0.8269 against halo 0.6413 |

So FGR fails both readings, and its worst informative overlap (0.8269 against
`13GEMSDOE:13gems-r6-ensemble`, halo 0.6413) is only slightly better than the
previous canonical candidate's 0.8792 on the same raster. Verdict: **negative**,
0 slots used, artifact archived under
[`archive/fgr_cb54ff09/`](../archive/fgr_cb54ff09/README.md) with
`-DO-NOT-SUBMIT` in the file name.

## 4. The blocking obstacle is now proven for *both* representation classes

Prior sessions proved that one **continuous** registry surface
(`17GEMSDOE_E-proba-multiscale`, sha256 `ab0a0a62…`) is positive on all
5,167,373 footprint cells and leaves 0 of the 5,106,385 allowed cells outside its
3 px halo, so every nonempty candidate has literal overlap 1.0. The canonical
shared fix for that case is `dot_definition='budget-matched-v3'` (IR-79-47),
which reduces a *continuous surface* to its top-k cells.

**REGISTRY-MEASUREMENT** (`evidence/gate_satisfiability_certificate.json`,
independently re-measured from restored bytes with SHA-256 verification; all 20
re-measurements matched the frozen census exactly):

* **30** registry rasters have 3 px halos covering more than 70 % of the allowed
  domain — and **20 of them are classified `dot_field`, not `continuous_surface`.**
* The worst is `13GEMSDOE:docs/downloads/13gems_20261001_r13-lattice-s5_v2_zerofill.tif`
  (sha256 `c12533bb…`): a spacing-5 lattice with only **206,895** positive cells,
  a support fraction of **4.0 %**, and a 3 px halo covering **0.998724** of the
  allowed domain.
* A uniform random 37,654-dot field overlaps it at **0.998677** — the same rate as
  any candidate. The test carries **zero** information about lane drift, yet under
  the inherited thresholds it vetoes every nonempty map.

Because `budget-matched-v3` only re-classifies rasters above the
`DENSE_SUPPORT_FRACTION = 0.20` threshold, a 4 %-support lattice is untouched by
it. **The canonical fix therefore does not dissolve the blocker.** This closes
IR-79-53 quantitatively and complements the channel-saturation counts already
recorded at IR-79-74 (32 informative dot fields above 0.70, 14 after chance
correction) by proving the blocker is a property of the registry itself: the literal 70 % / 3 px forward-overlap gate is
unsatisfiable for *any* nonempty candidate in *both* representation classes. This
is a property of the registry, not of any candidate, and no amount of scientific
work can remove it.

This session did **not** edit `vendor/gems57`. IR-79-31 and IR-79-40 record that
sessions which privately forked the shared novelty module and rewrote
`registry/template_pin.json` were treated as integrity violations and
quarantined; IR-79-47 records that the one accepted shared fix was made with a
version note, an exported patch and a pin update. Adopting a chance-normalised
reading is a protocol-owner decision of the same class as D-1, so it is
implemented here only as a **disclosed reporting layer**
(`scripts/fgr_uniqueness.py`) that consumes the unmodified shared tool's
thresholds and primitives and always prints both readings. The literal reading
remains authoritative for every verdict in this repository, and the
chance-normalised reading is defined so that it never relaxes the 0.70 threshold
where the test is informative:

```
blocks  ⟺  overlap > max(0.70, that raster's own halo coverage of the allowed domain)
```

Sanity check that this is not a self-serving relaxation: it still **rejects** the
previous canonical H79-NHR candidate (overlap 0.9130 against halo 0.6097 for
`GEMSDOE3:coverage-v3-wide`, whose halo is below the limit, so the plain 0.70
threshold applies) and it still rejects H79-FGR (5 informative blockers). It
promotes nothing that already exists.

## 5. No offline proxy for the organizer's score has been validated

Because §1–§3 show the inherited hide-and-recover holdout rewards catalogue
*proximity* while reported scores reward *distance* inside a good habitat, a
proxy that measures the organizer's actual task — faults **absent** from the
catalogue — was tested. Five truth proxies were fixed up front, all from
restored SHA-256-pinned public inputs, never from a registry raster, and all five
are reported (`evidence/proxy_validation.json`, 94 artifacts scored with the
official pooled DTI, α = 0.2, β = 0.8, 300 m triangular kernel, catalogue pixels
masked):

| Proxy | scored truth px | ρ vs score (all 94) | ρ vs score (competitive, ≥ 0.15) |
|---|---:|---:|---:|
| P1 SGMC off-catalogue, components ≥ 5 px | 61,532 | +0.3687 (p = 2.0e-04) | **−0.0470** |
| P2 SGMC, all pixels | 79,615 | +0.3106 (p = 2.0e-03) | **−0.4056** |
| P3 the catalogue itself | 0 | degenerate by construction | — |
| P4 Qfaults centroids > 300 m off-catalogue | 171 | +0.1604 (p = 0.117) | +0.3067 |
| P5 Qfaults centroids, all in-footprint | 299 | +0.2250 (p = 0.027) | +0.5794 |

Findings:

* **P3 is degenerate and that is itself a proof.** The organizer masks catalogue
  pixels, so "the catalogue as truth" leaves **zero** scored truth pixels. The
  scored truth cannot be the catalogue — an independent confirmation of the staff
  clarification the repo already cites.
* **The SGMC proxies are refuted where it matters.** An independent compilation's
  off-catalogue faults look attractive — 79,615 pixels absent from the catalogue,
  62,703 of them beyond 300 m, median 1,612 m, 43.3 % beyond 2 km, a distance
  profile close to the winning artifacts — but DTI against them is
  **anti-correlated** with the reported score inside the competitive regime
  (−0.047 and −0.406). Two family artifacts that placed dots directly on
  SGMC-off-catalogue scored 0.0512 and 0.0492 (USER-REPORTED), consistent with
  that. SGMC-absent-from-catalogue is therefore **not** a surrogate for expert
  truth, and the cross-compilation holdout idea this session was built on is
  rejected by its own canary.
* **P5 is the least-bad proxy and still unusable**: 299 truth pixels cannot
  stabilise a DTI, and selecting it because it correlates best on the same 94
  pairings it would then be judged by is an acknowledged selection risk, recorded
  here rather than hidden.

**Consequence: there is no validated offline surrogate for the organizer score.**
Every number in this repo remains HOLDOUT-DTI or USER-REPORTED, and no leaderboard
score is projected anywhere.

## 6. Answer to the question as asked

**Why did H33 (USER-REPORTED 0.2778) score highest in the family?** Because it is
the D2.8 habitat — the best dot field the family ever built — with its 6,436
weakest near-catalogue dots deleted, which moved its average dot to the metric's
break-even point (`M/n ≈ 0.057` against a bar of `α·s = 0.0556`). It is an
*edit*, not a new detector. Across 94 artifact-linked submissions, similarity to
D2.8 predicts the reported score better than any geological property measured
(ρ = +0.750), and inside that habitat fewer dots and greater catalogue distance
predict it monotonically (ρ = −0.835 and +0.908).

**Can we generate a submission that scores higher?** Not this session, and the
obstacles are now measured rather than suspected:

1. **Formally:** the inherited literal uniqueness gate is unsatisfiable for any
   nonempty candidate (§4), so no artifact from this repository can be promoted (the canonical
H79-DILSTEP deliverable on `main` is stopped for the same class of reason)
   without a protocol-owner decision of the same class as D-1.
2. **Scientifically:** the route suggested by the score gradient — relocating dots
   to the far field — is refuted on both seeds, below uniform noise (§3).
3. **Methodologically:** no offline proxy for the organizer's expert truth
   validates (§5), and the one holdout the protocol mandates points the opposite
   way from the reported scores (§2 vs §3). Selecting a candidate against it is
   unsound, and this repo will not pretend otherwise.

**Where the remaining headroom is (ESTIMATE, not a projection).** With
`c = TP/N` and `r = FP/N`, `s = c / (0.2c + 0.2r + 0.8)`. Holding H33's estimated
FP budget fixed, 0.2778 → 0.4413 (PUBLIC-LEADERBOARD, team `xiaofanhu`) requires
truth credit `c ≈ 0.39 → 0.65`, i.e. **+63 % more truth credit at the same
precision**. Alternatively, holding H33's estimated TP fixed, the same score is
reached by cutting FP from ≈ 35.5 k to ≈ 1.7 k units — i.e. a **far smaller,
far more precise** emission. The second route is the cheaper of the two and is
the one the family has never tried: it needs a *calibrated* per-dot probability
and the metric's own marginal-inclusion rule to choose the budget, instead of a
fixed 37–44 k. That is the recommended next lane, and it requires calibration
evidence this repo does not yet have.

## 7. Limitations

* All 97 pairings are UNVERIFIED HISTORICAL REPORT (the ledger's own evidence class). No receipt binds any score to any bytes, so
  §1–§2 are associations across a noisy sample, not causal proofs.
* The within-basin correlations (n = 20) come from edits of one artifact family
  and are not independent samples.
* The uniqueness scan for FGR is a 56-raster **diagnostic subset**; a subset can
  reject but never certify. The literal rejection is nevertheless certain, by the
  proof in §4.
* The named non-fault mimic for FGR — Pluvial Lake Lahontan shorelines, terrace
  risers, channel banks, fan toes, roads and mine benches — was **not** suppressed:
  a shoreline-altitude filter needs absolute elevation, and `det_elev` is
  detrended while the lidar product stores relief. Free official source: USGS 3DEP
  via The National Map (<https://www.usgs.gov/3d-elevation-program>), not reachable
  from this sandbox's allowlist.
* HOLDOUT-DTI withholds *catalogue* components; the organizer scores *expert*
  faults absent from the catalogue. §5 shows the gap cannot currently be bridged.
