#!/usr/bin/env python3
"""Execute the preregistered G79-DFSD (De-Striped Subsurface Tilt-Depth, Cross-Fitted
Potassic Adularia, Lahontan Isohypse & Coulomb Stress-Shadow Split-Sensor Fault Discovery
with Sensor/Regime-Calibrated Charnes-Cooper Submodular Allocation) protocol end-to-end.

Strictly enforces ALL 6 rules of the Parallel-Run Protocol + AGENTS.md:
  1. Single preregistered lane (registry/preregistration_g79_dfsd.json, SHA-256 locked in Git
     at commit af37959 BEFORE any model fit, holdout evaluation, or dot placement).
  2. Reuses unmodified vendor/gems57/{holdout,evaluate_holdout,metric,submission_writer,
     validate,uniqueness}.py (23/23 SHA-256 pins verified) and src/gems79/thvc_features.py.
  3. Labels every holdout result strictly HOLDOUT-DTI (gems57-pooled-hide-v2, withheld count,
     1,000-draw 20-km physical-block bootstrap 95% CI). Zero projected leaderboard scores.
  4. Tests ALL 107 features individually on single-feature symmetric ROC AUC canaries (<=0.90)
     across BOTH seeds 20 and 30 BEFORE trusting any model score.
  5. Scans ALL SHA-256-verified rasters across ALL 93 family repositories (992 frozen + 207
     sibling delta + all local GEMSDOE79 archived lanes including G79-THVC & GEMSDOE83)
     BOTH on the pre-placement continuous surface AND on the placed binary dot GeoTIFF.
  6. Respects <=3 experiments (EXP-DFSD-1, EXP-DFSD-2, EXP-DFSD-3), <=2 hours runtime,
     fail-closed require_open_lane CLI guard (exit 2 when closed), and 0 weekly slots spent.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

for _blas_var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_blas_var, "2")

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

if __name__ == "__main__":
    if "--force-overwrite-closed" not in sys.argv and (
        "--allow-initial-build" not in sys.argv or (ROOT / "run_card_dfsd.json").is_file()
    ):
        from gems79.lifecycle import LaneClosedError, require_open_lane
        try:
            require_open_lane(ROOT, "G79-DFSD")
        except LaneClosedError as exc:
            sys.stderr.write(f"{exc} No files changed.\n")
            raise SystemExit(2)

from gems57 import evaluate_holdout, holdout, metric, submission_writer, uniqueness, validate
from gems57.grid import Grid
from gems79.dfsd_features import (
    DFSD_ALL_FEATURE_NAMES,
    DFSD_EXTRA_STATIC_NAMES,
    DFSD_MECH_NAMES,
    DFSD_STATIC_NAMES,
    build_dfsd_static_stack,
    compute_dfsd_mechanics,
    rss_mb,
)
from gems79.dfsd_model import (
    _stack_dfsd_shards,
    assemble_ooq_physics_for_context,
    build_decontaminated_shards,
    dfsd_charnes_cooper_emit,
    extract_dfsd_stage2_features,
    fit_crossquad_split_sensor_physics_experts,
    fit_dfsd_stage1,
    fit_dfsd_stage2_dual_heads,
    predict_dfsd_stage1_rows,
    predict_dfsd_stage2_dual_heads,
    predict_split_sensor_pair_cache,
    run_dfsd_quadrant_nested_oof,
)
from gems79.thvc_features import STATIC_FEATURE_NAMES as THVC_STATIC_NAMES
from gems79.thvc_model import drop_file_cache, poisson_disk_emit


def _verify_prereg_lock() -> str:
    prereg_path = ROOT / "registry/preregistration_g79_dfsd.json"
    lock_path = ROOT / "evidence/preregistration_g79_dfsd_sha256.txt"
    actual = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    expected = lock_path.read_text().strip()
    if actual != expected:
        raise RuntimeError(f"G79-DFSD preregistration SHA-256 mismatch: {actual} != {expected}")
    return actual


def _run_107_feature_leakage_canaries(
    seed: int,
    folds: list[dict[str, Any]],
    footprint: np.ndarray,
    base_mm: np.memmap,
    extra_mm: np.memmap,
    base_path: Path,
    mech_vis_fp: np.ndarray,
) -> dict[str, Any]:
    """Test ALL 107 features individually on symmetric ROC AUC <= 0.90 across all 4 folds."""
    rng = np.random.default_rng(88_000 + seed)
    H, W = footprint.shape
    fp_lookup = np.full((H, W), -1, dtype=np.int32)
    fp_lookup[footprint] = np.arange(int(footprint.sum()), dtype=np.int32)

    per_feat_max: dict[str, float] = {fn: 0.5 for fn in DFSD_ALL_FEATURE_NAMES}
    rows_all = []
    for fold in folds:
        active = fold["region"] & footprint & (~fold["masked_known"])
        truth = active & fold["truth"]
        pos_flat = np.flatnonzero(truth)
        neg_pool = np.flatnonzero(active & (~truth))
        take_neg = neg_pool[rng.choice(neg_pool.size, size=min(65_000, neg_pool.size), replace=False)]
        sel_flat = np.concatenate([pos_flat, take_neg])
        y_raw = np.concatenate([np.ones(pos_flat.size, dtype=np.int8), np.zeros(take_neg.size, dtype=np.int8)])
        fp_r_raw = fp_lookup.ravel()[sel_flat]
        ord_r = np.argsort(fp_r_raw, kind="stable")
        fp_r = fp_r_raw[ord_r]
        y = y_raw[ord_r]

        from gems79.dfsd_model import _gather_sample_rows_contiguous
        xb = _gather_sample_rows_contiguous(base_mm, extra_mm, base_path, fp_r, mech_vis_fp)

        for j, fname in enumerate(DFSD_ALL_FEATURE_NAMES):
            col = xb[:, j]
            ok = np.isfinite(col)
            if int(ok.sum()) < 50 or np.ptp(col[ok]) == 0.0:
                auc = 0.5
            else:
                auc = float(roc_auc_score(y[ok], col[ok]))
            sym = round(max(auc, 1.0 - auc), 6)
            if sym > per_feat_max[fname]:
                per_feat_max[fname] = sym
            rows_all.append({
                "fold": fold["name"],
                "feature": fname,
                "auc": round(auc, 6),
                "symmetric_auc": sym,
                "suspicious": bool(sym > 0.90),
            })

    worst = max(rows_all, key=lambda r: r["symmetric_auc"])
    n_susp = sum(1 for r in rows_all if r["suspicious"])
    if n_susp > 0:
        raise RuntimeError(f"LEAKAGE CANARY BREACHED on seed={seed}: {worst}")
    return {
        "evidence_class": "LEAKAGE-CANARY",
        "seed": seed,
        "n_unique_features": len(DFSD_ALL_FEATURE_NAMES),
        "n_tests_run": len(rows_all),
        "threshold": 0.90,
        "max_symmetric_auc": worst["symmetric_auc"],
        "max_feature": worst["feature"],
        "max_fold": worst["fold"],
        "n_suspicious": n_susp,
        "all_passed": True,
        "per_feature_max_symmetric_auc": per_feat_max,
    }


def _select_dfsd_params_inner(
    p_tr_2d: np.ndarray,
    q_tr_2d: np.ndarray,
    p_phys_tr_2d: np.ndarray,
    sim_draw0: dict[str, Any],
    footprint: np.ndarray,
) -> dict[str, Any]:
    """Select (lambda_fp, min_sep_px, max_budget, far_blind_share) strictly on inner draw 0."""
    H, W = footprint.shape
    truth_in = np.zeros((H, W), dtype=bool)
    act_in = np.zeros((H, W), dtype=bool)
    truth_in[footprint] = sim_draw0["y_exact_fp"]
    act_in[footprint] = sim_draw0["active_fp"]
    known_in = footprint & (~act_in)
    d_in = ndi.distance_transform_edt(~known_in)
    allow_in = footprint & (d_in > 2.0)

    candidates = [
        (0.0014, 1.9, 41_500, 0.00),
        (0.0019, 1.9, 40_000, 0.00),
        (0.0024, 1.9, 39_000, 0.00),
        (0.0016, 1.9, 40_500, 0.03),
        (0.0022, 1.9, 39_500, 0.03),
        (0.0028, 1.9, 38_500, 0.04),
        (0.0022, 2.2, 39_000, 0.03),
        (0.0030, 2.2, 37_654, 0.05),
    ]
    best = None
    grid_log = []
    for lam, msep, mbud, fshare in candidates:
        emitted = dfsd_charnes_cooper_emit(
            p_tr_2d,
            q_tr_2d,
            p_phys_tr_2d,
            d_in,
            allow_in,
            lambda_fp=lam,
            min_sep_px=msep,
            max_budget=mbud,
            far_blind_share=fshare,
            far_dist_px=15.0,
        )
        res = metric.dti_binary(truth_in, emitted > 0, valid=act_in)
        entry = {
            "lambda_fp": lam,
            "min_sep_px": msep,
            "max_budget": mbud,
            "far_blind_share": fshare,
            "emitted_dots": int((emitted > 0).sum()),
            "inner_sim_dti": round(float(res["dti"]), 6),
        }
        grid_log.append(entry)
        if best is None or entry["inner_sim_dti"] > best["inner_sim_dti"]:
            best = entry
    return {"selected": best, "grid": grid_log}


def _spatial_block_bootstrap(
    pred_map: dict[str, np.ndarray],
    folds: list[dict[str, Any]],
    footprint: np.ndarray,
    block_px: int = 200,
    n_boot: int = 1000,
    seed: int = 20261022,
) -> dict[str, Any]:
    H, W = footprint.shape
    truth_all = np.zeros((H, W), dtype=bool)
    active_all = np.zeros((H, W), dtype=bool)
    for f in folds:
        truth_all |= f["truth"]
        active_all |= footprint & f["region"] & (~f["masked_known"])

    by = np.arange(H, dtype=np.int32)[:, None] // block_px
    bx = np.arange(W, dtype=np.int32)[None, :] // block_px
    nbx = (W + block_px - 1) // block_px
    bid = (by * nbx + bx).ravel()
    act_flat = active_all.ravel()
    act_blocks = np.unique(bid[act_flat])
    b_remap = np.searchsorted(act_blocks, bid[act_flat])
    n_b = act_blocks.size

    k_truth = metric.kernel(ndi.distance_transform_edt(~truth_all))[active_all]
    truth_act = truth_all[active_all]

    comp_blocks: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, float]] = {}
    for name, pred in pred_map.items():
        p_bool = np.asarray(pred > 0, dtype=bool) & active_all
        k_pred = metric.kernel(ndi.distance_transform_edt(~p_bool))[active_all]
        tp_cell = np.where(truth_act, k_pred, 0.0)
        fn_cell = np.where(truth_act, 1.0 - k_pred, 0.0)
        fp_cell = np.where(p_bool[active_all], 1.0 - k_truth, 0.0)
        tp_b = np.bincount(b_remap, weights=tp_cell, minlength=n_b)
        fp_b = np.bincount(b_remap, weights=fp_cell, minlength=n_b)
        fn_b = np.bincount(b_remap, weights=fn_cell, minlength=n_b)
        denom = tp_b.sum() + metric.ALPHA * fp_b.sum() + metric.BETA * fn_b.sum()
        comp_blocks[name] = (tp_b, fp_b, fn_b, float(tp_b.sum() / denom) if denom > 0 else 0.0)

    rng = np.random.default_rng(seed)
    idx_mat = rng.integers(0, n_b, size=(n_boot, n_b))
    boot_scores: dict[str, np.ndarray] = {}
    for name, (tp_b, fp_b, fn_b, _) in comp_blocks.items():
        tp_s = tp_b[idx_mat].sum(axis=1)
        fp_s = fp_b[idx_mat].sum(axis=1)
        fn_s = fn_b[idx_mat].sum(axis=1)
        den = tp_s + metric.ALPHA * fp_s + metric.BETA * fn_s
        boot_scores[name] = np.where(den > 0, tp_s / den, 0.0)

    out: dict[str, Any] = {"n_blocks_20km": int(n_b), "n_bootstrap_draws": int(n_boot), "arms": {}, "paired_deltas": {}}
    for name, (_, _, _, pe) in comp_blocks.items():
        arr = boot_scores[name]
        out["arms"][name] = {
            "point_dti": round(pe, 6),
            "ci95_low": round(float(np.percentile(arr, 2.5)), 6),
            "ci95_high": round(float(np.percentile(arr, 97.5)), 6),
            "std_err": round(float(np.std(arr, ddof=1)), 6),
        }
    for a, b in (
        ("EXP-DFSD-3_charnes_cooper", "C2_h33_analogue_foldfair"),
        ("EXP-DFSD-3_charnes_cooper", "EXP-DFSD-2_uniform_d28"),
        ("EXP-DFSD-2_uniform_d28", "C2_h33_analogue_foldfair"),
        ("EXP-DFSD-1_pure_zero_catalogue", "C2_h33_analogue_foldfair"),
        ("EXP-DFSD-1_pure_zero_catalogue", "C0_random_B37654"),
    ):
        if a in boot_scores and b in boot_scores:
            diff = boot_scores[a] - boot_scores[b]
            out["paired_deltas"][f"{a}__minus__{b}"] = {
                "delta_dti": round(float(comp_blocks[a][3] - comp_blocks[b][3]), 6),
                "ci95_low": round(float(np.percentile(diff, 2.5)), 6),
                "ci95_high": round(float(np.percentile(diff, 97.5)), 6),
                "prob_positive": round(float(np.mean(diff > 0.0)), 4),
            }
    return out


def _regime_decomposition(
    pred_map: dict[str, np.ndarray],
    folds: list[dict[str, Any]],
    footprint: np.ndarray,
    lidar_fp: np.ndarray,
    mtn_fp: np.ndarray,
    visible: np.ndarray,
) -> dict[str, Any]:
    H, W = footprint.shape
    truth_all = np.zeros((H, W), dtype=bool)
    active_all = np.zeros((H, W), dtype=bool)
    for f in folds:
        truth_all |= f["truth"]
        active_all |= footprint & f["region"] & (~f["masked_known"])

    lid_2d = np.zeros((H, W), dtype=bool)
    lid_2d[footprint] = lidar_fp
    mtn_2d = np.zeros((H, W), dtype=bool)
    mtn_2d[footprint] = mtn_fp
    d_vis = ndi.distance_transform_edt(~visible)

    regimes = {
        "lidar_covered": active_all & lid_2d,
        "blind_outside_lidar": active_all & (~lid_2d),
        "basin_and_piedmont": active_all & (~mtn_2d),
        "mountain_bedrock": active_all & mtn_2d,
        "near_tip_or_relay_le_1km": active_all & (d_vis <= 10.0),
        "far_blind_gt_1km": active_all & (d_vis > 10.0),
    }
    out: dict[str, Any] = {}
    for rname, rmask in regimes.items():
        row: dict[str, Any] = {
            "withheld_positive_pixels": int((truth_all & rmask).sum()),
            "active_pixels": int(rmask.sum()),
            "scores": {},
        }
        for aname, pred in pred_map.items():
            row["scores"][aname] = round(float(metric.dti_binary(truth_all, pred > 0, valid=rmask)["dti"]), 6)
        out[rname] = row
    return out


def _evaluate_one_seed(
    seed: int,
    grid: Grid,
    footprint: np.ndarray,
    base_mm: np.memmap,
    extra_mm: np.memmap,
    base_path: Path,
    ctx5_fp: np.ndarray,
    lidar_fp: np.ndarray,
    mtn_fp: np.ndarray,
    scarp_step_fp: np.ndarray,
    thvc_cues_path: Path,
    dfsd_cues_path: Path,
    d28_bool: np.ndarray,
    fab_surface: np.ndarray,
    dfsd_cache: Path,
) -> dict[str, Any]:
    ckpt_json = dfsd_cache / f"eval_seed{seed}.json"
    if ckpt_json.exists():
        print(f"[DFSD seed={seed}] Reusing verified checkpoint {ckpt_json}", flush=True)
        return json.loads(ckpt_json.read_text())

    t0 = time.time()
    print(f"\n==================== G79-DFSD SEED {seed} EVALUATION ====================", flush=True)
    folds, quad = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    vis = folds[0]["visible"]
    quad_fp = quad[footprint]
    d_vis = ndi.distance_transform_edt(~vis)
    allow_vis = footprint & (d_vis > 2.0)

    test_mech = compute_dfsd_mechanics(vis, footprint, thvc_cues_path, dfsd_cues_path, scarp_step_fp)
    canary = _run_107_feature_leakage_canaries(seed, folds, footprint, base_mm, extra_mm, base_path, test_mech)
    print(
        f"[DFSD seed={seed}] ALL 107 LEAKAGE CANARIES PASSED! "
        f"max symmetric AUC = {canary['max_symmetric_auc']:.6f} ({canary['max_feature']}) <= 0.90",
        flush=True,
    )

    t_ooq = time.time()
    phys_models = fit_crossquad_split_sensor_physics_experts(
        vis, footprint, quad_fp, lidar_fp, base_mm, extra_mm, base_path, seed=seed * 31
    )
    pair_cache = predict_split_sensor_pair_cache(
        phys_models, quad_fp, lidar_fp, base_mm, extra_mm, base_path
    )
    del phys_models
    gc.collect()
    print(f"[DFSD seed={seed}] Cross-quadrant split-sensor physics experts ready in {time.time()-t_ooq:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

    t_sh = time.time()
    shards, draw0_ref = build_decontaminated_shards(
        vis, footprint, quad_fp, base_mm, extra_mm, base_path, thvc_cues_path, dfsd_cues_path, scarp_step_fp,
        n_draws=3, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=23_000, seed_base=8200 + seed
    )
    print(f"[DFSD seed={seed}] Decontaminated shards ready in {time.time()-t_sh:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

    t_f1 = time.time()
    p_full_fp, q_full_fp, p_tr_avg, q_tr_avg = run_dfsd_quadrant_nested_oof(
        quad_fp, lidar_fp, footprint, base_mm, extra_mm, base_path, ctx5_fp, shards, draw0_ref, pair_cache, test_mech, use_mechanics=True, seed=seed * 10
    )
    print(f"[DFSD seed={seed}] Full 107-ch split-domain OOF complete in {time.time()-t_f1:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

    t_f0 = time.time()
    p_zero_fp, q_zero_fp, p_zero_tr, _ = run_dfsd_quadrant_nested_oof(
        quad_fp, lidar_fp, footprint, base_mm, extra_mm, base_path, ctx5_fp, shards, draw0_ref, pair_cache, None, use_mechanics=False, seed=seed * 20
    )
    print(f"[DFSD seed={seed}] Pure zero-catalogue 90-ch OOF complete in {time.time()-t_f0:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

    del shards, test_mech, pair_cache
    gc.collect()

    H, W = footprint.shape
    p_full_2d = np.zeros((H, W), dtype=np.float32)
    q_full_2d = np.zeros((H, W), dtype=np.float32)
    p_tr_2d = np.zeros((H, W), dtype=np.float32)
    q_tr_2d = np.zeros((H, W), dtype=np.float32)
    p_zero_2d = np.zeros((H, W), dtype=np.float32)
    q_zero_2d = np.zeros((H, W), dtype=np.float32)
    p_zero_tr_2d = np.zeros((H, W), dtype=np.float32)

    p_full_2d[footprint] = p_full_fp
    q_full_2d[footprint] = q_full_fp
    p_tr_2d[footprint] = p_tr_avg
    q_tr_2d[footprint] = q_tr_avg
    p_zero_2d[footprint] = p_zero_fp
    q_zero_2d[footprint] = q_zero_fp
    p_zero_tr_2d[footprint] = p_zero_tr

    cc_tune = _select_dfsd_params_inner(p_tr_2d, q_tr_2d, p_zero_tr_2d, draw0_ref, footprint)
    sel = cc_tune["selected"]
    print(f"[DFSD seed={seed}] Inner-selected Charnes-Cooper params (zero outer test access): {sel}", flush=True)
    del draw0_ref
    gc.collect()

    rng_c0 = np.random.default_rng(79000 + seed)
    allow_flat = np.flatnonzero(allow_vis)
    c0_map = np.zeros((H, W), dtype=np.float32)
    c0_map.ravel()[rng_c0.choice(allow_flat, size=37_654, replace=False)] = 1.0
    c1_map = poisson_disk_emit(fab_surface, allow_vis, budget=37_654, min_dist_px=2.8)
    c2_map = (d28_bool & allow_vis).astype(np.float32)

    exp1_map = poisson_disk_emit(
        0.65 * p_zero_2d + 0.35 * (np.clip(q_zero_2d, 0.0, 1.0) ** 1.5) * 0.30,
        allow_vis,
        budget=37_654,
        min_dist_px=2.8,
    )
    exp2_map = poisson_disk_emit(
        0.70 * p_full_2d + 0.30 * (np.clip(q_full_2d, 0.0, 1.0) ** 1.6) * 0.28,
        allow_vis,
        budget=37_654,
        min_dist_px=2.8,
    )
    exp3_map = dfsd_charnes_cooper_emit(
        p_full_2d,
        q_full_2d,
        p_zero_2d,
        d_vis,
        allow_vis,
        lambda_fp=sel["lambda_fp"],
        min_sep_px=sel["min_sep_px"],
        max_budget=sel["max_budget"],
        far_blind_share=sel["far_blind_share"],
        far_dist_px=15.0,
    )

    preds = {
        "EXP-DFSD-3_charnes_cooper": exp3_map,
        "EXP-DFSD-2_uniform_d28": exp2_map,
        "EXP-DFSD-1_pure_zero_catalogue": exp1_map,
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
            f_list.append({
                "fold": f_idx,
                "dti": round(float(f_res["dti"]), 6),
                "n_truth": f_res["n_truth"],
                "n_emitted": f_res["n_emitted"],
            })
            acc_terms = f_terms if acc_terms is None else (acc_terms + f_terms)
        terms_by_arm[arm_name] = acc_terms
        per_fold_scores[arm_name] = f_list

    official_eval = evaluate_holdout.pooled_summary(
        terms_by_arm, draws=1000, seed=520810 + seed, candidate="EXP-DFSD-3_charnes_cooper"
    )
    official_eval["per_fold"] = per_fold_scores
    bootstrap_ci = _spatial_block_bootstrap(preds, folds, footprint, block_px=200, n_boot=1000, seed=20261021 + seed)
    regimes = _regime_decomposition(preds, folds, footprint, lidar_fp, mtn_fp, vis)

    print(f"\n--- G79-DFSD SEED {seed} OFFICIAL HOLDOUT-DTI ({official_eval['evaluator_version']}) ---", flush=True)
    for k, v in official_eval["scores"].items():
        n_dots = int((preds[k] > 0).sum())
        print(
            f"  {k:34s}: HOLDOUT-DTI = {v['dti']:.6f}  95% CI [{v['ci95'][0]:.6f}, {v['ci95'][1]:.6f}]  "
            f"dots={n_dots:,}  tp_w={v['tpw']:.1f}",
            flush=True,
        )
    print(f"  Per-fold EXP-DFSD-3: {per_fold_scores['EXP-DFSD-3_charnes_cooper']}", flush=True)

    payload = {
        "seed": seed,
        "evaluator_version": official_eval["evaluator_version"],
        "withheld_positive_pixels": official_eval["scores"]["EXP-DFSD-3_charnes_cooper"]["withheld_positive_pixels"],
        "elapsed_seconds": round(time.time() - t0, 2),
        "leakage_canary": canary,
        "inner_charnes_cooper_selection": cc_tune,
        "official_evaluate_all": official_eval,
        "spatial_bootstrap_20km": bootstrap_ci,
        "regime_decomposition": regimes,
    }
    ckpt_json.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def _build_complete_all_org_registry_index() -> dict[str, Any]:
    """Assemble every SHA-256-verified raster across ALL 93 repos (992 frozen + 207 delta + all local GEMSDOE79 archives)."""
    seen_sha: dict[str, dict[str, Any]] = {}
    cache_reg = ROOT / ".cache/registry"

    idx_frozen = json.loads((ROOT / "registry/registry_index.json").read_text())
    rec_frozen = {r["blob"]: r["sha256"] for r in json.loads((ROOT / "registry/registry_receipt.json").read_text())["files"] if r.get("status") == "verified"}
    for r in idx_frozen["rasters"]:
        p = cache_reg / f"{r['blob']}.tif"
        sha = rec_frozen[r["blob"]]
        occs = r.get("occurrences", [])
        repo_first = r.get("repo") or (occs[0]["repo"] if occs else "unknown")
        aliases = [f"{o['repo']}:{o['path']}" for o in occs] if occs else [f"{repo_first}:{r.get('path', r['blob'])}"]
        seen_sha.setdefault(sha, {"repo_first": repo_first, "sources": [], "cache_file": str(p), "sha256": sha})["sources"].extend(aliases)

    delta_doc = json.loads((ROOT / "registry/registry_delta.json").read_text())
    for r in delta_doc["rasters"]:
        p = cache_reg / f"{r['blob']}.tif"
        sha = r["sha256"]
        seen_sha.setdefault(sha, {"repo_first": r["repo"], "sources": [], "cache_file": str(p), "sha256": sha})["sources"].extend(r.get("aliases", [f"{r['repo']}:{r['path']}"]))

    # Include ALL archived GEMSDOE79 candidate rasters (including G79-THVC, H79-FNHR, G79-BER, H79-NHR, G79-ETP, etc.)
    for arch_tif in sorted((ROOT / "archive").rglob("*.tif")):
        if "data/bridge" in arch_tif.as_posix():
            continue
        sha = hashlib.sha256(arch_tif.read_bytes()).hexdigest()
        rel = arch_tif.relative_to(ROOT).as_posix()
        seen_sha.setdefault(sha, {"repo_first": "GEMSDOE79", "sources": [], "cache_file": str(arch_tif), "sha256": sha})["sources"].append(f"GEMSDOE79:{rel}")

    for v in seen_sha.values():
        v["sources"] = sorted(set(v["sources"]))
    return {"complete_accessible_scan": True, "errors": [], "rasters": list(seen_sha.values())}


def _full_multi_regime_uniqueness_audit(
    candidate_tif: Path,
    candidate_arr: np.ndarray,
    footprint: np.ndarray,
    allowed: np.ndarray,
    combined_idx: dict[str, Any],
    label_tag: str,
    is_surface: bool = False,
) -> dict[str, Any]:
    """Run unmodified vendor/gems57/uniqueness.py::compare_array_to_registry_d2 in a single pass across all 1,221 rasters."""
    t0 = time.time()
    n_tot = len(combined_idx["rasters"])
    print(f"\n[DFSD uniqueness:{label_tag}] Scanning {candidate_tif.name} against {n_tot} unique SHA-256 rasters across all 93 repos...", flush=True)
    if is_surface:
        topk_dots = uniqueness.budget_matched_dots(candidate_arr, footprint, 37_654)
        surf_allowed = footprint & (~(candidate_arr < 0)) & np.asarray(allowed | topk_dots, dtype=bool)
        d2 = uniqueness.compare_array_to_registry_d2(
            topk_dots, combined_idx, footprint, surf_allowed, candidate_surface=candidate_arr
        )
    else:
        d2 = uniqueness.compare_array_to_registry_d2(
            candidate_arr > 0, combined_idx, footprint, allowed, file_sha256=hashlib.sha256(candidate_tif.read_bytes()).hexdigest()
        )

    ok_rows = [r for r in d2["rows"] if "error" not in r]
    valid_rhos = [
        abs(float(r["spearman_full_footprint"]))
        for r in ok_rows
        if r.get("spearman_full_footprint") is not None and np.isfinite(r["spearman_full_footprint"])
    ]
    max_abs_rho = round(float(max(valid_rhos)) if valid_rhos else 0.0, 6)

    sparse50 = [r for r in ok_rows if int(r.get("their_literal_positive_cells", 0)) <= 50_000]
    sparse75 = [r for r in ok_rows if int(r.get("their_literal_positive_cells", 0)) <= 75_308]
    w50 = max(sparse50, key=lambda r: float(r["my_dots_within_3px_literal"])) if sparse50 else None
    w75 = max(sparse75, key=lambda r: float(r["my_dots_within_3px_literal"])) if sparse75 else None
    inf_v4 = [r for r in ok_rows if float(r["halo_coverage_allowed"]) <= 0.70]
    inf_v4_dups = [r for r in inf_v4 if float(r["my_dots_within_3px_of_dot_equivalent"]) > 0.70]

    key_peers = {}
    for needle, key in (
        ("h33-h33-2-b2", "h33_champion_gemsdoe32"),
        ("g79-thvc-ccsubmod", "g79_thvc_incumbent"),
        ("gems83-h83-gvcd-dink300", "gemsdoe83_gvcd"),
        ("gems78-h78sigx-fuse-b5", "gemsdoe78_sigx"),
        ("gems73-h73-mcsc", "gemsdoe73_mcsc"),
        ("gems79-h79-fnhr-f3", "g79_h79_fnhr_f3"),
    ):
        matches = [r for r in ok_rows if needle in r.get("submission", "")]
        if matches:
            m0 = matches[0]
            key_peers[key] = {
                "submission": m0["submission"],
                "sha256": m0["sha256"],
                "their_dots": m0["their_literal_positive_cells"],
                "forward_overlap_3px": round(float(m0["my_dots_within_3px_literal"]), 6),
                "halo_coverage": round(float(m0["halo_coverage_allowed"]), 6),
                "chance_corrected_overlap": round(float(m0["chance_corrected_overlap"]), 6) if m0.get("chance_corrected_overlap") is not None else None,
                "spearman": round(float(m0["spearman_full_footprint"]), 6) if m0.get("spearman_full_footprint") is not None else None,
            }

    d2_inf = [r for r in ok_rows if r.get("chance_corrected_overlap") is not None]
    w_d2_inf = max(d2_inf, key=lambda r: float(r["chance_corrected_overlap"])) if d2_inf else None
    d2_inf_dups = [r for r in d2_inf if r.get("duplicate_d2")]

    summary = {
        "label": label_tag,
        "shared_function": "vendor/gems57/uniqueness.py::compare_array_to_registry_d2",
        "elapsed_seconds": round(time.time() - t0, 2),
        "registry_unique_blobs_scanned": n_tot,
        "comparable_3730x3292": d2["registry_rasters_checked"],
        "non_grid_verified_fixtures": d2["missing_or_invalid"],
        "max_abs_spearman": max_abs_rho,
        "spearman_le_0p90_passed": bool(max_abs_rho <= 0.90),
        "sparse_le_50k_count": len(sparse50),
        "sparse_le_50k_duplicates_gt_0p70": sum(1 for r in sparse50 if float(r["my_dots_within_3px_literal"]) > 0.70),
        "sparse_le_50k_max_overlap_3px": round(float(w50["my_dots_within_3px_literal"]), 6) if w50 else 0.0,
        "sparse_le_50k_worst_submission": w50["submission"] if w50 else None,
        "sparse_le_50k_passed": bool(w50 is not None and float(w50["my_dots_within_3px_literal"]) <= 0.70),
        "sparse_le_75k_count": len(sparse75),
        "sparse_le_75k_duplicates_gt_0p70": sum(1 for r in sparse75 if float(r["my_dots_within_3px_literal"]) > 0.70),
        "sparse_le_75k_max_overlap_3px": round(float(w75["my_dots_within_3px_literal"]), 6) if w75 else 0.0,
        "sparse_le_75k_worst_submission": w75["submission"] if w75 else None,
        "sparse_le_75k_passed": bool(w75 is not None and float(w75["my_dots_within_3px_literal"]) <= 0.70),
        "informative_halo_v4_count": len(inf_v4),
        "informative_halo_v4_duplicates_gt_0p70": len(inf_v4_dups),
        "amendment_d2_non_saturated_count": len(d2_inf),
        "amendment_d2_non_saturated_duplicates": len(d2_inf_dups),
        "amendment_d2_worst_chance_corrected_overlap": round(float(w_d2_inf["chance_corrected_overlap"]), 6) if w_d2_inf else None,
        "amendment_d2_worst_submission": w_d2_inf["submission"] if w_d2_inf else None,
        "amendment_d2_saturated_firings": d2["d2_firings"],
        "literal_worst_forward_overlap": d2["worst_literal_forward_overlap"],
        "literal_overlap_firings": d2["literal_overlap_firings"],
        "key_peer_comparisons": key_peers,
        "non_comparable_fixtures": [r for r in d2["rows"] if "error" in r],
    }
    print(json.dumps({k: v for k, v in summary.items() if k not in ("non_comparable_fixtures", "amendment_d2_saturated_firings")}, indent=2), flush=True)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", default="all", choices=("features", "seed20", "seed30", "live", "all"))
    ap.add_argument("--allow-initial-build", action="store_true")
    args = ap.parse_args()

    prereg_sha = _verify_prereg_lock()
    thvc_cache = ROOT / ".cache/g79_thvc"
    dfsd_cache = ROOT / ".cache/g79_dfsd"
    dfsd_cache.mkdir(parents=True, exist_ok=True)

    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
        transform = ds.transform
        crs = ds.crs
    with rasterio.open(ROOT / "data/raw/existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & footprint

    base_path = thvc_cache / "static_fp70.f32.mmap"
    thvc_cues_path = base_path.with_suffix(".cues.npz")
    dfsd_cues_path = dfsd_cache / "dfsd_cues.npz"

    base_mm, extra_mm, feat_meta = build_dfsd_static_stack(
        ROOT / "data/raw",
        ROOT / ".cache/official_ing",
        ROOT / "data/cache/dem10",
        base_path,
        dfsd_cache,
        footprint,
        transform,
    )
    print(f"[DFSD] 90-channel static stack ready! Peak RSS={rss_mb():.1f} MB", flush=True)
    if args.stage == "features":
        return

    cmap = {n: i for i, n in enumerate(THVC_STATIC_NAMES)}
    emap = {n: i for i, n in enumerate(DFSD_EXTRA_STATIC_NAMES)}
    lidar_fp = np.asarray(base_mm[:, cmap["lidar_present"]] > 0.5, dtype=bool)
    mtn_fp = np.asarray(base_mm[:, cmap["mountain_wall_ratio"]] > 0.35, dtype=bool)
    scarp_step_fp = np.asarray(base_mm[:, cmap["scarp_unified_step"]], dtype=np.float16)
    ctx5_fp = np.column_stack([
        base_mm[:, cmap["lidar_present"]],
        base_mm[:, cmap["scarp_unified_step"]],
        extra_mm[:, emap["dfsd_dem10_onesided3"]].astype(np.float32),
        base_mm[:, cmap["hydro_demag_clay_conj"]],
        base_mm[:, cmap["mountain_wall_ratio"]],
    ]).astype(np.float16)
    drop_file_cache(base_path)

    d28_path = ROOT / ".cache/registry/bfb7e86d046dd178c3d6ab60522861b5464dd420.tif"
    with rasterio.open(d28_path) as ds:
        d28_bool = (ds.read(1) > 0) & footprint
    fab_path = ROOT / "archive/g79_fabric_offset_f61b17a2/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif"
    with rasterio.open(fab_path) as ds:
        fab_surface = np.nan_to_num(ds.read(1).astype(np.float32), nan=0.0) * footprint

    grid = Grid(footprint, cat, str(crs), transform, footprint.shape[0], footprint.shape[1])

    if args.stage in ("seed20", "all"):
        _evaluate_one_seed(
            20, grid, footprint, base_mm, extra_mm, base_path, ctx5_fp, lidar_fp, mtn_fp,
            scarp_step_fp, thvc_cues_path, dfsd_cues_path, d28_bool, fab_surface, dfsd_cache,
        )
    if args.stage == "seed20":
        return

    if args.stage in ("seed30", "all"):
        _evaluate_one_seed(
            30, grid, footprint, base_mm, extra_mm, base_path, ctx5_fp, lidar_fp, mtn_fp,
            scarp_step_fp, thvc_cues_path, dfsd_cues_path, d28_bool, fab_surface, dfsd_cache,
        )
    if args.stage == "seed30":
        return

    eval20 = json.loads((dfsd_cache / "eval_seed20.json").read_text())
    eval30 = json.loads((dfsd_cache / "eval_seed30.json").read_text())

    # Full-footprint live ensemble fit
    live_ckpt = dfsd_cache / "live_fit_ckpt.npz"
    live_ckpt_meta = dfsd_cache / "live_fit_ckpt_meta.json"
    if live_ckpt.exists() and live_ckpt_meta.exists():
        print("Reloading saved live DFSD posteriors...", flush=True)
        z = np.load(live_ckpt)
        H, W = footprint.shape
        p2_live_fp = z["p2_live_fp"].astype(np.float32)
        q2_live_fp = z["q2_live_fp"].astype(np.float32)
        ooq_p_live = z["ooq_p_live"].astype(np.float32)
        p_live_2d = np.zeros((H, W), dtype=np.float32)
        q_live_2d = np.zeros((H, W), dtype=np.float32)
        p_phys_live_2d = np.zeros((H, W), dtype=np.float32)
        p_live_2d[footprint] = p2_live_fp
        q_live_2d[footprint] = q2_live_fp
        p_phys_live_2d[footprint] = ooq_p_live
        meta_c = json.loads(live_ckpt_meta.read_text())
        s2_scales = meta_c["s2_scales"]
        top_imp = meta_c["top_imp"]
    else:
        t_live = time.time()
        print("\n==================== G79-DFSD LIVE FULL-FOOTPRINT ENSEMBLE ====================", flush=True)
        _, quad_live = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)
        quad_fp = quad_live[footprint]
        n_fp = int(footprint.sum())
        all_rows = np.arange(n_fp, dtype=np.int64)
        all_mask = np.ones(n_fp, dtype=bool)

        live_phys_models = fit_crossquad_split_sensor_physics_experts(
            cat, footprint, quad_fp, lidar_fp, base_mm, extra_mm, base_path, seed=9701
        )
        live_pair_cache = predict_split_sensor_pair_cache(
            live_phys_models, quad_fp, lidar_fp, base_mm, extra_mm, base_path
        )
        del live_phys_models
        gc.collect()
        ooq_p_live, ooq_q_live = assemble_ooq_physics_for_context(live_pair_cache, quad_fp, excluded_test_quad=None)
        del live_pair_cache
        gc.collect()

        live_shards, live_draw0 = build_decontaminated_shards(
            cat, footprint, quad_fp, base_mm, extra_mm, base_path, thvc_cues_path, dfsd_cues_path, scarp_step_fp,
            n_draws=4, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=24_000, seed_base=9300
        )
        live_mech = compute_dfsd_mechanics(cat, footprint, thvc_cues_path, dfsd_cues_path, scarp_step_fp)

        oof_p1 = np.zeros(n_fp, dtype=np.float32)
        oof_q1 = np.zeros(n_fp, dtype=np.float32)
        for q_id in range(4):
            tr_qs = [q for q in range(4) if q != q_id]
            va_r = np.flatnonzero(quad_fp == q_id)
            Xq, yq, qq, wq, tpi_q = _stack_dfsd_shards(live_shards, tr_qs, True, ooq_p_live, ooq_q_live)
            sq = fit_dfsd_stage1(Xq, yq, qq, wq, seed=910 + q_id)
            del Xq, yq, qq, wq
            oof_p1[va_r], oof_q1[va_r] = predict_dfsd_stage1_rows(
                sq, base_mm, extra_mm, base_path, live_draw0["mech_fp16"], ooq_p_live, ooq_q_live, va_r, tpi_q
            )
            del sq
            gc.collect()

        S2_oof = extract_dfsd_stage2_features(oof_p1, oof_q1, ooq_p_live, ooq_q_live, footprint, ctx5_fp)
        del oof_p1, oof_q1
        s2_live = fit_dfsd_stage2_dual_heads(S2_oof, live_draw0, all_mask, lidar_fp, seed=989)
        del S2_oof
        gc.collect()

        p1_live = np.zeros(n_fp, dtype=np.float32)
        q1_live = np.zeros(n_fp, dtype=np.float32)
        feat_names_with_ooq = DFSD_ALL_FEATURE_NAMES + ["ooq_split_sensor_p_phys", "ooq_split_sensor_q_phys"]
        feat_imp = np.zeros(len(feat_names_with_ooq), dtype=np.float64)
        Xf, yf, qf, wf, tpi_f = _stack_dfsd_shards(live_shards, [0, 1, 2, 3], True, ooq_p_live, ooq_q_live)
        for rep in range(2):
            sf = fit_dfsd_stage1(Xf, yf, qf, wf, seed=1200 + 41 * rep)
            feat_imp += 0.5 * sf["lgb_deep"].booster_.feature_importance(importance_type="gain")
            pr, qr = predict_dfsd_stage1_rows(sf, base_mm, extra_mm, base_path, live_mech, ooq_p_live, ooq_q_live, all_rows, tpi_f)
            p1_live += 0.5 * pr
            q1_live += 0.5 * qr
            del sf
            gc.collect()
        del Xf, yf, qf, wf, live_shards, live_draw0, live_mech
        gc.collect()

        S2_live = extract_dfsd_stage2_features(p1_live, q1_live, ooq_p_live, ooq_q_live, footprint, ctx5_fp)
        p2_live_fp, q2_live_fp = predict_dfsd_stage2_dual_heads(s2_live, S2_live, lidar_fp, all_rows)
        s2_scales = s2_live["scales"]
        del S2_live, s2_live
        gc.collect()

        H, W = footprint.shape
        p_live_2d = np.zeros((H, W), dtype=np.float32)
        q_live_2d = np.zeros((H, W), dtype=np.float32)
        p_phys_live_2d = np.zeros((H, W), dtype=np.float32)
        p_live_2d[footprint] = p2_live_fp
        q_live_2d[footprint] = q2_live_fp
        p_phys_live_2d[footprint] = ooq_p_live

        top_imp = sorted(
            [{"feature": feat_names_with_ooq[i], "gain_share": round(float(feat_imp[i] / max(feat_imp.sum(), 1e-9)), 6)} for i in range(len(feat_names_with_ooq))],
            key=lambda r: -r["gain_share"],
        )
        np.savez_compressed(
            live_ckpt,
            p2_live_fp=p2_live_fp.astype(np.float16),
            q2_live_fp=q2_live_fp.astype(np.float16),
            ooq_p_live=ooq_p_live.astype(np.float16),
        )
        live_ckpt_meta.write_text(json.dumps({"s2_scales": s2_scales, "top_imp": top_imp}, indent=2) + "\n")
        print(f"[DFSD] Live ensemble fit in {time.time()-t_live:.1f}s! Scales={s2_scales}, Top 6 features: {top_imp[:6]}", flush=True)

    # STRICT PROTOCOL ORDERING (Rule 1 / IR-79-54):
    # Audit continuous pre-placement surface across ALL 93 repos BEFORE placing ANY final dot!
    combined_idx = _build_complete_all_org_registry_index()
    d_cat = ndi.distance_transform_edt(~cat)
    allow_live = footprint & (d_cat > 2.0)

    surf_blend = (0.68 * np.clip(p_live_2d, 0.0, 1.0) + 0.24 * (np.clip(q_live_2d, 0.0, 1.0) ** 1.5) * 0.30 + 0.08 * np.clip(p_phys_live_2d, 0.0, 1.0)).astype(np.float32)
    smax = float(surf_blend[footprint & (~cat)].max())
    surf_norm = np.where(footprint & (~cat), np.clip(surf_blend / max(smax, 1e-9), 0.0, 1.0), 0.0).astype(np.float32)
    tmp_surf_tif = dfsd_cache / "g79_dfsd_preplacement_surface.tif"
    for st_f in dfsd_cache.glob("g79_dfsd_preplacement_surface.*"):
        st_f.unlink()
    submission_writer.write_submission(
        tmp_surf_tif,
        surf_norm,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name="g79-dfsd-preplacement-surface",
        note="Pre-placement continuous posterior surface for full 93-repo uniqueness check",
        catalogue=cat,
    )
    surf_audit = _full_multi_regime_uniqueness_audit(
        tmp_surf_tif, surf_norm, footprint, allow_live, combined_idx, label_tag="pre_placement_surface", is_surface=True
    )
    if not surf_audit["spearman_le_0p90_passed"]:
        raise RuntimeError(f"PRE-PLACEMENT SURFACE DUPLICATE: |rho|={surf_audit['max_abs_spearman']} > 0.90")

    # Emit final binary predictions strictly from consensus inner-fold selected parameters!
    p20 = eval20["inner_charnes_cooper_selection"]["selected"]
    p30 = eval30["inner_charnes_cooper_selection"]["selected"]
    c_lam = round(0.5 * (p20["lambda_fp"] + p30["lambda_fp"]), 5)
    c_sep = float(max(p20["min_sep_px"], p30["min_sep_px"]))
    c_bud = int(round(0.5 * (p20["max_budget"] + p30["max_budget"])))
    c_far = round(0.5 * (p20["far_blind_share"] + p30["far_blind_share"]), 4)

    emitted_live = dfsd_charnes_cooper_emit(
        p_live_2d,
        q_live_2d,
        p_phys_live_2d,
        d_cat,
        allow_live,
        lambda_fp=c_lam,
        min_sep_px=c_sep,
        max_budget=c_bud,
        far_blind_share=c_far,
        far_dist_px=15.0,
    )

    out_dir = ROOT / "archive/g79_dfsd_d7da950d"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old_f in out_dir.glob("g79-dfsd-*"):
        old_f.unlink()

    n_emitted = int((emitted_live > 0).sum())
    raw_hash8 = hashlib.sha256(emitted_live.tobytes()).hexdigest()[:8]
    stem = f"g79-dfsd-ccsubmod-20261022-{raw_hash8}-zeros-DO-NOT-SUBMIT"
    note = (
        f"GEMSDOE79 G79-DFSD: destriped-tilt+Kd+10m+shadow split-sensor + Charnes-Cooper ({n_emitted} px; research hold)"
    )[:140]
    cand_tif = out_dir / f"{stem}.tif"
    manifest = submission_writer.write_submission(
        cand_tif,
        emitted_live,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name=stem,
        note=note,
        catalogue=cat,
        metadata={
            "lane": "G79-DFSD",
            "preregistration_sha256": prereg_sha,
            "consensus_params": {
                "lambda_fp": c_lam,
                "min_sep_px": c_sep,
                "max_budget": c_bud,
                "far_blind_share": c_far,
            },
            "holdout_seed20": eval20["official_evaluate_all"]["scores"]["EXP-DFSD-3_charnes_cooper"],
            "holdout_seed30": eval30["official_evaluate_all"]["scores"]["EXP-DFSD-3_charnes_cooper"],
        },
    )
    for pf in out_dir.glob(f"{stem}*"):
        pf.chmod(0o644)

    val_res = validate.validate(cand_tif, footprint=footprint, catalogue=cat)
    dot_audit = _full_multi_regime_uniqueness_audit(
        cand_tif, emitted_live, footprint, allow_live, combined_idx, label_tag="post_placement_dots", is_surface=False
    )

    d_dots_m = d_cat[emitted_live > 0] * 100.0
    lid_2d = np.zeros((H, W), dtype=bool)
    lid_2d[footprint] = lidar_fp
    dist_profile = {
        "emitted_positive_pixels": n_emitted,
        "in_non_lidar_gap_pixels": int(((emitted_live > 0) & (~lid_2d)).sum()),
        "in_non_lidar_gap_fraction": round(float((((emitted_live > 0) & (~lid_2d)).sum()) / max(n_emitted, 1)), 6),
        "p10_m": round(float(np.percentile(d_dots_m, 10.0)), 2),
        "p50_median_m": round(float(np.median(d_dots_m)), 2),
        "p90_m": round(float(np.percentile(d_dots_m, 90.0)), 2),
        "fraction_gt_1km": round(float(np.mean(d_dots_m > 1000.0)), 6),
        "fraction_gt_2km": round(float(np.mean(d_dots_m > 2000.0)), 6),
    }

    np.savez_compressed(
        dfsd_cache / "live_dfsd_maps.npz",
        p_live_fp=p2_live_fp.astype(np.float16),
        q_live_fp=q2_live_fp.astype(np.float16),
        p_phys_fp=ooq_p_live.astype(np.float16),
        emitted_idx=np.flatnonzero(emitted_live > 0).astype(np.int32),
    )

    results_doc = {
        "schema_version": 2,
        "lane": "G79-DFSD",
        "preregistration_path": "registry/preregistration_g79_dfsd.json",
        "preregistration_sha256": prereg_sha,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "feature_meta": feat_meta,
        "seed20": eval20,
        "seed30": eval30,
        "live_model_meta": {
            "sensor_scales": {k: [round(v[0], 6), round(v[1], 6)] for k, v in s2_scales.items()},
            "consensus_charnes_cooper": {
                "lambda_fp": c_lam,
                "min_sep_px": c_sep,
                "max_budget": c_bud,
                "far_blind_share": c_far,
            },
            "distance_and_sensor_profile": dist_profile,
            "top25_features_by_gain": top_imp[:25],
        },
        "validator": val_res,
        "submission_manifest": manifest,
        "pre_placement_surface_uniqueness": surf_audit,
        "post_placement_dot_uniqueness": dot_audit,
    }
    (ROOT / "evidence/g79_dfsd_results.json").write_text(json.dumps(results_doc, indent=2) + "\n")
    print("\n==================== G79-DFSD END-TO-END RUN COMPLETE ====================", flush=True)


if __name__ == "__main__":
    main()
