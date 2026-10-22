# Candidate hypotheses — session 31f55b3a (H79-DCE lane)

Written before any H79-DCE holdout result existed (preregistration:
[`registry/preregistration_dce.json`](../registry/preregistration_dce.json),
pinned `evidence/preregistration_dce_sha256.txt`).
Ranks are qualitative judgements of expected DTI improvement, uniqueness
survival and cost, **not scores**. Only hypothesis 1 was executed this session.

"Untried" was checked against `src/`, `scripts/`, `vendor/gems57/` and the
archived lanes (`archive/`); the wider GEMSDOE family's attempts are noted
where the score ledger records them. The objective novelty arbiter remains the
shared registry duplicate gate (992 rasters, 986 comparable after IR-79-58).

| Rank | Hypothesis, exact layers | Physical signature / transform | Why it should catch a fault *missing* from the USGS/INGENIOUS catalogue | Difference from anything in this repo | Expected gain / cost | Named non-fault mimic | Data viability |
|---|---|---|---|---|---|---|---|
| **1 (executed)** | **H79-DCE decorrelated cover emission.** Surface: the existing 58-feature nested hide-to-recover stack (19 supplied bands, multiscale derivatives, 10 lidar scarp bands, 8 radiometric bands, 6 visible-catalogue geometry inputs), rebuilt byte-identically to H79-NHR X1. Emission: 200 m catalogue collar + 3 px tile-cover decimation on `E[k] = p (*) k` (shared `gems57.emit.emit_decimated`) + per-raster 0.68 collision ceiling during placement | Not a new detector: a metric-native emission. The metric's TP is a per-truth-cell max over the 300 m kernel while FP is a per-dot sum, so after one dot covers a crest's kernel neighbourhood, neighbouring crest pixels are pure FP; tile-cover converts the same predicted credit into non-redundant 300 m cover, and the ceiling displaces excess registry overlap to unoccupied tiles instead of deleting dots | The surface already ranks discovery habitat best-in-repo (X1 HOLDOUT-DTI 0.1431/0.1522 vs H33 control 0.0961/0.0989); what failed was the *emission* (26 registry dot fields at 0.73–0.91 overlap). Recovering that credit with a decorrelated dot set is the only path to a promotable artifact from the best measured surface | No lane here has used tile-cover decimation, a placement-time ceiling, or the collar together. X1 used top-k Poisson; G79B-SDPT's amendment deleted already-placed dots (cost −0.0176/−0.0203); a placement-time allowance displaces instead | Highest expected P(all gates pass) / low (surface code reused; ~1 h compute) | Same as X1 (Lahontan shorelines, channel banks, mine benches); displacement can move dots onto mimics outside registry halos | All inputs restored and SHA-256 verified; surface rebuild hash-matched the frozen X1 receipt |
| 2 | **Geodetic-strain / seismicity corridor gating.** `geod_shearrate`, `geod_dilaterate`, `geod_2ndinv`, `deq_n100a15`, `ieq_n100a15` intersected with potential-field edges (`iso_grav_anom_hg`, `rtp`, `tc`) | Corridors where modern GPS/InSAR strain localizes across gravity-defined basement block boundaries | Young active strands with subtle Quaternary scarps concentrate where strain concentrates, independent of mapping effort/bias; compilations under-map them because scarps are sub-10 m | Strain bands were only 6 of 58 X1 inputs, never a gating surface; GEMSDOE74 (triregime-radon, 0.0669 user-reported) and GEMSDOE36 (anderson-pinn, 0.2750) are siblings' related takes | Medium / medium | Magmatic/tectonic strain around volcanic centers; GPS/InSAR processing artifacts | Inputs present |
| 3 | **Antislope-scarp asymmetry** (untried #2 from `hypotheses_nhr.md`). Lidar `upface_max` vs `downface_max`, `coh100`, strike; `iso_grav_anom_hg` | Ratio of uphill-facing to downhill-facing band-passed step gradient, coherent along strike | Uphill-facing (antithetic) intrabasin scarps are under-represented in regional compilations; shorelines, channel banks and fan toes face downslope, so the ratio suppresses the main mimics | `upface_max` is only one of 58 inputs; no surface uses the asymmetry itself | Medium / low | Ridge-top sackung and landslide head scarps (also uphill-facing) | Inputs present; high collision risk with the 12GEMSDOE r7 scarp family |
| 4 | **Nested-target distance-band reweighting** (README next-step 3). Same X1 machinery with the kernel-credit target reweighted toward far-field (> 1 km) training pixels | Learned far-field conditional ranking | Expert faults may sit farther from mapped traces than withheld catalogue faults do; a far-field-tilted target hedges that shift | Target reweighting not implemented anywhere here | Low–medium on the real test, **negative on the holdout** (which rewards catalogue proximity) / medium | Far-field lineaments of non-fault origin (shorelines, joints) | Inputs present |
| 5 | **Lahontan shoreline suppression via absolute elevation** (untried #3 from `hypotheses_nhr.md`). Lidar `step_max`/`downface_max` + strike + absolute elevation | Down-weight steps that are contour-parallel within ±15 m of pluvial shoreline altitudes (highstand ≈1330 m, [USGS Benson & Thompson 1987](https://pubs.usgs.gov/publication/70015223)) | Removes the dominant false-positive population, freeing budget for real faults | Not implemented here | Medium / medium | Real faults paralleling a shoreline get suppressed | **Needs absolute 3DEP elevation** — not in the sandbox allowlist; free official source: [USGS 3DEP / The National Map](https://www.usgs.gov/3d-elevation-program). Not viable this session |

## Why hypothesis 1 was chosen

The user's requirement is a *unique, submittable* artifact. Three of the four
systemic blockers measured so far — 26 ordinary dot fields, the emission's
crest concentration, and the collar FP — are emission problems, not detector
problems, and the repo already owns the best measured detector surface. The
fourth and fifth blockers (30 space-filling rasters, 6 not-comparable files)
are registry-side and are resolved once in the shared tool (IR-79-57/58).
Hypotheses 2–5 all start new detectors whose holdout power is unproven; under
the protocol's own gate ("do not spend a submission slot on an idea that has
not beaten the current holdout best") they carry more risk for the same slot.

## Result (2026-10-22, recorded after the holdout, before final packaging)

Executed as preregistered (`registry/preregistration_dce.json`, hash-pinned before any result).
The surface rebuilt byte-identically to the frozen X1 receipt (SHA-256 match), the at-risk scan
froze 182 capped rasters (uncapped overlap > 0.50; worst uncapped 0.926 vs 0.612 chance), and the
capped emission placed exactly 37,654 dots with every capped raster at or below 0.67998.

HOLDOUT-DTI (`gems57-pooled-hide-v2`, 4 folds, seeds 20/30, n = 11,321 / 11,342):

| arm | seed 20 | seed 30 |
|---|---|---|
| **candidate (capped cover)** | **0.1019** [0.0888, 0.1153] | **0.1048** [0.0887, 0.1217] |
| cover, uncapped (cap-free control) | 0.1210 [0.1071, 0.1358] | 0.1229 [0.1060, 0.1405] |
| top-k + collar (no tile-cover) | 0.1463 | 0.1524 |
| X1 recipe reproduction (context) | 0.1462 | 0.1522 |
| H33 fold-fair control | 0.0961 | 0.0989 |
| uniform random control | 0.0151 | 0.0151 |

- Paired Δ vs H33 control: **+0.0058 [−0.0100, +0.0214]** and **+0.0059 [−0.0102, +0.0215]** —
  the 95 % CIs include zero on both seeds, so gate g3 (beat with CI lower bound > 0 on both
  seeds) **fails**. Verdict: **negative**; no weekly slot spent.
- Paired Δ vs uniform: +0.0868 [+0.0742, +0.1000] and +0.0897 [+0.0739, +0.1056] (g4 passes).
- Measured cap cost (uncapped cover − candidate): **0.0191 / 0.0181**; the tile-cover decimation
  itself costs a further 0.0253 / 0.0295 versus top-k + collar. Together they consume the entire
  X1-class gain (+0.0501 / +0.0533), which is exactly the pre-stated limitation below.
- Leakage canaries pass on both seeds (max single-feature AUC 0.8514 / 0.8589, worst
  `geom_log_dist_visible_tip`); the X1 recipe reproduction arm lands within 0.004 of the frozen
  X1 holdout numbers on both seeds, confirming the shared fold machinery.

## Known limitation, stated before results

Capping displaces dots off proven habitat onto lower-credit tiles; the measured
cap cost (paired `cover_uncapped_control` arm) is the honest price of
uniqueness. If that price drops the candidate below the H33 fold-fair control
on either seed, the verdict is negative and no slot is spent.
