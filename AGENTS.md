# Start-of-session contract

1. Read **all of README.md**, including the original prompt, then `run_card.json`,
   `reports/irregularities.md`, `registry/preregistration.json` (E1, frozen) and
   `registry/preregistration_g79b.json` (G79B, frozen) before work.
2. Work only on the Arena-assigned active session branch reported in the current
   session metadata. Do not hardcode a previous session's branch here. Never
   rename or switch branches. Historical branch names in immutable
   cards, reports or prior prompts are provenance, not instructions for a new session.
3. Both scientific lanes in this repo are **closed negative**:
   - G79-FABRIC-OFFSET (E1): literal pre-placement duplicate stop; post-stop
     diagnostic HOLDOUT-DTI 0.0474/0.0466. Card preserved at
     `evidence/run_card_g79_e1.json`; artifact under `archive/g79_e1_fabric_offset/`.
   - G79B-SCARP-DIPOLE-GEOAND (2026-10-22, owner-authorized new lane): unique and
     format-valid, but HOLDOUT-DTI 0.0530/0.0449 does not beat uniform (0.0538/0.0504)
     or the fold-fair H33 control (0.0961/0.0989). Current `run_card.json` is this card.
   Do not restart, retune, add jitter, exempt dense priors or silently open a new
   lane. A new lane requires explicit owner authorization AND a fresh
   preregistration before computation. Maximum three experiments/two hours per run;
   zero competition slots have ever been used by this repo.
4. `vendor/gems57` is immutable shared code, not a private fork. Check its SHA-256
   pins. A real shared defect belongs upstream once. Use the shared evaluator,
   writer and novelty mathematics; never invent scientific metrics or receipts.
5. Do not replace missing measurements with zero. Only a submission-page receipt
   establishes ORGANIZER-CONFIRMED for an artifact. Public leaderboard observations
   and user-reported scores must retain their evidence classes.
6. A local format PASS does not mean OK TO SUBMIT. `run_card.json` and
   `scripts/submission_status.py` must agree, and currently return a negative verdict.
7. Keep large input/cache files ignored. Serve only docs/ in previews and artifact
   deployments; legacy Pages also has a root redirect. Never publish credentials,
   invented source data, synthetic scientific scores, or a quarantined file as ready.
8. Run tests, offline byte/format verification, site link checking and a final
   requirements review. Record all three review passes and unresolved limitations.

- Concurrent H79-MCT and H79-CSPT material is historical text/data under
  `archive/` (see `evidence/concurrent_lanes_audit.json`); do not reactivate
  their dense-prior exemptions, overlap-capping solvers or positive flags.
  Decision D-1 (literal vs operative dot definition for continuous registry
  rasters) is still open; G79B's disclosed scoped/operative result does not
  resolve it and `protocol_unique` remains false.
