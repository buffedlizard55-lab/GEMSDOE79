"""Software/integrity checks, never geological validation experiments."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import requests
from check_site import check_site
import refresh_feed
import restore_data
from restore_registry import restore_blob
from gems79.novelty import shared_inventory
from gems79.status import submission_decision

ROOT = Path(__file__).resolve().parents[1]


def test_all_site_links_and_status_are_consistent():
    assert check_site()['passed']


def test_readme_project_links_exist_and_original_brief_is_present():
    import markdown
    from bs4 import BeautifulSoup
    from urllib.parse import urlsplit
    text = (ROOT / 'README.md').read_text()
    assert 'PARALLEL-RUN PROTOCOL' in text and 'Pass 3:' in text
    assert 'Predicted values must be in range [0, 1]' in text
    soup = BeautifulSoup(markdown.markdown(text), 'html.parser')
    for link in soup.find_all('a', href=True):
        href = urlsplit(link['href'])
        if not href.scheme and href.path:
            assert (ROOT / href.path).exists(), link['href']


def test_parser_accepts_only_unambiguous_public_first_place():
    page = '<table><tr><th>Rank</th><th>Participant</th><th>Public DW-Tversky</th></tr><tr><td>1</td><td>example</td><td>0.1234</td></tr></table>'
    got = refresh_feed.parse_leaderboard(page)
    assert got['public_dti'] == .1234 and 'NOT A SUBMISSION RECEIPT' in got['score_class']
    for bad in (page + page, '<p>Our top score 0.9999</p>', page.replace('Public DW-Tversky', 'Private DW-Tversky'), page.replace('<td>0.1234</td>', '<td>0.1234</td><td>0.5678</td>')):
        with pytest.raises(ValueError):
            refresh_feed.parse_leaderboard(bad)


def test_probe_network_failure_is_not_verified(monkeypatch):
    def fail(*a, **k):
        raise requests.exceptions.SSLError('No sandbox egress')
    monkeypatch.setattr(refresh_feed.requests, 'get', fail)
    result = refresh_feed.probe({'id': 'DD-PROBLEM', 'url': 'https://www.drivendata.org/'})
    assert result['state'] == 'fetch_failed' and 'http_status' not in result and 'leaderboard' not in result


def test_probe_login_redirect_is_not_receipt(monkeypatch):
    monkeypatch.setattr(refresh_feed.requests, 'get', lambda *a, **k: SimpleNamespace(status_code=200, url='https://www.drivendata.org/accounts/login/', ok=True))
    got = refresh_feed.probe({'id': 'DD-AUTH', 'url': 'https://www.drivendata.org/submissions/'})
    assert got['state'] == 'authentication_required'


def test_failed_feed_preserves_old_observation_date(tmp_path, monkeypatch):
    (tmp_path / 'knowledge').mkdir(); (tmp_path / 'docs/evidence').mkdir(parents=True)
    ledger = json.loads((ROOT / 'knowledge/official_sources.json').read_text())
    (tmp_path / 'knowledge/official_sources.json').write_text(json.dumps(ledger))
    path = tmp_path / 'docs/evidence/source_health.json'
    old = {'public_dti': .1234, 'observed_utc': '2026-01-01T00:00:00Z'}
    path.write_text(json.dumps({'leaderboard_observation': old}))
    monkeypatch.setattr(refresh_feed, 'ROOT', tmp_path)
    monkeypatch.setattr(refresh_feed, 'probe', lambda row: {'id': row['id'], 'state': 'fetch_failed'})
    refresh_feed.main()
    result = json.loads(path.read_text())
    assert result['leaderboard_observation'] == old
    assert result['scientific_claims_reviewed_date'] == '2026-10-21'
    assert result['submission_slots_used_by_this_refresh'] == 0


def test_restore_present_input_never_needs_network(tmp_path, monkeypatch):
    data = b'fixture bytes'; (tmp_path / 'tiny.tif').write_bytes(data)
    def no_network(*a, **k):
        pytest.fail('Present pinned input must not fetch')
    monkeypatch.setattr(restore_data, 'fetch', no_network)
    result = restore_data.restore_entry({'id': 'fixture', 'dest': 'tiny.tif', 'sha256': hashlib.sha256(data).hexdigest()}, tmp_path)
    assert result['status'] == 'present'


def test_frozen_registry_verifies_all_three_byte_pins(tmp_path):
    data = b'software-only registry storage fixture'
    blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
    directory = tmp_path / '.cache/registry'; directory.mkdir(parents=True)
    (directory / (blob + '.tif')).write_bytes(data)
    row = {'repo': 'fixture', 'blob': blob, 'size': len(data)}
    pin = {'sha256': hashlib.sha256(data).hexdigest()}
    assert restore_blob(tmp_path, row, pin)['verified']
    with pytest.raises(ValueError): restore_blob(tmp_path, {**row, 'size': 999}, pin)
    with pytest.raises(ValueError): restore_blob(tmp_path, row, {'sha256': 'bad'})


def test_shared_inventory_only_complete_for_full_verified_scope():
    index = {'repositories': [{'repo': 'fixture', 'status': 'ok'}], 'rasters': [{}]}
    receipt = {'verified': 1, 'unavailable': 0}
    records = [{'repo': 'fixture', 'submission': 'fixture:one.tif', 'file': 'one.tif', 'sha256': 'abc'}]
    assert shared_inventory(index, receipt, records)['complete_accessible_scan']
    assert not shared_inventory(index, receipt, records, early_rejection=True)['complete_accessible_scan']
    assert not shared_inventory(index, receipt, [])['complete_accessible_scan']
    assert not shared_inventory(index, {'verified': 0, 'unavailable': 1}, records)['complete_accessible_scan']


def test_finished_scientific_state_cannot_be_restarted():
    import run_experiment
    with pytest.raises(FileExistsError): run_experiment.main()


@pytest.mark.parametrize('bad', [True, float('nan'), float('inf'), -.1, 1.1, '0.5'])
def test_malformed_holdout_never_passes_status(bad):
    card = json.loads((ROOT / 'run_card.json').read_text())
    card['holdout_dti'] = {'dti': bad, 'ci95': [0, 1], 'withheld_positive_pixels': 100, 'evaluator_version': 'gems57-pooled-hide-v2'}
    got = submission_decision(card, actual_sha256=card['raster_sha256'], format_passed=True)
    assert 'holdout_dti_and_ci_not_measured' in got['blockers'] and not got['ok_to_submit']


def test_truthy_strings_and_booleans_do_not_fake_evidence():
    card = json.loads((ROOT / 'run_card.json').read_text())
    card.update(protocol_unique='true', current_best_holdout_beaten='true', capacity_verified_from_submission_page='yes', remaining_weekly_slots=True,
                selector_receipt='not a receipt', organizer_submission_receipt='present but unauthenticated')
    card['holdout_dti'] = {'dti': .5, 'ci95': [False, True], 'withheld_positive_pixels': True, 'evaluator_version': 'anything'}
    got = submission_decision(card, actual_sha256=card['raster_sha256'], format_passed=True)
    assert not got['ok_to_submit'] and not got['organizer_acceptance_established']
    assert 'current_account_weekly_capacity_not_verified' in got['blockers']
