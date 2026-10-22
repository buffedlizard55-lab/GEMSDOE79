# Three review passes — H79-DILSTEP

Recorded after the holdout, the registry scan, and the site build. These are review notes, not new measurements.

## Pass 1 — scientific honesty

Checked the card and the public pages against `evidence/dilstep/holdout_seed20.json`, `holdout_seed30.json`, and `uniqueness_surface.json`.

- Seed 20 candidate 0.0721 [0.0577, 0.0874], n = 11,321, matches the evaluator after rounding to 4 decimals.
- Seed 30 candidate 0.0650 [0.0528, 0.0778], n = 11,342, matches.
- Both paired intervals versus the H33 control are entirely below zero. The pages say the file lost. They do not project an organizer score.
- User-reported 0.2778 and the public leaderboard 0.4413 are labeled as not this file's score.
- Canary maximum 0.6981 is under 0.90. No feature is treated as leakage.
- The 12 informative flags are 7 distinct maps. Nan and all-finite twins are counted separately. The pages now say so. The stop does not depend on the weakest flag (0.7030 versus halo 0.4425); the worst is 0.8527 versus 0.6413.
- No coefficient was changed after the score. Ranks 2–5 were not started.

## Pass 2 — publication contract

- `docs/downloads/` contains one TIFF, one ZIP, and the adjacent receipt.
- The name contains `DO-NOT-SUBMIT`. `scripts/submission_status.py` exits 2 and prints `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`
- H79-NHR bytes were copied to `archive/h79_nhr/` before the canonical card changed. The archived SHA-256 still matches.
- `registry/score_ledger.csv` was not appended. No organizer receipt was invented.
- IR-79-67 is a table row in `reports/irregularities.md`, written before the scan.
- Six unreadable or off-grid registry files are listed. They are not counted as passes.
- Sandbox absolute paths were removed from the published receipt and the scan JSON.

## Pass 3 — requirements and remaining limits

The original prompt is still in the README. The download is one click. The submit decision does not need a person.

What this session does not do:

- It does not beat 0.2778, 0.3195, or 0.4413. Those are not measurements of this file.
- It does not claim protocol uniqueness. New bytes are not the same thing as a passed duplicate gate.
- It does not spend a weekly slot. A higher organizer score remains possible only as an untested difference between catalogue faults and expert faults.
- The registry scan is the indexed public sibling inventory (986 comparable of 992), not every file other participants have uploaded.

`pytest` : 235 passed. `scripts/check_site.py` : passed, 118 local links. `scripts/verify_project.py` : passed inside the site build.
