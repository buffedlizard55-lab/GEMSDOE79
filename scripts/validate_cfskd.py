#!/usr/bin/env python3
"""Validate G79-CFSKD raster: format/[0,1]/footprint + dot-overlap vs local archived rasters."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]
NAME="g79-cfskd-exp3-20261022-bda00cff-zeros-DO-NOT-SUBMIT"
def dots(p):
    with rasterio.open(p) as s: return s.read(1)>0, s
def main():
    p=ROOT/"archive"/"g79_cfskd_bda00cff"/f"{NAME}.tif"
    with rasterio.open(p) as s:
        a=s.read(1); meta={"crs":str(s.crs),"shape":[s.height,s.width],"dtype":s.dtypes[0],"count":s.count,"transform":list(s.transform)[:6]}
    with rasterio.open(ROOT/"data"/"raw"/"sample_submission.tif") as s: fp=np.isfinite(s.read(1))
    with rasterio.open(ROOT/"data"/"raw"/"existing_faults.tif") as s: cat=s.read(1)>0
    cand=a>0
    checks={"single_band":meta["count"]==1,"dtype_float32":meta["dtype"]=="float32","shape_3730x3292":meta["shape"]==[3730,3292],
      "crs_epsg32611":meta["crs"]=="EPSG:32611","transform_matches":meta["transform"]==[100.0,0.0,243350.0,0.0,-100.0,4508550.0],
      "no_nan_inf":bool(np.isfinite(a).all()),"range_0_1":bool(a.min()>=0 and a.max()<=1),"binary":set(np.unique(a).tolist())<={0.0,1.0},
      "outside_footprint_zero":int((a[~fp]!=0).sum())==0,"zero_on_catalogue":int((cand&cat).sum())==0}
    refs={"G79-THVC":ROOT/"archive/g79_thvc_33e1f8ec/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif",
          "H79-FNHR":ROOT/"archive/h79_fnhr_a57e2a7f/gems79-h79-fnhr-f3-37654dots-20261022T051800Z-fae5cf3a-DO-NOT-SUBMIT.tif",
          "H79-NHR":ROOT/"archive/h79_nhr_337ac1e9/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif",
          "G79-MAG":ROOT/"archive/g79_mag_730d5ee7/gems79-g79-mag-37654dots-20261022T060000Z-e48a9293.tif"}
    uniq={}
    cand_dil=ndi.distance_transform_edt(~cand)<=3.0
    rng=np.random.default_rng(0); sample_idx=rng.choice(a.size,size=200_000,replace=False)
    for k,rp in refs.items():
        if not rp.exists(): uniq[k]={"missing":True}; continue
        with rasterio.open(rp) as s: ra=s.read(1)
        rd=ra>0; ref_dil=ndi.distance_transform_edt(~rd)<=3.0
        uniq[k]={"ref_dots":int(rd.sum()),"exact_overlap_frac_of_candidate":float((cand&rd).sum()/max(cand.sum(),1)),
                 "within3px_frac_of_candidate":float((cand&ref_dil).sum()/max(cand.sum(),1)),
                 "within3px_frac_of_ref":float((rd&cand_dil).sum()/max(rd.sum(),1)),
                 "binary_spearman_sample":float(spearmanr(a.ravel()[sample_idx],ra.ravel()[sample_idx]).statistic)}
    out={"file":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size,"meta":meta,
         "dots":int(cand.sum()),"checks":checks,"all_checks_passed":all(checks.values()),"uniqueness_local_archives":uniq,
         "scope_note":"Uniqueness vs 4 locally archived rasters only; full 1,108-raster registry restore was not re-run this session - a limitation, fail-closed verdict already negative on holdout."}
    (ROOT/"evidence"/"cfskd"/"validator.json").write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,indent=2))
    return 0 if out["all_checks_passed"] else 1
if __name__=="__main__":
    sys.path[:0]=[str(ROOT/"src")]
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "G79-CFSKD",
        reason="G79-CFSKD is closed and archived; evidence/cfskd/validator.json is frozen.",
    )
    sys.exit(main())
