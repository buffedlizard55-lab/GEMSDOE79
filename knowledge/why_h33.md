# Forensic Analysis of H33 (`0.2778`), Metric Ceiling Theory (`0.4413`), and Empirical Validation via `G79-THVC`

## Executive Answer

1. **What `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`) actually is (byte-level proof):**
   Hash-verified byte comparison (`scripts/analyze_h33.py`, output in `evidence/h33_forensics.json`) proves that `H33` (`sha256: b3cd7386...`) is **not** a newly trained model. It is **pixel-for-pixel identical** to the earlier `D2.8` binary Poisson-disk dot submission (`44,090` isolated `1.0` pixels, `sha256: f872c184...`) with **all `6,436` dots at Euclidean distance `<= 2.0 px` (`200 m`) from `existing_faults.tif` set to `0.0`**, leaving exactly **`37,654` binary `1.0` pixels** (`0` pixels outside `D2.8`, `0` 8-neighbour adjacent pairs).
2. **Why `H33` (`0.2778` reported) beat dense continuous probability maps (`0.06–0.12` reported) and slightly edged `D2.8` (`0.2768` reported):**
   Under the official **Distance-Weighted Tversky Index (`DTI`)** with triangular kernel $k(d)=\max(1-d/300\text{ m},0)$, $\alpha=0.2$, $\beta=0.8$:
   $$\text{TP}_w = \sum_{y \in \mathcal{T}} \max_{x \in \mathcal{F}} p(x)\,k(\|x-y\|), \qquad \text{FP}_w = \sum_{x \in \mathcal{F}} p(x)\Big(1 - \max_{y \in \mathcal{T}} k(\|x-y\|)\Big)$$
   Notice the critical asymmetry: **$\text{TP}_w$ takes a point-wise $\max$ over predictions within $300\text{ m}$ of truth, whereas $\text{FP}_w$ takes a linear $\sum$ over all predicted pixels!** Emitting dense continuous probabilities ($5.17\times 10^6$ non-zero cells) inflates $\sum p(x)$ across background basins by orders of magnitude while $\max p(x)k(d)$ along a narrow fault trace cannot exceed $1$ per truth pixel. Converting continuous probability corridors into spaced binary `1.0` impulses (`D2.8`) eliminates redundant $\text{FP}_w$ mass inside each $300\text{ m}$ halo (`0.06–0.12` $\to$ `0.2768`), and deleting `6,436` dots within `<= 200 m` of already-mapped faults (`H33`) removes false-positive flank echoes parallel to masked `existing_faults.tif` traces (`+0.0010` reported gain: `0.2768` $\to$ `0.2778`).
3. **Score Provenance & Leaderboard Reconciliation (`0.2778` vs `0.3195` vs `0.4413`):**
   - `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`: **unverified historical filename-to-score report** in the prompt ledger (matching public Rank #48 `extradr19 = 0.2778` on the live leaderboard, without a signed submission-page receipt linking that hash).
   - `0.3195` in one older prompt paragraph: **stale earlier snapshot** superseded by later public submissions.
   - **`0.4413` (`xiaofanhu`, Rank #1)**: **verified official public leaderboard observation** retrieved directly from `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/` on `2026-10-21` (`knowledge/official_sources.json`, ID `DD-LEADERBOARD`). **No candidate in this repository has an `ORGANIZER-CONFIRMED` submission-page receipt**, and public leaderboard observations are never projected or claimed as this candidate's score.
4. **Is a higher score achievable — and did `G79-THVC` prove it empirically on strict spatial holdout?**
   **Yes, decisively.** On the unmodified shared whole-segment hide-and-recover spatial holdout evaluator (`gems57-pooled-hide-v2`, 300 m visible buffer, exact visible-fault pixel masking, `1,000`-draw `20 km` spatial block bootstrap 95% CIs), `G79-THVC` (`EXP-79-3`) nearly **doubles** the fold-fair `H33` benchmark across **both independent spatial holdout seeds**:
   - **Primary Canonical Holdout (`seed=20`, `n = 11,321` withheld positive pixels):**
     - `C2 H33 Fold-Fair Benchmark`: **`HOLDOUT-DTI = 0.0961`** (`95% CI: [0.0831, 0.1090]`)
     - `EXP-79-3 G79-THVC (Charnes-Cooper)`: **`HOLDOUT-DTI = 0.1905`** (`95% CI: [0.1741, 0.2069]`) — paired block gain **`+0.0944` (`+98.3%`, `95% CI: [+0.0785, +0.1100]`, `P(THVC > H33) = 1.000`)**
   - **Independent Secondary Holdout (`seed=30`, `n = 11,342` withheld positive pixels):**
     - `C2 H33 Fold-Fair Benchmark`: **`HOLDOUT-DTI = 0.0989`** (`95% CI: [0.0854, 0.1128]`)
     - `EXP-79-3 G79-THVC (Charnes-Cooper)`: **`HOLDOUT-DTI = 0.1944`** (`95% CI: [0.1774, 0.2126]`) — paired block gain **`+0.0955` (`+96.6%`, `95% CI: [+0.0792, +0.1122]`, `P(THVC > H33) = 1.000`)**

---

## Byte-Level Forensics of `D2.8` vs `H33`

All counts below are **exact raster measurements** reproduced deterministically by `.venv/bin/python scripts/analyze_h33.py` (`evidence/h33_forensics.json`):

| Measured Quantity | Exact Value |
|---|---:|
| `D2.8` (`d28-zeros`) positive pixels (`value == 1.0`) | `44,090` |
| `H33` (`h33-h33-2-b2-...-zeros`) positive pixels (`value == 1.0`) | `37,654` |
| `H33` pixels not present in `D2.8` | `0` |
| `D2.8` pixels removed in `H33` | `6,436` |
| Pixel disagreements with `(D2.8 > 0) & (dist_to_catalogue > 2.0 px)` | `0` |
| `H33` positive pixels with an 8-neighbour positive | `0` |
| `H33` median distance to `existing_faults.tif` | `19.6469 px` (`1.965 km`) |
| Share of `H33` dots `> 1.0 km` from `existing_faults.tif` | `69.83%` |

---

## Why `H33` Stalled — The Four Structural Bottlenecks Unlocked by `G79-THVC`

Evaluating `H33` and `G79-THVC` across six physically distinct structural regimes on `seed=20` (`evidence/g79_thvc_results.json`) reveals **why** `H33` left half of achievable `HOLDOUT-DTI` on the table:

| Structural / Observation Regime (`seed=20`) | Withheld Fault Pixels (`n`) | `C2 H33` `HOLDOUT-DTI` | `EXP-79-2 THVC` (`d=2.8`) | `EXP-79-3 THVC` (Charnes-Cooper) | Multiplier vs `H33` |
|---|---:|---:|---:|---:|---:|
| **1-m 3DEP LiDAR Covered (`75.01%` of area)** | `8,337` | `0.0240` | `0.0460` | **`0.0511`** | **`2.13×`** |
| **Blind Non-LiDAR Gap (`24.99%` of area)** | `2,984` | `0.0145` | `0.0468` | **`0.0477`** | **`3.29×`** |
| **Alluvial Basin & Piedmont Conduits** | `6,419` | `0.0191` | `0.0520` | **`0.0496`** | **`2.60×`** |
| **Steep Mountain-Block Bedrock** | `4,902` | `0.0192` | `0.0385` | **`0.0445`** | **`2.32×`** |
| **Elastic Crack-Tip / Relay (`<= 1 km` along strike)** | `3,891` | `0.0398` | `0.0563` | **`0.0584`** | **`1.47×`** |
| **Far Blind Basin (`> 1 km` from any visible fault)** | `7,430` | `0.0140` | `0.0291` | **`0.0348`** | **`2.49×`** |

1. **The 24.99% Nevada 1-m LiDAR Blind Gap (`3.29×` lift):** Exactly `1,291,341 / 5,167,373` in-footprint cells (`24.99%`) lack 1-m 3DEP LiDAR coverage (`dem_100m.tif` = `NaN`). `G79-THVC` explicitly incorporates a domain-adaptive context gate (`lidar_present`) and multi-scale non-LiDAR topographic/geophysical/thermal channels (`det_elev_prom_600m`, `block_step_elev_600m`), raising non-LiDAR discovery from `0.0145` to **`0.0477` (`+229%`)**.
2. **Subsurface & Geothermal Conduit Physics in Covered Basins (`2.49×–2.60×` lift):** Under Holocene playa/fan cover where scarps erode below `< 0.5 m`, official DOE GDR 1391 (`DOI: 10.15121/1881483`) **2-m shallow temperature probes (`temp_2m_probes.csv`), Quaternary sinter/travertine/tufa mounds (`paleogeothermal.geojson`), geothermometry spring temperatures (`geochem_springs.csv`), volcanic vents (`volcanic_vents.geojson`), magnetic demagnetization + Smectite clay alteration lows, and gravity basement-depth steps (`grav_bdepth`)** detect active blind fluid conduits.
3. **Anisotropic Elastic Mode-II/III Crack-Tip Mechanics vs Isotropic Distance (`#1` & `#2` features overall):** Instead of `H33`'s isotropic distance collar, `G79-THVC` computes along-strike crack-tip propagation lobes ahead of visible fault endpoints (`net_tip_fwd_35px` = **`11.55%` Stage-1 gain**, `net_tip_x_grav_bdepth` = **`10.37%` Stage-1 gain**), cleanly distinguishing high-probability along-strike fault relays from low-probability flank stress shadows.
4. **Exact Charnes-Cooper Submodular Kernel Allocation (`+0.0209` to `+0.0258` pure placement lift):** Replacing fixed `d = 3.0 px` Poisson-disk spacing (`EXP-79-2`) with exact Charnes-Cooper submodular greedy optimization of marginal $\mathbb{E}[\Delta\text{TP}_w] - \lambda_{\text{fp}}\mathbb{E}[\Delta\text{FP}_w]$ (`lambda_fp = 0.0022`, `min_sep = 1.9 px`, `EXP-79-3`) increases `HOLDOUT-DTI` from `0.1697` $\to$ **`0.1905`** (`seed=20`) and `0.1686` $\to$ **`0.1944`** (`seed=30`) on the **identical posterior surface**.
