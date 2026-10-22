import copy
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.distance import pdist
from gems79.placement import place
from gems79.status import submission_decision
ROOT=Path(__file__).resolve().parents[1]

def test_poisson_boundary_no_wrap_and_fixed_budget():
    a=np.random.default_rng(1).random((20,21)).astype('float32'); allowed=np.ones_like(a,bool); allowed[:,0]=False
    p,r=place(a,allowed,20)
    assert p.sum()==20 and not (p & ~allowed).any()
    assert pdist(np.argwhere(p)).min()>=3
    q,_=place(a,allowed,20); assert np.array_equal(p,q)

def test_empty_surface_is_not_padded_with_fake_dots():
    p,r=place(np.zeros((5,5)),np.ones((5,5),bool),10)
    assert not p.any() and r['exhausted']

def test_invalid_surface_never_silently_clipped():
    for value in (-.1,float('nan'),float('inf')):
        with pytest.raises(ValueError): place(np.full((5,5),value),np.ones((5,5),bool),5)

def test_format_green_never_means_submit_green():
    card=json.loads((ROOT/'run_card.json').read_text())
    result=submission_decision(card,actual_sha256=card['raster_sha256'],format_passed=True)
    assert result['ok_to_download'] and not result['ok_to_submit']
    assert not result['human_inspection_required_for_this_decision']

def test_edited_ok_flag_cannot_bypass_individual_gates():
    card=json.loads((ROOT/'run_card.json').read_text()); card['ok_to_submit']=True
    card['approved_for_weekly_slot']=True; card['verdict']='promote'
    result=submission_decision(card,actual_sha256=card['raster_sha256'],format_passed=True)
    assert not result['ok_to_submit']
    assert 'matched_current_best_holdout_not_beaten' in result['blockers']

def test_corrupt_bytes_disable_download_and_submission():
    card=json.loads((ROOT/'run_card.json').read_text())
    result=submission_decision(card,actual_sha256='bad',format_passed=True)
    assert not result['ok_to_download'] and not result['ok_to_submit']
