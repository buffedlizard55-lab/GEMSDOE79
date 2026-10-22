#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"), str(ROOT/"vendor")]
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw
from gems57 import evaluate_holdout as evaluator
from gems79.placement import place

BUDGET=37654
grid=load_grid(ROOT/"data/raw")
stack_path=ROOT/"data/raw/training_features.tif"
with rasterio.open(stack_path) as src:
    bands=[src.read(i).astype(np.float32) for i in range(1,20)]
stack=np.stack(bands, axis=-1)
footprint=grid.footprint
for b in range(stack.shape[-1]):
    arr=stack[:,:,b]
    valid=footprint & np.isfinite(arr) & (arr>-1e38)
    med=np.median(arr[valid])
    arr[~valid]=med

for seed in (20,30):
    folds,_=buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    terms={}
    for fold in folds:
        # training positives = visible (global minus hidden)
        pos_mask=fold['visible']
        pos_idx=np.flatnonzero(pos_mask)
        # negatives: footprint not catalogue, not near faults
        # compute distance to visible and truth
        # Use distance to any catalogue (visible+truth?) but we have visible+hidden = full cat
        # Use distance to all known faults (visible) and hidden truth
        dist_vis=ndi.distance_transform_edt(~pos_mask)
        dist_truth=ndi.distance_transform_edt(~fold['hidden_all'])
        neg_candidates=grid.footprint & ~grid.catalogue
        neg_valid=neg_candidates & (dist_vis>3) & (dist_truth>3)
        neg_idx=np.flatnonzero(neg_valid)
        rng=np.random.default_rng(seed*100+fold['fold'])
        if len(neg_idx)> 80000:
            neg_idx=rng.choice(neg_idx, 80000, replace=False)
        print(f"seed{seed} fold {fold['name']} pos {len(pos_idx)} neg {len(neg_idx)} truth {fold['truth'].sum()} hidden_all {fold['hidden_all'].sum()}")
        X_pos=stack.reshape(-1,19)[pos_idx]
        X_neg=stack.reshape(-1,19)[neg_idx]
        y=np.concatenate([np.ones(len(X_pos)), np.zeros(len(X_neg))])
        X=np.concatenate([X_pos, X_neg], axis=0)
        perm=rng.permutation(len(y))
        X=X[perm]; y=y[perm]
        clf=HistGradientBoostingClassifier(max_iter=150, learning_rate=0.08, max_depth=5, random_state=seed)
        clf.fit(X,y)
        # predict over crop
        ys,xs=np.nonzero(fold['region'])
        sy=slice(max(0,int(ys.min())-3), min(grid.height,int(ys.max())+4))
        sx=slice(max(0,int(xs.min())-3), min(grid.width,int(xs.max())+4))
        sl=sy,sx
        H,W=sy.stop-sy.start, sx.stop-sx.start
        crop_stack=stack[sy,sx,:].reshape(-1,19)
        prob=clf.predict_proba(crop_stack)[:,1].astype(np.float32).reshape(H,W)
        allowed=footprint[sl] & fold['region'][sl] & ~fold['visible'][sl]
        budget=int(round(BUDGET*fold['region'].sum()/grid.footprint.sum()))
        rng_unif=np.random.default_rng(790021).random((H,W), dtype=np.float32)
        for name,surface in [('candidate',prob),('uniform_control',rng_unif)]:
            dots, placement=place(surface, allowed, budget)
            if (dots & fold['visible'][sl]).any():
                raise AssertionError
            local_fold={k:fold[k][sl] for k in ('region','truth','visible','masked_known')}
            result, block_terms=evaluator.evaluate(dots.astype(np.float32), local_fold, footprint[sl], origin=(sy.start,sx.start), global_shape=grid.shape)
            terms[name]=terms.get(name, np.zeros_like(block_terms))+block_terms
            print(f"  {name} dti={result['dti']:.4f} n_truth={result['n_truth']} n_emit={result['n_emitted']}")
    summary=evaluator.pooled_summary(terms, candidate='candidate', draws=1000, seed=7900+seed)
    print(f"SEED {seed} SUMMARY candidate {summary['scores']['candidate']['dti']:.4f} CI {summary['scores']['candidate']['ci95']}")
    for k in summary['scores']:
        if k!='candidate':
            print(f"  {k} {summary['scores'][k]['dti']:.4f} delta {summary['paired_differences'][k]['delta']:.4f} CI {summary['paired_differences'][k]['ci95']}")
    Path(f"evidence/supervised2_seed{seed}.json").write_text(json.dumps(summary, indent=2)+"\n")
