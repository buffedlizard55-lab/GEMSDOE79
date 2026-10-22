# Shared template provenance

Most files in `gems57/` are byte-identical to
`buffedlizard55-lab/60GEMSDOE@b99591eede63c6d45c8a896255b8cd34824fa00b/src/gems57`.
**The blanket claim that every file is unchanged upstream was incorrect:**
`uniqueness.py` includes previously documented shared amendments. The authoritative
local SHA-256 pins, prior digests, upstream blob identifiers and amendment notes
are in [`registry/template_pin.json`](../registry/template_pin.json).

The shared evaluator, pooled metric, buffered whole-component split and submission
writer remain unchanged in review `e4a4422d`. `verify_project.py` checks every pinned
file. Reuse these shared tools; do not create lane-local metric or writer forks.
A shared defect must be fixed once, with a version note and irregularity entry.
Explicit data paths avoid the vendored-root ambiguity.

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

## Shared writer v2 — explicit NaN exterior (IR-79-232)

`write_submission(..., exterior="nan")` accepts only finite, real model arrays in
[0,1], zero outside the exact template footprint, and zero on supplied catalogue
pixels. It explicitly serializes that exterior as NaN; it does not fill or clip
bad model predictions. Both shared on-disk validators support this opt-in mode.
The default remains `zeros` for historical reproducibility, **not official R6
compliance**. The current canonical file is unchanged and still blocked.

Pins retain the previous digests; historical default-policy audit receipts remain
historical, not rerun results. The evaluator and novelty rules are unchanged.
Tests reopen TIFF and ZIP using the independent project R1–R8 validator, check
interior identity, reject malformed inputs, and ensure no approval is granted.
The patch is exported in `reports/upstream_patch_nan_exterior_v2.diff` for template
maintainers; it has not been merged into the external template repository.
Future selector integration must explicitly choose the new format mode and still
rederive every scientific and account-side gate. This repair authorizes no lane.
