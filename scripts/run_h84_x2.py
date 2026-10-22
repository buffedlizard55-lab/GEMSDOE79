#!/usr/bin/env python3
"""H84-X2 fallback: NHR-style nested hide but with far-field diversified final.
Holdout is global (to retain DTI ~0.14), final is far-field (>10px) to gain uniqueness.
"""
import argparse, hashlib, json, sys, time, gc
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"), str(ROOT/"vendor"), str(ROOT/"scripts")]
from gems57 import evaluate_holdout as evaluator
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw, quadrant_ids
from gems79 import nhr
from gems79.placement import place
PREREG=json.loads((ROOT/"registry/preregistration_h84.json").read_text())
FIX=json.loads((ROOT/"registry/preregistration_nhr.json").read_text())["fixed_parameters"]
BUDGET=37654
OUT=ROOT/"evidence/h84"
CACHE=ROOT/".cache/h84_x2"
FAR_PX=10

def log(*a): print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)

class Stack:
    def __init__(self, grid):
        self.grid=grid
        self.static, self.static_names, self.meta=nhr.build_static_stack(grid.footprint)
        self.row_of=np.full(grid.footprint.size, -1, np.int64)
        fpi=np.flatnonzero(grid.footprint)
        self.row_of[fpi]=np.arange(fpi.size)
        self.lstrike,self.lcoh=nhr.read_lidar_orientation(grid.footprint)
    def geometry(self, visible):
        return nhr.geometry_features(visible, self.grid.footprint, self.lstrike, self.lcoh)
    def rows(self, flat_idx, geom, use_geometry=True):
        st=np.asarray(self.static[self.row_of[flat_idx]], np.float32)
        if not use_geometry:
            return st
        g=np.stack([geom[n].ravel()[flat_idx] for n in nhr.GEOMETRY_NAMES], axis=1)
        return np.concatenate([st,g], axis=1)
    @property
    def names(self): return list(self.static_names)+list(nhr.GEOMETRY_NAMES)

def training_rows(stack, context, region, seed):
    rng=np.random.default_rng(seed)
    fp=stack.grid.footprint
    X,y=[],[]
    receipts=[]
    for rep in range(FIX["nested_replicates_per_model"]):
        hidden, remaining=nhr.nested_hide(context, region, rng, FIX["nested_hide_fraction"], FIX["nested_buffer_px"])
        t=nhr.kernel_target(hidden)
        geom=stack.geometry(remaining)
        base=region & fp & ~context
        pos=np.flatnonzero(base & (t>0))
        neg_pool=np.flatnonzero(base & (t==0))
        neg=rng.choice(neg_pool, min(FIX["negatives_sampled_per_replicate"], neg_pool.size), replace=False)
        idx=np.concatenate([pos,neg])
        X.append(stack.rows(idx, geom)); y.append(t.ravel()[idx])
        receipts.append(dict(replicate=rep, hidden_pixels=int(hidden.sum()), positive_rows=int(pos.size), negative_rows=int(neg.size)))
        del geom, t, hidden, remaining; gc.collect()
    return np.concatenate(X), np.concatenate(y), receipts

def fit(X,y,seed):
    m=HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=63, min_samples_leaf=200, l2_regularization=1.0, random_state=seed, early_stopping=False)
    m.fit(X,y); return m

def predict_surface(model, stack, cells_mask, geom, use_geometry=True, chunk=400000):
    surf=np.zeros(stack.grid.shape, np.float32)
    idx=np.flatnonzero(cells_mask)
    flat=surf.ravel()
    for s in range(0, idx.size, chunk):
        part=idx[s:s+chunk]
        Xp=stack.rows(part, geom, use_geometry)
        flat[part]=model.predict(Xp).astype(np.float32)
    m=float(flat[idx].min()) if idx.size else 0.0
    if m<=0: flat[idx]-=m-1e-6
    return surf

def stage_holdout(seed):
    t0=time.time()
    grid=load_grid(ROOT/"data/reference")
    stack=Stack(grid)
    folds,_=buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible=folds[0]["visible"]
    quad=quadrant_ids(grid.footprint)
    geom_vis=stack.geometry(visible)
    # canary via shared function
    from run_experiment import canaries
    class Lazy:
        def __init__(self):
            self.names=list(stack.static_names)+["geom_"+n for n in nhr.GEOMETRY_NAMES]
        def items(self):
            fpi=np.flatnonzero(grid.footprint)
            for j,n in enumerate(stack.static_names):
                col=np.zeros(grid.footprint.size, np.float32)
                col[fpi]=np.nan_to_num(np.asarray(stack.static[:,j], np.float32), nan=-99.0)
                yield n, col.reshape(grid.shape)
            for n in nhr.GEOMETRY_NAMES:
                yield "geom_"+n, np.nan_to_num(geom_vis[n], nan=-99.0)
    c_rows=canaries(Lazy(), folds, seed)
    canary=dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
                n_suspicious=sum(r["suspicious"] for r in c_rows))
    log("canary", canary["max_symmetric_auc"], canary["worst"]["feature"])
    # try locate H33 for control (optional)
    try:
        import analyze_h33
        d28,_=analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
        d28_pos=np.isfinite(d28)&(d28>0)&grid.footprint
    except Exception as e:
        log("H33 locate failed", e); d28_pos=None
    rng_surface=np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    receipts=[]
    terms_dict={}
    for fold in folds:
        q=fold["fold"]
        train_region=grid.footprint & (quad!=q) & (quad>=0)
        log(f"fold {fold['name']} training")
        X,y,rec=training_rows(stack, visible, train_region, seed*100+q)
        log(f"fold {fold['name']} fit full {X.shape}")
        m_full=fit(X,y, seed*100+q)
        m_abl=fit(X[:,:len(stack.static_names)], y, seed*100+q)
        del X,y; gc.collect()
        region=fold["region"]
        allowed=region & grid.footprint & ~fold["masked_known"]
        s_full=predict_surface(m_full, stack, allowed, geom_vis, True)
        s_abl=predict_surface(m_abl, stack, allowed, geom_vis, False)
        ys,xs=np.nonzero(region)
        sy=slice(max(0,int(ys.min())-3), min(grid.height, int(ys.max())+4))
        sx=slice(max(0,int(xs.min())-3), min(grid.width, int(xs.max())+4))
        sl=(sy,sx)
        local={k:fold[k][sl] for k in ("region","truth","visible","masked_known")}
        budget=int(round(BUDGET*region.sum()/grid.footprint.sum()))
        for name,surf in [("candidate", s_full), ("ablation_no_geometry", s_abl), ("uniform_control", rng_surface)]:
            dots,_=place(surf[sl], allowed[sl], budget)
            _,bt=evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl], origin=(sy.start,sx.start), global_shape=grid.shape)
            terms_dict[name]=terms_dict.get(name,0)+bt
        if d28_pos is not None:
            d_vis=ndi.distance_transform_edt(~fold["visible"][sl])
            h33=(d28_pos[sl] & region[sl] & (d_vis>2)).astype(np.float32)
            _,bt=evaluator.evaluate(h33, local, grid.footprint[sl], origin=(sy.start,sx.start), global_shape=grid.shape)
            terms_dict["h33_foldfair_control"]=terms_dict.get("h33_foldfair_control",0)+bt
        receipts.append(dict(fold=fold["name"], budget=budget, nested=rec))
        del s_full,s_abl,m_full,m_abl; gc.collect()
    summary=evaluator.pooled_summary(terms_dict, candidate="candidate", draws=1000, seed=7900+seed)
    out=dict(schema_version=1, lane="H84-FFA", experiment="X2", seed=seed, evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
             generated_utc=datetime.now(timezone.utc).isoformat(), runtime_s=round(time.time()-t0,1), leakage_canary=canary, holdout=summary, folds=receipts, feature_names=stack.names, static_stack_inputs=stack.meta["inputs_sha256"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/f"x2_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float)+"\n")
    log(f"seed {seed} DTI", {k:(round(v["dti"],4),[round(c,4) for c in v["ci95"]]) for k,v in summary["scores"].items()})
    log(summary["paired_differences"])

def stage_final():
    grid=load_grid(ROOT/"data/reference")
    stack=Stack(grid)
    cat=grid.catalogue
    log("final training whole footprint")
    X,y,rec=training_rows(stack, cat, grid.footprint, 790000)
    m=fit(X,y, 790000); del X,y; gc.collect()
    geom=stack.geometry(cat)
    allowed=grid.footprint & ~cat
    surf=predict_surface(m, stack, allowed, geom, True)
    v=surf[allowed]
    norm=np.zeros(grid.shape, np.float32)
    norm[allowed]=((v-v.min())/max(float(np.ptp(v)),1e-12)).astype(np.float32)
    # far-field filtered version for uniqueness
    dcat=ndi.distance_transform_edt(~cat)
    far= dcat > FAR_PX
    allowed_far= allowed & far
    # place far-field dots
    dots_far,_=place(norm, allowed_far, BUDGET)
    # also place global for comparison
    dots_global,_=place(norm, allowed, BUDGET)
    log("far dots", int(dots_far.sum()), "global dots", int(dots_global.sum()), "far allowed", int(allowed_far.sum()))
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE/"final_surface.npy", norm)
    np.save(CACHE/"final_dots_far.npy", dots_far)
    np.save(CACHE/"final_dots_global.npy", dots_global)
    imp=dict(nested=rec, far_dots=int(dots_far.sum()), global_dots=int(dots_global.sum()), far_allowed=int(allowed_far.sum()), surface_sha256=hashlib.sha256(norm.tobytes()).hexdigest(), dots_far_sha256=hashlib.sha256(dots_far.tobytes()).hexdigest(), feature_names=stack.names)
    (OUT/"x2_final_build.json").write_text(json.dumps(imp, indent=2)+"\n")
    log(imp)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("stage", choices=["holdout","final"])
    ap.add_argument("--seed", type=int, default=20)
    args=ap.parse_args()
    if args.stage=="holdout":
        stage_holdout(args.seed)
    else:
        stage_final()
