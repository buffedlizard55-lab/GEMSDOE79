# Session review `ff2e4413` (2026-10-22): G79-OPC

**Decision:**
- G79-OPC: OK TO DOWNLOAD (research artifact): YES. OK TO SUBMIT: NO.
- The project-wide decision is unchanged (`scripts/select_submission.py` exit 2). Slots used: 0.

## What was done (budget: 3 experiments in about 2 h, all used)
1. **Shared-tool fix, made once in the template.** Amendment D-3 (`vendor/gems57/uniqueness.py`, `IR-79-228`) chance-corrects the saturated exact-cell branch of D-2.
   - It was committed before any lane result.
   - The default behaviour is unchanged.
   - The pin chain was updated in `registry/template_pin.json`, `scripts/verify_project.py` and two tests.
2. **Preregistration:** `registry/preregistration_g79_opc.json` (sha in `registry/preregistration_g79_opc.sha256`).
   - Deviation D-OPC-1 (pre-result): the concordance sign/convention was fixed.
   - Deviation D-OPC-2 (post-result, disclosed): the holdout mask had used the full catalogue. The bug was fixed and the invalid run was preserved (`IR-79-229`).
3. **EXP-OPC-1/2 on seeds 20 and 30.** Each arm used the shared buffered holdout, shared evaluator, shared greedy placement and a leakage canary.
4. **EXP-OPC-3:**
   - live fit with 45,204 dots;
   - D-3 novelty over 1,232 rasters, of which 1,222 are comparable (992 frozen registry, frozen and live delta incl. `GEMSDOE89`, and local archives);
   - TIFF/ZIP written through `submission_writer`, then the validator, then `run_card_opc.json`, then the independent `scripts/opc_gate.py`.

## Results (HOLDOUT-DTI, `gems57-pooled-hide-v2`)
| Arm | Seed 20 (n = 11,321) | Seed 30 (n = 11,342) |
|---|---|---|
| EXP-OPC-2 full | 0.1207 [0.0968, 0.1448] | 0.1506 [0.1246, 0.1768] |
| EXP-OPC-1 oriented geometry | 0.0997 [0.0872, 0.1126] | 0.0693 [0.0584, 0.0810] |
| C-ISO isotropic control | 0.0533 [0.0396, 0.0685] | 0.0720 [0.0564, 0.0943] |
| C0 random | 0.0249 [0.0209, 0.0292] | 0.0378 [0.0322, 0.0428] |
| G79-THVC bar | 0.1905 | 0.1944 |

- **The anisotropy result did not replicate.** Oriented minus isotropic geometry was +0.0464 [0.0277, 0.0622] on seed 20 and −0.0027 [−0.0233, 0.0138] on seed 30.
- **G3 fails:** the 2-seed mean is 0.1357, below the 0.1963 bar.
- **G4 fails:** D-3 fired on 14 rows, covering 13 distinct dense dot-field paths. The worst chance-corrected overlap is 0.8264, against `GEMSDOE53` thin_bin. The literal 3-px rule fires on 119 rasters.
- **G2 passes:** the maximum single-feature AUC is 0.8036.
- **G1 (local shared validator) passes:** single band, EPSG:32611, 3730 × 3292, sample transform, finite values in [0, 1], and the ZIP holds identical bytes.
- **G1b (official R1–R8 validator, merged from `main` after the lane ran) FAILS R6.** The shared writer zero-fills outside the footprint, but the official text requires null/NaN there (IR-79-212/224/227). The file was not repackaged because the lane is closed and the writer policy needs an owner decision.

## Why H33 scored well and whether we can beat it (unchanged conclusion)
See [`knowledge/h33_review_e4a4422d.md`](../knowledge/h33_review_e4a4422d.md).
- H33 is a dense (~37.7k), near-catalogue dot field.
- DTI rewards recall within 300 m and penalises over-emission only through α = 0.2.
- Its 0.2778 is an unverified user report, not an organizer receipt.
- On the shared holdout, H33's fold-fair control scores 0.0961 / 0.0989. Several archived lanes beat that, including this one (0.1207 / 0.1506).
- No lane has beaten the leaderboard's 0.4413. HOLDOUT-DTI is not comparable to the leaderboard scale.

## Merge notes
- Concurrent `main` sessions used IR-79-207..220, so this session's IDs were renumbered to IR-79-228..230. Two sha-pinned files (`vendor/gems57/uniqueness.py` and the OPC preregistration) keep the original `IR-79-207` text, which is disclosed in IR-79-228.
- `main` had a gap at IR-79-221..223 left by a concurrent renumbering, which broke 3 tests. Pointer rows were added, and the full suite now passes (619 tests).

## Limitations
- Every TIFF in the repo, including this one, zero-fills outside the footprint and so fails official R6. A compliant future candidate needs a NaN-exterior writer mode, which is an owner decision.
- Catalogue-holdout labels are not the expert "new fault" labels that are actually scored, and the two seeds share geography.
- The full model's prior-corrected probabilities are under-calibrated about 5×, so it under-emits dots.
  - This was not fixed post hoc, because fixing it after seeing the holdout would be holdout peeking.
- 10 registry rasters are non-comparable (wrong grid, demo or corrupt files), so the novelty scan is "complete" only for comparable rasters.
- Organizer-side uniqueness rules and account slot capacity are unknown. The local gates are not organizer acceptance.
- The D-3 amendment is a project decision that the owner may reverse. If it is reversed, every nonempty candidate is blocked again under the literal rule.

## Suggested next work (each needs its own preregistration)
1. Inner-validated calibration of G79-OPC: fit the k_truth budget on simulated hides inside the training quadrants only, never on the holdout.
2. G79-SPRH spring/well Hough alignment (data are already pinned).
3. G79-SIGN signed scarp facing × gravity-step sign, as a shoreline/terrace veto.
4. Owner action: mirror USGS ComCat relocated seismicity and/or NASA OPERA DISP-S1 (needs an Earthdata login), so the external hypotheses become testable.
5. Owner decision: confirm or reverse amendment D-3. Under the literal one-sided rule, no new candidate can ever pass G4.
