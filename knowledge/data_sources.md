# Data and sources — auditable table

Every input used by this lane, where it came from, how it was verified, and the official origin
for manual review.  SHA-256 pins are in `registry/data_manifest.json` (inputs), `data/cache/dem10/manifest.json`
(10 m channels) and `registry/registry_inventory.json` (812 prior rasters).  `restore_data.py` fails
closed on any hash mismatch (`evidence/restore_data.log`).

## Competition files (login-walled originals; owner's SHA-pinned GitHub mirrors used)

| file | used for | mirror (repo @ ref) | sha256 (first 12) | bytes | official origin |
|---|---|---|---|---|---|
| `training_features.tif` (19 bands) | bands 12 `det_elev`, 19 `det_elev_slope` only | `GEMSDOE@c0c06ac8` `data/bridge/*.part-*` | `4371c82e3b83` | 418,912,844 | https://www.drivendata.org/competitions/306/competition-doe-gems/data/ |
| `existing_faults.tif` | catalogue (USGS Qfaults + INGENIOUS), masking, training positives | `GEMSDOE24@07345ea0` | `7ba308ccdc44` | 425,830 | same |
| `labels.tif` | identical bytes to `existing_faults.tif` (verified) | `GEMSDOE24@07345ea0` | `7ba308ccdc44` | 425,830 | same |
| `sample_submission.tif` | grid / footprint reference (5,167,373 finite cells) | `GEMSDOE24@07345ea0` | `2176d08e485a` | 1,599,597 | same |

Grid (verified from every file): EPSG:32611, 3730 rows × 3292 cols, 100 m, transform
(100, 0, 243350, 0, −100, 4508550).  Catalogue positives: 60,988 cells.

## External, free, official data (derived products cached by the owner's CI; de-quantised here)

| product | used for | cache (repo @ ref / tag) | sha256 | official source | licence |
|---|---|---|---|---|---|
| 1 m lidar scarp descriptors, 12 bands u8 (`lidar_scarp_features_u8.tif`) | 11 feature channels + strike | `GEMSDOE24@07345ea0` `data/external/` (built by 7GEMSDOE CI run 36266555805 from 706/716 tiles) | `d580bb8bdcdb…` | USGS 3DEP 1 m DEM tiles — https://www.usgs.gov/3d-elevation-program ; product catalog https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5 | public domain (USGS); acknowledge "Map services and data available from U.S. Geological Survey, National Geospatial Program" |
| 10 m (1/3 arc-second) 3DEP channels, 13 × float32 vectors | 8 feature channels | `GEMSDOE10` tag `ext/dem10-36343078537` (GitHub Actions run 36343078537, code sha 70c12296) | per-channel in `data/cache/dem10/manifest.json` | USGS 3DEP 1/3 arc-second seamless DEM — https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5 | public domain |
| H19-5 scored line set (`gems19-h19-5-…-e27054cf-nan.tif`) | uniqueness quota only (never a feature) | `GEMSDOE24@07345ea0` `inputs/` | `ec1f9b56b83c` | family artefact (19GEMSDOE), OWNER-REPORT 0.1922 | n/a |
| 812 prior family rasters | uniqueness audit only | GitHub git-blob API, blob-SHA1 verified, re-hashed SHA-256 | `registry/registry_inventory.json` | family artefacts | n/a |

Restored but **not used** by this lane (kept for completeness, listed in the manifest):
GeoDAWN radiometrics (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`; USGS data release DOI
10.5066/P93LGLVQ, https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
SGMC fault proxy (`derived_sgmc_faults_100m_u8.tif`; USGS SGMC https://doi.org/10.5066/P9WDH14R),
GDR 1391 wells/springs, Qfaults attributes, vents (DOI 10.15121/1881483, CC BY 4.0, https://gdr.openei.org/submissions/1391),
and 11 calibration/scored rasters under `data/raw/scored/`.

## LiDAR cache de-quantisation (from `data/cache/lidar_scarp_features.json`, GEMSDOE24)

`q = 1 + round(254 · t(clip(x / x_max, 0, 1)))`, `t ∈ {sqrt, linear}`, `q = 0` = no lidar.
Inverse used in `src/gems79/data.py`: `x = x_max · ((q−1)/254)^2` (sqrt bands) or `x_max · (q−1)/254`.
Band meanings: ex_max/ex_mean = 2 m slope in excess of the 30 m regional slope; step_max = 10 m-scale
minus 50 m-scale slope; lapneg/lappos = crest convexity / base concavity (LoG 6 m of the 50 m band-pass);
downface/upface/cross = band-passed step gradient along / against / across the 100 m regional slope;
relief; coh100 = structure-tensor coherence; strike 0–180°; valid.  Coverage 3,893,184 cells (75.3 %).
Caveats stated by the producer: uncalibrated descriptors; roads, channels, terrace risers,
paleo-shorelines, landslides and mines also create steps.

## Not obtainable from this sandbox (named so the next session can fetch it)

* USGS 3DEP 1/3 arc-second **elevation** (absolute heights) for Lahontan-shoreline de-confounding:
  https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5 (TNM download:
  https://apps.nationalmap.gov/downloader/).  Sandbox egress is limited to GitHub/PyPI.
