# What actually explains H33, and what would justify claiming an improvement?

## Answer in one paragraph

The named H33 raster is not evidence of a newly trained geological model. The
actual downloaded bytes show it is **exactly a subset** of the earlier D2.8
prediction: **44,090 → 37,654** isolated binary pixels after deleting **6,436**
points within 200 m of the known catalogue. Sparse emission can remove
redundant false-positive mass under the organizer's maximum-cover metric.
Catalogue-flank pruning can also remove unhelpful known-fault echoes, although
its effect against hidden truth cannot be established from public labels. These
are defensible mechanisms, not a causal proof of the prompt's reported score.
A better result is possible in principle, but this run establishes **no
leaderboard improvement** and recommends **no submission**.

## Evidence, not website branding

All counts in this section are **RASTER-MEASUREMENTS, not performance scores**.
Reproduce with `scripts/analyze_h33.py`; exact sources, Git blobs and SHA-256
values are in `evidence/h33_forensics.json`.

| Measured object | Result |
|---|---:|
| D2.8 positive pixels | 44,090 |
| H33 positive pixels | 37,654 |
| H33 points outside D2.8 | 0 |
| D2.8 points deleted | 6,436 |
| Disagreements with `D2.8 & (distance_to_catalogue > 2 px)` | 0 |
| H33 positives with an 8-neighbour positive | 0 |
| H33 median catalogue distance | 19.6469 px, approximately 1.965 km |
| H33 positives farther than 1 km from the catalogue | approximately 69.83% |

### Cross-repository lineage across 16 scored landmarks and 5 post-snapshot siblings (`evidence/family_lineage_forensics.json`)

Reproduce from actual immutable Git blobs with `scripts/analyze_family_lineage.py`
([`evidence/family_lineage_forensics.json`](../evidence/family_lineage_forensics.json)).
Measuring bidirectional 3-px overlap (`forward_3px_overlap_with_h33` = fraction
of candidate positives within 300 m of `H33`; `reverse_3px_overlap_from_h33` =
fraction of `H33`'s 37,654 positives within 300 m of the candidate) and exact
catalogue-distance histograms reveals why the historical leaderboard stratified
into four distinct regimes:

| Repo | Submission artifact | Positive px | Exact shared w/ `H33` | Fwd 3-px vs `H33` | Rev 3-px from `H33` | `0 < d_cat <= 200 m` | Reported public DTI (unverified report) | Structural lineage class |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `19GEMSDOE` | `h19-5-powerlaw-budget-multiline-corroborated…` | 121,131 | **37,654 (100%)** | 0.8925 | **1.0000** | **17,326** | 0.1922 | Contiguous ridge ancestor (`3.22x` over-emission penalizes `0.2 * FP`) |
| `GEMSDOE25` | `dotted-h19-5-d2-8…` (`D2.8`) | 44,090 | **37,654 (100%)** | 0.8817 | **1.0000** | **6,436** | 0.2600 | `d ≈ 2.8 px` Poisson pin thinning (`-77,041` redundant ridge pixels -> `+0.0678`) |
| `GEMSDOE33` | `h33d-analog-tip-stepover-r30…` | 41,865 | 31,614 | 0.9264 | **0.9998** | **3,894** | 0.2632 | Partial near-catalogue halo prune of `D2.8` (`ov_d28 = 0.9970`) |
| `GEMSDOE31` | `h27-4-solo-d28…` | 40,199 | **37,654 (100%)** | 0.9539 | **1.0000** | **2,545** | 0.2708 | Exact intermediate subset `H33 ⊂ h27-4 ⊂ D2.8` (`-3,891` near-catalogue pins -> `+0.0108`) |
| `GEMSDOE28` | `h36-1-rung30-blind-r1…` | 37,660 | 26,248 | 0.9547 | **0.9988** | **2,353** | 0.2710 | `D2.8` clone (`ov_d28 = 1.0000`) with `2,353` near-catalogue pins |
| **`GEMSDOE32`** | **`h33-h33-2-b2…-zeros` (`H33`)** | **37,654** | **37,654 (100%)** | **1.0000** | **1.0000** | **0** | **0.2778** | **Complete `d_cat <= 200 m` prune of `D2.8` (`2,171` pins retained in `200 < d_cat <= 300 m`)** |
| `GEMSDOE36` | `anderson-geothermal-pinn-38854…-zeros` | 38,854 | **37,654 (100%)** | 0.9740 | **1.0000** | 0 | 0.2750 | **Exact superset of `H33` (`H33 + 1,200` extra dots -> `-0.0028` dilution)** |
| `GEMSDOE63` | `cvarlw-thin-s3p17-54864…-zeros` | 54,864 | 14,600 | 0.5504 | **0.9589** | 0 | 0.2303 | Superset-halo covering `95.89%` of `H33` within 3 px plus `17,210` extra pins |
| `GEMSDOE48` | `h59-cover-ds-belief-b2xh33d…` | 37,723 | 2,706 | 0.9150 | **0.9998** | 2,870 | 0.2296 | Re-weighted/jittered `D2.8`/`H33` derivative (`ov_d28 = 0.9885`) |
| **`GEMSDOE70`** | **`gems70-p5-dual-submod300-oof38k…`** | **37,654** | **1,797 (4.8%)** | **0.5484** | **0.4432** | **0** | **0.2478** | **#1 genuinely non-duplicate lane: dual OOF supervised ML + 300 m submodular cover + `200 m` prune** |
| **`GEMSDOE49`** | **`gate_ortho_w0.25-40k…-nan`** | **40,000** | **1,174 (3.1%)** | **0.4339** | **0.4239** | **0** | **0.2376** | **#2 genuinely non-duplicate lane: orthogonal gated supervised model + `300 m` prune** |
| **`GEMSDOE73`** | **`gems73-h73-mcsc-seamfree-blakely-37654dots…`** | **37,654** | **1,743 (4.6%)** | **0.4860** | **0.4633** | **0** | **0.1917** | **#1 pure unsupervised geophysical derivative: seam-free multi-scale Blakely potential ridges** |
| `GEMSDOE75` | `gems75-trlt-radon-loco-ridge…-zeros` | 36,800 | 1,739 (4.6%) | 0.4561 | 0.4729 | 0 | 0.1627 | Independent LOCO localized Radon ridge detector |
| `GEMSDOE76` | `gems76_h76_3_geotherm_tilt_axial_submod…` | 37,654 | 1,503 (4.0%) | 0.5220 | 0.3880 | 0 | 0.1555 | Independent tilt-angle axial worm + submodular 300 m cover |
| `GEMSDOE77` | `gems85-h85-edti-collar35-skel-r33…-zeros` | 201,260 | 3,012 (8.0%) | 0.2108 | 0.7861 | 0 | 0.0964 | Over-emitted (`201,260` positives) + over-pruned (`0` dots at `d_cat <= 300 m`) |
| `GEMSDOE74` | `gemsdoe74-triregime-radon-piedmont-37654…` | 37,654 | 695 (1.8%) | 0.2450 | 0.3194 | 0 | 0.0669 | Domain-restricted piedmont Radon subset loses range-interior / basin recall |

Three structural findings follow directly from these byte measurements:

1. **Every reported score above `0.2478` (`0.2600` to `0.2778`) comes from a single root surface (`19GEMSDOE` `h19-5`), not nine independent breakthroughs.** In particular, `GEMSDOE36` (`0.2750`) contains all `37,654` exact pixels of `H33` plus `1,200` additional pixels, and across `D2.8` → `h33d` → `h27-4` → `h36-1` → `H33`, near-catalogue dot counts at `0 < d_cat <= 200 m` drop monotonically (`6,436 → 3,894 → 2,545 → 2,353 → 0`) while reported public DTI rises monotonically (`0.2600 → 0.2632 → 0.2708 → 0.2710 → 0.2778`). Retain-band dots in `200 < d_cat <= 300 m` (`2,171` in `H33`; `2,227` in `GEMSDOE70`) preserve step-over/splay linkages, whereas widening the exclusion zone to `>= 300 m` (`GEMSDOE77` `0.0964`) erases fault-tip junction credit.
2. **Among genuinely non-duplicate models (`forward_3px <= 0.55` and `reverse_3px <= 0.48` vs `H33`), out-of-fold multi-modal learning + submodular 300 m cover (`GEMSDOE70` `0.2478`, `GEMSDOE49` `0.2376`) beats single-operator geophysical filters (`GEMSDOE73` `0.1917`, `GEMSDOE75` `0.1627`, `GEMSDOE76` `0.1555`) by `+0.05` to `+0.09` DTI — yet still trails the public leaderboard leader (`xiaofanhu: 0.4413`) by `-0.1935`.** Closing the `0.2778 → 0.4413` gap requires moving from pixel-local tabular features to multi-scale 2D spatial encoder-decoder architectures (`U-Net` / `ConvNeXt-UNet`, as in the official organizer baseline `drivendataorg/gems-prize-reference-solution`) trained end-to-end with pooled soft-kernel Distance-Weighted Tversky Loss (`alpha=0.2, beta=0.8, R=300 m`) on multi-kilometre 2D patches + 1 m LiDAR scarp rasters + positive-unlabeled prior calibration, followed by submodular 300 m cover selection and `200 m` catalogue pruning.
3. **Post-snapshot sibling audit (`GEMSDOE78`, `GEMSDOE80`..`GEMSDOE83`) reinforces why Decision D-1 must be resolved first:** `GEMSDOE82` published a second dense continuous surface (`surface_h82.tif`, `4,862,825` positive footprint cells out of `5,167,373`), confirming that under the literal `finite > 0` support convention multiple sibling repositories create universal overlap blockers unless the protocol owner explicitly authorizes `top-K` or thresholded support (`Decision D-1`).

The source website calls the file a high-ranked primary, but explicitly says it
has no organizer score receipt and also includes projected/live-mirror numbers.
We do not convert those projections into scores. The prompt's **0.2778 is an
UNVERIFIED historical filename-to-score report**. An official public leaderboard
observation also shows 0.2778 for a participant, but neither that number nor the
participant's identity proves which file or hash was uploaded.

## The precise metric argument

[Official formula](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric):

- `k(d) = max(1 - d / 300 m, 0)`.
- `TP = sum_truth max_prediction[p(x) k(d)]`.
- `FP = sum_prediction p(x) (1 - max_truth k(d))`.
- `FN = number_of_truth_pixels - TP`.
- `DTI = TP / (TP + 0.2 FP + 0.8 FN)`.

The [staff clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)
excludes **exact known-fault pixels**, not a 200 m buffer around them.
The [aggregation clarification](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2)
requires pooling terms first rather than averaging fold DTI.

A dot can cover several truth pixels. Therefore its marginal true-positive
credit `A` is **not generally bounded by** its own nearest-truth credit `q`.
For a new unit dot, its false-positive increment is `B = 1 - q`. If the current
score is `s`, adding it improves DTI precisely when

`A > 0.2 * s * (A + B)`.

Only in the special case `A = q` does this simplify to `q > 0.2*s`.
We do not use that special-case threshold as a universal claim. Removing a
redundant dot with negligible lost coverage but positive false-positive mass
can improve DTI; this is why thinning is plausible. But removing a useful dot
can hurt recall. Geometry alone cannot determine the hidden-truth trade-off.

The `-zeros` encoding is a **format policy**, not a scientific discovery.
Replacing outside-footprint NaN with finite zero does not add in-footprint
geological evidence. Without the rejected bytes and server receipt, neither
NaN nor a sentinel can be proven to have caused the user's earlier range error.
Our writer simply rejects nonfinite/out-of-range outputs, never clips them,
and checks the serialized result and single-TIFF ZIP.

## Why a larger score cannot be inferred from this family table

1. **Confounding:** many submissions inherit the same ranking or dot set.
   They are not independent scientific replications.
2. **Distribution shift:** withheld existing faults are not the organizer's new
   expert-labelled faults. High catalogue recovery may select familiar exposed
   faults and miss weak, covered structures.
3. **Multiplicity:** dozens of ideas and emission settings compared on one proxy
   can overfit that proxy even when each model is superficially cross-validated.
4. **Measurement limits:** a 100 m grid does not imply independent 100 m airborne
   observations. USGS reports Area 2 flight lines spaced 400 m apart. Fine-scale
   registration lags can reflect interpolation, levelling or flight geometry.
5. **Novelty gate degeneracy:** under the supplied literal support convention,
   one whole-footprint prior rejects every nonempty candidate. A filename or
   byte hash cannot resolve this.

## What this new lane did, and did not, establish

Four hypotheses were preregistered before implementation. E1 computes
opposite-side magnetic-gradient profile registration across an independent
gravity-gradient normal. It requires a nonzero lag to beat zero lag and retain
its sign at two offsets. This targets **marker displacement**, unlike the
inspected same-pixel cross-gradient and orientation-consensus methods. It is
only a hypothesis: an oblique intrusive contact or survey seam can mimic it.

The new numerical surface exists and was exported through the unmodified shared
writer. It is byte-distinct from the 992 restored registry files. The literal
pre-placement shared gate nevertheless reports 100% support overlap with a
verified dense prior. **Scientific work stopped before canaries, hide-and-recover
or dot placement**. The downloadable TIFF is negative-result evidence, not a
validated detector. We explicitly do not invent a HOLDOUT-DTI or CI in
`run_card.json`, and do not claim this lane is better or worse scientifically
than the incumbent on the official run card.

In a separate **post-stop offline diagnostic** (`evidence/post_stop_diagnostic.json`,
which does not alter `run_card.json` or `evidence/experiment_state.json`),
evaluating E1 under hypothetical Decision D-1 Option B (`top-37,654` overlap
`0.0119` vs E-proba) or Option C (`p >= 0.5` overlap `0.3046` vs E-proba) showed
that while E1 passes all 72 feature-fold leakage canaries (`max_symmetric_auc =
0.5872` on seed 20, `0.6162` on seed 30, both `<= 0.90`), its pooled `HOLDOUT-DTI`
(`gems57-pooled-hide-v2`) is `0.0474 [0.0390, 0.0552]` on seed 20 and `0.0466
[0.0388, 0.0543]` on seed 30—failing to beat its matched zero-lag edge control,
underperforming uniform random placement (`0.0504` / `0.0496`), and trailing the
fold-fair H33 control (`0.0961` / `0.0989`). Likewise, independent canonical
audits (`evidence/concurrent_lanes_audit.json`) of the two archived concurrent
lanes (`H79-MCT` in `archive/h79_mct_c26efec/` and `H79-CSPT` in
`archive/h79_cspt_3d386a3/`) confirm that both failed the literal `0.70` overlap
gate (`1.0000` overlap against `17GEMSDOE_E-proba-multiscale`) and relied on
unauthorized local dense-prior exemptions and post-duplicate constrained overlap
capping (`0.6800` and `0.6900`).

## Next decision, not another submission gamble

Resolve the protocol/registry ambiguity through an explicit authorization
before any new scientific experiment. Then require whole-component buffered
hide-and-recover, feature-alone leakage canaries, a matched reproduction of the
incumbent, paired spatial confidence intervals and literal novelty checks. The
separate selector—not this pipeline—may consider a weekly slot only after those
gates pass. A public leaderboard value alone never authorizes promotion.
