#!/usr/bin/env python3
"""Lane TIPRELAY-E1: catalogue-only tip propagation + stepover bridge surface.
Hide-and-recover via vendor gems57 (buffered_component_draw, seeds 20/30), pooled DTI a=0.2 b=0.8 300m.
Surface derived ONLY from visible catalogue per seed. No physics features (cache absent in sandbox)."""
import sys, json, hashlib, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor')]
from gems57 import grid as G, holdout as HO, evaluate_holdout as EH
from gems79.placement import place

def tips_and_strike(vis):
    lab,n=ndi.label(vis, structure=np.ones((3,3)))
    # endpoint: exactly 1 neighbour
    cnt=ndi.convolve(vis.astype(int), np.ones((3,3)), mode='constant')-vis
    ys,xs=np.nonzero(vis & (cnt==1))
    tips=[]
    for y,x in zip(ys,xs):
        comp=lab[y,x]
        yy,xx=np.nonzero((lab==comp))
        d=np.hypot(yy-y,xx-x); m=d<=7
        if m.sum()<3: continue
        pts=np.stack([xx[m]-x, yy[m]-y],1).astype(float)  # from tip inward
        c=np.cov(pts.T); vals,vecs=np.linalg.eigh(c); v=vecs[:,np.argmax(vals)]
        inward=pts.mean(0); 
        if np.dot(v,inward)<0: v=-v
        strike=-v  # propagation direction = opposite of inward mean direction approx
        # refine: direction away from local centroid
        strike=np.array([x,y],float)-np.array([xx[m].mean(),yy[m].mean()])
        if np.hypot(*strike)<1e-6: strike=-inward
        strike=strike/np.hypot(*strike)
        tips.append((y,x,strike,comp))
    return tips,lab

def build_surface(vis, fp, bridges=True):
    surf=np.zeros(vis.shape,np.float32); tips,lab=tips_and_strike(vis)
    H,W=vis.shape
    for y,x,s,comp in tips:
        for d in range(3,26):
            cy,cx=y+s[1]*d, x+s[0]*d
            wgt=np.exp(-d/11.0)
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    yy,xx=int(round(cy))+dy,int(round(cx))+dx
                    if 0<=yy<H and 0<=xx<W:
                        lat=np.hypot(yy-cy,xx-cx); surf[yy,xx]+=wgt*np.exp(-(lat**2)/1.5)
    if bridges:
        # collinear tip pairs, different components, 5-30px, facing each other
        for i,(y1,x1,s1,c1) in enumerate(tips):
            for y2,x2,s2,c2 in tips[i+1:]:
                if c1==c2: continue
                vx,vy=x2-x1,y2-y1; dist=np.hypot(vx,vy)
                if not (5<=dist<=30): continue
                u=np.array([vx,vy])/dist
                if np.dot(s1,u)<0.55 or np.dot(s2,-u)<0.55: continue
                steps=int(dist)
                for t in range(1,steps):
                    yy,xx=int(round(y1+vy*t/steps)),int(round(x1+vx*t/steps))
                    if 0<=yy<H and 0<=xx<W: surf[yy,xx]+=0.8*np.exp(-dist/25.0)
    surf[~fp]=0; surf[vis]=0
    return surf

def main():
    grid=G.load_grid(ROOT/'data'/'reference'); fp=grid.footprint; cat=grid.catalogue
    out={'lane':'TIPRELAY-E1','evaluator':EH.VERSION,'arms':{}}
    all_terms={}
    for seed in (20,30):
        folds,_=HO.buffered_component_draw(grid,seed=seed,hide_frac=0.20,buffer_px=3)
        vis=folds[0]['visible']; masked=folds[0]['masked_known']
        dist=ndi.distance_transform_edt(~vis)
        allowed=fp & ~vis & (dist>2)
        terms={}
        # canary: surface alone AUC on withheld positives vs negatives
        from sklearn.metrics import roc_auc_score
        surf=build_surface(vis,fp,bridges=True)
        terms_surf={}
        for name,s,budget in [('tiprelay',surf,36500),('random',np.random.default_rng(seed).random(surf.shape).astype(np.float32),36500)]:
            dots,info=place(np.where(allowed,s,0),allowed,budget,spacing=3)
            pred=dots.astype(np.float32); fold_terms=[]
            for f in folds:
                r,t=EH.evaluate(pred,f,fp,origin=(0,0),global_shape=grid.shape); fold_terms.append(t)
            terms[name]=np.concatenate(fold_terms) if False else fold_terms[0]*0+sum(fold_terms)  # terms are per-block arrays; sum pools blocks? use pooled_summary on summed? Instead stack
            # pooled_summary expects per-block terms aligned; sum across folds double counts blocks -> use evaluate terms summed elementwise is correct pooling of additive terms
            all_terms.setdefault(name,[]).append(terms[name])
            print(seed,name,'dots',int(dots.sum()),flush=True)
        # canary on seed surface
        truth=np.zeros_like(vis); 
        for f in folds: truth|= f['truth']
        act=fp & folds[0]['region'] & ~masked
        pos=surf[act&truth]; neg=surf[act&~truth]
        rng=np.random.default_rng(0); neg=rng.choice(neg,size=min(100000,neg.size),replace=False)
        y=np.r_[np.ones(pos.size),np.zeros(neg.size)]; v=np.r_[pos,neg]
        auc=roc_auc_score(y,v); out.setdefault('canary',{})[str(seed)]={'feature':'tiprelay_surface','auc':float(auc),'sym_auc':float(max(auc,1-auc)),'pass_le_0.90':bool(max(auc,1-auc)<=0.90),'n_pos':int(pos.size)}
        print('canary',seed,auc,flush=True)
    pooled=EH.pooled_summary({k: np.sum(v,axis=0) for k,v in all_terms.items()}, draws=400, seed=1, candidate='tiprelay')
    out['pooled']=pooled
    # final artifact from FULL catalogue
    surf=build_surface(cat,fp,bridges=True)
    dist=ndi.distance_transform_edt(~cat); allowed=fp & ~cat & (dist>2)
    dots,info=place(np.where(allowed,surf,0),allowed,36500,spacing=3)
    out['final_dots']=int(dots.sum())
    np.save(ROOT/'evidence'/'tiprelay_final_dots.npy', dots)
    (ROOT/'evidence'/'tiprelay_experiment.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps(pooled,indent=2)[:2000])
if __name__=='__main__': main()
