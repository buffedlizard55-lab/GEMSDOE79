# Repository review — Arena session `7c7104d8` — 2026-10-22

## Executive decision

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The current canonical H79-NHR TIFF
already existed at the start of this review. It is byte-distinct from checked-in
registry hashes and passes the local GeoTIFF/range validator, but it failed the
registered duplicate gate. It is a negative research artifact, not an approved
competition submission. No new candidate TIFF, model, holdout, final-dot placement, slot
selection, or DrivenData upload was performed in this session. The pinned
registry witness was restored and verified only in the ignored `.cache`; it is
not a submission artifact.

The literal new-lane preflight was actually rerun with the pinned witness:

```text
state: impossible_under_literal_gate
start_new_lane: false
covered_allowed_fraction: 1.0
limit: 0.70
overlap for every nonempty candidate: 1.0 > 0.70
exit code: 2 (expected stop)
witness SHA-256: ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be
```

This is a **REGISTRY-MEASUREMENT**, not a score. Under the literal protocol,
there is no permitted nonempty submission to score or place in a weekly slot.
The separate matched-budget interpretation in archived work is not silently
adopted here. The existing H79-NHR file also exceeds the overlap threshold
against ordinary, non-space-filling registry dot fields, so resolving only the
universal-support witness would not promote it.

## Answer to the H33 question

The checked-in byte forensics (`evidence/h33_forensics.json`) show H33 is not a
newly trained geological detector. Its positive pixels are exactly a subset of
the earlier D2.8 dot raster after removing dots within 200 m of the mapped
catalogue: 44,090 D2.8 dots became 37,654 H33 dots; 6,436 were removed and the
pixel-set disagreement is zero. These are **RASTER-MEASUREMENTS**, not scores.
The `0.2778` filename/score pairing in the prompt is an **UNVERIFIED HISTORICAL
REPORT**: no submission-page receipt binds that score to the H33 filename and
raster hash.

A plausible metric mechanism is improved emission efficiency. The competition
metric's TP credit is distance-weighted and saturates at each truth pixel,
whereas positive prediction mass away from truth adds FP. Removing redundant
near-catalogue dots can therefore improve the index if they add more FP than
lost credit. It is **not proven** that the removed dots were false positives:
only exact mapped-fault pixels are masked, and an unknown expert fault may lie
near a mapped trace. The byte relationship explains a plausible mechanism, not
a causal decomposition of the hidden test score.

The last checked-in public-leaderboard observation is dated 2026-10-21 and
records a public first-place entry above the prompt's `0.3195` claim. This is a
**PUBLIC-LEADERBOARD OBSERVATION**, not an artifact-linked submission receipt;
it was not refreshed in this session. The user-reported H33 value is not proof
that the H33 bytes earned that value. A higher leaderboard result is possible in
principle, but none of the current offline evidence establishes that this
project can beat H33 or the current organizer test set.

## Current holdout evidence — historical H79-NHR run, not rerun here

The prior run card reports the following **HOLDOUT-DTI** values. Each is from
evaluator `gems57-pooled-hide-v2`, a whole-component buffered catalogue
hide-and-recover split, and includes the withheld-positive count and 95% CI:

| Seed | Candidate HOLDOUT-DTI | Fold-fair H33-control HOLDOUT-DTI |
|---|---|---|
| 20 | 0.1431; 11,321 withheld positives; 95% CI [0.1281, 0.1574] | 0.0961; 11,321 withheld positives; 95% CI [0.0837, 0.1086] |
| 30 | 0.1522; 11,342 withheld positives; 95% CI [0.1335, 0.1696] | 0.0989; 11,342 withheld positives; 95% CI [0.0842, 0.1120] |

The NHR result beat the fold-fair H33 control on this proxy, but its surface and
final dots failed registry novelty. This is not an ORGANIZER-CONFIRMED result,
not a leaderboard score, and not a projection. The leakage result is a separate
**LEAKAGE-CANARY**: 464 feature-alone tests cleared the 0.90 threshold, with
maximum symmetric AUC 0.8589. No canary or holdout was rerun in this review.

## Repository inspection and three passes

### Pass 1 — read and establish the current state

- Read the full README, including the preserved prompt; `AGENTS.md`; canonical
  `run_card.json`; active NHR and archived E1 preregistrations; irregularities;
  current status; source ledger; relevant uniqueness, holdout, validator,
  writer, build, test, and site code; and the prior hypothesis registers.
- Confirmed the request's single-method paragraph is not delimited, as already
  recorded under IR-79-02/IR-79-41. The active H79-NHR lane is already stopped.
- Installed the pinned Python environment from `requirements.lock` and reran
  `scripts/preflight_new_lane.py --restore`. It independently restored and
  verified the existing witness and returned exit 2. No experimental feature
  or candidate surface was built.
- Inspected current storage: only `data/reference/existing_faults.tif`,
  `data/reference/sample_submission.tif`, and the restoration receipt are
  present; the large training raster, `.cache` feature stack, raw GeoDAWN line
  products, raw MT tensors, and raw 1 m DEM are absent. The owner's hash pins
  verify mirror consistency, not organizer-origin authentication.

### Pass 2 — identify and fix a repository defect; review hypotheses

- Found two incompatible-looking declarations for `scikit-image` in
  `requirements.txt` (`>=0.25,<0.27` and `>=0.25,<1`). Although pip intersects
  these constraints, the duplicate was unnecessary and obscured alignment with
  the exact `0.26.0` lock. Removed the redundant broad declaration and added a
  regression test that rejects duplicate normalized package names in either
  requirements manifest. Logged this as IR-79-67. No locked package version or
  scientific artifact changed.
- The previous shortlist in
  `research/hypotheses_preflight_a7d092d7.md` was checked against the archives.
  Its far-field idea is adjacent to archived H79-FF; its cross-scale scarp idea
  is adjacent to tested SDPT features; and its magnetic/scarp and clay-cap ideas
  overlap prior E1/STEPCO and hydrothermal family work. They cannot all be
  described as wholly untried across the family.
- Added a new, explicitly unvalidated three-hypothesis research shortlist to
  `research/hypotheses_session_7c7104d8.md` and the generated Research page:
  raw GeoDAWN flight-line residual coherence, raw MT phase-tensor anisotropy,
  and a process-based lidar scarp-profile fit. It names each data layer,
  physical signature, fault-omission rationale, method difference, non-fault
  mimic, official source link and data-availability check. All three are blocked
  in this checkout; the list is not an authorization to run them.
- No new official website was fetched. The source links and descriptions are
  inherited from `knowledge/official_sources.json` and earlier source reviews;
  direct DrivenData, USGS and GDR requests are outside this sandbox's host
  allowlist. The local source-health feed's last attempt remains dated
  2026-10-21; the daily GitHub Actions workflow is the configured refresh
  mechanism, but no current fetch result is claimed here.

### Pass 3 — acceptance re-check

- Rebuilt the static site from the canonical run card and current research files.
  It continues to display **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO** and makes
  the automated rejection explicit without asking for a human inspection.
- Reopened the canonical TIFF through the shared local validator. It remains
  single-band float32, EPSG:32611, shape 3730 × 3292, with the sample's exact
  100 m transform, finite values in [0,1], and no NaN inside the footprint.
  Its file SHA-256 remains
  `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`.
  These are **RASTER/FORMAT-MEASUREMENTS**, not organizer acceptance.
- Reconfirmed the card, status CLI and Pages agree on a negative verdict;
  the status CLI's exit code 2 is expected. No account slot, upload, or
  ORGANIZER-CONFIRMED receipt is present.
- Verification after the final doc/test edits: `pip check` passed; `verify_project.py`
  passed all checks; `check_site.py` passed all seven pages, 120 local links and
  two compatibility redirects; `pytest -q` passed 231 tests (one upstream Rasterio deprecation warning only);
  `git diff --check` also passed. These are software/format checks, not a new
  scientific holdout or organizer acceptance result.

## New candidate shortlist: rank, cost, and blockers

The ranked list lives in
[`research/hypotheses_session_7c7104d8.md`](../research/hypotheses_session_7c7104d8.md)
and is published on the Research page. Ranking is qualitative, **not DTI and
not a score projection**:

1. **Raw GeoDAWN line-level anomaly coherence** — medium-high potential,
   high cost. It would test whether a basement anomaly persists across adjacent
   flight lines after tie-line and height effects are modeled. The official
   USGS release is the source lead; actual raw line files and footprint coverage
   are not verified in this checkout.
2. **Station-level MT phase-tensor anisotropy** — medium potential, high cost.
   It could add direction and frequency-depth structure beyond scalar
   `cond_surf`; the official DOE GDR submission is the source lead. Raw MT
   tensors/station coverage are absent and direct download was not checked.
3. **Process-based lidar scarp-profile inversion** — low-medium potential,
   medium-high cost. It would fit a fixed scarp diffusion profile rather than
   repeat an edge/curvature amplitude detector. Official USGS 3DEP is the source
   lead; raw DEM tiles and target-area availability are absent/unverified.

All current candidate sources therefore fail the user's availability gate for
this session. The top candidate was **not** evaluated on HOLDOUT-DTI: the
literal registry gate stops every nonempty candidate before holdout, and its raw
input is also missing. No weekly slot was touched. The next allowed scientific
step is not training; it is an explicit prospective protocol clarification and
verified source/data access.

## Limitations and manual-review links

- [DrivenData problem description / metric / format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition / leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DOE competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE GDR / INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [Official DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)

Claim-by-claim source dates, licensing notes and evidence limits are in
[`knowledge/official_sources.json`](../knowledge/official_sources.json). Links
are supplied for review; they do not mean those external hosts were fetched
again in this session. No claim here establishes a current leaderboard value,
submission receipt, remaining weekly capacity, geothermal vent, productive
reservoir, or commercial viability.
