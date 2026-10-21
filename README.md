# GEMSDOE79 — lane H79-MCT "Mapper-continuity scarp traces"

DOE GEMS Prize Challenge (DrivenData competition 306) — one parallel-run lane of the
`buffedlizard55-lab` GEMSDOE family.  Site: https://buffedlizard55-lab.github.io/GEMSDOE79/
(GitHub Pages from `docs/`, enabled by the repository owner; see *Limitations*).

<!-- STATUS:BEGIN -->
## Status — ✅ OK TO DOWNLOAD · OK TO SUBMIT

| | |
|---|---|
| candidate | [`gems79-h79-mct-capped-37654-20261021T222726Z-2987c74e-zeros.tif`](downloads/gems79-h79-mct-capped-37654-20261021T222726Z-2987c74e-zeros.tif) · [zip](downloads/gems79-h79-mct-capped-37654-20261021T222726Z-2987c74e-zeros.zip) |
| sha256 | `d1a4158acb3b6593c659ef37749bc80c5af0ddf20c62357554462e0870b7df6d` |
| dots | 37,654 binary dots (float32 {0,1}, all finite, EPSG:32611, 3730×3292) |
| note (≤ 140 chars) | `H79-MCT terrain-only lidar+10m scarp likelihood x Sato line-continuity; 37654 binary dots 2.8px apart >2px off catalogue; zeros outside` |
| HOLDOUT-DTI (gems57-pooled-hide-v2) | seed30: 0.1023 [0.0853, 0.1203] (11,342 withheld px) · seed20: 0.0946 [0.0788, 0.1116] (11,321 withheld px) |
| ORGANIZER-CONFIRMED | none yet (not scored by the organizer) |
| uniqueness (like-for-like, binding) | worst forward overlap 0.6800 ≤ 0.70 · worst abs Spearman 0.0975 ≤ 0.90 · 765 discriminating / 43 space-filling priors |
| uniqueness (literal) | worst forward overlap 1.0000 against space-filling witnesses (43 priors); identical to a prior: False |
| verdict | **promote** — generated 2026-10-21T22:37:21Z |

Site: https://buffedlizard55-lab.github.io/GEMSDOE79/ · feed: `docs/status.json` · run card: `evidence/run_card_h79.json`
<!-- STATUS:END -->

## Read first, every session

1. **The project prompt below** (it is the operative brief; the owner asked for it to live in the README).
2. `reports/why_02778.md` — the PhD-level answer to the standing question and the plan derived from it.
3. `registry/preregistration_h79.json`, `research/h79_hypotheses.md`, `evidence/run_card_h79.json`.
4. `docs/irregularities.md` — everything that looked wrong and what was done about it.
5. `knowledge/` — verified facts with official links (`knowledge/data_sources.md`, `knowledge/competition_facts.md`).
6. Historical: `docs/PROJECT_BRIEF.md` and `docs/EXECUTIVE_SUMMARY.md` were written by earlier sessions while the
   checkout had no data ("no submission is ready"); they are superseded by the status block above and carry a banner.
   `scripts/validate_submission.py` (same origin) is an independent format preflight; the binding validator is the
   vendored `gems57` writer/validator used by `scripts/audit_h79.py`.

## What this repository does end to end (no human in the loop)

| step | script | output (evidence) |
|---|---|---|
| restore the 23 SHA-256-pinned inputs | `scripts/restore_data.py --ids all` | `data/raw/`, `evidence/restore_data.log` |
| fetch all 812 prior family rasters (git-blob verified) and pin them | `scripts/fetch_registry.py`, `scripts/build_registry_inventory.py` | `data/registry/`, `registry/registry_inventory.json` |
| build the catalogue-free terrain feature stack (30 channels) | `PYTHONPATH=src:vendor python -m gems79.features` (also run automatically by the scripts below) | `data/cache/features/stack.f32.npy`, `evidence/features_receipt.json` |
| hide-and-recover holdout with leakage canaries (pre-registered arms) | `scripts/run_holdout_h79.py --seed 30/20` | `evidence/holdout_h79_seed{30,20}.json` |
| build the candidate TIF through the shared fail-closed writer | `scripts/build_submission_h79.py` | `docs/downloads/*.tif/.zip/.json`, `evidence/build_h79.json` |
| validator + 812-raster uniqueness audit + RUN CARD + status feed | `scripts/audit_h79.py` | `evidence/registry_audit_h79.json`, `evidence/run_card_h79.json`, `docs/status.json` |
| render the site and this status block | `scripts/build_site.py` | `docs/index.html`, `docs/executive-summary.html` |
| tests | `pytest -q` | — |

Environment: Python 3.11, `pip install numpy scipy rasterio scikit-image scikit-learn pandas pytest`
(2 vCPU / 3 GB RAM is enough: nothing loads the 19-band stack at once).  Shared template code is
vendored unmodified in `vendor/gems57/` (pinned in `registry/template_pin.json`).

---

# Project prompt (operative brief — re-read at the start of every session)

*Stored per the project owner's instruction ("Put this prompt into the repo readme and read it
every time we work on the project").  Carried verbatim in substance from the family template
(GEMSDOE77 `PROMPT.md`); family addenda specific to other lanes are omitted here and this lane's
addendum is at the end.*

## Highest urgency

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION
UNLESS IT'S FOR LEARNING AND EDUCATION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT
THE GENERATED TIF. There should be an easy-to-download submission TIF as described by the prompt.
All validation is done by the project automatically — there is no human inspector. Read the entire
prompt.

## Parallel-run protocol (read first; this session is one of several)

1. **Lane.** Your lane is the single method paragraph assigned to the session. Stay inside it. If
   your raster's rank-correlation with any registry raster exceeds 0.90, or more than 70 % of your
   dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it
   as a duplicate and stop. Check on the surface before placement AND on the final dots.
2. **Reuse, don't rebuild.** Use the template's cached feature stack, `evaluate_holdout.py` and
   `submission_writer.py`. Holdout = hide-and-recover: withhold whole fault segments with a buffer,
   derive every catalogue-based feature only from visible faults, mask visible faults pixel-exactly,
   score pooled DTI (α = 0.2, β = 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it
   once in the template and report it; never keep a private fork.
3. **Label every number** as HOLDOUT-DTI (evaluator version, # withheld positives, 95 % CI) or
   ORGANIZER-CONFIRMED (submission-page receipt). A projection is never written as a score.
4. **Leakage canary.** Test each feature alone on the holdout first. AUC > 0.90 means leakage until
   proven otherwise.
5. **Run card.** End with one JSON card: hypothesis; mechanism; the named non-fault process that
   could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output
   (no NaN in footprint, values [0,1], CRS/shape/transform match); submission name + note ≤ 140
   chars; verdict promote/negative. Negative results are deliverables.
6. **Budget.** Stop after 3 experiments or 2 hours. Do not pick submissions: promotion is a separate
   selector step within the weekly cap.

## Standing science instruction

Before implementing, generate 3–5 candidate geological hypotheses not yet tried, each naming
layer(s), physical signature, why it catches a fault missing from the USGS/INGENIOUS catalogue, and
how it differs from anything in the repo. Rank by expected DTI improvement ÷ implementation cost.
Validate the top candidate on the spatially blocked holdout before touching a weekly slot — do not
spend a slot on an idea that hasn't beaten the current holdout best. If a candidate needs new
external data, name the specific free official source and check obtainability before proposing it
as viable. Only free, publicly available, official/verified data may be used. Work line by line
from official verified sources with links for manual review; flag irregularities; no hallucinations.

## Core values (focal point for all decisions)

- **Maximize P(Win)** — weigh tradeoffs, assess risk, choose the path that maximizes the
  probability of success; set emotions aside.
- **Own the Outcome** — own results end to end; act without waiting for permission when we have
  the means; treat failure and success as signals.

## The question to answer every session

Why did `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (GEMSDOE32) get the family's highest
reported score (0.2778), and can we generate a unique submission scoring higher? Answer with
PhD-level judgement, then use the answer to build the lane's candidate. Verify line by line; no
hallucinations. The leaderboard target quoted in the brief is to beat 0.3195 with a distinct
strategy (the organizer leaderboard top is 0.4413, read 2026-10-21).  → `reports/why_02778.md`.

## Competition anchors

- Overview/problem/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Forum: https://community.drivendata.org/c/gems-prize-challenge/111
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS: https://gbcge.org/current-projects/ingenious/
- EPSG:32611: https://epsg.io/32611 · Tversky: https://en.wikipedia.org/wiki/Tversky_index
- Data (login-walled): https://www.drivendata.org/competitions/306/competition-doe-gems/data/ —
  sandbox route is the owner's SHA-pinned GitHub mirrors (`registry/data_manifest.json` +
  `scripts/restore_data.py`); the Dropbox mirrors in the brief are unreachable from the sandbox.

## Submission mechanics (must stay obvious on the site)

Single-band float32 GeoTIFF (or ZIP with exactly one), same CRS/shape/geotransform as the sample
submission, values in [0, 1], outside-footprint cells zero (all finite). A previous portal upload
failed with "Predicted values must be in range [0, 1]"; the shared fail-closed writer now guarantees
an all-finite [0, 1] read-back with `nodata=None` (this file: 0 NaN, min 0, max 1). Every candidate
needs a unique name and a ≤ 140-char Note-field text. The site's first screen must state the
download/submit status in one glance; the executive summary explains exactly how to submit a
*promoted* file.

## Site & deliverables

GitHub Pages site (clean, simple UI) with an executive-summary subpage explaining exactly how to
submit; download-to-submit TIF obvious at the top; an obvious OK / NOT-OK statement; an auditable
table of data and sources with official links; gathered knowledge from official verified sources
stored in the repo; a feed of current status; stated limitations and needed access.

## Multi-pass working rule

Pass 1 implement + verify. Pass 2 review for bugs/assumptions/edge cases; fix. Pass 3 re-check
against the original request; improve; fix. Then open a PR and merge to `main` (from the session
branch only), with remaining-work and limitation suggestions for the next session.

## Family score list (OWNER-REPORT; highlights)

GEMSDOE32 h33-2-b2 **0.2778** · GEMSDOE36 anderson-geothermal-pinn 0.2750 · GEMSDOE28/31 h27-4-solo
0.2708 · GEMSDOE33 analog-tip-stepover 0.2632 · GEMSDOE25/30 dotted-h19-5-d2.8 / poisson300m 0.2600 ·
GEMSDOE70 p5-dual-submod300-oof38k 0.2478 · GEMSDOE24 dotted d1.5 0.2477 · GEMSDOE49 gate_ortho 0.2376 ·
GEMSDOE63 cvarlw-thin 0.2303 · GEMSDOE48 h59-cover 0.2296 · 19GEMSDOE h19-5 0.1922 · GEMSDOE10
h28-dotted-ridge 0.1839 · GEMSDOE 0.1563 · GEMSDOE46 scarp-radiometric 0.1589 · 7GEMSDOE lidarscarp
0.1461 · all other sites ≤ 0.1461 down to 0.0000.  The 95 organizer-scored rasters and their scores
are pinned in `registry/registry_inventory.json` (`organizer_confirmed_public_score`, as carried by
the family registry index).

## GEMSDOE79 addendum (this lane, 2026-10-21)

Lane declared before any experiment in `registry/preregistration_h79.json`: terrain-only scarp
likelihood × line-continuity → 37,654 binary dots.  Experiments used: 2 of 3 (seed-30 and seed-20
holdout runs); no slot selected.  Verdict, scores and uniqueness measurements are in the status
block at the top and in `evidence/run_card_h79.json`.

---

## Lanes already run in the family (do not repeat)

H19-5 ridges/dotting (and every re-dotting of it); H33 tip–step-over; Anderson PINN; gate_ortho;
SGMC contacts; LIA inversion; H77D hydrotect; H77E autoctx/Dinkelbach, fluvial de-seam, knickpoint;
H77G demag trough / gravity step; H77H piedmont relay, hydrostruct; H77V vent advection / sinter;
H77VDS fault-valve; H78; H79 cross-gradient / rad-halo / orientation; H80 orphan thermal, Riedel
wing-crack, tilt persistence, HGB; H81 slip-cone; H82 cool-outlet chemistry, rank-entropy, texture,
remanence, TC-step, FMD, GMNS; H83 netsib, PCD pseudo-gravity; H84 ramp-relay / or-gate; H85 EDTI
collar/skeleton, FTMR medial ridge; TSD; XSEN; BGB; 62G datum-Lahontan; gap-closure (GEMSDOE27).

## Limitations and access needed (honest list)

* **No organizer score exists for this file.**  All numbers are HOLDOUT-DTI on catalogue-like
  truth; the holdout is a gate, not a predictor of the live score.
* The sandbox can reach only github.com / api.github.com / pypi; drivendata.org, the forum and
  USGS servers were read through the agent's page fetcher or via the owner's GitHub mirrors.  The
  10 m 3DEP *elevation* itself (needed for H79-C Lahontan de-confounding) was not obtainable here.
* GitHub Pages must be enabled by the repository owner (Settings → Pages → `main` / `docs`); the
  sandbox token cannot change repository settings.
* The registry covers the 812 hash-verified family rasters indexed on 2026-10-21; it is not the
  organizer's registry of all submissions.
* 2 vCPU / 3 GB RAM: the full-footprint HGB and Sato passes are streamed; re-running everything
  from scratch takes ≈ 25 min plus ≈ 15 min for the 812-raster audit.
