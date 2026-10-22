# G79-ETP artifacts — archived, not cleared for submission

These files were added to the repository by the merged `G79-ETP-v2` change on 2026-10-22. They are preserved byte-for-byte as research artifacts, but have been moved out of `docs/downloads/` so the site and automated publication contract expose only the canonical, explicitly gated artifact.

## Contents

- `downloads/g79-etp-elastic-tip-28761dots-20261022T140921Z-e2203dcf-zeros.tif` plus its `.zip` and metadata JSON
- `downloads/g79-etp-relay-ramp-34500dots-20261022T140951Z-ce6c5fca-zeros.tif` plus its `.zip` and metadata JSON
- Historical run card: [`run_card_etp.json`](run_card_etp.json)
- Verbatim Pages evidence copies: [`docs_evidence/`](docs_evidence/)
- Root registration and hypothesis notes: [`../../registry/preregistration_etp.json`](../../registry/preregistration_etp.json) and [`../../research/hypotheses_etp.md`](../../research/hypotheses_etp.md)

## Audit findings

1. **Do not submit either raster.** Neither is the canonical TIFF in `run_card.json`, and no separate selector or organizer receipt approves either.
2. The registration file's `sha256` field is the literal placeholder `a1b2c3d4...`, not a valid SHA-256 of the complete registration contents. The `run_card_etp.json` repeats this placeholder as `preregistration_sha256`; the pre-result registration cannot be authenticated from these records.
3. The card labels its two performance values `HOLDOUT-DTI`, but its evaluator description explicitly says “approximate pooled truth” and “official hide-and-recover requires full segmentation pipeline.” Therefore those numbers are **not accepted as protocol-compliant HOLDOUT-DTI** and must not be compared with the canonical `gems57-pooled-hide-v2` results. The 28,761-dot TIFF has no corresponding full run card in this directory.
4. The uniqueness receipt records only one full-grid registry comparison despite stating 1,108 expected rasters. Its reported pairwise overlap is not a complete-registry uniqueness certificate.
5. The preregistration stop threshold refers to a single random baseline value but does not document the prescribed segment-withhold, buffer, exact visible-fault masking, pooled evaluator run, or feature-by-feature leakage protocol. The experimental process needs independent reconstruction before its results can be used.

## File integrity

Moving the rasters did not alter their bytes. SHA-256:

- Elastic-tip artifact: `e2203dcf897e210dc124b48138ad57690bc7f19ec3f2df3830acc64b7de90e67`
- Relay-ramp artifact: `ce6c5fca4f1b2583bd3b4dbadfb1ec6839b20502fae4eeecf9bf1c4938a4afd8`

The card, registration and experiment scripts are retained for audit. Archiving is an administrative publication boundary, not a reinterpretation of the science or permission to rerun the lane.
