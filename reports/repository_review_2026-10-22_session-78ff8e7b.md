# Three-pass repository review — session `78ff8e7b` (2026-10-22)

## Decision and scope

This is a scoped three-pass review, **not a byte-for-byte revalidation of every historical lane and every row in the irregularities log**. It records the current blockers and reconciles the named shortlist against checked-in family indexes plus the newly merged mainline evidence; archived score/evidence claims remain subject to their own cited evidence classes. The review began on base `8055053`; while PR #80 was being opened, `origin/main` advanced to `ffd1647` (PR #79), so the review and PR branch were refreshed against that mainline state before delivery.

**No new scientific lane, holdout run, final placement, GeoTIFF, selector decision, competition upload, or weekly slot was used in this session.** The current request contains no delimited method paragraph assigning a new lane; G79-THVC and the newly merged G79-CFSKD lane are both negative/closed, and the literal registry novelty preflight exits `2`: a hash-verified prior covers every allowed cell, so any non-empty map has `1.0` forward 3-pixel overlap against a `0.70` limit. No alternate binarization or threshold was silently substituted. G79-CFSKD is cited below as prior mainline evidence, not as an experiment run by this review.

The prompt is already preserved in full in the README's **“Original project prompt”** section. The current published artifact is already the unique-by-bytes G79-THVC research TIFF, but it is **not unique under the required overlap gate** and must not be represented as submit-ready. The correct machine decision remains **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** This review is documentation-only and leaves the scientific artifacts and canonical run card unchanged.

## Pass 1 — map the repository and evidence

- Confirmed the working branch is `arena/78ff8e7b-gemsdoe79`, initially based on `8055053`; the checkout was clean before review. After PR #79 merged to main (`ffd1647`), updated this branch by merging `origin/main` without switching branches.
- Read `README.md`, including the embedded original prompt, plus `AGENTS.md`, the canonical `run_card.json`, the G79-THVC / DILSTEP / FFAS preregistrations, the shared-template pin, the feature/data manifests, current status evidence, and hypothesis backlogs. The refresh also reviewed mainline G79-CFSKD (`run_card_cfskd.json`, `evidence/cfskd/holdout_results.json`, and its archived artifact) and `research/hypotheses_45998a01.md` / `research/hypotheses_bda00cff.md`. Reviewed `reports/irregularities.md` in chunks and traced task-relevant entries; this did not revalidate every historical row or archived measurement.
- The project already contains an executive-summary/submission guide, static site, current canonical TIFF/ZIP, automated format validator, holdout evaluator, uniqueness gate, selector, source ledger, and regression suite. The prompt does not need to be copied into README a second time.
- The only TIFF/ZIP pair in active `docs/downloads/` is `g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT`. Its raster SHA-256 is `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`; the file is `137,299` bytes. The name and status correctly warn against submission.

## Pass 2 — verify implementation, fail-closed gates, and edge cases

### Reproducible local checks

The local ignored `.venv` was built from the pinned `requirements.lock`; no dependencies or large inputs were added to Git.

| Check | Observed result |
|---|---|
| `.venv/bin/python -m pytest -q` | **374 passed** after refreshing against mainline PR #79. |
| `.venv/bin/python scripts/verify_project.py` | **All checks passed**, including card/artifact/ZIP hashes, format, frozen witness, shared-tool pins, status agreement, and evidence consistency. This is not a new training run or upload. |
| `.venv/bin/python scripts/check_site.py` | **Passed**: 7 pages; 150 local links; all pages reachable; 2 compatibility redirects; submission remains false. |
| `.venv/bin/python scripts/submission_status.py` | Correct fail-closed JSON, `ok_to_download=true`, `ok_to_submit=false`, `verdict=negative`; exit `2` is expected. |
| `.venv/bin/python scripts/preflight_new_lane.py --restore` | `start_new_lane=false`, `state=impossible_under_literal_gate`, exit `2`; it restores/measures only the frozen witness and does not run science. |

### Registry stop is mathematical under the literal rule

The re-measured `REGISTRY-MEASUREMENT` witness SHA-256 is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`. Its literal positive support covers all `5,106,385` allowed cells; uncovered allowed cells are `0`. Therefore any non-empty prediction within the allowed domain has forward overlap `1.0`, exceeding the required `0.70`. This is a finding about the protocol's literal definition of registry “dots,” not an organizer score or evidence that the candidate copied that raster. The canonical raster has different bytes, but the prescribed gate still rejects it. A protocol owner must prospectively define how continuous registry surfaces become dots and apply that definition symmetrically before any lane is restarted.

### Existing holdout evidence — not rerun in this review

The canonical card records these as **HOLDOUT-DTI (`gems57-pooled-hide-v2`)**, not leaderboard scores. The fold-fair H33 analogue is included for context:

- Seed `20` (`11,321` withheld positives): G79-THVC **HOLDOUT-DTI `0.1905`**, 95% CI `[0.1741, 0.2069]`; H33 control **HOLDOUT-DTI `0.0961`**, 95% CI `[0.0831, 0.1090]`.
- Seed `30` (`11,342` withheld positives): G79-THVC **HOLDOUT-DTI `0.1944`**, 95% CI `[0.1774, 0.2126]`; H33 control **HOLDOUT-DTI `0.0989`**, 95% CI `[0.0854, 0.1128]`.

These are prior canonical measurements; this session did not recompute them. They show that G79-THVC beat the fold-fair H33 analogue under the shared spatial holdout evaluator. They do **not** establish that this raster beats H33's user-reported public result, the public leaderboard, or the private competition test set. The committed `evidence/uniqueness_final_artifact.json` is an early rejection after checking only `1` of `992` indexed rasters; it is explicitly incomplete, not a full uniqueness clearance.

### Format and download decision

The shared on-disk validator reopens the canonical TIFF and records: one `float32` band; `EPSG:32611`; shape `3730 × 3292`; transform `[100, 0, 243350, 0, -100, 4508550]`; no NaN or infinity; minimum `0.0`; maximum `1.0`; `35,093` positive pixels; no positive mass outside the sample footprint; and no positive pixels on the mapped catalogue. All recorded format checks pass. This only establishes local format/range validity. It does not clear novelty, establish organizer acceptance, or diagnose the previously rejected file because the rejected bytes and portal receipt are not available.

### Reproducibility / data-placement limitation

This checkout contains `data/reference/existing_faults.tif` and `sample_submission.tif`, but **does not contain `data/raw/` or `.cache/thvc/`**. In particular, the pinned `training_features.tif`, LiDAR derivatives, GeoDAWN layers, and INGENIOUS point data are not materialized here. `data/restore_receipt.json` records 13 manifest inputs as `present`; `scripts/verify_project.py` checks that the receipt IDs and SHA-256 values match `registry/data_manifest.json`, but does not establish that all 13 files are present on disk now. Treat that receipt as prior hash/provenance evidence, not proof of current local availability. The direct DrivenData data page is login-gated in the repository's source ledger; GitHub mirror consistency is not independent organizer authentication.

### Code-review irregularity: possible circular edge contamination

`src/gems79/thvc_features.py:636,644,653–662` uses `numpy.roll` for directional line integrals and cross-strike steps. `numpy.roll` wraps values from one raster edge to the opposite edge. The largest along-strike stencil reaches `10` pixels; the existing TIFF has `140` positive pixels within `10` pixels of the outer raster boundary. This is a **potential boundary artifact**, not proof that those predictions or the prior HOLDOUT-DTI values are wrong. The raw feature inputs and cached stack are absent, and G79-THVC is closed, so this review did not change its code or claim a corrected score. A prospective rebuild should use non-wrapping convolution/padding with full-stencil support masking and then re-evaluate on newly preregistered data; do not patch the closed lane or reuse its old scores as evidence for changed code.

## H33 (`0.2778`) — what the repository can and cannot establish

`evidence/h33_forensics.json` labels its findings **RASTER-MEASUREMENT, NOT A SCORE**. It records that H33 has `37,654` binary positive pixels and is pixel-for-pixel the earlier D2.8 dot map (`44,090` positives) after deleting `6,436` dots at distance `<= 2` grid pixels from `existing_faults.tif`; the measured disagreement with that pruning rule is `0`. This supports the interpretation that H33 was an emission/pruning change rather than a newly trained model.

Why that could improve the reported public metric: the competition's distance-weighted Tversky formulation gives a maximum-based credit to nearby prediction pixels but sums false-positive mass across predictions. Sparse, separated `1.0` dots can therefore reduce redundant background mass relative to diffuse positive probability surfaces. Removing near-catalogue dots can also improve a particular hidden set, but it is not valid to call every removed flank a false positive: organizer clarifications in the local source ledger say hidden truth may include close splays and continuations. Without the private truth and a submission-page receipt, the byte-level geometry supports a plausible mechanism, not a causal proof of the reported score.

The H33 value `0.2778` is an **UNVERIFIED HISTORICAL REPORT** supplied in the prompt; no submission-page receipt binds it to the measured H33 hash. The local source ledger records a public-leaderboard **PUBLIC-OBSERVATION `0.4413`** dated `2026-10-22`; against that stored observation, the prompt's `0.3195` “current top” figure is stale. This review did not refetch the page, and neither public observation is an ORGANIZER-CONFIRMED score for this repository's artifact. No score for this repository's artifact can be claimed from this review; the public-leaderboard observation is context only. The only newly relevant benchmark values are the prior, explicitly labelled HOLDOUT-DTI results above.

## Pass 3 — candidate hypotheses and decision against the request

The repo already has candidate backlogs (`research/hypotheses_preflight_a7d092d7.md`, `research/hypotheses_post_thvc_backlog.md`, `research/hypotheses_45998a01.md`, `research/hypotheses_bda00cff.md`, and earlier hypothesis files). I compared the proposals with checked-in `registry/registry_index.json` and `registry/registry_delta.json` names, the post-snapshot lineage audit, and the new mainline G79-CFSKD card/evidence. This remains a name/description and reported-method reconciliation, not a byte-level or algorithm-by-algorithm audit of all family work. Cross-scale/crest ideas overlap with `GEMSDOE40` `h13-crest-binary`, `GEMSDOE77` `h82-crestthin`, `GEMSDOE42` `xscale-worm-persistence`, and `55GEMSDOE` multiscale tensor persistence; magnetic/step ideas overlap with `GEMSDOE45` KMTIP, `GEMSDOE70` magnetic/cover outputs, and `GEMSDOE77` demagnetization/gravity-step and magnetic/gravity-coherence outputs; MT/clay-cap ideas overlap with `GEMSDOE32` `h32c-mt-claycap-breach`, `GEMSDOE76` MT-breach, and `GEMSDOE77` `h77c-claycap-breach`. Coulomb stress shadows were proposed as `H80-COULOMB-CFS` and are now implemented in mainline G79-CFSKD's visible-only flank-shadow veto (PR #79); that idea is removed from the untried shortlist. The drainage/knickpoint idea was already listed as H79-U2 and is also excluded.

The following are a **qualitative, risk-adjusted shortlist of previously proposed but unvalidated concepts**, not new research ideas, experiments, or measured performance. “Untried” means the exact transformation is not confirmed as an executed experiment in this repository; it does **not** mean novel within the GEMSDOE family. None can be certified as globally distinct, and none is viable for a run now. Priority and cost are qualitative judgments, not DTI predictions.

| Rank / expected value / cost | Layers and targeted signature | Why it could reveal a missing fault; difference from current methods | Named non-fault mimic and availability |
|---|---|---|---|
| **1 — Moderate prior; low–medium cost: scale-space scarp-crest migration** | `lidar_scarp_features_u8` (`lapneg_max`, `lappos_max`, `step_max`, `coh100`) with `training_features.tif:det_elev`; measure whether the same coherent crest persists or migrates across fixed smoothing scales. | Low-amplitude/degraded Quaternary scarps may retain a stable crest trace after amplitude-based rankers lose them. G79B-SDPT forms crest/base dipole and facing-polarity interactions; G79-THVC quantile-bridges curvature, but neither active implementation tracks the crest's spatial displacement through scale space. | **Mimic:** Lake Lahontan shorelines and fluvial terrace risers. Related family rasters already include `GEMSDOE40` `h13-crest-binary`, `GEMSDOE77` `h82-crestthin`, `GEMSDOE42` `xscale-worm-persistence`, and `55GEMSDOE` multiscale tensor persistence; the exact displacement-between-scales test is not confirmed as run. Inputs are absent locally; current source availability was not checked. Official source for review: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). **Not family-novel or runnable now.** |
| **2 — Moderate prior; medium cost: magnetic-marker termination corroborated by an independent scarp** | GeoDAWN `rtp`/`tmi_hg` plus LiDAR `cross_max`, `upface_max`, `downface_max`, and `step_max`; identify a terminated or offset magnetic marker only where a separate narrow scarp supports it. | A buried structure can interrupt basement fabric while leaving a weak surface step, unlike a single-field lineament. It differs from E1's profile-lag across a gravity edge and from THVC's local tilt/dip-shift channels by testing marker termination plus independent geomorphic corroboration. | **Mimic:** intrusive contacts or airborne levelling seams. Related family outputs include `GEMSDOE45` KMTIP, `GEMSDOE70` magnetic/cover outputs, and `GEMSDOE77` demagnetization/gravity-step and magnetic/gravity-coherence outputs; exact marker-termination plus independent-scarp corroboration is unverified. The [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) is in the local source ledger, but the input stack is absent and this review did not fetch it. **Not family-novel or runnable now.** |
| **3 — Medium–high theoretical prior; high data cost: depth-persistent MT phase/resistivity step aligned with gravity basement edge** | DOE GDR 1391 magnetotelluric resistivity at multiple depths plus gravity/basement-depth gradients; target a lateral resistivity step that persists beneath a shallow conductive cap and aligns with a gravity edge. | This could target blind basin faults hidden from topographic mapping. It differs from THVC's shallow temperature/spring point features and its supplied conductivity bands. However, MT/clay-cap ideas already appear in sibling GEMSDOE artifacts, so any implementation would require a complete surface and final-dot registry comparison before it could be called distinct. | **Mimic:** evaporite brines or lithologic contacts. This is directly anticipated by the `GEMSDOE32` `h32c-mt-claycap-breach`, `GEMSDOE76` MT-breach, and `GEMSDOE77` `h77c-claycap-breach` sibling rasters. Official source for review: [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391). Required depth slices are not in `registry/data_manifest.json` or this checkout; no fresh download/access check was possible. **Not family-novel or viable until data bytes and provenance are verified.** |


The three remaining shortlist ideas were **not** validated in this review. Their ranks and expected-value language are qualitative judgments only, not HOLDOUT-DTI values or numeric performance projections. The current mainline also contains prior G79-CFSKD evidence (merged PR #79), which is relevant because its EXP3 used a visible-only Coulomb flank-shadow veto. Its reported **HOLDOUT-DTI** (`gems57-pooled-hide-v2`) was negative: seed 20 (`n=11,321`) `0.0654`, 95% CI `[0.0520, 0.0803]`; seed 30 (`n=11,342`) `0.0678`, 95% CI `[0.0561, 0.0816]` (`evidence/cfskd/holdout_results.json`). The CFSKD card's local uniqueness check covered only four archived rasters; it is not full-registry clearance and does not override the current literal-witness stop. These are prior mainline measurements, not a run from this review, not a projection, and not ORGANIZER-CONFIRMED scores. The exact Coulomb idea was therefore removed from the untried shortlist. The literal novelty preflight blocks before any new feature canary or holdout, and source data/caches for re-execution are absent; generating a raster first and checking it later would violate the stop rule.

## Limitations and next steps

1. **Protocol-owner decision is the primary blocker.** Resolve how continuous full-footprint registry rasters are converted to “dots,” with one prospective, symmetric rule applied to every prior. Do not locally cap, jitter, exempt, or retune to evade the present gate.
2. **Restore/verify science inputs.** Obtain the login-gated competition files through an authorized route or reproduce the pinned public-mirror inputs while preserving the source caveat; verify bytes and explicit file presence. Rebuild required caches only after a new lane is prospectively registered.
3. **Address the `numpy.roll` edge behavior** only in a prospectively authorized, test-covered pipeline; then rerun the feature canary, shared spatial holdout, and both novelty checks before any selector action. Do not patch a closed lane or reuse its prior scores for changed code.
4. **Update external-source status only via permitted access.** Links below are for manual review; this session did not live-fetch DrivenData, USGS, or DOE GDR pages. The stored source ledger is dated `2026-10-22`.
5. **No organizer access was used.** Eligibility, current weekly capacity, submission receipt, and an ORGANIZER-CONFIRMED score remain unknown. No login bypass, slot selection, or upload was attempted.

## Manual-review sources

- [DrivenData problem, submission format, and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData about page and scoring rounds](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Official GEMS reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI `10.5066/P93LGLVQ`
- [DOE GDR / INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391), DOI `10.15121/1881483`
- [EPSG:32611](https://epsg.io/32611)
- Local claim/provenance ledger: [`knowledge/official_sources.json`](../knowledge/official_sources.json); local data pins and mirror caveats: [`registry/data_manifest.json`](../registry/data_manifest.json).

## Session JSON card

The machine-readable negative review card is [`evidence/session_review_78ff8e7b.json`](../evidence/session_review_78ff8e7b.json). It explicitly separates this session's **NOT RUN** holdout from the prior canonical G79-THVC HOLDOUT-DTI measurements and carries the existing artifact's validator and download-only status.
