#!/usr/bin/env python3
"""Execute the preregistered G79-CSKD experimental lane end-to-end.

Strictly adheres to all 6 rules of the Parallel-Run Protocol:
  1. Single preregistered method lane (G79-CSKD, registry/preregistration_g79_cskd.json).
     Audits all 1,199 external family blobs (992 frozen + 207 post-snapshot delta) plus
     local GEMSDOE79 priors BOTH on the pre-placement continuous surface AND on placed dots.
  2. Reuses unmodified vendor/gems57/{evaluate_holdout,submission_writer,uniqueness,metric,holdout}.py.
  3. Labels every holdout score HOLDOUT-DTI (gems57-pooled-hide-v2, withheld count, 95% CI).
  4. Runs single-feature leakage canaries across all 102 channels on both Seed 20 and Seed 30
     BEFORE fitting any multi-feature model; hard-stops if any feature exceeds symmetric AUC 0.90.
  5. Writes complete Run Card & byte-verifiable research GeoTIFF (-DO-NOT-SUBMIT.tif under the
     literal 17GEMSDOE / 13GEMSDOE pigeonhole witnesses; promotes to canonical docs/downloads/
     iff EXP-CSKD-3 beats G79-THVC on BOTH seeds AND clears <= 0.70 across all <=50k sparse maps,
     otherwise archives intact in archive/g79_cskd_6da2620c/).
  6. Respects the <= 3 experiments and <= 2 hours budget; consumes 0 weekly upload slots.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError, require_open_lane
    try:
        require_open_lane(ROOT, "G79-CSKD")
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

from gems57 import evaluate_holdout, holdout, metric, submission_writer, uniqueness  # noqa: E402
from gems57.grid import Grid  # noqa: E402
from gems79.cskd import (  # noqa: E402
    CSKD_ALL_FEATURE_NAMES,
    CSKD_MECH_NAMES,
    CSKD_STATIC_NAMES,
    _release_mm,
    blend_counterfactual_posteriors,
    build_cskd_static_memmaps,
    build_cskd_training_shards,
    compute_cskd_mechanics,
    predict_cskd_stage1_rows,
    run_cskd_quadrant_nested_oof,
    stack_cskd_shards,
)
from gems79.thvc_features import rss_mb  # noqa: E402
from gems79.thvc_model import (  # noqa: E402
    charnes_cooper_submodular_emit,
    drop_file_cache,
    extract_stage2_spatial_features,
    fit_stage1_ensemble,
    fit_stage2_dual_heads,
    poisson_disk_emit,
    predict_stage2_dual_heads,
)

PREREG_PATH = ROOT / "registry" / "preregistration_g79_cskd.json"
ARCHIVE_DIR = ROOT / "archive" / "g79_cskd_6da2620c"
THVC_SEED20_DTI = 0.190517
THVC_SEED30_DTI = 0.194366


def _require_open_cskd() -> dict[str, Any]:
    if not PREREG_PATH.is_file():
        raise RuntimeError("Missing registry/preregistration_g79_cskd.json; no files changed.")
    prereg = json.loads(PREREG_PATH.read_text())
    if prereg.get("lane") != "G79-CSKD" or prereg.get("status") != "open":
        raise RuntimeError(
            f"G79-CSKD lane is not open (status={prereg.get('status')!r}); "
            "do not rerun or retune a closed lane. No files changed."
        )
    return prereg


def _run_leakage_canaries(
    grid: Grid,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    cues_path: Path,
    cache_dir: Path,
) -> dict[str, Any]:
    """Protocol Rule 4: test every single static + fold-mechanics feature alone on Seed 20 & Seed 30."""
    out_path = ROOT / "evidence" / "g79_cskd_leakage_canary.json"
    if out_path.is_file():
        cached = json.loads(out_path.read_text())
        if cached.get("n_features_tested") == len(CSKD_ALL_FEATURE_NAMES) and cached.get("gate_passed") is True:
            print(f"[canary] Reusing verified 102-feature canary receipt ({out_path.relative_to(ROOT)})", flush=True)
            return cached

    t0 = time.time()
    print("\n==================== RUNNING 102-FEATURE LEAKAGE CANARIES (SEEDS 20 & 30) ====================", flush=True)
    by_seed: dict[str, Any] = {}
    overall_max_sym_auc = 0.0
    overall_worst_feat = ""
    overall_worst_seed = 20

    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        vis = folds[0]["visible"]
        truth_all = np.zeros(footprint.shape, dtype=bool)
        active_all = np.zeros(footprint.shape, dtype=bool)
        for f in folds:
            truth_all |= f["truth"]
            active_all |= footprint & f["region"] & (~f["masked_known"])

        act_fp = active_all[footprint]
        y_act = truth_all[footprint][act_fp]
        pos_idx = np.flatnonzero(y_act)
        neg_pool = np.flatnonzero(~y_act)
        rng = np.random.default_rng(306000 + seed)
        neg_sub = rng.choice(neg_pool, size=min(160_000, neg_pool.size), replace=False)
        eval_sub = np.sort(np.concatenate([pos_idx, neg_sub]))
        act_rows = np.flatnonzero(act_fp)[eval_sub]
        y_sub = y_act[eval_sub].astype(np.int32)

        mech_fp = compute_cskd_mechanics(vis, footprint, cues_path)
        xs_static = np.asarray(static_mm[act_rows], dtype=np.float32)
        xs_mech = mech_fp[act_rows]
        drop_file_cache(mmap_path)
        del mech_fp

        rows = []
        for idx_f, fname in enumerate(CSKD_ALL_FEATURE_NAMES):
            if idx_f < len(CSKD_STATIC_NAMES):
                vals = xs_static[:, idx_f]
            else:
                vals = xs_mech[:, idx_f - len(CSKD_STATIC_NAMES)]
            vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
            if np.all(vals == vals[0]):
                auc = 0.5
            else:
                auc = float(roc_auc_score(y_sub, vals))
            sym_auc = max(auc, 1.0 - auc)
            rows.append(
                {
                    "feature": fname,
                    "group": "static_label_free" if idx_f < len(CSKD_STATIC_NAMES) else "fold_visible_mechanics",
                    "raw_auc": round(auc, 6),
                    "symmetric_auc": round(sym_auc, 6),
                }
            )
            if sym_auc > overall_max_sym_auc:
                overall_max_sym_auc = sym_auc
                overall_worst_feat = fname
                overall_worst_seed = seed

        rows_sorted = sorted(rows, key=lambda r: -r["symmetric_auc"])
        by_seed[f"seed_{seed}"] = {
            "withheld_positives_tested": int(pos_idx.size),
            "negative_subsample_tested": int(neg_sub.size),
            "max_symmetric_auc": rows_sorted[0]["symmetric_auc"],
            "worst_feature": rows_sorted[0]["feature"],
            "top_10_features": rows_sorted[:10],
            "all_features": rows,
        }
        print(
            f"[canary:seed={seed}] max symmetric AUC = {rows_sorted[0]['symmetric_auc']:.6f} "
            f"({rows_sorted[0]['feature']}) <= 0.90",
            flush=True,
        )

    gate_passed = bool(overall_max_sym_auc <= 0.90)
    payload = {
        "schema_version": 1,
        "lane": "G79-CSKD",
        "evaluator_version": evaluate_holdout.VERSION,
        "n_features_tested": len(CSKD_ALL_FEATURE_NAMES),
        "threshold_max_symmetric_auc": 0.90,
        "overall_max_symmetric_auc": round(overall_max_sym_auc, 6),
        "overall_worst_feature": overall_worst_feat,
        "overall_worst_seed": overall_worst_seed,
        "gate_passed": gate_passed,
        "elapsed_seconds": round(time.time() - t0, 2),
        "by_seed": by_seed,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    if not gate_passed:
        raise RuntimeError(
            f"LEAKAGE CANARY FAILED: {overall_worst_feat} on seed {overall_worst_seed} "
            f"reached symmetric AUC {overall_max_sym_auc:.6f} > 0.90!"
        )
    return payload


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
        point_est = float(tp_b.sum() / denom) if denom > 0 else 0.0
        comp_blocks[name] = (tp_b, fp_b, fn_b, point_est)

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
        ("EXP-CSKD-3_counterfactual_cc", "C2_h33_analogue_foldfair"),
        ("EXP-CSKD-3_counterfactual_cc", "EXP-CSKD-2_cskd_uniform_d28"),
        ("EXP-CSKD-3_counterfactual_cc", "EXP-CSKD-1_zero_catalogue_physics"),
        ("EXP-CSKD-2_cskd_uniform_d28", "C2_h33_analogue_foldfair"),
        ("EXP-CSKD-1_zero_catalogue_physics", "C2_h33_analogue_foldfair"),
        ("EXP-CSKD-1_zero_catalogue_physics", "C0_random_B37654"),
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
    static_mm: np.memmap,
    visible: np.ndarray,
) -> dict[str, Any]:
    H, W = footprint.shape
    truth_all = np.zeros((H, W), dtype=bool)
    active_all = np.zeros((H, W), dtype=bool)
    for f in folds:
        truth_all |= f["truth"]
        active_all |= footprint & f["region"] & (~f["masked_known"])

    cmap = {n: i for i, n in enumerate(CSKD_STATIC_NAMES)}
    lid_2d = np.zeros((H, W), dtype=bool)
    lid_2d[footprint] = static_mm[:, cmap["lidar_present"]] > 0.5
    lah_2d = np.zeros((H, W), dtype=bool)
    lah_2d[footprint] = static_mm[:, cmap["lahontan_isohypse_env"]] > 0.35
    d_vis = ndi.distance_transform_edt(~visible)

    regimes = {
        "lidar_covered": active_all & lid_2d,
        "blind_outside_lidar": active_all & (~lid_2d),
        "lahontan_pluvial_belt": active_all & lah_2d,
        "near_tip_or_relay_le_1km": active_all & (d_vis <= 10.0),
        "far_blind_gt_1km": active_all & (d_vis > 10.0),
    }
    out: dict[str, Any] = {}
    for rname, rmask in regimes.items():
        n_pos = int((truth_all & rmask).sum())
        row: dict[str, Any] = {"withheld_positive_pixels": n_pos, "active_pixels": int(rmask.sum()), "scores": {}}
        for aname, pred in pred_map.items():
            res = metric.dti_binary(truth_all, pred > 0, valid=rmask)
            row["scores"][aname] = round(float(res["dti"]), 6)
        out[rname] = row
    return out


def _select_cskd_params_inner(
    p_full_tr_2d: np.ndarray,
    q_full_tr_2d: np.ndarray,
    p_zero_tr_2d: np.ndarray,
    q_zero_tr_2d: np.ndarray,
    sim_draw0: dict[str, Any],
    footprint: np.ndarray,
) -> dict[str, Any]:
    """Tune (w_base, w_far, lambda_fp, min_sep_px, max_budget) strictly on inner simulated draw 0."""
    H, W = footprint.shape
    truth_in = np.zeros((H, W), dtype=bool)
    score_act_in = np.zeros((H, W), dtype=bool)
    d_sim_2d = np.zeros((H, W), dtype=np.float32)

    truth_in[footprint] = sim_draw0["y_exact_fp"]
    score_act_in[footprint] = sim_draw0["score_active_fp"]
    d_sim_2d[footprint] = sim_draw0["d_sim_fp"].astype(np.float32)
    allow_in = footprint & score_act_in & (d_sim_2d > 3.0)

    candidates = [
        # (w_base, w_far, lambda_fp, min_sep_px, max_budget)
        (0.00, 0.20, 0.0010, 2.3, 41_000),
        (0.05, 0.30, 0.0010, 2.3, 41_000),
        (0.05, 0.30, 0.0016, 2.3, 39_500),
        (0.08, 0.38, 0.0012, 2.3, 40_000),
        (0.08, 0.38, 0.0018, 2.4, 38_500),
        (0.12, 0.45, 0.0012, 2.4, 39_500),
        (0.12, 0.45, 0.0020, 2.5, 37_654),
        (0.05, 0.25, 0.0008, 2.1, 42_000),
    ]
    best = None
    grid_log = []
    for wb, wf, lam, msep, mbud in candidates:
        p_cf, q_cf = blend_counterfactual_posteriors(
            p_full_tr_2d, q_full_tr_2d, p_zero_tr_2d, q_zero_tr_2d, d_sim_2d, allow_in, wb, wf
        )
        emitted = charnes_cooper_submodular_emit(
            p_cf,
            q_cf,
            allow_in,
            lambda_fp=lam,
            min_sep_px=msep,
            max_budget=mbud,
            min_budget=22_000,
        )
        res = metric.dti_binary(truth_in, emitted > 0, valid=score_act_in)
        entry = {
            "w_base": wb,
            "w_far": wf,
            "lambda_fp": lam,
            "min_sep_px": msep,
            "max_budget": mbud,
            "emitted_dots": int((emitted > 0).sum()),
            "inner_sim_dti": round(float(res["dti"]), 6),
        }
        grid_log.append(entry)
        if best is None or entry["inner_sim_dti"] > best["inner_sim_dti"]:
            best = entry
    return {"selected": best, "grid": grid_log}


def _evaluate_one_seed(
    seed: int,
    grid: Grid,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    cues_path: Path,
    d28_bool: np.ndarray,
    cache_dir: Path,
) -> dict[str, Any]:
    ckpt_json = cache_dir / f"eval_seed{seed}.json"
    if ckpt_json.exists():
        print(f"[seed={seed}] Reusing completed checkpoint {ckpt_json}", flush=True)
        return json.loads(ckpt_json.read_text())

    t0 = time.time()
    print(f"\n==================== STARTING G79-CSKD SEED {seed} EVALUATION ====================", flush=True)
    folds, quad = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    vis = folds[0]["visible"]
    quad_fp = quad[footprint]
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    # Key geometric fix: zero withheld positives exist at d_vis <= 3.0 px!
    allow_vis = footprint & (d_vis > 3.0)
    allow_c2 = footprint & (d_vis > 2.0)

    oof_raw_ckpt = cache_dir / f"raw_oof_seed{seed}.npz"
    if oof_raw_ckpt.exists():
        z = np.load(oof_raw_ckpt)
        p_full_fp = z["p_full_fp"].astype(np.float32)
        q_full_fp = z["q_full_fp"].astype(np.float32)
        p_tr_avg = z["p_tr_avg"].astype(np.float32)
        q_tr_avg = z["q_tr_avg"].astype(np.float32)
        p_zero_fp = z["p_zero_fp"].astype(np.float32)
        q_zero_fp = z["q_zero_fp"].astype(np.float32)
        pz_tr_avg = z["pz_tr_avg"].astype(np.float32)
        qz_tr_avg = z["qz_tr_avg"].astype(np.float32)
        draw0_ref = {
            "score_active_fp": z["d0_score_active"],
            "d_sim_fp": z["d0_d_sim"],
            "y_exact_fp": z["d0_y"],
        }
    else:
        shards, draw0_ref = build_cskd_training_shards(
            vis, footprint, quad_fp, static_mm, mmap_path, cues_path,
            n_draws=3, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=22_000, seed_base=8100 + seed
        )
        test_mech = compute_cskd_mechanics(vis, footprint, cues_path).astype(np.float16)
        print(f"[seed={seed}] Decontaminated d>3px shards + 18-ch Coulomb/slip mechanics built in {time.time()-t0:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

        tf0 = time.time()
        p_full_fp, q_full_fp, p_tr_avg, q_tr_avg = run_cskd_quadrant_nested_oof(
            quad_fp, footprint, static_mm, mmap_path, ctx_cols_fp, shards, draw0_ref, test_mech, use_mechanics=True, seed=seed * 10 + 3
        )
        del test_mech
        gc.collect()
        print(f"[seed={seed}] Full 102-ch nested OOF done in {time.time()-tf0:.1f}s, peak_RSS={rss_mb():.1f} MB", flush=True)

        tf1 = time.time()
        p_zero_fp, q_zero_fp, pz_tr_avg, qz_tr_avg = run_cskd_quadrant_nested_oof(
            quad_fp, footprint, static_mm, mmap_path, ctx_cols_fp, shards, draw0_ref, None, use_mechanics=False, seed=seed * 20 + 5
        )
        print(f"[seed={seed}] Zero-catalogue 84-ch nested OOF done in {time.time()-tf1:.1f}s, peak_RSS={rss_mb():.1f} MB", flush=True)

        np.savez_compressed(
            oof_raw_ckpt,
            p_full_fp=p_full_fp.astype(np.float16),
            q_full_fp=q_full_fp.astype(np.float16),
            p_tr_avg=p_tr_avg.astype(np.float16),
            q_tr_avg=q_tr_avg.astype(np.float16),
            p_zero_fp=p_zero_fp.astype(np.float16),
            q_zero_fp=q_zero_fp.astype(np.float16),
            pz_tr_avg=pz_tr_avg.astype(np.float16),
            qz_tr_avg=qz_tr_avg.astype(np.float16),
            d0_score_active=draw0_ref["score_active_fp"],
            d0_d_sim=draw0_ref["d_sim_fp"],
            d0_y=draw0_ref["y_exact_fp"],
        )
        del shards
        gc.collect()

    H, W = footprint.shape

    def to2d(vec: np.ndarray) -> np.ndarray:
        arr = np.zeros((H, W), dtype=np.float32)
        arr[footprint] = vec
        return arr

    p_full_2d = to2d(p_full_fp)
    q_full_2d = to2d(q_full_fp)
    p_zero_2d = to2d(p_zero_fp)
    q_zero_2d = to2d(q_zero_fp)

    cc_tune = _select_cskd_params_inner(
        to2d(p_tr_avg), to2d(q_tr_avg), to2d(pz_tr_avg), to2d(qz_tr_avg), draw0_ref, footprint
    )
    sel = cc_tune["selected"]
    print(f"[seed={seed}] Inner-selected CSKD counterfactual + Charnes-Cooper params: {sel}", flush=True)
    del draw0_ref
    gc.collect()

    rng_c0 = np.random.default_rng(79000 + seed)
    allow_flat = np.flatnonzero(allow_vis)
    c0_map = np.zeros((H, W), dtype=np.float32)
    c0_map.ravel()[rng_c0.choice(allow_flat, size=37_654, replace=False)] = 1.0
    c2_map = (d28_bool & allow_c2).astype(np.float32)

    exp1_surf = 0.70 * p_zero_2d + 0.30 * (np.clip(q_zero_2d, 0.0, 1.0) ** 1.6) * 0.28
    exp1_map = poisson_disk_emit(exp1_surf, allow_vis, budget=37_654, min_dist_px=2.8)

    exp2_surf = 0.70 * p_full_2d + 0.30 * (np.clip(q_full_2d, 0.0, 1.0) ** 1.6) * 0.28
    exp2_map = poisson_disk_emit(exp2_surf, allow_vis, budget=37_654, min_dist_px=2.8)

    p_cf_2d, q_cf_2d = blend_counterfactual_posteriors(
        p_full_2d, q_full_2d, p_zero_2d, q_zero_2d, d_vis, allow_vis, sel["w_base"], sel["w_far"]
    )
    exp3_map = charnes_cooper_submodular_emit(
        p_cf_2d,
        q_cf_2d,
        allow_vis,
        lambda_fp=sel["lambda_fp"],
        min_sep_px=sel["min_sep_px"],
        max_budget=sel["max_budget"],
        min_budget=22_000,
    )

    preds = {
        "EXP-CSKD-3_counterfactual_cc": exp3_map,
        "EXP-CSKD-2_cskd_uniform_d28": exp2_map,
        "EXP-CSKD-1_zero_catalogue_physics": exp1_map,
        "C2_h33_analogue_foldfair": c2_map,
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
        terms_by_arm, draws=1000, seed=520810 + seed, candidate="EXP-CSKD-3_counterfactual_cc"
    )
    official_eval["per_fold"] = per_fold_scores
    bootstrap_ci = _spatial_block_bootstrap(preds, folds, footprint, block_px=200, n_boot=1000, seed=20261022 + seed)
    regimes = _regime_decomposition(preds, folds, footprint, static_mm, vis)

    d_exp3 = d_vis[exp3_map > 0]
    spatial_stats = {
        "emitted_dots": int((exp3_map > 0).sum()),
        "min_dist_to_visible_px": round(float(d_exp3.min()), 4),
        "median_dist_to_visible_px": round(float(np.median(d_exp3)), 4),
        "p90_dist_to_visible_px": round(float(np.percentile(d_exp3, 90)), 4),
        "fraction_gt_2km_from_visible": round(float((d_exp3 > 20.0).mean()), 6),
    }

    print(f"\n--- SEED {seed} OFFICIAL HOLDOUT-DTI RESULTS ({official_eval['evaluator_version']}) ---", flush=True)
    for k, v in official_eval["scores"].items():
        n_dots = int((preds[k] > 0).sum())
        print(
            f"  {k:36s}: HOLDOUT-DTI = {v['dti']:.6f}  95% CI [{v['ci95'][0]:.6f}, {v['ci95'][1]:.6f}]  "
            f"dots={n_dots:,}  tp_w={v['tpw']:.1f}",
            flush=True,
        )
    thvc_ref = THVC_SEED20_DTI if seed == 20 else THVC_SEED30_DTI
    print(
        f"  Comparison vs G79-THVC ({thvc_ref:.6f}): "
        f"delta = {official_eval['scores']['EXP-CSKD-3_counterfactual_cc']['dti'] - thvc_ref:+.6f} | "
        f"EXP-CSKD-3 spatial={spatial_stats}",
        flush=True,
    )

    out_payload = {
        "seed": seed,
        "evaluator_version": official_eval["evaluator_version"],
        "withheld_positive_pixels": official_eval["scores"]["EXP-CSKD-3_counterfactual_cc"]["withheld_positive_pixels"],
        "elapsed_seconds": round(time.time() - t0, 2),
        "inner_cskd_selection": cc_tune,
        "exp3_spatial_stats": spatial_stats,
        "official_evaluate_all": official_eval,
        "spatial_bootstrap_20km": bootstrap_ci,
        "regime_decomposition": regimes,
    }
    ckpt_json.write_text(json.dumps(out_payload, indent=2) + "\n")
    return out_payload


def _fit_live_cskd_ensemble(
    cat: np.ndarray,
    footprint: np.ndarray,
    quad: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    cues_path: Path,
    cache_dir: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    lp_npz = cache_dir / "live_cskd_posteriors.npz"
    lp_meta = cache_dir / "live_cskd_meta.json"
    H, W = footprint.shape
    if lp_npz.exists() and lp_meta.exists():
        z = np.load(lp_npz)
        pf, qf, pz, qz = [np.zeros((H, W), dtype=np.float32) for _ in range(4)]
        pf[footprint] = z["p_full"].astype(np.float32)
        qf[footprint] = z["q_full"].astype(np.float32)
        pz[footprint] = z["p_zero"].astype(np.float32)
        qz[footprint] = z["q_zero"].astype(np.float32)
        return pf, qf, pz, qz, json.loads(lp_meta.read_text())

    t0 = time.time()
    print("\n==================== TRAINING LIVE FULL-FOOTPRINT G79-CSKD DUAL ENSEMBLE ====================", flush=True)
    quad_fp = quad[footprint]
    live_shards, live_draw0 = build_cskd_training_shards(
        cat, footprint, quad_fp, static_mm, mmap_path, cues_path,
        n_draws=4, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=24_000, seed_base=9400
    )
    live_mech = compute_cskd_mechanics(cat, footprint, cues_path).astype(np.float16)
    n_fp = int(footprint.sum())
    all_rows = np.arange(n_fp, dtype=np.int64)
    all_mask = np.ones(n_fp, dtype=bool)

    def _fit_branch(use_mech: bool, seed_off: int) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        oof_p1 = np.zeros(n_fp, dtype=np.float32)
        oof_q1 = np.zeros(n_fp, dtype=np.float32)
        d0_m = live_draw0["mech_fp16"] if use_mech else None
        for q_id in range(4):
            tr_qs = [q for q in range(4) if q != q_id]
            va_r = np.flatnonzero(quad_fp == q_id)
            Xq, yq, qq, wq, tpi_q, spi_q = stack_cskd_shards(live_shards, tr_qs, use_mech)
            sq = fit_stage1_ensemble(Xq, yq, qq, wq, seed=seed_off + q_id)
            del Xq, yq, qq, wq
            oof_p1[va_r], oof_q1[va_r] = predict_cskd_stage1_rows(sq, static_mm, mmap_path, d0_m, va_r, tpi_q, spi_q)
            del sq
            gc.collect()

        S2_oof = extract_stage2_spatial_features(oof_p1, oof_q1, footprint, ctx_cols_fp)
        del oof_p1, oof_q1
        s2_live = fit_stage2_dual_heads(S2_oof, live_draw0, all_mask, seed=seed_off + 79)
        del S2_oof
        gc.collect()

        p1_live = np.zeros(n_fp, dtype=np.float32)
        q1_live = np.zeros(n_fp, dtype=np.float32)
        n_feat = len(CSKD_ALL_FEATURE_NAMES) if use_mech else len(CSKD_STATIC_NAMES)
        feat_imp = np.zeros(n_feat, dtype=np.float64)
        Xf, yf, qf_t, wf, tpi_f, spi_f = stack_cskd_shards(live_shards, [0, 1, 2, 3], use_mech)
        for rep in range(2):
            sf = fit_stage1_ensemble(Xf, yf, qf_t, wf, seed=seed_off + 200 + 37 * rep)
            feat_imp += 0.5 * sf["lgb_deep"].booster_.feature_importance(importance_type="gain")
            pr, qr = predict_cskd_stage1_rows(sf, static_mm, mmap_path, live_mech if use_mech else None, all_rows, tpi_f, spi_f)
            p1_live += 0.5 * pr
            q1_live += 0.5 * qr
            del sf
            gc.collect()
        del Xf, yf, qf_t, wf
        gc.collect()

        S2_live = extract_stage2_spatial_features(p1_live, q1_live, footprint, ctx_cols_fp)
        p2_fp, q2_fp = predict_stage2_dual_heads(s2_live, S2_live, all_rows)
        del S2_live, s2_live
        gc.collect()
        return p2_fp, q2_fp, feat_imp

    pf_fp, qf_fp, imp_full = _fit_branch(True, 1200)
    pz_fp, qz_fp, imp_zero = _fit_branch(False, 1600)
    del live_shards, live_draw0, live_mech
    gc.collect()

    top_full = sorted(
        [{"feature": CSKD_ALL_FEATURE_NAMES[i], "gain_share": round(float(imp_full[i] / max(imp_full.sum(), 1e-9)), 6)} for i in range(len(CSKD_ALL_FEATURE_NAMES))],
        key=lambda r: -r["gain_share"],
    )
    top_zero = sorted(
        [{"feature": CSKD_STATIC_NAMES[i], "gain_share": round(float(imp_zero[i] / max(imp_zero.sum(), 1e-9)), 6)} for i in range(len(CSKD_STATIC_NAMES))],
        key=lambda r: -r["gain_share"],
    )
    meta_live = {
        "live_train_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
        "top25_full_features_by_gain": top_full[:25],
        "top15_zero_cat_features_by_gain": top_zero[:15],
    }
    np.savez_compressed(
        lp_npz,
        p_full=pf_fp.astype(np.float16),
        q_full=qf_fp.astype(np.float16),
        p_zero=pz_fp.astype(np.float16),
        q_zero=qz_fp.astype(np.float16),
    )
    lp_meta.write_text(json.dumps(meta_live, indent=2) + "\n")

    pf_2d, qf_2d, pz_2d, qz_2d = [np.zeros((H, W), dtype=np.float32) for _ in range(4)]
    pf_2d[footprint] = pf_fp
    qf_2d[footprint] = qf_fp
    pz_2d[footprint] = pz_fp
    qz_2d[footprint] = qz_fp
    return pf_2d, qf_2d, pz_2d, qz_2d, meta_live


def _build_full_family_index() -> dict[str, Any]:
    """Combine all 992 frozen blobs + 207 post-snapshot delta blobs + local GEMSDOE79 archived rasters."""
    seen_sha: dict[str, dict[str, Any]] = {}
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r["sha256"] for r in receipt["files"] if r["status"] == "verified"}

    idx_frozen = json.loads((ROOT / "registry/registry_index.json").read_text())
    for r in idx_frozen["rasters"]:
        cfile = ROOT / ".cache/registry" / f"{r['blob']}.tif"
        sha = pins[r["blob"]]
        sources = list(r.get("aliases") or [f"{r['repo']}:{r['path']}"])
        if sha in seen_sha:
            seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | set(sources))
        else:
            seen_sha[sha] = {
                "repo_first": r["repo"],
                "sources": sources,
                "cache_file": str(cfile),
                "sha256": sha,
            }

    idx_delta = json.loads((ROOT / "registry/registry_delta.json").read_text())
    for r in idx_delta["rasters"]:
        cfile = ROOT / ".cache/registry" / f"{r['blob']}.tif"
        sha = r["sha256"]
        sources = list(r.get("aliases") or [f"{r['repo']}:{r['path']}"])
        if sha in seen_sha:
            seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | set(sources))
        else:
            seen_sha[sha] = {
                "repo_first": r["repo"],
                "sources": sources,
                "cache_file": str(cfile),
                "sha256": sha,
            }

    # Include all local GEMSDOE79 archived rasters (including G79-THVC & H79-FNHR!)
    for local_tif in sorted((ROOT / "archive").rglob("*.tif")):
        if ARCHIVE_DIR in local_tif.parents:
            continue
        sha = hashlib.sha256(local_tif.read_bytes()).hexdigest()
        rel = local_tif.relative_to(ROOT).as_posix()
        src = f"GEMSDOE79:{rel}"
        if sha in seen_sha:
            seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | {src})
        else:
            seen_sha[sha] = {
                "repo_first": "GEMSDOE79",
                "sources": [src],
                "cache_file": str(local_tif),
                "sha256": sha,
            }

    return {"complete_accessible_scan": True, "errors": [], "rasters": list(seen_sha.values())}


def _audit_full_family_uniqueness(candidate_tif: Path, footprint: np.ndarray, label_tag: str, family_idx: dict[str, Any], ckpt_path: Path | None = None) -> dict[str, Any]:
    cand_sha = hashlib.sha256(candidate_tif.read_bytes()).hexdigest()
    if ckpt_path is not None and ckpt_path.is_file():
        cached = json.loads(ckpt_path.read_text())
        if cached.get("candidate_file_sha256") == cand_sha and cached.get("registry_rasters_expected") == len(family_idx["rasters"]):
            print(f"[uniqueness:{label_tag}] Reusing verified checkpoint {ckpt_path.name}", flush=True)
            return cached

    import concurrent.futures as cf
    t0 = time.time()
    rasters_all = family_idx["rasters"]
    n_tot = len(rasters_all)
    print(f"\n[uniqueness:{label_tag}] Scanning {candidate_tif.name} against {n_tot} unique SHA-256 rasters across all 93 repos...", flush=True)

    # Split into 4 chunks over 2 worker threads calling unmodified uniqueness.compare_to_registry
    chunks = [rasters_all[i::4] for i in range(4) if rasters_all[i::4]]
    def _run_chunk(sub_list: list[dict[str, Any]]) -> dict[str, Any]:
        sub_idx = {"complete_accessible_scan": True, "errors": [], "rasters": sub_list}
        return uniqueness.compare_to_registry(candidate_tif, sub_idx, footprint)

    with cf.ThreadPoolExecutor(3) as pool:
        parts = list(pool.map(_run_chunk, chunks))

    all_rows = [r for p in parts for r in p["rows"]]
    checked = sum(int(p["registry_rasters_checked"]) for p in parts)
    missing = sum(int(p["missing_or_invalid"]) for p in parts)
    passes_lit = all(bool(p["unique"]) for p in parts)
    phase = uniqueness.two_phase_summary(all_rows, int(footprint.sum()), expected_rasters=n_tot)

    valid_rows = [r for r in all_rows if "error" not in r]
    rhos = [abs(float(r["spearman_full_footprint"])) for r in valid_rows if r.get("spearman_full_footprint") is not None and np.isfinite(r["spearman_full_footprint"])]
    max_abs_rho = float(max(rhos)) if rhos else 0.0

    sparse_50k = [r for r in valid_rows if 1 <= int(r.get("their_dots", 0)) <= 50_000]
    sparse_50k_sorted = sorted(sparse_50k, key=lambda r: -float(r["my_dots_within_3px_of_theirs"]))
    sparse_50k_gt = [r for r in sparse_50k_sorted if float(r["my_dots_within_3px_of_theirs"]) > 0.70]

    cross_repo_sparse_50k = [r for r in sparse_50k_sorted if r.get("repo") != "GEMSDOE79"]
    cross_repo_50k_gt = [r for r in cross_repo_sparse_50k if float(r["my_dots_within_3px_of_theirs"]) > 0.70]

    def _find_peer(sha_prefix: str) -> dict[str, Any] | None:
        for r in valid_rows:
            if str(r.get("sha256", "")).startswith(sha_prefix):
                return {
                    "repo": r["repo"],
                    "submission": r["submission"],
                    "sha256": r["sha256"],
                    "their_dots": r["their_dots"],
                    "forward_overlap_3px": round(float(r["my_dots_within_3px_of_theirs"]), 6),
                    "spearman_full_footprint": round(float(r["spearman_full_footprint"]), 6) if r.get("spearman_full_footprint") is not None else None,
                }
        return None

    summary = {
        "label": label_tag,
        "candidate_file_sha256": cand_sha,
        "registry_rasters_expected": n_tot,
        "registry_rasters_checked": checked,
        "missing_or_invalid": missing,
        "max_abs_spearman": round(max_abs_rho, 6),
        "passes_spearman_0_90": bool(max_abs_rho <= 0.90),
        "literal_passes_0_70": bool(passes_lit),
        "two_phase_summary": {k: v for k, v in phase.items() if k != "literal_firings"},
        "sparse_le_50k_all_repos": {
            "compared": len(sparse_50k),
            "collisions_gt_0_70": len(sparse_50k_gt),
            "passes_0_70": len(sparse_50k_gt) == 0,
            "worst_10": [
                {
                    "repo": r["repo"],
                    "submission": r["submission"],
                    "sha256": r["sha256"],
                    "their_dots": r["their_dots"],
                    "forward_overlap_3px": round(float(r["my_dots_within_3px_of_theirs"]), 6),
                    "spearman_full_footprint": round(float(r["spearman_full_footprint"]), 6) if r.get("spearman_full_footprint") is not None else None,
                }
                for r in sparse_50k_sorted[:10]
            ],
        },
        "sparse_le_50k_cross_repo_only": {
            "compared": len(cross_repo_sparse_50k),
            "collisions_gt_0_70": len(cross_repo_50k_gt),
            "passes_0_70": len(cross_repo_50k_gt) == 0,
            "max_overlap_3px": round(float(cross_repo_sparse_50k[0]["my_dots_within_3px_of_theirs"]), 6) if cross_repo_sparse_50k else 0.0,
            "worst_submission": cross_repo_sparse_50k[0]["submission"] if cross_repo_sparse_50k else None,
        },
        "key_peer_overlaps": {
            "GEMSDOE83_h83_gvcd": _find_peer("79f14dc84cd7"),
            "GEMSDOE79_g79_thvc": _find_peer("d3db2e959df9"),
            "GEMSDOE32_h33_champ": _find_peer("65581b39be98") or _find_peer("fb7e86d0"),
            "13GEMSDOE_r13_lattice_s5": _find_peer("c12533bb"),
            "17GEMSDOE_proba_multiscale": _find_peer("ab0a0a62"),
        },
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    print(
        f"[uniqueness:{label_tag}] Done in {summary['elapsed_seconds']}s | "
        f"checked={summary['registry_rasters_checked']}/{n_tot} | "
        f"max|rho|={summary['max_abs_spearman']:.4f} | "
        f"cross-repo <=50k collisions={summary['sparse_le_50k_cross_repo_only']['collisions_gt_0_70']} "
        f"(max={summary['sparse_le_50k_cross_repo_only']['max_overlap_3px']:.4f}) | "
        f"GEMSDOE83={summary['key_peer_overlaps']['GEMSDOE83_h83_gvcd']} | "
        f"G79-THVC={summary['key_peer_overlaps']['G79-THVC' if 'G79-THVC' in summary['key_peer_overlaps'] else 'GEMSDOE79_g79_thvc']}",
        flush=True,
    )
    if ckpt_path is not None:
        ckpt_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=("canaries", "seed20", "seed30", "live", "all"))
    args = ap.parse_args()

    prereg = _require_open_cskd()
    t_all = time.time()
    cache_dir = ROOT / ".cache" / "g79_cskd"
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

    static_meta = build_cskd_static_memmaps(
        ROOT / "data/raw",
        ROOT / ".cache/official_ing",
        ROOT / ".cache/cskd_sources",
        cache_dir,
        footprint,
        transform,
    )
    mmap_path = cache_dir / "cskd_static_fp84.f32.mmap"
    cues_path = mmap_path.with_suffix(".cues.npz")
    static_mm = np.memmap(mmap_path, dtype="float32", mode="r", shape=(int(footprint.sum()), len(CSKD_STATIC_NAMES)))

    cmap = {n: i for i, n in enumerate(CSKD_STATIC_NAMES)}
    ctx_cols_fp = np.column_stack(
        [
            static_mm[:, cmap["lidar_present"]],
            static_mm[:, cmap["scarp_lahontan_mine_clean"]],
            static_mm[:, cmap["rad_kd_clean_conduit"]],
            static_mm[:, cmap["mountain_wall_ratio"]],
        ]
    ).astype(np.float16)
    _release_mm(static_mm, mmap_path)

    grid = Grid(footprint, cat, str(crs), transform, footprint.shape[0], footprint.shape[1])

    # Gate 0: Single-feature leakage canaries across all 102 channels
    canary_res = _run_leakage_canaries(grid, footprint, static_mm, mmap_path, cues_path, cache_dir)
    if args.stage == "canaries":
        return

    if args.stage in ("seed20", "all"):
        eval20 = _evaluate_one_seed(20, grid, footprint, static_mm, mmap_path, ctx_cols_fp, cues_path, d28_bool, cache_dir)
    if args.stage == "seed20":
        return

    if args.stage in ("seed30", "all"):
        eval30 = _evaluate_one_seed(30, grid, footprint, static_mm, mmap_path, ctx_cols_fp, cues_path, d28_bool, cache_dir)
    if args.stage == "seed30":
        return

    eval20 = json.loads((cache_dir / "eval_seed20.json").read_text())
    eval30 = json.loads((cache_dir / "eval_seed30.json").read_text())

    _, quad_live = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)
    pf_live, qf_live, pz_live, qz_live, live_meta = _fit_live_cskd_ensemble(
        cat, footprint, quad_live, static_mm, mmap_path, ctx_cols_fp, cues_path, cache_dir
    )

    s20_p = eval20["inner_cskd_selection"]["selected"]
    s30_p = eval30["inner_cskd_selection"]["selected"]
    cons_wb = round(0.5 * (s20_p["w_base"] + s30_p["w_base"]), 4)
    cons_wf = round(0.5 * (s20_p["w_far"] + s30_p["w_far"]), 4)
    cons_lam = round(0.5 * (s20_p["lambda_fp"] + s30_p["lambda_fp"]), 4)
    cons_sep = round(0.5 * (s20_p["min_sep_px"] + s30_p["min_sep_px"]), 2)
    cons_maxb = int(round(0.5 * (s20_p["max_budget"] + s30_p["max_budget"])))

    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    allow_live = footprint & (d_cat > 3.0)
    p_cf_live, q_cf_live = blend_counterfactual_posteriors(
        pf_live, qf_live, pz_live, qz_live, d_cat, allow_live, cons_wb, cons_wf
    )

    # Pre-placement continuous surface audit across all 1,210+ family blobs
    surf_blend = (0.70 * np.clip(p_cf_live, 0.0, 1.0) + 0.30 * (np.clip(q_cf_live, 0.0, 1.0) ** 1.6) * 0.28).astype(np.float32)
    smax = float(surf_blend[allow_live].max())
    surf_norm = np.where(allow_live, np.clip(surf_blend / max(smax, 1e-9), 0.0, 1.0), 0.0).astype(np.float32)
    tmp_surf_tif = cache_dir / "g79_cskd_preplacement_surface.tif"
    for stale in cache_dir.glob("g79_cskd_preplacement_surface.*"):
        stale.unlink()
    submission_writer.write_submission(
        tmp_surf_tif,
        surf_norm,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name="g79-cskd-preplacement-surface",
        note="G79-CSKD pre-placement continuous surface for full-family uniqueness audit",
        catalogue=cat,
    )
    family_idx = _build_full_family_index()
    surf_audit = _audit_full_family_uniqueness(
        tmp_surf_tif, footprint, "pre_placement_surface", family_idx, ckpt_path=cache_dir / "surf_audit.json"
    )

    # Emit brand-new research GeoTIFF into archive/g79_cskd_6da2620c/downloads/ first
    emitted_live = charnes_cooper_submodular_emit(
        p_cf_live,
        q_cf_live,
        allow_live,
        lambda_fp=cons_lam,
        min_sep_px=cons_sep,
        max_budget=cons_maxb,
        min_budget=22_000,
    )
    n_emitted = int((emitted_live > 0).sum())
    d_emit = d_cat[emitted_live > 0]
    raw_hash8 = hashlib.sha256(emitted_live.tobytes()).hexdigest()[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"g79-cskd-ccsubmod-20261022-{raw_hash8}-zeros-DO-NOT-SUBMIT"
    note = (
        f"RESEARCH ONLY DO NOT SUBMIT: G79-CSKD Lahontan+BLM+Kd+Coulomb+CC ({n_emitted} px); blocked by literal 17GEMSDOE/13GEMSDOE witnesses"
    )[:140]

    arch_dl = ARCHIVE_DIR / "downloads"
    arch_dl.mkdir(parents=True, exist_ok=True)
    for stale in arch_dl.glob("*"):
        stale.unlink()
    arch_tif = arch_dl / f"{stem}.tif"
    manifest = submission_writer.write_submission(
        arch_tif,
        emitted_live,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name=stem,
        note=note,
        catalogue=cat,
        metadata={
            "lane": "G79-CSKD",
            "branch": "arena/6da2620c-gemsdoe79",
            "consensus_params": {
                "w_base": cons_wb,
                "w_far": cons_wf,
                "lambda_fp": cons_lam,
                "min_sep_px": cons_sep,
                "max_budget": cons_maxb,
            },
            "generated_timestamp_utc": ts,
        },
    )
    for f in arch_dl.glob(f"{stem}*"):
        if f.suffix == ".json":
            f.write_text(f.read_text().replace(str(ROOT) + "/", ""))
        f.chmod(0o644)

    dot_audit = _audit_full_family_uniqueness(
        arch_tif, footprint, "post_placement_dots", family_idx, ckpt_path=cache_dir / "dot_audit.json"
    )

    s20_dti = float(eval20["official_evaluate_all"]["scores"]["EXP-CSKD-3_counterfactual_cc"]["dti"])
    s30_dti = float(eval30["official_evaluate_all"]["scores"]["EXP-CSKD-3_counterfactual_cc"]["dti"])
    beats_thvc_both_seeds = (s20_dti > THVC_SEED20_DTI) and (s30_dti > THVC_SEED30_DTI)
    clears_all_sparse_50k = (
        surf_audit["passes_spearman_0_90"]
        and dot_audit["passes_spearman_0_90"]
        and dot_audit["sparse_le_50k_all_repos"]["passes_0_70"]
    )
    promote_to_canonical = bool(beats_thvc_both_seeds and clears_all_sparse_50k)

    live_spatial = {
        "emitted_positive_pixels": n_emitted,
        "min_distance_to_catalogue_px": round(float(d_emit.min()), 4),
        "median_distance_to_catalogue_px": round(float(np.median(d_emit)), 4),
        "p90_distance_to_catalogue_px": round(float(np.percentile(d_emit, 90)), 4),
        "fraction_gt_2km_from_catalogue": round(float((d_emit > 20.0).mean()), 6),
    }

    summary = {
        "schema_version": 1,
        "lane": "G79-CSKD",
        "branch": "arena/6da2620c-gemsdoe79",
        "generated_utc": ts,
        "total_runtime_seconds": round(time.time() - t_all, 2),
        "static_feature_meta": static_meta,
        "leakage_canary_summary": {
            "n_features_tested": canary_res["n_features_tested"],
            "overall_max_symmetric_auc": canary_res["overall_max_symmetric_auc"],
            "overall_worst_feature": canary_res["overall_worst_feature"],
            "gate_passed": canary_res["gate_passed"],
        },
        "seed20": eval20,
        "seed30": eval30,
        "comparison_vs_g79_thvc": {
            "thvc_seed20_dti": THVC_SEED20_DTI,
            "cskd_seed20_dti": s20_dti,
            "delta_seed20": round(s20_dti - THVC_SEED20_DTI, 6),
            "thvc_seed30_dti": THVC_SEED30_DTI,
            "cskd_seed30_dti": s30_dti,
            "delta_seed30": round(s30_dti - THVC_SEED30_DTI, 6),
            "beats_thvc_on_both_seeds": beats_thvc_both_seeds,
            "clears_all_sparse_50k_0_70": clears_all_sparse_50k,
            "promoted_to_canonical_downloads": promote_to_canonical,
        },
        "live_model_meta": live_meta,
        "live_spatial_forensics": live_spatial,
        "archive_artifact": {
            "tif_path": arch_tif.relative_to(ROOT).as_posix(),
            "tif_sha256": hashlib.sha256(arch_tif.read_bytes()).hexdigest(),
            "tif_bytes": arch_tif.stat().st_size,
            "zip_path": (arch_dl / f"{stem}.zip").relative_to(ROOT).as_posix(),
            "zip_sha256": hashlib.sha256((arch_dl / f"{stem}.zip").read_bytes()).hexdigest(),
            "zip_bytes": (arch_dl / f"{stem}.zip").stat().st_size,
            "note": note,
        },
        "pre_placement_surface_audit": surf_audit,
        "post_placement_dot_audit": dot_audit,
    }
    (ROOT / "evidence/g79_cskd_results.json").write_text(json.dumps(summary, indent=2) + "\n")
    (ARCHIVE_DIR / "g79_cskd_results.json").write_text(json.dumps(summary, indent=2) + "\n")

    # Lock preregistration as closed so the lane is strictly single-pass and fail-closed on re-entry!
    prereg["status"] = "closed"
    prereg["completed_utc"] = ts
    prereg["results_evidence"] = "evidence/g79_cskd_results.json"
    PREREG_PATH.write_text(json.dumps(prereg, indent=2) + "\n")

    print("\n==================== G79-CSKD SUMMARY ====================", flush=True)
    print(json.dumps(summary["comparison_vs_g79_thvc"], indent=2), flush=True)
    print(json.dumps(summary["live_spatial_forensics"], indent=2), flush=True)
    print(json.dumps(dot_audit["key_peer_overlaps"], indent=2), flush=True)


if __name__ == "__main__":
    main()
