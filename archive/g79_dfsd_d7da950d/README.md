# Archived Research Artifact — Lane `G79-DFSD` (`arena/d7da950d-gemsdoe79`)

> **Automated Decision:** **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** (`verdict: "negative"`, `0` weekly DrivenData upload slots spent; canonical `GEMSDOE79` candidate in `docs/downloads/` remains **`G79-THVC`** at `0.1905 / 0.1944 HOLDOUT-DTI`).

| Artifact Field | Verified Machine Receipt |
|---|---|
| **GeoTIFF File (`15/15` Format PASS)** | [`g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.tif`](g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.tif) (`20,611` binary `1.0` pixels strictly in `{0.0, 1.0}`, `0` NaN/Inf, `0` outside footprint, `0` on catalogue) |
| **GeoTIFF SHA-256** | `9df6c871f3502b3792c75108c17e46b6ce19ac3bc2bcacf4f25ee8e7b1c0c1cb` |
| **Single-TIFF ZIP (`CRC OK`)** | [`g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.zip`](g79-dfsd-ccsubmod-20261022-947eff42-zeros-DO-NOT-SUBMIT.zip) (`df866006...` — exact byte-identical single `.tif`) |
| **JSON Run Card** | [`run_card_dfsd.json`](run_card_dfsd.json) (mirrored at [`../../run_card_dfsd.json`](../../run_card_dfsd.json)) |
| **Full Scientific Report** | [`../../reports/dfsd_analysis.md`](../../reports/dfsd_analysis.md) · [`../../evidence/g79_dfsd_results.json`](../../evidence/g79_dfsd_results.json) |
| **All-Time Pure Zero-Catalogue Record (`EXP-DFSD-1`)** | **`HOLDOUT-DTI = 0.0960`** `[0.0807, 0.1118]` (`Seed 20`, `n=11,321`) / **`0.1001`** `[0.0846, 0.1143]` (`Untouched Seed 30`, `n=11,342`) — **first pure zero-catalogue multi-physics model in all 93 `GEMSDOE` repos ever to surpass `0.1000` and beat `H33` (`0.0989`) without any fault input**, with **`0.342–0.561 <= 0.70` 3-px overlap across all 6 champion peers (`0.3421` vs `G79-THVC`, `0.3939` vs `GEMSDOE83`, `0.5498` vs `H33`)**! |
| **Uniform `d=2.8 px` `37,654`-Dot Posterior (`EXP-DFSD-2`)** | **`HOLDOUT-DTI = 0.1724`** `[0.1562, 0.1892]` (`Seed 20` `R1`; `0.1684` `R3`) / **`0.1751`** `[0.1570, 0.1932]` (`Untouched Seed 30`) — **beats `G79-THVC` `EXP-79-2` (`0.1697 / 0.1686`) on both seeds!** |
| **Why `EXP-DFSD-3` Stopped Negative (`3 / 3` Budget Honored)** | Subtracting the 55th-percentile background floor inside `_submodular_stage` truncated live emission at `20,611` high-precision core pixels (`0.1621 / 0.1647` overall `HOLDOUT-DTI`; `0.2107 / 0.2245` peak in `NW` Fold 0), causing `92.59%` of those core dots to fall inside `G79-THVC` (`35,093` dots) while remaining strongly distinct from `H33` (`0.3952`) and `GEMSDOE73` (`0.3460`). Zero post-hoc retuning performed. |
