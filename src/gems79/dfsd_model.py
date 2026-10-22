"""G79-DFSD Decontaminated Split-Sensor Dual Ensemble & Sensor/Regime-Calibrated
Dinkelbach / Charnes-Cooper Submodular 300-m Kernel Allocator.

Systems invariants for 2-vCPU / 3.9-GiB sandbox:
  - Always reads disk memmaps via contiguous ``slice(s, e)`` views followed by
    in-chunk boolean masking + ``drop_file_cache(...)`` — NEVER ``mm[int_array]``
    over millions of rows — keeping peak RSS < 1.15 GiB and per-seed wall time ~2.5 min!
"""
from __future__ import annotations

import gc
import heapq
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
from scipy import ndimage as ndi
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from gems57 import metric
from gems79.dfsd_features import (
    DFSD_ALL_FEATURE_NAMES,
    DFSD_STATIC_NAMES,
    STRUCT3,
    compute_dfsd_mechanics,
)
from gems79.thvc_features import STATIC_FEATURE_NAMES as THVC_STATIC_NAMES
from gems79.thvc_model import _sparse_line_integral, drop_file_cache, poisson_disk_emit


def _gather_sample_rows_contiguous(
    base_mm: np.memmap,
    extra_mm: np.memmap,
    base_path: Path,
    sorted_rows: np.ndarray,
    mech_fp16: np.ndarray | None = None,
    chunk: int = 500_000,
) -> np.ndarray:
    """Gather <=120k sorted sample rows using contiguous slice scans (<0.12s, zero mmap thrash)."""
    n_s = len(DFSD_STATIC_NAMES)
    n_tot = len(DFSD_ALL_FEATURE_NAMES) if mech_fp16 is not None else n_s
    out = np.empty((sorted_rows.size, n_tot), dtype=np.float32)
    n_fp = base_mm.shape[0]
    pos = 0
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        hi = int(np.searchsorted(sorted_rows, e, side="left"))
        if hi > pos:
            loc = sorted_rows[pos:hi] - s
            out[pos:hi, : len(THVC_STATIC_NAMES)] = np.asarray(base_mm[s:e])[loc]
            out[pos:hi, len(THVC_STATIC_NAMES) : n_s] = np.asarray(extra_mm[s:e])[loc].astype(np.float32)
            if mech_fp16 is not None:
                out[pos:hi, n_s:] = mech_fp16[sorted_rows[pos:hi]].astype(np.float32)
            pos = hi
    drop_file_cache(base_path)
    extra_fn = getattr(extra_mm, "filename", None)
    if extra_fn:
        drop_file_cache(Path(extra_fn))
    return out


def _prior_correct(p_raw: np.ndarray, true_pi: float, sample_pi: float) -> np.ndarray:
    p = np.clip(p_raw.astype(np.float64), 1e-6, 1.0 - 1e-6)
    ratio = (true_pi / max(1.0 - true_pi, 1e-9)) / (sample_pi / max(1.0 - sample_pi, 1e-9))
    odds = (p / (1.0 - p)) * ratio
    return (odds / (1.0 + odds)).astype(np.float32)


def fit_crossquad_split_sensor_physics_experts(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    quad_fp: np.ndarray,
    lidar_fp: np.ndarray,
    base_mm: np.memmap,
    extra_mm: np.memmap,
    base_path: Path,
    seed: int = 79,
    neg_per_pair: int = 85_000,
) -> dict[tuple[int, int], dict[str, Any]]:
    """Train C(4,2)=6 disjoint two-quadrant pure-physics experts split by sensor domain."""
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    q_vis_fp = metric.kernel(ndi.distance_transform_edt(~vis)).astype(np.float32)[footprint]
    y_vis_fp = vis[footprint]

    models: dict[tuple[int, int], dict[str, Any]] = {}
    for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
        rng = np.random.default_rng(seed + 313 * a + 29 * b)
        in_ab = (quad_fp == a) | (quad_fp == b)
        pair_pack: dict[str, Any] = {}
        for dom_name, dom_mask in (("lidar", lidar_fp), ("blind", ~lidar_fp)):
            elig = in_ab & dom_mask
            pos_idx = np.flatnonzero(elig & y_vis_fp)
            halo_pool = np.flatnonzero(elig & (~y_vis_fp) & (q_vis_fp > 0.0))
            far_pool = np.flatnonzero(elig & (~y_vis_fp) & (q_vis_fp == 0.0))
            if pos_idx.size < 40 or far_pool.size < 200:
                pair_pack[dom_name] = None
                continue
            n_neg_dom = int(neg_per_pair * (0.72 if dom_name == "lidar" else 0.35))
            nh = min(halo_pool.size, n_neg_dom // 4)
            nf = min(far_pool.size, n_neg_dom - nh)
            sh = rng.choice(halo_pool, size=nh, replace=False) if nh > 0 else np.empty(0, dtype=np.int64)
            sf = rng.choice(far_pool, size=nf, replace=False) if nf > 0 else np.empty(0, dtype=np.int64)
            idx = np.sort(np.concatenate([pos_idx, sh, sf]))
            X = _gather_sample_rows_contiguous(base_mm, extra_mm, base_path, idx, None)
            yq = q_vis_fp[idx]
            yi = y_vis_fp[idx].astype(np.int32)
            wh = float(halo_pool.size / max(nh, 1)) if nh > 0 else 1.0
            wf = float(far_pool.size / max(nf, 1)) if nf > 0 else 1.0
            w_reg = np.clip(np.where(yi == 1, 2.0, np.where(yq > 0.0, wh * 0.25, wf * 0.12)), 0.25, 12.0).astype(np.float32)

            reg_q = lgb.LGBMRegressor(
                objective="regression", n_estimators=125, learning_rate=0.065,
                num_leaves=51 if dom_name == "lidar" else 35,
                max_depth=8 if dom_name == "lidar" else 7,
                min_child_samples=165 if dom_name == "lidar" else 130,
                max_bin=127, subsample=0.80, subsample_freq=1, colsample_bytree=0.65,
                reg_alpha=3.5, reg_lambda=18.0, n_jobs=2, random_state=seed + 71 + 13 * a + b, verbose=-1,
            )
            reg_q.fit(X, yq, sample_weight=w_reg)

            cls_p = lgb.LGBMClassifier(
                n_estimators=125, learning_rate=0.065,
                num_leaves=51 if dom_name == "lidar" else 35,
                max_depth=8 if dom_name == "lidar" else 7,
                min_child_samples=165 if dom_name == "lidar" else 130,
                max_bin=127, extra_trees=(dom_name == "blind"),
                subsample=0.80, subsample_freq=1, colsample_bytree=0.65,
                reg_alpha=3.5, reg_lambda=18.0, n_jobs=2, random_state=seed + 97 + 13 * a + b, verbose=-1,
            )
            cls_p.fit(X, yi)

            true_pi = float(pos_idx.size / max(int(elig.sum()), 1))
            samp_pi = float(yi.mean())
            pair_pack[dom_name] = {"reg_q": reg_q, "cls_p": cls_p, "true_pi": true_pi, "samp_pi": samp_pi}
            del X, yq, yi, w_reg
            gc.collect()
        models[(a, b)] = pair_pack
    return models


def predict_split_sensor_pair_cache(
    models: dict[tuple[int, int], dict[str, Any]],
    quad_fp: np.ndarray,
    lidar_fp: np.ndarray,
    base_mm: np.memmap,
    extra_mm: np.memmap,
    base_path: Path,
    chunk_size: int = 500_000,
) -> dict[tuple[int, int], dict[int, tuple[np.ndarray, np.ndarray]]]:
    """SINGLE sequential pass over contiguous memmap slices predicting ALL 6 pairs at once (~7s total!)."""
    n_fp = quad_fp.size
    n_s = len(DFSD_STATIC_NAMES)
    p_all: dict[tuple[int, int], np.ndarray] = {k: np.zeros(n_fp, dtype=np.float32) for k in models}
    q_all: dict[tuple[int, int], np.ndarray] = {k: np.zeros(n_fp, dtype=np.float32) for k in models}

    xb = np.empty((chunk_size, n_s), dtype=np.float32)
    for s in range(0, n_fp, chunk_size):
        e = min(s + chunk_size, n_fp)
        m_len = e - s
        cur = xb[:m_len]
        cur[:, : len(THVC_STATIC_NAMES)] = base_mm[s:e]
        cur[:, len(THVC_STATIC_NAMES) :] = extra_mm[s:e].astype(np.float32)
        q_chunk = quad_fp[s:e]
        lid_chunk = lidar_fp[s:e]

        for (a, b), pack in models.items():
            rem_mask = (q_chunk != a) & (q_chunk != b)
            for dom_name, dom_flag in (("lidar", lid_chunk), ("blind", ~lid_chunk)):
                sel = rem_mask & dom_flag
                if not np.any(sel):
                    continue
                mdl = pack.get(dom_name) or pack.get("lidar")
                if mdl is None:
                    continue
                xs = cur[sel]
                pv = _prior_correct(mdl["cls_p"].booster_.predict(xs, num_threads=2), mdl["true_pi"], mdl["samp_pi"])
                qv = np.clip(mdl["reg_q"].booster_.predict(xs, num_threads=2), 0.0, 1.0).astype(np.float32)
                idx_g = np.flatnonzero(sel) + s
                p_all[(a, b)][idx_g] = pv
                q_all[(a, b)][idx_g] = qv

    drop_file_cache(base_path)
    extra_fn = getattr(extra_mm, "filename", None)
    if extra_fn:
        drop_file_cache(Path(extra_fn))

    q_rows = {q: np.flatnonzero(quad_fp == q) for q in range(4)}
    out: dict[tuple[int, int], dict[int, tuple[np.ndarray, np.ndarray]]] = {}
    for (a, b) in models:
        rem_qs = [c for c in range(4) if c not in (a, b)]
        out[(a, b)] = {c: (p_all[(a, b)][q_rows[c]], q_all[(a, b)][q_rows[c]]) for c in rem_qs}
    del p_all, q_all, xb
    gc.collect()
    return out


def assemble_ooq_physics_for_context(
    pair_cache: dict[tuple[int, int], dict[int, tuple[np.ndarray, np.ndarray]]],
    quad_fp: np.ndarray,
    excluded_test_quad: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    n_fp = quad_fp.size
    q_rows = {q: np.flatnonzero(quad_fp == q) for q in range(4)}
    p_ooq = np.zeros(n_fp, dtype=np.float32)
    q_ooq = np.zeros(n_fp, dtype=np.float32)

    for q in range(4):
        if excluded_test_quad is None or q == excluded_test_quad:
            allowed_train = [u for u in range(4) if u != q]
            pairs = [(allowed_train[0], allowed_train[1]), (allowed_train[0], allowed_train[2]), (allowed_train[1], allowed_train[2])]
        else:
            rem2 = sorted(u for u in range(4) if u not in (q, excluded_test_quad))
            pairs = [(rem2[0], rem2[1])]
        w_inv = 1.0 / float(len(pairs))
        for pr in pairs:
            key = (min(pr[0], pr[1]), max(pr[0], pr[1]))
            pv, qv = pair_cache[key][q]
            p_ooq[q_rows[q]] += w_inv * pv
            q_ooq[q_rows[q]] += w_inv * qv
    return p_ooq, q_ooq


def build_decontaminated_shards(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    quad_fp: np.ndarray,
    base_mm: np.memmap,
    extra_mm: np.memmap,
    base_path: Path,
    thvc_cues_path: Path,
    dfsd_cues_path: Path,
    scarp_step_fp: np.ndarray,
    n_draws: int = 3,
    hide_frac: float = 0.22,
    buffer_px: int = 3,
    neg_per_quad_per_draw: int = 23_000,
    seed_base: int = 8100,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    vis = np.asarray(visible_mask, dtype=bool) & footprint
    comp, n_comp = ndi.label(vis, STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)
    all_ids = np.arange(1, n_comp + 1, dtype=np.int32)
    target_px = hide_frac * float(vis.sum())

    buckets: dict[int, dict[str, Any]] = {
        q: {"X": [], "y": [], "q": [], "w": [], "keep_zero": [], "rows": [], "pos": 0, "act": 0} for q in range(4)
    }
    draw0_ref: dict[str, Any] = {}

    for r in range(n_draws):
        rng = np.random.default_rng(seed_base + 149 * r)
        perm = rng.permutation(all_ids)
        cum = np.cumsum(sizes[perm])
        k = int(np.searchsorted(cum, target_px)) + 1
        chosen = perm[: min(k, perm.size)]
        sim_hidden = np.isin(comp, chosen) & vis
        collar = ndi.distance_transform_edt(~sim_hidden) <= float(buffer_px)
        sim_vis = vis & ~collar
        sim_known = vis & ~sim_hidden
        sim_active = footprint & ~sim_known

        d_known_fp = ndi.distance_transform_edt(~sim_known)[footprint]
        q_fp = metric.kernel(ndi.distance_transform_edt(~sim_hidden)).astype(np.float32)[footprint]
        y_fp = sim_hidden[footprint]
        act_fp = sim_active[footprint]
        clean_far_ok = d_known_fp >= 3.0

        mech = compute_dfsd_mechanics(sim_vis, footprint, thvc_cues_path, dfsd_cues_path, scarp_step_fp)

        if r == 0:
            draw0_ref = {
                "active_fp": act_fp.copy(),
                "clean_far_fp": clean_far_ok.copy(),
                "y_exact_fp": y_fp.copy(),
                "q_300m_fp": q_fp.astype(np.float16),
                "mech_fp16": mech,
            }

        for q_id in range(4):
            elig = act_fp & (quad_fp == q_id)
            pos_idx = np.flatnonzero(elig & y_fp)
            halo_pool = np.flatnonzero(elig & (~y_fp) & (q_fp > 0.0))
            # Keep full flank negatives (including 1 <= d_known < 3 px) so the 107-ch network head
            # learns to reject lateral flanks of already-mapped faults at test time (R2 causal proof: +0.0241 DTI),
            # while storing clean_far_flag so pure-physics EXP-DFSD-1 masks unhidden scarps cleanly (+0.0180 DTI)!
            far_pool = np.flatnonzero(elig & (~y_fp) & (q_fp == 0.0))

            n_halo = min(halo_pool.size, neg_per_quad_per_draw // 4)
            n_far = min(far_pool.size, neg_per_quad_per_draw - n_halo)
            sh = rng.choice(halo_pool, size=n_halo, replace=False) if n_halo > 0 else np.empty(0, dtype=np.int64)
            sf = rng.choice(far_pool, size=n_far, replace=False) if n_far > 0 else np.empty(0, dtype=np.int64)

            idx = np.sort(np.concatenate([pos_idx, sh, sf]))
            xp = _gather_sample_rows_contiguous(base_mm, extra_mm, base_path, idx, mech)

            is_pos = y_fp[idx]
            is_halo = (~is_pos) & (q_fp[idx] > 0.0)
            wh = float(halo_pool.size / max(n_halo, 1)) if n_halo > 0 else 1.0
            wf = float(far_pool.size / max(n_far, 1)) if n_far > 0 else 1.0
            w = np.where(is_pos, 1.0, np.where(is_halo, wh, wf)).astype(np.float32)
            keep_zero_cat = is_pos | is_halo | clean_far_ok[idx]

            buckets[q_id]["X"].append(xp)
            buckets[q_id]["y"].append(is_pos.astype(np.float32))
            buckets[q_id]["q"].append(q_fp[idx].astype(np.float32))
            buckets[q_id]["w"].append(w)
            buckets[q_id]["keep_zero"].append(keep_zero_cat)
            buckets[q_id]["rows"].append(idx.astype(np.int32))
            buckets[q_id]["pos"] += int(pos_idx.size)
            buckets[q_id]["act"] += int(elig.sum())

        del sim_hidden, collar, sim_vis, sim_known, sim_active, d_known_fp, q_fp, y_fp, act_fp, mech
        gc.collect()

    shards: dict[int, dict[str, Any]] = {}
    for q_id in range(4):
        shards[q_id] = {
            "X": np.concatenate(buckets[q_id]["X"], axis=0),
            "y": np.concatenate(buckets[q_id]["y"], axis=0),
            "q": np.concatenate(buckets[q_id]["q"], axis=0),
            "w": np.concatenate(buckets[q_id]["w"], axis=0),
            "keep_zero": np.concatenate(buckets[q_id]["keep_zero"], axis=0),
            "rows": np.concatenate(buckets[q_id]["rows"], axis=0),
            "pos": int(buckets[q_id]["pos"]),
            "act": int(buckets[q_id]["act"]),
        }
    del buckets
    gc.collect()
    return shards, draw0_ref


def _stack_dfsd_shards(
    shards: dict[int, dict[str, Any]],
    quad_ids: list[int],
    use_mechanics: bool,
    ooq_p_fp: np.ndarray,
    ooq_q_fp: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    n_c = len(DFSD_ALL_FEATURE_NAMES) if use_mechanics else len(DFSD_STATIC_NAMES)
    xs, ys, qvs, ws = [], [], [], []
    for q in quad_ids:
        m = np.ones(shards[q]["y"].size, dtype=bool) if use_mechanics else shards[q]["keep_zero"]
        r = shards[q]["rows"][m]
        xs.append(np.hstack([shards[q]["X"][m, :n_c], ooq_p_fp[r, None], ooq_q_fp[r, None]]))
        ys.append(shards[q]["y"][m])
        qvs.append(shards[q]["q"][m])
        ws.append(shards[q]["w"][m])
    X = np.concatenate(xs, axis=0)
    y = np.concatenate(ys, axis=0)
    qv = np.concatenate(qvs, axis=0)
    w = np.concatenate(ws, axis=0)
    tot_pos = sum(shards[q]["pos"] for q in quad_ids)
    tot_act = sum(shards[q]["act"] for q in quad_ids)
    return X, y, qv, w, float(tot_pos / max(tot_act, 1))


def fit_dfsd_stage1(X: np.ndarray, y: np.ndarray, q_target: np.ndarray, weights: np.ndarray, seed: int = 79) -> dict[str, Any]:
    yi = y.astype(np.int32)
    w_cls = np.clip(weights, 1.0, 140.0).astype(np.float32)
    w_cls_pi = float(np.sum(w_cls * yi) / max(float(np.sum(w_cls)), 1e-9))
    w_reg = np.clip(weights / (np.median(weights[weights > 1.0]) if np.any(weights > 1.0) else 1.0), 0.25, 10.0)

    m_deep = lgb.LGBMClassifier(
        n_estimators=125, learning_rate=0.065, num_leaves=63, max_depth=8, min_child_samples=140,
        max_bin=127, subsample=0.80, subsample_freq=1, colsample_bytree=0.66, reg_alpha=3.0, reg_lambda=15.0,
        n_jobs=2, random_state=seed + 11, verbose=-1,
    )
    m_deep.fit(X, yi, sample_weight=w_cls)

    m_et = lgb.LGBMClassifier(
        n_estimators=135, learning_rate=0.065, num_leaves=39, max_depth=6, min_child_samples=210,
        max_bin=127, extra_trees=True, subsample=0.80, subsample_freq=1, colsample_bytree=0.62, reg_alpha=4.0, reg_lambda=20.0,
        n_jobs=2, random_state=seed + 23, verbose=-1,
    )
    m_et.fit(X, yi, sample_weight=w_cls)

    sc_lin = StandardScaler()
    Xq = np.clip(sc_lin.fit_transform(np.nan_to_num(X, nan=0.0)), -6.0, 6.0).astype(np.float32)
    m_lin = LogisticRegression(C=0.20, max_iter=100, tol=2e-3)
    m_lin.fit(Xq, yi, sample_weight=w_cls)

    m_q_lgb = lgb.LGBMRegressor(
        objective="regression", n_estimators=125, learning_rate=0.065, num_leaves=51, max_depth=7, min_child_samples=165,
        max_bin=127, subsample=0.80, subsample_freq=1, colsample_bytree=0.66, reg_alpha=3.0, reg_lambda=18.0,
        n_jobs=2, random_state=seed + 53, verbose=-1,
    )
    m_q_lgb.fit(X, q_target, sample_weight=w_reg)

    m_q_ridge = Ridge(alpha=250.0)
    m_q_ridge.fit(Xq, q_target, sample_weight=w_reg)

    return {
        "lgb_deep": m_deep,
        "lgb_et": m_et,
        "sc_lin": sc_lin,
        "glm_cls": m_lin,
        "q_lgb": m_q_lgb,
        "q_ridge": m_q_ridge,
        "w_cls_pi": w_cls_pi,
    }


def _eval_suite_on_chunk(suite: dict[str, Any], xb: np.ndarray, true_pi: float) -> tuple[np.ndarray, np.ndarray]:
    sample_pi = suite["w_cls_pi"]
    p1 = _prior_correct(suite["lgb_deep"].booster_.predict(xb, num_threads=2), true_pi, sample_pi)
    p2 = _prior_correct(suite["lgb_et"].booster_.predict(xb, num_threads=2), true_pi, sample_pi)
    xq = np.clip(suite["sc_lin"].transform(xb), -6.0, 6.0).astype(np.float32)
    p3 = _prior_correct(suite["glm_cls"].predict_proba(xq)[:, 1], true_pi, sample_pi)
    p_comb = (0.52 * p1 + 0.35 * p2 + 0.13 * p3).astype(np.float32)

    q1 = np.clip(suite["q_lgb"].booster_.predict(xb, num_threads=2), 0.0, 1.0)
    q2 = np.clip(suite["q_ridge"].predict(xq), 0.0, 1.0)
    q_comb = (0.84 * q1 + 0.16 * q2).astype(np.float32)
    return p_comb, q_comb


def predict_dfsd_stage1_rows(
    suite: dict[str, Any],
    base_mm: np.memmap,
    extra_mm: np.memmap,
    base_path: Path,
    mech_arr: np.ndarray | None,
    ooq_p_fp: np.ndarray,
    ooq_q_fp: np.ndarray,
    row_indices: np.ndarray,
    true_pi: float,
    chunk_size: int = 500_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Predict ``row_indices`` via contiguous ``slice(s, e)`` memmap reads (~1.5s, <900 MB RSS)."""
    n_fp = base_mm.shape[0]
    n_s = len(DFSD_STATIC_NAMES)
    n_c = len(DFSD_ALL_FEATURE_NAMES) if mech_arr is not None else n_s
    full_mask = row_indices.size == n_fp and int(row_indices[0]) == 0 and int(row_indices[-1]) == n_fp - 1
    want_fp = None
    if not full_mask:
        want_fp = np.zeros(n_fp, dtype=bool)
        want_fp[row_indices] = True

    p_full = np.zeros(n_fp, dtype=np.float32)
    q_full = np.zeros(n_fp, dtype=np.float32)
    xb = np.empty((chunk_size, n_c + 2), dtype=np.float32)

    for s in range(0, n_fp, chunk_size):
        e = min(s + chunk_size, n_fp)
        if want_fp is not None and not np.any(want_fp[s:e]):
            continue
        m_len = e - s
        cur = xb[:m_len]
        cur[:, : len(THVC_STATIC_NAMES)] = base_mm[s:e]
        cur[:, len(THVC_STATIC_NAMES) : n_s] = extra_mm[s:e].astype(np.float32)
        if mech_arr is not None:
            cur[:, n_s:n_c] = mech_arr[s:e].astype(np.float32)
        cur[:, n_c] = ooq_p_fp[s:e]
        cur[:, n_c + 1] = ooq_q_fp[s:e]

        if want_fp is None:
            pv, qv = _eval_suite_on_chunk(suite, cur, true_pi)
            p_full[s:e] = pv
            q_full[s:e] = qv
        else:
            sel = want_fp[s:e]
            pv, qv = _eval_suite_on_chunk(suite, cur[sel], true_pi)
            idx_g = np.flatnonzero(sel) + s
            p_full[idx_g] = pv
            q_full[idx_g] = qv

    drop_file_cache(base_path)
    extra_fn = getattr(extra_mm, "filename", None)
    if extra_fn:
        drop_file_cache(Path(extra_fn))
    if full_mask:
        return p_full, q_full
    return p_full[row_indices], q_full[row_indices]


DFSD_STAGE2_NAMES = [
    "s1_p_raw",
    "s1_p_logit",
    "s1_q_raw",
    "s1_p_gauss1p5",
    "s1_p_gauss4",
    "s1_p_gauss10",
    "s1_line_max_7px",
    "s1_line_max_17px",
    "s1_line_aniso_ratio",
    "s1_perp_peak_excess",
    "s1_sato_tubularity",
    "s1_q_gauss3",
    "s1_q_line_17px",
    "ooq_p_phys",
    "ooq_q_phys",
    "ooq_q_ridge_sharp",
    "ctx_lidar_present",
    "ctx_scarp_step",
    "ctx_dem10_step",
    "ctx_hydro_vent",
    "ctx_mountain_wall",
]


def extract_dfsd_stage2_features(
    p1_fp: np.ndarray,
    q1_fp: np.ndarray,
    ooq_p_fp: np.ndarray,
    ooq_q_fp: np.ndarray,
    footprint: np.ndarray,
    ctx5_fp: np.ndarray,
) -> np.ndarray:
    H, W = footprint.shape
    n_fp = int(footprint.sum())
    p2d = np.zeros((H, W), dtype=np.float32)
    q2d = np.zeros((H, W), dtype=np.float32)
    ooq2d = np.zeros((H, W), dtype=np.float32)
    p2d[footprint] = p1_fp
    q2d[footprint] = q1_fp
    ooq2d[footprint] = ooq_q_fp

    out = np.empty((n_fp, len(DFSD_STAGE2_NAMES)), dtype=np.float16)
    p_clip = np.clip(p1_fp, 1e-6, 1.0 - 1e-6)
    out[:, 0] = p1_fp.astype(np.float16)
    out[:, 1] = np.clip(np.log(p_clip / (1.0 - p_clip)), -20.0, 20.0).astype(np.float16)
    out[:, 2] = q1_fp.astype(np.float16)

    g08 = ndi.gaussian_filter(p2d, 0.8, mode="constant", cval=0.0)
    g15 = ndi.gaussian_filter(p2d, 1.5, mode="constant", cval=0.0)
    g4 = ndi.gaussian_filter(p2d, 4.0, mode="constant", cval=0.0)
    g10 = ndi.gaussian_filter(p2d, 10.0, mode="constant", cval=0.0)
    qg1 = ndi.gaussian_filter(q2d, 1.0, mode="constant", cval=0.0)
    ooq_g4 = ndi.gaussian_filter(ooq2d, 4.0, mode="constant", cval=0.0)

    out[:, 3] = g15[footprint].astype(np.float16)
    out[:, 4] = g4[footprint].astype(np.float16)
    out[:, 5] = g10[footprint].astype(np.float16)

    max7 = np.zeros((H, W), dtype=np.float32)
    max17 = np.zeros((H, W), dtype=np.float32)
    min17 = np.full((H, W), 1e9, dtype=np.float32)
    q_line17 = np.zeros((H, W), dtype=np.float32)
    ooq_line9 = np.zeros((H, W), dtype=np.float32)

    for az in (0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5):
        l7 = _sparse_line_integral(g08, half_span=3, step=1, angle_deg=az)
        l17 = _sparse_line_integral(g15, half_span=8, step=2, angle_deg=az)
        ql17 = _sparse_line_integral(qg1, half_span=8, step=2, angle_deg=az)
        ol9 = _sparse_line_integral(ooq2d, half_span=4, step=1, angle_deg=az)
        max7 = np.maximum(max7, l7)
        max17 = np.maximum(max17, l17)
        min17 = np.minimum(min17, l17)
        q_line17 = np.maximum(q_line17, ql17)
        ooq_line9 = np.maximum(ooq_line9, ol9)

    hyy = ndi.gaussian_filter(g15, 1.0, order=(2, 0), mode="nearest")
    hxx = ndi.gaussian_filter(g15, 1.0, order=(0, 2), mode="nearest")
    hxy = ndi.gaussian_filter(g15, 1.0, order=(1, 1), mode="nearest")
    tr = hxx + hyy
    disc = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy * hxy, 0.0))
    sato = np.maximum(-0.5 * (tr - disc), 0.0)

    out[:, 6] = max7[footprint].astype(np.float16)
    out[:, 7] = max17[footprint].astype(np.float16)
    out[:, 8] = np.clip(max17[footprint] / (min17[footprint] + 1e-4), 0.0, 500.0).astype(np.float16)
    out[:, 9] = (max7[footprint] - g4[footprint]).astype(np.float16)
    out[:, 10] = sato[footprint].astype(np.float16)
    out[:, 11] = ndi.gaussian_filter(q2d, 3.0, mode="constant", cval=0.0)[footprint].astype(np.float16)
    out[:, 12] = q_line17[footprint].astype(np.float16)
    out[:, 13] = ooq_p_fp.astype(np.float16)
    out[:, 14] = ooq_q_fp.astype(np.float16)
    out[:, 15] = (ooq_line9[footprint] - ooq_g4[footprint]).astype(np.float16)
    out[:, 16:21] = ctx5_fp.astype(np.float16)
    return out


def fit_dfsd_stage2_dual_heads(
    S2: np.ndarray,
    draw0_ref: dict[str, Any],
    train_mask_fp: np.ndarray,
    lidar_fp: np.ndarray,
    seed: int = 79,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed + 900)
    elig = draw0_ref["active_fp"] & train_mask_fp
    clean_far = draw0_ref["clean_far_fp"]
    y = draw0_ref["y_exact_fp"]
    q = draw0_ref["q_300m_fp"].astype(np.float32)

    pos_idx = np.flatnonzero(elig & y)
    halo_pool = np.flatnonzero(elig & (~y) & (q > 0.0))
    far_pool = np.flatnonzero(elig & (~y) & (q == 0.0))
    nh = min(halo_pool.size, 32_000)
    nf = min(far_pool.size, 135_000)
    sh = rng.choice(halo_pool, size=nh, replace=False) if nh > 0 else np.empty(0, dtype=np.int64)
    sf = rng.choice(far_pool, size=nf, replace=False) if nf > 0 else np.empty(0, dtype=np.int64)

    idx = np.sort(np.concatenate([pos_idx, sh, sf]))
    X2 = S2[idx].astype(np.float32)
    y2 = y[idx].astype(np.int32)
    q2 = q[idx]

    is_pos = y[idx]
    is_halo = (~is_pos) & (q2 > 0.0)
    wh = float(halo_pool.size / max(nh, 1)) if nh > 0 else 1.0
    wf = float(far_pool.size / max(nf, 1)) if nf > 0 else 1.0
    w2 = np.where(is_pos, 1.0, np.where(is_halo, wh, wf)).astype(np.float32)
    w2_cls = np.clip(w2, 1.0, 140.0).astype(np.float32)

    true_pi = float(pos_idx.size / max(int(elig.sum()), 1))
    sample_pi = float(np.sum(w2_cls * y2) / max(float(np.sum(w2_cls)), 1e-9))

    scaler = StandardScaler()
    X2_sc = scaler.fit_transform(X2)

    mlp_p = MLPClassifier(hidden_layer_sizes=(24, 12), alpha=3.0, batch_size=2048, max_iter=15, early_stopping=True, tol=1e-3, random_state=seed + 1)
    mlp_p.fit(X2_sc, y2)
    mlp_pi = float(y2.mean())

    lgb_p = lgb.LGBMClassifier(
        n_estimators=125, learning_rate=0.058, num_leaves=25, max_depth=5, min_child_samples=260,
        max_bin=127, colsample_bytree=0.78, subsample=0.80, subsample_freq=1, reg_alpha=5.0, reg_lambda=25.0, n_jobs=2, random_state=seed + 3, verbose=-1
    )
    lgb_p.fit(X2, y2, sample_weight=w2_cls)

    lgb_q = lgb.LGBMRegressor(
        n_estimators=130, learning_rate=0.058, num_leaves=29, max_depth=5, min_child_samples=240,
        max_bin=127, colsample_bytree=0.78, subsample=0.80, subsample_freq=1, reg_alpha=5.0, reg_lambda=25.0, n_jobs=2, random_state=seed + 7, verbose=-1
    )
    lgb_q.fit(X2, q2, sample_weight=w2)

    ridge_q = Ridge(alpha=300.0)
    ridge_q.fit(X2_sc, q2, sample_weight=w2)

    scales: dict[str, tuple[float, float]] = {}
    for dom_key, dom_m in (("lidar", lidar_fp), ("blind", ~lidar_fp)):
        dom_elig = np.flatnonzero(elig & dom_m)
        if dom_elig.size < 200:
            scales[dom_key] = (1.0, 1.0)
            continue
        cal_idx = np.sort(rng.choice(dom_elig, size=min(160_000, dom_elig.size), replace=False))
        cal_X = S2[cal_idx].astype(np.float32)
        cal_sc = scaler.transform(cal_X)
        rp = 0.68 * _prior_correct(lgb_p.booster_.predict(cal_X, num_threads=2), true_pi, sample_pi) + 0.32 * _prior_correct(
            mlp_p.predict_proba(cal_sc)[:, 1], true_pi, mlp_pi
        )
        rq = np.clip(0.82 * lgb_q.booster_.predict(cal_X, num_threads=2) + 0.18 * ridge_q.predict(cal_sc), 0.0, 1.0)
        sp = float(np.clip(y[cal_idx].mean() / max(float(rp.mean()), 1e-8), 0.40, 3.6))
        sq = float(np.clip(q[cal_idx].mean() / max(float(rq.mean()), 1e-8), 0.40, 3.6))
        scales[dom_key] = (sp, sq)

    return {
        "scaler": scaler,
        "mlp_p": mlp_p,
        "lgb_p": lgb_p,
        "lgb_q": lgb_q,
        "ridge_q": ridge_q,
        "scales": scales,
        "true_pi": true_pi,
        "sample_pi": sample_pi,
        "mlp_pi": mlp_pi,
    }


def predict_dfsd_stage2_dual_heads(
    s2_model: dict[str, Any],
    S2: np.ndarray,
    lidar_fp: np.ndarray,
    row_indices: np.ndarray,
    chunk_size: int = 450_000,
) -> tuple[np.ndarray, np.ndarray]:
    n = row_indices.size
    p_out = np.zeros(n, dtype=np.float32)
    q_out = np.zeros(n, dtype=np.float32)
    tpi, spi, mpi = s2_model["true_pi"], s2_model["sample_pi"], s2_model["mlp_pi"]
    sp_l, sq_l = s2_model["scales"]["lidar"]
    sp_b, sq_b = s2_model["scales"]["blind"]

    for s in range(0, n, chunk_size):
        e = min(s + chunk_size, n)
        rsub = row_indices[s:e]
        sub = S2[rsub].astype(np.float32)
        sc = s2_model["scaler"].transform(sub)
        rp = 0.68 * _prior_correct(s2_model["lgb_p"].booster_.predict(sub, num_threads=2), tpi, spi) + 0.32 * _prior_correct(
            s2_model["mlp_p"].predict_proba(sc)[:, 1], tpi, mpi
        )
        rq = np.clip(0.82 * s2_model["lgb_q"].booster_.predict(sub, num_threads=2) + 0.18 * s2_model["ridge_q"].predict(sc), 0.0, 1.0)
        lid_m = lidar_fp[rsub]
        sp_vec = np.where(lid_m, sp_l, sp_b).astype(np.float32)
        sq_vec = np.where(lid_m, sq_l, sq_b).astype(np.float32)
        p_out[s:e] = np.clip(rp * sp_vec, 1e-7, 0.95).astype(np.float32)
        q_out[s:e] = np.clip(rq * sq_vec, 0.0, 1.0).astype(np.float32)
    return p_out, q_out


def run_dfsd_quadrant_nested_oof(
    quad_fp: np.ndarray,
    lidar_fp: np.ndarray,
    footprint: np.ndarray,
    base_mm: np.memmap,
    extra_mm: np.memmap,
    base_path: Path,
    ctx5_fp: np.ndarray,
    shards: dict[int, dict[str, Any]],
    draw0_ref: dict[str, Any],
    pair_cache: dict[tuple[int, int], dict[int, tuple[np.ndarray, np.ndarray]]],
    test_mech_fp: np.ndarray | None,
    use_mechanics: bool,
    seed: int = 79,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_fp = int(footprint.sum())
    mech_d0 = draw0_ref["mech_fp16"] if use_mechanics else None
    q_rows = {q: np.flatnonzero(quad_fp == q) for q in range(4)}

    pair_preds: dict[tuple[int, int], dict[int, tuple[np.ndarray, np.ndarray]]] = {}
    for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
        rem_qs = [c for c in range(4) if c not in (a, b)]
        rem_pair = (rem_qs[0], rem_qs[1])
        ooq_p_ab = np.zeros(n_fp, dtype=np.float32)
        ooq_q_ab = np.zeros(n_fp, dtype=np.float32)
        for u in (a, b):
            ooq_p_ab[q_rows[u]], ooq_q_ab[q_rows[u]] = pair_cache[rem_pair][u]
        for c in rem_qs:
            ooq_p_ab[q_rows[c]], ooq_q_ab[q_rows[c]] = pair_cache[(a, b)][c]

        X_ab, y_ab, q_ab, w_ab, tpi = _stack_dfsd_shards(shards, [a, b], use_mechanics, ooq_p_ab, ooq_q_ab)
        s_ab = fit_dfsd_stage1(X_ab, y_ab, q_ab, w_ab, seed=seed + 10 * a + b)
        del X_ab, y_ab, q_ab, w_ab
        rem_rows = np.sort(np.concatenate([q_rows[c] for c in rem_qs]))
        p_rem, q_rem = predict_dfsd_stage1_rows(s_ab, base_mm, extra_mm, base_path, mech_d0, ooq_p_ab, ooq_q_ab, rem_rows, tpi)
        p_tmp = np.zeros(n_fp, dtype=np.float32)
        q_tmp = np.zeros(n_fp, dtype=np.float32)
        p_tmp[rem_rows] = p_rem
        q_tmp[rem_rows] = q_rem
        pair_preds[(a, b)] = {c: (p_tmp[q_rows[c]], q_tmp[q_rows[c]]) for c in rem_qs}
        del s_ab, p_rem, q_rem, p_tmp, q_tmp, ooq_p_ab, ooq_q_ab
        gc.collect()

    outer_p1 = np.zeros(n_fp, dtype=np.float32)
    outer_q1 = np.zeros(n_fp, dtype=np.float32)
    outer_ooq_p = np.zeros(n_fp, dtype=np.float32)
    outer_ooq_q = np.zeros(n_fp, dtype=np.float32)
    for q_test in range(4):
        tr_qs = [q for q in range(4) if q != q_test]
        ooq_p_q, ooq_q_q = assemble_ooq_physics_for_context(pair_cache, quad_fp, excluded_test_quad=q_test)
        outer_ooq_p[q_rows[q_test]] = ooq_p_q[q_rows[q_test]]
        outer_ooq_q[q_rows[q_test]] = ooq_q_q[q_rows[q_test]]
        X_3, y_3, q_3, w_3, tpi3 = _stack_dfsd_shards(shards, tr_qs, use_mechanics, ooq_p_q, ooq_q_q)
        s_3 = fit_dfsd_stage1(X_3, y_3, q_3, w_3, seed=seed + 100 + q_test)
        del X_3, y_3, q_3, w_3
        outer_p1[q_rows[q_test]], outer_q1[q_rows[q_test]] = predict_dfsd_stage1_rows(
            s_3, base_mm, extra_mm, base_path, test_mech_fp if use_mechanics else None, ooq_p_q, ooq_q_q, q_rows[q_test], tpi3
        )
        del s_3, ooq_p_q, ooq_q_q
        gc.collect()

    S2_outer_eval = extract_dfsd_stage2_features(outer_p1, outer_q1, outer_ooq_p, outer_ooq_q, footprint, ctx5_fp)
    del outer_p1, outer_q1
    gc.collect()

    pair_avg_p1 = np.zeros(n_fp, dtype=np.float32)
    pair_avg_q1 = np.zeros(n_fp, dtype=np.float32)
    for q_val in range(4):
        others = [q for q in range(4) if q != q_val]
        for sp_pair in ((others[0], others[1]), (others[0], others[2]), (others[1], others[2])):
            pair_avg_p1[q_rows[q_val]] += pair_preds[sp_pair][q_val][0] / 3.0
            pair_avg_q1[q_rows[q_val]] += pair_preds[sp_pair][q_val][1] / 3.0
    ooq_p_inner, ooq_q_inner = assemble_ooq_physics_for_context(pair_cache, quad_fp, excluded_test_quad=None)
    S2_pair_oof = extract_dfsd_stage2_features(pair_avg_p1, pair_avg_q1, ooq_p_inner, ooq_q_inner, footprint, ctx5_fp)
    del pair_avg_p1, pair_avg_q1, pair_preds, ooq_p_inner, ooq_q_inner
    gc.collect()

    p2_test_all = np.zeros(n_fp, dtype=np.float32)
    q2_test_all = np.zeros(n_fp, dtype=np.float32)
    p2_tr_avg = np.zeros(n_fp, dtype=np.float32)
    q2_tr_avg = np.zeros(n_fp, dtype=np.float32)

    for q_test in range(4):
        tr_mask = quad_fp != q_test
        s2_m = fit_dfsd_stage2_dual_heads(S2_pair_oof, draw0_ref, tr_mask, lidar_fp, seed=seed + 300 + q_test)
        p2_tr_avg[q_rows[q_test]], q2_tr_avg[q_rows[q_test]] = predict_dfsd_stage2_dual_heads(
            s2_m, S2_pair_oof, lidar_fp, q_rows[q_test]
        )
        p2_test_all[q_rows[q_test]], q2_test_all[q_rows[q_test]] = predict_dfsd_stage2_dual_heads(
            s2_m, S2_outer_eval, lidar_fp, q_rows[q_test]
        )
        del s2_m
        gc.collect()

    del S2_pair_oof, S2_outer_eval
    gc.collect()
    return p2_test_all, q2_test_all, p2_tr_avg, q2_tr_avg


def _submodular_stage(
    p_eff: np.ndarray,
    q_clean: np.ndarray,
    eligible_mask: np.ndarray,
    cov_pad: np.ndarray,
    blocked_pad: np.ndarray,
    lambda_fp: float,
    min_sep_px: float,
    max_add: int,
    min_add: int = 0,
    candidate_pool: int = 380_000,
) -> list[tuple[int, int]]:
    H, W = p_eff.shape
    pad = 3
    p_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    p_pad[pad : pad + H, pad : pad + W] = p_eff

    dy = metric.OFF_DY.tolist()
    dx = metric.OFF_DX.tolist()
    kw = metric.OFF_K.tolist()
    n_off = len(kw)

    init_tp = np.zeros((H, W), dtype=np.float64)
    for oy, ox, k_val in zip(dy, dx, kw):
        rem_k = np.maximum(0.0, k_val - cov_pad[pad + oy : pad + oy + H, pad + ox : pad + ox + W])
        init_tp += rem_k * p_pad[pad + oy : pad + oy + H, pad + ox : pad + ox + W]

    pen_arr = float(lambda_fp) * (1.0 - q_clean)
    u0 = init_tp - pen_arr

    avail_now = eligible_mask & (~blocked_pad[pad : pad + H, pad : pad + W]) & (init_tp > 0.0)
    valid_idx = np.flatnonzero(avail_now)
    if valid_idx.size == 0 or max_add <= 0:
        return []
    if valid_idx.size > candidate_pool:
        sub = u0.ravel()[valid_idx]
        keep = np.argpartition(sub, -candidate_pool)[-candidate_pool:]
        valid_idx = valid_idx[keep]

    ys = (valid_idx // W + pad).tolist()
    xs = (valid_idx % W + pad).tolist()
    pens = pen_arr.ravel()[valid_idx].tolist()
    u_vals = u0.ravel()[valid_idx].tolist()

    r_sep = int(np.ceil(min_sep_px)) if min_sep_px > 1.01 else 0
    if r_sep > 0:
        sy_g, sx_g = np.mgrid[-r_sep : r_sep + 1, -r_sep : r_sep + 1]
        sep_m = (sy_g * sy_g + sx_g * sx_g) < (min_sep_px * min_sep_px)
        sep_dy = sy_g[sep_m].tolist()
        sep_dx = sx_g[sep_m].tolist()
    else:
        sep_dy, sep_dx = [0], [0]

    heap: list[tuple[float, int]] = [(-u_vals[i], i) for i in range(len(u_vals))]
    heapq.heapify(heap)
    added = 0
    out_coords: list[tuple[int, int]] = []
    while added < max_add and heap:
        _, i = heapq.heappop(heap)
        cy, cx = ys[i], xs[i]
        if blocked_pad[cy, cx]:
            continue
        gain = 0.0
        for m in range(n_off):
            ny, nx = cy + dy[m], cx + dx[m]
            k_m = kw[m]
            cur_c = cov_pad[ny, nx]
            if k_m > cur_c:
                gain += p_pad[ny, nx] * (k_m - cur_c)
        exact_u = gain - pens[i]
        if added >= min_add and exact_u <= 0.0:
            break
        if not heap or (-exact_u <= heap[0][0] + 1e-14):
            out_coords.append((cy - pad, cx - pad))
            for m in range(n_off):
                ny, nx = cy + dy[m], cx + dx[m]
                k_m = kw[m]
                if k_m > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = k_m
            for sdy, sdx in zip(sep_dy, sep_dx):
                blocked_pad[cy + sdy, cx + sdx] = True
            added += 1
        else:
            heapq.heappush(heap, (-exact_u, i))
    return out_coords


def dfsd_charnes_cooper_emit(
    p_dual_2d: np.ndarray,
    q_dual_2d: np.ndarray,
    p_phys_2d: np.ndarray,
    dist_vis_2d: np.ndarray,
    allowed_mask: np.ndarray,
    lambda_fp: float = 0.0028,
    min_sep_px: float = 1.9,
    max_budget: int = 38_500,
    far_blind_share: float = 0.05,
    far_dist_px: float = 15.0,
) -> np.ndarray:
    H, W = p_dual_2d.shape
    pad = 3
    q_clean = np.clip(q_dual_2d, 0.0, 1.0).astype(np.float64)
    q_sharp = np.maximum(0.0, q_clean - 0.50 * ndi.gaussian_filter(q_clean.astype(np.float32), 2.5))
    p_raw = np.clip(p_dual_2d, 0.0, 1.0).astype(np.float64)
    p_floor = float(np.percentile(p_raw[allowed_mask], 55.0))
    p_base = np.maximum(0.0, p_raw - p_floor)
    mass_p = float(p_base[allowed_mask].sum())
    mass_q = float(q_sharp[allowed_mask].sum())
    q_scaled = q_sharp * (mass_p / max(mass_q, 1e-8))
    p_eff_main = 0.65 * p_base + 0.35 * q_scaled

    cov_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    blocked_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool)

    main_cap = int(round((1.0 - far_blind_share) * max_budget))
    far_cap = int(max_budget - main_cap)

    coords_main = _submodular_stage(
        p_eff_main,
        q_clean,
        allowed_mask,
        cov_pad,
        blocked_pad,
        lambda_fp=lambda_fp,
        min_sep_px=min_sep_px,
        max_add=main_cap,
        min_add=min(20_000, main_cap),
    )

    out = np.zeros((H, W), dtype=np.float32)
    for ry, rx in coords_main:
        out[ry, rx] = 1.0

    if far_cap > 0:
        p_phys_clean = np.clip(p_phys_2d, 0.0, 1.0).astype(np.float64)
        p_far_eff = 0.55 * p_eff_main + 0.45 * p_phys_clean
        far_elig = allowed_mask & (dist_vis_2d > float(far_dist_px))
        coords_far = _submodular_stage(
            p_far_eff,
            q_clean,
            far_elig,
            cov_pad,
            blocked_pad,
            lambda_fp=0.0,
            min_sep_px=max(min_sep_px, 2.8),
            max_add=far_cap,
            min_add=far_cap,
        )
        for ry, rx in coords_far:
            out[ry, rx] = 1.0

    return out
