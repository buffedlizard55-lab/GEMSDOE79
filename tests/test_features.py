"""Software fixtures only; none of these numbers are scientific scores."""
import numpy as np
import pytest
from gems79.features import registration, unit_ranks

@pytest.mark.parametrize('lag', [-3,-2,-1,1,2,3])
def test_registration_recovers_known_shift(lag):
    b = np.random.default_rng(79).normal(size=(100,15)).astype('float32')
    a = b[:, 3+lag:12+lag]
    gain, found, corr = registration(a,b)
    assert np.all(found == lag)
    np.testing.assert_allclose(corr,1,atol=1e-6)
    assert np.all(gain > 0)

def test_zero_shift_does_not_invent_displacement():
    b = np.random.default_rng(12).normal(size=(100,15)).astype('float32')
    gain, _, _ = registration(b[:,3:12], b)
    np.testing.assert_allclose(gain,0,atol=1e-6)

def test_flat_profiles_abstain():
    gain, _, corr = registration(np.zeros((20,9)),np.zeros((20,15)))
    assert not gain.any() and np.isfinite(corr).all()

def test_registration_shape_mismatch_rejected():
    with pytest.raises(ValueError): registration(np.zeros((2,8)), np.zeros((2,15)))

def test_constant_field_supplies_no_evidence():
    a = np.ones((5,5),dtype='float32'); mask = np.ones_like(a,dtype=bool)
    assert not unit_ranks(a,mask).any()

def test_rank_ties_and_outside_mask():
    a=np.array([[2,2,4],[8,0,0]],dtype='float32'); mask=a>0
    p=unit_ranks(a,mask)
    assert p[0,0]==p[0,1] and np.all(p[~mask]==0)
    assert p.min()>=0 and p.max()<=1
