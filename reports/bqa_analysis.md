# H79-BQA: band-weighted hide-and-recover (session 0bd0e0b2)

All numbers below are **HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, 4 spatial quadrant folds, 37,654-dot budget scaled by fold area), copied by `scripts/report_bqa.py` from `evidence/bqa/holdout_seed*.json`. None is a leaderboard score. Seed 20 chose X2 among the preregistered arms ([amendment A1](../registry/preregistration_bqa_amendment_A1.json)); seeds 30 and 40 are confirmatory.

## Standard holdout (all withheld fault pixels)

| Arm | seed 20 | seed 30 | seed 40 |
|---|---|---|---|
| X2: band-weighted model, global placement | 0.1510 [0.1365, 0.1649] | 0.1625 [0.1438, 0.1808] | 0.1580 [0.1426, 0.1749] |
| X1: band-weighted model + H33 distance quotas | 0.1139 [0.0990, 0.1275] | 0.1235 [0.1059, 0.1404] | 0.1289 [0.1131, 0.1460] |
| Ablation: unweighted model + quotas | 0.1138 [0.0994, 0.1280] | 0.1133 [0.0949, 0.1324] | 0.1324 [0.1160, 0.1510] |
| NHR reproduction (unweighted, global placement) | 0.1431 [0.1281, 0.1574] | 0.1522 [0.1343, 0.1705] | 0.1605 [0.1439, 0.1789] |
| H33 fold-fair control (holdout best, non-duplicate) | 0.0961 [0.0837, 0.1086] | 0.0989 [0.0842, 0.1120] | 0.1000 [0.0860, 0.1141] |
| Uniform random control | 0.0484 [0.0432, 0.0537] | 0.0482 [0.0433, 0.0522] | 0.0489 [0.0434, 0.0544] |
| Withheld fault pixels | 11,321 | 11,342 | 11,437 |

Paired difference X2 − H33 control (95 % spatial-block bootstrap CI): seed 30: +0.0636 [+0.0460, +0.0830]; seed 40: +0.0580 [+0.0411, +0.0772].

## Far-field sub-holdout (withheld pixels > 1 km from fold-visible faults)

| Arm | seed 20 | seed 30 | seed 40 |
|---|---|---|---|
| X2: band-weighted model, global placement | 0.0917 [0.0731, 0.1101] | 0.0986 [0.0784, 0.1189] | 0.1070 [0.0867, 0.1270] |
| X1: band-weighted model + H33 distance quotas | 0.0771 [0.0601, 0.0947] | 0.0832 [0.0658, 0.1028] | 0.1004 [0.0779, 0.1215] |
| Ablation: unweighted model + quotas | 0.0748 [0.0589, 0.0909] | 0.0771 [0.0576, 0.0983] | 0.1040 [0.0797, 0.1291] |
| NHR reproduction (unweighted, global placement) | 0.0787 [0.0620, 0.0966] | 0.0910 [0.0685, 0.1129] | 0.1105 [0.0867, 0.1369] |
| H33 fold-fair control (holdout best, non-duplicate) | 0.0775 [0.0612, 0.0922] | 0.0853 [0.0700, 0.1009] | 0.0910 [0.0730, 0.1093] |
| Uniform random control | 0.0346 [0.0283, 0.0415] | 0.0356 [0.0301, 0.0412] | 0.0349 [0.0276, 0.0419] |
| Withheld fault pixels | 5,150 | 5,127 | 5,504 |

Paired difference X2 − H33 control (95 % spatial-block bootstrap CI): seed 30: +0.0133 [-0.0031, +0.0303]; seed 40: +0.0160 [-0.0074, +0.0387].

## Where each arm puts its dots (distance to fold-visible faults, px = 100 m; all folds, seed 20)

| Arm | (2,3] | (3,5] | (5,10] | (10,20] | (20,50] | >50 |
|---|---|---|---|---|---|---|
| X2: band-weighted model, global placement | 6.7 % | 13.9 % | 39.0 % | 25.8 % | 12.1 % | 2.6 % |
| X1: band-weighted model + H33 distance quotas | 4.3 % | 8.6 % | 16.7 % | 21.0 % | 29.4 % | 20.0 % |
| Ablation: unweighted model + quotas | 4.3 % | 8.6 % | 16.7 % | 21.0 % | 29.4 % | 20.0 % |
| NHR reproduction (unweighted, global placement) | 7.1 % | 17.1 % | 33.0 % | 23.3 % | 14.9 % | 4.6 % |
| H33 fold-fair control (holdout best, non-duplicate) | 4.8 % | 7.7 % | 14.6 % | 21.1 % | 30.7 % | 21.3 % |
| Uniform random control | 2.6 % | 4.5 % | 11.2 % | 20.1 % | 37.8 % | 23.8 % |

## Verdict: negative (no GeoTIFF)

- **X1** (band-weighted model + H33 distance quotas (registry/preregistration_bqa.json)): negative; G3 (far-field >= H33 control) failed on seed 20 and seed 30.
- **X2**: passed G1–G4 on the confirmatory seeds 30 and 40, then failed **G5 (surface uniqueness before placement)**. The provisional top-37,654 cells of the final X2 surface have chance-corrected 3 px overlap 0.943 with `GEMSDOE79:docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif` (raw 0.950, chance 0.129). 81 of 1,197 compared registry rasters exceed 0.70. The full-surface Spearman ρ is only 0.654, so the *ranking* is new, but the cells it would fill are already occupied.
- `run_bqa.py place-x2` refuses to place dots for a surface that failed G5, so no dots were placed and no file was written. There was no retuning and no overlap capping. X3 was not run.

| Worst registry rasters for the X2 provisional top-k | chance-corrected | raw | chance |
|---|---|---|---|
| `GEMSDOE79:docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif` | 0.943 | 0.950 | 0.129 |
| `GEMSDOE53:docs/submissions/gems53-h1-thin_bin_q0p1-20261008-aefc7582.tif` | 0.923 | 0.938 | 0.204 |
| `GEMSDOE37:docs/downloads/gemsdoe37-h6-physics-dotted-80k-20261005T055000Z-0bef9211631c.tif` | 0.902 | 0.928 | 0.268 |
| `GEMSDOE3:docs/downloads/coverage-v3-wide-20260925T054019Z-0ac095a7ed.tif` | 0.863 | 0.947 | 0.610 |
| `12GEMSDOE:docs/downloads/12GEMSDOE_r7-nms3-dem10-scarp_0c9199f14e62_allfinite.tif` | 0.855 | 0.901 | 0.317 |
| `12GEMSDOE:docs/downloads/12GEMSDOE_r7-nms3-dem10-scarp_0c9199f14e62.tif` | 0.855 | 0.901 | 0.317 |
| `GEMSDOE25:docs/downloads/gems25-factorial-bde-x123-sapd2-4-20261002-5e4b5a98d2c7-nan.tif` | 0.840 | 0.870 | 0.185 |
| `GEMSDOE80:docs/downloads/gems80-adpt-kkt-lagrangian-36500d-20261022T012049Z-5bd11c85-zeros.tif` | 0.834 | 0.858 | 0.146 |
| `59GEMSDOE:docs/downloads/gems59-h59i2-loco-ipp-corridor-20261011T000000Z-zeros.tif` | 0.830 | 0.869 | 0.230 |

- Uniqueness (surface): worst Spearman ρ 0.654, worst chance-corrected 3 px overlap 0.943, complete True, passed **False**.

## Reading

- **The distance quota was the wrong lever.** Forcing H33's distance profile (X1 and the quota-only ablation) tied H33 in the far field instead of beating it (X1 far field below H33 on seeds 20 and 30).
- **Band weighting helps the holdout, but not novelty.** Giving every distance band equal training weight put X2 above the unweighted NHR reproduction on seeds 20 and 30 (point estimates; the paired CI excludes zero only on seed 30, +0.0104 [+0.0005, +0.0211]) and level with it on seed 40. About 65 % of its holdout dots still sit 0.5–2 km from visible faults, the band that NHR and many earlier family maps already fill.
- **What the data say about winning.** No surface in this repository has yet both beaten H33 on the holdout and passed the duplicate gate. NHR and X2 beat it, but they concentrate within about 2 km of mapped faults, where registry dot fields already sit. X1 and STEPCO S1 spread out like H33 and tied it. A unique file that beats H33 probably needs evidence other than proximity: new physical layers, not a new weighting of the same stack.
- **Caveat.** The holdout hides mapped catalogue faults; the organizer scores expert-found faults that are not in the catalogue. Holdout rank may not transfer.
