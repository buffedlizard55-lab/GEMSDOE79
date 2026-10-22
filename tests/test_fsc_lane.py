"""G79-FSC lane (session 0a202578): gate logic, geometry primitives and publication agreement.

Software fixtures in the first half produce no geological score; the second half
checks that the published card, evidence, README and site agree.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from gems79 import fsc, fsc_card, fsc_gates as G

ROOT = Path(__file__).resolve().parents[1]


class _Card(dict):
    """Load run_card.json on first use so the pure unit tests do not depend on it."""
    def _load(self):
        if not dict.__len__(self):
            self.update(json.loads((ROOT / 'run_card.json').read_text()))
        return self

    def __getitem__(self, k):
        return dict.__getitem__(self._load(), k)

    def __eq__(self, other):
        return dict(self._load()) == other

    __hash__ = None


CARD = _Card()


# ----------------------------------------------------------------- pure gate logic

def test_holdout_gate_requires_every_incumbent_seed():
    inc = {20: 0.19, 30: 0.19}
    assert G.holdout_gate({20: 0.2, 30: 0.2}, inc)['passed']
    assert not G.holdout_gate({20: 0.2}, inc)['passed']            # missing seed fails
    assert not G.holdout_gate({20: 0.2, 30: 0.19}, inc)['passed']  # tie is not a win
    assert not G.holdout_gate({20: 0.3, 30: 0.3}, {})['passed']    # no incumbent fails


@pytest.mark.parametrize('ci,ok', [([0.01, 0.1], True), ([0.0, 0.1], False), ([-0.01, 0.1], False), (None, False)])
def test_random_control_gate(ci, ok):
    assert G.random_control_gate({20: [0.05, 0.1], 30: ci})['passed'] is ok


@pytest.mark.parametrize('auc,ok', [(0.5, True), (0.90, True), (0.9001, False), (None, False)])
def test_canary_gate_boundary(auc, ok):
    assert G.canary_gate({20: 0.6, 30: auc})['passed'] is ok


def test_novelty_gate_needs_unique_and_complete():
    assert G.novelty_gate({'unique_under_D2': True, 'complete_accessible_scan': True})['passed']
    assert not G.novelty_gate({'unique_under_D2': True, 'complete_accessible_scan': False})['passed']
    assert not G.novelty_gate({'unique_under_D2': False, 'complete_accessible_scan': True})['passed']
    assert not G.novelty_gate(None)['passed']


def test_format_gate_and_text_gate():
    assert G.format_gate({'checks': {'a': True}, 'all_checks_passed': True})['passed']
    assert not G.format_gate({'checks': {'a': True, 'b': False}, 'all_checks_passed': True})['passed']
    assert not G.format_gate({'checks': {}, 'all_checks_passed': True})['passed']
    assert not G.format_gate(None)['passed']
    assert G.text_gate('n', 'x' * 140)['passed']
    assert not G.text_gate('n', 'x' * 141)['passed']
    assert not G.text_gate(' ', 'note')['passed']


def test_decide_fails_closed():
    assert not G.decide({})['ok_to_submit']
    assert G.decide({'a': {'passed': True}})['ok_to_submit']
    d = G.decide({'a': {'passed': True}, 'b': {'passed': False}})
    assert not d['ok_to_submit'] and d['failed_gates'] == ['b'] and d['label'] == 'OK TO SUBMIT: NO'


def test_missing_evidence_root_blocks_every_evidence_gate(tmp_path):
    gates = fsc_card.derive_gates(tmp_path, 'exp1', validator=None, name='n', note='n')
    assert [k for k, g in gates.items() if g['passed']] == ['G7_name_and_note_le_140']


# ----------------------------------------------------------------- geometry primitives

def test_structure_tensor_recovers_orientation_and_concordance():
    y, x = np.mgrid[0:64, 0:64].astype(np.float32)
    ramp_x = np.sin(x / 3.0)          # stripes vary along x: gradient along x -> c2 = +1
    c2, s2, coh, _ = fsc.structure_tensor(ramp_x, 1.0, 3.0)
    assert c2[32, 32] > 0.95 and abs(s2[32, 32]) < 0.05 and coh[32, 32] > 0.9
    same = fsc.concordance(c2, s2, coh, c2, s2, coh)[32, 32]
    ortho = fsc.concordance(c2, s2, coh, -c2, -s2, coh)[32, 32]
    assert same > 0.8 and ortho < 0.05


def test_endpoints_of_a_segment():
    m = np.zeros((20, 20), bool)
    m[5, 3:15] = True
    e = fsc.endpoints(m)
    assert set(zip(*np.nonzero(e))) == {(5, 3), (5, 14)}


def test_greedy_spacing_and_prefix_property():
    rng = np.random.default_rng(0)
    p = rng.random((40, 40)).astype(np.float32)
    ys, xs = fsc.greedy_spaced_order(p, np.ones_like(p, bool), 3.0, 80)
    pts = np.c_[ys, xs].astype(float)
    d = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1)) + np.eye(len(pts)) * 99
    assert d.min() >= 3.0
    assert np.all(np.diff(p[ys, xs]) <= 0)  # accepted in descending probability
    assert fsc.dots_from_order(p.shape, ys, xs, 10).sum() == 10


def test_a1_tip_cone_points_beyond_the_tip():
    vis = np.zeros((60, 60), bool)
    vis[10:30, 30] = True
    fp = np.ones_like(vis)
    c2 = np.full(vis.shape, -1.0, np.float32)   # fabric along y (doubled angle pi)
    s2 = np.zeros(vis.shape, np.float32)
    f = fsc.a1_features(vis, fp, c2, s2)
    g = {k: v.reshape(vis.shape) for k, v in f.items()}
    assert g['tip_cone'][40, 30] > g['tip_cone'][40, 40]   # straight ahead beats off-axis
    assert g['tip_forward'][40, 30] > 0 and g['tip_forward'][0, 30] > 0


# ----------------------------------------------------------------- published state

def test_card_numbers_come_from_frozen_evidence():
    for s in (20, 30):
        ev = json.loads((ROOT / f'evidence/fsc/seed{s}.json').read_text())['official_evaluate_all']
        assert CARD['experiments']['EXP-FSC-1_candidate'][f'seed_{s}']['dti'] == ev['scores']['candidate']['dti']
        a1 = json.loads((ROOT / f'evidence/fsc/seed{s}_a1.json').read_text())
        assert CARD['experiments']['EXP-FSC-3_A1'][f'seed_{s}']['dti'] == a1['official_evaluate_all']['scores']['candidate_a1']['dti']
        assert abs(a1['exp1_rebuild_dti'] - a1['exp1_recorded_dti']) < 1e-4
        assert ev['evaluator_version'] == 'gems57-pooled-hide-v2'


def test_incumbent_is_frozen_thvc():
    assert {k: round(v, 4) for k, v in fsc_card.incumbent(ROOT).items()} == {20: 0.1905, 30: 0.1944}


def test_decision_is_negative_and_labelled():
    # Every FSC arm is below THVC on both seeds: the selector must refuse.
    assert CARD['ok_to_submit'] is False and CARD['verdict'] == 'negative'
    assert 'G1_holdout_beats_incumbent_both_seeds' in CARD['failed_gates']
    assert CARD['submission_name'].endswith('-DO-NOT-SUBMIT')
    assert 'DO-NOT-SUBMIT' in Path(CARD['submission_file']).name
    assert CARD['experiment_count'] == 3 <= CARD['max_experiments']
    assert CARD['submission_slots_used'] == 0 and CARD['organizer_submission_receipt'] is None


def test_published_bytes_zip_and_downloads_dir():
    tif = ROOT / CARD['submission_file']
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == CARD['raster_sha256']
    with zipfile.ZipFile(ROOT / CARD['zip_file']) as z:
        assert z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes()
    names = sorted(p.name for p in (ROOT / 'docs/downloads').iterdir())
    assert names == sorted([tif.name, Path(CARD['zip_file']).name, CARD['submission_name'] + '.json'])


def test_values_in_unit_interval_and_grid():
    import rasterio
    with rasterio.open(ROOT / CARD['submission_file']) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == 'float32' and ds.crs.to_epsg() == 32611
        assert (ds.height, ds.width) == (3730, 3292)
    assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
    assert int((a > 0).sum()) == CARD['positive_pixels']


def test_novelty_evidence_complete_and_literal_reported():
    for stage in ('surface_before_placement', 'final_dots'):
        n = CARD['correlation_overlap_vs_registry'][stage]
        assert n is not None and n['complete_accessible_scan'] is True
        assert n['registry_rasters_checked'] >= 1200
        assert n['worst_literal_forward_overlap'] is not None


def test_readme_and_site_agree_with_card():
    readme = (ROOT / 'README.md').read_text()
    prompt = (ROOT / 'knowledge/project_prompt_0a202578.md').read_text().strip()
    assert prompt in readme
    assert 'OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.' in readme and 'OK TO SUBMIT: YES' not in readme
    assert CARD['raster_sha256'] in readme
    index = (ROOT / 'docs/index.html').read_text()
    assert CARD['decision_line'] in index and CARD['raster_sha256'] in index
    assert json.loads((ROOT / 'docs/run-card.json').read_text()) == CARD
    status = json.loads((ROOT / 'docs/status.json').read_text())
    assert status['ok_to_submit'] is False and status['raster_sha256'] == CARD['raster_sha256']


def test_verify_project_and_site_checks_pass():
    import check_site
    import verify_project
    r = verify_project.verify()
    assert r['all_checks_passed'], [k for k, v in r['checks'].items() if v is not True]
    s = check_site.check_site()
    assert s['ok'], s['problems']


def test_submission_status_blocks_with_gate_reasons():
    import submission_status
    r = submission_status.inspect_current(ROOT)
    assert r['ok_to_download'] is True and r['ok_to_submit'] is False
    assert 'G1_holdout_beats_incumbent_both_seeds' in r['blockers']
    assert 'inspection_error' not in r
