#!/usr/bin/env python3
"""G79-CFSKD preregistered 3 experiments, seeds 20/30, gems57-pooled-hide-v2."""
from __future__ import annotations
import hashlib, json, sys, time
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/"src"),str(ROOT/"vendor")]
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw, quadrant_ids
from gems57 import evaluate_holdout as ev
from gems79.placement import place
from gems79.cfskd import robust, kd_residual, coulomb_veto_factor
from gems79.nhr import kernel_target
RAW=ROOT/"data"/"raw"; OUT=ROOT/"evidence"/"cfskd"; OUT.mkdir(parents=True,exist_ok=True)
BUDGET=37654
def log(*a): print(f"[{time.strftime('%H:%M:%S')}]",*a,flush=True)

def build_stack(grid):
    fp=grid.footprint; fp_idx=np.flatnonzero(fp)
    cache=ROOT/".cache"/"cfskd"; cache.mkdir(parents=True,exist_ok=True)
    # first pass: collect names count = 19 tf +3 hp +1 transtension +4 rad +4 ext +5 lidar +2 kd = 38
    names=[]; 
    def plan(n): names.append(n)
    tf_names=[]
    with rasterio.open(RAW/"training_features.tif") as s: desc=list(s.descriptions)
    for d in desc: tf_names.append(d.split(" - ")[0].strip()); plan(f"tf_{d.split(' - ')[0].strip()}")
    for n in ("hp15_det_elev_slope","hp15_iso_grav_anom_hg","hp15_tmi_hg"): plan(n)
    plan("transtension")
    with rasterio.open(RAW/"external"/"geodawn_rad_u8.tif") as s: rad_names=list(s.descriptions)
    for n in rad_names: plan(f"rad_{n}")
    with rasterio.open(RAW/"external"/"geodawn_extensions_u8.tif") as s: ext_names=list(s.descriptions)
    for n in ext_names: plan(f"ext_{n}")
    for n in ("step_max","ex_max","cross_max","relief","coh100"): plan(f"lidar_{n}")
    plan("kd_residual"); plan("kd_coherence")
    F=len(names); mm=np.memmap(cache/"X.f16",dtype=np.float16,mode="w+",shape=(fp_idx.size,F))
    def push(j,a,v):
        mm[:,j]=robust(a,v&fp).ravel()[fp_idx].astype(np.float16)
    with rasterio.open(RAW/"training_features.tif") as s:
        saved={}
        for b in range(1,s.count+1):
            short=tf_names[b-1]; a=s.read(b).astype(np.float32); v=np.isfinite(a)&(a>-1e30)
            push(b-1,a,v)
            if short in("det_elev_slope","iso_grav_anom_hg","tmi_hg","geod_dilaterate","geod_shearrate"): saved[short]=(a,v)
            else: del a,v
        j=19
        for short in("det_elev_slope","iso_grav_anom_hg","tmi_hg"):
            a,v=saved[short]; med=float(np.median(a[v&fp])); f=np.where(v,a,med); r=(f-ndi.gaussian_filter(f,15)).astype(np.float32); del f; push(j,r,v); j+=1; del r
        dil,vd=saved["geod_dilaterate"]; shr,vs=saved["geod_shearrate"]; m=vd&vs&fp
        z=np.zeros(fp.shape,np.float32); z[m]=(((dil[m]-np.median(dil[m]))/(np.std(dil[m])+1e-9))*((shr[m]-np.median(shr[m]))/(np.std(shr[m])+1e-9))).astype(np.float32)
        push(j,z,m); del z,saved
    j=23; rad={}
    with rasterio.open(RAW/"external"/"geodawn_rad_u8.tif") as s:
        for i,n in enumerate(rad_names):
            a=s.read(i+1).astype(np.float32); rad[n]=np.where((a>0)&fp,a,np.nan); push(j,a,(a>0)&fp); j+=1
    with rasterio.open(RAW/"external"/"geodawn_extensions_u8.tif") as s:
        for i,n in enumerate(ext_names):
            a=s.read(i+1).astype(np.float32); push(j,a,(a>0)&fp); j+=1; del a
    with rasterio.open(RAW/"external"/"lidar_scarp_features_u8.tif") as s:
        dl=list(s.descriptions)
        for n in ("step_max","ex_max","cross_max","relief","coh100"):
            a=s.read(dl.index(n)+1).astype(np.float32); push(j,a,(a>0)&fp); j+=1; del a
    kd,coef=kd_residual(rad["K"],rad["Th"],rad["U"],rad["TC"],fp); del rad
    mm[:,j]=kd.ravel()[fp_idx].astype(np.float16); j+=1
    kdf=np.nan_to_num(kd); coh=ndi.gaussian_filter(np.abs(kdf),1.0).astype(np.float32); del kdf,kd
    mm[:,j]=robust(coh,fp).ravel()[fp_idx].astype(np.float16)
    mm.flush(); return mm,names,coef

def fit(X,y,seed):
    m=HistGradientBoostingRegressor(loss="squared_error",learning_rate=0.07,max_iter=240,max_leaf_nodes=63,min_samples_leaf=180,l2_regularization=1.5,early_stopping=True,validation_fraction=0.1,n_iter_no_change=15,random_state=seed)
    m.fit(X,y); return m

def main():
    t0=time.time(); grid=load_grid(RAW); fp=grid.footprint; cat=grid.catalogue
    fp_idx=np.flatnonzero(fp); lookup=np.full(fp.shape,-1,np.int32); lookup.ravel()[fp_idx]=np.arange(fp_idx.size)
    X,names,coef=build_stack(grid); kd_idx=[names.index("kd_residual"),names.index("kd_coherence")]
    base_idx=[i for i in range(len(names)) if i not in kd_idx]
    log("features",len(names),"kd coef",coef)
    quad=quadrant_ids(fp)
    rngU=np.random.default_rng(123)
    results={}
    for seed in (20,30):
        folds,_=buffered_component_draw(grid,seed=seed,buffer_px=3)
        canary_max=0.0; canary_worst=None
        terms={k:[] for k in ("EXP1","EXP2","EXP3","UNIFORM")}
        npos=0
        for fold in folds:
            q=fold["fold"]; region=fold["region"]; visible=fold["visible"]; hidden=fold["truth"]
            npos+=int(hidden.sum())
            train=(quad!=q)&fp
            tgt=kernel_target(visible&train)
            dvis=ndi.distance_transform_edt(~visible)
            pos=np.flatnonzero(train&fp&(tgt>0)); negpool=np.flatnonzero(train&fp&(tgt==0)&(dvis>=3))
            rng=np.random.default_rng(seed*100+q); neg=negpool[rng.choice(negpool.size,size=min(250_000,negpool.size),replace=False)]
            sel=np.concatenate([pos,neg]); rows=lookup.ravel()[sel]
            models={}
            for key,idxs in (("EXP1",base_idx),("EXP2",list(range(len(names))))):
                models[key]=fit(np.asarray(X[rows][:,idxs],dtype=np.float32),tgt.ravel()[sel],seed+q)
            # canaries on held fold (label = hidden truth)
            hid=np.flatnonzero(region&hidden); negh=np.flatnonzero(region&fp&~fold["masked_known"]&(ndi.distance_transform_edt(~cat)>=0))
            negh=negh[rng.choice(negh.size,size=min(120_000,negh.size),replace=False)]
            csel=np.concatenate([hid,negh]); yv=np.zeros(csel.size); yv[:hid.size]=1
            crow=lookup.ravel()[csel]
            for j,n in enumerate(names):
                v=np.asarray(X[crow,j],dtype=np.float32); ok=np.isfinite(v)
                if ok.sum()>100 and 0<yv[ok].sum()<ok.sum():
                    auc=max(roc_auc_score(yv[ok],v[ok]),1-roc_auc_score(yv[ok],v[ok]))
                    if auc>canary_max: canary_max,canary_worst=float(auc),n
            dcat=ndi.distance_transform_edt(~fold["masked_known"])
            allowed=region&fp&~fold["masked_known"]&(dcat>2)
            budget=int(round(BUDGET*allowed.sum()/ (fp&~cat).sum()))  # per-fold share of the global 37,654 budget
            surfs={}
            reg_idx=np.flatnonzero(region&fp); rrows=lookup.ravel()[reg_idx]
            for key,idxs in (("EXP1",base_idx),("EXP2",list(range(len(names))))):
                s=np.zeros(fp.shape,np.float32); s=np.zeros(fp.shape,np.float32)
                for i0 in range(0,rrows.size,250_000):
                    rr=rrows[i0:i0+250_000]; s.ravel()[reg_idx[i0:i0+250_000]]=np.clip(models[key].predict(np.asarray(X[rr][:,idxs],dtype=np.float32)),0,1)
                surfs[key]=s
            surfs["EXP3"]=surfs["EXP2"]*coulomb_veto_factor(visible)
            surfs["UNIFORM"]=np.where(allowed,rngU.random(fp.shape).astype(np.float32),0)
            for key,surf in surfs.items():
                dots,info=place(np.where(allowed,surf,0),allowed,budget,spacing=3)
                r,term=ev.evaluate(dots.astype(np.float32),fold,fp); terms[key].append(term)
        # ev.evaluate returns per-20km-block terms per fold; concatenating folds along
        # the block axis and pooling via the shared summary is the evaluator's intended use.
        concat={k:np.concatenate(v,axis=0) for k,v in terms.items()}
        summ=ev.pooled_summary(concat,draws=1000,seed=999,candidate="EXP3")
        results[f"seed{seed}"]={"withheld":npos,"canary_max_auc":canary_max,"canary_worst":canary_worst,"summary":summ}
        log(seed, {k:round(v["dti"],4) for k,v in summ["scores"].items()}, "canary",round(canary_max,4),canary_worst)
    (OUT/"holdout_results.json").write_text(json.dumps(results,indent=2))
    log("done",time.time()-t0)
if __name__=="__main__": main()
