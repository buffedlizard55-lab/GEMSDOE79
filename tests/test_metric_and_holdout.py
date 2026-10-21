"""Test shared arithmetic and geometry, not geological performance."""
import numpy as np
import pytest
from affine import Affine
from gems57 import metric, evaluate_holdout as ev
from gems57.grid import Grid
from gems57.holdout import buffered_component_draw

@pytest.mark.parametrize('seed', range(8))
def test_official_formula_matches_literal_brute_force(seed):
    rng=np.random.default_rng(seed)
    p=rng.random((7,8)); p[p<.4]=0
    truth=rng.random((7,8))<.12
    a=metric.dti_exact(p,truth); b=metric.dti_bruteforce(p,truth)
    for key in ('tp','fp','fn','dti'):
        assert a[key]==pytest.approx(b[key],abs=1e-10)

def test_known_pixels_are_masked_exactly_not_buffered():
    p=np.zeros((11,11)); truth=np.zeros_like(p,dtype=bool); known=truth.copy()
    known[5,5]=True; truth[5,6]=True; p[5,5]=1; p[5,6]=.5
    got=metric.dti_exact(p,truth,known=known)
    assert got['n_emitted']==1 and got['tp']==.5
    assert metric.kernel(np.array([0,1,2,3,4])).tolist()==pytest.approx([1,2/3,1/3,0,0])

def test_additive_terms_and_spatial_pooling():
    p=np.zeros((40,40),np.float32); truth=np.zeros_like(p,dtype=bool)
    p[5,5]=1; p[25,25]=1; truth[5,6]=True; truth[25,24]=True
    fold={'region':np.ones_like(truth),'truth':truth,'visible':np.zeros_like(truth)}
    result,terms=ev.evaluate(p,fold,np.ones_like(truth),block_side=10)
    assert terms.sum(axis=0).tolist()==pytest.approx([result['tp'],result['fp'],result['fn'],2])
    pooled=ev.pooled_summary({'candidate':terms,'control':terms},candidate='candidate',draws=40)
    assert pooled['scores']['candidate']['dti']==pytest.approx(result['dti'])
    assert pooled['paired_differences']['control']['ci95']==[0,0]
    assert pooled['scores']['candidate']['withheld_positive_pixels']==2

def test_invalid_predictions_rejected_before_masking():
    p=np.zeros((5,5)); p[0,0]=np.nan
    fold={'region':np.zeros((5,5),bool),'truth':np.ones((5,5),bool),'visible':np.zeros((5,5),bool)}
    with pytest.raises(ValueError): ev.evaluate(p,fold,np.ones((5,5),bool))

def test_whole_components_and_real_visible_context_buffer():
    fp=np.ones((160,160),bool); cat=np.zeros_like(fp)
    for y in (25,45,105,125):
        for x in (25,45,105,125): cat[y:y+5,x]=True
    grid=Grid(fp,cat,'EPSG:32611',Affine(100,0,0,0,-100,16000),160,160)
    folds,_=buffered_component_draw(grid,seed=20,buffer_px=3,boundary_px=12)
    hidden=folds[0]['hidden_all']
    assert len(folds)==4 and hidden.any()
    for f in folds:
        assert not (f['visible'] & hidden).any()
        assert f['receipt']['nearest_visible_to_truth_px']>3
        assert np.array_equal(f['masked_known'], cat & ~hidden)
        assert not (f['truth'] & ~f['region']).any()
        for y in (25,45,105,125):
            for x in (25,45,105,125):
                assert hidden[y:y+5,x].sum() in (0,5)
