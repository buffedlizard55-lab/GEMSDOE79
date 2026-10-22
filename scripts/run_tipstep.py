#!/usr/bin/env python3
"""G79-TIPSTEP Experiment 1: holdout (seeds 20/30) + final unique TIF + novelty scan."""
import sys, json, hashlib, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor')]
from gems57.grid import load_grid
from gems57 import holdout, evaluate_holdout
from gems57.submission_writer import write_submission
from gems79.tipstep import emit, build_surface
from sklearn.metrics import roc_auc_score

NAME="gems79-tipstep-20261022"
NOTE="G79-TIPSTEP catalogue tip-extension + collinear stepover bridges, dotted 3px, >2px off catalogue"
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    t0=time.time(); g=load_grid(ROOT/'data/reference'); fp,cat=g.footprint,g.catalogue
    out={'lane':'G79-TIPSTEP','hypothesis':'Unmapped faults are disproportionately straight continuations beyond mapped tips and collinear stepover bridges between nearby fault tips; dotted 3px emission >2px off catalogue captures them at low FP cost.','mimic':'Roads/drainage lineaments and catalogue digitisation fragmentation (bridges may merely reconnect one fault split by mapping, not a hidden fault).','experiments':[]}
    final_budget=40000
    hold={}
    for seed in (20,30):
        folds,quad=holdout.buffered_component_draw(g,seed=seed,buffer_px=3,boundary_px=12)
        vis=folds[0]['visible']
        dots_c,info_c=emit(vis,fp,final_budget)
        surf=info_c.pop('_surface'); info={k:v for k,v in info_c.items()}
        truth=np.zeros(fp.shape,bool)
        for f in folds: truth|=f['truth']
        active=fp & ~folds[0]['masked_known']
        pos=active&truth; dvis=ndi.distance_transform_edt(~vis); dtr=ndi.distance_transform_edt(~truth)
        neg=active&~truth&(dtr>3)&(dvis>3)
        rng=np.random.default_rng(seed); pi=np.flatnonzero(pos.ravel()); ni=np.flatnonzero(neg.ravel())
        ns=rng.choice(ni,size=min(len(ni),len(pi)*3),replace=False)
        for feat_nm,feat in [('tipstep_surface',surf),('dist_to_visible',-dvis)]:
            y=np.r_[np.ones(len(pi)),np.zeros(len(ns))]; s=np.r_[feat.ravel()[pi],feat.ravel()[ns]]
            a=float(roc_auc_score(y,s))
            out.setdefault('canaries',{})[f'seed{seed}_{feat_nm}']={'auc':a,'symmetric_auc':max(a,1-a),'withheld':int(len(pi))}
        n=int(dots_c.sum())
        rng=np.random.default_rng(seed+999); allowed=fp&~folds[0]['masked_known']&(ndi.distance_transform_edt(~cat)>2)
        idx=np.flatnonzero(allowed.ravel()); pick=rng.choice(idx,size=min(n,len(idx)),replace=False)
        dots_u=np.zeros(fp.shape,bool); dots_u.ravel()[pick]=True
        arms={}
        for nm,dots in [('TIPSTEP',dots_c),('UNIFORM',dots_u)]:
            terms=[]
            for f in folds:
                res,trm=evaluate_holdout.evaluate(dots.astype(np.float32),f,fp); terms.append(trm)
            arms[nm]=np.vstack(terms)
        pooled=evaluate_holdout.pooled_summary(arms,draws=1000,seed=520810,candidate='TIPSTEP')
        hold[f'seed{seed}']={'emitted':n,'surface_info':info,'pooled':pooled}
        print(f"seed{seed} TIPSTEP HOLDOUT-DTI={pooled['scores']['TIPSTEP']['dti']:.4f} CI{pooled['scores']['TIPSTEP']['ci95']} n={pooled['scores']['TIPSTEP']['withheld_positive_pixels']} UNIFORM={pooled['scores']['UNIFORM']['dti']:.4f} diff={pooled['paired_differences']['UNIFORM']}",flush=True)
    out['holdout']=hold
    # final
    dots,info=emit(cat,fp,final_budget); info.pop('_surface',None); out['final_info']=info; out['final_dots']=int(dots.sum())
    pred=dots.astype(np.float32)
    # outside footprint must be 0 for writer with zeros-outside convention: writer requires no positive outside fp (ok) but file will have 0 outside, finite everywhere
    dest=ROOT/'docs/downloads'/f"{NAME}-{int(dots.sum())}dots-zeros.tif"
    for suf in ('.tif','.zip','.json'):
        q=dest.with_suffix(suf)
        if q.exists(): q.unlink()
    dest.parent.mkdir(parents=True,exist_ok=True)
    meta=write_submission(dest,pred,ROOT/'data/reference/sample_submission.tif',fp,note=NOTE,name=NAME,catalogue=cat,metadata={'lane':'G79-TIPSTEP'})
    out['submission']={'name':NAME,'note':NOTE,'note_chars':len(NOTE),'file':str(dest.relative_to(ROOT)),'sha256':sha(dest),'dots':int(dots.sum())}
    print('FINAL',out['submission'],flush=True)
    (ROOT/'evidence/tipstep_experiment1.json').write_text(json.dumps(out,indent=2))
    print('elapsed',time.time()-t0)
if __name__=='__main__': main()
