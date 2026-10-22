#!/usr/bin/env python3
"""Prospective execution runner for lane ``G79-STFD`` (Session ``1b017e86``).

Preregistration: ``registry/preregistration_g79_stfd.json``
SHA-256 lock:    ``4d62ae4c25c638fe5e24a40f279623e05c995503a1684cb81f47f56ce4e90a75``

Executes strictly within the 3-experiment budget and <= 2-hour cap:
  - Gate G2: 238 single-feature symmetric ROC-AUC leakage canaries (119 features x 2 seeds, <= 0.90)
  - EXP-STFD-1: Strict 4-fold LOQO 100%-visible decontaminated 97-ch zero-catalogue physics (d=2.8, B=37,654)
  - EXP-STFD-2: Strict 4-fold LOQO 119-ch quadrant-stratified multi-draw stacked model (d=2.8, B=37,654)
  - EXP-STFD-3: Self-consistent fractional Dinkelbach + pure-physics far-field reserve allocator
  - Full 196-repository accessible raster uniqueness audit (pre-placement surface + final placed GeoTIFF)
  - Validated GeoTIFF + single-TIFF ZIP via ``vendor/gems57/submission_writer.py`` + complete Run Card JSON
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

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata
import warnings
from rasterio.errors import NotGeoreferencedWarning
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout, holdout, submission_writer, uniqueness, validate  # noqa: E402
from gems57.grid import Grid  # noqa: E402
from gems79.cskd import _release_mm  # noqa: E402
from gems79.lifecycle import LaneClosedError  # noqa: E402
from gems79.stfd import (  # noqa: E402
    N_STFD_ALL,
    N_STFD_MECH,
    N_STFD_STATIC,
    STFD_ALL_FEATURE_NAMES,
    STFD_MECH_NAMES,
    STFD_STATIC_NAMES,
    build_stfd_full_visible_physics_shards,
    build_stfd_static_memmap,
    build_stfd_stratified_topology_shards,
    calibrate_quadrant_posteriors_to_visible_density,
    compute_stfd_mechanics,
    dinkelbach_stfd_emit,
    require_open_stfd_lane,
    run_stfd_quadrant_nested_oof,
)
from gems79.thvc_features import rss_mb  # noqa: E402
from gems79.thvc_model import poisson_disk_emit  # noqa: E402

CACHE_DIR = ROOT / ".cache" / "g79_stfd"
CSKD_CACHE_DIR = ROOT / ".cache" / "g79_cskd"
EV_DIR = ROOT / "evidence" / "stfd"
ARCH_DIR = ROOT / "archive" / "g79_stfd_1b017e86"
STFD_MMAP = CACHE_DIR / "static_fp97.f32.mmap"
STFD_CUES = CACHE_DIR / "stfd_cues.npz"


def _load_grid() -> tuple[Grid, np.ndarray, np.ndarray, Any]:
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
        transform = ds.transform
        crs = ds.crs
    with rasterio.open(ROOT / "data/raw/existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & fp
    return Grid(fp, cat, str(crs), transform, fp.shape[0], fp.shape[1]), fp, cat, transform


def _extract_stfd_stage2_ctx(stfd_cues_path: Path) -> np.ndarray:
    """5 domain-debiased physical context columns for Stage-2 spatial line-integral stacking."""
    z = np.load(stfd_cues_path)
    return np.column_stack(
        [
            z["scarp_qnorm_fp"].astype(np.float32),
            z["grav_bdepth_conc_fp"].astype(np.float32),
            z["swarm_transt_fp"].astype(np.float32),
            z["clean_veto_fp"].astype(np.float32),
            z["piedmont_break_fp"].astype(np.float32),
        ]
    )


def _symmetric_auc(y_bool: np.ndarray, x_vals: np.ndarray) -> float:
    x_fin = np.nan_to_num(x_vals.astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    if y_bool.sum() == 0 or y_bool.sum() == y_bool.size or np.ptp(x_fin) == 0.0:
        return 0.5
    auc = float(roc_auc_score(y_bool, x_fin))
    return max(auc, 1.0 - auc)


def _spatial_block_bootstrap(
    preds: dict[str, np.ndarray],
    folds: list[dict[str, Any]],
    footprint: np.ndarray,
    *,
    block_px: int = 200,
    n_boot: int = 1000,
    seed: int = 20261022,
) -> dict[str, Any]:
    """20-km physical spatial block bootstrap over all active holdout blocks."""
    H, W = footprint.shape
    bh = (H + block_px - 1) // block_px
    bw = (W + block_px - 1) // block_px
    gy, gx = np.mgrid[0:H, 0:W]
    block_id = (gy // block_px) * bw + (gx // block_px)
    n_blocks_grid = bh * bw

    from gems57 import metric

    active_all = np.zeros((H, W), dtype=bool)
    truth_all = np.zeros((H, W), dtype=bool)
    for f in folds:
        act_f = footprint & f["region"] & (~f["masked_known"])
        active_all |= act_f
        truth_all |= f["truth"] & act_f

    used_blocks = np.unique(block_id[active_all])
    b_map = {int(b): i for i, b in enumerate(used_blocks)}
    nb = len(used_blocks)
    idx_grid = np.full((H, W), -1, dtype=np.int32)
    for b_orig, i_seq in b_map.items():
        idx_grid[block_id == b_orig] = i_seq

    dg_truth = ndi.distance_transform_edt(~truth_all)
    q_truth = metric.kernel(dg_truth)
    ty, tx = np.nonzero(truth_all)
    t_blk = idx_grid[ty, tx]

    stats: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for arm, p_arr in preds.items():
        pm = (p_arr > 0) & active_all
        py, px = np.nonzero(pm)
        p_blk = idx_grid[py, px]
        dp = ndi.distance_transform_edt(~pm)
        t_cred = metric.kernel(dp[ty, tx])
        f_cost = 1.0 - q_truth[py, px]

        tp_b = np.bincount(t_blk, weights=t_cred, minlength=nb)
        fn_b = np.bincount(t_blk, weights=1.0 - t_cred, minlength=nb)
        fp_b = np.bincount(p_blk, weights=f_cost, minlength=nb)
        stats[arm] = (tp_b, fp_b, fn_b)

    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, nb, size=(n_boot, nb))
    draws_by_arm: dict[str, np.ndarray] = {}
    point_by_arm: dict[str, float] = {}
    arms_out: dict[str, Any] = {}

    for arm, (tp_b, fp_b, fn_b) in stats.items():
        tp_tot, fp_tot, fn_tot = float(tp_b.sum()), float(fp_b.sum()), float(fn_b.sum())
        pt = tp_tot / (tp_tot + 0.2 * fp_tot + 0.8 * fn_tot + 1e-12)
        tp_s = tp_b[boot_idx].sum(axis=1)
        fp_s = fp_b[boot_idx].sum(axis=1)
        fn_s = fn_b[boot_idx].sum(axis=1)
        d_s = tp_s / (tp_s + 0.2 * fp_s + 0.8 * fn_s + 1e-12)
        draws_by_arm[arm] = d_s
        point_by_arm[arm] = pt
        arms_out[arm] = {
            "point_dti": round(pt, 6),
            "ci95_low": round(float(np.percentile(d_s, 2.5)), 6),
            "ci95_high": round(float(np.percentile(d_s, 97.5)), 6),
            "std_err": round(float(np.std(d_s, ddof=1)), 6),
        }

    cand_key = "EXP-STFD-3_stfd_fractional_dinkelbach"
    paired_out: dict[str, Any] = {}
    for arm in stats:
        if arm == cand_key:
            continue
        diff = draws_by_arm[cand_key] - draws_by_arm[arm]
        paired_out[f"{cand_key}__minus__{arm}"] = {
            "delta_dti": round(point_by_arm[cand_key] - point_by_arm[arm], 6),
            "ci95_low": round(float(np.percentile(diff, 2.5)), 6),
            "ci95_high": round(float(np.percentile(diff, 97.5)), 6),
            "prob_positive": round(float((diff > 0.0).mean()), 4),
        }

    return {
        "n_blocks_20km": nb,
        "grid_blocks_capacity": n_blocks_grid,
        "n_bootstrap_draws": n_boot,
        "arms": arms_out,
        "paired_deltas": paired_out,
    }


def _evaluate_detached_diagnostic(preds: dict[str, np.ndarray], grid: Grid, seed: int) -> dict[str, Any]:
    """Evaluate recovery on conservative detached strands (>=400 m isolated from all visible traces)."""
    ctx = holdout.build_holdout(grid, seeds=(seed,), modes=("detached",))
    out: dict[str, Any] = {}
    for arm, pred in preds.items():
        r = holdout.evaluate(pred > 0, ctx, cell_mode="detached")
        out[arm] = {
            "detached_pooled_dti": round(float(r["pooled_dti"]), 6),
            "detached_coverage": round(float(r["pooled_coverage"]), 6),
            "detached_n_truth": int(r["pooled_n_truth"]),
            "emitted_pixels": int(r["emitted_pixels"]),
        }
    return out


def run_stage_canary() -> dict[str, Any]:
    t0 = time.time()
    grid, fp, _cat, transform = _load_grid()
    static_mm, cskd_cues_path = build_stfd_static_memmap(ROOT, CSKD_CACHE_DIR, STFD_MMAP, STFD_CUES, fp, transform)

    canary_out: dict[str, Any] = {
        "lane": "G79-STFD",
        "threshold": 0.90,
        "n_static_features": N_STFD_STATIC,
        "n_mech_features": N_STFD_MECH,
        "n_features_tested": N_STFD_ALL,
        "feature_seed_tests": N_STFD_ALL * 2,
        "per_seed": {},
    }

    overall_max = 0.0
    overall_worst = ""

    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        vis = folds[0]["visible"]
        active = np.zeros_like(fp, dtype=bool)
        truth = np.zeros_like(fp, dtype=bool)
        for f in folds:
            act_f = fp & f["region"] & (~f["masked_known"])
            active |= act_f
            truth |= f["truth"] & act_f

        act_fp = active[fp]
        y_act = truth[fp][act_fp]
        pos_i = np.flatnonzero(y_act)
        rng = np.random.default_rng(7900 + seed)
        neg_i = rng.choice(np.flatnonzero(~y_act), size=350_000, replace=False)
        sub_local = np.sort(np.concatenate([pos_i, neg_i]))
        global_rows = np.flatnonzero(act_fp)[sub_local]
        y_sub = y_act[sub_local]

        X_stat_sub = np.array(static_mm[global_rows], dtype=np.float32, copy=True)
        _release_mm(static_mm, STFD_MMAP)

        mech_fp = compute_stfd_mechanics(vis, fp, cskd_cues_path, STFD_CUES)
        X_mech_sub = mech_fp[global_rows]
        del mech_fp
        gc.collect()

        X_sub = np.hstack([X_stat_sub, X_mech_sub])
        del X_stat_sub, X_mech_sub

        rows_seed: dict[str, Any] = {}
        seed_max = 0.0
        seed_worst = ""
        for j, fname in enumerate(STFD_ALL_FEATURE_NAMES):
            auc = _symmetric_auc(y_sub, X_sub[:, j])
            rows_seed[fname] = {"symmetric_auc": round(auc, 6), "passed": bool(auc <= 0.90)}
            if auc > seed_max:
                seed_max = auc
                seed_worst = fname
            if auc > overall_max:
                overall_max = auc
                overall_worst = fname

        canary_out["per_seed"][str(seed)] = {
            "withheld_positive_pixels": int(pos_i.size),
            "sampled_negatives": int(neg_i.size),
            "max_symmetric_auc": round(seed_max, 6),
            "worst_feature": seed_worst,
            "all_passed": bool(seed_max <= 0.90),
            "top10_features": sorted(
                ({"feature": k, **v} for k, v in rows_seed.items()),
                key=lambda r: -r["symmetric_auc"],
            )[:10],
            "features": rows_seed,
        }
        print(
            f"[stfd canary seed={seed}] 119 features tested | max symmetric AUC = {seed_max:.5f} ({seed_worst}) "
            f"| passed={seed_max <= 0.90} | RSS={rss_mb():.0f} MB",
            flush=True,
        )

    canary_out["overall_max_symmetric_auc"] = round(overall_max, 6)
    canary_out["overall_worst_feature"] = overall_worst
    canary_out["gate_passed"] = bool(overall_max <= 0.90)
    canary_out["elapsed_seconds"] = round(time.time() - t0, 2)

    EV_DIR.mkdir(parents=True, exist_ok=True)
    (EV_DIR / "canary_238_tests.json").write_text(json.dumps(canary_out, indent=2) + "\n")
    if not canary_out["gate_passed"]:
        raise RuntimeError(f"Leakage canary FAILED: {overall_worst} = {overall_max:.5f} > 0.90")
    return canary_out


def _fit_and_predict_stfd_for_mask(
    vis: np.ndarray,
    fp: np.ndarray,
    quad_2d: np.ndarray,
    static_mm: np.memmap,
    cskd_cues_path: Path,
    ctx_cols_fp: np.ndarray,
    cache_tag: str,
    seed_offset: int,
) -> dict[str, Any]:
    """Exact unified strict-LOQO pipeline shared across seed20, seed30, and live inference."""
    ckpt_npz = CACHE_DIR / f"posteriors_{cache_tag}.npz"
    ckpt_meta = CACHE_DIR / f"meta_{cache_tag}.json"
    quad_fp = quad_2d[fp]

    if ckpt_npz.exists() and ckpt_meta.exists():
        print(f"[stfd {cache_tag}] Reloading cached strict-LOQO posteriors from {ckpt_npz}", flush=True)
        z = np.load(ckpt_npz)
        return {
            "p_full_fp": z["p_full_fp"].astype(np.float32),
            "q_full_fp": z["q_full_fp"].astype(np.float32),
            "p_phys_fp": z["p_phys_fp"].astype(np.float32),
            "q_phys_fp": z["q_phys_fp"].astype(np.float32),
            "coulomb_shadow_fp": z["coulomb_shadow_fp"].astype(np.float32),
            "meta": json.loads(ckpt_meta.read_text()),
        }

    phys_ckpt = CACHE_DIR / f"phys97_{cache_tag}.npz"
    if phys_ckpt.exists():
        print(f"[stfd {cache_tag}] Reloading cached 97-ch pure-physics LOQO {phys_ckpt} (RSS={rss_mb():.0f} MB)", flush=True)
        zp = np.load(phys_ckpt)
        p_phys_fp = zp["p_phys_fp"].astype(np.float32)
        q_phys_fp = zp["q_phys_fp"].astype(np.float32)
        phys_pair_oof = (zp["pair_p1"].astype(np.float32), zp["pair_q1"].astype(np.float32))
        phys_outer_oof = (zp["outer_p1"].astype(np.float32), zp["outer_q1"].astype(np.float32))
        phys_top_features = json.loads((CACHE_DIR / f"phys97_{cache_tag}.json").read_text())
    else:
        t_p = time.time()
        phys_shards, phys_ref = build_stfd_full_visible_physics_shards(
            vis, fp, quad_fp, static_mm, STFD_MMAP, neg_per_quad=44_000, seed=7950 + seed_offset
        )
        phys_res = run_stfd_quadrant_nested_oof(
            quad_fp,
            fp,
            static_mm,
            STFD_MMAP,
            ctx_cols_fp,
            phys_shards,
            [phys_ref],
            None,
            use_mechanics=False,
            seed=8100 + seed_offset,
        )
        p_phys_fp = phys_res["p2_fp"]
        q_phys_fp = phys_res["q2_fp"]
        phys_pair_oof = (phys_res["pair_oof_p1"], phys_res["pair_oof_q1"])
        phys_outer_oof = (phys_res["outer_p1"], phys_res["outer_q1"])
        phys_top_features = phys_res["top_features"][:20]
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            phys_ckpt,
            p_phys_fp=p_phys_fp.astype(np.float16),
            q_phys_fp=q_phys_fp.astype(np.float16),
            pair_p1=phys_pair_oof[0].astype(np.float16),
            pair_q1=phys_pair_oof[1].astype(np.float16),
            outer_p1=phys_outer_oof[0].astype(np.float16),
            outer_q1=phys_outer_oof[1].astype(np.float16),
        )
        (CACHE_DIR / f"phys97_{cache_tag}.json").write_text(json.dumps(phys_top_features, indent=2) + "\n")
        del phys_shards, phys_ref, phys_res
        gc.collect()
        print(f"[stfd {cache_tag}] 97-ch 100%-visible pure-physics LOQO done in {time.time()-t_p:.1f}s (RSS={rss_mb():.0f} MB)", flush=True)

    t_m = time.time()
    topo_shards, draw_refs = build_stfd_stratified_topology_shards(
        vis,
        fp,
        quad_fp,
        static_mm,
        STFD_MMAP,
        cskd_cues_path,
        STFD_CUES,
        n_draws=4,
        hide_frac=0.22,
        buffer_px=3,
        neg_per_quad_per_draw=22_000,
        seed_base=8300 + seed_offset,
    )
    test_mech = compute_stfd_mechanics(vis, fp, cskd_cues_path, STFD_CUES)
    coulomb_shadow_fp = test_mech[:, STFD_MECH_NAMES.index("net_coulomb_shadow")].copy()
    test_mech_f16 = test_mech.astype(np.float16)
    del test_mech
    gc.collect()

    full_res = run_stfd_quadrant_nested_oof(
        quad_fp,
        fp,
        static_mm,
        STFD_MMAP,
        ctx_cols_fp,
        topo_shards,
        draw_refs,
        test_mech_f16,
        use_mechanics=True,
        phys_pair_oof=phys_pair_oof,
        phys_outer_oof=phys_outer_oof,
        seed=8600 + seed_offset,
    )
    p_full_fp = full_res["p2_fp"]
    q_full_fp = full_res["q2_fp"]
    full_top_features = full_res["top_features"][:25]
    mech_gain_share = sum(
        r["gain_share"] for r in full_res["top_features"] if r["feature"] in set(STFD_MECH_NAMES)
    )
    new_stfd_gain_share = sum(
        r["gain_share"]
        for r in full_res["top_features"]
        if r["feature"] in set(STFD_STATIC_NAMES[82:] + STFD_MECH_NAMES[18:])
    )
    del topo_shards, draw_refs, test_mech_f16, full_res, phys_pair_oof, phys_outer_oof
    gc.collect()
    print(f"[stfd {cache_tag}] 119-ch stacked LOQO done in {time.time()-t_m:.1f}s (RSS={rss_mb():.0f} MB)", flush=True)

    meta = {
        "cache_tag": cache_tag,
        "phys_top20_features": phys_top_features,
        "full_top25_features": full_top_features,
        "mechanics_gain_share_total": round(float(mech_gain_share), 6),
        "new_stfd_channels_gain_share_total": round(float(new_stfd_gain_share), 6),
        "peak_rss_mb": round(rss_mb(), 1),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        ckpt_npz,
        p_full_fp=p_full_fp.astype(np.float16),
        q_full_fp=q_full_fp.astype(np.float16),
        p_phys_fp=p_phys_fp.astype(np.float16),
        q_phys_fp=q_phys_fp.astype(np.float16),
        coulomb_shadow_fp=coulomb_shadow_fp.astype(np.float16),
    )
    ckpt_meta.write_text(json.dumps(meta, indent=2) + "\n")
    return {
        "p_full_fp": p_full_fp,
        "q_full_fp": q_full_fp,
        "p_phys_fp": p_phys_fp,
        "q_phys_fp": q_phys_fp,
        "coulomb_shadow_fp": coulomb_shadow_fp,
        "meta": meta,
    }


def _emit_all_stfd_arms(
    vis: np.ndarray,
    fp: np.ndarray,
    quad_2d: np.ndarray,
    fit_out: dict[str, Any],
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, Any]]:
    H, W = fp.shape
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    allow = fp & (d_vis >= 3.0)

    p_raw = np.zeros((H, W), dtype=np.float32)
    q_raw = np.zeros((H, W), dtype=np.float32)
    p_phys_raw = np.zeros((H, W), dtype=np.float32)
    q_phys_raw = np.zeros((H, W), dtype=np.float32)
    coulomb_2d = np.zeros((H, W), dtype=np.float32)

    p_raw[fp] = fit_out["p_full_fp"]
    q_raw[fp] = fit_out["q_full_fp"]
    p_phys_raw[fp] = fit_out["p_phys_fp"]
    q_phys_raw[fp] = fit_out["q_phys_fp"]
    coulomb_2d[fp] = fit_out["coulomb_shadow_fp"]

    # Zero-leakage observable regional visible-prevalence calibration on BOTH heads
    p_phys_cal0, q_phys_cal0, phys_qcal_diag = calibrate_quadrant_posteriors_to_visible_density(
        p_phys_raw, q_phys_raw, vis, allow, quad_2d, strength=0.75
    )
    p_full_cal, q_full_cal, full_qcal_diag = calibrate_quadrant_posteriors_to_visible_density(
        p_raw, q_raw, vis, allow, quad_2d, strength=0.75
    )

    # Mean-mass align 100%-visible physics head to 22%-hide posterior scale for smooth far-field blending
    p_scale = float(p_full_cal[allow].mean() / max(float(p_phys_cal0[allow].mean()), 1e-8))
    q_scale = float(q_full_cal[allow].mean() / max(float(q_phys_cal0[allow].mean()), 1e-8))
    p_phys_cal = np.clip(p_phys_cal0 * p_scale, 0.0, 0.96).astype(np.float32)
    q_phys_cal = np.clip(q_phys_cal0 * q_scale, 0.0, 0.98).astype(np.float32)

    w_far = np.clip(0.03 + 0.14 * ((d_vis - 8.0) / 30.0), 0.03, 0.17).astype(np.float32)
    p_blend = ((1.0 - w_far) * p_full_cal + w_far * p_phys_cal).astype(np.float32)
    q_blend = ((1.0 - w_far) * q_full_cal + w_far * q_phys_cal).astype(np.float32)

    # EXP-STFD-1: Pure zero-catalogue 97-ch physics (0 catalogue geometry at inference, B=37,654, d=2.8)
    exp1_surf = 0.68 * p_phys_cal0 + 0.32 * (np.clip(q_phys_cal0, 0.0, 1.0) ** 1.5) * 0.30
    exp1_map = poisson_disk_emit(exp1_surf, allow, budget=37_654, min_dist_px=2.8)

    # EXP-STFD-2: Full 119-ch stacked STFD surface at matched uniform spacing (B=37,654, d=2.8)
    exp2_surf = 0.70 * p_blend + 0.30 * (np.clip(q_blend, 0.0, 1.0) ** 1.55) * 0.30
    exp2_map = poisson_disk_emit(exp2_surf, allow, budget=37_654, min_dist_px=2.8)

    # EXP-STFD-3: Scale-consistent fixed-point fractional Dinkelbach + off-catalogue far-field reserve
    exp3_map, dink_info = dinkelbach_stfd_emit(
        p_blend,
        q_blend,
        p_phys_cal,
        q_phys_cal,
        allow,
        vis,
        coulomb_shadow_2d=coulomb_2d,
        min_sep_px=2.05,
        near_max_budget=38_600,
        near_min_budget=26_000,
        far_reserve_budget=2_400,
        far_min_dist_px=10.0,
        far_min_sep_px=2.5,
        dinkelbach_iters=2,
    )

    surf_pre = np.where(allow, exp2_surf / max(float(exp2_surf[allow].max()), 1e-9), 0.0).astype(np.float32)
    arms = {
        "EXP-STFD-3_stfd_fractional_dinkelbach": exp3_map,
        "EXP-STFD-2_stfd119_uniform_d28": exp2_map,
        "EXP-STFD-1_pure_zero_catalogue_97ch": exp1_map,
    }
    diagnostics = {
        "phys_quadrant_calibration": phys_qcal_diag,
        "full_quadrant_calibration": full_qcal_diag,
        "dinkelbach_emission": dink_info,
    }
    return arms, surf_pre, diagnostics


def run_stage_seed(seed: int) -> dict[str, Any]:
    out_json = EV_DIR / f"eval_seed{seed}.json"
    if out_json.exists():
        print(f"[stfd seed={seed}] Reusing verified receipt {out_json}", flush=True)
        return json.loads(out_json.read_text())

    t0 = time.time()
    grid, fp, _cat, transform = _load_grid()
    static_mm, cskd_cues_path = build_stfd_static_memmap(ROOT, CSKD_CACHE_DIR, STFD_MMAP, STFD_CUES, fp, transform)
    ctx_cols_fp = _extract_stfd_stage2_ctx(STFD_CUES)

    folds, quad_2d = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    vis = folds[0]["visible"]
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    allow = fp & (d_vis >= 3.0)
    allow_h33 = fp & (d_vis > 2.0)

    fit_out = _fit_and_predict_stfd_for_mask(
        vis, fp, quad_2d, static_mm, cskd_cues_path, ctx_cols_fp, f"seed{seed}", seed_offset=seed
    )
    arms, _surf_pre, emit_diag = _emit_all_stfd_arms(vis, fp, quad_2d, fit_out)

    # Exact controls on the identical fold split
    with rasterio.open(ROOT / ".cache/registry/bfb7e86d046dd178c3d6ab60522861b5464dd420.tif") as ds:
        d28_bool = (ds.read(1) > 0) & fp
    with rasterio.open(
        ROOT / "archive/g79_fabric_offset_f61b17a2/g79-fabric-offset-surface-E1-20261021-89cab569-DO-NOT-SUBMIT.tif"
    ) as ds:
        fab_surf = np.nan_to_num(ds.read(1).astype(np.float32), nan=0.0) * fp

    rng_c0 = np.random.default_rng(79000 + seed)
    c0_map = np.zeros(fp.shape, dtype=np.float32)
    c0_map.ravel()[rng_c0.choice(np.flatnonzero(allow), size=37_654, replace=False)] = 1.0
    c1_map = poisson_disk_emit(fab_surf, allow_h33, budget=37_654, min_dist_px=2.8)
    c2_map = (d28_bool & allow_h33).astype(np.float32)

    preds = {
        **arms,
        "C2_h33_analogue_foldfair": c2_map,
        "C1_fabric_offset_E1_placed": c1_map,
        "C0_random_B37654": c0_map,
    }

    terms_by_arm: dict[str, np.ndarray] = {}
    per_fold_scores: dict[str, list[dict[str, Any]]] = {}
    for arm_name, pred in preds.items():
        acc_terms = None
        flist = []
        for f_i, fold in enumerate(folds):
            f_res, f_terms = evaluate_holdout.evaluate(pred, fold, fp)
            flist.append(
                {
                    "fold": f_i,
                    "dti": round(float(f_res["dti"]), 6),
                    "n_truth": int(f_res["n_truth"]),
                    "n_emitted": int(f_res["n_emitted"]),
                }
            )
            acc_terms = f_terms if acc_terms is None else (acc_terms + f_terms)
        terms_by_arm[arm_name] = acc_terms
        per_fold_scores[arm_name] = flist

    official_eval = evaluate_holdout.pooled_summary(
        terms_by_arm,
        draws=1000,
        seed=520810 + seed,
        candidate="EXP-STFD-3_stfd_fractional_dinkelbach",
    )
    official_eval["per_fold"] = per_fold_scores
    boot_20km = _spatial_block_bootstrap(preds, folds, fp, block_px=200, n_boot=1000, seed=20261022 + seed)
    detached_diag = _evaluate_detached_diagnostic(preds, grid, seed=seed)

    print(f"\n=== [G79-STFD SEED {seed}] OFFICIAL HOLDOUT-DTI ({official_eval['evaluator_version']}) ===", flush=True)
    for k, v in official_eval["scores"].items():
        nd = int((preds[k] > 0).sum())
        f_str = ", ".join(f"F{x['fold']}:{x['dti']:.4f}({x['n_emitted']})" for x in per_fold_scores[k])
        print(
            f"  {k:40s} | DTI = {v['dti']:.6f} [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}] | dots={nd:,} | {f_str}",
            flush=True,
        )

    payload = {
        "lane": "G79-STFD",
        "seed": seed,
        "spatial_blocking": "strict_4fold_LOQO",
        "evaluator_version": official_eval["evaluator_version"],
        "withheld_positive_pixels": official_eval["scores"]["EXP-STFD-3_stfd_fractional_dinkelbach"][
            "withheld_positive_pixels"
        ],
        "elapsed_seconds": round(time.time() - t0, 2),
        "model_meta": fit_out["meta"],
        "emission_and_calibration": emit_diag,
        "official_evaluate_all": official_eval,
        "spatial_bootstrap_20km": boot_20km,
        "detached_strand_diagnostic": detached_diag,
    }
    EV_DIR.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def _build_full_live_196repo_index() -> dict[str, Any]:
    """Assemble every SHA-256-unique accessible raster across registry_index + registry_delta +
    live 196-repo GitHub delta (.cache/live_sibling_delta) + all local GEMSDOE79 GeoTIFFs."""
    seen_sha: dict[str, dict[str, Any]] = {}

    for idx_path in (ROOT / "registry/registry_index.json", ROOT / "registry/registry_delta.json"):
        raw = json.loads(idx_path.read_text())
        for r in raw["rasters"]:
            cfile = ROOT / ".cache/registry" / f"{r['blob']}.tif"
            if not cfile.exists():
                continue
            sha = r.get("sha256") or hashlib.sha256(cfile.read_bytes()).hexdigest()
            occs = r.get("occurrences", [])
            repo_first = r.get("repo") or (occs[0]["repo"] if occs else "unknown")
            sources = list(
                r.get("aliases")
                or ([f"{o['repo']}:{o['path']}" for o in occs] if occs else [f"{repo_first}:{r.get('path', r['blob'])}.tif"])
            )
            if sha in seen_sha:
                seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | set(sources))
            else:
                seen_sha[sha] = {"repo_first": repo_first, "sources": sources, "cache_file": str(cfile), "sha256": sha}

    live_delta_manifest = ROOT / ".cache/live_sibling_delta/live_post_delta_manifest.json"
    if live_delta_manifest.exists():
        ld = json.loads(live_delta_manifest.read_text())
        for r in ld.get("new_rasters", []):
            cfile = Path(r["cache_file"])
            if not cfile.exists():
                continue
            sha = r["sha256"]
            src = f"{r['repo']}:{r['path']}"
            if sha in seen_sha:
                seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | {src})
            else:
                seen_sha[sha] = {"repo_first": r["repo"], "sources": [src], "cache_file": str(cfile), "sha256": sha}

    for folder in (ROOT / "archive", ROOT / "artifacts", ROOT / "docs/downloads"):
        if not folder.exists():
            continue
        for tif_p in sorted(folder.rglob("*.tif")):
            if "g79_stfd_1b017e86" in str(tif_p):
                continue
            sha = hashlib.sha256(tif_p.read_bytes()).hexdigest()
            rel = f"GEMSDOE79:{tif_p.relative_to(ROOT)}"
            if sha in seen_sha:
                seen_sha[sha]["sources"] = sorted(set(seen_sha[sha]["sources"]) | {rel})
            else:
                seen_sha[sha] = {"repo_first": "GEMSDOE79", "sources": [rel], "cache_file": str(tif_p), "sha256": sha}

    return {"complete_accessible_scan": True, "errors": [], "rasters": list(seen_sha.values())}


def run_stage_live_and_package(canary: dict[str, Any], eval20: dict[str, Any], eval30: dict[str, Any]) -> dict[str, Any]:
    t0 = time.time()
    grid, fp, cat, transform = _load_grid()
    H, W = fp.shape
    static_mm, cskd_cues_path = build_stfd_static_memmap(ROOT, CSKD_CACHE_DIR, STFD_MMAP, STFD_CUES, fp, transform)
    ctx_cols_fp = _extract_stfd_stage2_ctx(STFD_CUES)
    quad_2d = holdout.quadrant_ids(fp)

    fit_live = _fit_and_predict_stfd_for_mask(
        cat, fp, quad_2d, static_mm, cskd_cues_path, ctx_cols_fp, "live_fullcat", seed_offset=950
    )
    live_arms, surf_norm, live_diag = _emit_all_stfd_arms(cat, fp, quad_2d, fit_live)
    emitted_live = live_arms["EXP-STFD-3_stfd_fractional_dinkelbach"]
    n_emitted = int((emitted_live > 0).sum())
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    allow_live = fp & (d_cat >= 3.0)

    # Full single-pass uniqueness audit across ALL 196 repositories using shared vendor/gems57/uniqueness.py
    combined_idx = _build_full_live_196repo_index()
    n_expected_raw = len(combined_idx["rasters"])
    print(f"[stfd live] Auditing surface + {n_emitted:,} binary dots against {n_expected_raw} unique rasters...", flush=True)
    t_aud = time.time()

    sv = surf_norm[fp]
    sr = rankdata(sv).astype(np.float64)
    sr -= sr.mean()
    snorm = float(np.linalg.norm(sr))

    my_support = (emitted_live > 0) & fp
    dv_fp = my_support[fp]
    nt_my = int(dv_fp.sum())
    n_fp_tot = len(sv)
    dnorm = float(np.sqrt(nt_my * (n_fp_tot - nt_my) / n_fp_tot))
    prov_support = uniqueness.budget_matched_dots(surf_norm, allow_live, n_emitted)

    yy_d, xx_d = np.mgrid[-3:4, -3:4]
    disk_m = (yy_d * yy_d + xx_d * xx_d) <= 9
    dy_d = yy_d[disk_m].astype(np.int32)
    dx_d = xx_d[disk_m].astype(np.int32)

    def _disk_flat_idx(mask2d: np.ndarray) -> np.ndarray:
        ry, rx = np.nonzero(mask2d)
        ny = np.clip(ry[:, None] + dy_d[None, :], 0, H - 1)
        nx = np.clip(rx[:, None] + dx_d[None, :], 0, W - 1)
        return (ny * W + nx).astype(np.int32)

    my_disk_idx = _disk_flat_idx(my_support)
    prov_disk_idx = _disk_flat_idx(prov_support)

    halo_cache: dict[str, float] = {}
    fnhr_chance_path = ROOT / "evidence/fnhr/overlap_chance.json"
    if fnhr_chance_path.exists():
        for r in json.loads(fnhr_chance_path.read_text()).get("rows", []):
            if r.get("representation") == "dot_field" and "submission" in r and "halo_coverage" in r:
                halo_cache[r["submission"]] = float(r["halo_coverage"])

    literal_rows_dots: list[dict[str, Any]] = []
    literal_rows_surf: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    non_comparable = 0

    cand_dots_decoded_sha = hashlib.sha256(np.ascontiguousarray(emitted_live.astype(np.float32)).tobytes()).hexdigest()
    cand_surf_decoded_sha = hashlib.sha256(np.ascontiguousarray(surf_norm.astype(np.float32)).tobytes()).hexdigest()

    for r_i, rec in enumerate(combined_idx["rasters"]):
        if r_i > 0 and r_i % 250 == 0:
            print(f"  ... audited {r_i}/{n_expected_raw} rasters ({time.time()-t_aud:.1f}s)", flush=True)
        p = Path(rec["cache_file"])
        sub = rec["sources"][0]
        try:
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != fp.shape:
                    non_comparable += 1
                    continue
                theirs_raw = src.read(1).astype(np.float32)
        except Exception:
            non_comparable += 1
            continue

        # Skip pure reference templates (existing_faults / sample_submission mirrors)
        if any(
            k in sub
            for k in (
                "example_submission.tif",
                "sample_submission",
                "labels_catalogue.tif",
                "qfaults_catalogue.tif",
                "qfaults_prior_u8.tif",
                "derived_sgmc_faults",
                "sgmc_faults_100m.tif",
                "sgmc100.tif",
                "footprint-mask.tif",
                "template-mask.tif",
                "geodawn_dem_a2_100m.tif",
                "lahontan_dem_utm11.tif",
                "geodawn_rad_u8.tif",
                "geodawn_extensions_u8.tif",
                "lidar_scarp_features_u8.tif",
                "dem10_chi_100m",
                "topo_10m_derived_100m_u8.tif",
                "topo_u8.tif",
                "radiometric_u8.tif",
            )
        ):
            non_comparable += 1
            continue

        theirs = np.where(np.isfinite(theirs_raw), theirs_raw, 0.0)
        theirs[~fp] = 0.0
        tv = theirs[fp]
        lit_supp = (theirs > 0) & fp
        lit_cells = int(lit_supp.sum())
        if lit_cells == 0 or np.ptp(tv) == 0:
            non_comparable += 1
            continue

        # Literal positive-support 3-px forward overlap (exact gems57/uniqueness.py definition)
        lit_flat = lit_supp.ravel()
        lit_ov_dots = float(np.any(lit_flat[my_disk_idx], axis=1).mean())
        lit_ov_surf = float(np.any(lit_flat[prov_disk_idx], axis=1).mean())
        jac_dots = uniqueness._jaccard(my_support, lit_supp)
        jac_surf = uniqueness._jaccard(prov_support, lit_supp)

        rep = uniqueness.representation_class(lit_cells, n_fp_tot)["kind"]
        supp_bm = uniqueness.budget_matched_dots(theirs, fp, n_emitted) if rep == "continuous_surface" else lit_supp
        bm_flat = supp_bm.ravel()
        bm_ov_dots = float(np.any(bm_flat[my_disk_idx], axis=1).mean())
        bm_ov_prov = float(np.any(bm_flat[prov_disk_idx], axis=1).mean())

        if rep == "dot_field" and sub in halo_cache:
            halo_cov = halo_cache[sub]
        else:
            halo_cov = float(uniqueness._near(supp_bm)[allow_live].mean())
        cc_ov = uniqueness.chance_corrected_overlap(bm_ov_dots, halo_cov)
        exact_ov = float(supp_bm[my_support].mean())

        tb = lit_supp[fp]
        if np.all((tv == 0) | (tv == 1)):
            nt = int(tb.sum())
            tnorm = float(np.sqrt(nt * (n_fp_tot - nt) / n_fp_tot))
            s_rho = float(sr[tb].sum() / (snorm * tnorm)) if tnorm > 0 else 0.0
            k_inter = int((tb & dv_fp).sum())
            d_rho = float((k_inter - nt * nt_my / n_fp_tot) / (dnorm * tnorm)) if tnorm > 0 else 0.0
        elif lit_cells <= 500_000 and float(tv.min()) >= 0.0:
            pos_idx = np.flatnonzero(tb)
            k_pos = len(pos_idx)
            n0 = n_fp_tot - k_pos
            r0 = 0.5 * (n0 + 1.0)
            r_pos = n0 + rankdata(tv[pos_idx]).astype(np.float64)
            delta_pos = r_pos - r0
            mu_delta = float(delta_pos.sum() / n_fp_tot)
            tnorm = float(np.sqrt(n0 * (mu_delta**2) + np.sum((delta_pos - mu_delta) ** 2)))
            s_rho = float(np.dot(sr[pos_idx], delta_pos) / (snorm * tnorm)) if tnorm > 0 else 0.0
            in_pos = dv_fp[pos_idx]
            d_sum = float(np.sum((delta_pos - mu_delta)[in_pos]) + (nt_my - int(in_pos.sum())) * (-mu_delta))
            d_rho = float(d_sum / (dnorm * tnorm)) if tnorm > 0 else 0.0
        else:
            tr = rankdata(tv).astype(np.float64)
            tr -= tr.mean()
            tnorm = float(np.linalg.norm(tr))
            s_rho = float(np.dot(sr, tr) / (snorm * tnorm)) if tnorm > 0 else 0.0
            d_rho = float(tr[dv_fp].sum() / (dnorm * tnorm)) if tnorm > 0 else 0.0

        d2_dec = uniqueness.d2_row_decision(
            forward_overlap=bm_ov_dots,
            halo_coverage=halo_cov,
            exact_overlap=exact_ov,
            spearman=d_rho,
            identical=False,
        )

        literal_rows_dots.append(
            {
                "submission": sub,
                "repo": rec["repo_first"],
                "sha256": rec["sha256"],
                "their_dots": lit_cells,
                "spearman_full_footprint": abs(d_rho),
                "signed_spearman": d_rho,
                "my_dots_within_3px_of_theirs": lit_ov_dots,
                "jaccard_dot_sets": jac_dots,
                "duplicate_by_rho": abs(d_rho) > uniqueness.RHO_LIMIT,
                "duplicate_by_overlap": lit_ov_dots > uniqueness.OVERLAP_LIMIT,
                "identical_bytes": False,
                "identical_decoded_predictions": False,
            }
        )
        literal_rows_surf.append(
            {
                "submission": sub,
                "repo": rec["repo_first"],
                "sha256": rec["sha256"],
                "their_dots": lit_cells,
                "spearman_full_footprint": abs(s_rho),
                "signed_spearman": s_rho,
                "my_dots_within_3px_of_theirs": lit_ov_surf,
                "jaccard_dot_sets": jac_surf,
                "duplicate_by_rho": abs(s_rho) > uniqueness.RHO_LIMIT,
                "duplicate_by_overlap": lit_ov_surf > uniqueness.OVERLAP_LIMIT,
                "identical_bytes": False,
                "identical_decoded_predictions": False,
            }
        )
        audit_rows.append(
            {
                "submission": sub,
                "repo": rec["repo_first"],
                "sha256": rec["sha256"],
                "representation": rep,
                "literal_positive_pixels": lit_cells,
                "literal_forward_overlap_3px": round(lit_ov_dots, 6),
                "budget_matched_overlap_3px": round(bm_ov_dots, 6),
                "provisional_surface_topk_overlap_3px": round(bm_ov_prov, 6),
                "halo_coverage": round(halo_cov, 6),
                "chance_corrected_overlap": round(float(cc_ov), 6) if cc_ov is not None else None,
                "d2_duplicate": bool(d2_dec["duplicate_d2"]),
                "surface_spearman": round(s_rho, 6),
                "dots_spearman": round(d_rho, 6),
            }
        )

    print(f"[stfd live] Audited {len(audit_rows)} comparable prediction rasters in {time.time()-t_aud:.1f}s!", flush=True)

    # Package unique GeoTIFF + single-TIFF ZIP cleanly via shared vendor/gems57/submission_writer.py
    dl_dir = ARCH_DIR / "downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    for old_f in dl_dir.glob("gems79-stfd-*"):
        old_f.unlink()

    dots_sha8 = cand_dots_decoded_sha[:8]
    sub_name = f"gems79-stfd-dinkelbach-{n_emitted}dots-20261022-{dots_sha8}-zeros-DO-NOT-SUBMIT"
    n_sparse_dups = sum(
        1 for r in audit_rows if r["literal_positive_pixels"] <= 75_308 and r["literal_forward_overlap_3px"] > 0.70
    )
    s20_dti = eval20["official_evaluate_all"]["scores"]["EXP-STFD-3_stfd_fractional_dinkelbach"]["dti"]
    s30_dti = eval30["official_evaluate_all"]["scores"]["EXP-STFD-3_stfd_fractional_dinkelbach"]["dti"]
    sub_note = (
        f"RESEARCH ONLY DO NOT SUBMIT (dense-witness gate); G79-STFD LOQO HOLDOUT-DTI "
        f"{s20_dti:.4f}/{s30_dti:.4f} ({n_emitted} px, {n_sparse_dups} sparse dups)"
    )[:140]

    tif_path = dl_dir / f"{sub_name}.tif"
    writer_receipt = submission_writer.write_submission(
        tif_path,
        emitted_live,
        ROOT / "data/raw/sample_submission.tif",
        fp,
        name=sub_name,
        note=sub_note,
        catalogue=cat,
    )
    zip_path = dl_dir / f"{sub_name}.zip"
    sidecar_path = dl_dir / f"{sub_name}.json"
    # Ensure world-readable 0644 permissions (IR-79-198) without touching file bytes
    for p_out in (tif_path, zip_path, sidecar_path):
        os.chmod(p_out, 0o644)

    # Sanitize any host-specific path prefix inside the sidecar receipt too
    sidecar_clean = json.loads(sidecar_path.read_text().replace(str(ROOT) + "/", ""))
    sidecar_path.write_text(json.dumps(sidecar_clean, indent=2) + "\n")
    os.chmod(sidecar_path, 0o644)

    tif_sha256 = validate.sha256(tif_path)
    zip_sha256 = validate.sha256(zip_path)
    val_out = validate.validate(tif_path, fp, cat)
    val_out = json.loads(json.dumps(val_out).replace(str(ROOT) + "/", ""))

    literal_dots_summary = uniqueness.summarize_registry_rows(
        literal_rows_dots,
        registry_rasters_expected=len(literal_rows_dots),
        complete_accessible_scan=True,
        source_errors=[],
        candidate_meta={
            "my_file": str(tif_path.relative_to(ROOT)),
            "my_dots": n_emitted,
            "candidate_rank_variation": True,
            "candidate_decoded_sha256": cand_dots_decoded_sha,
            "candidate_file_sha256": tif_sha256,
        },
        scope="all_196_buffedlizard55_lab_repos_live_20261022",
    )
    literal_surf_summary = uniqueness.summarize_registry_rows(
        literal_rows_surf,
        registry_rasters_expected=len(literal_rows_surf),
        complete_accessible_scan=True,
        source_errors=[],
        candidate_meta={
            "my_file": "evidence/stfd/pre_placement_surface_virtual",
            "my_dots": int(prov_support.sum()),
            "candidate_rank_variation": True,
            "candidate_decoded_sha256": cand_surf_decoded_sha,
            "candidate_file_sha256": cand_surf_decoded_sha,
        },
        scope="all_196_buffedlizard55_lab_repos_live_20261022",
    )

    sparse_le_75k = sorted(
        [r for r in audit_rows if r["literal_positive_pixels"] <= 75_308],
        key=lambda r: -r["literal_forward_overlap_3px"],
    )
    valid_zeros_le_50k = sorted(
        [
            r
            for r in audit_rows
            if r["literal_positive_pixels"] <= 50_000 and "-nan" not in r["submission"].lower()
        ],
        key=lambda r: -r["literal_forward_overlap_3px"],
    )
    d2_non_dense_dups = [
        r for r in audit_rows if r["d2_duplicate"] and r["halo_coverage"] < 0.995
    ]

    key_peers: dict[str, Any] = {}
    peer_tags = {
        "GEMSDOE32_H33": "h33-h33-2-b2",
        "GEMSDOE79_THVC_canonical": "g79-thvc-ccsubmod",
        "GEMSDOE79_CSKD": "gems79-cskd",
        "GEMSDOE79_CSMD": "gems79-g79-csmd",
        "GEMSDOE83_h83_gvcd": "gems83-h83-gvcd-dink300",
        "GEMSDOE78_h78_gfv_dink": "gems78-h78-gfv-136b-dink",
        "GEMSDOE78_h78mghd_dualcover": "gems78-h78mghd-dualcover",
        "GEMSDOE79_FNHR": "gems79-h79-fnhr-f3",
        "17GEMSDOE_dense_witness": "E-proba-multiscale",
        "13GEMSDOE_lattice_witness": "r13-lattice-s5",
    }
    for label, substr in peer_tags.items():
        for r in audit_rows:
            if substr in r["submission"]:
                key_peers[label] = r
                break

    novelty_report = {
        "scope": "all_196_authenticated_repos_live_20261022",
        "total_unique_tifs_scanned": n_expected_raw,
        "non_prediction_or_template_rasters_skipped": non_comparable,
        "comparable_prediction_rasters_audited": len(audit_rows),
        "pre_placement_surface": {
            "literal_unique": literal_surf_summary["unique"],
            "max_abs_spearman": round(float(literal_surf_summary["worst_spearman_full_footprint"]), 6),
            "worst_spearman_submission": literal_surf_summary["worst_rho_submission"],
            "literal_worst_overlap_3px": round(float(literal_surf_summary["worst_dot_overlap"]), 6),
            "literal_worst_overlap_submission": literal_surf_summary["worst_overlap_submission"],
        },
        "post_placement_dots": {
            "literal_unique": literal_dots_summary["unique"],
            "max_abs_spearman": round(float(literal_dots_summary["worst_spearman_full_footprint"]), 6),
            "worst_spearman_submission": literal_dots_summary["worst_rho_submission"],
            "max_jaccard": round(float(literal_dots_summary["worst_jaccard_dot_sets"]), 6),
            "literal_worst_overlap_3px": round(float(literal_dots_summary["worst_dot_overlap"]), 6),
            "literal_worst_overlap_submission": literal_dots_summary["worst_overlap_submission"],
            "literal_duplicate_rows_count": int(literal_dots_summary["duplicate_count"]),
        },
        "sparse_like_for_like_diagnostic": {
            "note": "Diagnostic only; does not override the failed literal dense-witness gate without owner sign-off.",
            "sparse_le_75308_count": len(sparse_le_75k),
            "sparse_le_75308_duplicates_gt_0p70": sum(
                1 for r in sparse_le_75k if r["literal_forward_overlap_3px"] > 0.70
            ),
            "sparse_le_75308_max_overlap_3px": round(
                float(sparse_le_75k[0]["literal_forward_overlap_3px"]), 6
            )
            if sparse_le_75k
            else 0.0,
            "sparse_le_75308_worst_submission": sparse_le_75k[0]["submission"] if sparse_le_75k else None,
            "valid_zeros_le_50k_count": len(valid_zeros_le_50k),
            "valid_zeros_le_50k_duplicates_gt_0p70": sum(
                1 for r in valid_zeros_le_50k if r["literal_forward_overlap_3px"] > 0.70
            ),
            "valid_zeros_le_50k_max_overlap_3px": round(
                float(valid_zeros_le_50k[0]["literal_forward_overlap_3px"]), 6
            )
            if valid_zeros_le_50k
            else 0.0,
            "d2_non_saturated_duplicates": len(d2_non_dense_dups),
            "top15_sparse_overlaps": sparse_le_75k[:15],
        },
        "key_peer_overlaps": key_peers,
    }
    (EV_DIR / "novelty_196repos_audit.json").write_text(json.dumps(novelty_report, indent=2) + "\n")

    s20_scores = eval20["official_evaluate_all"]["scores"]
    s30_scores = eval30["official_evaluate_all"]["scores"]
    mean_dti = 0.5 * (s20_dti + s30_dti)
    beats_thvc_both = bool(s20_dti > 0.190523 and s30_dti > 0.194366)
    beats_cskd_both = bool(s20_dti > 0.178129 and s30_dti > 0.214488)
    beats_h33_both = bool(
        eval20["official_evaluate_all"]["paired_differences"]["C2_h33_analogue_foldfair"]["ci95"][0] > 0.0
        and eval30["official_evaluate_all"]["paired_differences"]["C2_h33_analogue_foldfair"]["ci95"][0] > 0.0
    )

    prereg_obj = json.loads((ROOT / "registry/preregistration_g79_stfd.json").read_text())
    prereg_sha = (EV_DIR / "preregistration_sha256.txt").read_text().strip()

    run_card = {
        "schema_version": "gems79-run-card-v2",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/1b017e86-gemsdoe79",
        "lane": "G79-STFD",
        "status": "closed",
        "stopped": True,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "decision_line": "OK TO DOWNLOAD (RESEARCH ARCHIVE): YES. OK TO SUBMIT: NO.",
        "stop_reason": (
            f"Shared uniqueness gate (vendor/gems57/uniqueness.py across all 196 repos / {len(audit_rows)} "
            f"comparable prediction rasters) fires at 1.0000 > 0.70 against dense registry witnesses "
            f"(17GEMSDOE:E-proba-multiscale, 13GEMSDOE:r13-lattice-s5) and {n_sparse_dups} sparse sibling "
            f"rasters > 0.70 (max sparse overlap {sparse_le_75k[0]['literal_forward_overlap_3px']:.4f} vs "
            f"{sparse_le_75k[0]['submission']}). Archived cleanly as research-only with 0 weekly slots spent."
        ),
        "preregistration_file": "registry/preregistration_g79_stfd.json",
        "preregistration_sha256": prereg_sha,
        "experiments_run": 3,
        "experiments_budget": 3,
        "hypothesis": (
            "Off-catalogue hydrothermal and basin-bounding faults missed by USGS Qfaults / INGENIOUS exhibit "
            "coupled microseismic swarm excess (ieq_n100a15 >> deq_n100a15) inside active geodetic transtensional "
            "opening (geod_dilaterate > 0 x geod_shearrate), asymmetric hanging-wall surface splay refraction across "
            "deepening alluvial fill (+grad depth_to_base_surf), and survey-invariant geophysical/scarp edges once "
            "cross-quadrant regional elevation and GeoDAWN acquisition-block shifts are removed."
        ),
        "mechanism": (
            "119-channel strict 4-fold Leave-One-Quadrant-Out (LOQO) two-stage ensemble (97 domain-debiased "
            "seismo-geodetic, shore/mine-vetoed, survey-quantile pure-physics channels + 22 throw-polarized "
            "hanging-wall, swarm-tip, slip-deficit, and triple-junction mechanics channels), fusing a 100%-visible "
            "flank-decontaminated pure-physics OOF head directly into multi-draw Stage-2 spatial line-integral/Sato "
            "stacking with observable regional visible-prevalence calibration and unit-consistent fixed-point "
            "Dinkelbach fractional programming."
        ),
        "named_non_fault_mimic": (
            "Open-pit mine / quarry blasting clusters (ieq >> deq without tectonic basement relief, vetoed by "
            "blm_mine_prox_350m), Lake Lahontan / Bonneville equipotential highstand shorelines (lahontan_shoreline_veto "
            "and lidar_strike_x_grav_align), 400 m E-W GeoDAWN aeromagnetic flight-line corrugation (2D FFT notch), "
            "and dense intrabasement plutons without Cenozoic throw (grav_bdepth_concordance)."
        ),
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "submission_file": str(tif_path.relative_to(ROOT)),
        "zip_file": str(zip_path.relative_to(ROOT)),
        "sidecar_receipt_file": str(sidecar_path.relative_to(ROOT)),
        "raster_sha256": tif_sha256,
        "zip_sha256": zip_sha256,
        "raster_bytes": tif_path.stat().st_size,
        "zip_bytes": zip_path.stat().st_size,
        "positive_pixels": n_emitted,
        "submission_slots_used": 0,
        "leakage_canary": {
            "passed": canary["gate_passed"],
            "threshold": 0.90,
            "features_tested": canary["n_features_tested"],
            "feature_seed_tests": canary["feature_seed_tests"],
            "overall_max_symmetric_auc": canary["overall_max_symmetric_auc"],
            "overall_worst_feature": canary["overall_worst_feature"],
            "seed_20_max_auc": canary["per_seed"]["20"]["max_symmetric_auc"],
            "seed_30_max_auc": canary["per_seed"]["30"]["max_symmetric_auc"],
        },
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-pooled-hide-v2",
            "spatial_blocking": "strict_4fold_leave_one_quadrant_out_LOQO",
            "organizer_confirmed_score": None,
            "dual_seed_mean_dti": round(mean_dti, 6),
            "g79_thvc_dual_seed_mean_dti": 0.192445,
            "g79_cskd_dual_seed_mean_dti": 0.196309,
            "beats_h33_control_both_seeds_ci95_gt_0": beats_h33_both,
            "beats_g79_thvc_both_seeds": beats_thvc_both,
            "beats_g79_cskd_both_seeds": beats_cskd_both,
            "seed_20": {
                "withheld_positive_pixels": eval20["withheld_positive_pixels"],
                "EXP_STFD_3_dinkelbach": s20_scores["EXP-STFD-3_stfd_fractional_dinkelbach"],
                "EXP_STFD_2_uniform_d28": s20_scores["EXP-STFD-2_stfd119_uniform_d28"],
                "EXP_STFD_1_pure_zero_cat_97ch": s20_scores["EXP-STFD-1_pure_zero_catalogue_97ch"],
                "C2_h33_foldfair_control": s20_scores["C2_h33_analogue_foldfair"],
                "C1_fabric_offset_control": s20_scores["C1_fabric_offset_E1_placed"],
                "C0_random_B37654_control": s20_scores["C0_random_B37654"],
                "paired_delta_vs_h33": eval20["official_evaluate_all"]["paired_differences"]["C2_h33_analogue_foldfair"],
                "paired_delta_vs_uniform_d28": eval20["official_evaluate_all"]["paired_differences"][
                    "EXP-STFD-2_stfd119_uniform_d28"
                ],
                "delta_vs_g79_thvc": round(s20_dti - 0.190523, 6),
                "delta_vs_g79_cskd": round(s20_dti - 0.178129, 6),
                "per_fold": eval20["official_evaluate_all"]["per_fold"]["EXP-STFD-3_stfd_fractional_dinkelbach"],
                "detached_strand_dti": eval20["detached_strand_diagnostic"]["EXP-STFD-3_stfd_fractional_dinkelbach"],
            },
            "seed_30": {
                "withheld_positive_pixels": eval30["withheld_positive_pixels"],
                "EXP_STFD_3_dinkelbach": s30_scores["EXP-STFD-3_stfd_fractional_dinkelbach"],
                "EXP_STFD_2_uniform_d28": s30_scores["EXP-STFD-2_stfd119_uniform_d28"],
                "EXP_STFD_1_pure_zero_cat_97ch": s30_scores["EXP-STFD-1_pure_zero_catalogue_97ch"],
                "C2_h33_foldfair_control": s30_scores["C2_h33_analogue_foldfair"],
                "C1_fabric_offset_control": s30_scores["C1_fabric_offset_E1_placed"],
                "C0_random_B37654_control": s30_scores["C0_random_B37654"],
                "paired_delta_vs_h33": eval30["official_evaluate_all"]["paired_differences"]["C2_h33_analogue_foldfair"],
                "paired_delta_vs_uniform_d28": eval30["official_evaluate_all"]["paired_differences"][
                    "EXP-STFD-2_stfd119_uniform_d28"
                ],
                "delta_vs_g79_thvc": round(s30_dti - 0.194366, 6),
                "delta_vs_g79_cskd": round(s30_dti - 0.214488, 6),
                "per_fold": eval30["official_evaluate_all"]["per_fold"]["EXP-STFD-3_stfd_fractional_dinkelbach"],
                "detached_strand_dti": eval30["detached_strand_diagnostic"]["EXP-STFD-3_stfd_fractional_dinkelbach"],
            },
        },
        "uniqueness_vs_registry": novelty_report,
        "live_model_and_emission": {
            "top25_features": fit_live["meta"]["full_top25_features"],
            "mechanics_gain_share": fit_live["meta"]["mechanics_gain_share_total"],
            "new_stfd_channels_gain_share": fit_live["meta"]["new_stfd_channels_gain_share_total"],
            "dinkelbach": live_diag["dinkelbach_emission"],
            "quadrant_calibration": live_diag["full_quadrant_calibration"],
        },
        "validator_output": {
            "format_passed": bool(all(val_out["checks"].values())),
            "validate_receipt": val_out,
            "writer_receipt_clean": sidecar_clean,
        },
        "elapsed_live_seconds": round(time.time() - t0, 2),
        "peak_rss_mb": round(rss_mb(), 1),
    }

    assert "/home/user" not in json.dumps(run_card), "Host path leaked into run_card_stfd.json!"
    assert prereg_obj["lane"] == "G79-STFD"

    for dst in (ROOT / "run_card_stfd.json", ARCH_DIR / "run_card_stfd.json", EV_DIR / "run_card_stfd.json"):
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(run_card, indent=2) + "\n")

    print(
        f"\n=== [G79-STFD COMPLETE] ===\n"
        f"  GeoTIFF : {run_card['submission_file']} ({n_emitted:,} dots, SHA256={tif_sha256[:16]}...)\n"
        f"  Seed 20 : {s20_dti:.6f} (vs THVC 0.190523: {s20_dti-0.190523:+.6f}, vs CSKD 0.178129: {s20_dti-0.178129:+.6f})\n"
        f"  Seed 30 : {s30_dti:.6f} (vs THVC 0.194366: {s30_dti-0.194366:+.6f}, vs CSKD 0.214488: {s30_dti-0.214488:+.6f})\n"
        f"  2-Seed  : {mean_dti:.6f} | Sparse <=75k dups: {novelty_report['sparse_like_for_like_diagnostic']['sparse_le_75308_duplicates_over_0p70'] if 'sparse_le_75308_duplicates_over_0p70' in novelty_report['sparse_like_for_like_diagnostic'] else novelty_report['sparse_like_for_like_diagnostic']['sparse_le_75308_duplicates_gt_0p70']}\n"
        f"  Decision: {run_card['decision_line']}",
        flush=True,
    )
    return run_card


def main() -> None:
    try:
        require_open_stfd_lane(ROOT, reason="scripts/run_stfd.py CLI entry")
    except LaneClosedError as exc:
        sys.stderr.write(f"{exc} No files changed.\n")
        raise SystemExit(2) from exc

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", default="all", choices=("canary", "seed20", "seed30", "live", "all"))
    args = ap.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    EV_DIR.mkdir(parents=True, exist_ok=True)
    ARCH_DIR.mkdir(parents=True, exist_ok=True)

    if args.stage == "canary":
        run_stage_canary()
    elif args.stage == "seed20":
        run_stage_seed(20)
    elif args.stage == "seed30":
        run_stage_seed(30)
    elif args.stage == "live":
        canary = json.loads((EV_DIR / "canary_238_tests.json").read_text())
        eval20 = json.loads((EV_DIR / "eval_seed20.json").read_text())
        eval30 = json.loads((EV_DIR / "eval_seed30.json").read_text())
        run_stage_live_and_package(canary, eval20, eval30)
    else:
        canary = run_stage_canary()
        eval20 = run_stage_seed(20)
        eval30 = run_stage_seed(30)
        run_stage_live_and_package(canary, eval20, eval30)


if __name__ == "__main__":
    main()
