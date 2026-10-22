#!/usr/bin/env python3
"""H80-FARFIELD X2: reduced feature set (worm + antislope + geophysics, no scarp amplitude) for uniqueness."""
import sys
from pathlib import Path
import numpy as np, json, time
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
sys.path.insert(0, str(ROOT/"vendor"))
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw, quadrant_ids
from gems57 import evaluate_holdout as evaluator
from gems79 import nhr
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingRegressor
import hashlib, gc

# Load grid and stack
grid=load_grid(ROOT/"data/reference")
from gems79.farfield import build_extended_stack
# We need to load or build stack but then filter features
# For this X2 we will build full stack then select subset
from pathlib import Path
CACHE=ROOT/".cache/farfield"
stack_path=CACHE/"static_stack_farfield_f16.npy"
meta_path=CACHE/"static_stack_farfield.json"
if stack_path.exists():
    import json as js
    meta=js.load(open(meta_path))
    static=np.load(stack_path, mmap_mode="r")
    names=meta["names"]
else:
    from gems79.farfield import build_extended_stack
    static, names, meta = build_extended_stack(grid.footprint, grid.catalogue)

print(f"full static {static.shape} names {len(names)}")
# Define scarp features to exclude
SCARP_FEATS = {"ex_max","ex_max_max5","ex_mean","step_max","step_max_max5","lapneg_max","lappos_max","downface_max","downface_max_max5","upface_max","cross_max","relief","coh100"}
# Find indices to keep
keep_idx = [i for i,n in enumerate(names) if n not in SCARP_FEATS]
print(f"keeping {len(keep_idx)} of {len(names)} base features")
# New static names
new_names = [names[i] for i in keep_idx]
print(new_names)

# Also need geometry
geom_names = nhr.GEOMETRY_NAMES
print(f"geom {geom_names}")

# Build new stack matrix
new_static = np.asarray(static[:, keep_idx], dtype=np.float32)  # keep as float32 for training
# Need row_of mapping
row_of=np.full(grid.footprint.size, -1, np.int64)
fpi=np.flatnonzero(grid.footprint)
row_of[fpi]=np.arange(fpi.size)
lstrike,lcoh=nhr.read_lidar_orientation(grid.footprint)
def geometry(visible):
    return nhr.geometry_features(visible, grid.footprint, lstrike, lcoh)

def rows(flat_idx, geom, use_geometry=True):
    # static part
    # flat_idx are global flat indices
    # Need to map to fpi rows
    r=row_of[flat_idx]
    st=new_static[r]
    if not use_geometry:
        return st
    g=np.stack([geom[n].ravel()[flat_idx] for n in geom_names], axis=1)
    return np.concatenate([st,g], axis=1)

def training_rows(context, region, seed):
    rng=np.random.default_rng(seed)
    fp=grid.footprint
    X_list=[]
    y_list=[]
    for rep in range(3):
        hidden, remaining=nhr.nested_hide(context, region, rng, 0.20, 3)
        t=nhr.kernel_target(hidden)
        geom=geometry(remaining)
        base=region & fp & ~context
        pos=np.flatnonzero(base & (t>0))
        neg_pool=np.flatnonzero(base & (t==0))
        neg=rng.choice(neg_pool, min(200000, neg_pool.size), replace=False)
        idx=np.concatenate([pos,neg]) if pos.size else neg
        X=rows(idx, geom, True)
        y=t.ravel()[idx]
        X_list.append(X); y_list.append(y)
    return np.concatenate(X_list), np.concatenate(y_list)

def fit(X,y,seed):
    m=HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=63, min_samples_leaf=200, l2_regularization=1.0, random_state=seed, early_stopping=False)
    m.fit(X,y)
    return m

def predict_surface(model, cells_mask, geom):
    surf=np.zeros(grid.shape, dtype=np.float32)
    idx=np.flatnonzero(cells_mask)
    flat=surf.ravel()
    for s in range(0, idx.size, 400000):
        part=idx[s:s+400000]
        Xp=rows(part, geom, True)
        flat[part]=model.predict(Xp).astype(np.float32)
    m=float(flat[idx].min()) if idx.size else 0
    if m<=0:
        flat[idx]-=m-1e-6
    return surf

# Test holdout for seeds 20,30
BUDGET=37654
for seed in [20,30]:
    folds,_=buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible=folds[0]["visible"]
    quad=quadrant_ids(grid.footprint)
    # canary quickly
    from run_experiment import canaries
    geom_vis=geometry(visible)
    class Lazy:
        def __init__(self):
            self.names=new_names+["geom_"+n for n in geom_names]
        def items(self):
            fpi2=np.flatnonzero(grid.footprint)
            for j,n in enumerate(new_names):
                col=np.zeros(grid.footprint.size, np.float32)
                col[fpi2]=np.nan_to_num(np.asarray(new_static[:,j], dtype=np.float32), nan=-99.0)
                yield n, col.reshape(grid.shape)
            for n in geom_names:
                yield "geom_"+n, np.nan_to_num(geom_vis[n], nan=-99.0)
    feats=Lazy()
    c_rows=canaries(feats, folds, seed)
    print(f"seed {seed} canary max {max(r['symmetric_auc'] for r in c_rows):.4f} worst {max(c_rows, key=lambda r: r['symmetric_auc'])['feature']}")

    terms={}
    rng_surf=np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    for fold in folds:
        q=fold["fold"]
        train_region=grid.footprint & (quad!=q) & (quad>=0)
        X,y=training_rows(visible, train_region, seed*100+q)
        m=fit(X,y, seed*100+q)
        del X,y; gc.collect()
        region=fold["region"]
        allowed=region & grid.footprint & ~fold["masked_known"]
        geom_vis_fold=geometry(visible)  # visible is same for all folds? Use fold visible? Actually should use fold visible? For holdout, visible is global visible (all folds share same visible). That's okay.
        surf=predict_surface(m, allowed, geom_vis_fold)
        ys,xs=np.nonzero(region)
        sy=slice(max(0, int(ys.min())-3), min(grid.height, int(ys.max())+4))
        sx=slice(max(0, int(xs.min())-3), min(grid.width, int(xs.max())+4))
        sl=sy,sx
        local={k: fold[k][sl] for k in ("region","truth","visible","masked_known")}
        budget=int(round(BUDGET * region.sum() / grid.footprint.sum()))
        # candidate
        from gems79.placement import place
        dots,_=place(surf[sl], allowed[sl], budget)
        _,bt=evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl], origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["candidate"]=terms.get("candidate",0)+bt
        # uniform
        dots_u,_=place(rng_surf[sl], allowed[sl], budget)
        _,bt_u=evaluator.evaluate(dots_u.astype(np.float32), local, grid.footprint[sl], origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["uniform"]=terms.get("uniform",0)+bt_u
        # H33 if available
        try:
            import analyze_h33
            d28,_=analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
            d28_pos=np.isfinite(d28) & (d28>0) & grid.footprint
            d_vis=ndi.distance_transform_edt(~fold["visible"][sl])
            h33=(d28_pos[sl] & region[sl] & (d_vis>2)).astype(np.float32)
            _,bt_h=evaluator.evaluate(h33, local, grid.footprint[sl], origin=(sy.start, sx.start), global_shape=grid.shape)
            terms["h33"]=terms.get("h33",0)+bt_h
        except: pass
        del m, surf
        gc.collect()
    summary=evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900+seed)
    print(f"seed {seed} summary {summary['scores']}")
    print(f"paired {summary['paired_differences']}")

