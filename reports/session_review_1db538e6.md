# Session review 1db538e6 — why no new unique TIF was generated

Branch: `arena/1db538e6-gemsdoe79` (from `main` @ `5fb2fec`).
Scope: repository review, baseline verification, a measured diagnosis of the novelty gate, one reproducible diagnostic script with tests. No new candidate raster, no holdout experiment, no weekly slot touched.

## 1. Bottom line

- **OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** Same disposition as the canonical card (`run_card.json`). Verified again from bytes this session (section 3).
- **No new unique TIF was generated, on purpose.** Under the parallel-lane protocol in the README prompt, a candidate whose dots are more than 70% within 3 px of one registry raster's dots must be logged as a duplicate and stopped. This session measured that the rule cannot be cleared by any candidate that is not placed on the registry's blind spot (section 2). Generating another file would produce a duplicate, a relabelled file, or an exploit of the gate. None of those is a unique, submittable TIF.
- **The decision that unblocks this is an owner decision, not a coding task.** It is stated in section 5.

## 2. Measured diagnosis of the novelty gate (from raw bytes)

Commands (all reproducible, run in this session):

```
.venv/bin/python scripts/preflight_new_lane.py --restore      # exit 2, impossible_under_literal_gate
.venv/bin/python scripts/measure_registry_halo.py .cache/registry/r13_lattice.tif --json evidence/halo_saturation_13GEMSDOE_1db538e6.json
.venv/bin/python scripts/measure_registry_halo.py .cache/registry/374c88b1da2b803e2ed160de467fd71ae114010d.tif --json evidence/halo_saturation_17GEMSDOE_Eproba_1db538e6.json
```

| Registry raster | SHA-256 (verified here) | Positive dot cells | 3-px halo coverage of footprint | Uncovered footprint cells |
|---|---|---:|---:|---:|
| `13GEMSDOE` `r13-lattice-s5_v2_zerofill.tif` (blob `5c1a1594…`, path cited in `docs/evidence/gate_satisfiability_certificate.json`) | `c12533bb980234c3a706af641d4f1d514bbbe482714b2ebcac3b10f3e72a7a3f` | 206,895 | **0.998713** | 6,649 (0.129 %) |
| `17GEMSDOE` `E-proba-multiscale_20260930T044527Z.tif` (cited in `docs/evidence/g79_thvc_results.json`, witness of `preflight_new_lane.py`) | `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be` | 5,167,373 (every finite cell, value 0.00046–0.984) | **1.000000** | 0 |

Reading: a candidate with forward overlap ≤ 0.70 against the lattice must put at least 30 % of its dots in the 6,649 uncovered cells. That is a blind-spot placement, not a geological hypothesis, and it cannot be defended as "unique" or "novel". The E-proba witness is a continuous probability surface; the gate counts every finite cell as a registry "dot", which is an interpretation of the rule, not something the rule states. The lattice blocker does not depend on that interpretation.

Consequence: the literal rule is non-informative for every honest candidate. This matches `docs/evidence/gate_satisfiability_certificate.json` (`answer: false`), which this session re-derived rather than trusted.

## 3. Current download validation (re-run this session)

File: `docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif`

- SHA-256 `d3db2e959df96f71936c019bb5e4f1599f4591dbcfbf78d2a3f78332a5ecfee2` (matches `run_card.json`); 137,299 bytes.
- CRS EPSG:32611 = sample; shape (3730, 3292) = sample; transform identical to sample; one float32 band; nodata none.
- NaN cells: 0. Min 0.0, max 1.0, all values in [0, 1]. Unique values {0, 1}. Positive cells: 35,093.
- NaN inside the sample footprint: 0. Nonzero cells outside the footprint: 0.
- ZIP `…DO-NOT-SUBMIT.zip` (SHA-256 `dfee2552…788f9`) contains one member whose bytes equal the TIF exactly.

This is a **format** pass. It is not novelty approval and not a portal acceptance.

## 4. Baseline checks

- `pytest`: 477 passed (before this session's new test file). New file `tests/test_measure_registry_halo.py`: 3 passed.
- `scripts/verify_project.py`: exit 0.
- `scripts/submission_status.py`: exit 2, `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`
- `scripts/select_submission.py`: exit 2, card unchanged.
- `scripts/preflight_new_lane.py --restore`: exit 2, `start_new_lane: false`.

## 5. Decision needed from the owner (not decided here)

Pick one, in writing, before any new lane is generated:

- **A. Keep the literal gate.** Then the answer to "generate a unique TIF that can be submitted" is **no** for every candidate, permanently. Stop here.
- **B. Prospective amendment, excluding saturating registry rasters.** Compare only against registry rasters whose 3-px halo covers ≤ 70 % of the footprint. Dense rasters (such as `13GEMSDOE` and `17GEMSDOE` above) are reported separately, never silently dropped. Must be recorded as an IR entry and applied once in shared code.
- **C. Prospective amendment to chance-corrected overlap (`compare_array_to_registry_d2`, already in shared code, IR-79-128).** Caution: this rule already rejected G79-BER, so it is not neutral. Its behaviour against dense rasters must be stated before adoption.

Whichever is chosen, the new lane still needs a frozen mechanism, all-feature leakage canaries, and a fair incumbent comparison (AGENTS.md §4, the README "Reproduce" section). The 3-experiment / 2-hour budget applies.

## 6. Irregularities for review

1. **Allowed-cell count mismatch.** `gate_satisfiability_certificate.json` says `allowed_cells: 5,106,385` and halo coverage 0.998724. The finite footprint of `data/reference/sample_submission.tif` has **5,167,373** cells (the same count as the E-proba witness), and coverage here is 0.998713. The certificate's allowed-cell definition is not documented in the artifact. Not resolved here.
2. **Range error from the portal is undiagnosed.** The user reported "Predicted values must be in range [0, 1]". The inherited file passes the range check locally (section 3). The official problem page ([DrivenData page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), checked this session) states: values "between 0 and 1", float32, EPSG 32611, 100 m, and "data outside the bounds is null or nan". The inherited file uses zero fill outside the footprint, which the page does not forbid but does not describe. That gap is unresolved; no receipt exists for the rejected file.
3. **The 3-px "dot" gate is a lane construct, not an organizer rule.** The official metric is a distance-weighted Tversky index over probabilistic predictions p(x) in [0,1] (same page: "pixel-wise probabilities or confidence scores"; kernel k(d)=max(1-d/R,0), R = 300 m, alpha 0.2, beta 0.8). The organizer does not define "dots" or a 3-px overlap novelty test. The "full-footprint witness" blocks every candidate only because a continuous probability raster is treated as a set of all its finite cells. The owner should decide whether the gate is a lane rule to keep, amend, or drop (decision B/C).
4. **Leaderboard figures are unverified.** The 0.4413, 0.3195 and 0.2778 figures in the README prompt have no organizer receipt in this repository. They are not used as scores here.
5. **Git-hosted registry blobs.** The `13GEMSDOE` blob was fetched via `gh api` from `buffedlizard55-lab/13GEMSDOE` and matched its pinned SHA-256. This verifies the bytes against the pin, not against the organizer.
6. **Scope not performed.** This session did not run new literature searches, did not gather new external data sources, and did not generate or test new hypotheses. Those items are in the prompt; they are not claimed as done here. The existing ranked hypotheses in `research/hypotheses_e4a4422d.md` and `research/hypotheses_post_thvc_backlog.md` remain the reference.
7. **Prompt item not met: "unique TIF with OK TO SUBMIT: YES".** Not met, deliberately, per section 1.

## 7. Next steps (suggested, not started)

1. Owner chooses A, B or C in section 5.
2. If B or C: write the amendment as an IR entry and a preregistration, implement once in `vendor/gems57/uniqueness.py` with a version note, then run the new lane's canaries and holdout on the existing cached feature stack (requires restoring `data/raw` via `scripts/restore_data.py --preserve-receipt`, which fetches pinned GitHub mirrors).
3. Obtain an organizer submission-page receipt for the currently published file, if the owner is willing to spend a slot on it. That is the only route to ORGANIZER-CONFIRMED evidence. It is an owner action, not a session action.
