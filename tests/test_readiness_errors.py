"""Software rejection fixtures; no geological score is produced by these tests."""
import hashlib
import json
from pathlib import Path
import pytest
import submission_status as cli
from gems79.status import submission_decision

ROOT = Path(__file__).resolve().parents[1]


def assert_blocked(result):
    assert result['ok_to_download'] is False
    assert result['ok_to_submit'] is False
    assert result['verdict'] == 'negative'
    assert result['organizer_acceptance_established'] is False
    assert result['human_inspection_required_for_this_decision'] is False
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('payload', ['[]', 'null', 'true', '42', '"text"', '{',
                                      '{"x":NaN}', '{"x":Infinity}',
                                      '{"ok_to_submit":false,"ok_to_submit":true}'])
def test_unreadable_card_returns_json_rejection(tmp_path, payload):
    (tmp_path / 'run_card.json').write_text(payload)
    result = cli.inspect_current(tmp_path)
    assert_blocked(result)
    assert result['inspection_error']['stage'] == 'read_run_card'


def test_missing_card_returns_json_rejection(tmp_path):
    result = cli.inspect_current(tmp_path)
    assert_blocked(result)
    assert result['inspection_error'] == {'stage': 'read_run_card', 'type': 'FileNotFoundError'}


@pytest.mark.parametrize('path', [None, '', 1, '../outside.tif', '/tmp/outside.tif'])
def test_artifact_path_must_remain_inside_repository(tmp_path, path):
    (tmp_path / 'run_card.json').write_text(json.dumps({'submission_file': path}))
    result = cli.inspect_current(tmp_path)
    assert_blocked(result)
    assert result['inspection_error']['stage'] == 'resolve_artifact'


def test_symlink_cannot_escape_repository(tmp_path):
    (tmp_path / 'escape.tif').symlink_to(tmp_path.parent / 'outside.tif')
    (tmp_path / 'run_card.json').write_text('{"submission_file":"escape.tif"}')
    result = cli.inspect_current(tmp_path)
    assert_blocked(result)
    assert result['inspection_error']['stage'] == 'resolve_artifact'


def test_missing_artifact_returns_json_rejection(tmp_path):
    (tmp_path / 'run_card.json').write_text('{"submission_file":"missing.tif"}')
    result = cli.inspect_current(tmp_path)
    assert_blocked(result)
    assert result['inspection_error']['stage'] == 'read_artifact'


def test_corrupt_artifact_returns_json_rejection(tmp_path):
    (tmp_path / 'run_card.json').write_text('{"submission_file":"broken.tif"}')
    (tmp_path / 'broken.tif').write_bytes(b'not a GeoTIFF')
    result = cli.inspect_current(tmp_path)
    assert_blocked(result)
    assert result['inspection_error']['stage'] == 'validate_artifact'


def test_readiness_requires_all_validators_to_inspect_the_snapshotted_bytes(tmp_path, monkeypatch):
    artifact = tmp_path / 'raster.tif'
    artifact.write_bytes(b'byte-identity fixture')
    actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (tmp_path / 'run_card.json').write_text(json.dumps({
        'submission_file': 'raster.tif', 'raster_sha256': actual,
    }))
    monkeypatch.setattr(cli, 'validate_path', lambda _: {
        'format_passed': True, 'official_format_passed': True,
        'validated_sha256': 'b' * 64,
        'official_format_report': {'sha256': 'b' * 64, 'ok': True, 'failed_rules': []},
    })
    result = cli.inspect_current(tmp_path)
    assert result['validation_sha256_matches_snapshot'] is False
    assert result['ok_to_download'] is False
    assert result['ok_to_submit'] is False


def test_validation_error_does_not_leak_details(tmp_path, monkeypatch):
    (tmp_path / 'run_card.json').write_text('{"submission_file":"broken.tif"}')
    (tmp_path / 'broken.tif').write_bytes(b'bytes')
    def fail(_):
        raise RuntimeError('sensitive filesystem details')
    monkeypatch.setattr(cli, 'validate_path', fail)
    result = cli.inspect_current(tmp_path)
    assert_blocked(result)
    assert result['inspection_error']['type'] == 'RuntimeError'
    assert 'sensitive' not in json.dumps(result)


@pytest.mark.parametrize('value', [None, [], 'text', 0, True])
def test_nonobject_card_never_raises(value):
    result = submission_decision(value, actual_sha256=None, format_passed=False)
    assert_blocked(result)
    assert 'run_card_is_not_an_object' in result['blockers']


def test_nonhex_hash_cannot_clear_integrity_gate():
    result = submission_decision({'raster_sha256': 'z' * 64},
                                 actual_sha256='z' * 64, format_passed=True)
    assert_blocked(result)
    assert 'raster_bytes_do_not_match_run_card' in result['blockers']


def test_oversized_holdout_integer_returns_rejection_not_overflow():
    card = json.loads((ROOT / 'run_card.json').read_text())
    card['holdout_dti'] = {'dti': 10**1000, 'ci95': [0, 1],
                           'withheld_positive_pixels': 1,
                           'evaluator_version': 'gems57-pooled-hide-v2'}
    result = submission_decision(card, actual_sha256=card['raster_sha256'], format_passed=True)
    assert not result['ok_to_submit']
    assert 'holdout_dti_and_ci_not_measured' in result['blockers']


def test_cli_exit_contract(monkeypatch, capsys):
    decision = cli.inspect_current(ROOT)
    monkeypatch.setattr(cli, 'inspect_current', lambda: decision)
    assert cli.main() == (0 if decision['ok_to_submit'] else 2)
    assert json.loads(capsys.readouterr().out) == decision


@pytest.mark.parametrize('auc', [None, True, '0.6', -1, 0.49, 0.90001, 1,
                                  float('nan'), float('inf'), 10**1000])
def test_canary_boolean_pass_cannot_override_bad_measurement(auc):
    card = {'leakage_canary': {'passed': True, 'auc': auc,
                             'features_cleared': 9, 'required_threshold': 0.90}}
    result = submission_decision(card, actual_sha256=None, format_passed=False)
    assert 'feature_alone_canaries_not_cleared' in result['blockers']


@pytest.mark.parametrize('field,value', [
    ('features_cleared', 0), ('features_cleared', True),
    ('features_cleared', '9'), ('required_threshold', 1),
    ('required_threshold', None), ('required_threshold', '0.9'),
    ('passed', False),
])
def test_canary_requires_numeric_contract(field, value):
    canary = {'passed': True, 'auc': 0.6, 'features_cleared': 9,
              'required_threshold': 0.90}
    canary[field] = value
    result = submission_decision({'leakage_canary': canary},
                                 actual_sha256=None, format_passed=False)
    assert 'feature_alone_canaries_not_cleared' in result['blockers']


@pytest.mark.parametrize('auc', [0.5, 0.6, 0.90])
def test_canary_boundary_clears_only_canary_gate(auc):
    # Software fixture, not a measured geological AUC or promotion receipt.
    card = {'leakage_canary': {'passed': True, 'auc': auc,
                             'features_cleared': 9, 'required_threshold': 0.90}}
    result = submission_decision(card, actual_sha256=None, format_passed=False)
    assert 'feature_alone_canaries_not_cleared' not in result['blockers']
    assert not result['ok_to_submit']
