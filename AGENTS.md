# Start-of-session contract

1. Read **all of README.md**, including the original prompt, then `run_card.json`,
   `reports/irregularities.md`, `registry/preregistration_fnhr.json` (active lane),
   `registry/preregistration_nhr.json` (archived NHR) and `registry/preregistration.json`
   (archived E1) before work.
2. Work only on the Arena-assigned active session branch reported in the current session metadata. Do not hardcode a previous session's branch here. Never rename or switch branches. Historical branch names in immutable cards, reports or prior prompts are provenance, not instructions for a new session.
3. Active lane: **H79-FNHR** (session a57e2a7f), preregistered before execution in
   `registry/preregistration_fnhr.json` (SHA-256 locked in `evidence/fnhr/preregistration_sha256.txt`)
   within the 3-experiment budget (`F1`, `F2`, `F3`). All three arms cleared single-feature
   leakage canaries (`<= 0.8262`) and beat `H33` with paired 95 % CIs strictly `> 0` on both
   `seed 20` and `seed 30` (`F1`: `0.1078` / `0.1173`, `F2`: `0.1207` / `0.1332`,
   `F3`: `0.1292` / `0.1431`), and `chance-calibrated-v4` (`IR-79-60`) cleared all `32`
   `H_3 > 0.70` plateau/lattice artifacts, **but** `20..25` wide-halo coverage sweeps
   (`0.40 <= H_3 <= 0.65`, `250k..624k` dots) still overlapped `> 0.70` raw (`IR-79-63`).
   Honoring the preregistered gate with zero retroactive threshold edits, `H79-FNHR` is
   stopped with `verdict: "negative"` (`DO-NOT-SUBMIT`). Do not retune or overlap-cap `F1..F3`.
   `H79-NHR` (`X1`), `G79B-SDPT`, `G79-STEPCO`, and `E1` (`G79-FABRIC-OFFSET`) stay stopped
   negative and archived unchanged.
4. `vendor/gems57` is shared code, not a private fork. Check its SHA-256
   pins (`registry/template_pin.json`). A real shared defect is fixed once in the shared module, with a
   version note and an IR entry. Examples: `budget-matched-v3` (`IR-79-47`) and
   `chance-calibrated-v4` (`IR-79-60`, `reports/upstream_patch_uniqueness_v4.diff`). Use the shared evaluator,
   writer and novelty gate; never invent scientific metrics or receipts.
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
