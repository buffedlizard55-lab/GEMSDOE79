# Preregistered hypotheses — G79-FABRIC-OFFSET

Recorded before implementing or scoring the new method. Read alongside
[`registry/preregistration.json`](../registry/preregistration.json). No predicted
leaderboard scores are assigned to these ideas.

## Scope and evidence

The initial checkout contained only an 11-byte README. Therefore “not tried in
this repo” is verifiable but weak. We also inspected the sibling registry and
GEMSDOE32/76/77 method records: same-pixel multi-physics edges, magnetic/gravity
cross-gradients, radiometric lagged halos, scarp dipoles, relay tips, and
pseudogravity discordance already exist there. We do **not** rebrand those as
new. A global claim that nobody has tried these ideas is not supportable.

The assigned-method paragraph referred to in the request is absent. We declare
one narrow autonomous lane: **opposite-side magnetic-marker displacement across
an independent gravity edge**. Only the top hypothesis is computed and novelty-tested; the other
entries are future hypotheses within that lane, not permission to switch lanes.

| Rank / expected improvement (qualitative, not a score) | Geological hypothesis and exact layers | Physical statistic | Why an uncatalogued fault might appear | Difference from inspected implementations | Cost / viability | Named non-fault mimic |
|---|---|---|---|---|---|---|
| 1 · strongest specificity, uncertain recall | A cross-cutting, covered fault offsets a magnetic lithologic marker across a density boundary; cached `rtp` band 2 and `iso_grav_anom` band 13 | Opposite-side tangent-profile normalized correlation; best nonzero registration lag must improve on zero lag and retain its sign at 300 m and 500 m cross-contact distances | A buried displacement may preserve no surface scarp, yet displace a subsurface marker | Existing cross-gradient and oriented-consensus methods compare local directions/strengths. This compares **spatially displaced profiles on opposite sides**, not a same-pixel product | Medium, CPU only; both cached inputs restored and hash-checked; E1 | Unfaulted oblique intrusive/volcanic contact; survey levelling seam |
| 2 · lower expected specificity | A displaced magnetic fabric has the same signed registration in reduced-to-pole and total-field observations; cached `rtp` 2, `tmi` 14, gravity 13 | Agreement of estimated offset sign, not independent evidence from two sensors | Could reject transformations of one field that merely move the apparent edge | No independent-sensor claim: RTP and TMI are dependent products; this is a robustness check absent from the inspected offset lane | Low incremental cost; viable with cached bands; **not tested** | A shared flight-line or processing artifact survives both magnetic products |
| 3 · high specificity, likely low recall | A magnetic marker and a surficial compositional marker share a displacement at the same gravity edge; cached `external/geodawn_rad_u8.tif` bands 1 (K) and 2 (Th), plus RTP/gravity | Cross-contact registration-lag agreement between magnetic gradient and K–Th common-mode profiles, never K/Th values as a direct fault label | Small youthful displacement could cut both bedrock fabric and surface material, without a clear 100 m scarp | Distinct from sibling H79 radiometric *alteration-halo lag*: this estimates displacement **of markers across** a boundary, not halo position normal to one | Medium; pinned 8-bit radiometric derivatives restored; only rank/shape testing is viable without source units; **not tested** | Fan sediment drapes offset compositional boundaries without tectonic slip |
| 4 · moderate specificity, scale-limited | A displaced marker terminates coherently on a transverse fault rather than curving continuously around a contact; cached RTP 2, gravity 13, detrended elevation 12 | Profile-registration improvement combined with two-sided marker termination and failure of a smooth-curvature alternative | Covered transverse structures can truncate magnetic fabric without a mapped scarp | Adds explicit fault-versus-smooth-bend discrimination, rather than local curvature or Hessian ridge strength alone | Higher implementation cost; existing inputs only; **not tested** | Erosional truncation, depositional pinch-out, or a volcanic caldera margin |

No new external dataset is required for these four hypotheses. Availability is
not inferred from a web link: the actual cached input bytes are recorded in
`data/restore_receipt.json`. Their GitHub mirror hashes establish consistency,
**not organizer authentication**.

## Trusted-source boundary

- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
  was read in full: this is **fault mapping**, not direct detection of vents,
  reservoir temperature, productive permeability, or commercially viable wells.
  Existing labels are incomplete; new expert-labelled faults form test data.
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
  explicitly identifies aeromagnetics with subsurface geology/structure and
  aeroradiometrics with surface geology/soil composition. It also documents
  differing survey specifications, tie-line levelling and terrain-clearance
  variation. Those are confounders, not proofs of a new fault.
- [Official organizer reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution)
  confirms a train/predict baseline is available. It does not validate this new
  physical hypothesis or any expected improvement.

The displacement interpretation is a **testable hypothesis**, not an assertion
that every detected lag is a fault. Rejection by hide-and-recover, leakage, or
literal novelty gates is an equally valid deliverable. No weekly slot is used.

## Post-stop availability clarification (software/source review, 2026-10-21)

The restored external radiometric file is a four-band **uint8 derivative**,
labelled K, Th, U and TC on the reference grid, not a newly authenticated
calibrated USGS measurement product. Rank-based profile analysis could use its
spatial pattern, but quantitative concentrations, ratios or physical error bars
are not justified by those bytes. Original USGS GeoDAWN grids/reports are the
free official source needed to establish units and processing; the release was
reviewed, but no new direct binary download was verified in this sandbox. This
clarification does not change the immutable E1 preregistration or revive E1.
