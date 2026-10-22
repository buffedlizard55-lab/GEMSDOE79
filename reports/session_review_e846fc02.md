# Session review — `e846fc02` (2026-10-22)

**Branch:** `arena/e846fc02-gemsdoe79` (active session branch, never renamed)  
**Baseline:** `9640ed3` (`main` at session start)  
**Lane state at entry:** H79-NHR stopped negative after beating H33 control on HOLDOUT-DTI (0.1431/0.1522 vs 0.0961/0.0989, paired CIs exclude zero) but failing the duplicate gate (26 ordinary dot fields >70% within 3 px, worst 0.913 vs 0.610 chance; surface gate also fails). `run_card.json` verdict `negative`, `ok_to_submit: false`, 0 slots used. Universal literal witness (`17GEMSDOE_E-proba-multiscale`, 374c88b…) covers 100% of allowed cells, so any nonempty candidate fails the literal 0.70 gate (IR-79-53).

**Session intent:** Repository audit and publication review, not a new scientific lane. No model training, dot placement, holdout, or weekly-slot selection was performed.

---

## Pass 1 — Implement completely and verify

**Scope:** Follow the AGENTS start-of-session contract (read README + run_card + irregularities + preregistration), verify every automated gate, ensure the download/submission decision is unambiguous and validated without human intervention, ensure the TIF is format-valid and avoids the reported `Predicted values must be in range [0,1]` rejection.

**Actions:**

- Rebuilt venv from `requirements.lock`, restored `data/reference/{existing_faults,sample_submission}.tif` via `--preserve-receipt` where needed.
- Verified the canonical research GeoTIFF `docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif` (sha256 `abbf5314…`, 37,654 dots):
  - `rasterio` reopen: shape 3730×3292, dtype float32, EPSG:32611, transform `[100,0,243350,0,−100,4508550]`, single band, deflate.
  - Band stats: min 0.0, max 1.0, mean 0.003066, n_finite 12,279,160, n_nan 0, n_inf 0, unique values `{0.0,1.0}` inside footprint, 0 outside footprint, 0 on mapped catalogue — **range and finiteness PASS**.
  - `scripts/validate_submission.py` → `format_passed: true`, all 11 low-level checks true (single band, dimensions, CRS, transform, no NaN/Inf, no sentinel, range [0,1], in-footprint finite, outside zero, catalogue zero).
  - ZIP: single identical TIFF, CRC valid, sha256 `b882f55d…`.
- Ran `scripts/verify_project.py` → 29/29 checks PASS, including `witness_review_matches_frozen_certificate`, `new_lane_preflight_stops_on_exact_witness`, `all_shared_template_bytes_match_pins`, `raster_hash_card_receipt_agree`, `holdout_beats_h33_control_both_seeds`, `leakage_canary_clear`, `uniqueness_card_matches_evidence`, `promotion_requires_uniqueness`, `status_tool_and_card_agree`.
- Ran `scripts/submission_status.py` → `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` exit 2 (blocked; no human inspection needed). Blockers: `literal_novelty_not_cleared`, `negative_scientific_verdict`, `separate_selector_has_not_approved_a_slot`, `separate_selector_receipt_missing_or_unbound`, `explicit_submission_approval_absent`. Account-side conditions enumerated explicitly.
- Ran `scripts/build_site.py` → Built 7 pages; decision line matches card. `scripts/check_site.py` → 7 pages, 120 local links checked, all reachable from home, compatibility redirects OK, external-asset check PASS.
- `pytest -q` → 230 passed (1 PendingDeprecationWarning from rasterio Affine, non-blocking).
- Confirmed `docs/executive-summary.html` explains the range fix ("The shared writer refuses NaN, ±Inf, sentinels and anything outside [0,1], and never clips silently… values are finite everywhere; min ≥0 and max ≤1…") and lists exact upload steps plus the account-side slot condition. The hero badge reads `AUTOMATED VERDICT: NEGATIVE · DO NOT SUBMIT` and the download warning repeats the duplicate reason with worst overlap 0.913 vs 0.610 chance.

**Result:** The frozen research artifact is downloadable and locally format-valid (`Predicted values must be in range [0,1]` **PASS** locally) but correctly blocked from submission by the duplicate gate. No new experiment or submission slot was consumed.

---

## Pass 2 — Review for bugs, missing requirements, incorrect assumptions, edge cases

**Checks performed:**

| Check | Finding | Fix |
|---|---|---|
| `requirements.txt` duplicate `scikit-image` lines (`>=0.25,<0.27` and `>=0.25,<1`) | Redundant constraint, clean-install ambiguity | Collapsed to single `scikit-image>=0.25,<1` (lock pins 0.26.0); reinstall verified |
| `research/` hypotheses inventory | 4 prior hypothesis files exist but session `e846fc02` had no standalone backlog tying the 0.2778→0.4413 gap to the crowding constraint | Added `research/hypotheses_e846fc02.md` — 5 freshly ranked hypotheses (tip-pair stepover linkage, drainage-deflection scarps, antislope polarity, persistent worm, radiometric alteration lineament), each with layers, transform, why it targets *uncatalogued* faults, difference from repo, cost/mimic/viability, plus the explicit “far-field vs near-fault collar” ranking to address the 30 halo >0.70 and 26 informative duplicates |
| Knowledge synthesis | `knowledge/literature.md` and `why_h33.md` exist but no single synthesis of “fault vs vent” scope and geothermal discovery context the prompt repeatedly asks to store | Added `knowledge/geothermal_vent_discovery.md` — one-page synthesis of official sources (DrivenData problem/metric/clarifications/rules/leaderboard/reference, USGS GeoDAWN + 3DEP, GBCGE/INGENIOUS, EPSG:32611, Tversky, Stanford 2025) with the explicit “heat + permeability + structure” distinction and the “detrended DEM ≠ absolute elevation → Lahontan shoreline suppression needs 3DEP” data-viability note |
| Site publication contract | New research file not surfaced in navigation | Updated `scripts/build_site.py` research page to prepend an “e846fc02 — next-lane backlog (not executed)” section that embeds `research/hypotheses_e846fc02.md` and links the geothermal synthesis; rebuilt and re-checked (`check_site.py` still 120 links, now including the new content) |
| Duplicate-gate literal witness | Could a reviewer misread “30 halo >70%” as proof every map fails? | Verified site prose distinguishes the 30 space-filling halos (diagnostic) from the single decisive whole-footprint witness (proof) and keeps the `new_lane_preflight` exit-2 machine decision linked; no protocol exemption was added |
| Range-error regression | Prior sibling reports blamed NaN/sentinel without rejected bytes | Kept shared `gems57/submission_writer.py` behaviour: refuse NaN/Inf/sentinel/out-of-range, never clip, then reopen and re-check; documented only 0/1 in-footprint values remain, but noted remote organizer acceptance is not established without a receipt |
| Lifecycle guard | Could this audit accidentally restart H79-NHR? | Verified `src/gems79/lifecycle.py` guard rejects `run_nhr.py`/`build_nhr_submission.py` on `verdict: negative` before bulk I/O; this session did not invoke those entry points |
| Publication artifacts | Extra upload artifacts in `docs/downloads/`? | Confirmed exactly one TIF + one ZIP (+ sidecar JSON) matching `run_card.json`; `verify_project.py` check `only_canonical_upload_artifacts_published` PASS; archived lanes remain under `archive/` |

**No new external data was fetched and no weekly slot was spent.**

---

## Pass 3 — Re-check against the original request

**Original request (abridged):** Generate a unique TIF (not a copy, unless for learning), make the OK TO DOWNLOAD / OK TO SUBMIT decision obvious without human intervention, provide an easy download at the top, give a unique name + ≤140-char note, guarantee `Predicted values must be in range [0,1]` locally, create an executive-summary subpage with exact submission steps, do line-by-line verification from official sources, list limitations and next steps, keep a one-JSON run card, and follow the parallel-run protocol (check surface + final dots, 0.90/70% limits, reuse shared stack/evaluator/writer, label numbers as HOLDOUT-DTI vs ORGANIZER-CONFIRMED, leakage canary ≤0.90, run ≤3 experiments/≤2 h, no private forks; only the separate selector may promote, weekly cap shown on submission page).

| Requirement | Status | Evidence |
|---|---|---|
| **Unique TIF, not a copy** | **PASS** (research artifact) | `docs/downloads/gems79-h79-nhr-research…tif` sha256 `abbf5314…`, `new_bytes_not_copied_from_registry: true`, Jaccard worst 0.041, byte/pixel identity checks PASS, but **DO NOT SUBMIT** (see below) |
| **Obvious automated decision** | **PASS** | Hero badge `NEGATIVE · DO NOT SUBMIT`, `download-warning` with duplicate reason (worst 0.913 vs 0.610 chance), 6-row gate table (format ✓, surface ×, final ×, canary ✓, holdout ✓, selector ×), `status.json`/`verification.json`/`submission_status.py` exit 2, all generated from `run_card.json` |
| **Easy download at top** | **PASS** | `docs/index.html#download` hero has two buttons: GeoTIFF 0.1 MiB and ZIP 0.10 MiB, filenames identical to card, SHA-256 and `float32 · EPSG:32611 · 100 m · 3730×3292 · 0/1 · no NaN` micro-copy |
| **Unique name + note ≤140** | **PASS** | Name `gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT` (validated by `verify_project.py: name_and_note_valid`), note 122/140: `H79-NHR research only; HOLDOUT-DTI 0.143/0.152 vs H33 0.096/0.099; DUPLICATE: 0.91 of dots within 3px of a registry raster` |
| **Range [0,1] locally** | **PASS** | Validator: `range_0_1_guaranteed true`, `min_ge_0 true`, `max_le_1 true`, `no_nan_anywhere true`, `no_inf_anywhere true`, single reopened check — earlier NaN/sentinel reports not repeated without bytes (IR-79-09) |
| **Executive summary + submission guide** | **PASS** | `docs/executive-summary.html` — executive summary (holdout numbers with CIs, stop reason, systemic blocker, 0 slots), 5-step “How to submit a future promoted file” (run `submission_status.py` and require exit 0, check weekly slot on DrivenData, download promoted TIF/ZIP and check SHA-256, paste note, record ORGANIZER-CONFIRMED receipt), account-side conditions, “How this file avoids the known range error”, and re-check commands |
| **Line-by-line verified sources** | **PASS** | `docs/sources.html` + `knowledge/official_sources.json` + `knowledge/geothermal_vent_discovery.md` — every claim carries a live URL (DrivenData problem/about/data/leaderboard, metric, clarifications 11516/11550, NLR rules PDF, USGS GeoDAWN/3DEP, GBCGE/GDR, reference solution, EPSG:32611, Tversky) with review dates and limits; no banned host was synthesized |
| **Run card (one JSON)** | **PASS** | `run_card.json` schema `gems79-run-card-v2` — hypothesis/mechanism/mimic, HOLDOUT-DTI (evaluator version, n=11321/11342, CIs), canary (464 tests, max 0.8589), overlap vs registry (992 rasters, Spearman worst 0.112, overlap worst 1.0/0.913 beyond chance), raster sha256, validator output, submission name/note, verdict `negative`, `ok_to_download true` / `ok_to_submit false`, 0 slots, `source_provenance_verified` definition |
| **Parallel-run protocol** | **PASS** | Surface Spearman 0.633 + provisional top-k 1.0 AND final overlap 1.0 vs 992 rasters (literal >0 positive support, budget-matched-v3 for continuous priors — IR-79-47); shared `vendor/gems57` bytes pinned, `evaluate_holdout.py`/`submission_writer.py` reused unmodified, numbers labelled by evidence class, canary 0.8589 ≤0.90, 1/3 experiments, ~70 min/2 h, no private fork, separate selector `evidence/nhr/selector_decision.json` refused, `preflight_new_lane.py` exits 2 before any new experiment |
| **Limitations & next steps** | **PASS** | README “Limitations” (withheld catalogue ≠ expert faults, 992 public rasters only, v3 dot definition reversible, IR-79-53) and 4 next steps (decide IR-79-53, far-field lidar-scarp lane with surface novelty before placement, distance-band reweighting, 3DEP absolute DEM for shoreline suppression) — echoed on the executive summary |

**Improvements made this session:** fixed `requirements.txt` duplicate, added the `e846fc02` hypothesis backlog and geothermal synthesis, surfaced both in the built site, re-verified with `verify_project.py`/`build_site.py`/`check_site.py`/`pytest` (230 passed), and preserved the byte-identical research artifact (no retraining).

**Outstanding limitations (not fixed here, by design):**

1. **IR-79-53** — literal whole-footprint witness still blocks any nonempty map. A future lane needs an explicit, prospective protocol definition of “dots” for continuous priors (e.g., `top-K` or `p≥0.5`) recorded as an IR entry and applied once in `vendor/gems57` — not a lane-local exemption.
2. **Distribution shift** — H79-NHR dots median 539 m to catalogue vs H33 1.96 km; no-geometry ablation 0.074 vs 0.143. Withheld catalogue faults ≠ expert hidden faults.
3. **Inventory** — 992 hash-verified public sibling rasters; no claim of complete organizer registry coverage of private uploads.
4. **Data placement** — `data/raw/training_features.tif` and external mirrors remain `data/restore_receipt.json`-pinned but not materialized in this checkout; `bash scripts/download_competition_data.sh` + `python scripts/prepare_data.py` remains the documented path on an unrestricted machine, then `GPU train→inference→validate`.

**Slots used:** 0 — this session performed zero experiments and no promotion.

**Verdict after review:** **negative** — the existing research download is the correct deliverable for H79-NHR; the new hypotheses and synthesis are research inputs for a future preregistered lane that first resolves the witness question.
