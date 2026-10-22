# Geothermal vent discovery — official sources and scope for fault mapping

**Question asked by the competition:** predict where a **hidden fault** is likely to be, as mapped by experts and missing from the USGS/INGENIOUS catalogue. This is **structural favourability**, not proof of a hot, permeable, or economic vent/reservoir. The three are logically distinct.

## What a vent needs beyond a fault

1. **Heat** — high temperature gradient or heat flow anomaly.
2. **Permeability** — open fracture network or porous horizon that can transmit fluid.
3. **Structure** — a fault or intersection that provides a conduit or trap, often at a stepover, relay, or tip.

Only (3) is scored by DTI. A good fault map is necessary but not sufficient for a producing vent. Conflating a favourable lineament with a vent is a category error the site explicitly avoids (“Fault-mapping research, not proof of geothermal resources”).

## Official, verified, free sources that define the problem

All links below were fetched and quoted line-by-line for manual review; no claim is made from a page that failed to load in the sandbox.

### 1. Organizer problem and metric

- **DrivenData competition 306, page 967** — [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) (read 2026-10-21, every paragraph). Defines hidden test faults as new expert-mapped faults absent from the public database, and the Distance-Weighted Tversky metric (`k(d)=max(1−d/300 m,0)`, `TP = Σ_truth max_x p·k(d)`, `FP = Σ_x p·(1−max_truth k)`, `FN = N−TP`, `DTI = TP/(TP+0.2·FP+0.8·FN)`, pooled over chunks). The challenge is fault discovery.
- **About page** — [page 968](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/) (read 2026-10-21). Lists additional context, including the GeoDAWN release.
- **Data page** — [Data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (verified redirect to login). Confirms training features, labels and sample submission exist behind auth; mirrors are owner GitHub copies hash-pinned in `registry/data_manifest.json` and not organizer-authenticated.
- **Leaderboard** — [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (read 2026-10-22). Public leader observed as `xiaofanhu 0.4413` — a team score, not a file/score receipt. Historic family reports (e.g., H33 0.2778) have no organizer receipt in this repo and remain UNVERIFIED HISTORICAL REPORTS.
- **Organizer clarifications** — [known faults masked](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) (exact catalogue pixels only, not a buffer) and [pooled aggregation](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2).
- **Rules** — [DOE/NLR FY26OSTI 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (read in chunks, including end). Up to three submissions per week, final selection must be made without private-test knowledge, AI disclosure required, finalists must provide reproducible code.
- **Reference solution** — [gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) (README/notebook retrieved via API). U-Net + MC CV + Tversky loss; CPU is supported. Baseline only, not evidence of this repo's score.

### 2. Geophysical basis — what the supplied bands actually are

- **USGS GeoDAWN airborne magnetics & radiometrics, Area 2, northwestern Great Basin** — [data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) (full scientific description read). Flight-line spacing 400 m, tie-line 4000 m; grids at 100 m do not imply independent 100 m observations; processing includes tie-line levelling and micro-levelling; variable terrain clearance affects interpretation. Lists grids, CSV line data, flight-path shapefiles and processing reports as products. Source of `rtp`, `tmi`, `geodawn_rad_u8` bands.
- **USGS Regional geophysics of the Great Basin (Glen et al., 2022)** — [P9Z6SA1Z](https://doi.org/10.5066/P9Z6SA1Z) (release description read). Lists regional gravity, magnetic and depth-to-basement compilations — the family of `iso_grav_anom`, `depth_to_base_surf` etc.
- **USGS 3DEP Elevation Program** — [3DEP](https://www.usgs.gov/3d-elevation-program) and lidar product [ScienceBase 4f70aa9fe4b058caae3f8de5](https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5) (the scheduled GitHub Actions job can fetch 1 m tiles; this sandbox is allowlisted to `github.com`/`registry.npmjs.org`/`pypi.org` only, so direct 3DEP fetch is not observable here but is obtainable via Actions, as `7GEMSDOE` demonstrated).

### 3. Geological compilation — catalogue limits

- **INGENIOUS / GBCGE** — [current projects](https://gbcge.org/current-projects/ingenious/) (project description read). Integrates geophysical, geological, thermal and exploration data for hidden geothermal systems; INGENIOUS compilation and the USGS regional release are listed as related publications. Also [GDR 1391](https://gdr.openei.org/submissions/1391) (description read): 2 m probes, gravity/magnetics, heat flow, MT, faults, volcanic features, paleogeothermal features, well/spring chemistry — superseded by Quaternary Faults v2, not independent of the competition catalogue.

### 4. Metric and CRS details

- **EPSG:32611 (WGS 84 / UTM zone 11N)** — [epsg.io](https://epsg.io/32611) (CRS of every submission; shape 3730×3292, 100 m, transform `[100,0,243350,0,−100,4508550]` identical to `sample_submission.tif`).
- **Tversky index** — [Wikipedia](https://en.wikipedia.org/wiki/Tversky_index) (general definition; the competition weighting is α=0.2, β=0.8 as defined on page 967, not the Wikipedia default).

### 5. Primary literature read line-by-line (context, not scores)

- **Hermant, Kiersnowski & Bellanger, Stanford Geothermal Workshop 2025** — [Using Deep Learning to Map Quaternary Faults](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf) (all eight parsed chunks read). Uses elevation/slope + Sentinel-2 B8A at ~10 m; reports overfitting and explicitly names paleo-shorelines, canyon margins and streams as fault mimics (§6–7, Figs 8–9); distinguishes incomplete mapping from true absence (Fig 2). Metrics are PR-AUC / weighted focal IoU, not DTI; random tile split ≠ buffered whole-segment split. Qualitative figures do not transfer to pooled DTI.

## Why most vents are missed by the catalogue — and what actually generalizes

- The catalogue is demonstrably incomplete and heterogeneous (Hermant Fig 2; regional compilations truncated at map-sheet/cover boundaries). “No line on the map” ≠ “no fault”. A model that learns `p(fault | mapped)` rather than `p(fault missing | visible map + geophysics + scarps)` will simply reproduce known exposure.
- Basin-and-Range normal faults are multi-strand: synthetic/antithetic companions, relay stepovers and tip continuations typically 0.3–3 km from a mapped trace, often under Quaternary cover where lidar can still resolve a few-metre step. That multi-strand neighbourhood is exactly the band where the organizer's withheld-catalogue holdout concentrates truth, and where the family's dot fields already crowd.
- The dominant scarp mimics are **not** random noise: pluvial Lake Lahontan shorelines/terraces (highstand ~1330–1335 m, USGS Benson & Thompson 1987, Circular 1267), fluvial terrace risers, fan toes, road/canal grades, lithologic benches, mine benches, landslide sackung. Any detector that ranks purely by step amplitude will be dominated by these.

## What we therefore test — and what we explicitly do not claim

- **We test** structural lineament predictors that are measurable on the supplied grids (detrended elevation, gravity/RTP magnetics, lidar scarp dipoles, radiometric ratios) or on pinned mirrors (SGMC geology, TIGER roads) — always with the caveat that mirrored bytes are hash-consistent, not organizer-authenticated, and that 100 m grids do not manufacture independent 100 m airborne observations.
- **We do not claim** a scarp alone is a fault, that a magnetic lineament alone is permeable, or that a Tversky gain on withheld catalogue faults equals a gain on hidden expert faults (distribution shift, IR-79-51). Only an organizer score can speak to the latter.

## Data actually restored in this repo (hash-pinned, not organizer-authenticated)

From `registry/data_manifest.json` / `evidence/restore_receipt.json`: `training_features.tif` (19 bands, 418 MB), `existing_faults.tif`/`labels.tif`, `sample_submission.tif`, `external/lidar_scarp_features_u8.tif` (12 bands), `external/geodawn_rad_u8.tif`, `external/geodawn_extensions_u8.tif` (`geodawn_mag_u8` + derivatives), `external/derived_sgmc_faults_100m_u8.tif`, `external/tiger_road_distance_m.tif`, and GDR CSVs. Every `holdout_dti` number in `run_card.json` is produced by the shared evaluator `gems57-pooled-hide-v2` on buffered whole-component hides — not a projected leaderboard score.

## One-sentence check for any future submission

> Does this candidate rank a previously undotted piece of terrain — far-field or relay, not another near-fault collar — for a physical lineament that an expert would draw as a trace and that a non-fault process cannot mimic at the same scale and orientation?

If the answer is no, the DTI prior is to duplicate a family dot field and fail the gate, regardless of nominal model sophistication.

## Further reading (every entry in `knowledge/sources/` and `knowledge/prior_work/` is a line-by-line ledger)

- `knowledge/official_sources.json` — claim-by-claim ledger with live URLs and review dates.
- `knowledge/literature.md` — Stanford paper and regional geophysics notes.
- `knowledge/why_h33.md` — byte forensics of the best family raster.
- `research/hypotheses_*.md` — ranked, preregistered hypotheses and their mimics.
- `reports/nhr_analysis.md` — exact metric algebra and H33/NHR holdout comparison.
- `reports/irregularities.md` — IR-79-01…66, including the literal-witness blocker (IR-79-53) and its implications.
