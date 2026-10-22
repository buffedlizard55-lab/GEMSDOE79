# Three-pass review — 50335987, 2026-10-22

## Executive decision

**OK TO DOWNLOAD: YES (inherited research artifact). OK TO SUBMIT: NO.**
No new candidate TIFF, copied submission, scientific surface, placement, holdout,
canary or competition upload was made. The urgent new unique TIFF requirement is
**not fulfilled**: the mandatory preflight forbids it, rather than requiring a
human inspection. No alternative novelty definition was silently adopted.

## Pass 1 — repository and executable gate audit

- Re-ran `scripts/preflight_new_lane.py --restore`: exit 2. The hash-pinned
  registry witness covers all allowed cells. Any nonempty prediction has forward
  overlap 1.0 against that witness, exceeding the stipulated limit. This is a
  REGISTRY-MEASUREMENT / mathematical obstruction, not HOLDOUT-DTI. See
  `evidence/preflight_50335987.json`. No complete fresh registry scan is claimed.
- Re-ran `scripts/data_status.py`: exit 2, no manifest inputs present under
  `data/raw`. Reference grid/catalogue files exist separately. Historical restore
  receipts do not prove runtime readiness (`evidence/runtime_data_status_50335987.json`).
- The prompt's single assigned method paragraph is absent. Deferred three ranked
  existing untried proposals in `research/hypotheses_50335987.md`; no stopped lane
  restarted. No expensive input restoration was attempted after the decisive stop.
- Inspected the download/prepare scripts. They restore pinned owner mirrors and
  reproduce an old E1 cache, not an automatically ready new GPU-training pipeline.
  The official reference README offers CPU training too; a GPU is not categorically
  required. Data placement is not the only blocker.

## Pass 2 — actual software defect and fix

`src/gems79/portal_spec.py` discarded the inner TIFF's R1 result after checking a
ZIP had one member. A single multi-band TIFF therefore could incorrectly pass
R1 when zipped. Fixed in that central validator, without a private evaluator or
writer fork: archive R1 and inner single-band R1 must both pass. A junk TIFF inside
a valid ZIP now produces a negative validation report instead of a Rasterio
exception. Regression tests exercise both direct and ZIP routes, including a
nested member path. Temporary synthetic test fixtures are not research submissions.

Targeted tests: **16 passed**. Full software suite: **599 passed**. These are
SOFTWARE-TEST counts, not scientific scores. The shared scientific modules and
pinned TIFF/ZIP bytes were unchanged.

Revalidated the canonical download and ZIP with the official-text validator:
both fail R6 (zero exterior instead of NaN). Both pass in-footprint finite/range,
single-band, dtype, CRS, shape and transform checks. Machine receipt:
`evidence/portal_spec_50335987.json`. No cause is claimed for the user's past
range error: the rejected file and its organizer receipt are unavailable.

## H33: what can actually be concluded

Freshly fetched GEMSDOE32's `docs/index.html` through GitHub's contents API. Its
H33 note still says **UNSCORED** and includes a projection; that projection is not
an experimental score and is not reused. The user-reported H33 result is not
ORGANIZER-CONFIRMED without an artifact-linked submission-page receipt.

The inherited pixel audit (`evidence/h33_forensics.json`) establishes near-catalogue
pruning, not hidden-label performance causality. Under the shared metric, if
T is weighted true-positive credit, F weighted false-positive cost, and G scored
truth count, DTI = T / (0.2T + 0.2F + 0.8G + epsilon). Removing redundant dots
can reduce F while preserving T because truth recovery uses maximum nearby
credit. Removing useful dots can instead harm recall. Therefore H33 suggests
redundancy control, not a theorem that a wider collar or another thinning will
win. See `knowledge/h33_review_e4a4422d.md` for the conditional deletion inequality.
No result here demonstrates improvement over any reported leaderboard score.
Fault recovery is not certification of a geothermal vent or commercial reservoir.

## Pass 3 — publication and requirements review

Simplified the homepage: removed ambiguous “new unique” archive claims and bare
historical score rankings from the hero; it now separates grid/range validity,
R6 failure, and novelty refusal. Narrowed the executive summary's “every research
TIFF” format claim to the three artifacts actually in its frozen calibration.
README now links this review before historical sections. Original prompt remains
in README, not replaced with a false claim of task completion.

The canonical run card, scientific receipts, evaluator, writer, inventory and
archived files are unchanged. `submission_status.py` independently returns the
negative decision without a human inspector. Full build, site and project checks
are recorded in the verification receipt accompanying this review. Existing
Pages workflow remains responsible for publishing after merge; deployment is not
assumed to have succeeded merely because local HTML builds.

## Source scope / limitations

- Fresh official source read: [reference solution README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md).
  Confirms CPU/GPU environment options and separate data download; does not
  authenticate local mirror data or promise performance.
- Fresh owner-source read: [GEMSDOE32 page source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/index.html).
  Not an organizer receipt. Other family sites were not freshly exhaustively crawled.
- Official manual-review links: [problem/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
  [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
  [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
  These hosts are outside this sandbox's outbound allowlist. No fresh official
  board, account capacity or PDF verification is claimed.
- Highest-priority next step is a prospective shared definition of registry dots
  resolving the saturated witness, not another renamed candidate. Then restore
  pinned inputs, audit feature semantics, freeze untouched validation, and test
  one mechanism within budget. Resolve exterior writing against official format
  before an eligible future export. None authorizes an upload of stopped files.

## Concurrent-main reconciliation before merge

Main advanced during review. Incorporated the d754356b and e1bfa000 reviews and
preserved the incoming vent-proximity negative artifact without generating or
endorsing it. The 148fa8f5 session independently fixed the same inner-ZIP defect
and added driver validation and a broader fail-closed inspection boundary. Adopted
that shared implementation rather than retaining a competing version; kept this
session's direct/ZIP regression cases. Thus this PR's final validator content is
identical to that incoming fix, not a second private validator. Rebuilt generated
pages and reran the combined suite after resolving conflicts. Earlier test counts
above describe the pre-integration checkout, not the enlarged final suite.

Final integrated verification: **609 software tests passed**; site build, site-link
checker and project verification passed. No new scientific measurements.

A further main merge added a201fa92's independent official-format promotion gate.
Retained it. Its ignored restored inputs are not present in this workspace.
Integration tests exposed an inherited gap in issue IDs and a stale AGENTS.md
reference; assigned this review's three findings IDs 221–223 to fill that gap
and corrected the writer-policy reference to 227. No gate thresholds changed.

After the final gate integration and issue-reference fixes: **611 tests passed**;
site build, link check and project verification passed again.

The subsequent main follow-up 17e9049 independently closed its issue-number gap.
Retained that published numbering and AGENTS reference (writer policy = 224);
this review's three findings use session-scoped IR-50335987-01 through -03 to
avoid further concurrent collisions. This supersedes the intermediate numbering
repair described above; no executable code changed in this last reconciliation.
