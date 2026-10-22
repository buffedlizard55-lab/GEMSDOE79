# Superseded H33 narrative — do not use as evidence

This file replaces an earlier draft that over-attributed the user-reported `0.2778` value to a pruning mechanism and described deleted pixels as if their hidden-truth status were known. Those causal claims are withdrawn. The original text remains available in Git history for audit.

The correct evidence boundary is:

- `0.2778` is an **UNVERIFIED HISTORICAL REPORT**, not an organizer-confirmed score for the H33 TIFF.
- The source TIFF geometry is measurable: 37,654 positive pixels, all contained in D2.8; 6,436 D2.8 pixels are removed by the exact `d_cat <= 2 px` rule. This does not reveal the private truth or prove why a reported score changed.
- The DrivenData public leaderboard's `0.4413` is a separate **PUBLIC-LEADERBOARD OBSERVATION**, not H33's score or this repository's result. `0.3195` is an older user-reported benchmark, not the current public leader.
- Removing redundant predictions can reduce false-positive cost, while removing useful predictions can lose true-positive credit. The hidden labels decide which occurred; no causal attribution is supported.

Use the full current review in [`h33_review_e4a4422d.md`](h33_review_e4a4422d.md), the corrected research summary in [`../research/h33_analysis.md`](../research/h33_analysis.md), the byte record in [`../evidence/h33_forensics.json`](../evidence/h33_forensics.json), and the current official-source observation in [`official_sources.json`](official_sources.json). None is a submission receipt.
