# Session review `0607bf35` — source and publication reconciliation

- **Date:** 2026-10-22 (UTC)
- **Branch:** `arena/0607bf35-gemsdoe79`
- **Base:** `847a4a0fb16b9173507b89cbb5a532d40fcea966`
- **Scope:** Documentation/source-ledger corrections, public-site copy, and verification guards only. No scientific experiment, lane restart, dot placement, TIFF/ZIP generation, upload, score query, or slot use.

## Decision state

The canonical research artifact remains `G79-THVC`, SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`. **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The exact literal-uniqueness obstruction is unchanged; no numerical score or submission clearance was produced.

## Review pass 1 — official source and frozen-evidence review

- Re-read the working-tree `README.md`, `AGENTS.md`, canonical run card, current irregularities ledger, and the named preregistration records before editing.
- Inspected the official USGS ScienceBase metadata for DOI `10.5066/P9TWT2LU`, *Electrical Conductance Maps of the Great Basin, USA* (Peacock & Bedrosian, 2022). It lists conductance products integrated over `2–12`, `12–20`, `20–50`, `50–90`, and `90–200 km`; metadata reports native CRS `EPSG:4269`. These are depth-integrated conductance products, not phase-tensor measurements or fixed-depth resistivity slices. The file listing is not proof that raster bytes were downloaded; none were.
- Read all seven parsed chunks of the official DOE/NLR rules PDF. Sections 3.2–3.5 confirm one single-layer 100 m GeoTIFF, up to three weekly feedback submissions subject to the site limit, one final selection across both prize rounds, and required generative-AI narrative disclosure; this is not evidence of account eligibility, a free slot, or organizer acceptance.
- Corrected the MT backlog to treat the data only as possible coarse regional context after future grid/coverage/unit QA. It makes no 100 m fault-trace resolution claim. All gain/runtime ranges in the backlog are explicitly labeled unvalidated planning estimates, not `HOLDOUT-DTI`, public DTI, or organizer-confirmed scores.
- Reconciled historical lane-count scope without inventing a current total: the key `gemsdoe79_16_lanes_summary` in the frozen JSON contains 17 rows; the separate README through-PR-62 summary describes 19 records, and the earlier backlog enumerates 11 formulations. These are different dates and inclusion rules; later records extend them. The previous generated homepage’s “All 9” table was not exhaustive.
- Logged the findings as `IR-79-143` (source correction) and `IR-79-144` (site/status and count scope).

## Review pass 2 — implementation, negative checks, and tests

- Updated `knowledge/official_sources.json`, `research/hypotheses_post_thvc_backlog.md`, README, AGENTS guidance, the site generator, and its site-check assertions. The site calls the historical table selected/non-exhaustive, labels `G79-THVC` a negative canonical research artifact, compares measured holdout output only with the H33 fold-fair control, and states that a weekly slot cannot bypass the literal gate.
- `scripts/preflight_new_lane.py --restore` was run and returned the expected fail-closed exit `2`: the pinned witness covers `1.0` of allowed cells, above the `0.70` limit. It did not run an experiment or write a new run card.
- The first new metadata test used case-sensitive display text for a lowercase hostname and expected “not retrieved” while the ledger said “no raster bytes.” The assertions were corrected to test the hostname and the actual limitation semantically; the focused test then passed before the full-suite rerun.

## Review pass 3 — final verification, build, and limitations

- `.venv/bin/python scripts/preflight_new_lane.py --restore` returned exit `2` as required: witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, allowed-cell coverage `1.0`, gate limit `0.70`. No experiment or run card was created.
- `.venv/bin/python scripts/verify_project.py`: `all_checks_passed: true` (**31 / 31** checks). Canonical raster SHA-256 remains `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2`.
- `.venv/bin/python scripts/build_site.py`: **7 pages**, decision line `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`
- `.venv/bin/python scripts/check_site.py`: **passed**, 7 pages, **146 local links**, 2 compatibility redirects, no third-party assets; fail-closed submission copy and explicit non-exhaustive comparison scope both pass.
- `.venv/bin/python -m pytest -q`: **356 passed**.
- `.venv/bin/python scripts/submission_status.py`: exit `2` (expected); `ok_to_download: true`, `ok_to_submit: false`, verdict `negative`, organizer acceptance false. Blockers include literal novelty not cleared, negative scientific verdict, missing selector approval/receipt, and absent explicit approval.
- The source-health feed was not refreshed. Its recorded attempt remains `2026-10-22T05:40:41.522520+00:00`; the source-ledger update is a metadata review, not a feed-reachability result.
- No ScienceBase TIFF bytes were downloaded, no new leaderboard check was made, and no DrivenData account receipt or weekly-slot status was accessible. No relationship between the user-reported H33 score and a specific raster was verified here.
