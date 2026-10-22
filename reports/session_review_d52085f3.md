# Session review d52085f3 — repository review, gate audit, and the unique-TIF question

Branch `arena/d52085f3-gemsdoe79`, started at `baee09e` (main). Scope: review the repo, reproduce every gate with live commands, answer the H33 0.2778 question, and state exactly what blocks a unique submittable TIF. **No new scientific lane, placement, holdout, canary or competition submission was run in this session.** Experiments spent: **0 of 3**. Submission slots used: **0**.

## 1. Bottom line

- **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The live gate says this, and it is correct to say it.
- **A unique, submittable TIF was not generated.** This is not a shortage of compute. Two things stop it, and only the protocol owner can clear them:
  1. **No lane method paragraph exists in the record.** The parallel-run protocol requires one. `README.md` and IR-79-02 say the paragraph was absent, and the current prompt still contains bracketed placeholders (`[0.90]`, `[70%]`, `[3]`) instead of a method. Inventing one would be exactly the "invented assignment" that AGENTS.md forbids.
  2. **The duplicate gate is unsatisfiable under the literal reading.** One pinned registry raster (`17GEMSDOE_E-proba-multiscale`) is a continuous surface with positive support on all 5,167,373 footprint cells. Under the literal definition every nonempty candidate has 3-px overlap 1.0 > 0.70. Measured below. The repo's own amendment D-1 (top-k dots for continuous surfaces) would clear this, but it is recorded as "open to reversal by the protocol owner" and has not been ratified for a new lane.
- **The H33 0.2778 score is an unverified historical report.** No organizer receipt links it to a file. The public leaderboard page confirms #1 at **0.4413**, not 0.3195 (see §5).

## 2. Reproduced gate results (live, this session)

Environment: `python3 -m venv .venv && .venv/bin/pip install -r requirements.lock` (Python 3.11.2, all pins installed).

| Command | Result |
|---|---|
| `git status` / `git branch` | clean; on `arena/d52085f3-gemsdoe79` |
| `.venv/bin/python -m pytest -q` (with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`) | **477 passed**, exit 0 (56.7 s) |
| `.venv/bin/python scripts/verify_project.py` | **exit 0** (publication contract and all pinned checks pass) |
| `.venv/bin/python scripts/submission_status.py` | **exit 2**; `ok_to_download: true`, `ok_to_submit: false`, `verdict: negative`; blockers `literal_novelty_not_cleared`, `negative_scientific_verdict`, `separate_selector_has_not_approved_a_slot`, `separate_selector_receipt_missing_or_unbound`, `explicit_submission_approval_absent` |
| `.venv/bin/python scripts/preflight_new_lane.py` (no restore) | **exit 3** `unverified`: the pinned witness is not in the working tree (fail closed) |
| `.venv/bin/python scripts/preflight_new_lane.py --restore` | **exit 2** `impossible_under_literal_gate`; witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`; `covered_allowed_fraction 1.0`; limit 0.70 |

The `--restore` run fetched the pinned witness blob (`374c88b1da2b803e2ed160de467fd71ae114010d`, 25,065,181 bytes) into the gitignored `.cache/registry/`. Its SHA-256, Git blob hash and size were all verified by the shared verifier before measurement.

## 3. Measured facts about the blocking witness

Direct raster read of `.cache/registry/374c88b1da2b803e2ed160de467fd71ae114010d.tif` (not a score):

- 3,730 × 3,292, float32, EPSG:32611, transform `[100, 0, 243350, 0, -100, 4508550]`.
- Finite and positive cells: **5,167,373** of 12,279,160 grid cells. This equals the footprint count the repo reports, so the support covers the whole footprint.
- Value range **0.000463 – 0.984116**; percentiles 1/10/50/90/99 = 0.0095 / 0.0431 / 0.2187 / 0.5516 / 0.8161. It is a continuous probability-like surface, not a dot set.

Chance-level halo measurement under the shared module's own top-k reading (`vendor/gems57/uniqueness.py::budget_matched_dots` and `_near`, 3-px disk, no candidate involved):

| k (matched budget) | Witness top-k dots | Footprint coverage within 3 px |
|---|---|---|
| 37,654 (H33 budget) | 37,654 | **0.0185** |
| 38,000 | 38,000 | **0.0186** |

Interpretation: under the top-k reading, a candidate with *random* placement inside the footprint would overlap this witness by about 1.9%, against a 70% limit. The literal reading (every positive cell is a dot) gives 100%. The entire impossibility therefore comes from how "dots" is defined for a continuous surface, and the outcome flips on that definition alone. This is a feasibility measurement of the gate, not a candidate's score, and it is labelled **REGISTRY-MEASUREMENT**.

## 4. Why H33 scored 0.2778 — what the repo can and cannot say

Sources: `knowledge/h33_review_e4a4422d.md`, `evidence/h33_forensics.json`, `evidence/review_e4a4422d/h33_remeasurement.json`, `registry/score_ledger.csv`.

- **Score status:** `UNVERIFIED HISTORICAL REPORT` in `registry/score_ledger.csv`, with an empty `organizer_receipt`. The GEMSDOE32 page describes the file as UNSCORED. Under the protocol it cannot be ORGANIZER-CONFIRMED.
- **Byte lineage (re-measured this review):** the related D2.8 raster has 44,090 positive pixels; H33 has 37,654; 6,436 are deleted; 0 H33 pixels are absent from D2.8; 0 disagreements with `D2.8 & (distance_to_catalogue > 2 px)`; no deleted pixel lies exactly on the catalogue. H33 is therefore a pruned D2.8 that removed nearby off-catalogue pixels.
- **Mechanism, as far as the metric allows:** the organizer metric (DW-Tversky, [competition metric page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric)) gives each truth pixel its best nearby prediction credit, and false-positive cost is summed over predictions. Removing a redundant prediction (no lost true-positive credit) can only help; removing a true-positive prediction can hurt. The repo's algebra is `DTI = T / (0.2T + 0.2F + 0.8G + ε)`. Hidden truth is unavailable, so whether H33's deletions were net-positive **cannot be determined from anything local.**
- **What is NOT established:** that the 0.2778 figure is the organizer's score for that file; that thinning generalises; and that a higher score is reachable. The holdout is a hide-and-recover on the existing catalogue, which the organizer's expert-identified-fault target does not match.

**Answer to "why did it score highest?"** The evidence supports only a conditional explanation: the reported H33 result is consistent with removing redundant prediction mass while keeping coverage. That is a plausible metric-based mechanism, not a proof. Whether H33 is the highest *organizer-scored* artifact, and why it scored as it did, needs a submission-page receipt. I cannot supply one.

## 5. Score and leaderboard irregularities (flagged for review)

- **Leader is 0.4413, not 0.3195.** The official leaderboard page at [drivendata.org/…/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) lists #1 `xiaofanhu` at **0.4413** (Best public DW-Tversky), #2 `cfld__` at 0.3904, #3 `Batik Shirt Brothers` at 0.3894. I did not locate 0.3195 in the first two of the three pages. Treat the user-reported "0.3195 highest" as inconsistent with the public record; this matches IR-79-05.
- **Public-page versus repo scores** remain unverified until a submission-page receipt is attached.
- **"Predicted values must be in range [0, 1]"** error: the repo's current files pass local range checks, but the rejected file and its receipt are not in the repo, so the cause is undiagnosed (README, existing caveat). Do not assume the portal behaviour is fixed.
- **Merge request for `main`:** the prompt asks for a PR and a merge. See §7.

## 6. Hypotheses (3–5 requested) — pointer, not new work

The repo already holds four ranked, prospective hypotheses in `research/hypotheses_e4a4422d.md`: **G79-CJX** (cross-scale contact-junction localization, cached inputs, moderate cost), **G79-BLC** (bilateral lithology-contrast change-point), **G79-RSS** (relief-screened structural saddle), and **G79-HFR** (paired hydrothermal recharge residuals, which is **not data-ready**: the USGS heat-flow files are not acquired and were not checked for content). Each has a named non-fault mimic and a falsification test. None was validated this session; each needs a lane authorisation first. I did not add new hypotheses, because I could not validate or cost them without a lane and would have been speculating.

## 7. Decisions needed from you (the protocol owner)

1. **Gate reading for continuous surfaces.** Options: (a) keep literal, which blocks every candidate and makes a unique TIF impossible; (b) adopt D-1 top-k (`budget-matched-v3`) prospectively, as the shared tool already implements, which the measurement above suggests is non-blocking for random placement but still needs a full registry rerun; (c) another reading. Choose before any lane runs. Without a choice, the outcome is a stop.
2. **Lane assignment.** Provide the single method paragraph, or authorise G79-CJX from the ranked list. Without one, I will not start a lane.
3. **Merge to `main`.** The prompt requests a PR and merge. The repo's verification passes on this branch, and the change is docs-only. Confirm before I merge.

## 8. Irregularities and limitations

- The witness (`374c88b1…`) is a 17GEMSDOE public mirror blob. Pins prove mirror consistency, not organizer authenticity (IR-79-06).
- `drivendata.org` is login-walled for data; the public leaderboard page was readable through the fetch tool, but the sandbox allowlist permits only GitHub, npm and PyPI for direct downloads. Organizer rules and metric details were cited from the public pages only.
- Data inputs for the 13 pinned files were not re-restored this session except the witness; the earlier restoration is recorded in `data/restore_receipt.json`.
- No hallucinated numbers: every figure above is either a live command output in §2, a raster read in §3, or a quoted repo/public source with its path.

## 9. Verification passes

- **Pass 1 (implement and verify):** ran tests, verify, submission status, preflight with and without restore; measured the witness.
- **Pass 2 (bugs and assumptions):** checked whether `preflight` exit 3 was a code fault (it is fail-closed by design; restoring fixed it); checked whether the 100% overlap was a shared-tool bug (it is the literal definition, documented as IR-79-24/42/47, not a code error); checked the v3 measurement against the shared functions, not a reimplementation.
- **Pass 3 (requirements re-check):** the request for a unique TIF is not met and is blocked by two owner decisions (§7). The governance rules forbid bypassing them. The site and README state the decision plainly.

Reproduce:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/submission_status.py          # expected exit 2
.venv/bin/python scripts/preflight_new_lane.py --restore  # expected exit 2
```
