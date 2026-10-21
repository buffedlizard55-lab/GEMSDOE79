> **HISTORICAL H79-MCT MATERIAL, NOT CURRENT APPROVAL.** Preserved from concurrent main c26efec. The literal protocol was not cleared; dense-prior exemptions and post-duplicate placement amendments are not authorized by this run. All incoming scores/claims retain their unreviewed original provenance. DO NOT SUBMIT these artifacts. Read the active root README/run_card.json.

# Competition facts (verified from official pages; read 2026-10-21)

| fact | class | source |
|---|---|---|
| Metric: distance-tolerant Tversky index, α = 0.2, β = 0.8, triangular kernel k(d) = max(1 − d/300 m, 0), radius 3 px; TP_w = Σ_g max_x p(x)k(d), FP_w = Σ_x p(x)[1 − max_g k(d)], FN_w = Σ_g[1 − max_x p(x)k(d)] | ORGANIZER-CONFIRMED | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ |
| Test set = expert-labelled faults NOT in the USGS/INGENIOUS database; region chunked into public/private test; final round re-scored on labels expanded after expert review of all submissions; one selected submission for both rounds | ORGANIZER-CONFIRMED | same |
| Format: EPSG:32611, 100 m, same bounds as sample, single float32 band, values in [0, 1], outside bounds null/NaN (zeros also accepted in practice — the 0.2778 file is all-zeros outside) | ORGANIZER-CONFIRMED (format) / BYTES (zeros) | same; `reports/why_02778.md` |
| Known USGS/INGENIOUS fault pixels are masked from evaluation (no penalty, no credit) in both rounds | ORGANIZER-CONFIRMED (staff chrisk-dd, 2026-09-16) | https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516 |
| "New fault" = any fault pixel not already captured by USGS/INGENIOUS; includes continuations beyond endpoints, splays, parallel strands of known systems | ORGANIZER-CONFIRMED (staff, 2026-09-23) | https://community.drivendata.org/t/where-do-you-draw-the-line/11536 |
| Staff decline to disclose data sources / fault types behind the test labels | ORGANIZER-CONFIRMED (2026-09-23) | https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527 |
| Leaderboard 2026-10-21: #1 xiaofanhu 0.4413, #2 0.3904, #3 0.3894, #4 0.3713, #5 0.3539, #6–#7 0.3418/0.3416, #8 0.3375, #9–#19 0.3330→0.3273, #20 0.3262, owner's account extradr19 0.2778 (#48) | ORGANIZER-CONFIRMED | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ |
| Reference solution repository | official | https://github.com/drivendataorg/gems-prize-reference-solution |
| Rules | official | https://docs.nlr.gov/docs/fy26osti/96647.pdf |

Metric consequences used in this lane (derivations in `reports/why_02778.md`): binary dots are
optimal; thinning to ≈ 3 px spacing along lines is free recall; dots within 2 px of the catalogue
can only cost; recall is worth 4× precision.

## How to submit a promoted file (the mechanics)

1. Download the `.tif` (or the `.zip` containing exactly that one `.tif`) from the site's top banner.
2. Log in at https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/ and
   upload it; paste the submission **name** and the **note** (≤ 140 chars) shown on the site.
3. After the portal shows a score, record it as ORGANIZER-CONFIRMED in `docs/status.json`
   (`organizer_confirmed_score`) and in `evidence/run_card_h79.json`; never before.
