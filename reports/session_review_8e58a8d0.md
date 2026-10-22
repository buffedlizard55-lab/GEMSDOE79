# Session review 8e58a8d0 — G79-MDSC (2026-10-22)

Branch `arena/8e58a8d0-gemsdoe79`. Budget used: 2 of 3 experiments. Slots used: **0**.

## The question: why did h33-h33-2-b2 (reported 0.2778) lead, and can we beat it?

Short answer: **credit density under a budget metric — and this session did not beat it.**

1. **Provenance caveat (flagged irregularity).** 0.2778 is an *UNVERIFIED HISTORICAL REPORT*
   (`registry/score_ledger.csv`); the GEMSDOE32 site itself, re-read this session, labels the
   identical file "UNSCORED — NO ORGANISER SCORE EXISTS for this or any artifact in this
   repository." The prompt's leaderboard figures also disagree with each other (0.4413 vs
   0.3195 vs a derived 0.3262). No number here is ORGANIZER-CONFIRMED.
2. **Measured lineage (prior frozen receipt, re-cited):** H33 ≡ D2.8 (44,090 dots) minus the
   6,436 dots within 2 px of the catalogue → 37,654 dots; zero added.
3. **Mechanism (metric algebra, α=0.2, β=0.8):** DTI = T/(0.2T+0.2F+0.8G). A marginal dot is
   worth emitting only if its expected triangular-kernel credit exceeds ≈0.2·DTI
   (≈0.052 at DTI≈0.26; the family measured 0.0548 empirically). Near-catalogue dots add
   FP mass where hidden truth is masked or already covered, so pruning them cuts cost
   faster than credit. This explains H33 > D2.8-type files > thick continuous surfaces.
4. **Implication:** beating 0.2778 (let alone the leaderboard) needs ~+25% mean credit per
   dot at equal mass — a better *ranking*, not more thinning. Hence two new detector
   surfaces were tested instead of another emission variant.

## Experiments (shared evaluator `gems57-pooled-hide-v2`, unmodified vendor code)

Preregistered before scoring: `registry/preregistration_mdsc_8e58a8d0.json` (+ `.sha256`),
`registry/preregistration_sfgc_lite_8e58a8d0_E2.json`. Hypotheses ranked in
`research/hypotheses_8e58a8d0.md` (5 candidates; SFGC-full deferred as it needs an
84-feature ensemble retrain; MCST blocked — `geodesy.unr.edu` outside sandbox egress).

| Arm (HOLDOUT-DTI) | Seed 20 (n=11,321) | Seed 30 (n=11,342) |
|---|---|---|
| E1 A: MDSC (z,N) screen | 0.0448 [0.0328, 0.0565] | 0.0434 [0.0329, 0.0540] |
| E1 B: HG amplitude only | 0.0454 [0.0312, 0.0593] | 0.0453 [0.0326, 0.0577] |
| E1/E2 C0: random | 0.0457 [0.0398, 0.0517] | 0.0459 [0.0411, 0.0506] |
| E2 A: SFGC-lite signed polarity | 0.0683 [0.0568, 0.0786] | 0.0626 [0.0527, 0.0723] |
| E2 B: THVC unsigned quantity | 0.0530 [0.0425, 0.0639] | 0.0436 [0.0352, 0.0520] |
| **Bars (G79-THVC, canonical)** | **0.1905** | **0.1944** |

- **E1 verdict: falsified.** Magnetic (z,N) screening adds nothing over HG amplitude
  (paired Δ −0.0005 [−0.0061, 0.0052] / −0.0019 [−0.0077, 0.0039]); both ≈ random for
  recovering withheld *catalogue* faults. Canaries pass (max symmetric AUC 0.5421 ≤ 0.90) —
  the null result is not leakage in disguise; the FFT continuation itself was sanity-checked
  against the shipped TMI_up150 band (Spearman 0.647 on a 200k sample; quantised u8 band,
  different input field, so this is a consistency check, not identity).
- **E2 verdict: mechanism supported, magnitude insufficient.** Signed polarity beats the
  exact unsigned quantity THVC used by +0.0152 [0.0092, 0.0207] / +0.0190 [0.0143, 0.0245]
  standalone. Actionable: replace `abs(up−down)` with signed features in the next ensemble
  retrain (SFGC-full). Still 3× below the promotion bars → no raster emitted from E2.
- **Interpretation limit:** holdout truth = mapped faults; the organizer scores
  *unmapped* faults. Zero-catalogue physics surfaces are systematically disadvantaged on
  this instrument (THVC's own zero-catalogue ablation: 0.0784/0.0648). That bias argues
  for the ensemble route, not for lowering the preregistered bar.

## New unique artifact (research only)

`artifacts/mdsc_8e58a8d0/gems79-mdsc-magdepth-37654dots-20261022T191639Z-d09aa2f6-zeros-DO-NOT-SUBMIT.tif`
(SHA-256 `270183c…186a21`, 141,485 bytes; ZIP alongside). Written only via the shared
`submission_writer`; independent re-read: float32, 1 band, EPSG:32611, 3730×3292,
transform = sample, **finite, min 0.0, max 1.0, 0 NaN, nodata=None** — the
`"Predicted values must be in range [0, 1]"` failure mode (float32 sentinel −3.4e38 and/or
NaN nodata written through) is excluded by construction. Uniqueness vs 28 unique sparse
dot rasters present in this checkout: max forward 3-px overlap **0.3736 ≤ 0.70**, max
|Spearman| **0.0311 ≤ 0.90** (surface sample 400k; final dots full-grid EDT). This is a
genuinely distinct dot field — and it is still **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.**

## Irregularities flagged

1. Prompt leaderboard/score claims conflict (0.4413 / 0.3195; H33 0.2778 vs its site's
   UNSCORED label). All treated as unverified reports.
2. The literal novelty gate (any registry raster, `>0` positives) is *mathematically
   unsatisfiable* for every nonempty candidate (dense witness covers 100% of allowed
   cells; spacing-5 lattice forces ≥82.7% overlap). Owner decision needed prospectively:
   define comparators as sparse submitted dot files. Not changed unilaterally here.
3. `vendor/gems57` writer receipts embed absolute checkout paths (precedent: DZD artifact).
   Shared-tool fix candidate; not forked.
4. CANONICAL card `run_card.json` (G79-THVC) untouched; a later lane (G79-CSKD, seed-30
   0.2145 per its page) exceeds THVC on one seed but the preregistered bars used the
   canonical two-seed record. Either bar rejects both experiments here.

## Next steps (next session)

1. SFGC-full: THVC retrain with signed (up−down) + strike features, flank-decontaminated
   negatives (d_vis>3 px), Dinkelbach λ — the only route with a plausible path past 0.19.
2. Owner decision on the novelty-gate comparator definition (item 2 above), frozen
   prospectively before any new lane.
3. Stage UNR MIDAS GPS file via an allowed mirror if MCST is to become executable.
