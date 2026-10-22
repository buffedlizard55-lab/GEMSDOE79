#!/usr/bin/env python3
"""Run the preregistered G79-FSC lane (registry/preregistration_g79_fsc.json).

Stages (each writes evidence under evidence/fsc/):
  static   catalogue-free feature stack -> data/cache/fsc/static.f32 (column-major memmap)
  seed N   outer buffered draw (shared holdout.py), inner draw on the outer-visible
           catalogue, LOQO LightGBM per arm, inner-only (K, s, c) selection, outer
           shared-evaluator scores + paired block-bootstrap, leakage canaries
  live     full-catalogue model and the candidate surface / dots (data/cache/fsc/)

Fail-closed: a stage refuses to overwrite its own evidence file (no retuning).
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '2')
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
sys.path.insert(0, str(ROOT / 'src'))

from gems57 import evaluate_holdout, holdout, metric  # noqa: E402
from gems57.grid import Grid, load_grid  # noqa: E402
from gems79 import fsc  # noqa: E402

RAW = ROOT / 'data/raw'
CACHE = ROOT / 'data/cache/fsc'
EVID = ROOT / 'evidence/fsc'
PREREG = ROOT / 'registry/preregistration_g79_fsc.json'
K_GRID = (25000, 35000, 45000, 60000, 80000)
S_GRID = (2.0, 2.5, 3.0)
C_GRID = (0, 1, 2)
N_NEG = 350_000
LGB_PARAMS = dict(objective='binary', learning_rate=0.06, num_leaves=63, min_data_in_leaf=200,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
                  num_threads=2, verbose=-1, seed=79)
N_ROUNDS = 300
THVC = {20: 0.1905, 30: 0.1944}


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(*a):
    print(f'[{now()}]', *a, flush=True)


def write_once(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f'{path} exists; G79-FSC stages are write-once (no retuning)')
    path.write_text(json.dumps(obj, indent=2, allow_nan=False, default=float) + '\n')


def grid_and_fp():
    g = load_grid(RAW)
    return g, np.asarray(g.footprint, bool)


# ----------------------------------------------------------------------------- static

def static_names():
    names = [f'tf_{n}' for n in fsc.STACK_NAMES] + [f'lidar_{n}' for n in fsc.LIDAR_NAMES] + list(fsc.RAD_NAMES)
    for s in ('topo', 'grav', 'mag'):
        names += [f'{s}_c2', f'{s}_s2', f'{s}_coh', f'{s}_logE']
    names += ['lidar_c2', 'lidar_s2', 'lidar_coh', 'hess_topo_2', 'hess_topo_5', 'hess_grav_4']
    return names


def build_static():
    _, fp = grid_and_fp()
    names = static_names()
    n = int(fp.sum())
    CACHE.mkdir(parents=True, exist_ok=True)
    mm = np.lib.format.open_memmap(CACHE / 'static.npy', mode='w+', dtype=np.float32, shape=(len(names), n))
    col = {nm: i for i, nm in enumerate(names)}
    t0 = time.time()
    with rasterio.open(RAW / 'training_features.tif') as src:
        for b, nm in enumerate(fsc.STACK_NAMES, start=1):
            a = src.read(b).astype(np.float32)
            a[~np.isfinite(a) | (a < -1e30)] = np.nan
            mm[col[f'tf_{nm}']] = a[fp]
            if nm in ('det_elev', 'iso_grav_anom', 'rtp'):
                f = fsc.fill_nearest(a)
                key = {'det_elev': 'topo', 'iso_grav_anom': 'grav', 'rtp': 'mag'}[nm]
                sd, si = {'topo': (1.5, 3.0), 'grav': (2.0, 4.0), 'mag': (2.0, 4.0)}[key]
                c2, s2, coh, e = fsc.structure_tensor(f, sd, si)
                mm[col[f'{key}_c2']], mm[col[f'{key}_s2']] = c2[fp], s2[fp]
                mm[col[f'{key}_coh']], mm[col[f'{key}_logE']] = coh[fp], np.log10(e[fp] + 1e-12)
                del c2, s2, coh, e
                if key == 'topo':
                    mm[col['hess_topo_2']] = fsc.hessian_ridge(f, 2.0)[fp]
                    mm[col['hess_topo_5']] = fsc.hessian_ridge(f, 5.0)[fp]
                if key == 'grav':
                    mm[col['hess_grav_4']] = fsc.hessian_ridge(f, 4.0)[fp]
                del f
            del a
            gc.collect()
    with rasterio.open(RAW / 'external/lidar_scarp_features_u8.tif') as src:
        valid = src.read(12) > 0
        for b, nm in enumerate(fsc.LIDAR_NAMES, start=1):
            a = src.read(b).astype(np.float32)
            if nm != 'valid':
                a[~valid | (a == 0)] = np.nan
            mm[col[f'lidar_{nm}']] = a[fp]
            if nm == 'strike':
                # strike band q = 1 + round(254*deg/180); strike direction -> normal angle
                deg = (a - 1.0) / 254.0 * 180.0
                phi = np.deg2rad(deg) + np.pi / 2.0  # gradient (normal) direction
                c2, s2 = np.cos(2 * phi), np.sin(2 * phi)
                with rasterio.open(RAW / 'external/lidar_scarp_features_u8.tif') as s2src:
                    coh = s2src.read(10).astype(np.float32)
                coh = np.where(np.isfinite(a) & (coh > 0), (coh - 1.0) / 254.0, 0.0)
                c2 = np.where(np.isfinite(a), c2, 0.0)
                s2 = np.where(np.isfinite(a), s2, 0.0)
                mm[col['lidar_c2']], mm[col['lidar_s2']], mm[col['lidar_coh']] = c2[fp], s2[fp], coh[fp]
                del deg, phi, c2, s2, coh
            del a
    for path, bands, offs in ((RAW / 'external/geodawn_rad_u8.tif', 4, 0),
                              (RAW / 'external/geodawn_extensions_u8.tif', 4, 4)):
        with rasterio.open(path) as src:
            for b in range(1, bands + 1):
                a = src.read(b).astype(np.float32)
                a[a == 0] = np.nan
                mm[col[fsc.RAD_NAMES[offs + b - 1]]] = a[fp]
    mm.flush()
    meta = dict(names=names, n_footprint=n, seconds=round(time.time() - t0, 1), built_utc=now(),
                inputs_sha256={p: sha256(RAW / p) for p in ('training_features.tif', 'external/lidar_scarp_features_u8.tif',
                                                             'external/geodawn_rad_u8.tif', 'external/geodawn_extensions_u8.tif',
                                                             'existing_faults.tif', 'sample_submission.tif')})
    (CACHE / 'static_meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    log('static built', meta['seconds'], 's', len(names), 'features')


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''):
            h.update(ch)
    return h.hexdigest()


def load_static():
    meta = json.loads((CACHE / 'static_meta.json').read_text())
    mm = np.load(CACHE / 'static.npy', mmap_mode='r')
    return mm, meta['names']


# ----------------------------------------------------------------------------- features per variant

def variant_features(visible, fp, mm, names, a1=False):
    geom = fsc.geometry_features(visible, fp)
    if a1:
        geom.update(fsc.a1_features(visible, fp, unflatten(geom['fab_c2'], fp), unflatten(geom['fab_s2'], fp)))
    col = {n: i for i, n in enumerate(names)}
    edge = {}
    for s in fsc.EDGE_SOURCES:
        for k in ('c2', 's2', 'coh'):
            edge[f'{s}_{k}'] = np.asarray(mm[col[f'{s}_{k}']])
    conc = fsc.concordance_features(edge, geom)
    del edge
    geom.update(conc)
    return geom


def feature_list(arm, names):
    base = list(names) + ['log_d_vis', 'log_d_end', 'cat_dens_10', 'cat_dens_30']
    if arm == 'candidate':
        return base + ['fab_c2', 'fab_s2', 'fab_coh', 'fab_logE'] + fsc.CONCORDANCE_NAMES
    if arm == 'ablation_no_fabric':
        return base
    if arm == 'candidate_a1':
        return base + ['fab_c2', 'fab_s2', 'fab_coh', 'fab_logE'] + fsc.CONCORDANCE_NAMES + fsc.A1_NAMES
    raise ValueError(arm)


def matrix(rows, feats, mm, names, geom):
    col = {n: i for i, n in enumerate(names)}
    X = np.empty((rows.size, len(feats)), np.float32)
    for j, f in enumerate(feats):
        X[:, j] = mm[col[f], rows] if f in col else geom[f][rows]
    return X


# ----------------------------------------------------------------------------- placement / scoring

def steering(prob2d, fp, geom_full_fab, arm):
    """Doubled-angle NMS direction field (full grid)."""
    pc2, ps2, pcoh, _ = fsc.structure_tensor(prob2d, 1.0, 2.0)
    if arm not in ('candidate', 'candidate_a1'):
        return pc2, ps2
    fc2, fs2, fcoh, dens = geom_full_fab
    w = np.clip(fcoh * np.clip(dens / 0.003, 0, 1), 0, 1)
    c2 = w * fc2 + (1 - w) * pc2
    s2 = w * fs2 + (1 - w) * ps2
    return c2.astype(np.float32), s2.astype(np.float32)


def unflatten(v, fp, fill=0.0):
    a = np.full(fp.shape, fill, np.float32)
    a[fp] = v
    return a


def place_orders(prob2d, visible, fp, steer, spacing, collar, kmax):
    allowed = fp & ~visible
    if collar > 0:
        allowed &= ndi.distance_transform_edt(~visible) > collar
    ridge = fsc.fabric_normal_nms(prob2d, steer[0], steer[1], allowed)
    return fsc.greedy_spaced_order(prob2d, ridge, spacing, kmax)


def crop_eval(pred_bool, fold, fp, block=200):
    reg = fold['region']
    rows = np.flatnonzero(reg.any(axis=1)); cols = np.flatnonzero(reg.any(axis=0))
    y0, y1 = max(0, rows[0] - 6), min(fp.shape[0], rows[-1] + 7)
    x0, x1 = max(0, cols[0] - 6), min(fp.shape[1], cols[-1] + 7)
    sl = (slice(y0, y1), slice(x0, x1))
    f = dict(region=reg[sl], truth=fold['truth'][sl], masked_known=fold['masked_known'][sl], visible=fold['visible'][sl])
    return evaluate_holdout.evaluate(pred_bool[sl].astype(np.float32), f, fp[sl], block,
                                     origin=(y0, x0), global_shape=fp.shape)


def pooled_dti(pred_bool, folds, fp):
    tp = fpw = fn = 0.0
    terms = None
    for f in folds:
        r, t = crop_eval(pred_bool, f, fp)
        tp += r['tpw']; fpw += r['fpw']; fn += r['fnw']
        terms = t if terms is None else terms + t
    return tp / (tp + metric.ALPHA * fpw + metric.BETA * fn + metric.EPS), terms


# ----------------------------------------------------------------------------- seed run

def train_predict(arm, seed, fp, quad, mm, names, geom_inner, geom_outer, pos, neg_pool, rng):
    import lightgbm as lgb
    feats = feature_list(arm, names)
    p_in = np.zeros(fp.sum(), np.float32)
    p_out = np.zeros(fp.sum(), np.float32)
    quad_fp = quad[fp]
    gains = np.zeros(len(feats))
    for q in range(4):
        tr = quad_fp != q
        tr &= quad_fp >= 0
        prow = np.flatnonzero(pos & tr)
        npool = np.flatnonzero(neg_pool & tr)
        nrow = rng.choice(npool, size=min(N_NEG, npool.size), replace=False)
        rows = np.concatenate([prow, nrow])
        y = np.concatenate([np.ones(prow.size), np.zeros(nrow.size)]).astype(np.float32)
        X = matrix(rows, feats, mm, names, geom_inner)
        booster = lgb.train(LGB_PARAMS, lgb.Dataset(X, y, free_raw_data=True), N_ROUNDS)
        gains += booster.feature_importance('gain')
        del X
        rate = nrow.size / max(npool.size, 1)
        test = np.flatnonzero(quad_fp == q)
        for geom, out in ((geom_inner, p_in), (geom_outer, p_out)):
            for i in range(0, test.size, 400_000):
                r = test[i:i + 400_000]
                p = booster.predict(matrix(r, feats, mm, names, geom))
                odds = p / np.maximum(1 - p, 1e-9) * rate  # undo negative subsampling
                out[r] = (odds / (1 + odds)).astype(np.float32)
        log(f'seed {seed} arm {arm} fold {q}: pos={prow.size} neg={nrow.size}')
        del booster
        gc.collect()
    imp = sorted(zip(feats, (gains / max(gains.sum(), 1e-9)).tolist()), key=lambda t: -t[1])
    return p_in, p_out, imp


def canaries(seed, fp, folds, mm, names, geom_outer, rng, arm='candidate'):
    from sklearn.metrics import roc_auc_score
    truth = np.zeros(fp.shape, bool); active = np.zeros(fp.shape, bool)
    for f in folds:
        a = fp & f['region'] & ~f['masked_known']
        active |= a
        truth |= f['truth'] & a
    t = truth[fp]; a = active[fp]
    pos = np.flatnonzero(t)
    neg = rng.choice(np.flatnonzero(a & ~t), size=300_000, replace=False)
    rows = np.concatenate([pos, neg]); y = np.r_[np.ones(pos.size), np.zeros(neg.size)]
    out = []
    feats = feature_list(arm, names)
    for f in feats:
        v = (mm[{n: i for i, n in enumerate(names)}[f], rows] if f in names else geom_outer[f][rows]).astype(np.float64)
        ok = np.isfinite(v)
        v = np.where(ok, v, np.nanmedian(v[ok]) if ok.any() else 0.0)
        auc = float(roc_auc_score(y, v)) if np.ptp(v) > 0 else 0.5
        out.append(dict(feature=f, auc=round(auc, 5), symmetric_auc=round(max(auc, 1 - auc), 5)))
    worst = max(out, key=lambda r: r['symmetric_auc'])
    return dict(seed=seed, n_positive=int(pos.size), n_negative=int(neg.size), features=len(out),
                max_symmetric_auc=worst['symmetric_auc'], max_feature=worst['feature'],
                leakage_flag=bool(worst['symmetric_auc'] > 0.90), rows=out)


def run_seed(seed: int):
    out_path = EVID / f'seed{seed}.json'
    if out_path.exists():
        raise FileExistsError(f'{out_path} exists; no retuning')
    t0 = time.time()
    g, fp = grid_and_fp()
    mm, names = load_static()
    folds, quad = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
    outer_visible = folds[0]['visible']
    n_withheld = int(sum(int((f['truth'] & fp & f['region'] & ~f['masked_known']).sum()) for f in folds))
    ig = Grid(footprint=fp, catalogue=outer_visible, crs=g.crs, transform=g.transform, height=g.height, width=g.width)
    ifolds, _ = holdout.buffered_component_draw(ig, seed=seed + 1000, buffer_px=3, boundary_px=12)
    inner_visible = ifolds[0]['visible']
    inner_hidden = ifolds[0]['hidden_all']
    inner_known = ifolds[0]['masked_known']
    pos2d = ndi.binary_dilation(inner_hidden, structure=np.ones((3, 3), bool)) & fp & ~inner_known
    pos = pos2d[fp]
    neg_pool = (fp & ~pos2d & ~inner_known)[fp]
    log(f'seed {seed}: outer withheld={n_withheld} inner hidden={int(inner_hidden.sum())} positives={int(pos.sum())}')
    geom_outer = variant_features(outer_visible, fp, mm, names)
    geom_inner = variant_features(inner_visible, fp, mm, names)
    rng = np.random.default_rng(seed * 7919)
    canary = canaries(seed, fp, folds, mm, names, geom_outer, rng)
    log(f'seed {seed}: canary max symmetric AUC {canary["max_symmetric_auc"]} ({canary["max_feature"]})')
    result = dict(lane='G79-FSC', seed=seed, evaluator_version=evaluate_holdout.VERSION,
                  withheld_positive_pixels=n_withheld, inner_draw_seed=seed + 1000,
                  inner_hidden_pixels=int(inner_hidden.sum()), canaries=canary, arms={})
    outer_dots = {}
    for arm in ('candidate', 'ablation_no_fabric'):
        p_in, p_out, imp = train_predict(arm, seed, fp, quad, mm, names, geom_inner, geom_outer, pos, neg_pool, rng)
        P_in, P_out = unflatten(p_in, fp), unflatten(p_out, fp)
        fab_in = (unflatten(geom_inner['fab_c2'], fp), unflatten(geom_inner['fab_s2'], fp),
                  unflatten(geom_inner['fab_coh'], fp), unflatten(geom_inner['cat_dens_30'], fp))
        fab_out = (unflatten(geom_outer['fab_c2'], fp), unflatten(geom_outer['fab_s2'], fp),
                   unflatten(geom_outer['fab_coh'], fp), unflatten(geom_outer['cat_dens_30'], fp))
        steer_in = steering(P_in, fp, fab_in, arm)
        grid_rows = []
        best = None
        for s in S_GRID:
            for c in C_GRID:
                ys, xs = place_orders(P_in, inner_visible, fp, steer_in, s, c, max(K_GRID))
                for k in K_GRID:
                    d, _ = pooled_dti(fsc.dots_from_order(fp.shape, ys, xs, k), ifolds, fp)
                    row = dict(K=k, spacing=s, collar=c, emitted=int(min(k, ys.size)), inner_sim_dti=round(float(d), 6))
                    grid_rows.append(row)
                    if best is None or row['inner_sim_dti'] > best['inner_sim_dti']:
                        best = row
        log(f'seed {seed} arm {arm}: inner selection {best}')
        steer_out = steering(P_out, fp, fab_out, arm)
        ys, xs = place_orders(P_out, outer_visible, fp, steer_out, best['spacing'], best['collar'], best['K'])
        dots = fsc.dots_from_order(fp.shape, ys, xs, best['K'])
        outer_dots[arm] = dots
        result['arms'][arm] = dict(selected=best, inner_grid=grid_rows, emitted=int(dots.sum()),
                                   top_features=[dict(feature=f, gain_share=round(v, 5)) for f, v in imp[:25]])
        np.save(CACHE / f'seed{seed}_{arm}_pout.npy', p_out)
        del P_in, P_out, p_in, p_out, fab_in, fab_out, steer_in, steer_out
        gc.collect()
    # uniform-random control at the candidate budget inside the same allowed domain
    allowed = fp & ~outer_visible
    idx = np.flatnonzero(allowed.ravel())
    pick = np.random.default_rng(seed + 424242).choice(idx, size=int(outer_dots['candidate'].sum()), replace=False)
    rnd = np.zeros(fp.size, bool); rnd[pick] = True
    outer_dots['random_control'] = rnd.reshape(fp.shape)
    terms = {}
    for arm, dots in outer_dots.items():
        _, terms[arm] = pooled_dti(dots, folds, fp)
    summary = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810, candidate='candidate')
    result['official_evaluate_all'] = summary
    result['thvc_incumbent_point_dti'] = THVC[seed]
    result['beats_thvc_point'] = bool(summary['scores']['candidate']['dti'] > THVC[seed])
    result['elapsed_seconds'] = round(time.time() - t0, 1)
    result['generated_utc'] = now()
    write_once(out_path, result)
    for arm in ('candidate', 'ablation_no_fabric', 'random_control'):
        s = summary['scores'][arm]
        log(f'seed {seed} {arm}: HOLDOUT-DTI {s["dti"]:.4f} CI {s["ci95"]} n={s["withheld_positive_pixels"]} emitted={int(outer_dots[arm].sum())}')


# ----------------------------------------------------------------------------- amendment A1 (EXP-FSC-3)

def run_seed_a1(seed: int):
    out_path = EVID / f'seed{seed}_a1.json'
    if out_path.exists():
        raise FileExistsError(f'{out_path} exists; no retuning')
    t0 = time.time()
    g, fp = grid_and_fp()
    mm, names = load_static()
    folds, quad = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
    outer_visible = folds[0]['visible']
    n_withheld = int(sum(int((f['truth'] & fp & f['region'] & ~f['masked_known']).sum()) for f in folds))
    ig = Grid(footprint=fp, catalogue=outer_visible, crs=g.crs, transform=g.transform, height=g.height, width=g.width)
    ifolds, _ = holdout.buffered_component_draw(ig, seed=seed + 1000, buffer_px=3, boundary_px=12)
    inner_visible, inner_hidden, inner_known = ifolds[0]['visible'], ifolds[0]['hidden_all'], ifolds[0]['masked_known']
    pos2d = ndi.binary_dilation(inner_hidden, structure=np.ones((3, 3), bool)) & fp & ~inner_known
    pos = pos2d[fp]
    neg_pool = (fp & ~pos2d & ~inner_known)[fp]
    geom_outer = variant_features(outer_visible, fp, mm, names, a1=True)
    geom_inner = variant_features(inner_visible, fp, mm, names, a1=True)
    rng = np.random.default_rng(seed * 7919)
    canary = canaries(seed, fp, folds, mm, names, geom_outer, rng, arm='candidate_a1')
    log(f'seed {seed} A1: canary max symmetric AUC {canary["max_symmetric_auc"]} ({canary["max_feature"]})')
    result = dict(lane='G79-FSC', amendment='A1', seed=seed, evaluator_version=evaluate_holdout.VERSION,
                  withheld_positive_pixels=n_withheld, inner_draw_seed=seed + 1000, canaries=canary, arms={})
    if canary['leakage_flag']:
        result['stopped'] = 'leakage canary > 0.90'
        write_once(out_path, result)
        return
    arm = 'candidate_a1'
    p_in, p_out, imp = train_predict(arm, seed, fp, quad, mm, names, geom_inner, geom_outer, pos, neg_pool, rng)
    P_in, P_out = unflatten(p_in, fp), unflatten(p_out, fp)
    fab_in = (unflatten(geom_inner['fab_c2'], fp), unflatten(geom_inner['fab_s2'], fp),
              unflatten(geom_inner['fab_coh'], fp), unflatten(geom_inner['cat_dens_30'], fp))
    fab_out = (unflatten(geom_outer['fab_c2'], fp), unflatten(geom_outer['fab_s2'], fp),
               unflatten(geom_outer['fab_coh'], fp), unflatten(geom_outer['cat_dens_30'], fp))
    steer_in = steering(P_in, fp, fab_in, arm)
    grid_rows, best = [], None
    for s in S_GRID:
        for c in C_GRID:
            ys, xs = place_orders(P_in, inner_visible, fp, steer_in, s, c, max(K_GRID))
            for k in K_GRID:
                d, _ = pooled_dti(fsc.dots_from_order(fp.shape, ys, xs, k), ifolds, fp)
                row = dict(K=k, spacing=s, collar=c, emitted=int(min(k, ys.size)), inner_sim_dti=round(float(d), 6))
                grid_rows.append(row)
                if best is None or row['inner_sim_dti'] > best['inner_sim_dti']:
                    best = row
    log(f'seed {seed} A1: inner selection {best}')
    steer_out = steering(P_out, fp, fab_out, arm)
    ys, xs = place_orders(P_out, outer_visible, fp, steer_out, best['spacing'], best['collar'], best['K'])
    outer_dots = {arm: fsc.dots_from_order(fp.shape, ys, xs, best['K'])}
    np.save(CACHE / f'seed{seed}_{arm}_pout.npy', p_out)
    # EXP-FSC-1 candidate rebuilt deterministically from its saved outer probabilities
    s1 = json.loads((EVID / f'seed{seed}.json').read_text())
    sel1 = s1['arms']['candidate']['selected']
    P1 = unflatten(np.load(CACHE / f'seed{seed}_candidate_pout.npy'), fp)
    ys1, xs1 = place_orders(P1, outer_visible, fp, steering(P1, fp, fab_out, 'candidate'), sel1['spacing'], sel1['collar'], sel1['K'])
    outer_dots['exp1_candidate'] = fsc.dots_from_order(fp.shape, ys1, xs1, sel1['K'])
    idx = np.flatnonzero((fp & ~outer_visible).ravel())
    pick = np.random.default_rng(seed + 525252).choice(idx, size=int(outer_dots[arm].sum()), replace=False)
    rnd = np.zeros(fp.size, bool); rnd[pick] = True
    outer_dots['random_control'] = rnd.reshape(fp.shape)
    terms = {a: pooled_dti(d, folds, fp)[1] for a, d in outer_dots.items()}
    summary = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810, candidate=arm)
    exp1_check = summary['scores']['exp1_candidate']['dti']
    result['arms'][arm] = dict(selected=best, inner_grid=grid_rows, emitted=int(outer_dots[arm].sum()),
                               top_features=[dict(feature=f, gain_share=round(v, 5)) for f, v in imp[:25]])
    result['exp1_rebuild_dti'] = exp1_check
    result['exp1_recorded_dti'] = s1['official_evaluate_all']['scores']['candidate']['dti']
    result['official_evaluate_all'] = summary
    result['thvc_incumbent_point_dti'] = THVC[seed]
    result['beats_thvc_point'] = bool(summary['scores'][arm]['dti'] > THVC[seed])
    result['elapsed_seconds'] = round(time.time() - t0, 1)
    result['generated_utc'] = now()
    write_once(out_path, result)
    for a in outer_dots:
        sc = summary['scores'][a]
        log(f'seed {seed} {a}: HOLDOUT-DTI {sc["dti"]:.4f} CI {sc["ci95"]} n={sc["withheld_positive_pixels"]} emitted={int(outer_dots[a].sum())}')


# ----------------------------------------------------------------------------- live

def run_live(arm='candidate'):
    suffix = '' if arm == 'candidate' else '_a1'
    out_path = EVID / f'live{suffix}.json'
    if out_path.exists():
        raise FileExistsError(f'{out_path} exists; no retuning')
    import lightgbm as lgb
    s20 = json.loads((EVID / f'seed20{suffix}.json').read_text())
    s30 = json.loads((EVID / f'seed30{suffix}.json').read_text())
    # preregistered rule: configuration with the best mean inner-simulation DTI over both seeds
    def key(r):
        return (r['K'], r['spacing'], r['collar'])
    acc = {}
    for s in (s20, s30):
        for r in s['arms'][arm]['inner_grid']:
            acc.setdefault(key(r), []).append(r['inner_sim_dti'])
    best_key = max(acc, key=lambda k: float(np.mean(acc[k])))
    K, S, C = best_key
    g, fp = grid_and_fp()
    cat = np.asarray(g.catalogue, bool)
    mm, names = load_static()
    ifolds, _ = holdout.buffered_component_draw(g, seed=2079, buffer_px=3, boundary_px=12)
    inner_visible, inner_hidden, inner_known = ifolds[0]['visible'], ifolds[0]['hidden_all'], ifolds[0]['masked_known']
    pos2d = ndi.binary_dilation(inner_hidden, structure=np.ones((3, 3), bool)) & fp & ~inner_known
    pos = np.flatnonzero(pos2d[fp])
    npool = np.flatnonzero((fp & ~pos2d & ~inner_known)[fp])
    rng = np.random.default_rng(2079)
    nrow = rng.choice(npool, size=min(N_NEG, npool.size), replace=False)
    geom_inner = variant_features(inner_visible, fp, mm, names, a1=(arm == 'candidate_a1'))
    feats = feature_list(arm, names)
    rows = np.concatenate([pos, nrow])
    y = np.r_[np.ones(pos.size), np.zeros(nrow.size)].astype(np.float32)
    booster = lgb.train(LGB_PARAMS, lgb.Dataset(matrix(rows, feats, mm, names, geom_inner), y), N_ROUNDS)
    del geom_inner
    gc.collect()
    geom_full = variant_features(cat, fp, mm, names, a1=(arm == 'candidate_a1'))
    rate = nrow.size / npool.size
    n = int(fp.sum())
    p = np.zeros(n, np.float32)
    for i in range(0, n, 400_000):
        r = np.arange(i, min(n, i + 400_000))
        q = booster.predict(matrix(r, feats, mm, names, geom_full))
        odds = q / np.maximum(1 - q, 1e-9) * rate
        p[r] = (odds / (1 + odds)).astype(np.float32)
    P = unflatten(p, fp)
    P[cat] = 0.0
    fab = (unflatten(geom_full['fab_c2'], fp), unflatten(geom_full['fab_s2'], fp),
           unflatten(geom_full['fab_coh'], fp), unflatten(geom_full['cat_dens_30'], fp))
    steer = steering(P, fp, fab, arm)
    ys, xs = place_orders(P, cat, fp, steer, S, C, K)
    dots = fsc.dots_from_order(fp.shape, ys, xs, K)
    surface = np.clip(P, 0.0, 1.0).astype(np.float32)
    surface[~fp] = 0.0
    np.save(CACHE / f'live_surface{suffix}.npy', surface)
    np.save(CACHE / f'live_dots{suffix}.npy', dots)
    gains = booster.feature_importance('gain')
    imp = sorted(zip(feats, (gains / gains.sum()).tolist()), key=lambda t: -t[1])
    write_once(out_path, dict(lane='G79-FSC', arm=arm, generated_utc=now(), selection_rule='max mean inner-simulation DTI over seeds 20 and 30',
                              selected=dict(K=K, spacing=S, collar=C, mean_inner_sim_dti=float(np.mean(acc[best_key]))),
                              inner_draw_seed=2079, positives=int(pos.size), negatives=int(nrow.size),
                              emitted_dots=int(dots.sum()), dots_on_catalogue=int((dots & cat).sum()),
                              dots_outside_footprint=int((dots & ~fp).sum()),
                              top_features=[dict(feature=f, gain_share=round(v, 5)) for f, v in imp[:25]]))
    log('live done', int(dots.sum()), 'dots')


if __name__ == '__main__':
    if not PREREG.exists():
        sys.exit('preregistration missing')
    stage = sys.argv[1]
    if stage == 'static':
        build_static()
    elif stage == 'seed':
        run_seed(int(sys.argv[2]))
    elif stage == 'live':
        run_live()
    elif stage == 'a1':
        run_seed_a1(int(sys.argv[2]))
    elif stage == 'live_a1':
        run_live('candidate_a1')
    else:
        sys.exit(f'unknown stage {stage}')
