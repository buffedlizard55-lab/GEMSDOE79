# Start-of-session contract

1. Read **all of README.md**, including the original prompt, then `run_card.json`,
   `reports/irregularities.md`, `registry/preregistration_g79_thvc.json` (canonical
   `G79-THVC` lane), `registry/preregistration_nhr.json` (archived `H79-NHR`), and
   `registry/preregistration.json` (archived `E1`) before work.
2. Work only on the Arena-assigned active session branch reported in the current session metadata. Do not hardcode a previous session's branch here. Never rename or switch branches. Historical branch names in immutable cards, reports or prior prompts are provenance, not instructions for a new session.
3. Canonical deliverable lane: **`G79-THVC`** (`g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`,
   `sha256: d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`, `35,093` binary dots),
   preregistered in `registry/preregistration_g79_thvc.json`. It achieved the highest `GEMSDOE79`
   two-seed `HOLDOUT-DTI` (`0.1905` Seed 20 / `0.1944` Seed 30 vs `H33 = 0.0961 / 0.0989`) and cleared all
   `718` sparse `<= 50k`-dot registry maps (`0.6844 <= 0.70`), while remaining fail-closed
   (`verdict: "negative"`, `ok_to_download: true`, `ok_to_submit: false`, `3/3` experiments used) under
   unchanged `vendor/gems57/uniqueness.py` space-filling/`80k` blankets (`IR-79-84`), post-index sibling
   `GEMSDOE83` collision (`0.7139 > 0.70`, `IR-79-89`), and unverified account weekly slot selection.
   Do not retune or overlap-cap `G79-THVC`.

   All ten sibling `GEMSDOE79` lanes are stopped and archival — never restart, retune, or add overlap caps to them:
   - **`H79-NHR`** (`archive/h79_nhr/`, `archive/concurrent_downloads/`, `IR-79-55`): `0.1431 / 0.1522`, stopped on 26 informative duplicates.
   - **`H79-STEP`** (`archive/h79_step_21642326/`, `IR-79-86`): `0.0949 / 0.1087`, below `H33` on Seed 20; stopped negative.
   - **`H79-ASYM`** (`run_card_asym.json`, `IR-79-74`): stopped at pre-placement surface duplicate gate (`0` placements).
   - **`H79-FF`** (`archive/h79_ff_1de1617f/`, `IR-79-66`): unpreregistered / unscored duplicate; quarantined.
   - **`G79B-SDPT`** (`archive/g79b_sdpt_67557396/`), **`G79-STEPCO`** (`archive/g79_stepco_s1/`), **`E2`** (`archive/concurrent_2026-10-22_5d14587/`), **`H79-CSPT`** (`archive/h79_cspt_3d386a3/`), **`H79-MCT`** (`archive/h79_mct_c26efec/`), and **`E1`** (`G79-FABRIC-OFFSET`, `archive/g79_fabric_offset_e1/`): all preserved read-only.
   A new idea needs a new preregistered lane (`<= 3` experiments or `<= 2` hours), subject to `scripts/preflight_new_lane.py --restore` (`exit 2` under the literal gate unless owner protocol amendment is ratified; see `IR-79-90`).
4. `vendor/gems57` is shared code, not a private fork. Check its SHA-256
   pins (`registry/template_pin.json`). A real shared defect is fixed once in the shared module, with a
   version note and an IR entry. Example: the `budget-matched-v3` dot definition, IR-79-47. Use the shared evaluator,
   writer and literal novelty gate; never invent scientific metrics or receipts.
5. Do not replace missing measurements with zero. Only a submission-page receipt
   establishes ORGANIZER-CONFIRMED for an artifact. Public leaderboard observations
   and user-reported scores must retain their evidence classes.
6. A local format PASS does not mean OK TO SUBMIT. `run_card.json`,
   `scripts/submission_status.py`, README and Pages must agree. They are all generated from
   or checked against the card by `scripts/verify_project.py`. Only
   `scripts/select_submission.py` may set `ok_to_submit` after re-deriving every gate.
   Weekly-slot availability stays an account-side condition that the user checks.
7. Keep large input/cache files ignored. Serve only docs/ in previews and artifact deployments; legacy Pages also has a root redirect. Never publish credentials,
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
