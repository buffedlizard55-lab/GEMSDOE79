# Session review — `arena/220dabc8-gemsdoe79` (2026-10-22)

Three passes as instructed. Pass 1 produced the science; Pass 2 reviewed it
for bugs, missing requirements and overclaims and fixed what it found;
Pass 3 re-checked the whole implementation against the original request.

## Pass 1 — implement completely and verify

**Repository state found.** A mature, heavily audited repo whose canonical
lane (G79-FABRIC-OFFSET E1) had been stopped the previous day: the literal
registry-overlap rule is unsatisfiable (one prior covers the whole
footprint), and a post-stop diagnostic had already measured E1 below uniform
placement. Re-running E1 variants would have been theatre.

**Lane declared.** The request again contained no delimited method paragraph
(IR-79-41), so one lane was self-declared and preregistered before scoring:
**G79-STEPCO** — faults as cross-trace *steps* corroborated in independent
fields (detrended elevation, isostatic gravity, log depth-to-basement, RTP
magnetics, conductivity), with fixed step-dipole/gradient/Laplacian
transforms, all 19 competition bands, 1 m-derived lidar scarp channels and
GeoDAWN radiometric patterns (58 features), one fixed HistGradientBoosting
model refit per buffered whole-component hide-and-recover draw, and matched
emission (37,654 binary dots, 3 px spacing, catalogue >2 px excluded).
Five hypotheses were ranked first (`research/hypotheses_g79stepco_20261022.md`);
Decision D-1 was resolved prospectively in writing
(`reports/protocol_amendment_D1_20261022.md`) using the pinned shared tool's
own two-phase summary — no vendor byte changed, no threshold moved, literal
reading always printed.

**Results (all HOLDOUT-DTI, evaluator `gems57-pooled-hide-v2`).**

| Experiment | Seed 20 (n=11,321) | Seed 30 (n=11,342) | vs uniform | vs single-field ablation | vs H33-lineage incumbent |
|---|---|---|---|---|---|
| S1 | 0.0946 [0.0778, 0.1110] | 0.0948 [0.0782, 0.1115] | +0.046/+0.045, CI>0 | +0.054/+0.055, CI>0 | −0.0015 [−0.0153,+0.0110]; −0.0041 [−0.0191,+0.0111] → **tie** |
| S2-COVER | 0.0935 | 0.0961 | wins | wins | −0.0025 [−0.0156,+0.0104]; −0.0028 → **tie** |

Canaries: 464 single-feature tests, max symmetric AUC 0.684 (seed 20) / 0.661
(seed 30), limit 0.90 — no leakage signal. Uniqueness: surface ρ ≤ 0.518 and
final-dot ρ ≤ 0.086 across 986 grid-comparable registry rasters (992/992
accounted for); worst forward overlap vs 748 comparable sparse emissions
0.647 (S1) / 0.70003 (S2); 0.414 vs H33 itself. Both written GeoTIFFs are
locally format-valid by re-read (float32, EPSG:32611, [0,1], no NaN,
nodata=None, single-TIFF ZIP byte-identical).

**Verdict:** `negative` for both experiments. The preregistered promotion
gate required beating the incumbent with paired CI above 0 on both seeds; a
tie does not clear it, and uniqueness cannot be certified while space-filling
registry priors fire the like-for-like overlap reading (IR-79-43).

## Why did "H33 = 0.2778" lead the family, and can this beat it?

PhD-level answer, with receipts separated from reports:

1. **The number is not attached to the file.** No submission-page receipt
   links 0.2778 to the H33 hash. The GEMSDOE32 page (fetched this session)
   calls the file UNSCORED and its 0.2747 a projection. 0.2778 also appears
   as a participant value on the public leaderboard (leader 0.4413, fetched
   2026-10-22), which cannot identify a file. Treating 0.2778 as H33's
   measured score is an unverified historical report.
2. **What H33 is, byte-exactly:** D2.8's 44,090 isolated dots minus the 6,436
   within 200 m of the catalogue → 37,654 dots (this repo's forensics,
   reproduced from restored bytes). D2.8 in turn is a thinning of the H19-5
   supervised surface. So the "best model's" marginal gains over its parent
   were **emission geometry**, not new geology: under the max-cover DTI,
   TP saturates per truth pixel while every emitted pixel risks α=0.2 FP
   mass, so deleting redundant and catalogue-echo dots raises credit density
   at fixed recall. The score progression of the lineage
   (continuous 0.1922 → dotted 0.2477/0.2600 → pruned 0.2778-reported) is
   exactly that signature.
3. **Can STEPCO beat it?** On clean hide-and-recover it ties the lineage's
   actual dots while refitting honestly per draw — meaning its *ranking* is
   of comparable quality, independently derived (ρ = 0.52 to the nearest
   supervised prior, dot overlap 0.41 to H33). Organizer truth (expert faults
   absent from the catalogue) is a different distribution; catalogue-recovery
   performance neither proves nor refutes hidden-fault performance. The only
   honest route to "beats 0.2778" is a receipt, and spending a slot to get
   one is forbidden by the failed gates. Anyone claiming a projected
   leaderboard number for this file would be hallucinating.
4. **What the 0.4413 class likely does differently** (inference, labelled as
   such): a step change in ranking credit density (+60% over 0.2778) is not
   obtainable by emission tweaks on the same surface; it implies a stronger
   detector — plausibly GPU segmentation ensembles and/or full 1 m DEM
   exploitation — plus the same dotted emission discipline. That is a
   compute-and-data program, not a prompt away.

## Pass 2 — bugs, gaps and edge cases found and fixed

- **Registry restore rate limit:** parallel `gh api` exhausted the REST
  budget instantly. Replaced with blobless sparse clones (git protocol),
  then 3 single-blob fetches after reset; all pins verified (IR-79-44).
- **Missing registry files:** 3 indexed rasters had been renamed upstream;
  restored by blob SHA, completing 992/992 accounting. 6 files are
  grid-invalid (wrong/zero origin, format test, corrupt) — documented with
  diagnostics instead of silently dropped or force-compared.
- **Uniqueness self-deception check:** the like-for-like reading still fired
  on a space-filling lattice *after* D-1. Reported `protocol_unique=false`
  rather than extending the amendment post hoc; S2's 0.70003 sparse overlap
  reported exactly, not rounded to 0.70.
- **Experiment shopping guard:** S3 was considered (lidar-regime
  stratification) and rejected after a diagnostic showed no regime collapse
  (NE no-lidar AUC 0.63–0.68; the global model already carries a regime
  indicator). Two ties + a diagnostic do not justify a third search.
- **Publication contract:** writer outputs landed in `docs/downloads/`
  alongside the E1 canonical file; resolved by archiving E1 and S2
  byte-identical so exactly one canonical artifact is published, and
  generalising `verify_project.py` to check the STEPCO card against its
  measured evidence while keeping E1's stop checks pointed at the archive.
- **Tooling slips caught by tests/checkers:** parallel edits to one file
  raced (reapplied sequentially); site evidence subdirectory links, preview
  filename and status scope were fixed until `check_site.py` passed
  (7 pages, 117 local links).
- **Status semantics verified end-to-end:** `scripts/submission_status.py`
  on the STEPCO card returns download YES / submit NO (exit 2) with the
  correct surviving blockers; canary and holdout-format gates clear
  individually without producing approval.

## Pass 3 — re-check against the original request

| Requirement | Status |
|---|---|
| Unique newly generated TIF, obvious download, obvious submit decision | **Met.** Hero download is STEPCO S1; decision states OK TO DOWNLOAD: YES / OK TO SUBMIT: NO everywhere (README, site, status.json, run card, filename). |
| Validation without human intervention | **Met.** `submission_status.py`, `verify_project.py`, `validate_submission.py`, pytest + site checks are fully automated and fail closed. |
| Unique name + ≤140-char note | **Met** (104 chars), copyable on the site, enforced by the shared writer. |
| "Predicted values must be in range [0, 1]" fixed | **Met locally.** No-sentinel/no-clip writer + re-read verification; cause documented; organizer acceptance not claimed. |
| Executive-summary subpage explaining exactly how to submit | **Met** (`docs/executive-summary.html`): gates, slot check, form steps, receipt discipline. |
| Study why 0.2778 led; beat it if honestly possible | **Answered; not beaten.** Emission-efficiency mechanism proven from bytes; 0.2778 shown unreceipted; STEPCO ties the lineage on holdout and is therefore not promoted. No projection invented. |
| 3–5 new hypotheses ranked before implementing; validate top on blocked holdout | **Met** (5 hypotheses, preregistration, canaries before scores, two-seed pooled holdout vs 3 controls). |
| Parallel-run protocol (lane, shared tools, labels, canary, run card, budget) | **Met with one documented amendment (D-1).** 2/3 experiments inside the 2 h scientific clock (01:26–02:11 UTC); shared vendor files byte-unmodified; every number labelled HOLDOUT-DTI or UNVERIFIED HISTORICAL REPORT; run card complete. |
| Original prompt preserved in README; Core Values visible | **Met** (tail of README byte-preserved; values in README + site footer). |
| PR created and merged to main | Done at the end of this session via `gh` (see PR link in the session report). |
| No hallucinations; official links for manual review | Official pages re-fetched this session (problem, metric, leaderboard, GEMSDOE32); every quantitative claim traces to an evidence JSON or an official URL. |

## Limitations and what to do next (Maximize P(Win))

1. **Owner decision D-1 v2:** classify registry priors by emitted-mass class
   (sparse emissions vs tilings vs continuous surfaces) so the overlap gate
   tests duplication instead of density. Until then no candidate in this
   family can be certified unique — by construction, not by geology.
2. **If a slot is ever to teach us something,** the highest-information
   experiment is a *receipt-generating* submission of an already-archived
   strong lineage file by the account holder — but that is a selector/owner
   decision this pipeline must not make, and it would spend a slot on a
   non-unique file. Not recommended by these gates.
3. **Real headroom:** GPU segmentation ensembles on the 19-band stack + 1 m
   DEM tiles (official free source: USGS 3DEP via the provided
   `1m_DEM_links.csv`; GeoDAWN grids DOI 10.5066/P93LGLVQ), each behind the
   same preregistration/canary/holdout/uniqueness gates. Expect the binding
   constraint to remain catalogue-vs-hidden distribution shift: validate on
   detached-component folds, not just quadrant folds.
4. **Sandbox limits that bound this session:** 2 vCPU / ~4 GB RAM (no GPU
   training), no DrivenData auth (no uploads, receipts or slot counts;
   data via hash-pinned GitHub mirrors), REST rate limits for bulk registry
   work (git-clone route documented), 21 GB disk (registry clones live in
   `.cache/`, never in Git).
