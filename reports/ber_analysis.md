# G79-BER analysis — why H33 leads, what banded evidence recovery measured, and whether 0.2778 can be beaten

Session `4f80e0d0`, branch `arena/4f80e0d0-gemsdoe79`, 2026-10-22.
Lane **G79-BER**, experiment **X1 of at most 3** (1 used), preregistered in
[`registry/preregistration_ber.json`](../registry/preregistration_ber.json)
before any result. Run card: [`run_card_ber.json`](../run_card_ber.json).
Machine evidence: [`evidence/ber/`](../evidence/ber/).

**Verdict: negative. OK TO DOWNLOAD: YES (research). OK TO SUBMIT: NO.**
No submission slot was used. Every performance number below is labelled
HOLDOUT-DTI, REGISTRY-MEASUREMENT, RASTER-MEASUREMENT or
UNVERIFIED HISTORICAL REPORT. No leaderboard score is claimed or projected
for any file produced here; the only ORGANIZER-CONFIRMED scores this project
can ever cite are DrivenData submission-page receipts, of which this session
produced none.

---

## 1. Executive answer

1. **A new, unique-by-construction GeoTIFF was generated and is downloadable**
   (`archive/g79_ber_4f80e0d0/downloads/gems79-ber-banded-research-37654dots-20261022T054737Z-ad519409-DO-NOT-SUBMIT.tif`,
   SHA-256 `934b5c50…c56dbc89b`). It is format-valid (single-band float32,
   EPSG:32611, 3730 × 3292, values exactly 0/1, all finite, no nodata
   sentinel — the local conditions for the portal error
   "Predicted values must be in range [0, 1]" are absent). It is labelled
   **DO NOT SUBMIT** automatically, because it failed two preregistered
   gates. No human inspection is needed or permitted to change that.
2. **HOLDOUT-DTI**: the candidate scored 0.0788 [0.0684, 0.0889] (seed 20,
   n = 11,321 withheld positives) and 0.0882 [0.0739, 0.1011] (seed 30,
   n = 11,342) against the fold-fair H33 control's 0.0961 / 0.0989 on the
   identical instrument (`gems57-pooled-hide-v2`). It beats uniform
   placement decisively but does **not** beat the current holdout best on
   either seed. Under the protocol ("do not spend a submission slot on an
   idea that hasn't beaten the current holdout best"), that ends the lane.
3. **Uniqueness**: against every informative comparable registry raster the
   surface is the most distinct this repo has measured (worst Spearman
   ρ = 0.314, worst chance-corrected 3 px overlap = 0.654; limits 0.90 /
   0.70). It is nevertheless recorded **not unique under amendment D-2**,
   because four full-footprint diagnostic surfaces fire D-2's
   saturated-halo exact test (IR-79-128) and 6 of 992 registry rasters are
   not comparable on this grid. The gate was **not** modified after seeing
   this; §7 explains why, and what a prospective D-3 would need.
4. **Can 0.2778 be beaten?** Nothing in this session's evidence supports
   spending a slot on that claim. §8 quantifies what beating it requires in
   metric terms and ranks the remaining paths by expected value. The honest
   summary: every measured route that is *independent* of the H19-5 lineage
   scores below the H33 control on the only validated instrument available
   offline, and every route that beats the control offline has so far
   reproduced prior rasters. Breaking that trade-off needs either new
   information (GPU-scale modelling, absolute-elevation data) or an owner
   decision on the duplicate definition — not another tabular retune.

## 2. What was verified from official sources (line by line)

Fetched 2026-10-22; verify manually at the links.

- **Problem and metric** — DrivenData competition 306 overview,
  <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>:
  detect geothermal-indicative faults in the GeoDAWN region; the USGS
  catalogue is incomplete/inaccurate; the test labels are expert-identified
  faults **not** in the USGS database. Metric (verbatim structure):
  kernel `k(d) = max(1 − d/R, 0)`, R = 300 m;
  `TPw = Σ_g max_x p(x)·k(d)`, `FPw = Σ_{p>0} p(x)·[1 − max_g k(d)]`,
  `FNw = Σ_g [1 − max_x p(x)·k(d)]`;
  `DTI = TPw / (TPw + α·FPw + β·FNw)`, α = 0.2, β = 0.8. Worked example on
  the page: TPw = 3.00, FPw = 1.89, FNw = 2.00 → 0.60. Our offline
  evaluator (`vendor/gems57/evaluate_holdout.py`, `gems57-pooled-hide-v2`)
  implements the same pooled form; its frozen control values reproduced
  exactly this session (§5), which is the strongest available check that
  the wiring is unchanged.
- **Submission format** — same page: GeoTIFF, CRS UTM 11N (EPSG:32611),
  100 m pixels, same bounds as the sample, single layer float32, values
  0–1, null/NaN outside bounds in the template. This repo's writer emits
  finite 0/1 everywhere instead (zeros template lineage), which the shared
  validator checks byte-wise.
- **Prize structure** — same page: one chosen submission is scored in both
  prize rounds; the final round rescoring uses expanded expert labels.
  Consequence: there is no "probe now, fix later" — a weak file submitted
  this week can become the file that counts.
- **Official reference solution** —
  <https://github.com/drivendataorg/gems-prize-reference-solution>: a U-Net
  with Monte-Carlo cross-validation (John Lipor). That is the organizer-sanctioned
  modelling family; it is **not runnable in this sandbox** (2 CPU,
  ~3.8 GB RAM, no GPU), which is a hard scope limit recorded in
  `research/hypotheses_ber.md` (hypothesis 5).
- **Not verified**: the live leaderboard (login-walled from here). The
  brief cites both 0.4413 and 0.3195 as "highest"; treat both as
  UNVERIFIED HISTORICAL REPORT until read on the submission page. The
  family-best `h33-h33-2-b2-…-e5eb6e7e-zeros: 0.2778` is likewise a
  user-reported ledger value (`registry/score_ledger.csv`), not an
  ORGANIZER-CONFIRMED receipt in this repo.

## 3. Why H33 scored highest (PhD-level mechanism)

Evidence: `evidence/h33_forensics.json`,
`evidence/family_lineage_forensics.json`, `knowledge/why_h33.md`
(all RASTER-MEASUREMENT unless stated).

**Lineage.** Every reported family score above 0.2478 descends from one
root surface, `h19-5`. H33 is not a new model: it is the D2.8 dot field
with its 6,436 dots within 200 m of the catalogue deleted, leaving 37,654
dots. Along the lineage, the count of dots within 200 m of the catalogue
falls 6436 → 3894 → 2545 → 2353 → 0 while the reported score rises
0.2600 → 0.2632 → 0.2708 → 0.2710 → 0.2778 (UNVERIFIED HISTORICAL REPORT
for the scores; RASTER-MEASUREMENT for the dot counts).

**Why deleting near-catalogue dots helps, in metric terms.** DTI's FP term
charges each positive pixel `p(x)·(1 − max_g k(d))` against the *expert*
truth set, and the catalogue itself is masked pixel-exactly. A dot 100 m
from a catalogue trace earns credit only if an *expert* (unmapped) fault
pixel lies within 300 m; dots hugging mapped traces mostly pay FP mass
while adding little TPw, because the max-cover in TPw saturates — one dot
near a truth pixel already captures most of its credit, and β = 0.8 makes
uncovered truth (FNw) four times more expensive per unit than FPw. H33's
edit therefore does two things at once: it removes nearly pure-FP mass,
and the fixed budget is re-expressed as a dot field whose median distance
to the catalogue is 1.96 km, with 69.8 % of dots beyond 1 km
(RASTER-MEASUREMENT, `evidence/ber/distance_diagnostics.json` reproduces
this profile: median 19.6 px). In other words, H33 wins not by modelling
faults better but by *spending its fixed budget where unmapped-fault
discovery is geometrically possible* and refusing to spend it re-tracing
the catalogue.

**Why the H19-5 root is hard to beat.** The genuinely independent family
lanes (GEMSDOE70 at a reported 0.2478, forward 3 px overlap vs H33 only
0.548; GEMSDOE49 at 0.2376, overlap 0.434 — overlaps RASTER-MEASUREMENT,
scores UNVERIFIED) prove expert truth has large mass off the H19-5 lines.
Yet on the offline hide-and-recover instrument, H19-5-lineage dots recover
withheld catalogue components better than any single-sensor evidence
ranking tried in this repo (H33 fold-fair control 0.0961 / 0.0989
HOLDOUT-DTI, reproduced exactly in three independent lanes). The likely
reason is corroboration: H19-5 was built from multiple independent
lineament extractions, so its lines encode cross-sensor agreement that a
per-pixel tabular model over the same rasters does not reconstruct —
agreement is precisely what separates fault scarps from the named mimics
(paleo-shorelines, canyon margins, lithologic contacts). G79-BER's
stratified results (§5) are direct evidence: within 1 km of the catalogue
our per-band models match the control, but beyond 2 km — where single-
sensor evidence thins and corroboration matters most — they lose in every
band on both seeds.

**The trap this sets.** The pooled holdout rewards catalogue proximity
(withheld *catalogue* components sit near mapped systems; 98 % of withheld
truth pixels this session lie within 5 km, 83 % within 2 km). H79-NHR
exploited that with distance/density geometry, beat the control
(0.1431 / 0.1522 HOLDOUT-DTI), and duplicated 26 registry fields whose
reported public scores are 0.016–0.143 — i.e. the offline instrument's
optimum is a known poor leaderboard region. Any lane that simply
maximises pooled HOLDOUT-DTI will re-enter that trap. G79-BER was designed
against it explicitly; that it still lost to the control is the scientific
content of this session.

## 4. What G79-BER tested (design, frozen before results)

Full specification: `registry/preregistration_ber.json`; ranked hypotheses
with viability checks: `research/hypotheses_ber.md`.

- **Bands.** Five distance-to-visible-catalogue bands — (200, 500],
  (500, 1000], (1000, 2000], (2000, 5000], > 5000 m. Cells ≤ 200 m from
  the catalogue and catalogue cells are never eligible (mirroring the
  measured H33 rule). Full-footprint allowed cells per band:
  409,430 / 595,180 / 1,009,170 / 1,782,574 / 1,066,471; the 37,654-dot
  budget is allocated ∝ allowed area by largest remainder:
  **3170 / 4609 / 7814 / 13803 / 8258** (RASTER-MEASUREMENT).
- **Models.** One histogram gradient-boosting regressor per band (NHR
  hyperparameters verbatim: 250 iterations, lr 0.08, 63 leaves, min-leaf
  200, L2 1.0), target = 300 m triangular-kernel credit to nested-withheld
  whole fault components (3 replicates, hide fraction 0.20, 3 px buffer,
  200k uniform negatives per replicate). No band needed the preregistered
  < 3000-positive merge fallback (final positive rows per band:
  42,161 / 67,834 / 60,040 / 38,518 / 3,810).
- **Features (85).** The cached 52-feature NHR static stack (SHA-pinned
  inputs, `evidence/ber/feature_receipt.json`) + 30 new transforms + 3
  geometry features. New: FFT upward-continuation worms (horizontal
  gradient magnitude and tilt of RTP magnetics, band 2, and isostatic
  gravity, band 13, at 0/200/500/1000/2000 m continuation plus a rank-
  persistence summary) targeting **buried intrabasinal faults** whose only
  expression is a basement offset; step dipoles / σ3 gradients of
  log depth-to-basement (band 15) and surface conductance (band 17); six
  lidar antislope/dipole rank interactions targeting uphill-facing scarps.
  Geometry restricted to `log_dist_visible_tip`, `lidar_strike_alignment`,
  `strike_field_coherence`; raw distance-to-catalogue and density — the
  features that collapsed NHR onto prior fields — are excluded from
  ranking and used only to define bands.
- **Named non-fault mimics.** Lake Lahontan shoreline/terrace risers
  (contour-parallel steps with identical lidar and worm signatures) and
  buried lithologic basement contacts / onlap edges (identical worm
  signature, no fault). Absolute-elevation shoreline suppression was
  assessed and rejected as not viable here: it needs an absolute DEM
  (USGS 3DEP is the named free official source), but this sandbox's egress
  is limited to GitHub/PyPI (hypotheses doc, hypothesis 3).
- **Holdout.** Shared `buffered_component_draw`, seeds 20/30, leave-one-
  quadrant-out; arms: candidate, `h33_foldfair_control`,
  `uniform_control`, `banded_uniform_control` (diagnostic isolating the
  allocation), plus a distance-stratified kernel-credit diagnostic.
- **Promotion gate (preregistered).** Canaries ≤ 0.90 both seeds;
  candidate > H33 fold-fair control point estimate both seeds; paired 95 %
  CI vs uniform excludes 0 both seeds; amendment-D-2 uniqueness before
  placement and on final dots; shared writer/validator pass with exactly
  37,654 dots. "Promote" would have meant promote-to-selector only.

The worm implementation was verified independently: spectral HGM at 0 m
continuation correlates 0.90 (RTP) / 0.77 (gravity) with the repo's
existing spatial-Gaussian gradient magnitudes on a 200k-cell sample, all
features are finite where the source rasters are, and no new feature
approaches the leakage canary (worm AUCs 0.52–0.58). The negative below is
therefore a measurement, not an implementation artefact.

## 5. Results (all HOLDOUT-DTI, evaluator `gems57-pooled-hide-v2`)

| Arm | Seed 20 (n = 11,321) | Seed 30 (n = 11,342) |
|---|---|---|
| **candidate (G79-BER)** | **0.0788** [0.0684, 0.0889] | **0.0882** [0.0739, 0.1011] |
| h33_foldfair_control (bar) | 0.0961 [0.0837, 0.1086] | 0.0989 [0.0842, 0.112] |
| uniform_control | 0.0500 [0.0448, 0.0552] | 0.0498 [0.0449, 0.0541] |
| banded_uniform_control | 0.0502 [0.0450, 0.0553] | 0.0490 [0.0442, 0.0532] |
| paired Δ candidate − H33 | −0.0173 [−0.0287, −0.0055] | −0.0106 [−0.0245, +0.0044] |
| paired Δ candidate − uniform | +0.0288 [0.0185, 0.0386] | +0.0385 [0.0248, 0.0508] |

Control values reproduce the frozen H79-NHR X1 numbers exactly (0.096086…,
0.098898…), confirming identical folds, evaluator and wiring. The banded-
uniform arm shows the area-proportional allocation itself is neutral for
random dots; all candidate lift over uniform comes from within-band
ranking, and it is not enough.

**Leakage canary: PASS.** 680 single-feature AUC tests (85 features × 4
folds × 2 seeds); maximum 0.8589 (`geom_log_dist_visible_tip`, the same
known geometry feature as in NHR), threshold 0.90.

**Distance-stratified kernel credit per withheld truth pixel**
(diagnostic, HOLDOUT-DTI machinery; bands by truth distance to visible
catalogue):

| Band | Truth px (s20/s30) | BER s20 | H33 s20 | BER s30 | H33 s30 |
|---|---|---|---|---|---|
| (200, 500] m | 2509 / 2377 | 0.110 | 0.120 | 0.123 | 0.123 |
| (500, 1000] m | 3662 / 3838 | 0.126 | 0.144 | 0.137 | 0.131 |
| (1000, 2000] m | 3306 / 3089 | 0.102 | 0.151 | 0.143 | 0.168 |
| (2000, 5000] m | 1659 / 1939 | 0.118 | 0.140 | 0.094 | 0.156 |
| > 5000 m | 185 / 99 | 0.077 | 0.163 | 0.003 | 0.216 |

Two mechanisms, both unfavourable: (i) **allocation** — 58 % of dots are
sent beyond 2 km, where only ~16 % of holdout truth lives; (ii) **within-
band ranking** — even per truth pixel, the far-band models recover less
than H19-5-lineage dots, and beyond 5 km they recover almost nothing on
seed 30. Mechanism (ii) is the deeper result: at fixed budget share, our
worm/scarp evidence ranks far-field withheld faults worse than the
corroborated multiline field. Caveat, stated before the run and still
true: the holdout withholds *catalogue* components, so it cannot directly
reward discovery of the *expert* faults that determine the leaderboard,
and its far-band truth counts (185 / 99 pixels) are small. That caveat
cuts both ways — it is not evidence BER would score well publicly; it is
a statement that this instrument cannot settle the far-field question,
which is exactly why the preregistered bar was the pooled control
comparison rather than the stratified diagnostic.

**Distance/road profile of the final dots** (RASTER-MEASUREMENT,
`evidence/ber/distance_diagnostics.json`): median distance to catalogue
20.9 px (2.09 km) vs H33's 19.6 px; 79.3 % of dots beyond 1 km (H33:
69.8 %); 8.4 % within 500 m (H33: 15.0 %). Median distance to a TIGER road
781 m vs 640 m footprint-wide; 12.9 % of dots within 100 m of a road vs
16.2 % footprint-wide — the dot field is not a road-following artefact.
The design achieved its intended H33-like far profile; profile alone does
not produce H33-like recovery.

## 6. Uniqueness and amendment D-2 (REGISTRY-MEASUREMENT)

The literal duplicate rule (" > 70 % of dots within 3 px of *any* registry
raster's positive support") is unsatisfiable in this registry (IR-79-53:
space-filling priors flag even uniform-random dots). With the user's
standing instruction that uniqueness must be decidable, this session
adopted **amendment D-2** prospectively, before any BER result
(`reports/protocol_amendment_D2_20261022.md`), implemented once in the
shared tool (`vendor/gems57/uniqueness.py`,
`compare_array_to_registry_d2`, pin updated in
`registry/template_pin.json`, 7 unit tests): a candidate is a duplicate
iff it is byte/decoded-identical, or Spearman ρ > 0.90, or its 3 px
forward overlap against a prior's dot-equivalent set exceeds 0.70 **and**
the chance-corrected overlap `(ov − h)/(1 − h)` (h = the prior halo's
share of allowed cells) also exceeds 0.70; if the halo saturates
(h ≥ 0.999999) exact-cell overlap > 0.70 decides instead. D-2 does not
resurrect stopped lanes (NHR's worst corrected overlap is 0.777 — still a
duplicate). Wording is always "unique under D-2", never literal-rule
unique; literal overlaps are reported alongside (78 literal firings for
BER, as for any map in this registry).

Surface scan (pre-placement, as protocol requires): 986 of 992 registry
rasters comparable. The 6 exceptions are named in the evidence: four
CRS/transform mismatches (including two `SCHEMA-DEMO` files), one corrupt
TIFF (`smoke.tif`, missing `StripOffsets`), one grid/band mismatch
(`GEMS36_FORMAT_TEST_NOT_SUBMISSION`). Results:

- worst Spearman ρ **0.314** (GEMSDOE48 H56b plausibility) — limit 0.90;
- worst chance-corrected overlap **0.654** (coverage-v3-wide, raw overlap
  0.859 at halo 0.593) — limit 0.70;
- **4 D-2 firings**, all full-footprint diagnostic surfaces whose tie-
  inclusive dot-equivalent set is the entire footprint (5,167,373 cells),
  forcing exact overlap 1.0 for *any* candidate: three GEMSDOE48
  "unassigned-mass" diagnostics (ρ = 0.0013) and the 5GEMSDOE density
  probe (ρ = 0.178). Recorded as **IR-79-128**.

**Decision:** the lane is recorded *not unique under D-2*, placement was
never run, and the archived TIFF serialises the audited provisional
top-quota dots once as negative evidence. The saturated branch was
designed for genuine dot lattices (|S| = 37,654); for tie-degenerate
plateau surfaces a chance-corrected exact test (or declaring
|S| ≥ 99 % of allowed non-informative) would be the principled fix — but
adopting it after seeing it fire on our own experiment would be moving
the goalposts, and the verdict is negative on holdout regardless. A D-3
amendment is a prospective owner decision for a future lane; the exact
formula recommended is recorded in IR-79-128. What can be stated as
measurement: against all 982 informative comparable rasters, BER passes
both D-2 numeric criteria with margin — intrinsic uniqueness-by-design
(banded allocation + per-band rank normalisation) worked where
uniqueness-by-capping (G79B-SDPT) and pooled ranking (H79-NHR) did not.

## 7. Irregularities found this session

- **IR-79-127** — `data/restore_receipt.json` pins `ext_geodawn_rad_u8` to
  SHA `e8086c…`, conflicting with the manifest's `c22420…`; the on-disk
  file matches the manifest. Left untouched (frozen evidence); restores
  must not use `--preserve-receipt`.
- **IR-79-128** — D-2 saturated-halo degeneracy on plateau diagnostics
  (above). Gate left exactly as preregistered; D-3 recommendation
  recorded.
- **IR-79-129** — a parallel-edit race truncated the first finalize note
  mid-token; one documented repackage with identical dots, gates and
  verdict produced byte-identical raster bytes (SHA-256 `934b5c50…`
  before and after).

## 8. Can the family best (reported 0.2778) be beaten?

**What the metric requires.** At H33-like FP mass, reaching a reported
0.3195 needs ≈ 1.2× H33's expert-truth kernel credit and 0.4413 needs
≈ 1.6–1.7× (arithmetic on the verified DTI formula; the leaderboard
values themselves are UNVERIFIED per §2). No formatting trick buys this:
values must stay in [0, 1], the budget of useful dots is fixed by FP
economics, and max-cover means credit only grows by putting dots within
300 m of *expert* faults that H33 misses, without spending the dots that
earn H33's existing credit.

**What the accumulated evidence says.**

- Independent tabular evidence ranking over the supplied 19 bands +
  lidar/radiometric mirrors has now been measured four ways in this repo
  (NHR pooled, STEPCO, G79B, BER banded). Offline, only the
  catalogue-proximity variant beats the H33 control, and it duplicates
  known low-scoring fields. The far-field, where new credit must come
  from, is exactly where per-pixel evidence is weakest (§5).
- The two independent reported scores near the top (GEMSDOE70 0.2478,
  GEMSDOE49 0.2376; UNVERIFIED) show off-lineage truth exists but was
  captured at lower efficiency than H33 captures on-lineage truth.
- Therefore a > 0.2778 file most plausibly requires **new information or
  corroboration structure**, not a new weighting of the same rasters:
  (a) the organizer's U-Net family (spatial context learns scarp-vs-
  shoreline morphology per-pixel features cannot) — needs GPU
  infrastructure this sandbox lacks; (b) absolute-elevation data (USGS
  3DEP, free/public-domain) enabling Lahontan shoreline suppression, the
  single largest named mimic — needs a data path into the sandbox
  (egress is GitHub/PyPI only; a GitHub-mirrored, SHA-pinned derivative,
  as was done for the lidar stack, is the established pattern);
  (c) an *independent* multiline corroboration build in the H19-5 spirit
  but from disjoint extractors, preregistered against the D-2/D-3 gate so
  its uniqueness is intrinsic. Each is a future preregistered lane, and
  none may spend a weekly slot before beating the H33 fold-fair control
  on both seeds of the shared instrument — the rule that stopped this
  lane.
- The duplicate-gate blocker also needs the owner's prospective decision
  (D-3, IR-79-128): under any reading in force today, even a future
  holdout-winning surface would need its uniqueness established against
  plateau diagnostics in a way the current tool cannot express.

**Bottom line for this week:** there is no file in this repository —
including the one generated this session — that the automatic gates can
honestly mark OK TO SUBMIT. The canonical site artifact (H79-NHR on this
session's base; G79-THVC on `main` at merge time) remains DO NOT SUBMIT.
Spending a slot on the BER file would mean choosing a holdout-loser over
the protocol's bar; the protocol exists precisely to refuse that choice.

*Merge note (2026-10-22): this report was written on base `9640ed3`, whose
canonical lane was H79-NHR. By merge time, `main`'s canonical card is
G79-THVC, reporting HOLDOUT-DTI 0.1905 / 0.1944 on the same evaluator (its
own evidence in `run_card.json`, not re-measured here; also negative /
DO NOT SUBMIT). BER is below that as well. Nothing in §§3–5 changes: BER's
preregistered bar was the H33 fold-fair control, and THVC's existence
strengthens §8's conclusion that corroborated multi-sensor structure —
not per-pixel tabular ranking — is where offline gains have come from.
IR numbers in this report were renumbered 67–69 → 127–129 at merge.*

## 9. Limitations

- Holdout truth is withheld *catalogue* components; leaderboard truth is
  expert-only faults. HOLDOUT-DTI is a gate, not a score estimate, in
  either direction.
- Far-band stratified counts are small (185 / 99 truth pixels beyond
  5 km); the seed-30 value 0.003 should be read as "essentially no
  recovery measured", with wide uncertainty.
- Inputs are owner GitHub mirrors verified against
  `registry/data_manifest.json` SHA-256 pins; organizer-origin
  authentication is impossible without a DrivenData login. 6 of 992
  registry rasters are not grid-comparable (§6).
- Compute ceiling (2 CPU / 3.8 GB) excluded the reference U-Net family;
  tabular HGB is what was measurable here.
- Experiment budget: 1 of 3 experiments used; feature build + two
  holdout seeds + final fit + registry scan ≈ 62 min inside the 2 h
  window from preregistration (04:45 → 05:47 UTC). X2/X3 were reserved
  for defect fixes; line-by-line review found no implementation defect
  (controls reproduced exactly, quotas exact in every fold, worms
  verified against independent gradients), so they were not spent.

## 10. Reproduction (read-only checks; the lane is terminal)

```bash
.venv/bin/python -m pytest tests/test_ber.py tests/test_uniqueness_d2.py -q
.venv/bin/python scripts/validate_submission.py \
  archive/g79_ber_4f80e0d0/downloads/gems79-ber-banded-research-37654dots-20261022T054737Z-ad519409-DO-NOT-SUBMIT.tif
.venv/bin/python scripts/verify_project.py
```

`scripts/run_ber.py` and `scripts/finalize_ber.py` refuse to run now that
`run_card_ber.json` exists; that refusal is the terminal-lane guard, not
an error.
