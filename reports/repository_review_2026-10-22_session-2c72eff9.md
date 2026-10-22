# Repository review — `arena/2c72eff9-gemsdoe79` — 2026-10-22

## Decision at a glance

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. No submission slot used; no upload attempted.**

The active checkout contains an already-generated, byte-distinct GeoTIFF research artifact, but its submission status is negative. A locally valid file is not equivalent to uniqueness clearance, scientific promotion, or organizer acceptance. The current hard-stop is reproducible: `scripts/preflight_new_lane.py --restore` returns exit 2 because the inherited literal 3-pixel overlap rule has a hash-verified registry witness covering every allowed cell. I did not create another prediction, alter the gate, select a slot, or rerun a stopped lane.

This review is confined to the active branch assigned by the session, `arena/2c72eff9-gemsdoe79`. The checkout began clean at `80550533` (`origin/main`); no branch change was made. The repository's own `AGENTS.md`, README, frozen run card, shared-template pins, and stop protocol control over historical lane names or stale branch labels in artifacts.

## The previous high result and what can honestly be concluded

The repository's `knowledge/why_h33.md` and `evidence/h33_forensics.json` report exact pixel lineage: the H33 raster is the earlier D2.8 binary dot set with the 6,436 dots within 200 m (2 pixels) of the known-fault catalogue removed, with no other pixel changes. That construction is consistent with the competition metric's asymmetric treatment of false positives and false negatives: spaced dots avoid paying linear false-positive mass along broad ridges, while pruning catalogue-adjacent echoes avoids penalties where the known-fault mask excludes exact catalogue pixels. This is a plausible mechanism, not proof of why an organizer score changed.

The H33 filename-to-`0.2778` pairing is not tied here to an artifact-linked submission receipt, so it remains an **UNVERIFIED HISTORICAL REPORT**, not ORGANIZER-CONFIRMED. The repository's dated source ledger recorded a public leaderboard snapshot of `0.4413` for first place on 2026-10-22; this review did not freshly access the DrivenData site and therefore makes no claim about today's leaderboard. Neither reported value predicts this repository's holdout or leaderboard outcome.

## Three-pass review

### Pass 1 — instructions, scientific state, artifacts, and sources

- Read `AGENTS.md`, the complete README including the preserved prompt, the canonical `run_card.json`, `reports/irregularities.md`, and the three preregistration files required by `AGENTS.md`.
- Inspected the registered G79-STEPCO hypotheses and the existing S1/S2 evidence under `research/hypotheses_g79stepco_20261022.md`, `registry/preregistration_g79stepco_20261022.json`, `registry/preregistration_g79stepco_s2_amendment_20261022.json`, and `evidence/stepco/`.
- Confirmed the working tree was clean before review. Set up the exact pinned environment in ignored `.venv`; no tracked dependencies or scientific data were changed.
- Reproduced the shared new-lane preflight decision: `start_new_lane=false`, `impossible_under_literal_gate`, exit code 2. Its precise scope is the literal support rule, not every possible future protocol interpretation.
- Recomputed the locally reported submission decision: `ok_to_download=true`, `ok_to_submit=false`, verdict `negative`, no human inspection needed for that automated decision, and blockers include literal novelty, the negative scientific verdict, no separate-selector approval/receipt, and absent explicit upload approval.

### Pass 2 — code, test, site, and result cross-check

- `.venv/bin/python -m pytest -q`: **355 tests passed**. These are software tests, not HOLDOUT-DTI.
- `.venv/bin/python scripts/verify_project.py`: all recorded integrity/consistency checks passed, including byte pins, run-card/evidence agreement, GeoTIFF/ZIP checks, status/card consistency, and stop enforcement.
- `.venv/bin/python scripts/check_site.py`: passed; 7 pages, 146 local links checked, all pages reachable from home, 2 compatibility redirects, 0 external assets, and `submit=false`.
- `.venv/bin/python scripts/submission_status.py`: expected fail-closed JSON and exit code 2; no acceptance or slot approval asserted.
- `git diff --check`: passed. Canonical G79-THVC TIFF digest independently matched the card: `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`.
- Ran no new canaries, holdout evaluation, dot placement, raster build, external-source download, or upload. This avoids spending the closed lane's experiment budget and does not present archived scores as fresh results.

### Pass 3 — requirements, edge cases, and next steps

- **Range-error requirement:** the canonical research TIFF is single-band float32, EPSG:32611, 3730 × 3292, has the reference grid transform, contains no NaN/Inf, and has values in `[0,1]` (specifically 0/1). This is local format/range validation only; it does not guarantee DrivenData acceptance.
- **Easy download and clear status:** the root README and executive-summary page expose the file and say **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**. This is the correct fail-closed label; do not rename or present it as submission-ready.
- **Unique-name/note requirement:** the canonical run card carries a distinct filename, submission name, and note under the 140-character limit. Name/note uniqueness does not waive the scientific or registry novelty gates.
- **Candidate-hypothesis requirement:** the repository already records five ranked G79-STEPCO hypotheses, layers, signatures, mimics, qualitative expected-value ranking, and implementation cost before its evaluation. The top candidate (multi-field step-dipole ranking) was tested in S1 and its preregistered single-change placement variant in S2. Both were negative versus the H33 fold-fair comparator; they are not evidence for a promotable new method. The lower-ranked alternatives were not separately evaluated and must not be relabelled “validated.”
- **No replacement lane:** proposing a fresh 3–5-item ranking and implementing its top item now would violate the explicitly single-lane parallel-run protocol and the universal preflight stop. The actionable work is an authorized prospective protocol resolution for the meaning of “dots” against continuous/full-coverage registry surfaces. Do not locally weaken the 0.70 threshold, exclude inconvenient rasters, jitter/cap the prediction, or change the shared tool without protocol-owner authorization.
- **External/account limitations:** the repo records that DrivenData account/data pages require authorized login and that current per-account remaining submissions, participant eligibility, selector approval, and organizer receipt are not visible here. I did not bypass authentication. Official-source facts and limits are maintained in `knowledge/official_sources.json` for manual review; prior source observations are dated and are not asserted as a fresh 2026-10-22 web check by this session.

## Existing STEPCO hypothesis and saved validation (not rerun in this review)

The one preregistered top hypothesis was that short, subtle piedmont/basin-margin faults exhibit co-located step responses in detrended elevation, gravity, basement depth, RTP magnetics, and conductivity. Its transforms were step dipoles plus gradient/Laplacian context, combined by a fixed HistGradientBoosting model fit only to visible faults in each buffered hide-and-recover draw. Named confounds included facies/paleochannel boundaries, alluvial-fan lobes, and airborne survey levelling seams.

All values below are **HOLDOUT-DTI** from `gems57-pooled-hide-v2`; each seed uses the indicated number of withheld positive pixels and paired 95% spatial-cluster bootstrap intervals. They are historical receipts in `evidence/stepco/`, not fresh measurements in this review:

| Existing experiment | Seed 20 | Seed 30 | Decision |
|---|---|---|---|
| S1: step-dipole HGB; 37,654 spaced dots | `0.0946` (95% CI `[0.0778, 0.1110]`, 11,321 withheld positives) | `0.0948` (95% CI `[0.0782, 0.1115]`, 11,342 withheld positives) | Negative: paired difference vs H33 was `-0.0015` (95% CI `[-0.0153, 0.0110]`) and `-0.0041` (95% CI `[-0.0191, 0.0111]`), respectively; neither clears the preregistered superiority gate. |
| S2-COVER: same surface, rank dots by shared 300 m expected credit | `0.0935` (95% CI `[0.0780, 0.1088]`, 11,321 withheld positives) | `0.0961` (95% CI `[0.0796, 0.1117]`, 11,342 withheld positives) | Negative: paired difference vs H33 was `-0.0025` (95% CI `[-0.0156, 0.0104]`) and `-0.0028` (95% CI `[-0.0158, 0.0110]`), respectively. |

S1's saved canaries cleared its threshold: maximum symmetric single-feature AUC was `0.6836` on seed 20 and `0.6607` on seed 30 (threshold `0.90`). This does not rescue a failed holdout gate. For the STEPCO surface, the saved maximum absolute rank correlation was `0.5177` (under `0.90`), but its final dot maps had literal 3-pixel forward overlap `1.0` against registry witnesses, above the `0.70` threshold. The source scan was incomplete (`989` checked of `992` indexed; `6` missing/invalid), so it is not a complete inventory-wide uniqueness clearance. A matched-budget auxiliary comparison is not permission to override the literal rule.

## Current artifact run card (this review; negative)

```json
{
  "hypothesis": "Repository audit only; no new geological hypothesis or raster emitted. Existing G79-STEPCO step-dipole candidate and S1/S2 evidence reviewed.",
  "mechanism": "No new model execution. Saved STEPCO model combined fixed multi-field step-dipole/gradient/Laplacian transforms; S2 changed placement ranking only to expected kernel credit.",
  "named_non_fault_process": "Unfaulted sedimentary facies pinch-out or paleochannel margin, alluvial-fan lobe boundary, or airborne survey levelling seam.",
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": "gems57-pooled-hide-v2",
    "withheld_positive_pixels_seed20": 11321,
    "seed20_s1": {"dti": 0.0946, "ci95": [0.0778, 0.1110]},
    "seed20_s2": {"dti": 0.0935, "ci95": [0.0780, 0.1088]},
    "withheld_positive_pixels_seed30": 11342,
    "seed30_s1": {"dti": 0.0948, "ci95": [0.0782, 0.1115]},
    "seed30_s2": {"dti": 0.0961, "ci95": [0.0796, 0.1117]},
    "scope": "Existing saved evidence reviewed, not rerun; no claim of organizer performance."
  },
  "correlation_overlap_vs_registry": {
    "scope": "STEPCO saved scan, 989/992 indexed; 6 missing/invalid.",
    "surface_max_abs_spearman": 0.5177,
    "final_dot_literal_3px_forward_overlap": 1.0,
    "overlap_limit": 0.70,
    "result": "duplicate under the unchanged literal gate"
  },
  "raster_sha256": "d50974d1f9148adf0e0a484052c97579af0c50e079d8afd6d6ac2cc22541497c",
  "validator_output": {
    "reviewed_archived_artifact": "archive/g79_stepco_s2/downloads/gems79-stepco-s2cover-37654dots-20261022T021024Z-7e676fe2-DO-NOT-SUBMIT.tif",
    "sha256": "d50974d1f9148adf0e0a484052c97579af0c50e079d8afd6d6ac2cc22541497c",
    "no_nan_inside_footprint": true,
    "values_in_0_1": true,
    "crs": "EPSG:32611",
    "shape": [3730, 3292],
    "transform_matches_sample_submission": true,
    "validation_class": "historical local validator receipt; archived negative, not organizer acceptance"
  },
  "submission_name": "gems79-stepco-s2cover-37654dots-20261022T021024Z-7e676fe2-DO-NOT-SUBMIT",
  "submission_note": "GEMSDOE79 STEPCO S2-COVER: step-dipole HGB + kernel-cover dots 37654 s3 cat>2px 20261022T021024Z",
  "verdict": "negative",
  "ok_to_download": true,
  "ok_to_submit": false,
  "submission_slots_used": 0
}
```

## Official/primary-source links and source boundary

- [DrivenData problem overview and score definition](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — official organizer page; prior repo record, not freshly accessed in this review.
- [DrivenData competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/) — official rules; account/slot state still requires authorized session.
- [DrivenData about/timeline page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/) — official organizer page.
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — source code and baseline; not evidence that a local candidate will win.
- [USGS GeoDAWN airborne survey release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — official survey metadata; not independent validation of local mirrored derivative bytes.
- [DOE INGENIOUS/GDR submission 1391](https://gdr.openei.org/submissions/1391) — official repository landing page; local data provenance/fitness limitations remain in the source ledger.
- [EPSG:32611 definition](https://epsg.io/32611) — projection metadata reference.

## Remaining work and limitations

1. Obtain prospective rule-owner clarification for continuous full-footprint surfaces under the literal 3-px dot overlap gate; keep all stopped artifacts negative until then.
2. After clarification only, perform a new preflight and register a distinct lane before any feature scoring; do not spend a competition slot until a separate selector authorizes it.
3. For an authorized new candidate, run feature-alone leakage tests, buffered whole-component holdout and paired spatial confidence intervals on both seeds using the shared pinned evaluator; stop on any canary or uniqueness failure.
4. Reconcile the discovered top candidate against the full contemporaneous registry inventory, not only locally restored rasters, before placement and again on final dots.
5. Obtain authorized DrivenData access for private competition data, live leaderboard/slot state, and an artifact-linked submission receipt. No credentials should be stored in repository or chat.
6. Current repository site is static and shows evidence/status; it cannot train a new model in the browser or auto-check private DrivenData account state. External status needs authenticated/available source access and cannot be claimed current without an actual check.

---

This review preserves prior science and its negative results. Tests and local format checks are not leaderboard scores, organizer acceptance, or permission to submit.
