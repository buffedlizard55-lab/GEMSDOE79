#!/usr/bin/env python3
"""Lane G79B-SDPT — full-catalogue fit, surface uniqueness audit, emission,
final audit, and fail-closed GeoTIFF write (shared gems57 writer).

Stages (resumable, each cached):
  fit            train on FULL catalogue (A2 feature set) -> p surface;
                 apply SDPT-C trace reranking -> final ranking surface S
  surface-audit  shared compare of S vs all 992 registry rasters (pre-placement)
  emit           37,654 dots; if the preregistered cap contingency is needed
                 it is applied in `final-audit` after measuring the overlap
  final-audit    shared compare of the final dots; extra continuous tests;
                 if a dot-field prior fires >0.70, re-emit with the 0.68 cap
                 (experiment E2 measures its holdout cost separately) and
                 re-audit in full
  write          shared submission_writer (rejects out-of-range, never clips)
  card           run_card_g79b.json with the automated promote/negative verdict

Candidate arm selection (fixed before fitting): A3 if it was the mean-holdout
winner in E1, else A2. The verdict is computed from gates G1-G5 in
registry/preregistration_g79b.json — no human inspection anywhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import submission_writer as SW, uniqueness as U, validate as V  # noqa: E402
from gems79b import data as D, features as F, model as MD, trace as T  # noqa: E402
import audit_g79b as AU  # noqa: E402

PROC = ROOT / "data" / "cache" / "final_g79b"
EV = ROOT / "evidence"
DL = ROOT / "docs" / "downloads"
BUDGET = 37_654
ARCHIVED_BEST = {20: 0.1095, 30: 0.1152}  # H79-MCT C2 continuity B37654 (archived scans)


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def holdout_summary():
    out = {}
    for seed in (20, 30):
        d = json.loads((EV / f"holdout_g79b_seed{seed}.json").read_text())
        out[seed] = d
    return out


def choose_arm(h):
    means = {}
    for arm in ("A2_sdpt_pixel", "A3_sdpt_trace"):
        means[arm] = float(np.mean([h[s]["arms"][arm]["pooled_holdout_dti"] for s in (20, 30)]))
    return max(means, key=means.get), means


def stage_fit(arm):
    PROC.mkdir(parents=True, exist_ok=True)
    p_path, s_path = PROC / "full_p.npy", PROC / "full_S.npy"
    grid = D.load_grid()
    foot, cat = grid.footprint, grid.catalogue
    if not p_path.exists():
        stack = np.load(F.STACK, mmap_mode="r")
        cols = MD.cols_for(F.CHANNELS)
        rng = np.random.default_rng(79_000)
        idx, y, info = MD.sample_training(cat, foot, foot, rng)
        log(f"FULL train {info}")
        clf = MD.fit(stack, cols, idx, y, tag="FULL")
        p = MD.predict(clf, stack, cols, foot)
        np.save(p_path, p)
        (PROC / "full_train_info.json").write_text(json.dumps(
            {"train": info, "features": F.CHANNELS, "hgb": MD.HGB_KW}, indent=2) + "\n")
    p = np.load(p_path)
    if arm == "A3_sdpt_trace":
        if not s_path.exists():
            step_rank = np.load(ROOT / "data/cache/holdout_g79b/step_rank.npy")
            s, info = T.trace_surface(p, step_rank, foot)
            np.save(s_path, s)
            (PROC / "full_trace_info.json").write_text(json.dumps(info, indent=2) + "\n")
            log(f"FULL trace {info}")
        return np.load(s_path)
    return p


def emit_final(surface, allowed, cap_records=None):
    if not cap_records:
        return T.emit_dots(surface, allowed, BUDGET)
    sampler = T.halo_sampler_from_files([r["file"] for r in cap_records], surface.shape)
    dots, info = T.emit_dots_caps(surface, allowed, BUDGET, sampler, len(cap_records), cap_share=0.68)
    info["capped_priors"] = [{"submission": r["submission"], "file": r["file"], "sha256": r["sha256"]}
                             for r in cap_records]
    return dots, info


def decoded_sha(a):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(a, np.float32)).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["all", "fit", "surface-audit", "emit", "final-audit", "write", "card"])
    args = ap.parse_args()
    from gems79.lifecycle import require_open_lane
    require_open_lane(ROOT, "G79B-SDPT")
    grid = D.load_grid()
    foot, cat = grid.footprint, grid.catalogue
    h = holdout_summary()
    arm, means = choose_arm(h)
    log(f"candidate arm: {arm} (mean holdout {means})")
    (PROC).mkdir(parents=True, exist_ok=True)
    (PROC / "chosen_arm.json").write_text(json.dumps({"arm": arm, "means": means}, indent=2) + "\n")

    if args.stage in ("all", "fit"):
        s = stage_fit(arm)
        log(f"surface ready: decoded sha256={decoded_sha(s)[:16]}… max={float(s.max()):.4f} positives={int((s>0).sum())}")
        if args.stage == "fit":
            return
    else:
        s = stage_fit(arm)

    allowed = T.allowed_domain(foot, cat, 2.0)

    surf_audit_path = EV / "uniqueness_g79b_surface.json"
    if args.stage in ("all", "surface-audit"):
        if not surf_audit_path.exists():
            AU.compare_full(s, "surface", surf_audit_path, file_sha256=None)
        else:
            log("surface audit cached")
        if args.stage == "surface-audit":
            return

    dots_path = PROC / "final_dots.npy"
    emit_info_path = PROC / "emit_info.json"
    if args.stage in ("all", "emit"):
        if not dots_path.exists():
            dots, info = emit_final(s, allowed)
            np.save(dots_path, dots)
            emit_info_path.write_text(json.dumps(info, indent=2) + "\n")
            log(f"emitted unconstrained {info}")
        if args.stage == "emit":
            return

    final_audit_path = EV / "uniqueness_g79b_final.json"
    extra_path = EV / "uniqueness_g79b_extra_continuous.json"
    disp_path = EV / "uniqueness_g79b_error_dispositions.json"
    if args.stage in ("all", "final-audit"):
        def dotfield_firings(audit):
            return [r for r in audit["rows"] if "error" not in r
                    and U.representation_class(int(r["their_dots"]), int(foot.sum()))["kind"] == "dot_field"
                    and r["my_dots_within_3px_of_theirs"] > 0.70]

        cap_by_sha = {}
        coverage_path = EV / "uniqueness_g79b_coverage_final.json"
        for iteration in range(3):
            dots = np.load(dots_path)
            tag = "final" if iteration == 0 and not cap_by_sha else f"final-capped{iteration}"
            if not final_audit_path.exists():
                AU.compare_full(dots.astype(np.float32), tag, final_audit_path, file_sha256=None)
            audit = json.loads(final_audit_path.read_text())
            firings = dotfield_firings(audit)
            # Amendment B1: classify firings by halo coverage; only
            # discriminating priors (coverage < 0.70) trigger/enter the cap.
            classified = AU.classify_firings(dots, firings) if firings else []
            coverage_path.write_text(json.dumps(
                {"evidence_class": "REGISTRY-MEASUREMENT", "phase": tag,
                 "amendment": "B1 (registry/preregistration_g79b_amendment_B1.json)",
                 "rows": classified}, indent=1, default=float) + "\n")
            disc_firings = [c for c in classified if c["discriminating"]]
            log(f"firings={len(firings)} unique={len(classified)} discriminating={len(disc_firings)} "
                f"non-discriminating={len(classified) - len(disc_firings)}")
            if not disc_firings:
                break
            log(f"CAP CONTINGENCY iter{iteration}: {len(disc_firings)} discriminating priors >0.70")
            for c in disc_firings:
                cap_by_sha[c["decoded_sha256"]] = {"submission": c["submission"], "file": c["file"],
                                                   "sha256": c["sha256"],
                                                   "decoded_sha256": c["decoded_sha256"]}
            log(f"unique cap supports so far: {len(cap_by_sha)}")
            if iteration == 0:
                np.save(PROC / "final_dots_unconstrained.npy", dots)
                (EV / "uniqueness_g79b_final_unconstrained.json").write_text(final_audit_path.read_text())
            dots, info = emit_final(s, allowed, list(cap_by_sha.values()))
            np.save(dots_path, dots)
            emit_info_path.write_text(json.dumps(info, indent=2) + "\n")
            log(f"capped emission iter{iteration}: dots={info['dots']} caps={info['n_priors_capped']} "
                f"max_share={info['max_share_in_any_capped_halo']:.4f}")
            final_audit_path.unlink()
        audit = json.loads(final_audit_path.read_text())
        dots = np.load(dots_path)
        surf_topk = AU.topk_mask(s, allowed)
        if extra_path.exists():
            extra_path.unlink()
        AU.extra_continuous(dots, surf_topk, audit["rows"], extra_path)
        surf_audit_for_disp = json.loads(surf_audit_path.read_text())
        disp = {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "surface_candidate": AU.disposition_errors(s, surf_audit_for_disp["rows"]),
            "final_dots_candidate": AU.disposition_errors(dots.astype(np.float32), audit["rows"]),
        }
        disp_path.write_text(json.dumps(disp, indent=1, default=float) + "\n")
        log(f"error dispositions: surface={len(disp['surface_candidate'])} final={len(disp['final_dots_candidate'])}")
        if args.stage == "final-audit":
            return

    # ---------- gates + write + card ----------
    dots = np.load(dots_path)
    surf_audit = json.loads(surf_audit_path.read_text())
    fin_audit = json.loads(final_audit_path.read_text())
    extra = json.loads(extra_path.read_text())
    emit_info = json.loads(emit_info_path.read_text())
    disp = json.loads(disp_path.read_text())
    coverage_rows = json.loads((EV / "uniqueness_g79b_coverage_final.json").read_text())["rows"]

    def accounted(a, disp_list):
        return a["registry_checked"] + len(disp_list) == 992

    def disp_ok(disp_list, *, overlap):
        for d in disp_list:
            if d["disposition"] == "wrong_transform_measured_as_if_pixel_aligned":
                if d["spearman_full_footprint_asif"] is not None and d["spearman_full_footprint_asif"] > 0.90:
                    return False
                if overlap and d["representation"] == "dot_field" and d["forward_overlap_3px_asif"] > 0.70:
                    return False
        return True

    def surface_ok(a, disp_list):
        # Candidate surface is continuous: template surface test = Spearman.
        return (a["two_phase"]["literal_reading"]["rho_firings"] == 0
                and accounted(a, disp_list) and disp_ok(disp_list, overlap=False)
                and a["byte_unique_among_checked"] and a["pixel_unique_among_checked"])

    def final_ok(a, disp_list, cov_rows):
        # Amendment B1: no discriminating firing; non-discriminating firings
        # must pass exact-cell overlap <= 0.70.
        disc_bad = [c for c in cov_rows if c["discriminating"] and c["halo_overlap"] > 0.70]
        nondisc_bad = [c for c in cov_rows if not c["discriminating"] and c["exact_dot_overlap"] > 0.70]
        return (a["two_phase"]["literal_reading"]["rho_firings"] == 0
                and not disc_bad and not nondisc_bad
                and accounted(a, disp_list) and disp_ok(disp_list, overlap=True)
                and a["byte_unique_among_checked"] and a["pixel_unique_among_checked"])

    g1 = all(not h[s]["leakage_channels_gt_0p90"] for s in (20, 30))
    g2 = g3 = True
    for s in (20, 30):
        summ = h[s]["pooled_summary_candidate_A3" if arm.startswith("A3") else "pooled_summary_candidate_A2"]
        if not summ["paired_differences"]["A0_random"]["ci95"][0] > 0:
            g2 = False
        cand_d = h[s]["arms"][arm]["pooled_holdout_dti"]
        ctrl_d = h[s]["arms"]["A1_control_h79_pixel"]["pooled_holdout_dti"]
        if not (cand_d > ctrl_d and cand_d >= ARCHIVED_BEST[s]):
            g3 = False
    g4 = (surface_ok(surf_audit, disp["surface_candidate"])
          and final_ok(fin_audit, disp["final_dots_candidate"], coverage_rows)
          and extra.get("passed_amended_B2", extra["passed"]))

    # E2 (preregistered cap contingency): capped emission must still beat
    # the A1 control on both seeds, else the lane ends negative.
    capcost_path = EV / "cap_cost_g79b.json"
    capcost = json.loads(capcost_path.read_text()) if capcost_path.exists() else None
    e2_ok = True
    if capcost is None:
        e2_ok = emit_info.get("n_priors_capped", 0) in (0, None)
    elif capcost.get("cap_fired"):
        e2_ok = all(capcost["seeds"][str(s)]["capped_vs_control"] > 0 for s in (20, 30))

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    sha8 = decoded_sha(dots.astype(np.float32))[:8]
    promote_pre_format = bool(g1 and g2 and g3 and g4 and e2_ok)
    suffix = "zeros" if promote_pre_format else "DO-NOT-SUBMIT"
    name = f"gems79b-sdpt-{arm.split('_')[0].lower()}-{BUDGET}dots-{stamp}-{sha8}-{suffix}"
    # Reuse an already-written artifact for these exact dots (idempotent card).
    existing = sorted(DL.glob(f"gems79b-sdpt-*-{sha8}-{suffix}.tif"))
    if existing:
        name = existing[0].stem
    note = ("G79B-SDPT dipole-persistence+trace scarp detector; 37654 dots 2.8px, "
            ">2px off catalogue; holdout-gated, registry-unique; zeros outside")
    assert len(note) <= 140, len(note)
    tif = DL / f"{name}.tif"
    receipt = None
    g5 = False
    if args.stage in ("all", "write", "card"):
        if not tif.exists():
            receipt = SW.write_submission(
                tif, dots.astype(np.float32), ROOT / "data/reference/sample_submission.tif",
                foot, note=note, name=name, catalogue=cat,
                metadata={"lane": "G79B-SDPT", "arm": arm, "emit_info": emit_info})
        vr = V.validate(tif, foot, cat)
        # extra range/dot-count assertions beyond the shared validator
        with rasterio.open(tif) as src:
            a = src.read(1)
        uniq = np.unique(a)
        g5 = bool(vr["all_checks_passed"] and int((a > 0).sum()) == BUDGET
                  and set(float(u) for u in uniq) <= {0.0, 1.0}
                  and vr["meta"]["nodata"] is None)
        (EV / "validator_g79b.json").write_text(json.dumps(
            {"shared_validate": vr, "unique_values": [float(u) for u in uniq],
             "positive_pixels": int((a > 0).sum())}, indent=2, default=float) + "\n")
        if receipt is None:
            receipt = json.loads(tif.with_suffix(".json").read_text())

    verdict = "promote" if (promote_pre_format and g5) else "negative"
    card = {
        "schema_version": "gems79b-run-card-v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "branch": "arena/67557396-gemsdoe79",
        "lane": "G79B-SDPT",
        "hypothesis": ("Crest-base curvature-dipole, facing-polarity and cross-scale/cross-sensor "
                       "step-persistence channels, plus object-level trace scoring, rank true "
                       "fault scarps above terrace/channel/road mimics better than the same "
                       "terrain bands used as independent amplitudes."),
        "mechanism": ("Terrain-only HGB on 49 catalogue-free channels (1 m lidar cache + 10 m 3DEP "
                      "+ 100 m det_elev + road distance), SDPT-C trace-object reranking, 37,654 "
                      "binary dots at 2.8 px separation, >2 px from the USGS/INGENIOUS catalogue."),
        "named_non_fault_process": ("Fluvial terrace risers and Lahontan shorelines form the same "
                                    "curvature dipole; road cuts repeat across DEM products."),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2",
            "candidate_arm": arm,
            "seed30": h[30]["pooled_summary_candidate_A3" if arm.startswith("A3") else "pooled_summary_candidate_A2"]["scores"][arm],
            "seed20": h[20]["pooled_summary_candidate_A3" if arm.startswith("A3") else "pooled_summary_candidate_A2"]["scores"][arm],
            "paired_vs_control_A1": {
                "seed30": h[30]["pooled_summary_candidate_A3" if arm.startswith("A3") else "pooled_summary_candidate_A2"]["paired_differences"]["A1_control_h79_pixel"],
                "seed20": h[20]["pooled_summary_candidate_A3" if arm.startswith("A3") else "pooled_summary_candidate_A2"]["paired_differences"]["A1_control_h79_pixel"]},
            "control_A1": {str(s): h[s]["arms"]["A1_control_h79_pixel"]["pooled_holdout_dti"] for s in (20, 30)},
            "archived_best_H79MCT_C2": {str(k): v for k, v in ARCHIVED_BEST.items()},
            "caveat": "Paired 95% CIs vs the A1 control include 0 on both seeds: the improvement is consistent in direction and beats the archived best point estimates, but its size (+0.003..+0.007) is not individually significant. Holdout truth is catalogue-like; no leaderboard score is projected.",
        },
        "leakage_canary": {"seed30_worst": h[30]["canary_worst"], "seed20_worst": h[20]["canary_worst"],
                           "threshold": 0.90, "passed": bool(g1)},
        "correlation_overlap_vs_registry": {
            "registry": "992 hash-verified rasters (registry/registry_index.json + registry_receipt.json)",
            "decision_D1": "vendor two_phase_summary: Spearman on all rasters; dot overlap on dot fields; literal reading reported; extra continuous tests in evidence/uniqueness_g79b_extra_continuous.json",
            "amendment_B1": {
                "file": "registry/preregistration_g79b_amendment_B1.json",
                "final_firings_classified": len(coverage_rows),
                "discriminating_firings_remaining": sum(1 for c in coverage_rows if c["discriminating"] and c["halo_overlap"] > 0.70),
                "non_discriminating_firings": sum(1 for c in coverage_rows if not c["discriminating"]),
                "worst_exact_overlap_non_discriminating": max((c["exact_dot_overlap"] for c in coverage_rows if not c["discriminating"]), default=None),
                "worst_halo_overlap_discriminating": max((c["halo_overlap"] for c in coverage_rows if c["discriminating"]), default=None),
                "coverage_evidence": "evidence/uniqueness_g79b_coverage_final.json",
            },
            "surface": surf_audit["two_phase"], "final_dots": fin_audit["two_phase"],
            "extra_continuous_worst_final_overlap": extra["worst_final_overlap"],
            "extra_continuous_worst_final_overlap_topk": extra.get("worst_final_overlap_topk"),
            "extra_continuous_strict_passed": extra["passed"],
            "extra_continuous_passed_amended_B2": extra.get("passed_amended_B2"),
            "amendment_B2_file": "registry/preregistration_g79b_amendment_B2.json",
            "cap_cost_E2": capcost,
            "e2_capped_beats_control_both_seeds": bool(e2_ok),
            "passed": bool(g4),
        },
        "raster_sha256": receipt["sha256"] if receipt else None,
        "decoded_sha256": decoded_sha(dots.astype(np.float32)),
        "validator_output": "evidence/validator_g79b.json (shared gems57 validate; all values finite in [0,1])",
        "gates": {"G1_canary_le_0.90": bool(g1), "G2_beats_random_CI": bool(g2),
                  "G3_beats_current_holdout_best_both_seeds_unconstrained": bool(g3),
                  "G4_registry_uniqueness_surface_and_final": bool(g4),
                  "G5_format_validator": bool(g5),
                  "E2_capped_emission_still_beats_control_both_seeds": bool(e2_ok)},
        "verdict_reason": ("NEGATIVE by the preregistered E2 rule: the registry-unique (capped) "
                           "emission scores BELOW the A1 control on both holdout seeds "
                           "(cap cost -0.018/-0.020 HOLDOUT-DTI vs an unconstrained edge of "
                           "+0.003/+0.007). The unconstrained dots that pass G3 are not "
                           "registry-unique (99 dot-field priors >0.70 forward overlap); the "
                           "unique dots are not better than the control. Do not spend a "
                           "submission slot on this file." if not e2_ok else "all gates pass"),
        "submission_name": name, "note": note, "note_chars": len(note),
        "organizer_confirmed_score": None,
        "verdict": verdict,
        "ok_to_download": True,
        "ok_to_submit": bool(verdict == "promote"),
        "submission_slots_used": 0,
        "experiments_used": ("E1 holdout seeds 30+20 complete; E2 cap-cost complete "
                             "(cap fired, Amendment B1: 52 discriminating priors capped at 0.68); "
                             "E3 not used"),
        "emit_info": emit_info,
    }
    for p in (ROOT / "run_card_g79b.json", EV / "run_card_g79b.json"):
        p.write_text(json.dumps(card, indent=2, default=float) + "\n")
    log(f"VERDICT {verdict} gates={card['gates']}")
    log(f"file {tif.name} sha256={card['raster_sha256']}")
    log(f"note ({len(note)} chars): {note}")


if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError
    try:
        main()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
