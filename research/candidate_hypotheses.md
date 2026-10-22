# GEMSDOE79 — Candidate geological hypotheses (3–5, not yet tried)

This document proposes distinct geological hypotheses for generating a competition
submission that beats the current best verified reports (0.4413 leaderboard
observation; 0.2778 unverified H33 report; 0.3195 historical report). Each
hypothesis names: the specific layer(s), the physical signature targeted, why it
should catch faults missing from the USGS/INGENIOUS catalogue, how it differs
from anything in this repo, expected DTI improvement, implementation cost, and
the external data required.

Ranking is by expected DTI improvement per unit implementation cost. The top
candidate MUST be validated on a spatially-blocked holdout before any weekly
submission slot is used. No submission slot may be spent on an idea that has not
beaten the current holdout best.

Budget per the parallel-run protocol: stop after 3 experiments or 2 hours.

---

## H1 — Damage-zone distance decay from catalogue faults (G79-DZD) — IMPLEMENTED

**Layers:** USGS/INGENIOUS existing_faults catalogue (mapped Quaternary faults)
only; competition footprint mask from sample_submission.tif.

**Physical signature:** Fault damage-zone permeability — fracture-enhanced
permeability concentrates in the fractured rock *adjacent* to fault cores, not
on the mapped traces themselves. Geothermal fluids exploit damage zones where
fault-core sealing is bypassed. A Gaussian damage-zone score centred at an
optimal ~200 m cross-fault distance, decaying along strike, targets conduits
absent from the catalogue because they lie off mapped traces but within the
damage-zone envelope.

**Why it catches catalogue-missing faults:** Catalogue traces are the fault
cores. Unmapped splay faults, relay ramps and damage-zone fractures offset from
the trace produce geothermal permeability at a distance from the mapped line.
Distance-decay scoring finds them without needing to map each trace.

**Differs from repo:** G79-THVC uses an 84-channel multi-physics ML ensemble
(gravity, magnetics, shallow temperature, sinter, LiDAR scarps) with a kernel
cover allocator. G79-DZD is a single deterministic distance transform — no ML,
no multi-physics stack, no training data needed.

**Expected DTI improvement:** Modest standalone (damage zones are narrow). Best
as a prior or sparse seed in combination. Estimated holdout-DTI 0.08–0.14.

**Implementation cost:** Low (~1 hour; implemented as scripts/generate_unique_submission.py).

**External data required:** None beyond existing_faults.tif + sample_submission.tif (already in data/reference).

**Status:** Implemented. Locally format-valid, unique vs 36 local rasters
(max |ρ| = 0.0212, max overlap = 0.2456). Holdout-DTI unmeasurable offline
(training data login-gated).

---

## H2 — Shallow-temperature residual + radiometric potassium anomaly conjunction

**Layers:** DOE GDR submission 1391 (DOI: 10.15121/1881483) 2-m shallow
temperature probe residuals; GEODAWN airborne radiometric potassium (%K) from
the USGS northwestern Great Basin survey.

**Physical signature:** Blind geothermal systems leak heat to shallow
groundwater, producing positive shallow-temperature residuals above background.
Potassium enrichment in altered volcanic rocks (argillic/advanced argillic
alteration) co-locates with hydrothermal conduits. The *conjunction* (both
anomalies present) is specific: neither temperature residuals nor potassium
anomalies alone are diagnostic, but together they target blind hydrothermal
plumes with no surface fault expression.

**Why it catches catalogue-missing faults:** Blind geothermal systems may have
no surface fault scarp at all — heat and chemistry reach the surface through
diffuse flow or young faults not yet mapped. Temperature + K+ conjunction finds
them directly.

**Differs from repo:** No lane in this repo combines GDR shallow-temperature
residuals with GEODAWN radiometrics as a conjunction. G79-THVC used temperature
as one channel among 84 in an ML ensemble — not a two-variable conjunction
prior.

**Expected DTI improvement:** High if blind systems dominate missing faults.
Estimated holdout-DTI 0.12–0.18.

**Implementation cost:** Medium. Requires GDR 1391 temperature data (public,
free) and GEODAWN radiometric %K raster (USGS, public). Both named in the data
manifest but not cached locally.

**External data required:**
- GDR submission 1391: https://gdr.openei.org/submissions/1391 (free, public)
- GEODAWN radiometric survey: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (free, public)

**Viability check:** Both sources are free and official. Obtainability must be
confirmed by download before this hypothesis is ranked as actionable.

---

## H3 — Quaternary volcanic vent + sinter/travertine proximity with step-over dilation

**Layers:** GDR volcanic vent points (gdr_volcanic_vents_in_footprint.csv,
already in data manifest); USGS/INGENIOUS catalogue; derived step-over/dilation
zones from catalogue fault geometry.

**Physical signature:** Volcanic vents are magmatic heat sources; sinter/travertine
deposits mark fossil hot springs. Step-overs and dilational jogs between
en-echelon fault segments create localized dilation (volume increase) that
focuses geothermal upflow. Proximity to vents + sinter + dilation zones targets
active geothermal plumbing.

**Why it catches catalogue-missing faults:** Dilational step-overs are often
sub-resolution at 100 m and may not be individually mapped. Vent/sinter proximity
captures the heat source and surface expression without needing the exact fault
trace.

**Differs from repo:** G79-THVC mentioned "volcanic vent conduits" as one channel
among 84. No lane builds a dedicated vent+sinter+dilation proximity prior with
step-over geometry.

**Expected DTI improvement:** Medium-high in volcanic areas of the footprint.
Estimated holdout-DTI 0.10–0.16.

**Implementation cost:** Medium. Requires computing step-over polygons from
fault catalogue geometry and rasterizing vent/sinter proximity.

**External data required:** GDR volcanic vents (in manifest, not cached); Quaternary
sinter/travertine deposits (USGS/state geological maps, free).

---

## H4 — Moment tensor / focal mechanism consistency with catalogue strike

**Layers:** USGS/INGENIOUS catalogue fault strikes; regional earthquake focal
mechanisms (USGS ANSS / ComCat, free); derived fault-slip tendency.

**Physical signature:** Active geothermal systems correlate with faults that are
optimally oriented for slip in the contemporary stress field. Faults whose
strike/dip match the regional σ1–σ3 orientation (high slip tendency) are more
likely to be permeable conduits. Mismatched faults are sealed or inactive.

**Why it catches catalogue-missing faults:** Catalogue includes many mapped
Quaternary faults of varying activity. Slip-tendency filtering identifies the
subset most likely to host active geothermal flow, effectively down-weighting
sealed fossil faults that dominate the catalogue.

**Differs from repo:** No lane in this repo uses focal mechanisms or slip
tendency. All existing lanes use static geophysical/geomorphic proxies.

**Expected DTI improvement:** Medium. Estimated holdout-DTI 0.08–0.14.

**Implementation cost:** Low-medium. USGS ComCat API is free and scriptable.

**External data required:** USGS ANSS/ComCat focal mechanisms (free, public,
https://earthquake.usgs.gov/data/comcat/).

---

## H5 — 3DEP LiDAR curvature + TPI anomaly in the 24.99% LiDAR coverage gap

**Layers:** 1-m 3DEP LiDAR DEM (where available, 75% of footprint); 10 m NED/3DEP
bare-earth DEM (gap areas); multi-scale curvature and topographic position index.

**Physical signature:** Fault scarps produce characteristic curvature signatures
(concave-up at scarp base, convex at crest) and TPI breaks. Multi-scale
curvature (50 m, 200 m, 1 km) captures scarps of different ages. In the ~25% LiDAR
gap, coarser DEM curvature still detects large scarps.

**Why it catches catalogue-missing faults:** Young or subtle scarps may be
unmapped in the USGS/INGENIOUS catalogue but produce LiDAR curvature/TPI
anomalies. This directly images geomorphic fault expression.

**Differs from repo:** G79-THVC used LiDAR scarp steps as one channel. No lane
builds a dedicated multi-scale curvature + TPI anomaly surface with gap-aware
fusion.

**Expected DTI improvement:** Medium-high where scarps are young and preserved.
Estimated holdout-DTI 0.10–0.16.

**Implementation cost:** Medium-high. Requires 3DEP LiDAR DEM download (large,
public via The National Map) and curvature computation.

**External data required:** USGS 3DEP LiDAR DEM (https://www.usgs.gov/3dep,
free, public); gap-fill 10 m NED DEM.

---

## Recommended validation sequence

1. **Validate H1 (G79-DZD)** first — already implemented, zero external data,
   lowest cost. Confirm holdout-DTI once training data is available.
2. **Validate H2 (temperature + radiometrics)** second — highest expected
   improvement for blind systems, both external sources are free and official.
   Confirm obtainability of GDR 1391 and GEODAWN %K before committing.
3. If H2 data is unobtainable, fall back to **H3 (vent + sinter + dilation)**.

**Rule:** Do not spend a weekly submission slot on any hypothesis until its
holdout-DTI beats the current incumbent on both seeds with paired 95% CI
excluding zero, AND all leakage canaries pass (AUC ≤ 0.90), AND the full
registry uniqueness scan passes.
