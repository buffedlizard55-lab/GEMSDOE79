# Archived Lane `G79-CSKD` (`arena/6da2620c-gemsdoe79`, 2026-10-22)

**AUTOMATED DECISION FOR THIS ARCHIVED FILE: `OK TO DOWNLOAD: YES (RESEARCH ARCHIVE). OK TO SUBMIT: NO.`**

- **GeoTIFF (`downloads/g79-cskd-ccsubmod-20261022-cdfdd16f-zeros-DO-NOT-SUBMIT.tif`):** `151,998` bytes · SHA-256 `91ffc11017f7d7ff1d6f77feb8be3734560e295e2f1067a463d89185c4ac37e7` · `42,000` binary `{0.0, 1.0}` fault-candidate pixels (`EPSG:32611`, `3730 x 3292`, `0` NaN/Inf anywhere, `0` mapped-catalogue overlap).
- **ZIP (`downloads/g79-cskd-ccsubmod-20261022-cdfdd16f-zeros-DO-NOT-SUBMIT.zip`):** `118,433` bytes · SHA-256 `bf41727924ecea4f55e10e41e3f33f074bae2fb02f89965d063be57a3ceca0ac`.
- **Protocol Run Card:** [`run_card_cskd.json`](run_card_cskd.json)
- **Preregistration:** [`../../registry/preregistration_g79_cskd.json`](../../registry/preregistration_g79_cskd.json)
- **Full Machine Evidence Receipt:** [`../../evidence/g79_cskd_results.json`](../../evidence/g79_cskd_results.json) & [`../../evidence/g79_cskd_leakage_canary.json`](../../evidence/g79_cskd_leakage_canary.json)

## Summary of Measured Results (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`)

| Metric / Gate | `G79-CSKD` (`EXP-CSKD-3`) | Canonical `G79-THVC` (`EXP-79-3`) | `H33` Fold-Fair Control |
|---|---|---|---|
| **Seed 30 `HOLDOUT-DTI`** (`n = 11,342` withheld px) | **`0.214488`** `[0.196592, 0.232188]` (**#1 all-time `GEMSDOE79`**) | `0.194366` `[0.177400, 0.212627]` | `0.098898` `[0.085412, 0.112762]` |
| **Seed 20 `HOLDOUT-DTI`** (`n = 11,321` withheld px) | `0.178129` `[0.161835, 0.194433]` (`#2` in `GEMSDOE79`) | **`0.190517`** `[0.174082, 0.206932]` | `0.096086` `[0.082774, 0.109514]` |
| **Dual-Seed Mean `HOLDOUT-DTI`** (`22,663` withheld px) | **`0.196308`** (**#1 all-time `GEMSDOE79`**, `+0.003867`) | `0.192442` | `0.097492` |
| **Single-Feature Leakage Canary** (`102` features × 2 seeds) | **PASS** (`max AUC = 0.805165 <= 0.90`) | **PASS** (`max AUC = 0.7855 <= 0.90`) | — |
| **Stage-1 Isotropic Catalogue-Distance Gain Share** | **`9.7%`** (`90.3%` directional tip/scarp/Coulomb/physics) | `52.8%` | — |
| **Forward 3-px Overlap vs `GEMSDOE83` (`h83-gvcd-dink300`)** | **`0.613690 <= 0.70` (COLLISION RESOLVED)** | `0.713903 > 0.70` | `0.3301` |
| **Max Overlap Across All Valid `-zeros.tif` Cross-Repo `<=50k` Maps** | **`0.679643 <= 0.70` (`0` collisions)** | `0.713903 > 0.70` | — |
| **Preregistered Promotion Gate (`beats_thvc_on_both_seeds`)** | **`False`** (`Seed 20: -0.0124`; `Seed 30: +0.0201`) | Canonical baseline (`docs/downloads/`) | — |
