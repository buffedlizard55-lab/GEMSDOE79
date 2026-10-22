# G79B hypothesis register — written BEFORE any G79B experiment (2026-10-22)

Session lane (declared by this session; the prompt again contains no explicit
single method paragraph — same absence recorded as IR-79-02 in the prior run):

**G79B-SDPT — Scarp Dipole-Persistence + Trace-object reranking.**
Terrain-only fault-scarp detection. No geophysics channel, no catalogue-derived
feature, no prior-submission raster as a feature. Prior lanes in this repo:
`G79-FABRIC-OFFSET` (geophysics marker-offset; post-stop diagnostic HOLDOUT-DTI
0.0474/0.0466 — *below* its own uniform control, verdict negative) and the
archived `H79-MCT` (30-channel terrain HGB × Sato(pixel likelihood); HOLDOUT-DTI
unconstrained 0.1152 seed 30 / 0.1095 seed 20, archived because its authors
applied an unauthorised dense-prior exemption and a post-hoc amendment).
G79B reuses the H79-MCT 30-channel stack and training recipe **as the control
arm** and tests whether explicit scarp-physics interaction channels and
object-level trace scoring beat it on the identical holdout. Reusing a control
is "learning from a previous submission", which the brief permits; copying its
dots would not be, and is gated against (see uniqueness gate).

## Why this direction at all (evidence, not preference)

* Organizer (problem page, read 2026-10-22): hidden labels are faults
  *manually identified by fault experts*, not in USGS/INGENIOUS; metric is
  distance-weighted Tversky, α=0.2, β=0.8, 300 m triangular kernel.
* Byte-level forensics already in this repo (`knowledge/why_h33.md`,
  `evidence/h33_forensics.json`): the family's best reported file
  (`h33-…-zeros`, 0.2778 *unverified historical report — the GEMSDOE32 site
  itself states no organizer score exists for its artifacts*) is exactly
  37,654 binary dots = the D2.8 dotted H19-5 lidar-scarp line set minus every
  dot ≤2 px from the catalogue. Its score comes from (a) the H19-5 scarp
  detector's support and (b) metric-optimal sparse emission, not from a
  geophysics model.
* Every geophysics-only family lane scored ≤ ~0.10 live (family ledger in the
  prompt), and this repo's own geophysics lane failed its holdout against a
  uniform control. Geophysics is therefore *excluded* from G79B.
* Public leaderboard read 2026-10-22: #1 = 0.4413, then 0.3904 / 0.3894 /
  0.3713 / 0.3539 and a dense 0.326–0.342 cluster. Beating 0.2778 requires a
  *better scarp detector* (more true scarps ranked top, fewer mimics), because
  the emitter (37,654 dots, ~2.8 px spacing, >2 px off catalogue) is already
  at the family's measured live optimum and is kept fixed here.

## Ranked candidate hypotheses

Ranking criterion: expected live-DTI gain × P(mechanism real) ÷ cost.
"Expected gain" is qualitative; no leaderboard number is predicted anywhere.

| # | Hypothesis | Layers / exact transform | Physical signature | Why it catches *uncatalogued* faults | Difference from everything in this repo / family lanes inspected | Cost |
|---|---|---|---|---|---|---|
| 1 | **SDPT-A Crest–base curvature dipole with consistent facing** | 1 m lidar cache bands `lapneg_max`, `lappos_max`, `downface_max`, `upface_max`, `cross_max`, `step_max`, `coh100`. New channels: `dip_min=min(rank lapneg, rank lappos)`, `dip_geo=√(rank·rank)`, `dip_balance=1−|Δrank|`, `face_polarity=(up−down)/(up+down)`, `step_vs_cross=rank(step)−rank(cross)`, `coh_step=rank(step)·coh100` | A degraded fault scarp is a one-sided step: convex crest + concave base (curvature *dipole*) with one facing direction. Channel banks are two-sided (`cross` dominant, both facings); hilltops are monopoles. Amplitude rankers cannot express "both curvatures present, balanced, one facing" | Subtle piedmont scarps have low amplitude but keep the dipole/polarity structure; they are buried by high-relief non-fault steps in any amplitude ranking, which is exactly why they were never mapped | H79-MCT/H19-5 use the raw bands as independent amplitudes (HGB splits or fixed weights). No inspected lane constructs the *paired-curvature / polarity* interaction. Antislope (uphill-facing) scarps — near-diagnostic of faulting in piedmonts — become directly visible via `face_polarity` | Low: all bands cached & hash-pinned |
| 2 | **SDPT-B Cross-scale & cross-sensor step persistence** | `ex_max` (2 m vs 30 m), `step_max` (10–50 m), DEM10 `hgm20/hgm50`, `det_elev_slope` (100 m). New: `persist_min`, `persist_geo` over the four scale ranks; `xsensor_min=min(rank lidar step, rank DEM10 hgm20)` | A tectonic step has power at every scale from 2 m to 100 m and appears in *both* independent DEMs (1 m lidar tiles vs 10 m 3DEP seamless). Road cuts/mine benches are fine-scale only; range fronts coarse only; processing seams exist in one product only | Unmapped scarps in the 24.7 % lidar gap and subdued scarps elsewhere survive as weak-but-persistent signals; single-scale detectors rank them below strong narrow mimics | Prior lanes used per-scale amplitudes or a Sato filter at 1–2 px on one surface. None computed min/geometric-mean rank persistence across 2 m→100 m, and none required cross-DEM agreement | Low |
| 3 | **SDPT-C Trace-object (segment) acceptance** | Stage-2 reranking of the pixel likelihood: 8-connected components of the top-2 % likelihood ∩ step support; per-component PCA elongation `1−λ₂/λ₁`, size factor, mean likelihood; pixel score `√(rank(p)·segment_score)` | Experts accept/reject *traces*, not pixels. A real trace is a long, straight, continuous object; the dominant mimics (terrace corners, benches, road segments) are short or blobby at the 0.5–5 km object scale | The hidden labels were drawn as traces by experts; object geometry is the closest available proxy for "would an expert draw this line?", and it is scale-free enough to promote long faint traces over short loud ones | H79-MCT applied a *local* (σ=1–2 px) Sato tubularity to pixels; measured effect ≈ 0 (Δ −0.0009). SDPT-C is object-scale (5–50 px components) — a different operator, listed as untried future work in the archived H79 analysis itself | Low–medium |
| 4 | **SDPT-E Road-cut suppression** | `external/tiger_road_distance_m.tif` (hash-pinned in `registry/data_manifest.json`), channel `road_logdist=log1p(d)` | Roads/canals/rail grades are the most fault-like artificial steps in lidar; distance-to-road lets the model discount steps that hug infrastructure | Experts tracing new faults already discount road cuts, so the hidden set is depleted near roads relative to raw scarp density | The road-distance raster exists in the family as an *audit* source; it is not among H79-MCT's 30 training channels. Risk: catalogue mapping itself is road-access-biased, so the holdout may understate or reverse the live benefit — flagged, not hidden | Low |
| 5 | **SDPT-D Lidar-gap completion with the full DEM10 set** | DEM10 channels H79-MCT dropped: `slope_mean`, `hgm200_mean`, `resid_range`, `onesided`, `valid_frac` (+ `lid_valid` already present) | In the lidar gap only 10 m evidence exists; the dropped channels carry the gap's step/residual structure | Gap faults are the cheapest recall: every prior raster is weakest exactly there | H79-MCT used 8 of 13 DEM10 channels; H19-5 quantile-matched a lidar model into the gap instead of learning gap-native behaviour | Low (all 13 restored & sha256-verified this session) |

**Named non-fault mimics the lane must be judged against:** pluvial Lake
Lahontan shorelines, fluvial terrace risers, road/canal/railway grades,
lithologic benches, mine benches, landslide head-scarps, DEM tile seams.

**Not viable without new external data (recorded, not proposed):** absolute-
elevation shoreline de-confounding needs the raw USGS 3DEP 1/3″ DEM heights
(free/official: ScienceBase 4f70aa9fe4b058caae3f8de5; only derived slope/
gradient vectors are mirrored on GitHub, and sciencebase.gov is outside this
sandbox's egress allowlist). Drainage-deflection analysis needs a raw DEM for
flow routing for the same reason.

## Decision

Test SDPT-A+B+D+E as added channels (arm A2) against the exact H79-MCT pixel
recipe (arm A1) on the shared hide-and-recover holdout, then SDPT-C trace
reranking of A2 (arm A3). Promotion gates, budgets and the uniqueness rule are
fixed in `registry/preregistration_g79b.json` before any score is read.

---

## Results addendum (2026-10-22, after E1+E2; original text above untouched)

All numbers HOLDOUT-DTI (`gems57-pooled-hide-v2`, whole fault components
hidden + buffer; seed 30 n=11,342 / seed 20 n=11,321 withheld positives):

| arm | seed 30 | seed 20 |
|---|---|---|
| A0 random | 0.0509 | 0.0491 |
| A1 control (H79 recipe) | 0.1143 | 0.1087 |
| archived best (H79-MCT C2) | 0.1152 | 0.1095 |
| A2 = SDPT pixel | 0.1203 | 0.1113 |
| A3 = A2 + SDPT-C trace | **0.1211 [0.1029, 0.1402]** | **0.1114 [0.0943, 0.1287]** |
| A3 capped for registry uniqueness (E2) | 0.1036 | 0.0910 |

- Leakage canary: worst single-channel symmetric AUC 0.571 (seed 30) /
  0.600 (seed 20), far below the 0.90 stop line.
- A3 beat A1 and the archived best on both seeds (preregistered G3 point
  criterion), but paired A3−A1 CIs include 0 (+0.0068 [−0.0004, +0.0151];
  +0.0027 [−0.0029, +0.0084]): direction consistent, size not proven.
- Unconstrained A3 dots fired the duplicate rule vs 99 dot-field priors
  (63 unique supports). 11 are halo-saturating/non-discriminating
  (Amendment B1); capping the 52 discriminating priors at 0.68 produced a
  registry-unique artifact (worst Spearman 0.093; capped shares ≤0.680;
  non-discriminating exact overlaps ≤0.089) — but E2 measured the cap cost
  at −0.0176/−0.0203, landing below the control on both seeds.
- **Verdict: negative / DO NOT SUBMIT** (`run_card_g79b.json`). Lesson for
  the next lane: in this family the binding constraint is no longer
  detector skill but *crowding* — every good scarp detector's top terrain
  is already dotted. A future lane must be born unique (top terrain ≠
  family's top terrain), e.g. rank within strata the family ignores,
  rather than capped into uniqueness afterwards.
