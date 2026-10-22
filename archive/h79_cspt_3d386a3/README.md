# Historical H79-CSPT work — NOT cleared for submission

**DO NOT SUBMIT these artifacts.** This provenance archive preserves the work
introduced by PR #12, merge commit `3d386a3f0c6f89c31e33a656dee8851cee64753d`.
Its source and generated HTML are stored as non-executable `.txt` files outside
the published `docs/` tree. No CSPT experiment was rerun during this review.

## Why the advertised promotion is not adopted

- The incoming README and two HTML pages advertised `PROMOTED` while the
  canonical root `run_card.json`, experiment state and status API remained
  negative for G79-FABRIC-OFFSET. These are conflicting lanes, not one run.
- `src/gems79/lagrangian_solver.py` excluded entries marked `is_space_filling`
  from the hard overlap constraint. Its certificate's `overall_uniqueness_pass`
  therefore does **not** certify the user's all-registry literal rule. An
  exemption was not authorized. The full-footprint rejection witness remains
  decisive under that rule.
- PR #12 changed the shared `vendor/gems57/uniqueness.py` and its pin manifest.
  The active module/pins are restored to the previously verified shared bytes.
  The modified module is retained in Git history only, not as a private fork;
  its source hash is recorded in this archive's manifest.
- The incoming README described the H33 score as `ORGANIZER-CONFIRMED`, but no
  file-linked organizer submission receipt was supplied. It also gave numerical
  projected gains for untested hypotheses. Neither is adopted as evidence.
- The incoming holdout provenance explicitly says `buffer_px=0.0` for masked
  training worlds. The measurements and claimed leakage checks have **not** been
  independently reproduced here; neither their protocol compliance nor their
  performance claims are established by merely preserving JSON.

Historical JSON and TIFF/ZIP bytes are unchanged, including any `promote` or
`ok_to_submit` fields. Those are **archived claims, not current authorization**.
The tests archived here asserted that promotion and the dense-prior exclusion;
they are preserved for audit, not used as active acceptance tests. Inputs and
registries overwritten by that merge are also preserved, so nothing is silently
lost. `manifest.json` records all 55 affected paths and source SHA-256 hashes.

Active files were recovered from first parent
`b1f27dc43eb2b5fe61ccfcb6303672cb8adaa772`; this is recovery of the existing stopped
lane, not a branch switch, new experiment, or new submission selection. The
active downloadable E1 research surface is still marked **DO NOT SUBMIT**. Its
format PASS cannot override the duplicate stop or establish a leaderboard score.
