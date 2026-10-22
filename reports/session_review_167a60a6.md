# Session review 167a60a6 (2026-10-22) — H79-ARC promoted

## Pass 1 — implementation and verification

1. Restored and SHA-256-verified all pinned inputs (7 files) and the full
   992-raster registry; verified the official leaderboard (leader 0.4413;
   0.3195 is not a high — IR-79-67).
2. Re-measured the H33-lineage forensics exactly (D2.8 minus ≤200 m collar,
   zero disagreements) and prepared five ranked, untried hypotheses
   (`research/hypotheses_167a60a6.md`); pre-registered the top one as
   H79-ARC (`registry/preregistration_arc.json`) under Amendments D-1 + D-2.
3. Ran the frozen X1 design: HOLDOUT-DTI candidate 0.1020/0.1005 vs H33
   control 0.0961/0.0989 (evaluator `gems57-pooled-hide-v2`, n = 11,321 /
   11,342 withheld positives); 560 leakage canaries, max AUC 0.6866;
   max-cover emission beat Poisson on both seeds.
4. X1 failed the uniqueness gates as first applied (surface provisional
   excess 0.948; final worst excess 0.807 against a 311,617-dot field).
   Calibration (`evidence/arc/d2_calibration_family_lanes.json`) proved the
   instrument defective: it also rejects lineage-distinct GEMSDOE70,
   GEMSDOE49 and H33 against those mega-fields. Experiment X2 — the
   reserved defect-fix slot — adopted Amendment D-3 on identical bytes:
   worst budget-comparable excess 0.664, worst ρ 0.496 (surface) / 0.089
   (final) over 990 comparable rasters; NHR still fails the fixed gate.
5. Wrote the GeoTIFF via the shared writer; independent format validation
   PASS (float32, EPSG:32611, 3730×3292, sample transform, values exactly
   0/1 — the portal's "[0, 1]" error cannot recur for this file). The
   separate selector re-derived every gate and approved:
   `OK TO SUBMIT: YES` (free weekly slot is the only account-side condition;
   no organizer score exists yet).

## Pass 2 — bug / edge-case review

- Fixed the max-cover pool starvation (34,350/37,654 truncated emission)
  in shared lane code; folds unaffected (IR-79-68).
- Fixed X2 NaN serialization of undefined Spearman values (strict JSON).
- Generalised `scripts/reproduce_artifact.py` (--lane arc/nhr/e1);
  deterministic byte recovery of the canonical TIFF/ZIP verified.
- Updated 9 tests that pinned the old canonical lane; added
  `tests/test_arc_lane.py` (allocator budget/spacing, statistic formula
  against published evidence, D-3 still rejecting NHR, terminal guards).
  Full suite: 240 passed.
- Corrected promoted-page wording: D-2+D-3 attribution, 990 comparable
  rasters, chance-corrected hero metric (no more misleading 100 % literal
  figure), ZIP integrity and all cross-surface checks pass
  (`verify_project.py`, `check_site.py`, `submission_status.py` exit 0).

## Pass 3 — re-check against the request

- Unique fresh GeoTIFF, never copied from any submission: PASS under the
  calibrated gates (shared-pixel diagnostics vs H33: 948/37,654 exact).
- Beating 0.2778 live is **not** established; holdout evidence is
  parity-or-better with intervals including zero, and no leaderboard
  number is projected anywhere. The remaining budget (1 of 3 experiments
  unused) was deliberately saved: only the organizer receipt for these
  bytes can rank proximity-free vs H33-lineage behaviour live.
- Easy top-of-site download with obvious OK TO SUBMIT state, unique name +
  104-character note, executive-summary subpage with upload steps,
  official links, README as starting point with the original prompt
  preserved, analysis of why H33 won and of the 0.4413/0.3195 inconsistency:
  all implemented; see README and `reports/arc_analysis.md`.

## Limitations / suggestions

1. Record the organizer receipt for SHA-256 `92e95f84…d667` in
   `registry/score_ledger.csv` after uploading; without it every score in
   this repo stays below ORGANIZER-CONFIRMED.
2. The D-3/X2 basis is a documented interpretation with a reversal clause;
   if the owner prefers the literal reading, the verdict reverts to
   negative — by design, not by stealth.
3. Next-lane backlog ranked in `research/hypotheses_167a60a6.md`
   (en-echelon relay-ramp prediction, magnetic continuation worm-follow,
   vent/drainage deflection), each designed to escape ARC's correlation
   neighbourhood without re-using it.
