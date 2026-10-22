#!/usr/bin/env python3
"""One-fold diagnostic: does any feature family rank held-out components?"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'vendor')]
from gems57 import holdout as H, evaluate_holdout as E
from gems57.grid import load_grid
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score
import gems79.cblf as cblf
from scripts.run_cblf import _stack_for, _predict_region, CACHE, BUDGET, SEED

g = load_grid(ROOT/'data'/'reference')
folds,_ = H.buffered_component_draw(g, seed=SEED, hide_frac=0.20, buffer_px=3)
f = folds[0]
region = np.asarray(f['region']); vis = np.asarray(f['visible']); cat = np.asarray(f['catalogue']) if hasattr(f,'catalogue') else g.catalogue
stack = _stack_for(vis)
train_area = g.footprint & ~region
pos = ndi.binary_dilation(vis, iterations=3)
neg = train_area & ~ndi.binary_dilation(pos, iterations=4)
allowed = g.footprint & ~np.asarray(f['masked_known']) & region
truth = np.asarray(f['truth'])
tube = ndi.binary_dilation(truth, iterations=3) & allowed
out = {}
prior = cblf.distance_band_prior(vis, g.footprint)
for name, keep in (('all', cblf.FEATURE_NAMES),
                   ('geophys', tuple(n for n in cblf.FEATURE_NAMES if n not in cblf.CONTEXT_FEATURES)),
                   ('combined', tuple(n for n in cblf.FEATURE_NAMES if n not in cblf.CONTEXT_FEATURES))):
    st = stack.subset(keep)
    m,_ = cblf.fit_model(st, neg, pos & train_area, seed=SEED, pos_cap=45000, neg_cap=250000, max_iter=120)
    prob = _predict_region(m, st, region)
    if name == 'combined':
        prob = prob * prior
    ok = allowed & (prob>0)
    auc = roc_auc_score(tube[ok].astype(int), prob[ok])
    cur,ci = cblf.emit_curves(prob, allowed, budget=BUDGET)
    dot,di = cblf.emit_dots(prob, allowed, budget=BUDGET)
    rc,_ = E.evaluate(cur.astype('float32'), f, g.footprint, origin=(0,0), global_shape=(g.height,g.width))
    rd,_ = E.evaluate(dot.astype('float32'), f, g.footprint, origin=(0,0), global_shape=(g.height,g.width))
    d = np.log1p(ndi.distance_transform_edt(~vis))
    rng = np.random.default_rng(0); s = rng.choice(np.flatnonzero(ok.ravel()), 200000, replace=False)
    out[name] = dict(auc_tube=float(auc), curves_dti=float(rc['dti']), dots_dti=float(rd['dti']),
                     emitted=dict(curves=int(cur.sum()), dots=int(dot.sum())),
                     corr_prob_logdist=float(np.corrcoef(prob.ravel()[s], d.ravel()[s])[0,1]),
                     tau=ci['tau'])
    print(name, json.dumps(out[name]), flush=True)
(ROOT/'evidence').mkdir(exist_ok=True)
(ROOT/'evidence'/'cblf_fold_diagnostic.json').write_text(json.dumps(out, indent=2)+'\n')
