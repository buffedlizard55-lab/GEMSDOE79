# Start-of-session contract

1. Read **all of README.md**, including the original prompt, then `run_card.json`,
   `reports/irregularities.md`, `registry/preregistration_arc.json` +
   `registry/preregistration_arc_amendment_X2.json` (canonical lane),
   `registry/preregistration_nhr.json` (archived negative lane) and
   `registry/preregistration.json` (archived E1) before work.
2. Work only on the Arena-assigned active session branch reported in the current session metadata. Do not hardcode a previous session's branch here. Never rename or switch branches. Historical branch names in immutable cards, reports or prior prompts are provenance, not instructions for a new session.
3. Canonical lane: **H79-ARC** (session 167a60a6), terminal with verdict `promote`
   after X1 + X2 (gate-instrument defect fix, identical bytes) under Amendments
   D-1+D-2+D-3 (`reports/protocol_amendment_D3_20261022.md`). X1's failed readings
   are preserved; if the owner reverses D-3/X2 the verdict reverts to negative.
   Do not retune, rerun or re-place X1/X2. **H79-NHR** stays stopped negative and
   archived at `archive/h79_nhr_337ac1e9/` (it also fails under D-3, IR-79-70);
   do not retune or overlap-cap it.
   A new idea needs a new preregistered lane, with three experiments or two hours at most.
   E1 (G79-FABRIC-OFFSET) stays **stopped negative** and archived; do not restart
   it, add jitter to it, or exempt dense priors for it.
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
