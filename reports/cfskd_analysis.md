# G79-CFSKD analysis (session bda00cff) — NEGATIVE

Question: why did H33 score 0.2778 (historical report) and can we beat it?
Answer (verified in-repo, `knowledge/why_h33.md`): H33 is D2.8 binary dots minus the
6,436 dots within 200 m of mapped faults. DTI (alpha 0.2, beta 0.8, 300 m triangular
kernel) takes max over predictions for TP but sum for FP, so sparse binary 1.0 dots
beat dense probability maps, and deleting near-catalogue flank dots removes FP mass
on faults the organiser masks out. 0.4413 is a public leaderboard observation
(xiaofanhu), not an ORGANIZER-CONFIRMED receipt for any repo artifact.

This lane tested backlog hypotheses H80-RADIO-KD + H80-COULOMB-CFS (preregistered,
`registry/preregistration_g79_cfskd.json`). HOLDOUT-DTI (gems57-pooled-hide-v2):

| arm | seed20 (n=11,321) | seed30 (n=11,342) |
|---|---|---|
| EXP1 physics-only | 0.0825 | 0.0843 |
| EXP2 +K_d | 0.0797 | 0.0766 |
| EXP3 +Coulomb veto (primary) | 0.0654 | 0.0678 |
| UNIFORM | 0.0462 | 0.0463 |
| H33 fold-fair (run_card.json) | 0.0961 | 0.0989 |
| G79-THVC (run_card.json) | 0.1905 | 0.1944 |

Canary max AUC 0.665/0.625 <= 0.90. K_d and the veto each hurt on both seeds
(paired CIs exclude 0): the stress-shadow corridor evidently hosts real antithetic/
parallel splays, and K_d residual adds playa-evaporite noise. Verdict: negative.
Do not submit; 0 weekly slots used. The raster is downloadable for inspection only.

## Irregularities flagged this session
- IR-CFS-1: labels.tif == existing_faults.tif (same SHA-256, 60,988 px): public labels are the catalogue, not hidden truth.
- IR-CFS-2: Coulomb veto 20px tip radius exempted most of the shadow corridor; fixed to 8px, regression-tested.
- IR-CFS-3: first run OOM-killed (exit 137, 3.9GB sandbox); fixed with float16 on-disk memmap stack.
- IR-CFS-4: full 1,108-raster registry uniqueness not re-run (4 local archives only) - fail-closed, verdict already negative.
- IR-CFS-5: docs/downloads/ accepts only the canonical artifact (publication contract), so this lane's raster lives in archive/g79_cfskd_bda00cff/.
