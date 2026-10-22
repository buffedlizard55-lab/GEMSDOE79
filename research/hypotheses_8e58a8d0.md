# Candidate hypotheses — session arena/8e58a8d0 (2026-10-22)

All five are inherited from the verified untried backlog `research/hypotheses_0d90d81b.md`
(none executed; checked against `run_card*.json` lanes and `archive/`). Re-ranked here by
**expected HOLDOUT-DTI gain ÷ in-session implementation cost**, with executability as a hard
filter. Numbers labelled "hypothesis range" are prior-session expectations, NOT scores.

| Rank (this session) | ID | Layers | Physical signature | Why it catches catalogue-missing faults | Differs from repo lanes | Cost |
|---|---|---|---|---|---|---|
| 1 (executed as E1) | G79-MDSC | `training_features` rtp/tmi_hg/tmi_vg/tmi; `geodawn_extensions_u8` TMI_up150 (cross-check) | Multi-altitude upward-continuation decay → per-pixel (depth-to-top z, structural index N); keep z∈[50,400] m, N∈[0,0.6] HG ridges | Faults under 50–400 m of basin fill have no scarp for photogeologic compilation (USGS QFaults targets M>6 surface deformation, DOI 10.5066/P9BCVRCK) but still offset magnetic units | H80-DRAPE used an E–W notch + tilt only; no lane inverts vertical attenuation for (z,N) | Low (~15 min CPU FFT) |
| 2 | G79-SFGC | lidar `upface_max/downface_max/strike`; `det_elev`, `iso_grav_anom(_hg)` | Signed scarp-facing polarity × hanging-wall gravity-step concordance; flank-decontaminated negatives; Dinkelbach λ | Antithetic graben counter-scarps face up-slope — shorelines/terraces physically cannot; USGS simplifies multi-strand piedmont zones to one trace | THVC took abs(up−down) and discarded sign/strike | Medium-high: requires retraining the 84-feature nested THVC ensemble; not reproducible inside this session's budget without its full cache — deferred, not executed |
| 3 | G79-UGBP | GDR-1391 well/spring CSV (`geothermquartz_c`, `geothermcat_c`, `temp_c`); `det_elev`, `iso_grav_anom_hg` | Quartz vs Na-K-Ca geothermometer disequilibrium → up-gradient advection to first basement step | Blind feeders hide under fans; springs emerge 1–8 km down-gradient | All prior thermal lanes used isotropic kernels at spring points | Low, but only 827 chemistry records → sparse support |
| 4 | G79-PSDC | radiometric U/Th; springs; `iso_grav_anom_vg`; road-distance veto | Playa U/Th redox lineaments collinear with gravity zero-crossings | Intra-playa faults leave no relief; expressed as groundwater-barrier chemistry | Prior lanes down-weighted radiometrics in basins | Low; small playa support fraction |
| 5 | G79-MCST | UNR NGL MIDAS GPS velocities (external) + strain bands | Principal extension azimuth φ_ext(x) × contact strike → dilation tendency | Short Walker Lane echelon faults below M>6 compilation threshold | Prior lanes used only scalar strain invariants | BLOCKED: geodesy.unr.edu is outside this sandbox's egress allowlist; free official source exists (https://geodesy.unr.edu/gps_timeseries/IGS20/midas/midas.NA.txt, DOI 10.1029/2018EO104623) but is not obtainable here — not viable this session |

**Selection rule applied:** validate the top *executable* candidate (MDSC) on the shared
spatially-blocked holdout against the canonical G79-THVC bars (HOLDOUT-DTI 0.1905 seed 20 /
0.1944 seed 30, `gems57-pooled-hide-v2`) before any submission-slot recommendation.
SFGC has the highest prior expected gain but fails the in-session executability filter;
claiming it as "validated" without retraining would be a hallucination.
