import sys; sys.path.insert(0,"src")
import numpy as np
from gems79.cfskd import coulomb_veto_factor, kd_residual
def test_veto_shadow_and_tip():
    v=np.zeros((60,60),bool); v[10:50,30]=True; f=coulomb_veto_factor(v)
    assert f[30,30]==0 and f[30,35]==0.30 and f[30,55]==1.0
def test_kd_residual_removes_lithology_trend():
    rng=np.random.default_rng(0); th=rng.uniform(1,3,(40,40)).astype(np.float32); u=rng.uniform(0,1,(40,40)).astype(np.float32); tc=th+u
    k=(2*th+u).astype(np.float32); fp=np.ones((40,40),bool); r,c=kd_residual(k,th,u,tc,fp)
    assert np.nanmax(np.abs(r))<2.0
