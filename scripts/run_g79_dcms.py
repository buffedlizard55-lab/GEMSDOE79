#!/usr/bin/env python3
"""Execute the preregistered G79-DCMS (Dip-Coupled Multi-Scale Scarp-to-Basement
Reactivation, Pluvial/Fluvial Mimic Suppression & Calibrated Dinkelbach Submodular
Kernel Allocator) experimental protocol end-to-end.

Strictly adheres to all 6 rules of the Parallel-Run Protocol (AGENTS.md):
  1. Single method lane (G79-DCMS, registry/preregistration_g79_dcms.json).
     Audits all 1,201 verified family rasters (992 frozen + 209 post-freeze delta)
     across all 92 non-self sibling repos PLUS all local GEMSDOE79 lanes BOTH on
     the pre-placement continuous surface AND on the placed binary dot raster.
  2. Reuses unmodified vendor/gems57/{evaluate_holdout,submission_writer,uniqueness,validate,metric,holdout}.py.
  3. Labels every holdout score HOLDOUT-DTI (gems57-pooled-hide-v2, withheld count, 95% CI).
  4. Runs single-feature symmetric ROC AUC leakage canaries across all 118 channels
     on BOTH Seed 20 and Seed 30 (236 feature-seed tests) BEFORE any model scoring.
  5. Emits complete JSON receipts, diagnostic figures, and byte-unique GeoTIFF + ZIP.
  6. Respects the 3-experiment budget (EXP-DCMS-1, EXP-DCMS-2, EXP-DCMS-3) and consumes
     0 weekly upload slots unless every gate in scripts/select_submission.py passes.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout, holdout, metric, submission_writer, uniqueness, validate as shared_validate
from gems57.grid import Grid
from gems79.dcms_features import (
    ALL_DCMS_NAMES,
    MECH_DCMS_NAMES,
    STATIC_DCMS_NAMES,
    _drop_cache,
    build_dcms_static_memmap,
    compute_dcms_mechanics,
    rss_mb,
)
from gems79.dcms_model import (
    build_complementary_5fold_shards,
    dinkelbach_submodular_emit,
    extract_dcms_stage2_features,
    fit_dcms_stage1_ensemble,
    fit_dcms_stage2_calibrated_heads,
    poisson_disk_emit,
    predict_dcms_stage2,
    proc_rss_mb,
    run_dcms_quadrant_nested_oof,
    select_dinkelbach_params_inner,
    stack_dcms_shards,
    stream_predict_dcms_stage1,
)
from gems79.thvc_features import STATIC_FEATURE_NAMES as THVC_STATIC_NAMES, compute_network_mechanics as compute_thvc_mech
from gems79.thvc_model import (
    build_per_quadrant_training_shards as build_thvc_shards,
    charnes_cooper_submodular_emit,
    run_quadrant_nested_oof as run_thvc_oof,
)


def _build_combined_full_registry_index() -> dict[str, Any]:
    """Combine all 992 frozen blobs + all post-freeze delta blobs (1,201 unique blobs across 92 repos)."""
    seen_blob: dict[str, dict[str, Any]] = {}
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r["sha256"] for r in receipt["files"] if r["status"] == "verified"}
    delta = json.loads((ROOT / "registry/registry_delta.json").read_text())

    for r in index["rasters"]:
        cfile = ROOT / ".cache/registry" / f"{r['blob']}.tif"
        aliases = list(r.get("aliases") or [f"{r['repo']}:{r['path']}"])
        seen_blob[r["blob"]] = {
            "repo_first": r["repo"],
            "sources": aliases,
            "cache_file": str(cfile),
            "sha256": pins[r["blob"]],
        }
    for r in delta["rasters"]:
        cfile = ROOT / ".cache/registry" / f"{r['blob']}.tif"
        aliases = list(r.get("aliases") or [f"{r['repo']}:{r['path']}"])
        if r["blob"] in seen_blob:
            seen_blob[r["blob"]]["sources"] = sorted(set(seen_blob[r["blob"]]["sources"]) | set(aliases))
        else:
            seen_blob[r["blob"]] = {
                "repo_first": r["repo"],
                "sources": aliases,
                "cache_file": str(cfile),
                "sha256": r["sha256"],
            }
    rasters = list(seen_blob.values())
    sub_counts: dict[str, int] = {}
    for r in rasters:
        key = f"{r['repo']}:{r['path']}"
        sub_counts[key] = sub_counts.get(key, 0) + 1
    for r in rasters:
        key = f"{r['repo']}:{r['path']}"
        if sub_counts[key] > 1:
            r["path"] = f"{r['path']}@{r['blob'][:8]}"
    return {"complete_accessible_scan": True, "errors": [], "rasters": rasters}


def run_all_118_leakage_canaries(
    grid: Grid,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    dcms_cues_path: Path,
    out_json: Path,
) -> dict[str, Any]:
    """Test EVERY ONE of the 118 DCMS channels alone on BOTH Seed 20 and Seed 30 before any modeling."""
    t0 = time.time()
    out: dict[str, Any] = {
        "schema_version": 1,
        "lane": "G79-DCMS",
        "evidence_class": "LEAKAGE-CANARY",
        "threshold": 0.90,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        vis = folds[0]["visible"]
        truth = np.zeros(footprint.shape, dtype=bool)
        active = np.zeros(footprint.shape, dtype=bool)
        for f in folds:
            truth |= f["truth"]
            active |= footprint & f["region"] & ~f["masked_known"]

        pos_fp = (truth & active)[footprint]
        neg_fp = (active & ~truth)[footprint]
        pos_idx = np.flatnonzero(pos_fp)
        rng = np.random.default_rng(7900 + seed)
        neg_pool = np.flatnonzero(neg_fp)
        neg_idx = np.sort(rng.choice(neg_pool, size=min(220_000, neg_pool.size), replace=False))
        eval_idx = np.concatenate([pos_idx, neg_idx])
        y_bin = np.concatenate([np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)])

        mech = compute_dcms_mechanics(vis, footprint, dcms_cues_path)
        rows = []
        for c_i, fname in enumerate(STATIC_DCMS_NAMES):
            vals = static_mm[eval_idx, c_i].astype(np.float64)
            vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
            raw_auc = float(roc_auc_score(y_bin, vals)) if np.ptp(vals) > 0 else 0.5
            sym_auc = max(raw_auc, 1.0 - raw_auc)
            rows.append({"feature": fname, "raw_auc": round(raw_auc, 6), "symmetric_auc": round(sym_auc, 6)})
        _drop_cache(mmap_path)

        for m_i, fname in enumerate(MECH_DCMS_NAMES):
            vals = mech[eval_idx, m_i].astype(np.float64)
            vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
            raw_auc = float(roc_auc_score(y_bin, vals)) if np.ptp(vals) > 0 else 0.5
            sym_auc = max(raw_auc, 1.0 - raw_auc)
            rows.append({"feature": fname, "raw_auc": round(raw_auc, 6), "symmetric_auc": round(sym_auc, 6)})
        del mech
        gc.collect()

        worst = max(rows, key=lambda r: r["symmetric_auc"])
        passed = all(r["symmetric_auc"] <= 0.90 for r in rows)
        out[f"seed{seed}"] = {
            "seed": seed,
            "withheld_positive_pixels": int(pos_idx.size),
            "negative_pixels_sampled": int(neg_idx.size),
            "features_tested": len(rows),
            "threshold": 0.90,
            "max_symmetric_auc": worst["symmetric_auc"],
            "max_symmetric_auc_feature": worst["feature"],
            "all_passed": passed,
            "all_features": rows,
        }
        print(
            f"[canary seed={seed}] Tested {len(rows)} features | max symmetric AUC = {worst['symmetric_auc']:.6f} "
            f"({worst['feature']}) | PASS={passed}",
            flush=True,
        )
        if not passed:
            raise RuntimeError(f"LEAKAGE CANARY FAILED ON SEED {seed}: {worst}")

    out["elapsed_seconds"] = round(time.time() - t0, 2)
    out_json.write_text(json.dumps(out, indent=2) + "\n")
    return out


def _regime_decomposition(
    pred_map: dict[str, np.ndarray],
    folds: list[dict[str, Any]],
    footprint: np.ndarray,
    reg_cols_fp: np.ndarray,
    visible: np.ndarray,
) -> dict[str, Any]:
    H, W = footprint.shape
    truth_all = np.zeros((H, W), dtype=bool)
    active_all = np.zeros((H, W), dtype=bool)
    for f in folds:
        truth_all |= f["truth"]
        active_all |= footprint & f["region"] & ~f["masked_known"]

    lid_2d = np.zeros((H, W), dtype=bool)
    lid_2d[footprint] = reg_cols_fp[:, 0]
    mtn_2d = np.zeros((H, W), dtype=bool)
    mtn_2d[footprint] = reg_cols_fp[:, 1]
    sgmc_2d = np.zeros((H, W), dtype=bool)
    sgmc_2d[footprint] = reg_cols_fp[:, 2]
    d_vis = ndi.distance_transform_edt(~visible)

    regimes = {
        "lidar_covered": active_all & lid_2d,
        "blind_outside_lidar": active_all & (~lid_2d),
        "basin_and_piedmont": active_all & (~mtn_2d),
        "mountain_bedrock": active_all & mtn_2d,
        "sgmc_bedrock_reactivation_corridor": active_all & sgmc_2d,
        "near_tip_or_relay_le_1km": active_all & (d_vis <= 10.0),
        "far_blind_gt_1km": active_all & (d_vis > 10.0),
    }
    out: dict[str, Any] = {}
    for rname, rmask in regimes.items():
        n_pos = int((truth_all & rmask).sum())
        row: dict[str, Any] = {"withheld_positive_pixels": n_pos, "active_pixels": int(rmask.sum()), "scores": {}}
        for aname, pred in pred_map.items():
            res = metric.dti_binary(pred > 0, truth_all, valid=rmask)
            row["scores"][aname] = round(float(res["dti"]), 6)
        out[rname] = row
    return out


def _select_thvc_inner(p_tr_2d: np.ndarray, q_tr_2d: np.ndarray, sim_draw0: dict[str, Any], footprint: np.ndarray) -> dict[str, Any]:
    H, W = footprint.shape
    truth_in = np.zeros((H, W), dtype=bool)
    act_in = np.zeros((H, W), dtype=bool)
    truth_in[footprint] = sim_draw0["y_exact_fp"]
    act_in[footprint] = sim_draw0["active_fp"]
    known_in = footprint & (~act_in)
    allow_in = footprint & (ndi.distance_transform_edt(~known_in) > 2.0)
    best = None
    for lam, msep, mbud in [
        (0.0006, 1.9, 44_000), (0.0010, 1.9, 43_000), (0.0015, 1.9, 42_000), (0.0022, 1.9, 40_000),
        (0.0008, 2.3, 42_000), (0.0014, 2.3, 40_000), (0.0022, 2.3, 39_000), (0.0035, 2.3, 38_000),
    ]:
        em = charnes_cooper_submodular_emit(p_tr_2d, q_tr_2d, allow_in, lambda_fp=lam, min_sep_px=msep, max_budget=mbud, min_budget=20_000)
        dti_v = float(metric.dti_binary(em > 0, truth_in, valid=act_in)["dti"])
        if best is None or dti_v > best["inner_sim_dti"]:
            best = {"lambda_fp": lam, "min_sep_px": msep, "max_budget": mbud, "inner_sim_dti": dti_v}
    return best


def evaluate_seed_dcms(
    seed: int,
    grid: Grid,
    footprint: np.ndarray,
    reg_cols_fp: np.ndarray,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    dcms_cues_path: Path,
    base70_mmap_path: Path,
    base70_cues_path: Path,
    thvc_ctx_fp: np.ndarray,
    d28_bool: np.ndarray,
    fab_surface: np.ndarray,
    cache_dir: Path,
) -> dict[str, Any]:
    ckpt = cache_dir / f"dcms_eval_seed{seed}.json"
    if ckpt.exists():
        print(f"[seed={seed}] Reusing completed DCMS seed checkpoint {ckpt}", flush=True)
        return json.loads(ckpt.read_text())

    t0 = time.time()
    print(f"\n==================== G79-DCMS SEED {seed} EVALUATION ====================", flush=True)
    folds, quad = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    vis = folds[0]["visible"]
    quad_fp = quad[footprint]
    allow_vis = footprint & (ndi.distance_transform_edt(~vis) > 2.0)
    H, W = footprint.shape

    c3_npy = cache_dir / f"c3_thvc_seed{seed}.npy"
    if c3_npy.exists():
        c3_thvc_map = np.load(c3_npy)
        print(f"[seed={seed}] Loaded cached C3_g79_thvc_incumbent (dots={int((c3_thvc_map>0).sum()):,}, VmRSS={proc_rss_mb():.1f} MB)", flush=True)
    else:
        base_mm = np.memmap(base70_mmap_path, dtype="float32", mode="r", shape=(int(footprint.sum()), len(THVC_STATIC_NAMES)))
        th_shards, th_draw0 = build_thvc_shards(
            vis, footprint, quad_fp, base_mm, base70_mmap_path, base70_cues_path,
            n_draws=3, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=22_000, seed_base=7000 + seed,
        )
        th_mech = compute_thvc_mech(vis, footprint, base70_cues_path).astype(np.float16)
        th_p_fp, th_q_fp, th_ptr_fp, th_qtr_fp = run_thvc_oof(
            quad_fp, footprint, base_mm, base70_mmap_path, thvc_ctx_fp, th_shards, th_draw0, th_mech, use_mechanics=True, seed=seed * 10
        )
        del th_shards, th_mech, base_mm
        _drop_cache(base70_mmap_path)
        gc.collect()

        th_p2d = np.zeros((H, W), dtype=np.float32)
        th_q2d = np.zeros((H, W), dtype=np.float32)
        th_ptr2d = np.zeros((H, W), dtype=np.float32)
        th_qtr2d = np.zeros((H, W), dtype=np.float32)
        th_p2d[footprint] = th_p_fp
        th_q2d[footprint] = th_q_fp
        th_ptr2d[footprint] = th_ptr_fp
        th_qtr2d[footprint] = th_qtr_fp
        th_sel = _select_thvc_inner(th_ptr2d, th_qtr2d, th_draw0, footprint)
        c3_thvc_map = charnes_cooper_submodular_emit(
            th_p2d, th_q2d, allow_vis,
            lambda_fp=th_sel["lambda_fp"], min_sep_px=th_sel["min_sep_px"], max_budget=th_sel["max_budget"], min_budget=20_000,
        )
        np.save(c3_npy, c3_thvc_map)
        del th_p_fp, th_q_fp, th_ptr_fp, th_qtr_fp, th_p2d, th_q2d, th_ptr2d, th_qtr2d, th_draw0
        gc.collect()
        print(f"[seed={seed}] Paired C3_g79_thvc_incumbent ready in {time.time()-t0:.1f}s (dots={int((c3_thvc_map>0).sum()):,}, VmRSS={proc_rss_mb():.1f} MB)", flush=True)

    # 2. Build 100% full-network complementary 5-fold inner shards + checkpoint 118-ch & 98-ch OOF independently!
    oof118_npz = cache_dir / f"dcms_oof118_seed{seed}.npz"
    oof98_npz = cache_dir / f"dcms_oof98_seed{seed}.npz"

    if oof118_npz.exists() and oof98_npz.exists():
        z118 = np.load(oof118_npz)
        p_full_fp = z118["p_full_fp"].astype(np.float32)
        q_full_fp = z118["q_full_fp"].astype(np.float32)
        oof_world_preds = [
            (z118["pw0"].astype(np.float32), z118["qw0"].astype(np.float32)),
            (z118["pw1"].astype(np.float32), z118["qw1"].astype(np.float32)),
        ]
        sim_worlds = [
            {"y_exact_fp": z118["y0"].astype(bool), "active_fp": z118["act0"].astype(bool)},
            {"y_exact_fp": z118["y1"].astype(bool), "active_fp": z118["act1"].astype(bool)},
        ]
        p_zero_fp = np.load(oof98_npz)["p_zero_fp"].astype(np.float32)
        print(f"[seed={seed}] Loaded cached OOF118 + OOF98 posteriors, VmRSS={proc_rss_mb():.1f} MB", flush=True)
    else:
        t1 = time.time()
        shards, sim_worlds_full = build_complementary_5fold_shards(
            vis, footprint, quad_fp, mmap_path, dcms_cues_path,
            n_inner_folds=5, buffer_px=3, neg_per_quad_per_fold=15_000, seed_base=8100 + seed,
        )
        print(f"[seed={seed}] DCMS 5-fold complementary shards ready in {time.time()-t1:.1f}s, VmRSS={proc_rss_mb():.1f} MB", flush=True)

        if oof118_npz.exists():
            z118 = np.load(oof118_npz)
            p_full_fp = z118["p_full_fp"].astype(np.float32)
            q_full_fp = z118["q_full_fp"].astype(np.float32)
            oof_world_preds = [
                (z118["pw0"].astype(np.float32), z118["qw0"].astype(np.float32)),
                (z118["pw1"].astype(np.float32), z118["qw1"].astype(np.float32)),
            ]
            print(f"[seed={seed}] Reused cached 118-ch nested OOF {oof118_npz}", flush=True)
        else:
            t2 = time.time()
            test_mech = compute_dcms_mechanics(vis, footprint, dcms_cues_path).astype(np.float16)
            p_full_fp, q_full_fp, oof_world_preds = run_dcms_quadrant_nested_oof(
                quad_fp, footprint, mmap_path, ctx_cols_fp, shards, sim_worlds_full, test_mech, use_mechanics=True, seed=seed * 10
            )
            del test_mech
            np.savez_compressed(
                oof118_npz,
                p_full_fp=p_full_fp.astype(np.float16),
                q_full_fp=q_full_fp.astype(np.float16),
                pw0=oof_world_preds[0][0].astype(np.float16),
                qw0=oof_world_preds[0][1].astype(np.float16),
                pw1=oof_world_preds[1][0].astype(np.float16),
                qw1=oof_world_preds[1][1].astype(np.float16),
                y0=sim_worlds_full[0]["y_exact_fp"],
                act0=sim_worlds_full[0]["active_fp"],
                y1=sim_worlds_full[1]["y_exact_fp"],
                act1=sim_worlds_full[1]["active_fp"],
            )
            print(f"[seed={seed}] DCMS 118-ch nested OOF saved in {time.time()-t2:.1f}s, VmRSS={proc_rss_mb():.1f} MB", flush=True)

        if oof98_npz.exists():
            p_zero_fp = np.load(oof98_npz)["p_zero_fp"].astype(np.float32)
        else:
            t3 = time.time()
            p_zero_fp, _, _ = run_dcms_quadrant_nested_oof(
                quad_fp, footprint, mmap_path, ctx_cols_fp, shards, sim_worlds_full, None, use_mechanics=False, seed=seed * 20
            )
            np.savez_compressed(oof98_npz, p_zero_fp=p_zero_fp.astype(np.float16))
            print(f"[seed={seed}] DCMS 98-ch zero-catalogue OOF saved in {time.time()-t3:.1f}s, VmRSS={proc_rss_mb():.1f} MB", flush=True)

        sim_worlds = [
            {"y_exact_fp": sim_worlds_full[0]["y_exact_fp"].copy(), "active_fp": sim_worlds_full[0]["active_fp"].copy()},
            {"y_exact_fp": sim_worlds_full[1]["y_exact_fp"].copy(), "active_fp": sim_worlds_full[1]["active_fp"].copy()},
        ]
        del shards, sim_worlds_full
        gc.collect()

    from gems79.dcms_model import trim_heap
    trim_heap()
    print(f"[seed={seed}] Entering inner Dinkelbach selection at VmRSS={proc_rss_mb():.1f} MB", flush=True)
    dink_tune = select_dinkelbach_params_inner(oof_world_preds, sim_worlds, footprint)
    sel = dink_tune["selected"]
    print(f"[seed={seed}] Inner-validated Dinkelbach params (zero outer access): {sel} (VmRSS={proc_rss_mb():.1f} MB)", flush=True)

    del sim_worlds, oof_world_preds
    trim_heap()

    p_full_2d = np.zeros((H, W), dtype=np.float32)
    q_full_2d = np.zeros((H, W), dtype=np.float32)
    p_zero_2d = np.zeros((H, W), dtype=np.float32)
    p_full_2d[footprint] = p_full_fp
    q_full_2d[footprint] = q_full_fp
    p_zero_2d[footprint] = p_zero_fp

    rng_c0 = np.random.default_rng(79000 + seed)
    allow_flat = np.flatnonzero(allow_vis)
    c0_map = np.zeros((H, W), dtype=np.float32)
    c0_map.ravel()[rng_c0.choice(allow_flat, size=37_654, replace=False)] = 1.0
    c1_map = poisson_disk_emit(fab_surface, allow_vis, budget=37_654, min_dist_px=2.8)
    c2_map = (d28_bool & allow_vis).astype(np.float32)

    exp1_map = poisson_disk_emit(p_zero_2d, allow_vis, budget=37_654, min_dist_px=2.8)
    exp2_map = poisson_disk_emit(
        0.70 * p_full_2d + 0.30 * (np.clip(q_full_2d, 0.0, 1.0) ** 1.6) * 0.28,
        allow_vis,
        budget=37_654,
        min_dist_px=2.8,
    )
    exp3_map = dinkelbach_submodular_emit(
        p_full_2d,
        q_full_2d,
        allow_vis,
        lambda_fp=sel["lambda_fp"],
        min_sep_px=sel["min_sep_px"],
        crest_gamma=sel["crest_gamma"],
        max_budget=sel["max_budget"],
        min_budget=18_000,
    )

    preds = {
        "EXP-DCMS-3_calibrated_dinkelbach": exp3_map,
        "EXP-DCMS-2_full_network_d28": exp2_map,
        "EXP-DCMS-1_pure_physics_d28": exp1_map,
        "C3_g79_thvc_incumbent": c3_thvc_map,
        "C2_h33_analogue_foldfair": c2_map,
        "C1_fabric_offset_E1_placed": c1_map,
        "C0_random_B37654": c0_map,
    }

    terms_by_arm: dict[str, np.ndarray] = {}
    per_fold_scores: dict[str, list[dict[str, Any]]] = {}
    for arm_name, pred in preds.items():
        acc_terms = None
        f_list = []
        for f_idx, fold in enumerate(folds):
            f_res, f_terms = evaluate_holdout.evaluate(pred, fold, footprint)
            f_list.append({"fold": f_idx, "dti": round(float(f_res["dti"]), 6), "n_truth": f_res["n_truth"], "n_emitted": f_res["n_emitted"]})
            acc_terms = f_terms if acc_terms is None else (acc_terms + f_terms)
        terms_by_arm[arm_name] = acc_terms
        per_fold_scores[arm_name] = f_list

    official_eval = evaluate_holdout.pooled_summary(
        terms_by_arm, draws=1000, seed=520810 + seed, candidate="EXP-DCMS-3_calibrated_dinkelbach"
    )
    official_eval["per_fold"] = per_fold_scores
    regimes = _regime_decomposition(preds, folds, footprint, reg_cols_fp, vis)

    print(f"\n--- SEED {seed} OFFICIAL SHARED EVALUATOR RESULTS ({official_eval['evaluator_version']}) ---", flush=True)
    for k, v in official_eval["scores"].items():
        n_dots = int((preds[k] > 0).sum())
        delta_str = ""
        if k != "EXP-DCMS-3_calibrated_dinkelbach":
            pd = official_eval["paired_differences"][k]
            delta_str = f"  |  paired delta={pd['delta']:+.6f} [{pd['ci95'][0]:+.6f}, {pd['ci95'][1]:+.6f}]"
        print(
            f"  {k:34s}: HOLDOUT-DTI = {v['dti']:.6f}  95% CI [{v['ci95'][0]:.6f}, {v['ci95'][1]:.6f}]  "
            f"dots={n_dots:,}  tp_w={v['tpw']:.1f}{delta_str}",
            flush=True,
        )

    out_payload = {
        "seed": seed,
        "evaluator_version": official_eval["evaluator_version"],
        "withheld_positive_pixels": official_eval["scores"]["EXP-DCMS-3_calibrated_dinkelbach"]["withheld_positive_pixels"],
        "elapsed_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(proc_rss_mb(), 1),
        "inner_dinkelbach_selection": dink_tune,
        "official_evaluate_all": official_eval,
        "regime_decomposition": regimes,
    }
    ckpt.write_text(json.dumps(out_payload, indent=2) + "\n")
    return out_payload


def fit_live_dcms_ensemble(
    cat: np.ndarray,
    footprint: np.ndarray,
    quad: np.ndarray,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    dcms_cues_path: Path,
    seed_params: list[dict[str, Any]],
    cache_dir: Path,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    lp_npz = cache_dir / "dcms_live_posteriors.npz"
    lp_meta = cache_dir / "dcms_live_meta.json"
    if lp_npz.exists() and lp_meta.exists():
        z = np.load(lp_npz)
        H, W = footprint.shape
        pl = np.zeros((H, W), dtype=np.float32)
        ql = np.zeros((H, W), dtype=np.float32)
        pl[footprint] = z["p_live_fp"].astype(np.float32)
        ql[footprint] = z["q_live_fp"].astype(np.float32)
        return pl, ql, json.loads(lp_meta.read_text())

    t0 = time.time()
    print("\n==================== TRAINING FULL-FOOTPRINT LIVE G79-DCMS ENSEMBLE ====================", flush=True)
    quad_fp = quad[footprint]
    live_shards, live_worlds = build_complementary_5fold_shards(
        cat, footprint, quad_fp, mmap_path, dcms_cues_path,
        n_inner_folds=5, buffer_px=3, neg_per_quad_per_fold=17_000, seed_base=9300,
    )
    live_mech = compute_dcms_mechanics(cat, footprint, dcms_cues_path).astype(np.float16)

    n_fp = int(footprint.sum())
    n_worlds = len(live_worlds)
    all_rows = np.arange(n_fp, dtype=np.int64)
    all_mask = np.ones(n_fp, dtype=bool)

    live_specs = []
    for q_id in range(4):
        tr_qs = [q for q in range(4) if q != q_id]
        Xq, yq, qq, wcq, wrq, tpi_q, spi_q = stack_dcms_shards(live_shards, tr_qs, True)
        sq = fit_dcms_stage1_ensemble(Xq, yq, qq, wcq, wrq, seed=900 + q_id)
        del Xq, yq, qq, wcq, wrq
        for w_idx in range(n_worlds):
            live_specs.append((sq, live_worlds[w_idx]["mech_fp16"], tpi_q, spi_q, quad_fp == q_id))

    feat_imp = np.zeros(len(ALL_DCMS_NAMES), dtype=np.float64)
    Xf, yf, qf, wcf, wrf, tpi_f, spi_f = stack_dcms_shards(live_shards, [0, 1, 2, 3], True)
    for rep in range(2):
        sf = fit_dcms_stage1_ensemble(Xf, yf, qf, wcf, wrf, seed=1200 + 41 * rep)
        feat_imp += 0.5 * sf["deep_gain"]
        live_specs.append((sf, live_mech, tpi_f, spi_f, None))
    del Xf, yf, qf, wcf, wrf, live_shards, live_mech
    gc.collect()

    stream_res = stream_predict_dcms_stage1(live_specs, mmap_path, n_fp, use_mechanics=True)
    del live_specs
    gc.collect()

    oof_p1_w = [np.zeros(n_fp, dtype=np.float32) for _ in range(n_worlds)]
    oof_q1_w = [np.zeros(n_fp, dtype=np.float32) for _ in range(n_worlds)]
    cur = 0
    for q_id in range(4):
        va_r = np.flatnonzero(quad_fp == q_id)
        for w_idx in range(n_worlds):
            oof_p1_w[w_idx][va_r] = stream_res[cur][0][va_r]
            oof_q1_w[w_idx][va_r] = stream_res[cur][1][va_r]
            cur += 1
    p1_live = 0.5 * (stream_res[cur][0] + stream_res[cur + 1][0])
    q1_live = 0.5 * (stream_res[cur][1] + stream_res[cur + 1][1])
    del stream_res
    gc.collect()

    S2_oof_worlds = [extract_dcms_stage2_features(oof_p1_w[w], oof_q1_w[w], footprint, ctx_cols_fp) for w in range(n_worlds)]
    del oof_p1_w, oof_q1_w
    s2_live = fit_dcms_stage2_calibrated_heads(S2_oof_worlds, live_worlds, all_mask, seed=979)
    del S2_oof_worlds, live_worlds
    gc.collect()

    S2_live = extract_dcms_stage2_features(p1_live, q1_live, footprint, ctx_cols_fp)
    p2_live_fp, q2_live_fp = predict_dcms_stage2(s2_live, S2_live, all_rows)
    del S2_live, s2_live
    gc.collect()

    H, W = footprint.shape
    p_live_2d = np.zeros((H, W), dtype=np.float32)
    q_live_2d = np.zeros((H, W), dtype=np.float32)
    p_live_2d[footprint] = p2_live_fp
    q_live_2d[footprint] = q2_live_fp

    top_imp = sorted(
        [{"feature": ALL_DCMS_NAMES[i], "gain_share": round(float(feat_imp[i] / max(feat_imp.sum(), 1e-9)), 6)} for i in range(len(ALL_DCMS_NAMES))],
        key=lambda r: -r["gain_share"],
    )
    meta_live = {
        "live_train_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(proc_rss_mb(), 1),
        "top25_features_by_gain": top_imp[:25],
        "dinkelbach_params_by_seed": seed_params,
    }
    np.savez_compressed(lp_npz, p_live_fp=p2_live_fp.astype(np.float16), q_live_fp=q2_live_fp.astype(np.float16))
    lp_meta.write_text(json.dumps(meta_live, indent=2) + "\n")
    print(f"Live DCMS ensemble complete in {meta_live['live_train_seconds']}s! Top 8 features: {top_imp[:8]}", flush=True)
    return p_live_2d, q_live_2d, meta_live


def audit_1201_rasters(candidate_tif: Path, footprint: np.ndarray, label_tag: str, combined_idx: dict[str, Any]) -> dict[str, Any]:
    t0 = time.time()
    n_tot = len(combined_idx["rasters"])
    print(f"\n[uniqueness:{label_tag}] Running unmodified gems57.uniqueness across {n_tot} family blobs...", flush=True)
    merged = uniqueness.compare_to_registry(candidate_tif, combined_idx, footprint)
    phase = uniqueness.two_phase_summary(merged["rows"], int(footprint.sum()), expected_rasters=n_tot)
    valid_rhos = [
        abs(float(r["spearman_full_footprint"]))
        for r in merged["rows"]
        if r.get("spearman_full_footprint") is not None and np.isfinite(r["spearman_full_footprint"])
    ]
    max_abs_rho = float(max(valid_rhos)) if valid_rhos else 0.0
    non_grid = [r for r in merged["rows"] if "error" in r]
    sparse_50k = [r for r in merged["rows"] if "error" not in r and int(r.get("their_dots", 0)) <= 50_000]
    sparse_60k = [r for r in merged["rows"] if "error" not in r and int(r.get("their_dots", 0)) <= 60_000]
    worst_50k = max(sparse_50k, key=lambda r: float(r["my_dots_within_3px_of_theirs"]))
    worst_60k = max(sparse_60k, key=lambda r: float(r["my_dots_within_3px_of_theirs"]))

    merged["max_abs_spearman"] = round(max_abs_rho, 6)
    merged["non_comparable_entries"] = non_grid
    merged["two_phase_summary"] = phase
    merged["audit_elapsed_seconds"] = round(time.time() - t0, 2)
    merged["sparse_le_50k_worst"] = {
        "repo": worst_50k["repo"],
        "submission": worst_50k["submission"],
        "their_dots": worst_50k["their_dots"],
        "forward_overlap_3px": round(float(worst_50k["my_dots_within_3px_of_theirs"]), 6),
    }
    merged["sparse_le_60k_worst"] = {
        "repo": worst_60k["repo"],
        "submission": worst_60k["submission"],
        "their_dots": worst_60k["their_dots"],
        "forward_overlap_3px": round(float(worst_60k["my_dots_within_3px_of_theirs"]), 6),
    }
    print(
        f"[uniqueness:{label_tag}] Done in {merged['audit_elapsed_seconds']}s | "
        f"comparable={merged['registry_rasters_checked']}/{merged['registry_rasters_expected']} | "
        f"max |Spearman|={merged['max_abs_spearman']} | "
        f"sparse<=50k max={merged['sparse_le_50k_worst']['forward_overlap_3px']} ({merged['sparse_le_50k_worst']['submission']}) | "
        f"sparse<=60k max={merged['sparse_le_60k_worst']['forward_overlap_3px']} | "
        f"literal max={merged['worst_dot_overlap']}",
        flush=True,
    )
    return merged


def make_dcms_figures(
    eval20: dict[str, Any],
    eval30: dict[str, Any],
    live_meta: dict[str, Any],
    dot_audit: dict[str, Any],
    surf_audit: dict[str, Any],
    p_live_2d: np.ndarray,
    q_live_2d: np.ndarray,
    emitted_2d: np.ndarray,
    cat: np.ndarray,
    footprint: np.ndarray,
) -> list[str]:
    fig_dir = ROOT / "docs" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

    fig, axes = plt.subplots(1, 2, figsize=(15.2, 5.8), dpi=160)
    arms_order = [
        ("C1_fabric_offset_E1_placed", "C1 Prior G79\nFabric-Offset"),
        ("C0_random_B37654", "C0 Random\n(37,654 dots)"),
        ("C2_h33_analogue_foldfair", "C2 H33 Family\nBest (0.2778)"),
        ("EXP-DCMS-1_pure_physics_d28", "EXP-DCMS-1 Pure\n98-ch Physics"),
        ("C3_g79_thvc_incumbent", "C3 G79-THVC\nPrior Incumbent"),
        ("EXP-DCMS-2_full_network_d28", "EXP-DCMS-2 118-ch\nUniform d=2.8"),
        ("EXP-DCMS-3_calibrated_dinkelbach", "EXP-DCMS-3 DCMS\nCalib Dinkelbach"),
    ]
    colors = ["#f59e0b", "#94a3b8", "#64748b", "#0ea5e9", "#7c3aed", "#2563eb", "#059669"]
    for ax, ev, title in [
        (axes[0], eval20, f"Primary Shared Holdout (seed=20, n={eval20['withheld_positive_pixels']:,} px)"),
        (axes[1], eval30, f"Independent Secondary Holdout (seed=30, n={eval30['withheld_positive_pixels']:,} px)"),
    ]:
        sc = ev["official_evaluate_all"]["scores"]
        ys = np.arange(len(arms_order))
        vals = [sc[k]["dti"] for k, _ in arms_order]
        lo = [vals[i] - sc[k]["ci95"][0] for i, (k, _) in enumerate(arms_order)]
        hi = [sc[k]["ci95"][1] - vals[i] for i, (k, _) in enumerate(arms_order)]
        upper_tips = [vals[i] + hi[i] for i in range(len(vals))]
        bars = ax.barh(ys, vals, xerr=[lo, hi], color=colors, capsize=4, height=0.62, edgecolor="#0f172a", linewidth=0.7)
        ax.axvline(sc["C2_h33_analogue_foldfair"]["dti"], ls="--", lw=1.2, color="#dc2626", label="H33 Fold-Fair Baseline")
        ax.axvline(sc["C3_g79_thvc_incumbent"]["dti"], ls=":", lw=1.4, color="#7c3aed", label="Prior G79-THVC Bar")
        ax.set_yticks(ys, [lbl for _, lbl in arms_order])
        ax.set_xlabel("HOLDOUT-DTI (gems57-pooled-hide-v2, 95% Physical Spatial-Cluster Bootstrap CI)")
        ax.set_title(title, fontweight="bold")
        ax.set_xlim(0, max(upper_tips) * 1.22)
        ax.legend(loc="lower right", fontsize=8.5)
        ax.grid(axis="x", alpha=0.25)
        for bar, v, ut in zip(bars, vals, upper_tips):
            ax.text(ut + max(upper_tips) * 0.018, bar.get_y() + bar.get_height() / 2, f"{v:.4f}", va="center", fontweight="bold", fontsize=9)
    fig.suptitle("GEMSDOE79 (G79-DCMS) — Dual-Seed Shared Spatially-Blocked Holdout Progression", fontweight="bold", fontsize=12.5)
    fig.tight_layout()
    f1 = fig_dir / "fig1_dcms_holdout_progression.png"
    fig.savefig(f1)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14.8, 5.8), dpi=160)
    reg = eval20["regime_decomposition"]
    r_keys = [
        ("lidar_covered", "1-m LiDAR\nCovered"),
        ("blind_outside_lidar", "Blind Non-LiDAR\n(25.5% Gap)"),
        ("basin_and_piedmont", "Basin & Piedmont\nConduits"),
        ("mountain_bedrock", "Mountain\nBedrock"),
        ("sgmc_bedrock_reactivation_corridor", "USGS DS-1052\nSGMC Corridor"),
        ("near_tip_or_relay_le_1km", "Crack Tip / Relay\n(<=1 km)"),
        ("far_blind_gt_1km", "Far Blind Basin\n(>1 km)"),
    ]
    x = np.arange(len(r_keys))
    w = 0.26
    axes[0].bar(x - w, [reg[k]["scores"]["C2_h33_analogue_foldfair"] for k, _ in r_keys], width=w, color="#64748b", label="C2 H33 Baseline")
    axes[0].bar(x, [reg[k]["scores"]["C3_g79_thvc_incumbent"] for k, _ in r_keys], width=w, color="#7c3aed", label="C3 G79-THVC Prior")
    axes[0].bar(x + w, [reg[k]["scores"]["EXP-DCMS-3_calibrated_dinkelbach"] for k, _ in r_keys], width=w, color="#059669", label="EXP-DCMS-3 (Active)")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([lbl for _, lbl in r_keys], rotation=20, ha="right", fontsize=8.5)
    axes[0].set_ylabel("Regime HOLDOUT-DTI (seed=20)")
    axes[0].set_title("Regime-by-Regime Discovery Breakdown", fontweight="bold")
    axes[0].legend(fontsize=8.5)
    axes[0].grid(axis="y", alpha=0.25)

    top15 = live_meta["top25_features_by_gain"][:15][::-1]
    axes[1].barh([r["feature"] for r in top15], [r["gain_share"] * 100.0 for r in top15], color="#0284c7", edgecolor="#0f172a", linewidth=0.6)
    axes[1].set_xlabel("Share of Stage-1 Gain (%)")
    axes[1].set_title("Top 15 Dip-Coupled, Scarp, Bedrock & Hydrothermal Channels", fontweight="bold")
    axes[1].grid(axis="x", alpha=0.25)
    fig.tight_layout()
    f2 = fig_dir / "fig2_dcms_regimes_and_features.png"
    fig.savefig(f2)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.0), dpi=160)
    sp_vals = [
        abs(float(r["spearman_full_footprint"]))
        for r in surf_audit["rows"]
        if r.get("spearman_full_footprint") is not None and np.isfinite(r["spearman_full_footprint"])
    ]
    dot_vals = [
        float(r["my_dots_within_3px_of_theirs"])
        for r in dot_audit["rows"]
        if "error" not in r and int(r.get("their_dots", 0)) <= 60_000
    ]
    axes[0].hist(sp_vals, bins=40, color="#0284c7", edgecolor="white")
    axes[0].axvline(0.90, color="#dc2626", ls="--", lw=1.6, label="Protocol Gate |rho| <= 0.90")
    axes[0].set_xlabel(f"|Spearman rho| Across Full {int(footprint.sum()):,}-Pixel Footprint")
    axes[0].set_ylabel("Count of Prior Family Rasters")
    axes[0].set_title(f"Pre-Placement Surface vs {len(sp_vals):,} Rasters (Max={max(sp_vals):.4f})", fontweight="bold")
    axes[0].legend()

    axes[1].hist(dot_vals, bins=40, color="#059669", edgecolor="white")
    axes[1].axvline(0.70, color="#dc2626", ls="--", lw=1.6, label="Protocol Gate 3-px Overlap <= 0.70")
    axes[1].set_xlabel("3-Pixel Forward Overlap vs Sparse Family Submissions (<=60k dots)")
    axes[1].set_ylabel("Count of Sparse Dot Rasters")
    axes[1].set_title(f"Placed Dots vs {len(dot_vals):,} Sparse Rasters (Max={max(dot_vals):.4f}; Universal Witness=1.0)", fontweight="bold", fontsize=9.5)
    axes[1].legend()
    fig.tight_layout()
    f3 = fig_dir / "fig3_dcms_uniqueness_1201_audit.png"
    fig.savefig(f3)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13.4, 6.1), dpi=160)
    vis_q = np.where(footprint, q_live_2d, np.nan)
    im0 = axes[0].imshow(vis_q[::4, ::4], cmap="inferno", vmin=0.0, vmax=np.nanpercentile(vis_q, 99.5))
    axes[0].set_title("G79-DCMS Calibrated 300-m Kernel Credit q_300m(x)", fontweight="bold")
    axes[0].axis("off")
    fig.colorbar(im0, ax=axes[0], fraction=0.042, pad=0.02)

    axes[1].imshow(np.where(footprint, 0.08, np.nan)[::4, ::4], cmap="Greys", vmin=0, vmax=1)
    cy, cx = np.nonzero(cat[::2, ::2])
    axes[1].scatter(cx / 2.0, cy / 2.0, s=0.14, c="#64748b", alpha=0.45, label="Mapped Catalogue (Masked)")
    ey, ex = np.nonzero(emitted_2d)
    axes[1].scatter(ex / 4.0, ey / 4.0, s=0.26, c="#047857", alpha=0.82, label=f"G79-DCMS Placed Dots ({int((emitted_2d>0).sum()):,})")
    axes[1].set_title("G79-DCMS Binary GeoTIFF Geometry vs Mapped Faults", fontweight="bold")
    axes[1].legend(loc="lower right", markerscale=12, fontsize=8.5, framealpha=0.94)
    axes[1].axis("off")
    fig.tight_layout()
    f4 = fig_dir / "fig4_dcms_live_map_overview.png"
    fig.savefig(f4)
    plt.close(fig)

    return [str(p.relative_to(ROOT)) for p in (f1, f2, f3, f4)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=("canaries", "seed20", "seed30", "eval", "live_and_audit", "all"))
    args = ap.parse_args()

    t_all = time.time()
    cache_dir = ROOT / ".cache" / "g79_dcms"
    cache_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
        transform = ds.transform
        crs = ds.crs
    with rasterio.open(ROOT / "data/raw/existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & footprint

    grid = Grid(footprint, cat, str(crs), transform, footprint.shape[0], footprint.shape[1])

    static_meta = build_dcms_static_memmap(
        ROOT / "data/raw",
        ROOT / ".cache/official_ing",
        ROOT / "data/cache/dem10",
        cache_dir,
        footprint,
        transform,
    )
    mmap_path = cache_dir / "static_fp98.f32.mmap"
    dcms_cues_path = Path(static_meta["dcms_cues_path"])
    base70_mmap_path = cache_dir / "base_fp70.f32.mmap"
    base70_cues_path = Path(static_meta["base_cues_path"])

    static_mm = np.memmap(mmap_path, dtype="float32", mode="r", shape=(int(footprint.sum()), len(STATIC_DCMS_NAMES)))
    cmap = {n: i for i, n in enumerate(STATIC_DCMS_NAMES)}
    ctx_cols_fp = np.column_stack(
        [
            static_mm[:, cmap["lidar_present"]],
            static_mm[:, cmap["scarp_unified_step"]],
            static_mm[:, cmap["hydro_demag_clay_conj"]],
            static_mm[:, cmap["mountain_wall_ratio"]],
            static_mm[:, cmap["dem10_scarp_focus_nosym"]],
            static_mm[:, cmap["grav_dip_asymmetry"]],
            static_mm[:, cmap["sgmc_corridor_400m"]],
        ]
    ).astype(np.float16)
    reg_cols_fp = np.column_stack(
        [
            static_mm[:, cmap["lidar_present"]] > 0.5,
            static_mm[:, cmap["mountain_wall_ratio"]] > 0.35,
            static_mm[:, cmap["sgmc_corridor_400m"]] > 0.30,
        ]
    )
    thvc_ctx_fp = ctx_cols_fp[:, :4].copy()

    canary_path = ROOT / "evidence/dcms_leakage_canary.json"
    if args.stage in ("canaries", "all") or not canary_path.exists():
        run_all_118_leakage_canaries(grid, footprint, static_mm, mmap_path, dcms_cues_path, canary_path)
    del static_mm
    _drop_cache(mmap_path)
    gc.collect()
    if args.stage == "canaries":
        return

    with rasterio.open(ROOT / ".cache/registry/bfb7e86d046dd178c3d6ab60522861b5464dd420.tif") as ds:
        d28_bool = (ds.read(1) > 0) & footprint
    with rasterio.open(ROOT / "archive/g79_fabric_offset_f61b17a2/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif") as ds:
        fab_surface = np.nan_to_num(ds.read(1).astype(np.float32), nan=0.0) * footprint

    if args.stage in ("seed20", "eval", "all"):
        eval20 = evaluate_seed_dcms(
            20, grid, footprint, reg_cols_fp, mmap_path, ctx_cols_fp, dcms_cues_path,
            base70_mmap_path, base70_cues_path, thvc_ctx_fp, d28_bool, fab_surface, cache_dir,
        )
        if args.stage == "seed20":
            return
    if args.stage in ("seed30", "eval", "all"):
        eval30 = evaluate_seed_dcms(
            30, grid, footprint, reg_cols_fp, mmap_path, ctx_cols_fp, dcms_cues_path,
            base70_mmap_path, base70_cues_path, thvc_ctx_fp, d28_bool, fab_surface, cache_dir,
        )
        if args.stage in ("seed30", "eval"):
            return

    eval20 = json.loads((cache_dir / "dcms_eval_seed20.json").read_text())
    eval30 = json.loads((cache_dir / "dcms_eval_seed30.json").read_text())

    _, quad_live = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)
    p_live_2d, q_live_2d, live_meta = fit_live_dcms_ensemble(
        cat, footprint, quad_live, mmap_path, ctx_cols_fp, dcms_cues_path,
        [eval20["inner_dinkelbach_selection"]["selected"], eval30["inner_dinkelbach_selection"]["selected"]],
        cache_dir,
    )

    # Gate 1: Full 1,201-raster pre-placement continuous surface uniqueness scan BEFORE dot placement!
    surf_blend = (0.70 * np.clip(p_live_2d, 0.0, 1.0) + 0.30 * (np.clip(q_live_2d, 0.0, 1.0) ** 1.6) * 0.28).astype(np.float32)
    smax = float(surf_blend[footprint & ~cat].max())
    surf_norm = np.where(footprint & ~cat, np.clip(surf_blend / max(smax, 1e-9), 0.0, 1.0), 0.0).astype(np.float32)
    tmp_surf = cache_dir / "g79_dcms_preplacement_surface.tif"
    for f_old in cache_dir.glob("g79_dcms_preplacement_surface.*"):
        f_old.unlink()
    submission_writer.write_submission(
        tmp_surf,
        surf_norm,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name="g79-dcms-preplacement-surface",
        note="Pre-placement continuous posterior surface for 1,201-raster uniqueness check",
        catalogue=cat,
    )
    combined_idx = _build_combined_full_registry_index()
    surf_audit_path = ROOT / "evidence/dcms_surface_uniqueness_1201.json"
    if surf_audit_path.exists():
        surf_audit = json.loads(surf_audit_path.read_text())
        print(f"Reused completed pre-placement surface audit ({surf_audit['registry_rasters_checked']}/{surf_audit['registry_rasters_expected']} blobs, max |Spearman|={surf_audit['max_abs_spearman']})", flush=True)
    else:
        surf_audit = audit_1201_rasters(tmp_surf, footprint, "pre_placement_surface", combined_idx)
        surf_audit_path.write_text(json.dumps(surf_audit, indent=2) + "\n")
    if surf_audit["max_abs_spearman"] > 0.90:
        raise RuntimeError(f"PRE-PLACEMENT DUPLICATE SURFACE DETECTED: |rho|={surf_audit['max_abs_spearman']} > 0.90")

    # Gate 2: Consensus inner-validated Dinkelbach emission (zero outer access, zero post-hoc overlap cap!)
    s20_p = eval20["inner_dinkelbach_selection"]["selected"]
    s30_p = eval30["inner_dinkelbach_selection"]["selected"]
    consensus_lam = round(0.5 * (s20_p["lambda_fp"] + s30_p["lambda_fp"]), 5)
    consensus_sep = round(0.5 * (s20_p["min_sep_px"] + s30_p["min_sep_px"]), 3)
    consensus_gam = round(0.5 * (s20_p["crest_gamma"] + s30_p["crest_gamma"]), 3)
    consensus_maxb = int(round(0.5 * (s20_p["max_budget"] + s30_p["max_budget"])))

    allow_live = footprint & (ndi.distance_transform_edt(~cat) > 2.0)
    emitted_live = dinkelbach_submodular_emit(
        p_live_2d,
        q_live_2d,
        allow_live,
        lambda_fp=consensus_lam,
        min_sep_px=consensus_sep,
        crest_gamma=consensus_gam,
        max_budget=consensus_maxb,
        min_budget=18_000,
    )

    stage_out = cache_dir / "staged_artifact"
    stage_out.mkdir(parents=True, exist_ok=True)
    for f_old in stage_out.glob("*"):
        f_old.unlink()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_hash = hashlib.sha256(emitted_live.tobytes()).hexdigest()[:8]
    # Because universal witness 17GEMSDOE:E-proba-multiscale forces literal overlap = 1.0000,
    # filename AND submission_name match path.stem with unmistakable -DO-NOT-SUBMIT tag per verify_project.py!
    stem = f"g79-dcms-dipcoupled-20261022-{raw_hash}-zeros-DO-NOT-SUBMIT"
    sub_name = stem
    note = (
        f"GEMSDOE79 G79-DCMS DO-NOT-SUBMIT: dip-coupled+10m3DEP+SGMC+hydro 2-stage + Dinkelbach ({int((emitted_live>0).sum())} px)"
    )[:140]

    staged_tif = stage_out / f"{stem}.tif"
    manifest = submission_writer.write_submission(
        staged_tif,
        emitted_live,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name=sub_name,
        note=note,
        catalogue=cat,
        metadata={
            "lane": "G79-DCMS",
            "consensus_dinkelbach": {
                "lambda_fp": consensus_lam,
                "min_sep_px": consensus_sep,
                "crest_gamma": consensus_gam,
                "max_budget": consensus_maxb,
            },
            "holdout_dti_seed20": eval20["official_evaluate_all"]["scores"]["EXP-DCMS-3_calibrated_dinkelbach"],
            "holdout_dti_seed30": eval30["official_evaluate_all"]["scores"]["EXP-DCMS-3_calibrated_dinkelbach"],
            "generated_timestamp_utc": ts,
        },
    )

    dot_audit = audit_1201_rasters(staged_tif, footprint, "post_placement_dots", combined_idx)
    dot_audit_path = ROOT / "evidence/dcms_dot_uniqueness_1201.json"
    dot_audit_path.write_text(json.dumps(dot_audit, indent=2) + "\n")

    # Also measure overlap against EVERY local GEMSDOE79 historical GeoTIFF (including G79-THVC!)
    local_peers = {
        "G79-THVC": ROOT / "archive/g79_thvc_33e1f8ec/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif",
        "H79-NHR": ROOT / "archive/h79_nhr/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif",
        "H79-FNHR": ROOT / "archive/h79_fnhr_a57e2a7f/gems79-h79-fnhr-f3-37654dots-20261022T051800Z-fae5cf3a-DO-NOT-SUBMIT.tif",
        "H79-DILSTEP": ROOT / "archive/h79_dilstep_6444be2d/downloads/gems79-h79-dilstep-research-37654dots-20261022T045200Z-7dd0d54b-DO-NOT-SUBMIT.tif",
        "G79-CFSKD": ROOT / "archive/g79_cfskd_bda00cff/g79-cfskd-exp3-20261022-bda00cff-zeros-DO-NOT-SUBMIT.tif",
        "G79-MAG": ROOT / "archive/g79_mag_730d5ee7/downloads/gems79-g79-mag-37654dots-20261022T060000Z-e48a9293.tif",
        "G79-ETP-v1": ROOT / "archive/g79_etp_incoming_45998a01/downloads/g79-etp-elastic-tip-28761dots-20261022T140921Z-e2203dcf-zeros.tif",
        "G79-ETP-v2": ROOT / "archive/g79_etp_incoming_45998a01/downloads/g79-etp-relay-ramp-34500dots-20261022T140951Z-ce6c5fca-zeros.tif",
    }
    local_overlaps = {}
    for pname, ppath in local_peers.items():
        if ppath.exists():
            with rasterio.open(ppath) as ds:
                parr = (ds.read(1) > 0) & footprint
            local_overlaps[pname] = {
                "path": str(ppath.relative_to(ROOT)),
                "sha256": hashlib.sha256(ppath.read_bytes()).hexdigest(),
                "their_dots": int(parr.sum()),
                "forward_overlap_3px": round(float(uniqueness.dot_overlap(emitted_live > 0, parr)), 6),
                "reverse_overlap_3px": round(float(uniqueness.dot_overlap(parr, emitted_live > 0)), 6),
            }
            print(f"  [local-peer {pname:12s}] forward_3px={local_overlaps[pname]['forward_overlap_3px']:.6f}", flush=True)

    figs = make_dcms_figures(eval20, eval30, live_meta, dot_audit, surf_audit, p_live_2d, q_live_2d, emitted_live, cat, footprint)

    results_doc = {
        "schema_version": 1,
        "lane": "G79-DCMS",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runtime_seconds": round(time.time() - t_all, 2),
        "static_feature_meta": static_meta,
        "seed20": eval20,
        "seed30": eval30,
        "live_model_meta": live_meta,
        "submission_manifest": manifest,
        "local_gems79_peer_overlaps": local_overlaps,
        "pre_placement_surface_audit_summary": {
            "checked": surf_audit["registry_rasters_checked"],
            "expected": surf_audit["registry_rasters_expected"],
            "missing_or_invalid": surf_audit["missing_or_invalid"],
            "max_abs_spearman": surf_audit["max_abs_spearman"],
            "sparse_le_50k_worst": surf_audit["sparse_le_50k_worst"],
            "sparse_le_60k_worst": surf_audit["sparse_le_60k_worst"],
        },
        "post_placement_dot_audit_summary": {
            "checked": dot_audit["registry_rasters_checked"],
            "expected": dot_audit["registry_rasters_expected"],
            "missing_or_invalid": dot_audit["missing_or_invalid"],
            "max_abs_spearman": dot_audit["max_abs_spearman"],
            "sparse_le_50k_worst": dot_audit["sparse_le_50k_worst"],
            "sparse_le_60k_worst": dot_audit["sparse_le_60k_worst"],
            "two_phase_summary": dot_audit["two_phase_summary"],
        },
        "figures": figs,
    }
    (ROOT / "evidence/dcms_results.json").write_text(json.dumps(results_doc, indent=2) + "\n")
    print("\nG79-DCMS STAGE COMPLETE! Staged GeoTIFF:", staged_tif, "SHA-256:", manifest["sha256"], flush=True)


if __name__ == "__main__":
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "G79-DCMS",
        reason="G79-DCMS completed its preregistered 3-experiment protocol and is closed; receipts in evidence/dcms_*.json and docs/downloads/ are frozen.",
    )
    main()
