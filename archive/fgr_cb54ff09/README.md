# Archived negative research lane — H79-FGR (session `cb54ff09`, 2026-10-22)

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**

This directory holds the bytes of one completed, preregistered, **negative**
experiment. It is archived here rather than published in `docs/downloads/`
because the canonical publication contract allows only the canonical H79-NHR
artifacts there (IR-79-52, IR-79-66); the H79-FF precedent is followed exactly.
Nothing in this directory changes the canonical deliverable, the canonical
`run_card.json`, the registry inventory, or the automated submission decision.

| | |
|---|---|
| Lane | **H79-FGR** — far-field gradient ranker |
| Preregistration | [`registry/preregistration_fgr.json`](../../registry/preregistration_fgr.json), written before any result |
| Experiments used | **1** of 3 (about 55 min of the 2 h budget) |
| File | [`downloads/gems79-h79-fgr-farfield-38000dots-20261022T045243Z-72c45bc4-DO-NOT-SUBMIT.tif`](downloads/gems79-h79-fgr-farfield-38000dots-20261022T045243Z-72c45bc4-DO-NOT-SUBMIT.tif) |
| ZIP (one TIFF) | [`downloads/gems79-h79-fgr-farfield-38000dots-20261022T045243Z-72c45bc4-DO-NOT-SUBMIT.zip`](downloads/gems79-h79-fgr-farfield-38000dots-20261022T045243Z-72c45bc4-DO-NOT-SUBMIT.zip) |
| GeoTIFF SHA-256 | `ff7c2ee62948e7760e1617fe7a2e48aa18782ef2878b400146068f6b46520442` |
| Dots SHA-256 | `72c45bc4a3220b233049059d97aeadc41b00c82aef480c1d3082bba4c375e195` |
| Format | single band float32, EPSG:32611, 3730 × 3292, transform identical to the sample, values exactly 0/1, no NaN anywhere: **PASS** |
| Positive pixels | 38,000 |
| Submission note (95/140) | `H79-FGR far-field ranker NEGATIVE; HOLDOUT-DTI 0.0058/0.0056 below uniform 0.0456; research only` |
| Verdict | **negative** |
| Slots used | **0** |

## HOLDOUT-DTI (`gems57-pooled-hide-v2`, 4 folds, both seeds)

| Arm | Seed 20 (n = 11,321 withheld px) | Seed 30 (n = 11,342 withheld px) |
|---|---:|---:|
| candidate (far-field) | **0.0058** [0.0012, 0.0112] | **0.0056** [0.0025, 0.0095] |
| near-field inversion | 0.0846 [0.0705, 0.0983] | 0.0686 [0.0584, 0.0803] |
| uniform control | 0.0456 [0.0408, 0.0499] | 0.0456 [0.0403, 0.0506] |
| H33 fold-fair control | 0.0961 [0.0831, 0.1096] | 0.0989 [0.0859, 0.1132] |

Paired Δ candidate − uniform: **−0.0399** [−0.0458, −0.0330] and **−0.0400**
[−0.0462, −0.0334]. Leakage canary 24 tests per seed, max AUC 0.6480 / 0.5985,
both ≤ 0.90: **PASS** — the candidate is not leaking, it is genuinely
uninformative on this holdout.

## Why it stopped

1. Far-field relocation is **refuted**: the candidate scores below uniform random
   noise on both seeds, while inverting the same distance weight recovers most of
   the control's performance. The +0.905 within-habitat distance correlation in
   `evidence/score_geometry_study.json` is a **pruning** effect, not a relocation
   target.
2. Mechanism defect, reported not retuned: because the weight saturates at 1
   beyond 5 km while competence is a bounded rank average, the emitted set has
   median catalogue distance **5,780 m**, **100 %** of dots beyond 2 km and **0 %**
   within 500 m — the surface degenerated into a pure distance ranking.
3. Uniqueness fails both readings (literal 35/56 blocking, worst 1.000;
   chance-normalised 19/56 blocking of which **5 informative**, worst 0.8269
   against halo 0.6413). See
   [`evidence/fgr/uniqueness_both_readings.json`](../../evidence/fgr/uniqueness_both_readings.json).
4. The inherited literal overlap gate is independently proven unsatisfiable for
   *any* nonempty candidate: 20 registry **dot fields** have 3 px halos covering
   more than 70 % of the allowed domain, the worst 0.998724 while flagging a
   uniform random field at 0.998677. See
   [`evidence/gate_satisfiability_certificate.json`](../../evidence/gate_satisfiability_certificate.json).

No retuning, no overlap capping, no coordinate jitter, no second experiment, and
no stopped lane was restarted. Full analysis:
[`reports/fgr_farfield_refutation.md`](../../reports/fgr_farfield_refutation.md).

## Reproduce (read-only inspection of frozen bytes; does not rerun the lane)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/python scripts/restore_data.py --ids training_features,ext_lidar_scarp_features_u8,ext_lidar_scarp_features_json --target-dir data/raw --preserve-receipt
.venv/bin/python scripts/certify_gate_satisfiability.py     # §4 certificate
.venv/bin/python scripts/study_score_geometry.py            # §1–§2 study
.venv/bin/python scripts/validate_proxies.py                # §5 proxy meta-validation
```

Historical experiment entry points (`scripts/run_fgr.py`,
`scripts/fgr_uniqueness.py`, `scripts/finalize_fgr.py`) document reproduction.
They are **not** permission to resume this lane.
