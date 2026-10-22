#!/usr/bin/env python3
"""H79-MRND experiment M1 runner: canaries + two-seed holdout + surface/dot gates.

Executes the single preregistered experiment ``M1`` locked in
``registry/preregistration_mrnd.json`` (SHA-256 recorded prior to execution in
``evidence/preregistration_mrnd_sha256.txt``):

  holdout --seed S   4-fold leave-one-quadrant-out evaluation on
                     ``gems57-pooled-hide-v2`` with single-feature AUC canaries,
                     three specialized Basin-and-Range regime kernel-credit
                     ``HistGradientBoostingRegressor`` models, and paired 1,000-draw
                     spatial-block bootstrap CIs against ``h33_foldfair_control``,
                     ``ablation_single_regime_static``, and ``uniform_control``.
  final              Full-catalogue 3-regime surface construction, mandatory
                     pre-placement ``vendor.gems57.uniqueness.screen_surface`` check
                     across all 992 frozen blobs, deterministic 3 px NMS placement
                     (``gems79.placement.place``), mandatory post-placement
                     ``vendor.gems57.uniqueness.screen_placement`` check across all
                     992 frozen blobs, exact chance-overlap decomposition across all
                     990 comparable rasters, and automatic terminal lane lock on
                     gate failure (no dense-prior exemption).
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
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout as evaluator  # noqa: E402
from gems57 import uniqueness as vuniq  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw, quadrant_ids  # noqa: E402
from gems79 import mrnd, nhr  # noqa: E402
from gems79.lifecycle import LaneClosedError  # noqa: E402
from gems79.placement import place  # noqa: E402
import analyze_h33  # noqa: E402
import nhr_uniqueness  # noqa: E402
from run_experiment import canaries  # noqa: E402

OUT = ROOT / "evidence" / "mrnd"
CACHE = ROOT / ".cache" / "mrnd"
REG_DIR = ROOT / ".cache" / "registry"
STATE_PATH = OUT / "m1_experiment_state.json"


def log(*args: object) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *args, flush=True)


def load_prereg() -> dict:
    prereg_path = ROOT / "registry" / "preregistration_mrnd.json"
    pin_path = ROOT / "evidence" / "preregistration_mrnd_sha256.txt"
    raw = prereg_path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    expected = pin_path.read_text().strip()
    if actual != expected:
        raise RuntimeError(f"Preregistration drift: {actual} != {expected}")
    return json.loads(raw.decode("utf-8"))


def check_mrnd_lane_open() -> None:
    if STATE_PATH.exists():
        st = json.loads(STATE_PATH.read_text())
        if st.get("stopped") or st.get("verdict") in ("negative", "promote"):
            raise LaneClosedError(
                f"H79-MRND: lane is closed ({st.get('verdict', 'stopped')}). No files changed."
            )


class MRNDStack:
    """Memory-mapped float16 static feature matrix + fold-isolated fault geometry."""

    def __init__(self, grid, fix: dict):
        self.grid = grid
        self.static, self.canyon_vec, self.static_names, self.meta = mrnd.build_static_stack(
            grid.footprint,
            road_scale_m=float(fix["road_deseam_scale_m"]),
            road_floor=float(fix["road_deseam_floor"]),
        )
        self.row_of = np.full(grid.footprint.size, -1, np.int64)
        fpi = np.flatnonzero(grid.footprint)
        self.row_of[fpi] = np.arange(fpi.size)
        self.canyon_grid = np.zeros(grid.shape, np.float32)
        self.canyon_grid.ravel()[fpi] = self.canyon_vec
        self.lstrike, self.lcoh = nhr.read_lidar_orientation(grid.footprint)

    def geometry(self, visible: np.ndarray) -> dict[str, np.ndarray]:
        return mrnd.geometry_features(visible, self.grid.footprint, self.lstrike, self.lcoh)

    def rows(self, flat_idx: np.ndarray, geom: dict[str, np.ndarray], use_geometry: bool = True) -> np.ndarray:
        st = np.asarray(self.static[self.row_of[flat_idx]], np.float32)
        if not use_geometry:
            return st
        g = np.stack([geom[n].ravel()[flat_idx] for n in mrnd.GEOMETRY_NAMES], axis=1)
        return np.concatenate([st, g], axis=1)

    @property
    def names(self) -> list[str]:
        return list(self.static_names) + list(mrnd.GEOMETRY_NAMES)


def training_rows_by_regime(
    stack: MRNDStack,
    context: np.ndarray,
    region: np.ndarray,
    fix: dict,
    seed: int,
) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray], list[dict]]:
    """Sample nested hide-to-recover kernel-credit rows partitioned by regime."""
    rng = np.random.default_rng(seed)
    fp = stack.grid.footprint
    X_reg: dict[int, list[np.ndarray]] = {0: [], 1: [], 2: []}
    y_reg: dict[int, list[np.ndarray]] = {0: [], 1: [], 2: []}
    receipts: list[dict] = []

    for rep in range(int(fix["nested_replicates_per_model"])):
        hidden, remaining = nhr.nested_hide(
            context,
            region,
            rng,
            float(fix["nested_hide_fraction"]),
            int(fix["nested_buffer_px"]),
        )
        target = nhr.kernel_target(hidden)
        geom = stack.geometry(remaining)
        base = region & fp & ~context
        reg_map = mrnd.regime_id_from_dist_px(geom["_dist_px"], base)

        rep_info = {"replicate": rep, "hidden_pixels": int(hidden.sum()), "regimes": {}}
        for r_idx, (_, _, _, share) in enumerate(mrnd.REGIME_SPECS):
            in_reg = base & (reg_map == r_idx)
            pos = np.flatnonzero(in_reg & (target > 0))
            neg_pool = np.flatnonzero(in_reg & (target == 0))
            n_neg_target = max(15000, int(round(int(fix["negatives_sampled_per_replicate"]) * float(share))))
            neg = rng.choice(neg_pool, min(n_neg_target, neg_pool.size), replace=False)
            idx = np.concatenate([pos, neg])
            X_reg[r_idx].append(stack.rows(idx, geom, use_geometry=True))
            y_reg[r_idx].append(target.ravel()[idx].astype(np.float32))
            rep_info["regimes"][f"R{r_idx + 1}"] = {
                "positive_rows": int(pos.size),
                "negative_rows": int(neg.size),
            }
        receipts.append(rep_info)
        del geom, target, hidden, remaining, reg_map
        gc.collect()

    X_out = {r: np.concatenate(X_reg[r], axis=0) for r in (0, 1, 2)}
    y_out = {r: np.concatenate(y_reg[r], axis=0) for r in (0, 1, 2)}
    return X_out, y_out, receipts


def fit_hgb(X: np.ndarray, y: np.ndarray, fix: dict, seed: int) -> HistGradientBoostingRegressor:
    m = HistGradientBoostingRegressor(
        max_iter=int(fix["hgb_max_iter"]),
        learning_rate=float(fix["hgb_learning_rate"]),
        max_leaf_nodes=int(fix["hgb_max_leaf_nodes"]),
        min_samples_leaf=int(fix["hgb_min_samples_leaf"]),
        l2_regularization=float(fix["hgb_l2_regularization"]),
        random_state=int(seed),
        early_stopping=False,
    )
    m.fit(X, y)
    return m


def predict_regime_surface(
    models: dict[int, HistGradientBoostingRegressor],
    stack: MRNDStack,
    allowed: np.ndarray,
    geom: dict[str, np.ndarray],
    fix: dict,
    budget_scale: int,
    chunk: int = 350_000,
) -> tuple[np.ndarray, np.ndarray]:
    reg_map = mrnd.regime_id_from_dist_px(geom["_dist_px"], allowed)
    raw_scores: dict[int, np.ndarray] = {}
    for r_idx in (0, 1, 2):
        idx = np.flatnonzero(allowed & (reg_map == r_idx))
        preds = np.empty(idx.size, dtype=np.float32)
        for s in range(0, idx.size, chunk):
            part = idx[s : s + chunk]
            preds[s : s + chunk] = models[r_idx].predict(stack.rows(part, geom, True)).astype(np.float32)
        raw_scores[r_idx] = preds
    surf = mrnd.calibrate_regime_surface(
        raw_regime_scores=raw_scores,
        regime_map=reg_map,
        allowed=allowed,
        canyon_grid=stack.canyon_grid,
        canyon_weight=float(fix["canyon_penalty_weight"]),
        budget_scale=int(budget_scale),
    )
    return surf, reg_map


def predict_single_model(
    model: HistGradientBoostingRegressor,
    stack: MRNDStack,
    allowed: np.ndarray,
    geom: dict[str, np.ndarray],
    use_geometry: bool = False,
    chunk: int = 350_000,
) -> np.ndarray:
    surf = np.zeros(stack.grid.shape, np.float32)
    idx = np.flatnonzero(allowed)
    flat = surf.ravel()
    for s in range(0, idx.size, chunk):
        part = idx[s : s + chunk]
        flat[part] = model.predict(stack.rows(part, geom, use_geometry=use_geometry)).astype(np.float32)
    if idx.size:
        m = float(flat[idx].min())
        if m <= 0:
            flat[idx] -= m - 1e-6
    return surf


def stage_holdout(seed: int) -> None:
    check_mrnd_lane_open()
    prereg = load_prereg()
    fix = prereg["experiments"][0]["fixed_parameters"]
    budget_total = int(fix["budget_full_footprint"])
    spacing = int(fix["placement_spacing_px"])

    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = MRNDStack(grid, fix)
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    quad = quadrant_ids(grid.footprint)
    geom_vis = stack.geometry(visible)

    log(f"seed {seed}: running single-feature leakage canaries ({len(stack.names)} features)")

    class LazyFeatures:
        def __init__(self) -> None:
            self.names = list(stack.static_names) + ["geom_" + n for n in mrnd.GEOMETRY_NAMES]

        def items(self):
            fpi = np.flatnonzero(grid.footprint)
            for j, name in enumerate(stack.static_names):
                col = np.zeros(grid.footprint.size, np.float32)
                col[fpi] = np.nan_to_num(np.asarray(stack.static[:, j], np.float32), nan=-99.0)
                yield name, col.reshape(grid.shape)
            for name in mrnd.GEOMETRY_NAMES:
                yield "geom_" + name, np.nan_to_num(geom_vis[name], nan=-99.0)

    c_rows = canaries(LazyFeatures(), folds, seed)
    gc.collect()
    canary = dict(
        evidence_class="LEAKAGE-CANARY",
        seed=seed,
        tests=len(c_rows),
        threshold=0.90,
        max_symmetric_auc=float(max(r["symmetric_auc"] for r in c_rows)),
        worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
        n_suspicious=int(sum(r["suspicious"] for r in c_rows)),
        per_feature_max={
            n: float(max(r["symmetric_auc"] for r in c_rows if r["feature"] == n))
            for n in sorted({r["feature"] for r in c_rows})
        },
    )
    log("canary max AUC =", round(canary["max_symmetric_auc"], 4), "feature =", canary["worst"]["feature"])
    if canary["n_suspicious"] > 0 or canary["max_symmetric_auc"] > 0.90:
        raise RuntimeError(f"Leakage canary breached on seed {seed}: {canary['worst']}")

    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)

    terms: dict[str, np.ndarray] = {}
    fold_receipts: list[dict] = []

    for fold in folds:
        q = fold["fold"]
        train_region = grid.footprint & (quad != q) & (quad >= 0)
        log(f"seed {seed} fold {fold['name']}: sampling nested rows across 3 structural regimes")
        X_reg, y_reg, rec = training_rows_by_regime(stack, visible, train_region, fix, seed * 100 + q)
        models = {}
        for r_idx in (0, 1, 2):
            models[r_idx] = fit_hgb(X_reg[r_idx], y_reg[r_idx], fix, seed * 1000 + q * 10 + r_idx)

        n_static = len(stack.static_names)
        X_pool_static = np.concatenate([X_reg[r][:, :n_static] for r in (0, 1, 2)], axis=0)
        y_pool = np.concatenate([y_reg[r] for r in (0, 1, 2)], axis=0)
        m_abl = fit_hgb(X_pool_static, y_pool, fix, seed * 1000 + q * 10 + 9)
        del X_reg, y_reg, X_pool_static, y_pool
        gc.collect()

        region = fold["region"]
        allowed = region & grid.footprint & ~fold["masked_known"]
        budget = int(round(budget_total * float(region.sum()) / float(grid.footprint.sum())))
        s_full, _ = predict_regime_surface(models, stack, allowed, geom_vis, fix, budget_scale=budget)
        s_abl = predict_single_model(m_abl, stack, allowed, geom_vis, use_geometry=False)

        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = (sy, sx)
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}

        for arm_name, surf in (
            ("candidate", s_full),
            ("ablation_single_regime_static", s_abl),
            ("uniform_control", rng_surface),
        ):
            dots, _ = place(surf[sl], allowed[sl], budget, spacing=spacing)
            _, bt = evaluator.evaluate(
                dots.astype(np.float32),
                local,
                grid.footprint[sl],
                origin=(sy.start, sx.start),
                global_shape=grid.shape,
            )
            terms[arm_name] = terms.get(arm_name, 0) + bt

        d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
        h33_ff = (d28_pos[sl] & region[sl] & (d_vis > 2)).astype(np.float32)
        _, bt = evaluator.evaluate(
            h33_ff,
            local,
            grid.footprint[sl],
            origin=(sy.start, sx.start),
            global_shape=grid.shape,
        )
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt

        fold_receipts.append(
            dict(
                fold=fold["name"],
                budget=budget,
                nested=rec,
                withheld_truth=int((fold["truth"] & region).sum()),
            )
        )
        del s_full, s_abl, models, m_abl
        gc.collect()

    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    OUT.mkdir(parents=True, exist_ok=True)
    payload = dict(
        schema_version=1,
        lane="H79-MRND",
        experiment="M1",
        seed=seed,
        evidence_class="HOLDOUT-DTI",
        evaluator_version=evaluator.VERSION,
        generated_utc=datetime.now(timezone.utc).isoformat(),
        runtime_s=round(time.time() - t0, 1),
        leakage_canary=canary,
        holdout=summary,
        folds=fold_receipts,
        h33_control_source=d28src,
        feature_names=stack.names,
        static_stack_inputs=stack.meta["inputs_sha256"],
    )
    (OUT / f"m1_holdout_seed{seed}.json").write_text(json.dumps(payload, indent=2, default=float) + "\n")
    log(
        f"seed {seed} summary:",
        {k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in summary["scores"].items()},
    )


def _registry_metadata_map() -> tuple[dict[str, dict], dict[str, dict]]:
    idx = json.loads((ROOT / "registry/registry_index.json").read_text())
    rec = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    sha_by_blob = {r["blob"]: r["sha256"] for r in rec["files"] if r.get("sha256")}
    by_blob = {}
    for r in idx["rasters"]:
        b = r["blob"]
        by_blob[b] = {**r, "sha256": sha_by_blob.get(b, "")}
    chance_nhr = json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())
    nhr_by_sha = {r["sha256"]: r for r in chance_nhr["rows"]}
    return by_blob, nhr_by_sha


def _partition_uniqueness_report(raw_report: dict, by_blob: dict, nhr_by_sha: dict) -> dict:
    informative_flags = []
    dense_prior_flags = []
    max_informative_overlap = 0.0
    max_informative_spearman = 0.0
    top_informative_rows = []

    for row in raw_report["per_raster"]:
        blob = Path(row["path"]).stem
        meta = by_blob.get(blob, {})
        sha256 = meta.get("sha256", "")
        prev = nhr_by_sha.get(sha256, {})
        halo = float(prev["halo_coverage"]) if "halo_coverage" in prev else None
        ov = row.get("forward_overlap_3px")
        sp = row.get("spearman")
        enriched = {
            "blob": blob,
            "sha256": sha256,
            "submission": prev.get("submission", f"{meta.get('repo', 'UNKNOWN')}:{meta.get('path', Path(row['path']).name)}"),
            "representation": prev.get("representation", "unknown"),
            "halo_coverage": halo,
            "forward_overlap_3px": ov,
            "spearman": sp,
            "flagged": bool(row.get("flagged")),
            "reasons": row.get("reasons", []),
        }
        if halo is not None and halo <= 0.70:
            if ov is not None and ov > max_informative_overlap:
                max_informative_overlap = float(ov)
            if sp is not None and abs(sp) > abs(max_informative_spearman):
                max_informative_spearman = float(sp)
            top_informative_rows.append(enriched)
            if row.get("flagged"):
                informative_flags.append(enriched)
        elif row.get("flagged"):
            dense_prior_flags.append(enriched)

    top_informative_rows.sort(key=lambda r: r["forward_overlap_3px"] or 0.0, reverse=True)
    dense_prior_flags.sort(key=lambda r: r["forward_overlap_3px"] or 0.0, reverse=True)

    return {
        "raw_unexempted_passed": bool(raw_report["passed"]),
        "raw_total_compared": int(raw_report["compared"]),
        "raw_flagged_count": sum(1 for r in raw_report["per_raster"] if r.get("flagged")),
        "informative_non_space_filling_count": len(top_informative_rows),
        "informative_flagged_count": len(informative_flags),
        "informative_passed": len(informative_flags) == 0,
        "max_informative_forward_overlap_3px": round(max_informative_overlap, 6),
        "max_informative_spearman": round(max_informative_spearman, 6),
        "space_filling_prior_flagged_count": len(dense_prior_flags),
        "informative_flags": informative_flags,
        "space_filling_prior_flags": dense_prior_flags,
        "top_15_informative_rasters": top_informative_rows[:15],
    }


def _non_identical_transform_audit(surface: np.ndarray, dots: np.ndarray, top_k: int) -> list[dict]:
    """Audit the 4 same-shape mismatched-transform + 2 non-full-grid registry files."""
    idx = json.loads((ROOT / "registry/registry_index.json").read_text())
    by_blob = {r["blob"]: r for r in idx["rasters"]}
    ref_path = ROOT / "data/reference/sample_submission.tif"
    with rasterio.open(ref_path) as ref:
        ref_shape, ref_crs, ref_transform = ref.shape, ref.crs, ref.transform

    surf_top = np.zeros(surface.shape, bool)
    flat_s = surface.ravel()
    top_idx = np.argsort(-flat_s, kind="stable")[:top_k]
    surf_top.ravel()[top_idx] = True

    results = []
    for tif_path in sorted(REG_DIR.glob("*.tif")):
        blob = tif_path.stem
        meta = by_blob.get(blob, {})
        try:
            with rasterio.open(tif_path) as src:
                if src.shape == ref_shape and src.crs == ref_crs and src.transform == ref_transform:
                    continue
                arr = src.read(1)
                shape, crs = src.shape, str(src.crs)
        except Exception as exc:
            results.append({"blob": blob, "repo": meta.get("repo"), "path": meta.get("path"), "status": f"unreadable: {exc}"})
            continue
        if shape != ref_shape:
            results.append({"blob": blob, "repo": meta.get("repo"), "path": meta.get("path"), "shape": list(shape), "crs": crs, "status": "non_full_grid_fixture"})
            continue
        pos = np.isfinite(arr) & (arr > 0)
        halo = ndi.distance_transform_edt(~pos) <= 3.0 if pos.any() else np.zeros(shape, bool)
        results.append({
            "blob": blob,
            "repo": meta.get("repo"),
            "path": meta.get("path"),
            "shape": list(shape),
            "crs": crs,
            "status": "same_shape_mismatched_transform",
            "halo_coverage": round(float(halo[surface > 0].mean()), 6),
            "surface_forward_overlap_3px": round(float(halo[surf_top].mean()), 6),
            "dots_forward_overlap_3px": round(float(halo[dots].mean()), 6),
        })
    return results


def stage_final() -> None:
    check_mrnd_lane_open()
    prereg = load_prereg()
    fix = prereg["experiments"][0]["fixed_parameters"]
    budget = int(fix["budget_full_footprint"])
    spacing = int(fix["placement_spacing_px"])

    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = MRNDStack(grid, fix)
    cat = grid.catalogue
    allowed = grid.footprint & ~cat

    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    surf_cache = CACHE / "final_surface.npy"
    rec_cache = CACHE / "final_nested_receipts.json"
    geom = stack.geometry(cat)
    reg_map = mrnd.regime_id_from_dist_px(geom["_dist_px"], allowed)

    if surf_cache.exists():
        log("final: loading precomputed final_surface.npy from cache")
        norm_surface = np.load(surf_cache)
        rec = json.loads(rec_cache.read_text()) if rec_cache.exists() else []
    else:
        log("final: fitting 3-regime nested hide-to-recover models on full visible catalogue")
        X_reg, y_reg, rec = training_rows_by_regime(stack, cat, grid.footprint, fix, 790800)
        models = {r: fit_hgb(X_reg[r], y_reg[r], fix, 790810 + r) for r in (0, 1, 2)}
        del X_reg, y_reg
        gc.collect()
        norm_surface, reg_map = predict_regime_surface(models, stack, allowed, geom, fix, budget_scale=budget)
        np.save(surf_cache, norm_surface)
        rec_cache.write_text(json.dumps(rec, indent=2) + "\n")

    by_blob, nhr_by_sha = _registry_metadata_map()

    # ---- MANDATORY GATE 1: Continuous surface uniqueness BEFORE dot placement ----
    log("final gate 1/2: running nhr_uniqueness.run('surface') BEFORE dot placement")
    surf_res = nhr_uniqueness.run("surface", lane="H79-MRND", cache=CACHE, out_dir=OUT)
    surf_sha = surf_res["surface_sha256"]

    # Measure full per-raster surface overlap vs halo_coverage (diagnostic partition)
    inv, expected = nhr_uniqueness.inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    prov = vuniq.budget_matched_dots(norm_surface, allowed, budget).astype(np.float32)
    r_prov = vuniq.compare_array_to_registry(
        prov, inv, grid.footprint, include_reverse=False, expected_grid=eg, dot_definition="budget-matched-v3"
    )
    nhr_chance = json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())
    nhr_by_sub = {r["submission"]: r for r in nhr_chance["rows"]}

    surf_inf_flags = []
    surf_dense_flags = []
    max_surf_inf_ov = 0.0
    for r in r_prov["rows"]:
        if "error" in r:
            continue
        hc = nhr_by_sub.get(r["submission"], {}).get("halo_coverage")
        ov = float(r["my_dots_within_3px_of_theirs"])
        if hc is not None and hc <= 0.70:
            max_surf_inf_ov = max(max_surf_inf_ov, ov)
            if ov > 0.70:
                surf_inf_flags.append({"submission": r["submission"], "overlap": ov, "halo_coverage": hc})
        elif ov > 0.70:
            surf_dense_flags.append({"submission": r["submission"], "overlap": ov, "halo_coverage": hc})

    log(
        "surface check complete:",
        "literal_passed=", surf_res["passed"],
        "informative_flags=", len(surf_inf_flags),
        "max_informative_overlap=", round(max_surf_inf_ov, 6),
        "max_spearman=", round(surf_res["worst_spearman"], 6),
    )

    # ---- Place 37,654 dots deterministically via shared placement rule ----
    log("final: placing deterministic 3 px NMS dots via gems79.placement.place")
    dots, p_info = place(norm_surface, allowed, budget, spacing=spacing)
    np.save(CACHE / "final_dots.npy", dots)
    dots_sha = hashlib.sha256(dots.tobytes()).hexdigest()

    reg_counts = {
        name: int((dots & (reg_map == r_idx)).sum())
        for r_idx, (name, _, _, _) in enumerate(mrnd.REGIME_SPECS)
    }
    d_m = geom["_dist_px"][dots] * 100.0
    dist_stats = {
        "median_m": round(float(np.median(d_m)), 1),
        "p10_m": round(float(np.percentile(d_m, 10)), 1),
        "p90_m": round(float(np.percentile(d_m, 90)), 1),
        "share_le_1400m": round(float((d_m <= 1400.0).mean()), 4),
        "share_1400_to_4500m": round(float(((d_m > 1400.0) & (d_m <= 4500.0)).mean()), 4),
        "share_gt_4500m": round(float((d_m > 4500.0).mean()), 4),
        "regime_dot_counts": reg_counts,
    }

    # ---- MANDATORY GATE 2: Placed dot uniqueness across ALL 992 frozen blobs ----
    log("final gate 2/2: running nhr_uniqueness.run('final') across all registry rasters")
    final_res = nhr_uniqueness.run("final", lane="H79-MRND", cache=CACHE, out_dir=OUT)

    # Full 990-raster overlap_chance.json (identical formula to scripts/nhr_overlap_chance.py)
    from scipy.stats import rankdata

    rng_u = np.random.default_rng(79)
    cells = np.flatnonzero(allowed.ravel())
    uni = np.zeros(grid.footprint.size, bool)
    uni[rng_u.choice(cells, budget, replace=False)] = True
    uni = uni.reshape(grid.footprint.shape)
    mine = dots.astype(np.float64)[grid.footprint]
    ranks = rankdata(mine)
    ranks -= ranks.mean()
    norm_r = float(np.linalg.norm(ranks))

    rows, not_comparable = [], []
    for rec_item in inv["rasters"]:
        p = Path(rec_item["cache_file"])
        name = (
            rec_item["sources"][0]
            if ":" in rec_item["sources"][0]
            else rec_item["repo_first"] + ":" + rec_item["sources"][0]
        )
        try:
            if hashlib.sha256(p.read_bytes()).hexdigest() != rec_item["sha256"]:
                raise ValueError("sha256 pin mismatch")
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != grid.footprint.shape:
                    raise ValueError(f"shape {src.shape} / bands {src.count} differ from competition grid")
                georef_ok = (
                    src.crs is not None and src.crs.to_epsg() == 32611 and src.transform == grid.transform
                )
                a = src.read(1).astype(np.float32)
        except Exception as exc:
            not_comparable.append(dict(submission=name, reason=str(exc)[:160]))
            continue
        a = np.where(np.isfinite(a), a, 0.0)
        a[~grid.footprint] = 0
        support = (a > 0) & grid.footprint
        kind = vuniq.representation_class(int(support.sum()), int(grid.footprint.sum()))["kind"]
        if kind == "continuous_surface":
            support = vuniq.budget_matched_dots(a, grid.footprint, budget)
        halo = vuniq._near(support)
        cov = float(halo[allowed].mean())
        ov = float(halo[dots].mean())
        ou = float(halo[uni].mean())
        tv = a[grid.footprint].astype(np.float64)
        if np.ptp(tv) == 0:
            rho = None
        else:
            tr = rankdata(tv)
            tr -= tr.mean()
            rho = float(np.dot(ranks, tr) / (norm_r * np.linalg.norm(tr)))
        kappa = None if cov >= 1.0 else (ov - cov) / (1.0 - cov)
        kappa_u = None if cov >= 1.0 else (ou - cov) / (1.0 - cov)
        rows.append(
            dict(
                submission=name,
                sha256=rec_item["sha256"],
                representation=kind,
                georeference_matches_sample=georef_ok,
                their_dots=int(support.sum()),
                halo_coverage=cov,
                overlap_candidate=ov,
                overlap_uniform=ou,
                overlap_beyond_chance=kappa,
                overlap_beyond_chance_uniform=kappa_u,
                spearman=rho,
            )
        )

    lit_flags = [r for r in rows if r["overlap_candidate"] > vuniq.OVERLAP_LIMIT]
    uni_fail = [r for r in rows if r["overlap_uniform"] > vuniq.OVERLAP_LIMIT]
    space = [r for r in rows if r["halo_coverage"] > vuniq.OVERLAP_LIMIT]
    informative = [r for r in rows if r["halo_coverage"] <= vuniq.OVERLAP_LIMIT]
    inf_flags = [r for r in informative if r["overlap_candidate"] > vuniq.OVERLAP_LIMIT]

    def worst(rs, k):
        rs = [r for r in rs if r[k] is not None]
        return max(rs, key=lambda r: r[k]) if rs else None

    chance_payload = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        lane="H79-MRND",
        experiment="M1",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        shared_tool_sha256=hashlib.sha256(Path(vuniq.__file__).read_bytes()).hexdigest(),
        dot_definition="budget-matched-v3",
        budget=budget,
        uniform_control_seed=79,
        registry_rasters_expected=expected,
        compared=len(rows),
        not_comparable=not_comparable,
        same_shape_other_georeference=[r["submission"] for r in rows if not r["georeference_matches_sample"]],
        rasters_where_candidate_overlap_gt_0_70=len(lit_flags),
        rasters_where_uniform_random_overlap_gt_0_70=len(uni_fail),
        space_filling_rasters_halo_gt_0_70=len(space),
        informative_rasters_halo_le_0_70=len(informative),
        informative_surface_flags_gt_0_70=len(surf_inf_flags),
        informative_final_flags_gt_0_70=len(inf_flags),
        max_informative_surface_overlap_3px=round(max_surf_inf_ov, 6),
        candidate_flagged_only_by_space_filling_rasters=all(
            r["halo_coverage"] > vuniq.OVERLAP_LIMIT for r in lit_flags
        ),
        worst_candidate_overlap_vs_informative_rasters=worst(informative, "overlap_candidate"),
        worst_candidate_overlap_beyond_chance=worst(rows, "overlap_beyond_chance"),
        worst_uniform_overlap_beyond_chance=worst(rows, "overlap_beyond_chance_uniform"),
        worst_spearman_all_comparable=worst(rows, "spearman"),
        informative_flagged_rows=inf_flags,
        surface_informative_flagged_rows=surf_inf_flags,
        rows=sorted(rows, key=lambda r: -r["overlap_candidate"]),
    )
    (OUT / "overlap_chance.json").write_text(
        json.dumps(chance_payload, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n"
    )

    build_meta = {
        "lane": "H79-MRND",
        "experiment": "M1",
        "runtime_s": round(time.time() - t0, 1),
        "surface_sha256": surf_sha,
        "dots_sha256": dots_sha,
        "n_dots": int(dots.sum()),
        "placement": p_info,
        "distance_distribution": dist_stats,
        "nested_training": rec,
        "feature_count": len(stack.names),
        "feature_names": stack.names,
        "surface_informative_flags": len(surf_inf_flags),
        "surface_max_informative_overlap_3px": round(max_surf_inf_ov, 6),
        "final_informative_flags": len(inf_flags),
        "final_max_informative_overlap_3px": (
            round(chance_payload["worst_candidate_overlap_vs_informative_rasters"]["overlap_candidate"], 6)
            if chance_payload["worst_candidate_overlap_vs_informative_rasters"]
            else 0.0
        ),
    }
    (OUT / "m1_final_build.json").write_text(json.dumps(build_meta, indent=2) + "\n")

    all_literal_unique = bool(surf_res["passed"] and final_res["passed"] and not lit_flags)
    state = {
        "lane": "H79-MRND",
        "experiment": "M1",
        "experiment_count": 1,
        "max_experiments": 3,
        "stopped": True,
        "verdict": "promote" if all_literal_unique else "negative",
        "stop_reason": (
            None
            if all_literal_unique
            else (
                f"Unexempted gems57.uniqueness gate flagged {len(lit_flags)} rasters "
                f"({len(lit_flags) - len(inf_flags)} space-filling/lattice priors with halo_coverage > 0.70, "
                f"{len(inf_flags)}/{len(informative)} informative non-space-filling rasters). "
                "Lane closed without dense-prior exemptions."
            )
        ),
        "informative_non_space_filling_surface_flags": len(surf_inf_flags),
        "informative_non_space_filling_final_flags": len(inf_flags),
        "candidate_flagged_only_by_space_filling_rasters": chance_payload[
            "candidate_flagged_only_by_space_filling_rasters"
        ],
        "locked_utc": datetime.now(timezone.utc).isoformat(),
    }
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
    log("final check complete:", json.dumps(state, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Execute preregistered H79-MRND experiment M1.")
    ap.add_argument("stage", choices=["holdout", "final"])
    ap.add_argument("--seed", type=int, default=20)
    args = ap.parse_args()
    try:
        if args.stage == "holdout":
            stage_holdout(args.seed)
        else:
            stage_final()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
