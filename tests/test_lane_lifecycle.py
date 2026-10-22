"""Software-only terminal-lane protection; never executes geological models."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from gems79.lifecycle import LaneClosedError, require_open_lane

ROOT = Path(__file__).resolve().parents[1]


def write_card(root, **changes):
    card = dict(lane='fixture-lane', verdict='in_progress')
    card.update(changes)
    (root / 'run_card.json').write_text(json.dumps(card))


@pytest.mark.parametrize('verdict', ['negative', 'promote', None, '', 'unknown'])
def test_terminal_or_unknown_verdict_cannot_resume(tmp_path, verdict):
    write_card(tmp_path, verdict=verdict)
    with pytest.raises(LaneClosedError, match='lane is closed'):
        require_open_lane(tmp_path, 'fixture-lane')


@pytest.mark.parametrize('verdict', ['pending', 'in_progress'])
def test_explicit_nonterminal_state_only(tmp_path, verdict):
    write_card(tmp_path, verdict=verdict)
    assert require_open_lane(tmp_path, 'fixture-lane') is None


@pytest.mark.parametrize('changes', [dict(stop_reason='duplicate'), dict(stopped=True)])
def test_stop_cannot_be_overridden_by_nonterminal_verdict(tmp_path, changes):
    write_card(tmp_path, **changes)
    with pytest.raises(LaneClosedError):
        require_open_lane(tmp_path, 'fixture-lane')


def test_other_lane_cannot_reuse_runner(tmp_path):
    write_card(tmp_path)
    with pytest.raises(LaneClosedError, match='mismatched'):
        require_open_lane(tmp_path, 'another-lane')


@pytest.mark.parametrize('raw', ['', '{', '[]', 'null'])
def test_missing_or_invalid_card_fails_closed(tmp_path, raw):
    (tmp_path / 'run_card.json').write_text(raw)
    with pytest.raises(LaneClosedError):
        require_open_lane(tmp_path, 'fixture-lane')


def test_absent_card_fails_closed(tmp_path):
    with pytest.raises(LaneClosedError):
        require_open_lane(tmp_path, 'fixture-lane')


@pytest.mark.parametrize('script,args', [
    ('run_nhr.py', ['holdout', '--seed', '20']),
    ('run_nhr.py', ['final']),
    ('nhr_uniqueness.py', ['surface']),
    ('nhr_uniqueness.py', ['final']),
    ('build_nhr_submission.py', []),
    ('finalize_nhr.py', []),
    ('nhr_overlap_chance.py', []),
    ('nhr_surface_flagged.py', []),
    ('nhr_distance_profile.py', []),
    ('run_stepco_experiment.py', []),
    ('run_stepco_s2.py', []),
    ('build_stepco_run_card.py', []),
    ('supplementary_uniqueness_stepco.py', []),
    ('run_holdout_g79b.py', []),
    ('build_submission_g79b.py', []),
    ('cap_cost_g79b.py', []),
    ('build_ff_candidate.py', []),
    ('run_g79_thvc.py', ['--stage', 'seed20']),
    ('run_asym.py', ['surface']),
    ('finalize_asym.py', []),
    ('asym_surface_diagnostic.py', []),
    ('run_edge_lane.py', []),
    ('run_ffas.py', ['holdout', '--seed', '20']),
    ('build_ffas_submission.py', []),
    ('finalize_ffas.py', []),
    ('ffas_uniqueness.py', ['surface']),
    ('ffas_overlap_chance.py', []),
    ('run_cov.py', ['holdout', '--seed', '20']),
    ('build_cov_submission.py', []),
    ('finalize_cov.py', []),
    ('cov_uniqueness.py', ['surface']),
    ('run_dilstep.py', []),
    ('dilstep_scan.py', []),
    ('emit_dilstep_research.py', []),
    ('run_fgr.py', ['holdout', '--seed', '20']),
    ('finalize_fgr.py', []),
    ('run_mrnd.py', ['holdout', '--seed', '20']),
    ('mrnd_uniqueness.py', ['surface']),
    ('finalize_mrnd.py', []),
])
def test_current_scientific_commands_refuse_before_writing(script, args):
    paths = (
        [ROOT / 'run_card.json', ROOT / 'run_card_stepco.json', ROOT / 'run_card_g79b.json', ROOT / 'run_card_asym.json']
        + list((ROOT / 'evidence/nhr').glob('*.json'))
        + list((ROOT / 'evidence/ffas').glob('*.json'))
        + list((ROOT / 'docs/downloads').glob('*'))
    )
    frozen = {p: p.read_bytes() for p in paths if p.is_file()}
    cache = ROOT / '.cache/nhr'
    before = set(cache.rglob('*')) if cache.exists() else set()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 2, result.stderr
    err = result.stderr
    assert 'no files changed' in err.lower()
    assert ('lane is closed' in err) or ('mismatched' in err)
    assert all(p.read_bytes() == data for p, data in frozen.items())
    assert (set(cache.rglob('*')) if cache.exists() else set()) == before


def test_site_description_does_not_claim_failed_artifact_is_unique():
    from bs4 import BeautifulSoup
    for path in (ROOT / 'docs').glob('*.html'):
        meta = BeautifulSoup(path.read_text(), 'html.parser').find('meta', attrs={'name': 'description'})
        if meta:
            assert 'a validated, unique GeoTIFF' not in meta.get('content', '')
