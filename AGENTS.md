# Start-of-session contract

1. Read **all of README.md**, including the original prompt, then `run_card.json`,
   `reports/irregularities.md`, `registry/preregistration_nhr.json` (active lane) and
   `registry/preregistration.json` (archived E1) before work.
2. Work only on the Arena-assigned active session branch reported in the current session metadata. Do not hardcode a previous session's branch here. Never rename or switch branches. Historical branch names in immutable cards, reports or prior prompts are provenance, not instructions for a new session.
3. Active lane: **H79-NHR** (session 337ac1e9), opened at the user's explicit
   request and preregistered before any result. One experiment (X1) was used. It beat
   the holdout best but **failed the duplicate gate** (IR-79-55), so the verdict is `negative`
   and the lane is stopped. Do not retune or overlap-cap X1.
   A new idea needs a new preregistered lane, with three experiments or two hours at most.
   Follow-up review a7d092d7 re-measured the universal literal-overlap witness:
   `scripts/preflight_new_lane.py --restore` exits 2, forbidding any nonempty new
   candidate under that reading. Do not bypass it or restart the stopped lane.

   Session 2026-10-22 also ran **H79-ASYM** (antislope excess, `registry/preregistration_asym.json`)
   and **H79-MRND** (multi-regime brittle-crustal nested discovery across 77 physical features,
   `registry/preregistration_mrnd.json`). Both stopped cleanly at the pre-placement surface
   duplicate gate before placing final dots (`run_card_asym.json`, IR-79-74; `run_card_mrnd.json`,
   IR-79-83, where `H79-MRND` beat `H33` on both seeds and cleared all ~950 normal-budget
   `<= 167,596`-dot submissions while exposing the `168k..624k` wide-blanket threshold trap, IR-79-84).
   The canonical card remains `run_card.json`. Do not reopen H79-ASYM or H79-MRND by retuning.
   Note that the standalone lidar-scarp and geodetic-strain channels are already saturated in the
   registry (16 strain-named rasters; 32 informative scarp-channel overlaps).
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
