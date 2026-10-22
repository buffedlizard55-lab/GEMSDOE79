"""Software-only selector fixtures; not scientific measurements or receipts."""
import copy

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


@pytest.mark.parametrize('error', [FileNotFoundError, ValueError, KeyError, TypeError, IndexError])
def test_missing_or_malformed_measurements_fail_closed(monkeypatch, gate_fixture, error):
    def broken(*_):
        raise error('software fixture')
    monkeypatch.setattr(selector, 'evidence_checks', broken)
    passed, checks = selector.selection_evidence(None, {}, gate_fixture, 'a' * 64)
    assert not passed and checks == {'evidence_read_error': error.__name__}
