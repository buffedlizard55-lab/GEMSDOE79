# H79-NHR (session 337ac1e9) — stopped negative, archived

The H79-NHR lane ran on 2026-10-22 and stopped as a protocol duplicate after
beating the holdout best (HOLDOUT-DTI 0.1431 [0.1281, 0.1574] seed 20 /
0.1522 [0.1335, 0.1696] seed 30 vs H33 fold-fair control 0.0961 / 0.0989;
26 ordinary registry dot fields each contained > 70 % of its final dots within
3 px, worst 0.913 against a 0.610 chance level — IR-79-55).

Contents (moved byte-for-byte when H79-DCE became the canonical lane; the TIFF
SHA-256 `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`
matches the frozen run card):

- `downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif` — **DO NOT SUBMIT** (research artifact)
- `downloads/…-DO-NOT-SUBMIT.zip` — single-TIFF ZIP of the same bytes
- `downloads/…-DO-NOT-SUBMIT.json` — writer receipt
- `run_card_nhr.json` — the lane's canonical card at stop time (also preserved
  in git history and as `evidence/nhr/` evidence files)

Its evidence (`evidence/nhr/`), preregistration
(`registry/preregistration_nhr.json`) and analysis (`reports/nhr_analysis.md`)
remain in place and frozen. The lane is not restarted, retuned or
overlap-capped; the H79-DCE lane reuses its *surface* (rebuilt
hash-identically) under a new preregistered emission instead.
