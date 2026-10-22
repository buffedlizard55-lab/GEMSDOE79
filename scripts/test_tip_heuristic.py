#!/usr/bin/env python3
import sys
sys.path.insert(0,"src"); sys.path.insert(0,"vendor")
from gems57.grid import load_grid
from pathlib import Path
import numpy as np, rasterio
from gems57.holdout import buffered_component_draw
from gems57 import evaluate_holdout, metric
from scipy import ndimage as ndi
grid=load_grid(Path("data/reference"))
footprint=grid.footprint
cat=grid.catalogue
H,W=footprint.shape
# Load G79-THVC tip logic: extract tips from visible
def extract_tips(visible):
    STRUCT3=np.ones((3,3),dtype=np.int8)
    vis_u8=visible.astype(np.uint8)
    nbr_cnt = ndi.convolve(vis_u8, STRUCT3, mode='constant', cval=0) - vis_u8
    endpoints = visible & ((nbr_cnt==1)|(nbr_cnt==0))
    comp,n_comp = ndi.label(visible, STRUCT3)
    slices = ndi.find_objects(comp)
    tips=[]
    dirs=[]
    for cid, sl in enumerate(slices, start=1):
        if sl is None: continue
        sub = comp[sl]==cid
        if sub.sum()<3: continue
        ep_sub = endpoints[sl] & sub
        ey,ex = np.nonzero(ep_sub)
        if ey.size==0:
            sy,sx = np.nonzero(sub)
            pts=np.column_stack([sy,sx]).astype(np.float64)
            pts_c=pts-pts.mean(axis=0)
            _,_,vt=np.linalg.svd(pts_c, full_matrices=False)
            proj=pts_c @ vt[0]
            picks=[int(np.argmin(proj)), int(np.argmax(proj))]
            ey,ex = sy[picks], sx[picks]
        sy_all,sx_all = np.nonzero(sub)
        pts_all=np.column_stack([sy_all,sx_all]).astype(np.float64)
        oy,ox = sl[0].start, sl[1].start
        for py,px in zip(ey.tolist(), ex.tolist()):
            d=np.hypot(pts_all[:,0]-py, pts_all[:,1]-px)
            loc=pts_all[(d>0)&(d<=9)]
            if loc.shape[0]<2:
                loc=pts_all[d>0]
            if loc.shape[0]==0:
                continue
            vec=np.array([float(py)-loc[:,0].mean(), float(px)-loc[:,1].mean()], dtype=np.float64)
            nrm=float(np.hypot(vec[0],vec[1]))
            if nrm<1e-6: continue
            vec/=nrm
            tips.append((oy+py, ox+px))
            dirs.append(vec)
    return np.array(tips, dtype=np.float64) if tips else np.zeros((0,2)), np.array(dirs, dtype=np.float64) if dirs else np.zeros((0,2))

for seed in (20,):
    folds,_ = buffered_component_draw(grid, seed=seed)
    # For each fold, we will generate prediction based on visible for that fold
    # But for simplicity, generate prediction based on global visible for seed20 (all folds share same visible? Actually buffered_component_draw gives same visible for all folds? Let's check)
    vis_global = folds[0]['visible']
    # vis should be same for all folds for same seed (hidden is union across quadrants, visible is cat & ~collar)
    print("vis sum", vis_global.sum(), "cat sum", cat.sum(), "hidden sum", (cat & ~vis_global).sum())
    tips, dirs = extract_tips(vis_global)
    print(f"seed {seed} tips {len(tips)}")
    # Create forward cone weight map
    R_MAX=38
    gy, gx = np.mgrid[-R_MAX:R_MAX+1, -R_MAX:R_MAX+1].astype(np.float32)
    rr=np.hypot(gy,gx)
    valid_disc=(rr>=1)&(rr<=R_MAX)
    uy=np.divide(gy, rr, out=np.zeros_like(gy), where=valid_disc)
    ux=np.divide(gx, rr, out=np.zeros_like(gx), where=valid_disc)
    exp10=np.exp(-rr/10.0)*(rr<=18)
    exp24=np.exp(-rr/24.0)*valid_disc
    fwd15=np.zeros((H,W), dtype=np.float32)
    fwd35=np.zeros((H,W), dtype=np.float32)
    for (py,px),(vy,vx) in zip(tips, dirs):
        cy,cx=int(round(py)),int(round(px))
        y0,y1=max(0,cy-R_MAX),min(H,cy+R_MAX+1)
        x0,x1=max(0,cx-R_MAX),min(W,cx+R_MAX+1)
        sy=slice(y0-(cy-R_MAX), y1-(cy-R_MAX))
        sx=slice(x0-(cx-R_MAX), x1-(cx-R_MAX))
        cos_th=uy[sy,sx]*float(vy)+ux[sy,sx]*float(vx)
        fwd_pos=np.maximum(cos_th,0)
        cone=fwd_pos**6
        fwd15[y0:y1, x0:x1]=np.maximum(fwd15[y0:y1,x0:x1], cone*exp10[sy,sx])
        fwd35[y0:y1,x0:x1]=np.maximum(fwd35[y0:y1,x0:x1], cone*exp24[sy,sx])
    # Also create far-field basin weight as before
    dist_cat = ndi.distance_transform_edt(~cat)
    dist_edge = ndi.distance_transform_edt(footprint)
    edge_norm = dist_edge/(dist_edge.max()+1e-6)
    # Combine: weight = 0.7*fwd35 + 0.3*far + baseline near distance
    w_global = np.zeros((H,W), dtype=np.float32)
    # Tip weight dominates
    w_global += 0.6*fwd35
    w_global += 0.2*fwd15
    # Add far-field for blind basins: >20px from cat
    far_mask = footprint & (dist_cat>20)
    w_global[far_mask] += 0.15 * np.exp(-(dist_cat[far_mask]-20)/30.0) * (0.5+0.5*edge_norm[far_mask])
    # Also add isotropic near for continuity
    near_mask = footprint & (dist_cat<=20) & (dist_cat>2)
    w_global[near_mask] += 0.1*np.exp(-(dist_cat[near_mask]-8)**2/36)
    # Emit via Poisson
    from gems79.thvc_model import poisson_disk_emit
    # Allow = footprint & (dist_cat>2)
    allow = footprint & (dist_cat>2)
    # Need to convert w_global to 2D for emit
    emitted = poisson_disk_emit(w_global, allow, budget=37654, min_dist_px=2.8)
    print(f"emitted {emitted.sum()}")
    # Evaluate per fold
    for f in folds:
        res,_ = evaluate_holdout.evaluate(emitted, f, footprint)
        print(f"fold {f['name']} dti {res['dti']:.6f} tp {res['tp']:.1f} fp {res['fp']:.1f} n_truth {res['n_truth']} n_emitted {res['n_emitted']}")
    # Pooled
    terms_by_arm={}
    for name,pred in [('tip',emitted)]:
        acc=None
        for f in folds:
            _, t = evaluate_holdout.evaluate(pred, f, footprint)
            acc = t if acc is None else acc+t
        terms_by_arm[name]=acc
    rnd = (np.random.rand(H,W) < 0.007).astype(np.float32) * footprint
    for name,pred in [('rnd',rnd)]:
        acc=None
        for f in folds:
            _, t = evaluate_holdout.evaluate(pred, f, footprint)
            acc = t if acc is None else acc+t
        terms_by_arm[name]=acc
    summ = evaluate_holdout.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate='tip')
    print("pooled tip", summ['scores']['tip'])
    print("pooled rnd", summ['scores']['rnd'])
PY
