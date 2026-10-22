#!/usr/bin/env python3
"""G79-UGBP: preregistered Exp1-3 holdout + final unique TIF + novelty + validation.

Reuses shared vendor/gems57 grid/holdout/evaluate_holdout/submission_writer.
Frozen recipe: registry/preregistration_g79_ugbp.json (read that file first).
Every score written here is HOLDOUT-DTI (gems57-pooled-hide-v2) unless labelled
ORGANIZER-CONFIRMED (none exists for this artifact).
"""
import sys, json, hashlib, time
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata, spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems57.grid import load_grid
from gems57 import holdout, evaluate_holdout
from gems57.submission_writer import write_submission
from gems79.ugbp import build_ugbp_surfaces, emit_dotted, rank01
from gems79.tipstep import build_surface as tipstep_surface

NAME = "gems79-ugbp-20261022"
NOTE = "G79-UGBP disequilibrium up-gradient conduits x gravity step gate, dotted 2.8px learner fusion"
BUDGET = 37654
RAW = ROOT / 'data/raw'
CACHE = ROOT / '.cache/g79_ugbp'
FEATURES = ["tf_rtp_rank","tf_tmi_hg_rank","tf_iso_grav_hg_rank","tf_iso_grav_rank",
 "tf_det_elev_rank","tf_det_elev_slope_rank","tf_depth_base_rank","tf_cond_rank",
 "tf_dilaterate_rank","tf_2ndinv_rank","lidar_step_rank","lidar_coh","lidar_present",
 "rad_kth_rank","ugbp_prox_iso","ugbp_distal_iso","ugbp_upgrad","ugbp_upgrad_gated",
 "mech_logdist","mech_exp6","mech_exp18","mech_dens15","mech_tipstep"]
STATIC = FEATURES[:18]
UGBP_IDX = [FEATURES.index(x) for x in ("ugbp_prox_iso","ugbp_distal_iso","ugbp_upgrad","ugbp_upgrad_gated")]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def build_static(fp):
    """18 static columns -> memmap (n_fp x 18 float32). Returns (mm, ugbp2d dict, info)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / 'static18.f32.mmap'
    n = int(fp.sum())
    prox, distal, upg, gated, uinfo = build_ugbp_surfaces(RAW, fp)
    ugbp2d = {'ugbp_prox_iso': prox, 'ugbp_distal_iso': distal,
              'ugbp_upgrad': upg, 'ugbp_upgrad_gated': gated}
    if path.exists() and path.stat().st_size == n * len(STATIC) * 4:
        mm = np.memmap(path, dtype='float32', mode='r+', shape=(n, len(STATIC)))
        print('static cache reused', flush=True)
        return mm, ugbp2d, uinfo
    mm = np.memmap(path, dtype='float32', mode='w+', shape=(n, len(STATIC)))
    col = {k: i for i, k in enumerate(STATIC)}
    def put(name, a2d):
        mm[:, col[name]] = np.asarray(a2d[fp], dtype=np.float32)
    def tf(band):
        with rasterio.open(RAW / 'training_features.tif') as ds:
            return ds.read(band).astype(np.float32)
    for name, band in [('tf_rtp_rank',2),('tf_tmi_hg_rank',3),('tf_iso_grav_hg_rank',18),
                       ('tf_iso_grav_rank',13),('tf_det_elev_rank',12),('tf_det_elev_slope_rank',19),
                       ('tf_depth_base_rank',15),('tf_cond_rank',17),('tf_dilaterate_rank',8),
                       ('tf_2ndinv_rank',4)]:
        put(name, rank01(tf(band), fp)); print('built', name, flush=True)
    with rasterio.open(RAW / 'external/lidar_scarp_features_u8.tif') as ds:
        step, coh, valid = ds.read(3).astype(np.float32), ds.read(10).astype(np.float32), ds.read(12).astype(np.float32)
    sr = rank01(np.where(valid > 0, step, 0.0), fp)
    put('lidar_step_rank', sr); put('lidar_coh', np.where(valid > 0, coh/255.0, 0.0).astype(np.float32))
    put('lidar_present', (valid/255.0).astype(np.float32)); del step, coh, valid, sr
    with rasterio.open(RAW / 'external/geodawn_rad_u8.tif') as ds:
        k_, th_ = ds.read(1).astype(np.float32), ds.read(2).astype(np.float32)
    put('rad_kth_rank', rank01(k_/255.0 - th_/255.0, fp)); del k_, th_
    for k, v in ugbp2d.items():
        # store raw surface values (learner standardizes internally); keep 2D for Exp1
        mm[:, col[k]] = v[fp].astype(np.float32)
    mm.flush()
    print('static built', uinfo, flush=True)
    return mm, ugbp2d, uinfo


def mech(visible, fp):
    d = ndi.distance_transform_edt(~visible).astype(np.float32)
    tip, _ = tipstep_surface(visible)
    return {'mech_logdist': np.log1p(d), 'mech_exp6': np.exp(-d/6.0).astype(np.float32),
            'mech_exp18': np.exp(-d/18.0).astype(np.float32),
            'mech_dens15': ndi.uniform_filter(visible.astype(np.float32), 15),
            'mech_tipstep': tip.astype(np.float32)}, d


def train_predict(mm, fp, visible, use_ugbp, seed):
    """Inner simulated hide of `visible`; predict footprint probabilities."""
    comp, nc = ndi.label(visible, np.ones((3,3), int))
    sizes = np.bincount(comp.ravel(), minlength=nc+1)
    ids = np.arange(1, nc+1)
    rng = np.random.default_rng(7900)
    perm = rng.permutation(ids)
    cum = np.cumsum(sizes[perm])
    k = int(np.searchsorted(cum, 0.22*float(visible.sum()))) + 1
    sim_hidden = np.isin(comp, perm[:k]) & visible
    collar = ndi.distance_transform_edt(~sim_hidden) <= 3.0
    sim_vis = visible & ~collar
    sim_known = visible & ~sim_hidden
    active = fp & ~sim_known
    m2d, _d = mech(sim_vis, fp)
    fp_rows = np.flatnonzero(fp.ravel())
    # assemble training frame on footprint rows
    cols = list(range(len(STATIC))) + [None]*5
    def frame(mask2d):
        rows = np.searchsorted(fp_rows, np.flatnonzero(mask2d.ravel()))
        X = np.empty((len(rows), len(FEATURES)), np.float32)
        X[:, :len(STATIC)] = mm[rows, :len(STATIC)]
        for j, nm in enumerate(FEATURES[len(STATIC):]):
            X[:, len(STATIC)+j] = m2d[nm].ravel()[fp_rows[rows]]
        return X
    pos_mask = active & sim_hidden
    dsv = ndi.distance_transform_edt(~sim_vis)
    neg_cand = np.flatnonzero((active & ~sim_hidden & (dsv > 3)).ravel())
    rng2 = np.random.default_rng(7901)
    neg_flat = rng2.choice(neg_cand, size=min(60000, len(neg_cand)), replace=False)
    neg_mask = np.zeros(fp.shape, bool); neg_mask.ravel()[neg_flat] = True
    Xp, Xn = frame(pos_mask), frame(neg_mask)
    drop = [] if use_ugbp else UGBP_IDX
    keep = [i for i in range(len(FEATURES)) if i not in drop]
    X = np.vstack([Xp, Xn])[:, keep]
    y = np.r_[np.ones(len(Xp)), np.zeros(len(Xn))]
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
        max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0, random_state=7900)
    clf.fit(X, y)
    # predict with OUTER visible mechanics
    mo, _ = mech(visible, fp)
    prob = np.zeros(fp.shape, np.float32)
    fp2d_rows = fp_rows
    for s in range(0, len(fp2d_rows), 500000):
        rows = np.arange(s, min(s+500000, len(fp2d_rows)))
        Xc = np.empty((len(rows), len(FEATURES)), np.float32)
        Xc[:, :len(STATIC)] = mm[rows, :len(STATIC)]
        for j, nm in enumerate(FEATURES[len(STATIC):]):
            Xc[:, len(STATIC)+j] = mo[nm].ravel()[fp2d_rows[rows]]
        prob.ravel()[fp2d_rows[rows]] = clf.predict_proba(Xc[:, keep])[:, 1].astype(np.float32)
    return prob


def evaluate_dots(dots, folds, fp, seed):
    terms = []
    for f in folds:
        _r, t = evaluate_holdout.evaluate(dots.astype(np.float32), f, fp)
        terms.append(t)
    return np.vstack(terms)


def uniform_dots(folds0, fp, n, seed):
    vis = folds0['visible']
    allowed = fp & ~folds0['masked_known'] & (ndi.distance_transform_edt(~vis) > 2)
    rng = np.random.default_rng(seed + 999)
    idx = np.flatnonzero(allowed.ravel())
    pick = rng.choice(idx, size=min(n, len(idx)), replace=False)
    d = np.zeros(fp.shape, bool); d.ravel()[pick] = True
    return d


def main():
    t0 = time.time()
    g = load_grid(ROOT / 'data/reference')
    fp, cat = g.footprint, g.catalogue
    mm, ugbp2d, uinfo = build_static(fp)
    out = {'lane': 'G79-UGBP', 'ugbp_info': uinfo, 'experiments': {}}
    # ---- canary sample design shared across seeds (per-seed truth) ----
    canaries = {}
    surfaces_by_seed = {}
    for seed in (20, 30):
        folds, _q = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        vis = folds[0]['visible']
        truth = np.zeros(fp.shape, bool)
        for f in folds:
            truth |= f['truth']
        active = fp & ~folds[0]['masked_known']
        dvis = ndi.distance_transform_edt(~vis); dtr = ndi.distance_transform_edt(~truth)
        pos = np.flatnonzero((active & truth).ravel())
        negc = np.flatnonzero((active & ~truth & (dtr > 3) & (dvis > 3)).ravel())
        rng = np.random.default_rng(seed)
        neg = rng.choice(negc, size=min(len(negc), len(pos)*3), replace=False)
        fp_rows = np.flatnonzero(fp.ravel())
        prow = np.searchsorted(fp_rows, pos); nrow = np.searchsorted(fp_rows, neg)
        mo, _ = mech(vis, fp)
        feats = {}
        for i, nm in enumerate(STATIC):
            feats[nm] = np.r_[mm[prow, i], mm[nrow, i]]
        for nm in FEATURES[len(STATIC):]:
            v = mo[nm].ravel()
            feats[nm] = np.r_[v[pos], v[neg]]
        yy = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
        for nm, s in feats.items():
            a = float(roc_auc_score(yy, s))
            canaries[f'seed{seed}:{nm}'] = {'auc': a, 'symmetric_auc': max(a, 1-a)}
        print(f'seed{seed} canaries done max={max(v["symmetric_auc"] for v in canaries.values() if v)}', flush=True)
        surfaces_by_seed[seed] = (folds, vis)
    out['canaries'] = canaries
    out['canary_max_symmetric_auc'] = max(v['symmetric_auc'] for v in canaries.values())
    # ---- experiments ----
    for exp, use_ugbp, pure in [('EXP1', True, True), ('EXP2', True, False), ('EXP3', False, False)]:
        hold = {}
        for seed in (20, 30):
            folds, vis = surfaces_by_seed[seed]
            if pure:
                score = ugbp2d['ugbp_upgrad_gated']
            else:
                score = train_predict(mm, fp, vis, use_ugbp, seed)
                np.save(CACHE / f'prob_{exp}_seed{seed}.npy', score)
            dots = emit_dotted(score, vis, fp, BUDGET)
            n = int(dots.sum())
            uni = uniform_dots(folds[0], fp, n, seed)
            arms = {exp: evaluate_dots(dots, folds, fp, seed),
                    'UNIFORM': evaluate_dots(uni, folds, fp, seed)}
            pooled = evaluate_holdout.pooled_summary(arms, draws=1000, seed=520810, candidate=exp)
            hold[f'seed{seed}'] = {'emitted': n, 'pooled': pooled}
            s = pooled['scores'][exp]
            print(f"{exp} seed{seed} HOLDOUT-DTI={s['dti']:.4f} CI{s['ci95']} n={s['withheld_positive_pixels']} emitted={n}", flush=True)
        out['experiments'][exp] = hold
    (ROOT / 'evidence/ugbp_holdout.json').write_text(json.dumps(out, indent=2))
    # ---- final surface + pre-placement novelty (local scope) ----
    prob = train_predict(mm, fp, cat, True, 0)
    np.save(CACHE / 'prob_final.npy', prob)
    registry_files = sorted([p for p in list((ROOT/'artifacts').rglob('*.tif')) +
                             list((ROOT/'archive').rglob('*.tif')) +
                             list((ROOT/'docs/downloads').glob('*.tif'))])
    rng = np.random.default_rng(79)
    fp_idx = np.flatnonzero(fp.ravel())
    sample = rng.choice(fp_idx, size=min(200000, len(fp_idx)), replace=False)
    rows_out = []
    surf = prob.ravel()[sample].astype(np.float64)
    for p in registry_files:
        try:
            with rasterio.open(p) as ds:
                a = ds.read(1).astype(np.float64)
            if a.shape != fp.shape:
                rows_out.append({'file': str(p.relative_to(ROOT)), 'comparable': False}); continue
            rho = float(spearmanr(surf, a.ravel()[sample]).statistic)
            rows_out.append({'file': str(p.relative_to(ROOT)), 'comparable': True,
                             'surface_spearman_sample200k': rho})
        except Exception as e:
            rows_out.append({'file': str(p.relative_to(ROOT)), 'comparable': False, 'error': str(e)[:120]})
    comp = [r for r in rows_out if r.get('comparable')]
    maxrho = max((abs(r['surface_spearman_sample200k']) for r in comp), default=None)
    out['novelty_surface_local'] = {'n_files': len(registry_files), 'n_comparable': len(comp),
                                    'max_abs_spearman': maxrho, 'rows': rows_out}
    print('surface novelty max|rho|=', maxrho, 'files', len(registry_files), flush=True)
    # ---- final dots + writer ----
    dots = emit_dotted(prob, cat, fp, BUDGET)
    pred = dots.astype(np.float32)
    dest = ROOT / 'docs/downloads' / f"{NAME}-{int(dots.sum())}dots-zeros.tif"
    meta = write_submission(dest, pred, ROOT / 'data/reference/sample_submission.tif', fp,
                            note=NOTE, name=NAME, catalogue=cat, metadata={'lane': 'G79-UGBP'})
    out['final'] = {'file': str(dest.relative_to(ROOT)), 'dots': int(dots.sum()),
                    'sha256': sha(dest), 'writer_receipt_file': meta['file']}
    # post-placement novelty
    post = []
    cand = dots
    for p in registry_files:
        try:
            with rasterio.open(p) as ds:
                a = ds.read(1)
            if a.shape != fp.shape:
                continue
            theirs = a > 0
            if not theirs.any():
                post.append({'file': str(p.relative_to(ROOT)), 'their_dots': 0}); continue
            near = ndi.distance_transform_edt(~theirs) <= 3.0
            post.append({'file': str(p.relative_to(ROOT)), 'their_dots': int(theirs.sum()),
                         'forward_overlap_3px': float(near[cand].mean()) if cand.any() else 0.0})
        except Exception:
            pass
    out['novelty_dots_local'] = {'n_compared': len(post),
        'max_forward_overlap_3px': max((r.get('forward_overlap_3px', 0) for r in post), default=None),
        'rows': post}
    out['elapsed_s'] = time.time() - t0
    (ROOT / 'evidence/ugbp_holdout.json').write_text(json.dumps(out, indent=2))
    print('FINAL', out['final'], 'elapsed', out['elapsed_s'], flush=True)


if __name__ == '__main__':
    main()
