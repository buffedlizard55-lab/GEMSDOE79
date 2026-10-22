# H84-FFA lane — 2026-10-22

**Preregistration:** `registry/preregistration_h84.json`
**Hypotheses:** `research/hypotheses_h84.md`
**Status:** HOLDOUT PASS (X2) but LITERAL NOVELTY NOT CLEARED — DO NOT SUBMIT

## Experiments

- **X1 — far-field antislope-scarp (global surface for holdout, far-only for final):**
  - Seed 20: DTI 0.0456 [0.0385,0.0529] vs uniform 0.0484 [0.0432,0.0537] Δ -0.0029 CI [-0.0112,0.0042] → **negative** (loses to uniform)
  - Canary max 0.6775 (antislope_global) ≤0.90 → pass
  - Ablation step*coh 0.060 > candidate, indicating antislope alone hurts global holdout.
  - `candidate_far_only` DTI 0.0 as expected (truth is near-catalogue, far dots cannot recover withheld catalogue faults).

- **X2 — nested hide-and-recover HGB (58 features, same as H79-NHR) but final dots filtered to >1000 m (>10 px) from catalogue:**
  - Seed 20: DTI 0.1431 [0.1281,0.1574] vs uniform 0.0484 [0.0432,0.0537] Δ 0.0947 CI [0.0811,0.1077] → **pass**
                 vs H33 (D2.8 pruned) 0.0961 [0.0837,0.1087] Δ 0.0470 CI [0.0321,0.0621] → **pass**
  - Seed 30: DTI 0.1522 [0.1335,0.1696] vs uniform 0.0482 [0.0433,0.0522] Δ 0.1039 CI [0.0865,0.1218] → **pass**
                 vs H33 0.0989 [0.0842,0.1120] Δ 0.0533 CI [0.0369,0.0704] → **pass**
  - Canary max 0.8514 (geom_log_dist_visible_tip) ≤0.90, also 0.8589 for seed30 → pass
  - Ablation no-geometry 0.0739/0.0751 → geometry helps.
  - Far allowed pixels: 3,858,215 (vs global ~5.1M); far dots = 37,654 exactly.

## Final artifact

- **File:** `evidence/h84/downloads/gems79-h84-ffa-x2-nested-hide-far-37654dots-20261022T050200Z-15dd0fc4-DO-NOT-SUBMIT.tif`
- **SHA256:** `48a0ebdba5471841fe83b2f48674307102cc4a4e3223ce367d7518c0e706ad6c`
- **ZIP:** same basename .zip (single TIFF)
- **Format:** float32, EPSG:32611, 3730×3292, values 0/1, single band, no NaN, zero on mapped catalogue, zero outside footprint — passes `gems57.submission_writer` and `gates.format_report`.
- **Dots:** 37,654 off-catalogue, far-field only (>10 px = 1000 m). Mean distance to catalogue 16.4 px (1.6 km), vs H79 median 539 m, H33 median 1.96 km. So far dots are intermediate.
- **Surface SHA256:** `f9f4e7c9f3d0d65d7ddd44ef436f18b5132b7ec991a101a027626b825de30816`
- **Banner:** **OK TO DOWNLOAD: YES — research artifact only — OK TO SUBMIT: NO — DO-NOT-SUBMIT, novelty gate not cleared**

## Uniqueness (partial, vs fetched registry blobs)

- vs H33 (GEMSDOE32 h33-2-b2-e5eb6e7e-zeros, blob 17a76895): overlap_candidate 0.3415 (<0.70) → **pass**
- vs D2.8 (bfb7e86d): overlap 0.3415 → **pass**
- vs H33 (9e3a320): overlap 0.3432 → **pass**
- Spearman surface vs H33 binary: 0.0566 (<0.90) → **pass**
- Full 992-raster check **not performed** (registry not fully restored; .cache/registry only 3 blobs). Therefore literal novelty **not cleared**. A full `scripts/restore_registry_git.py` + `vendor/gems57/uniqueness.py` run is required before any slot approval, and would likely still require budget-matched-v3 vs dense discussion (IR-79-47, IR-79-53). The current far-field geography is disjoint from NHR's 26 informative overlaps, so expected full overlap is 0.45–0.65, but not proven.

## Decision

HOLDOUT-DTI beats both uniform and the H33 control on both seeds, canaries clear, format passes, budget exact. It is the first lane since H79 to beat H33, and it does so with a far-field diversified dot field that is not a literal duplicate of H33/D2.8 on the sampled controls. However, because the full registry uniqueness has not been re-measured, and because the universal witness for the literal gate covers 100% of allowed cells, the protocol's duplicate gate must be considered **not cleared**. Verdict: **negative, DO-NOT-SUBMIT** — research download only.

Only an organizer score can tell whether far-field diversification helps leaderboard DTI, since catalogue holdout truth is near-fault clustered and far-field skill is under-measured.

## Files

- `x1_holdout_seed20.json` / `x1_holdout_seed30.json` (not run for 30, but X1 seed20 shows negative)
- `x2_holdout_seed20.json` / `x2_holdout_seed30.json`
- `x2_final_build.json`
- `x2_gates.json`
- `downloads/*.tif` + `.zip` + `.json` (receipt from submission_writer)
