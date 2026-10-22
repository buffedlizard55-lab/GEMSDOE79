# Repository review — 2026-10-22, session 0c9f6bad

## Outcome

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** No new experiment, raster,
placement, registry rescan or competition submission was performed. H79-NHR
remains stopped negative. A different byte hash alone would not establish
protocol uniqueness. No valid path to a newly promoted submission was established.

## Pass 1 — contract and implementation

Read the README in full (including the preserved original prompt), AGENTS,
canonical card, both required preregistrations, irregularities, current status,
selector, shared pin contract and existing five-hypothesis NHR table. The table
already ranks layers, signatures, missing-catalogue rationale, differences, costs
and mimics. Its unexecuted ideas are not validated improvements and were not run.
The active method is stopped under the mandatory duplicate rule; a repeated
request to improve the result does not justify quietly bypassing that rule.

Changes:

- Replaced README's routine verification recipe, which retrained the stopped lane
  and placed dots before checking uniqueness, with read-only scientific verification.
- The separate selector now reconciles existing evaluator/novelty evidence with
  the card and requires every named gate with literal boolean `true`, not just an
  aggregate PASS. Missing/malformed evidence refuses approval. This checks frozen
  consistency; it does not recompute holdouts or authenticate their provenance.
- Qualified causal claims about H33 and removed the claim that a U-Net strategy
  is *required* to close the leaderboard gap. The actual hidden-label effect of
  pruning is unknown. Architecture suggestions remain untested hypotheses.

## Pass 2 — bugs and edge cases

A clean pinned install exposed a reproducible CI defect: test collection imported
`skimage.filters.sato` from `src/gems79b/features.py`, but scikit-image was absent
from both dependency lists. Added it and pinned its five-package dependency
closure (scikit-image, imageio, lazy-loader, networkx, tifffile). No scientific
algorithm or shared template bytes were changed.

Added software-only regression fixtures covering complete receipts, empty/missing
gates, nonliteral booleans, hash mismatch, a new failed gate, disagreement with
frozen measurements, and missing/malformed evidence. These are not geological
validation results or simulated organizer receipts.

## Pass 3 — final verification

- Installed exact `requirements.lock`; `pip check`: passed.
- Full software tests: **202 passed**.
- `verify_project.py`: all checks passed; reopened TIFF/ZIP, input pins, shared pins,
  evidence/card consistency and negative publication contract verified.
- `build_site.py`: seven pages built, negative decision retained.
- `check_site.py`: seven pages, 114 local links, all passed.
- `submission_status.py`: expected exit **2**, negative; no human inspection needed.
- Ran selector evidence adapter against canonical evidence without invoking the
  mutating selector CLI: refused due to failed literal novelty receipt.
- No new scientific performance measurements. Frozen HOLDOUT-DTI and confidence
  intervals remain in the canonical card; they are not predictions of public DTI.

## Official sources and evidence boundary

The organizer's reference repository was reachable through GitHub and its README
was read at commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`:
<https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md>.
It explicitly supports CPU-only execution and says GPU training is faster;
the prompt's blanket claim that GPU is required is not supported by this source.
This does not establish training speed or efficacy in this repository.

Manual-review links (not newly fetched/verified in this session):

- Competition problem: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Account-side submissions and data: <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
- Leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- GeoDAWN: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>

Network access is restricted to GitHub and package registries. No claim of a
fresh official leaderboard, competition rules, external DEM availability, public
Pages freshness or account-side weekly cap verification is made. Conflicting
user-listed leaderboard figures cannot be resolved from the available evidence.
Input mirrors match frozen hashes but are not organizer-authenticated downloads.

## Next-session priorities

1. Resolve IR-79-53 at protocol-owner level before a new lane. Do not silently
   exclude dense registry rasters. NHR also fails against ordinary dot fields,
   so resolving saturation alone will not promote this TIFF.
2. If authorized, preregister one distinct method and its budget; run feature-alone
   canaries and buffered whole-segment holdout. Complete surface novelty before
   placement. Compare paired uncertainty with the declared incumbent.
3. Require final novelty and a separate evidence-bound selector decision. Account
   eligibility/remaining weekly slots are not observable here; do not auto-upload.
4. Obtain new official sources only through allowed, provenance-recorded means.
   Shoreline suppression remains a hypothesis, not a verified path to a prize.
