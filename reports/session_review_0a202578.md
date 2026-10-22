# Session 0a202578: three-pass review (2026-10-22)

**Outcome: OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.** The new file is `docs/downloads/g79-fsc-exp1-45k-20261022-6febd9a3-zeros-DO-NOT-SUBMIT.tif` (SHA-256 `031b1335…fd837d7`). The automated selector refused it on three gates:

- **G1, holdout:** it is below the THVC incumbent on both seeds.
- **G4, surface novelty:** 33 informative duplicates.
- **G5, dot novelty:** it fails only against 4 registry rasters that are positive everywhere; see IR-79-195.

## Pass 1: implement and verify

| Step | Result |
|---|---|
| Restore the 13 pinned inputs and the frozen registry; rescan the post-freeze delta | 13/13 inputs. 992 frozen + 209 delta rasters, of which 1,216 are comparable with this repository's own TIFFs (10 non-comparable, listed) |
| Preregister G79-FSC before any feature existed | `registry/preregistration_g79_fsc.json`, commit `49d2383` |
| EXP-FSC-1 and EXP-FSC-2 (seeds 20 and 30) | 0.1406 / 0.1472 candidate; 0.1344 / 0.1347 ablation; canary ≤ 0.778 |
| Amendment A1, registered before seed 30 existed (commit `fedd6c7`) → EXP-FSC-3 | 0.1469 / 0.1580; canary ≤ 0.781. Rebuild check: absolute difference ≤ 6.3e-6 |
| Live map (EXP-1 rule: max mean inner-simulation DTI) | 45,000 dots, 0 on catalogue, 0 outside footprint |
| Write through the shared writer and validate with the shared validator | All checks passed: float32, 1 band, EPSG:32611, 3730×3292, transform match, finite, [0, 1], 0 outside footprint, 0 on catalogue |
| D-2 novelty scans: surface and dots, 1,216 rasters, 0 invalid | Surface: 37 duplicates. Dots: 4 duplicates, all saturated |
| Run the selector, then the site, README, verification and tests | Selector exit 2; `verify_project` all 33 checks pass; `check_site` ok; pytest passes |

## Pass 2: review and fix

| Finding | Fix |
|---|---|
| The Pages API reports legacy mode (`main:/`), which raised the question of whether the site URL needs `/docs/` | Checked the live site. `…/GEMSDOE79/evidence/site_manifest.json` is served and `…/GEMSDOE79/docs/…` returns 404, so the Actions artifact (`docs/` as root) is what is live. The root URL is kept, and the repository-root `index.html` redirect still covers legacy builds |
| The README blockquote ran four status lines together into one paragraph | Added separator lines |
| Gate details printed 16-digit floats | Formatted to 4 decimals |
| Executive summary said "unique" while novelty gates fail, and quoted the THVC gap as 0.045–0.05 | Now says "bytes match no registry file". Gap corrected to 0.036–0.050 (A1 seed 30 is 0.036 below) |
| "Last refresh … at None" | Reads `observed_date` |
| Markdown links rendered on Pages pointed at repository-relative paths (101 broken) | Rewritten to GitHub source URLs. `check_site` verifies that every such target file exists |
| Archiving 12 test modules dropped 245 still-valid generic tests | 6 generic modules restored to `tests/` (lifecycle, sibling audit, THVC pipeline, FNHR, novelty/artifact, site feed). 3 assertions re-pointed at the new card, site and checker |
| The submissions URL was unverified | Fetched: it redirects to the DrivenData login, as expected for an account page. The page says so |

### Merge with a moving main (IR-79-202)

Seven parallel PRs reached `main` during this session. The merge kept their work:

- **Lane pages:** the CJX and DZD pages are generated from those lanes' own cards.
- **Download checker:** the browser download-identity checker was ported into this builder.
- **Hypotheses:** session `0d90d81b`'s hypotheses are on the research page.
- **Renumbering:** this session's irregularities are renumbered to IR-79-194..201.
- **Novelty supplement:** the FSC candidate was compared with the two new TIFFs. Neither is a duplicate.
- **Deploy contract:** `verify_public_site.py`, which runs after every deploy, passes against the local preview. Its manifest and status keys were added.

## Pass 3: recheck against the request

| Requirement | Status |
|---|---|
| Generate a unique TIFF without copying a previous submission | **Met in bytes.** The file is newly generated and its SHA is not in the registry (`bytes_not_copied_from_frozen_registry`). **Not met under protocol novelty**: G4 fails, and G5 fails against positive-everywhere rasters |
| Make it obvious whether it is OK to download and submit, decided automatically | The red banner is first on the README and every page. The file name carries `-DO-NOT-SUBMIT`. `submission_status.py` exits 2. No human step |
| Values in [0, 1] and valid format | Writer and validator both pass; checks are listed on the executive summary |
| Unique name and note (≤ 140 characters) | Name 54 characters, note 115 |
| Why H33 scored 0.2778, and can we beat it | `knowledge/fsc_findings_0a202578.md` §1, with evidence classes |
| 3–5 untried hypotheses, ranked, with layers, signature, mechanism and difference | `research/hypotheses_0a202578.md` (5 ranked; data availability verified or flagged) |
| Validate on a blocked holdout before using a slot; do not spend a slot on an idea that has not beaten the best | Done. No slot used |
| Protocol: lane, shared tools, labels, canary, run card, ≤ 3 experiments, no self-selection | All followed. Budget 3/3. The selector is a separate script |
| Prompt kept in the README; executive-summary subpage; download link at the top; clean site with verified links | Done; `check_site` and the tests enforce it |
| Irregularities flagged | IR-79-194 … IR-79-201 |
| PR merged to main | See the PR in the session summary |

## Limitations and next work

1. **Owner decision D-3 (blocking).** Decide prospectively how D-2 treats registry rasters that are positive on every cell. Until then no lane can reach OK TO SUBMIT, whatever its science.
2. After D-3, run a new preregistered lane with THVC as the frozen control. The cheapest is G79-FGC (the fabric prior inside kernel-cover placement); G79-CJX, the rank-3 idea, was tested by a parallel session at the same time and came out negative (0.1041 / 0.1063), so ranks 4 and 5 are the remaining new mechanisms.
3. Reserve an untouched spatial validation partition. Repeated looks at the shared holdout inflate apparent gains.
4. Holdout ≠ leaderboard: the organizer labels new faults. Only an organizer receipt can show transfer.
5. Ranks 4 and 5 (3DEP 1 m DEM, heat-flow residuals) need network access beyond this sandbox.
