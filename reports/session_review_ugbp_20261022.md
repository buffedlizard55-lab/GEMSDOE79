# Session review — G79-UGBP (2026-10-22, three passes)

Branch: Arena-assigned session branch. Canonical G79-THVC decision unchanged
(0 slots used, no ORGANIZER-CONFIRMED score exists for any artifact here).

## What was asked, what was delivered

The session required a genuinely new, unique GeoTIFF with an obvious
download/submit decision, in-project (non-human) inspection, 3–5 ranked
untried geological hypotheses with the top one validated on the shared
spatially-blocked holdout before any slot, and a protocol run card.
Delivered: `artifacts/ugbp/gems79-ugbp-20261022-37654dots-zeros.tif`
(SHA-256 `1bf7a156…35a`, 37,654 binary dots), `run_card_ugbp.json`,
`docs/ugbp-submission.html` (download buttons + gates at the top),
`research/hypotheses_ugbp.md` (5 ranked hypotheses; Rank-5 GPS-strain idea
named its free official source — UNR MIDAS — and failed the sandbox egress
gate, so it was not proposed as runnable), frozen preregistration
`registry/preregistration_g79_ugbp.json` (written before any holdout score).
Decision, computed by the project validators: **OK TO DOWNLOAD: YES.
OK TO SUBMIT: NO** (holdout incumbent gate fails; full registry novelty and
official-text R6 uncleared). No slot spent.

## Pass 1 — implementation

Restored 13/13 SHA-pinned inputs; verified the official metric/format from
the DrivenData problem page (DTI α=0.2 β=0.8, 300 m triangular kernel;
single float32 band EPSG:32611, values in [0,1]). Implemented
`src/gems79/ugbp.py` (cation–quartz disequilibrium classes, uphill
streamline advection on `det_elev`, gravity-step gate; CSV whitelist never
reads `dist_known_fault_px`) and `scripts/run_ugbp.py` reusing shared
`gems57` grid/holdout/evaluator/writer. Results (HOLDOUT-DTI,
gems57-pooled-hide-v2): Exp2 candidate 0.1465 [0.1298,0.1615] (s20,
n=11,321) / 0.1477 [0.1289,0.1661] (s30, n=11,342); Exp1 pure surface
0.0148/0.0100 (below uniform); Exp3 ablation 0.1458/0.1468 (UGBP delta
+0.0007/+0.0009). 46 canaries pass (max symmetric AUC 0.806 ≤ 0.90; UGBP
features 0.500–0.512, i.e. chance on this instrument).

## Pass 2 — bugs, edge cases, fixes

1. **Canonical-downloads gate:** the new TIFF was first written to
   `docs/downloads/`, breaking `only_canonical_upload_artifacts_published`
   (only the canonical THVC file may live there). Moved the trio to
   `artifacts/ugbp/` (TIPSTEP pattern) and pointed the site at GitHub blob
   download URLs; run card/README paths updated.
2. **Orphaned site pages:** `check_site.py` already failed on `main`
   (TIPSTEP page unregistered). Fixed once in shared tooling: registered
   `tipstep-submission.html` + `ugbp-submission.html` in
   `docs/evidence/site_manifest.json` and the checker's expected set, added
   the missing skip links. Checker now passes (16 pages, 393 links).
   Limitation: `scripts/build_site.py` still generates only its 14 pages;
   a full rebuild would drop the two lane pages — recorded, not hidden.
3. **Exp1 interpretation:** with budget-forced filling, zero-score ties break
   by flat index, so Exp1 dots concentrate geographically; its below-uniform
   score is therefore not a clean pure-mechanism estimate. The cleaner
   falsification is the chance-level canary AUCs. Disclosed in the run card;
   recipe not retuned after seeing holdout.
4. **Gated vs ungated canary equality:** verified not a bug — only 876
   non-zero footprint cells, gate ratio ≈0.97–1.00 at the sampled head
   (array maxima 2.99 vs 1.90 differ); ties dominate the AUC.
5. **Format conflict kept explicit:** local validators PASS (no NaN,
   [0,1], grid match — the range-error-safe file); portal-spec R6 FAILs the
   zeros exterior (official text wants null/NaN; IR-79-224). Neither is
   presented as organizer acceptance.

## Pass 3 — re-check against the request

Independent rasterio re-read: 1 band float32, EPSG:32611, 3730×3292,
transform matches sample, 12,279,160 finite cells, min 0.0/max 1.0,
37,654 dots, 0 on catalogue, 0 outside footprint. ZIP contains exactly one
TIFF. Novelty (local, 47 files): surface max |ρ| 0.119 ≤ 0.90 pre-placement;
final sparse-dot max 3-px overlap 0.663 ≤ 0.70; literal 0.892 worst is a
dense continuous surface (halo-saturation class), flagged. Full 1,108-row
registry not scanned offline → not registry-certified. Test suite:
636 passed (incl. new `tests/test_ugbp.py`). `verify_project.py` exit 0;
`check_site.py` passed. Leaderboard language: no projection; H33 0.2778
stays an unverified report, 0.4413 another entrant's public observation.
Answer to "can we beat 0.2778?": not demonstrated by any artifact here;
the holdout incumbent itself (0.19) was not beaten, so promotion would be
spending a slot against the protocol. Lane closed — do not retune.
