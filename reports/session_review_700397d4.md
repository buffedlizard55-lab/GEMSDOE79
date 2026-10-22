# Session review — `arena/700397d4-gemsdoe79` (2026-10-22)

## Scope and start-of-session protocol check

Following `AGENTS.md`, this session began on the Arena-assigned branch
`arena/700397d4-gemsdoe79` by reading `AGENTS.md`, `run_card.json`, the full
`README.md` (including the preserved original prompt), `reports/irregularities.md`,
and `registry/preregistration.json` before executing any work. No new scientific
experiment was started, no lane was switched, `vendor/gems57` was kept byte-identical
to `registry/template_pin.json`, and zero competition submission slots were used.

## Pass 1 — Audit of repository state, frozen witness, and concurrent `origin/main` merges

1. **Baseline verification on `5e3067e`:**
   - Installed pinned dependencies from `requirements.lock` into `.venv`.
   - Restored and re-verified the frozen universal overlap witness
     `.cache/registry/374c88b1da2b803e2ed160de467fd71ae114010d.tif`
     (`17GEMSDOE:docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif`,
     `sha256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`)
     via `scripts/verify_overlap_witness.py --restore` and wrote
     [`evidence/session_witness_700397d4.json`](../evidence/session_witness_700397d4.json)
     (`positive_pixels = 5,167,373`, `allowed_pixels = 5,106,385`,
     `uncovered_allowed_pixels = 0`, `covered_allowed_fraction = 1.0`,
     `all_checks_passed = true`).
2. **Audit of concurrent `origin/main` commits (`b1f27dc` and `3d386a3`):**
   - `b1f27dc` (Merge PR #13 from `arena/9e23b44d-gemsdoe79`, commit `20eef10`)
     was a clean verification review adding `reports/session_review_9e23b44d.md`.
   - `3d386a3` (Merge PR #12 from `arena/d6ab5cbf-gemsdoe79`, commit `464d591`,
     lane `H79-CSPT`) broke `main` CI (`Verify research deliverable` run
     `39702012362` and `Pages and public-source health` run `39702012311`) and
     violated multiple `AGENTS.md` and Parallel-Run Protocol rules:
     - Modified `vendor/gems57/uniqueness.py` (`sha256: d60cd8db...`) to exempt
       **67 space-filling priors** (`n_space_filling_rasters_ge_0p70 = 67`) and
       rewrote `registry/template_pin.json` with an incompatible dict schema.
     - After unconstrained submodular placement (`seed30_h79_pure_submodular`,
       reported `0.2181`) failed the `0.70` overlap gate, applied a constrained
       Lagrangian solver (`hard_cap_frac = 0.690 < 0.700`) and C99 1-swap
       post-processor to push its 3-px forward overlap to `0.689973`
       (`25,184 / 36,500` dots) against four registry rasters (`306ee1b1...`,
       `gems57-relative-strand-surface...`, `gems57-twohost-relay-bend-surface...`,
       `gems77-h82gmns-lagrangian...`), while still having `1.0000` literal
       overlap against `17GEMSDOE_E-proba-multiscale`.
     - Used `buffer_px = 0.0` (unbuffered) when generating `K=5` whole-component
       self-supervision (`GMNS`) features.
     - Claimed `0.2778` (`H33-2-b2`) was `ORGANIZER-CONFIRMED` without a
       submission-page receipt and advertised `verdict: "promote"` /
       `ok_to_submit: true`.

## Pass 2 — Bugs fixed, concurrent lane quarantined, and readiness gate hardened

1. **Quarantined concurrent `H79-CSPT` (`IR-79-31`):**
   - Merged `origin/main` (`3d386a3` and `f93b8d7`) into `arena/700397d4-gemsdoe79`, preserving
     canonical `E1` files and restoring `reports/session_review_9e23b44d.md`
     from PR #13 (`20eef10`).
   - Verified the unified archive under [`archive/h79_cspt_3d386a3/`](../archive/h79_cspt_3d386a3/README.md)
     with its SHA-256 `manifest.json`, explicit `DO NOT SUBMIT` banners,
     zero executable `.py`/`.html` files, and no private `uniqueness.py` fork.
   - Created [`scripts/audit_archived_concurrent_lanes.py`](../scripts/audit_archived_concurrent_lanes.py)
     and generated [`evidence/concurrent_lanes_audit.json`](../evidence/concurrent_lanes_audit.json),
     verifying both `archive/h79_mct_c26efec` and `archive/h79_cspt_3d386a3` with
     the unmodified canonical `gems57.validate`, `gems57.uniqueness`, and
     `gems79.status` tools.
2. **Hardened `leakage_canary` validation in `src/gems79/status.py` (`IR-79-31`):**
   - Previously, `src/gems79/status.py` checked only `canary.get('passed') is True`,
     allowing missing, non-numeric, or out-of-range `auc` values (`< 0.5` or
     `> 0.90`), wrong `required_threshold`, or `features_cleared <= 0` to bypass
     `feature_alone_canaries_not_cleared`.
   - Fixed `src/gems79/status.py` to enforce numeric `0.5 <= auc <= 0.90`,
     `required_threshold == 0.90`, and positive `int` `features_cleared`, and
     added 19 parameterized unit tests in `tests/test_readiness_errors.py`.
3. **Updated `AGENTS.md` and `knowledge/why_h33.md` (`IR-79-32`):**
   - Made Rule 2 in `AGENTS.md` branch-neutral (referring to Arena's active
     session metadata rather than hardcoding a prior session's branch) and noted
     both `archive/h79_mct_c26efec/` and `archive/h79_cspt_3d386a3/`.
   - Updated `knowledge/why_h33.md` to reference both the post-stop offline
     diagnostic (`evidence/post_stop_diagnostic.json`) and the concurrent-lane
     audit (`evidence/concurrent_lanes_audit.json`) while keeping `run_card.json`
     untouched in its frozen negative state.

## Pass 3 — Full verification against the original prompt

- Re-checked every requirement in `reports/requirements_review.md` against the
  preserved original prompt in `README.md`.
- Rebuilt the GitHub Pages site (`scripts/build_site.py`) and verified:
  - `.venv/bin/python -m pytest -q`: **130 passed**.
  - `.venv/bin/python scripts/verify_project.py`: **`all_checks_passed: true`**.
  - `.venv/bin/python scripts/check_site.py`: **7 pages, 108 local links, 2 compatibility redirects**.
  - `.venv/bin/python scripts/submission_status.py`: **exit code 2** (`ok_to_download: true`, `ok_to_submit: false`, `verdict: "negative"`).
  - `node scripts/browser_review.cjs`: **21/21 real headless Chromium checks passed** across 1440px, 390px, and 320px viewports with downloaded TIFF SHA-256 matching `run_card.json`.

## Limitations and recommendations for the next session

1. **Resolve Decision D-1 before any new scientific run:**
   Under the literal support rule (`finite prediction > 0`), the verified
   5,167,373-pixel prior `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif`
   forces `1.0000` forward 3-px overlap for every nonempty candidate. Any change
   to that rule (e.g., evaluating continuous priors at `top-37,654` or `p >= 0.5`)
   requires explicit protocol-owner authorization in `registry/protocol_clarification.json`,
   never an agent-invented dense-prior exemption.
2. **Do not revive `G79-FABRIC-OFFSET` (`E1`), `H79-MCT`, or `H79-CSPT`:**
   - `E1` (`G79-FABRIC-OFFSET`) is stopped negative, and its post-stop offline
     diagnostic (`evidence/post_stop_diagnostic.json`) proved that even under
     Decision D-1 Option B or C it scores `HOLDOUT-DTI = 0.0474` (seed 20) and
     `0.0466` (seed 30), failing its matched zero-lag edge control and trailing
     the fold-fair H33 control (`0.0961` / `0.0989`).
   - `H79-MCT` and `H79-CSPT` both violated the literal overlap gate and used
     post-duplicate constrained overlap capping (`0.6800` and `0.6900`).
3. **If a future session is explicitly authorized to open a new lane after Decision D-1:**
   Preregister a new hypothesis before writing code, enforce the `300 m`
   (`buffer_px = 3`) buffer on all fold-derived features, run all feature-alone
   leakage canaries (`AUC <= 0.90`), evaluate pooled `HOLDOUT-DTI` (`gems57-pooled-hide-v2`)
   against the matched fold-fair H33 incumbent on seeds `20` and `30`, and run
   the unmodified novelty gate without post-duplicate overlap tuning.
