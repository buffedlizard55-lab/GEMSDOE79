# G79-CONJ — Conjugate cross-strike offsets + exact Dinkelbach DTI emission

**Lane:** `G79-CONJ` · **Verdict:** `promote` (selector-approved) · **Preregistration:** `registry/preregistration_g79_conj.json` (2026-10-22T14:19:20Z, before any result) · **Hypotheses:** `research/hypotheses_20261022_conj.md` (5 ranked candidates; CONJ = #1) · **Evidence:** `evidence/conj/` · **File:** `docs/downloads/gems79-g79conj-dinkelbach-37863dots-20261022T152806Z-ecbc7748-zeros.tif` (SHA-256 `96a715909aefa722a0f1a81d6658e68eb996f08a25f78c5b1483f513f2d93e80`, 37,863 binary pixels).

All scores below are **HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, spatially blocked hide-and-recover, Tversky α = 0.2 / β = 0.8, 300 m triangular kernel). No number here is ORGANIZER-CONFIRMED; this file has no organizer score until a receipt exists.

## 1. Why H33 reportedly scored 0.2778 (mechanism, not magic)

Byte forensics (`knowledge/why_h33.md`, `evidence/h33_forensics.json`) prove `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is exactly the D2.8 dot set (44,090 binary pixels) minus the 6,436 dots within 2 px (200 m) of the mapped catalogue: 37,654 dots, a strict subset, median catalogue distance 19.65 px (1.96 km), 69.83% beyond 1 km. The value 0.2778 is **user-reported**; no organizer receipt in this repository binds it to those bytes.

The Distance-weighted Tversky Index explains the win. For each withheld truth pixel, TP credit is the **maximum** kernel-weighted prediction within 300 m; FP cost is the **sum** of all predicted mass not credited. A dense corridor pays FP for every halo pixel while earning each TP once; a spaced binary dot field pays once per dot and can credit several truth pixels (ideal straight trace, 3-px spacing: ≈2.33 TP units per dot). Pruning the ≤200 m catalogue flank removes dots whose kernel mass mostly overlaps already-masked known faults. H33 is therefore best understood as metric-optimal *emission geometry* applied to a mediocre surface — which implies the remaining headroom is a better surface under the same emission economics.

## 2. The CONJ hypothesis

**Statement.** In Basin-and-Range extension, through-going normal-fault systems link across relay ramps and stepovers and are transected by cross-strike transfer (conjugate) faults whose positions are geometrically predictable from the *mapped* network: at segment-length-scaled cross-strike offsets from segment tips, on the down-dip side, at bends and at junctions. These structures are prime geothermal conduits (intersections maximise fracture permeability) and are systematically under-mapped because their surface expression is short, oblique to the dominant range-front trend, and easily buried by basin fill. A catalogue-distance model cannot express "0.5 segment-lengths cross-strike from that tip"; a network-geometry model can.

**Named non-fault mimic.** Shoreline terraces, road cuts and channel lineaments produce linear steps. CONJ controls this by construction: every channel is anchored to a real visible segment (its length, strike and dip side), so generic lineament energy away from the network scores zero.

**Difference from prior work.** GEMSDOE69-style geodesic corridor linkage and THVC crack-tip lobes propagate *along* strike. CONJ propagates *across* strike at length-scaled offsets and adds bend/stepover/junction geometry; the ablation below isolates its contribution from the shared 84-channel stack.

## 3. Method

- **Inputs (all SHA-256-pinned, official/free):** competition grids incl. `training_features.tif` band 15 (`depth_to_base_surf`), `labels.tif`, `existing_faults.tif`, `sample_submission.tif`; DOE GDR Submission 1391 INGENIOUS payloads (DOI `10.15121/1881483`, https://gdr.openei.org/submissions/1391); USGS 3DEP-derived morphology (https://www.usgs.gov/3d-elevation-program). Restored via the repository's pinned scripts; 13/13 raw inputs verified.
- **Channels:** the frozen THVC 84-channel static stack (reused, not forked) + 12 CONJ channels from `src/gems79/conj.py`: cross-strike offsets at 0.25/0.5/1.0 × segment length (down-dip side from the basement-depth gradient), bend curvature, stepover midpoints, junction density, length-normalised perpendicular distance, and related network scalars — all computed from **visible faults only** inside each fold.
- **Holdout:** shared `gems57` pooled hide-and-recover: whole fault segments withheld with buffer, catalogue-derived features rebuilt from visible faults, visible faults masked pixel-exactly, pooled DTI over 4 spatial folds, seeds 20 and 30 (n = 11,321 / 11,342 withheld positive pixels).
- **Emission:** Dinkelbach fractional optimisation of expected DTI (lazy greedy on the posterior, penalty-weighted, FP price λ updated every 1,000 dots; live run λ_fp ≈ 0.0301). Emission stops when marginal utility ≤ 0 (min 20k, cap 55k): live candidate stopped at **37,863 dots** (`marginal_utility_nonpositive`).
- **Leakage canary:** every feature alone, symmetric AUC per seed; max over 96 channels ≤ 0.8036 (threshold 0.90). Strongest new channel `conj_bend` (0.7844 / 0.7944) — informative, not leaking.

## 4. Results

| Arm | Seed 20 DTI [95% CI] | Seed 30 DTI [95% CI] |
|---|---:|---:|
| C0 uniform | 0.0497 | 0.0422 |
| C2 H33 fold-fair control | 0.0961 [0.0831, 0.1090] | 0.0989 [0.0854, 0.1128] |
| Previous best G79-THVC | 0.1905 [0.1741, 0.2069] | 0.1944 [0.1774, 0.2126] |
| ABL zero-CONJ (84 ch) | 0.2034 [0.1854, 0.2219] | 0.2248 [0.2057, 0.2432] |
| EXP-CONJ-2 (greedy) | 0.2337 [0.2148, 0.2533] | 0.2315 [0.2125, 0.2505] |
| **EXP-CONJ-3 (Dinkelbach)** | **0.2348 [0.2148, 0.2559]** | **0.2521 [0.2312, 0.2733]** |

Paired differences (candidate − ablation): **+0.0314 [0.0227, 0.0409]** (seed 20), **+0.0273 [0.0190, 0.0369]** (seed 30) — the 12 CONJ channels carry 15.7% / 12.9% of the total gain over the H33 control. Candidate − C2: +0.1387 [0.1219, 0.1564] / +0.1532 [0.1345, 0.1736]. All preregistered performance gates pass on both seeds. Emission choice (EXP-CONJ-3) was fixed by the preregistered seed-20 rule before seed 30 was run.

Live dot geometry: median distance to catalogue 671 m; 25.8% beyond 1 km; 0 dots on catalogue faults; 0 outside footprint; minimum distance 316 m (3.16 px).

## 5. Uniqueness (1,199-raster inventory; 1,189 readable, 10 error rows)

- **Rank correlation (protocol rule 1):** continuous surface max |ρ| = **0.7331** (vs 57GEMSDOE twohost-relay surface); placed dots max |ρ| = **0.1233**; provisional top-k ρ = 0.1945. All ≤ 0.90.
- **Identity/Jaccard:** no byte- or decoded-identical twin; max Jaccard = **0.0463**. vs H33: forward overlap 0.3508, ρ = 0.0199. vs previous canonical THVC dots: 5,581 exact shared dots, Jaccard 0.0828.
- **Operative amendment-D2 (chance-corrected):** duplicate iff corrected overlap (ov−h)/(1−h) > 0.70. Among **875 comparable sparse priors** (dot-equivalent ≤ 50,000): **0 firings**, worst corrected **0.6711** (GEMSDOE25 factorial-bde: raw ov 0.7290, halo 0.1762, Jaccard 0.0275, ρ = 0.046 — habitat co-location on the same fault systems, not copying; the generation code never reads registry rasters).
- **Raw readings (disclosed, not operative):** budget-matched worst 1.0 and 15 dense D2 firings, all dense corridor/diagnostic maps (77k–624k dot-equivalents, halos covering most of the allowed domain). The same maps flag withheld ground truth itself (THVC oracle: truth20 raw 0.8682 vs 59GEMSDOE), so the raw all-rasters rule is unsatisfiable by a perfect submission; the literal reading is unsatisfiable by any non-empty map (space-filling witness). See IR-79-143.

## 6. Limitations and remaining work

1. **Distribution shift is the dominant risk.** Holdout recovers withheld *catalogue* faults; organizers score expert-found faults absent from the catalogue. CONJ dots sit closer to mapped faults than H33's (median 671 m vs 1.96 km). If hidden faults avoid mapped systems, the organizer score can fall below the reported 0.2778 despite holdout superiority.
2. **No organizer confirmation.** Promotion means every automated preregistered gate passed and the separate selector approved; spending a weekly slot remains the account holder's decision, and only the resulting receipt creates an ORGANIZER-CONFIRMED score.
3. **Uniqueness scope.** Checked against 1,199 public sibling-repository rasters, not private uploads. A stricter owner preferring the raw sparse ≤ 0.70 reading would block this file on the single disclosed 0.7290 reading; we judged post-hoc emission-switching to evade it a worse scientific sin (registry tuning) and disclosed instead.
4. **Next mechanisms (preregister fresh):** the remaining ranked hypotheses (basement-step gravity worms, sinter-age decay fields, drainage χ-anomaly lineaments, InSAR-style strain proxies) are documented in `research/hypotheses_20261022_conj.md`; CONJ itself must not be retuned on holdout.
