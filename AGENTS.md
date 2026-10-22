# Start-of-session contract

1. Read **all of README.md**, including the full original prompt, then `run_card.json` (canonical `G79-THVC`),
   `reports/irregularities.md`, `registry/preregistration_g79_thvc.json`,
   `registry/preregistration_h79_dilstep.json` (archived DILSTEP), and
   `registry/preregistration_ffas.json` (archived FFAS) before any work.
2. Work only on the Arena-assigned active session branch reported in the current session metadata. Do not hardcode a previous session's branch here. Never rename or switch branches. Historical branch names in immutable cards, reports or prior prompts are provenance, not instructions for a new session.
3. Canonical research file in `docs/downloads/`: **`G79-THVC`** (`g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`), achieving the highest shared `gems57-pooled-hide-v2` `HOLDOUT-DTI` across all **17** `GEMSDOE79` lanes (**`0.1905`** on Seed 20, **`0.1944`** on Seed 30 vs `H33` fold-fair control `0.0961 / 0.0989`), verdict `negative` (`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`, `0` weekly slots spent) because of non-sparse / corridor registry overlap (`28` under `informative-halo-v4`, `58` under `budget-matched-v3`, `96` literal, plus live `GEMSDOE83 = 0.7139 > 0.70`, while `0 / 718` sparse `<= 50k` pinned submissions fire at `max = 0.6844 <= 0.70`).
   All concurrent/historical `GEMSDOE79` lanes stay **stopped negative** and byte-archived under `archive/`:
   - `G79-CSMD` (`0.1629 / 0.1749` multi-regime Charnes-Cooper; `0.1817 / 0.1967` unconstrained; `0.0996 / 0.1119` zero-catalogue pure physics `> H33`, session `1dc8cff0`, `run_card_csmd.json`, `archive/g79_csmd_1dc8cff0/`, & `evidence/csmd/`) — `0 / 939` comparable sparse duplicates (`<= 75,308` dots, `max = 0.6961 <= 0.70`, `GEMSDOE83 = 0.5921 <= 0.70`, `G79-THVC = 0.6893 <= 0.70`); stopped negative under wide density sweeps (`> 75,308` dots; `IR-79-145`)
   - `H79-NHR` (`0.1431 / 0.1522`, `archive/h79_nhr/` & `archive/h79_nhr_337ac1e9/`)
   - `H79-FNHR` (`0.1292 / 0.1431`, session `a57e2a7f`, `run_card_fnhr.json`, `archive/h79_fnhr_a57e2a7f/`, & `evidence/fnhr/`) — `0 / 934` comparable sparse duplicates (`<= 75,308` dots, `max = 0.6726 <= 0.70`; `IR-79-142`)
   - `H79-MRND` (`0.1044 / 0.1236`, session `800321e2`, `run_card_mrnd.json` & `evidence/mrnd/`) — multi-regime nested discovery (`77` features, `max AUC = 0.8589 <= 0.90`); beats `H33` control on both seeds (`+0.0247`, 95% CI `[+0.0095, +0.0389]` on Seed 30) and clears all `982` informative comparable priors on chance-corrected overlap (`worst = 0.5486 <= 0.70`, `0` normal-budget `<=167k` flags), stopped pre-placement under literal one-sided overlap (`IR-79-132`); do not retune quotas or re-place dots
   - `H79-STEP` (`0.0949 / 0.1087`, `archive/h79_step_21642326/`)
   - `H79-DILSTEP` (`0.0721 / 0.0689`, `archive/h79_dilstep_6444be2d/`)
   - `H79-COV` (`0.0610 / 0.0581`, `archive/h79_cov_e23d5371/`)
   - `H79-FF` (`0.0510 / 0.0488`, `archive/h79_ff/` & `archive/h79_ff_1de1617f/`)
   - `H79-ML-STRAIN-RELAY` (`0.0472 / 0.0442`, `archive/concurrent_2026-10-22_5d14587/`)
   - `G79-STEPCO` (`0.0468 / 0.0422`, `archive/g79_stepco_s1/` & `archive/g79_stepco_s2/`)
   - `H79-FFAS` (`0.0422 / 0.0367`, `archive/h79_ffas_c04e5e27/`)
   - `G79-BER` (`0.0788 / 0.0882`, `archive/g79_ber_4f80e0d0/`) — session 4f80e0d0, merged after the 17-lane snapshot; terminal `run_card_ber.json`, not unique under amendment D-2 (IR-79-128); do not retune its band quotas or re-place its dots
   - `G79B-SDPT` (`0.0297 / 0.0290`, `archive/g79b_sdpt_a3/`)
   - `H79-FGR` (`0.0058 / 0.0056`, `archive/fgr_cb54ff09/`)
   - `G79-MAG` (`0.0045 / 0.0067`, `archive/g79_mag_730d5ee7/`)
   - Surface-stopped / quarantined: `G79-FABRIC-OFFSET`, `H79-ASYM`, `H79-MCT`, `H79-CSPT`, `G79B-SCARP-DIPOLE-GEOAND`.
   Do not restart stopped lanes, retune on holdout, add overlap caps/jitter, or exempt dense priors locally. `scripts/preflight_new_lane.py --restore` exits `2` under the literal reading.
4. `vendor/gems57` is shared code, not a private fork. Check its SHA-256
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
   or checked against the card by `scripts/verify_project.py`. Only
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
