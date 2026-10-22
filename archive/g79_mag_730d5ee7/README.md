# Archived Lane `G79-MAG` (`PR #54`, session `730d5ee7`, stopped negative — DO NOT SUBMIT)

Quarantined out of live `docs/g79_mag/` (`IR-79-95`) to preserve the single-canonical-upload-artifact contract (`docs/downloads/` contains only the single active `-DO-NOT-SUBMIT` research GeoTIFF + ZIP).

- **Artifact:** `gems79-g79-mag-37654dots-20261022T060000Z-e48a9293.tif` (`37,654` binary `{0, 1}` pixels, format PASS)
- **`HOLDOUT-DTI` (`gems57-pooled-hide-v2`):** `0.0045` (seed 20) / `0.0067` (seed 30) vs `H33` control `0.0961 / 0.0989` (**lost by >14x**)
- **Uniqueness re-measurement (`IR-79-95`):** Despite claiming `0.644 < 0.70` after checking only `952/992` rasters, actual forward `3-px` overlap against binary dot raster `13GEMSDOE:docs/downloads/13gems_20261001_r13-lattice-s5_v2_zerofill.tif` is **`0.990864 > 0.70`** (consistent with the universal Pigeonhole lower bound `>= 0.827004` for every `37,654`-dot map).
- **Verdict:** `negative` (`OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.`, `0` weekly slots used).
