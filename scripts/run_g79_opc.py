#!/usr/bin/env python3
"""Run the preregistered G79-OPC lane (registry/preregistration_g79_opc.json).

Stages (checkpointed under .cache/opc/):
  phys   build the label-free physics feature memmap (footprint rows)
  seed20 / seed30   leakage canaries + EXP-OPC-1, C-ISO, EXP-OPC-2, C0 on the shared
                    gems57-pooled-hide-v2 buffered whole-component holdout
  live   EXP-OPC-3: live fit on the full catalogue + continuous surface + placement

Shared tools reused, not forked: holdout.buffered_component_draw,
evaluate_holdout.evaluate / pooled_summary, emit.greedy_allocate,
submission_writer.write_submission, uniqueness.compare_array_to_registry_d2.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import emit, evaluate_holdout, holdout  # noqa: E402
from gems57.grid import Grid  # noqa: E402
from gems79 import opc  # noqa: E402

RAW = ROOT / "data/raw"
CACHE = ROOT / ".cache/opc"
EVID = ROOT / "evidence/opc"
PRE = json.loads((ROOT / "registry/preregistration_g79_opc.json").read_text())
HP = PRE["mechanism"]["fixed_hyperparameters"]
LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "valid"]
NEG_PER_QUAD = 60_000
N_DRAWS = 2


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load_grid():
    with rasterio.open(RAW / "sample_submission.tif") as s:
        fp = np.isfinite(s.read(1))
        crs, tr = s.crs, s.transform
    with rasterio.open(RAW / "existing_faults.tif") as s:
        cat = (s.read(1) > 0) & fp
    return Grid(fp, cat, str(crs), tr, fp.shape[0], fp.shape[1])


def phys_names():
    with rasterio.open(RAW / "training_features.tif") as s:
        tf = [d.split(" - ")[0] for d in s.descriptions]
    return (tf + [f"lidar_{b}" for b in LIDAR_BANDS] + ["rad_K", "rad_Th", "rad_U", "rad_TC",
            "ext_ThK", "ext_UK", "ext_UTh", "ext_TMI_up150", "log1p_road_m", "log1p_d_sgmc_px",
            "grad_det_elev_s2", "grad_iso_grav_s2", "grad_rtp_s2"])


def build_phys(grid):
    CACHE.mkdir(parents=True, exist_ok=True)
    names = phys_names()
    path = CACHE / "phys.f32"
    done = CACHE / "phys.json"
    if done.exists():
        return names
    fp = grid.footprint
    n = int(fp.sum())
    mm = np.memmap(path, dtype=np.float32, mode="w+", shape=(n, len(names)))
    j = 0
    keep = {}
    with rasterio.open(RAW / "training_features.tif") as s:
        for b in range(1, 20):
            a = s.read(b).astype(np.float32)
            a[~np.isfinite(a) | (np.abs(a) > 1e30)] = np.nan
            if b in (12, 13, 2):
                keep[b] = a.copy()
            mm[:, j] = a[fp]; j += 1
            del a
    lidar = RAW / "external/lidar_scarp_features_u8.tif"
    with rasterio.open(lidar) as s:
        desc = list(s.descriptions)
        for name in LIDAR_BANDS:
            a = s.read(desc.index(name) + 1).astype(np.float32)
            a[a == 0] = np.nan
            mm[:, j] = a[fp]; j += 1
    for f in ("geodawn_rad_u8.tif", "geodawn_extensions_u8.tif"):
        with rasterio.open(RAW / "external" / f) as s:
            for b in range(1, 5):
                a = s.read(b).astype(np.float32)
                a[a == 0] = np.nan
                mm[:, j] = a[fp]; j += 1
    with rasterio.open(RAW / "external/tiger_road_distance_m.tif") as s:
        a = s.read(1).astype(np.float32)
        a[~np.isfinite(a) | (a < 0)] = np.nan
        mm[:, j] = np.log1p(a[fp]); j += 1
    with rasterio.open(RAW / "external/derived_sgmc_faults_100m_u8.tif") as s:
        sg = s.read(1) > 0
    mm[:, j] = np.log1p(ndi.distance_transform_edt(~sg)[fp]).astype(np.float32); j += 1
    for b in (12, 13, 2):
        a = keep[b]
        filled = np.where(np.isfinite(a), a, np.nanmedian(a)).astype(np.float32)
        sm = ndi.gaussian_filter(filled, 2)
        g = np.hypot(ndi.sobel(sm, 0), ndi.sobel(sm, 1)).astype(np.float32)
        g[~np.isfinite(a)] = np.nan
        mm[:, j] = g[fp]; j += 1
    assert j == len(names), (j, len(names))
    mm.flush(); del mm
    done.write_text(json.dumps(dict(names=names, rows=n)) + "\n")
    log("phys memmap built", n, len(names))
    return names


def lidar_phi(grid):
    p = CACHE / "lidar_phi.npz"
    if p.exists():
        z = np.load(p)
        return z["phi"], json.loads(str(z["meta"]))
    with rasterio.open(RAW / "external/lidar_scarp_features_u8.tif") as s:
        desc = list(s.descriptions)
        st = s.read(desc.index("strike") + 1)
        sp = s.read(desc.index("step_max") + 1)
        va = s.read(desc.index("valid") + 1)
    phi, meta = opc.lidar_strike_phi(st, sp, va)
    np.savez_compressed(p, phi=phi, meta=json.dumps(meta))
    return phi, meta


def geom_fp(mask, grid, lphi, seed, tag):
    """Geometry features restricted to footprint rows, cached per visible-set tag."""
    p = CACHE / f"geom_{tag}.npz"
    if p.exists():
        z = np.load(p, allow_pickle=False)
        return z["G"], json.loads(str(z["meta"]))
    t0 = time.time()
    feats, meta = opc.geometry_features(mask, grid.footprint, lphi, seed=seed)
    G = np.column_stack([feats[n][grid.footprint] for n in opc.GEOM_NAMES]).astype(np.float32)
    del feats; gc.collect()
    meta = {k: v for k, v in meta.items() if k != "w_grid"} | {"w_grid": meta["w_grid"]}
    np.savez(p, G=G, meta=json.dumps(meta))
    log(f"geometry {tag}: {time.time()-t0:.0f}s")
    return G, meta


def sim_draws(visible, grid, base_seed, lphi, tag):
    """Simulated buffered whole-component hides on ``visible`` (training labels only)."""
    draws = []
    for d in range(N_DRAWS):
        g2 = Grid(grid.footprint, visible, grid.crs, grid.transform, grid.height, grid.width)
        folds, _ = holdout.buffered_component_draw(g2, seed=base_seed + d, hide_frac=0.2,
                                                   buffer_px=3, boundary_px=12)
        hid = folds[0]["hidden_all"]
        vis_sim = folds[0]["visible"]
        regions = np.stack([f["region"] for f in folds])
        G, meta = geom_fp(vis_sim, grid, lphi, seed=7907 + d, tag=f"{tag}_sim{d}")
        dsim = ndi.distance_transform_edt(~vis_sim)
        draws.append(dict(hidden=hid, regions=regions, G=G, dsim=dsim, meta=meta,
                          n_hidden=int(hid.sum())))
    return draws


def assemble(draws, grid, quad, train_quads, phys, rng, known):
    """Training rows (footprint-row indices) for the given quadrants."""
    fp = grid.footprint
    rowid = np.full(fp.shape, -1, np.int64)
    rowid[fp] = np.arange(int(fp.sum()))
    Xs, ys, ws = [], [], []
    stats = []
    for dr in draws:
        for q in train_quads:
            reg = dr["regions"][q]
            pos = dr["hidden"] & reg
            # ``known`` = the catalogue the lane is allowed to see (visible V in the
            # holdout, full catalogue live). Using grid.catalogue here would drop the
            # real withheld truth from the negatives (D-OPC-2).
            negpool = reg & fp & ~known & (dr["dsim"] > 3)
            negpool &= ~pos
            pidx = rowid[pos]
            nidx_all = np.flatnonzero(negpool.ravel())
            k = min(NEG_PER_QUAD, nidx_all.size)
            nsel = rng.choice(nidx_all, size=k, replace=False)
            nidx = rowid.ravel()[nsel]
            idx = np.concatenate([pidx, nidx])
            order = np.argsort(idx)
            idx = idx[order]
            y = np.concatenate([np.ones(pidx.size), np.zeros(nidx.size)])[order]
            frac = k / max(nidx_all.size, 1)
            w = np.where(y == 1, 1.0, 1.0)
            X = np.hstack([phys[idx], dr["G"][idx]])
            Xs.append(X); ys.append(y); ws.append(w)
            stats.append(dict(quad=int(q), pos=int(pidx.size), neg=int(k), neg_pool=int(nidx_all.size), keep_frac=frac))
    pos_total = sum(s["pos"] for s in stats)
    neg_total = sum(s["neg"] for s in stats)
    pool_total = sum(s["neg_pool"] for s in stats)
    f_neg = neg_total / pool_total
    return np.vstack(Xs), np.concatenate(ys), np.concatenate(ws), dict(rows=stats, f_neg=f_neg,
                                                                        pos=pos_total, neg=neg_total)


def fit(X, y, cols, seed):
    import lightgbm as lgb
    m = lgb.LGBMClassifier(objective="binary", num_leaves=HP["num_leaves"],
                           learning_rate=HP["learning_rate"], n_estimators=HP["n_estimators"],
                           min_child_samples=HP["min_child_samples"], subsample=HP["subsample"],
                           subsample_freq=1, colsample_bytree=HP["colsample_bytree"],
                           reg_lambda=HP["reg_lambda"], n_jobs=2, random_state=seed, verbose=-1)
    m.fit(X[:, cols], y)
    return m


def prior_correct(p, f_neg):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    odds = p / (1 - p) * f_neg
    return (odds / (1 + odds)).astype(np.float32)


def place(p2d, allowed):
    k_truth = float(p2d[allowed].sum())
    alloc = emit.greedy_allocate(p2d * allowed, allowed, k_truth, max_dots=120_000)
    return alloc.emitted.astype(np.float32), dict(n_dots=alloc.n_dots, k_truth_expected=k_truth,
                                                  surrogate_dti=alloc.surrogate_dti, rounds=alloc.rounds)


def canary(phys, G, truth_fp, neg_fp, rng):
    from sklearn.metrics import roc_auc_score
    ti = np.flatnonzero(truth_fp)
    ni = np.sort(rng.choice(np.flatnonzero(neg_fp), size=min(200_000, int(neg_fp.sum())), replace=False))
    idx = np.concatenate([ti, ni])
    sub = np.hstack([phys[np.sort(idx)], G[np.sort(idx)]])
    order = np.argsort(idx); inv = np.empty_like(order); inv[order] = np.arange(idx.size)
    sub = sub[inv]
    out = {}
    for j in range(sub.shape[1]):
        v = sub[:, j]
        yv = np.concatenate([np.ones(ti.size), np.zeros(ni.size)])
        ok = np.isfinite(v)
        if ok.sum() < 100 or yv[ok].min() == yv[ok].max():
            out[j] = None
            continue
        a = roc_auc_score(yv[ok], v[ok])
        out[j] = float(max(a, 1 - a))
    return out


def run_seed(seed, grid, names_phys, lphi):
    ck = EVID / f"seed{seed}.json"
    if ck.exists():
        log("seed", seed, "checkpoint exists")
        return json.loads(ck.read_text())
    t0 = time.time()
    fp = grid.footprint
    n = int(fp.sum())
    phys = np.memmap(CACHE / "phys.f32", dtype=np.float32, mode="r", shape=(n, len(names_phys)))
    folds, quad = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    vis = folds[0]["visible"]
    hidden_all = folds[0]["hidden_all"]
    d_vis = ndi.distance_transform_edt(~vis)
    # D-OPC-2: only the VISIBLE catalogue may shape the domain; excluding the full
    # catalogue would forbid dots exactly on the withheld truth (a truth leak).
    allowed = fp & (d_vis > 3) & (quad >= 0)
    Gv, gmeta = geom_fp(vis, grid, lphi, seed=7907, tag=f"vis{seed}")
    names = names_phys + opc.GEOM_NAMES
    rng = np.random.default_rng(79_000 + seed)

    # ---- leakage canary: every feature alone vs real withheld truth ----
    truth_fp = np.zeros(n, bool); neg_fp = np.zeros(n, bool)
    regs_any = np.zeros(fp.shape, bool)
    for f in folds:
        regs_any |= f["region"]
    truth_fp[:] = (hidden_all & regs_any)[fp]
    neg_fp[:] = (allowed & regs_any & ~hidden_all)[fp]
    can = canary(phys, Gv, truth_fp, neg_fp, rng)
    canary_named = {names[j]: v for j, v in can.items()}
    max_auc = max(v for v in canary_named.values() if v is not None)
    log(f"seed {seed} canary max symmetric AUC {max_auc:.4f}")

    draws = sim_draws(vis, grid, 9000 + 10 * seed, lphi, tag=f"s{seed}")
    quad_fp = quad[fp]
    col_all = list(range(len(names)))
    col_iso = [len(names_phys) + opc.GEOM_NAMES.index(c) for c in opc.ISO_NAMES]
    col_geo = [len(names_phys) + opc.GEOM_NAMES.index(c) for c in opc.OPC_GEO_NAMES]
    arms = {"EXP-OPC-2_full": col_all, "EXP-OPC-1_geometry_oriented": col_geo, "C-ISO_geometry_isotropic": col_iso}
    P = {a: np.zeros(fp.shape, np.float32) for a in arms}
    train_meta = {}
    importances = {}
    for q in range(4):
        tq = [k for k in range(4) if k != q]
        X, y, w, st = assemble(draws, grid, quad, tq, phys, rng, vis)
        rows_q = np.flatnonzero(quad_fp == q)
        Xq = np.hstack([phys[rows_q], Gv[rows_q]])
        train_meta[q] = st
        for a, cols in arms.items():
            m = fit(X, y, cols, seed * 10 + q)
            pq = prior_correct(m.predict_proba(Xq[:, cols])[:, 1], st["f_neg"])
            tmp = np.zeros(n, np.float32); tmp[rows_q] = pq
            P[a][fp] += tmp
            if a == "EXP-OPC-2_full":
                imp = m.booster_.feature_importance("gain")
                importances[q] = {names[c]: float(v) for c, v in zip(cols, imp)}
            del m
        del X, y, Xq; gc.collect()
        log(f"seed {seed} fold {q} done ({time.time()-t0:.0f}s)")
    preds, place_meta = {}, {}
    for a in arms:
        preds[a], place_meta[a] = place(P[a], allowed)
        log(f"seed {seed} {a}: {place_meta[a]['n_dots']} dots")
    n_c0 = int(preds["EXP-OPC-2_full"].sum())
    c0 = np.zeros(fp.shape, np.float32)
    c0.ravel()[rng.choice(np.flatnonzero(allowed.ravel()), size=n_c0, replace=False)] = 1.0
    preds["C0_random_same_count"] = c0
    terms, per_fold = {}, {}
    for a, pr in preds.items():
        acc = None; fl = []
        for fi, f in enumerate(folds):
            r, t = evaluate_holdout.evaluate(pr, f, fp)
            fl.append(dict(fold=fi, dti=round(float(r["dti"]), 6), n_truth=r["n_truth"], n_emitted=r["n_emitted"]))
            acc = t if acc is None else acc + t
        terms[a] = acc; per_fold[a] = fl
    summ = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810 + seed, candidate="EXP-OPC-2_full")
    summ["per_fold"] = per_fold
    # paired anisotropy test EXP-OPC-1 vs C-ISO
    aniso = evaluate_holdout.pooled_summary({k: terms[k] for k in ("EXP-OPC-1_geometry_oriented", "C-ISO_geometry_isotropic")},
                                            draws=1000, seed=620810 + seed, candidate="EXP-OPC-1_geometry_oriented")
    gain = {}
    for q, d in importances.items():
        for k, v in d.items():
            gain[k] = gain.get(k, 0.0) + v
    tot = sum(gain.values())
    gain = {k: round(v / tot, 5) for k, v in sorted(gain.items(), key=lambda kv: -kv[1])}
    out = dict(seed=seed, evidence_class="HOLDOUT-DTI", evaluator_version=summ["evaluator_version"],
               withheld_positive_pixels=summ["scores"]["EXP-OPC-2_full"]["withheld_positive_pixels"],
               official_evaluate_all=summ, anisotropy_test=aniso,
               canary=dict(max_symmetric_auc=max_auc, limit=0.90, per_feature=canary_named,
                           method="feature alone, all withheld truth in eroded regions vs <=200k allowed non-truth cells"),
               placement=place_meta, training=train_meta, gain_share_full_model=gain,
               geometry_meta={k: v for k, v in gmeta.items() if k != "w_grid"},
               elapsed_s=round(time.time() - t0, 1))
    EVID.mkdir(parents=True, exist_ok=True)
    ck.write_text(json.dumps(out, indent=1) + "\n")
    np.savez_compressed(CACHE / f"oof_seed{seed}.npz", **{a: P[a][fp].astype(np.float16) for a in arms})
    for a, s in summ["scores"].items():
        log(f"seed {seed} {a}: HOLDOUT-DTI {s['dti']:.4f} CI {s['ci95']} n={s['withheld_positive_pixels']}")
    return out


def run_live(grid, names_phys, lphi):
    out_p = CACHE / "live.npz"
    if out_p.exists():
        return
    fp = grid.footprint
    n = int(fp.sum())
    phys = np.memmap(CACHE / "phys.f32", dtype=np.float32, mode="r", shape=(n, len(names_phys)))
    cat = grid.catalogue
    _, quad = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)
    Gl, gmeta = geom_fp(cat, grid, lphi, seed=7907, tag="live")
    draws = sim_draws(cat, grid, 9900, lphi, tag="live")
    rng = np.random.default_rng(79_999)
    X, y, w, st = assemble(draws, grid, quad, [0, 1, 2, 3], phys, rng, cat)
    m = fit(X, y, list(range(X.shape[1])), 7999)
    del X, y; gc.collect()
    p = np.zeros(n, np.float32)
    for s in range(0, n, 1_000_000):
        Xs = np.hstack([phys[s:s + 1_000_000], Gl[s:s + 1_000_000]])
        p[s:s + 1_000_000] = prior_correct(m.predict_proba(Xs)[:, 1], st["f_neg"])
    P = np.zeros(fp.shape, np.float32); P[fp] = p
    d_cat = ndi.distance_transform_edt(~cat)
    allowed = fp & (d_cat > 3) & ~cat
    dots, pm = place(P, allowed)
    np.savez_compressed(out_p, P=P.astype(np.float32), dots=dots.astype(np.uint8))
    (EVID / "live_fit.json").write_text(json.dumps(dict(training=st, placement=pm,
        geometry_meta={k: v for k, v in gmeta.items() if k != "w_grid"},
        pair_correlation_excess_grid_folded_2px=gmeta["w_grid"]), indent=1) + "\n")
    log("live done", pm)


def refuse_if_closed():
    """Lane lifecycle guard: once run_card_opc.json records a terminal verdict, no rerun/retune."""
    card = Path(__file__).resolve().parents[1] / "run_card_opc.json"
    if card.exists():
        import json as _j
        v = _j.loads(card.read_text()).get("verdict")
        if v not in (None, "pending", "in_progress"):
            sys.stderr.write(f"G79-OPC is closed ({v}); do not restart, retune or repackage. No files changed.\n")
            raise SystemExit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["phys", "seed20", "seed30", "live", "all"])
    a = ap.parse_args()
    refuse_if_closed()
    CACHE.mkdir(parents=True, exist_ok=True); EVID.mkdir(parents=True, exist_ok=True)
    grid = load_grid()
    names = build_phys(grid)
    lphi, lmeta = lidar_phi(grid)
    (EVID / "lidar_strike_convention.json").write_text(json.dumps(lmeta, indent=1) + "\n")
    if a.stage in ("seed20", "all"):
        run_seed(20, grid, names, lphi)
    if a.stage in ("seed30", "all"):
        run_seed(30, grid, names, lphi)
    if a.stage in ("live", "all"):
        run_live(grid, names, lphi)


if __name__ == "__main__":
    main()
