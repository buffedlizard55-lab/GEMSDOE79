"""Software-only selector fixtures; not scientific measurements or receipts."""
import copy
import json

import pytest
import select_submission as selector


@pytest.fixture
def gate_fixture(monkeypatch):
    monkeypatch.setattr(selector, 'evidence_checks', lambda *_: {'measured_consistency': True})
    return {'gates': {name: True for name in selector.REQUIRED_GATES},
            'all_passed': True, 'raster_sha256': 'a' * 64}


def test_complete_consistent_evidence_can_clear_adapter(gate_fixture):
    passed, checks = selector.selection_evidence(None, {}, gate_fixture, 'a' * 64)
    assert passed and all(checks.values())


@pytest.mark.parametrize('bad', [False, 1, 'true', None])
def test_literal_boolean_required_for_every_gate(gate_fixture, bad):
    gate_fixture['gates']['exact_budget'] = bad
    assert not selector.selection_evidence(None, {}, gate_fixture, 'a' * 64)[0]


@pytest.mark.parametrize('change', ['empty', 'missing', 'extra_false', 'wrong_hash', 'aggregate_only'])
def test_summary_cannot_override_incomplete_receipt(gate_fixture, change):
    gates = copy.deepcopy(gate_fixture)
    if change == 'empty':
        gates['gates'] = {}
    elif change == 'missing':
        gates['gates'].pop('surface_uniqueness_passed')
    elif change == 'extra_false':
        gates['gates']['new_safety_gate'] = False
    elif change == 'wrong_hash':
        gates['raster_sha256'] = 'b' * 64
    else:
        gates.pop('gates')
    assert not selector.selection_evidence(None, {}, gates, 'a' * 64)[0]


def test_inconsistent_frozen_measurements_refuse_even_with_pass_receipt(monkeypatch, gate_fixture):
    monkeypatch.setattr(selector, 'evidence_checks', lambda *_: {'uniqueness_card_matches_evidence': False})
    assert not selector.selection_evidence(None, {}, gate_fixture, 'a' * 64)[0]


def test_canonical_adapter_reports_literal_overlap_blocker(tmp_path, monkeypatch):
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    (evidence / 'g79_surface_uniqueness_1108.json').write_text(json.dumps({
        'max_abs_spearman': 0.2, 'worst_dot_overlap': 1.0,
    }))
    (evidence / 'g79_dot_uniqueness_1108.json').write_text(json.dumps({
        'max_abs_spearman': 0.1, 'worst_dot_overlap': 1.0,
    }))
    canary = {
        seed: {'all_passed': True, 'max_symmetric_auc': 0.8, 'threshold': 0.9}
        for seed in ('seed20', 'seed30')
    }
    (evidence / 'g79_leakage_canary.json').write_text(json.dumps(canary))
    (evidence / 'g79_thvc_results.json').write_text('{"measured": true}')
    monkeypatch.setattr(selector, 'evidence_checks', lambda *_: {'frozen_receipts_consistent': True})
    card = {
        'raster_sha256': 'a' * 64, 'current_best_holdout_beaten': True,
        'protocol_unique': False,
    }
    checks = selector.canonical_thvc_evidence(tmp_path, card, 'a' * 64, True)
    assert checks['feature_alone_canary_le_0_90'] is True
    assert checks['surface_rank_correlation_le_0_90'] is True
    assert checks['final_rank_correlation_le_0_90'] is True
    assert checks['surface_forward_overlap_le_0_70'] is False
    assert checks['final_forward_overlap_le_0_70'] is False
    assert checks['protocol_unique'] is False


def test_canonical_adapter_fails_closed_on_missing_receipt(tmp_path):
    checks = selector.canonical_thvc_evidence(tmp_path, {}, 'a' * 64, True)
    assert checks['canonical_evidence_read_error'] is False


@pytest.mark.parametrize('error', [FileNotFoundError, ValueError, KeyError, TypeError, IndexError])
def test_missing_or_malformed_measurements_fail_closed(monkeypatch, gate_fixture, error):
    def broken(*_):
        raise error('software fixture')
    monkeypatch.setattr(selector, 'evidence_checks', broken)
    passed, checks = selector.selection_evidence(None, {}, gate_fixture, 'a' * 64)
    assert not passed and checks == {'evidence_read_error': error.__name__}


@pytest.mark.parametrize('payload', ['{', 'null', '[]', '{}'])
def test_cli_malformed_card_refuses_without_writing(tmp_path, monkeypatch, capsys, payload):
    import json
    monkeypatch.setattr(selector, 'ROOT', tmp_path)
    card = tmp_path / 'run_card.json'
    card.write_text(payload)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert selector.main() == 2
    refusal = json.loads(capsys.readouterr().out)
    assert refusal['selected'] is False
    assert refusal['ok_to_submit'] is False
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert after == before


def test_cli_missing_inputs_refuses_without_traceback(tmp_path, monkeypatch, capsys):
    import json
    monkeypatch.setattr(selector, 'ROOT', tmp_path)
    assert selector.main() == 2
    assert json.loads(capsys.readouterr().out)['error_type'] == 'FileNotFoundError'
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('payload', ['{', 'null', '[]', '{}', '{"gates": null}'])
def test_cli_bad_gate_receipt_never_promotes(tmp_path, monkeypatch, capsys, payload):
    import json
    monkeypatch.setattr(selector, 'ROOT', tmp_path)
    (tmp_path / 'raster.tif').write_bytes(b'software fixture, not a raster')
    card = {'submission_file': 'raster.tif', 'verdict': 'promote'}
    (tmp_path / 'run_card.json').write_text(json.dumps(card))
    folder = tmp_path / 'evidence/nhr'
    folder.mkdir(parents=True)
    (folder / 'x1_gates.json').write_text(payload)
    monkeypatch.setattr(selector, 'validate_path', lambda *_: {'format_passed': True})
    monkeypatch.setattr(selector, 'submission_decision', lambda *_, **__: {'blockers': []})
    monkeypatch.setattr(selector, 'evidence_checks', lambda *_: {'measured': True})
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert selector.main() == 2
    assert json.loads(capsys.readouterr().out)['selected'] is False
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
