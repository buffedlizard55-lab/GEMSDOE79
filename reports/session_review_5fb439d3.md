# Session review — `arena/5fb439d3-gemsdoe79` (2026-10-22)

Three-pass review (implement → defect hunt → requirements re-check). No new
experiment, no new raster, no slot spent (`submission_slots_used = 0`).
Canonical artifact unchanged: `G79-THVC`, SHA-256
`d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`.

## Decision (machine-readable, no human inspector)

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**
(`scripts/submission_status.py` exit `2`; blockers:
`literal_novelty_not_cleared`, `negative_scientific_verdict`,
`separate_selector_has_not_approved_a_slot`,
`separate_selector_receipt_missing_or_unbound`,
`explicit_submission_approval_absent`.)

- File: `archive/g79_thvc_33e1f8ec/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`
  (137,299 B) + single-TIFF ZIP (SHA-256 `dfee2552d9ba94bbb778f6da8e35b42ea7e5c55ff580dc5e9f9c809964b788f9`).
- Unique name (55/140 chars): `g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT`
- Note (98/140 chars): `GEMSDOE79 G79-THVC: 2m-probe+sinter+geophys+scarp 2-stage ensemble + Charnes-Cooper DTI (35093 px)`

## Pass 1 — verify the artifact line by line

Reopened bytes with rasterio: single band `float32`, `EPSG:32611`,
`3730 × 3292`, transform `[100, 0, 243350, 0, -100, 4508550]`,
values strictly `{0.0, 1.0}`, `min=0.0 max=1.0`, 0 NaN, 0 Inf,
35,093 positives, 0 on mapped catalogue. `validate_submission.py` PASS,
`verify_project.py` PASS, `check_site.py` PASS (7 pages, 146 links),
355 tests passed.

**DrivenData error "Predicted values must be in range [0, 1]":** this
`-zeros` file cannot trigger it locally (no NaN/Inf, all values in [0,1]).
The error is consistent with uploading a `-nan` variant (NaN outside the
footprint). Upload only the `-zeros` TIF or its ZIP; never a `-nan` file.

## Why H33 scored 0.2778, and can we beat it?

Evidence classes: `0.2778` = UNVERIFIED HISTORICAL REPORT (no organizer
receipt); `0.4413` = public leaderboard observation (2026-10-22); no
GEMSDOE79 raster has an ORGANIZER-CONFIRMED score.

Byte forensics (`evidence/h33_forensics.json`): H33 (37,654 px) = D2.8
(44,090 px) minus the 6,436 dots within 200 m of `existing_faults.tif`.
DTI (`alpha=0.2, beta=0.8`, 300 m triangular kernel) takes `max` for TP but
`sum` for FP, so sparse binary dots beat dense probability maps, and the
200 m prune removes masked-fault flank echoes. G79-THVC nearly doubles the
fold-fair H33 control on hide-and-recover holdout — HOLDOUT-DTI
(`gems57-pooled-hide-v2`) seed 20: 0.1905 [0.1741, 0.2069] (n=11,321) vs
0.0961; seed 30: 0.1944 [0.1774, 0.2126] (n=11,342) vs 0.0989. That is a
holdout proxy, **not** a leaderboard score; beating 0.2778/0.4413 on the
private test set is unproven until an organizer receipt exists.

## Ranked untried hypotheses (detail: `research/hypotheses_post_thvc_backlog.md`)

| Rank | Hypothesis | Layers / signature | Catches uncatalogued faults because | Blocker before validation |
|---|---|---|---|---|
| 1 | H80-MT-PHASE | GDR-1391 MT resistivity slices + gravity step-normal alignment | Blind sub-clay-cap conduits, no scarp needed | MT slices not in local cache; free official source: https://gdr.openei.org/submissions/1391 (DOI 10.15121/1881483) — must be downloaded on an unrestricted machine first |
| 2 | H80-DRAPE-DECONV | GeoDAWN RTP magnetics + drape/line-spacing deconvolution | Recovers Area-2 (400 m line) sub-fan offsets | Needs GeoDAWN drape metadata (USGS doi:10.5066/P93LGLVQ) |
| 3 | H80-RADIO-KD | K/eTh lithology-normalised residual | Adularia/illite along magnetite-destroyed faults | Uses cached radiometrics; lowest cost |
| 4 | H80-SLIP-DEFICIT | dem_100m + range-front sinuosity/relief conservation | Piedmont step-outs across mapped gaps | DEM-only; moderate cost |
| 5 | H80-COULOMB-CFS | Okada ΔCFS from fold-visible faults only | Stress shadows veto flank FPs | Needs preregistered lane + owner D-3 ruling |

Per protocol: no slot is spent on any of these until it beats HOLDOUT-DTI
0.1905/0.1944 on both seeds with canaries ≤ 0.90 and uniqueness cleared.
Top candidate (MT) is **not yet validatable** — its data are not cached here.

## Pass 2 — defects found and fixed

- **IR-79-143 (new):** README + scientific report stated name length
  `43/140`; actual `len()` = 55. Fixed to `55/140` in both sources and
  rebuilt the site. Note length 98/140 verified correct.
- No raster, card, gate, or verdict changed. `DO-NOT-SUBMIT` filename
  warning still matches `verdict: negative`.

## Pass 3 — requirements re-check

Unique TIF ✓ (sparse overlap max 0.6844 ≤ 0.70 across 718 ≤50k-dot maps;
0.3427 vs H33) · [0,1] validator ✓ · obvious download/submit banner on
home + executive summary (`docs/executive-summary.html`) ✓ · name+note
≤140 ✓ · every number labelled HOLDOUT-DTI or historical report ✓ ·
run card `run_card.json` unchanged ✓.

## Limitations / next work (do not auto-spend a slot)

1. Protocol-owner ruling on dense/space-filling registry priors
   (even oracle truth overlaps 0.8682–1.0000 > 0.70) — blocks `promote`.
2. Separate selector (`scripts/select_submission.py`) approval bound to
   this SHA; currently refuses non-NHR/FFAS lanes.
3. Download GDR-1391 MT slices + GeoDAWN drape metadata on an unrestricted
   machine, cache under `data/`, then preregister H80-MT-PHASE.
4. DrivenData login, weekly-slot availability, eligibility, and any
   organizer receipt remain account-side and unverifiable here.
