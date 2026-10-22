"""Software fixtures only, not scientific validation or competition scores."""
import pytest
from review_readiness import inspect_safely, summarize


def test_unavailable_is_not_fabricated_measurement():
    def missing():
        raise FileNotFoundError('unavailable')
    check = inspect_safely(missing)
    assert check == {'completed': False, 'error_type': 'FileNotFoundError'}
    result = summarize({'runtime_inputs': check})
    assert result['ok_to_submit'] is False
    assert 'runtime_inputs_unverified' in result['blockers']


def test_even_all_inspections_cannot_select_submission():
    checks = {name: {'completed': True, 'result': value} for name, value in {
        'runtime_inputs': {'all_manifest_inputs_ready': True},
        'novelty_preflight': {'start_new_lane': True},
        'local_format': {'format_passed': True},
        'portal_text_format': {'ok': True},
    }.items()}
    result = summarize(checks)
    assert result['blockers'] == ['review_is_not_selector_approval']
    assert result['ok_to_submit'] is False
    assert result['start_new_lane'] is False


def test_local_pass_does_not_hide_portal_text_failure():
    result = summarize({
        'local_format': {'completed': True, 'result': {'format_passed': True}},
        'portal_text_format': {'completed': True, 'result': {'ok': False}},
    })
    assert 'portal_text_format_not_passed' in result['blockers']
    assert 'local_format_not_passed' not in result['blockers']


def test_interrupts_are_not_swallowed():
    def interrupted():
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        inspect_safely(interrupted)
