---
title: Sources and evidence ledger
---

# Sources and evidence ledger

Checked 2026-10-21 (UTC). Primary/official sources are used for factual statements; unofficial GEMSDOE pages and user-pasted scores are context only.

| Topic | Source | Verified from source | Limits / evidence class |
|---|---|---|---|
| Competition goal, incomplete catalogue, expert-labeled faults, datasets and feature layer families | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | The challenge asks for fault predictions; public fault data may be incomplete/inaccurate; dataset includes geophysical/topographic/geological features and USGS/INGENIOUS labels. | Official text, fetched 2026-10-21. Not a validation of any local raster. |
| Metric and submission format | [DrivenData problem description, scoring/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Distance-weighted Tversky, alpha 0.2, beta 0.8, triangular kernel support 300 m; format requires EPSG:32611, 100m, one float32 band, values [0,1], same bounds and null/NaN outside. | Official format; always follow any current portal validator as final authority. |
| Current public leaderboard | [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | At fetch time, rank 1 displayed 0.4413. | Public leaderboard only; not a private/final round guarantee. This is not a project score. |
| Data access | [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Unauthenticated page redirected to DrivenData login. | This agent has no authenticated account session/data files. Do not claim to have downloaded competition data. |
| GeoDAWN magnetic/radiometric products and lidar context | [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [ScienceBase item](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) | USGS says GeoDAWN contains airborne magnetic/radiometric surveys and that lidar collection was coordinated over a similar extent. The release states products include geophysical grids and flightline data; rights are marked CC0 1.0. | Does not prove a particular file has been downloaded, aligns to training grid, or will improve scoring. |
| GeoDAWN item metadata/file listing | [ScienceBase JSON](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7?format=json) | Official item metadata identifies data release 10.5066/P93LGLVQ and lists downloadable files. | File list can include large products; test actual direct download, integrity, coverage, licenses and pixel alignment before use. |
| CRS | [EPSG:32611](https://epsg.io/32611) | WGS 84 / UTM zone 11N, metre units, northing/easting projected coordinates. | CRS name alone does not prove candidate transform/extent matches a training raster. |
| Reference solution | [DrivenData reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution) | Public source repository is available; its README describes obtaining competition data and running its model notebook. | This GEMSDOE79 checkout does not contain that repository or its code/data. Do not claim its model is implemented here. |
| H33 artifact claims in supplied sister project | [GEMSDOE32 landing page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | Page labels H33 as a candidate and says no organizer score exists for its artifacts. | Non-organizer project page; conflicting user-pasted numeric score cannot be confirmed from that page. Treat any projection as a model output, never an official score. |
| Official scoring history for this project | [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Live public score displayed at fetch time. | User-supplied results table from numerous sister websites is not independently verified in this checkout and has no organizer submission receipts. |
| ComCat for optional earthquake-event proposal | [USGS FDSN event service](https://earthquake.usgs.gov/fdsnws/event/1/) | Official USGS service endpoint is documented for event queries. | Not checked for local event/focal mechanism density; do not consider adequate coverage established. |

## Important discrepancies / irregularities

1. User-provided context says the current highest score is 0.3195 (elsewhere 0.4413). The live official public leaderboard fetched on 2026-10-21 displays 0.4413. The observed current value takes precedence; the user-provided 0.3195 is stale or from another snapshot/definition.
2. The user-provided GEMSDOE32 list says H33 scored 0.2778. The linked GEMSDOE32 page itself describes it as a candidate and explicitly states there is no organizer score for its artifacts. No submission receipt was supplied. Therefore 0.2778 is **not verified as an ORGANIZER-CONFIRMED score** here.
3. GEMSDOE32 says in its own description the H33 note includes a projected result and “UNSCORED”; a projected number is not evidence of an actual leaderboard result.
4. The competition's data endpoint requires login; this checkout has no data or authenticated session. User-shared Dropbox and other third-party files are not treated as official training data, registry rasters, or permission to copy submitted predictions.
5. The user supplied many historical scores and names from related sites. They were not checked against organizer receipts or their underlying artifacts; use only as hypothesis context, not as measured results.
