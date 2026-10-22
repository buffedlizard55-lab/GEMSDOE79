# Archived Lane `H79-PFSD` (`arena/9574eb05-gemsdoe79`)

- **Status:** `OK TO DOWNLOAD: YES` (research inspection) | **`OK TO SUBMIT: NO`** (`verdict = negative`, `0` weekly slots spent)
- **Canonical repository artifact:** Unchanged — [`docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`](../../docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif) (`G79-THVC`, `HOLDOUT-DTI` `0.1905` Seed 20 / `0.1944` Seed 30) remains the highest-holdout primary deliverable per `IR-79-120`.
- **Preregistration:** [`registry/preregistration_pfsd.json`](../../registry/preregistration_pfsd.json) (`SHA-256`: `81a0770e97c7eb520971478fc7512e0e4e076b41d96803c8e3ace076b41d96803c8e3ace076b99ea77c` in [`evidence/pfsd/preregistration_pfsd_sha256.txt`](../../evidence/pfsd/preregistration_pfsd_sha256.txt))
- **Run Card:** [`run_card_pfsd.json`](run_card_pfsd.json) (mirrored in [`evidence/pfsd/run_card_pfsd.json`](../../evidence/pfsd/run_card_pfsd.json))

## Validated Archived Deliverables

| File | Bytes | SHA-256 | Grid / Range / Catalogue Mask |
|---|---:|---|---|
| [`h79-pfsd-equilcc-20261022-2c5d5fd3-zeros-DO-NOT-SUBMIT.tif`](h79-pfsd-equilcc-20261022-2c5d5fd3-zeros-DO-NOT-SUBMIT.tif) | `146,056` | `23cc11b49380e7e6eac772157b3b9538e3fc44559b871d69e1fe3fa2faa2bf84` | `EPSG:32611`, `3730 x 3292`, `float32`, `[0.0, 1.0]`, `0` NaN/Inf, `39,250` binary `{0, 1}` pixels, `0` on `existing_faults.tif` |
| [`h79-pfsd-equilcc-20261022-2c5d5fd3-zeros-DO-NOT-SUBMIT.zip`](h79-pfsd-equilcc-20261022-2c5d5fd3-zeros-DO-NOT-SUBMIT.zip) | `146,286` | `68aea1e223041cda84aa81ce7fd2013ac7ff0b25bf1a9245455df1f7a6ce9813` | Single-GeoTIFF competition upload archive |
| [`h79-pfsd-equilcc-20261022-2c5d5fd3-zeros-DO-NOT-SUBMIT.json`](h79-pfsd-equilcc-20261022-2c5d5fd3-zeros-DO-NOT-SUBMIT.json) | `1,658` | Writer receipt | Emitted by unmodified `vendor/gems57/submission_writer.py` |

## Official `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, $\alpha=0.2, \beta=0.8$, 300 m kernel)

| Experiment / Control | Seed 20 (`n = 11,321`) | Seed 30 (`n = 11,342`) | Comparison vs `G79-THVC` & `H33` |
|---|---|---|---|
| **`EXP-PFSD-1` (Uncorrupted 92-ch Pure Physics, `0` catalogue features)** | **`0.0997`** `[0.0829, 0.1174]` | **`0.1134`** `[0.0963, 0.1322]` | **New repo pure-physics record**: beats `H33` fold-fair (`0.0961 / 0.0989`) on **both seeds** with zero catalogue input; `+27.2% / +75.0%` over `EXP-79-1` (`0.0784 / 0.0648`); `+10.1% / +17.4%` over `H79-FNHR` (`0.0906 / 0.0966`) |
| **`EXP-PFSD-2` (106-ch Dual-Expert, uniform `d=2.8 px`, `37,654` dots)** | **`0.1854`** `[0.1670, 0.2036]` | **`0.1751`** `[0.1566, 0.1933]` | **Beats `G79-THVC` `EXP-79-2` (`0.1697 / 0.1686`) on both seeds** (`+0.0158` Seed 20, `+0.0065` Seed 30) |
| **`EXP-PFSD-3` (Equilibrated Charnes-Cooper Allocator)** | **`0.1886`** `[0.1710, 0.2064]` | **`0.1746`** `[0.1578, 0.1911]` | Balanced Fold 3 on Seed 20 (`7,460` vs `3,330` dots), but inner-to-outer `lambda_fp = 0.0058` shift halted Seed 30 at `25,679` dots, trailing `EXP-79-3` (`0.1905 / 0.1944`) |
| `C2` (`H33` `GEMSDOE32` fold-fair control) | `0.0961` `[0.0837, 0.1095]` | `0.0989` `[0.0845, 0.1131]` | Matched baseline |
| `C1` (`G79-FabricOffset-E1` placed at `B = 37,654`) | `0.0441` `[0.0369, 0.0516]` | `0.0440` `[0.0365, 0.0518]` | Matched baseline |
| `C0` (Uniform random `B = 37,654` in active domain) | `0.0497` `[0.0432, 0.0565]` | `0.0422` `[0.0382, 0.0464]` | Matched baseline |
