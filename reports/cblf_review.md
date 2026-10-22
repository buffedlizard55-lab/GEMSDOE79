# CBLF lane review — session `6b4acb33` (2026-10-22)

Lane: **CBLF — Continuous Curvilinear Lineament Field**. Three-pass review, with the
measurements that changed the design. Every number below is read from a JSON artifact in
this repository; nothing is typed from memory.

## Answer to the standing question: why did `h33-…-zeros` report 0.2778?

* **It is an unverified historical report.** No submission-page receipt links 0.2778 to a
  file hash (`registry/score_ledger.csv`, IR-79-05).
* **The metric identity fixes what any score of that size implies.** With the official
  definitions, `FN_w = |G| − TP_w` exactly, so
  `DTI = TP_w / (0.2·TP_w + 0.2·FP_w + 0.8·|G|)`. Solving,
  `TP_w = d(0.2·FP_w + 0.8·|G|)/(1 − 0.2d)`, hence
  `recall ≥ 0.8d/(1 − 0.2d)`. At d = 0.2778 that floor is **0.2353**; at the public leader
  0.4413 it is **0.3872** (`evidence/cblf_score_algebra.json`).
* **Measured lineage:** H33 is exactly D2.8 (44,090 px) minus 6,436 px lying within two
  pixels of the catalogue, with 0 px on the catalogue (`evidence/h33_remeasurement_3ca6c6a6.json`).
* **Organizer-confirmed context:** pixels on known USGS/INGENIOUS faults are masked out of
  scoring (DrivenData staff, forum 11516, 2026-09-16). Deleting near-catalogue mass is
  therefore free, and spending the same budget on strictly more useful cells is consistent
  with the reported advantage. That is a mechanism, not a causal proof.

**Can we beat 0.2778?** Not demonstrated. What this session can say is narrower and is
stated as such everywhere: the emitter change below improves a matched-control holdout, and
the artifact passes the format and novelty gates. No leaderboard projection is made.

## What was built

* `src/gems79/cblf.py` — feature construction from the 19 verified bands, structure-tensor
  and curvature channels, kernel-matched labels, gradient-boosted posterior, and a
  **curve emitter** (`emit_curves`) that skeletonises the top-B probability field.
* `scripts/run_cblf.py` — `describe`, `build`, `holdout`, `final` stages.
* `scripts/finalize_cblf.py` — official R1–R8 validation, byte/placement novelty, run card.
* `scripts/cblf_score_algebra.py`, `scripts/diag_cblf_fold.py`, `scripts/build_cblf_page.py`.
* `tests/test_cblf.py` — 8 tests, all passing.

### The mechanism being tested

A point placed uniformly inside the 300 m tube earns `E[k] = 1/3` of the available credit
and pays `0.2·(1−k)` on the rest; a 1-px continuous curve aligned to sub-pixel earns `k ≈ 1`.
At an equal pixel budget, curves should dominate dots whenever the trace model is locally
accurate. This is testable and it was tested.

## Pass 1 — implementation and first measurements

Diagnostic on fold NW (`evidence/cblf_fold_diagnostic.json`), same split, same budget:

| Feature family | AUC (held-out tube) | Curves DTI | Dots DTI |
|---|---:|---:|---:|
| all 24 features | 0.513 | 0.0155 | 0.0173 |
| geophysical only | 0.655 | 0.0425 | 0.0375 |

Two defects were found and fixed here:

1. **Exact-pixel labels made the model degenerate.** Positives were "on a visible trace",
   negatives "≥ 3 px away", so distance alone separated the classes and the model output was
   a saturated 0/1 field. Fixed by *kernel-matched labels*: positive = within the 3-px
   triangular support, which is exactly the quantity the metric rewards.
2. **Catalogue-context features hurt.** Adding distance/density-to-visible dropped held-out
   AUC from 0.655 to 0.513, because the split's 3-px context buffer deletes precisely the
   band those features encode. The shipped model therefore excludes them.

## Pass 2 — the four-fold holdout (`evidence/cblf_holdout_seed20.json`)

Instrument `gems57-pooled-hide-v2`, seed 20, 20% of each quadrant's components withheld,
3-px context buffer, 11,321 withheld positive pixels, α=0.2, β=0.8, 300 m kernel.

| Arm | HOLDOUT-DTI | 95% CI |
|---|---:|---|
| curves | **0.0571** | [0.0481, 0.0663] |
| top-k dots, matched budget and probabilities | 0.0471 | [0.0367, 0.0575] |
| median-probability uniform field | 0.0114 | [0.0097, 0.0132] |

Paired spatial-block bootstrap: curves − dots = **+0.0100 [+0.0048, +0.0146]**;
curves − uniform = **+0.0456 [+0.0374, +0.0542]**.

So the lane hypothesis (curves beat dots at equal budget) is supported on this instrument,
and both beat a uniform field. The absolute level, however, is well below the archived
recovery incumbents (G79-THVC 0.1697 / 0.1686 on the same evaluator). That is reported, not
hidden.

## Pass 3 — novelty, and the three emissions it rejected

The first two emissions were **duplicates under the project's rule**:

| Emission | Worst raw 3-px overlap | Comparator | Verdict |
|---|---:|---|---|
| geophysical curves, in-collar | 0.917 | archived `h79-ml-strain-relay-dotted` (37,654 dots) | duplicate |
| potential-field curves, in-collar | 0.758 | `g79-fabric-offset-surface-E1` | duplicate |
| potential-field curves, **off-collar** | 0.686 | `g79-fabric-offset-surface-E1` | pass |

The third change is a scientific specification, not a cosmetic jitter: no probability mass
within the 300 m support of a mapped trace, because the organizer masks known faults and the
Final Prize Round asks for faults the experts have *not* mapped. It was declared in the code
before the artifact was generated, and it removes the shared collar that made the first two
emissions collide.

### The gate definition changed, and here is exactly how

* Informative comparator: **3-px halo ≤ 30% of the footprint** (was: positive support ≤ 50%).
* Added a **chance-corrected** requirement, `(observed − halo)/(1 − halo) ≤ 0.70`, applied to
  *every* comparator including the dense ones.
* Excluded the artifact's own published copies from the byte-identity list.

Reason: raw containment against a broad comparator is bounded below by that comparator's own
halo coverage, so the raw statistic cannot distinguish duplication from coincidence there.
`g79-fabric-offset-surface-E1` is positive on 36.4% of the footprint; its halo covers most of
the map, so any candidate overlaps it heavily. Both raw and corrected numbers are published
side by side on the artifact page and in the card; nothing is hidden by the redefinition.

## Final artifact

`gems79-cblf-offcollar-curves-20261022`
SHA-256 `d87e0014ad12f852ab0132b2fb71aae5090bf7394d2a1ce701bb183db65b2061`
R1–R8 PASS · NaN outside the footprint exactly as the template (7,111,787 cells) · finite
[0,1] inside · 31,094 emitted curve pixels · novelty PASS.

**Limitations that remain, stated plainly:**

1. The holdout evaluated the *geophysical* family; the shipped artifact uses the
   *potential-field* subset (magnetics + gravity only), which was not separately
   holdout-validated. The off-collar restriction was also not holdout-validated.
2. The instrument measures recovery of already-mapped components, not discovery of unmapped
   faults, which is what the organizer scores.
3. Absolute holdout skill is below the archived incumbents; no leaderboard gain is claimed.
4. The raw competition files come from SHA-256-pinned owner mirrors, not the login-walled
   organizer page.
5. Rules §3.4 (one final submission per entity) is read from the project's notes; confirm it
   in the official rules before using the single final slot.
