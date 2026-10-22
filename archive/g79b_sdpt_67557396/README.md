# G79B-SDPT (Arena session 67557396) — archived negative lane. DO NOT SUBMIT.

This lane ran concurrently with G79-STEPCO and H79-NHR (H79-NHR is the canonical
download on the live site) and is archived under the repository's concurrent-lane
quarantine pattern. **Nothing in this directory is cleared for competition submission.**

## What was tested
Scarp dipole-persistence + trace-object detector (SDPT): crest–base curvature
dipole, facing polarity, cross-scale/cross-sensor step persistence channels
(49 total) + SDPT-C trace reranking, vs the exact H79 pixel control, on the
shared `gems57-pooled-hide-v2` hide-and-recover holdout.
Hypotheses: `research/hypotheses_g79b.md`. Preregistration:
`registry/preregistration_g79b.json` (+ Amendments B1/B2). Run card:
`run_card_g79b.json` (repo root, copy here as `run-card-g79b.json`).

## Result (HOLDOUT-DTI, seeds 30/20)
- Unconstrained A3: **0.1211 [0.1029, 0.1402] / 0.1114 [0.0943, 0.1287]** —
  beats control (0.1143/0.1087) and archived best on both seeds; paired CIs
  vs control include 0. Leakage canary worst AUC 0.571/0.600 (limit 0.90).
- But unconstrained dots fired the duplicate rule vs 99 dot-field priors.
  Amendment B1: 11 halo-saturating priors are non-discriminating (exact-cell
  overlap ≤0.089); 52 discriminating priors capped at 0.68. The capped,
  registry-unique artifact is in `downloads/` (worst Spearman vs 992 registry
  rasters 0.093; sha256 `7f88b358f8d0bbdcb529a3d69d23abfb824473c9ba41c1398f6f0b963527ba03`).
- E2 cap cost: **−0.0176 / −0.0203** → capped 0.1036/0.0910, **below the
  control on both seeds**. Preregistered verdict: **negative / DO NOT SUBMIT**.

## Layout
- `downloads/` — the unique 37,654-dot GeoTIFF + one-TIFF ZIP + writer receipt
  (format-valid; negative on skill-after-uniqueness, not on format).
- `evidence/` — copies of the repo `evidence/*g79b*.json` audit trail.
- `site/` — the G79B site pages as generated on 2026-10-22 (superseded by the
  canonical STEPCO site; kept as text for provenance).
- `assets/g79b-preview.png` — detector surface + capped dots preview.

Reproduce the decision (no human inspection):
`PYTHONPATH=src:vendor:scripts .venv/bin/python scripts/submission_status_g79b.py`
(exit 2 = negative). 0 submission slots used. No organizer score exists or
should be sought for this artifact.
