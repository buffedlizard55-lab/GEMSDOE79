# G79-TIPSTEP session — ranked candidate hypotheses (generated before the experiment)

Data reality checked first: `python scripts/data_status.py` = 0/13 manifest inputs in
`data/raw`; only `data/reference/{existing_faults,sample_submission}.tif` are present.
Any hypothesis needing GeoDAWN/DEM/geophysics bands is therefore NOT executable in this
checkout without restoring hash-pinned inputs (registry/data_manifest.json).

| Rank | Hypothesis | Layers / signature | Why a catalogue-missing fault | Difference from repo lanes | Cost / expected |
|---|---|---|---|---|---|
| 1 (tested) | **Tip-extension + collinear stepover bridging (G79-TIPSTEP)** | Catalogue geometry only: tip PCA strike, rays ≤60 px, bridges 6–45 px between different components, dotted 3 px, >2 px off catalogue | Faults continue beyond mapped tips; en-échelon stepovers are often unmapped between mapped segments | Prior lanes used geophysics/DEM surfaces + submodular cover; none emitted pure catalogue-geometry rays/bridges as the sole mechanism | Low cost; tested: HOLDOUT-DTI 0.0927/0.0928, below incumbent → negative |
| 2 | Conjugate-strike Riedel accommodation zones | Visible-fault orientation-transition polygons × RTP/gravity (needs training_features.tif restore) | Short oblique transfer faults simplified away in regional compilations | Regional fabric-transition, not endpoint cones (prior: hypotheses_1f9d2dc9 rank 1) | Moderate; blocked on data restore |
| 3 | Multi-drainage knickpoint collinearity at fan apices | Absolute DEM (USGS 3DEP https://www.usgs.gov/3d-elevation-program) channel-profile curvature × independent catchments | Low-slip piedmont faults with reworked scarps still break channel profiles | Cross-catchment topology, not local scarp pixels | High; needs 3DEP coverage check |
| 4 | Relief-screened structural saddle × crossing gravity gradient | Detrended elevation Hessian saddles × isostatic gravity gradient (needs restore) | Low-relief transfer zones missed by range-front-dominated mapping | Catalogue-independent terrain topology + independent potential field | Moderate; blocked on data restore |
| 5 | Paired well/spring geothermometer disequilibrium up-gradient | INGENIOUS tables (DOI 10.15121/1881483, https://gdr.openei.org/submissions/1391) + hydrologic up-gradient paths | Fluid upflow along buried structures with weak surface trace | Paired chemistry residuals + transport direction, not spring proximity | High QA; sparse clustered points |

Mimic for #1 (named non-fault process): catalogue digitisation fragmentation and
roads/drainage lineaments. Falsifier used: uniform same-budget control and whole-component
buffered holdout (gems57-pooled-hide-v2, seeds 20/30).

## Why H33 (0.2778, unverified historical report) plausibly scored high — and why we cannot claim to beat it
Repo remeasurement (docs/index.html §02, evidence/h33_remeasurement.json): H33 = D2.8 dotted
map minus 6,436 px within 2 px of the catalogue. Under DTI (α=0.2 FP, β=0.8 FN, 300 m max-cover
kernel), redundant near-catalogue dots add FP cost without TP gain; removing them can raise the
organiser score IF the hidden truth is not there. That is conditional algebra, not proof of
hidden-truth location, and 0.4413 is another entrant's public-leaderboard value. TIPSTEP adopts
the two transferable, verifiable parts (dotted spacing, >2 px catalogue exclusion) and adds a
new mechanism (tip/stepover geometry). Its holdout (0.093) is honest evidence it is NOT, on
catalogue geometry alone, an incumbent-beater; no leaderboard projection is made.
