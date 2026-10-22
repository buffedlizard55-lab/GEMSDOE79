# H80 Candidate Hypotheses — 2026-10-22 (new lane, not E1)

Ranked before any new scoring. All use only cached, hash-pinned `training_features.tif` bands or the already-restored `geodawn_rad_u8.tif` external radiometric derivative. No catalogue-derived features (distance to faults, fault density) are used to avoid leakage (AUC>0.90 canary). Each names layers, physical signature, why it should catch a USGS/INGENIOUS-missing fault, and difference from inspected prior implementations.

## Rank 1 — Triple concordance: topographic scarp + gravity step + magnetic edge (H80-SCARP-GRAVITY-MAGNETIC) — EXPECTED BEST

- **Layers:** `det_elev_slope` (19), `iso_grav_anom_hg` (18), `tmi_hg` (3) from `training_features.tif`. All three are already provided as horizontal gradients; no extra DEM download needed.
- **Physical signature:** Multiscale normalized rank product: geometric mean of the three footprint ranks. A pixel must be simultaneously in the top decile of scarp strength, gravity horizontal-gradient strength, and magnetic horizontal-gradient strength. Edge orientation concordance is implicitly required because all three are horizontal gradients responding to a common linear source; a strong response in only one dataset is downweighted multiplicatively. Unlike same-pixel products that use one physics, this requires agreement across independent sensors (topography = surface rupture; gravity = density step; magnetics = lithologic susceptibility).
- **Why missing from catalogue:** Range-front and intra-basin faults under Quaternary alluvium often have subdued scarps visible only in detrended slope, but without a surface trace they are omitted from USGS/INGENIOUS historic mapping. Yet they still juxtapose basement densities (gravity) and volcanic/sedimentary magnetic units. A topographic-only detector misses them; a magnetic-only detector flags intrusive contacts. Requiring all three selects buried Quaternary normal faults over fluvial terraces (topo only) or oblique contacts (mag only).
- **Difference:** Siblings used scarp ridges alone (`lidarscarp-ridge-top2pct` 0.1461), scarp+rad (`r11f-scarp-radiometric` 0.1589), or gap-closure (`topo-gap-closure` 0.2449). None computed a triple geometric mean of detrended slope + iso_grav_anom_hg + tmi_hg with footprint ranks. Previous magnetic/gravity edges were vertical derivatives or total-gradient, not the horizontal-gradient pair that is most sensitive to near-vertical fault contacts.
- **Cost / viability:** Low-medium CPU, all bands restored & pinned (sha256 4371c82e3b83). No new external data. Canary test feasible on holdout with whole-component hiding. Mimic: paleo-shoreline/terrace (strong topo, weak gravity/mag) and survey levelling seam (mag only) are suppressed.

## Rank 2 — Radiometric alteration halo offset (H80-RAD-HALO)

- **Layers:** `ext_geodawn_rad_u8.tif` K band 1, Th band 2 (already restored, 4-band uint8), plus `det_elev_slope` (19).
- **Signature:** K/Th ratio profile offset: detect K enrichment 100–300 m lateral to a scarp lineament, using short cross-scarp K/Th profiles (NCC gain at nonzero lag, analogous to E1 but for radiometric rather than magnetic fabric). Surface = scarp rank × K/Th contrast rank × off-scarp halo gain.
- **Why missing:** Fault-controlled hydrothermal alteration produces K-metasomatism halos; these are too subtle for geologic mapping but correlate with geothermal systems (GBCGE INGENIOUS goal). Surface radiometric is independent of subsurface magnetic/gravity, so it can flag a young fault that hasn't yet offset basement markers.
- **Difference:** Previous radiometric halo `h73-mcsc-seamfree-blakely` (0.1917) used MCSC+Blakely on total counts; sibling `r11f-scarp-radiometric-fusion` fused scarp + radiometric concordance, not offset halo. This estimates lateral offset of K/Th, not just halo presence.
- **Cost:** Medium; external file already present (sha256 c22420f75999) but is uint8 derivative, not calibrated source. Rank-based only, no concentration physics. Viable but needs extra profiling code.
- **Mimic:** Fan gravel pediment drapes compositional contact without tectonic slip.

## Rank 3 — Blind basement step (H80-BASEMENT-STEP)

- **Layers:** `depth_to_base_surf` (15), `iso_grav_anom` (13), `cond_surf` (17).
- **Signature:** Normalized discontinuity in basement depth that coincides with a gravity anomaly step (>3 px) and a conductivity break, measured as gradient agreement product.
- **Why missing:** Blind faults bounding half-grabens under >500 m basin fill have no surface scarp; USGS lidar scarps miss them, yet they offset basement and control density.
- **Difference:** Prior `cvarlw-thin-s3p17` (0.2303) used cond_surf + variance but not depth_to_basement; no prior combined depth + iso_grav_anom + cond_surf triple.
- **Cost:** Low-medium, all bands cached. However depth_to_basement is coarse regional compilation (USGS Glen et al. 2022, 6.5 MB grid ZIP) resampled to 100 m; not independent.
- **Mimic:** Volcanic caldera margin or erosional unconformity produces similar depth step without Quaternary offset.

## Rank 4 — Geodetic strain gradient + topographic lineament (H80-STRAIN-GRADIENT)

- **Layers:** `geod_2ndinv` (4), `geod_shearrate` (7), `det_elev` (12).
- **Signature:** Strain-invariant spatial gradient (Sobel) that aligns with a topographic lineament (Hough orientation concordance).
- **Why missing:** Actively creeping faults accumulating strain but not yet ruptured in Holocene have no mapped scarp; geodetic data (GPS/InSAR strain rates) could highlight them.
- **Difference:** No sibling used geodetic second invariant/shear rate for fault prediction; most used only magnetic/gravity/topo. This is first to test geodetic.
- **Cost:** Low, but geodetic bands are interpolated GPS, ~10 km effective resolution, so 100 m grid is oversampled; risk of smooth-field canary leakage.
- **Mimic:** Distributed shear across a broad zone without a discrete fault; or reference-frame artifact.
- **Viability check:** Requires free official source verification: strain rates derive from UNAVCO/NSF GAGE GPS velocity field and USGS InSAR, not newly acquired. The training_features description cites geodetic strain; the underlying GPS network is public (https://www.unavco.org, https://doi.org/10.5066/P9Z6SA1Z regional compilation). Obtainable but coarse.

## Rank 5 — Magnetic tilt termination (H80-TILT-TERMINATION)

- **Layers:** `tc` (6, tilt/curvature), `tmi_hg` (3), `iso_grav_anom_hg` (18).
- **Signature:** Tilt-angle zero-contour termination where a magnetic marker ends abruptly at a gravity edge; measured as along-gravity-edge coherence of tilt-zero density contrast before vs after contact.
- **Why missing:** Covered transverse faults truncate magnetic stratigraphy without a gravity offset of their own; they appear only as magnetic fabric terminations.
- **Difference:** Prior tip Euler methods (`h32-1-prethin-tip-euler` 0.2649, `h36-1-rung30` 0.2710) used Euler deconvolution depth clustering, not tilt zero-termination per se. This is curvature-based, not depth-based.
- **Cost:** Higher (needs tilt zero extraction, coherence windowing). Intermediate.
- **Mimic:** Depositional pinch-out or erosional truncation of magnetic unit without fault.
