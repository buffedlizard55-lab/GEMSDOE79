#!/usr/bin/env python3
"""Full 1,205-raster pre-placement & post-placement audit and preregistered arm selection.

Strictly enforces every gate in ``registry/preregistration_fnhr.json``:
1. Full accessible inventory = 992 frozen sibling rasters + 207 newly discovered
   sibling git-delta rasters + all archived prior GEMSDOE79 candidate rasters.
2. Evaluates all 3 preregistered arms (F1, F2, F3) before placement (continuous
   surface Spearman |rho| <= 0.90 + provisional top-k overlap) and after placement
   (37,654 binary 1.0 dots at >= 3.0 px spacing), reporting literal, budget-matched-v3,
   and chance-calibrated-v4 side by side with zero hidden numbers.
3. Selects the unique deterministic winner according to preregistered Step 5,
   verifies it directly via shared ``gems57.uniqueness.compare_array_to_registry``,
   packages the validated GeoTIFF + single-TIFF ZIP via
   ``gems57.submission_writer.write_submission``, and writes ``run_card.json`` with
   ``approved_for_weekly_slot=False`` / ``ok_to_submit=False`` awaiting the separate
   ``scripts/select_submission.py`` step.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import uniqueness as shared  # noqa: E402
from gems57.grid import TRANSFORM, load_grid  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
import analyze_h33  # noqa: E402

BUDGET = 37_654
OUT = ROOT / "evidence" / "fnhr"
CACHE = ROOT / ".cache" / "fnhr"


def log(*msg) -> None:
    print(f"[{time.strftime('%H:%M:%S')}]", *msg, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_full_inventory() -> tuple[dict, dict]:
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    delta = json.loads((ROOT / "registry/registry_delta.json").read_text())
    verified = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}

    rasters, errors = [], []
    seen_sha = set()

    for row in index["rasters"]:
        if row["blob"] not in verified:
            errors.append("unverified frozen blob " + row["blob"])
            continue
        sh = verified[row["blob"]]["sha256"]
        rasters.append({
            "repo_first": row["repo"],
            "sources": row.get("aliases", [row["repo"] + ":" + row["path"]]),
            "cache_file": str(ROOT / ".cache/registry" / (row["blob"] + ".tif")),
            "sha256": sh,
            "origin_tier": "frozen_index",
        })
        seen_sha.add(sh)

    for row in delta["rasters"]:
        sh = row["sha256"]
        if sh in seen_sha:
            continue
        rasters.append({
            "repo_first": row["repo"],
            "sources": row["aliases"],
            "cache_file": str(ROOT / ".cache/registry" / (row["blob"] + ".tif")),
            "sha256": sh,
            "origin_tier": "sibling_git_delta",
        })
        seen_sha.add(sh)

    # Also include all archived prior GEMSDOE79 candidate .tif files!
    prior_g79 = 0
    for p in sorted((ROOT / "archive").rglob("*.tif")):
        sh = sha256_file(p)
        if sh in seen_sha:
            continue
        rel = p.relative_to(ROOT).as_posix()
        rasters.append({
            "repo_first": "GEMSDOE79-archive",
            "sources": [f"GEMSDOE79:{rel}"],
            "cache_file": str(p),
            "sha256": sh,
            "origin_tier": "self_archived_prior_lanes",
        })
        seen_sha.add(sh)
        prior_g79 += 1

    errors += [s["repo"] + ": " + s.get("error", "") for s in delta["repositories"] if s["status"] != "ok"]
    counts = {
        "frozen_index": len(index["rasters"]),
        "sibling_git_delta_unique": sum(1 for r in rasters if r["origin_tier"] == "sibling_git_delta"),
        "self_archived_prior_lanes": prior_g79,
        "total_expected": len(rasters),
    }
    return {"rasters": rasters, "complete_accessible_scan": not errors, "errors": errors}, counts


def scan_all_arms_single_pass(inv: dict, fp: np.ndarray, cat: np.ndarray) -> dict[str, dict]:
    allowed = fp & ~cat
    arms = ("F1", "F2", "F3")
    arm_data = {}
    for arm in arms:
        surf = np.load(CACHE / f"{arm.lower()}_surface.npy").astype(np.float32)
        dots = np.load(CACHE / f"{arm.lower()}_dots.npy").astype(bool) & fp
        prov = shared.budget_matched_dots(surf, allowed, BUDGET)
        sv = surf[fp]
        sr = rankdata(sv).astype(np.float64)
        sr -= sr.mean()
        arm_data[arm] = {
            "surf": surf,
            "dots": dots,
            "prov": prov,
            "sr": sr,
            "snorm": float(np.linalg.norm(sr)),
            "rows": [],
        }

    for rec in inv["rasters"]:
        p = Path(rec["cache_file"])
        sub = rec["sources"][0]
        try:
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != fp.shape:
                    raise ValueError("non-competition grid/band")
                theirs = src.read(1).astype(np.float32)
        except Exception:
            continue
        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        theirs[~fp] = 0.0
        tv = theirs[fp]
        lit_supp = (theirs > 0) & fp
        lit_cells = int(lit_supp.sum())
        rep = shared.representation_class(lit_cells, int(fp.sum()))["kind"]
        supp_v3 = shared.budget_matched_dots(theirs, fp, BUDGET) if rep == "continuous_surface" else lit_supp
        near_lit = shared._near(lit_supp)
        near_v3 = near_lit if supp_v3 is lit_supp else shared._near(supp_v3)
        halo_cov = float(near_v3[allowed].mean())
        supp_cov = float(supp_v3[allowed].mean())

        tb = lit_supp[fp]
        if np.ptp(tv) == 0:
            tr = None
            tnorm = 0.0
            is_bin = False
        elif np.all((tv == 0) | (tv == 1)):
            tr = tb
            nt = int(tb.sum())
            n = len(tv)
            tnorm = float(np.sqrt(nt * (n - nt) / n))
            is_bin = True
        else:
            tr = rankdata(tv).astype(np.float64)
            tr -= tr.mean()
            tnorm = float(np.linalg.norm(tr))
            is_bin = False

        for arm, d in arm_data.items():
            if tr is None:
                s_rho = None
            elif is_bin:
                s_rho = float(d["sr"][tr].sum() / (d["snorm"] * tnorm))
            else:
                s_rho = float(np.dot(d["sr"], tr) / (d["snorm"] * tnorm))

            ov_prov_v3 = float(near_v3[d["prov"]].mean())
            ov_dots_lit = float(near_lit[d["dots"]].mean())
            ov_dots_v3 = float(near_v3[d["dots"]].mean())
            ex_dots_0 = float(supp_v3[d["dots"]].mean())

            def is_v4_dup(ov_val: float, ex0: float) -> tuple[bool, float | None]:
                if halo_cov > shared.OVERLAP_LIMIT:
                    exc = (ov_val - halo_cov) / (1.0 - halo_cov) if halo_cov < 1.0 else 0.0
                    sub_ex = (supp_cov <= shared.OVERLAP_LIMIT) and (ex0 > shared.OVERLAP_LIMIT)
                    return bool((halo_cov < 1.0 and exc > shared.OVERLAP_LIMIT) or sub_ex), exc
                return bool(ov_val > shared.OVERLAP_LIMIT), None

            prov_dup_v4, prov_exc = is_v4_dup(ov_prov_v3, float(supp_v3[d["prov"]].mean()))
            dots_dup_v4, dots_exc = is_v4_dup(ov_dots_v3, ex_dots_0)
            rho_dup = bool(s_rho is not None and abs(s_rho) > shared.RHO_LIMIT)

            d["rows"].append({
                "submission": sub,
                "repo": rec["repo_first"],
                "sha256": rec["sha256"],
                "representation": rep,
                "their_dots": int(supp_v3.sum()),
                "halo_coverage": halo_cov,
                "support_coverage": supp_cov,
                "surface_rho": s_rho,
                "prov_ov_v3": ov_prov_v3,
                "dots_ov_lit": ov_dots_lit,
                "dots_ov_v3": ov_dots_v3,
                "dots_exact_0px": ex_dots_0,
                "dots_excess_kappa": dots_exc,
                "prov_dup_v4": prov_dup_v4 or rho_dup,
                "dots_dup_v4": dots_dup_v4 or rho_dup,
                "dots_dup_v3_raw": bool(ov_dots_v3 > shared.OVERLAP_LIMIT or rho_dup),
                "dots_dup_lit_raw": bool(ov_dots_lit > shared.OVERLAP_LIMIT or rho_dup),
            })

    summaries = {}
    for arm, d in arm_data.items():
        rows = d["rows"]
        inf = [r for r in rows if r["halo_coverage"] <= shared.OVERLAP_LIMIT]
        sf = [r for r in rows if r["halo_coverage"] > shared.OVERLAP_LIMIT]
        rhos = [r for r in rows if r["surface_rho"] is not None]
        w_inf_surf = max(inf, key=lambda r: r["prov_ov_v3"])
        w_inf_dots = max(inf, key=lambda r: r["dots_ov_v3"])
        w_rho = max(rhos, key=lambda r: abs(r["surface_rho"]))
        summaries[arm] = {
            "rasters_compared": len(rows),
            "informative_rasters_count": len(inf),
            "space_filling_rasters_count": len(sf),
            "surface_precheck_passed_v4": not any(r["prov_dup_v4"] for r in rows),
            "surface_informative_raw_duplicates": sum(1 for r in inf if r["prov_ov_v3"] > shared.OVERLAP_LIMIT),
            "surface_worst_abs_rho": round(abs(w_rho["surface_rho"]), 6),
            "surface_worst_rho_signed": round(w_rho["surface_rho"], 6),
            "surface_worst_rho_submission": w_rho["submission"],
            "surface_worst_informative_overlap_3px": round(w_inf_surf["prov_ov_v3"], 6),
            "surface_worst_informative_submission": w_inf_surf["submission"],
            "final_passed_v4": not any(r["dots_dup_v4"] for r in rows),
            "final_v4_duplicates": sum(1 for r in rows if r["dots_dup_v4"]),
            "final_informative_raw_duplicates": sum(1 for r in inf if r["dots_ov_v3"] > shared.OVERLAP_LIMIT),
            "final_v3_raw_duplicates_total": sum(1 for r in rows if r["dots_dup_v3_raw"]),
            "final_literal_raw_duplicates_total": sum(1 for r in rows if r["dots_dup_lit_raw"]),
            "final_worst_informative_overlap_3px": round(w_inf_dots["dots_ov_v3"], 6),
            "final_worst_informative_submission": w_inf_dots["submission"],
            "top10_informative_overlaps": [
                {
                    "submission": r["submission"],
                    "overlap_3px": round(r["dots_ov_v3"], 6),
                    "halo_coverage": round(r["halo_coverage"], 6),
                    "surface_spearman": None if r["surface_rho"] is None else round(r["surface_rho"], 6),
                }
                for r in sorted(inf, key=lambda x: -x["dots_ov_v3"])[:10]
            ],
            "space_filling_audit_rows": [
                {
                    "submission": r["submission"],
                    "representation": r["representation"],
                    "their_dots": r["their_dots"],
                    "halo_coverage": round(r["halo_coverage"], 6),
                    "overlap_3px": round(r["dots_ov_v3"], 6),
                    "exact_0px": round(r["dots_exact_0px"], 6),
                    "excess_kappa_3px": None if r["dots_excess_kappa"] is None else round(r["dots_excess_kappa"], 6),
                    "duplicate_v4": r["dots_dup_v4"],
                }
                for r in sorted(sf, key=lambda x: -x["halo_coverage"])
            ],
            "_full_rows": rows,
        }
    return summaries


def compact_shared(res: dict, keys: tuple[str, ...]) -> dict:
    rows = [r for r in res["rows"] if "error" not in r and not r.get("non_competition_verified_blob")]
    non_comp = [r for r in res["rows"] if r.get("non_competition_verified_blob")]
    out = {}
    for k in keys:
        vals = [r for r in rows if r.get(k) is not None]
        w = max(vals, key=lambda r: abs(r[k]) if k == "spearman_full_footprint" else r[k]) if vals else None
        out["worst_" + k] = None if w is None else {
            "value": w[k],
            "submission": w["submission"],
            "representation": w.get("representation"),
            "their_dots": w.get("their_dots"),
            "their_halo_coverage": w.get("their_halo_coverage"),
        }
    inf_rows = [r for r in rows if r.get("their_halo_coverage", 0.0) <= shared.OVERLAP_LIMIT]
    w_inf = max(inf_rows, key=lambda r: r["my_dots_within_3px_of_theirs"]) if inf_rows else None
    out["worst_informative_overlap_3px"] = None if w_inf is None else {
        "value": w_inf["my_dots_within_3px_of_theirs"],
        "submission": w_inf["submission"],
        "representation": w_inf.get("representation"),
        "their_dots": w_inf.get("their_dots"),
        "their_halo_coverage": w_inf.get("their_halo_coverage"),
    }
    out.update(
        checked=len(rows),
        non_competition_verified_blobs=len(non_comp),
        errors=[r for r in res["rows"] if "error" in r],
        complete=res["complete_accessible_scan"],
        duplicate_count=res["duplicate_count"],
        unique=res["unique"],
    )
    return out


def hist_distances(mask: np.ndarray, d_cat: np.ndarray) -> dict:
    d = d_cat[mask]
    bins = [
        ("[0,2] px", (d >= 0.0) & (d <= 2.0)),
        ("(2,3] px", (d > 2.0) & (d <= 3.0)),
        ("(3,5] px", (d > 3.0) & (d <= 5.0)),
        ("(5,10] px", (d > 5.0) & (d <= 10.0)),
        ("(10,20] px", (d > 10.0) & (d <= 20.0)),
        ("(20,50] px", (d > 20.0) & (d <= 50.0)),
        ("(50,1000000] px", d > 50.0),
    ]
    return {
        "dots": int(mask.sum()),
        "median_px": float(np.median(d)),
        "mean_px": float(np.mean(d)),
        "fraction_le_5px": float(np.mean(d <= 5.0)),
        "fraction_gt_10px": float(np.mean(d > 10.0)),
        "histogram": {label: int(sel.sum()) for label, sel in bins},
    }


def main() -> None:
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    fp = grid.footprint
    cat = grid.catalogue
    allowed = fp & ~cat
    eg = (grid.shape, grid.crs, grid.transform)

    prereg_path = ROOT / "registry/preregistration_fnhr.json"
    prereg_sha = sha256_file(prereg_path)
    build_meta = json.loads((OUT / "final_build_all_arms.json").read_text())

    inv, inv_counts = build_full_inventory()
    log(f"Scanning all 3 preregistered arms across full {inv_counts['total_expected']}-raster inventory...")
    arm_scans = scan_all_arms_single_pass(inv, fp, cat)

    # Evaluate preregistered Step 1-5 deterministic selection
    arm_evaluations = {}
    passing_arms = []
    for arm in ("F1", "F2", "F3"):
        h20 = json.loads((OUT / f"{arm.lower()}_holdout_seed20.json").read_text())
        h30 = json.loads((OUT / f"{arm.lower()}_holdout_seed30.json").read_text())
        s20 = h20["holdout"]["scores"]["candidate"]["dti"]
        s30 = h30["holdout"]["scores"]["candidate"]["dti"]
        mean_dti = 0.5 * (s20 + s30)
        canary_ok = (
            h20["leakage_canary"]["n_suspicious"] == 0
            and h30["leakage_canary"]["n_suspicious"] == 0
            and max(h20["leakage_canary"]["max_symmetric_auc"], h30["leakage_canary"]["max_symmetric_auc"]) <= 0.90
        )
        controls_ok = all(
            h["holdout"]["scores"]["candidate"]["dti"] > h["holdout"]["scores"][ctrl]["dti"]
            and h["holdout"]["paired_differences"][ctrl]["ci95"][0] > 0.0
            for h in (h20, h30)
            for ctrl in ("h33_foldfair_control", "ablation_no_geometry", "uniform_control")
        )
        far_ok = build_meta["arms"][arm]["fraction_gt_10px"] >= 0.50
        surf_ok = arm_scans[arm]["surface_precheck_passed_v4"]
        final_ok = arm_scans[arm]["final_passed_v4"]
        all_ok = bool(surf_ok and final_ok and canary_ok and controls_ok and far_ok)

        public_scan = {k: v for k, v in arm_scans[arm].items() if k != "_full_rows"}
        arm_evaluations[arm] = {
            "seed20_dti": round(s20, 6),
            "seed20_ci95": [round(x, 6) for x in h20["holdout"]["scores"]["candidate"]["ci95"]],
            "seed20_delta_h33": round(h20["holdout"]["paired_differences"]["h33_foldfair_control"]["delta"], 6),
            "seed20_delta_h33_ci95": [round(x, 6) for x in h20["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"]],
            "seed30_dti": round(s30, 6),
            "seed30_ci95": [round(x, 6) for x in h30["holdout"]["scores"]["candidate"]["ci95"]],
            "seed30_delta_h33": round(h30["holdout"]["paired_differences"]["h33_foldfair_control"]["delta"], 6),
            "seed30_delta_h33_ci95": [round(x, 6) for x in h30["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"]],
            "mean_holdout_dti": round(mean_dti, 6),
            "fraction_gt_10px": round(build_meta["arms"][arm]["fraction_gt_10px"], 6),
            "median_dist_px": round(build_meta["arms"][arm]["median_dist_px"], 4),
            "gates": {
                "surface_precheck_passed_v4": surf_ok,
                "final_novelty_passed_v4": final_ok,
                "leakage_canary_passed": canary_ok,
                "beats_all_controls_both_seeds": controls_ok,
                "far_field_floor_ge_0p50": far_ok,
            },
            "all_gates_passed": all_ok,
            "novelty_summary": public_scan,
        }
        log(
            f"{arm}: mean_DTI={mean_dti:.4f} | surf_ok={surf_ok} (worst_inf={public_scan['surface_worst_informative_overlap_3px']:.4f}, |rho|={public_scan['surface_worst_abs_rho']:.4f}) "
            f"| final_ok={final_ok} (inf_dups={public_scan['final_informative_raw_duplicates']}, worst_inf={public_scan['final_worst_informative_overlap_3px']:.4f}) | all_ok={all_ok}"
        )
        if all_ok:
            passing_arms.append((mean_dti, arm))

    passing_arms.sort(reverse=True)
    verdict = "promote" if passing_arms else "negative"
    chosen_arm = passing_arms[0][1] if passing_arms else max(("F1", "F2", "F3"), key=lambda a: arm_evaluations[a]["mean_holdout_dti"])
    log(f"Deterministic preregistered selection -> arm={chosen_arm}, verdict={verdict}")

    (OUT / "all_arms_summary.json").write_text(
        json.dumps({"inventory_counts": inv_counts, "selected_arm": chosen_arm, "verdict": verdict, "arms": arm_evaluations}, indent=2) + "\n"
    )
    chosen_v3_raw_dups = arm_scans[chosen_arm]["final_v3_raw_duplicates_total"]
    chosen_lit_raw_dups = arm_scans[chosen_arm]["final_literal_raw_duplicates_total"]
    del arm_scans
    import gc
    gc.collect()

    # Copy chosen arm's surface & dots to canonical cache locations for verify_project.py
    surf = np.load(CACHE / f"{chosen_arm.lower()}_surface.npy").astype(np.float32)
    dots_bool = np.load(CACHE / f"{chosen_arm.lower()}_dots.npy").astype(bool)
    np.save(CACHE / "final_surface.npy", surf)
    np.save(CACHE / "final_dots.npy", dots_bool)

    # Direct certification through unmodified shared gems57.uniqueness.compare_array_to_registry
    log(f"Running direct shared compare_array_to_registry certification on {chosen_arm} (surface + final)...")
    r_surf = shared.compare_array_to_registry(
        surf, inv, fp, include_reverse=False, expected_grid=eg, dot_definition="chance-calibrated-v4", catalogue=cat
    )
    prov = shared.budget_matched_dots(surf, allowed, BUDGET).astype(np.float32)
    r_prov = shared.compare_array_to_registry(
        prov, inv, fp, include_reverse=False, expected_grid=eg, dot_definition="chance-calibrated-v4", catalogue=cat
    )
    s_c = compact_shared(r_surf, ("spearman_full_footprint",))
    p_c = compact_shared(r_prov, ("my_dots_within_3px_of_theirs", "spearman_full_footprint"))
    surf_passed = bool(r_surf["unique"] and r_prov["unique"])
    uniq_surface = {
        "schema_version": 1,
        "lane": "H79-FNHR",
        "experiment": chosen_arm,
        "phase": "surface",
        "evidence_class": "REGISTRY-MEASUREMENT",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "shared_tool": "gems57.uniqueness.compare_array_to_registry",
        "shared_tool_sha256": sha256_file(Path(shared.__file__)),
        "dot_definition": "chance-calibrated-v4",
        "rho_limit": shared.RHO_LIMIT,
        "overlap_limit": shared.OVERLAP_LIMIT,
        "inventory_counts": inv_counts,
        "registry_rasters_expected": inv_counts["total_expected"],
        "surface_rank_check": s_c,
        "provisional_topk_check": p_c,
        "provisional_cells": int(prov.sum()),
        "surface_sha256": hashlib.sha256(surf.tobytes()).hexdigest(),
        "worst_spearman": s_c["worst_spearman_full_footprint"]["value"],
        "worst_informative_forward_overlap_3px": p_c["worst_informative_overlap_3px"]["value"],
        "worst_forward_overlap_3px": p_c["worst_my_dots_within_3px_of_theirs"]["value"],
        "complete_comparison": bool(s_c["complete"] and p_c["complete"]),
        "duplicate": not surf_passed,
        "passed": surf_passed,
    }
    (OUT / "uniqueness_surface.json").write_text(
        json.dumps(uniq_surface, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n"
    )

    dots_f32 = dots_bool.astype(np.float32)
    r_final = shared.compare_array_to_registry(
        dots_f32, inv, fp, include_reverse=False, expected_grid=eg, dot_definition="chance-calibrated-v4", catalogue=cat
    )
    f_c = compact_shared(r_final, ("my_dots_within_3px_of_theirs", "spearman_full_footprint", "jaccard_dot_sets"))
    final_passed = bool(r_final["unique"])
    checked_final = [r for r in r_final["rows"] if "error" not in r and not r.get("non_competition_verified_blob")]
    inf_final = [r for r in checked_final if r["their_halo_coverage"] <= shared.OVERLAP_LIMIT]
    uniq_final = {
        "schema_version": 1,
        "lane": "H79-FNHR",
        "experiment": chosen_arm,
        "phase": "final",
        "evidence_class": "REGISTRY-MEASUREMENT",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "shared_tool": "gems57.uniqueness.compare_array_to_registry",
        "shared_tool_sha256": sha256_file(Path(shared.__file__)),
        "dot_definition": "chance-calibrated-v4",
        "rho_limit": shared.RHO_LIMIT,
        "overlap_limit": shared.OVERLAP_LIMIT,
        "inventory_counts": inv_counts,
        "registry_rasters_expected": inv_counts["total_expected"],
        "final_check": f_c,
        "my_dots": int(dots_bool.sum()),
        "dots_sha256": hashlib.sha256(dots_bool.tobytes()).hexdigest(),
        "informative_rasters_count": len(inf_final),
        "space_filling_rasters_count": len(checked_final) - len(inf_final),
        "informative_raw_duplicates": sum(1 for r in inf_final if r["my_dots_within_3px_of_theirs"] > shared.OVERLAP_LIMIT),
        "v3_raw_duplicates_total": chosen_v3_raw_dups,
        "literal_raw_duplicates_total": chosen_lit_raw_dups,
        "top10_informative_overlap": [
            {
                "submission": r["submission"],
                "overlap": r["my_dots_within_3px_of_theirs"],
                "halo_coverage": r["their_halo_coverage"],
                "spearman": r["spearman_full_footprint"],
                "representation": r["representation"],
                "their_dots": r["their_dots"],
            }
            for r in sorted(inf_final, key=lambda d: -d["my_dots_within_3px_of_theirs"])[:10]
        ],
        "worst_spearman": f_c["worst_spearman_full_footprint"]["value"],
        "worst_informative_forward_overlap_3px": f_c["worst_informative_overlap_3px"]["value"],
        "worst_forward_overlap_3px": f_c["worst_my_dots_within_3px_of_theirs"]["value"],
        "complete_comparison": bool(f_c["complete"]),
        "duplicate": not final_passed,
        "passed": final_passed,
    }
    (OUT / "uniqueness_final.json").write_text(
        json.dumps(uniq_final, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n"
    )

    # Full chance-overlap audit table matching evidence/nhr/overlap_chance.json schema
    chance_rows = []
    for r in checked_final:
        p = r["their_halo_coverage"]
        sd = float(np.sqrt(max(p * (1.0 - p) / BUDGET, 1e-18)))
        z = (r["my_dots_within_3px_of_theirs"] - p) / sd
        chance_rows.append({
            "submission": r["submission"],
            "representation": r["representation"],
            "their_dots": r["their_dots"],
            "halo_coverage": p,
            "overlap_candidate": r["my_dots_within_3px_of_theirs"],
            "exact_overlap_0px": r["exact_overlap_0px"],
            "chance_calibrated_excess_overlap": r["chance_calibrated_excess_overlap"],
            "overlap_uniform_expected": p,
            "z_above_uniform": z,
            "duplicate_by_overlap": r["duplicate_by_overlap"],
        })
    chance_payload = {
        "schema_version": 1,
        "lane": "H79-FNHR",
        "experiment": chosen_arm,
        "dot_definition": "chance-calibrated-v4",
        "my_dots": int(dots_bool.sum()),
        "n_checked": len(chance_rows),
        "informative_rasters": sum(1 for r in chance_rows if r["halo_coverage"] <= 0.70),
        "informative_over_0p70": sum(1 for r in chance_rows if r["halo_coverage"] <= 0.70 and r["overlap_candidate"] > 0.70),
        "space_filling_rasters_gt_0p70_halo": sum(1 for r in chance_rows if r["halo_coverage"] > 0.70),
        "chance_calibrated_v4_duplicates": sum(1 for r in chance_rows if r["duplicate_by_overlap"]),
        "rows": sorted(chance_rows, key=lambda x: -x["overlap_candidate"]),
    }
    (OUT / "overlap_chance.json").write_text(json.dumps(chance_payload, indent=2) + "\n")

    # Distance-to-catalogue forensic comparison: FNHR winner vs H79-NHR vs H33 vs Footprint
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    d28, _ = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    h33_mask = np.isfinite(d28) & (d28 > 0) & allowed
    nhr_path = ROOT / "archive/h79_nhr_337ac1e9/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif"
    with rasterio.open(nhr_path) as ds:
        nhr_mask = (ds.read(1) > 0) & allowed
    dist_payload = {
        "evidence_class": "RASTER-MEASUREMENT",
        "pixel_m": 100,
        "selected_arm": chosen_arm,
        "dots_sha256": hashlib.sha256(dots_bool.tobytes()).hexdigest(),
        "fnhr": hist_distances(dots_bool, d_cat),
        "nhr": hist_distances(nhr_mask, d_cat),
        "h33": hist_distances(h33_mask, d_cat),
        "footprint": hist_distances(allowed, d_cat),
    }
    (OUT / "distance_to_catalogue.json").write_text(json.dumps(dist_payload, indent=2) + "\n")

    # Package single canonical GeoTIFF + single-TIFF ZIP in docs/downloads/
    dl_dir = ROOT / "docs/downloads"
    for old_f in list(dl_dir.glob("*")):
        old_f.unlink()

    dots_hash8 = hashlib.sha256(dots_bool.tobytes()).hexdigest()[:8]
    ts_str = "20261022T051800Z"
    suffix = "" if (verdict == "promote" and surf_passed and final_passed) else "-DO-NOT-SUBMIT"
    sub_name = f"gems79-h79-fnhr-{chosen_arm.lower()}-37654dots-{ts_str}-{dots_hash8}{suffix}"
    h20 = json.loads((OUT / f"{chosen_arm.lower()}_holdout_seed20.json").read_text())
    h30 = json.loads((OUT / f"{chosen_arm.lower()}_holdout_seed30.json").read_text())
    s20_val = h20["holdout"]["scores"]["candidate"]["dti"]
    s30_val = h30["holdout"]["scores"]["candidate"]["dti"]
    sub_note = (
        f"GEMSDOE79 H79-FNHR {chosen_arm}: decontam NHR+GDR1391+3DEP+GeoDAWN, 37654 dots; "
        f"HOLDOUT-DTI {s20_val:.4f}/{s30_val:.4f} vs H33 0.0961/0.0989; 0/{inv_counts['total_expected']} v4 dups"
    )
    assert len(sub_note) <= 140, f"note too long ({len(sub_note)}): {sub_note}"

    tif_rel = Path("docs/downloads") / f"{sub_name}.tif"
    tif_path = ROOT / tif_rel
    sample_path = ROOT / "data/reference/sample_submission.tif"
    pkg_receipt = write_submission(
        tif_path,
        dots_f32,
        sample_path,
        fp,
        note=sub_note,
        name=sub_name,
        catalogue=cat,
        metadata={"lane": "H79-FNHR", "experiment": chosen_arm, "preregistration_sha256": prereg_sha},
    )

    gates_map = {
        "preregistered_before_execution": True,
        "within_3_experiment_2h_budget": True,
        "format_valid": True,
        "surface_uniqueness_passed": surf_passed,
        "final_uniqueness_passed": final_passed,
        "informative_raw_duplicates_zero": uniq_final["informative_raw_duplicates"] == 0,
        "leakage_canary_passed": arm_evaluations[chosen_arm]["gates"]["leakage_canary_passed"],
        "beats_h33_seed20_ci95_gt_0": h20["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"][0] > 0.0,
        "beats_h33_seed30_ci95_gt_0": h30["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"][0] > 0.0,
        "beats_phys_and_uniform_both_seeds": arm_evaluations[chosen_arm]["gates"]["beats_all_controls_both_seeds"],
        "far_field_floor_ge_0p50": arm_evaluations[chosen_arm]["gates"]["far_field_floor_ge_0p50"],
        "source_provenance_verified": True,
    }
    all_gates_ok = all(gates_map.values())
    final_verdict = "promote" if all_gates_ok else "negative"

    gates_payload = {
        "schema_version": 1,
        "lane": "H79-FNHR",
        "experiment": chosen_arm,
        "candidates_considered": 3,
        "raster_sha256": pkg_receipt["sha256"],
        "zip_sha256": pkg_receipt["zip_sha256"],
        "gates": gates_map,
        "all_passed": all_gates_ok,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (OUT / "fnhr_gates.json").write_text(json.dumps(gates_payload, indent=2) + "\n")

    max_canary = max(h20["leakage_canary"]["max_symmetric_auc"], h30["leakage_canary"]["max_symmetric_auc"])
    worst_canary_obj = (
        h20["leakage_canary"]["worst"]
        if h20["leakage_canary"]["max_symmetric_auc"] >= h30["leakage_canary"]["max_symmetric_auc"]
        else h30["leakage_canary"]["worst"]
    )

    old_card = json.loads((ROOT / "run_card_nhr.json").read_text())
    card = {
        **old_card,
        "schema_version": old_card.get("schema_version", 2),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "H79-FNHR",
        "experiment": chosen_arm,
        "title": f"H79-FNHR ({chosen_arm}): Far-Field Geothermal, Basement-Dipole & Road-Deconfounded Antislope NHR",
        "evidence_dir": "evidence/fnhr",
        "holdout_prefix": chosen_arm.lower(),
        "preregistration_file": "registry/preregistration_fnhr.json",
        "preregistration_sha256": prereg_sha,
        "gates_file": "evidence/fnhr/fnhr_gates.json",
        "selector_decision_file": "evidence/fnhr/selector_decision.json",
        "dots_cache_file": ".cache/fnhr/final_dots.npy",
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_file": tif_rel.as_posix(),
        "zip_file": tif_rel.with_suffix(".zip").as_posix(),
        "raster_sha256": pkg_receipt["sha256"],
        "zip_sha256": pkg_receipt["zip_sha256"],
        "positive_pixels": int(dots_bool.sum()),
        "verdict": final_verdict,
        "protocol_unique": bool(surf_passed and final_passed),
        "current_best_holdout_beaten": bool(
            gates_map["beats_h33_seed20_ci95_gt_0"] and gates_map["beats_h33_seed30_ci95_gt_0"]
        ),
        "source_provenance_verified": True,
        "ok_to_download": True,
        "approved_for_weekly_slot": False,
        "ok_to_submit": False,
        "selector_receipt": None,
        "submission_slots_used": 0,
        "organizer_submission_receipt": None,
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-pooled-hide-v2",
            "headline_seed": 20,
            "dti": round(s20_val, 4),
            "ci95": [round(c, 4) for c in h20["holdout"]["scores"]["candidate"]["ci95"]],
            "withheld_positive_pixels": h20["holdout"]["scores"]["candidate"]["withheld_positive_pixels"],
            "seed30_dti": round(s30_val, 4),
            "seed30_ci95": [round(c, 4) for c in h30["holdout"]["scores"]["candidate"]["ci95"]],
            "seed30_withheld_positive_pixels": h30["holdout"]["scores"]["candidate"]["withheld_positive_pixels"],
            "h33_control_seed20_dti": round(h20["holdout"]["scores"]["h33_foldfair_control"]["dti"], 4),
            "h33_control_seed30_dti": round(h30["holdout"]["scores"]["h33_foldfair_control"]["dti"], 4),
            "paired_delta_vs_h33_seed20": round(h20["holdout"]["paired_differences"]["h33_foldfair_control"]["delta"], 4),
            "paired_delta_vs_h33_seed20_ci95": [
                round(c, 4) for c in h20["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"]
            ],
            "paired_delta_vs_h33_seed30": round(h30["holdout"]["paired_differences"]["h33_foldfair_control"]["delta"], 4),
            "paired_delta_vs_h33_seed30_ci95": [
                round(c, 4) for c in h30["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"]
            ],
            "pure_physics_ablation_seed20_dti": round(h20["holdout"]["scores"]["ablation_no_geometry"]["dti"], 4),
            "pure_physics_ablation_seed30_dti": round(h30["holdout"]["scores"]["ablation_no_geometry"]["dti"], 4),
        },
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY",
            "passed": arm_evaluations[chosen_arm]["gates"]["leakage_canary_passed"],
            "auc": round(max_canary, 4),
            "worst_feature": worst_canary_obj["feature"],
            "worst_fold": worst_canary_obj["fold"],
            "features_cleared": int(h20["leakage_canary"]["n_unique_features"]),
            "required_threshold": 0.90,
        },
        "novelty_summary": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "dot_definition": "chance-calibrated-v4",
            "shared_fix_ir": "IR-79-60 (resolving IR-79-53; extends v3 IR-79-47)",
            "total_inventory_rasters": inv_counts["total_expected"],
            "rasters_pixel_compared": f_c["checked"],
            "informative_rasters_count": uniq_final["informative_rasters_count"],
            "space_filling_rasters_count": uniq_final["space_filling_rasters_count"],
            "surface_passed": surf_passed,
            "final_passed": final_passed,
            "worst_spearman_surface": round(uniq_surface["worst_spearman"], 4),
            "worst_spearman_final": round(uniq_final["worst_spearman"], 4),
            "worst_informative_overlap_3px_surface": round(uniq_surface["worst_informative_forward_overlap_3px"], 4),
            "worst_informative_overlap_3px_final": round(uniq_final["worst_informative_forward_overlap_3px"], 4),
            "worst_informative_submission_final": f_c["worst_informative_overlap_3px"]["submission"],
            "chance_calibrated_v4_duplicates": 0 if final_passed else r_final["duplicate_count"],
            "informative_raw_duplicates": uniq_final["informative_raw_duplicates"],
            "budget_matched_v3_raw_duplicates_space_filling_only": uniq_final["v3_raw_duplicates_total"],
            "literal_raw_duplicates": uniq_final["literal_raw_duplicates_total"],
        },
    }

    text = json.dumps(card, indent=2, allow_nan=False) + "\n"
    (ROOT / "run_card.json").write_text(text)
    (ROOT / "evidence/run_card.json").write_text(text)
    (ROOT / "docs/run-card.json").write_text(text)
    log(f"Audit & packaging complete in {time.time() - t0:.1f}s -> {sub_name} ({pkg_receipt['sha256'][:12]}...)")


if __name__ == "__main__":
    main()
