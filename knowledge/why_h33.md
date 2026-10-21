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
validated detector. We explicitly do not invent a HOLDOUT-DTI or CI, and do not
claim this lane is better or worse scientifically than the incumbent.

## Next decision, not another submission gamble

Resolve the protocol/registry ambiguity through an explicit authorization
before any new scientific experiment. Then require whole-component buffered
hide-and-recover, feature-alone leakage canaries, a matched reproduction of the
incumbent, paired spatial confidence intervals and literal novelty checks. The
separate selector—not this pipeline—may consider a weekly slot only after those
gates pass. A public leaderboard value alone never authorizes promotion.
