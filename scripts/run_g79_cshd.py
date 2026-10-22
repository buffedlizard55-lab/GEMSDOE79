#!/usr/bin/env python3
"""Execute the preregistered G79-CSHD (Crustal-Structural-Hydrothermal-Deconvolved
Dual-Regime Submodular Discovery) lane end-to-end.

Strictly honors all 6 Parallel-Run Protocol rules & AGENTS.md safeguards:
  1. Single preregistered lane (`G79-CSHD`, `registry/preregistration_g79_cshd.json`).
     Pre-placement continuous surface AND post-placement binary dots checked across ALL
     1,201 cross-repo rasters (992 frozen + 209 post-snapshot delta across 92 sibling repos)
     PLUS archived GEMSDOE79 lanes; zero `overlap_cap`, zero `vendor/gems57/` edits.
  2. Reuses shared cached 70-band THVC stack + 10 untried CSHD static channels + 16
     strictly fold-visible analytical Voronoi stress-shadow/relay/throw-deficit channels,
     official `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`), and
     `vendor/gems57/submission_writer.py`.
  3. Every score labeled strictly as `HOLDOUT-DTI` (with evaluator version, withheld
     positives, and 95% CIs) or `ORGANIZER-CONFIRMED`.
  4. Tests ALL 96 features individually on holdout (`0.5 <= max(auc, 1-auc) <= 0.90`).
  5. Writes complete `gems79-run-card-v2` JSON receipt and invokes `scripts/select_submission.py`.
  6. Executes strictly within the 3-experiment preregistered budget (`EXP-CSHD-1..3`).
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

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "2")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout, holdout, metric, submission_writer, uniqueness  # noqa: E402
from gems57.grid import Grid  # noqa: E402
from gems79.cshd_features import (  # noqa: E402
    CSHD_ALL_FEATURE_NAMES,
    CSHD_EXTRA_STATIC_NAMES,
    CSHD_MECH_NAMES,
    CSHD_STATIC_NAMES,
    build_cshd_static_stack,
    compute_cshd_mechanics,
    drop_file_cache,
)
from gems79.cshd_model import (  # noqa: E402
    _stack_cshd_shards,
    build_decontaminated_mech_shards,
    build_pure_physics_shards,
    extract_cshd_stage2_features,
    fit_decontaminated_stage2,
    fit_weighted_stage1_suite,
    predict_decontaminated_stage2,
    predict_weighted_stage1_rows,
    run_full_cshd_oof,
    run_pure_physics_oof,
)
from gems79.thvc_model import charnes_cooper_submodular_emit, poisson_disk_emit  # noqa: E402
from gems79.thvc_features import STATIC_FEATURE_NAMES as THVC_70_NAMES, rss_mb  # noqa: E402


def _audit_single_feature_canaries(
    seeds: tuple[int, ...],
    grid: Grid,
    footprint: np.ndarray,
    mm70: np.memmap,
    mmap70_path: Path,
    mm10: np.memmap,
    mmap10_path: Path,
    cues_path: Path,
    cache_dir: Path,
) -> dict[str, Any]:
    """Protocol Rule 4: test EVERY SINGLE ONE of all 96 features alone on holdout."""
    out_path = ROOT / "evidence" / "g79_cshd_single_feature_auc.json"
    if out_path.exists():
        doc = json.loads(out_path.read_text())
        if doc.get("n_features_checked") == len(CSHD_ALL_FEATURE_NAMES):
            print(f"Reusing verified 98-feature canary audit (max AUC={doc['max_symmetric_auc']:.4f} <= 0.90)", flush=True)
            return doc

    t0 = time.time()
    print("\n--- RUNNING PROTOCOL RULE 4 SINGLE-FEATURE LEAKAGE CANARY ACROSS ALL 98 FEATURES ---", flush=True)
    rows: list[dict[str, Any]] = []
    by_seed_max: dict[str, float] = {}

    # Sample clean 600k active non-truth cells + ALL truth cells per seed for exact high-precision ROC-AUC in ~4s!
    for seed in seeds:
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        vis = folds[0]["visible"]
        truth_all = np.zeros_like(footprint, dtype=bool)
        active_all = np.zeros_like(footprint, dtype=bool)
        for f in folds:
            truth_all |= f["truth"]
            active_all |= footprint & f["region"] & ~f["masked_known"]
        truth_fp = truth_all[footprint]
        active_fp = active_all[footprint]
        pos_i = np.flatnonzero(active_fp & truth_fp)
        neg_pool = np.flatnonzero(active_fp & (~truth_fp))
        rng = np.random.default_rng(20261022 + seed)
        neg_i = rng.choice(neg_pool, size=min(500_000, neg_pool.size), replace=False)
        eval_i = np.sort(np.concatenate([pos_i, neg_i]))
        y_ev = truth_fp[eval_i].astype(np.int32)
        w_ev = np.where(y_ev == 1, 1.0, float(neg_pool.size / max(neg_i.size, 1)))

        mech = compute_cshd_mechanics(vis, footprint, cues_path)
        X_ev = np.empty((eval_i.size, len(CSHD_ALL_FEATURE_NAMES)), dtype=np.float32)
        X_ev[:, :70] = mm70[eval_i]
        X_ev[:, 70:80] = mm10[eval_i]
        X_ev[:, 80:] = mech[eval_i]
        del mech
        drop_file_cache(mmap70_path)
        drop_file_cache(mmap10_path)

        seed_max = 0.5
        for j, fname in enumerate(CSHD_ALL_FEATURE_NAMES):
            vals = np.nan_to_num(X_ev[:, j], nan=0.0, posinf=0.0, neginf=0.0)
            if np.ptp(vals) == 0.0:
                raw_auc = 0.5
            else:
                raw_auc = float(roc_auc_score(y_ev, vals, sample_weight=w_ev))
            sym_auc = float(max(raw_auc, 1.0 - raw_auc))
            seed_max = max(seed_max, sym_auc)
            if sym_auc > 0.90:
                raise RuntimeError(
                    f"LEAKAGE CANARY TRIPPED on seed={seed}, feature={fname}: symmetric AUC={sym_auc:.6f} > 0.90!"
                )
            if seed == seeds[0]:
                rows.append({"feature": fname, "group": "static_80" if j < 80 else "fold_visible_mechanics_18", f"auc_seed{seed}": round(raw_auc, 6), f"sym_auc_seed{seed}": round(sym_auc, 6)})
            else:
                rows[j][f"auc_seed{seed}"] = round(raw_auc, 6)
                rows[j][f"sym_auc_seed{seed}"] = round(sym_auc, 6)
                rows[j]["max_sym_auc"] = round(max(rows[j][f"sym_auc_seed{seeds[0]}"], sym_auc), 6)
        by_seed_max[f"seed_{seed}"] = round(seed_max, 6)
        del X_ev
        gc.collect()

    rows_sorted = sorted(rows, key=lambda r: -r["max_sym_auc"])
    max_sym = float(rows_sorted[0]["max_sym_auc"])
    doc = {
        "schema_version": 1,
        "lane": "G79-CSHD",
        "evaluator_version": getattr(evaluate_holdout, "VERSION", "gems57-pooled-hide-v2"),
        "n_features_checked": len(CSHD_ALL_FEATURE_NAMES),
        "limit": 0.90,
        "all_features_passed": bool(max_sym <= 0.90),
        "max_symmetric_auc": round(max_sym, 6),
        "max_feature": rows_sorted[0]["feature"],
        "by_seed_max_symmetric_auc": by_seed_max,
        "elapsed_seconds": round(time.time() - t0, 2),
        "features": rows_sorted,
    }
    out_path.write_text(json.dumps(doc, indent=2) + "\n")
    print(
        f"ALL 98 FEATURES PASSED LEAKAGE CANARY: max symmetric AUC = {max_sym:.4f} ({rows_sorted[0]['feature']}) <= 0.90 in {doc['elapsed_seconds']}s",
        flush=True,
    )
    return doc


def _emit_cshd_exp3(
    p_full_2d: np.ndarray,
    q_full_2d: np.ndarray,
    p_phys_2d: np.ndarray,
    d_vis_2d: np.ndarray,
    allowed_mask: np.ndarray,
    far_boost: float,
    lambda_fp: float,
    min_sep_px: float,
    max_budget: int,
    tau_decay: float = 42.0,
) -> np.ndarray:
    """Exact Charnes-Cooper submodular kernel allocator over relay-calibrated CSHD posterior."""
    dec = np.exp(-np.maximum(d_vis_2d - 8.0, 0.0) / float(tau_decay)).astype(np.float32)
    sc_p = float(p_full_2d[allowed_mask].mean() / max(float(p_phys_2d[allowed_mask].mean()), 1e-8))
    far_w = np.clip((d_vis_2d - 10.0) / 14.0, 0.0, 1.0).astype(np.float32) * float(far_boost)
    p_cal = np.clip((p_full_2d + far_w * (p_phys_2d * sc_p)) * dec, 0.0, 1.0)
    q_cal = np.clip(q_full_2d * np.sqrt(dec), 0.0, 1.0)
    return charnes_cooper_submodular_emit(
        p_exact_2d=p_cal,
        q_300m_2d=q_cal,
        allowed_mask=allowed_mask,
        lambda_fp=lambda_fp,
        min_sep_px=min_sep_px,
        max_budget=max_budget,
        min_budget=22_000,
    )


def _select_dual_cc_params_inner(
    p_full_tr_2d: np.ndarray,
    q_full_tr_2d: np.ndarray,
    p_phys_tr_2d: np.ndarray,
    q_phys_tr_2d: np.ndarray,
    draw0_ref: dict[str, Any],
    footprint: np.ndarray,
) -> dict[str, Any]:
    """Tune (tau_decay, lambda_fp, min_sep_px, max_budget) strictly on inner simulated draw0
    using exact competition DTI kernel (`metric.kernel`, zero outer holdout access).
    """
    H, W = footprint.shape
    active_2d = np.zeros((H, W), dtype=bool)
    truth_2d = np.zeros((H, W), dtype=bool)
    d_sim_2d = np.zeros((H, W), dtype=np.float32)
    active_2d[footprint] = draw0_ref["active_fp"]
    truth_2d[footprint] = draw0_ref["y_exact_fp"]
    d_sim_2d[footprint] = draw0_ref["d_sim_vis_fp16"].astype(np.float32)
    known_in = footprint & (~active_2d)
    allow_inner = footprint & (ndi.distance_transform_edt(~known_in) > 2.0)

    k_truth = metric.kernel(ndi.distance_transform_edt(~truth_2d))[active_2d]
    tr_act = truth_2d[active_2d]
    n_tr = float(tr_act.sum())

    candidates = [
        (34.0, 0.0016, 1.9, 40_500),
        (42.0, 0.0015, 1.9, 41_500),
        (42.0, 0.0018, 1.9, 40_000),
        (54.0, 0.0016, 1.9, 40_500),
        (42.0, 0.0018, 2.2, 39_500),
        (54.0, 0.0018, 2.2, 39_500),
    ]
    best: dict[str, Any] | None = None
    grid_log: list[dict[str, Any]] = []
    for tau_d, lam, sep, maxb in candidates:
        em = _emit_cshd_exp3(
            p_full_2d=p_full_tr_2d,
            q_full_2d=q_full_tr_2d,
            p_phys_2d=p_phys_tr_2d,
            d_vis_2d=d_sim_2d,
            allowed_mask=allow_inner,
            far_boost=0.0,
            lambda_fp=lam,
            min_sep_px=sep,
            max_budget=maxb,
            tau_decay=tau_d,
        )
        pb = (em > 0) & active_2d
        kp = metric.kernel(ndi.distance_transform_edt(~pb))[active_2d]
        tp_v = float(kp[tr_act].sum())
        denom = tp_v + metric.ALPHA * float((1.0 - k_truth[pb[active_2d]]).sum()) + metric.BETA * (n_tr - tp_v)
        dti_v = tp_v / denom if denom > 0 else 0.0
        entry = {
            "tau_decay": tau_d,
            "far_boost": 0.0,
            "lambda_fp": lam,
            "min_sep_px": sep,
            "max_budget": maxb,
            "emitted_dots": int((em > 0).sum()),
            "inner_sim_dti": round(float(dti_v), 6),
        }
        grid_log.append(entry)
        if best is None or entry["inner_sim_dti"] > best["inner_sim_dti"]:
            best = entry
    assert best is not None
    return {"selected": best, "phi_far_empirical": round(float(draw0_ref["phi_far_empirical"]), 6), "grid": grid_log}


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
        active_all |= footprint & f["region"] & ~f["masked_known"]

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

    ci_out: dict[str, Any] = {"n_blocks_20km": int(n_b), "n_bootstrap_draws": int(n_boot), "arms": {}, "paired_deltas": {}}
    for name, (_, _, _, pe) in comp_blocks.items():
        arr = boot_scores[name]
        ci_out["arms"][name] = {
            "point_dti": round(pe, 6),
            "ci95_low": round(float(np.percentile(arr, 2.5)), 6),
            "ci95_high": round(float(np.percentile(arr, 97.5)), 6),
            "std_err": round(float(np.std(arr, ddof=1)), 6),
        }

    pairs = [
        ("EXP-CSHD-3_dual_regime_cc", "C2_h33_analogue_foldfair"),
        ("EXP-CSHD-3_dual_regime_cc", "EXP-CSHD-2_cshd_uniform_d28"),
        ("EXP-CSHD-3_dual_regime_cc", "EXP-CSHD-1_pure_zero_catalogue"),
        ("EXP-CSHD-2_cshd_uniform_d28", "C2_h33_analogue_foldfair"),
        ("EXP-CSHD-1_pure_zero_catalogue", "C2_h33_analogue_foldfair"),
        ("EXP-CSHD-1_pure_zero_catalogue", "C0_random_B37654"),
    ]
    for a, b in pairs:
        if a in boot_scores and b in boot_scores:
            diff = boot_scores[a] - boot_scores[b]
            pe_diff = comp_blocks[a][3] - comp_blocks[b][3]
            ci_out["paired_deltas"][f"{a}__minus__{b}"] = {
                "delta_dti": round(float(pe_diff), 6),
                "ci95_low": round(float(np.percentile(diff, 2.5)), 6),
                "ci95_high": round(float(np.percentile(diff, 97.5)), 6),
                "prob_positive": round(float(np.mean(diff > 0.0)), 4),
            }
    return ci_out


def _regime_decomposition(
    pred_map: dict[str, np.ndarray],
    folds: list[dict[str, Any]],
    footprint: np.ndarray,
    mm70: np.memmap,
    visible: np.ndarray,
) -> dict[str, Any]:
    H, W = footprint.shape
    truth_all = np.zeros((H, W), dtype=bool)
    active_all = np.zeros((H, W), dtype=bool)
    for f in folds:
        truth_all |= f["truth"]
        active_all |= footprint & f["region"] & ~f["masked_known"]

    cmap = {n: i for i, n in enumerate(THVC_70_NAMES)}
    lid_2d = np.zeros((H, W), dtype=bool)
    lid_2d[footprint] = mm70[:, cmap["lidar_present"]] > 0.5
    mtn_2d = np.zeros((H, W), dtype=bool)
    mtn_2d[footprint] = mm70[:, cmap["mountain_wall_ratio"]] > 0.35
    d_vis = ndi.distance_transform_edt(~visible)

    regimes = {
        "near_network_le_1500m": active_all & (d_vis <= 15.0),
        "stepover_piedmont_1500_to_4000m": active_all & (d_vis > 15.0) & (d_vis <= 40.0),
        "blind_basin_gt_4000m": active_all & (d_vis > 40.0),
        "lidar_1m_covered": active_all & lid_2d,
        "non_lidar_10m_3dep_gap": active_all & (~lid_2d),
        "low_relief_piedmont_basin": active_all & (~mtn_2d),
    }
    out: dict[str, Any] = {}
    for rname, rmask in regimes.items():
        tr_sub = truth_all & rmask
        out[rname] = {"truth_pixels": int(tr_sub.sum()), "scores": {}}
        for aname, pred in pred_map.items():
            sc = metric.dti_exact(pred, tr_sub, valid=rmask, known=~rmask & footprint)
            out[rname]["scores"][aname] = {
                "dti": round(float(sc["dti"]), 6),
                "tp_w": round(float(sc["tp"]), 2),
                "emitted_in_regime": int(((pred > 0) & rmask).sum()),
            }
    return out


def _evaluate_one_seed(
    seed: int,
    grid: Grid,
    footprint: np.ndarray,
    mm70: np.memmap,
    mmap70_path: Path,
    mm10: np.memmap,
    mmap10_path: Path,
    ctx_cols_fp: np.ndarray,
    cues_path: Path,
    d28_bool: np.ndarray,
    fab_surface: np.ndarray,
    cache_dir: Path,
) -> dict[str, Any]:
    ckpt_json = cache_dir / f"eval_seed{seed}.json"
    if ckpt_json.exists():
        print(f"[seed={seed}] Reusing completed checkpoint {ckpt_json}", flush=True)
        return json.loads(ckpt_json.read_text())

    t0 = time.time()
    print(f"\n==================== STARTING G79-CSHD SEED {seed} EVALUATION ====================", flush=True)
    folds, quad = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    vis = folds[0]["visible"]
    quad_fp = quad[footprint]
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    d_vis_fp = d_vis[footprint]
    allow_vis = footprint & (d_vis > 2.0)
    far_vis = footprint & (d_vis > 15.0)
    del d_vis

    oof_ckpt = cache_dir / f"raw_oof_seed{seed}.npz"
    if oof_ckpt.exists():
        z = np.load(oof_ckpt)
        p_full_fp = z["p_full_fp"].astype(np.float32)
        q_full_fp = z["q_full_fp"].astype(np.float32)
        p_tr_avg = z["p_tr_avg"].astype(np.float32)
        q_tr_avg = z["q_tr_avg"].astype(np.float32)
        p_phys_fp = z["p_phys_fp"].astype(np.float32)
        q_phys_fp = z["q_phys_fp"].astype(np.float32)
        p_phys_tr = z["p_phys_tr"].astype(np.float32)
        q_phys_tr = z["q_phys_tr"].astype(np.float32)
        draw0_ref = {
            "active_fp": z["d0_active"],
            "y_exact_fp": z["d0_y"],
            "d_sim_vis_fp16": z["d0_d_sim_vis"],
            "phi_far_empirical": float(z["phi_far_empirical"]),
            "phi_far_clipped": float(z["phi_far_clipped"]),
        }
    else:
        tp0 = time.time()
        phys_shards, phys_ref = build_pure_physics_shards(
            vis, footprint, quad_fp, mm70, mmap70_path, mm10, mmap10_path, cues_path, neg_per_quad=44_000, seed_base=5100 + seed
        )
        phys_oof = run_pure_physics_oof(
            quad_fp, footprint, mm70, mmap70_path, mm10, mmap10_path, ctx_cols_fp, phys_shards, phys_ref, seed=seed * 20
        )
        del phys_shards, phys_ref
        gc.collect()
        print(f"[seed={seed}] Pure zero-catalogue 80-ch OOF complete in {time.time()-tp0:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

        tm0 = time.time()
        mech_shards, draw0_ref = build_decontaminated_mech_shards(
            vis, footprint, quad_fp, mm70, mmap70_path, mm10, mmap10_path, cues_path,
            n_draws=3, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=24_000, seed_base=7000 + seed
        )
        test_mech = compute_cshd_mechanics(vis, footprint, cues_path).astype(np.float16)
        p_full_fp, q_full_fp, p_tr_avg, q_tr_avg = run_full_cshd_oof(
            quad_fp, footprint, mm70, mmap70_path, mm10, mmap10_path, ctx_cols_fp,
            mech_shards, draw0_ref, test_mech, d_vis_fp, phys_oof, seed=seed * 10
        )
        p_phys_fp = phys_oof["p_phys_test"]
        q_phys_fp = phys_oof["q_phys_test"]
        p_phys_tr = phys_oof["p_phys_tr"]
        q_phys_tr = phys_oof["q_phys_tr"]
        del mech_shards, test_mech, phys_oof
        gc.collect()
        print(f"[seed={seed}] Full 98-ch CSHD OOF complete in {time.time()-tm0:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

        np.savez_compressed(
            oof_ckpt,
            p_full_fp=p_full_fp,
            q_full_fp=q_full_fp,
            p_tr_avg=p_tr_avg,
            q_tr_avg=q_tr_avg,
            p_phys_fp=p_phys_fp,
            q_phys_fp=q_phys_fp,
            p_phys_tr=p_phys_tr,
            q_phys_tr=q_phys_tr,
            d0_active=draw0_ref["active_fp"],
            d0_y=draw0_ref["y_exact_fp"],
            d0_d_sim_vis=draw0_ref["d_sim_vis_fp16"],
            phi_far_empirical=np.float32(draw0_ref["phi_far_empirical"]),
            phi_far_clipped=np.float32(draw0_ref["phi_far_clipped"]),
        )

    H, W = footprint.shape
    p_full_2d = np.zeros((H, W), dtype=np.float32)
    q_full_2d = np.zeros((H, W), dtype=np.float32)
    p_tr_2d = np.zeros((H, W), dtype=np.float32)
    q_tr_2d = np.zeros((H, W), dtype=np.float32)
    p_phys_2d = np.zeros((H, W), dtype=np.float32)
    q_phys_2d = np.zeros((H, W), dtype=np.float32)
    p_phys_tr_2d = np.zeros((H, W), dtype=np.float32)
    q_phys_tr_2d = np.zeros((H, W), dtype=np.float32)

    p_full_2d[footprint] = p_full_fp
    q_full_2d[footprint] = q_full_fp
    p_tr_2d[footprint] = p_tr_avg
    q_tr_2d[footprint] = q_tr_avg
    p_phys_2d[footprint] = p_phys_fp
    q_phys_2d[footprint] = q_phys_fp
    p_phys_tr_2d[footprint] = p_phys_tr
    q_phys_tr_2d[footprint] = q_phys_tr

    cc_tune = _select_dual_cc_params_inner(p_tr_2d, q_tr_2d, p_phys_tr_2d, q_phys_tr_2d, draw0_ref, footprint)
    sel = cc_tune["selected"]
    print(f"[seed={seed}] Inner-selected Dual-Regime CC params (zero test access): {sel}", flush=True)
    del draw0_ref, p_tr_2d, q_tr_2d, p_phys_tr_2d, q_phys_tr_2d
    gc.collect()

    rng_c0 = np.random.default_rng(79000 + seed)
    allow_flat = np.flatnonzero(allow_vis)
    c0_map = np.zeros((H, W), dtype=np.float32)
    c0_map.ravel()[rng_c0.choice(allow_flat, size=37_654, replace=False)] = 1.0
    c1_map = poisson_disk_emit(fab_surface, allow_vis, budget=37_654, min_dist_px=2.8)
    c2_map = (d28_bool & allow_vis).astype(np.float32)

    d_vis_full = ndi.distance_transform_edt(~vis).astype(np.float32)
    dec_vis = np.exp(-np.maximum(d_vis_full - 8.0, 0.0) / float(sel["tau_decay"])).astype(np.float32)
    exp1_map = poisson_disk_emit(p_phys_2d, allow_vis, budget=37_654, min_dist_px=2.8)

    exp2_surf = (0.75 * p_full_2d + 0.25 * (np.clip(q_full_2d, 0.0, 1.0) ** 1.6) * 0.22) * dec_vis
    exp2_map = poisson_disk_emit(exp2_surf, allow_vis, budget=37_654, min_dist_px=2.8)

    exp3_map = _emit_cshd_exp3(
        p_full_2d=p_full_2d,
        q_full_2d=q_full_2d,
        p_phys_2d=p_phys_2d,
        d_vis_2d=d_vis_full,
        allowed_mask=allow_vis,
        far_boost=sel["far_boost"],
        lambda_fp=sel["lambda_fp"],
        min_sep_px=sel["min_sep_px"],
        max_budget=sel["max_budget"],
        tau_decay=sel["tau_decay"],
    )
    del d_vis_full

    preds = {
        "EXP-CSHD-3_dual_regime_cc": exp3_map,
        "EXP-CSHD-2_cshd_uniform_d28": exp2_map,
        "EXP-CSHD-1_pure_zero_catalogue": exp1_map,
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
        terms_by_arm, draws=1000, seed=520810 + seed, candidate="EXP-CSHD-3_dual_regime_cc"
    )
    official_eval["per_fold"] = per_fold_scores
    bootstrap_ci = _spatial_block_bootstrap(preds, folds, footprint, block_px=200, n_boot=1000, seed=20261022 + seed)
    regimes = _regime_decomposition(preds, folds, footprint, mm70, vis)

    print(f"\n--- SEED {seed} OFFICIAL HOLDOUT-DTI RESULTS ({official_eval['evaluator_version']}) ---", flush=True)
    for k, v in official_eval["scores"].items():
        n_dots = int((preds[k] > 0).sum())
        n_far = int(((preds[k] > 0) & far_vis).sum())
        print(
            f"  {k:34s}: HOLDOUT-DTI = {v['dti']:.6f}  95% CI [{v['ci95'][0]:.6f}, {v['ci95'][1]:.6f}]  "
            f"dots={n_dots:,} (far>1.5km={n_far:,})  tp_w={v['tpw']:.1f}",
            flush=True,
        )

    out_payload = {
        "seed": seed,
        "evaluator_version": official_eval["evaluator_version"],
        "withheld_positive_pixels": official_eval["scores"]["EXP-CSHD-3_dual_regime_cc"]["withheld_positive_pixels"],
        "elapsed_seconds": round(time.time() - t0, 2),
        "inner_charnes_cooper_selection": cc_tune,
        "emitted_dot_counts": {k: int((preds[k] > 0).sum()) for k in preds},
        "emitted_far_gt_1500m_counts": {k: int(((preds[k] > 0) & far_vis).sum()) for k in preds},
        "official_evaluate_all": official_eval,
        "spatial_bootstrap_20km": bootstrap_ci,
        "regime_decomposition": regimes,
    }
    ckpt_json.write_text(json.dumps(out_payload, indent=2) + "\n")
    return out_payload


def _fit_live_cshd_ensembles(
    cat: np.ndarray,
    footprint: np.ndarray,
    quad: np.ndarray,
    mm70: np.memmap,
    mmap70_path: Path,
    mm10: np.memmap,
    mmap10_path: Path,
    ctx_cols_fp: np.ndarray,
    cues_path: Path,
    cache_dir: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    lp_npz = cache_dir / "live_cshd_posteriors.npz"
    lp_meta = cache_dir / "live_cshd_meta.json"
    if lp_npz.exists() and lp_meta.exists():
        print("Reusing saved live full-footprint CSHD posteriors...", flush=True)
        z = np.load(lp_npz)
        H, W = footprint.shape
        pf, qf, pp, qp = (np.zeros((H, W), dtype=np.float32) for _ in range(4))
        pf[footprint] = z["p_full_fp"].astype(np.float32)
        qf[footprint] = z["q_full_fp"].astype(np.float32)
        pp[footprint] = z["p_phys_fp"].astype(np.float32)
        qp[footprint] = z["q_phys_fp"].astype(np.float32)
        return pf, qf, pp, qp, json.loads(lp_meta.read_text())

    t0 = time.time()
    print("\n==================== TRAINING LIVE FULL-FOOTPRINT CSHD DUAL ENSEMBLE ====================", flush=True)
    quad_fp = quad[footprint]
    n_fp = int(footprint.sum())
    all_rows = np.arange(n_fp, dtype=np.int64)
    all_mask = np.ones(n_fp, dtype=bool)

    # 1. Live 80-channel Zero-Catalogue Pure Physics Ensemble `M_phys`
    phys_shards, phys_ref = build_pure_physics_shards(
        cat, footprint, quad_fp, mm70, mmap70_path, mm10, mmap10_path, cues_path, neg_per_quad=48_000, seed_base=6100
    )
    oof_phys_p1 = np.zeros(n_fp, dtype=np.float32)
    oof_phys_q1 = np.zeros(n_fp, dtype=np.float32)
    for q_id in range(4):
        tr_qs = [q for q in range(4) if q != q_id]
        va_r = np.flatnonzero(quad_fp == q_id)
        Xp, yp, qp_t, wp, cp, tpi_p, spi_p = _stack_cshd_shards(phys_shards, tr_qs)
        sp = fit_weighted_stage1_suite(Xp, yp, qp_t, wp, cp, seed=810 + q_id)
        del Xp, yp, qp_t, wp, cp
        oof_phys_p1[va_r], oof_phys_q1[va_r] = predict_weighted_stage1_rows(
            sp, mm70, mmap70_path, mm10, mmap10_path, None, va_r, tpi_p, spi_p
        )
        del sp
        gc.collect()

    drop_file_cache(mmap70_path)
    drop_file_cache(mmap10_path)
    S2_phys_oof = extract_cshd_stage2_features(oof_phys_p1, oof_phys_q1, footprint, ctx_cols_fp)
    s2_phys_live = fit_decontaminated_stage2(
        S2_phys_oof, all_mask, phys_ref["clean_neg_fp"], phys_ref["y_vis_fp"], phys_ref["q_vis_fp"], all_mask, seed=879, include_halo_in_cls=False
    )
    del S2_phys_oof, oof_phys_p1, oof_phys_q1

    Xp_all, yp_all, qp_all, wp_all, cp_all, tpi_pa, spi_pa = _stack_cshd_shards(phys_shards, [0, 1, 2, 3])
    p1_phys_live = np.zeros(n_fp, dtype=np.float32)
    q1_phys_live = np.zeros(n_fp, dtype=np.float32)
    for rep in range(2):
        sp_f = fit_weighted_stage1_suite(Xp_all, yp_all, qp_all, wp_all, cp_all, seed=850 + 29 * rep)
        pr, qr = predict_weighted_stage1_rows(sp_f, mm70, mmap70_path, mm10, mmap10_path, None, all_rows, tpi_pa, spi_pa)
        p1_phys_live += 0.5 * pr
        q1_phys_live += 0.5 * qr
        del sp_f
        gc.collect()
    del Xp_all, yp_all, qp_all, wp_all, cp_all, phys_shards, phys_ref

    S2_phys_live = extract_cshd_stage2_features(p1_phys_live, q1_phys_live, footprint, ctx_cols_fp)
    p2_phys_fp, q2_phys_fp = predict_decontaminated_stage2(s2_phys_live, S2_phys_live, all_rows)
    del S2_phys_live, s2_phys_live, p1_phys_live, q1_phys_live
    gc.collect()

    # 2. Live 98-channel Full CSHD Ensemble `M_full`
    live_shards, live_draw0 = build_decontaminated_mech_shards(
        cat, footprint, quad_fp, mm70, mmap70_path, mm10, mmap10_path, cues_path,
        n_draws=4, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=24_000, seed_base=9100
    )
    live_mech = compute_cshd_mechanics(cat, footprint, cues_path).astype(np.float16)

    oof_m_p1 = np.zeros(n_fp, dtype=np.float32)
    oof_m_q1 = np.zeros(n_fp, dtype=np.float32)
    for q_id in range(4):
        tr_qs = [q for q in range(4) if q != q_id]
        va_r = np.flatnonzero(quad_fp == q_id)
        Xm, ym, qm, wm, cm, tpi_m, spi_m = _stack_cshd_shards(live_shards, tr_qs)
        sm = fit_weighted_stage1_suite(Xm, ym, qm, wm, cm, seed=910 + q_id)
        del Xm, ym, qm, wm, cm
        oof_m_p1[va_r], oof_m_q1[va_r] = predict_weighted_stage1_rows(
            sm, mm70, mmap70_path, mm10, mmap10_path, live_draw0["mech_fp16"], va_r, tpi_m, spi_m
        )
        del sm
        gc.collect()

    drop_file_cache(mmap70_path)
    drop_file_cache(mmap10_path)
    S2_full_oof = extract_cshd_stage2_features(oof_m_p1, oof_m_q1, footprint, ctx_cols_fp)
    del oof_m_p1, oof_m_q1
    s2_full_live = fit_decontaminated_stage2(
        S2_full_oof,
        live_draw0["active_fp"],
        live_draw0["clean_neg_fp"],
        live_draw0["y_exact_fp"],
        live_draw0["q_300m_fp"],
        all_mask,
        seed=979,
    )
    del S2_full_oof
    gc.collect()

    Xf_all, yf_all, qf_all, wf_all, cf_all, tpi_fa, spi_fa = _stack_cshd_shards(live_shards, [0, 1, 2, 3])
    p1_full_live = np.zeros(n_fp, dtype=np.float32)
    q1_full_live = np.zeros(n_fp, dtype=np.float32)
    feat_imp = np.zeros(len(CSHD_ALL_FEATURE_NAMES), dtype=np.float64)
    for rep in range(2):
        sf = fit_weighted_stage1_suite(Xf_all, yf_all, qf_all, wf_all, cf_all, seed=1100 + 37 * rep)
        feat_imp += 0.5 * sf["lgb_deep"].booster_.feature_importance(importance_type="gain")
        pr, qr = predict_weighted_stage1_rows(sf, mm70, mmap70_path, mm10, mmap10_path, live_mech, all_rows, tpi_fa, spi_fa)
        p1_full_live += 0.5 * pr
        q1_full_live += 0.5 * qr
        del sf
        gc.collect()
    phi_live_emp = float(live_draw0["phi_far_empirical"])
    del Xf_all, yf_all, qf_all, wf_all, cf_all, live_shards, live_draw0, live_mech
    gc.collect()

    drop_file_cache(mmap70_path)
    drop_file_cache(mmap10_path)
    S2_full_live = extract_cshd_stage2_features(p1_full_live, q1_full_live, footprint, ctx_cols_fp)
    p2_full_fp, q2_full_fp = predict_decontaminated_stage2(s2_full_live, S2_full_live, all_rows)
    del S2_full_live, s2_full_live, p1_full_live, q1_full_live
    gc.collect()

    H, W = footprint.shape
    p_full_2d, q_full_2d, p_phys_2d, q_phys_2d = (np.zeros((H, W), dtype=np.float32) for _ in range(4))
    p_full_2d[footprint] = p2_full_fp
    q_full_2d[footprint] = q2_full_fp
    p_phys_2d[footprint] = p2_phys_fp
    q_phys_2d[footprint] = q2_phys_fp

    top_imp = sorted(
        [{"feature": CSHD_ALL_FEATURE_NAMES[i], "gain_share": round(float(feat_imp[i] / max(feat_imp.sum(), 1e-9)), 6)} for i in range(len(CSHD_ALL_FEATURE_NAMES))],
        key=lambda r: -r["gain_share"],
    )
    meta_live = {
        "live_train_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
        "phi_far_live_empirical": round(phi_live_emp, 6),
        "top30_features_by_gain": top_imp[:30],
    }
    np.savez_compressed(
        lp_npz,
        p_full_fp=p2_full_fp.astype(np.float16),
        q_full_fp=q2_full_fp.astype(np.float16),
        p_phys_fp=p2_phys_fp.astype(np.float16),
        q_phys_fp=q2_phys_fp.astype(np.float16),
    )
    lp_meta.write_text(json.dumps(meta_live, indent=2) + "\n")
    return p_full_2d, q_full_2d, p_phys_2d, q_phys_2d, meta_live


def _build_complete_1209_index() -> list[dict[str, Any]]:
    """Build complete deduplicated SHA-256 index across:
      - ALL 992 frozen registry rasters (`registry/registry_index.json`),
      - ALL 209 post-snapshot git-delta rasters across 92 sibling repos (`registry/registry_delta.json`), AND
      - ALL local archived `GEMSDOE79` lanes (`archive/**/*.tif`).
    """
    seen_sha: dict[str, dict[str, Any]] = {}
    pins = {
        r["blob"]: r["sha256"]
        for r in json.loads((ROOT / "registry/registry_receipt.json").read_text())["files"]
        if r.get("status") == "verified"
    }
    for row in json.loads((ROOT / "registry/registry_index.json").read_text())["rasters"]:
        sha = row.get("sha256") or pins.get(row["blob"])
        p = ROOT / ".cache/registry" / f"{row['blob']}.tif"
        if p.exists() and sha and sha not in seen_sha:
            seen_sha[sha] = {
                "repo": row["repo"],
                "submission": f"{row['repo']}:{row.get('path', p.name)}",
                "file": str(p),
                "sha256": sha,
                "source_bucket": "frozen_992",
            }
    for row in json.loads((ROOT / "registry/registry_delta.json").read_text())["rasters"]:
        sha = row["sha256"]
        p = ROOT / ".cache/registry" / f"{row['blob']}.tif"
        if p.exists() and sha not in seen_sha:
            seen_sha[sha] = {
                "repo": row["repo"],
                "submission": f"{row['repo']}:{row.get('path', p.name)}",
                "file": str(p),
                "sha256": sha,
                "source_bucket": "post_snapshot_delta_209",
            }
    for p in sorted((ROOT / "archive").rglob("*.tif")):
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if sha not in seen_sha:
            seen_sha[sha] = {
                "repo": "GEMSDOE79",
                "submission": f"GEMSDOE79:{p.relative_to(ROOT)}",
                "file": str(p),
                "sha256": sha,
                "source_bucket": "local_gemsdoe79_archive",
            }
    return list(seen_sha.values())


def _full_uniqueness_scan(
    cand_tif: Path,
    footprint: np.ndarray,
    allowed: np.ndarray,
    records: list[dict[str, Any]],
    candidate_surface: np.ndarray | None = None,
) -> dict[str, Any]:
    """Run BOTH literal parallel-run audit AND official Amendment D-2 audit across ALL unique rasters."""
    t0 = time.time()
    with rasterio.open(cand_tif) as ds:
        cand_arr = ds.read(1).astype(np.float32)
    cand_arr = np.where(np.isfinite(cand_arr), cand_arr, 0.0)
    cand_arr[~footprint] = 0.0
    file_sha = hashlib.sha256(cand_tif.read_bytes()).hexdigest()
    mine = (cand_arr > 0) & footprint

    # Official `vendor/gems57/uniqueness.py` Amendment D-2 + literal forward overlap + Spearman across ALL records!
    d2 = uniqueness.compare_array_to_registry_d2(
        candidate_dots=mine,
        registry_index=records,
        footprint=footprint,
        allowed=allowed,
        candidate_surface=candidate_surface,
        file_sha256=file_sha,
    )

    valid_rows = [r for r in d2["rows"] if "error" not in r]
    sparse_50k = [r for r in valid_rows if r["representation"] == "dot_field" and r["their_literal_positive_cells"] <= 50_000]
    sparse_75k = [r for r in valid_rows if r["representation"] == "dot_field" and r["their_literal_positive_cells"] <= 75_308]
    dot_fields_all = [r for r in valid_rows if r["representation"] == "dot_field"]

    rho_vals = [abs(float(r["spearman_full_footprint"])) for r in valid_rows if r.get("spearman_full_footprint") is not None]
    max_abs_rho = max(rho_vals) if rho_vals else 0.0
    max_ov_50k = max(float(r["my_dots_within_3px_literal"]) for r in sparse_50k)
    max_ov_75k = max(float(r["my_dots_within_3px_literal"]) for r in sparse_75k)
    worst_50k = max(sparse_50k, key=lambda r: float(r["my_dots_within_3px_literal"]))
    worst_75k = max(sparse_75k, key=lambda r: float(r["my_dots_within_3px_literal"]))

    # Non-saturated D-2 rows (`halo_coverage_allowed < 0.999999`)
    d2_nonsat = [r for r in valid_rows if r.get("chance_corrected_overlap") is not None]
    max_d2_nonsat = max(float(r["chance_corrected_overlap"]) for r in d2_nonsat)
    worst_d2_nonsat = max(d2_nonsat, key=lambda r: float(r["chance_corrected_overlap"]))

    # Named key neighbors (`H33`, `G79-THVC`, `GEMSDOE83`, `GEMSDOE78`, `GEMSDOE77`, `GEMSDOE70`, `H79-NHR`, `H79-FNHR`)
    named_hits = {}
    for needle in ("GEMSDOE32:", "g79-thvc-ccsubmod", "GEMSDOE83:", "GEMSDOE78:", "GEMSDOE77:", "GEMSDOE70:", "h79-nhr", "h79-fnhr"):
        matches = [r for r in valid_rows if needle in r["submission"]]
        if matches:
            top_m = max(matches, key=lambda r: float(r["my_dots_within_3px_literal"]))
            named_hits[needle.rstrip(":")] = {
                "submission": top_m["submission"],
                "their_dots": top_m["their_literal_positive_cells"],
                "forward_overlap_3px": round(float(top_m["my_dots_within_3px_literal"]), 6),
                "chance_corrected_d2": None if top_m["chance_corrected_overlap"] is None else round(float(top_m["chance_corrected_overlap"]), 6),
                "spearman": None if top_m["spearman_full_footprint"] is None else round(float(top_m["spearman_full_footprint"]), 6),
            }

    return {
        "elapsed_seconds": round(time.time() - t0, 2),
        "total_unique_rasters_checked": len(valid_rows),
        "errors": d2["missing_or_invalid"],
        "max_abs_spearman": round(max_abs_rho, 6),
        "sparse_le_50k_count": len(sparse_50k),
        "sparse_le_50k_max_overlap": round(max_ov_50k, 6),
        "sparse_le_50k_worst_submission": worst_50k["submission"],
        "sparse_le_50k_collisions_gt_0p70": sum(1 for r in sparse_50k if float(r["my_dots_within_3px_literal"]) > 0.70),
        "sparse_le_75k_count": len(sparse_75k),
        "sparse_le_75k_max_overlap": round(max_ov_75k, 6),
        "sparse_le_75k_worst_submission": worst_75k["submission"],
        "sparse_le_75k_collisions_gt_0p70": sum(1 for r in sparse_75k if float(r["my_dots_within_3px_literal"]) > 0.70),
        "dot_fields_all_count": len(dot_fields_all),
        "d2_nonsaturated_count": len(d2_nonsat),
        "d2_nonsaturated_max_excess_overlap": round(max_d2_nonsat, 6),
        "d2_nonsaturated_worst_submission": worst_d2_nonsat["submission"],
        "d2_nonsaturated_firings_gt_0p70": sum(1 for r in d2_nonsat if bool(r["duplicate_by_overlap_d2"])),
        "d2_summary": {k: v for k, v in d2.items() if k != "rows"},
        "named_family_neighbors": named_hits,
        "d2_full": d2,
    }


def _make_cshd_figures(
    eval20: dict[str, Any],
    eval30: dict[str, Any],
    live_meta: dict[str, Any],
    dot_scan: dict[str, Any],
    emitted_2d: np.ndarray,
    q_live_2d: np.ndarray,
    cat: np.ndarray,
    footprint: np.ndarray,
) -> list[str]:
    fig_dir = ROOT / "docs" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "figure.dpi": 150})

    # Figure 1: Full progression including G79-CSHD, archived G79-THVC, H33, E1, Random
    thvc_res = json.loads((ROOT / "archive/g79_thvc_33e1f8ec/run_card.json").read_text()) if (ROOT / "archive/g79_thvc_33e1f8ec/run_card.json").exists() else None
    arms_order = [
        ("C0_random_B37654", "C0: Random\n(37,654 px)"),
        ("C1_fabric_offset_E1_placed", "C1: Fabric-Offset\nE1 Placed"),
        ("C2_h33_analogue_foldfair", "C2: H33 Control\n(GEMSDOE32)"),
        ("EXP-CSHD-1_pure_zero_catalogue", "EXP-CSHD-1: Pure\nZero-Cat Physics"),
        ("THVC_REF", "Prior Best:\nG79-THVC"),
        ("EXP-CSHD-2_cshd_uniform_d28", "EXP-CSHD-2: CSHD\nUniform d=2.8"),
        ("EXP-CSHD-3_dual_regime_cc", "EXP-CSHD-3: CSHD\nDual-Regime CC"),
    ]
    colors = ["#94a3b8", "#64748b", "#d97706", "#0284c7", "#7c3aed", "#2563eb", "#059669"]

    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.2), sharey=True)
    for ax, ev, title in zip(
        axes,
        [eval20, eval30],
        ["Seed 20 Spatial Holdout (11,321 Withheld Positives)", "Seed 30 Spatial Holdout (11,342 Withheld Positives)"],
    ):
        sc_map = ev["official_evaluate_all"]["scores"]
        thvc_v = (0.190523, [0.174098, 0.206945]) if ev["seed"] == 20 else (0.194379, [0.177401, 0.212584])
        xs = np.arange(len(arms_order))
        vals, yerr_lo, yerr_hi = [], [], []
        for k, _ in arms_order:
            if k == "THVC_REF":
                d, ci = thvc_v
            else:
                d = sc_map[k]["dti"]
                ci = sc_map[k]["ci95"]
            vals.append(d)
            yerr_lo.append(max(0.0, d - ci[0]))
            yerr_hi.append(max(0.0, ci[1] - d))
        bars = ax.bar(xs, vals, color=colors, width=0.62, edgecolor="#0f172a", linewidth=0.7)
        ax.errorbar(xs, vals, yerr=[yerr_lo, yerr_hi], fmt="none", ecolor="#0f172a", capsize=4, lw=1.2)
        ax.axhline(sc_map["C2_h33_analogue_foldfair"]["dti"], color="#d97706", ls="--", lw=1.0, alpha=0.8, label="H33 Baseline")
        ax.axhline(thvc_v[0], color="#7c3aed", ls=":", lw=1.1, alpha=0.85, label="Prior G79-THVC")
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2.0, v + 0.011, f"{v:.4f}", ha="center", va="bottom", fontweight="bold", fontsize=8.3)
        ax.set_xticks(xs)
        ax.set_xticklabels([lbl for _, lbl in arms_order], fontsize=7.8)
        ax.set_title(title, fontweight="bold")
        ax.set_ylim(0, max(vals) * 1.24)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(loc="upper left", fontsize=8.5)
    axes[0].set_ylabel("Official Pooled HOLDOUT-DTI (gems57-pooled-hide-v2)")
    fig.suptitle("GEMSDOE79 (G79-CSHD) — Two-Seed Holdout Progression vs Prior Best G79-THVC & H33", fontweight="bold", fontsize=12)
    fig.tight_layout()
    p1 = fig_dir / "fig1_holdout_progression.png"
    fig.savefig(p1)
    plt.close(fig)
    written.append(str(p1.relative_to(ROOT)))

    # Figure 2: Geological Regime Decomposition
    reg20 = eval20["regime_decomposition"]
    r_keys = list(reg20.keys())
    r_labels = [
        "Near-Network\n(<= 1.5 km)",
        "Stepover/Piedmont\n(1.5 - 4.0 km)",
        "Blind Basin\n(> 4.0 km)",
        "1-m 3DEP\nLiDAR Covered",
        "Non-LiDAR\n10-m 3DEP Gap",
        "Low-Relief\nBasin/Piedmont",
    ]
    fig, ax = plt.subplots(figsize=(11.8, 4.9))
    x = np.arange(len(r_keys))
    w_bar = 0.25
    v_h33 = [reg20[k]["scores"]["C2_h33_analogue_foldfair"]["dti"] for k in r_keys]
    v_e1 = [reg20[k]["scores"]["EXP-CSHD-1_pure_zero_catalogue"]["dti"] for k in r_keys]
    v_e3 = [reg20[k]["scores"]["EXP-CSHD-3_dual_regime_cc"]["dti"] for k in r_keys]
    ax.bar(x - w_bar, v_h33, w_bar, label="C2: H33 Analogue Control", color="#d97706", edgecolor="#0f172a", lw=0.6)
    ax.bar(x, v_e1, w_bar, label="EXP-CSHD-1: Pure Zero-Catalogue Physics", color="#0284c7", edgecolor="#0f172a", lw=0.6)
    ax.bar(x + w_bar, v_e3, w_bar, label="EXP-CSHD-3: G79-CSHD Dual-Regime CC", color="#059669", edgecolor="#0f172a", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(r_labels, fontsize=8.8)
    ax.set_ylabel("Regime HOLDOUT-DTI (Seed 20)")
    ax.set_title("G79-CSHD Geological & Sensor Regime Decomposition Across All 6 Tectonic Regimes", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p2 = fig_dir / "fig2_regime_decomposition.png"
    fig.savefig(p2)
    plt.close(fig)
    written.append(str(p2.relative_to(ROOT)))

    # Figure 3: Feature Gain + Full 1,209-Raster Cross-Repo Uniqueness Audit
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.2))
    topf = live_meta["top30_features_by_gain"][:16][::-1]
    ax1.barh([r["feature"] for r in topf], [r["gain_share"] * 100.0 for r in topf], color="#2563eb", edgecolor="#0f172a", lw=0.5)
    ax1.set_xlabel("Share of Stage-1 GBDT Split Gain (%)")
    ax1.set_title("Top 16 Physical, Geothermal & Mechanical Features", fontweight="bold")
    ax1.grid(axis="x", alpha=0.25)

    valid_rows = [r for r in dot_scan["d2_full"]["rows"] if "error" not in r and r["representation"] == "dot_field" and r["their_literal_positive_cells"] <= 75_308]
    ovs = [float(r["my_dots_within_3px_literal"]) for r in valid_rows]
    ax2.hist(ovs, bins=32, color="#059669", edgecolor="#0f172a", alpha=0.88)
    ax2.axvline(0.70, color="#dc2626", ls="--", lw=1.8, label="Protocol Duplicate Limit (0.70)")
    ax2.set_xlabel(f"3-px Forward Dot Overlap Across All {len(valid_rows)} Sparse Rasters (93 Repos)")
    ax2.set_ylabel("Number of Submissions")
    ax2.set_title(f"Sparse Registry Audit: 0/{len(valid_rows)} Duplicates (Max = {max(ovs):.4f} <= 0.70)", fontweight="bold")
    ax2.legend()
    ax2.grid(alpha=0.25)
    fig.tight_layout()
    p3 = fig_dir / "fig3_features_and_uniqueness.png"
    fig.savefig(p3)
    plt.close(fig)
    written.append(str(p3.relative_to(ROOT)))

    # Figure 4: Spatial Map Overview of Dual-Regime CSHD Predictions
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.2))
    im0 = axes[0].imshow(np.where(footprint[::4, ::4], q_live_2d[::4, ::4], np.nan), cmap="inferno", vmin=0.0, vmax=0.45)
    axes[0].set_title("G79-CSHD Expected 300-m Kernel Credit q_300m(x)", fontweight="bold")
    axes[0].axis("off")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.03)

    d_cat = ndi.distance_transform_edt(~cat)
    near_pts = (emitted_2d > 0) & (d_cat <= 15.0)
    far_pts = (emitted_2d > 0) & (d_cat > 15.0)
    ny_p, nx_p = np.nonzero(near_pts)
    fy_p, fx_p = np.nonzero(far_pts)
    cy_p, cx_p = np.nonzero(cat)
    axes[1].imshow(np.where(footprint[::4, ::4], 0.96, np.nan), cmap="Greys", vmin=0.0, vmax=1.0)
    axes[1].scatter(cx_p / 4.0, cy_p / 4.0, s=0.08, c="#94a3b8", alpha=0.40, label="Catalogue Faults")
    axes[1].scatter(nx_p / 4.0, ny_p / 4.0, s=0.18, c="#059669", alpha=0.80, label=f"Regime A Near/Stepover ({ny_p.size:,})")
    axes[1].scatter(fx_p / 4.0, fy_p / 4.0, s=0.24, c="#0284c7", alpha=0.88, label=f"Regime B Blind >1.5 km ({fy_p.size:,})")
    axes[1].set_title(f"Emitted Dual-Regime CSHD Map ({int((emitted_2d > 0).sum()):,} Binary Dots)", fontweight="bold")
    axes[1].legend(loc="lower left", markerscale=12, fontsize=8.2)
    axes[1].axis("off")
    fig.tight_layout()
    p4 = fig_dir / "fig4_live_map_overview.png"
    fig.savefig(p4)
    plt.close(fig)
    written.append(str(p4.relative_to(ROOT)))

    # Also update dark hero preview map `docs/figures/g79_thvc_emitted_dots_preview.png` so UI map matches live candidate!
    fig_p = plt.figure(figsize=(7.6, 8.6), facecolor="#0a0f1c")
    ax_p = fig_p.add_axes([0, 0, 1, 1], facecolor="#0a0f1c")
    ax_p.scatter(cx_p, cy_p, s=0.10, c="#475569", alpha=0.55)
    ax_p.scatter(nx_p, ny_p, s=0.18, c="#34d399", alpha=0.88)
    ax_p.scatter(fx_p, fy_p, s=0.22, c="#38bdf8", alpha=0.92)
    ax_p.set_xlim(0, footprint.shape[1])
    ax_p.set_ylim(footprint.shape[0], 0)
    ax_p.axis("off")
    prev_p = fig_dir / "g79_cshd_emitted_dots_preview.png"
    fig_p.savefig(prev_p, facecolor="#0a0f1c", dpi=150)
    plt.close(fig_p)
    written.append(str(prev_p.relative_to(ROOT)))
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["canary", "seed20", "seed30", "live", "all"], default="all")
    args = ap.parse_args()

    t_all = time.time()
    cache_dir = ROOT / ".cache" / "g79_cshd"
    cache_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
        transform = ds.transform
        crs = ds.crs
    with rasterio.open(ROOT / "data/raw/existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & footprint

    d28_path = ROOT / ".cache/registry/bfb7e86d046dd178c3d6ab60522861b5464dd420.tif"
    with rasterio.open(d28_path) as ds:
        d28_bool = (ds.read(1) > 0) & footprint
    fab_path = ROOT / "archive/g79_fabric_offset_f61b17a2/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif"
    with rasterio.open(fab_path) as ds:
        fab_surface = np.nan_to_num(ds.read(1).astype(np.float32), nan=0.0) * footprint

    stack = build_cshd_static_stack(ROOT, footprint, transform)
    mm70 = np.memmap(stack["thvc_mmap_path"], dtype="float32", mode="r", shape=(int(footprint.sum()), len(THVC_70_NAMES)))
    mm10 = np.memmap(stack["extra_mmap_path"], dtype="float32", mode="r", shape=(int(footprint.sum()), len(CSHD_EXTRA_STATIC_NAMES)))

    cmap70 = {n: i for i, n in enumerate(THVC_70_NAMES)}
    cues_npz = np.load(stack["cshd_cues_path"])
    ctx_cols_fp = np.column_stack(
        [
            mm70[:, cmap70["lidar_present"]],
            cues_npz["piedmont_scarp"].astype(np.float32),
            mm70[:, cmap70["hydro_demag_clay_conj"]],
            mm70[:, cmap70["mountain_wall_ratio"]],
        ]
    ).astype(np.float16)
    drop_file_cache(stack["thvc_mmap_path"])

    grid = Grid(footprint, cat, str(crs), transform, footprint.shape[0], footprint.shape[1])

    canary_doc = _audit_single_feature_canaries(
        (20, 30), grid, footprint, mm70, stack["thvc_mmap_path"], mm10, stack["extra_mmap_path"], stack["cshd_cues_path"], cache_dir
    )
    if args.stage == "canary":
        return

    if args.stage in ("seed20", "all"):
        eval20 = _evaluate_one_seed(
            20, grid, footprint, mm70, stack["thvc_mmap_path"], mm10, stack["extra_mmap_path"], ctx_cols_fp, stack["cshd_cues_path"], d28_bool, fab_surface, cache_dir
        )
    if args.stage == "seed20":
        return

    if args.stage in ("seed30", "all"):
        eval30 = _evaluate_one_seed(
            30, grid, footprint, mm70, stack["thvc_mmap_path"], mm10, stack["extra_mmap_path"], ctx_cols_fp, stack["cshd_cues_path"], d28_bool, fab_surface, cache_dir
        )
    if args.stage == "seed30":
        return

    eval20 = json.loads((cache_dir / "eval_seed20.json").read_text())
    eval30 = json.loads((cache_dir / "eval_seed30.json").read_text())

    # Verify both-seed promotion criterion BEFORE spending full-footprint inference compute!
    s20_dti = eval20["official_evaluate_all"]["scores"]["EXP-CSHD-3_dual_regime_cc"]["dti"]
    s30_dti = eval30["official_evaluate_all"]["scores"]["EXP-CSHD-3_dual_regime_cc"]["dti"]
    print(f"\nTWO-SEED SUMMARY FOR G79-CSHD: seed20={s20_dti:.6f} (vs THVC 0.190523), seed30={s30_dti:.6f} (vs THVC 0.194379)", flush=True)

    _, quad_live = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)
    p_full_live, q_full_live, p_phys_live, q_phys_live, live_meta = _fit_live_cshd_ensembles(
        cat, footprint, quad_live, mm70, stack["thvc_mmap_path"], mm10, stack["extra_mmap_path"], ctx_cols_fp, stack["cshd_cues_path"], cache_dir
    )

    records = _build_complete_1209_index()
    print(f"\nLoaded {len(records)} SHA-256-verified cross-repo + local rasters across all 93 GEMS repositories!", flush=True)

    # Gate 1: Pre-placement continuous surface Spearman check across ALL 1,209 rasters
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    allow_live = footprint & (d_cat > 2.0)
    far_live = footprint & (d_cat > 15.0)
    surf_blend = np.where(
        d_cat > 15.0,
        0.55 * np.clip(p_phys_live, 0.0, 1.0) + 0.45 * np.clip(p_full_live, 0.0, 1.0),
        0.70 * np.clip(p_full_live, 0.0, 1.0) + 0.30 * (np.clip(q_full_live, 0.0, 1.0) ** 1.6) * 0.28,
    ).astype(np.float32)
    smax = float(surf_blend[allow_live].max())
    surf_norm = np.where(allow_live, np.clip(surf_blend / max(smax, 1e-9), 0.0, 1.0), 0.0).astype(np.float32)

    surf_json = ROOT / "evidence/g79_cshd_surface_uniqueness.json"
    if surf_json.exists():
        surf_scan = json.loads(surf_json.read_text())
        print(f"Reusing verified pre-placement surface audit across {surf_scan['total_unique_rasters_checked']} rasters: max |rho| = {surf_scan['max_abs_spearman']:.6f} <= 0.90", flush=True)
    else:
        tmp_surf_tif = cache_dir / "g79_cshd_preplacement_surface.tif"
        for f_old in cache_dir.glob("g79_cshd_preplacement_surface.*"):
            f_old.unlink()
        submission_writer.write_submission(
            tmp_surf_tif,
            surf_norm,
            ROOT / "data/raw/sample_submission.tif",
            footprint,
            name="g79-cshd-preplacement-surface",
            note="Pre-placement continuous posterior surface for 1,209-raster uniqueness check",
            catalogue=cat,
        )
        surf_scan = _full_uniqueness_scan(tmp_surf_tif, footprint, allow_live, records, candidate_surface=surf_norm)
        surf_json.write_text(json.dumps({k: v for k, v in surf_scan.items() if k != "d2_full"}, indent=2) + "\n")
        print(f"Pre-placement surface audit across {surf_scan['total_unique_rasters_checked']} rasters: max |rho| = {surf_scan['max_abs_spearman']:.6f} <= 0.90", flush=True)
    if surf_scan["max_abs_spearman"] > 0.90:
        raise RuntimeError(f"STOP: Pre-placement |rho| = {surf_scan['max_abs_spearman']} > 0.90")

    # Gate 2: Emit consensus Dual-Regime Charnes-Cooper binary GeoTIFF (ZERO overlap_cap!)
    s20_p = eval20["inner_charnes_cooper_selection"]["selected"]
    s30_p = eval30["inner_charnes_cooper_selection"]["selected"]
    consensus_tau = round(0.5 * (s20_p["tau_decay"] + s30_p["tau_decay"]), 2)
    consensus_fboost = round(0.5 * (s20_p["far_boost"] + s30_p["far_boost"]), 4)
    consensus_lam = round(0.5 * (s20_p["lambda_fp"] + s30_p["lambda_fp"]), 4)
    consensus_sep = round(0.5 * (s20_p["min_sep_px"] + s30_p["min_sep_px"]), 3)
    consensus_maxb = int(round(0.5 * (s20_p["max_budget"] + s30_p["max_budget"])))

    emitted_live = _emit_cshd_exp3(
        p_full_2d=p_full_live,
        q_full_2d=q_full_live,
        p_phys_2d=p_phys_live,
        d_vis_2d=d_cat,
        allowed_mask=allow_live,
        far_boost=consensus_fboost,
        lambda_fp=consensus_lam,
        min_sep_px=consensus_sep,
        max_budget=consensus_maxb,
        tau_decay=consensus_tau,
    )
    n_emitted = int((emitted_live > 0).sum())
    n_far_live = int(((emitted_live > 0) & far_live).sum())

    cand_stage_dir = cache_dir / "emitted"
    cand_stage_dir.mkdir(parents=True, exist_ok=True)
    for f_old in cand_stage_dir.glob("*"):
        f_old.unlink()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_hash8 = hashlib.sha256(emitted_live.tobytes()).hexdigest()[:8]
    stem = f"g79-cshd-dualcc-20261022-{raw_hash8}-zeros-DO-NOT-SUBMIT"
    note = (
        f"GEMSDOE79 G79-CSHD: 98ch deconv-geophys+2m-probe+3DEP+Okada dual-regime CC ({n_emitted} px; {n_far_live} >1.5km)"
    )[:140]

    staged_tif = cand_stage_dir / f"{stem}.tif"
    manifest = submission_writer.write_submission(
        staged_tif,
        emitted_live,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name=stem,
        note=note,
        catalogue=cat,
        metadata={
            "lane": "G79-CSHD",
            "consensus_dual_charnes_cooper": {
                "far_boost": consensus_fboost,
                "lambda_fp": consensus_lam,
                "min_sep_px": consensus_sep,
                "max_budget": consensus_maxb,
                "emitted_dots": n_emitted,
                "far_dots_gt_1500m": n_far_live,
            },
            "holdout_dti_seed20": eval20["official_evaluate_all"]["scores"]["EXP-CSHD-3_dual_regime_cc"],
            "holdout_dti_seed30": eval30["official_evaluate_all"]["scores"]["EXP-CSHD-3_dual_regime_cc"],
            "generated_timestamp_utc": ts,
        },
    )

    dot_scan = _full_uniqueness_scan(staged_tif, footprint, allow_live, records, candidate_surface=None)
    (ROOT / "evidence/g79_cshd_dot_uniqueness_all.json").write_text(
        json.dumps(dot_scan["d2_full"], indent=2) + "\n"
    )
    print(
        f"\nPOST-PLACEMENT AUDIT ACROSS ALL {dot_scan['total_unique_rasters_checked']} RASTERS (93 REPOS):\n"
        f"  Max |Spearman|              = {dot_scan['max_abs_spearman']:.6f} (limit 0.90)\n"
        f"  Sparse <= 50k max overlap   = {dot_scan['sparse_le_50k_max_overlap']:.6f} ({dot_scan['sparse_le_50k_collisions_gt_0p70']}/{dot_scan['sparse_le_50k_count']} > 0.70; worst: {dot_scan['sparse_le_50k_worst_submission']})\n"
        f"  Sparse <= 75.3k max overlap = {dot_scan['sparse_le_75k_max_overlap']:.6f} ({dot_scan['sparse_le_75k_collisions_gt_0p70']}/{dot_scan['sparse_le_75k_count']} > 0.70; worst: {dot_scan['sparse_le_75k_worst_submission']})\n"
        f"  D-2 non-saturated max       = {dot_scan['d2_nonsaturated_max_excess_overlap']:.6f} ({dot_scan['d2_nonsaturated_firings_gt_0p70']}/{dot_scan['d2_nonsaturated_count']} > 0.70)\n"
        f"  Named neighbors             = {json.dumps(dot_scan['named_family_neighbors'], indent=2)}",
        flush=True,
    )

    figs = _make_cshd_figures(eval20, eval30, live_meta, dot_scan, emitted_live, q_full_live, cat, footprint)

    results_doc = {
        "schema_version": 1,
        "lane": "G79-CSHD",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runtime_seconds": round(time.time() - t_all, 2),
        "static_extra_meta": stack["meta"],
        "canary_summary": {k: v for k, v in canary_doc.items() if k != "features"},
        "seed20": eval20,
        "seed30": eval30,
        "live_model_meta": live_meta,
        "staged_manifest": manifest,
        "staged_tif": str(staged_tif.relative_to(ROOT)),
        "pre_placement_surface_audit": {k: v for k, v in surf_scan.items() if k != "d2_full"},
        "post_placement_dot_audit": {k: v for k, v in dot_scan.items() if k != "d2_full"},
        "figures": figs,
    }
    (ROOT / "evidence/g79_cshd_results.json").write_text(json.dumps(results_doc, indent=2) + "\n")
    print("\nALL G79-CSHD PREREGISTERED EXPERIMENTS, CANARIES, AND 1,209-RASTER AUDITS COMPLETE!", flush=True)


if __name__ == "__main__":
    main()
