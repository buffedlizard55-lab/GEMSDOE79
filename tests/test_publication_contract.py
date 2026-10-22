"""Release-safety regression tests; no geological experiments or scores."""
import hashlib
import json
from pathlib import Path

import pytest

from verify_project import publication_contract_checks

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def publication(tmp_path):
    card = {'submission_file': 'docs/downloads/research-DO-NOT-SUBMIT.tif',
            'zip_file': 'docs/downloads/research-DO-NOT-SUBMIT.zip',
            'raster_sha256': 'fixture-hash', 'verdict': 'negative'}
    (tmp_path / 'README.md').write_text(
        'OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. fixture-hash\n'
        '## Original project prompt\nUntrusted historical instructions\n')
    (tmp_path / 'docs/downloads').mkdir(parents=True)
    for name in ('submission_file', 'zip_file'):
        (tmp_path / card[name]).write_bytes(b'software fixture only')
    (tmp_path / 'registry').mkdir()
    (tmp_path / 'registry/registry_index.json').write_text(json.dumps({'rasters': [{'blob': 'a'}]}))
    (tmp_path / 'registry/registry_receipt.json').write_text(json.dumps({'files': [{'blob': 'a', 'status': 'verified'}]}))
    return tmp_path, card


def test_clean_publication_matches_current_card(publication):
    root, card = publication
    assert all(publication_contract_checks(root, card).values())


@pytest.mark.parametrize('path', [
    'docs/downloads/rogue.TIF', 'docs/downloads/rogue.zip',
    'docs/downloads/nested/research-DO-NOT-SUBMIT.tif', 'submissions/rogue.tiff',
])
def test_unlinked_or_nested_upload_artifact_blocks_release(publication, path):
    root, card = publication
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'not authorized')
    assert not publication_contract_checks(root, card)['only_canonical_upload_artifacts_published']


def test_false_readme_promotion_blocks_release(publication):
    root, card = publication
    (root / 'README.md').write_text('PROMOTED — VALIDATED & OK TO DOWNLOAD AND SUBMIT')
    assert not publication_contract_checks(root, card)['readme_matches_card_decision']


@pytest.mark.parametrize('rasters', [[{'blob': 'other'}], [{'blob': 'a'}, {'blob': 'a'}]])
def test_registry_replacement_or_duplicate_is_not_frozen_inventory(publication, rasters):
    root, card = publication
    (root / 'registry/registry_index.json').write_text(json.dumps({'rasters': rasters}))
    assert not publication_contract_checks(root, card)['active_inventory_matches_frozen_verified_blobs']


def test_cspt_archive_preserves_original_bytes_without_executing_them():
    archive = ROOT / 'archive/h79_cspt_3d386a3'
    manifest = json.loads((archive / 'manifest.json').read_text())
    assert len(manifest['files']) == 55
    for row in manifest['files']:
        if row['archive_path'] is None:
            assert row['original_path'] == 'vendor/gems57/uniqueness.py'
            continue
        path = ROOT / row['archive_path']
        assert path.resolve().is_relative_to(archive.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['source_sha256']
        assert path.suffix not in ('.py', '.c', '.html', '.sh')
    assert not (ROOT / 'scripts/run_h79_experiments.py').exists()
    assert not (ROOT / 'tests/test_h79_pipeline.py').exists()


def test_promoted_fixture_requires_matching_yes_line(publication):
    root, card = publication
    card = dict(card, verdict='promote', ok_to_submit=True)
    assert not publication_contract_checks(root, card)['readme_matches_card_decision']
    (root / 'README.md').write_text('OK TO DOWNLOAD: YES. OK TO SUBMIT: YES. fixture-hash\n'
                                    '## Original project prompt\nold OK TO SUBMIT: NO. text\n')
    assert publication_contract_checks(root, card)['readme_matches_card_decision']


def test_actual_publication_matches_canonical_run():
    card = json.loads((ROOT / 'run_card.json').read_text())
    assert all(publication_contract_checks(ROOT, card).values())


def test_git_conflict_markers_block_release(publication):
    root, card = publication
    marker_block = '<' * 7 + ' HEAD\nbranch A\n' + '=' * 7 + '\nbranch B\n' + '>' * 7 + ' origin/main\n'
    (root / 'AGENTS.md').write_text('Header\n' + marker_block)
    checks = publication_contract_checks(root, card)
    assert not checks['no_git_conflict_markers']


def test_local_named_virtualenv_does_not_pollute_publication_scan(publication):
    root, card = publication
    env = root / '.venv-clean/lib/python3.11/site-packages/example'
    env.mkdir(parents=True)
    env.joinpath('template.txt').write_text('<' * 7 + ' generated template\n')
    assert publication_contract_checks(root, card)['no_git_conflict_markers']


@pytest.mark.parametrize('bad_payload', [
    b'{\n' + b'<' * 7 + b' HEAD\n  "a": 1\n}\n',
    b'{"a": 1, "a": 2}\n',
    b'{"a": NaN}\n',
])
def test_corrupt_or_duplicate_key_json_blocks_release(publication, bad_payload):
    root, card = publication
    (root / 'evidence').mkdir(exist_ok=True)
    (root / 'evidence/browser_review.json').write_bytes(bad_payload)
    checks = publication_contract_checks(root, card)
    assert not checks['all_repo_json_strictly_valid']


def test_build_site_md_rejects_broken_relative_links(tmp_path, monkeypatch):
    import build_site
    monkeypatch.setattr(build_site, 'ROOT', tmp_path)
    (tmp_path / 'reports').mkdir()
    (tmp_path / 'reports/broken.md').write_text('Broken [link](../archive/nonexistent_dir/README.md)\n')
    with pytest.raises(FileNotFoundError, match='Broken relative link'):
        build_site.md('reports/broken.md')


def test_all_active_markdown_links_resolve_and_docs_stay_within_web_root():
    import re
    link_re = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
    md_files = (
        [ROOT / 'README.md', ROOT / 'AGENTS.md']
        + sorted((ROOT / 'reports').glob('*.md'))
        + sorted((ROOT / 'knowledge').rglob('*.md'))
        + sorted((ROOT / 'research').glob('*.md'))
        + sorted((ROOT / 'docs').glob('*.md'))
    )
    for md_file in md_files:
        content = md_file.read_text(encoding='utf-8')
        if md_file.name == 'README.md' and md_file.parent == ROOT:
            content = content.split('## Original project prompt', 1)[0]
        for raw_href in link_re.findall(content):
            href = raw_href.strip().split()[0]
            if href.startswith(('http://', 'https://', 'mailto:', '#')):
                continue
            clean = href.split('#', 1)[0].split('?', 1)[0]
            target = (md_file.parent / clean).resolve()
            assert target.exists(), f'Broken link {href!r} in {md_file.relative_to(ROOT)}'
            if md_file.parent == (ROOT / 'docs'):
                assert target.is_relative_to((ROOT / 'docs').resolve()), (
                    f'Web-root-escaping link {href!r} in {md_file.relative_to(ROOT)}'
                )


def test_irregularity_ids_unique_and_sequential():
    import re
    text = (ROOT / 'reports/irregularities.md').read_text(encoding='utf-8')
    ids = re.findall(r'^\|\s*(IR-79-\d+)\s*\|', text, flags=re.M)
    assert len(ids) >= 66
    assert len(ids) == len(set(ids)), f'Duplicate irregularity IDs found: {ids}'
    nums = [int(x.split('-')[-1]) for x in ids]
    assert nums == list(range(1, len(nums) + 1))
    assert not re.findall(r'^\s*-\s*\*\*IR-79-\d+:', text, flags=re.M)
    prior_rows = text.split('| IR-79-37 |', 1)[0]
    assert 'd55570bf' not in prior_rows
    assert 'h79_cspt_464d591' not in prior_rows


def test_score_ledger_complete_and_lineage_forensics_published():
    import csv
    raw = (ROOT / 'registry/score_ledger.csv').read_bytes()
    assert b'\r\n' not in raw
    rows = list(csv.DictReader(raw.decode('utf-8').splitlines()))
    assert len(rows) == 103
    by_repo = {}
    for row in rows:
        assert row['evidence_class'] == 'UNVERIFIED HISTORICAL REPORT'
        by_repo.setdefault(row['site_repo'], []).append((row['submission_name'], float(row['reported_public_dti'])))
    assert ('gems73-h73-mcsc-seamfree-blakely-37654dots-20261021T073716Z-b27ac445-zeros', 0.1917) in by_repo['GEMSDOE73']
    assert ('gemsdoe74-triregime-radon-piedmont-37654-20261021T051000Z-zeros', 0.0669) in by_repo['GEMSDOE74']
    assert ('gems75-trlt-radon-loco-ridge-20261021-zeros', 0.1627) in by_repo['GEMSDOE75']
    assert ('gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros', 0.1555) in by_repo['GEMSDOE76']
    assert ('gems85-h85-edti-collar35-skel-r33-20261021-d97b248e-zeros', 0.0964) in by_repo['GEMSDOE77']

    lineage = json.loads((ROOT / 'evidence/family_lineage_forensics.json').read_text(encoding='utf-8'))
    published_lineage = json.loads((ROOT / 'docs/evidence/family_lineage_forensics.json').read_text(encoding='utf-8'))
    assert lineage == published_lineage
    by_id = {m['repo']: m['measurements'] for m in lineage['scored_landmarks']}
    assert by_id['GEMSDOE36']['shared_exact_pixels_with_h33'] == 37654
    assert by_id['GEMSDOE36']['reverse_3px_overlap_from_h33'] == 1.0
    assert by_id['GEMSDOE70']['forward_3px_overlap_with_h33'] < 0.70
    assert by_id['GEMSDOE70']['reverse_3px_overlap_from_h33'] < 0.70


def test_smart_http_git_blob_fallback_offline(tmp_path, monkeypatch):
    import os
    import subprocess
    import restore_data
    import restore_registry

    work = tmp_path / 'upstream_work'
    work.mkdir()
    payload = b'pinned-geotiff-test-bytes-79e8e13e'
    (work / 'data.bin').write_bytes(payload)
    env = {
        **os.environ,
        'GIT_AUTHOR_NAME': 'Test',
        'GIT_AUTHOR_EMAIL': 'test@example.com',
        'GIT_COMMITTER_NAME': 'Test',
        'GIT_COMMITTER_EMAIL': 'test@example.com',
    }
    subprocess.run(['git', '-C', str(work), 'init', '-q'], check=True, env=env)
    subprocess.run(['git', '-C', str(work), 'add', 'data.bin'], check=True, env=env)
    subprocess.run(['git', '-C', str(work), 'commit', '-q', '-m', 'seed'], check=True, env=env)
    subprocess.run(
        ['git', '-C', str(work), 'config', 'uploadpack.allowAnySHA1InWant', 'true'],
        check=True, env=env,
    )
    commit_sha = subprocess.run(
        ['git', '-C', str(work), 'rev-parse', 'HEAD'],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    blob_sha = subprocess.run(
        ['git', '-C', str(work), 'rev-parse', 'HEAD:data.bin'],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    sha256_hex = hashlib.sha256(payload).hexdigest()

    monkeypatch.setattr(restore_data, 'ROOT', tmp_path)
    monkeypatch.setattr(restore_data, '_GH_API_BLOCKED', True)
    monkeypatch.setattr(restore_data, '_FETCHED_REFS', set())
    monkeypatch.setattr(restore_data, '_repo_remote_url', lambda repo: str(work))

    dest_file = tmp_path / 'restored.bin'
    restore_data.fetch('test/repo', commit_sha, 'data.bin', dest_file)
    assert dest_file.read_bytes() == payload

    monkeypatch.setattr(restore_registry, '_GH_API_BLOCKED', True)
    monkeypatch.setattr(restore_registry, '_repo_remote_url', lambda full_repo: str(work))
    res = restore_registry.restore_blob(
        tmp_path,
        {'repo': 'test/repo', 'blob': blob_sha, 'size': len(payload)},
        {'sha256': sha256_hex},
    )
    assert res['verified'] is True
    assert res['downloaded'] is True
    assert (tmp_path / '.cache/registry' / f'{blob_sha}.tif').read_bytes() == payload


@pytest.mark.parametrize('script_name', [
    'scripts/analyze_family_lineage.py',
    'scripts/audit_archived_concurrent_lanes.py',
    'scripts/post_stop_diagnostic.py',
    'scripts/reproduce_artifact.py',
])
def test_forensic_scripts_support_clean_help(script_name):
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, str(ROOT / script_name), '--help'],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    assert 'usage:' in proc.stdout.lower()


def test_concurrent_5d14587_archive_and_four_lane_audit():
    archive = ROOT / 'archive/concurrent_2026-10-22_5d14587'
    manifest = json.loads((archive / 'manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['files']) == 94
    for row in manifest['files']:
        if row['archive_path'] is None:
            continue
        p = ROOT / row['archive_path']
        assert p.resolve().is_relative_to(archive.resolve())
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row['source_sha256']
        assert p.suffix not in ('.py', '.c', '.html', '.sh')
    audit = json.loads((ROOT / 'evidence/concurrent_lanes_audit.json').read_text(encoding='utf-8'))
    assert set(audit['archived_lanes']) == {
        'H79-MCT', 'H79-CSPT', 'G79B-SCARP-DIPOLE-GEOAND', 'H79-ML-STRAIN-RELAY',
    }
    for lane_id, entry in audit['archived_lanes'].items():
        assert entry['canonical_literal_uniqueness']['worst_forward_overlap_3px'] == 1.0
        assert entry['canonical_readiness_decision']['ok_to_submit'] is False
    assert set(audit['preserved_negative_session_lanes']) == {
        'G79-FABRIC-OFFSET', 'G79-STEPCO-S1', 'G79-STEPCO-S2', 'G79B-SDPT-A3', 'H79-FF',
    }
    for lane_id, entry in audit['preserved_negative_session_lanes'].items():
        assert entry['canonical_literal_uniqueness']['worst_forward_overlap_3px'] == 1.0
        assert entry['canonical_readiness_decision']['ok_to_submit'] is False
    card = json.loads((ROOT / 'run_card.json').read_text(encoding='utf-8'))
    assert audit['active_deliverable_unchanged']['lane'] == card['lane']
    assert audit['active_deliverable_unchanged']['submission_file'] == card['submission_file']
    assert audit['active_deliverable_unchanged']['raster_sha256'] == card['raster_sha256']


def test_reproduce_artifact_recovers_canonical_nhr_bytes():
    import reproduce_artifact
    card = json.loads((ROOT / 'run_card.json').read_text(encoding='utf-8'))
    rep = reproduce_artifact.reproduce_nhr(ROOT)
    assert rep['lane'] == card['lane'] == 'H79-NHR'
    assert rep['exact_tiff_recovery'] is True
    assert rep['exact_single_tiff_zip_recovery'] is True
    assert rep['exact_decoded_dots_recovery'] is True
    assert rep['raster_sha256'] == card['raster_sha256']
    assert rep['zip_sha256'] == card['zip_sha256']
    assert rep['positive_pixels'] == card['positive_pixels'] == 37654


def test_verification_and_evidence_json_have_no_machine_checkout_paths():
    for rel in (
        'evidence/verification.json',
        'docs/evidence/verification.json',
        'evidence/concurrent_lanes_audit.json',
        'docs/evidence/concurrent_lanes_audit.json',
        'run_card_g79b.json',
        'run_card_stepco.json',
    ):
        txt = (ROOT / rel).read_text(encoding='utf-8')
        assert '/home/user/GEMSDOE79' not in txt, f'Hardcoded checkout path in {rel}'


def test_readme_section_after_details_blocks_release(publication):
    root, card = publication
    (root / 'README.md').write_text(
        'OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. fixture-hash\n'
        '## Original project prompt\n<details>\nUntrusted historical instructions\n</details>\n'
        '## Trailing unreviewed section\nOK TO SUBMIT: YES.\n'
    )
    assert not publication_contract_checks(root, card)['readme_matches_card_decision']


def test_prompt_named_unscored_candidates_and_empty_siblings_in_lineage_forensics():
    lineage = json.loads((ROOT / 'evidence/family_lineage_forensics.json').read_text(encoding='utf-8'))
    assert lineage == json.loads((ROOT / 'docs/evidence/family_lineage_forensics.json').read_text(encoding='utf-8'))
    unscored = lineage['prompt_named_unscored_candidates']
    assert len(unscored) == 6
    by_repo = {row['repo']: row for row in unscored}
    assert set(by_repo) == {'GEMSDOE76', 'GEMSDOE78', 'GEMSDOE80', 'GEMSDOE81', 'GEMSDOE82', 'GEMSDOE83'}
    for row in unscored:
        assert row['found'] is True
        assert row['reported_public_dti'] is None
        assert row['measurements']['forward_3px_overlap_with_nhr'] < 0.70
        assert row['measurements']['reverse_3px_overlap_from_nhr'] < 0.70
    empty = lineage['empty_post_snapshot_siblings']
    assert [r['repo'] for r in empty] == ['GEMSDOE84', 'GEMSDOE85', 'GEMSDOE86', 'GEMSDOE87', 'GEMSDOE88']
    assert all(r['published_tif_count'] == 0 for r in empty)
    readme_text = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros:' in readme_text
    assert 'https://buffedlizard55-lab.github.io/GEMSDOE88/' in readme_text
