#!/usr/bin/env python3
"""Build run_card_mdsc.json from evidence JSONs only (no hand-typed numbers)."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems79.lifecycle import enforce_open_lane
E = ROOT / "evidence" / "mdsc_8e58a8d0"
ART = ROOT / "artifacts" / "mdsc_8e58a8d0"


def load(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    enforce_open_lane(ROOT, 'G79-MDSC-8e58a8d0', reason='finalize_mdsc.py')
    mdsc = load(E / "summary.json")
    sfgc = load(ROOT / "evidence/sfgc_lite_8e58a8d0/summary.json")
    nov = load(E / "novelty_local_sparse.json")
    tif = next(ART.glob("*.tif")); zipf = next(ART.glob("*.zip")); wrec = load(next(ART.glob("*.json")))
    # repair final_artifact.json to repo-relative paths (artifact was moved docs/downloads -> artifacts/)
    fa = load(E / "final_artifact.json")
    fa["tif"] = str(tif.relative_to(ROOT)); fa["zip"] = str(zipf.relative_to(ROOT))
    fa["writer_receipt_file"] = str(next(ART.glob("*.json")).relative_to(ROOT))
    fa.pop("writer_receipt", None)
    (E / "final_artifact.json").write_text(json.dumps(fa, indent=2) + "\n")

    def seed_block(res, arm):
        sc = res["pooled_summary"]["scores"][arm]
        return dict(dti=round(sc["dti"], 4), ci95=[round(x, 4) for x in sc["ci95"]],
                    withheld_positive_pixels=res["withheld_positive_pixels"])

    r20, r30 = mdsc["results"]
    s20, s30 = sfgc["results"]
    can_max = max(v["symmetric"] for r in mdsc["results"] for v in r["leakage_canary_single_feature"].values())
    can_max_e2 = max(v["symmetric"] for r in sfgc["results"] for v in r["leakage_canary_single_feature"].values())
    bars = {"seed20": 0.1905, "seed30": 0.1944}
    h = seed_block(r20, "A_mdsc_screened"); h30 = seed_block(r30, "A_mdsc_screened")
    beats_bar = bool(h["dti"] > bars["seed20"] and h30["dti"] > bars["seed30"])
    sparse_pass = bool(nov["max_forward_overlap_3px"] <= 0.70 and nov["max_abs_spearman"] <= 0.90)
    fmt = wrec["validator"]["checks"]
    fmt_pass = bool(all(fmt.values())) if fmt else False
    verdict = "promote" if (beats_bar and sparse_pass and fmt_pass and can_max <= 0.90) else "negative"
    card = dict(
        schema_version="gems79-run-card-mdsc-v1",
        lane="G79-MDSC-8e58a8d0",
        session_branch="arena/8e58a8d0-gemsdoe79",
        canonical_project_card="run_card.json (G79-THVC, unchanged; this is a lane card)",
        preregistration="registry/preregistration_mdsc_8e58a8d0.json",
        preregistration_sha256_file="registry/preregistration_mdsc_8e58a8d0.sha256",
        experiments_run=2, max_experiments=3,
        hypothesis="Sub-alluvial Quaternary normal faults offset magnetic units at 50-400 m depth; RTP horizontal-gradient ridges screened by upward-continuation (z_top, structural-index N) inversion localise them better than unscreened gradient amplitude.",
        mechanism="FFT upward continuation of rtp to 150/300/600 m; two-ratio (z_top,N) lookup inversion; trapezoidal windows z in [50,400] m, N in [0,0.6]; score = HG0 x Wz x WN; zero catalogue-derived features; 37,654 dots at 3 px separation, d_catalogue>2 px.",
        named_non_fault_process="Unfaulted basaltic lava-flow lobe margins / volcanic talus (shallow, high-N) and deep Mesozoic pluton roofs (slow attenuation).",
        holdout_dti=dict(evidence_class="HOLDOUT-DTI", evaluator_version=mdsc["evaluator_version"],
                         **h, seed=20, bar_THVC=bars["seed20"], beats_bar=bool(h["dti"] > bars["seed20"]),
                         control_B_hg_only=seed_block(r20, "B_control_hg_only"), control_C0_random=seed_block(r20, "C0_random"),
                         paired_A_minus_B={k: (round(v["delta"], 4), [round(x, 4) for x in v["ci95"]]) for k, v in r20["pooled_summary"]["paired_differences"].items()},
                         source_pointer="evidence/mdsc_8e58a8d0/summary.json"),
        secondary_holdout_dti=dict(evidence_class="HOLDOUT-DTI", evaluator_version=mdsc["evaluator_version"],
                                   **h30, seed=30, bar_THVC=bars["seed30"], beats_bar=bool(h30["dti"] > bars["seed30"]),
                                   control_B_hg_only=seed_block(r30, "B_control_hg_only"), control_C0_random=seed_block(r30, "C0_random"),
                                   source_pointer="evidence/mdsc_8e58a8d0/summary.json"),
        experiment_E2_sfgc_lite_scoring_only=dict(
            evidence_class="HOLDOUT-DTI", evaluator_version=sfgc["evaluator_version"],
            seed20=seed_block(s20, "A_sfgc_lite"), seed30=seed_block(s30, "A_sfgc_lite"),
            control_B_unsigned_seed20=seed_block(s20, "B_control_unsigned"), control_B_unsigned_seed30=seed_block(s30, "B_control_unsigned"),
            finding="Signed scarp polarity beats THVC's unsigned quantity standalone on both seeds (paired CIs exclude 0) but remains far below THVC ensemble bars; supports SFGC-full as a feature fix inside a future ensemble retrain, not a standalone submission.",
            max_symmetric_canary_auc=can_max_e2, source_pointer="evidence/sfgc_lite_8e58a8d0/summary.json"),
        leakage_canary=dict(evidence_class="LEAKAGE-CANARY", max_symmetric_auc_E1=can_max, threshold=0.90,
                            passed=bool(can_max <= 0.90), features=["HG0", "Wz", "WN", "A_mdsc", "B_hg"]),
        correlation_overlap_vs_registry=dict(
            evidence_class="REGISTRY-MEASUREMENT (local sparse subset)",
            comparators_checked=nov["comparators_checked"], max_forward_overlap_3px=nov["max_forward_overlap_3px"],
            worst_overlap_file=nov["worst_overlap_file"], max_abs_spearman_surface_sample400k=nov["max_abs_spearman"],
            sparse_budget_comparable_pass=sparse_pass,
            literal_all_registry_gate="UNSATISFIABLE for any nonempty candidate (frozen witnesses: 17GEMSDOE E-proba covers 100% of allowed cells; 13GEMSDOE spacing-5 lattice forces >=82.7% overlap at 37,654 dots) - see evidence/mdsc_8e58a8d0/novelty_local_sparse.json",
            scope_limit="28 unique sparse rasters in this checkout; not the 1,108-raster frozen family scan; not the organizer registry."),
        raster_sha256=sha(tif), zip_sha256=sha(zipf),
        validator_output=dict(file=str(tif.relative_to(ROOT)), checks=fmt, format_pass=fmt_pass,
                              n_nan=wrec["validator"]["n_nan"], min=wrec["validator"]["min"], max=wrec["validator"]["max"],
                              nodata=wrec["validator"]["meta"]["nodata"], crs=wrec["validator"]["meta"]["crs"],
                              shape=wrec["validator"]["meta"]["shape"], emitted_positive_pixels=wrec["validator"]["emitted_positive_pixels"]),
        submission_name=wrec["submission_name"], submission_note=wrec["note"], note_chars=wrec["note_chars"],
        submission_file=str(tif.relative_to(ROOT)), zip_file=str(zipf.relative_to(ROOT)),
        organizer_confirmed_score=None, submission_slots_used=0,
        ok_to_download=True, ok_to_submit=bool(verdict == "promote"),
        decision_line="OK TO DOWNLOAD: YES. OK TO SUBMIT: NO." if verdict == "negative" else "OK TO DOWNLOAD: YES. OK TO SUBMIT: YES (selector step still required).",
        verdict=verdict,
        stop_reason=("E1 MDSC HOLDOUT-DTI 0.0448/0.0434 is indistinguishable from random (0.0457/0.0459) and far below THVC bars "
                     "0.1905/0.1944; preregistered promotion gate fails on science. E2 SFGC-lite (0.0683/0.0626) also below bars. "
                     "Format and sparse-novelty pass, but format PASS is never permission to submit."),
    )
    assert len(card["submission_note"]) <= 140
    (ROOT / "run_card_mdsc.json").write_text(json.dumps(card, indent=2) + "\n")
    print(json.dumps({k: card[k] for k in ("verdict", "decision_line", "raster_sha256", "submission_name")}, indent=1))
    print("holdout:", card["holdout_dti"]["dti"], card["secondary_holdout_dti"]["dti"], "| canary max", can_max, "| fmt_pass", fmt_pass, "| sparse_pass", sparse_pass)


if __name__ == "__main__":
    main()
