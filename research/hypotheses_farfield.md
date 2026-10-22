# Candidate hypotheses — far-field lane (2026-10-22, this session)
All scores cited are HOLDOUT-DTI (gems57-pooled-hide-v2) or user-reported
ORGANIZER scores from the prompt; no projections are written as scores.

| # | Hypothesis (layers / signature) | Why it should catch catalogue-missing faults | Differs from repo history | Cost | Rank |
|---|---|---|---|---|---|
| H1 | **Far-field band ranking**: NHR nested hide-to-recover HGB surface, placement restricted to 10–30 px (1–3 km at 100 m/px) from visible catalogue, 3DEP lidar scarp bands (`step_max`,`ex_max`,`downface_max`) already in stack. Antithetic/synthetic subsidiary strands live in this band. | Mapped-fault pixels are masked by organiser; near-field (<1 km) dots were pure FP in H33 forensics and duplicate 26 registry fields. Band keeps kernel-credit geometry while vacating occupied near-field. | NHR placed at median 5.4 px; H33 median 19.6 px but unmodelled D2.8 dots. No prior lane combined learned surface + hard far-field band restriction checked for uniqueness *before* full placement in this repo's next-steps list (README Limitations #2). | Low (reuse `run_nhr` Stack/training/fit) | 1 |
| H2 | Along-strike tip extension only: dots beyond catalogue endpoints (`log_dist_visible_tip` small, `log_dist_visible` large), collinear strike field. | Faults propagate along strike beyond mapped tips. | STEPCO/NHR used tips as feature, never as hard placement gate. | Low | 2 |
| H3 | Lahontan shoreline suppression: exclude contour-parallel steps at palaeo-shoreline elevations (needs absolute 3DEP DEM, not yet restored). | Removes named mimic, raising precision of scarp dots. | Not implemented; DEM restore is extra data step. | Medium (new external data) | 3 |
| H4 | Radiometric alteration (K/Th/U) corridor maxima far from faults. | Hydrothermal alteration along unmapped conduits. | TSO1 tried alteration alone (user-reported 0.0782). | Medium | 4 |
| H5 | Gravity/magnetic worm persistence far-field. | Basement steps under cover. | GEMSDOE42 worm persistence (0.0581 user-reported). | Medium | 5 |

Decision: test H1 as lane **H79-FF1** (experiment X1 only). Mimic named:
pluvial Lake Lahontan shoreline/terrace risers (contour-parallel steps).
Promotion requires: canary ≤0.90, HOLDOUT-DTI > H33 fold-fair control on both
seeds 20/30, paired CI vs uniform excludes 0, uniqueness (ρ≤0.90, ≤70% dots
within 3 px) on surface-before-placement AND final dots, shared-writer format PASS.
