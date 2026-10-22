# Start-of-session contract

1. Read **all of README.md**, including the original prompt, then `run_card.json`,
   `reports/irregularities.md`, `registry/preregistration_h79_dilstep.json` (current research file) and
   `registry/preregistration_ffas.json` (archived FFAS) before work.
2. Work only on the Arena-assigned active session branch reported in the current session metadata. Do not hardcode a previous session's branch here. Never rename or switch branches. Historical branch names in immutable cards, reports or prior prompts are provenance, not instructions for a new session.
3. Active research file: **H79-DILSTEP** (this session), one preregistered experiment,
   verdict `negative`. It lost the holdout to the H33 control and failed the surface
   gate (same operative rule as shared `informative-halo-v4`, IR-79-86; recorded as
   IR-79-90 because IR-79-67 was already taken on main). Do not retune it, overlap-cap
   it, or place submission dots from it.
   **H79-FFAS** (session `c04e5e27`) is archived under `archive/h79_ffas_c04e5e27/` and
   stays stopped negative. Do not retune it.
   H79-NHR, H79-ASYM, H79-FF, H79-STEP, G79-THVC, G79-STEPCO, G79B-SDPT and
   G79-FABRIC-OFFSET stay **stopped negative** and archived; do not restart them,
   add jitter, or exempt dense priors for them.
   `scripts/preflight_new_lane.py --restore` exits 2 under the literal reading.
   That does not reopen stopped lanes.
4. `vendor/gems57` is shared code, not a private fork. Check its SHA-256
   pins (`registry/template_pin.json`). A real shared defect is fixed once in the shared module, with a
   version note and an IR entry. Example: `informative-halo-v4` overlap mode, IR-79-86.
   Use the shared evaluator, writer and novelty gate; never invent scientific metrics or receipts.
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
