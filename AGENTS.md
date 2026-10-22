# Start-of-session contract

1. Read **all of README.md**, including the original prompt, then `run_card.json`,
   `reports/irregularities.md`, `registry/preregistration_ffas.json` (active lane) and
   `registry/preregistration_nhr.json` (archived NHR) before work.
2. Work only on the Arena-assigned active session branch reported in the current session metadata. Do not hardcode a previous session's branch here. Never rename or switch branches. Historical branch names in immutable cards, reports or prior prompts are provenance, not instructions for a new session.
3. Active lane: **H79-FFAS** (session `c04e5e27`), opened because the prompt again
   contains no assigned method paragraph (IR-79-83) and previous lanes are stopped.
   Preregistered before any holdout result. X1 (closed-form far-field antislope
   scarp) is the only experiment and is **stopped negative**. Do not retune it
   against the holdout; X2/X3 are for shared-tool defects only.
   H79-NHR, H79-ASYM, H79-FF, G79-STEPCO, G79B-SDPT and G79-FABRIC-OFFSET stay
   **stopped negative** and archived; do not restart them, add jitter, or exempt
   dense priors for them.
   Follow-up reviews on `main` re-measured the universal literal-overlap witness:
   `scripts/preflight_new_lane.py --restore` exits 2 under the *literal* reading.
   H79-FFAS used shared `informative-halo-v4` (IR-79-82) declared in its
   preregistration; that does not reopen stopped lanes.
4. `vendor/gems57` is shared code, not a private fork. Check its SHA-256
   pins (`registry/template_pin.json`). A real shared defect is fixed once in the shared module, with a
   version note and an IR entry. Example: `informative-halo-v4` overlap mode, IR-79-82.
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
