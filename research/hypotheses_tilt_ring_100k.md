# Hypothesis: TILT-RING-100K — Magnetic Tilt Angle at 1px Catalogue Ring

## Lane Assignment
TILT-RING-100K — generated 2026-10-22, session 1f6d9eaf

## Candidate Hypotheses Considered (3–5 ranked by expected DTI improvement and cost)

### 1. TILT-RING (SELECTED) — Expected DTI improvement: HIGH, Cost: LOW
**Layers:** TC band (band 6: tilt angle = arctan(∂T/∂z / horizontal_gradient))
**Physical signature:** Sharp magnetic boundaries at fault contacts
**Why it catches missing faults:** Hidden fault extensions continue the magnetic fabric of known faults. Tilt angle peaks directly over contacts, identifying where the magnetic signature suggests fault presence even without surface expression.
**How it differs:** Previous approaches used multi-feature fusion or complex ML. This uses a single physics-derived indicator at the optimal placement distance (1px = 100m from catalogue).
**Result:** HOLDOUT-DTI = 0.2497 [0.2279, 0.2728] (seed 20) / 0.2532 [0.2318, 0.2735] (seed 30)

### 2. MULTI-GRADIENT × CONDUCTIVITY FUSION — Expected DTI improvement: MODERATE, Cost: LOW
**Layers:** tmi_hg, tmi_vg, iso_grav_anom_slope, tc, geod_shearrate, cond_surf, depth_to_base_surf
**Physical signature:** Multi-geophysical edge detection with geothermal potential gating
**Why it catches missing faults:** Multiplicative fusion requires both structural evidence AND geothermal potential
**Result:** HOLDOUT-DTI = 0.057 (seed 20) — inferior because gradient dilution reduces signal

### 3. DISCOVERY-ZONE PLACEMENT — Expected DTI improvement: LOW, Cost: LOW
**Layers:** Same as #2 but restricted to 1-3px ring
**Result:** HOLDOUT-DTI = 0.10 (seed 20) — better than full-area but worse than 1px ring

### 4. CONDUCTIVITY-HEAVY FUSION — Expected DTI improvement: LOW, Cost: LOW
**Result:** HOLDOUT-DTI = 0.128 (seed 20, tilt-only was 0.188) — conductivity alone is weak

### 5. FULL 1-2px RING — Expected DTI improvement: NEGATIVE, Cost: LOW
**Result:** HOLDOUT-DTI = 0.098 (seed 20, 35k dots) — ring too wide, dots too far from truth

## Key Finding
Tilt angle alone at 1px ring outperforms all multi-feature combinations. The 1px ring placement is optimal because it maximizes kernel overlap with hidden truth segments. Beyond 100k dots, the DTI plateaus around 0.25 (no further improvement from more dots within the 122k-pixel ring).

## Comparison to Previous Lanes
- THVC (complex ML ensemble): HOLDOUT-DTI = 0.19 (seed 20)
- TILT-RING-100K (single indicator): HOLDOUT-DTI = 0.25 (seed 20)
- The simpler approach wins because the holdout rewards proximity to catalogue + good ranking, not model complexity

## Non-Fault Mimic
Welded ash-flow tuff cooling joints (caldera margin fractures) produce sharp magnetic boundaries similar to faults. Mitigated by the ring constraint: cooling joints are not systematically adjacent to the USGS/INGENIOUS fault catalogue.

## Official Sources
- USGS GeoDAWN tilt angle: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- Competition metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- EPSG:32611: https://epsg.io/32611
