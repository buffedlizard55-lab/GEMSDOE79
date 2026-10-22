"""Software-only preflight fixtures: these are not competition measurements."""
import json
from pathlib import Path
import preflight_new_lane as p
from verify_project import witness_report_checks

ROOT = Path(__file__).resolve().parents[1]


def test_report_consistency_and_forged_preflight_rejected(tmp_path):
    assert all(witness_report_checks(ROOT).values())
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    for filename in ('universal_overlap_certificate.json', 'witness_review_20261022_a7d092d7.json',
                     'new_lane_preflight_a7d092d7.json'):
        (evidence / filename).write_bytes((ROOT / 'evidence' / filename).read_bytes())
    path = evidence / 'new_lane_preflight_a7d092d7.json'
    data = json.loads(path.read_text())
    data['start_new_lane'] = True
    path.write_text(json.dumps(data))
    assert witness_report_checks(tmp_path)['new_lane_preflight_stops_on_exact_witness'] is False


def test_public_proof_does_not_conflate_random_expectation_and_certainty():
    html = (ROOT / 'docs/index.html').read_text()
    assert 'halo coverage = 100% of allowed cells' in html
    assert 'halo coverage &gt; 0.70 ⇒ every map' not in html
    assert 'does not prove every map fails' in html
    card = json.loads((ROOT / 'run_card.json').read_text())
    expected = ('OK TO DOWNLOAD: YES. OK TO SUBMIT: YES.' if card.get('ok_to_submit') is True
                else 'OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.')
    assert expected in html


def test_verified_saturated_witness_blocks_new_lane():
    result = p.decision({'all_checks_passed': True, 'measured_certificate': {
        'overlap_limit': .70, 'covered_allowed_fraction': 1.0,
        'universal_overlap_blocker': True, 'witness_sha256': 'a' * 64}})
    assert result['state'] == 'impossible_under_literal_gate'
    assert result['start_new_lane'] is False and result['exit_code'] == 2
    assert '1.0 > 0.70' in result['reason']


def test_incomplete_witness_never_authorizes_experiment():
    for review in ({}, {'all_checks_passed': False, 'measured_certificate': {
        'covered_allowed_fraction': 1.0, 'overlap_limit': .7, 'universal_overlap_blocker': True}},
        {'all_checks_passed': True, 'measured_certificate': {
        'covered_allowed_fraction': .8, 'overlap_limit': .7, 'universal_overlap_blocker': False}}):
        result = p.decision(review)
        assert result['start_new_lane'] is False and result['exit_code'] == 3


def test_missing_witness_returns_negative_machine_decision(monkeypatch, capsys):
    monkeypatch.setattr(p, 'verify_witness', lambda **kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setattr('sys.argv', ['preflight_new_lane.py'])
    assert p.main() == 3
    assert '"start_new_lane": false' in capsys.readouterr().out


def test_malformed_certificate_is_unverified_not_a_crash():
    for review in (None, [], 'verified', {'measured_certificate': None},
                   {'measured_certificate': []}):
        result = p.decision(review)
        assert result['exit_code'] == 3
        assert result['start_new_lane'] is False


def test_certificate_requires_typed_measurements_and_valid_hash():
    base = {'overlap_limit': .7, 'covered_allowed_fraction': 1.0,
            'universal_overlap_blocker': True, 'witness_sha256': 'a' * 64}
    for field, value in (('covered_allowed_fraction', True),
                         ('universal_overlap_blocker', 'false'),
                         ('universal_overlap_blocker', 1),
                         ('witness_sha256', None), ('witness_sha256', 'not-a-hash'),
                         ('overlap_limit', float('nan'))):
        measured = {**base, field: value}
        result = p.decision({'all_checks_passed': True, 'measured_certificate': measured})
        assert result['exit_code'] == 3
        assert result['start_new_lane'] is False


# These are software fault-injection tests, not new scientific experiments.
def test_manifest_shape_and_restore_errors_emit_unverified_json(monkeypatch, capsys):
    import subprocess
    for error in (TypeError('private path'), AttributeError('private path'),
                  IndexError('private path'),
                  subprocess.CalledProcessError(1, ['git', 'private path'])):
        def fail(**kwargs):
            raise error
        monkeypatch.setattr(p, 'verify_witness', fail)
        monkeypatch.setattr('sys.argv', ['preflight_new_lane.py'])
        assert p.main() == 3
        result = json.loads(capsys.readouterr().out)
        assert result['state'] == 'unverified'
        assert result['start_new_lane'] is False
        assert result['error_type'] == type(error).__name__
        assert 'private path' not in json.dumps(result)


def test_inspection_failure_writes_refusal_report(monkeypatch, tmp_path, capsys):
    path = tmp_path / 'refusal.json'
    def fail(**kwargs):
        raise TypeError('bad manifest')
    monkeypatch.setattr(p, 'verify_witness', fail)
    monkeypatch.setattr('sys.argv', ['preflight_new_lane.py', '--report', str(path)])
    assert p.main() == 3
    assert json.loads(path.read_text()) == json.loads(capsys.readouterr().out)


def test_preflight_does_not_swallow_process_interrupts(monkeypatch):
    import pytest
    def interrupt(**kwargs):
        raise KeyboardInterrupt()
    monkeypatch.setattr(p, 'verify_witness', interrupt)
    monkeypatch.setattr('sys.argv', ['preflight_new_lane.py'])
    with pytest.raises(KeyboardInterrupt):
        p.main()
