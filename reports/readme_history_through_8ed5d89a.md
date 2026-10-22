# README status history (archived 2026-10-22, superseded by the H79-NHR README)

> Relative links rebased with `../` so they resolve from `reports/`, and archived download links point at their archive location. The text is otherwise verbatim.

Verbatim copy of README.md lines 1–260 at commit 1ece8d9. Historical; not current instructions.

## GEMSDOE79 — auditable fault-discovery research

## Download and submission decision — start here

**OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. Automated verdict: `negative`.**

### Current repository review — 2026-10-22 (session `8ed5d89a`)

**Critical release conflict repaired:** PR #12's H79-CSPT pages advertised approval,
while the canonical run card still rejected E1. Its uniqueness procedure excluded
space-filling priors and changed the shared tool; this is not allowed by the
literal parallel-run protocol. All incoming work is preserved with byte hashes in
[the non-authoritative CSPT archive](../archive/h79_cspt_3d386a3/README.md), outside
the published website. The original shared tool, registry and input pins, stopped
lane and full original prompt below are restored. No new experiment or weekly
submission slot was used. Final local checks: **122 tests passed**, 7 pages /
109 links verified, and 21 responsive browser cases passed. [Three-pass review and next steps](../reports/session_review_8ed5d89a.md).

A fresh independent [witness re-measurement](../evidence/session_witness_review_8ed5d89a.json)
confirms that every allowed cell is within the prior's positive support halo.
**No nonempty candidate can pass the current literal overlap rule.** A different
filename or byte-distinct TIFF does not fix this. The existing research download
remains **DO NOT SUBMIT**; no higher leaderboard score is claimed.

[**Download existing research GeoTIFF — DO NOT SUBMIT**](../archive/g79_fabric_offset_e1/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif) · [Single-TIFF ZIP](../archive/g79_fabric_offset_e1/downloads/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.zip) · [Machine run card](../run_card.json) · [Executive summary / submission guide](../docs/executive-summary.html)

This is a **newly computed, byte-distinct research surface**, not a copied prior
submission and **not protocol-unique**. Its name deliberately includes
`DO-NOT-SUBMIT`. SHA-256:
`8f8c2cd17b8484a8ab61fbc7b370e3dde6ed4cedeb2d1ee362e9d9c214bb64ca`.

The unmodified shared validator reopens the written bytes and confirms a
single-band float32 GeoTIFF, EPSG:32611, shape 3730 × 3292, exact sample
transform/bounds, all values finite and in [0,1], zero positive mass outside the
footprint and on the mapped catalogue. This prevents the reported numerical
range hazard; **local format validity is not organizer acceptance**. The earlier
portal rejection cannot be diagnosed without the rejected file and server
receipt.

### Concurrent session re-verification and post-stop diagnostic, 2026-10-21

Re-checked line by line from official pages, restored bytes, and the post-stop
diagnostic on `arena/70519113-gemsdoe79`; see
[`evidence/session_verification_2026-10-21.json`](../evidence/session_verification_2026-10-21.json),
[`evidence/post_stop_diagnostic.json`](../evidence/post_stop_diagnostic.json),
and irregularities IR-79-22 to IR-79-29 in [`reports/irregularities.md`](../reports/irregularities.md).

- **Format:** the downloadable GeoTIFF is float32, one band, EPSG:32611, 3730 × 3292,
  100 m, identical transform to the sample, values in [0,1], no NaN. Local format
  PASS only; not organizer acceptance.
- **Duplicate gate:** the 17GEMSDOE E-proba raster (commit `6fc71d19…`, sha256
  `ab0a0a62…`) covers all 5,167,373 footprint cells, so the literal gate forces overlap
  = 1.0 for any candidate. **Decision D-1** (how to define "dots" for continuous
  rasters) belongs to the protocol owner. The agent did not change the gate.
- **Sample:** the official sample's 60,988 ones are exactly the USGS/INGENIOUS
  catalogue cells, despite the page's "total fault absence" wording.
- **Leaderboard:** public leader 0.4413 (xiaofanhu), rank 22 = 0.3183. The 0.3195
  figure is not on the page.
- **Official `run_card.json` vs. post-stop offline diagnostic:** `run_card.json` keeps
  `holdout_dti.dti = null` and `leakage_canary.auc = null` because E1 stopped
  pre-placement under the literal duplicate gate. After restoring all 13 SHA-256-pinned
  inputs (`training_features.tif` `sha256: 4371c82e3b83…`) and reproducing all 10
  `.cache/g79/*.npy` arrays, [`scripts/post_stop_diagnostic.py`](../scripts/post_stop_diagnostic.py)
  confirmed that **even if Decision D-1 resolved to Option B (`top-37,654` of E-proba,
  3-px overlap `0.0119`) or Option C (`p >= 0.5`, 3-px overlap `0.3046`), E1 (`G79-FABRIC-OFFSET`)
  still fails the preregistered holdout gate (`verdict: negative`, `DO NOT SUBMIT`)**:
  - `LEAKAGE-CANARY` (`gems57-pooled-hide-v2`): `36/36` feature-fold tests pass on `seed=20`
    (`max_symmetric_auc = 0.5872 <= 0.90`) and `36/36` pass on `seed=30` (`max_symmetric_auc = 0.6162 <= 0.90`).
  - `HOLDOUT-DTI` (post-stop diagnostic, 37,654 dots at 3 px spacing, `gems57-pooled-hide-v2`):
    - `seed=20` (`n=11,321` withheld positive pixels): candidate `0.0474 [0.0390, 0.0552]` vs
      `zero_lag_edge_control` `0.0420 [0.0327, 0.0517]` (paired $\Delta = +0.0054 [-0.0018, +0.0128]$,
      95% CI spans 0), `uniform_control` `0.0504 [0.0450, 0.0557]` (paired $\Delta = -0.0030$), and
      `h33_foldfair_control` `0.0961 [0.0827, 0.1091]` (paired $\Delta = -0.0487 [-0.0623, -0.0352]$).
    - `seed=30` (`n=11,342` withheld positive pixels): candidate `0.0466 [0.0388, 0.0543]` vs
      `zero_lag_edge_control` `0.0455 [0.0359, 0.0545]` (paired $\Delta = +0.0011 [-0.0065, +0.0083]$),
      `uniform_control` `0.0496 [0.0447, 0.0548]` (paired $\Delta = -0.0030$), and
      `h33_foldfair_control` `0.0989 [0.0835, 0.1122]` (paired $\Delta = -0.0523 [-0.0671, -0.0370]$).

### Why submission is automatically blocked

The prompt's literal novelty gate counts every finite positive registry pixel
as support. A real registry file is positive on all **5,167,373 footprint
pixels**. The shared template independently certifies **zero uncovered allowed
pixels**. Consequently **every nonempty candidate overlaps this prior by 100%**,
which exceeds the required 70% / 3 px threshold. No geological method, spacing
change, random jitter or filename change can solve that mathematical conflict.
See [certificate](../evidence/universal_overlap_certificate.json),
[pre-placement gate](../evidence/uniqueness_surface.json), and
[irregularities](../reports/irregularities.md).

The fixed E1 surface was rejected **before placement**. Scientific work stopped:
no final dots, no E2/E3, no canary clearance, no HOLDOUT-DTI or CI, no slot used.
Null scores in the run card mean **not measured**, never zero or a projection.
Only the already-computed rejected surface was serialized as negative-result
evidence. No human inspector is needed to reach the **DO NOT SUBMIT** decision.

## Latest repository review — no new scientific experiment

The follow-up review on `arena/79f9140a-gemsdoe79` independently restored **one**
frozen registry witness and re-measured it with the unchanged shared tool.
Its Git blob, SHA-256, grid and every certificate measurement match the original:
zero allowed cells escape its positive-support halo. This confirms the stop;
it does **not** create a new, protocol-unique submission or repeat the historical
992-file restoration. The existing TIFF and scientific run card remain unchanged.

- [Three-pass review and limitations (session `79f9140a`)](../reports/session_review_79f9140a.md) · [Session `9e23b44d`](../reports/session_review_9e23b44d.md) · [Session `8ed5d89a`](../reports/session_review_8ed5d89a.md) · [Session `700397d4` (canary gate hardening & concurrent-lane audit)](../reports/session_review_700397d4.md)
- [Actual witness re-measurement](../evidence/session_witness_review.json) · [Session `8ed5d89a` witness receipt](../evidence/session_witness_review_8ed5d89a.json) · [Session `700397d4` witness receipt](../evidence/session_witness_700397d4.json)
- [Independent canonical audit of archived concurrent lanes (`H79-MCT` & `H79-CSPT`)](../evidence/concurrent_lanes_audit.json)
- `scripts/submission_status.py` now emits a JSON **negative** verdict (exit 2)
  even for missing/corrupt files or malformed run cards; no stale PASS is reused,
  and `src/gems79/status.py` requires numerical `auc in [0.5, 0.90]` in addition
  to `passed == True` for `leakage_canary` (`IR-79-31`).
- For an offline witness re-check, run
  `.venv/bin/python scripts/verify_overlap_witness.py`. On a fresh checkout add
  `--restore` to fetch just the immutable rejection witness from GitHub. This
  command never performs placement, scoring, slot selection or upload.

The full original prompt remains below. Its instruction to stop on duplicates
prevents delivering its conflicting request for a promotable unique TIFF under
the current literal registry rule. No unauthorized dense-raster exemption is used.

## Concurrent upstream work integrated

The initial checkout was the 11-byte README commit. While E1 was running,
parallel PRs #1–#3 added a no-data preflight site/validator to `main`. PR #4
integrates those changes rather than overwriting their history: generic-format
API and useful tests retained, novelty delegated to the unchanged shared tool,
old HTML bookmarks redirected, current `docs/run-card.json` aliased to the
same negative card, and superseded prose archived under
[`knowledge/prior_work/`](../knowledge/prior_work/README.md). The old missing-input
blocker has been resolved for the used mirror inputs; the literal novelty stop
has not. No scientific lane switch or new experiment occurred.

A later concurrent main update (`c26efec`, PRs #5–#6) added H79-MCT and a
local dense-halo gate exemption. Its own audit records 100% literal overlap.
That approval is **not adopted**: the lane's original evidence/artifacts and
non-executable source are preserved in
[`archive/h79_mct_c26efec/`](../archive/h79_mct_c26efec/README.md), with source hashes.
The original shared module remains unmodified; old active H79-MCT download URLs
are retired, and every active status path stays negative. No H79-MCT experiment
was rerun by this session; its reported holdout numbers are not E1 measurements.

## Scientific work and audit

- Initial checkout: only an 11-byte README; no previous local pipeline or work to continue.
- [Four ranked, preregistered hypotheses](../research/hypotheses.md), each with layers,
  physical signature, catalogue-missing rationale, novelty limits, cost and mimic.
- One declared lane: **opposite-side magnetic-marker displacement across a gravity edge**.
  The request did not contain the referenced explicit method paragraph; this is
  recorded as an ambiguity, not an invented assignment.
- Reused the cached 19-band numerical feature GeoTIFF directly. Restored five
  hash-pinned mirror inputs. The historical 54-channel `.npy` cache has no
  portable bytes here; we do not pretend to have restored it or rebuild it.
- Restored **992 immutable prior raster blobs across 92 accessible sibling repositories**,
  including dense, withdrawn and large predictions. Files are Git-blob and
  SHA-256 checked. One decisive witness rejects this run; this is **not** a claim
  that all 992 rasters were compared or that inaccessible predictions are absent.
- Reused the shared `evaluate_holdout.py`, `submission_writer.py`, whole-component
  split and literal uniqueness tools **without modification**. Pins and hashes:
  [`registry/template_pin.json`](../registry/template_pin.json).
- [H33 byte-level forensic analysis](../evidence/h33_forensics.json): 37,654 dots are
  exactly the D2.8 set of 44,090 dots with 6,436 points at catalogue distance
  ≤200 m deleted. This supports an emission-efficiency explanation; it does not
  prove a causal private-score gain.
- [Official-source claim ledger](../knowledge/official_sources.json),
  [scientific explanation](../knowledge/why_h33.md), [primary-literature review](../knowledge/literature.md), [three-pass review](../reports/verification_passes.md).

### Score discipline

New measured scores must be labelled **HOLDOUT-DTI**, with shared evaluator
version, withheld positives and 95% CI. **ORGANIZER-CONFIRMED** is reserved for an
actual submission-page receipt. This project has none. The prompt's H33 score
is an unverified filename-to-score report. The official public leaderboard was
read on 2026-10-21 and shows a leader at 0.4413; that is a public observation,
**not this artifact's score or an authenticated H33 receipt**. The prompt's
0.3195 reference is stale relative to that observation. No higher score is
promised or projected.

## Reproduce and verify

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_project.py
.venv/bin/python scripts/build_site.py
```

The committed TIFF and small reference grid allow **offline** validation. Large
observations and registry files are ignored, not placed in Git. To restore them:

```bash
bash scripts/download_competition_data.sh
.venv/bin/python scripts/restore_registry.py
# Reproduce deterministic E1 transforms, never tune/restart the stopped experiment:
.venv/bin/python scripts/prepare_data.py --reproduce
# Privately reserialize the same rejected field and require identical TIFF/ZIP hashes:
.venv/bin/python scripts/reproduce_artifact.py
```

The cold cache and the TIFF/ZIP were recovered byte-for-byte on the recorded
local Python 3.11 / pinned-library environment. This is not a cross-hardware
floating-point guarantee: recovery fails closed on hash drift and never
replaces the original scientific receipts. The shared ZIP writer uses a fixed
member timestamp for reproducibility, not the actual experiment time.

`run_experiment.py` is the fixed, fail-closed orchestration, **not** permission to
restart a stopped lane. It uses whole 8-connected components, a 300 m visible
context buffer, label-blind spatial quadrants, pixel-exact visible-fault masks,
pooled shared DTI and 20 km cluster intervals if the pre-placement gate permits
it. Tests exercise these tools on software fixtures, **not scientific scores**.
`validate_submission.py` checks format only; `submission_status.py` returns exit
2 for this rejected file and never uploads anything.

## Website and current feed

The self-contained site is built in **`docs/`**, with a prominent download/status block,
executive-summary subpage, evidence links, source table and reproducibility
instructions. Optional browser QA: `npm ci --prefix tools/browser-qa --ignore-scripts`,
serve `docs/` on port 8080, then `node scripts/browser_review.cjs`. This checks all
seven pages at 1440, 390 and 320 px, clipboard/filter behavior and the actual
download SHA-256. Browser assets and large data stay ignored.

The existing Pages setting is legacy `main` / root; the root
`.nojekyll` and `index.html` redirect also support that configuration. A Pages
settings update returned HTTP 403 (integration permission); no settings change
is claimed. The workflow attempts artifact deployment using its own permitted
Pages token; deployment results are tracked in the final review report. Daily
source-health refresh records real response statuses and timestamps; it does not
invent receipt access, regenerate scientific candidates, approve a slot, or
present failed/stale fetches as fresh verified content.

## Limitations and next session

1. **Resolve the universal-overlap protocol conflict first.** An explicit,
   authorized rule/registry clarification is needed before another scientific
   run could produce a promotable file. This run introduces no exemption.
2. Obtain organizer-authenticated input checksums and the actual account
   submission receipt/remaining weekly capacity through an authorized workflow.
   No passwords, tokens, eligibility certification or login bypass is requested.
3. After a valid gate and explicit lane are available, run single-feature
   canaries and buffered, matched hide-and-recover against a reproduced incumbent.
   The current global holdout best has **not** been reproduced or beaten here.
4. Only the separate selector may allocate a real weekly slot. Official rules
   specify up to three per week; the signed-in account's remaining slots are
   unknown. This session used **zero**.
5. Fault predictions do not establish a geothermal vent, permeable reservoir,
   temperature or productive well. The GeoDAWN Area 2 400 m flight spacing also
   limits interpretation of sub-kilometre registration lags. No GPU is needed
   for this lane; learning a full spatial-context model would be a different
   authorized lane and resource decision, not a hidden extension of this run.

**Core values:** maximize the probability of a valid, reproducible result, not a
headline score; own failures end to end, fail closed, and never spend a slot on
an unvalidated idea. Generative AI assisted research, code, tests and prose;
no source measurements or organizer receipts were synthesized. See
[`knowledge/ai_disclosure.md`](../knowledge/ai_disclosure.md).

---

