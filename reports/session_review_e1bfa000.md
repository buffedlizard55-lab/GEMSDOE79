# Three-pass review — e1bfa000 — 2026-10-22

## Outcome

**No new TIFF generated; no competition submission approved; no slot used.** This does not complete the requested unique high-performing submission: the unchanged literal gate makes that request infeasible. It is a negative deliverable, not a substituted copied TIFF. The inherited research download remains available with an explicit DO NOT SUBMIT label.

## Pass 1 — repository, feasibility and implementation

Read the start-of-session contract, README/original brief, canonical and historical run cards, preregistrations, shared-code and source limitations. Recreated the pinned Python environment. Ran `scripts/preflight_new_lane.py --restore`: exit 2, pinned witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be` remeasured as covering every allowed cell. Any nonempty candidate therefore has literal overlap 1.0, exceeding 0.70. These are geometric measurements, **not scores**. Logged as an unavoidable duplicate before surface creation/placement. No retired lane restarted; no novelty thresholds changed.

Ran current input inspection: zero of thirteen pinned runtime inputs verified. The historical restore receipt agrees with manifest metadata but proves no current presence. This is not merely a GPU problem: the official reference README supports CPU training as well as GPU acceleration. Missing data and an infeasible gate are independent blockers.

Added `scripts/review_readiness.py`: one rejection-only, read-only command combining existing runtime input inspection, shared novelty preflight, shared local-format validation, and separate official-text format validation. Exceptions become unverified checks, not false PASSes; interrupts propagate. It does not restore data, mutate cards, select submissions, generate rasters or upload. JSON output uses exclusive creation and cannot overwrite old evidence. Four tests cover missing checks, local-versus-portal distinction, no implicit selector approval, and interrupts. Initial suite: **601 passed** (software tests, not scientific measurements).

## Pass 2 — scientific claims, bugs and edge cases

Reopened the inherited raster through both validators. Shared local format passes: finite values in [0,1], exact reference grid. Official-text validator fails R6: zero exterior where it expects NaN. The new combined report preserves both results and refuses approval. Neither validator recreates the portal backend; the rejected upload bytes/receipt are absent, so the previous portal message cannot be diagnosed.

Removed README's overclaim that the range error “cannot occur”; added an explicit local-versus-portal warning next to download controls in the site generator, then rebuilt Pages. Left frozen rasters, writer, evaluator and scientific receipts unchanged. Resolving the all-finite writer versus official-text exterior policy needs a shared prospective policy, not a private fork or a post-hoc modification to pass a candidate.

Reused and qualified four unexecuted backlog hypotheses in `research/hypotheses_e1bfa000.md`. No numerical uplift projected. External-data candidates are marked not data-ready: this environment permits GitHub/npm/PyPI hosts, not DrivenData/USGS/GDR/Dropbox/PDF hosts. GitHub official reference HEAD and README were checked through `gh`; source pin is in `evidence/reference_source_e1bfa000.json`. Other official links are historical context/manual-review links, not claimed freshly verified sources. The prompt's “single method paragraph” is not identifiable, so no lane was invented.

A second full suite found two broken-link tests because this report and the terminal card were not yet written. Created both files rather than weakening the checks. No scientific experiments were run.

## Why H33 could be more efficient — not proof of its reported score

The pinned historical forensic measurement (`evidence/h33_forensics.json`) identifies H33 as D2.8 pruned at catalogue distance <=2 pixels: 37,654 retained, 6,436 deleted, no retained pixels outside D2.8, and no deleted pixels exactly on catalogue pixels. These are historical raster measurements, not newly measured scores.

With T weighted true-positive credit, F weighted false-positive cost and G truth count, DTI is `T/(0.2T + 0.2F + 0.8G + epsilon)`. Deleting mass that adds little maximum kernel coverage can improve prediction efficiency. If a deletion loses a in T and removes b in F, it improves the ratio when `0.2*T*b > a*(0.2*F + 0.8*G + epsilon)`. This algebra explains a plausible advantage; it does not reveal hidden truth or establish causality. H33's reported value is not an artifact-bound organizer receipt. This review therefore does not present it, any leaderboard observation, or an older user benchmark as ORGANIZER-CONFIRMED, nor invent a HOLDOUT-DTI result.

A higher organizer score is possible in principle; none is demonstrated by this review. A research emphasis on geothermal conduits must still be validated against the competition's fault-recovery target, not treated as confirmed vent discovery.

Official metric reference for manual review: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/

## Pass 3 — end-to-end requirements and publication

Final verification results are recorded after this document is created: full pytest, `scripts/verify_project.py`, `scripts/check_site.py`, and `git diff --check`. The site keeps its research download prominent and the executive-summary guide intact; generated download notices now expose the separate R6 limitation. No new .tif/.zip was added and no byte hash was renamed as a novel submission. Machine-readable review evidence and a null-valued negative run card preserve the difference between not measured and zero.

The full original prompt remains in README. Existing scheduled Pages/source-health workflow remains; this review adds no unsupported live-feed claims. PR creation/merge will use the fixed session branch and explicit PR number; merge outcome is reported separately rather than preclaimed here.

## Next permitted steps / unresolved limitations

1. Resolve the comparator definition prospectively across lanes. The present positive-support witness makes the literal rule impossible; do not silently exempt it, jitter dots or retune overlap caps.
2. Resolve the shared writer's exterior policy against official rules without changing frozen artifact claims. Preserve both validators and test the template and candidate round-trip.
3. Restore hash-pinned inputs into ignored runtime locations only after lane feasibility is established; audit raw channel semantics, masks, coordinate transforms and external-source permissions/coverage.
4. Register one genuinely distinct method, run every feature-alone canary, then spatial whole-segment hide-and-recover and same-evaluator incumbent comparisons with withheld counts and cluster CIs. Stop at duplicates or budget exhaustion.
5. Only a separate selector can approve a slot. No account receipt/capacity is available here; no autonomous upload was attempted.

Terminal JSON card: `evidence/run_card_e1bfa000.json`. Automated combined receipt: `evidence/readiness_e1bfa000.json`.

### Final measured software verification

- Pass 3 full suite: **601 passed** (81.45 s); no scientific score implied.
- `scripts/verify_project.py`: exit 0.
- `scripts/check_site.py`: PASS, 13 pages, 341 local links, every page reachable, `submit:false`.
- `git diff --check`: exit 0.
- Combined readiness command: expected exit 2; no inspection exception, runtime missing, new lane unauthorized, local-format PASS, portal-text R6 FAIL.

### Concurrent-main reconciliation

PR #132 initially conflicted with concurrently merged reviews. Merged `origin/main` into the fixed session branch, preserved both README reviews, and regenerated only the derived Pages files. Preserved the incoming VENTPROX artifacts as inherited negative research, not artifacts generated or approved by this review. Post-merge verification: **601 passed** (81.30 s), integrity verifier exit 0, site PASS (13 pages / 341 local links). No scope expansion or new scientific run occurred.
