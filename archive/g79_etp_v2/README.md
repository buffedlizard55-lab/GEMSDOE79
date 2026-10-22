# G79-ETP artifacts — archived negative research, not active downloads

**Status:** archived; `OK TO SUBMIT: NO`. These outputs came into `main` in PR #70. They are not the canonical run in `run_card.json`, do not clear the literal registry novelty gate, and must not be submitted or regenerated. The active site is rebuilt from the canonical G79-THVC card; this folder preserves the ETP bytes for audit.

The original copies were in `docs/downloads/`. They were moved here byte-for-byte after the merged files caused the publication contract to fail (the contract permits only the canonical run-card TIFF in the active download folder). Each SHA-256 below is a `RASTER-SHA256` or file-integrity value, **not a score**.

| Historical output | Archived path | SHA-256 / evidence |
|---|---|---|
| ETP elastic-tip candidate, 28,761 dots | [`downloads/g79-etp-elastic-tip-28761dots-20261022T140921Z-e2203dcf-zeros.tif`](downloads/g79-etp-elastic-tip-28761dots-20261022T140921Z-e2203dcf-zeros.tif) | `e2203dcf897e210dc124b48138ad57690bc7f19ec3f2df3830acc64b7de90e67`; per-file receipt is beside it. The receipt describes its expected holdout value as a projection and says the shared hide-and-recover evaluation had not been run. |
| ETP relay-ramp candidate, 34,500 dots | [`downloads/g79-etp-relay-ramp-34500dots-20261022T140951Z-ce6c5fca-zeros.tif`](downloads/g79-etp-relay-ramp-34500dots-20261022T140951Z-ce6c5fca-zeros.tif) | `ce6c5fca4f1b2583bd3b4dbadfb1ec6839b20502fae4eeecf9bf1c4938a4afd8`; its historical run card is [`../../run_card_etp.json`](../../run_card_etp.json). |

The JSON companions beside the rasters are the original generator receipts and were preserved byte-for-byte. Any generation-time `ok_to_download` or `ok_to_submit` fields in those receipts are historical and **superseded** by the current negative cards/audit; the archived paths are not active downloads. The elastic-tip receipt's expected `+0.02–0.04` `holdout_estimate` is a **projection only**, not a measured score; no shared holdout, withheld-positive count or CI was produced for that run.

The relay card's reported `0.021` and `0.019` values are retained as a **CUSTOM_PROXY_NOT_COMPARABLE** report only; the card itself described approximate pooled truth rather than the required buffered whole-segment evaluator. They are not HOLDOUT-DTI results and are not used in any ranking. The card's pairwise `REGISTRY-OVERLAP = 0.4781` is only against G79-THVC; it checked one raster, not the full registry. It also records literal overlap `1.0` against the universal full-footprint witness, so it fails the controlling gate.

See [`evidence/etp_post_merge_audit_6515acc4.json`](../../evidence/etp_post_merge_audit_6515acc4.json) and [`reports/session_review_6515acc4.md`](../../reports/session_review_6515acc4.md) for the audit and disposition. No weekly slot was used for these research artifacts.
