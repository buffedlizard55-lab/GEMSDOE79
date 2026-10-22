# Session review — `a92a0164` (2026-10-22)

## Decision summary

**Blocked before candidate generation.** `evidence/preflight_a92a0164.json` was run with the repository's pinned registry inputs and literal overlap rule. Its hash-verified witness covers `1.0000` of allowed cells, giving any non-empty candidate a lower-bound 3-pixel forward overlap of `1.0000`, above the `0.70` gate. The preflight exits 2 and records `start_new_lane:false`. I did not exclude the witness, redefine the rule, or continue to surface construction.

Therefore this session produced **no experiment, leakage canary, holdout, surface/dot placement, candidate raster, validator result, submission, selector action, or new downloadable TIFF**. No weekly slot was used. The inherited research TIFF remains available through the [download guide](../docs/executive-summary.html), labeled **DO NOT SUBMIT**; it is not new work and its format receipt is not organizer approval. No higher leaderboard result is forecast or promised.

The checkout has only reference rasters and a historical restore receipt; `data/raw/` and the local training-feature raster are absent. The absence of training data is a separate limitation, not a reason to override the preflight. See the [source/availability receipt](../evidence/source_review_a92a0164.json) and [run card](../evidence/run_card_a92a0164.json).

## Pass 1 — protocol, preflight, and local data

- Read the full project brief in `README.md` and the canonical `AGENTS.md`, run card, preregistrations, source ledgers, and irregularity register.
- Re-ran `scripts/preflight_new_lane.py --restore --report evidence/preflight_a92a0164.json`. Result: `impossible_under_literal_gate`, exit 2, `start_new_lane:false`; the pinned witness SHA-256 is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`.
- Confirmed no local `data/raw/` training stack. No candidate-specific validation path was entered. Whole-segment buffered holdout, visible-only catalogue features, exact visible-fault masking, pooled DTI (α 0.2, β 0.8, 300 m triangular kernel), feature-alone leakage canaries, novelty-before-placement/final-dot checks, and the 3-experiment/2-hour budget remain future protocol requirements—not actions claimed for this blocked session.
- No selector/slot operation occurred; a future real slot remains separate selector work.

**Pass 1 result: PASS — fail-closed stop preserved; no candidate work started.**

## Pass 2 — ranked backlog, official-source checks, and score evidence

Four related proposal families were deduplicated and ranked in [the current backlog](../research/hypotheses_a92a0164.md). They are **qualitatively prioritized, genuinely unexecuted as scoped in this repository, and not represented as globally novel**. No numeric DTI projection is made.

| Rank | Hypothesis and signature | Why it is different / untried here | Main non-fault mimic | Official source check; cost |
|---:|---|---|---|---|
| 1 | Event-level ComCat earthquake lineation plus focal-plane/temporal coherence, cross-checked with existing magnetic/gravity structure. | Goes beyond the previously used smoothed earthquake-density bands; no event-feature or mechanism-coherence lane/holdout was found. Could identify blind subsurface strands not represented in a surface-rupture catalogue. | Quarry blasts, induced geothermal events, aftershock clouds. | [USGS ComCat](https://earthquake.usgs.gov/fdsnws/event/1/): sample-area count query returned 5,886 M≥2.5 events and 2,249 focal-mechanism-product records; no bulk ingest or mechanism parsing. Medium cost. |
| 2 | Gravity-supported magnetic decoupling: a persistent density/contact gradient where a regularized magnetic edge weakens or is interrupted. | Existing repository work includes potential-field edges/junctions, not this narrow discordant signature. Regional USGS studies are method analogies, not target-area proof. | Nonmagnetic lithologic contacts, basin fill, flight-line seams. | [USGS Amargosa report](https://pubs.usgs.gov/of/2000/of00-188/of00-188.pdf) and [Professional Paper 1652-D2](https://pubs.usgs.gov/pp/2004/1652/pdf/508/ChapD2508.pdf), reviewed as regional/method context; no new binary needed. Low-to-medium incremental cost after data restoration. |
| 3 | Paired signed residuals in USGS Great Basin heat flow, aligned with independent structure after conductive-background and quality control. | Unlike existing radial kernels around known springs/probes; no local source ZIP or executed residual-pair holdout was found. | Groundwater circulation, pumping, shallow correction error, clustered sampling. | [USGS ScienceBase item](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28), DOI `10.5066/P9BZPVUC`: official item JSON exposes a public download URI and lists a 130,154,244-byte ZIP (124.12 MiB) plus an advertised MD5. The archive was not transferred, so its bytes, schema, and target coverage remain unvalidated. High cost. |
| 4 | Multi-temporal Sentinel-1 IW SLC interferometry for a persistent LOS-deformation discontinuity, checked against ascending/descending tracks and independent geophysics. | No SLC bytes, interferogram, time series, or holdout receipt was found in this checkout; distinct from single-scene amplitude. | Groundwater subsidence, seasonal moisture, landslides, atmospheric delay. | [Copernicus SLC STAC](https://stac.dataspace.copernicus.eu/v1/collections/sentinel-1-slc) returned five metadata items for the sample bbox/date query. Terms describe free/open data, but registration and generated credentials are required for S3 access. A metadata hit does not prove full-footprint temporal coverage; no asset was downloaded. Very high cost. |

Other official checks are preserved in the [source review](../evidence/source_review_a92a0164.json), including the official task metric, staff's clarification that a new pixel may be an extension/splay/parallel strand (so proximity alone is not invalid), USGS QFaults scope, DOE GDR-1391 listing, and UNR MIDAS response samples. Remote counts, listings, and metadata are not locally acquired feature data. The direct shell HTTP probe failures remain separately recorded in the source-health feed; they do not convert the research-fetch reads into successful shell probes.

### H33 and leaderboard evidence boundary

- H33 `0.2778` is an **unverified historical user report**. No organizer submission-page receipt links it to the H33 bytes. The H33 geometry audit shows 37,654 positive pixels, a subset of D2.8's 44,090, with 6,436 pixels removed by the stated `d_cat <= 2 px` thinning. Those byte counts neither establish hidden truth nor prove that thinning caused a score change.
- The separate **public leaderboard observation** fetched on 2026-10-22 showed rank 1 `xiaofanhu = 0.4413` and rank 50 `arnofault = 0.2817`. These are not this repository's score and not submission-page receipts.
- `0.3195` remains an older user-reported benchmark, not the current public leader and not independently verified here.
- The earlier same-day public snapshot with rank 50 `sam35 = 0.2804` is preserved as historical and explicitly superseded for current-board reporting. No causal link is implied by the matching H33 number seen in an earlier board snapshot.

The corrected [H33 analysis](../research/h33_analysis.md) and supersession note in `knowledge/why_h33.md` withdraw unsupported causal claims. Only an artifact-linked organizer submission-page receipt may be called `ORGANIZER-CONFIRMED`; any future local score must be labeled `HOLDOUT-DTI` with evaluator, withheld-positive count, and 95% CI.

**Pass 2 result: PASS — proposals are ranked with layer/signature, mechanism, mimic, repo-difference, source status, and cost; evidence classes are kept separate.**

## Pass 3 — documentation, site, and verification

- Preserved the full project prompt in `README.md`, updated its current status/links, and made the inherited TIFF's download-only / do-not-submit decision explicit. The decision guide now says this session made no TIFF.
- Rebuilt the static site: **11 pages**, `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` The site check passed: **269 local links**, every page reachable from home, no external assets, and submit remains false.
- The current H33 explanation explicitly separates the unverified `0.2778` report, rank-1 public observation `0.4413`, and older user-reported `0.3195`. Superseded full narratives and speculative old hypothesis notes are linked as historical source files rather than rendered as current advice.
- Added tests for public top-50 parsing, the fail-closed session card, and stale-vs-current leaderboard snapshots. Full test suite: **562 passed**. `scripts/build_site.py` and `scripts/refresh_feed.py` compile successfully.
- Rechecked the report and run card against the no-candidate state; no TIFF hash, holdout score, submission name/note, validator pass, selector receipt, or slot was invented.

**Pass 3 result: PASS — site, evidence labels, code checks, and tests agree with the blocked/no-candidate decision.**

## Limitations and next work

1. The current pinned literal-overlap witness blocks all non-empty candidates. Resolve the shared rule prospectively through the authorized process; do not bypass it in a local experiment.
2. Restore and checksum the absent official training stack only if work is authorized; restoration by itself does not clear novelty.
3. Before any future eligible lane, preregister a single test, freeze non-fault mimics, reuse cached features and shared evaluator/writer, hide full fault segments with a buffer, build catalogue features from visible faults only, mask visible fault pixels exactly, and run leakage canaries (AUC > 0.90 blocks trust).
4. Check surface novelty before placement, then final-dot novelty. Stop on a duplicate or overlap-gate failure. Maximum three experiments or two hours; no slot is implied.
5. Acquire/hash/audit official external data before use. In particular, ComCat counts are not parsed focal mechanisms, ScienceBase's ZIP listing is not a dataset acquisition, Copernicus STAC metadata is not a processed time series, and MIDAS samples are not a coverage audit.
6. Make no score forecast from geological plausibility. Report all valid local outcomes as `HOLDOUT-DTI` with evaluator version, withheld count and CI; use `ORGANIZER-CONFIRMED` only with a submission-page receipt.

## Review artifacts

- [Full preserved project prompt and current decision](../README.md)
- [Fail-closed preflight](../evidence/preflight_a92a0164.json)
- [Session run card](../evidence/run_card_a92a0164.json)
- [Source and availability review](../evidence/source_review_a92a0164.json)
- [Four ranked hypotheses](../research/hypotheses_a92a0164.md)
- [H33 evidence analysis](../research/h33_analysis.md)
- [Official-source ledger](../knowledge/official_sources.json)
- [Current website](../docs/index.html)
