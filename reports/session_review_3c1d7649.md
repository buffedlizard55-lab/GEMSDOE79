# Session review — G79-XCR (branch `arena/3c1d7649-gemsdoe79`, 2026-10-22)

Three passes, in the order they were run. Every number carries its evidence class.
No previous raster was copied, renamed or re-placed, and no competition slot was used.

## Pass 1 — implement and verify

1. **Verified the official format from the bytes, not from prose.** The official
   `data/reference/sample_submission.tif` contains **7,111,787 NaN cells** outside
   the footprint, `nodata = NaN`, and 0/1 values inside (`evidence/xcr/official_sample_bytes.json`).
   The problem page says "data outside the bounds is null or nan"
   (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>).
   The shared writer could only emit zeros outside, and the project's own
   official-format validator therefore rejected every artifact at R6. **This was a
   real shared defect, and it was the format dead end.** Fixed once in
   `vendor/gems57` as an opt-in `exterior="nan"` mode (IR-79-232); the four
   changed files were re-pinned in `registry/template_pin.json` with an
   amendment record, and every existing caller keeps `exterior="zeros"`.
2. **Built a second validation instrument.** All archived lanes score
   hide-and-recover on the QFDB catalogue. The competition truth is the opposite
   population. I2 uses SGMC fault pixels more than 3 px from the catalogue
   (62,122 of 83,593 px, 2,115 components — `evidence/xcr/sgmc_overlap.json`).
   SGMC is never a feature, so the instrument is independent of the model.
3. **Preregistered the lane before scoring** (`registry/preregistration_g79_xcr.json`,
   SHA-256 pinned in `evidence/xcr/preregistration_sha256.txt`): 14 label-blind
   physics channels + 4 catalogue-geometry channels, out-of-fold component-masked
   HistGradientBoosting, three emission arms, fixed parameters, one
   promotion gate.
4. **Ran leakage canaries first** on both instruments (144 rows, seed 20). No
   feature exceeded 0.90. The canaries produced the session's key measurement:
   catalogue-proximity channels score 0.72–0.84 on I1 but 0.43–0.55 on I2, while
   terrain channels score 0.53–0.68 on I1 and 0.75–0.79 on I2.
5. **Ran the holdout.** Three arms were measured. The ML surface with a
   37,654-dot blanket budget reached I1 0.043–0.059; the calibrated
   marginal-DTI emitter reached 0.002–0.003; a mass-matched sparse budget
   reached 0.001–0.003; the catalogue-corridor surface reached 0.09–0.13. The
   blanket-budget arm beat every smarter emitter, which is a negative result
   about emitter calibration and is recorded as such.
6. **Shipped surface** = `0.5·rank(dens_visible_40) + 0.5·rank(relief × step)`,
   emitted at 37,654 dots with 3 px NMS, NaN exterior.
   I1: **0.1234** (seed 20, n = 11,321) / **0.1211** (seed 30, n = 11,342),
   point estimates, no bootstrap interval computed for this arm.
   I2: 0.231 / 0.236 / 0.188 / 0.284 per fold vs uniform 0.152 / 0.190 / 0.134 /
   0.199 — the surface beats its own uniform control in 4/4 folds (seed 20 only;
   the seed-30 uniform control was not measured and is not claimed).
7. **Restored all 992 frozen registry blobs** by git protocol and SHA-256
   verified them, then scanned the candidate: 986 comparable of 1,199 indexed,
   213 non-comparable, `complete_accessible_scan = true`. Max |ρ| **0.1097**;
   **18 like-for-like firings**, worst dot-field overlap **1.0**.

## Pass 2 — review for bugs and wrong assumptions

Four real defects were found and fixed before any number was reported:

| Defect | Effect if unfixed | Fix |
|---|---|---|
| The first out-of-fold design zeroed the surface inside the 3 px collar of every fault | Deleted the only band where the competition kernel has support; all emitter arms scored ~0.05 on noise | Predict everywhere; withhold the collar from **training** only |
| The first inner-partition target set the target only on a group's own components, where credit to *other* components is ~0 | No positive and negative samples; the fit refused to run | Replaced with an out-of-fold per-group surface (`xcr.oof_surface`) |
| The raw regressor output was passed to `greedy_allocate` as a probability | Its total expected credit (≈30,000) exceeded the truth mass (≈2,800), so the exact marginal test accepted 29k background dots (I1 0.003) | Calibrated the surface so Σ expected credit = a label-blind truth-mass proxy; the failure is still reported as a negative result |
| The receipt JSON contained `NaN` | `json.dumps(allow_nan=False)` crashed the writer after the raster was staged | `nodata` serialized as the string `"nan"` in `validate`; the on-disk raster was validated separately |

Assumptions checked:

- **"NaN outside is required."** Verified against the official page text *and*
  the official template bytes. Not inferred from the earlier portal error; the
  cause of that error still has no receipt and remains unverified.
- **"SGMC is independent."** SGMC is a different compilation. It is **not**
  independently authenticated as a truth set, it contains pre-Quaternary faults,
  and it is used only as a *ranking* instrument, never as an organizer score.
- **"The two seeds are independent."** They are not. They reuse the same region
  and catalogue; their positive counts are never added.
- **"Format PASS means submittable."** It does not. The card and the page say so
  explicitly.

## Pass 3 — re-check against the request, improve, record limits

Against the original request:

| Requirement | Status |
|---|---|
| Answer why 0.2778 led and whether it can be beaten, with the metric algebra | Done, with the recall inversion `r ≈ 0.8·DTI/(1 − 0.2·DTI)`. The 0.2778 figure stays an UNVERIFIED HISTORICAL REPORT |
| 3–5 new hypotheses with layers, signature, off-catalogue argument, novelty vs repo | Five, ranked, in `research/hypotheses_xcr.md` |
| Validate the top candidate on a spatially blocked holdout before a slot | Done on two instruments; the gate failed, so no slot was used |
| A unique, easy-to-download TIF with an obvious verdict | Byte-unique and format-compliant, **not** protocol-unique. The verdict is on the filename, the page, the card and the README: **DOWNLOAD YES / SUBMIT NO** |
| Inspection through the project, no human inspector | Every gate is a script; the verdict is a function of the bytes |
| No hallucination; every number labelled | Every table cell in the card names its class; unmeasured values (CIs, seed-30 uniform) are explicitly absent rather than filled |

Remaining limitations, stated rather than hidden:

1. **The candidate is a duplicate** under the like-for-like reading (18 firings,
   worst 1.0). The cause is structural: the surface is half catalogue-corridor
   density, which is the shared ancestor of all 937 archived dot fields.
2. **Emitter science did not work.** The exact marginal-DTI emitter lost to a
   blanket budget, because the surface is not calibrated far from the catalogue.
   That is reported as a negative result, not retuned.
3. **No confidence interval** for the shipped arm. The seed-20/30 point
   estimates are not a paired comparison, and no bootstrap was run.
4. **I2 is a proxy**, not organizer truth. It measures transfer to a different
   compilation, which is *closer* to the competition target than I1 but is not
   the same population.
5. **The registry is owner-repository-bounded.** 213 of 1,199 indexed rasters were
   non-comparable (grid-invalid or unreadable). Private or unlinked organizer
   submissions cannot be observed.
6. **No weekly slot was used and no leaderboard claim is made.** The 0.4413 figure
   is a public-leaderboard observation, not this project's score.
7. **Thermal, permeability and economic claims are out of scope.** This is fault
   mapping, not proof of a geothermal resource.

## Files produced

- Raster: `docs/downloads/research/gems79-xcr-corridor-rugged-20261022-DO-NOT-SUBMIT.tif`
  (+ `.zip`, + `.json` receipt), SHA-256 `74ec512b…7cfb0b`
- Lane code: `src/gems79/xcr.py`, `scripts/run_g79_xcr.py`,
  `scripts/build_xcr_submission.py`, `scripts/xcr_uniqueness.py`
- Preregistration: `registry/preregistration_g79_xcr.json` + SHA-256 pin
- Evidence: `evidence/xcr/{official_sample_bytes,official_convention_receipt,sgmc_overlap,canaries_seed20,holdout_seed20,shipped_surface_holdout,uniqueness_final}.json`
- Card: `evidence/run_card_xcr.json`; page: `docs/g79-xcr.html`
