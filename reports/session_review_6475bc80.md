# Repository review — Arena session `6475bc80` (2026-10-22)

## Executive decision

**No new TIFF was generated; no competition slot was used.** The requested unique submission cannot be made while following the user's unchanged literal uniqueness rule: fresh preflight exit 2 establishes a pinned registry witness covering 100% of allowed cells, so any nonempty raster has literal forward 3-px overlap 1.0, above the 0.70 limit. The required single method paragraph is absent, and the current checkout has 0/13 pinned raw inputs present. The inherited G79-THVC raster is downloadable **for research only**, not approved to submit; it independently fails the official R6 exterior-null check. The earlier portal error is not diagnosed because the rejected file and receipt are unavailable.

- **New candidate:** none; no new filename, note, TIFF, or raster SHA-256 exists.
- **Inherited download:** `OK TO DOWNLOAD: YES (research only); OK TO SUBMIT: NO`.
- **Competition slots / scientific experiments:** 0 / 0.
- **Final card:** [`evidence/run_card_6475bc80.json`](../evidence/run_card_6475bc80.json).
- **Fresh preflight:** [`evidence/preflight_6475bc80.json`](../evidence/preflight_6475bc80.json).
- **Conditional, deduplicated hypotheses:** [`research/hypotheses_6475bc80.md`](../research/hypotheses_6475bc80.md).

## Pass 1 — repository and primary-evidence review

1. Read the repository start-of-session contract, the entire README including its embedded verbatim prompt, canonical `run_card.json`, current review `a201fa92`, irregularities ledger and the required preregistrations. Worked only on `arena/6475bc80-gemsdoe79`.
2. Confirmed the supplied prompt has no delimited single-method paragraph after the parallel protocol. No lane was invented or restarted.
3. Re-ran `.venv/bin/python scripts/preflight_new_lane.py --restore --report evidence/preflight_6475bc80.json`. **Exit 2: `impossible_under_literal_gate`**, witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, allowed-cell coverage `1.0`, limit `0.70`. This is a mathematical pre-placement stop, not a measured candidate correlation or experiment. No candidate surface, holdout, placement, or output raster was created.
4. Re-ran `.venv/bin/python scripts/data_status.py`: **0/13 current runtime inputs** under `data/raw`; training-supervision and core-pipeline inputs are not ready. The historical restore receipt is explicitly not current-presence evidence. I did not download hundreds of megabytes of data because the scientific lane is blocked before training or holdout.
5. Independently ran the official-text validator on the sample and inherited artifact. The official sample template **passes R1–R8**. The inherited G79-THVC research GeoTIFF **fails R6**: all 7,111,787 cells outside the sample bounds are finite zero, while the official requirement is null/NaN. Its existing inside-footprint values are finite and in [0,1] with matching CRS/grid/transform; that is not sufficient for official format pass or submission approval.
6. Reviewed the official source links recorded in the repository: [DrivenData problem/features/metric/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), [USGS heat-flow metadata](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28), and [DOE competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf). Links are provided for review; no new external data binary was acquired or independently certified in this turn.
7. Audited the proposed shortlist against source files. Existing work already covers multiscale scarp/curvature, fault tips/relays, RTP×gravity junctions, geothermal-point proximity and bajada knickpoint proxies. The five ideas in the session shortlist are therefore narrowly distinct extensions, not asserted discoveries. Ideas requiring new official DEM, tensor, chemistry, or heat-flow data are explicitly marked not viable until their exact product/schema and availability are verified.

## H33 `0.2778`: defensible interpretation and limits

The user-reported `0.2778` is **not an artifact-linked ORGANIZER-CONFIRMED result**. Existing byte forensics establish that the H33 raster contains 37,654 positives and is the 44,090-pixel D2.8 field after deleting 6,436 pixels within 2 pixels of the mapped catalogue. The GEMSDOE32 page is reported in the repository evidence as labelling the artifact **UNSCORED** and describing its score as a projection. Separately, the same-day public leaderboard observation lists a `0.2778` score at rank 52; this does not establish that the artifact generated that entry.

A plausible metric mechanism is reduced redundant prediction cost: under the official weighted Tversky/triangular-credit metric, a truth pixel receives at most its best nearby prediction credit while false-positive costs accumulate. Removing a redundant off-catalogue prediction can improve the ratio if it costs false positives without removing useful truth credit. But the deleted pixels were near mapped faults, not all exact catalogue pixels; they could also have recovered unseen faults. Hidden true positives and false-positive contributions for those specific pixels are unavailable, so **the mechanism is conditional, not proof of the cause of a score**. See [`knowledge/h33_review_e4a4422d.md`](../knowledge/h33_review_e4a4422d.md) and the byte receipt [`evidence/review_e4a4422d/h33_remeasurement.json`](../evidence/review_e4a4422d/h33_remeasurement.json).

`0.3195` remains an unverified user-reported figure; repository-captured public leaderboard evidence places the leader at `0.4413` on 2026-10-22. Neither is a score for a candidate made in this review. This session claims no projection or leaderboard improvement.

## Pass 2 — correctness, risk, and hypothesis review

- Confirmed that the shared preflight fails closed and does not authorize a test run. No local novelty amendment, density cap, dot jitter, or selector bypass was used.
- Confirmed current raw input absence separately from old restore receipts. Mirror hash pins do not authenticate organizer provenance or imply current availability.
- Preserved the official R6 failure separately from finite in-range values; this prevents the same file from being described as unconditionally submission-valid.
- Compared proposed ideas with existing code and records. The highest-ranked saddle-crossing idea is not implemented in the source search, but it remains only a proposal; absence of an implementation is not evidence of efficacy.
- Did not produce a new TIFF merely to satisfy a filename requirement. It would necessarily be a duplicate under the literal preflight and would fail the user's own gate.
- No evidence identifies the cause of the earlier portal error `Predicted values must be in range [0, 1]`: the rejected bytes and submission-page receipt were not supplied. No cause is guessed.
- Found stale site content that still presented a92/a201 as current, and a site rebuild removed the tracked historical TIPSTEP page while its old prose made an unsupported claim about the prior portal range error. Updated the generator to publish this review's preflight, run card, review report, and hypothesis shortlist while retaining older audits as provenance; preserved the TIPSTEP page as historical, corrected its R6/novelty warnings and unknown portal-error cause, and added a regression guard.
- The first full test run exposed three stale link/site assertions. Corrected the broken README link and changed the site assertion to check the current session page rather than a superseded 0d90 backlog. Targeted regression tests then passed.

## Integration note — concurrent upstream main advanced during PR review

After this review's initial commit, `origin/main` advanced through merged PR #144 (`G79-CSHD`). That separate lane archived two newly generated CSHD research GeoTIFFs (including an R1–R8 NaN-exterior variant) and reported separate `gems57-pooled-hide-v2` HOLDOUT-DTI measurements. Those artifacts and results are from session `e8afe252`, not this review. The CSHD lane's own full novelty checks still failed against 16/1,209 legacy corridor rasters and the literal universal witness, so its verdict remains negative and it is **not approved to submit**. This integration does not change this review's no-experiment/no-new-TIFF card; the canonical THVC card and decision remain unchanged. The site is regenerated from the merged main code and this review is explicitly linked as a distinct, later review.

## Pass 3 — final regression and deliverable verification

- After merging the concurrent upstream update, full test suite: **637 passed** (`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q`).
- Final site rebuild: **17 pages**; canonical status remains **OK TO DOWNLOAD: YES (inherited research artifact), OK TO SUBMIT: NO**.
- `scripts/verify_project.py`: all checks passed, including canonical file/card hash, strict official format, shared-template pins, historical holdout receipts, selector refusal, README publication contract, and the single-canonical-publication-artifact rule.
- `scripts/check_site.py`: PASS; **509 local links checked**, all pages reachable, scientific tables/gates reconciled, `submit: false`.
- Browser download-check tests: **12 passed**; matching a published file never approves submission.
- Official-text validator: sample template PASS; archived CSHD NaN-exterior TIFF and ZIP PASS R1–R8; inherited THVC TIFF FAIL R6 (7,111,787 non-NaN exterior cells). CSHD remains DO-NOT-SUBMIT because its separate full novelty gate is negative.
- Fresh preflight: exit 2, expected stop; runtime checker: 0/13, exit 2, current raw inputs missing.
- No canary, holdout, score, raster creation, upload, or slot was performed. Candidate score/count/CI/raster fields are null or explicitly NOT MEASURED rather than fabricated.