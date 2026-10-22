#!/usr/bin/env python3
"""Build final G79-CFSKD EXP3 raster (full catalogue). Research artifact, DO NOT SUBMIT (holdout negative)."""
from __future__ import annotations
import hashlib, json, sys, time, zipfile
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/"src"),str(ROOT/"vendor"),str(ROOT/"scripts")]
from gems57.grid import load_grid, write_submission
from gems79.placement import place
from gems79.cfskd import coulomb_veto_factor
from gems79.nhr import kernel_target
from run_cfskd import build_stack, fit, RAW
def main():
    grid=load_grid(RAW); fp=grid.footprint; cat=grid.catalogue
    fp_idx=np.flatnonzero(fp); lookup=np.full(fp.shape,-1,np.int32); lookup.ravel()[fp_idx]=np.arange(fp_idx.size)
    X,names,coef=build_stack(grid)
    tgt=kernel_target(cat); dcat=ndi.distance_transform_edt(~cat)
    pos=np.flatnonzero(fp&(tgt>0)); negpool=np.flatnonzero(fp&(tgt==0)&(dcat>=3))
    rng=np.random.default_rng(79); neg=negpool[rng.choice(negpool.size,size=min(300_000,negpool.size),replace=False)]
    sel=np.concatenate([pos,neg]); rows=lookup.ravel()[sel]
    model=fit(np.asarray(X[rows],dtype=np.float32),tgt.ravel()[sel],79)
    surf=np.zeros(fp.shape,np.float32)
    for i0 in range(0,fp_idx.size,250_000):
        rr=fp_idx[i0:i0+250_000]; surf.ravel()[rr]=np.clip(model.predict(np.asarray(X[lookup.ravel()[rr]],dtype=np.float32)),0,1)
    surf*=coulomb_veto_factor(cat)
    allowed=fp&~cat&(dcat>2)
    dots,info=place(np.where(allowed,surf,0),allowed,37654,spacing=3)
    name="g79-cfskd-exp3-20261022-bda00cff-zeros-DO-NOT-SUBMIT"
    out=ROOT/"archive"/"g79_cfskd_bda00cff"/f"{name}.tif"; out.parent.mkdir(parents=True,exist_ok=True)
    arr=np.where(dots,1.0,0.0).astype(np.float32)
    rep=write_submission(out,arr,mode="zeros")
    zpath=out.with_suffix(".zip")
    with zipfile.ZipFile(zpath,"w",zipfile.ZIP_DEFLATED) as z: z.write(out,out.name)
    meta={"file":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size,
          "zip_sha256":hashlib.sha256(zpath.read_bytes()).hexdigest(),"dots":int(dots.sum()),"placement":info,
          "submission_name":name,"note":"G79-CFSKD EXP3 KD+Coulomb veto; HOLDOUT-DTI 0.0654/0.0678 NEGATIVE - do not submit"[:140],
          "writer_report":rep}
    (out.with_suffix(".json")).write_text(json.dumps(meta,indent=2)+"\n"); print(json.dumps(meta,indent=2))
if __name__=="__main__":
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "G79-CFSKD",
        reason="G79-CFSKD is closed and archived (HOLDOUT-DTI 0.0654/0.0678 < H33; archive/g79_cfskd_bda00cff/ frozen).",
    )
    main()
