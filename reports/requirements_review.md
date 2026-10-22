# Final brief-to-evidence review

Reviewed against the full original prompt in README on **2026-10-21**. A valid
negative result does not satisfy the stronger request for a protocol-unique,
scientifically validated competition submission. We do not hide that distinction.

| Requirement | Status | Evidence / unresolved boundary |
|---|---|---|
| Review repository and continue previous work | Done | Initial checkout had only an 11-byte README. Reused accessible sibling data/code/history; integrated concurrently merged main preflight code/tests/briefs and quarantined concurrent lanes `H79-MCT` (`archive/h79_mct_c26efec/`) and `H79-CSPT` (`archive/h79_cspt_464d591/`) without a scientific lane switch (`evidence/concurrent_lanes_audit.json`). |
| Keep original prompt in README and read each session | Done | Complete brief under expandable section; only trailing whitespace normalized. `AGENTS.md` requires the read. |
| Propose 3–5 ranked geological hypotheses before implementation | Done | Four in `research/hypotheses.md` / immutable `registry/preregistration.json`; exact layers, physical signatures, catalogue-missing rationale, differences, qualitative priority/cost and named mimics. No projected scores. |
| Stay in one lane, ≤3 experiments / ≤2 h | Done for science | One fixed fabric-offset surface. Stopped on literal duplicate; zero canaries/holdouts/placements. Subsequent software/reporting/cold-byte recovery is not more geological experimentation. |
| Reuse cached features and shared evaluator/writer | Done with disclosed compatibility limit | Restored 19-band numerical GeoTIFF; unavailable historical 54-channel cache not reconstructed. Twenty-three shared modules unchanged and hash-pinned. |
| Recover obtainable data autonomously | Done for all 13 manifest inputs | All 13 real mirror inputs (`training_features.tif`, `labels.tif`, `existing_faults.tif`, `sample_submission.tif`, and 9 external files) checked by SHA-256 via `scripts/restore_data.py --preserve-receipt`; 992 prior blobs with SHA-256/Git-blob/size receipts. Login was not used as an excuse to abandon recovery. |
| Official/free third-party sources and audit table | Done with access limits | Official claim ledger, data manifest, source page, USGS/GDR/project listings and full primary-paper review. New official binary downloads / independent organizer-origin identity are not claimed where unavailable. |
| Study why H33 reportedly performed well | Done as forensic/metric analysis | Exact D2.8 subset/prune counts, maximum-cover metric mechanism, confounders, no causal score proof. Reported 0.2778 remains unverified; official public 0.4413 observation does not identify an uploaded H33 file. |
| New downloadable TIFF, not a copied prior | Done for research artifact | Newly computed field, new hash not equal to any of 992 registry hashes. Writer/ZIP/reopened validation and actual browser download verified. |
| Genuinely protocol-unique competition candidate | **BLOCKED / NOT DELIVERED** | Universal positive-support witness forces 100% overlap >70%. Byte distinction is not protocol novelty. No exemption, jitter, renamed old submission or second lane. |
| Single-band float32, [0,1], finite footprint, exact CRS/shape/transform | Done locally | Shared writer/validators and `verify_project.py`; EPSG:32611, 3730×3292, exact reference transform/bounds, finite everywhere, zero outside footprint/on catalogue. No claim of remote acceptance. |
| Diagnose earlier portal range failure | Limited | Rejected original bytes and server receipt absent. New numerical checks prevent the local hazard; cause of the original failure is not proven. |
| Canary every feature and trust no AUC >0.90 | **STOPPED PRE-PLACEMENT in official run; post-stop diagnostic measured** | Official `run_card.json` keeps `leakage_canary.auc = null` because E1 stopped pre-placement. Post-stop diagnostic (`evidence/post_stop_diagnostic.json`) verified 72/72 feature-fold tests pass (`max_symmetric_auc = 0.5872` on seed 20, `0.6162` on seed 30, both `<= 0.90`). |
| Buffered whole-segment hide-and-recover, pooled metric/CI, beat current best | **STOPPED PRE-PLACEMENT in official run; post-stop diagnostic negative** | Official `run_card.json` keeps `holdout_dti.dti = null`. Post-stop diagnostic (`evidence/post_stop_diagnostic.json`, `gems57-pooled-hide-v2`) proves E1 scores `0.0474 [0.0390, 0.0552]` on seed 20 (`n=11,321`) and `0.0466 [0.0388, 0.0543]` on seed 30 (`n=11,342`), failing both the matched zero-lag edge control gate and `h33_foldfair_control` (`0.0961` / `0.0989`). |
| Train a model and improve leaderboard score | **NOT ESTABLISHED** | Fixed physical transforms computed without fitting labels; no neural-network training or leaderboard gain after mandatory stop. |
| Automated OK TO DOWNLOAD / OK TO SUBMIT | Done | Status CLI and main/executive pages: download YES / submit NO. No human inspector is asked to approve this rejected file. Format alone cannot promote. |
| Unique name and ≤140-character note | Done | Identity/receipt/card and copy buttons; deliberate `DO-NOT-SUBMIT` suffix and 108-character note. |
| Executive-summary subpage and obvious top download | Done | Main hero, status, TIFF/ZIP buttons; executive page separates current prohibition from exact future approved-file submission steps. |
| Modern clean website and current source/feed auditing | Done locally; deployment recorded separately | Seven self-contained pages, actual field preview, 103 local-link checks, 21 real-browser viewport cases, source health with dates/errors and no stale-as-fresh labels. Daily workflow does not fabricate receipts. |
| Label performance and flag irregularities | Done | No measured E1 performance. Historical reports/public observations retain evidence classes; `reports/irregularities.md` documents conflicts and dispositions. |
| No upload/slot selection | Done | Zero competition uploads and zero slots; separate selector/capacity evidence required, never inferred from public rules. |
| One JSON run card ending the run | Done | `run_card.json` and `evidence/run_card.json` identical; hypothesis/mechanism/mimic, null unmeasured results, actual comparison, SHA/validator/name/note and negative verdict. |
| Three review passes, PR then merge to main | In release verification | `reports/verification_passes.md` contains actual local review and is updated with observed PR/check/merge/Pages outcomes; no pending action is called successful. |
| Limitations and next session | Done | README, executive page, run card, knowledge and reports: resolve protocol first; authenticate source/account/receipts through authorized workflow; only then consider a new preregistered lane, canaries and matched holdout. |

## Review coverage and honesty

This is an engineering/scientific acceptance review, not a formal proof of every
line in all inherited code or every external web page. Core shared metric
arithmetic is checked against its brute-force oracle. Actual serialized bytes,
source pins, status, all local links and rendered interactions are tested.
Official claims are attributed to the specific pages/sections actually read;
HTTP reachability does not count as scientific re-verification. Inaccessible
account state, hidden truth, unrun performance and scientific impossibility are
left explicit rather than guessed.
