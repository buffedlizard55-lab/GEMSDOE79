# Candidate geological hypotheses not yet tried in GEMSDOE79 — ranked (2026-10-22)

Scope checked before ranking: all 17 stopped GEMSDOE79 lanes in `AGENTS.md`,
every `registry/preregistration*.json` in this repo, the THVC 84-channel stack
(`src/gems79/thvc_features.py`, `thvc_model.py`), and the scored sibling names in
`registry/score_ledger.csv` / `knowledge/why_h33.md`. A candidate below is only
listed if its *transform* is absent from that inventory (grep for
pseudogravity / conjugate / spring-alignment / knickpoint-collinearity /
detection-bias terms returned no lane; geodesic tip-linking was found in
GEMSDOE69 `h69-efg-kinematic-geodesic` and is therefore excluded).

Promotion bar (project protocol): a candidate may not spend a weekly slot unless
it beats the current holdout best, G79-THVC `HOLDOUT-DTI = 0.1905` (seed 20,
n=11,321) and `0.1944` (seed 30, n=11,342), evaluator `gems57-pooled-hide-v2`.

## Rank 1 — G79-CONJ: cross-strike conjugate-strand completion (SELECTED)

- **Layers:** visible catalogue geometry only (`existing_faults.tif` fold-visible
  mask) + `depth_to_base_surf` (training_features band 15) for throw sense;
  evidence corroboration comes from the existing THVC static stack (lidar scarp,
  gravity/magnetic derivatives) inside the learner.
- **Physical signature / transform:** for every cell, decompose the offset to its
  nearest visible fault pixel into along-strike `d_par` and cross-strike
  `d_perp` using the shared `gems57.network` strike frame, then score
  strike-parallel *offset ridges* at fixed spacings (0.5 / 1.1 / 2.2 km),
  separated by hanging-wall vs footwall side (side where basement deepens =
  downthrown), plus a length-scaled damage-zone offset
  `exp(-d_perp / (0.35 L + 3px))` where `L` is the anchor segment length
  (displacement–length scaling), junction proximity and trace-bend proximity.
- **Why it catches catalogue-missing faults:** regional compilations draw the
  master range-front trace; secondary synthetic/antithetic strands in the
  hanging-wall alluvium are shorter, lower-throw and routinely omitted, yet they
  sit at characteristic cross-strike offsets from the master strand. THVC's
  network mechanics are *along-strike* (tip cones, bridges, relays) and its
  distance features are isotropic — no prior lane encodes side-specific
  cross-strike offset loci.
- **Named non-fault mimic:** Pleistocene Lake Lahontan shoreline benches, which
  are also strike-parallel lines offset from range fronts. The learner must use
  scarp step sign / elevation context to separate them; the canary and ablation
  arms expose failure.
- **Expected DTI effect / cost:** highest of the five on hide-and-recover
  (withheld segments include parallel splays the isotropic model ranks by
  distance alone); cost low-medium (EDT + segment table per fold, reuses the
  cached 70-channel static stack and shared evaluator/writer).

## Rank 2 — Poisson pseudogravity discordance ridges

- **Layers:** `rtp`, `iso_grav_anom` (training_features).
- **Transform:** FFT pseudogravity of RTP (Poisson relation, incl./decl.
  corrected), robust local regression against isostatic gravity in 2.1 km
  windows; discordance = `(1 - local r) x |gradient of residual|`.
- **Why missing faults:** a buried fault juxtaposes blocks whose
  density:magnetization ratios differ, so the two fields' edges are offset or
  unpaired even where neither field alone shows a clean ridge and no scarp
  exists under basin fill. FABRIC-OFFSET tested profile *lag* across single
  gravity edges (HOLDOUT-DTI 0.0441 as control C1); field-level Poisson
  discordance is a different operator, but the family resemblance and that weak
  control result lower its prior.
- **Cost:** low (FFT). **Risk:** magnetization-direction assumptions; volcanic
  centres mimic discordance.

## Rank 3 — Thermal spring / vent collinearity (point-alignment lines)

- **Layers:** pinned `gdr_wellspring_in_footprint.csv` (27,092 rows; temperature
  and geothermometry columns; the leakage column `dist_known_fault_px` must be
  blocked at ingestion, as THVC does).
- **Transform:** RANSAC/Hough alignments of >=3 hot points (temp-weighted)
  within a 300 m corridor over 2–10 km, rasterized as line corridors — as
  opposed to THVC's isotropic KDE smoothing of the same points.
- **Why missing faults:** upflow localizes on permeable fault intersections;
  aligned springs can trace a blind fault with no scarp and no potential-field
  edge. **Limit:** sparse coverage — cannot fill a ~37k-dot budget alone;
  viable only as auxiliary channels. Cost low, expected pooled-DTI gain small.

## Rank 4 — Cross-drainage knickpoint collinearity

- **Layers:** pinned USGS 3DEP `dem10_chi_100m_i16.tif` chi/ksn cache.
- **Transform:** for each cell, the maximum over strike angles of chi-step mass
  summed along parallel lines offset across several adjacent drainages
  (aligned knickpoints), instead of THVC's per-pixel `chi_step_max`.
- **Why missing faults:** a young fault crossing multiple catchments stamps a
  *line* of knickpoints at a common structural position; single-drainage
  knickpoints are usually lithologic. **Cost:** medium; signal restricted to
  bedrock ranges where catalogue completeness is already better.

## Rank 5 — Mapping-effort (detection-bias) correction — REJECTED for this gate

- **Layers:** lidar presence, TIGER road distance, relief/slope.
- **Transform:** Horvitz–Thompson style reweighting `score / P(mapped | fault,
  effort)`. Scientifically aimed exactly at *unmapped* faults, but the
  hide-and-recover holdout hides segments independently of mapping effort, so
  the correction is expected to *hurt* HOLDOUT-DTI while possibly helping the
  organizer score. Under the stated promotion gate it cannot be validated
  honestly with the available instrument; parked, not implemented.

## Data-availability check (all inputs already pinned, no new external data)

- `training_features.tif` sha256 `4371c82e…`, `existing_faults.tif` /
  `labels.tif` sha256 `7ba308cc…`, `sample_submission.tif` sha256 `2176d08e…`
  restored and hash-verified 2026-10-22 (`scripts/restore_data.py
  --preserve-receipt`, 13 files). Origin: DrivenData competition 306 data page
  (login-walled; owner mirrors only prove mirror consistency, not organizer
  authentication) — https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- DOE GDR 1391 INGENIOUS + USGS 3DEP caches restored and hash-verified
  (`scripts/restore_official_ingenious.py`, 5 files) —
  https://gdr.openei.org/submissions/1391 (DOI 10.15121/1881483),
  https://www.usgs.gov/3d-elevation-program
- No candidate above needs any other external source.
