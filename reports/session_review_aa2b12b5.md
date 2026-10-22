# Session `aa2b12b5` · 2026-10-22 · three-pass review

**Decision:** **OK TO DOWNLOAD: YES (inherited research artifact only). OK TO SUBMIT: NO.** No new unique competition TIFF was produced. The prompt simultaneously requires a unique nonempty candidate and requires stopping when more than 70% of its dots lie within 3 px of any registry raster. A freshly restored, hash-pinned registry witness covers every allowed cell, so that second condition is mathematically unavoidable. I preserved the stop rather than exempting a raster, jittering dots, renaming an old file, or fabricating a score. Zero scientific experiments, placements, uploads and weekly slots were used.

## Pass 1 — repository, data and primary-source audit

1. Read the complete README/project brief, current canonical G79-THVC card, archived preregistrations and irregularity ledger. No new single-method lane paragraph was assigned in the current prompt; no stopped lane was reopened.
2. Installed the locked CPU environment and ran `scripts/preflight_new_lane.py --restore --report evidence/preflight_aa2b12b5.json`. It returned **exit 2**, `impossible_under_literal_gate`: witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, allowed-cell coverage 1.0, literal forward overlap 1.0 > 0.70 for every nonempty candidate. This is a measured protocol result, not a tooling failure or a competition score.
3. Restored all **13/13** manifest inputs with `scripts/restore_data.py --preserve-receipt`; `scripts/data_status.py` then reported `all_manifest_inputs_verified` ([runtime receipt](../evidence/runtime_data_status_aa2b12b5.json)). This removes data placement as a local blocker. It does not authenticate organizer provenance, and the large raw files remain Git-ignored.
4. Read the official [problem, metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR 1391](https://gdr.openei.org/submissions/1391), and [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html). The official sample passes local R1–R8 validation. The current public leader observation is **0.4413**, not this project's score and not an artifact-linked receipt. Claim-level provenance and acquisition limits are in [the source review](../evidence/source_review_aa2b12b5.json).
5. Before changing code, wrote [three ranked, untried hypotheses](../research/hypotheses_aa2b12b5.md): cross-sensor characteristic-length concordance (cached and data-ready), mapping-certainty/kinematics-aware continuation (official 5.85 MB GDR fault archive still to acquire), and repeat-survey replication (official CC0 Area 1/Area 2 archives still to acquire). Each names layers, a physical signature, missing-catalogue rationale, implementation distinction, non-fault mimic, controls, cost and availability. None was executed because the preflight stops first.
6. Baseline software test result: **632 passed, 2 failed**. The failures were a stale TIPSTEP page outside the reproducible Pages manifest and the corresponding site-consistency check. They were real publication defects, not ignored.

## H33: what the evidence does and does not answer

The reported H33 **0.2778** remains an **UNVERIFIED HISTORICAL REPORT**. GEMSDOE32's own page calls the file **UNSCORED** and calls **0.2747 a projection**. No artifact-linked organizer submission-page receipt was found. The public leaderboard's **0.4413** is a separate public observation.

Direct raster measurements establish the lineage: D2.8 has **44,090** positive pixels; H33 has **37,654**; H33 is exactly D2.8 after deleting **6,436 off-catalogue pixels within 2 px** of the catalogue. This is geometry, not causal score evidence.

The organizer defines `T = TP_w`, `F = FP_w`, and `G = N_truth`, with `FN_w = G − T`. Therefore:

```text
DTI = T / (0.2 T + 0.2 F + 0.8 G + epsilon)
```

Deleting predictions that lose `a` units of TP credit and remove `b` units of FP cost improves the score exactly when:

```text
0.2 T b > a (0.2 F + 0.8 G + epsilon)
```

Redundant predictions can add summed cost without improving max-cover credit, so thinning can help. Deleting a useful prediction can hurt. Hidden organizer truth is required to know H33's actual `a` and `b`; the pixels alone cannot prove why any score was assigned. A higher score is possible in principle, but this review demonstrates none. The defensible research direction is better independent fault discrimination and higher credit per emitted mass—not another H33 copy or cosmetic re-thinning. The full reasoning is retained in [the H33 review](../knowledge/h33_review_e4a4422d.md) and linked official metric page.

## Pass 2 — bug, assumption and edge-case review

### Reproducible Pages and evidence scope

- Added a receipt-driven TIPSTEP page to `scripts/build_site.py`, added navigation and raw-byte research download links, and updated `scripts/check_site.py` to the actual 15-page contract. Clean builds now preserve rather than delete the page.
- Corrected the unsupported statement that the TIPSTEP file “will NOT trigger” the portal range error. Its in-footprint values pass local range/grid checks, but its zero exterior **fails official R6**; the earlier rejected upload remains undiagnosed without its bytes and receipt.
- Distinguished the 40-local-sparse-raster diagnostic from full-registry novelty. No local subset is presented as approval.
- Updated `run_card_tipstep.json` and README with these limitations; historical TIFF bytes and HOLDOUT-DTI receipts were not changed.

### Holdout-control audit

The historical TIPSTEP runner constructs the candidate's allowed domain from the visible catalogue but constructs the UNIFORM control with `distance_to_full_catalogue > 2 px`. That excludes a hidden-truth collar only for the control. Their reported contrast is therefore not a fair promotion measurement. The generated page now states this explicitly. The candidate remains below the incumbent and negative; no result was rescued or rerun.

### Closed-lane lifecycle

Added fail-closed `enforce_open_lane` protection before bulk reads/writes in seven mutating scripts: `run_tipstep.py`, `novelty_tipstep.py`, `run_tdw.py`, `tdw_novelty.py`, `run_mdsc.py`, `finalize_mdsc.py`, and `generate_ventprox_submission.py`. Registered the commands and their artifacts/evidence in lifecycle tests. One import-path defect found by the new MDSC test was also corrected. No closed runner was allowed to replace historical bytes.

All findings are logged as IR-79-242 through IR-79-246 in [the irregularity register](irregularities.md).

## Pass 3 — final requirements and verification

The final verification covered code compilation, the 17-page site build after concurrent-main reconciliation, local link/evidence consistency, canonical fail-closed status, the complete test suite, JSON integrity, the current data manifest, and the official sample format. Exact command outcomes are recorded below after the final run.

- `python scripts/build_site.py` → built 17 pages after concurrent-main reconciliation with the canonical negative decision.
- `python scripts/check_site.py` → PASS; all pages reachable and scientific tables/gates receipt-derived.
- `python scripts/verify_project.py` → PASS; this is integrity verification, not submission approval.
- `python scripts/submission_status.py` → expected **exit 2**, automated BLOCKED decision; no human inspector required.
- Targeted TIPSTEP/lifecycle/site tests → initial run found an MDSC import-path error and the then-missing review link; both were corrected and are included in the final full-suite rerun.
- Full Python suite → **646 passed, 0 failed**.
- Download-identity Node suite → **12 passed, 0 failed**.
- Real Chromium QA → **51/51 rendered cases passed** (17 pages × 1440/390/320 px), exact TIFF SHA-256 download, clipboard, two redirects, private TIFF/ZIP identity checks and altered-byte refusal; zero network requests during local hashing and zero browser errors ([receipt](../evidence/browser_review_aa2b12b5.json)).
- Machine-readable final summary: [`evidence/verification_aa2b12b5.json`](../evidence/verification_aa2b12b5.json).

## Concurrent-main reconciliation (required before PR merge)

PR #150 initially conflicted because `main` advanced to `406bd28` with G79-CSHD and THVC-NANFIX. I merged that revision into the assigned session branch, preserved both concurrent lanes and their evidence, kept the canonical G79-THVC decision negative, renumbered this session's irregularities to IR-79-242..246, and rebuilt the combined 17-page site. The final full suite is **646 passed**, Node identity suite **12 passed**, and real-browser suite **51/51 passed** with **507** local links checked. Active CSHD/NANFIX prose that claimed to eliminate or prevent the portal range error was corrected to local R1–R8 PASS with portal acceptance unverified; no raster or scientific score was changed (IR-79-246).

## Negative run card

[`evidence/run_card_aa2b12b5.json`](../evidence/run_card_aa2b12b5.json) contains the conditional hypothesis, mechanism, named non-fault mimic, null HOLDOUT-DTI with NOT RUN status, the measured universal overlap obstruction, null new-raster SHA-256, validator scope, no new submission name/note, and verdict `negative`. Null means not measured; it is not a zero score.

## Limitations and next work

1. **Protocol decision required:** the owner must prospectively define how continuous, plateau and lattice registry rasters count as “dots,” applied uniformly to all future lanes. The current literal rule is unsatisfiable for any nonempty candidate; no local amendment is justified.
2. **Writer/format reconciliation required before any eligible candidate:** the older shared writer requires all-finite zeros while official R6 requires NaN outside the sample footprint. A future shared update must permit NaN **only outside**, keep finite [0,1] values inside, update pins/tests, and still avoid claiming that this diagnoses the old portal error.
3. **Validation independence:** the existing holdout has been reused heavily and hides catalogue faults, whereas organizer truth is expert-identified faults absent from that catalogue. Reserve a genuinely untouched spatial partition; do not equate hide-and-recover improvement with leaderboard improvement.
4. **External data for conditional hypotheses:** acquire and hash the official GDR Quaternary Faults v2 archive or GeoDAWN Area 1/Area 2 products only if a future protocol permits the corresponding preregistered lane. Check geometry, schema, licensing, co-registration and footprint coverage first.
5. **Account-side requirements unavailable:** DrivenData authentication, participant eligibility, remaining weekly capacity and artifact-linked submission receipts cannot be inspected here. No upload was attempted. Only a submission-page receipt can support ORGANIZER-CONFIRMED.
6. **Geothermal scope:** the competition scores fault predictions, not proof of vents, reservoir temperature, permeability, sustainable flow or economics. Thermal/alteration evidence is only corroborating structural evidence.

Primary review links: [problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [DOE INGENIOUS compilation](https://gdr.openei.org/submissions/1391) · [GEMSDOE32 H33 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html).
