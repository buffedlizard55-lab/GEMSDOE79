# Ranked hypotheses: session 0a202578

These are ranked by expected HOLDOUT-DTI gain against cost. Gains are qualitative judgments, not forecasts.

Rank 1 was tested in this session. Ranks 2–5 are untried in this repository; we checked them against every local lane listed in `AGENTS.md`. "Untried" here means not implemented locally. It does not mean nobody has ever thought of the idea.

| Rank | Hypothesis | Layers (all free, official) | Physical signature | Why it could catch off-catalogue faults | How it differs from tried lanes | Expected gain / cost | Status |
|---|---|---|---|---|---|---|---|
| 1 | **G79-FSC: fabric-steered concordance** | `training_features.tif` bands (detrended elevation, isostatic gravity, RTP), LiDAR scarp band, visible catalogue | Edge strike sub-parallel to the local mapped fault fabric | Unmapped splays inherit the regional strike set | First lane to use the visible-catalogue structure tensor as a steering field for features and for the NMS direction | Moderate expected, low cost | **Tested: NEGATIVE.** 0.1406–0.1580 vs THVC 0.1905/0.1944 |
| 2 | **G79-FGC: fabric-gated kernel cover.** Use the measured concordance family only as a *prior inside* the incumbent's kernel-cover placement, not as a classifier input | Same as rank 1 + the incumbent's surface | Same as rank 1 | The fabric family added +0.006 to +0.012 DTI over its ablation on the same folds. Placement, not features, was FSC's weakness | Reuses the measured fabric signal with the stronger placement. Not a restart of THVC: it is a new preregistered lane with THVC frozen as the control | Small (≈ +0.005 to +0.01 if additive), low cost | Needs an owner decision because it builds on archived THVC code |
| 3 | **G79-CJX: cross-scale contact-junction localization** | `training_features.tif` RTP (band 2) and isostatic gravity (band 13) | Persistent ridge-director winding and branch points across scales, with signed cross-contact contrast in both fields | Buried terminations and intersections keep density and susceptibility contrasts without a surface scarp | No lane uses persistence-qualified director junctions against a phase-randomised null | Uncertain (moderate), moderate cost | Untried. Data ready (pinned) |
| 4 | **G79-KNK: knickpoint and channel-steepness alignment** | USGS 3DEP 1 m DEM tiles listed by the organizer in `1m_DEM_links.csv` | Aligned knickpoints and steepness jumps across a line, independent of scarp relief | Slow, young or eroded faults perturb river profiles before a scarp is mappable | All terrain lanes used the 100 m stack; none used channel-profile physics | Uncertain, high cost (tile download and hydrology) | Untried. **Data blocked here:** this sandbox can only reach GitHub and package hosts, so the tiles must be fetched elsewhere |
| 5 | **G79-HFR: paired heat-flow residuals** | USGS Great Basin heat-flow maps and well residuals, [DOI 10.5066/P9BZPVUC](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28) | Paired warm and cool residuals along a structural corridor | Hydrothermal advection exposes permeable faults without scarps | Prior lanes used temperatures or springs, not residual pairs | Promising but unquantified, high QA cost | Untried. **Not data-ready:** metadata only; binary not acquired |

## Recommended next lane

**Prerequisite:** the owner must first make a prospective decision on the novelty rule's saturated branch (IR-79-173). Until then no file from any lane can pass every gate, so a new lane cannot yield a submittable file.

**Rank 2 (G79-FGC)** is the cheapest test of the only signal this session measured. To keep it honest:

- Preregister it with THVC as the frozen control.
- Use the same seeds, evaluator and gates.
- Allow at most 3 experiments.

Rank 3 is the best fully new mechanism with data on hand.

Data availability:

- The organizer's [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) lists the training features and the 1 m DEM links.
- External data is allowed if it is licensed for this use.
- In this sandbox, outbound access is limited to GitHub and package hosts. Ranks 4 and 5 therefore cannot be acquired here, and that has been recorded rather than assumed away.
