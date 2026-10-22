# Session review `778c4a96` — G79-SWER fixed swarm-excess structural ridge

**Date:** 2026-10-22  
**Branch:** `arena/778c4a96-gemsdoe79`  
**Decision:** **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**  
**Run card:** [`run_card_swer.json`](../run_card_swer.json)  
**New TIFF:** [`g79-swer-swarmridge-340574px-20261022T191501Z-36bdfde7-DO-NOT-SUBMIT.tif`](../artifacts/swer/g79-swer-swarmridge-340574px-20261022T191501Z-36bdfde7-DO-NOT-SUBMIT.tif)  
**TIFF SHA-256:** `e20be7471e3dab75a53bc75bd2e2b1618434903ea4c6dd273a59619f466c49aa`

## Executive finding

This session produced the requested **new, byte-distinct, automatically validated single-band GeoTIFF**, but the fixed scientific method was decisively negative:

- `HOLDOUT-DTI` (`gems57-pooled-hide-v2`) is **0.0117** `[0.0075, 0.0170]` on seed 20 (`n=11,321`) and **0.0113** `[0.0077, 0.0148]` on seed 30 (`n=11,342`).
- The equal-support uniform control is `0.0606 / 0.0610`; canonical G79-THVC is `0.1905 / 0.1944`. G79-SWER beats neither.
- All 72 single-feature/fold leakage canaries pass (`max symmetric AUC 0.5879 / 0.6118 <= 0.90`). This excludes one obvious leakage mode; it does not rescue a weak model.
- The pinned registry witness has absolute full-footprint Spearman `0.0262 <= 0.90`, but the candidate's forward 3-pixel overlap is exactly **`1.0000 > 0.70`**. The unchanged literal rule therefore says duplicate and stop.
- The file is **byte-new but not protocol-unique**. No competition slot was selected or used. There is no organizer receipt and no projected leaderboard score.

The literal preflight had already proved that every nonempty map must fail that overlap rule. Running the lane anyway was necessary only to reconcile the prompt's separate highest-urgency demand for a new TIFF. That ordering conflict is disclosed in the run card and irregularities ledger; it is not represented as protocol clearance.

## 1. Prospective hypothesis review

Five unimplemented hypotheses were ranked before code or results in [`research/hypotheses_778c4a96.md`](../research/hypotheses_778c4a96.md):

1. **G79-SWER:** dependent/independent swarm excess × coherent magnetic/gravity edges × positive transtension × cover.
2. **G79-PGDC:** porphyry dike-contact anisotropy × gravity-depth closure.
3. **G79-UGTH:** upward-continuation tilt-depth consistency × geothermal heat residual.
4. **G79-SRBR:** seismic ridge-break rupture endpoints.
5. **G79-VFA:** volcanic-fluid accommodation corridor.

Each entry names exact layers and transforms, a catalogue-missing rationale, distinction from implemented work, expected qualitative DTI leverage, implementation cost, a named non-fault mimic, and official/free data status. G79-SWER ranked first because all seven required bands were available in the SHA-256-pinned cached stack and because the interaction—not its scalar inputs—was unimplemented.

The fixed equation and thresholds were committed and SHA-256 locked before the experimental run in [`registry/preregistration_g79_swer.json`](../registry/preregistration_g79_swer.json). The hand-entered `registered_utc` field is not treated as an independently clock-derived receipt; Git commit `5b590a8` at `2026-10-22T19:11:46Z` is the authoritative before-result ordering record. The experiment did not fit labels, choose weights from holdout outcomes, or tune after seeing either seed.

## 2. Inputs, mechanism, and source boundaries

### Exact cached layers

The runner read only these bands from `data/raw/training_features.tif` (`SHA-256 4371c82e...`):

- B10 `deq_n100a15` — dependent/swarm earthquake density according to the INGENIOUS lineage audit;
- B16 `ieq_n100a15` — independent/background earthquake density;
- B3 `tmi_hg` — total magnetic intensity horizontal gradient;
- B18 `iso_grav_anom_hg` — isostatic gravity anomaly horizontal gradient;
- B7 `geod_shearrate` and B8 `geod_dilaterate`;
- B15 `depth_to_base_surf` — cover thickness.

The feature builder masks every nonfinite value and float32 sentinel (`<= -1e30`) before logarithms, derivatives, quantiles, or Gaussian smoothing. The shared valid mask contains `5,164,312` pixels, with `3,061` invalid pixels inside the organizer footprint.

The official-source boundary is explicit and claim-by-claim status is retained in [`evidence/swer/source_claims.json`](../evidence/swer/source_claims.json):

- The existing repository source ledger records the DrivenData task as fault mapping against expert labels absent from the public USGS catalogue, with `alpha=0.2`, `beta=0.8`, and 300 m support (`DD-PROBLEM-REVIEW`).
- USGS describes Quaternary catalogue traces as evidence-based surface-deformation features and simplified geometry (`USGS-QFAULTS-REVIEW`), supporting—but not proving—the buried-fault rationale.
- DOE GDR/INGENIOUS lists seismicity, magnetic, gravity, geodetic, and depth-to-basement layers as public CC BY 4.0 resources (`GDR-1391-REVIEW`).
- The official GeoDAWN release says airborne magnetic data support subsurface geologic interpretation and radiometrics support surface interpretation (`USGS-GEODAWN-REVIEW`). It does not validate this specific interaction.

### Metadata irregularity

Band 10's embedded GDAL description says “Distance to earthquake,” while the official INGENIOUS lineage and prior direct audit identify `deq_n100a15` as dependent/swarm density. This conflict was known before the lane and is preserved rather than silently rewritten. It weakens interpretation and is a plausible contributor to failure, although it does not change the measured raster or holdout result.

### Named mimics

Open-pit mine blasting, geothermal injection/production-induced seismicity, and mainshock aftershock halos can raise dependent-event density. Lithologic contacts and flight-line/processing artifacts can create unrelated potential-field edges. A structure-tensor ridge reduces isotropic-cluster response but does not prove fault origin.

## 3. Fixed transform

For the shared seven-band valid domain, each scalar is clamped by its valid P10/P90. The primary terms are:

```text
swarm = q(log1p(max(deq,0)) - log1p(max(ieq,0)))
edge  = sqrt(q(log1p(abs(tmi_hg))) * q(log1p(abs(grav_hg))))
edge_coherence = edge * structure_tensor_coherence(edge; sigma_gradient=1.5, sigma_tensor=4)
transtension = sqrt(q(max(shear,0)) * q(max(dilatation,0)))
cover = q(log1p(max(depth_to_basement,0)))

candidate = swarm^1.5
            * (0.20 + 0.80*edge_coherence)
            * (0.35 + 0.65*transtension)
            * (0.40 + 0.60*cover)
support = valid & swarm>=0.60 & edge_coherence>=0.35
```

There is no adaptive placement stage. The same normalized continuous surface is used for holdout and live export; mapped catalogue pixels and cells outside the footprint are zero in the TIFF.

## 4. Buffered whole-fault-segment holdout

The shared `holdout.buffered_component_draw` creates four whole connected-component folds with `buffer_px=3`, `boundary_px=12`. The shared evaluator masks visible catalogue pixels exactly and pools weighted TP/FP/FN with the 300 m triangular kernel. Because this method has no catalogue-derived features, there is no catalogue feature to recompute; the static physical surface is unchanged between folds.

| Arm | Seed 20 `HOLDOUT-DTI` [95% CI] | Seed 30 `HOLDOUT-DTI` [95% CI] |
|---|---:|---:|
| **G79-SWER primary** | **0.0117 [0.0075, 0.0170]**, n=11,321 | **0.0113 [0.0077, 0.0148]**, n=11,342 |
| Swarm-only control | 0.0126 [0.0095, 0.0160] | 0.0115 [0.0087, 0.0148] |
| Edge-only control | 0.0141 [0.0113, 0.0174] | 0.0157 [0.0128, 0.0184] |
| Equal-support uniform control | 0.0606 [0.0526, 0.0689] | 0.0610 [0.0533, 0.0688] |
| Canonical G79-THVC incumbent | 0.1905 [0.1741, 0.2069] | 0.1944 [0.1774, 0.2126] |

Intervals are 1,000-draw paired physical 20 km spatial-block percentile bootstraps, conditional on this catalogue, fixed folds, and method. They are not leaderboard intervals. The two seeds reuse the same geography and must not be added as independent samples.

### Scientific interpretation

The interaction is worse than each structural control and much worse than a random surface with equal positive support. Its 340,574 positive pixels accumulate `~94,400` weighted false-positive mass in each pooled evaluation while receiving only `~317–328` weighted true-positive credit. The seismic/edge/strain/cover conjunction therefore does not localize the held-out catalogue geometry at the DTI scale. Plausible reasons include:

1. earthquake-density and geodetic fields are spatially broad relative to a 300 m metric;
2. potential-field contacts are numerous and mostly lithologic, not faults missing from the catalogue;
3. high cover may identify basins but not a precise buried trace;
4. source/processing artifacts and anthropogenic seismicity can satisfy portions of the interaction;
5. the catalogue proxy may under-reward genuinely blind active structures, so this is a falsification against the declared holdout—not proof that no such structures exist.

No retuning, support reduction, alternate ratio sign, or placement pass was attempted after observing the result.

### Post-run boundary-gradient defect

Pass-2 inspection found that `masked_gaussian` correctly normalizes the convolution by valid weight but then zeros invalid cells before `np.gradient`. The zero discontinuity can create false structure-tensor contrast at invalid and footprint boundaries. The frozen TIFF is enriched `2.91x` within eight pixels of the 3,061 interior sentinels and `2.24x` along the inner eight-pixel footprint edge; those regions contain 2.37% and 4.37% of all positives, respectively ([diagnostic](../evidence/swer/boundary_diagnostic.json)). This is a post-run implementation diagnostic, not `HOLDOUT-DTI` and not another scientific experiment. It strengthens the negative decision. The closed lane was not repaired and rerun; a future preregistration must use valid-domain field extension or an explicit prospective boundary exclusion before gradients.

## 5. Why reported H33 was strongest, and whether SWER beats it

### What is measured

Independent raster forensics establish that H33 has `37,654` isolated binary dots and is an exact subset of the `44,090`-dot D2.8 map. It removes exactly `6,436` dots within two pixels of the mapped catalogue, has zero positive eight-neighbour adjacencies, and places `69.83%` of dots more than 1 km from the catalogue. These are raster measurements, not scores.

This geometry is well matched to the competition metric:

- truth credit uses maximum nearby predicted support, so several adjacent dots need not add truth credit;
- false-positive cost sums prediction mass, so redundant nearby predictions can still cost;
- uniform spacing reduces duplicate coverage;
- pruning the near-catalogue shell removes candidates where the known-fault mask and nearby well-mapped structure make novelty less likely, while retaining far-field coverage.

That provides a credible *conditional* reason H33 could outperform denser or redundant family maps. It does not establish that every pruned dot was false, that H33 caused the reported improvement, or that its geometry is optimal.

### Evidence classes

- **`0.2778`: unverified historical user report.** GEMSDOE32's own public page labels H33 UNSCORED; no organizer submission-page receipt links that value to H33's SHA-256.
- **`0.4413`: public leaderboard observation** recorded on 2026-10-22 for user `xiaofanhu`; it is not this repository's score and not an artifact receipt.
- **G79-SWER `0.0117 / 0.0113`: `HOLDOUT-DTI` only**, with evaluator, withheld counts, and intervals above.
- **ORGANIZER-CONFIRMED for G79-SWER: none.** No upload occurred.

Therefore G79-SWER is **not demonstrated to beat H33**. It loses even to the fold-fair H33 control in existing shared-evaluator receipts (`0.0961 / 0.0989`) and to the current G79-THVC holdout incumbent. No projection is offered.

## 6. New TIFF and automatic validation

The shared `vendor/gems57/submission_writer.py` wrote and round-tripped a TIFF, a ZIP containing exactly that TIFF, and a JSON receipt. The TIFF has:

- one float32 band;
- EPSG:32611;
- shape `3730 x 3292`;
- affine `[100, 0, 243350, 0, -100, 4508550]`;
- `12,279,160` finite values; 0 NaN; 0 infinity; no sentinel;
- min `0.0`, max `1.0`;
- zero positive values outside the footprint and on mapped catalogue pixels;
- `340,574` positive pixels;
- SHA-256 `e20be7471e3dab75a53bc75bd2e2b1618434903ea4c6dd273a59619f466c49aa`.

The SHA-256 does not match any hash in the pinned registry receipt. This proves byte distinction within that indexed inventory, not scientific novelty. The exact file's first pinned witness comparison is:

| Metric | Result | Limit | Decision |
|---|---:|---:|---|
| absolute full-footprint Spearman | 0.0262 | 0.90 | pass this criterion |
| candidate dots within witness's 3-pixel halo | 1.0000 | 0.70 | **duplicate / stop** |

The first duplicate ends the registry scan under the user rule. No partial scan is misrepresented as an all-registry correlation maximum; the maximum overlap is already mathematically fixed at 1.0.

## 7. Three review passes

### Pass 1 — implementation and verification

- Locked hypothesis and exact transforms before execution.
- Added sentinel-safe physical transforms in `src/gems79/swer.py`.
- Used the shared buffered holdout evaluator and shared writer without a private metric or output fork.
- Ran all single-feature canaries before trusting each seed's DTI.
- Generated one new TIFF and its exact ZIP/receipt; no competition submission occurred.

### Pass 2 — bug and edge-case review

- Tested constant/invalid quantile behavior, structure-tensor bounds, invalid-cell exclusion, preregistration hash locking, artifact/card identity, mode bits, and mandatory negative status.
- Re-ran the independent submission validator and ZIP byte round-trip.
- Found a shared operational defect: `mkstemp` left writer outputs at mode `0600`. The shared writer now applies `0644` before atomic commit; bytes and hashes are unchanged. The vendor pin and version note record this one prospective shared fix.
- Found the lane-specific boundary-gradient enrichment (`2.91x` sentinel-halo, `2.24x` footprint-edge). Because discovery occurred after the frozen negative run, it is documented as an additional rejection reason rather than silently repaired and rerun.
- Preserved the Band-10 metadata conflict, hand-entered preregistration timestamp limitation, and preflight/run ordering conflict as irregularities rather than smoothing them over.

### Pass 3 — full requirements recheck

- README and generated site put **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO** before historical material.
- One JSON run card contains hypothesis, mechanism, named mimics, DTI/CI/n/evaluator, registry correlation/overlap, raster SHA-256, full validator output, name/note, and `verdict: negative`.
- H33's report, public leaderboard observation, local holdout, and absent organizer receipt remain separate evidence classes.
- Five hypotheses retain exact layers, missing-fault rationales, distinctions, expected leverage, costs, mimics, and official/free availability.
- Runtime was 58.2 seconds; two planned experiments were represented by canary/control evaluation and fixed candidate evaluation; the three-experiment/two-hour ceiling was not exceeded.
- Zero weekly slots were selected or used.
- Final software verification: `566 passed`; `verify_project.py` PASS including 14 SWER-specific bindings; static site 12 pages / 287 local links PASS; download-check tests 12/12 PASS; rendered browser review 36 cases PASS; canonical `submission_status.py` retains expected exit 2 / blocked.

## 8. Limitations and next work

1. Do **not** tune or resubmit G79-SWER. The fixed hypothesis is negative and the lane is closed.
2. Do **not** upload the TIFF simply because local format passes. Literal overlap and holdout both fail.
3. Resolve the globally impossible literal overlap rule prospectively before another lane. Do not invent a candidate-specific exception.
4. Reconcile Band 10's embedded description against the authoritative source package before another dependent/independent seismicity hypothesis.
5. Correct invalid-boundary treatment prospectively—extend the normalized field through masked cells before gradients or exclude a declared halo—and test it before any new result. Do not retrofit G79-SWER.
6. Prefer much sparser, independently localized traces; broad seismicity/strain priors should modulate sharp evidence rather than define 340k positive cells.
7. Any future eligible lane must beat the current holdout incumbent on both declared seeds, pass both novelty criteria, and receive separate selector approval before account-side slot checks.

**Final outcome:** negative result delivered; new research TIFF available; submission prohibited.
