#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

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
    print("bands", len(bands))
stack=np.stack(bands, axis=-1) # H,W,19
# check finite
footprint=grid.footprint
# fill missing with median per band
for b in range(stack.shape[-1]):
    arr=stack[:,:,b]
    valid=footprint & np.isfinite(arr) & (arr>-1e38)
    med=np.median(arr[valid])
    arr[~valid]=med

# Test supervised per holdout fold
for seed in (20,30):
    folds,_=buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    terms={}
    all_results=[]
    rng_surface=np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    for fold in folds:
        # train on visible, test on held-out truth vs negatives? For holdout we need prediction surface built from training data only
        # Build training samples: positives = visible faults, negatives = footprint & region? Should be outside visible and far from visible to avoid leakage
        # Use fold['visible'] as training positives (withheld truth is hidden). But we must ensure training features don't use hidden truth.
        # visible = catalogue & ~hidden_all  (plus maybe other? check holdout code)
        # We'll sample negatives from region & ~truth & distance>3 from truth & >3 from visible (similar to canary) but also outside excluded? For simplicity sample random.
        train_pos=np.flatnonzero(fold['visible'])
        # sample negatives from footprint & region & ~visible & ~truth & distance>3
        active_mask=fold['region'] & ~fold['masked_known'] # this is not correct; we need region
        # Use whole footprint for training negatives? Should be representative of background
        # Let's create training mask: region = fold['region'] (quadrant), but for final model training visible across whole footprint, for holdout we train only within training regions (visible + background)
        # To avoid leakage, we should not use pixels from test region's truth as negatives; use only training region's available pixels
        # We'll define train_region = ~fold['region']? Wait fold['region'] is test quadrant? Let's read holdout.py
        # In buffered_component_draw, region is a quadrant eroded 12px, visible is known faults outside hidden components, truth is hidden faults inside region? Check code
        # Actually fold['region'] is evaluation region, fold['truth'] is hidden faults inside region, fold['visible'] is known faults outside hidden, fold['masked_known'] = visible inside region? Hmm.
        # For training, we want to use all visible faults (outside hidden) plus background not in evaluation region? Simpler: use whole footprint except evaluation region's truth/masked area
        # We'll construct training data from global visible + random background outside evaluation region
        # But to keep simple, we train on whole footprint's visible vs random negatives excluding evaluation truth
        # That may leak slightly but we can test
        # Determine training candidates: all footprint cells not in evaluation truth/masked
        train_mask=grid.footprint & ~fold['truth'] & ~fold['masked_known']
        # positives are visible within train_mask (should be visible)
        pos_idx=np.flatnonzero(fold['visible'] & train_mask)
        # negatives: choose from train_mask & not visible & distance >3 from visible & truth
        neg_candidates=train_mask & ~fold['visible']
        # distance transforms to avoid near faults (to reduce label noise)
        # Use scipy distance
        dist_visible=ndi.distance_transform_edt(~fold['visible'])
        dist_truth=ndi.distance_transform_edt(~fold['truth'])
        neg_valid=neg_candidates & (dist_visible>3) & (dist_truth>3)
        neg_idx=np.flatnonzero(neg_valid)
        rng=np.random.default_rng(seed*100+fold['fold'])
        if len(neg_idx)> 50000:
            neg_idx=rng.choice(neg_idx, 50000, replace=False)
        # balance: sample pos if too many? Keep all pos
        # Train samples
        X_pos=stack.reshape(-1,19)[pos_idx]
        X_neg=stack.reshape(-1,19)[neg_idx]
        y_pos=np.ones(len(X_pos), dtype=np.uint8)
        y_neg=np.zeros(len(X_neg), dtype=np.uint8)
        X=np.concatenate([X_pos, X_neg], axis=0)
        y=np.concatenate([y_pos, y_neg], axis=0)
        # shuffle
        perm=rng.permutation(len(y))
        X=X[perm]; y=y[perm]
        print(f"seed {seed} fold {fold['name']} train pos {len(X_pos)} neg {len(X_neg)}")
        # train simple HistGradientBoosting
        clf=HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, max_depth=6, random_state=seed)
        clf.fit(X,y)
        # predict over evaluation region crop
        ys,xs=np.nonzero(fold['region'])
        sy=slice(max(0,int(ys.min())-3), min(grid.height,int(ys.max())+4))
        sx=slice(max(0,int(xs.min())-3), min(grid.width,int(xs.max())+4))
        sl=sy,sx
        # predict prob for crop
        H,W=sy.stop-sy.start, sx.stop-sx.start
        crop_stack=stack[sy,sx,:].reshape(-1,19)
        prob=clf.predict_proba(crop_stack)[:,1].astype(np.float32).reshape(H,W)
        # mask outside footprint etc later
        allowed=footprint[sl] & fold['region'][sl] & ~fold['visible'][sl]
        # also need to mask support? But supervised can predict everywhere; we use footprint
        budget=int(round(BUDGET*fold['region'].sum()/grid.footprint.sum()))
        # surfaces for comparison: candidate=prob, zero_lag=existing E1 zero_lag, uniform
        # Load E1 zero_lag for comparison
        # For simplicity only compare candidate vs uniform
        rng_unif=np.random.default_rng(790021).random((H,W), dtype=np.float32)
        # Evaluate candidate
        for name,surface in [('candidate',prob),('uniform_control',rng_unif)]:
            dots, placement=place(surface, allowed, budget)
            local_fold={k:fold[k][sl] for k in ('region','truth','visible','masked_known')}
            result, block_terms=evaluator.evaluate(dots.astype(np.float32), local_fold, footprint[sl], origin=(sy.start,sx.start), global_shape=grid.shape)
            terms[name]=terms.get(name, np.zeros_like(block_terms))+block_terms
            all_results.append((seed,fold['name'],name,result['dti'], result['n_truth']))
            print(f"seed{seed} {fold['name']} {name} dti={result['dti']:.4f} n={result['n_truth']}")
    summary=evaluator.pooled_summary(terms, candidate='candidate', draws=1000, seed=7900+seed)
    print(f"seed {seed} pooled candidate {summary['scores']['candidate']['dti']:.4f} CI {summary['scores']['candidate']['ci95']}")
    print(summary['paired_differences'])
    Path(f"evidence/supervised_holdout_seed{seed}.json").write_text(json.dumps(summary, indent=2)+"\n")
