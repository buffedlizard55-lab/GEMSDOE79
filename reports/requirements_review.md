# Final brief-to-evidence review — 2026-10-22 continuation

Reviewed against the full original brief preserved in `README.md`, the current
`run_card.json`, the frozen input/registry manifests, and the updated official
source ledger. **The core request for a genuinely protocol-unique, submittable
GeoTIFF is not satisfied.** The existing H79-NHR research artifact remains
negative; this continuation generated no candidate TIFF, ran no new holdout,
selected no slot, and uploaded nothing.

| Requirement | Status | Evidence / boundary |
|---|---|---|
| Review the repository and continue prior work on the fixed branch | Done | Current branch is `arena/616fe8e7-gemsdoe79`; README, active H79-NHR card, source artifacts, audits, current/archived hypothesis records, and site/status code reviewed. No branch switch or scientific-lane restart. |
| Preserve and re-read the full user brief | Done | Full brief remains in the expandable README section; this review explicitly treats its historic scores and data assertions as claims to verify, not ground truth. |
| Analyze H33's reported 0.2778 result | Done with evidence limits | `knowledge/why_h33.md` and `reports/nhr_analysis.md` document pixel-level lineage: H33 is the D2.8 dot set minus 6,436 points within 200 m of mapped faults. The 0.2778 score remains an unverified historical filename-to-score report, not an artifact-linked organizer receipt. |
| Verify current public leaderboard values | Done as a dated public-page observation | Official page fetch (2026-10-22): #1 **0.4413**, #22 **0.3183**, #48 **0.2804**. These are `OFFICIAL PUBLIC LEADERBOARD OBSERVATIONS`, not this repo's score or a receipt for H33. The user's 0.3195 is not the observed current #22 value. `knowledge/official_sources.json` and `docs/evidence/source_health.json` are updated. |
| Produce a new, unique GeoTIFF | **Not delivered in this continuation; existing artifact is negative** | Existing file: `docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif`, SHA-256 `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`. It is newly computed, but failed surface and final uniqueness. **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** No new TIFF was built here. |
| Validate format automatically and make status unmistakable | Done for existing artifact | Run card, validator, `scripts/submission_status.py`, README, download page, and executive page all say download YES / submit NO. Existing format preflight is single-band float32, EPSG:32611, 3730×3292, sample transform, finite [0,1] values; this is not uniqueness or organizer acceptance. |
| Explain submission in an executive-summary page | Done | Existing `docs/executive-summary.html` and static-site decision panel describe the negative artifact and do not present upload instructions as a pass. Site regenerated and checked: 7 pages, 114 local links, all reachable, 2 compatibility redirects, 0 external assets. |
| Use one method and honor duplicate stop gates | Done for H79-NHR; no new lane started | Existing H79-NHR uses the registered method, shared evaluator/writer, 464 single-feature AUC canaries (max 0.8589), and two-seed buffered hide-and-recover. It beat H33 control but failed the uniqueness gate: 26 informative registry dot fields each exceed 70% forward 3-px overlap; worst 0.913. No retuning, overlap cap, or registry exemption was applied. |
| Surface and final uniqueness checked against a complete registry | **Blocked / fail-closed** | The exact H79-NHR surface/final audit has **986 grid/format-comparable of 992** rasters and six errors; its audit remains incomplete. Git-based restoration now verifies **992/992 bytes** (`evidence/registry_restore_git_2026-10-22.json`), but hash restoration does not fix CRS/transform/TIFF comparison errors. The 26 duplicate witnesses remain. |
| Check the fixed 37,654-dot budget's lattice capacity | Done as a registry measurement | `evidence/registry_capacity_2026-10-22.json`: only 6,514 allowed cells lie outside the 13GEMSDOE lattice's 3-px halo. At 37,654 dots, at least 31,140 (82.70%) must overlap that raster, exceeding 70% regardless of candidate surface. This bound is budget-specific and is not claimed to prove every lower budget impossible. |
| Rank 3–5 distinct new hypotheses with official sources, mimics, gain/cost, and novelty rationale | Done; none eligible for holdout yet | Four ideas in `research/hypotheses_followup_20261022.md`: USGS heat-flow well residual corridors (prospective top), depth-sliced MT conductance pathways, ComCat focal-mechanism stress compatibility, and Qfault-derived slip/dilation (explicitly rejected as leakage-prone). Ranking is qualitative, not projected DTI. |
| Test the new top candidate on blocked holdout before a slot | **Not done; no new holdout was authorized** | The prospective heat-flow ZIP (USGS DOI 10.5066/P9BZPVUC) is publicly listed at 124.12 MB, but its binary fetch returned HTTP 500; no bytes, SHA-256, field schema, or grid compatibility are available. The registry comparator also remains incomplete. H79-NHR's previously measured holdout is not reused as a result for the new hypothesis. No account slot was used. |
| Confirm free/official source availability | Partially done; binaries not downloaded | Official USGS/GDR/ComCat descriptions and resource listings are recorded in `knowledge/official_sources.json`. The GDR 1391 page advertises public CC BY 4.0 data; USGS heat-flow and MT file listings are public. A listed resource is not a retrieved feature layer or proof of compatibility. |
| Restore source data and registry bytes | Done, with scope limits | Rehashed all **13/13** manifest inputs (`evidence/data_restore_2026-10-22.json`) while preserving the original receipt. Git-based registry blob restoration verified **992/992** frozen TIFF bytes; it does not certify source-mirror organizer authenticity or pixel-grid comparability. |
| Keep every score correctly labelled | Done | H79-NHR values remain `HOLDOUT-DTI` with evaluator `gems57-pooled-hide-v2`, withheld-positive counts and CIs in `run_card.json` / `reports/nhr_analysis.md`. Leaderboard values are dated public observations. No projection is stated as a score and no new score was computed. |
| One JSON run card and a separate selector | Done for prior lane; no new run card needed | `run_card.json` is unchanged and remains negative; `evidence/nhr/selector_decision.json` refused promotion. This continuation created no scientific run, so it did not overwrite or create a candidate card. |
| Name/comment limit and no copied submission | Existing artifact compliant; no new artifact | Existing name ends in `DO-NOT-SUBMIT` and note is 122 characters. No copied prior artifact or new name/comment was generated here. |
| Three review passes and source integrity | Done for this continuation | `reports/repository_review_2026-10-22.md` records the evidence review, engineering pass, and acceptance recheck. The lock now declares `scikit-image` and its runtime dependencies; a clean install from `requirements.lock` and `pip check` succeeded. |
| Create and merge a PR to `main` | **Pending** | No PR/merge is claimed until the branch is pushed, checks complete, and the explicit PR merge command succeeds. |

## Acceptance decision

This continuation improves reproducibility, current-source reporting, and
research planning. It does **not** turn the existing negative H79-NHR file into
a unique submission, and it does not manufacture a new artifact or score. No
new lane is eligible to enter holdout until (1) the comparison inventory can be
checked completely, (2) any new external bytes are retrieved and hash-pinned,
and (3) a fixed, preregistered surface passes the surface uniqueness gate.
