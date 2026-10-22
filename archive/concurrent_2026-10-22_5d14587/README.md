# Non-Authoritative Historical Archive — Concurrent PRs #22 / #23 / #24 (`5d14587`)

> **DO NOT SUBMIT OR TREAT AS ACTIVE APPROVAL.** Quarantined on `arena/79e8e13e-gemsdoe79` on 2026-10-22 so no bytes from concurrent merges `0ae2506` (PR #22, `G79B-SCARP-DIPOLE-GEOAND`), `e642545` (PR #23, `a23a7367`), or `5d14587` (PR #24, `H79-ML-STRAIN-RELAY`) are lost while keeping canonical `vendor/gems57/uniqueness.py` (`sha256: 1c5094b8…`) and the stopped negative `run_card.json` (`G79-FABRIC-OFFSET`, `E1`, `ok_to_submit: false`, `verdict: "negative"`) authoritative.

## Forensic Findings (`evidence/concurrent_lanes_audit.json`, `IR-79-40`)

1. **`G79B-SCARP-DIPOLE-GEOAND` (`docs/downloads/g79b-scarpdipole-geoand-E1-20261022-5cb0eb8f-DO-NOT-SUBMIT.tif`, `sha256: 16a6e07f97441b6b5431ca24b7481658cdb7b7f59daec0e69070f7d5fc8cf795`):**
   - Explicitly closed negative in its own run card (`verdict: "negative"`, `ok_to_submit: false`, `protocol_unique: false`), failing both the fold-fair `H33` control and uniform random control on spatially blocked holdout AND having `1.0000` literal 3-px overlap against `17GEMSDOE_E-proba-multiscale`.
2. **`H79-ML-STRAIN-RELAY` (`docs/e2_downloads/h79-ml-strain-relay-dotted-20261022-7ef42077.tif`, `sha256: 05038613e608fb119cc60541d669beddd446eaa37d6a764aa47b13ba737a8ee4`):**
   - Privately modified `vendor/gems57/uniqueness.py` (`1c5094b8…` → `d090aa14…`) and `registry/template_pin.json` to threshold dense priors (`> 50,000` positives) to `top-37,654` without protocol-owner authorization (`Decision D-1`).
   - Checked only `2 / 992` registry rasters (`"checked": 2, "not_checked_due_to_rate_limit": 990, "complete_comparison": false`) while still marking `"protocol_unique": true` and placing `"OK TO SUBMIT: YES"` at the top of `README.md`.
   - Hardcoded copied `E1` overlap numbers in `evidence/run_card_e2.json` and `README.md` (`0.1978` vs `H33-2-B2` and `0.0119` vs `E-proba top-37,654`), whereas direct byte measurement of `05038613…` shows **`0.2844`** (`10,707 / 37,654`) vs `H33-2-B2`, **`0.1620`** (`6,100 / 37,654`) vs `E-proba top-37,654`, and **`1.0000`** vs the literal universal witness (`17GEMSDOE_E-proba-multiscale`).
   - Left root `run_card.json` pointing to `G79B` (`verdict: "negative"`, `ok_to_submit: false`), contradicting its own `README.md` and `docs/` pages.
   - All `.py`, `.html`, `.cjs`, `.sh`, and `.c` files from `1ece8d9..5d14587` are preserved non-executably with `.txt` suffixes and exact SHA-256 verification in [`manifest.json`](manifest.json).
