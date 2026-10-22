"""CLI failure contracts. Byte fixtures here are not competition predictions."""
import json
import sys
import zipfile

import pytest
import validate_submission as cli


def invoke(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, 'argv', ['validate_submission.py', *map(str, args)])
    code = cli.main()
    return code, json.loads(capsys.readouterr().out)


@pytest.mark.parametrize('kind', ['missing.tif', 'corrupt.tif', 'corrupt.zip'])
def test_unreadable_input_is_json_rejection(tmp_path, monkeypatch, capsys, kind):
    path = tmp_path / kind
    if not kind.startswith('missing'):
        path.write_bytes(b'not a raster or archive')
    report = tmp_path / 'evidence' / 'reject.json'
    code, result = invoke(monkeypatch, capsys, path, '--report', report)
    assert code == 1
    assert result['format_passed'] is False
    assert result['does_not_approve_submission'] is True
    assert result['inspection_error']['stage'] == 'inspect_artifact'
    assert json.loads(report.read_text()) == result
    assert str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize('members', [[], ['a.tif', 'b.tif'], ['nested/a.tif'],
                                    ['../a.tif'], ['nested\\a.tif'], ['/a.tif'],
                                    ['C:\\a.tif'], ['readme.txt']])
def test_invalid_zip_layout_rejected_before_raster_read(tmp_path, monkeypatch, capsys, members):
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as out:
        for name in members:
            out.writestr(name, b'fixture')
    def unexpected(_):
        pytest.fail('Invalid ZIP must not reach raster validator')
    monkeypatch.setattr(cli, 'validate_path', unexpected)
    code, result = invoke(monkeypatch, capsys, archive)
    assert code == 1
    assert result['inspection_error']['type'] == 'ValueError'


def test_report_collision_never_prints_pass_or_overwrites(tmp_path, monkeypatch, capsys):
    # Mocked software PASS, not a measured format or science result.
    monkeypatch.setattr(cli, 'validate_path', lambda _: {'format_passed': True})
    report = tmp_path / 'existing.json'
    report.write_text('immutable evidence')
    code, result = invoke(monkeypatch, capsys, 'unused.tif', '--report', report)
    assert code == 1
    assert result['format_passed'] is False
    assert result['inspection_error'] == {'stage': 'write_report', 'type': 'FileExistsError'}
    assert report.read_text() == 'immutable evidence'


def test_zip_single_tiff_and_report_success(tmp_path, monkeypatch, capsys):
    archive = tmp_path / 'valid-layout.zip'
    with zipfile.ZipFile(archive, 'w') as out:
        out.writestr('candidate.TIF', b'fixture')
    def inspect(path):
        assert path.read_bytes() == b'fixture'
        return {'format_passed': True, 'does_not_approve_submission': True}
    monkeypatch.setattr(cli, 'validate_path', inspect)
    code, result = invoke(monkeypatch, capsys, archive)
    assert code == 0
    assert result['does_not_approve_submission'] is True


def test_exception_details_are_not_published(monkeypatch, capsys):
    def fail(_):
        raise RuntimeError('private filesystem and credentials')
    monkeypatch.setattr(cli, 'validate_path', fail)
    code, result = invoke(monkeypatch, capsys, 'unused.tif')
    assert code == 1
    assert 'private' not in json.dumps(result)


def test_missing_default_card_is_json_rejection(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    code, result = invoke(monkeypatch, capsys)
    assert code == 1
    assert result['inspection_error'] == {'stage': 'resolve_artifact', 'type': 'FileNotFoundError'}


def test_rejection_report_collision_keeps_original(tmp_path, monkeypatch, capsys):
    report = tmp_path / 'original.json'
    report.write_text('original evidence')
    code, result = invoke(monkeypatch, capsys, tmp_path / 'absent.zip', '--report', report)
    assert code == 1
    assert result['format_passed'] is False
    assert result['report_error']['type'] == 'FileExistsError'
    assert report.read_text() == 'original evidence'


def test_report_parent_is_file_returns_json_refusal(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, 'validate_path', lambda _: {'format_passed': True})
    parent = tmp_path / 'not-a-directory'
    parent.write_text('bytes')
    code, result = invoke(monkeypatch, capsys, 'unused.tif', '--report', parent / 'report.json')
    assert code == 1
    assert result['inspection_error']['stage'] == 'write_report'
    assert result['format_passed'] is False
