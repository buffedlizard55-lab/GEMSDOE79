# Five candidate hypotheses considered this session (ranked)

Status labels: every score below is **HOLDOUT-DTI** (`gems57-pooled-hide-v2`,
α=0.2, β=0.8, 300 m triangular kernel) or a **frozen receipt** quoted from
`evidence/g79_thvc_results.json`. No leaderboard number is projected.
Historical scores in the prompt (H33 0.2778 etc.) are unverified user/site
reports — GEMSDOE32 itself labels its file UNSCORED — not organizer receipts
for any artifact in this repo (see `knowledge/h33_review_e4a4422d.md`).

## Why H33 (reported 0.2778) plausibly scored above the dotted family
Byte-verified geometry (not a causal score proof): H33 = the 44,090-dot
D2.8 field minus 6,436 dots, **all** of them within 2 px of the catalogue and
none exactly on it (`evidence/review_e4a4422d/h33_remeasurement.json`).
Under DTI = T/(0.2T+0.2F+0.8G+ε), deleting a dot that earns no new truth
credit (a=0) but carries false-positive mass (b>0) always helps; near-
catalogue dots are the most likely to be redundant because a known trace's
neighbourhood is already dense with predictions in dotted fields. Thinning
is therefore *prediction-efficiency*, not new geology — and copying H33's
pixels would be a registry duplicate, which the lane rule forbids.

## Candidates (none previously implemented as a named lane in this repo)

| # | Hypothesis | Layers / signature | Why it could find a catalogue-missing fault | Difference from implemented lanes | Cost / expected value |
|---|---|---|---|---|---|
| 1 | **G79-CJX tip-steered contact junctions** (IMPLEMENTED this session) | Bands 2 `rtp` + 13 `iso_grav_anom`; multi-scale (1/2/4 px) structure-tensor edge persistence, cross-field coincidence √（pers_mag·pers_grav), orientation concordance, discordance; Exp 3 steers by exp(−d/12 px) to visible-catalogue skeleton endpoints | A buried contact offset/junction can persist in both potential fields where no scarp is mapped; at a visible tip, a coincident contact crossing is a continuation candidate rather than a pluton margin | THVC is a learned 84-channel ensemble; no lane used cross-field contact coincidence or orientation winding as the mechanism. CJX v1/v2 use **zero** catalogue pixels | Low cost (cached bands). Ranked #1 for novelty+cost, with value explicitly uncertain |
| 2 | **G79-SRX strain-axis rotation** | Bands 4 `geod_2ndinv`, 7 `geod_shearrate`, 8 `geod_dilaterate`; winding of the geodetic strain principal-axis field + shear/dilatation sign change-points | Actively deforming unmapped faults rotate the local strain axes before a scarp forms | Strain bands were ensemble *inputs* in THVC; nobody used axis-rotation topology as the detector | Low cost; coarse geodetic resolution ⇒ low/uncertain value |
| 3 | **G79-BLC bilateral lithology-contrast change-point** (backlog #2) | `rtp`, `iso_grav_anom`, GeoDAWN radiometric ranks; along-ridge change in cross-flank joint distributions | A transfer fault offsets two pre-existing contacts under alluvium even with weak relief | Not a scalar anomaly or across-normal lag (E1) | Moderate/high cost |
| 4 | **G79-RSS relief-screened structural saddle** (backlog #3) | Bands 12 `det_elev`, 19 slope, 13/18 gravity; multi-scale saddles crossed (not followed) by a gravity contrast | Low-relief transfer zones between range segments are under-mapped vs range fronts | Starts from terrain topology, not visible endpoints | Moderate cost, low/uncertain value |
| 5 | **G79-HFR paired heat-flow residuals** (backlog #4) | USGS Heat Flow, DOI 10.5066/P9BZPVUC well-point residuals ± paired along a structural corridor | Hydrothermal advection exposes buried permeability with no scarp | THVC used spring/temperature proximity, not paired signed residuals vs the source's conductive background | **Data-blocked**: metadata verified, binary not acquired in this sandbox; not viable until acquisition+QA pass |

Ranking rule applied: validate the top candidate on the blocked holdout
**before** any slot; a candidate that does not beat the incumbent
G79-THVC holdout (0.1905 seed 20 / 0.1944 seed 30, frozen) is not promoted.

## Result for #1 (three experiments, budget exhausted)
- Exp 1 CJX v1 edge: 0.0406 [0.0316, 0.0505] (n=11,321) / 0.0473 [0.0362, 0.0594] (n=11,342) — **below random**.
- Exp 2 CJX v2 junction: 0.0404 / 0.0452 — below random. The pluton/caldera-margin mimic dominates coincident-edge extremes.
- Exp 3 CJX v3 tip-steered: **0.1041 [0.0870, 0.1220] / 0.1063 [0.0910, 0.1207]** — beats random (≈0.045–0.049) and the frozen H33 fold-fair control (0.0961/0.0989), but **does not beat G79-THVC (0.1905/0.1944)**. CJX v3 band arm: 0.0387/0.0460 (negative).
- Leakage canary: max symmetric AUC 0.5483 (seed 20) / 0.5674 (seed 30) over 7 channels — PASS ≤ 0.90, i.e. no single channel is a catalogue leak (expected: v1/v2 are catalogue-free).

**Verdict: negative.** The unique TIF generated from Exp 3 is a research
artifact, labelled DO NOT SUBMIT by the automated gate
(`scripts/cjx_gate.py`, `run_card_cjx.json`). Beating 0.2778/0.4413 on the
organizer leaderboard is **not** claimed: no organizer receipt exists, and
the holdout gate that this project uses to protect slots failed.

Sources (manual review): competition metric/rules
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ •
reference solution https://github.com/drivendataorg/gems-prize-reference-solution •
GeoDAWN https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and •
INGENIOUS https://gbcge.org/current-projects/ingenious/ • EPSG:32611
https://epsg.io/32611 • Tversky index https://en.wikipedia.org/wiki/Tversky_index •
heat-flow DOI https://doi.org/10.5066/P9BZPVUC
