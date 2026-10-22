# Five ranked hypotheses for the GEMS Prize — and what happened to the top three

Session branch `arena/36514e3d-gemsdoe79`, 2026-10-22. Every claim below is either a
**RASTER-MEASUREMENT** (counted from pinned bytes by a script in this repository) or a
**HOLDOUT-DTI** (the shared `gems57-pooled-hide-v2` evaluator). Nothing on this page is a
leaderboard projection.

The brief asked for 3–5 candidate hypotheses that had not been tried, each naming the layers,
the physical signature, why it should catch a fault *missing* from the catalogue, and how it
differs from everything already in the repository; ranked by expected HOLDOUT-DTI gain per unit
of implementation cost; and validated on the spatially blocked holdout before a slot is touched.

Three were preregistered before measurement (`registry/preregistration_g79_{mfx,ece,por}.json`),
run, and are reported with their terminal cards. Two remain untested and are kept as a
source-checked backlog with the honest reason they were not run.

---

## Ranked list

| Rank | ID | Layers | Physical signature targeted | Why it should catch a *missing* fault | How it differs from this repo | Cost | Status |
|---:|---|---|---|---|---|---|---|
| 1 | **G79-MFX** — catalogue-template matched filtering | `training_features.tif` b2 RTP magnetic, b13 isostatic gravity, b19 detrended-elevation slope, b15 depth-to-basement | 15×15 px and 21×21 px zero-mean multi-channel templates cut from **visible** catalogue pixels, transferred by normalized cross-correlation (matched filter), fused by a 4-quadrant out-of-fold LightGBM | An unmapped strand reproduces the *same local joint magnetic/gravity/slope texture* as a mapped one; the filter fires on the signature, not on the distance to a neighbouring trace | Every prior learned lane (H79-NHR, G79-CSKD, G79-DFSD, G79-CSMD, H79-MRND) is pointwise: one pixel, one feature vector. Analytic-signal lane H78-MPC uses phase congruency with no learned template. No lane in the repository or in the 93-repository family used a template bank | ~20 min CPU | **RUN — NEGATIVE** (0.0504 / 0.0492 vs uniform 0.0505 / 0.0515) |
| 2 | **G79-ECE** — enriched-coverage emission | Derived from b2 (structure tensor) and b2+b9 (tilt angle); no catalogue input | Kernel-spaced 3 px lattice over a fault-likelihood corridor prior, exploiting that α = 0.2 / β = 0.8 make the index coverage-dominated | A coverage-first emission does not need to know *which* fault is missing, only where faults can be; every truth cell reached inside 300 m is a true positive at no ranking cost | Prior emitters (Charnes-Cooper submodular, Poisson-disk, greedy DTI allocation) all rank *pixels by a score*; this ranks *area by coverage* and was pre-declared as such | ~8 min CPU | **RUN — NEGATIVE** (0.0443 / 0.0441 vs uniform 0.0688 / 0.0642; corridor enrichment only 1.06× / 1.22×) |
| 3 | **G79-POR** — two-regime portfolio emission | b2/b9 for the corridor arm; the pinned catalogue for the collar arm | 50/50 fixed budget: 3 px lattice in the 3–12 px collar (validated regime) plus 3 px lattice in corridors beyond 12 px (blind-basin regime) | The two readings of "where are the new faults" are mutually exclusive; a fixed split hedges the hidden test instead of betting the instrument's preferred regime | No prior lane emitted a *declared mixture of two mutually exclusive geological regimes at a fixed budget split*; all prior lanes optimise one posterior | ~9 min CPU | **RUN — NEGATIVE, PUBLISHED AS LABELLED PROBE** (HYBRID 0.0440 / 0.0468; collar alone 0.0509 / 0.0564 did beat uniform) |
| 4 | **G79-FLT** — magnetic flight-line deconvolution with known acquisition geometry | `training_features.tif` b1, b2, b9, b14 + USGS GeoDAWN survey metadata (line spacing/azimuth, `doi:10.5066/P93LGLVQ`) | Estimate the acquisition stripe kernel in the 2-D Fourier domain from the survey's published line spacing and deconvolve it, instead of notching it away; then re-run tilt-depth contact extraction on the deconvolved RTP | Intrabasin step faults under 50–500 m of playa fill have **no topographic scarp**, so they are invisible to the LiDAR/scarp lanes that dominate this repository; a deconvolved magnetic edge is the only surface-geophysical signal that survives burial | G79-TDW already *notched* ±0° / ±90° stripes and scored 0.0395 / 0.0413. Deconvolution keeps the amplitude information the notch destroys; that is a different estimator, not a different threshold | ~45 min CPU + survey metadata | **NOT RUN** — see "Why 4 and 5 were not run" |
| 5 | **G79-KNP** — multi-drainage knickpoint collinearity on a free 10 m DEM | USGS 3DEP 1/3 arc-second DEM (free, `apps.nationalmap.gov/downloader/`) + `training_features.tif` b12/b19 | Convex knickpoints on channel long-profiles inside convergent plan-curvature channels, then a Hough/Radon collinearity test linking ≥3 independent adjacent drainages across 1–6 km | A slow normal fault across an active bajada has its scarp erased between ruptures, but every drainage crossing the footwall uplift keeps a locked knickpoint on the same strike | H79-U2 in the backlog proposed this and was never executed; the repository has no drainage-network lane at all | ~60 min CPU + one 10 m DEM tile mosaic | **NOT RUN** — the DEM host is outside this sandbox's egress allowlist |

---

## Why 4 and 5 were not run (checked, not assumed)

* **G79-FLT** needs the GeoDAWN survey's published line spacing and azimuth. The USGS data
  release (`https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and`,
  `doi:10.5066/P93LGLVQ`) is not reachable from this sandbox, whose egress allowlist is
  `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`,
  `files.pythonhosted.org`. The stripe period could be estimated from the raster alone, but a
  fitted period is not the published acquisition geometry, and calling it that would be a
  hallucination. **Specific free official source required: USGS ScienceBase GeoDAWN metadata.**
* **G79-KNP** needs 3DEP 1/3 arc-second tiles (`https://apps.nationalmap.gov/downloader/`), also
  outside the allowlist. The alternative — the 100 m detrended elevation already in the stack —
  cannot resolve knickpoints at the 1–6 km spacing the hypothesis needs.
* Both remain valid, source-named ideas. Neither was proposed as viable, and neither consumed a
  slot.

## Why the top three all failed, stated once

The instrument withholds **whole catalogue components** and scores recovery of them. That makes
it a test of *catalogue-extrapolation*, not of *discovery*: 100% of its truth pixels lie on the
mapped network's own geometry. Measured consequences in this session:

1. A matched filter trained on catalogue texture reproduces catalogue *proximity* (0% of its dots
   landed beyond 1 km) and scores like uniform noise.
2. Geophysical corridors that carry no catalogue information enrich withheld-fault density by
   only 1.06×–1.22×, so coverage-first emission there is worse than uniform.
3. The only reproducible skill is the collar arm (3–12 px from a mapped trace), and it is worth
   roughly **+0.006 DTI** over uniform at the same budget — an order of magnitude less than the
   incumbent's 0.1905, which comes from concentrating a small number of dots very near the
   visible network.

That is a property of the instrument, and it is the single most important limitation for the
competition: **beating 0.4413 requires generalising off the catalogue, and this holdout cannot
certify that.** It can only falsify. All three cards are therefore negative, and the negative is
the deliverable.
