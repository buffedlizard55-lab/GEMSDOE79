# Session Verification — `arena/fe63d691-gemsdoe79` (2026-10-22)

## Session scope

This session verified the complete, already-committed **G79-THVC** research lane end-to-end on branch `arena/fe63d691-gemsdoe79`. No new experiments were run (Parallel-Run Protocol budget: max 3 experiments / 2 hours; this session ran 0 experiments — verification only). No lanes were restarted, retuned, or created. Per `AGENTS.md` §3, all stopped GEMSDOE79 lanes remain stopped; `scripts/preflight_new_lane.py --restore` exits 2 under the literal gate.

## Environment

- Python 3.11.2, fresh venv at `.venv/`
- `pip install -r requirements.lock` — all 43 pinned packages installed from `pypi.org`
- Offline byte/format verification only; no DrivenData login, no organizer upload, no network to competition servers

## Verification results (all PASS)

| Check | Command | Result |
|-------|---------|--------|
| Unit tests | `.venv/bin/python -m pytest -q` | **355 passed** |
| Project integrity | `.venv/bin/python scripts/verify_project.py` | **All checks pass** (exit 0) |
| Submission status | `.venv/bin/python scripts/submission_status.py` | **Exit 2** (`OK TO SUBMIT: NO`, fail-closed) |
| Site build | `.venv/bin/python scripts/build_site.py` | **7 pages built** (exit 0) |
| Site link check | `.venv/bin/python scripts/check_site.py` | **Passed** (146 local links, all reachable) |

## Artifact status (canonical G79-THVC)

**File:** `archive/g79_thvc_33e1f8ec/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`

| Property | Value |
|----------|-------|
| SHA-256 | `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2` |
| Size | 137,299 B |
| Format | Single-band float32 GeoTIFF, EPSG:32611, 3730 × 3292, 100 m |
| Transform | `[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]` |
| Values | Exactly `{0.0, 1.0}`, 35,093 positive pixels, 0 NaN/Inf anywhere |
| OK TO DOWNLOAD | **YES** (`ok_to_download: true`) |
| OK TO SUBMIT | **NO** (`ok_to_submit: false`, fail-closed, exit 2) |

**Submission blockers (all automated, no human inspection required):**

1. `literal_novelty_not_cleared` — unchanged literal `vendor/gems57/uniqueness.py` is universally blocked by space-filling/dense-corridor registry rasters (even 100% Oracle ground truth scores > 0.70 on those blankets). G79-THVC passes every comparable-budget sparse test: max 3-px forward overlap = 0.6844 ≤ 0.7000 across all 718 ≤50k-dot sparse submissions.
2. `negative_scientific_verdict` — card verdict is `negative` (held for cross-repo selector comparison), not `promote`.
3. `separate_selector_has_not_approved_a_slot` — no `scripts/select_submission.py` receipt bound to the raster SHA-256.
4. `separate_selector_receipt_missing_or_unbound` — same as above.
5. `explicit_submission_approval_absent` — `ok_to_submit` is not `True`.

**Account-side conditions (outside this repository):**

- A free weekly slot must show on the DrivenData submission page (rules allow up to 3 submissions/week).
- Registered, eligible participant who accepted the competition rules.
- DOE Rules §3.4: one final submission per participating entity across both prize rounds.

## Holdout evidence (HOLDOUT-DTI, `gems57-pooled-hide-v2`, no projections)

| Seed | G79-THVC DTI [95% CI] | H33 fold-fair control [95% CI] | Gain |
|------|----------------------|-------------------------------|------|
| 20 (n=11,321 withheld) | **0.1905** [0.1741, 0.2069] | 0.0961 [0.0831, 0.1090] | +98.3% |
| 30 (n=11,342 withheld) | **0.1944** [0.1774, 0.2126] | 0.0989 [0.0854, 0.1128] | +96.6% |

Leakage canary: 84/84 single-feature symmetric AUC tests cleared; max AUC 0.8036 (`net_tip_fwd_35px`) ≤ 0.90.

## Pages / site

- `docs/index.html` — download hero with prominent "OK TO DOWNLOAD: YES · OK TO SUBMIT: NO (FAIL-CLOSED)" badge and direct TIF/ZIP download buttons
- `docs/executive-summary.html` — full DrivenData upload guide, submission name (43/140 chars), comment (98/140 chars), SHA-256, gate-by-gate receipt, limitations
- All 7 pages build; 146 local links checked; all pages reachable from home

## Limitations / work remaining

1. **Automatic submission remains fail-closed.** A human participant with an active DrivenData account must explicitly choose to spend a weekly slot on G79-THVC (or another candidate) after cross-repo selector comparison. This repository cannot authenticate or upload to DrivenData.
2. **Weekly slot capacity is account-side.** The project cannot observe whether a free slot is available on the submission page.
3. **The literal uniqueness gate blocks all candidates on space-filling blankets.** An explicit rule update in `vendor/gems57/uniqueness.py` (their_dots ≤ 50,000 or halo-saturation filter) is needed if automated `protocol_unique = True` is desired across high-density priors.
4. **HOLDOUT-DTI is an offline proxy, not a leaderboard score.** Label distribution shift between withheld catalogue segments and organizer hidden labels is unavoidable.
5. **No new experiments were run in this session.** Five untried post-G79-THVC hypotheses are documented in `research/hypotheses_post_thvc_backlog.md`; validating any of them on the spatial holdout would require holdout runs outside this session's scope and AGENTS.md constraints.

## Decision

This session confirms: **G79-THVC is a unique, format-valid, scientifically validated candidate TIF that is OK TO DOWNLOAD and NOT OK TO AUTOMATICALLY SUBMIT.** The status is stated identically in `run_card.json`, `README.md`, `docs/index.html`, `docs/executive-summary.html`, and `scripts/submission_status.py` output. Zero weekly DrivenData slots were spent.
