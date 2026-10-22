#!/usr/bin/env python3
"""Execute preregistered H79-FNHR holdout (seeds 20, 30) and full-catalogue build.

Runs the exact 3-experiment regime schedule (F1, F2, F3) preregistered in
``registry/preregistration_fnhr.json`` (SHA-256 locked in
``evidence/fnhr/preregistration_sha256.txt`` before execution) using:
- ``src/gems79/fnhr.py`` (zero registry access, decontaminated nested target +
  out-of-quadrant pure-physics head, 68 physical/geothermal/scarp features)
- ``vendor/gems57/holdout.py::buffered_component_draw``
- ``vendor/gems57/evaluate_holdout.py`` (``gems57-pooled-hide-v2``, 1,000 paired
  20 km physical-block bootstrap draws)
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

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout as evaluator  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw, quadrant_ids  # noqa: E402
from gems79 import fnhr, nhr  # noqa: E402
from gems79.placement import place  # noqa: E402
import analyze_h33  # noqa: E402

BUDGET = 37_654
OUT = ROOT / "evidence" / "fnhr"
CACHE = ROOT / ".cache" / "fnhr"

EXPERIMENTS: dict[str, tuple[float, ...]] = {
    "F1": (0.13, 0.17, 0.21, 0.29, 0.20),
    "F2": (0.16, 0.24, 0.24, 0.22, 0.14),
    "F3": (0.20, 0.28, 0.24, 0.18, 0.10),
}


def log(*msg) -> None:
    print(f"[{time.strftime('%H:%M:%S')}]", *msg, flush=True)


def verify_prereg_lock() -> str:
    prereg_path = ROOT / "registry" / "preregistration_fnhr.json"
    lock_path = OUT / "preregistration_sha256.txt"
    actual = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    expected = lock_path.read_text().strip()
    if actual != expected:
        raise RuntimeError(f"Preregistration lock mismatch: {actual} != {expected}")
    return actual


def fit_hgb(X: np.ndarray, y: np.ndarray, seed: int) -> HistGradientBoostingRegressor:
    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.07,
        max_iter=260,
        max_leaf_nodes=63,
        min_samples_leaf=180,
        l2_regularization=1.5,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=15,
        random_state=seed,
    )
    model.fit(X, y)
    return model


def predict_grid(
    model: HistGradientBoostingRegressor,
    phys_fp: np.ndarray,
    fp: np.ndarray,
    fp_idx: np.ndarray,
    active_mask: np.ndarray,
    geom_dict: dict[str, np.ndarray] | None,
) -> np.ndarray:
    fp_lookup = np.full(fp.shape, -1, dtype=np.int32)
    fp_lookup.ravel()[fp_idx] = np.arange(fp_idx.size, dtype=np.int32)
    sel = np.flatnonzero(active_mask & fp)
    out = np.zeros(fp.shape, dtype=np.float32)
    chunk = 250_000
    for i in range(0, sel.size, chunk):
        s = sel[i : i + chunk]
        rows = fp_lookup.ravel()[s]
        X = phys_fp[rows].astype(np.float32)
        if geom_dict is not None:
            g = np.column_stack([geom_dict[name].ravel()[s] for name in nhr.GEOMETRY_NAMES]).astype(np.float32)
            X = np.hstack([X, g])
        out.ravel()[s] = np.clip(model.predict(X), 0.0, 1.0).astype(np.float32)
    return out


def compute_canaries(
    phys_fp: np.ndarray,
    phys_names: list[str],
    geom_vis: dict[str, np.ndarray],
    fp: np.ndarray,
    fp_idx: np.ndarray,
    folds: list[dict],
    seed: int,
) -> dict:
    fp_lookup = np.full(fp.shape, -1, dtype=np.int32)
    fp_lookup.ravel()[fp_idx] = np.arange(fp_idx.size, dtype=np.int32)
    rng = np.random.default_rng(79_500 + seed)
    rows = []
    for fold in folds:
        active = fold["region"] & fp & ~fold["masked_known"]
        truth = active & fold["truth"]
        pos_flat = np.flatnonzero(truth)
        neg_pool = np.flatnonzero(active & ~truth)
        neg_flat = neg_pool[rng.choice(neg_pool.size, size=min(60_000, neg_pool.size), replace=False)]
        sel = np.concatenate([pos_flat, neg_flat])
        y = np.concatenate([np.ones(pos_flat.size, np.int8), np.zeros(neg_flat.size, np.int8)])
        fp_rows = fp_lookup.ravel()[sel]

        p_sub = phys_fp[fp_rows].astype(np.float32)
        for j, fname in enumerate(phys_names):
            v = p_sub[:, j]
            ok = np.isfinite(v)
            if ok.sum() < 50 or y[ok].sum() < 5 or (1 - y[ok]).sum() < 5 or np.ptp(v[ok]) == 0:
                auc = 0.5
            else:
                auc = float(roc_auc_score(y[ok], v[ok]))
            sym = max(auc, 1.0 - auc)
            rows.append({
                "fold": fold["name"],
                "feature": fname,
                "auc": round(auc, 6),
                "symmetric_auc": round(sym, 6),
                "suspicious": bool(sym > 0.90),
            })

        for gname in nhr.GEOMETRY_NAMES:
            v = geom_vis[gname].ravel()[sel].astype(np.float32)
            ok = np.isfinite(v)
            if ok.sum() < 50 or y[ok].sum() < 5 or (1 - y[ok]).sum() < 5 or np.ptp(v[ok]) == 0:
                auc = 0.5
            else:
                auc = float(roc_auc_score(y[ok], v[ok]))
            sym = max(auc, 1.0 - auc)
            rows.append({
                "fold": fold["name"],
                "feature": f"geom_{gname}",
                "auc": round(auc, 6),
                "symmetric_auc": round(sym, 6),
                "suspicious": bool(sym > 0.90),
            })

    worst = max(rows, key=lambda r: r["symmetric_auc"])
    per_feat = {}
    for r in rows:
        per_feat[r["feature"]] = max(per_feat.get(r["feature"], 0.0), r["symmetric_auc"])
    return {
        "evidence_class": "LEAKAGE-CANARY",
        "seed": seed,
        "tests": len(rows),
        "n_unique_features": len(per_feat),
        "threshold": 0.90,
        "max_symmetric_auc": worst["symmetric_auc"],
        "worst": worst,
        "n_suspicious": int(sum(r["suspicious"] for r in rows)),
        "per_feature_max": per_feat,
    }


def stage_holdout(seed: int) -> None:
    t0 = time.time()
    prereg_sha = verify_prereg_lock()
    grid = load_grid(ROOT / "data/reference")
    fp = grid.footprint
    fp_idx = np.flatnonzero(fp)

    log(f"seed {seed}: building/loading physics stack")
    phys_fp, phys_names, phys_meta = fnhr.build_physics_stack(fp)
    lidar_strike, lidar_coh = nhr.read_lidar_orientation(fp)

    folds, quad = buffered_component_draw(grid, seed=seed)
    visible = folds[0]["visible"]
    geom_vis = nhr.geometry_features(visible, fp, lidar_strike, lidar_coh)

    log(f"seed {seed}: computing single-feature leakage canaries ({len(phys_names) + len(nhr.GEOMETRY_NAMES)} features x 4 folds)")
    canary = compute_canaries(phys_fp, phys_names, geom_vis, fp, fp_idx, folds, seed)
    log(f"seed {seed}: max canary symmetric AUC = {canary['max_symmetric_auc']:.4f} ({canary['worst']['feature']})")
    if canary["n_suspicious"] > 0:
        raise RuntimeError(f"Leakage canary breached on seed {seed}: {canary['worst']}")

    # Controls loaded exclusively for fold-fair benchmark comparison
    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & fp
    del d28
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)

    terms_by_arm: dict[str, np.ndarray] = {}
    fold_receipts = []

    for fold in folds:
        q = fold["fold"]
        train_region = fp & (quad != q) & (quad >= 0)

        log(f"seed {seed} fold {fold['name']}: building decontaminated nested rows")
        X_nest, y_nest, rec_nest = fnhr.decontaminated_nested_rows(
            phys_fp, fp, fp_idx, lidar_strike, lidar_coh, visible, train_region, seed * 100 + q
        )
        m_nest = fit_hgb(X_nest, y_nest, seed * 100 + q)
        del X_nest, y_nest
        gc.collect()

        log(f"seed {seed} fold {fold['name']}: building pure-physics full-visible rows")
        X_phys, y_phys, rec_phys = fnhr.physics_rows(
            phys_fp, fp, fp_idx, visible, train_region, seed * 1000 + q
        )
        m_phys = fit_hgb(X_phys, y_phys, seed * 1000 + q)
        del X_phys, y_phys
        gc.collect()

        region = fold["region"]
        allowed = region & fp & ~fold["masked_known"]
        s_nest = predict_grid(m_nest, phys_fp, fp, fp_idx, allowed, geom_vis)
        s_phys = predict_grid(m_phys, phys_fp, fp, fp_idx, allowed, None)
        dist_vis = ndi.distance_transform_edt(~fold["visible"]).astype(np.float32)
        s_blend = fnhr.blend_dual_heads(s_nest, s_phys, dist_vis, allowed)

        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = (sy, sx)
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        fold_budget = int(round(BUDGET * region.sum() / fp.sum()))

        arm_stats = {}
        for exp_id, quotas in EXPERIMENTS.items():
            _, dots_sub, st = fnhr.build_regime_surface_and_dots(
                s_blend[sl], dist_vis[sl], allowed[sl], quotas=quotas, budget=fold_budget, spacing=3
            )
            _, bt = evaluator.evaluate(
                dots_sub.astype(np.float32), local, fp[sl], origin=(sy.start, sx.start), global_shape=grid.shape
            )
            terms_by_arm[exp_id] = terms_by_arm.get(exp_id, 0) + bt
            arm_stats[exp_id] = st

        # Pure-physics control (no catalogue geometry features at all)
        dots_phys, _ = place(s_phys[sl], allowed[sl], fold_budget)
        _, bt_phys = evaluator.evaluate(
            dots_phys.astype(np.float32), local, fp[sl], origin=(sy.start, sx.start), global_shape=grid.shape
        )
        terms_by_arm["ablation_no_geometry"] = terms_by_arm.get("ablation_no_geometry", 0) + bt_phys

        # Unstratified decontaminated blend diagnostic
        dots_raw, _ = place(s_blend[sl], allowed[sl], fold_budget)
        _, bt_raw = evaluator.evaluate(
            dots_raw.astype(np.float32), local, fp[sl], origin=(sy.start, sx.start), global_shape=grid.shape
        )
        terms_by_arm["unstratified_decontaminated_ref"] = terms_by_arm.get("unstratified_decontaminated_ref", 0) + bt_raw

        # Uniform random control
        dots_uni, _ = place(rng_surface[sl], allowed[sl], fold_budget)
        _, bt_uni = evaluator.evaluate(
            dots_uni.astype(np.float32), local, fp[sl], origin=(sy.start, sx.start), global_shape=grid.shape
        )
        terms_by_arm["uniform_control"] = terms_by_arm.get("uniform_control", 0) + bt_uni

        # Fold-fair H33 control
        h33_ff = (d28_pos[sl] & region[sl] & (dist_vis[sl] > 2.0)).astype(np.float32)
        _, bt_h33 = evaluator.evaluate(
            h33_ff, local, fp[sl], origin=(sy.start, sx.start), global_shape=grid.shape
        )
        terms_by_arm["h33_foldfair_control"] = terms_by_arm.get("h33_foldfair_control", 0) + bt_h33

        fold_receipts.append({
            "fold": fold["name"],
            "budget": fold_budget,
            "withheld_truth": int((fold["truth"] & region).sum()),
            "nested": rec_nest,
            "physics_head": rec_phys,
            "arm_placement": arm_stats,
        })
        del m_nest, m_phys, s_nest, s_phys, s_blend, dist_vis
        gc.collect()

    OUT.mkdir(parents=True, exist_ok=True)
    runtime_s = round(time.time() - t0, 1)
    all_feature_names = phys_names + [f"geom_{g}" for g in nhr.GEOMETRY_NAMES]

    for exp_id in EXPERIMENTS:
        sub_terms = {
            "candidate": terms_by_arm[exp_id],
            "h33_foldfair_control": terms_by_arm["h33_foldfair_control"],
            "ablation_no_geometry": terms_by_arm["ablation_no_geometry"],
            "uniform_control": terms_by_arm["uniform_control"],
        }
        summary = evaluator.pooled_summary(sub_terms, candidate="candidate", draws=1000, seed=7900 + seed)
        payload = {
            "schema_version": 1,
            "lane": "H79-FNHR",
            "experiment": exp_id,
            "quotas": list(EXPERIMENTS[exp_id]),
            "seed": seed,
            "preregistration_sha256": prereg_sha,
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluator.VERSION,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "runtime_s": runtime_s,
            "leakage_canary": canary,
            "holdout": summary,
            "folds": fold_receipts,
            "h33_control_source": d28src,
            "feature_names": all_feature_names,
            "static_stack_inputs": phys_meta["inputs_sha256"],
        }
        out_file = OUT / f"{exp_id.lower()}_holdout_seed{seed}.json"
        out_file.write_text(json.dumps(payload, indent=2, default=float) + "\n")
        sc = summary["scores"]
        diff_h33 = summary["paired_differences"]["h33_foldfair_control"]
        log(
            f"seed {seed} {exp_id}: DTI={sc['candidate']['dti']:.4f} CI95={[round(x, 4) for x in sc['candidate']['ci95']]} "
            f"| H33={sc['h33_foldfair_control']['dti']:.4f} | delta_H33={diff_h33['delta']:+.4f} CI95={[round(x, 4) for x in diff_h33['ci95']]} "
            f"| phys_only={sc['ablation_no_geometry']['dti']:.4f}"
        )


def stage_final() -> None:
    t0 = time.time()
    prereg_sha = verify_prereg_lock()
    grid = load_grid(ROOT / "data/reference")
    fp = grid.footprint
    fp_idx = np.flatnonzero(fp)
    cat = grid.catalogue
    allowed = fp & ~cat

    phys_fp, phys_names, phys_meta = fnhr.build_physics_stack(fp)
    lidar_strike, lidar_coh = nhr.read_lidar_orientation(fp)

    # 1. Decontaminated nested head over full catalogue
    log("final: fitting decontaminated nested head")
    X_nest, y_nest, rec_nest = fnhr.decontaminated_nested_rows(
        phys_fp, fp, fp_idx, lidar_strike, lidar_coh, cat, fp, seed=790_501, n_rep=3, neg_per_rep=90_000
    )
    m_nest = fit_hgb(X_nest, y_nest, seed=790_501)
    del X_nest, y_nest
    gc.collect()

    geom_full = nhr.geometry_features(cat, fp, lidar_strike, lidar_coh)
    s_nest = predict_grid(m_nest, phys_fp, fp, fp_idx, allowed, geom_full)
    del m_nest, geom_full
    gc.collect()

    # 2. Spatially cross-fitted 4-quadrant pure-physics head (zero in-quadrant catalogue memorization!)
    log("final: fitting 4-quadrant out-of-fold pure-physics head")
    quad = quadrant_ids(fp)
    s_phys = np.zeros(fp.shape, dtype=np.float32)
    phys_fold_receipts = []
    for q in range(4):
        q_mask = quad == q
        train_reg = ndi.binary_erosion(fp & ~q_mask, iterations=12) & fp
        X_p, y_p, rec_p = fnhr.physics_rows(phys_fp, fp, fp_idx, cat, train_reg, seed=791_000 + q, neg_sample=320_000)
        m_p = fit_hgb(X_p, y_p, seed=791_000 + q)
        del X_p, y_p
        gc.collect()
        s_q = predict_grid(m_p, phys_fp, fp, fp_idx, allowed & q_mask, None)
        s_phys[allowed & q_mask] = s_q[allowed & q_mask]
        phys_fold_receipts.append({"quadrant": q, **rec_p})
        del m_p, s_q
        gc.collect()

    dist_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    s_blend = fnhr.blend_dual_heads(s_nest, s_phys, dist_cat, allowed)

    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "raw_blend_surface.npy", s_blend)
    np.save(CACHE / "raw_phys_surface.npy", s_phys)
    np.save(CACHE / "raw_nest_surface.npy", s_nest)

    build_summary = {
        "lane": "H79-FNHR",
        "preregistration_sha256": prereg_sha,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_s": round(time.time() - t0, 1),
        "n_features": len(phys_names) + len(nhr.GEOMETRY_NAMES),
        "feature_names": phys_names + [f"geom_{g}" for g in nhr.GEOMETRY_NAMES],
        "nested_receipts": rec_nest,
        "crossfit_physics_receipts": phys_fold_receipts,
        "static_stack_inputs": phys_meta["inputs_sha256"],
        "arms": {},
    }

    for exp_id, quotas in EXPERIMENTS.items():
        surf, dots, st = fnhr.build_regime_surface_and_dots(
            s_blend, dist_cat, allowed, quotas=quotas, budget=BUDGET, spacing=3
        )
        np.save(CACHE / f"{exp_id.lower()}_surface.npy", surf)
        np.save(CACHE / f"{exp_id.lower()}_dots.npy", dots)
        build_summary["arms"][exp_id] = {
            **st,
            "surface_sha256": hashlib.sha256(surf.tobytes()).hexdigest(),
            "dots_sha256": hashlib.sha256(dots.tobytes()).hexdigest(),
        }
        log(f"final {exp_id}: dots={st['emitted']} median_px={st['median_dist_px']:.2f} frac_gt10px={st['fraction_gt_10px']:.4f}")

    (OUT / "final_build_all_arms.json").write_text(json.dumps(build_summary, indent=2) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["holdout", "final", "all"])
    ap.add_argument("--seed", type=int, default=20)
    args = ap.parse_args()
    if args.stage == "holdout":
        stage_holdout(args.seed)
    elif args.stage == "final":
        stage_final()
    else:
        stage_holdout(20)
        stage_holdout(30)
        stage_final()
