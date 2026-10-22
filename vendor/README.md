# Shared template provenance

Most files in `gems57/` are byte-identical to
`buffedlizard55-lab/60GEMSDOE@b99591eede63c6d45c8a896255b8cd34824fa00b/src/gems57`.
**The blanket claim that every file is unchanged upstream was incorrect:**
`uniqueness.py` includes previously documented shared amendments. The authoritative
local SHA-256 pins, prior digests, upstream blob identifiers and amendment notes
are in [`registry/template_pin.json`](../registry/template_pin.json).

The shared evaluator, pooled metric and buffered whole-component split remain
unchanged in review `778c4a96`. The shared submission writer has one prospective
operational amendment: v2 normalizes the atomically staged TIFF, ZIP and JSON
receipt to mode `0644`. Earlier `mkstemp` outputs inherited private mode `0600`,
which made a locally valid download unnecessarily inaccessible. The amendment
changes mode bits only—not TIFF/ZIP/receipt bytes, hashes, validation, gates or
scientific output—and is recorded in `registry/template_pin.json` and
`reports/irregularities.md`. `verify_project.py` checks every pinned file. Reuse
these shared tools; do not create lane-local metric or writer forks. A shared
defect must be fixed once, with a version note and irregularity entry. Explicit
data paths avoid the vendored-root ambiguity.

The literal novelty default remains mandatory for the active decision. Historical
`informative-halo-v4` and D-2 modes coexisting in the shared module do **not** give
this lane permission to ignore the user's literal gate or rescue a stopped run.
Prior patch exports and protocol notes remain under `reports/`.

Some historical module prose contains unverified reports and a simplifying
marginal-credit aside that is not generally valid for one dot covering several
truth pixels. We do not repeat that aside as a theorem or edit shared code to
conceal it. Exact numerical metric tests use a literal brute-force oracle.

The shared writer fixes ZIP-member time to 2026-10-08 for deterministic bytes.
That archive timestamp is **not** the scientific experiment/export time; the
original run card contains that provenance.
