# Repository review — 2026-10-22

## Executive outcome

The repository's active `run_card.json` is an E1 **negative** run in lane
`G79-FABRIC-OFFSET`. It authorizes download of one newly computed research
GeoTIFF, but explicitly does not authorize submission. A literal pre-placement
overlap witness stopped the registered experiment; the authorized E1 run placed
no final dots and did not run the holdout or leakage canary. No current score is
claimed for this artifact, and no competition slot has been used.

The repo had serious current-vs-historical conflicts: the root README and
published Pages HTML described `H79-CSPT` as promoted, while the active run card,
status JSON, preregistration and negative evidence described a different lane
and an automated rejection. The stale positive Pages copy linked an older
candidate. This review made active README/Pages content derive from the negative
run card and removed those obsolete files from the active `docs/downloads/`
folder. The separate historical files under `submissions/` and old analysis
records are not evidence for the current run and were not promoted.

## Pass 1 — inspect and implement

- Read the current README, `AGENTS.md`, run card, irregularity log,
  preregistration, current status, evidence and site builder before changes.
- Found that `scripts/verify_project.py` treated `registry/template_pin.json`
  `files` as a list of `{path, sha256}` records, but the actual pin schema is a
  filename-to-SHA-256 object. Changed verification to check each named file in
  `vendor/gems57/` against the frozen map.
- Found `scripts/build_site.py` expected `registry_index.json['repositories']`,
  while the frozen index contains `rasters` and `scored`. Changed the displayed
  repository count to derive from the actual indexed raster records.
- Rebuilt the static Pages site from the negative run card. It now states
  **OK TO DOWNLOAD: YES / OK TO SUBMIT: NO**, links the active research-only
  artifact, and exposes the automated rejection rather than a human-inspection
  placeholder.
- Removed three obsolete positive H79-CSPT artifacts from the public download
  directory; retained historical records outside the active download path.
- Replaced H79-CSPT-era tests that asserted promotion/old scores with tests of
  current artifact hashes, format-only validity, negative status, and ZIP
  integrity. Replaced tests for an obsolete feature API with software-only
  numerical helper tests. Updated the README to retain the persistent brief,
  parallel-run protocol, and three-pass procedure without continuing to present
  old promotion claims as current.

## Pass 2 — review assumptions, bugs, edge cases

- Confirmed a local format PASS is kept separate from scientific approval. The
  status checker returns a machine-readable negative decision and exit code 2.
- Confirmed the active artifact is not renamed from an old registry raster and
  the public download directory contains only the current run-card TIFF.
- Confirmed missing cached bulk inputs do not silently become zero-filled
  measurements. This checkout lacks `.cache/data/` and the full restored feature
  inputs; the stopped E1 must not be restarted just to obtain a score.
- Found a second test inconsistency: test assumptions expected the vendored
  uniqueness helper not to contain a binding helper, although the actual frozen
  pin explicitly records a local amendment and the code contains it. Replaced
  that assertion with byte-pin and amendment-disclosure checks. This does not
  certify that the helper is upstream code.
- Kept the legacy experiment runner unexecuted: importing it fails because it
  expects a different `FEATURE_NAMES` API. No attempt was made to adapt it to
  restart the scientifically stopped run.

## Pass 3 — full requirement re-check

- Persistent prompt/values and this review are present in the README.
- `research/hypotheses.md` documents four ranked hypotheses and named mimics;
  only the preregistered top hypothesis was computed. The stop is honored; no
  second or third experiment, new lane, registry exemption, submission-slot
  selection, or upload was performed.
- The H33 explanation is qualitative and mechanism-based. The 0.2778 number is
  treated as a reported historical score without an artifact-linked receipt;
  this review does not claim a causal score decomposition or leaderboard gain.
- The registry and data source receipts explicitly separate owner-mirror
  consistency from organizer authentication. Missing private data, login,
  submission capacity and organizer receipts remain limitations.
- The final machine card, site status and status script agree: download yes,
  submit no, `verdict = negative`, no human inspection required for that
  automated decision.

## Verification performed

Using the repository lockfile in a local virtual environment:

- `pytest -q`: **104 passed**.
- `python scripts/verify_project.py`: **all 19 consistency/format/status checks
  passed**; raster SHA-256
  `8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca`.
- `python scripts/check_site.py`: **passed**, 7 pages, 107 local links checked,
  all pages reachable, two compatibility redirects, no external assets.
- `python scripts/submission_status.py`: returns JSON with `ok_to_download=true`,
  `ok_to_submit=false`, `verdict=negative`; exit code 2 is expected for this
  blocked artifact.

These are repository-integrity and local-format checks, not an organizer upload,
scientific holdout score, private leaderboard result, or uniqueness clearance.

## Remaining limitations / next steps

1. The literal overlap definition currently admits a whole-footprint prior,
   making every nonempty candidate fail. Obtain an authoritative protocol
   clarification before any further novelty clearance or scientific run.
2. Review `registry/template_pin.json` and the local amendments to `vendor/gems57`
   with upstream provenance. The pin is self-contained; do not describe it as
   proof of upstream source integrity. Do not bypass the current gate.
3. `src/gems79/features.py`, `scripts/run_experiment.py`, portions of
   `tests/`, and historical H79-CSPT documentation originated in incompatible
   prior work. The runner is currently unimportable and is not the registered
   E1 method. Quarantine or reconcile this code through a separately reviewed
   change before treating it as reproducible science.
4. The post-stop diagnostic reports weak performance and does not turn the
   stopped run into a promotion candidate. A different hypothesis requires a
   new authorized preregistration after issue 1 is resolved.
5. This environment cannot authenticate to the DrivenData account, verify the
   current weekly cap, upload files, or obtain organizer receipts. No score above
   H33 or the public leaderboard leader is established.
