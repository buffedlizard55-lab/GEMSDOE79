"""G79-CFSKD: K_d residual + Coulomb flank-shadow veto (label-free / visible-only)."""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi

def robust(a, valid):
    out=np.full(a.shape,np.nan,np.float32); v=a[valid]
    if v.size==0: return out
    q25,q50,q75=np.percentile(v,[25,50,75]); s=float(q75-q25) or float(np.std(v)) or 1.0
    out[valid]=((v-q50)/s).astype(np.float32); return out

def kd_residual(K,Th,U,TC,fp):
    """Label-free ridge fit K~[1,Th,U,TC] on footprint pixels; return robust residual + raw inputs mask."""
    m=fp & np.isfinite(K)&np.isfinite(Th)&np.isfinite(U)&np.isfinite(TC)
    idx=np.flatnonzero(m); rng=np.random.default_rng(79)
    take=idx[rng.choice(idx.size,size=min(400_000,idx.size),replace=False)]
    X=np.column_stack([np.ones(take.size),Th.ravel()[take],U.ravel()[take],TC.ravel()[take]]).astype(float)
    y=K.ravel()[take].astype(float)
    mu,sd=X[:,1:].mean(0),X[:,1:].std(0)+1e-9; Xn=(X[:,1:]-mu)/sd
    A=np.column_stack([np.ones(take.size),Xn]); coef=np.linalg.solve(A.T@A+1e-3*np.eye(4),A.T@y)
    pred=np.full(K.shape,np.nan,np.float32)
    Xn_all=np.column_stack([(Th[fp]-mu[0])/sd[0],(U[fp]-mu[1])/sd[1],(TC[fp]-mu[2])/sd[2]])
    pred.ravel()[np.flatnonzero(fp)] = (coef[0]+Xn_all@coef[1:]).astype(np.float32)
    resid=np.where(m,K-pred,np.nan).astype(np.float32)
    return robust(resid,m), coef.tolist()

def endpoints(vis):
    k=np.ones((3,3),int); k[1,1]=0
    n=ndi.convolve(vis.astype(int),k,mode="constant")
    return vis & (n==1)

def coulomb_veto_factor(visible, shape=None):
    """1.0 everywhere except lateral shadow corridor 3-15px from visible faults,
    excluding within 20px of a visible endpoint (tip/relay zone). Analytic Okada
    sign pattern proxy: normal-fault slip relieves Coulomb stress on parallel flanks."""
    vis=np.asarray(visible,bool)
    d=ndi.distance_transform_edt(~vis)
    tips=endpoints(vis)
    dt=ndi.distance_transform_edt(~tips) if tips.any() else np.full(vis.shape,999.0)
    factor=np.ones(vis.shape,np.float32)
    shadow=(d>=3)&(d<=15)&(dt>8)
    factor[shadow]=0.30
    near_tip=(dt<=8)&(d>=3)&(d<=15)
    factor[near_tip]=1.0
    factor[vis]=0.0
    return factor
