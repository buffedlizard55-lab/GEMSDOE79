# Five ranked untried hypotheses — session 0be4d7bb (2026-10-22)

All scores below are HOLDOUT-DTI (gems57-pooled-hide-v2) unless labelled
ORGANIZER-CONFIRMED (organizer receipt only). Historical site scores in the
prompt (0.2778, 0.4413, 0.3195) are UNVERIFIED HISTORICAL REPORTS — no
organizer receipt links them to bytes in this repo (see evidence/h33_forensics.json).

| Rank | ID | Layers (official source) | Physical signature / operator | Why it catches catalogue-missing faults | Differs from repo lanes | Cost / viability |
|---|---|---|---|---|---|---|
| 1 | G79-TDW tilt-depth worms | training_features.tif bands rtp(2), iso_grav_anom(13), tmi(14), depth_to_base_surf(15) — DrivenData GEMS data via SHA-pinned mirror registry/data_manifest.json (organizer origin https://www.drivendata.org/competitions/306/competition-doe-gems/data/) + USGS GeoDAWN DOI 10.5066/P93LGLVQ | Directional FFT notch of E-W flight lines, Salem tilt theta=atan(dz/HGM), tilt-zero worm proximity x shallow half-width depth (<600 m) x gravity-step concordance | Buried intrabasin step faults under 50-500 m fan/playa cover have no LiDAR scarp but offset shallow magnetic basement; prior lanes fired on un-notched seams/deep plutons | THVC/CSKD/DFSD use broad ML ensembles; CJX-DIR uses RTP x gravity junctions without destriping or tilt-depth gating; no lane notches flight lines + tilt-depth | Low (~5 min CPU). Viable offline: SHA verified this session |
| 2 | H79-U2 fan-apex knickpoints | det_elev/slope/curvature bands + lidar_scarp_features_u8.tif (GeoDAWN/3DEP) | Knickpoint (-d2z/ds2) peaks in convergent channels, >=3-drainage collinearity (Hough) over 1-6 km | Low-slip piedmont faults lose scarps to debris flows but lock incision knickpoints on every crossing drainage | No repo lane links independent drainages collinearly; scarp lanes score single scarps | Low-medium. Viable offline |
| 3 | H79-U3 MT conductance edge | cond_surf + depth bands; GDR 1391 DOI 10.15121/1881483, MT DOI 10.5066/P9TWT2LU | Lateral log-conductance gradient aligned 0-2 km and 2-10 km x heat-flow residual | Sealed blind geothermal faults contrast resistive footwall vs conductive damage zone with no surface trace | CSMD used conductance inside 90-ch ML, never as standalone cross-depth edge x heat veto | Low. Viable offline |
| 4 | H79-U4 Riedel transfer zones | existing_faults (visible only per fold) + rtp/gravity + lidar | Strike divergence 35-85 deg between Walker Lane (310-335) and Basin-Range (010-035), R/R' scoring in intersection polygon | Short 1-4 km transfer faults in structural tangles are under-digitised vs >20 km masters (Faulds & Hinz 2015, INGENIOUS https://gbcge.org/current-projects/ingenious/) | Network lanes score tips/relays of single faults, not conjugate-divergence polygons | Low. Viable offline, fold-strict recompute required |
| 5 | H79-U5 shoreline veto | USGS 3DEP 10 m DEM https://www.usgs.gov/3d-elevation-program + lidar scarps | Along-scarp elevation drift \|dz/ds\|: shorelines <1.5 m/km vs faults >>8 m/km; reallocate vetoed dots | Removes Lahontan shoreline false positives, freeing budget for true piedmont traces | CSKD has Lahontan env feature inside ML; no standalone true-altitude veto + reallocation | Medium. NOT viable in sandbox (3DEP host outside egress allowlist github/pypi/npm); free official source named, obtainable via GitHub Actions/USGS National Map — flagged, not proposed as this session's lane |

## Decision
Top candidate = G79-TDW (rank 1). It is validated below on the shared
hide-and-recover holdout BEFORE any submission decision. No weekly slot is
spent unless it beats the frozen incumbent THVC HOLDOUT-DTI 0.1905 (seed 20,
n=11,321) / 0.1944 (seed 30, n=11,342) and clears canary + novelty gates.
Named non-fault mimic: Miocene basalt dike swarms + residual flight-line
seams. Rejection filter: +-4 deg azimuth notch + unilateral gravity-step
concordance (dikes are symmetric dipoles, faults are unilateral steps).
