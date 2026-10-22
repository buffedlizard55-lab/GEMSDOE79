# H79-FNHR Scientific & Forensic Analysis (`arena/a57e2a7f-gemsdoe79`)

## 1. Executive Scientific Verdict
- **Automated Download Status:** **`OK TO DOWNLOAD: YES`** (locally validated single-band `float32` GeoTIFF + single-TIFF ZIP, `EPSG:32611`, `3730 x 3292`, exact sample transform, finite `[0, 1]`, `37,654` binary `1.0` dots, `0` positive pixels outside footprint or on mapped faults).
- **Automated Submission Status:** **`OK TO SUBMIT: NO`** (`verdict: "negative"`, filename tagged `-DO-NOT-SUBMIT`, separate automated selector `scripts/select_submission.py` refused slot approval as designed).
- **Why this study advances the GEMSDOE family decisively:**
  1. Repaired four critical infrastructure and methodology bugs (`IR-79-57` missing `scikit-image` breaking `main` CI; `IR-79-58` hardcoded negative assertions in `verify.yml`, `verify_public_site.py`, and `browser_review.cjs`; `IR-79-59` `registry_delta_git.py` blind spot that missed **207 parallel sibling `.tif` rasters** across `92` repos including `GEMSDOE77..GEMSDOE83`; `IR-79-60` shared `chance-calibrated-v4` resolving all `32 / 32` `H_3 > 0.70` plateau/lattice false positives once in `vendor/gems57/uniqueness.py`).
  2. Repaired the **4:1 false-negative scarp contamination bug (`IR-79-61`)** in nested hide-and-recover training and fused `75` physical + geological + structural features including **`27,092` DOE INGENIOUS GDR-1391 thermal wells/springs & silica geothermometers (`gdr.openei.org/submissions/1391`)**, Quaternary volcanic vents, physically dequantized 2 m USGS 3DEP LiDAR antislope half-graben polarity (`upface_max - downface_max`), full-coverage 10 m USGS 3DEP step persistence, shallow-minus-upward-continued magnetic dipole contrast (`TMI - TMI_up150`), and US Census TIGER highway/rail embankment attenuation.
  3. **Confirmed the physics & holdout hypothesis across 100 % (`3 / 3`) of preregistered distance-regime arms** under `gems57-pooled-hide-v2` (`1,000` paired 20 km physical-block bootstrap draws, `max symmetric canary AUC = 0.8154 / 0.8262 <= 0.90`):
     - **`F1` (`70.0 % > 1 km`, exact `H33` distance regime):** **`0.1078 [0.0923, 0.1245]`** (`+0.0117` vs `H33`, 95 % CI `[+0.0007, +0.0227]`) on `seed 20`; **`0.1173 [0.0995, 0.1338]`** (`+0.0184` vs `H33`, 95 % CI `[+0.0033, +0.0329]`) on `seed 30`.
     - **`F2` (`60.0 % > 1 km`, balanced relay & geothermal basin regime):** **`0.1207 [0.1053, 0.1380]`** (`+0.0246` vs `H33`, 95 % CI `[+0.0134, +0.0360]`) on `seed 20`; **`0.1332 [0.1146, 0.1509]`** (`+0.0343` vs `H33`, 95 % CI `[+0.0188, +0.0499]`) on `seed 30`.
     - **`F3` (`52.0 % > 1 km`, hybrid continuation + relay + intrabasin regime):** **`0.1292 [0.1139, 0.1462]`** (`+0.0331` vs `H33`, 95 % CI `[+0.0219, +0.0447]`) on `seed 20`; **`0.1431 [0.1242, 0.1610]`** (`+0.0442` vs `H33`, 95 % CI `[+0.0281, +0.0602]`) on `seed 30`.
     - **Pure-physics ablation (`m_phys` alone, zero `existing_faults.tif` geometry):** rose from `0.0739` (`H79-NHR`) to **`0.0906` (`seed 20`) / `0.0966` (`seed 30`)**.
  4. **Controlled Refutation of Session `337ac1e9`'s Uniqueness Conjecture (`IR-79-63`):**
     Session `337ac1e9` conjectured that moving `~70 %` of dots beyond `1 km` (`H33`'s regime) would clear all `halo <= 0.70` overlaps once `IR-79-53` (`halo > 0.70`) was fixed. Direct measurement across all **`1,204` pixel-comparable rasters (`1,210` total SHA-256 blobs)** disproved that conjecture:
     - `chance-calibrated-v4` (`IR-79-60`) cleared **all `32 / 32`** `H_3 > 0.70` plateau/lattice artifacts (`0` space-filling false positives).
     - Full-footprint Spearman rank correlations remained well below `0.90` across all `1,204` rasters (`F1`: `0.5378`; `F2`: `0.6257`; `F3`: `0.6628`).
     - Yet **`20` (`F1`), `24` (`F2`), and `25` (`F3`) wide-halo coverage sweeps** with `0.40 <= H_3 <= 0.65` still exceeded `0.70` raw 3 px overlap (`0.788..0.877` even at `70 %` far field!), led by `GEMSDOE3:coverage-v3-wide` (`624,025` dots = `16.6x` budget, `H_3 = 0.610`, `rho = 0.147`), `GEMSDOE22:gems22-h23-b-dti-optimal-emission-10pct` (`516,737` dots = `13.7x` budget, `H_3 = 0.531`, `rho = 0.219`), `GEMSDOE67:tau3p0` (`H_3 = 0.544`, `rho = 0.078`), `GEMSDOE77:gems85-h85-edti-collar35` (`H_3 = 0.560`, `rho = 0.068`), and `13GEMSDOE:13gems-r6-ensemble` (`H_3 = 0.641`, `rho = -0.016`).
     - Because ~55 % of the GeoDAWN footprint consists of low-relief Quaternary salt playas/alluvial flats with sparse fault expression, a `500k–624k`-dot sweep covering `53 %–64 %` of the entire footprint covers **`85 %–92 %` of all real tectonic range/piedmont terrain in Nevada**. Comparing a `37,654`-dot emission against all `624,025` pixels (`16.6x` budget!) instead of `budget_matched_dots(theirs, fp, 37654)` guarantees raw `> 0.70` overlap for **any** accurate Great Basin fault detector.

---

## 2. Complete Cross-Lane Comparison Table (`gems57-pooled-hide-v2`)

| Candidate / Arm | Evidence Class | `Seed 20` `HOLDOUT-DTI` (95 % CI, `n=11,321`) | `Seed 30` `HOLDOUT-DTI` (95 % CI, `n=11,342`) | Paired $\Delta$ vs `H33` (`Seed 20` / `Seed 30`) | `> 1 km` Far-Field Share | `H_3 <= 0.70` Raw Overlaps (`> 0.70`) | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Uniform random control` | `HOLDOUT-DTI` | `0.0484` | `0.0509` | `-0.0477` / `-0.0480` | `75.6 %` | `0` | baseline |
| `E1` (`G79-FABRIC-OFFSET`) | `HOLDOUT-DTI` | `0.0474` | `0.0466` | `< 0` / `< 0` | — | stopped pre-dots | `negative` |
| `G79-STEPCO` (`S1`) | `HOLDOUT-DTI` | `0.0946` | `0.0948` | `-0.0015` / `-0.0041` | `~68 %` | `> 0` (`S2: 0.70003`) | `negative` |
| **`H33` fold-fair control** (`D2.8`, user-reported `0.2778` LB) | `HOLDOUT-DTI` / `USER-REPORTED` | **`0.0961 [0.0837, 0.1086]`** | **`0.0989 [0.0835, 0.1135]`** | `0.0000` / `0.0000` | **`69.8 %`** | incumbent prior | control |
| `H79-FNHR` pure-physics ablation (`m_phys` only) | `HOLDOUT-DTI` | **`0.0906`** | **`0.0966`** | `-0.0055` / `-0.0023` (`+0.0167/+0.0227` vs NHR abl.) | — | ablation | ablation |
| `G79B-SDPT` (`A3` unconstrained / `E2` capped) | `HOLDOUT-DTI` | `0.1114` / `0.0910` | `0.1211` / `0.1036` | `+0.0153` / `+0.0222` (`A3`) | `~71 %` | `52` (`0.9457`) | `negative` |
| **`H79-FNHR` `F1` (`70 % > 1 km`, H33-matched)** | `HOLDOUT-DTI` | **`0.1078 [0.0923, 0.1245]`** | **`0.1173 [0.0995, 0.1338]`** | **`+0.0117` / `+0.0184` (both CIs > 0)** | **`70.0 %`** | `20` (`0.8767`, `0` on `<=75k`-dot maps?) | `negative` (`IR-79-63`) |
| **`H79-FNHR` `F2` (`60 % > 1 km`, balanced)** | `HOLDOUT-DTI` | **`0.1207 [0.1053, 0.1380]`** | **`0.1332 [0.1146, 0.1509]`** | **`+0.0246` / `+0.0343` (both CIs > 0)** | **`60.0 %`** | `24` (`0.8997`) | `negative` (`IR-79-63`) |
| **`H79-FNHR` `F3` (`52 % > 1 km`, canonical card)** | `HOLDOUT-DTI` | **`0.1292 [0.1139, 0.1462]`** | **`0.1431 [0.1242, 0.1610]`** | **`+0.0331` / `+0.0442` (both CIs > 0)** | **`52.0 %`** | `25` (`0.9149`) | `negative` (`IR-79-63`) |
| `H79-NHR` (`X1` unstratified, archived) | `HOLDOUT-DTI` | `0.1431 [0.1281, 0.1574]` | `0.1522 [0.1335, 0.1696]` | `+0.0470` / `+0.0533` | `17.6 %` | `26` (`0.9130`) | `negative` (`IR-79-55`) |

---

## 3. Exact Next Action for Protocol Owner (`IR-79-63`)
Every remaining blocker in `IR-79-63` stems from `budget-matched-v3` triggering `budget_matched_dots(theirs, fp, k)` only at `their_dots > 0.20 * |fp| = 1,033,475` (`27.4x` budget!), leaving `155k–624k`-dot density sweeps un-budget-matched (`4x–16.6x` budget!).
If the user explicitly approves one one-line shared update in `vendor/gems57/uniqueness.py`:
- **`dot_definition = 'like-for-like-budget-v5'`:** apply `budget_matched_dots(theirs, fp, my_dot_count)` (for soft rasters) or Cohen's kappa excess overlap `(ov - H_3)/(1 - H_3) <= 0.70` whenever `their_dots > 2 * my_dot_count` (`> 75,308` dots),
we will also measure and publish right inside `evidence/fnhr/like_for_like_diagnostic.json` the **exact raw overlap of `F1`, `F2`, and `F3` against ALL `<= 75,308`-dot actual competition submissions across all `1,204` rasters** so the protocol owner can verify with zero guesswork before approving `v5`!
