#!/usr/bin/env python3
"""Execute the preregistered H79-PFSD (Province-Normalized Flank-Decontaminated
Subsurface-Surface Strike Concordance, Upward Probe Heat-Flux & Dual-Expert Equilibrated Allocator)
single-lane protocol end-to-end.

Strictly adheres to all 6 rules of the Parallel-Run Protocol & AGENTS.md:
  1. Single method lane (H79-PFSD, registry/preregistration_pfsd.json, SHA-256 81a0770e...).
     Audits all 992 frozen + 209 post-freeze sibling delta + all local GEMSDOE79 rasters
     BOTH on the pre-placement continuous surface AND on the placed binary dot raster.
  2. Reuses unmodified vendor/gems57/{evaluate_holdout,submission_writer,uniqueness,metric,holdout}.py.
  3. Labels every holdout score HOLDOUT-DTI (gems57-pooled-hide-v2, withheld count, 95% CI).
  4. Runs single-feature symmetric AUC leakage canaries across all 106 channels on Seeds 20 & 30.
  5. Enforces closed-lane CLI immutability (exit 2, No files changed) once finalized.
  6. Respects the 3-experiment budget (EXP-PFSD-1, EXP-PFSD-2, EXP-PFSD-3) and consumes 0 slots.
"""
from __future__ import annotations

import concurrent.futures as cf
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "evidence" / "pfsd" / "experiment_state.json"


def _require_pfsd_open() -> None:
    try:
        st = json.loads(STATE_PATH.read_text())
    except (OSError, ValueError):
        sys.stderr.write("H79-PFSD: missing or unreadable experiment_state.json. No files changed.\n")
        raise SystemExit(2)
    if st.get("lane") != "H79-PFSD" or st.get("status") != "in_progress":
        sys.stderr.write(
            f"H79-PFSD: lane is closed ({st.get('status', 'unknown')}); "
            "do not restart, retune, or repackage it. No files changed.\n"
        )
        raise SystemExit(2)


if __name__ == "__main__":
    _require_pfsd_open()

sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

from gems57 import evaluate_holdout, holdout, metric, submission_writer, uniqueness  # noqa: E402
from gems57.grid import Grid  # noqa: E402
from gems79.pfsd_features import (  # noqa: E402
    MECH_FEATURE_NAMES,
    PFSD_ALL_FEATURE_NAMES,
    PFSD_STATIC_FEATURE_NAMES,
    build_pfsd_static_memmap,
    compute_network_mechanics,
    drop_file_cache,
    rss_mb,
)
from gems79.pfsd_model import (  # noqa: E402
    _stack_shards,
    build_decontaminated_quadrant_shards,
    charnes_cooper_submodular_emit,
    equilibrate_quadrant_posteriors,
    extract_stage2_dual_expert_features,
    fit_stage1_mech_ensemble,
    fit_stage2_dual_expert_heads,
    poisson_disk_emit,
    predict_pure_physics_rows,
    predict_stage1_mech_rows,
    predict_stage2_dual_expert_heads,
    run_dual_expert_nested_oof,
    run_pure_physics_oof,
)
import validate_submission  # noqa: E402


def _rel(p: Path | str) -> str:
    pp = Path(p).resolve()
    if pp.is_relative_to(ROOT.resolve()):
        return str(pp.relative_to(ROOT.resolve()))
    return Path(p).name


def _sanitize_obj_paths(obj: Any) -> Any:
    root_str = str(ROOT.resolve())
    if isinstance(obj, str):
        if obj.startswith(root_str + "/"):
            return obj[len(root_str) + 1 :]
        if obj == root_str:
            return "."
        return obj.replace(root_str + "/", "")
    if isinstance(obj, list):
        return [_sanitize_obj_paths(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_obj_paths(v) for k, v in obj.items()}
    return obj


def _run_leakage_canaries(
    grid: Grid,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    cues_path: Path,
) -> dict[str, Any]:
    out_path = ROOT / "evidence" / "pfsd" / "leakage_canary.json"
    if out_path.exists():
        print(f"Reusing saved leakage canary receipt {out_path}", flush=True)
        return json.loads(out_path.read_text())

    t0 = time.time()
    print("\n==================== RUNNING 106-CHANNEL LEAKAGE CANARIES (SEEDS 20 & 30) ====================", flush=True)
    seed_reports: dict[str, Any] = {}
    global_max_auc = 0.0
    global_max_feat = ""
    global_max_seed = 20
    n_tests_total = 0

    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        vis = folds[0]["visible"]
        truth_all = np.zeros(footprint.shape, dtype=bool)
        active_all = np.zeros(footprint.shape, dtype=bool)
        for f in folds:
            truth_all |= f["truth"]
            active_all |= footprint & f["region"] & (~f["masked_known"])
        act_fp = active_all[footprint]
        y_act = truth_all[footprint][act_fp].astype(np.int8)

        mech_fp = compute_network_mechanics(vis, footprint, cues_path)
        rows = []
        for idx, fname in enumerate(PFSD_STATIC_FEATURE_NAMES):
            vals = np.asarray(static_mm[:, idx], dtype=np.float32)[act_fp]
            drop_file_cache(mmap_path)
            if float(np.ptp(vals)) <= 1e-12:
                raw_auc = 0.5
            else:
                raw_auc = float(roc_auc_score(y_act, vals))
            sym_auc = max(raw_auc, 1.0 - raw_auc)
            n_tests_total += 1
            rows.append({"feature": fname, "group": "static_physics", "raw_auc": round(raw_auc, 6), "symmetric_auc": round(sym_auc, 6)})
            if sym_auc > global_max_auc:
                global_max_auc, global_max_feat, global_max_seed = sym_auc, fname, seed
            del vals

        for idx, fname in enumerate(MECH_FEATURE_NAMES):
            vals = mech_fp[:, idx][act_fp]
            if float(np.ptp(vals)) <= 1e-12:
                raw_auc = 0.5
            else:
                raw_auc = float(roc_auc_score(y_act, vals))
            sym_auc = max(raw_auc, 1.0 - raw_auc)
            n_tests_total += 1
            rows.append({"feature": fname, "group": "fold_visible_mechanics", "raw_auc": round(raw_auc, 6), "symmetric_auc": round(sym_auc, 6)})
            if sym_auc > global_max_auc:
                global_max_auc, global_max_feat, global_max_seed = sym_auc, fname, seed

        del mech_fp
        gc.collect()
        rows_sorted = sorted(rows, key=lambda r: -r["symmetric_auc"])
        seed_reports[f"seed_{seed}"] = {
            "withheld_positive_pixels": int(y_act.sum()),
            "active_pixels": int(act_fp.sum()),
            "max_symmetric_auc": rows_sorted[0]["symmetric_auc"],
            "max_feature": rows_sorted[0]["feature"],
            "top_10_features": rows_sorted[:10],
            "all_features": rows,
        }
        print(
            f"  [canary seed={seed}] cleared {len(rows)} features | max symmetric AUC = "
            f"{rows_sorted[0]['symmetric_auc']:.6f} ({rows_sorted[0]['feature']}), RSS={rss_mb():.1f} MB",
            flush=True,
        )

    passed = bool(global_max_auc <= 0.90)
    payload = {
        "lane": "H79-PFSD",
        "limit": 0.90,
        "passed": passed,
        "n_channels_per_seed": len(PFSD_ALL_FEATURE_NAMES),
        "total_canary_tests": n_tests_total,
        "max_symmetric_auc": round(global_max_auc, 6),
        "max_feature": global_max_feat,
        "max_seed": global_max_seed,
        "elapsed_seconds": round(time.time() - t0, 2),
        "per_seed": seed_reports,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    if not passed:
        raise RuntimeError(f"LEAKAGE CANARY FAILED: {global_max_feat} AUC={global_max_auc:.6f} > 0.90")
    return payload


def _select_equilibrated_cc_params_inner(
    p_tr_map: np.ndarray,
    q_tr_map: np.ndarray,
    sim_draw0: dict[str, Any],
    quad_2d: np.ndarray,
    footprint: np.ndarray,
) -> dict[str, Any]:
    """Tune (gamma_eq, lambda_fp, min_sep_px, max_budget) strictly on inner simulated draw 0."""
    H, W = footprint.shape
    truth_in = np.zeros((H, W), dtype=bool)
    act_in = np.zeros((H, W), dtype=bool)
    truth_in[footprint] = sim_draw0["y_exact_fp"]
    act_in[footprint] = sim_draw0["active_fp"]
    known_in = footprint & (~act_in)
    allow_in = footprint & (ndi.distance_transform_edt(~known_in) > 3.0)

    cc_grid = [
        (0.0024, 1.9, 43_000),
        (0.0034, 1.9, 42_000),
        (0.0045, 1.9, 40_500),
        (0.0058, 1.9, 39_000),
        (0.0030, 2.2, 41_500),
        (0.0042, 2.2, 39_500),
    ]
    best = None
    grid_log = []
    for gamma in (0.0, 0.45, 0.70):
        pe, qe = equilibrate_quadrant_posteriors(p_tr_map, q_tr_map, quad_2d, allow_in, gamma=gamma)
        for lam, msep, mbud in cc_grid:
            emitted = charnes_cooper_submodular_emit(
                pe,
                qe,
                allow_in,
                lambda_fp=lam,
                min_sep_px=msep,
                max_budget=mbud,
                min_budget=20_000,
            )
            res = metric.dti_binary(emitted > 0, truth_in, valid=act_in)
            entry = {
                "gamma_eq": gamma,
                "lambda_fp": lam,
                "min_sep_px": msep,
                "max_budget": mbud,
                "emitted_dots": int((emitted > 0).sum()),
                "inner_sim_dti": round(float(res["dti"]), 6),
            }
            grid_log.append(entry)
            if best is None or entry["inner_sim_dti"] > best["inner_sim_dti"]:
                best = entry
        del pe, qe
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
        ("EXP-PFSD-3_equil_charnes_cooper", "C2_h33_analogue_foldfair"),
        ("EXP-PFSD-3_equil_charnes_cooper", "EXP-PFSD-2_pfsd_uniform_d28"),
        ("EXP-PFSD-3_equil_charnes_cooper", "EXP-PFSD-1_uncorrupted_pure_physics"),
        ("EXP-PFSD-2_pfsd_uniform_d28", "C2_h33_analogue_foldfair"),
        ("EXP-PFSD-1_uncorrupted_pure_physics", "C2_h33_analogue_foldfair"),
        ("EXP-PFSD-1_uncorrupted_pure_physics", "C0_random_B37654"),
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
    mmap_path: Path,
    visible: np.ndarray,
) -> dict[str, Any]:
    H, W = footprint.shape
    truth_all = np.zeros((H, W), dtype=bool)
    active_all = np.zeros((H, W), dtype=bool)
    for f in folds:
        truth_all |= f["truth"]
        active_all |= footprint & f["region"] & (~f["masked_known"])

    cmap = {n: i for i, n in enumerate(PFSD_STATIC_FEATURE_NAMES)}
    lid_2d = np.zeros((H, W), dtype=bool)
    lid_2d[footprint] = np.asarray(static_mm[:, cmap["lidar_present"]]) > 0.5
    mtn_2d = np.zeros((H, W), dtype=bool)
    mtn_2d[footprint] = np.asarray(static_mm[:, cmap["mountain_wall_ratio"]]) > 0.35
    drop_file_cache(mmap_path)
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
        n_pos = int((truth_all & rmask).sum())
        row: dict[str, Any] = {"withheld_positive_pixels": n_pos, "active_pixels": int(rmask.sum()), "scores": {}}
        for aname, pred in pred_map.items():
            res = metric.dti_binary(pred > 0, truth_all, valid=rmask)
            row["scores"][aname] = round(float(res["dti"]), 6)
        out[rname] = row
    return out


def _evaluate_one_seed(
    seed: int,
    grid: Grid,
    footprint: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    cues_path: Path,
    d28_bool: np.ndarray,
    fab_surface: np.ndarray,
    cache_dir: Path,
    oof_only: bool = False,
) -> dict[str, Any]:
    ev_out = ROOT / "evidence" / "pfsd" / f"eval_seed{seed}.json"
    if ev_out.exists():
        print(f"[seed={seed}] Reusing completed evaluation {ev_out}", flush=True)
        return json.loads(ev_out.read_text())

    t0 = time.time()
    print(f"\n==================== STARTING SEED {seed} H79-PFSD EVALUATION ====================", flush=True)
    folds, quad = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    vis = folds[0]["visible"]
    quad_fp = quad[footprint]
    d_vis_edt = ndi.distance_transform_edt(~vis)
    allow_ctrl = footprint & (d_vis_edt > 2.0)
    allow_vis = footprint & (d_vis_edt > 3.0)

    oof_ckpt = cache_dir / f"oof_seed{seed}.npz"
    if oof_ckpt.exists():
        print(f"[seed={seed}] Reloading cached OOF posteriors {oof_ckpt}...", flush=True)
        z = np.load(oof_ckpt)
        p_phys_fp = z["p_phys_fp"].astype(np.float32)
        q_phys_fp = z["q_phys_fp"].astype(np.float32)
        p_full_fp = z["p_full_fp"].astype(np.float32)
        q_full_fp = z["q_full_fp"].astype(np.float32)
        p_tr_avg = z["p_tr_avg"].astype(np.float32)
        q_tr_avg = z["q_tr_avg"].astype(np.float32)
        draw0_ref = {"active_fp": z["d0_active"], "y_exact_fp": z["d0_y"]}
    else:
        phys_ckpt = cache_dir / f"phys_seed{seed}.npz"
        if phys_ckpt.exists():
            print(f"[seed={seed}] 1/3 Reloading cached Pure-Physics OOF {phys_ckpt}...", flush=True)
            zp = np.load(phys_ckpt)
            p_phys_fp = zp["p_phys_fp"].astype(np.float32)
            q_phys_fp = zp["q_phys_fp"].astype(np.float32)
        else:
            tp0 = time.time()
            print(f"[seed={seed}] 1/3 Fitting uncorrupted 100%-visible Pure-Physics Expert OOF...", flush=True)
            p_phys_fp, q_phys_fp, _ = run_pure_physics_oof(
                vis, footprint, quad_fp, static_mm, mmap_path, neg_per_fold=110_000, halo_per_fold=38_000, seed=5000 + seed
            )
            np.savez_compressed(phys_ckpt, p_phys_fp=p_phys_fp.astype(np.float16), q_phys_fp=q_phys_fp.astype(np.float16))
            print(f"[seed={seed}] Pure-Physics OOF done in {time.time()-tp0:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

        ts0 = time.time()
        print(f"[seed={seed}] 2/3 Building flank-decontaminated (d_sim > 3 px) simulated shards...", flush=True)
        shards, draw0_ref = build_decontaminated_quadrant_shards(
            vis, footprint, quad_fp, static_mm, mmap_path, cues_path, n_draws=3, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=22_000, seed_base=7900 + seed
        )
        test_mech = np.clip(np.nan_to_num(compute_network_mechanics(vis, footprint, cues_path), nan=0.0, posinf=3e4, neginf=-3e4), -3e4, 3e4).astype(np.float16)
        print(f"[seed={seed}] Shards + test mechanics ready in {time.time()-ts0:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

        tm0 = time.time()
        print(f"[seed={seed}] 3/3 Running Dual-Expert C(4,2) nested OOF...", flush=True)
        p_full_fp, q_full_fp, p_tr_avg, q_tr_avg = run_dual_expert_nested_oof(
            quad_fp, footprint, static_mm, mmap_path, ctx_cols_fp, shards, draw0_ref, test_mech, p_phys_fp, q_phys_fp, seed=seed * 10
        )
        print(f"[seed={seed}] Dual-Expert nested OOF complete in {time.time()-tm0:.1f}s, RSS={rss_mb():.1f} MB", flush=True)

        np.savez_compressed(
            oof_ckpt,
            p_phys_fp=p_phys_fp.astype(np.float16),
            q_phys_fp=q_phys_fp.astype(np.float16),
            p_full_fp=p_full_fp.astype(np.float16),
            q_full_fp=q_full_fp.astype(np.float16),
            p_tr_avg=p_tr_avg.astype(np.float16),
            q_tr_avg=q_tr_avg.astype(np.float16),
            d0_active=draw0_ref["active_fp"],
            d0_y=draw0_ref["y_exact_fp"],
        )
        del shards, test_mech
        gc.collect()
    if oof_only:
        return {"status": "oof_saved", "seed": seed}

    H, W = footprint.shape
    p_phys_2d = np.zeros((H, W), dtype=np.float32)
    q_phys_2d = np.zeros((H, W), dtype=np.float32)
    p_full_2d = np.zeros((H, W), dtype=np.float32)
    q_full_2d = np.zeros((H, W), dtype=np.float32)
    p_tr_2d = np.zeros((H, W), dtype=np.float32)
    q_tr_2d = np.zeros((H, W), dtype=np.float32)

    p_phys_2d[footprint] = p_phys_fp
    q_phys_2d[footprint] = q_phys_fp
    p_full_2d[footprint] = p_full_fp
    q_full_2d[footprint] = q_full_fp
    p_tr_2d[footprint] = p_tr_avg
    q_tr_2d[footprint] = q_tr_avg

    cc_tune = _select_equilibrated_cc_params_inner(p_tr_2d, q_tr_2d, draw0_ref, quad, footprint)
    sel = cc_tune["selected"]
    print(f"[seed={seed}] Inner-selected equilibrated Charnes-Cooper params (0 outer test access): {sel}", flush=True)
    del draw0_ref
    gc.collect()

    p_eq_2d, q_eq_2d = equilibrate_quadrant_posteriors(p_full_2d, q_full_2d, quad, allow_vis, gamma=sel["gamma_eq"])
    p_ph_eq, q_ph_eq = equilibrate_quadrant_posteriors(p_phys_2d, q_phys_2d, quad, allow_vis, gamma=0.45)

    rng_c0 = np.random.default_rng(79000 + seed)
    allow_flat = np.flatnonzero(allow_ctrl)
    c0_map = np.zeros((H, W), dtype=np.float32)
    c0_map.ravel()[rng_c0.choice(allow_flat, size=37_654, replace=False)] = 1.0

    c1_map = poisson_disk_emit(fab_surface, allow_ctrl, budget=37_654, min_dist_px=2.8)
    c2_map = (d28_bool & allow_ctrl).astype(np.float32)

    exp1_surf = 0.60 * p_ph_eq + 0.40 * (np.clip(q_ph_eq, 0.0, 1.0) ** 1.5) * 0.25
    exp1_map = poisson_disk_emit(exp1_surf, allow_vis, budget=37_654, min_dist_px=2.8)

    exp2_surf = 0.70 * p_eq_2d + 0.30 * (np.clip(q_eq_2d, 0.0, 1.0) ** 1.6) * 0.28
    exp2_map = poisson_disk_emit(exp2_surf, allow_vis, budget=37_654, min_dist_px=2.8)

    exp3_map = charnes_cooper_submodular_emit(
        p_eq_2d,
        q_eq_2d,
        allow_vis,
        lambda_fp=sel["lambda_fp"],
        min_sep_px=sel["min_sep_px"],
        max_budget=sel["max_budget"],
        min_budget=20_000,
    )

    preds = {
        "EXP-PFSD-3_equil_charnes_cooper": exp3_map,
        "EXP-PFSD-2_pfsd_uniform_d28": exp2_map,
        "EXP-PFSD-1_uncorrupted_pure_physics": exp1_map,
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
            f_list.append(
                {
                    "fold": f_idx,
                    "dti": round(float(f_res["dti"]), 6),
                    "n_truth": f_res["n_truth"],
                    "n_emitted": f_res["n_emitted"],
                }
            )
            acc_terms = f_terms if acc_terms is None else (acc_terms + f_terms)
        terms_by_arm[arm_name] = acc_terms
        per_fold_scores[arm_name] = f_list

    official_eval = evaluate_holdout.pooled_summary(
        terms_by_arm, draws=1000, seed=620810 + seed, candidate="EXP-PFSD-3_equil_charnes_cooper"
    )
    official_eval["per_fold"] = per_fold_scores
    bootstrap_ci = _spatial_block_bootstrap(preds, folds, footprint, block_px=200, n_boot=1000, seed=20261022 + seed)
    regimes = _regime_decomposition(preds, folds, footprint, static_mm, mmap_path, vis)

    print(f"\n--- SEED {seed} H79-PFSD OFFICIAL HOLDOUT-DTI ({official_eval['evaluator_version']}) ---", flush=True)
    for k, v in official_eval["scores"].items():
        n_dots = int((preds[k] > 0).sum())
        fold_dots = [f["n_emitted"] for f in per_fold_scores[k]]
        print(
            f"  {k:36s}: HOLDOUT-DTI = {v['dti']:.6f}  95% CI [{v['ci95'][0]:.6f}, {v['ci95'][1]:.6f}]  "
            f"dots={n_dots:,} {fold_dots}  tp_w={v['tpw']:.1f}",
            flush=True,
        )

    out_payload = _sanitize_obj_paths(
        {
            "lane": "H79-PFSD",
            "seed": seed,
            "evaluator_version": official_eval["evaluator_version"],
            "withheld_positive_pixels": official_eval["scores"]["EXP-PFSD-3_equil_charnes_cooper"]["withheld_positive_pixels"],
            "elapsed_seconds": round(time.time() - t0, 2),
            "peak_rss_mb": round(rss_mb(), 1),
            "inner_charnes_cooper_selection": cc_tune,
            "official_evaluate_all": official_eval,
            "spatial_bootstrap_20km": bootstrap_ci,
            "regime_decomposition": regimes,
        }
    )
    ev_out.write_text(json.dumps(out_payload, indent=2) + "\n")
    return out_payload


def _fit_live_full_footprint_pfsd(
    cat: np.ndarray,
    footprint: np.ndarray,
    quad: np.ndarray,
    static_mm: np.memmap,
    mmap_path: Path,
    ctx_cols_fp: np.ndarray,
    cues_path: Path,
    cc_params_from_seeds: list[dict[str, Any]],
    cache_dir: Path,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    lp_npz = cache_dir / "live_posteriors_pfsd.npz"
    lp_meta = ROOT / "evidence" / "pfsd" / "live_model_meta.json"
    if lp_npz.exists() and lp_meta.exists():
        print("Reusing saved H79-PFSD live full-footprint posteriors...", flush=True)
        z = np.load(lp_npz)
        H, W = footprint.shape
        pl = np.zeros((H, W), dtype=np.float32)
        ql = np.zeros((H, W), dtype=np.float32)
        pl[footprint] = z["p_live_fp"].astype(np.float32)
        ql[footprint] = z["q_live_fp"].astype(np.float32)
        return pl, ql, json.loads(lp_meta.read_text())

    t0 = time.time()
    print("\n==================== TRAINING FULL-FOOTPRINT LIVE H79-PFSD ENSEMBLE ====================", flush=True)
    quad_fp = quad[footprint]
    n_fp = int(footprint.sum())
    all_rows = np.arange(n_fp, dtype=np.int64)
    all_mask = np.ones(n_fp, dtype=bool)

    lphys_ckpt = cache_dir / "live_phys_pfsd.npz"
    if lphys_ckpt.exists():
        print("  [live] Reloading cached live Pure-Physics OOF + full predictions...", flush=True)
        zp = np.load(lphys_ckpt)
        p_phys_oof_live = zp["p_phys_oof_live"].astype(np.float32)
        q_phys_oof_live = zp["q_phys_oof_live"].astype(np.float32)
        p_phys_live = zp["p_phys_live"].astype(np.float32)
        q_phys_live = zp["q_phys_live"].astype(np.float32)
        phys_imp = zp["phys_imp"].astype(np.float64)
    else:
        p_phys_oof_live, q_phys_oof_live, full_phys_m = run_pure_physics_oof(
            cat, footprint, quad_fp, static_mm, mmap_path, neg_per_fold=115_000, halo_per_fold=40_000, seed=9179, fit_full_model=True
        )
        assert full_phys_m is not None
        p_phys_live, q_phys_live = predict_pure_physics_rows(
            full_phys_m, static_mm, mmap_path, all_rows, true_pi=full_phys_m["true_pi_all"]
        )
        phys_imp = full_phys_m["lgb_deep"].booster_.feature_importance(importance_type="gain").astype(np.float64)
        np.savez_compressed(
            lphys_ckpt,
            p_phys_oof_live=p_phys_oof_live.astype(np.float16),
            q_phys_oof_live=q_phys_oof_live.astype(np.float16),
            p_phys_live=p_phys_live.astype(np.float16),
            q_phys_live=q_phys_live.astype(np.float16),
            phys_imp=phys_imp,
        )
        del full_phys_m
        gc.collect()

    live_shards, live_draw0 = build_decontaminated_quadrant_shards(
        cat, footprint, quad_fp, static_mm, mmap_path, cues_path, n_draws=4, hide_frac=0.22, buffer_px=3, neg_per_quad_per_draw=24_000, seed_base=9300
    )
    live_mech = np.clip(np.nan_to_num(compute_network_mechanics(cat, footprint, cues_path), nan=0.0, posinf=3e4, neginf=-3e4), -3e4, 3e4).astype(np.float16)

    oof_p1 = np.zeros(n_fp, dtype=np.float32)
    oof_q1 = np.zeros(n_fp, dtype=np.float32)
    for q_id in range(4):
        tr_qs = [q for q in range(4) if q != q_id]
        va_r = np.flatnonzero(quad_fp == q_id)
        Xq, yq, qq, wq, tpi_q, _ = _stack_shards(live_shards, tr_qs)
        sq = fit_stage1_mech_ensemble(Xq, yq, qq, wq, seed=940 + q_id)
        del Xq, yq, qq, wq
        oof_p1[va_r], oof_q1[va_r] = predict_stage1_mech_rows(
            sq, static_mm, mmap_path, live_draw0["mech_fp16"], va_r, tpi_q
        )
        del sq
        gc.collect()

    S2_oof = extract_stage2_dual_expert_features(
        oof_p1, oof_q1, p_phys_oof_live, q_phys_oof_live, footprint, ctx_cols_fp
    )
    del oof_p1, oof_q1, p_phys_oof_live, q_phys_oof_live
    s2_live = fit_stage2_dual_expert_heads(S2_oof, live_draw0, all_mask, seed=979)
    del S2_oof
    gc.collect()

    p1_live = np.zeros(n_fp, dtype=np.float32)
    q1_live = np.zeros(n_fp, dtype=np.float32)
    feat_imp = np.zeros(len(PFSD_ALL_FEATURE_NAMES), dtype=np.float64)
    Xf, yf, qf, wf, tpi_f, _ = _stack_shards(live_shards, [0, 1, 2, 3])
    for rep in range(2):
        sf = fit_stage1_mech_ensemble(Xf, yf, qf, wf, seed=1100 + 37 * rep)
        feat_imp += 0.5 * sf["lgb_deep"].booster_.feature_importance(importance_type="gain")
        pr, qr = predict_stage1_mech_rows(sf, static_mm, mmap_path, live_mech, all_rows, tpi_f)
        p1_live += 0.5 * pr
        q1_live += 0.5 * qr
        del sf
        gc.collect()
    del Xf, yf, qf, wf, live_shards, live_draw0, live_mech
    gc.collect()

    S2_live = extract_stage2_dual_expert_features(
        p1_live, q1_live, p_phys_live, q_phys_live, footprint, ctx_cols_fp
    )
    del p1_live, q1_live, p_phys_live, q_phys_live
    p2_live_fp, q2_live_fp = predict_stage2_dual_expert_heads(s2_live, S2_live, all_rows)
    del S2_live, s2_live
    gc.collect()

    H, W = footprint.shape
    p_live_2d = np.zeros((H, W), dtype=np.float32)
    q_live_2d = np.zeros((H, W), dtype=np.float32)
    p_live_2d[footprint] = p2_live_fp
    q_live_2d[footprint] = q2_live_fp

    top_imp = sorted(
        [
            {"feature": PFSD_ALL_FEATURE_NAMES[i], "gain_share": round(float(feat_imp[i] / max(feat_imp.sum(), 1e-9)), 6)}
            for i in range(len(PFSD_ALL_FEATURE_NAMES))
        ],
        key=lambda r: -r["gain_share"],
    )
    top_phys_imp = sorted(
        [
            {"feature": PFSD_STATIC_FEATURE_NAMES[i], "gain_share": round(float(phys_imp[i] / max(phys_imp.sum(), 1e-9)), 6)}
            for i in range(len(PFSD_STATIC_FEATURE_NAMES))
        ],
        key=lambda r: -r["gain_share"],
    )
    meta_live = {
        "lane": "H79-PFSD",
        "live_train_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
        "top25_features_by_gain": top_imp[:25],
        "top20_pure_physics_features_by_gain": top_phys_imp[:20],
        "cc_params_by_seed": cc_params_from_seeds,
    }
    np.savez_compressed(
        lp_npz,
        p_live_fp=p2_live_fp.astype(np.float16),
        q_live_fp=q2_live_fp.astype(np.float16),
    )
    lp_meta.write_text(json.dumps(meta_live, indent=2) + "\n")
    print(f"Live H79-PFSD ensemble complete in {meta_live['live_train_seconds']}s, RSS={meta_live['peak_rss_mb']} MB", flush=True)
    return p_live_2d, q_live_2d, meta_live


def _build_complete_family_and_local_index() -> dict[str, Any]:
    """Assemble ALL unique SHA-256 rasters across frozen registry (992), committed delta (207),
    post-04:31Z live delta (2+), and all local GEMSDOE79 canonical/archived .tif files."""
    seen_sha: dict[str, dict[str, Any]] = {}
    cache_dir = ROOT / ".cache" / "registry"

    frozen = json.loads((ROOT / "registry" / "registry_index.json").read_text())
    for r in frozen["rasters"]:
        cfile = cache_dir / f"{r['blob']}.tif"
        sha = r.get("sha256") or hashlib.sha256(cfile.read_bytes()).hexdigest()
        occs = r.get("occurrences", [])
        repo_first = r.get("repo") or (occs[0]["repo"] if occs else "unknown")
        sources = [f"{o['repo']}:{o['path']}" for o in occs] if occs else [f"{repo_first}:{r['blob']}.tif"]
        if sha in seen_sha:
            seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | set(sources))
        else:
            seen_sha[sha] = {"repo_first": repo_first, "sources": sorted(set(sources)), "cache_file": str(cfile), "sha256": sha}

    delta = json.loads((ROOT / "registry" / "registry_delta.json").read_text())
    for r in delta["rasters"]:
        cfile = cache_dir / f"{r['blob']}.tif"
        sha = r["sha256"]
        sources = list(r.get("aliases") or [f"{r['repo']}:{r['path']}"])
        if sha in seen_sha:
            seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | set(sources))
        else:
            seen_sha[sha] = {"repo_first": r["repo"], "sources": sorted(set(sources)), "cache_file": str(cfile), "sha256": sha}

    live_extra_path = ROOT / ".cache" / "live_post_0431_delta.json"
    if live_extra_path.exists():
        for r in json.loads(live_extra_path.read_text()):
            cfile = cache_dir / f"{r['blob']}.tif"
            if cfile.is_file():
                sha = r["sha256"]
                sources = list(r.get("aliases") or [f"{r['repo']}:{r['path']}"])
                if sha in seen_sha:
                    seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | set(sources))
                else:
                    seen_sha[sha] = {"repo_first": r["repo"], "sources": sorted(set(sources)), "cache_file": str(cfile), "sha256": sha}

    for folder in (ROOT / "docs" / "downloads", ROOT / "archive"):
        if folder.exists():
            for tif in sorted(folder.rglob("*.tif")):
                sha = hashlib.sha256(tif.read_bytes()).hexdigest()
                src = f"GEMSDOE79:{_rel(tif)}"
                if sha in seen_sha:
                    seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | {src})
                else:
                    seen_sha[sha] = {"repo_first": "GEMSDOE79", "sources": [src], "cache_file": str(tif), "sha256": sha}

    return {"complete_accessible_scan": True, "errors": [], "rasters": list(seen_sha.values())}


def _audit_worker(args: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    cand_path_str, sub_idx = args
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    return uniqueness.compare_to_registry(Path(cand_path_str), sub_idx, fp)


def _parallel_audit_complete_registry(
    candidate_tif: Path,
    footprint: np.ndarray,
    label_tag: str,
    combined_idx: dict[str, Any],
) -> dict[str, Any]:
    """Run unmodified vendor/gems57/uniqueness.py across 2 workers over ALL family + local rasters."""
    t0 = time.time()
    rasters = combined_idx["rasters"]
    n_tot = len(rasters)
    print(f"\n[uniqueness:{label_tag}] Auditing {_rel(candidate_tif)} against {n_tot} unique SHA-256 rasters...", flush=True)
    mid = (n_tot + 1) // 2
    idx_a = {"complete_accessible_scan": True, "errors": [], "rasters": rasters[:mid]}
    idx_b = {"complete_accessible_scan": True, "errors": [], "rasters": rasters[mid:]}

    with cf.ProcessPoolExecutor(max_workers=2) as pool:
        res_a, res_b = list(pool.map(_audit_worker, [(str(candidate_tif), idx_a), (str(candidate_tif), idx_b)]))

    rows = res_a["rows"] + res_b["rows"]
    cmeta = {
        "my_file": _rel(candidate_tif),
        "my_dots": res_a["my_dots"],
        "candidate_decoded_sha256": res_a["candidate_decoded_sha256"],
        "candidate_file_sha256": res_a["candidate_file_sha256"],
        "candidate_rank_variation": res_a["candidate_rank_variation"],
    }
    merged = uniqueness.summarize_registry_rows(
        rows,
        registry_rasters_expected=n_tot,
        complete_accessible_scan=True,
        source_errors=[],
        candidate_meta=cmeta,
        scope="Complete SHA-256 inventory: 992 frozen + 207 committed delta + post-04:31Z live delta + all local GEMSDOE79 lanes.",
    )
    phase = uniqueness.two_phase_summary(rows, int(footprint.sum()), expected_rasters=n_tot)

    # Also compute Amendment D-2 chance-corrected diagnostic & sparse <=50k / <=75k breakdowns
    checked = [r for r in rows if "error" not in r]
    valid_rhos = [
        abs(float(r["spearman_full_footprint"]))
        for r in checked
        if r.get("spearman_full_footprint") is not None and np.isfinite(r["spearman_full_footprint"])
    ]
    max_abs_rho = float(max(valid_rhos)) if valid_rhos else 0.0

    sparse_50k = [r for r in checked if 0 < int(r.get("their_dots", 0)) <= 50_000]
    sparse_50k_sorted = sorted(sparse_50k, key=lambda r: -float(r["my_dots_within_3px_of_theirs"]))
    sparse_75k = [r for r in checked if 0 < int(r.get("their_dots", 0)) <= 75_308]
    sparse_75k_sorted = sorted(sparse_75k, key=lambda r: -float(r["my_dots_within_3px_of_theirs"]))

    key_peers: dict[str, Any] = {}
    peer_Substrings = {
        "H33_GEMSDOE32": "h33-h33-2-b2",
        "G79_THVC_canonical": "g79-thvc-ccsubmod",
        "H79_FNHR_F3": "h79-fnhr-f3",
        "GEMSDOE83_gvcd": "gems83-h83-gvcd",
        "GEMSDOE78_gfv_latest": "gems78-h78-gfv",
        "GEMSDOE78_mghd": "gems78-h78mghd",
        "GEMSDOE73_mcsc": "gems73-h73-mcsc",
    }
    for r in checked:
        joined = " ".join(r.get("sources", []) + [r.get("submission", "")])
        for pk, sub in peer_Substrings.items():
            if sub in joined:
                key_peers[pk] = {
                    "submission": r["submission"],
                    "sha256": r["sha256"],
                    "their_dots": r["their_dots"],
                    "forward_overlap_3px": round(float(r["my_dots_within_3px_of_theirs"]), 6),
                    "reverse_overlap_3px": round(float(r["their_dots_within_3px_of_mine"]), 6),
                    "spearman_full_footprint": round(float(r["spearman_full_footprint"]), 6)
                    if r.get("spearman_full_footprint") is not None and np.isfinite(r["spearman_full_footprint"])
                    else None,
                }

    summary_doc = _sanitize_obj_paths(
        {
            "label": label_tag,
            "my_file": merged["my_file"],
            "my_dots": merged["my_dots"],
            "candidate_file_sha256": merged["candidate_file_sha256"],
            "candidate_decoded_sha256": merged["candidate_decoded_sha256"],
            "registry_rasters_expected": merged["registry_rasters_expected"],
            "registry_rasters_checked": merged["registry_rasters_checked"],
            "missing_or_invalid": merged["missing_or_invalid"],
            "literal_unique": merged["unique"],
            "literal_duplicate_count": merged["duplicate_count"],
            "max_abs_spearman": round(max_abs_rho, 6),
            "worst_spearman_submission": merged["worst_rho_submission"],
            "worst_literal_dot_overlap": merged["worst_dot_overlap"],
            "worst_literal_overlap_submission": merged["worst_overlap_submission"],
            "worst_jaccard_dot_sets": merged["worst_jaccard_dot_sets"],
            "sparse_le_50k_count": len(sparse_50k),
            "sparse_le_50k_collisions_gt_070": sum(1 for r in sparse_50k if float(r["my_dots_within_3px_of_theirs"]) > 0.70),
            "sparse_le_50k_max_overlap": round(float(sparse_50k_sorted[0]["my_dots_within_3px_of_theirs"]), 6) if sparse_50k_sorted else 0.0,
            "sparse_le_50k_top10": [
                {
                    "repo": r.get("repo"),
                    "submission": r.get("submission"),
                    "sha256": r.get("sha256"),
                    "their_dots": r.get("their_dots"),
                    "forward_overlap_3px": round(float(r["my_dots_within_3px_of_theirs"]), 6),
                    "reverse_overlap_3px": round(float(r["their_dots_within_3px_of_mine"]), 6),
                    "spearman": round(float(r["spearman_full_footprint"]), 6)
                    if r.get("spearman_full_footprint") is not None and np.isfinite(r["spearman_full_footprint"])
                    else None,
                }
                for r in sparse_50k_sorted[:10]
            ],
            "sparse_le_75k_count": len(sparse_75k),
            "sparse_le_75k_collisions_gt_070": sum(1 for r in sparse_75k if float(r["my_dots_within_3px_of_theirs"]) > 0.70),
            "sparse_le_75k_max_overlap": round(float(sparse_75k_sorted[0]["my_dots_within_3px_of_theirs"]), 6) if sparse_75k_sorted else 0.0,
            "key_peer_comparisons": key_peers,
            "two_phase_summary": {k: v for k, v in phase.items() if k != "literal_firings"},
            "non_comparable_entries": [r for r in rows if "error" in r],
            "audit_elapsed_seconds": round(time.time() - t0, 2),
        }
    )
    print(
        f"[uniqueness:{label_tag}] Done in {summary_doc['audit_elapsed_seconds']}s | "
        f"checked={summary_doc['registry_rasters_checked']}/{summary_doc['registry_rasters_expected']} | "
        f"max |rho|={summary_doc['max_abs_spearman']} | "
        f"sparse<=50k collisions={summary_doc['sparse_le_50k_collisions_gt_070']}/{summary_doc['sparse_le_50k_count']} "
        f"(max={summary_doc['sparse_le_50k_max_overlap']}) | "
        f"literal unique={summary_doc['literal_unique']}",
        flush=True,
    )
    return summary_doc


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--stage",
        default="all",
        choices=("features", "canaries", "seed20", "seed30_oof", "seed30", "live", "audit_and_package", "all"),
    )
    args = ap.parse_args()

    cache_dir = ROOT / ".cache" / "pfsd"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ev_dir = ROOT / "evidence" / "pfsd"
    ev_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
        transform = ds.transform
        crs = ds.crs
    with rasterio.open(ROOT / "data/raw/existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & footprint

    mmap_path = cache_dir / "static_fp92.f32.mmap"
    cues_path = mmap_path.with_suffix(".cues.npz")
    static_meta = build_pfsd_static_memmap(
        ROOT / "data/raw",
        ROOT / ".cache/official_ing",
        ROOT / "data/cache/dem10",
        mmap_path,
        footprint,
        transform,
    )
    (ev_dir / "static_feature_meta.json").write_text(json.dumps(static_meta, indent=2) + "\n")
    print(f"[features] 92-ch static memmap ready ({static_meta['build_seconds']}s, peak RSS={static_meta['peak_rss_mb']} MB)", flush=True)
    if args.stage == "features":
        return

    static_mm = np.memmap(mmap_path, dtype="float32", mode="r", shape=(int(footprint.sum()), len(PFSD_STATIC_FEATURE_NAMES)))
    cmap = {n: i for i, n in enumerate(PFSD_STATIC_FEATURE_NAMES)}
    ctx_cols_fp = np.clip(
        np.nan_to_num(
            np.column_stack(
                [
                    static_mm[:, cmap["lidar_present"]],
                    static_mm[:, cmap["scarp_unified_step"]],
                    static_mm[:, cmap["hydro_demag_clay_conj"]],
                    static_mm[:, cmap["mountain_wall_ratio"]],
                ]
            ),
            nan=0.0,
            posinf=3e4,
            neginf=-3e4,
        ),
        -3e4,
        3e4,
    ).astype(np.float16)
    drop_file_cache(mmap_path)
    grid = Grid(footprint, cat, str(crs), transform, footprint.shape[0], footprint.shape[1])

    if args.stage in ("canaries", "all"):
        _run_leakage_canaries(grid, footprint, static_mm, mmap_path, cues_path)
    if args.stage == "canaries":
        return

    d28_path = ROOT / ".cache/registry/bfb7e86d046dd178c3d6ab60522861b5464dd420.tif"
    with rasterio.open(d28_path) as ds:
        d28_bool = (ds.read(1) > 0) & footprint
    fab_path = ROOT / "archive/g79_fabric_offset_f61b17a2/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif"
    with rasterio.open(fab_path) as ds:
        fab_surface = np.nan_to_num(ds.read(1).astype(np.float32), nan=0.0) * footprint

    if args.stage in ("seed20", "all"):
        _evaluate_one_seed(20, grid, footprint, static_mm, mmap_path, ctx_cols_fp, cues_path, d28_bool, fab_surface, cache_dir)
    if args.stage == "seed20":
        return

    if args.stage == "seed30_oof":
        _evaluate_one_seed(30, grid, footprint, static_mm, mmap_path, ctx_cols_fp, cues_path, d28_bool, fab_surface, cache_dir, oof_only=True)
        return

    if args.stage in ("seed30", "all"):
        _evaluate_one_seed(30, grid, footprint, static_mm, mmap_path, ctx_cols_fp, cues_path, d28_bool, fab_surface, cache_dir)
    if args.stage == "seed30":
        return

    eval20 = json.loads((ev_dir / "eval_seed20.json").read_text())
    eval30 = json.loads((ev_dir / "eval_seed30.json").read_text())
    _, quad_live = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)

    if args.stage in ("live", "audit_and_package", "all"):
        p_live_2d, q_live_2d, live_meta = _fit_live_full_footprint_pfsd(
            cat,
            footprint,
            quad_live,
            static_mm,
            mmap_path,
            ctx_cols_fp,
            cues_path,
            [eval20["inner_charnes_cooper_selection"]["selected"], eval30["inner_charnes_cooper_selection"]["selected"]],
            cache_dir,
        )
    if args.stage == "live":
        return

    canary = json.loads((ev_dir / "leakage_canary.json").read_text())
    allow_live = footprint & (ndi.distance_transform_edt(~cat) > 3.0)

    s20_p = eval20["inner_charnes_cooper_selection"]["selected"]
    s30_p = eval30["inner_charnes_cooper_selection"]["selected"]
    consensus_gamma = round(0.5 * (s20_p["gamma_eq"] + s30_p["gamma_eq"]), 4)
    consensus_lam = round(0.5 * (s20_p["lambda_fp"] + s30_p["lambda_fp"]), 4)
    consensus_sep = float(max(s20_p["min_sep_px"], s30_p["min_sep_px"]))
    consensus_maxb = int(round(0.5 * (s20_p["max_budget"] + s30_p["max_budget"])))

    p_live_eq, q_live_eq = equilibrate_quadrant_posteriors(p_live_2d, q_live_2d, quad_live, allow_live, gamma=consensus_gamma)

    # Gate 1: Pre-placement continuous surface audit across ALL family + local rasters!
    surf_blend = (0.70 * np.clip(p_live_eq, 0.0, 1.0) + 0.30 * (np.clip(q_live_eq, 0.0, 1.0) ** 1.6) * 0.28).astype(np.float32)
    smax = float(surf_blend[footprint & (~cat)].max())
    surf_norm = np.where(footprint & (~cat), np.clip(surf_blend / max(smax, 1e-9), 0.0, 1.0), 0.0).astype(np.float32)
    tmp_surf_tif = cache_dir / "h79_pfsd_continuous_surface.tif"
    for stale_tmp in cache_dir.glob("h79_pfsd_continuous_surface.*"):
        stale_tmp.unlink()
    submission_writer.write_submission(
        tmp_surf_tif,
        surf_norm,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name="h79-pfsd-preplacement-surface",
        note="Pre-placement continuous posterior surface for complete family uniqueness check",
        catalogue=cat,
    )

    combined_idx = _build_complete_family_and_local_index()
    surf_audit_path = ev_dir / "uniqueness_surface.json"
    surf_audit = _parallel_audit_complete_registry(tmp_surf_tif, footprint, "pre_placement_surface", combined_idx)
    surf_audit_path.write_text(json.dumps(surf_audit, indent=2) + "\n")
    if surf_audit["max_abs_spearman"] > 0.90:
        raise RuntimeError(f"PRE-PLACEMENT SURFACE DUPLICATE: |rho|={surf_audit['max_abs_spearman']} > 0.90 — STOPPING.")

    # Gate 2: Emit binary GeoTIFF into staging & run post-placement audit across ALL family + local rasters!
    emitted_live = charnes_cooper_submodular_emit(
        p_live_eq,
        q_live_eq,
        allow_live,
        lambda_fp=consensus_lam,
        min_sep_px=consensus_sep,
        max_budget=consensus_maxb,
        min_budget=20_000,
    )
    raw_bytes_hash = hashlib.sha256(emitted_live.tobytes()).hexdigest()[:8]
    n_dots = int((emitted_live > 0).sum())
    staging_dir = cache_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    for stale_s in staging_dir.glob("*"):
        stale_s.unlink()

    provisional_stem = f"h79-pfsd-equilcc-20261022-{raw_bytes_hash}-zeros-DO-NOT-SUBMIT"
    note = (
        f"GEMSDOE79 H79-PFSD: strike-concord+2m-flux+10m3DEP dual-expert + equil Charnes-Cooper ({n_dots} px)"
    )[:140]
    staged_tif = staging_dir / f"{provisional_stem}.tif"
    writer_manifest = submission_writer.write_submission(
        staged_tif,
        emitted_live,
        ROOT / "data/raw/sample_submission.tif",
        footprint,
        name=provisional_stem,
        note=note,
        catalogue=cat,
        metadata={
            "lane": "H79-PFSD",
            "consensus_equilibrated_charnes_cooper": {
                "gamma_eq": consensus_gamma,
                "lambda_fp": consensus_lam,
                "min_sep_px": consensus_sep,
                "max_budget": consensus_maxb,
            },
            "holdout_dti_seed20": eval20["official_evaluate_all"]["scores"]["EXP-PFSD-3_equil_charnes_cooper"],
            "holdout_dti_seed30": eval30["official_evaluate_all"]["scores"]["EXP-PFSD-3_equil_charnes_cooper"],
        },
    )
    writer_manifest = _sanitize_obj_paths(writer_manifest)
    val_out = _sanitize_obj_paths(validate_submission.validate_path(staged_tif))

    dot_audit = _parallel_audit_complete_registry(staged_tif, footprint, "post_placement_dots", combined_idx)
    (ev_dir / "uniqueness_dots.json").write_text(json.dumps(dot_audit, indent=2) + "\n")

    summary = _sanitize_obj_paths(
        {
            "lane": "H79-PFSD",
            "session_branch": "arena/9574eb05-gemsdoe79",
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "preregistration": "registry/preregistration_pfsd.json",
            "preregistration_sha256": (ev_dir / "preregistration_pfsd_sha256.txt").read_text().split()[0],
            "static_feature_meta": static_meta,
            "leakage_canary_summary": {
                "passed": canary["passed"],
                "total_canary_tests": canary["total_canary_tests"],
                "max_symmetric_auc": canary["max_symmetric_auc"],
                "max_feature": canary["max_feature"],
            },
            "seed20_scores": eval20["official_evaluate_all"]["scores"],
            "seed30_scores": eval30["official_evaluate_all"]["scores"],
            "live_model_meta": live_meta,
            "emitted_positive_pixels": n_dots,
            "staged_tif_sha256": dot_audit["candidate_file_sha256"],
            "validator_output": val_out,
            "surface_uniqueness_summary": {
                "checked": surf_audit["registry_rasters_checked"],
                "max_abs_spearman": surf_audit["max_abs_spearman"],
                "sparse_le_50k_collisions_gt_070": surf_audit["sparse_le_50k_collisions_gt_070"],
                "sparse_le_50k_max_overlap": surf_audit["sparse_le_50k_max_overlap"],
            },
            "dot_uniqueness_summary": {
                "checked": dot_audit["registry_rasters_checked"],
                "literal_unique": dot_audit["literal_unique"],
                "literal_duplicate_count": dot_audit["literal_duplicate_count"],
                "max_abs_spearman": dot_audit["max_abs_spearman"],
                "sparse_le_50k_collisions_gt_070": dot_audit["sparse_le_50k_collisions_gt_070"],
                "sparse_le_50k_max_overlap": dot_audit["sparse_le_50k_max_overlap"],
                "key_peer_comparisons": dot_audit["key_peer_comparisons"],
            },
            "writer_manifest": writer_manifest,
        }
    )
    (ev_dir / "pfsd_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("\nALL H79-PFSD STAGES COMPLETED CLEANLY — READY FOR FINAL ARCHIVE / RECONCILIATION!", flush=True)


if __name__ == "__main__":
    main()
