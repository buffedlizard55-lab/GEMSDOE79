"""H79-NHR: shared dot-definition fix (v3), nested hiding and evidence integrity."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from scipy import ndimage as ndi

from gems57 import uniqueness
from gems79 import nhr

ROOT = Path(__file__).resolve().parents[1]


def _tif(path, arr):
    with rasterio.open(path, 'w', driver='GTiff', width=arr.shape[1], height=arr.shape[0], count=1,
                       dtype='float32', crs='EPSG:32611', transform=Affine(100, 0, 1000, 0, -100, 9000)) as d:
        d.write(arr.astype(np.float32), 1)
    return [{'file': str(path), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}]


def test_budget_matched_dots_takes_exact_top_k_and_includes_ties():
    fp = np.ones((10, 10), bool)
    t = np.arange(100, dtype=np.float32).reshape(10, 10) / 100
    d = uniqueness.budget_matched_dots(t, fp, 5)
    assert d.sum() == 5 and d[9, 5:].all()
    flat = np.full((10, 10), .3, np.float32)
    assert uniqueness.budget_matched_dots(flat, fp, 5).sum() == 100     # ties -> all, never fewer


def test_v3_resolves_continuous_saturation_but_not_constant_or_sparse(tmp_path):
    fp = np.ones((30, 30), bool)
    grad = (np.arange(900, dtype=np.float32).reshape(30, 30) + 1) / 901     # continuous, top cells at bottom
    mine = np.zeros((30, 30), np.float32); mine[2, 2] = mine[2, 10] = 1      # far from the top-2 cells
    reg = _tif(tmp_path / 'grad.tif', grad)
    lit = uniqueness.compare_array_to_registry(mine, reg, fp)
    v3 = uniqueness.compare_array_to_registry(mine, reg, fp, dot_definition='budget-matched-v3')
    assert lit['rows'][0]['my_dots_within_3px_of_theirs'] == 1.0          # literal saturation
    assert v3['rows'][0]['representation'] == 'continuous_surface'
    assert v3['rows'][0]['my_dots_within_3px_of_theirs'] == 0.0
    assert v3['rows'][0]['their_dots'] == 2
    # a constant dense raster still blocks under v3 (ties included): no exemption
    const = _tif(tmp_path / 'const.tif', np.full((30, 30), .2, np.float32))
    assert uniqueness.compare_array_to_registry(mine, const, fp, dot_definition='budget-matched-v3')['rows'][0]['duplicate_by_overlap']
    # a sparse dot field is compared literally under both definitions
    dots = np.zeros((30, 30), np.float32); dots[2, 3] = 1
    sp = _tif(tmp_path / 'sparse.tif', dots)
    r = uniqueness.compare_array_to_registry(mine, sp, fp, dot_definition='budget-matched-v3')['rows'][0]
    assert r['representation'] == 'dot_field' and r['my_dots_within_3px_of_theirs'] == 0.5
    with pytest.raises(ValueError):
        uniqueness.compare_array_to_registry(mine, sp, fp, dot_definition='made-up')


def test_nested_hide_is_whole_component_inside_region_with_buffer():
    ctx = np.zeros((60, 60), bool)
    ctx[10, 5:20] = True; ctx[30, 5:25] = True; ctx[50, 30:55] = True; ctx[5:15, 40] = True
    region = np.zeros_like(ctx); region[:, :30] = True
    rng = np.random.default_rng(0)
    hidden, remaining = nhr.nested_hide(ctx, region, rng, hide_frac=0.5, buffer_px=3)
    assert hidden.any() and not (hidden & ~region).any()
    lab, _ = ndi.label(ctx, np.ones((3, 3), bool))
    for c in np.unique(lab[hidden]):
        assert (hidden[lab == c]).all()          # whole components only
    assert not (remaining & hidden).any()
    assert ndi.distance_transform_edt(~remaining)[hidden].min() > 3


def test_kernel_target_is_official_triangle():
    h = np.zeros((9, 9), bool); h[4, 4] = True
    t = nhr.kernel_target(h)
    assert t[4, 4] == 1 and abs(t[4, 5] - 2 / 3) < 1e-6 and t[4, 7] == 0


def test_recorded_holdout_meets_preregistered_gate_on_both_seeds():
    for seed in (20, 30):
        p = ROOT / f'evidence/nhr/x1_holdout_seed{seed}.json'
        d = json.loads(p.read_text())
        assert d['evaluator_version'] == 'gems57-pooled-hide-v2'
        assert d['leakage_canary']['max_symmetric_auc'] <= 0.90 and d['leakage_canary']['n_suspicious'] == 0
        s, diff = d['holdout']['scores'], d['holdout']['paired_differences']
        assert s['candidate']['dti'] > s['h33_foldfair_control']['dti']
        assert diff['uniform_control']['ci95'][0] > 0
        assert s['candidate']['withheld_positive_pixels'] > 10000
