# Archived lane: G79-BER X1 (session 4f80e0d0, negative, DO NOT SUBMIT)

Band-stratified evidence recovery: five distance-to-catalogue bands, one
nested-hide gradient-boosted model per band, area-proportional quotas, new
multi-height worm / basement-step / antislope transforms. Preregistered in
[`registry/preregistration_ber.json`](../../registry/preregistration_ber.json)
before any result; full analysis in
[`reports/ber_analysis.md`](../../reports/ber_analysis.md); run card at
[`run_card_ber.json`](../../run_card_ber.json); machine evidence in
[`evidence/ber/`](../../evidence/ber/).

| | |
|---|---|
| HOLDOUT-DTI (`gems57-pooled-hide-v2`) | seed 20: **0.0788** [0.0684, 0.0889], n = 11,321 · seed 30: **0.0882** [0.0739, 0.1011], n = 11,342 |
| H33 fold-fair control (the bar) | 0.0961 · 0.0989 — **candidate below the bar on both seeds** |
| Paired Δ vs H33 control | −0.0173 [−0.0287, −0.0055] · −0.0106 [−0.0245, +0.0044] |
| Paired Δ vs uniform | +0.0288 [0.0185, 0.0386] · +0.0385 [0.0248, 0.0508] (beats chance; not enough) |
| Leakage canary | 680 single-feature AUC tests over 85 features, max 0.8589 ≤ 0.90: PASS |
| Uniqueness (amendment D-2) | **Not unique under D-2 as preregistered.** Worst Spearman ρ 0.314 and worst chance-corrected overlap 0.654 against all 982 informative comparable registry rasters (both within limits), but 4 full-footprint diagnostic surfaces fire the saturated-halo exact test (IR-79-68) and 6 of 992 registry rasters are not comparable on this grid. Placement was therefore never run; the TIFF below serialises the audited provisional top-quota dots once, as negative evidence. |
| Verdict | **negative**. No retuning, no capping, no second experiment. `ok_to_submit: false`; no submission slot used. |

Artifact (research only):

| | |
|---|---|
| File | [`downloads/gems79-ber-banded-research-37654dots-20261022T054737Z-ad519409-DO-NOT-SUBMIT.tif`](downloads/gems79-ber-banded-research-37654dots-20261022T054737Z-ad519409-DO-NOT-SUBMIT.tif) · ZIP alongside |
| SHA-256 | `934b5c50dfe79553c7ccd674932854bfa4ed474fd7e46b9385deaf4c56dbc89b` |
| Dots SHA-256 | `ad5194091950f47972aadc28fcf4d115753734d700832a1007e4fb8e7900c276` |
| Format | single-band float32, EPSG:32611, 3730 × 3292, values exactly 0/1, all finite, no nodata sentinel: local format PASS (a format pass is not permission to submit) |

The canonical site artifact remains the H79-NHR research GeoTIFF in
`docs/downloads/` (IR-79-52 single-artifact contract). Nothing in this lane
changed it.
