# Start-of-session contract

1. Read **all of README.md**, including the full original prompt, then `run_card.json` (canonical `G79-THVC`),
   `reports/irregularities.md`, `registry/preregistration_g79_thvc.json`,
   `registry/preregistration_h79_dilstep.json` (archived DILSTEP), and
   `registry/preregistration_ffas.json` (archived FFAS) before any work.
2. Work only on the Arena-assigned active session branch reported in the current session metadata. Do not hardcode a previous session's branch here. Never rename or switch branches. Historical branch names in immutable cards, reports or prior prompts are provenance, not instructions for a new session.
3. Canonical research file in `docs/downloads/`: **`G79-THVC`** (`g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`), verdict **negative**: **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** It is inherited, not a newly generated or unique candidate. Full literal novelty fails both before and after placement (maximum forward overlap 1.0); the frozen scans have 1,108 rows, 1,088 comparable and 20 non-comparable entries. Sparse-only passes, low correlation, amended diagnostics and manual upload cannot override this refusal.
   `src/gems79/evidence_summary.py` derives current site tables from both seeds of the frozen shared evaluator (`official_evaluate_all`). Do not mix that output with the separate historical bootstrap, add seed counts as independent observations, or claim all-lane/leaderboard superiority from it. The original card and explicit metadata correction are preserved under `evidence/review_e4a4422d/`; TIFF/ZIP and scientific receipts are unchanged. Read `knowledge/h33_review_e4a4422d.md` and `research/hypotheses_e4a4422d.md` for corrected interpretation and data-source limits. Historical numeric summaries below are archival context, not a new matched benchmark.
   All concurrent/historical `GEMSDOE79` lanes stay **stopped negative** and byte-archived under `archive/`:
   - `G79-DFSD` (`0.1621 / 0.1647` `20,611`-px core, `0.2107 / 0.2245` NW Fold 0; `0.1724 / 0.1751` `EXP-DFSD-2` uniform `d=2.8 px > G79-THVC 0.1697 / 0.1686`; `0.0960 / 0.1001` `EXP-DFSD-1` split-sensor zero-catalogue physics `> H33` with `0.342–0.561 <= 0.70` peer overlap across all 6 champions, session `d7da950d`, `archive/g79_dfsd_d7da950d/`, `run_card_dfsd.json` & `evidence/g79_dfsd_results.json`, `IR-79-204`..`IR-79-206`)
   - `G79-CSMD` (`0.1629 / 0.1749` multi-regime Charnes-Cooper; `0.1817 / 0.1967` unconstrained; `0.0996 / 0.1119` pure zero-catalogue physics `> H33`, `archive/g79_csmd_1dc8cff0/`, `run_card_csmd.json` & `evidence/csmd/`, `IR-79-201`..`IR-79-203`) — `0 / 939` comparable sparse duplicates (`<= 75,308` dots, `max = 0.6961 <= 0.70`, `GEMSDOE83 = 0.5921 <= 0.70`); stopped negative under wide density sweeps (`> 75,308` dots; `IR-79-203`)
   - `G79-CSKD` (`0.1781 / 0.2145`, 2-seed mean `0.1963` — #1 Seed-30 & #1 2-seed mean in `GEMSDOE79`, `0.6137 <= 0.70` vs `GEMSDOE83`, session `6da2620c`, `archive/g79_cskd_6da2620c/` & `evidence/g79_cskd_results.json`, `IR-79-198`..`IR-79-200`)
   - `H79-NHR` (`0.1431 / 0.1522`, `archive/h79_nhr/` & `archive/h79_nhr_337ac1e9/`)
   - `H79-FNHR` (`0.1292 / 0.1431` `F3`, `0.0906 / 0.0966` pure zero-catalogue physics, `archive/h79_fnhr_a57e2a7f/` & `run_card_fnhr.json`, `IR-79-140`..`IR-79-142`)
   - `H79-MRND` (`0.1044 / 0.1236`, session `800321e2`, `run_card_mrnd.json` & `evidence/mrnd/`) — multi-regime nested discovery (`77` features, `max AUC = 0.8589 <= 0.90`); beats `H33` control on both seeds (`+0.0247`, 95% CI `[+0.0095, +0.0389]` on Seed 30) and clears all `982` informative comparable priors on chance-corrected overlap (`worst = 0.5486 <= 0.70`, `0` normal-budget `<=167k` flags), stopped pre-placement under literal one-sided overlap (`IR-79-132`); do not retune quotas or re-place dots
   - `H80-PILOTS` (`H80-DRAPE-PILOT` `0.1190 / 0.1235`, `H80-RADIO-PILOT` `0.0085 / 0.0097`, `run_card_h80_pilots.json`, `evidence/h80_drape_pilot/` & `evidence/h80_radio_pilot/`, `IR-79-149`..`IR-79-151`)
   - `G79-ETP` / `G79-ETP-v2` (`0.0968 / 0.1061` fold-fair `gems57-pooled-hide-v2`, `0.0000` static full-catalogue, `archive/g79_etp_incoming_45998a01/run_card_etp_root.json` & `archive/g79_etp_incoming_45998a01/evidence/run_card_etp.json`, `IR-79-147` / `IR-79-158`)
   - `H79-STEP` (`0.0949 / 0.1087`, `archive/h79_step_21642326/` & `archive/h79_step_21642326/run_card_step.json`)
   - `H79-DILSTEP` (`0.0721 / 0.0689`, `archive/h79_dilstep_6444be2d/` & `run_card_dilstep.json`)
   - `G79-CFSKD` (`0.0654 / 0.0678`, `archive/g79_cfskd_bda00cff/` & `run_card_cfskd.json`, `IR-79-155` / `IR-79-162`)
   - `H79-FF1` (`0.0641 / 0.0631`, `archive/g79_ff1/` & `run_card_ff1.json`, `IR-79-125`)
   - `H79-BQA` (`0.0616 / 0.0604`, `archive/h79_bqa/` & `run_card_bqa.json`, `IR-79-126`)
   - `H79-COV` (`0.0610 / 0.0581`, `archive/h79_cov_e23d5371/` & `run_card_cov.json`)
   - `H79-FF` (`0.0510 / 0.0488`, `archive/h79_ff_1de1617f/` & `evidence/ff/`)
   - `H79-ML-STRAIN-RELAY` (`0.0472 / 0.0442`, `archive/concurrent_2026-10-22_5d14587/`)
   - `G79-STEPCO` (`0.0468 / 0.0422`, `archive/g79_stepco_s1/`, `archive/g79_stepco_s2/` & `run_card_stepco.json`)
   - `H79-FFAS` (`0.0422 / 0.0367`, `archive/h79_ffas_c04e5e27/` & `evidence/ffas/`)
   - `G79-BER` (`0.0788 / 0.0882`, `archive/g79_ber_4f80e0d0/` & `run_card_ber.json`) — session 4f80e0d0, merged after the 17-lane snapshot; terminal `run_card_ber.json`, not unique under amendment D-2 (IR-79-128); do not retune its band quotas or re-place its dots
   - `G79B-SDPT` (`0.0297 / 0.0290`, `archive/g79b_sdpt_67557396/` & `run_card_g79b.json`)
   - `H79-FGR` (`0.0058 / 0.0056`, `archive/fgr_cb54ff09/` & `evidence/fgr/`)
   - `G79-MAG` (`0.0045 / 0.0067`, `archive/g79_mag_730d5ee7/` & `archive/g79_mag_730d5ee7/run_card_g79_mag.json`)
   - `G79-CJX-DIR` (`0.0256 / 0.0319` candidate EXP2, below EDGE/UNIFORM controls; phase-randomized null `0.0338 / 0.0324` beats the real σ=2 junction surface `0.0225 / 0.0230`; `archive/g79_cjxdir/` & `run_card_cjxdir.json`, `IR-79-194`) — cross-scale RTP×gravity director-junction lane, preregistered `registry/preregistration_cjxdir.json`, 3/3 arms exhausted; do not retune its scales, budget or placement   - Surface-stopped / quarantined: `G79-FABRIC-OFFSET`, `H79-ASYM`, `H79-MCT`, `H79-CSPT`, `G79B-SCARP-DIPOLE-GEOAND`.
   - `G79-CJX` (`0.1041 / 0.1063` tip-steered, Exps 1-2 below random, `run_card_cjx.json`, `evidence/cjx/`, TIF in `artifacts/cjx/`) — unique TIF generated 2026-10-22, verdict **negative**: G3 holdout failed vs THVC incumbent, G4 literal failed vs the 100%-footprint diagnostics witness; do not re-place its dots or rename it as a submission.
   - `G79-SWER` (`0.0117 / 0.0113`, equal-support uniform control `0.0606 / 0.0610`, `run_card_swer.json`, `evidence/swer/`, TIF/ZIP in `artifacts/swer/`, `IR-79-207`..`IR-79-212`) — fixed dependent/independent swarm-excess × magnetic/gravity coherence × strain × cover lane; new byte-distinct TIFF is format-valid but literal witness overlap is `1.0000 > 0.70`; verdict **negative**, `OK TO DOWNLOAD: YES`, `OK TO SUBMIT: NO`; do not retune, thin support, place, rename, or upload it.
   Do not restart stopped lanes, retune on holdout, add overlap caps/jitter, or exempt dense priors locally. `scripts/preflight_new_lane.py --restore` exits `2` under the literal reading.
4. `vendor/gems57` is shared code, not a private fork. Most files match the upstream pin; `uniqueness.py` contains documented shared amendments (see `vendor/README.md`). Check its SHA-256
   pins (`registry/template_pin.json`). A real shared defect is fixed once in the shared module, with a
   version note and an IR entry. Example: `informative-halo-v4` overlap mode, IR-79-86.
   Amendment D-2's chance-corrected overlap (`compare_array_to_registry_d2`, IR-79-128)
   coexists in the same module; the D-3 saturated-branch question needs a prospective
   owner decision, never a post-hoc edit to pass a finished lane.
   Use the shared evaluator, writer and novelty gate; never invent scientific metrics or receipts.
5. Do not replace missing measurements with zero. Only a submission-page receipt
   establishes ORGANIZER-CONFIRMED for an artifact. Public leaderboard observations
   and user-reported scores must retain their evidence classes.
6. A local format PASS does not mean OK TO SUBMIT. `run_card.json`,
   `scripts/submission_status.py`, README and Pages must agree. They are all generated from
   or checked against the card by `scripts/verify_project.py`. A manual upload is not an exception to failed gates. Only
   `scripts/select_submission.py` may set `ok_to_submit` after re-deriving every gate.
   Weekly-slot availability stays an account-side condition that the user checks, and DOE Rules §3.4 restricts each participating entity to **one final submission**.
7. Keep large input/cache files ignored. Serve only `docs/` in previews and artifact deployments; legacy Pages also has a root redirect. Never publish credentials,
   invented source data, synthetic scientific scores, or a quarantined file as ready.
8. Run tests, offline byte/format verification, site link checking and a final
   requirements review. Record all three review passes and unresolved limitations.

- Concurrent H79-MCT material is historical text/data under `archive/`; do not
  reactivate its dense-prior exemptions, placement amendments or positive flags.
  E1 is stopped. Any protocol clarification must be recorded as an IR entry
  and applied once in shared code, never as a lane-local bypass.

- PR #12 H79-CSPT is also historical/non-authoritative under
  `archive/h79_cspt_3d386a3/`. It excluded space-filling priors and changed the
  shared novelty module; neither promotion nor the local fork is adopted.
  Before publishing run `scripts/verify_project.py`: its publication contract
  rejects a conflicting README, extra upload artifacts or a replaced inventory.
