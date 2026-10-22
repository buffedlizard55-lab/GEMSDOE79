# Session `87f53313` — Three-Pass Scientific, Forensic, & Software Hardening Review

- **Date (UTC):** `2026-10-22`
- **Branch:** `arena/87f53313-gemsdoe79`
- **Automated Gate Decision:** **`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`** (`scripts/submission_status.py` exit `2`; `scripts/select_submission.py` exit `2`; zero human inspection required)
- **Session Budget Accounting:** `0 / 3` scientific experiments executed · `0` new competition GeoTIFFs promoted · `0` weekly submission slots spent
- **Session Evidence Directory:** [`evidence/review_87f53313/`](../evidence/review_87f53313/) ([`run_card.json`](../evidence/review_87f53313/run_card.json), [`preflight.json`](../evidence/review_87f53313/preflight.json), [`witness_verification.json`](../evidence/review_87f53313/witness_verification.json), [`three_tier_obstruction_summary.json`](../evidence/review_87f53313/three_tier_obstruction_summary.json), [`feature_stack_audit.json`](../evidence/review_87f53313/feature_stack_audit.json), [`format_validation.json`](../evidence/review_87f53313/format_validation.json), [`browser_review.json`](../evidence/review_87f53313/browser_review.json))

---

## 1. Executive Decision & Why No New Submission TIFF Was Promoted

1. **Automated download/submit status is loud and fail-closed:** Canonical research artifact [`docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif) (`SHA-256: d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`, `35,093` binary `{0, 1}` pixels) passes all `15 / 15` local GeoTIFF format/grid/range checks (`EPSG:32611`, `3730 × 3292`, `100 m`, `float32`, `0` NaN, `0` Inf, values in `[0, 1]`, `0` on-catalogue pixels) and is **OK TO DOWNLOAD** for research inspection, but is **NOT OK TO SUBMIT** (`-DO-NOT-SUBMIT` filename suffix, `verdict: "negative"`, `ok_to_submit: false`).
2. **Two independent protocol blockers forbid starting a new experiment or spending a weekly slot in this session:**
   - **No assigned method lane in the prompt (`IR-79-02`):** `README.md` retains the literal placeholder `[PASTE THE ONE METHOD PARAGRAPH FOR THIS SESSION HERE]`. Under `AGENTS.md`, closed lanes (`G79-THVC`, `H79-NHR`, `G79-CFSKD`, `H80-PILOTS`, etc.) are immutable (`enforce_open_lane` exit `2`), and inventing an unassigned private lane or private fork of `vendor/gems57/` is forbidden.
   - **Three-tier mathematical obstruction in the pinned family registry ([`three_tier_obstruction_summary.json`](../evidence/review_87f53313/three_tier_obstruction_summary.json)):**
     - **Tier 1 (Literal positive support, `scripts/preflight_new_lane.py --restore` exit `2`):** `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` (`SHA-256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) has finite positive values on all `5,167,373` footprint cells (`0` uncovered off-catalogue cells out of `5,106,385`), forcing `1.0000 > 0.70` 3-px forward overlap for every nonempty candidate.
     - **Tier 2 (`budget-matched-v3` continuous plateaus):** Four SHA-256-verified rasters (`GEMSDOE48` ×3 + `5GEMSDOE` ×1) have tie-inclusive top-`37,654` support covering all `5,167,373` footprint cells (`0` uncovered off-catalogue cells), still forcing `1.0000 > 0.70` forward overlap even under `Amendment D-1` (`budget-matched-v3`).
     - **Tier 3 (Sparse binary lattice Pigeonhole bound):** `13GEMSDOE` `r13-lattice-s5_v2_{zerofill,nan-outside}.tif` (`206,895` strictly binary `{0, 1}` dots = `4.004%` support, below the `20%` dense threshold) places a `5 px` grid across the study area ($\sup_{x \in \mathbb{Z}^2} d(x, 5\mathbb{Z}^2) = \sqrt{8} \approx 2.8284 < 3.0\text{ px}$), leaving only **`6,514` uncovered off-catalogue cells** out of `5,106,385`. By the Pigeonhole Principle, *every* `37,654`-dot off-catalogue candidate has exact minimum 3-px forward overlap $(37{,}654 - 6{,}514)/37{,}654 = 15{,}570/18{,}827 \approx 0.827004 > 0.70$ (and `28,579 / 35,093 = 0.814379 > 0.70` at `35,093` dots).

---

## 2. Why `GEMSDOE32` `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` Reported `0.2778` — and Whether/How It Can Be Beaten

### 2.1 Evidentiary Status of `0.2778`, `0.3195`, and `0.4413`
- **`0.2778` (`USER-REPORTED / UNVERIFIED`):** Not `ORGANIZER-CONFIRMED`. Live verification of [`GEMSDOE32`'s public site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) on `2026-10-22` confirms the artifact (`SHA-256: c55bafc470054e82…`) is self-labelled **`UNSCORED`** with `"projected live DTI 0.2747 (a MODEL, not a score). NO ORGANISER SCORE EXISTS for this or any artifact in this repository."`
- **Live DrivenData Public Leaderboard (`PUBLIC-OBSERVATION`, all 3 chunks read `2026-10-22` UTC at [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)):**
  - `#1 xiaofanhu`: **`0.4413`** (`27` submissions)
  - `#2 cfld__`: **`0.3904`** (`15` submissions)
  - `#3 Batik Shirt Brothers`: **`0.3894`** (`45` submissions)
  - `#21 kinghorton42`: **`0.3261`** · `#22 li002666`: **`0.3183`** (21 teams exceed `0.3195`; **`0.3195` does not appear anywhere on the public leaderboard**)
  - `#50 sam35`: **`0.2804`** (new entries on `2026-10-22` — including `#23 like2 = 0.3160`, `#27 like60986 = 0.3033`, `#32 dmitry_v = 0.2963` — raised the visible top-50 cutoff from `0.2784` earlier today to `0.2804`; `0.2778` is below `#50`).

### 2.2 Byte-Lineage & Official `DW-Tversky` Mechanism
- **Exact pixel lineage (`RASTER-MEASUREMENT`, [`evidence/review_e4a4422d/h33_remeasurement.json`](../evidence/review_e4a4422d/h33_remeasurement.json)):** `H33` (`37,654` positive pixels) equals `D2.8` (`44,090` positive pixels, `SHA-256: 64376734…`) minus the **exact `6,436` off-catalogue pixels at Euclidean distance $0 < d_{\text{cat}} \le 2\text{ px}$ ($\le 200\text{ m}$)** from `existing_faults.tif` (`0` deletions on catalogue, `0` disagreements across all `12,279,160` cells).
- **Exact metric algebra ([DrivenData `page/967`](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation)):** With $\alpha = 0.2$, $\beta = 0.8$, and triangular kernel $k(d) = \max(1 - d / 300\text{ m}, 0)$:
  $$\text{TP}_w = \sum_{g \in G} \max_{x: d(x, g) \le R} p(x)\,k(d(x, g)), \qquad \text{FP}_w = \sum_{x: p(x) > 0} p(x)\!\left[1 - \max_{g \in G} k(d(x, g))\right], \qquad \text{DTI} = \frac{\text{TP}_w}{0.2\,\text{TP}_w + 0.2\,\text{FP}_w + 0.8\,|G| + \epsilon}.$$
  Because $\text{TP}_w$ takes a **pointwise $\max$** per truth pixel while $\text{FP}_w$ **sums** over every emitted pixel, pruning $\Delta S = 6{,}436$ near-catalogue flank dots strictly increases `DTI` whenever their lost unique max-kernel credit $\Delta \text{TP}_w$ is smaller than the marginal break-even threshold:
  $$\frac{\Delta \text{TP}_w}{\Delta \text{FP}_w} < \frac{0.2\,\text{DTI}}{1 - 0.2\,\text{DTI}} \approx 0.0588 \quad (\text{at }\text{DTI} \approx 0.2778).$$
  Because known USGS/INGENIOUS fault pixels are masked from evaluation (`DD-MASK`), and dots placed at $d_{\text{cat}} = 3\text{ px}$ (`300 m`) already supply partial kernel coverage up to the collar boundary while avoiding lateral stress-shadow false positives immediately adjacent to mapped traces, collar pruning removes summed $\text{FP}_w$ mass at minimal $\text{TP}_w$ loss — *conditional* on the organizer's hidden truth distribution (which cannot be proven locally without an organizer receipt).

### 2.3 Can `0.2778` Be Beaten?
- **On spatially blocked catalogue holdout (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`):** Canonical `G79-THVC` already nearly doubles the fold-fair `H33` control on both seeds (`0.1905 [0.1741, 0.2069]` vs `0.0961 [0.0831, 0.1090]` on seed 20, `11,321` withheld positives, paired $\Delta = +0.0944 [0.0784, 0.1098]$; `0.1944 [0.1774, 0.2126]` vs `0.0989 [0.0854, 0.1128]` on seed 30, `11,342` withheld positives, paired $\Delta = +0.0955 [0.0778, 0.1133]$).
- **Why that does NOT guarantee beating `0.2778` or `0.4413` on the organizer test set:** `G79-THVC` concentrates `97.58%` of its `35,093` dots within `2 km` of mapped faults (`median d_cat = 565.7 m`), whereas `H33` places `49.20%` of its `37,654` dots beyond `2 km` (`median d_cat = 1,964.7 m`). Because organizer Phase 1 & Phase 2 labels consist of **expert-mapped faults omitted from USGS/INGENIOUS** (including blind intra-basin structures and non-LiDAR valleys across the `24.99%` 3DEP gap), beating `0.2778` and closing toward `#1 = 0.4413` requires:
  1. **Protocol unblocking:** a prospective owner decision resolving the 3-tier registry halo obstruction; and
  2. **Catalogue-free far-field precision:** fusing `G79-THVC`'s near-tip continuation physics with zero-catalogue subsurface/seismicity/potential-field fault localization beyond `2 km` (ranked in [`research/hypotheses_87f53313.md`](../research/hypotheses_87f53313.md)).

---

## 3. New 19-Band `training_features.tif` Byte Forensics (`evidence/review_87f53313/feature_stack_audit.json`)

Restoring all `13 / 13` SHA-256-pinned inputs via `scripts/restore_data.py --preserve-receipt` (`SHA-256: 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`) and inspecting all 19 bands cell-by-cell uncovered three previously undocumented data-contract irregularities:

1. **Band 6 (`tc`) carries `+12` extra interior `-3.4028235e+38` sentinel cells (`3,073` vs `3,061`):**
   - Bands `1–5` and `7–19` (18 bands) each contain `7,113,308` float32 sentinels (`3,061` inside the `5,167,373`-cell submission footprint).
   - **Band 6 (`tc`) contains `7,113,320` sentinels (`3,073` inside the footprint — `+12` extra interior sentinel cells).**
   - Consequently, $18 \times 7{,}113{,}308 + 7{,}113{,}320 = 135{,}152{,}852 + 12 = 135{,}152{,}864$ (correcting `IR-79-153`'s arithmetic claim that `7,113,308 × 19 = 135,152,864`). Any pipeline that builds a single validity mask from Band 1 alone leaks **12 `-3.4028235e+38` cells** from Band 6 into features or predictions — a direct vector for `"Predicted values must be in range [0, 1]"`.
2. **Band 6 (`tc`, valid range `[+2.953, +88.567]`, median `+18.482`, zero negative values) is GeoDAWN Radiometric Total Count / Dose Rate, NOT `"Tilt angle or total curvature"`:**
   - A magnetic tilt angle $\tan^{-1}(M_z / \|\nabla_h M\|)$ spans $[-\pi/2, +\pi/2]$ (or $[-90^\circ, +90^\circ]$) around zero; Band 6 is strictly positive (`2.95–88.57`) and matches DrivenData [`page/967`](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#provided-features)'s own `gems_tc_tmi.png` caption (*"total radiometric counts per second (left) and total magnetic intensity (right)"*).
3. **Band 10 (`deq_n100a15`, valid range `[0.0, 4,962,515]`, median `622.8`) is INGENIOUS *Dependent* (Swarm/Aftershock) Earthquake Density, NOT `"Distance to earthquake"`:**
   - Official [DOE GDR Submission `1391`](https://gdr.openei.org/submissions/1391) (`doi:10.15121/1881483`, `seismicity_INGENIOUS_regional_data.zip`) documents paired Nevada Geodetic Laboratory **independent (`ieq_n100a15`, Band 16, `[236.8, 7,869.5]`) and dependent (`deq_n100a15`, Band 10) earthquake density** grids ($n=100$, $a=15$). Treating Band 10 as distance inverts its physical sign (`0` away from swarms, `4.96e6` inside active swarms).

---

## 4. Ranked Unimplemented Candidate Geological Hypotheses

Full mathematical transforms, exact official data links, non-fault mimics, and novelty audits against all 20+ closed `GEMSDOE79` lanes (`E1` through `G79-CFSKD`, `H80-PILOTS`, and `G79-CJX` from `PR #102`) are documented in [`research/hypotheses_87f53313.md`](../research/hypotheses_87f53313.md):

1. **`G79-SWARM` (Rank 1 — High qualitative value, Low compute cost, Data-ready):** Dimensionless swarm-clustering ratio $\log_{10}((\text{deq}_{10} + 10)/(\text{ieq}_{16} + 10))$ gated by transtensional GPS dilatation + shear (`Bands 7, 8`) and `depth_to_base_surf > 400 m` (`Band 15`), localized onto anisotropic hypocentral lineaments from `Seismicity.zip` to detect blind fluid-driven geothermal fracture meshes.
2. **`G79-BLC` (Rank 2 — Moderate–High qualitative value, Moderate cost, Data-ready):** Four-quadrant bilateral multivariate lithology-truncation detector across `rtp` (`Band 2`), `iso_grav_anom` (`Band 13`), and properly masked/interpreted radiometric Total Count `tc` (`Band 6`, masking all `3,073` interior sentinels) for cryptic low-relief transverse transfer faults.
3. **`G79-RSS` (Rank 3 — Low–Moderate qualitative value, Moderate cost, Data-ready):** Multi-scale detrended-elevation (`Band 12 det_elev`) Hessian structural-saddle detector ($\lambda_1 < 0 < \lambda_2$) crossed orthogonally by isostatic-gravity horizontal gradients (`Bands 5, 13, 18`) and screened against steep range-front scarps (`Band 19 det_elev_slope`) to catch unmapped inter-range relay ramps without requiring visible catalogue tips.
4. **`G79-HFR` (Rank 4 — Uncertain regional recall, High acquisition/QA cost, NOT data-ready in sandbox):** Paired warm/cool convective well heat-flow dipoles from [USGS `doi:10.5066/P9BZPVUC`](https://doi.org/10.5066/P9BZPVUC) aligned along `depth_to_base_surf` (`Band 15`) corridors; deferred until external bytes (`sciencebase.gov` unreachable in sandbox) are SHA-256-pinned and screened for well-depth bias.

---

## 5. Three Explicit Verification & Audit Passes

### Pass 1 — Implementation, Restoration, & Primary-Source Verification
- Read `README.md` (including the verbatim `<details>` original prompt), `AGENTS.md`, `run_card.json`, required preregistrations, `reports/irregularities.md`, H33 forensics, and prior hypothesis files.
- Verified primary official sources live via `fetch_page`: [DrivenData Problem Description (`page/967`)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) (both chunks), [DrivenData Public Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (all 3 chunks), [DOE Official Rules PDF (`96647.pdf`)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (title, eligibility §1.1–1.4, submission & judging §3.1–3.7, Appendix A.1), [USGS GeoDAWN (`doi:10.5066/P93LGLVQ`)](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR `1391` (`doi:10.15121/1881483`)](https://gdr.openei.org/submissions/1391), [GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/), [EPSG:32611](https://epsg.io/32611), [Tversky Index Reference](https://en.wikipedia.org/wiki/Tversky_index), and [GEMSDOE32 Public Site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html).
- Restored and SHA-256-verified all `13 / 13` manifest inputs via `scripts/restore_data.py --preserve-receipt` without mutating `data/restore_receipt.json`, re-ran `preflight_new_lane.py --restore` (`exit 2`), validated the canonical TIFF/ZIP, and measured the 19-band feature stack and 3-tier registry obstructions.

### Pass 2 — Codebase Bug Hunt, Concurrent-PR Forensic Audit, & Remediation
Found and fixed **concrete software and audit defects** (`IR-79-191`..`IR-79-193`, atop `05ba998` without modifying any pinned `vendor/gems57/` file or frozen receipt) and audited concurrent PRs:
1. **`scripts/verify_overlap_witness.py` workspace path leak & nested `--report` crash (`IR-79-192`):** Normalized `measured['witness_file']` relative to `root` (eliminating `/home/user/GEMSDOE79/...` leaks in generated witness JSONs) and added `args.report.parent.mkdir(parents=True, exist_ok=True)` before `open('x')`.
2. **`scripts/scan_tracked_rasters.py` multi-band blindness, sentinel `nodata` blindness, default receipt-overwrite hazard, & external-path crash (`IR-79-192`):** Read all bands (`s.read()`) instead of only Band 1 (`s.read(1)`), recorded `nodata_is_nan` + `nodata_outside_0_1`, flagged finite `nodata` sentinels outside `[0, 1]` (e.g., `-3.4028235e+38`) and `count != 1`, changed `--out` to fail closed (`open('x')`) unless `--overwrite` is passed (defaulting to stdout so historical `evidence/review_b40c0d45/tracked_raster_scan.json` is never clobbered), and handled external `--out` paths safely.
3. **`scripts/check_site.py` stale `docs/irregularities.html` blind spot & `scripts/browser_review.cjs` 8-page coverage (`IR-79-192`):** Added an explicit assertion checking that the exact sequence of `IR-79-*` IDs rendered in `docs/irregularities.html` matches `reports/irregularities.md`, and updated `scripts/browser_review.cjs` to dynamically iterate all pages in `docs/evidence/site_manifest.json` (`8` pages including `cjx-submission.html`, `24` viewport cases) while honoring `QA_REPORT_PATH`.
4. **`scripts/verify_registry_obstructions.py` duplicate `'emitted_dots'` dictionary key & `scripts/measure_registry_halo.py` `--catalogue` hardening (`IR-79-192`):** Removed the duplicate dict key, added an AST test scanning every `.py` file under `scripts/` and `src/` for duplicate string dict keys, and wired `--catalogue` CLI fail-closed validation (`FileNotFoundError` / `ValueError`, `allow_nan=False`, parent `mkdir`) in `scripts/measure_registry_halo.py`.
5. **Forensic audit of open `PR #100` (`G79-CONJ`, `arena/34dbe61d-gemsdoe79`, `IR-79-193`):** Direct inspection of `PR #100`'s `run_card.json` shows it self-promotes `"verdict": "promote"` and `"ok_to_submit": true` while (a) failing pre-placement surface dot overlap even after chance correction (`0.8921 > 0.70`), (b) failing final-dot 3-px overlap even restricted to sparse `<= 50k`-dot priors (`0.7290 > 0.70` vs `GEMSDOE25:gems25-factorial-bde-x123-sapd2-4-20261002-5e4b5a98d2c7-nan.tif`), (c) leaving `10 / 1,199` registry rows unchecked (`1,189` checked), and (d) rewriting `AGENTS.md`, `scripts/select_submission.py`, `scripts/verify_project.py`, and `tests/test_current_run_integrity.py`. Per `AGENTS.md`, `PR #100` must not be merged as a promoted submission.
6. **Interior-sentinel cliff root-cause diagnosis on `PR #102` (`095c9f0`, closed negative lane `G79-CJX`, `IR-79-191`):** Diagnosed why `G79-CJX` Exp 1–2 scored below random (`0.0404–0.0473`): `src/gems79/cjx.py` left the `3,061` in-footprint `-3.4028235e+38` sentinels unmasked inside `footprint`, clipping them to `-20.0` IQR cliffs and concentrating `29.73%` (`11,193 / 37,654`) of the top `cjx_v1_edge` pixels into the `0.5925%` 6-px sentinel halo (`50.2×` area enrichment). Closed-lane lifecycle guards from `PR #103` (`IR-79-181`) are preserved and all frozen `PR #102` receipts (`run_card_cjx.json`, `evidence/cjx/*`, `artifacts/cjx/*`) remain byte-identical.

### Pass 3 — End-to-End Requirement & Integrity Re-Check
- Rebuilt static Pages via `scripts/build_site.py`, verified `scripts/check_site.py` (`8` pages, `0` external assets, exact `IR-79-*` parity), `scripts/verify_project.py` (`all_checks_passed: true`), `scripts/submission_status.py` (`exit 2`), `scripts/select_submission.py` (`exit 2`), `node --test tools/browser-qa/download-check.test.cjs` (`12` passed), full `pytest -q` suite, `unittest` (`test_validate_submission.py`), and Playwright Chromium `scripts/browser_review.cjs` (`24 / 24` rendered cases passed).
- Confirmed zero `/home/user/` paths across `evidence/review_87f53313/*.json`, strict duplicate-key/NaN-free JSON across the entire repository, intact `<details>` original prompt at the end of `README.md`, and byte-identical canonical `G79-THVC` and closed-lane `G79-CJX` artifacts.

---

## 6. Verified Official Sources (Manual Review Links)

| Source | URL / DOI | Verified Takeaway |
|---|---|---|
| DrivenData Problem & Metric | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Fault prediction target; `DW-Tversky` ($\alpha=0.2, \beta=0.8, R=300\text{ m}$); `EPSG:32611`, `100 m`, `float32` in `[0, 1]`, outside bounds `null or nan`; `gems_tc_tmi.png` confirms `TC` = radiometric total counts/sec. |
| DrivenData Public Leaderboard | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | `PUBLIC-OBSERVATION` (`2026-10-22` UTC): `#1 xiaofanhu = 0.4413`, `#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3894`, `#21 = 0.3261`, `#22 = 0.3183`, `#50 sam35 = 0.2804`; neither `0.3195` nor `0.2778` in live top 50. |
| DOE / NLR Official Rules (Sept 2026) | https://docs.nlr.gov/docs/fy26osti/96647.pdf | $300k pool ($50k Phase 1 + $250k Phase 2); max 3 submissions/week (§3.2, §3.4); 1 final selected submission across both rounds without private-score knowledge (§3.5, §3.6.2); mandatory narrative AI disclosure (§3.2); US eligibility rules (§1.3). |
| USGS GeoDAWN Release | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (`doi:10.5066/P93LGLVQ`) | CC0 1.0; Area 1 (`200 m` lines @ `100–150 m` drape) vs Area 2 (`400 m` lines @ `150–200 m` drape, `90°` E–W flight azimuth); radiometrics + magnetics processing. |
| DOE GDR `1391` (INGENIOUS) | https://gdr.openei.org/submissions/1391 (`doi:10.15121/1881483`) | CC BY 4.0; documents independent (`ieq`) & dependent (`deq`) earthquake density models, `2–200 km` MT conductance (`doi:10.5066/P9TWT2LU`), heat flow (`doi:10.5066/P9BZPVUC`), probes, paleogeothermal, and geochemistry. |
| GBCGE INGENIOUS Project | https://gbcge.org/current-projects/ingenious/ | DOE GTO award `DE-EE0009254`; lists regional geophysical (`10.5066/P9Z6SA1Z`), strain-seismicity (`10.1785/0220220153`), MT (`10.5066/P9TWT2LU`), and heat-flow (`10.5066/P9BZPVUC`) primary publications. |
| EPSG:32611 Specification | https://epsg.io/32611 | WGS 84 / UTM zone 11N (`120°W–114°W`), metric Cartesian `(E, N)`, central meridian `-117°`, scale factor `0.9996`, false easting `500,000 m`. |
| GEMSDOE32 Public Site | https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html | Confirms `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`c55bafc4…`) is self-labelled `UNSCORED` with `0.2747` explicitly called a model projection, not an organizer score. |

---

## 7. Ordered Remaining Work & Explicit Limitations

### Ordered Next Steps (Requires Owner Action First)
1. **Prospective novelty-gate owner decision:** Ratify in writing how the 3-px duplicate rule treats saturating continuous surfaces (`Tier 1`), tie-inclusive plateaus (`Tier 2`), and dense periodic lattices (`Tier 3`, `13GEMSDOE r13-lattice-s5`), while keeping genuine sparse submission collisions (such as `GEMSDOE25` `0.7290 > 0.70`) strictly enforced.
2. **Resolve outside-footprint fill contract (`0.0` vs `NaN`, `IR-79-69`):** Confirm whether future promoted exports should emit `NaN` outside the `5,167,373`-cell footprint matching `sample_submission.tif` and `page/967` prose, while masking all per-band `-3.4028235e+38` sentinels (including Band 6's `3,073` interior sentinels).
3. **Assign one session method lane (recommended: `G79-SWARM` in [`research/hypotheses_87f53313.md`](../research/hypotheses_87f53313.md)):** Preregister before running, clear single-feature leakage canaries (`AUC <= 0.90`) on both seeds, pass pre-placement surface and final-dot novelty gates, beat canonical `G79-THVC` (`0.1905 / 0.1944`) on `gems57-pooled-hide-v2`, and submit to `scripts/select_submission.py` only if every gate passes and the signed-in DrivenData account confirms an available weekly slot.

### Explicit Limitations
- **No new scientific score or candidate raster:** All `HOLDOUT-DTI` figures reported here are read-only reconciliations of frozen receipts; `0` new models were trained.
- **Offline holdout $\ne$ organizer test truth:** Quadrant-blocked catalogue hide-and-recover evaluates recovery of withheld USGS/INGENIOUS traces, not Phase 1/2 expert-added blind faults.
- **Owner-mirrored inputs $\ne$ organizer authentication:** Checksum verification against `registry/data_manifest.json` proves byte reproducibility across sessions, not direct authenticated download from DrivenData's login-walled data portal.
- **Account & eligibility blindness:** Remaining weekly submission slots (`<= 3/week`), participant US eligibility (§1.3), narrative AI-use disclosure attachment (§3.2), and portal submission-page receipts cannot be observed or certified from this sandbox.
