# Untried hypotheses ranked by DTI gain and cost (session 842c8c7c, 2026-10-22)

Scope rule: HOLDOUT-DTI means the offline quadrant-blocked hide-and-recover proxy in `vendor/gems57/holdout.py` (4 spatial quadrant folds, paired 20 km block bootstrap, 1000 draws). It is not a DrivenData score. DrivenData scores are not organizer-confirmed here. Expected gains below are **ESTIMATES, not measurements**. A slot is used only after a candidate passes the blocked holdout bar (G79-THVC: `0.1905` seed 20, `0.1944` seed 30, HOLDOUT-DTI).

| Rank | Hypothesis | Evidence basis (verified in repo) | Estimated DTI gain | Cost | Status |
|---|---|---|---|---|---|
| 1 | **H-A: FNHR zero-catalogue physics head placed by the G79-THVC Charnes-Cooper placer.** | Physics head alone: `0.0906` seed 20 / `0.0966` seed 30 HOLDOUT-DTI; canonical THVC zero-catalogue ablation `0.0784` (IR-79-140, `archive/h79_fnhr_a57e2a7f/`). Placer in `scripts/run_g79_thvc.py`. Combination untested. | Unknown. The seed-20 head-vs-ablation difference is `+0.0122`, which is not a combined gain. | Medium: requires GDR-derived channels (`data/raw/external/gdr_*.csv` present) and new wiring of `build_physics_stack` into the inner-tuned placer. | **Not validated. Top candidate. No slot used.** Pre-register and commit before any run. |
| 2 | **H-C: MT conductance layers as a deep-structure prior (regional, not pixel-scale).** | GDR 1391 / ScienceBase `62979746d34ec53d276c113b` (Peacock and Bedrosian 2022) has conductance layers at 2–12, 12–20, 20–50, 50–90, and 90–200 km. The backlog's resistivity slices at 500 m, 1.5 km, and 3 km are **not** in the product (IR-79-144). | Unknown; likely small, because the layers are far coarser than the 100 m grid. | High: 117 MB file at gdr.openei.org, which is outside the sandbox outbound allowlist, so the owner must download it. | Not run. Needs owner download and a re-scoped spec. |
| 3 | **H-B: Thorium-normalised K residual with ASTER silica correction.** | Pilot without silica: candidate `0.0206 / 0.0318` vs raw-K control `0.0274 / 0.0294`, below random on seed 20 (IR-79-146). AUC `0.47 / 0.49`. | Likely near zero, because the pilot signal is at or below chance. | Medium: ASTER data not restored; uint8 K/Th units unknown (IR-79-152). | Negative pilot. Prior lowered. |
| 4 | **H-D: Full drape-height source-depth model (parent of H80-DRAPE).** | The notch pilot is negative (IR-79-145): notch minus control `-0.0002` / `-0.0018`. Tilt-edge alone equals control. The drape-height model is untested. | Unknown; the notch branch has no positive signal. | High: needs per-line drape height from GeoDAWN flight geometry (Area 1 200 m, Area 2 400 m, drape 100–200 m, per the USGS page). | Not run. Prior lowered by the negative notch pilot. |

## Top-candidate validation plan (H-A), to execute before any slot decision

1. Preregister H-A (commit first; then no result is read before the commit timestamp).
2. Run the blocked holdout on seeds 20 and 30 with the same fold receipts (11,321 / 11,342 withheld positives) and the same canary (single-feature AUC must stay `<= 0.90`).
3. Pass criteria, fixed in advance: paired gain over the G79-THVC bar `> 0` with 95 % CI excluding 0 on both seeds, and `0` near-duplicates against H33 and D2.8 (overlap `<= 0.70` per the project rule).
4. If it passes, run the validator and the submission-status gate. Promotion is a separate selector step. No slot is chosen automatically.

Experiment budget used this session: 2 of 3. The third is reserved for H-A and is not yet used.
