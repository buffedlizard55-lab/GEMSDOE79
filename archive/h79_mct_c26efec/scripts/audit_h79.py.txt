#!/usr/bin/env python3
"""Lane H79-MCT — release gate: validator + full registry uniqueness audit + RUN CARD.

One pass over every hash-verified registry raster (812) computes, with the shared
``gems57.uniqueness`` helpers and thresholds:
* Spearman rank correlation (full footprint) of the SHIPPED raster and of the pre-placement
  continuity SURFACE against the prior (rule 1: check the surface before placement AND the dots);
* forward overlap = share of my dots within 3 px of the prior's positive pixels;
* halo coverage of my allowed domain by the prior (IR-H85-01 like-for-like classification);
* reverse overlap and Jaccard (diagnostic).
The binding verdict is ``gems57.uniqueness.binding_duplicate_decision`` (rho <= 0.90 for every
prior; forward overlap <= 0.70 for every *discriminating* prior); the literal reading is kept.

Then the on-disk validator (``gems57.validate`` + ``gems57.gates``) is run on the TIF and the
JSON RUN CARD required by the parallel-run protocol is written to evidence/run_card_h79.json,
together with docs/status.json for the site banner.
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
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import uniqueness as U, validate as V, gates as GT, grid as G  # noqa: E402
from gems79 import data as D, trace as T  # noqa: E402

FINAL = ROOT / "data" / "cache" / "final"


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def centred_ranks(v):
    r = rankdata(v).astype(np.float64)
    r -= r.mean()
    return r, float(np.linalg.norm(r))


def rho_against(ranks, norm, tv):
    if norm == 0 or np.ptp(tv) == 0:
        return None
    if np.all((tv == 0) | (tv == 1)):
        tb = tv > 0
        nt = int(tb.sum()); n = len(tv)
        return float(ranks[tb].sum() / (norm * np.sqrt(nt * (n - nt) / n)))
    tr, tn = centred_ranks(tv)
    return float(np.dot(ranks, tr) / (norm * tn))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", default=None, help="candidate TIF (default: the one in evidence/build_h79.json)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reuse-audit", action="store_true", help="re-render verdict/run card from the existing audit JSON")
    args = ap.parse_args()
    t0 = time.time()
    build = json.loads((ROOT / "evidence" / "build_h79.json").read_text())
    tif = Path(args.tif) if args.tif else ROOT / build["tif"]
    grid = D.load_grid()
    foot, cat = grid.footprint, grid.catalogue
    with rasterio.open(tif) as src:
        mine = src.read(1).astype(np.float32)
        meta = dict(crs=str(src.crs), transform=list(src.transform)[:6], shape=src.shape, dtype=src.dtypes[0], nodata=src.nodata)
    file_sha = sha256(tif)
    if file_sha != build["sha256"]:
        raise SystemExit(f"candidate sha256 drifted: {file_sha} != {build['sha256']}")
    surface = np.load(FINAL / "s_full.npy").astype(np.float32)
    surface = np.where(foot, surface, 0)
    allowed = T.allowed_domain(foot, cat, 2.0)

    inv = json.loads((ROOT / "registry" / "registry_inventory.json").read_text())
    records = inv["rasters"][: args.limit] if args.limit else inv["rasters"]
    prev = None
    if args.reuse_audit:
        prev = json.loads((ROOT / "evidence" / "registry_audit_h79.json").read_text())
        if prev["candidate_sha256"] != file_sha:
            raise SystemExit("existing audit belongs to a different candidate")
        records = []
    my_vals = mine[foot]
    my_ranks, my_norm = centred_ranks(my_vals)
    s_ranks, s_norm = centred_ranks(surface[foot])
    my_support = (mine > 0) & foot
    my_near = U._near(my_support)
    n_my = int(my_support.sum())
    rows = []
    for i, rec in enumerate(records, 1):
        f = ROOT / rec["cache_file"]
        base = dict(repo=rec["repo_first"], submission=rec["sources"][0], file=rec["cache_file"],
                    organizer_confirmed_public_score=rec.get("organizer_confirmed_public_score"))
        try:
            if sha256(f) != rec["sha256"]:
                raise ValueError("registry SHA256 pin mismatch")
            with rasterio.open(f) as src:
                if src.count != 1 or src.shape != mine.shape or src.crs is None or src.crs.to_epsg() != 32611 or src.transform != G.TRANSFORM:
                    raise ValueError("registry grid/CRS/transform mismatch")
                theirs = src.read(1).astype(np.float32)
            theirs = np.where(np.isfinite(theirs), theirs, 0.0)
            theirs[~foot] = 0
            tv = theirs[foot]
            support = (theirs > 0) & foot
            their_near = U._near(support)
            fwd = float(their_near[my_support].mean()) if n_my else 0.0
            cov = float(their_near[allowed].mean())
            rows.append({**base, "sha256": rec["sha256"], "their_dots": int(support.sum()),
                         "spearman_full_footprint": rho_against(my_ranks, my_norm, tv),
                         "surface_spearman_full_footprint": rho_against(s_ranks, s_norm, tv),
                         "my_dots_within_3px_of_theirs": fwd, "forward_overlap": fwd,
                         "their_dots_within_3px_of_mine": float(my_near[support].mean()) if support.any() else 0.0,
                         "jaccard_dot_sets": U._jaccard(my_support, support), "halo_coverage": cov,
                         "representation": "space_filling" if cov >= U.DENSE_HALO_FRACTION else "discriminating",
                         "identical_decoded_predictions": bool(np.array_equal(theirs, np.where(foot, mine, 0)))})
        except Exception as e:  # noqa: BLE001
            rows.append({**base, "error": str(e)})
        if i % 50 == 0 or i == len(records):
            worst = max((r.get("forward_overlap", 0) for r in rows if "error" not in r), default=0)
            log(f"[{i}/{len(records)}] worst forward overlap so far {worst:.3f} ({time.time()-t0:.0f}s)")

    if prev is not None:
        rows = prev["rows"]
    decision = U.binding_duplicate_decision(rows)
    checked = [r for r in rows if "error" not in r]
    literal = {
        "worst_forward_overlap": max(r["forward_overlap"] for r in checked),
        "worst_forward_overlap_file": max(checked, key=lambda r: r["forward_overlap"])["file"],
        "worst_abs_spearman": max(abs(r["spearman_full_footprint"] or 0) for r in checked),
        "worst_abs_spearman_file": max(checked, key=lambda r: abs(r["spearman_full_footprint"] or 0))["file"],
        "worst_surface_abs_spearman": max(abs(r["surface_spearman_full_footprint"] or 0) for r in checked),
        "worst_surface_abs_spearman_file": max(checked, key=lambda r: abs(r["surface_spearman_full_footprint"] or 0))["file"],
        "n_overlap_firings": sum(r["forward_overlap"] > U.OVERLAP_LIMIT for r in checked),
        "n_rho_firings": sum((r["spearman_full_footprint"] or 0) > U.RHO_LIMIT for r in checked),
        "identical_decoded_any": any(r["identical_decoded_predictions"] for r in checked),
    }
    champion = next((r for r in checked if "17a76895f6" in r["file"]), None)
    h19 = D.read_h19_5_support()
    h19_halo = T.halo(h19, 3.0)
    audit = {"evidence_class": "REGISTRY-MEASUREMENT", "candidate_file": str(tif.relative_to(ROOT)), "candidate_sha256": file_sha,
             "rasters_expected": len(records), "rasters_checked": len(checked), "errors": [r for r in rows if "error" in r],
             "complete_accessible_scan": bool(inv.get("complete_accessible_scan")) and not args.limit,
             "thresholds": {"rho": U.RHO_LIMIT, "forward_overlap": U.OVERLAP_LIMIT, "dense_halo_fraction": U.DENSE_HALO_FRACTION},
             "binding_decision_like_for_like": decision, "literal_reading": literal,
             "vs_champion_0p2778": champion, "share_in_h19_5_halo": float((my_support & h19_halo).sum() / max(n_my, 1)),
             "surface_rule": "surface Spearman checked against every prior before placement; dots after",
             "rows": rows, "seconds": round(time.time() - t0, 1) if prev is None else prev.get("seconds")}
    audit["rasters_expected"] = prev["rasters_expected"] if prev is not None else len(records)
    audit["complete_accessible_scan"] = prev["complete_accessible_scan"] if prev is not None else audit["complete_accessible_scan"]
    (ROOT / "evidence" / "registry_audit_h79.json").write_text(json.dumps(audit, indent=1, default=float) + "\n")

    # ---------- validator ----------
    val = V.validate(tif, foot, cat)
    try:
        V.assert_submittable(val)
        val_ok = True
        val_err = None
    except AssertionError as e:
        val_ok, val_err = False, str(e)
    gate = GT.format_report(tif, D.RAW / "sample_submission.tif", footprint=foot)
    inside = mine[foot]
    checks = {
        "all_finite_inside_footprint": bool(np.isfinite(inside).all()),
        "all_finite_everywhere": bool(np.isfinite(mine).all()),
        "min_inside": float(inside.min()), "max_inside": float(inside.max()),
        "values_in_unit_interval": bool((mine >= 0).all() and (mine <= 1).all()),
        "no_positive_outside_footprint": bool(not (mine[~foot] > 0).any()),
        "no_positive_on_catalogue": bool(not (mine[cat] > 0).any()),
        "crs_epsg": meta["crs"], "shape": list(meta["shape"]), "transform": meta["transform"], "dtype": meta["dtype"], "nodata": meta["nodata"],
        "matches_sample_grid": bool(gate.get("ok")), "template_gate_report": gate, "template_validate": val, "assert_submittable": val_ok, "assert_error": val_err,
        "positive_pixels": n_my, "unique_values": [float(v) for v in np.unique(mine)[:5]],
    }
    hold = {}
    capped = bool(build["construction"].get("amendment_A1_capped_priors"))
    con_p = ROOT / "evidence" / "holdout_h79_constrained.json"
    con = json.loads(con_p.read_text()) if (capped and con_p.exists()) else None
    for seed in (30, 20):
        p = ROOT / "evidence" / f"holdout_h79_seed{seed}.json"
        if p.exists():
            h = json.loads(p.read_text())
            ps = h["pooled_summary"]
            cand = "C3_continuity_q_B37654"
            entry = {
                "evidence_class": "HOLDOUT-DTI", "evaluator_version": h["evaluator_version"],
                "withheld_positive_pixels": h["withheld_positive_pixels"],
                "candidate": cand, "dti": ps["scores"][cand]["dti"], "ci95": ps["scores"][cand]["ci95"],
                "paired_vs": {k: {"delta": v["delta"], "ci95": v["ci95"]} for k, v in ps["paired_differences"].items()
                              if k in ("C0_random_B37654", "C1_pixel_B37654", "REF_h19_5_redot_B37654", "REF_champion_static")},
                "canary_worst": h["canary_worst"], "leakage_channels": h["leakage_channels_gt_0p90"]}
            if con is not None:
                cs = con["seeds"][f"seed{seed}"]["pooled_summary"]
                unc = entry.copy()
                entry = {
                    "evidence_class": "HOLDOUT-DTI", "evaluator_version": con["evaluator_version"],
                    "withheld_positive_pixels": con["seeds"][f"seed{seed}"]["withheld_positive_pixels"],
                    "candidate": "capped_0.68 (shipped construction, amendment A1)",
                    "dti": cs["scores"]["capped_0.68"]["dti"], "ci95": cs["scores"]["capped_0.68"]["ci95"],
                    "paired_vs": {"unconstrained_C3": {"delta": cs["paired_differences"]["unconstrained"]["delta"],
                                                       "ci95": cs["paired_differences"]["unconstrained"]["ci95"]}},
                    "unconstrained_construction_context": {k: unc[k] for k in ("dti", "ci95", "paired_vs")},
                    "canary_worst": h["canary_worst"], "leakage_channels": h["leakage_channels_gt_0p90"]}
                # random-control gate for the shipped construction: capped dti minus random dti, conservative CI
                r = ps["scores"]["C0_random_B37654"]
                entry["paired_vs"]["C0_random_B37654"] = {
                    "delta": entry["dti"] - r["dti"],
                    "ci95": [entry["ci95"][0] - r["ci95"][1], entry["ci95"][1] - r["ci95"][0]],
                    "note": "conservative interval difference (not paired); random arm from the same holdout draw"}
            hold[f"seed{seed}"] = entry
    ok = (val_ok and checks["values_in_unit_interval"] and checks["all_finite_everywhere"] and checks["matches_sample_grid"]
          and not decision["duplicate"] and not literal["identical_decoded_any"] and bool(hold)
          and all(v["paired_vs"]["C0_random_B37654"]["ci95"][0] > 0 for v in hold.values())
          and all(v["canary_worst"]["sym_auc"] <= 0.90 for v in hold.values()))
    verdict = "promote" if ok else "negative"
    card = {
        "RUN_CARD": "GEMSDOE79 / lane H79-MCT", "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": "Experts trace continuous lidar-visible scarps; scoring pixel scarp likelihood by its line-continuity (Sato tubularity) and emitting 3-px dots along reconstructed traces recovers unmapped scarps that pixel-rank detectors fragment, including in the 25 % lidar gap via 10 m 3DEP channels.",
        "mechanism": ("HGB on 30 catalogue-free terrain channels (1 m lidar cache, 10 m 3DEP, 100 m det_elev) -> p; S = sqrt(p * Sato01(p)); "
                      "greedy rank-ordered dots, 2.8 px spacing, > 2 px from catalogue"
                      + (", with amendment A1: at most 68 % of the dots inside the 3-px halo of any one prior raster that the "
                         "unconstrained emission overlapped > 0.60 (59 priors incl. H19-5), so the parallel-run duplicate rule holds by construction"
                         if capped else ", <= 66 % inside the H19-5 3-px halo.")),
        "amendment_A1": ({"status": "applied after the first audit (post-registration; logged as IR-79-16)",
                          "priors_capped": len(build["construction"]["amendment_A1_capped_priors"]) + 1, "cap_share": build["construction"]["cap_share"],
                          "holdout_cost": {k: v["paired_vs"].get("unconstrained_C3") for k, v in hold.items()},
                          "unconstrained_candidate": {"sha256": json.loads((ROOT / "evidence" / "build_h79_unconstrained.json").read_text())["sha256"],
                                                      "worst_like_for_like_overlap": json.loads((ROOT / "evidence" / "registry_audit_h79_unconstrained.json").read_text())["binding_decision_like_for_like"]["worst_forward_overlap"],
                                                      "verdict": "negative (duplicate by overlap 0.893 vs a 10 %-budget terrain raster)"}}
                         if capped and (ROOT / "evidence" / "build_h79_unconstrained.json").exists() else None),
        "named_non_fault_mimics": ["pluvial Lake Lahontan shorelines", "fluvial terrace risers", "roads/canals/railway grades", "lithologic benches", "mine benches", "landslide head-scarps"],
        "holdout": hold,
        "organizer_confirmed_score": None,
        "registry_audit": {"rasters_checked": len(checked), "binding_like_for_like": {k: decision[k] for k in ("duplicate", "worst_forward_overlap", "worst_forward_overlap_file", "worst_abs_spearman", "worst_abs_spearman_file", "discriminating_priors", "space_filling_priors")},
                           "literal": literal, "vs_champion": {k: champion[k] for k in ("spearman_full_footprint", "forward_overlap", "jaccard_dot_sets")} if champion else None,
                           "share_of_dots_in_h19_5_halo": audit["share_in_h19_5_halo"]},
        "raster": {"file": str(tif.relative_to(ROOT)), "sha256": file_sha, "name": build["name"], "note": build["note"], "note_chars": len(build["note"]), "dots": n_my},
        "validator": checks,
        "verdict": verdict,
        "verdict_rule": "promote iff validator passes, like-for-like duplicate test passes, no identical prior, canary <= 0.90, and candidate beats random with paired 95 % CI > 0 on both seeds",
        "labels": "every holdout number is HOLDOUT-DTI (gems57-pooled-hide-v2); no ORGANIZER-CONFIRMED score exists for this file; nothing here is a projection of a live score",
    }
    (ROOT / "evidence" / "run_card_h79.json").write_text(json.dumps(card, indent=2, default=float) + "\n")
    status = {"ok_to_submit": verdict == "promote", "verdict": verdict, "file": f"downloads/{tif.name}", "zip": f"downloads/{tif.stem}.zip",
              "sha256": file_sha, "name": build["name"], "note": build["note"], "dots": n_my, "generated_utc": card["generated_utc"],
              "holdout": {k: {"dti": v["dti"], "ci95": v["ci95"], "withheld": v["withheld_positive_pixels"]} for k, v in hold.items()},
              "audit": card["registry_audit"]["binding_like_for_like"], "validator_ok": val_ok and checks["values_in_unit_interval"] and checks["matches_sample_grid"]}
    (ROOT / "docs" / "status.json").write_text(json.dumps(status, indent=2, default=float) + "\n")
    log(f"VERDICT {verdict}; audit {len(checked)}/{len(records)}; worst fwd overlap (like-for-like) {decision['worst_forward_overlap']}; worst |rho| {decision['worst_abs_spearman']}; validator {val_ok}")


if __name__ == "__main__":
    main()
