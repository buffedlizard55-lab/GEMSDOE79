"""G79-TIPSTEP: catalogue-geometry-only fault tip extension + collinear stepover bridging.
No external/geophysics layers (absent in checkout). Built ONLY from a visible catalogue mask,
so it is directly reusable inside hide-and-recover folds with the visible mask substituted."""
import numpy as np
from scipy import ndimage as ndi

STRUCT=np.ones((3,3),int)
def endpoints(cat):
    n=ndi.convolve(cat.astype(int),STRUCT,mode='constant')-cat.astype(int)
    return np.argwhere(cat&((n==1)|(n==0))), n
def component_info(cat):
    lab,m=ndi.label(cat,STRUCT)
    sizes=np.bincount(lab.ravel(),minlength=m+1)
    return lab,sizes
def ray_points(cat, max_len=60, step=3.0, min_comp=20, bridge_max=45.0):
    """Return ordered candidate (y,x,score,kind) lists: bridges first, then tip rays."""
    lab,sizes=component_info(cat)
    ends,_=endpoints(cat)
    # endpoint descriptors
    desc=[]
    H,W=cat.shape
    for (y,x) in ends:
        c=lab[y,x]
        if sizes[c]<min_comp: continue
        # same-component pixels within 12 px
        y0,y1=max(0,y-12),min(H,y+13); x0,x1=max(0,x-12),min(W,x+13)
        sub=(lab[y0:y1,x0:x1]==c)
        yy,xx=np.nonzero(sub); yy=yy+y0; xx=xx+x0
        if len(yy)<3: continue
        pts=np.column_stack([yy-y,xx-x]).astype(float)
        # PCA direction of local trace
        cov=np.cov(pts.T)
        vals,vecs=np.linalg.eigh(cov)
        d=vecs[:,np.argmax(vals)]  # (dy,dx) eigenvector in (y,x) order from cov of pts columns (y,x)
        centroid=pts.mean(axis=0)
        # outward = away from local centroid
        if np.dot(d,-centroid)<0: d=-d
        desc.append(dict(y=int(y),x=int(x),comp=int(c),dir=d,size=int(sizes[c])))
    cand=[]  # (score,y,x,kind)
    # stepover bridges between endpoints of different components, collinear with both dirs
    # spatial hash by 45px cells
    from collections import defaultdict
    grid=defaultdict(list)
    for i,e in enumerate(desc): grid[(e['y']//45,e['x']//45)].append(i)
    seen=set()
    for i,e in enumerate(desc):
        for gy in range(e['y']//45-1,e['y']//45+2):
            for gx in range(e['x']//45-1,e['x']//45+2):
                for j in grid.get((gy,gx),[]):
                    if j<=i: continue
                    f=desc[j]
                    if f['comp']==e['comp']: continue
                    dy=f['y']-e['y']; dx=f['x']-e['x']; dist=np.hypot(dy,dx)
                    if dist<6 or dist>bridge_max: continue
                    u=np.array([dy,dx])/dist
                    a1=abs(np.dot(u,e['dir'])); a2=abs(np.dot(u,f['dir']))
                    if a1<0.75 or a2<0.75: continue
                    key=(e['comp'],f['comp'])
                    if key in seen: continue
                    seen.add(key)
                    score=2.0*a1*a2*(1-dist/(bridge_max*2))+np.log10(min(e['size'],f['size']))*0.1
                    t=step
                    while t<dist-2:
                        yy=e['y']+u[0]*t; xx=e['x']+u[1]*t
                        cand.append((float(score),float(yy),float(xx),'bridge')); t+=step
    bridges=len(cand)
    # tip rays, longer components first via score
    for e in desc:
        base=np.log10(e['size'])  # 1.3..2.55
        t=step
        while t<=max_len:
            yy=e['y']+e['dir'][0]*t; xx=e['x']+e['dir'][1]*t
            score=float(base*(1-0.5*t/max_len))
            cand.append((score,float(yy),float(xx),'tip')); t+=step
    cand.sort(key=lambda z:-z[0])
    return cand, dict(endpoints=len(desc), bridge_points=bridges, candidates=len(cand))
def emit(cat_visible, footprint, budget, min_sep=2.8, **kw):
    cand,info=ray_points(cat_visible,**kw)
    dcat=ndi.distance_transform_edt(~cat_visible)
    accepted=np.zeros(cat_visible.shape,bool)
    pts=[]
    # spatial occupancy via boolean grid + local check using accepted mask dilation each accept is costly;
    # use dict of blocked cells: mark neighbourhood in a coarse set
    blocked=set()
    r=int(np.ceil(min_sep))
    for score,y,x,kind in cand:
        if len(pts)>=budget: break
        iy,ix=int(round(y)),int(round(x))
        if not (0<=iy<cat_visible.shape[0] and 0<=ix<cat_visible.shape[1]): continue
        if not footprint[iy,ix] or dcat[iy,ix]<=2.0: continue
        if (iy,ix) in blocked: continue
        # exact min-sep check against nearby accepted
        ok=True
        for ay,ax,_ in pts:
            if abs(ay-iy)<=3 and abs(ax-ix)<=3 and (ay-iy)**2+(ax-ix)**2 < min_sep**2: ok=False;break
        # NOTE pts scan is O(N^2) worst; blocked set prunes most: only check if blocked missed due to rounding
        if not ok: continue
        pts.append((iy,ix,kind)); accepted[iy,ix]=True
        for by in range(iy-r,iy+r+1):
            for bx in range(ix-r,ix+r+1):
                if (by-iy)**2+(bx-ix)**2 < min_sep**2: blocked.add((by,bx))
    info['emitted']=len(pts)
    surf=np.zeros(cat_visible.shape,np.float32)
    for score,y,x,kind in cand:
        iy,ix=int(round(y)),int(round(x))
        if 0<=iy<cat_visible.shape[0] and 0<=ix<cat_visible.shape[1] and score>surf[iy,ix]: surf[iy,ix]=np.float32(score)
    info['_surface']=surf
    kinds={}
    for _,_,k in pts: kinds[k]=kinds.get(k,0)+1
    info['kinds']=kinds
    return accepted, info
def build_surface(cat, **kw):
    cand,info=ray_points(cat,**kw)
    surf=np.zeros(cat.shape,np.float32)
    for score,y,x,kind in cand:
        iy,ix=int(round(y)),int(round(x))
        if 0<=iy<cat.shape[0] and 0<=ix<cat.shape[1] and score>surf[iy,ix]: surf[iy,ix]=score
    return surf,info
