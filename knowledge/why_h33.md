# H33 Raster Forensics, Unverified Score Reports, and G79-THVC HOLDOUT-DTI

## Executive Answer

1. **What `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`) actually is (byte-level proof):**
   Hash-verified byte comparison (`scripts/analyze_h33.py`, output in `evidence/h33_forensics.json`) proves that `H33` (`sha256: b3cd7386...`) is **not** a newly trained model. It is **pixel-for-pixel identical** to the earlier `D2.8` binary Poisson-disk dot submission (`44,090` isolated `1.0` pixels, `sha256: f872c184...`) with **all `6,436` dots at Euclidean distance `<= 2.0 px` (`200 m`) from `existing_faults.tif` set to `0.0`**, leaving exactly **`37,654` binary `1.0` pixels** (`0` pixels outside `D2.8`, `0` 8-neighbour adjacent pairs).
2. **A plausible, unconfirmed metric mechanism for the reported D2.8/H33 difference:** The commonly reported values are D2.8 `0.2600` and H33 `0.2778`, both **UNVERIFIED HISTORICAL REPORTS** without a receipt binding either score to the inspected bytes. Under the official **Distance-Weighted Tversky Index (`DTI`)** with triangular kernel $k(d)=\max(1-d/300\text{ m},0)$, $\alpha=0.2$, $\beta=0.8$:
   $$\text{TP}_w = \sum_{y \in \mathcal{T}} \max_{x \in \mathcal{F}} p(x)\,k(\|x-y\|), \qquad \text{FP}_w = \sum_{x \in \mathcal{F}} p(x)\Big(1 - \max_{y \in \mathcal{T}} k(\|x-y\|)\Big)$$
   The metric's numerator pools maximum kernel credit while false-positive mass is summed, so thinning redundant predictions can plausibly help. If the reported score pair is correctly associated, removing the `6,436` D2.8 dots within `<= 200 m` of mapped faults could have reduced false-positive cost; it could also remove credit for nearby unknown faults. The exact byte relation does **not** prove which effect occurred or establish causation. Earlier dense-map values (`0.06–0.12`) are also historical reports, not new measurements in this review.
3. **Score Provenance & Leaderboard Reconciliation (`0.2778` vs `0.3195` vs `0.4413`):**
   - `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`: **UNVERIFIED HISTORICAL REPORT** from the prompt ledger. A separate dated public-leaderboard observation records the same numeric value for a participant, but no submission-page receipt links that participant, score, or file hash to this H33 raster; the participant's rank is time-dependent.
   - `0.3195` in one older prompt paragraph: **stale earlier snapshot** superseded by later public submissions.
   - **`0.4413` (`xiaofanhu`, Rank #1)**: an **OFFICIAL PUBLIC LEADERBOARD OBSERVATION** recorded in `knowledge/official_sources.json` (ID `DD-LEADERBOARD`, observed date `2026-10-22`). The page was not freshly fetched in this review. **No candidate in this repository has an `ORGANIZER-CONFIRMED` submission-page receipt**, and a public leaderboard observation is not this candidate's score.
4. **What do the existing G79-THVC spatial holdouts establish?**
   The canonical card records higher `HOLDOUT-DTI` than the fold-fair H33 analogue on both seeds. Those are useful offline hide-and-recover results; they do **not** establish a competition leaderboard score, do not prove that a score above the unverified H33 `0.2778` would be achieved, and do not establish organizer acceptance. The results below are copied from the existing card/evidence and were not recomputed in this review. Evaluator: `gems57-pooled-hide-v2`; whole-segment hide-and-recover, exact visible-fault masking, and 1,000-draw 20 km block-bootstrap 95% CIs.
   - **Seed 20 (`n = 11,321` withheld positive pixels):** H33 control **`HOLDOUT-DTI = 0.0961`** (95% CI `[0.0831, 0.1090]`); G79-THVC **`HOLDOUT-DTI = 0.1905`** (95% CI `[0.1741, 0.2069]`); paired difference `+0.0944` (95% CI `[+0.0785, +0.1100]`).
   - **Seed 30 (`n = 11,342` withheld positive pixels):** H33 control **`HOLDOUT-DTI = 0.0989`** (95% CI `[0.0854, 0.1128]`); G79-THVC **`HOLDOUT-DTI = 0.1944`** (95% CI `[0.1774, 0.2126]`); paired difference `+0.0955` (95% CI `[+0.0792, +0.1122]`).

---

## Byte-Level Forensics of `D2.8` vs `H33`

All counts below are **exact raster measurements** reproduced deterministically by `.venv/bin/python scripts/analyze_h33.py` (`evidence/h33_forensics.json`):

| Measured Quantity | Exact Value |
|---|---:|
| `D2.8` (`d28-zeros`) positive pixels (`value == 1.0`) | `44,090` |
| `H33` (`h33-h33-2-b2-...-zeros`) positive pixels (`value == 1.0`) | `37,654` |
| `H33` pixels not present in `D2.8` | `0` |
| `D2.8` pixels removed in `H33` | `6,436` |
| Pixel disagreements with `(D2.8 > 0) & (dist_to_catalogue > 2.0 px)` | `0` |
| `H33` positive pixels with an 8-neighbour positive | `0` |
| `H33` median distance to `existing_faults.tif` | `19.6469 px` (`1.965 km`) |
| Share of `H33` dots `> 1.0 km` from `existing_faults.tif` | `69.83%` |

### Cross-repository lineage across 16 scored landmarks and 11 post-snapshot siblings (`evidence/family_lineage_forensics.json`)

Reproduce from actual immutable Git blobs with `scripts/analyze_family_lineage.py`
([`evidence/family_lineage_forensics.json`](../evidence/family_lineage_forensics.json)).
Across the 103 scored submissions in `registry/score_ledger.csv` (all labelled
`UNVERIFIED HISTORICAL REPORT`), direct pixel-level comparison against `H33` (`37,654`
dots) and `D2.8` (`44,090` dots) separates the family's top reported scores
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
| `GEMSDOE76` | `gems76_h76_3_geotherm_tilt_axial_submod…` | 37,654 | 1,503 (4.0%) | 0.5220 | 0.3880 | 0 | 0.1555 / 0.2194* | Independent tilt-angle axial worm + submodular 300 m cover (*see `IR-79-86`) |
| `GEMSDOE77` | `gems85-h85-edti-collar35-skel-r33…-zeros` | 201,260 | 3,012 (8.0%) | 0.2108 | 0.7861 | 0 | 0.0964 | Over-emitted (`201,260` positives) + over-pruned (`0` dots at `d_cat <= 300 m`) |
| `GEMSDOE74` | `gemsdoe74-triregime-radon-piedmont-37654…` | 37,654 | 695 (1.8%) | 0.2450 | 0.3194 | 0 | 0.0669 | Domain-restricted piedmont Radon subset loses range-interior / basin recall |

---

## Recorded G79-THVC HOLDOUT-DTI by structural regime

The archived `seed=20` per-regime comparison (`evidence/g79_thvc_results.json`) shows where this particular G79-THVC model scored differently from the fold-fair H33 control under the shared evaluator. These **HOLDOUT-DTI** measurements do not explain H33's reported public score, establish a causal geological mechanism, or predict organizer performance:

| Structural / Observation Regime (`seed=20`) | Withheld Fault Pixels (`n`) | `C2 H33` `HOLDOUT-DTI` | `EXP-79-2 THVC` (`d=2.8`) | `EXP-79-3 THVC` (Charnes-Cooper) | Multiplier vs `H33` |
|---|---:|---:|---:|---:|---:|
| **1-m 3DEP LiDAR Covered (`75.01%` of area)** | `8,337` | `0.0240` | `0.0460` | **`0.0511`** | **`2.13×`** |
| **Blind Non-LiDAR Gap (`24.99%` of area)** | `2,984` | `0.0145` | `0.0468` | **`0.0477`** | **`3.29×`** |
| **Alluvial Basin & Piedmont Conduits** | `6,419` | `0.0191` | `0.0520` | **`0.0496`** | **`2.60×`** |
| **Steep Mountain-Block Bedrock** | `4,902` | `0.0192` | `0.0385` | **`0.0445`** | **`2.32×`** |
| **Elastic Crack-Tip / Relay (`<= 1 km` along strike)** | `3,891` | `0.0398` | `0.0563` | **`0.0584`** | **`1.47×`** |
| **Far Blind Basin (`> 1 km` from any visible fault)** | `7,430` | `0.0140` | `0.0291` | **`0.0348`** | **`2.49×`** |

1. **Non-LiDAR regime:** A raster measurement in the archived holdout reports `1,291,341 / 5,167,373` in-footprint cells (`24.99%`) without the 1 m lidar-derived product. In that regime, the table's `HOLDOUT-DTI` is `0.0477` for G79-THVC versus `0.0145` for the H33 control. The feature stack contains a `lidar_present` gate and non-LiDAR channels; this comparison does not establish which channel caused the difference or generalize to the private test.
2. **Basin and piedmont regime:** Archived per-regime `HOLDOUT-DTI` is `0.0496` for G79-THVC versus `0.0191` for the H33 control. The model uses thermal, vent, alteration, gravity, terrain, and fault-geometry features. Their association with the holdout result is not evidence that any predicted pixel is a geothermal conduit or that a specific physical process caused the gain.
3. **Crack-tip feature family:** Archived ablations report `net_tip_fwd_35px` and `net_tip_x_grav_bdepth` as influential features in this holdout setup. Feature attribution is model-specific association, not proof of elastic stress transfer or causal geological interpretation.
4. **Placement ablation:** On the same archived posterior surface, the run card reports `HOLDOUT-DTI` `0.1697` to `0.1905` on seed 20 and `0.1686` to `0.1944` on seed 30 when comparing fixed spacing with the Charnes-Cooper placement step. This is a controlled offline ablation, not a public-score improvement.

### Review qualification (2026-10-22)

The lineage measurements identify shared pixels, not hidden-label precision or causal score effects. Architecture, calibration and pruning proposals above are hypotheses, not necessary or sufficient conditions for a leaderboard improvement. No organizer receipt for any `GEMSDOE79` raster exists. Public/user-reported historical scores must not be relabelled `ORGANIZER-CONFIRMED`.
