# README status section on main at 9417f4e (G79-STEPCO), preserved verbatim

> Relative links rebased with `../` so they resolve from `reports/`, and archived download links point at their archive location. The text is otherwise verbatim.

# GEMSDOE79 — auditable fault-discovery research

## Download and submission decision — start here

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. Automated verdict: `negative`.**

### Current lane G79-STEPCO — 2026-10-22 (session `220dabc8`)

A **newly generated, unique-to-this-session GeoTIFF** is the canonical download.
It was computed in this session from the hash-pinned competition feature stack
by lane **G79-STEPCO** (multi-field step-dipole transforms + one fixed
HistGradientBoosting model, refit per hide-and-recover draw; 37,654 binary dots
at 3 px spacing; catalogue excluded beyond 2 px). It is **not** a copy or
re-emission of any prior submission: byte-distinct from all 992 pinned registry
files, final surface rank-correlation at most ρ = 0.518 and final-dot ρ at most
0.086 against 986 grid-comparable registry rasters.

[**Download G79-STEPCO S1 GeoTIFF — DO NOT SUBMIT**](../archive/g79_stepco_s1/downloads/gems79-stepco-s1-37654dots-20261022T020857Z-7e676fe2-DO-NOT-SUBMIT.tif) · [Single-TIFF ZIP](../archive/g79_stepco_s1/downloads/gems79-stepco-s1-37654dots-20261022T020857Z-7e676fe2-DO-NOT-SUBMIT.zip) · [Machine run card](../run_card.json) · [Executive summary / submission guide](../docs/executive-summary.html) · [Three-pass session review](../reports/session_review_220dabc8.md)

- **Name:** `gems79-stepco-s1-37654dots-20261022T020857Z-7e676fe2-DO-NOT-SUBMIT`
- **Note (104/140 chars):** `GEMSDOE79 STEPCO s1: multi-field step-dipole HGB, 37654 dots s3, cat>2px; holdout-gated 20261022T020857Z`
- **Raster SHA-256:** `6ae07fbf14dfe2d169aa9f926c54ee5e74215d7c569ffcc325cb91da297e510a`
- **Format (re-read from written bytes):** single-band float32, EPSG:32611,
  3730 × 3292, 100 m, exact sample transform, every value finite and in [0,1],
  no NaN anywhere, `nodata=None`, 37,654 positive pixels, 0 on the catalogue.
  This is the contract that prevents the reported
  "Predicted values must be in range [0, 1]" portal rejection (caused in this
  family by float32 nodata sentinels / out-of-range values); local format PASS
  is **not** organizer acceptance.

### Why the automated verdict is still DO NOT SUBMIT

Two preregistered, independent gates failed. No human inspection is involved
(`.venv/bin/python scripts/submission_status.py` reproduces the decision and
exits 2):

1. **Holdout gate.** HOLDOUT-DTI (shared evaluator `gems57-pooled-hide-v2`,
   pooled α=0.2/β=0.8, 300 m triangular kernel): S1 candidate **0.0946
   [0.0778, 0.1110]** (seed 20, n=11,321 withheld pixels) and **0.0948
   [0.0782, 0.1115]** (seed 30, n=11,342). It beats uniform placement
   (+0.046/+0.045, 95% CIs above 0) and its single-field ablation, and clears
   all 464 leakage canaries (max symmetric AUC 0.684 ≤ 0.90) — but it only
   **ties** the fold-fair H33-lineage incumbent (0.0961/0.0989; paired
   −0.0015 [−0.0153,+0.0110] and −0.0041 [−0.0191,+0.0111]). The preregistered
   rule required beating the incumbent with CI above 0 on both seeds.
   Experiment S2-COVER (kernel-cover placement on the identical surface)
   tied as well (0.0935/0.0961). A tie is not an improvement claim, and no
   leaderboard score is projected from these numbers.
2. **Uniqueness certification.** Under the session's documented
   [amendment D-1](../reports/protocol_amendment_D1_20261022.md) the candidate is
   rank-unique everywhere and its worst overlap against 748 comparable sparse
   registry emissions is 0.647 < 0.70 (0.414 against H33 itself) — but the
   shared tool's like-for-like dot-field reading still fires because the
   registry contains space-filling priors (a 206,895-dot lattice and dot
   fields up to ~1M dots) whose 3 px halos cover the study area. The literal
   reading (overlap 1.0 vs whole-footprint continuous priors) is reported,
   not hidden. All 992 indexed rasters are accounted for: 986 grid-comparable
   vendor comparisons + 6 grid-invalid files documented in
   `evidence/stepco/uniqueness_supplementary.json`.

**Does this beat 0.2778?** Unknown, and this repo will not guess. The 0.2778
figure has no submission-page receipt tying it to the H33 file hash; the
GEMSDOE32 site itself labels that file **UNSCORED** (its 0.2747 is labelled a
projection). What H33 measurably is: the D2.8 dot set (44,090) with every dot
within 200 m of the catalogue deleted (→37,654, zero disagreement,
`knowledge/why_h33.md`). Its family's advantage is emission efficiency under
the max-cover metric, not new geology. STEPCO's independent ranking ties that
lineage's dots on clean hide-and-recover; whether it would score above or
below them against the organizer's hidden expert faults cannot be known
without spending a submission slot, which the failed gates forbid. Today the
official public leaderboard lists 0.4413 at rank 1 (fetched 2026-10-22);
0.3195 / 0.4413 confusion in older briefs is an unverified-report artefact.

### Prior lane G79-FABRIC-OFFSET E1 (closed, archived unchanged)

E1 (magnetic fabric-offset) stopped in 2026-10-21 before placement under the
literal overlap rule; a post-stop diagnostic then measured HOLDOUT-DTI
0.0474/0.0466 — below uniform. Its run card and GeoTIFF are preserved
byte-identical under [`archive/g79_fabric_offset_e1/`](../archive/g79_fabric_offset_e1/README.md)
(raster SHA-256 `8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca`);
its root-level evidence (universal-overlap certificate, witness re-checks,
concurrent-lane audits) is unchanged. STEPCO S2-COVER is likewise archived
under [`archive/g79_stepco_s2/`](../archive/g79_stepco_s2/README.md). The
archived concurrent approvals H79-MCT / H79-CSPT remain **not adopted**.

## Score discipline and sources

New scores are labelled **HOLDOUT-DTI** (evaluator version, withheld-positive
count, 95% CI) or **ORGANIZER-CONFIRMED** (submission-page receipt only; this
project has none). All 98 sibling filename→score pairs in
`registry/score_ledger.csv` are UNVERIFIED HISTORICAL REPORTS. Official
sources are claim-checked in [`knowledge/official_sources.json`](../knowledge/official_sources.json):
[DrivenData problem + metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ·
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) ·
[DOE rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) ·
[USGS GeoDAWN (DOI 10.5066/P93LGLVQ)](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) ·
[official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) ·
[GDR 1391 INGENIOUS](https://gdr.openei.org/submissions/1391).

## Reproduce and verify (offline, no new experiment)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/restore_data.py --ids training_features,existing_faults,sample_submission,ext_lidar_scarp_features_u8,ext_lidar_scarp_features_json,ext_geodawn_rad_u8,ext_geodawn_extensions_u8 --preserve-receipt
.venv/bin/python scripts/submission_status.py        # exit 2 = automated DO NOT SUBMIT
.venv/bin/python scripts/verify_project.py           # byte/format/evidence contract
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/build_site.py && .venv/bin/python scripts/check_site.py
# Full STEPCO rerun (features -> canaries -> holdout -> uniqueness -> writer):
.venv/bin/python scripts/run_stepco_experiment.py    # S1; needs registry clones in .cache/clones
```

Shared template code in `vendor/gems57/` is byte-pinned and unmodified
(`registry/template_pin.json`, commit `b99591eede63c6d45c8a896255b8cd34824fa00b`).

## Website

GitHub Pages serves `docs/`: the landing page leads with the download above
and its automated decision; `docs/executive-summary.html` is the step-by-step
submission guide (including what to check before ever spending a weekly
slot); `docs/status.json` is the machine-readable verdict. Rebuild with
`scripts/build_site.py`; `scripts/check_site.py` verifies every link offline.

## Limitations and next steps (honest list)

1. **Holdout truth ≠ hidden truth.** Hide-and-recover rewards recovering
   mapped faults; the organizer scores expert faults absent from the
   catalogue. STEPCO's tie on the former establishes nothing about the latter.
2. **Uniqueness needs an owner decision (D-1).** Space-filling lattice/dense
   priors make any literal dot-overlap gate vacuous; amendment D-1 documents
   the like-for-like reading but cannot certify uniqueness against tilings.
   A registry policy that distinguishes *emissions* from *tilings/surfaces*
   by emitted-mass class is the clean fix and belongs to the protocol owner.
3. **Ranking headroom is in features this sandbox could not use at full
   strength:** 1 m DEM tiles beyond the precomputed lidar channels, GPU
   segmentation ensembles (the likely 0.44-class approach), and calibrated
   per-regime models. Each needs its own preregistration and the same gates.
4. **No DrivenData authentication** in this environment: uploads, weekly-slot
   counts and score receipts cannot be obtained or faked here. Data bytes are
   mirror-hash-consistent, not organizer-authenticated.
5. Two of three session experiments were used; the third was deliberately not
   spent on holdout-driven search (see session review).

**Core values.** Maximize P(Win) — every gate above exists so a scarce weekly
slot is never spent on an unproven file. Own the Outcome — both STEPCO
experiments are reported with their failures intact.

### Prior repository review (same-day, main) — 2026-10-22 (session `79e8e13e`)

- **Conflict markers, broken links, and false hash repaired (`IR-79-44`..`IR-79-45`):**
  Resolved Git merge conflict markers left on `main` by PR #20 (`1ece8d9`) in `AGENTS.md`
  and `evidence/browser_review.json` (`JSONDecodeError`), corrected stale `archive/h79_cspt_464d591/`
  paths to [`archive/h79_cspt_3d386a3/`](../archive/h79_cspt_3d386a3/README.md) and the `H79-CSPT`
  GeoTIFF SHA-256 prefix from `d55570bf…` to `388d8678…`, deduplicated `IR-79-*` IDs (`IR-79-01`..`IR-79-39`),
  fixed relative links in `knowledge/prior_work/README.md` and `docs/*.md`, and hardened
  [`scripts/verify_project.py`](../scripts/verify_project.py) and [`scripts/build_site.py`](../scripts/build_site.py)
  against future conflict markers, invalid JSON, or broken links.
- **Zero-REST-quota Git Smart-HTTP recovery (`IR-79-46`):** Upgraded [`scripts/restore_data.py`](../scripts/restore_data.py)
  and [`scripts/restore_registry.py`](../scripts/restore_registry.py) with bare-Git Smart-HTTP blob fetching
  against `github.com` (bypassing GitHub REST `403` rate limits and blocked `raw.githubusercontent.com` redirects
  while verifying SHA-1 + SHA-256 + byte length). Restored all 13/13 raw/external inputs, reproduced all 10
  `.cache/g79/*.npy` features bit-for-bit, recovered exact GeoTIFF/ZIP hashes, and verified the universal witness
  ([`evidence/session_witness_79e8e13e.json`](../evidence/session_witness_79e8e13e.json)).
- **103-row score ledger & cross-family pixel lineage audit (`IR-79-39`):** Added the 5 newly reported scores
  (`GEMSDOE73`: `0.1917`, `GEMSDOE74`: `0.0669`, `GEMSDOE75`: `0.1627`, `GEMSDOE76`: `0.1555`, `GEMSDOE77`: `0.0964`)
  to [`registry/score_ledger.csv`](../registry/score_ledger.csv) (103 data rows, `UNVERIFIED HISTORICAL REPORT`) and
  measured actual GeoTIFF bytes across 16 scored landmarks and 5 post-snapshot siblings (`GEMSDOE78`, `GEMSDOE80`..`GEMSDOE83`)
  via [`scripts/analyze_family_lineage.py`](../scripts/analyze_family_lineage.py) →
  [`evidence/family_lineage_forensics.json`](../evidence/family_lineage_forensics.json) (see [`knowledge/why_h33.md`](../knowledge/why_h33.md)
  and [`reports/session_review_79e8e13e.md`](../reports/session_review_79e8e13e.md)). Every score `>= 0.2600` (`0.2600`..`0.2778`)
  derives from `19GEMSDOE` (`h19-5`, `121,131` px, `0.1922`) via `300 m` pin thinning (`D2.8`, `44,090` px, `0.2600`)
  and monotonic `0 < d_cat <= 200 m` halo pruning (`6,436 -> 3,894 -> 2,545 -> 2,353 -> 0` across `0.2600 -> 0.2778`);
  `GEMSDOE36` (`0.2750`) contains all `37,654` exact pixels of `H33`; `GEMSDOE70` (`0.2478`) and `GEMSDOE49` (`0.2376`)
  are the #1 and #2 genuinely non-duplicate models; and post-snapshot `GEMSDOE82` published a second dense continuous
  surface (`surface_h82.tif`, `4,862,825` positive cells), reinforcing **Decision D-1**.
- **Concurrent PRs #22 / #23 / #24 quarantine & byte-level fabrication catch (`IR-79-40`):** Quarantined concurrent merges
  `0ae2506` (`G79B-SCARP-DIPOLE-GEOAND`, holdout-negative) and `5d14587` (`H79-ML-STRAIN-RELAY`) under
  [`archive/concurrent_2026-10-22_5d14587/`](../archive/concurrent_2026-10-22_5d14587/README.md) with full SHA-256 `manifest.json`
  and audited all four archived concurrent lanes in [`evidence/concurrent_lanes_audit.json`](../evidence/concurrent_lanes_audit.json).
  Proved that PR #24 (`5d14587`) privately forked `vendor/gems57/uniqueness.py`, checked only `2 / 992` registry rasters while
  advertising `"OK TO SUBMIT: YES"`, and recorded copied `E1` overlap numbers (`0.1978` / `0.0119`) that contradict its own
  GeoTIFF bytes (`05038613…`, actual measured overlaps `0.2844` vs `H33` and `0.1620` vs `E-proba top-37,654`, `1.0000` literal).


