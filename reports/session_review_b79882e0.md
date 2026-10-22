# Three-pass review — session b79882e0, 2026-10-22

## Outcome

**OK TO DOWNLOAD: YES / OK TO SUBMIT: NO.** No new scientific experiment, raster, upload or weekly slot was used. The requested protocol-unique, submittable TIFF remains **unfulfilled**, not silently waived. The existing canonical research artifact remains downloadable from the home page and executive summary, with its warning intact.

## Pass 1 — inspect and independently verify the blocker

Reviewed README (including the embedded original request), AGENTS, active and archived preregistrations, canonical card, irregularities, hypothesis backlog, shared witness measurement, readiness/selector scripts, tests and publication workflows. Installed the pinned Python requirements in ignored `.venv`.

Executed `scripts/preflight_new_lane.py --restore --report evidence/new_lane_preflight_b79882e0.json`. The freshly restored, hash-verified witness returned exit **2**, `impossible_under_literal_gate`. Its SHA-256 is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`; allowed-cell coverage is exactly **1.0**, above the **0.70** overlap limit. Those numbers are REGISTRY-MEASUREMENT, not scores. A nonempty candidate cannot clear the literal positive-support rule. This is why no new surface, placement or holdout was attempted; the stopped NHR lane was not restarted.

The four ranked, unexecuted hypotheses in [the existing backlog](../research/hypotheses_preflight_a7d092d7.md) remain the preimplementation shortlist. They name layers, signatures, catalogue-missing rationale, differences, cost and confounders. Their ranking is qualitative judgment, not projected DTI improvement. None is newly validated here. No additional external-data proposal is represented as obtainable.

## Pass 2 — defect and regression review

Found a software boundary defect: preflight's `decision()` rejects malformed certificates, but exceptions raised *while loading* malformed manifest containers (`TypeError`, `AttributeError`) or restoring via a failed subprocess could escape `main()` without the promised JSON refusal. This did not authorize a lane, but broke machine-readable automation.

Fixed the CLI inspection boundary to convert all ordinary inspection exceptions into exit **3**, `state=unverified`, `start_new_lane=false`. It exposes only the exception class, not filesystem details. `KeyboardInterrupt` and other process-control exceptions remain uncaught. Report creation remains exclusive: existing evidence is never overwritten. No shared scientific code, pins, thresholds, data, selector receipt or scientific card changed.

Regression coverage injects malformed-container and restore errors, verifies report/stdout agreement and absence of private error text, and confirms interrupts propagate. These are software fixtures, not experiments.

## Pass 3 — full contract recheck

- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q`: **245 passed**, one Rasterio pending-deprecation warning.
- `.venv/bin/python scripts/verify_project.py`: **all 29 checks passed**, including byte pins, artifact/ZIP identity, format, evidence reconciliation, stopped-lane and publication rules.
- `.venv/bin/python scripts/check_site.py`: **PASS**, 7 pages, 120 local links, 2 compatibility redirects, no external assets.
- `.venv/bin/python scripts/submission_status.py`: expected exit **2**, download true, submit false; no human inspection needed for this negative decision.
- Rebuilt the evidence-driven site and repeated the checks before commit. Canonical scientific card and raster bytes remain unchanged.

Software counts and format checks are not scientific scores. The unchanged run card records HOLDOUT-DTI with evaluator version, withheld counts and confidence intervals; no artifact-bound ORGANIZER-CONFIRMED receipt exists.

## Scientific interpretation and verification limits

[Existing H33 analysis](nhr_analysis.md) explains the metric mechanism: 300 m triangular-kernel maximum truth credit versus per-pixel false-positive cost can reward less redundant sparse placements. H33 pruned the older dot field near mapped traces. This is **not** proof that its reported competition result was caused by that pruning, nor a guarantee of improvement. Nearby dots can still credit hidden faults. The reported H33 value and conflicting leaderboard targets in the request must not become verified scores without artifact-bound receipts. No new leaderboard performance is claimed.

Official reference repository availability was freshly checked with `gh api repos/drivendataorg/gems-prize-reference-solution`: [organizer reference](https://github.com/drivendataorg/gems-prize-reference-solution). This checks public repository metadata, not a new scientific validation. Network access here is restricted to GitHub and package registries. DrivenData, USGS, NLR and GDR pages were not freshly fetched in this session; existing source records retain their original scope. Relevant review links:

- [Official competition problem and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [USGS GeoDAWN data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [Existing irregularities](irregularities.md), especially outside-footprint convention conflict IR-79-69.

The project predicts faults, not verified geothermal vents or commercially usable reservoirs. Local all-finite range/grid PASS does not resolve the outside-footprint convention conflict or establish organizer acceptance.

## Next session, in dependency order

1. Resolve the protocol definition of dots in continuous registry surfaces prospectively. Do not silently exclude witnesses or retune the stopped lane. The software cannot invent that authorization.
2. Resolve the official sample/description versus reference-output outside-footprint discrepancy before producing any future upload artifact.
3. Only after those blockers are resolved, preregister one distinct method from the backlog; use the cached stack, shared evaluator/writer, per-feature leakage canaries, buffered whole-segment holdout and both novelty checks. Enforce the experiment/time budget and require independent selector clearance.
4. Establish account-side eligibility, slot availability and an artifact-bound organizer receipt before describing any real submission as accepted/scored. No credentials were requested or stored.

Canonical scientific JSON card: [run_card.json](../run_card.json). This review is not a new scientific run card and does not promote the existing negative result.
