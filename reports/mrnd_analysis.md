# H79-MRND Experiment `M1` — Multi-Regime Brittle-Crustal Nested Discovery & Complete Three-Tier Registry Theorem

- **Session / Branch:** `arena/800321e2-gemsdoe79` (`2026-10-22`)
- **Preregistration:** [preregistration_mrnd.json](../registry/preregistration_mrnd.json) (locked prior to execution at SHA-256 `ea12fe39a45287a32152958bdfa5160f8514b0bd0200c613b46a245f7d22b265` in [preregistration_mrnd_sha256.txt](../evidence/preregistration_mrnd_sha256.txt))
- **Archival Run Card:** [run_card_mrnd.json](../run_card_mrnd.json) · **Verdict:** `negative` (`OK TO SUBMIT: NO.`, `0` weekly slots spent; canonical artifact remains `H79-NHR` in [run_card.json](../run_card.json))

---

## 1. Scientific Motivation & Multi-Modal Feature Engineering (`77` Zero-Leakage Features)

Prior lanes in `GEMSDOE79` exposed an acute scientific tension:
- `GEMSDOE32` (`H33`, user-reported public score `0.2778`) achieved broad spatial reach (`median = 1,960 m` from mapped faults) across 19 regional geophysical/DEM bands, but masked all cells within `200 m` of known traces and omitted physically dequantized 3DEP lidar scarps, road-cut deseaming, and INGENIOUS aqueous geothermometry.
- `H79-NHR` achieved strong offline `HOLDOUT-DTI` (`0.1431 / 0.1522` in [x1_holdout_seed20.json](../evidence/nhr/x1_holdout_seed20.json)), but trained a single global model dominated by `log_dist_visible`, crowding **82.4% of its dots inside `<= 1.5 km`** (`median = 539 m`) and colliding with **26 ordinary non-space-filling prior submissions** (`max = 0.9130`).
- `H79-ASYM` ([run_card_asym.json](../run_card_asym.json)) relied solely on uphill-facing lidar scarp excess and collided with **32 ordinary non-space-filling prior submissions** (`14` even after chance subtraction).

`H79-MRND` ([src/gems79/mrnd.py](../src/gems79/mrnd.py)) integrates **all 11 non-catalogue SHA-256-pinned datasets** into **77 zero-leakage physical features** across three specialized Basin-and-Range structural regimes:

1. **Physically Decoded 3DEP Scarp Dipoles, Geomorphic Scarp-vs-Channel Invariant & TIGER Deseaming:**
   - Exact inverse quantisation per [lidar_scarp_features.json](../registry/data_manifest.json) ($x = x_{\max}((q-1)/254)^2$ on `sqrt` bands; `q == 0 -> NaN`).
   - Road/rail/canal embankment deseaming via `tiger_road_distance_m.tif` ($w_{\text{road}} = \mathrm{clip}(d_{\text{road}} / 150\text{ m}, 0.15, 1.0)$).
   - Contour-parallel normal fault scarp vs down-slope drainage bank invariant:
     $$\mathrm{scarp\_vs\_channel}(x) = \frac{\max(x_{\text{up}}, x_{\text{down}}) - x_{\text{cross}}}{\max(x_{\text{up}}, x_{\text{down}}) + x_{\text{cross}} + 10^{-3}} \in [-1, +1].$$
   - Dimensionless footwall erosional canyon penalty $C_{\text{canyon}}(x) \in [0, 1]$ suppressing bare crystalline range cores lacking sedimentary cover (`Hermant et al., 2025`).
2. **Multi-Scale Potential-Field Worms & Sedimentary Cover Interaction:**
   - Multi-scale Gaussian horizontal-gradient ("worm") and Laplacian ridges across $\sigma \in \{200\text{ m}, 500\text{ m}, 1.2\text{ km}\}$ on `iso_grav_anom`, `rtp`, `TMI_up150`, `cond_surf`, and `tc`, plus $\log(1 + \mathrm{depth\_to\_base\_surf}) \times |\nabla G_{\sigma=2}(\mathrm{iso\_grav\_anom})|$.
3. **INGENIOUS (`DOE GDR 1391`) Hydrothermal Upflow & Geothermometry (`dist_known_fault_px` Strictly Stripped):**
   - Multi-scale thermal plumes ($\sigma \in \{600\text{ m}, 2{,}000\text{ m}\}$) from `27,092` wells/springs (`temp_c > 25 °C`) and deep reservoir silica/cation geothermometry plumes ($\sigma \in \{800\text{ m}, 2{,}400\text{ m}\}$, `max(quartz, chalcedony, Na-K-Ca) > 70 °C`) gated onto basement gravity horizontal gradients, plus Quaternary volcanic vent proximity (`21` vents).
4. **Three Specialized Nested Hide-to-Recover `HistGradientBoostingRegressor` Models (`R1/R2/R3`):**
   - **Regime I (`0 < d <= 1,400 m`, share $q_1 = 0.24$):** Relay ramps, directional crack-tip cones (`tip_propagation_cone`), and splay strands.
   - **Regime II (`1,400 < d <= 4,500 m`, share $q_2 = 0.34$):** Piedmont bajada scarps and synthetic/antithetic normal faults.
   - **Regime III (`d > 4,500 m`, share $q_3 = 0.42$):** Concealed intra-basin horst/graben steps and blind geothermal upflow conduits.

---

## 2. Measured Experiment `M1` Results (`HOLDOUT-DTI` & Pre-Placement Uniqueness Gate)

### 2.1 Single-Feature Leakage Canary (`LEAKAGE-CANARY`)

Across **616 single-feature tests** (`77` features × `4` quadrants × `2` seeds in [m1_holdout_seed20.json](../evidence/mrnd/m1_holdout_seed20.json) and [m1_holdout_seed30.json](../evidence/mrnd/m1_holdout_seed30.json)):
- **Seed 20 max symmetric AUC:** `0.8514` (`geom_log_dist_visible_tip`, `0 / 308` suspicious) — **PASS (`<= 0.90`)**
- **Seed 30 max symmetric AUC:** `0.8589` (`geom_log_dist_visible_tip`, `0 / 308` suspicious) — **PASS (`<= 0.90`)**

### 2.2 Two-Seed Spatially-Blocked Holdout Evaluation (`gems57-pooled-hide-v2`)

*Note: All numbers below are offline `HOLDOUT-DTI` proxy measurements on withheld mapped fault components (`1,000` paired 20 km spatial-cluster bootstrap draws), never public leaderboard projections.*

| Evaluation Seed | Withheld Positive Pixels | `H79-MRND` Candidate (`0.24/0.34/0.42` Regimes) | `H33` Fold-Fair Control | Paired $\Delta$ vs `H33` `[95% CI]` | Single-Regime Static Ablation | Paired $\Delta$ vs Ablation `[95% CI]` | Uniform Random Control |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Seed 20** | `11,321` | **`0.1044`** `[0.0902, 0.1184]` | `0.0961` `[0.0837, 0.1086]` | **`+0.0084`** `[-0.0041, +0.0211]` | `0.0801` `[0.0648, 0.0957]` | **`+0.0243`** `[+0.0082, +0.0411]` | `0.0484` `[0.0432, 0.0537]` |
| **Seed 30** | `11,342` | **`0.1236`** `[0.1065, 0.1414]` | `0.0989` `[0.0842, 0.1120]` | **`+0.0247`** `[+0.0095, +0.0389]` | `0.0817` `[0.0671, 0.0952]` | **`+0.0419`** `[+0.0269, +0.0581]` | `0.0482` `[0.0433, 0.0522]` |

Even while forcing **42% of candidate mass beyond `4.5 km` from all mapped faults** (`R3`), `H79-MRND` surpasses `h33_foldfair_control` on both seeds (`+8.7%` relative on Seed 20; **`+25.0%` relative on Seed 30 with paired 95% CI strictly above zero**) and outperforms single-regime static HGB by **`+30.3%` to `+51.3%`** (`95% CIs strictly > 0` on both seeds).

---

## 3. Pre-Placement Surface Uniqueness Gate & The Complete Three-Tier Registry Theorem

Mandatory pre-placement screening ([uniqueness_surface.json](../evidence/mrnd/uniqueness_surface.json), [surface_diagnostic.json](../evidence/mrnd/surface_diagnostic.json)) across all `992` frozen blobs (`986` strict reference-grid rasters) revealed **zero rank-correlation duplicates (`worst Spearman = 0.2582 <= 0.90`)** and uncovered the **exact three-tier combinatorial structure** of the entire `GEMSDOE` family registry:

| Registry Tier | Count of Rasters | `their_dots` Range | `halo_coverage` Range | `H79-NHR` Flags | `H79-ASYM` Flags | **`H79-MRND` (`M1`) Flags** | Mathematical Mechanism |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **Tier 1 — Space-Filling / Lattice Priors** | `30` | `206,895 .. 5,167,373` | `0.7211 .. 1.0000` | `30 / 30` | `30 / 30` | `30 / 30` | **Combinatorial Pigeonhole Lower Bound:** $\operatorname{ov}_{3\text{px}}(M, R) \ge \max(0, 1 - U(R)/K)$ forces `>= 0.8270` on `13GEMSDOE` lattice (`U = 6,514`) and `1.0000` on `GEMSDOE48` (`U = 0`) for **every** `37,654`-dot set. |
| **Tier 2 — Over-Emitted Wide Blankets (`4.5x..16.6x` Budget)** | `10` (`6` unique maps) | `167,597 .. 624,025` | `0.5312 .. 0.6760` | `10 / 10` | `10 / 10` | `10 / 10` | **Threshold Escape Trap:** `representation_class` triggers top-`K` matching only above `0.15 * footprint = 775,105` cells, leaving `168k..624k`-dot blankets (`GEMSDOE3:coverage-v3-wide` `624,025` dots; `GEMSDOE22:10pct` `516,738` dots; `13GEMSDOE` `344,041` & `246,469` dots; `GEMSDOE77` `201,260` dots; `GEMSDOE67` `167,597` dots) un-budget-matched (`0.7302 .. 0.8163`). |
| **Tier 3 — All Normal-Budget Family Submissions (`<= 167,596` Dots)** | **`946` strict (`950` same-shape)** | **`1 .. 167,596`** | **`0.0000 .. 0.6365`** | `16` flagged | `22` flagged | **`0 / 950` (`0.0%`)** | **`H79-MRND` clears 100% of genuine normal-budget family submissions across all 88 repositories (`max overlap <= 0.70`, `max Spearman = 0.2582`).** |

### Protocol Stop & Exact Human-Owner Resolution

Because the literal one-sided overlap rule failed at the pre-placement surface check (`40` flags across Tiers 1 + 2), **`H79-MRND` stopped immediately before placing final dots** ([m1_experiment_state.json](../evidence/mrnd/m1_experiment_state.json)), leaving `final_dots` ungenerated, `verdict = "negative"`, `OK TO SUBMIT: NO.`, and `0` slots spent.

Crucially, this proves that **merely exempting `halo_coverage > 0.70` (`IR-79-53`) is NOT sufficient** — Tier 2 wide-blanket files (`168k..624k` dots) still compare a `37,654`-dot map asymmetrically against up to `16.6×` as many dots. A single parameter-free human amendment in `vendor/gems57/uniqueness.py`:
$$\operatorname{ov}_{\text{sym}, 3\text{px}}(M, R) = \min\!\bigl(\operatorname{ov}_{3\text{px}}(M, R),\; \operatorname{ov}_{3\text{px}}(R, M)\bigr) \le 0.70$$
preserves strict `0.70` duplicate blocking between every pair of genuine sparse submissions while simultaneously eliminating both Tier 1 (`halo > 0.70`) and Tier 2 (`168k..624k` blanket) asymmetry without magic thresholds or manual file blacklists.
