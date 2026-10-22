# Repository review — 2026-10-22, session `bab8f374`

## Executive decision

**OK TO DOWNLOAD: YES — existing canonical research artifact only. OK TO SUBMIT: NO.**
This review produced **no new candidate, GeoTIFF, ZIP, model, holdout run, or
submission**. The canonical file remains `G79-THVC`, visibly named
`DO-NOT-SUBMIT`; its locally validated format is not approval to upload.

The decisive gate was rerun after restoring its frozen, SHA-256-pinned witness:
[`evidence/preflight_bab8f374.json`](../evidence/preflight_bab8f374.json) reports
`impossible_under_literal_gate`, `start_new_lane: false`, and exit code `2`.
The witness's positive support covers every allowed cell, so under the required
literal definition any nonempty candidate has `3 px` forward overlap `1.0`,
above the `0.70` limit. This is a protocol/representation obstruction, not a
scientific conclusion that the candidate geology is impossible. The full local
training feature raster and `data/raw/` are also absent, so the proposed top
hypothesis could not be evaluated on the shared spatial holdout even if the
novelty gate were resolved.

The recorded `HOLDOUT-DTI` values for existing `G79-THVC` are **archival card
results, not reproduced in this review and not organizer scores**. The reported
H33 value `0.2778` has no submission-page receipt in this repository tying it to
the H33 raster hash; the separate public leaderboard observation in the source
ledger does not identify this candidate. Therefore this review cannot claim a
higher competition score.

## Pass 1 — scientific evidence, H33, and metric claims

Read the canonical run card and preregistration, existing H33 analysis, official
source ledger, score caveats, active and archived lane records, and the evaluator
contract. Restored the frozen H33 and D2.8 rasters from the owner mirror and
checked them against the registry SHA-256 pins; reran `scripts/analyze_h33.py`.
It reproduced [`evidence/h33_forensics.json`](../evidence/h33_forensics.json)
without a tracked diff.

### What the bytes establish

- **RASTER-MEASUREMENT:** H33 contains `37,654` positive pixels. It is exactly
the D2.8 `44,090`-pixel field after deleting `6,436` cells at Euclidean distance
`<= 2 px` (`200 m`) from mapped faults; the disagreement count is zero. H33's
median catalogue distance is `19.6469 px`, `69.83%` of dots are farther than
`1 km`, and the map has no positive 8-neighbour adjacencies. These are raster
properties, not causal proof of a score change.
- **UNVERIFIED HISTORICAL REPORT:** `0.2778` is a reported filename-to-score
association, not an organizer-confirmed receipt for those bytes. The source
ledger records a `0.4413` **OFFICIAL PUBLIC LEADERBOARD OBSERVATION** dated
2026-10-22; it is not a receipt connecting H33 or G79-THVC to that score. Neither
page was freshly fetched in this review. See
[`knowledge/official_sources.json`](../knowledge/official_sources.json).
- **HOLDOUT-DTI, existing card only:** `gems57-pooled-hide-v2`, seed 20,
`11,321` withheld positive pixels: G79-THVC `0.1905` [95% CI `0.1741, 0.2069`]
versus fold-fair H33 control `0.0961` [95% CI `0.0831, 0.1090`]. Seed 30,
`11,342` withheld positive pixels: G79-THVC `0.1944` [95% CI `0.1774, 0.2126`]
versus H33 control `0.0989` [95% CI `0.0854, 0.1128`]. These values come from
`run_card.json` and its evidence, **were not recomputed here**, and cannot be
compared directly with a public leaderboard score.
- The result supports the limited claim that the existing candidate did better
than its matched H33 control on the recorded hide-and-recover folds. It does not
show that it beats the reported `0.2778` on competition evaluation, nor does it
establish organizer acceptance. “Holdout” here means withheld catalogue faults,
not the organizer's private test set.
- The review caught and corrected a documentation error: old README/analysis
prose called D2.8 `0.2768` and described a `+0.0010` increase to H33. The local
score ledger and prior prompt instead record D2.8 `0.2600` and H33 `0.2778`,
both as unverified historical reports. The corrected explanation is explicitly
conditional and does not claim the pixel deletion caused the reported change.

### Official references recorded by the project

- [DrivenData problem, data, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData staff clarification on known-fault masking](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official DOE / National Laboratory of the Rockies competition rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE Geothermal Data Repository submission 1391](https://gdr.openei.org/submissions/1391)
- Full claim, date, access, and limitation records: [`knowledge/official_sources.json`](../knowledge/official_sources.json).

The source ledger records previous research fetches/reviews, but I did not freshly
fetch any external pages in this session. Official-site reachability is not a
receipt, and owner-mirror hash verification is not independent organizer
authentication.

## Pass 2 — hypothesis, feature overlap, novelty, and data review

Compared the active feature names and implementation in
[`src/gems79/thvc_features.py`](../src/gems79/thvc_features.py), current and
archived hypotheses, lane cards, family-lineage material, and the frozen registry
audits. The reconciled qualitative slate is
[`research/hypotheses_bab8f374.md`](../research/hypotheses_bab8f374.md). Its four
candidates are **unexecuted concepts**, not newly preregistered methods and not
claims of global novelty. Several have appeared in older research notes; the
raster registry by itself cannot tell whether a sibling's source code used a
similar method.

1. **Rank 1 — depth-resolved MT boundary.** Potentially relevant to buried
geothermal faults, but only if GDR 1391 contains a correctly georeferenced,
footprint-covering MT product. The active stack already uses `cond_surf` and
`hydro_demag_clay_conj`; no raw depth-resolved MT layer was verified locally.
The non-fault mimic is a conductive saline/clay-rich basin. Potential and
feasibility are both uncertain; no DTI improvement is estimated.
2. **Rank 2 — multi-temporal InSAR displacement discontinuity.** A genuinely
different measurement from the static rasters, but it only addresses currently
deforming faults and requires external scene/time-series processing. Pumping,
geothermal operations, and volcanic inflation are named mimics. No local data or
holdout evidence exists.
3. **Rank 3 — three-dimensional relocated microseismicity planes.** The existing
`deq_n100a15` / `ieq_n100a15` bands are smoothed fields, not raw hypocentres.
Mining blasts, induced geothermal events, and network-detection artifacts are
important mimics. No raw catalogue or tested event-plane model is present.
4. **Rank 4 — GeoDAWN raw flight-line re-leveling.** This is different from
computing another magnetic gradient but related to prior magnetic-marker work.
It depends on original line observations and navigation data, which are not
restored here; dikes/intrusive contacts and leveling seams can mimic a fault.

These priorities are qualitative assessments of plausible **HOLDOUT-DTI**
benefit against cost and data risk, not projected scores. The current training
feature raster and `data/raw/` are absent, and no candidate surface was built.
A top candidate therefore was **not validated** on the requested spatial holdout.

### Ideas excluded as repeats or unsupported

- A radiometric ratio or residual is not a distinct lane without a specified
measurement beyond the active `rad_k_th_alteration` and
`hydro_demag_clay_conj` features.
- Catalog-near relays, crack tips, and stress/strain transfer overlap active
features and stopped archived lanes; they must not be retuned or restarted.
- Scarp crests, knickpoints/drainage, shoreline-datum controls, and far-field
banding overlap active features or prior sibling experiments/proposals. In
particular, shoreline/datum experiments are already present in historical
GEMSDOE62 records; a new name would not make that idea untried.

### Novelty gate and data boundary

- **REGISTRY-MEASUREMENT from the existing G79-THVC card:** its pre-placement
surface's maximum absolute Spearman correlation is `0.771236` (below the stated
`0.90` limit), but the literal forward-overlap maximum is `1.0`. Its final dots
have maximum Spearman `0.121049` and maximum Jaccard `0.041683`; sparse maps at
or below `50,000` dots have maximum reported overlap `0.684410` across `718`
comparisons. The unchanged literal full-registry overlap is nevertheless `1.0`.
Passing the sparse subset does not clear the literal gate.
- **Fresh preflight in this review:**
[`evidence/preflight_bab8f374.json`](../evidence/preflight_bab8f374.json) records
witness SHA-256
`ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`,
`covered_allowed_fraction: 1.0`, limit `0.70`, and `start_new_lane: false`.
The strict preflight stopped before any model or placement work; no surface or
final-dot comparison was computed for a new candidate.
- These novelty statistics are **registry measurements**, not DTI values. The
preflight is not a scientific test of geological merit; it is a hard stop under
the specified uniqueness rule. We did not alter `vendor/gems57`, change the
dot definition, or exempt any raster.
- `registry/data_manifest.json` contains hash pins for the full numerical stack
and external layers, but this checkout has only small reference rasters and
`data/restore_receipt.json`; `training_features.tif` and `data/raw/` are absent.
Do not replace missing measurements with zero.

## Pass 3 — reproducibility, publication status, and checks

This pass checked the submitted documentation/site changes against the canonical
card and publication contract. The fresh commands and outcomes for this review
are recorded below (the older `reports/verification_passes.md` is a historical
log, not the evidence for this review):

- `scripts/verify_project.py`: **31 checks passed**; shared template pin:
**23/23** files matched.
- `pytest`: **356 passed**, including a new publication regression test for the current negative status and H33 evidence-class wording.
- `scripts/check_site.py`: **passed**, **7 pages**, **149 local links**, all
pages reachable from the home page.
- `scripts/analyze_h33.py`: reproduced the tracked forensics JSON exactly; no
evidence diff.
- `scripts/preflight_new_lane.py --restore`: expected stop, exit **2**.
- `scripts/submission_status.py`: **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**.
Blockers include the uncleared literal novelty rule, negative scientific verdict,
missing separate selector approval/receipt, and missing explicit submission
approval. Weekly account capacity is unknown; no slot was selected or spent.
- No experiment was run; no new raster/ZIP was emitted; no upload was attempted.
The README's original prompt remains intact. Website and README status refer to
the existing research artifact only.

### Limitations and disposition

1. No new candidate can pass the present literal novelty gate while the pinned
witness remains; any protocol change must be prospective and owner-approved.
2. The feature stack is absent, so no new spatial holdout result, leakage canary,
feature build, or candidate validator was produced.
3. The official pages, USGS/GDR product contents, remote submission account,
weekly capacity, selector decision, and organizer receipt were not independently
checked during this session. No upload or slot spend occurred.
4. H33's reported competition value and the public leaderboard observation
remain different evidence classes. Neither establishes this TIFF's score.
5. The prior hypothesis backlog includes numerical projections and data/runtime
claims that were not validated here. They are historical planning notes, not
current measured results. This review's slate supersedes those rankings for
current decision-making but does not erase their audit trail.

**Recommendation:** Keep the canonical G79-THVC file downloadable for research
only and visibly `DO-NOT-SUBMIT`. Do not generate or promote a candidate under
the current preflight. If an owner-authorized prospective rule change resolves
the literal gate, first restore and receipt the exact data, define a single
method lane, preregister it, pass surface novelty before placement, test every
feature alone, use the shared buffered evaluator/writer, and report both seeds'
HOLDOUT-DTI and uncertainty. Only then may a separate selector consider a slot.

## Review decision card (not an experiment card)

```json
{
  "card_type": "REVIEW_DECISION_NOT_EXPERIMENT",
  "review_id": "bab8f374",
  "hypothesis": "No new candidate was run. Highest-ranked future concept: depth-resolved MT boundary contrast, conditional on verifying the actual GDR product and prospective protocol approval.",
  "mechanism": "If a validated depth-resolved MT product exists over the footprint, test cross-depth lateral resistivity boundaries against an independent gravity-basement edge using fold-safe processing; no such feature was built or scored in this review.",
  "named_non_fault_process": "Saline playa brines and clay/evaporite-rich basin fill can create conductivity boundaries without a Quaternary fault.",
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "measured_in_this_review": false,
    "new_candidate": null,
    "existing_canonical_card": {
      "evaluator_version": "gems57-pooled-hide-v2",
      "seed_20": {
        "withheld_positive_pixels": 11321,
        "dti": 0.1905,
        "ci95": [0.1741, 0.2069]
      },
      "seed_30": {
        "withheld_positive_pixels": 11342,
        "dti": 0.1944,
        "ci95": [0.1774, 0.2126]
      },
      "status": "copied from existing run_card.json; not reproduced in this review; not an organizer score"
    }
  },
  "correlation_overlap_vs_registry": {
    "evidence_class": "REGISTRY-MEASUREMENT",
    "new_candidate": "not computed; preflight stopped before a surface or dots existed",
    "preflight": {
      "state": "impossible_under_literal_gate",
      "exit_code": 2,
      "witness_sha256": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
      "covered_allowed_fraction": 1.0,
      "overlap_limit": 0.7,
      "literal_overlap_for_any_nonempty_map": 1.0
    },
    "existing_canonical_g79_thvc": {
      "preplacement_max_abs_spearman": 0.771236,
      "preplacement_literal_max_forward_overlap_3px": 1.0,
      "final_max_abs_spearman": 0.121049,
      "final_max_jaccard": 0.041683,
      "max_sparse_forward_overlap_3px_at_or_below_50000_dots": 0.68441,
      "sparse_comparisons": 718,
      "literal_max_forward_overlap_3px": 1.0
    }
  },
  "raster_sha256": "d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2",
  "raster_role": "pre-existing canonical G79-THVC research TIFF; no new TIFF generated",
  "validator_output": {
    "applies_to": "pre-existing canonical TIFF only",
    "local_format_range_passed": true,
    "single_band_float32": true,
    "crs": "EPSG:32611",
    "shape": [3730, 3292],
    "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
    "no_nan_inside_footprint": true,
    "all_values_in_0_1": true,
    "organizer_acceptance": "UNKNOWN; no submission-page receipt"
  },
  "submission_name": "g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT",
  "submission_note": "GEMSDOE79 G79-THVC: 2m-probe+sinter+geophys+scarp 2-stage ensemble + Charnes-Cooper DTI (35093 px)",
  "ok_to_download": true,
  "ok_to_submit": false,
  "verdict": "negative",
  "new_candidate_tiff_generated": false,
  "weekly_slots_used_in_this_review": 0
}
```
