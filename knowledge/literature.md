## Additional primary-literature review — implications, not new experiments

Reviewed on **2026-10-21**, after the mandatory E1 stop. This review did not
change features, consume another experiment, label new faults or authorize a
second lane. It provides context for interpreting failures and planning an
explicitly authorized future study.

### Hermant, Kiersnowski & Bellanger (Stanford Geothermal Workshop, 2025)

[Using Deep Learning to Map Quaternary Faults in Western USA — full paper](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf).
All eight parsed chunks, including methods, discussion and references, were read.
This is a primary author publication hosted by Stanford, **not an organizer
receipt, USGS endorsement, or evidence that its model was reproduced here**.

What is useful for this problem:

- The paper distinguishes incomplete, regionally heterogeneous public mapping
  from true fault absence. Its Figure 2 illustrates mapping discrepancies; this
  supports treating catalogue zeros as **unlabelled**, not certified negatives.
- The authors use approximately 10 m elevation/slope and Sentinel-2 B8A imagery,
  not this lane's 100 m magnetic/gravity stack. They restrict their elevation
  selection to lidar-derived areas after observing slope artifacts elsewhere
  (§3.1). Resampling a coarse grid cannot manufacture that independent evidence.
- Their §5.1 procedure randomly splits fault-containing image tiles before data
  augmentation. Their paper metrics are PR-AUC and weighted focal IoU, not the
  competition's pooled distance-weighted Tversky. Neither these metrics nor
  qualitative figures establish our blocked hide-and-recover performance. A
  random tile split is not a substitute for our required buffered whole-segment
  split; this is a protocol distinction, not proof that their results leaked.
- The authors report overfitting and explicitly identify **paleo-shorelines,
  canyon margins, streams and other scarps** as fault mimics (§6–7, Figures 8–9).
  A long, clear lineament is therefore not sufficient geological evidence.
  Automatically excluding every shoreline or drainage feature is unsafe too,
  because faults can be co-located with them.
- Faults can conduct **or impede** fluid flow (§2). Better fault detection is not
  proof of a permeable, hot or commercially productive reservoir. Their expert
  manual correction is not an automated submission-validation method; it was
  not substituted for our automatic gates.

**Practical consequence:** a future, separately authorized morphological lane
would need independent data provenance/resolution checks, a non-fault-mimic
control, and buffered spatial tests. Proprietary FaultSEG weights and its tracing
algorithm are not claimed to be available. This project neither implemented nor
scored a CNN from that publication.

### Official INGENIOUS project and USGS regional geophysics

- [Great Basin Center for Geothermal Energy — INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
  describes integrated structural, geophysical, thermal and exploration work;
  its primary project/publication listing was reviewed. It does not establish
  independent hidden-test labels or commercial discovery from a raster alone.
- [USGS, Glen et al. (2022), Regional geophysical maps of the Great Basin](https://doi.org/10.5066/P9Z6SA1Z)
  lists a multi-source provisional gravity grid, a magnetic compilation and a
  depth-to-basement grid. The release lists a public **6.5 MB** grid ZIP and
  metadata/readme. This checks that a real official release exists; **no new
  binary download or verified correspondence to a particular mirrored band is
  claimed**. Regional compilations and resampled grids should not be read as
  uniformly sampled, independent 100 m observations.

These sources strengthen the uncertainty and confounder analysis. They do not
make the literal novelty conflict disappear, validate E1, or justify an expected
leaderboard gain. The four earlier hypotheses remain qualitative priorities,
not numerical score projections.
