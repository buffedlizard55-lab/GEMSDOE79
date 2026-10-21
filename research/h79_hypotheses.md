# H79 hypothesis register (written BEFORE any experiment; 2026-10-21)

Context that constrains every hypothesis (all reproduced from bytes or organizer-confirmed,
see `reports/why_02778.md`):

* The hidden labels are "any fault pixel not already captured by USGS/INGENIOUS", including new
  geometry of known systems (continuations, splays, parallel strands) — organizer-confirmed.
* The live inversion of 95 scored rasters (GEMSDOE77, LOO Spearman +0.917) puts ≈38× hidden-truth
  enrichment on the H19-5 scarp-detector ridges > 2 km from the catalogue and ≈0 beyond the
  3-px halo of those ridges *on average*; geophysics-only lanes never exceeded 0.10 live.
* H19-5 is 90 % a 1 m-lidar / 10 m-DEM scarp detector (Openness–LRM, "anti-piedmont" steps),
  trained on the catalogue — the hidden truth is therefore, to first order, **lidar-visible scarps
  that an expert traced on a hillshade**.
* Every ≥ 0.26 live scorer is a re-dotting of H19-5; the uniqueness rule (≤ 70 % of dots within
  3 px of any prior) forbids another one.  The new lane must put ≥ 30 % of its dots on *other*
  evidence and still earn ≥ 0.06 credit per such dot to be net positive.

Ranking criterion: expected live-DTI gain × probability the mechanism is real ÷ cost.

| rank | id | hypothesis | layers / transform | why it catches faults missing from the catalogue | how it differs from the 90+ prior lanes | expected gain | cost |
|---|---|---|---|---|---|---|---|
| 1 | **H79-A Mapper-continuity scarp traces** | Experts trace *continuous* scarps; pixel detectors score *isolated* steps.  Score = pixel scarp likelihood × line-continuity (tubularity) of that likelihood, emitted as 3-px dots along reconstructed traces. | 1 m lidar cache (11 descriptors + strike), 10 m 3DEP (8 channels), 100 m det_elev(+slope); Sato ridge filter σ = 1–2 px on the strongest step descriptors (as features) and on the OOF likelihood (as the final continuity gate). | Unmapped scarps are typically subtler than mapped ones but *equally continuous*; continuity separates them from the dominant mimics (road cuts, terrace corners, mine benches), which are high-amplitude but short/blobby. Also works in the 25 % lidar gap through 10 m channels. | Prior lanes ranked pixels (H16/H19 Openness-LRM, 7G, 12G, gems66) or applied ad-hoc ridge thinning *after* ranking; none scored continuity of the evidence itself, and none enforced an off-H19-5 quota. | medium (+0.00…+0.03 live if ≥ 0.06 credit/off-halo dot) | low: all inputs cached; 1 model |
| 2 | H79-E Lidar-gap 10 m scarp detector | In the 24.7 % of the footprint without 1 m lidar, H19-5 falls back to quantile-matched 10 m channels; a model trained only in the gap with gap-specific descriptors should rank better there. | 10 m 3DEP channels only. | Gap areas are exactly where prior rasters are weakest, so hidden faults there are "cheap". | Prior gap treatment was quantile matching of a lidar model, not a gap-native model. | small-medium | low — **folded into H79-A** (model sees `lid_valid`, learns gap behaviour) |
| 3 | H79-B Hanging-wall piedmont strands | Range-front faults have basinward parallel strands 0.4–3 km into the piedmont (young alluvial scarps, low relief). | 1 m lidar step/openness restricted to a basinward band of catalogue range-front faults, strike-parallel. | Organizer counts parallel strands as new. | H77H "piedmont relay" tried a related idea (negative, ≤ 0.15 holdout). | small | medium |
| 4 | H79-D Along-strike tip extrapolation | Mapped traces end where the mapper stopped; continuation exists 0.5–2 km beyond tips where lidar still shows steps. | tip detection + oriented search cone + scarp likelihood. | Organizer counts continuations as new. | h32-1 / h33 / GEMSDOE27 gap-closure all ≤ 0.2649 live; "tip" lanes are exhausted. | ~0 | low |
| 5 | H79-C Lahontan shoreline de-confounder | Pluvial Lake Lahontan shorelines (≈ 1,330–1,340 m highstand) are the most fault-like non-fault steps in the lidar; removing scarps that follow a constant absolute elevation would raise precision. | absolute elevation (NOT available: `det_elev` is detrended; cache has no DEM heights). | precision, not recall. | 62G "datum-lahontan" scored 0.0000 (implementation failure, not a test of the idea). | small | **blocked** — needs USGS 3DEP 10 m DEM download (free, official: https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5 ; not reachable from this sandbox) |

## Decision

Validate **H79-A** (with H79-E folded in) on the spatially-blocked hide-and-recover holdout
before anything is written to `docs/downloads/`.  Named non-fault mimic processes the lane
must be judged against: pluvial shorelines (Lahontan), fluvial terrace risers, roads/canals/
railway grades, lithologic benches, mine benches and landslide head-scarps.

Pre-registered arms, budgets and gates are in `registry/preregistration_h79.json`.
