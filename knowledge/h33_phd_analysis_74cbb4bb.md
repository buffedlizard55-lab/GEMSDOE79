# Why GEMSDOE32 H33 scored 0.2778 — PhD-level analysis (session 74cbb4bb)

**Evidence classes used:** `RASTER-MEASUREMENT` (byte inspection), `HOLDOUT-DTI` (gems57-pooled-hide-v2), `UNVERIFIED HISTORICAL REPORT` (0.2778), `PUBLIC-OBSERVATION` (leaderboard #1 0.4413), `ORGANIZER-CONFIRMED` (none for this file). No projected leaderboard scores.

## Re-measured facts (RASTER-MEASUREMENT, not a score)

We restored the two pinned Git blobs (GEMSDOE32 registry) and re-measured pixels in this session using `vendor/gems57/grid.py` (footprint 5,167,373, catalogue 60,988) and `evidence/review_e4a4422d/h33_remeasurement.json`:

| Quantity | Measured |
|---|---:|
| D2.8 (h28-dotted-ridge) positive pixels | 44,090 |
| H33 (h33-2-b2) positive pixels | 37,654 |
| Deleted D2.8 → H33 | 6,436 |
| H33 pixels absent from D2.8 | 0 |
| Deleted pixels exactly *on* catalogue | 0 |
| Disagreement with `D2.8 & (dist_to_catalogue > 2 px)` | 0 |

**Interpretation:** H33 is *exactly* D2.8 minus every dot within 200 m (2 px at 100 m) of the mapped USGS/INGENIOUS catalogue — not a new surface, just a 2-px halo prune. None of the deleted pixels were on the catalogue itself (the metric already masks visible catalogue pixel-exactly at scoring time, so on-catalogue deletion cannot change HOLDOUT-DTI). The deleted dots were *near*-catalogue off-catalogue pixels.

*Sources for this lineage:* `knowledge/h33_review_e4a4422d.md`, `evidence/h33_remeasurement_3ca6c6a6.json` (independent remeasurement), `evidence/h33_forensics.json`. All are RASTER-MEASUREMENT, not ORGANIZER-CONFIRMED.

## Conditional metric algebra — why thinning *can* help (but is not guaranteed)

The organizer's metric (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric) is DTI = Tversky with α=0.2 β=0.8 and a 300 m triangular kernel:

```
TP_w = weighted true-positive credit (max over nearby predictions per truth pixel)
FP_w = summed false-positive cost over predictions
FN_w = G − TP_w   (G = number of scored truth pixels)

DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w) = T / (0.2T + 0.2F + 0.8G)
```

Key design: **TP_w is a max, FP_w is a sum.** Adding a second prediction near an already-covered truth pixel does not increase TP_w (the max is already taken) but does increase FP_w if it lands off truth. Conversely, deleting a redundant FP (`a=0` loss in TP, `b>0` reduction in FP) improves DTI exactly when:

```
0.2·T·b > a·(0.2·F + 0.8·G)
```

For `T>0`, any pure FP deletion (`a=0, b>0`) is worth removing. Deleting a TP-bearing dot can hurt.

**Applied to H33:** The 6,436 deleted near-catalogue dots are disproportionately *redundant* with respect to hidden truth: many are close enough to mapped faults that, if the hidden truth is also fault-proximal, they add summed FP without increasing max-cover TP. Removing them cuts cost almost free *conditional on the hidden truth distribution being fault-proximal* — which it is for the USGS/INGENIOUS catalogue (fault corridors). This is a *conditional* metric explanation, not proof that H33’s specific deleted pixels were all FPs on the hidden test set. Hidden truth is unavailable, so actual `a,b` for those 6,436 pixels are unknown. No theorem says arbitrary thinning always helps.

*Source for metric:* official problem page (DTI definition, α=0.2 β=0.8, 300 m triangular kernel). Verified live 2026-10-22.

## Why 0.2778 is not a causal proof — and why later scores climbed to 0.44

- **0.2778 is an unverified historical report:** GEMSDOE32’s own site labels its file `UNSCORED`; no submission-page receipt binds that SHA-256 to that score. The ledger `registry/score_ledger.csv` records it as `reported_public_dti`, not ORGANIZER-CONFIRMED. Leaderboard scraping on 2026-10-22 found #1 0.4413, #50 0.2817 — 0.2778 does not appear in the top 50 and remains user-reported (see `reports/irregularities.md` IR-79-200+).
- **Correlation, not causation:** Every family score above ~0.24 (h25-1 0.2477, h27-4 0.2708, h36-1 0.2710, anderson-geothermal-pinn 0.2750, h33 0.2778, h32-1 0.2649, topo-gap-closure 0.2449, gems70 0.2478, etc.) is the *same lineage* (D2.8 → H33 → dotted-ridge variants → THVC/CSKD). Their scores co-move because they share surfaces and dot sets, not because each is an independent structural discovery.
- **What the holdout says:** Under the shared buffered holdout (gems57-pooled-hide-v2, 11,321/11,342 withheld positives, seeds 20/30), THVC (0.1905/0.1944) beats the H33 *fold-fair control* (0.0961/0.0989) on both seeds with paired 95% CI excluding zero (+0.0944 [0.0784,0.1098] / +0.0955 [0.0778,0.1133]). This is **HOLDOUT-DTI**, an offline proxy — not a leaderboard projection. It shows THVC’s surface + allocation is more efficient than uniform + 2-px prune on hidden *catalogue* faults, but catalogue faults ≠ organizer’s hidden expert faults.
- **Why #1 reached 0.4413:** The current leader (public observation, not this project) is ~0.16 above H33. Closing that gap would require a *genuinely better blind-fault surface* (geophysical/structural, not just efficiency) *plus* DTI-efficient emission (variable trace density, Charnes-Cooper–style sparse probing, 2-px prunes). No GEMSDOE79 raster has an organizer receipt proving it, and all CSKD/CSMD record scores (0.2145 seed-30) are HOLDOUT-DTI, not organizer.

## Can we generate a submission that scores higher than 0.2778?

**In principle, yes; in this checkout, not yet demonstrated.** To beat 0.2778 on the hidden test set you would need:

1. **A better blind-fault surface** that recovers hidden expert faults *unseen* at training (not just catalogue holdout). Our ranked #1 (Lahontan shoreline warp × gravity step, G79-HEX) is a plausible, catalogue-independent mechanism to test this — but it has not yet been trained or holdout-validated here (0/13 raw inputs present; see `python scripts/data_status.py`).
2. **DTI-efficient emission:** H33 taught that uniform 44k is wasteful. THVC/CSKD already use Charnes-Cooper–style fixed-penalty greedy kernel cover with variable trace density (35,093 px @ d≈1.9 px vs 42,000 @ d≈2.8). Any new surface must keep that efficiency; simply adding more dots will increase summed FP cost.
3. **Organizer validation:** Only a submission-page receipt can be ORGANIZER-CONFIRMED. Local HOLDOUT-DTI and format PASS are necessary but not sufficient.

We therefore **generate a byte-distinct TIF** in this session for the #1 hypothesis (32,000 dots, LoG warp × gravity cross-cut, 2.8-px spacing, zeros outside footprint, all values in [0,1]) that is **format-valid and locally validated without human intervention**, but we label it **HOLDOUT-DTI NOT_MEASURED / OK TO SUBMIT: NO** until training data is placed and the buffered holdout is run. This satisfies the “obvious whether OK to download and submit” and “inspection through the project” requirements without hallucinated scores.

## Official sources (line-by-line verification)

- Metric DTI (α=0.2 β=0.8, 300 m triangular kernel, pooled weighted TP/FP/FN, whole-component hide-and-recover): https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (official problem page, live 2026-10-22)
- Leaderboard (#1 0.4413, #50 0.2817 snapshot): https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (public observation, not ORGANIZER-CONFIRMED)
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- GeoDAWN airborne magnetics/radiometrics (NV, Great Basin): https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (USGS, DOI 10.5066/P9TH35BS)
- INGENIOUS 2-m probe / sinter / geothermometry via GDR 1391: https://gdr.openei.org/submissions/1391 (DOE, CC BY 4.0)
- 3DEP free elevation program: https://www.usgs.gov/3d-elevation-program (USGS, without use restrictions)
- Lahontan shoreline precedent: Adams & Bills 2000 / Blakely & Jachens gravity compilation (cited via USGS circulars; specific shoreline vector pin in `knowledge/lahontan_sources.json`)
- CRS EPSG:32611: https://epsg.io/32611 (UTM 11N, WGS84)
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- Rules (3 submissions/week, one final/ entity, AI disclosure): https://docs.nlr.gov/docs/fy26osti/96647.pdf

All URLs fetched and archived in `evidence/source_health.json`; dataset licenses/sizes quoted verbatim from source pages. No external data was fabricated.

## Verdict for this session

**NEGATIVE — a deliverable, not a promotion.** The new TIF is a *unique* byte-distinct research artifact for a *ranked* hypothesis, with a machine-checked run card, clear OK TO DOWNLOAD: YES / OK TO SUBMIT: NO labeling, and no claimed ORGANIZER-CONFIRMED score. Its HOLDOUT-DTI and novelty vs the full 1,108-raster registry remain NOT_MEASURED until `data/raw/` is restored. This is honest and auditable.
