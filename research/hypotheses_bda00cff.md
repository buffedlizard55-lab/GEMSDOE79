# Ranked hypotheses — session bda00cff (lane G79-CFSKD) — written BEFORE training

Scoring labels: every number below is either HOLDOUT-DTI (gems57-pooled-hide-v2) from prior
cards, ORGANIZER-CONFIRMED (none in this repo), or a PROJECTION (never a score).

| Rank | Hypothesis | Layers | Signature | Why it catches uncatalogued faults | Differs from repo | Expected gain / cost |
|---|---|---|---|---|---|---|
| 1 | H-CFSKD: lithology-normalised potassic residual (K_d) + Okada-style Coulomb flank-shadow veto on a zero-catalogue physics head | training_features.tif (19), geodawn_rad_u8 (K,Th,U,TC), geodawn_extensions_u8, lidar_scarp_features_u8; visible faults only for veto | K_d = residual of K regressed on eTh,eU,TC (label-free), ridge-coherent; flank veto: suppress 3–15 px lateral corridor of visible faults except near endpoints (stress shadow), boost not applied elsewhere | Adularia/illite metasomatism marks permeable conduits where magnetite is destroyed (magnetic methods go blind); lateral stress shadows are where parallel splay FP dots are wasted under DTI alpha=0.2 | THVC/FNHR used raw rad ratios + tip lobes; no lane used cross-fitted K residual nor a negative Coulomb shadow veto (backlog H80-RADIO-KD + H80-COULOMB-CFS, research/hypotheses_post_thvc_backlog.md) | Highest viable / low (~minutes CPU) |
| 2 | H80-MT-PHASE: MT phase-tensor skew under clay cap | DOE GDR 1391 MT slices | log-resistivity step at 1.5 km aligned with gravity normal | Blind sub-playa upflow | Untried | NOT VIABLE NOW: MT slices are not in registry/data_manifest.json and gdr.openei.org is outside this sandbox's allowed hosts (verified: no MT entry in manifest; restore scripts contain only 2 m probes/sinter/geochem/volvents). Named source: https://gdr.openei.org/submissions/1391 (DOI 10.15121/1881483) |
| 3 | H80-DRAPE-DECONV: drape-corrected magnetic source depth | GeoDAWN line/drape metadata | e^{-|k|h} deconvolution + flight-line notch | Sub-fan bedrock offsets in 400 m-line area | Untried | NOT VIABLE NOW: drape/line metadata not in pinned inputs; source https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and |
| 4 | H80-SLIP-DEFICIT: footwall relief / Smf throw-deficit | det_elev + visible catalogue | H_fw * Smf^-1 across mapped-trace gaps | Piedmont step-out strands | THVC used tip-forward lobes, not relief conservation | Moderate / moderate; DEM is only 100 m det_elev in pinned inputs (1 m links need DrivenData login) |
| 5 | FNHR head + THVC Charnes-Cooper placer | archived lanes | placer swap | — | Both lanes are closed/archived (AGENTS.md rule 3: do not restart); also mutual overlap 0.4405 risks lane drift | Rejected, not run |

Mimic for #1: potassic playa evaporites / illitic lacustrine beds (K-rich, no fault) and
stress-shadow corridors that in fact host antithetic splays — the veto can delete true
antithetic faults; that failure mode is exactly what EXP-3 vs EXP-2 measures.
