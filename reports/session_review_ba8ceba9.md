# Active-branch review — session `ba8ceba9` (2026-10-22)

## Outcome

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The repository already contains a newly generated, byte-unique research GeoTIFF at [`docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif), SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`. The automated decision is negative because literal registry novelty fails, the selector has not approved a slot, and no organizer receipt is bound to this artifact. This review did not upload a file or spend a weekly slot.

This is not a contradiction: the bytes are absent from the pinned registry, but the required spatial novelty gate is stricter than byte uniqueness. The machine-readable final card remains [`run_card.json`](../run_card.json); no second run card was created.

## H33 answer

The repository's byte-level analysis in [`knowledge/why_h33.md`](../knowledge/why_h33.md) establishes that H33 is the D2.8 impulse field with 6,436 predictions within 200 m of the mapped-fault raster removed. Its reported `0.2778` is historical/user-supplied, **not ORGANIZER-CONFIRMED in this repository**. The defensible mechanism is metric-aware sparsification: high-confidence separated impulses can retain triangular-kernel true-positive credit while avoiding the false-positive mass of a diffuse probability surface. Catalogue-collar pruning additionally removes predictions likely to rediscover already mapped traces. This explains the design; it does not prove a future leaderboard score.

The current G79-THVC candidate beats the fold-fair H33 control on both spatial holdout seeds: `HOLDOUT-DTI` (`gems57-pooled-hide-v2`) `0.1905` (95% CI `[0.1741, 0.2069]`, 11,321 withheld positives) and `0.1944` (`[0.1774, 0.2126]`, 11,342 withheld positives), versus H33 control `0.0961` and `0.0989`. A leaderboard score above `0.2778` cannot be claimed without a submission receipt.

## Candidate hypotheses reviewed before implementation

The ranked, untried set is already preregistered in [`research/hypotheses_post_thvc_backlog.md`](../research/hypotheses_post_thvc_backlog.md), rather than invented after seeing a result:

1. **H80-MT-PHASE** — GDR-1391 3-D magnetotelluric resistivity gradients crossed with gravity-gradient normals; targets sub-clay-cap conductive boundaries in covered basin, with saline groundwater/lithologic contacts as the named mimic. Expected improvement: highest; cost: high.
2. **H80-DRAPE-DECONV** — GeoDAWN magnetic field plus flight-line/drape-height information; source-depth and edge transforms target concealed basement breaks away from catalogue traces, with acquisition drape and cultural noise as mimics. Expected improvement: high; cost: medium-high.
3. **H80-RADIO-KD** — GeoDAWN K/eTh/eU plus lithology/silica conditioning; cross-fitted potassium residual targets hydrothermal adularia rather than unnormalized mapped-fault proximity, with felsic lithology and soil moisture as mimics. Expected improvement: medium; cost: medium.
4. **H80-SLIP-DEFICIT** — 3DEP elevation/relief and visible fault geometry; along-range footwall-relief residual targets missing continuation segments, with fluvial incision and resistant beds as mimics. Expected improvement: medium; cost: medium.
5. **H80-COULOMB-CFS** — mapped fault geometry plus elastic dislocation stress transfer; negative stress-shadow and tip-lobe transforms target mechanically plausible blind splays, with uncertain slip/rake and regional stress as mimics. Expected improvement: uncertain; cost: high.

The detailed backlog identifies official/free source provenance and distinguishes each from implemented lanes. No candidate was run because the mandatory preflight stopped the lane before experimentation.

## Three verification passes

### Pass 1 — repository and protocol

Read the complete README, `AGENTS.md`, canonical card, irregularity ledger, active THVC preregistration, and archived DILSTEP/FFAS preregistrations. Confirmed branch `arena/ba8ceba9-gemsdoe79`. The full original prompt is preserved in README. Historical branch names and archived cards were treated as provenance only.

### Pass 2 — automated defects and edge cases

Installed the exact lockfile into ignored `.venv` and ran:

- `pytest -q`: **355 passed**.
- `scripts/verify_project.py`: **all 29 checks passed**; raster hash agrees with the card and receipt.
- `scripts/check_site.py`: **7 pages, 146 local links, all reachable**, no external assets; submit status remains false.
- `scripts/submission_status.py`: expected exit `2`, `ok_to_download=true`, `ok_to_submit=false`, `human_inspection_required_for_this_decision=false`.

The reopened raster checks pass locally: one band, float32, EPSG:32611, 3,730 × 3,292, reference transform match, finite values in `[0,1]`, and no NaN/Inf. Local validation is not organizer acceptance.

### Pass 3 — original requirements and stop rule

`preflight_new_lane.py --restore` returned the mandated stop (`exit 2`): one hash-verified registry raster has positive support within 3 px of every allowed cell, so every nonempty candidate has literal overlap `1.0 > 0.70`. Under the user's lane rule, starting an experiment or manufacturing another TIFF would be a protocol violation. The existing candidate's feature canaries all remain below the `0.90` leakage threshold; nevertheless its literal novelty failure controls the final verdict.

## Irregularities and limitations

- The literal overlap requirement is unsatisfiable for any nonempty candidate given the frozen full-footprint witness. A prospective owner clarification of “dots” for continuous/dense rasters is required; it must not be changed post hoc for this lane.
- Outbound access in this environment is restricted, so this pass did not re-fetch DrivenData, USGS, NLR, GDR, Dropbox, or deployed Pages. Stored source receipts were reviewed but are not converted into fresh web receipts.
- DrivenData authentication/account state, rule acceptance, weekly capacity, upload acceptance, and leaderboard score are not available locally. Only a submission-page receipt can support an `ORGANIZER-CONFIRMED` label.
- No score above `0.2778` or the stated leaderboard values is promised. Holdout results are proxy measurements, not projections or organizer scores.

## Official/manual-review links

- Competition overview: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Competition resources: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Official reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- DOE GDR dataset record: https://gdr.openei.org/submissions/1391
- USGS GeoDAWN record: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- EPSG:32611 definition: https://epsg.io/32611

## Final decision

No new experiment and no submission selection. Preserve the existing, genuinely generated TIFF as a downloadable negative research deliverable. Do **not** submit it until a prospective novelty-rule clarification is encoded in shared tooling and a separate selector re-derives every gate.
