#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"), str(ROOT/"vendor")]
from gems57 import evaluate_holdout as evaluator
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw
from gems79.placement import place

BUDGET=37654

grid=load_grid(ROOT/"data/raw")
cache=Path(".cache/e2")
# load e2 features
FEATURE_NAMES=('gravity_edge_rank','magnetic_contrast_rank','lag_gain_r3','lag_gain_r5','best_correlation_r3','best_correlation_r5','signed_lag_agreement','strain_favorability_rank','fabric_offset_strain_surface','zero_lag_edge_control')
features={n: np.load(cache/(n+".npy")) for n in FEATURE_NAMES}
support=np.load(cache/"support.npy")
# also load E1 for comparison? Use e1 cache
e1_cache=Path(".cache/g79")
e1_features={n: np.load(e1_cache/(n+".npy"), mmap_mode='r') for n in ('gravity_edge_rank','magnetic_contrast_rank','lag_gain_r3','lag_gain_r5','signed_lag_agreement','fabric_offset_surface','zero_lag_edge_control')}
# sanity
print("support", support.sum(), "footprint", grid.footprint.sum())
# leakage canary
def canaries(features, folds, seed):
    rows=[]
    for fold in folds:
        active=fold['region'] & ~fold['masked_known']
        truth=active & fold['truth']
        negatives=active & (ndi.distance_transform_edt(~truth) > 3)
        negatives &= ndi.distance_transform_edt(~fold['visible']) > 3
        ni=np.flatnonzero(negatives)
        rng=np.random.default_rng(seed*100+fold['fold'])
        if len(ni)>100000:
            ni=rng.choice(ni,100000,replace=False)
        pi=np.flatnonzero(truth)
        sample=np.concatenate([pi,ni])
        labels=np.r_[np.ones(len(pi),np.uint8), np.zeros(len(ni),np.uint8)]
        for name, arr in features.items():
            auc=float(roc_auc_score(labels, arr.ravel()[sample]))
            rows.append(dict(feature=name, fold=fold['name'], auc=auc, symmetric_auc=max(auc,1-auc), positive=len(pi), negatives=len(ni)))
    return rows

for seed in (20,30):
    folds,_=buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    # canaries for all e2 features
    can_rows=canaries({k:features[k] for k in FEATURE_NAMES}, folds, seed)
    max_sauc=max(r['symmetric_auc'] for r in can_rows)
    print(f"seed {seed} max sym AUC {max_sauc:.4f} worst {max(can_rows, key=lambda r:r['symmetric_auc'])}")
    # holdout per seed
    rng_surface=np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    # prepare loop like evaluate_seed
    terms={}; results=[]
    arm_surfaces={'candidate': features['fabric_offset_strain_surface'],
                  'zero_lag_edge_control': features['zero_lag_edge_control'],
                  'uniform_control': rng_surface,
                  'e1_like': e1_features['fabric_offset_surface']}
    for fold in folds:
        ys,xs=np.nonzero(fold['region'])
        sy=slice(max(0,int(ys.min())-3), min(grid.height,int(ys.max())+4))
        sx=slice(max(0,int(xs.min())-3), min(grid.width,int(xs.max())+4))
        sl=sy,sx
        local_fold={name: fold[name][sl] for name in ('region','truth','visible','masked_known')}
        allowed=support[sl] & fold['region'][sl] & ~fold['visible'][sl]
        budget=int(round(BUDGET*fold['region'].sum()/grid.footprint.sum()))
        for name,surface in arm_surfaces.items():
            dots, placement=place(surface[sl], allowed, budget)
            if (dots & fold['visible'][sl]).any():
                raise AssertionError('visible fault pixels')
            result, block_terms=evaluator.evaluate(dots.astype(np.float32), local_fold, grid.footprint[sl], origin=(sy.start,sx.start), global_shape=grid.shape)
            terms[name]=terms.get(name, np.zeros_like(block_terms))+block_terms
            results.append((seed, fold['name'], name, result['dti'], result['n_truth']))
            print(f"seed{seed} {fold['name']} {name}: dti={result['dti']:.4f} n={result['n_truth']}")
    summary=evaluator.pooled_summary(terms, candidate='candidate', draws=1000, seed=7900+seed)
    print(f"seed {seed} pooled summary candidate {summary['scores']['candidate']['dti']:.4f} CI {summary['scores']['candidate']['ci95']}")
    for k in ('zero_lag_edge_control','uniform_control','e1_like'):
        if k in summary['scores']:
            d=summary['scores'][k]['dti']
            delta=summary['paired_differences'][k]['delta']
            ci=summary['paired_differences'][k]['ci95']
            print(f"  vs {k}: dti={d:.4f} delta={delta:.4f} CI {ci}")
    Path(f"evidence/e2_holdout_seed{seed}.json").write_text(json.dumps(summary, indent=2)+"\n")
