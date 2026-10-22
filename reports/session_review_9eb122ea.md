# Three-pass repository review — session 9eb122ea

**Review date:** 2026-10-22 (UTC)

**Branch:** `arena/9eb122ea-gemsdoe79`

**Outcome:** negative feasibility result, a new read-only runtime-data availability check, four ranked untried hypotheses, and no candidate TIFF. This is not a new scientific experiment or a submission decision.

## Executive decision

The literal pre-placement novelty gate is mathematically unsatisfiable for any nonempty candidate in this checkout: the independently SHA-verified registry witness covers the entire allowed domain. The measured preflight returns `impossible_under_literal_gate`, exit code `2`; witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`; allowed-cell coverage `1.0`; permitted forward overlap `0.70`. The source evidence is [`evidence/preflight_9eb122ea.json`](../evidence/preflight_9eb122ea.json).

I did **not** reinterpret “dots” as top-k surface cells, exempt dense priors, cap overlap, generate an empty/misleading raster, run a holdout, or create a purportedly unique TIFF. Those actions would silently change or evade the stated gate. A prospective clarification by the protocol owner is required before any candidate can be tested. The preserved project artifact remains an inherited research file, `OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`

A separate data-readiness audit found **0 of 13** pinned manifest files present under `data/raw`. The historical `data/restore_receipt.json` still matches the manifest's metadata, but is not proof of current file availability. I added `scripts/data_status.py` plus tests and a build-time GitHub Pages status panel so that a stale restore receipt can no longer be mistaken for live inputs. The report is [`evidence/runtime_data_status_9eb122ea.json`](../evidence/runtime_data_status_9eb122ea.json).

## Pass 1 — prompt, source classes, and scientific evidence

### Project and protocol review

Read the complete README, including its preserved original prompt; the active-agent contract; canonical `run_card.json`; the relevant preregistrations; the irregularity history; the shared DTI implementation; H33 forensics; the candidate backlog; the source ledger; and the existing site/evaluator/selector paths. No single delimited assigned-method paragraph was present, so no lane was assigned. The repository's existing rule prohibits a new lane after the literal preflight stop.

The metric code in [`vendor/gems57/metric.py`](../vendor/gems57/metric.py) implements a 300 m triangular distance kernel, pooled weighted components, alpha `0.2` and beta `0.8`:

```text
DTI = TP_w / (TP_w + 0.2 × FP_w + 0.8 × FN_w)
```

Each truth pixel receives its maximum nearby prediction credit, while prediction-side false-positive costs are summed. At the component level, an FN carries four times the weight of an FP, but repeated predictions can still add FP cost without adding max-cover credit. Removing a useful prediction can also reduce TP and hurt. This gives a *conditional* reason why a sparser H33-like map might do well, not a causal explanation of an organizer score.

### What H33 does and does not establish

The pinned H33/D2.8 pixel remeasurement records 44,090 D2.8 positives, 37,654 H33 positives, and 6,436 deleted pixels ([remeasurement receipt](../evidence/review_e4a4422d/h33_remeasurement.json)). H33 is an exact subset consistent with removing predictions within two pixels of the public catalogue; none of the deleted pixels was exactly on a catalogue pixel. This is byte geometry, **not** a score or evidence that a two-pixel exclusion improves hidden-test performance.

- **H33 `0.2778` — USER-REPORTED / UNVERIFIED HISTORICAL SCORE.** The repository's prior source ledger records the sibling project site labeling its H33 file UNSCORED; there is no submission-page receipt binding the value to the exact TIFF bytes. A numerically matching public-board row is not proof of artifact identity.
- **`0.3195` — USER-PROVIDED COMPARATOR, NOT VERIFIED AS THE PUBLIC-BOARD LEADER.** The repository's four-page public-board audit dated 2026-10-22 did not find that value in its 200-row snapshot ([IR-79-123](irregularities.md); [dated source ledger](../knowledge/official_sources.json)). This session did not refresh the board.
- **`0.4413` — PUBLIC-OBSERVATION.** The repository records it as the first-place public-board observation on 2026-10-22 ([dated source ledger](../knowledge/review_e4a4422d_sources.json)). It is neither this project's score nor an artifact-linked organizer receipt, and it is not a forecast or guaranteed ceiling.

Numerically, the reported H33 `0.2778` is below the user-provided `0.3195` comparator and the repository-recorded `0.4413` public observation. Evidentially, that ordering does not establish a verified performance gap or a reachable target: none is an artifact-linked organizer receipt, and the repository's dated 200-row board audit did not contain `0.3195`.

The latest source-health record is dated 2026-10-22, but no external site was fetched during this session: the sandbox's outbound policy does not allow the DrivenData or ScienceBase hosts. Therefore the historical board observation is not asserted as freshly current. The three evidence classes above are deliberately not interchanged.

### Existing holdout reference (not new results)

Every value below is an inherited **HOLDOUT-DTI** measurement from the shared evaluator, not an organizer leaderboard score and not a result produced in this session.

| Lane / seed | HOLDOUT-DTI | Evaluator | Withheld positives | 95% CI |
|---|---:|---|---:|---|
| G79-THVC / 20 | 0.190500 | `gems57-pooled-hide-v2` | 11,321 | [0.1741, 0.2069] |
| G79-THVC / 30 | 0.194393 | `gems57-pooled-hide-v2` | 11,342 | [0.177372, 0.212552] |
| G79-CSKD / 20 | 0.178129 | `gems57-pooled-hide-v2` | 11,321 | [0.161835, 0.194433] |
| G79-CSKD / 30 | 0.214488 | `gems57-pooled-hide-v2` | 11,342 | [0.196592, 0.232188] |

CSKD exceeded the canonical THVC reference on its second seed but trailed it on its first; it did not satisfy its registered both-seed replacement rule and remains archived negative. For a future experiment, the meaningful project frontier is at least the best existing result on **each** seed—not H33 alone. Full receipts: [`evidence/g79_thvc_results.json`](../evidence/g79_thvc_results.json) and [`evidence/g79_cskd_results.json`](../evidence/g79_cskd_results.json).

## Pass 2 — candidate slate, input availability, and source limits

The four hypotheses in [`research/hypotheses_9eb122ea.md`](../research/hypotheses_9eb122ea.md) are untried as the specific methods described, though they were already recorded in the broader repository backlog. The already-tested cross-scale contact-junction lane is not proposed again. The slate states inputs, physical signature, why omitted faults might exhibit it, repository distinction, named non-fault mimics, qualitative expected incremental HOLDOUT-DTI value, implementation cost, and data readiness. It contains no numeric score projection.

**Rank 1 is G79-RSS**, a relief-screened saddle crossed by independent gravity contrast. It has no additional external data requirement, but cannot run because (a) the universal literal novelty witness blocks every nonempty candidate and (b) the pinned feature stack is not present locally. G79-HFR is deliberately last despite scientific interest: the official USGS heat-flow release's metadata and ZIP listing were recorded in an earlier repository review, but the file, schema, quality fields, spatial coverage, and license suitability have not been checked here. Metadata visibility is not data acquisition.

The new checker `python scripts/data_status.py` inspects the exact `registry/data_manifest.json` destinations beneath `data/raw`, streams SHA-256 checks for files that exist, and reports missing/mismatched files separately from the historical receipt. It performs no network access, restoration, copying, or scientific validation. Current output: `0/13` verified, `13/13` missing. The repository already contains reference rasters, but these are not silently substituted for the manifest's raw destinations. The checker exits `2` while the full pinned input set is not verified.

Official source pointers are retained in the source ledger and hypothesis document. The competition metric/rules, USGS GeoDAWN release, USGS QFaults database, USGS heat-flow release, and DOE INGENIOUS repository are cited there. No new external data were acquired or verified in this session.

## Pass 3 — implementation, gates, tests, and site

### Scientific stop

Ran `.venv/bin/python scripts/preflight_new_lane.py --restore --report evidence/preflight_9eb122ea.json`. It restored/rechecked only the single hash-pinned registry witness, measured full allowed-domain coverage, and stopped before a candidate surface, feature canary, holdout, or placement. This is a rejection-only preflight, not a full registry rescan or a protocol amendment.

Accordingly, this session has:

- `0` experiments and `0` holdout evaluations;
- `0` final-dot placements and `0` new candidate TIFFs;
- `0` selector approvals, uploads, or submission slots used.

No new score exists. No value is imputed for a missing holdout.

### Software and site changes

Added `src/gems79/data_status.py`, a read-only check of current runtime input presence, optional byte-size pins, and SHA-256 pins; added `scripts/data_status.py` for machine-readable CLI output; added unit tests for verified inputs, missing inputs despite a matching historical receipt, byte/hash mismatches, and path traversal. Updated the site generator so its Sources page reports the data state at publication build time and distinguishes it from the historical restore receipt. The latest review and hypothesis slate are now linked from the decision/research pages. The README's original prompt remains preserved.

Local checks completed after the changes:

- `scripts/verify_project.py`: passed; the canonical TIFF and historic scientific records remain unchanged.
- `pytest`: **571 passed** in 80.48 seconds.
- `scripts/check_site.py`: passed; 11 pages, 267 local links, all reachable from home, 2 compatibility redirects, no external assets, scientific tables and gates match receipts, and `submit: false`.
- Public Pages verification: not performed, because the public site host is outside this sandbox's allowed outbound hosts. This is not a claim of deployment or remote reachability.

### Limitations and next actions

1. The literal novelty definition is the blocking protocol issue. The owner must prospectively clarify what “candidate dots on a continuous surface” means, or otherwise amend the shared gate; do not resolve it locally or after a candidate fails.
2. After that clarification, verify/retrieve the pinned inputs, confirm `python scripts/data_status.py` reports the required files as SHA-256 verified, then preregister exactly one of the untried methods before any holdout score.
3. Use only the shared buffered whole-segment split, evaluator, writer, visible-only catalogue features, pixel-exact visible-fault mask, and per-feature leakage canaries. An AUC above 0.90 is a stop pending explanation. Respect the three-experiment/two-hour cap.
4. Keep holdout results labeled `HOLDOUT-DTI` with evaluator, seed, withheld-positive count, and 95% CI. Use `ORGANIZER-CONFIRMED` only for a submission-page receipt bound to the exact file. Keep public-board observations and user reports in their own classes. Promotion remains a separate selector decision.
5. Do not treat local format validity or a repository mirror hash as organizer acceptance, official provenance, license verification, or geothermal resource certification.

## Review sign-off

Three passes were completed: scientific/source review; hypothesis/data-readiness review; and implementation/gate/reproducibility review. The main deliverable is the negative feasibility finding plus a corrected live input-availability check—not a submission raster. The session run card is [`evidence/session_9eb122ea_run_card.json`](../evidence/session_9eb122ea_run_card.json).
