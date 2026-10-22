# Repository review — 2026-10-22, Arena branch `arena/63e67511-gemsdoe79`

## Executive decision

**No new TIFF was generated and no submission slot was used. The existing TIFF is `OK TO DOWNLOAD: YES; OK TO SUBMIT: NO`.** This is a deliberate fail-closed result, not an incomplete upload attempt. The exact shared preflight was run before any new experiment; it exited `2` because a SHA-256-pinned registry raster has positive support over every allowed prediction cell. Under the repository's literal 3-pixel overlap rule, every nonempty candidate therefore has overlap `1.0`, greater than the `0.70` limit. Generating and labelling another nonempty raster as unique or submit-ready would contradict that proof. No alternate interpretation of “dots” was assumed.

A second independent stop is that the canonical G79-THVC lane has exhausted its registered three-experiment budget. The local feature cache/data needed to reproduce another hide-and-recover experiment is also absent in this checkout (`data/raw/` and `data/cache/` have no files; only the two small reference rasters and one restored registry witness are present). Do not try to evade the stop by clipping, changing thresholds, re-doting, changing the candidate budget, or relabelling a continuous surface.

## Why the reported H33 score was high — and what is actually established

The repository's byte-level forensics (`evidence/h33_forensics.json`, reproduced by `scripts/analyze_h33.py`) establish a **raster relationship**, not the provenance of an organizer score: H33 is pixel-for-pixel D2.8 after deleting every D2.8 dot at Euclidean distance `<= 2` pixels from the mapped-fault raster. The measured counts are 44,090 D2.8 positive pixels, 6,436 removed pixels, and 37,654 remaining H33 pixels; the H33 pixels are isolated (no 8-neighbour positive pairs). These are raster measurements, not scores.

The plausible metric mechanism is that the official distance-weighted Tversky metric rewards nearby hits using a local maximum but charges false-positive mass across predictions. Thus, sparse binary point emission can reduce redundant background mass relative to a dense probability corridor; removing points adjacent to already-mapped faults can further reduce predictions that are unlikely to earn credit when known faults are excluded from evaluation. This is a mechanism consistent with the exact raster transformation and the published metric, **not a causal proof** of the reported score change: private truth is unavailable, and the exact H33 file has no submission-page receipt tying its bytes to the score.

- `0.2778` is an **unverified historical filename/score report**, not ORGANIZER-CONFIRMED for the H33 hash.
- `0.4413` is the dated public-leaderboard observation recorded in `knowledge/official_sources.json`; it is not a score for a repository artifact or a submission-page receipt.
- `0.3195` is an older user-provided snapshot, not the current repository's verified reference.
- The canonical artifact's results below are **HOLDOUT-DTI**, never organizer scores. The repository has no organizer receipt for this artifact.

The byte derivation provides a sound explanation for why H33 could outperform denser predecessors. It does not establish that the result will generalize to the private test set or that this repository's current artifact can beat that reported leaderboard score.

## Candidate hypotheses for future research (not executed)

The audit found extensive existing experiments and overlapping proposal documents. “Different from this repo” below means a distinct *mechanism not implemented as this exact executable formulation*; it is **not** a claim of global novelty across the listed sibling sites. These are ranked qualitative research priorities, not numeric DTI forecasts. The stated mimics are explicit alternative causes that would need to be tested.

| Rank / potential / cost | Layers and physical signature | Why it could find a catalogue-missing fault | Difference from existing implementation and principal mimic | Data/validation status |
|---|---|---|---|---|
| **1 — potentially high; high data/processing cost** | DOE GDR 1391 magnetotelluric (MT) observations/models, if the specific resources support co-registration at useful scale, plus competition gravity/basement-depth layers. Test cross-depth resistivity-boundary orientation and its spatial alignment with a basement-density edge (not merely low resistivity). | A steep basement discontinuity beneath conductive cover could identify a buried structure that lacks a surface scarp or public fault trace. | G79-THVC uses shallow thermal/geochemical and potential-field indicators, but its preregistration does not describe this MT cross-depth test. **Mimic:** saline basin brines or a broad smectite clay cap, neither of which alone demonstrates a fault. | Official DOE GDR 1391 is cited in `knowledge/official_sources.json` and its listing describes an INGENIOUS compilation including MT. The needed MT files, spatial coverage, resolution, license on the exact files, and availability of resource downloads were **not independently checked in this session** and are absent from `registry/data_manifest.json` and `data/`. Therefore this is **not currently viable or validated**. Source: [DOE Geothermal Data Repository, submission 1391](https://gdr.openei.org/submissions/1391). |
| **2 — potentially moderate; medium-high cost** | GeoDAWN reduced-to-pole magnetic grid plus official survey flight-line/flight-path products and the DEM. Estimate direction-dependent edge persistence after accounting for documented flight-line/tie-line geometry; target a structural edge that persists across directions/scales rather than a simple magnetic gradient maximum. | A fault beneath alluvium may offset or truncate a magnetic source without producing a surface scarp; explicitly modelling survey geometry could retain weak geology while rejecting line artefacts. | Distinct from E1's magnetic/gravity lag and THVC's multi-physics model only if the flight-geometry correction is specified before looking at holdout. **Mimics:** flight-line levelling, variable terrain clearance, and lithologic contacts. | The official USGS GeoDAWN release record in `knowledge/official_sources.json` lists gridded products and flight-path/line products, and records line spacing/terrain-clearance caveats. Those source files are not present in this checkout. Re-download, exact product identity, and grid alignment must be confirmed before implementation. Source: [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). |
| **3 — potentially moderate; high cost** | USGS 3DEP elevation and a mapped hydrography network (NHD or successor) if coverage and resolution are sufficient. Measure paired channel-planform deflection, knickpoint alignment, and upstream-area-normalized channel steepness across a candidate lineament. | A fault can offset or warp drainage across a basin margin where scarps are muted; using network topology could find discontinuities missed by pixel-local scarp scoring. | THVC already uses DEM/chi/steepness-derived channels, and MRND includes a scarp-versus-channel discriminator; a new test would have to be a network-topology/paired-deflection model, not another local curvature or channel-edge feature. **Mimics:** lithologic knickpoints, transient incision, landslides, and stream capture. | The DEM derivatives presently referenced in source code are not a substitute for raw DEM and flow-network data. Neither the required USGS hydrography inputs nor a reproducible local flow network is in the checkout. A free official data source must be confirmed for the exact coverage/resolution before this becomes viable; no DTI claim is made. |
| **4 — potentially low-to-moderate and conditional on activity; high acquisition/processing cost** | Multi-temporal Sentinel-1 InSAR displacement/coherence products from an official archive, combined with competition terrain and known-fault masks. Test persistent narrow deformation gradients or discontinuities, not a single-date thermal/radar anomaly. | Persistent deformation may reveal a currently active concealed strand not represented in the compilation. | This is not a static magnetic, gravity, thermal-probe, or scarp detector used in the repository. **Mimics:** groundwater withdrawal, subsidence, volcanic deformation, atmospheric delay, and decorrelation. | InSAR coverage, acquisition dates, coherence, and processing availability over the full footprint were not checked; the necessary data are not local. Inactive/old faults may have no present deformation, limiting recall. Treat as **not viable for this run** until a free official archive and spatial/temporal coverage are verified (for example, NASA/ASF Sentinel-1 products; no access or availability claim is made here). |

### Top-candidate decision

Candidate 1 is the leading *scientific research question* in this shortlist, not an approved experiment. It cannot be validated from the current checkout: the MT data are not in the manifest/cache, the official listing alone does not prove suitable files or coverage, the literal novelty preflight blocks any nonempty candidate before feature tests, and this lane's registered experiment budget is spent. Accordingly, no feature-alone AUC, holdout DTI, surface audit, dot audit, or new TIF is claimed for it. Do not spend a weekly slot on it. First obtain prospective protocol-owner clarification of the literal overlap definition, restore and verify the exact permitted data, then preregister a new lane with a fresh budget; only then run single-feature leakage canaries followed by the shared spatially-blocked holdout and both novelty checks. No private evaluator or local threshold workaround is acceptable.

## Three review passes

### Pass 1 — state, provenance and reproduction boundary

- Read the entire README, `AGENTS.md`, canonical `run_card.json`, irregularities register, the required archived preregistrations, source manifest, current evidence and site.
- Confirmed branch `arena/63e67511-gemsdoe79`; no branch switch. Confirmed the project already preserves the original user prompt in the README and labels the canonical download `DO-NOT-SUBMIT`.
- Confirmed `scripts/preflight_new_lane.py --restore` exits `2` with state `impossible_under_literal_gate`, witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be` (see `evidence/new_lane_preflight_b79882e0.json` and `evidence/universal_overlap_certificate.json`).
- No new hypothesis was preregistered, no feature was evaluated, no holdout was rerun, no dots were placed, and no upload was attempted.

### Pass 2 — bug, contradictions and edge cases

- Pinned environment installed from `requirements.lock`; `pytest -q`: **355 passed**.
- `scripts/verify_project.py`: all current project checks passed. This validates consistency of existing files/evidence and is **not** an independent recreation of the holdout or an organizer acceptance.
- `scripts/check_site.py`: passed, 7 pages, 146 local links, all pages reachable, 2 compatibility redirects, no external assets, submit false.
- `scripts/submission_status.py`: `ok_to_download=true`, `ok_to_submit=false`, `verdict=negative`, exit `2` as intended. It reports no human inspection is needed to reach the current automated rejection.
- Identified and corrected two README ambiguities in this review: the former top summary said selected format/canary/holdout gates “ALL PASS” without clearly stating the literal novelty failure; it now names that failure. The former phrase “Zero scores here are labeled ORGANIZER-CONFIRMED” was ambiguous; it now explicitly says no repository artifact has a bound organizer receipt. Some generated Pages copy still says “Active Candidate” and uses a stale lane count. The machine card and prominent `OK TO SUBMIT: NO` decision remain authoritative; the site-builder source needs a provenance-aware refresh before those residual labels are changed.
- The current cache directory has no feature-stack files and `data/raw/` / `data/cache/` are absent; the README's full rerun command is not currently executable without restoring the ignored source data. The required shared evaluator/writer and their pins are present.

### Pass 3 — original-request and safety review

- The repository already has a newly generated canonical GeoTIFF, a ZIP, and a machine-generated executive summary. The existing TIFF hash is `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`; its local validator passes one-band float32, EPSG:32611, 3730×3292, exact sample transform, finite values in [0,1], no NaN in footprint. This file was **not generated in this session** and is **not approved for upload**.
- The existing G79-THVC results are **HOLDOUT-DTI** from `gems57-pooled-hide-v2`, not organizer scores: seed 20, 11,321 withheld positives, 0.1905 with 95% CI [0.1741, 0.2069]; seed 30, 11,342 withheld positives, 0.1944 with 95% CI [0.1774, 0.2126]. These historical measurements beat the fold-fair H33 analogue in the same evaluator, but do not clear novelty or establish a public/private leaderboard score.
- Registry measurements in the existing card: maximum absolute Spearman correlation before placement 0.771236; after placement 0.121049. The literal 3-pixel forward overlap is 1.0 due the universal positive-support witness; the candidate also has a measured 0.7139 overlap with the live GEMSDOE83 sibling per `reports/irregularities.md` IR-79-122. The sparse-only maximum reported in the frozen audit is 0.684410 over 718 maps; it cannot override the full literal-gate failure.
- No weekly slot, submission-page receipt, account eligibility, or organizer-confirmed score was observed. The proposal that this work itself can be uploaded now is rejected. The downloadable file is only for research/reproducibility.

## Work still needed / blockers

1. Obtain a prospective, authoritative owner decision on how literal positive-support overlap applies to continuous and space-filling registry rasters. Until then, honor the current fail-closed gate and do not generate another nonempty candidate.
2. Correct the documentation drift through a controlled source-of-truth update (card → generated README/Pages/status), then add regression tests so Pages cannot claim promotion/active candidacy when `protocol_unique` is false or the verdict is negative.
3. Restore the exact permitted input/cache files from verified sources. The DrivenData data page requires authentication; owner mirrors establish byte consistency, not organizer authentication. For any external data, verify source files, license, spatial coverage, resolution, and checksum before use.
4. If rule clarification and data restoration allow a new lane, preregister one hypothesis, test each feature alone for leakage, run `vendor/gems57/evaluate_holdout.py` on the two blocked seeds using only visible catalogue-derived features, and audit the surface before placement and final dots. The candidate must beat the current holdout best on both seeds with confidence intervals reported before a separate selector can consider it.
5. Keep the final approval decision separate from a weekly slot: only an authenticated submission page and a bound organizer receipt can establish capacity/acceptance. Never convert a holdout result or public leaderboard observation into an organizer score.

## Machine run card (this review; no new candidate)

```json
{
  "hypothesis": "No new experiment authorized. Future research shortlist ranks a DOE GDR 1391 MT cross-depth resistivity boundary test first, conditional on data verification and protocol clearance.",
  "mechanism": "A conductive-cover resistivity transition that aligns across depth with a gravity/basement boundary could indicate a concealed fault; this is a research hypothesis, not a measured result.",
  "named_non_fault_process": "Saline basin brines or a laterally extensive smectite clay cap can mimic a conductive anomaly without a fault.",
  "holdout_dti": {
    "status": "NOT RUN THIS SESSION",
    "existing_artifact_measurements": [
      {
        "class": "HOLDOUT-DTI",
        "evaluator": "gems57-pooled-hide-v2",
        "seed": 20,
        "withheld_positives": 11321,
        "value": 0.1905,
        "ci95": [0.1741, 0.2069]
      },
      {
        "class": "HOLDOUT-DTI",
        "evaluator": "gems57-pooled-hide-v2",
        "seed": 30,
        "withheld_positives": 11342,
        "value": 0.1944,
        "ci95": [0.1774, 0.2126]
      }
    ]
  },
  "correlation_overlap_vs_registry": {
    "existing_artifact_surface_max_abs_spearman": 0.771236,
    "existing_artifact_final_dot_max_abs_spearman": 0.121049,
    "literal_positive_support_forward_overlap_3px": 1.0,
    "current_verdict": "negative; literal uniqueness gate fails"
  },
  "raster_sha256": "d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2",
  "validator_output": {
    "artifact": "Existing canonical G79-THVC research TIFF; not created this session",
    "no_nan_inside_footprint": true,
    "values_in_0_1": true,
    "crs": "EPSG:32611",
    "shape": [3730, 3292],
    "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
    "local_format_validation": "PASS; not organizer acceptance"
  },
  "submission_name": "g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT",
  "submission_note": "GEMSDOE79 G79-THVC: 2m-probe+sinter+geophys+scarp 2-stage ensemble + Charnes-Cooper DTI (35093 px)",
  "verdict": "negative"
}
```
