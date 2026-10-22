# Candidate hypotheses — 2026-10-22 session `arena/6444be2d-gemsdoe79`

Written before any H79-DILSTEP score. The E1 result is in `reports/dilstep_result.md`: the holdout lost to the H33 control, and the surface gate failed. Rank is expected usefulness for faults
**missing from the USGS/INGENIOUS catalogue**, then implementation cost on the
pinned mirrors. These are not DTI scores and not leaderboard projections.

Official context, read this session:

- Task and metric: [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). Alpha 0.2 penalizes false positives; beta 0.8 penalizes false negatives; kernel radius 300 m. Known USGS/INGENIOUS pixels are masked at scoring ([staff clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)).
- Public leaderboard observed 2026-10-22: rank 1 is 0.4413 (xiaofanhu), not 0.3195. The prompt's 0.3195 figure is stale (already IR-79-05). [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- Structural prior: Faulds & Hinz, World Geothermal Congress 2015, [Favorable tectonic and structural settings](https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11100.pdf). Step-overs ~32%, terminations ~25%, intersections ~22%, major range-front faults ~1% of catalogued Great Basin systems.
- GeoDAWN magnetics/radiometrics: [USGS data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI 10.5066/P93LGLVQ. Area 2 flight lines are 400 m apart; a 100 m grid is not 100 m independent magnetic observations.
- Grid: [EPSG:32611](https://epsg.io/32611).

| Rank | Hypothesis | Layers and signature | Why a fault missing from the catalogue, not one already in it | Difference from this repo | Cost | Data |
|---|---|---|---|---|---|---|
| 1 (run as E1) | **H79-DILSTEP.** Linking strands in step-overs, tip horse-tails and high-angle intersections. | `tmi_hg`, `iso_grav_anom_hg`, positive `geod_dilaterate`, rank-only Th/K, lidar `step_max` only as a shoreline suppressor. Visible-catalogue tips only. | Faulds settings are exactly the strands regional linework omits. Mid-segment range fronts are down-weighted, not re-predicted. | Not NHR regression, not STEPCO dipoles, not scarp persistence, not far-field lidar rank, not E1 lag. Band 6 `tc` unused (IR-79-13). | Medium. Closed form, no new download. | Pinned mirrors already in `registry/data_manifest.json`. |
| 2 (not run) | Walker Lane cross-strike magnetic ridges in basin floors only (strike 280–330°). | `rtp` gradient orientation, low `det_elev_slope`, high `depth_to_base_surf`. | Blind NW cross-faults lack scarps, so Qfaults omits them. | Not the all-orientation Blakely/Radon/tilt-worm siblings, and not E1's lag. | Low, but holdout truth is mostly range-front, so the proxy may reject a real organizer signal. | Same pinned stack. |
| 3 (not run) | Upflow offset: dots upslope of a Th/K high that is not adjacent to a mapped fault. | Th/K, `det_elev` aspect, distance to visible faults. | Alteration can mark a blind conduit the mapper did not draw. | GEMSDOE46 fused radiometrics onto scarps. This would place the dot off the anomaly, toward the inferred conduit. | Medium. | Same uint8 Th/K derivative. Not a calibrated concentration (IR-79-17). |
| 4 (not run) | Basin-floor blind gravity edge under cover, no lidar step required. | `iso_grav_anom_hg`, high `depth_to_base_surf`, low slope. | Cover hides the scarp, so the fault is absent from a geomorphic catalogue. | Not the scarp family and not H79-FF (which requires a lidar step 2–8 km out). | Low. Same holdout-mismatch risk as rank 2. | Same pinned stack. |
| 5 (not run) | Distance-band hide-and-recover (backlog item from a7d092d7). | Full feature stack plus visible-only distance, separate rankings by distance band. | Could learn far-field discoveries instead of NHR's 300 m–2 km collar. | NHR used one pooled target. This would split the target. | High, and the near band is the known duplicate corridor. | Same pinned stack. |

Only rank 1 is preregistered and executed (`registry/preregistration_h79_dilstep.json`).
Ranks 2–5 were not scored. No external dataset beyond the pinned mirrors was required
for rank 1, so none was proposed as a blocker.
