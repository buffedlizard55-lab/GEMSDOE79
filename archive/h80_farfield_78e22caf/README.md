# H80-FARFIELD archived artifact — 2026-10-22

This lane was run under preregistration `registry/preregistration_farfield.json` (H80-FARFIELD, 2026-10-22T05:00:00Z).

**Geological hypothesis:** Far-field (>10 px, >1 km) unmapped faults extend buried range fronts under piedmont alluvium; antislope-ratio (det_elev scarps facing uphill) and magnetic/gravity worm persistence (RTP + isostatic gravity at scales 2/5 px) trace buried faults that near-catalogue NHR underweights.

**Result:** HOLDOUT-DTI (pooled hide-v2, 4 spatial folds) beats H33 fold-fair control on both seeds:
- seed 20: candidate 0.151 [0.1344,0.1658] vs H33 0.0961 Δ+0.0549 [0.0391,0.0707]
- seed 30: candidate 0.159 [0.1396,0.1781] vs H33 0.0989 Δ+0.0601 [0.0422,0.0794]
- vs uniform: +0.103/+0.111, vs ablation_no_farfield: +0.0048/+0.0068
- Leakage canary max 0.8589 ≤0.90 (geom_log_dist_visible_tip), 0 suspicious — PASS

**Format:** single-band float32 EPSG:32611 3730×3292 transform [100,0,243350,0,-100,4508550] values 0/1 no NaN — PASS. 37,654 dots far-field only (distance_transform_edt>10 px from catalogue), median 14.14 px (1414 m), 100% >1 km.

**Uniqueness:** FAIL under both literal and D-1 like-for-like. Dot field overlap 0.862 vs `GEMSDOE3:docs/downloads/coverage-v3-wide` (halo 0.61, 624k dots, beyond-chance 0.64) and 26 informative rasters >0.70. Rank correlation vs H33 0.02 passes. Pure worm-persistence far-field surface is unique (0.58 vs coverage, 0.209 vs H33) but HOLDOUT-DTI 0.037 vs H33 0.096 — not skillful. HGBR with far-field features recovers skill but reintroduces correlation with dense coverage lattice.

**Verdict:** Negative — research only, DO NOT SUBMIT. New bytes (SHA fa1f056...), not a copy, but protocol requires uniqueness. No weekly slot spent.

**Files:** `gems79-h80-farfield-37654dots-20261022T050931Z-78e22caf.tif` (826 KB, 37,654 positive pixels) and `.zip` (177 KB).

**Evidence:** `evidence/farfield/x1_holdout_seed20.json`, `x1_holdout_seed30.json`, `x1_final_build.json`, `src/gems79/farfield.py`, `scripts/run_farfield.py`, `scripts/build_farfield_submission.py`.

**Why 0.2778 family best:** H33 (dotted-h19-5-d2-8 / h33-2-b2) is D2.8 minus near-catalogue pruning; sparse 37k dots (1.96 km median) maximize TP per dot (~2.33 on ideal trace) under kernel metric.

**Next steps:** Tip-pair stepover linkage (relay ramps 0.3–2 km between opposite-polarity tips) or hybrid worm+dispersed sampling to reduce overlap vs 30 space-filling lattices while retaining skill. Requires D-1 like-for-like adjudication and overlap-capped placement (tested cost −0.017 in G79B) with re-validation on both holdout seeds.
