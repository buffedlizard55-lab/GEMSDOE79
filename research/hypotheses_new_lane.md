# New-lane hypotheses (this session, catalogue-only — sandbox has NO cached feature stack)

Sandbox audit (verified 2026-10-22): `.cache/` feature stack absent (excluded from snapshot);
only `data/bridge/{existing_faults,sample_submission,labels}.tif` present. Any hypothesis needing
GeoDAWN/DEM/MT layers is NOT executable here until `scripts/restore_data.py` cache is restored on an
unrestricted machine. Free official source if needed: USGS GeoDAWN https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and

| Rank | Hypothesis | Layers | Signature | Why uncatalogued? | Differs from repo | Cost |
|---|---|---|---|---|---|---|
| 1 (TESTED) | Fault-tip propagation + en-échelon stepover relay completion | existing_faults only | Tip strike (PCA of tip neighbourhood) ray-cone decay + collinear inter-tip bridges | Hidden faults in hide-and-recover are whole withheld strands; their continuations/stepovers project from visible tips | H79 used tips only as a collar *gate* on a 130ch physics surface; no pure-geometry emitter + bridge term in this repo. Sibling tip lanes exist (flagged) | Low |
| 2 | Strand-orientation field continuation (structure-tensor extrapolation) | existing_faults only | Orientation coherence extrapolated into gaps | Same as above | Overlaps relay lanes; not tested (budget) | Low |
| 3 | Wavelet phase congruency on mag/grav | GeoDAWN tif (absent) | log-Gabor PC | Blind intrabasin steps | H79-2 in README, untested | BLOCKED: no cache |
| 4 | MT clay-cap edge crest | cond layer (absent) | grad log sigma crest | Upflow breach | in H79 130ch already | BLOCKED |
| 5 | Sentinel-1 InSAR creep gradient | external InSAR (absent) | grad v_LOS | aseismic creep | untried anywhere listed | BLOCKED: network allowlist |

Mimic for #1: aligned but unrelated mapped strands (coincidental collinearity), palaeo-shoreline scarps mapped as faults.
