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


def test_failed_feed_uses_newer_dated_reviewed_leaderboard(tmp_path, monkeypatch):
    (tmp_path / 'knowledge').mkdir(); (tmp_path / 'docs/evidence').mkdir(parents=True)
    ledger = json.loads((ROOT / 'knowledge/official_sources.json').read_text())
    (tmp_path / 'knowledge/official_sources.json').write_text(json.dumps(ledger))
    path = tmp_path / 'docs/evidence/source_health.json'
    old = {'public_dti': .1234, 'observed_date': '2026-01-01', 'method': 'older review'}
    path.write_text(json.dumps({'leaderboard_observation': old}))
    monkeypatch.setattr(refresh_feed, 'ROOT', tmp_path)
    monkeypatch.setattr(refresh_feed, 'probe', lambda row: {'id': row['id'], 'state': 'fetch_failed'})
    refresh_feed.main()
    result = json.loads(path.read_text())
    assert result['leaderboard_observation']['public_dti'] == .4413
    assert result['leaderboard_observation']['observed_date'] == '2026-10-22'
    assert result['leaderboard_observation']['rank_22_public_dti'] == .3183
    assert result['scientific_claims_reviewed_date'] == '2026-10-22'
    assert result['submission_slots_used_by_this_refresh'] == 0


def test_failed_feed_keeps_a_newer_prior_snapshot_than_an_older_ledger():
    prior = {'public_dti': .5678, 'observed_utc': '2026-10-21T23:59:00Z', 'method': 'newer reviewed snapshot'}
    ledger = {'public_dti': .4413, 'observed_date': '2026-10-20', 'method': 'ledger'}
    assert refresh_feed.newest_leaderboard_observation(('ledger', ledger), ('prior', prior)) == prior


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
    card = json.loads((ROOT / 'evidence/e1/run_card_e1.json').read_text())
    card.update(protocol_unique='true', current_best_holdout_beaten='true', capacity_verified_from_submission_page='yes', remaining_weekly_slots=True,
                selector_receipt='not a receipt', organizer_submission_receipt='present but unauthenticated')
    card['holdout_dti'] = {'dti': .5, 'ci95': [False, True], 'withheld_positive_pixels': True, 'evaluator_version': 'anything'}
    got = submission_decision(card, actual_sha256=card['raster_sha256'], format_passed=True)
    assert not got['ok_to_submit'] and not got['organizer_acceptance_established']
    assert 'separate_selector_receipt_missing_or_unbound' in got['blockers']
    assert 'holdout_dti_and_ci_not_measured' in got['blockers']


@pytest.mark.parametrize('archive_rel', ['archive/h79_mct_c26efec', 'archive/h79_cspt_3d386a3'])
def test_incoming_concurrent_archives_preserve_provenance_without_executable_fork(archive_rel):
    archive = ROOT / archive_rel
    manifest = json.loads((archive / 'manifest.json').read_text())
    for row in manifest['files']:
        if row.get('archive_path'):
            expected_sha = row.get('archived_sha256') or row['source_sha256']
            assert hashlib.sha256((ROOT / row['archive_path']).read_bytes()).hexdigest() == expected_sha
    assert not list(archive.rglob('*.py')) and not list(archive.rglob('*.html'))
    assert not list(archive.rglob('vendor/gems57/uniqueness.py'))
    assert 'DO NOT SUBMIT' in (archive / 'README.md').read_text()


def test_concurrent_lanes_audit_verifies_literal_duplicate_and_negative_readiness():
    audit_path = ROOT / 'evidence/concurrent_lanes_audit.json'
    site_audit_path = ROOT / 'docs/evidence/concurrent_lanes_audit.json'
    assert audit_path.exists() and site_audit_path.exists()
    assert audit_path.read_bytes() == site_audit_path.read_bytes()
    audit = json.loads(audit_path.read_text())
    for lane_id in ('H79-MCT', 'H79-CSPT'):
        lane = audit['archived_lanes'][lane_id]
        assert lane['manifest_verification']['no_executable_py_or_html'] is True
        assert lane['manifest_verification']['no_private_uniqueness_fork'] is True
        assert lane['canonical_literal_uniqueness']['worst_forward_overlap_3px'] == 1.0
        assert lane['canonical_readiness_decision']['ok_to_submit'] is False
        assert lane['canonical_readiness_decision']['verdict'] == 'negative'


def test_stale_concurrent_status_cannot_promote_or_add_active_tiffs():
    card = json.loads((ROOT / 'run_card.json').read_text())
    card_b = json.loads((ROOT / 'run_card_g79b.json').read_text())
    status = json.loads((ROOT / 'docs/status.json').read_text())
    assert status['ok_to_submit'] is card['ok_to_submit'] and status['sha256'] == card['raster_sha256']
    assert [p.name for p in (ROOT / 'docs/downloads').glob('*.tif')] == [Path(card['submission_file']).name]
    # Concurrent lane G79B-SDPT stays quarantined in archive/, never published.
    archived = ROOT / 'archive/g79b_sdpt_67557396/downloads' / (card_b['submission_name'] + '.tif')
    assert archived.is_file() and 'DO-NOT-SUBMIT' in archived.name
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == card_b['raster_sha256']
    assert card_b['verdict'] == 'negative' and card_b['ok_to_submit'] is False
    assert not hasattr(__import__('gems57.uniqueness', fromlist=['uniqueness']), 'binding_duplicate_decision')


def test_workflow_feed_output_is_line_terminated(tmp_path):
    import os
    import shlex
    import subprocess
    import sys
    command = next(line.strip() for line in (ROOT / '.github/workflows/site.yml').read_text().splitlines() if 'GITHUB_OUTPUT' in line)
    args = shlex.split(command)
    output = tmp_path / 'github-output'
    subprocess.run([sys.executable, *args[1:]], cwd=ROOT,
                   env={**os.environ, 'GITHUB_OUTPUT': str(output)}, check=True)
    date = json.loads((ROOT / 'docs/evidence/source_health.json').read_text())['attempted_utc']
    assert output.read_bytes() == ('attempted_utc=' + date + '\n').encode()


def test_publication_retry_retains_expected_feed(monkeypatch):
    import verify_public_site as public
    calls = []
    def verify(url, expected):
        calls.append((url, expected))
        if len(calls) == 1:
            raise ValueError('old CDN snapshot')
        return {'passed': True}
    monkeypatch.setattr(public, 'verify', verify)
    monkeypatch.setattr(public.time, 'sleep', lambda _: None)
    assert public.verify_with_retries('https://example.invalid/', 'exact-time', 2, 0)['passed']
    assert calls == [('https://example.invalid/', 'exact-time')] * 2


def test_publication_retry_fails_closed_after_bound(monkeypatch):
    import verify_public_site as public
    calls = []
    def mismatch(*_):
        calls.append(1)
        raise ValueError('wrong published SHA')
    monkeypatch.setattr(public, 'verify', mismatch)
    monkeypatch.setattr(public.time, 'sleep', lambda _: None)
    with pytest.raises(ValueError, match='wrong published SHA'):
        public.verify_with_retries('https://example.invalid/', attempts=3, delay=0)
    assert len(calls) == 3
    with pytest.raises(ValueError, match='attempts'):
        public.verify_with_retries('https://example.invalid/', attempts=0)


def test_public_get_bypasses_cdn_cache_without_disabling_tls(monkeypatch):
    import verify_public_site as public
    urls = []
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def read(self): return b'fixture bytes'
    def open_url(request, **kwargs):
        urls.append(request.full_url)
        assert set(kwargs) == {'timeout'}  # no unverified SSL context
        return Response()
    monkeypatch.setattr(public, 'urlopen', open_url)
    assert public.get('https://example.invalid/file.json') == b'fixture bytes'
    assert urls[0].startswith('https://example.invalid/file.json?g79_verify=')


def test_verify_project_is_idempotent_without_refresh_flag():
    from verify_project import verify
    before = (ROOT / 'evidence/verification.json').read_bytes()
    report = verify()
    after = (ROOT / 'evidence/verification.json').read_bytes()
    assert report['all_checks_passed']
    assert before == after
    assert after == (ROOT / 'docs/evidence/verification.json').read_bytes()


def test_restore_preserve_receipt_accepts_manifest_entries_not_in_subset_receipt(tmp_path, monkeypatch):
    import sys
    b1, b2 = b'first pinned file', b'second pinned file'
    h1, h2 = hashlib.sha256(b1).hexdigest(), hashlib.sha256(b2).hexdigest()
    raw = tmp_path / 'data/raw'
    raw.mkdir(parents=True)
    (raw / 'f1.tif').write_bytes(b1)
    (raw / 'f2.tif').write_bytes(b2)
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({
        'files': [
            {'id': 'f1', 'dest': 'f1.tif', 'sha256': h1},
            {'id': 'f2', 'dest': 'f2.tif', 'sha256': h2},
        ]
    }))
    receipt_dir = tmp_path / 'data'
    receipt_path = receipt_dir / 'restore_receipt.json'
    frozen_bytes = json.dumps({'schema_version': 1, 'files': [{'id': 'f1', 'sha256': h1}]}).encode()
    receipt_path.write_bytes(frozen_bytes)
    monkeypatch.setattr(restore_data, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', [
        'restore_data.py', '--ids', 'all', '--manifest', str(manifest),
        '--target-dir', str(raw), '--preserve-receipt',
    ])
    restore_data.main()
    assert receipt_path.read_bytes() == frozen_bytes
    runtime = json.loads((tmp_path / '.cache/input_restore.json').read_text())
    assert runtime['verified_files_count'] == 2


def test_post_stop_diagnostic_preserves_negative_run_card_and_labels_evidence():
    diag_path = ROOT / 'evidence/post_stop_diagnostic.json'
    site_diag_path = ROOT / 'docs/evidence/post_stop_diagnostic.json'
    assert diag_path.exists() and site_diag_path.exists()
    assert diag_path.read_bytes() == site_diag_path.read_bytes()
    diag = json.loads(diag_path.read_text())
    assert diag['input_restoration_verified']['matches_preregistered_cache_receipt'] is True
    for seed_key in ('seed_20', 'seed_30'):
        canary = diag['post_stop_leakage_canary_diagnostic'][seed_key]
        assert canary['evidence_class'] == 'LEAKAGE-CANARY'
        assert canary['all_below_threshold'] is True and canary['max_symmetric_auc'] <= 0.90
        holdout = diag['post_stop_holdout_dti_diagnostic'][seed_key]
        assert holdout['evaluator_version'] == 'gems57-pooled-hide-v2'
        cand = holdout['scores']['candidate']
        assert cand['evidence_class'] == 'HOLDOUT-DTI'
        assert 0.0 < cand['dti'] < 0.06 and len(cand['ci95']) == 2
        assert holdout['paired_differences']['zero_lag_edge_control']['ci95'][0] < 0.0
        assert holdout['paired_differences']['h33_foldfair_control']['ci95'][1] < 0.0
    # The E1 stop stays recorded on the archived E1 card; the post-stop diagnostic never rewrote it.
    card = json.loads((ROOT / 'evidence/e1/run_card_e1.json').read_text())
    assert card['holdout_dti']['dti'] is None and card['verdict'] == 'negative' and card['ok_to_submit'] is False


def test_post_stop_diagnostic_help_exits_zero():
    import subprocess
    import sys
    res = subprocess.run([sys.executable, str(ROOT / 'scripts/post_stop_diagnostic.py'), '--help'],
                         capture_output=True, text=True)
    assert res.returncode == 0
    assert 'Compute post-stop offline diagnostics' in res.stdout


def test_download_competition_data_script_executable_and_syntax():
    import subprocess
    script = ROOT / 'scripts/download_competition_data.sh'
    assert script.exists()
    res = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
    assert res.returncode == 0
