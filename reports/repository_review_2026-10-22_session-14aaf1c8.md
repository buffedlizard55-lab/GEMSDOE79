# Repository review — 2026-10-22, session `14aaf1c8`

## Executive decision

**Current artifact: OK TO DOWNLOAD: YES / OK TO SUBMIT: NO.** The active
research GeoTIFF is byte-distinct and locally format-valid, but its novelty
checks failed. The protocol's literal positive-support definition has a
hash-verified witness covering every allowed cell, so any nonempty candidate
would exceed the 70% overlap limit. The preflight was rerun with witness restore
and returned the expected fail-closed exit code **2**. No new experiment, TIFF,
upload, or submission slot was used in this review. I did not weaken the gate,
reinterpret the registry, or copy a prior submission.

This is a repository and evidence review, **not** a new scientific result. The
current NHR HOLDOUT-DTI values below belong to its already-closed lane and are
not leaderboard scores or evidence that this review's work beats H33.

## Pass 1 — inspect the project and evidence

Read `AGENTS.md`, the complete `README.md`, `run_card.json`, the irregularity
log, active/archived preregistrations, current status code, site, verifier,
feature/experiment scripts, the hypothesis backlog, source ledger, and the
associated evidence. Checked the tracked branch and worktree before making
changes. The repository's active contract is H79-NHR negative; its active
GeoTIFF is intentionally labelled `DO-NOT-SUBMIT`.

### What the repository establishes

- Canonical file: `docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif`.
- SHA-256: `abbf5314b7941569216a907849278c0dad0c67c130a6b9269cf2e6e1d50ee7a2`.
- Local validator evidence: one-band float32, EPSG:32611, 3730 × 3292, sample transform, finite values in [0,1], no NaN, and no positive cells outside the allowed footprint. This is local format/range validation, **not** organizer acceptance.
- The active card reports **HOLDOUT-DTI** from `gems57-pooled-hide-v2`: seed 20, 11,321 withheld positive pixels, 0.1431 [0.1281, 0.1574]; seed 30, 11,342 withheld positive pixels, 0.1522 [0.1335, 0.1696]. The card says both exceed its H33 fold-fair control, but novelty fails and the lane is stopped. These values cannot be transferred to another raster or called a leaderboard result.
- The active final-dot comparison failed: 26 ordinary registry dot rasters each had >70% of candidate dots within 3 pixels; the cited worst was 0.913. The surface test also failed. The card records no organizer receipt and zero slots used.
- Independent literal-gate preflight: `scripts/preflight_new_lane.py --restore` restored and hash-checked the pinned witness, then returned `impossible_under_literal_gate`, `covered_allowed_fraction: 1.0`, overlap limit 0.70, and exit 2. This is scoped to the protocol's literal positive-support interpretation; it is not a judgment that the geology is impossible.
- The automatic submission checker reports `ok_to_download=true`, `ok_to_submit=false`, with no human inspection needed for this negative verdict. It exits 2 by design for the blocked artifact.

### H33 / score interpretation

The repository's raster for H33 is measured as an exact subset of an earlier
D2.8 binary dot set: 44,090 to 37,654 cells, removing 6,436 cells within 200 m
of the mapped catalogue. This supplies a plausible metric mechanism: the
competition's maximum-credit TP kernel can saturate near each truth, while
additional positive mass contributes false-positive cost. Pruning can
therefore help if it removes redundant predictions. It does **not** establish
that every removed point was false, nor does the byte comparison prove what
caused any score change.

The H33 value **0.2778** appears as a public/user-provided historical score
association in the repository, but the repository has no submission-page
receipt that binds that score to the named TIFF's SHA-256. Its identity and
causal explanation therefore remain unconfirmed. The repository's dated
official leaderboard observation (2026-10-21) records a public leader at
**0.4413**, which conflicts with the prompt's separate 0.3195 figure. These
are time-specific observations, not candidate scores. No claim that this work
beats either number is justified.

Official reference links recorded by the project:

- [Competition problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Competition submission-format PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Official reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- Full source claims, access notes, and evidence classes: [`knowledge/official_sources.json`](../knowledge/official_sources.json).

These sources do not authenticate the mirrored input bytes, provide this
artifact's remote acceptance, or certify a score. The official data and
submission pages require a logged-in account in the project's recorded checks.

## Pass 2 — review hypotheses, assumptions, and failure modes

Four ranked, explicitly qualitative ideas are already documented in
[`research/hypotheses_preflight_a7d092d7.md`](../research/hypotheses_preflight_a7d092d7.md):

| Rank | Hypothesis and layers/signature | Why potentially missed by the catalogue / difference from active work | Mimic; cost |
|---|---|---|---|
| 1 | Far-field conditional recovery using elevation, RTP/isostatic gravity, lidar scarp descriptors, and visible-only catalogue context; validate distance bands, especially >1 km. | Tests lineaments beyond NHR's near-catalogue concentration rather than refitting the pooled near-fault target. | Lahontan shorelines and alluvial-fan margins; medium-high. |
| 2 | Cross-scale scarp-crest migration from lidar `lapneg/lappos`, `step_max`, `coh100`, and multiscale elevation curvature. | Tests persistent degraded scarps omitted from regional linework; distinct from SDPT's crest/base dipoles. | Terrace risers and abandoned shorelines; medium. |
| 3 | Magnetic marker termination supported by a narrow lidar step (`rtp`, `tmi_hg`, `cross_max`, `upface/downface`). | Targets covered structures interrupting magnetic fabric; differs from E1's gravity-edge/nonzero-lag registration. | Intrusive contact or flight-line levelling seam; medium. |
| 4 | Conductivity-edge discordance across gravity structure (`cond_surf`, depth-to-base, isostatic gravity, lidar scarp), not conductivity maximum. | Targets possible covered fluid-pathway boundaries; unlike STEPCO's cap-breach formulation. | Saline playa or lithologic conductor; low. |

These are pre-experiment research hypotheses, not validated results. Under the
currently recorded literal novelty gate, the correct next action is **not** to
run candidate 1 on holdout: the universal-support witness rejects every
nonempty final map before experiments. Testing it anyway would violate the
requested stop-before-experiment rule. No external dataset is needed to state
these ideas, but the provenance of some mirrored derived layers is not
independently authenticated in this environment. If a later approved method requires independent lidar input, first verify the exact USGS 3DEP product, footprint, access, and license from an official source; this review did not verify a new product fetch or its availability.

Other important limitations:

1. `data/raw/` and the large feature cache are absent in this checkout; only the
   small reference rasters are present. Do not silently treat missing data as
   zero or claim the full training pipeline can run from this checkout alone.
2. No DrivenData authentication is available to inspect the live weekly cap,
   select a submission, upload, or get a receipt. Do not request credentials in
   chat or infer account-side status.
3. The submission format validator establishes local consistency only. It
   cannot establish portal acceptance, rights/eligibility, organizer scoring,
   or uniqueness under a different protocol interpretation.
4. The backlog's experimental hypotheses are not automatically "new" relative
   to every sibling repository listed in the prompt. Uniqueness must be
   established against the pinned registry under the active protocol, not by
   renaming a method or changing TIFF bytes.
5. The current README is intentionally extensive because it stores the full
   prompt and provenance as requested. It is auditable but long; future
   maintenance should keep the visible decision summary concise and preserve
   the full prompt/history in a clearly marked archive section.

## Pass 3 — verification and disposition

Created an isolated environment from `requirements.lock`; no project runtime
files or scientific artifacts were changed. Results:

- `pytest -q`: **230 passed**, one upstream Rasterio `PendingDeprecationWarning`.
- `python scripts/verify_project.py`: **all checks passed** (including active
  card/evidence/hash, format, ZIP, publication, pinned-template, and status
  consistency checks); artifact SHA-256 matched the card.
- `python scripts/check_site.py`: **passed**, 7 pages, 120 local links checked,
  all pages reachable, 2 compatibility redirects, 0 external assets.
- `python scripts/preflight_new_lane.py --restore`: expected refusal,
  **exit 2** (`impossible_under_literal_gate`). The initial no-restore invocation
  correctly failed closed with exit 3 because the local witness was not
  restored; after restoring, the actual pinned witness verified and produced
  the definitive exit 2.
- `python scripts/submission_status.py`: **OK TO DOWNLOAD: YES / OK TO SUBMIT:
  NO**, exit 2 as expected.
- No upload artifacts or scientific evidence changed during review.

### Recommendation

Keep the active file prominently marked **DO NOT SUBMIT**. Before any future
scientific experiment, the protocol owner must prospectively clarify how
continuous, space-filling registry rasters count as "dots"; do not silently
change definitions or skip the shared gate. Then create a separately
preregistered lane, use the shared hide-and-recover evaluator and writer, run
each-feature leakage canary, beat the matched holdout incumbent with uncertainty
reported, and run pre-placement and final-registry checks before a separate
selector considers a slot. No submission slot is recommended or selected here.
