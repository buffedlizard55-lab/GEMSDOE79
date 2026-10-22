# Session 0be4d7bb review — G79-TDW (3 passes)

## Pass 1 — Implement
- Restored SHA-pinned `training_features.tif` (4371c82e…) + `labels.tif` via `scripts/restore_data.py` (GitHub mirror; organizer origin is DrivenData login page). No DrivenData auth used.
- Pre-registered lane G79-TDW (`registry/preregistration_tdw_0be4d7bb.json`) and ranked 5 untried hypotheses (`research/hypotheses_0be4d7bb.md`). Top = de-striped tilt-depth worms; rank-5 (3DEP shoreline veto) flagged not viable in-sandbox (host outside egress allowlist).
- EXP-TDW-1 (`scripts/run_tdw.py`, `src/gems79/tdw.py`): canary max AUC 0.5321/0.5711 PASS; HOLDOUT-DTI (gems57-pooled-hide-v2) 0.0395 [0.0297,0.0490] n=11,321 / 0.0413 [0.0321,0.0507] n=11,342 — below uniform (0.0468/0.0491) and THVC (0.1905/0.1944). Final 37,654-dot TIF written via shared writer, validator PASS, SHA 0a79e3e5…

## Pass 2 — Bug / edge review
- Fixed: writer temp files landed 0600 → chmod 644; new TIF initially in `docs/downloads/` broke publication contract (only canonical artifacts allowed) → moved to `artifacts/tdw/` per CJX/DZD precedent; hand-made page broke frozen 11-page manifest → registered page in `scripts/build_site.py` + `scripts/check_site.py` (12 pages) and rebuilt; `data/restore_receipt.json` overwrite reverted (provenance preserved, restore logged here instead).
- Novelty: vs 40 local rasters max |rho| 0.057 PASS; sparse ≤100k max overlap 0.5420 PASS; literal blocked only by 1.88M-px continuous surface (saturated, non-informative; cf. gate certificate). Full 1,108 census NOT re-run — labelled NOT MEASURED.

## Pass 3 — Requirements recheck
- Unique TIF: yes, new bytes, never copied. Obvious decision: homepage hero + TDW page + README all state OK TO DOWNLOAD: YES / OK TO SUBMIT: NO with gate table; automated (no human inspector). Range error addressed: zeros-mode all-finite [0,1] writer + disk re-validation. Name (38 chars) + note (91/140) provided but marked do-not-use. Executive-summary page explains exact submission steps for a future YES. H33 0.2778 explained as thinning efficiency (UNVERIFIED report, no organizer receipt); beating it remains unproven — no projection written as a score. Budget: 1/3 experiments used, 0 slots spent. Verdict: **negative** (deliverable per protocol).

## Limitations / next
- Holdout truth is catalogue-style; blind-fault hypotheses are structurally disadvantaged there — still the protocol gate, not waived.
- Next viable lanes: H79-U2 (fan-apex collinearity) and H79-U4 (Riedel zones) from `research/hypotheses_0be4d7bb.md`; each needs its own preregistration. Do not retune TDW on holdout.
