# Five candidate hypotheses that had not been run (session `ff2e4413`)

Each hypothesis was ranked **before** implementation by expected HOLDOUT-DTI gain and by implementation cost. Only the top one (G79-OPC) was
executed, under `registry/preregistration_g79_opc.json`. The expected-gain column is a
*prior judgement*, not a score. Measured results are in `run_card_opc.json`.

**Why there is a gap.** The scored truth is "new faults" mapped by experts and absent
from the USGS/INGENIOUS catalogue. The USGS Quaternary Fault and Fold Database
compiles faults with evidence of Quaternary surface deformation and represents them
with simplified traces ([USGS faults program](https://www.usgs.gov/programs/earthquake-hazards/faults)).
That leaves short splays, step-over connectors and buried strands under-represented.
Faulds & Hinz (2015) found that in the Great Basin, step-overs/relay ramps (~32%),
fault terminations (~25%) and fault intersections (~22%) host most geothermal
systems. They describe these as places with "multiple, commonly overlapping fault strands" and
"closely-spaced faults"
([WGC 2015 paper, Stanford archive](https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11100.pdf),
[OSTI record](https://www.osti.gov/biblio/1724082)).

| Rank | ID | Layers | Physical / statistical signature | Why it targets *missing* faults | Different from repo lanes | Prior gain | Cost | Data |
|---|---|---|---|---|---|---|---|---|
| 1 | **G79-OPC** | visible catalogue (geometry only); LiDAR scarp (2-m 3DEP derived); geophysics stack | **Strike-rotated inter-component pair-correlation g(u,v)** (anisotropic Ripley/second-order statistic). Combined with LiDAR-strike concordance | Fault populations have characteristic spacing, and spacing scales with mechanical-layer thickness ([Soliva et al. 2006, JGR 111 B01402](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2004JB003507)). Companions of mapped faults sit at learnable offsets, and simplified catalogue traces omit them | No repo lane estimated an *empirical, oriented, between-component* second-order kernel. DZD used an isotropic distance band. Tip/stepover lanes used hand-drawn cones | High | Low (~15 min CPU) | Ready (13/13 pinned inputs) |
| 2 | G79-SPRH | GDR-1391 well/spring table (`gdr_wellspring_in_footprint.csv`) | **Hough-transform alignment of spring/well points** (thermal and cold). Linear spring lines are a classic fault indicator | Spring alignments mark permeable or barrier faults without relief, including on playas | Earlier lanes put isotropic kernels on springs. None used collinearity | Medium | Low | Ready |
| 3 | G79-SIGN | LiDAR `upface_max`/`downface_max` + `iso_grav_anom` | Signed scarp facing vs. sign of the horizontal gravity step (hanging-wall basin fill is low density) | Separates fault scarps from shorelines/terraces, which have no density step | THVC used `abs(up-down)` only | Medium | Low | Ready |
| 4 | G79-SEIS | Relocated microseismicity (3-D planar clusters) | Planar hypocentre clusters projected to the surface trace | Active blind faults below the catalogue's surface-evidence threshold | Training bands carry only distance/intensity summaries (`deq`, `ieq`) | Medium | Medium | **External:** [USGS ComCat API](https://earthquake.usgs.gov/fdsnws/event/1/) (free, no login). The sandbox cannot reach it; an owner mirror is needed |
| 5 | G79-INSAR | NASA OPERA DISP-S1 line-of-sight displacement | Discontinuities in the deformation field (creep/poroelastic offsets across faults) | Detects faults that act as groundwater barriers or creep, with no geomorphic scarp | No InSAR in any lane | Unknown | High | **External:** [ASF DAAC OPERA](https://asf.alaska.edu/datasets/daac/opera/) requires a free NASA Earthdata login, so it is not obtainable autonomously here |

## Why G79-OPC was chosen first

- It was the highest-ranked candidate whose data are already pinned in the repo.
- It is cheap enough to run inside the protocol budget (3 experiments, 2 hours).
- It has a built-in falsification test. EXP-OPC-1 (oriented kernel) is compared with C-ISO (the same pipeline
  with the rotationally averaged kernel) on the same folds. If anisotropy carried no information, the
  paired difference would straddle zero.
- Named mimic: Pleistocene Lake Lahontan shorelines and fluvial terrace risers are also
  parallel, regularly spaced linear steps, so they could fake a concordant LiDAR signal.
  The model sees the TIGER road distance but has no explicit shoreline veto (a known limitation).

## Data-source checks for the external candidates (4, 5)

These are named so that a future session can verify them. Neither was used here.
- USGS ComCat FDSN event service: `https://earthquake.usgs.gov/fdsnws/event/1/`. This is public. The sandbox
  allowlist only includes github.com / PyPI / npm hosts, so it was not fetched.
- NASA ASF DAAC OPERA products: `https://asf.alaska.edu/datasets/daac/opera/`. Download requires an
  Earthdata login, which cannot be created or used autonomously.
