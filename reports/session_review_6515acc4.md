# Three-pass review — session `arena/6515acc4-gemsdoe79`

**Date:** 2026-10-22 (UTC)
**Scope:** continue the geothermal-fault competition audit after the ETP merge; identify genuinely untried geology hypotheses, honor the literal novelty stop, reconcile historical ETP artifacts and H33/D2.8 prose, preserve canonical download/status behavior, and review evidence before PR/merge.

## Pass 1 — Scientific and protocol review

- Reviewed five unexecuted candidate transforms, ranked qualitative potential separately from cost. No numerical DTI improvement was forecast. See [`research/hypotheses_6515acc4.md`](../research/hypotheses_6515acc4.md).
- The single-method paragraph referenced by the task remains absent; the memo records this ambiguity rather than assigning an invented lane.
- Excluded ETP relay/ramp (already implemented), archived Coulomb strain-transfer/footwall-shadow, and claimed-as-new local K/Th ratios. The cross-fitted K residual is explicitly incremental.
- Re-ran the shared literal novelty preflight and preserved its machine-readable decision in [`evidence/preflight_6515acc4.json`](../evidence/preflight_6515acc4.json): exit `2`, `impossible_under_literal_gate`, witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, covered allowed fraction `1.0`, overlap limit `0.70`.
- **Top candidate HOLDOUT-DTI: NOT RUN.** The preflight proves that any nonempty candidate would have literal overlap `1.0`; no feature extraction, leakage canary, holdout, placement or TIFF generation followed. This is a protocol stop, not an evaluator score. No submission slot was selected or used.

## Pass 2 — Provenance and evidence review

- Reviewed `knowledge/official_sources.json`, `registry/data_manifest.json`, the GDR receipt and local source files. Claim-by-claim disposition and URLs are in [`evidence/official_source_audit_6515acc4.json`](../evidence/official_source_audit_6515acc4.json).
- No official page was freshly fetched during this session. Exact MT product availability is unverified and no MT volume exists in the current raw-file manifest; ARIA has no locally pinned product or source receipt; 3DEP raw/derived inputs are absent; GeoDAWN line/drape metadata were not restored. These candidates are research-ranked, not presented as viable datasets.
- Corrected the run-card witness digest to the preflight-measured SHA-256. The session card reports `HOLDOUT-DTI` as `NOT RUN`, null result/CI/withheld-positive count, no candidate raster SHA, no new submission name/note, zero experiments and zero weekly slots. Canonical G79-THVC evidence remains separately identified as a research artifact, not an organizer score.
- Reclassified the ETP card's `0.021` and `0.019` as `CUSTOM_PROXY_NOT_COMPARABLE`; its evaluator was approximate, its registry scan was incomplete, and its literal overlap against the full-footprint witness is `1.0`. The elastic-tip receipt's expected `+0.02–0.04` is marked `PROJECTION_NOT_RESULT`; no projection is presented as a score.

## Pass 3 — Code, publication, and delivery review

- Archived all six ETP TIFF/ZIP/JSON companions byte-for-byte under [`archive/g79_etp_v2/`](../archive/g79_etp_v2/README.md), with per-file SHA-256 values in [`archive/g79_etp_v2/relocation_receipt.json`](../archive/g79_etp_v2/relocation_receipt.json). Only the canonical G79-THVC TIFF, ZIP and JSON remain in `docs/downloads/`.
- Added fail-closed lifecycle guards to both ETP generator entry points before input reads or writes. Regression tests assert the scripts refuse and leave active downloads unchanged.
- Corrected README/site-facing status so `OK TO DOWNLOAD: YES` applies only to the existing canonical research artifact and `OK TO SUBMIT: NO` lists all automated blockers. Updated H33/D2.8 prose to state that `0.2778`/`0.2600` are unverified historical reports, not linked organizer scores; removed the unsupported causal-gain claim.
- Final checks after archival and site generation: `verify_project.py` **PASS** (`all_checks_passed: true`, including only-canonical-publication and status/card agreement); `check_site.py` **PASS** (7 pages, 154 local links, all reachable, submit false); `pytest -q` **359 passed, 0 failed**. `submission_status.py` returns exit `2` with `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.` and blockers `literal_novelty_not_cleared`, `negative_scientific_verdict`, missing selector approval, missing/unbound selector receipt, and missing explicit submission approval. The site build generates 7 pages with the same status.

## Findings that remain open

1. The protocol owner has not clarified the literal novelty rule; do not bypass it locally.
2. The exact GDR-1391 MT product and current remote availability are unconfirmed.
3. No shared holdout experiment was run and no new candidate raster exists.
4. DrivenData account eligibility, remaining weekly capacity, explicit approval and organizer acceptance are not established.
5. No fresh official-site retrieval was made; the source audit distinguishes prior source review from current local file availability.

## Final disposition

The new candidate remains **blocked / negative / not submitted**. The existing G79-THVC research artifact remains the only active downloadable TIFF. This review is not a submission approval and does not claim an organizer score. PR and merge identifiers will be added after the requested review flow completes.
