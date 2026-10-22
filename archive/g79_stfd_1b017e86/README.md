# Archive Manifest — `G79-STFD` (`arena/1b017e86-gemsdoe79`, `2026-10-22`)

> **Decision Line:** `OK TO DOWNLOAD (RESEARCH ARCHIVE): YES. OK TO SUBMIT: NO.`
> **Status:** `closed` (`stopped: true`, `verdict: "negative"`, `submission_slots_used: 0`)
> **Reason NOT to submit without coordinator sign-off:** Literal shared `vendor/gems57/uniqueness.py` (`3 px` overlap `<= 0.70`) flags full-footprint dense/lattice registry witnesses (`17GEMSDOE:E-proba-multiscale` `1.0000 > 0.70`, `13GEMSDOE:r13-lattice-s5` `0.9983 > 0.70`; `IR-79-125` / `IR-79-197`) as well as three unsubmitted `GEMSDOE79` internal research siblings (`CSMD` `0.8274`, `CSKD` `0.7600`, `THVC` `0.7388`). Across all `195` external `buffedlizard55-lab` repositories (`957` sparse `<= 75,308 px` prediction rasters), **zero** external sparse rasters exceed `0.70` (`max = 0.6981 <= 0.70`; `GEMSDOE83 = 0.6544 <= 0.70`; `H33 = 0.4316 <= 0.70`).

## Packaged Artifacts (`0644`, `EPSG:32611`, `3730 x 3292`, `float32`, `[0, 1]`, `0` NaN/Inf)

| Artifact | Path | Bytes | SHA-256 |
|---|---|---:|---|
| Competition-format single-band GeoTIFF (`41,000` positive pixels) | `archive/g79_stfd_1b017e86/downloads/gems79-stfd-dinkelbach-41000dots-20261022-6e022dbe-zeros-DO-NOT-SUBMIT.tif` | `146,956` | `07707b3f50dbb2e5f6c84e6baec03ea53895b6af1575f9a769747bc9c44f5a0a` |
| Competition-format single-TIFF ZIP archive | `archive/g79_stfd_1b017e86/downloads/gems79-stfd-dinkelbach-41000dots-20261022-6e022dbe-zeros-DO-NOT-SUBMIT.zip` | `112,274` | `3089115928698167968aa590d8227ae361b56b145b2436f31b150bb8b68e7183` |
| Shared `submission_writer.py` JSON receipt | `archive/g79_stfd_1b017e86/downloads/gems79-stfd-dinkelbach-41000dots-20261022-6e022dbe-zeros-DO-NOT-SUBMIT.json` | — | Verified parity with `.tif` and `.zip` |
| Preregistration (locked pre-holdout) | `registry/preregistration_g79_stfd.json` | — | `4d62ae4c25c638fe5e24a40f279623e05c995503a1684cb81f47f56ce4e90a75` |
| Complete JSON Run Card | `run_card_stfd.json` (mirrored at `evidence/stfd/run_card_stfd.json` & `docs/run-card-stfd.json`) | — | Sealed (`LaneClosedError` enforced on `scripts/run_stfd.py`) |

## Strict 4-Fold Leave-One-Quadrant-Out (`LOQO`) `HOLDOUT-DTI` (`gems57-pooled-hide-v2`)

*Evidence class: `HOLDOUT-DTI` (strict spatial quadrant holdout; never conflated with `ORGANIZER-CONFIRMED` leaderboard scores).*

| Arm | Emitted Dots | Seed 20 (`n=11,321` withheld px) | Seed 30 (`n=11,342` withheld px) | Dual-Seed Mean |
|---|---:|---:|---:|---:|
| **`EXP-STFD-3` (`G79-STFD` Dinkelbach)** | `39,867 / 39,930` (`41,000` live) | **`0.1928` (`[0.1737, 0.2117]`)** | **`0.2114` (`[0.1914, 0.2306]`)** | **`0.2021` (`#1` in `GEMSDOE79`)** |
| **`EXP-STFD-2` (`119`-ch uniform `37,654` dots)** | `37,654` | **`0.1923` (`[0.1755, 0.2082]`)** | **`0.2110` (`[0.1909, 0.2303]`)** | **`0.2016`** |
| **`EXP-STFD-1` (`97`-ch `100%` zero-catalogue physics)** | `37,654` | **`0.1090` (`[0.0865, 0.1314]`)** | **`0.1276` (`[0.1066, 0.1500]`)** | **`0.1183`** |
| Canonical `G79-THVC` reference (`run_card.json`) | `35,093` | `0.1905` (`[0.1743, 0.2063]`) | `0.1944` (`[0.1782, 0.2102]`) | `0.1924` |
| Archived `G79-CSKD` reference (`IR-79-200`) | `42,000` | `0.1781` (`[0.1605, 0.1950]`) | `0.2145` (`[0.1965, 0.2323]`) | `0.1963` |
| Archived `G79-CSMD` reference (`IR-79-203`) | `35,600` | `0.1629` (`[0.1476, 0.1781]`) | `0.1749` (`[0.1585, 0.1909]`) | `0.1689` |
| `C2_h33_analogue_foldfair` (`H33` on identical folds) | `38,802 / 38,829` | `0.0961` (`[0.0828, 0.1095]`) | `0.0989` (`[0.0852, 0.1130]`) | `0.0975` |
| `C1_fabric_offset_E1_placed` | `37,654` | `0.0441` (`[0.0375, 0.0511]`) | `0.0440` (`[0.0364, 0.0518]`) | `0.0441` |
| `C0_random_B37654` | `37,654` | `0.0425` (`[0.0374, 0.0473]`) | `0.0463` (`[0.0415, 0.0506]`) | `0.0444` |
