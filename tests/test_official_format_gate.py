"""Readiness/selector/publication regressions; all positive fixtures are synthetic.

No fixture is a real geological result or competition approval.
"""
from copy import deepcopy
import json
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from gems79.portal_spec import RULES, VALIDATOR_VERSION, PINNED_TEMPLATE_SHA256, validate_portal_file
from gems79.status import submission_decision
import select_submission as selector
import submission_status

ROOT = Path(__file__).resolve().parents[1]
SHA = 'a' * 64


@pytest.fixture
def software_evidence():
    card = {
        'raster_sha256': SHA, 'protocol_unique': True,
        'leakage_canary': {'passed': True, 'auc': 0.6, 'features_cleared': 2,
                           'required_threshold': 0.90},
        'current_best_holdout_beaten': True,
        'holdout_dti': {'dti': 0.5, 'ci95': [0.4, 0.6], 'withheld_positive_pixels': 10,
                        'evaluator_version': 'gems57-pooled-hide-v2'},
        'source_provenance_verified': True, 'verdict': 'promote',
        'approved_for_weekly_slot': True, 'ok_to_submit': True,
        'selector_receipt': {'raster_sha256': SHA, 'selector': 'scripts/select_submission.py',
                             'all_automated_gates_passed': True,
                             'source_url': 'SOFTWARE FIXTURE ONLY', 'observed_utc': 'SOFTWARE FIXTURE ONLY'},
    }
    report = {
        'validator_version': VALIDATOR_VERSION, 'ok': True, 'failed_rules': [],
        'sha256': SHA, 'template_sha256': PINNED_TEMPLATE_SHA256,
        'bytes_stable_during_validation': True,
        'rules': [{'rule': key, 'pass': True} for key in RULES],
    }
    return card, report


def test_historical_format_pass_alone_never_clears_submission(software_evidence):
    card, _ = software_evidence
    result = submission_decision(card, actual_sha256=SHA, format_passed=True)
    assert result['ok_to_download'] is True
    assert result['ok_to_submit'] is False
    assert result['official_text_format_passed'] is False
    assert result['blockers'] == ['official_format_rules_not_cleared']


def test_bound_complete_official_report_can_clear_only_its_format_gate(software_evidence):
    card, report = software_evidence
    result = submission_decision(card, actual_sha256=SHA, format_passed=True,
                                 official_format_report=report)
    assert result['ok_to_submit'] is True  # synthetic fixture, NOT a real candidate
    assert result['official_text_format_passed'] is True
    assert result['organizer_acceptance_established'] is False
    assert result['account_side_conditions']
    card['protocol_unique'] = False
    result = submission_decision(card, actual_sha256=SHA, format_passed=True,
                                 official_format_report=report)
    assert result['ok_to_submit'] is False and 'literal_novelty_not_cleared' in result['blockers']


def test_valid_nan_exterior_is_not_blocked_by_legacy_all_finite_policy(software_evidence):
    card, report = software_evidence
    result = submission_decision(card, actual_sha256=SHA, format_passed=False,
                                 official_format_report=report)
    assert result['ok_to_download'] is True
    assert result['local_research_format_passed'] is False
    assert result['official_text_format_passed'] is True
    assert 'format_validation_failed' not in result['blockers']


@pytest.mark.parametrize('change', ['failed_r6', 'wrong_hash', 'wrong_template', 'duplicate',
                                   'partial', 'truthy_ok', 'truthy_rule', 'inspection_error', 'legacy_error'])
def test_forged_or_stale_official_format_cannot_promote(software_evidence, change):
    card, original = software_evidence
    report = deepcopy(original)
    if change == 'failed_r6':
        report['rules'][5]['pass'] = False  # deliberately leave the aggregate optimistic
    elif change == 'wrong_hash':
        report['sha256'] = 'b' * 64
    elif change == 'wrong_template':
        report['template_sha256'] = 'c' * 64
    elif change == 'duplicate':
        report['rules'][0] = deepcopy(report['rules'][1])
    elif change == 'partial':
        report['rules'].pop()
    elif change == 'truthy_ok':
        report['ok'] = 1
    elif change == 'truthy_rule':
        report['rules'][0]['pass'] = 'true'
    elif change == 'inspection_error':
        report['inspection_error'] = {'type': 'ValueError'}
    else:
        report['error'] = {'type': 'ValueError'}
    result = submission_decision(card, actual_sha256=SHA, format_passed=True,
                                 official_format_report=report)
    assert result['ok_to_submit'] is False
    assert result['official_text_format_passed'] is False
    assert 'official_format_rules_not_cleared' in result['blockers']


def test_current_cli_rederives_r6_failure_instead_of_using_card_format_flag():
    result = submission_status.inspect_current(ROOT)
    assert result['ok_to_download'] is True and result['ok_to_submit'] is False
    assert result['local_research_format_passed'] is True
    assert result['official_text_format_passed'] is False
    assert result['official_format_validation']['failed_rules'] == ['R6']
    assert 'official_format_rules_not_cleared' in result['blockers']
    assert result['human_inspection_required_for_this_decision'] is False


def test_selector_refusal_reports_r6_and_preserves_card(capsys):
    before = (ROOT / 'run_card.json').read_bytes()
    assert selector.main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report['selected'] is False
    assert 'official_text_format_passed' in report['failed_gates']
    assert report['official_format_validation']['failed_rules'] == ['R6']
    assert report['card_left_unchanged'] is True
    assert (ROOT / 'run_card.json').read_bytes() == before


@pytest.mark.parametrize('relative', ['../escape.tif', '/tmp/escape.tif'])
def test_selector_rejects_outside_artifact_before_validation(tmp_path, monkeypatch, capsys, relative):
    monkeypatch.setattr(selector, 'ROOT', tmp_path)
    (tmp_path / 'run_card.json').write_text(json.dumps({'submission_file': relative}))
    assert selector.main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report['ok_to_submit'] is False
    assert report['error_type'] == 'ValueError'


@pytest.mark.parametrize('raw', ['{"submission_file":"a","submission_file":"b"}',
                                  '{"some_number":NaN}'])
def test_selector_rejects_ambiguous_json_before_inspection(tmp_path, monkeypatch, capsys, raw):
    monkeypatch.setattr(selector, 'ROOT', tmp_path)
    (tmp_path / 'run_card.json').write_text(raw)
    assert selector.main() == 2
    assert json.loads(capsys.readouterr().out)['ok_to_submit'] is False


def test_public_pages_and_status_expose_live_official_format_not_just_range_pass():
    card = json.loads((ROOT / 'run_card.json').read_text())
    expected = validate_portal_file(ROOT / card['submission_file'])
    public = json.loads((ROOT / 'docs/evidence/official_format_validation.json').read_text())
    assert public == expected
    status = json.loads((ROOT / 'docs/status.json').read_text())
    assert status['official_text_format_passed'] is False
    assert 'official_format_rules_not_cleared' in status['blockers']
    for name in ('index.html', 'executive-summary.html'):
        soup = BeautifulSoup((ROOT / 'docs' / name).read_text(), 'html.parser')
        row = soup.find(attrs={'data-gate': 'Official submission format (R1–R8)'})
        assert row and row['data-passed'] == 'false'
        assert 'R6' in row.get_text()
        assert 'OK TO SUBMIT: NO.' in soup.get_text(' ', strip=True)


def test_legacy_portal_boolean_is_only_a_veto_never_a_replacement(software_evidence):
    card, report = software_evidence
    missing = submission_decision(card, actual_sha256=SHA, format_passed=True,
                                  portal_passed=True)
    assert missing['ok_to_submit'] is False
    assert 'official_format_rules_not_cleared' in missing['blockers']
    vetoed = submission_decision(card, actual_sha256=SHA, format_passed=True,
                                 official_format_report=report, portal_passed=False)
    assert vetoed['ok_to_submit'] is False
    complete = submission_decision(card, actual_sha256=SHA, format_passed=True,
                                   official_format_report=report, portal_passed=True)
    assert complete['ok_to_submit'] is True  # synthetic software fixture only


def test_banner_ignores_card_injected_report_and_does_not_cache_a_path(monkeypatch, software_evidence):
    import build_site
    card, passed = software_evidence
    card['submission_file'] = 'SOFTWARE-FIXTURE.tif'
    card['_official_format_validation'] = deepcopy(passed)
    failed = deepcopy(passed)
    failed['ok'] = False
    failed['failed_rules'] = ['R6']
    failed['rules'][5]['pass'] = False
    responses = iter((passed, failed))
    monkeypatch.setattr(build_site, 'validate_portal_file', lambda path: next(responses))
    assert 'OFFICIAL FORMAT: PASS' in build_site.portal_status_panel(card)
    assert 'OFFICIAL FORMAT: FAIL (R6)' in build_site.portal_status_panel(card)


def test_preserved_tipstep_page_is_reachable_and_does_not_repeat_portal_guarantee():
    soup = BeautifulSoup((ROOT / 'docs/tipstep-submission.html').read_text(), 'html.parser')
    text = soup.get_text(' ', strip=True)
    assert 'Historical research artifact' in text
    assert 'OK TO SUBMIT: NO.' in text
    assert 'unsupported' in text and 'R6' in text
    actual = json.loads((ROOT / 'docs/evidence/tipstep_official_format.json').read_text())
    card = json.loads((ROOT / 'run_card_tipstep.json').read_text())
    assert actual['sha256'] == card['raster']['sha256']
    assert actual['failed_rules'] == ['R6']
    home = BeautifulSoup((ROOT / 'docs/index.html').read_text(), 'html.parser')
    assert home.find('a', href='tipstep-submission.html')
