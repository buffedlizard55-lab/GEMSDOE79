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
    'docs/downloads/nested/research-DO-NOT-SUBMIT.tif', 'docs/g79_mag/rogue.tif', 'submissions/rogue.tiff',
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
    assert len(ids) >= 89
    assert len(ids) == len(set(ids)), f'Duplicate irregularity IDs found: {ids}'
    nums = [int(x.split('-')[-1]) for x in ids]
    assert nums == list(range(1, len(nums) + 1))
    assert not re.findall(r'^\s*-\s*\*\*IR-79-\d+:', text, flags=re.M)
    prior_rows = text.split('| IR-79-37 |', 1)[0]
    assert 'd55570bf' not in prior_rows
    assert 'h79_cspt_464d591' not in prior_rows


def test_score_ledger_complete_and_lineage_forensics_published():
    import csv
    import analyze_family_lineage as afl
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
    landmarks_by_repo = {m['repo']: m for m in lineage['scored_landmarks']}
    by_id = {r: m['measurements'] for r, m in landmarks_by_repo.items()}
    assert by_id['GEMSDOE36']['shared_exact_pixels_with_h33'] == 37654
    assert by_id['GEMSDOE36']['reverse_3px_overlap_from_h33'] == 1.0
    assert by_id['GEMSDOE70']['forward_3px_overlap_with_h33'] < 0.70
    assert by_id['GEMSDOE70']['reverse_3px_overlap_from_h33'] < 0.70
    assert landmarks_by_repo['GEMSDOE76']['reported_public_dti'] == 0.1555
    assert landmarks_by_repo['GEMSDOE76']['prompt_3cfa694f_reported_public_dti'] == 0.2194

    siblings_by_repo = {s['repo']: s for s in lineage['post_snapshot_siblings']}
    assert set(siblings_by_repo) == {
        'GEMSDOE76', 'GEMSDOE78', 'GEMSDOE80', 'GEMSDOE81', 'GEMSDOE82', 'GEMSDOE83',
        'GEMSDOE84', 'GEMSDOE85', 'GEMSDOE86', 'GEMSDOE87', 'GEMSDOE88',
    }
    for stub_repo in ('GEMSDOE84', 'GEMSDOE85', 'GEMSDOE86', 'GEMSDOE87', 'GEMSDOE88'):
        assert siblings_by_repo[stub_repo]['total_tif_count_at_head'] == 0
        assert siblings_by_repo[stub_repo]['published_tifs'] == []
    for active_sib, expected_name in (
        ('GEMSDOE76', 'gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros.tif'),
        ('GEMSDOE78', 'gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros.tif'),
        ('GEMSDOE80', 'gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros.tif'),
        ('GEMSDOE81', 'gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros.tif'),
        ('GEMSDOE82', 'gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros.tif'),
        ('GEMSDOE83', 'gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros.tif'),
    ):
        names = [Path(t['path']).name for t in siblings_by_repo[active_sib]['published_tifs']]
        assert expected_name in names, f'{expected_name} missing in {active_sib}: {names}'

    # Unit check that select_sibling_tifs does not truncate alphabetically before prompt-named candidate
    synthetic_tifs = [
        {'path': f'archive/a{i}.tif', 'blob': f'blob{i}'} for i in range(6)
    ] + [
        {'path': 'docs/downloads/gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros.tif', 'blob': 'targetblob'},
    ]
    picked = afl.select_sibling_tifs('GEMSDOE78', synthetic_tifs)
    assert any(p['blob'] == 'targetblob' for p in picked)


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


def test_reproduce_artifact_recovers_archived_nhr_bytes():
    import reproduce_artifact
    live = json.loads((ROOT / 'run_card.json').read_text(encoding='utf-8'))
    rep = reproduce_artifact.reproduce_nhr(ROOT)
    assert rep['lane'] == 'H79-NHR'
    assert rep['exact_tiff_recovery'] is True
    assert rep['exact_single_tiff_zip_recovery'] is True
    assert rep['exact_decoded_dots_recovery'] is True
    assert rep['raster_sha256'] == reproduce_artifact.NHR_RASTER_SHA256
    assert rep['zip_sha256'] == 'b882f55d38a0020d1b4773a5f2db8d7eddc401fb38b5d58a98758c19b99a6bc7'
    assert rep['positive_pixels'] == 37654
    if live['lane'] == 'H79-NHR':
        assert rep['raster_sha256'] == live['raster_sha256']
        assert live['positive_pixels'] == 37654


def test_verification_and_evidence_json_have_no_machine_checkout_paths():
    for rel in (
        'evidence/verification.json',
        'docs/evidence/verification.json',
        'evidence/concurrent_lanes_audit.json',
        'docs/evidence/concurrent_lanes_audit.json',
        'evidence/registry_obstructions_certificate.json',
        'docs/evidence/registry_obstructions_certificate.json',
        'evidence/family_lineage_forensics.json',
        'docs/evidence/family_lineage_forensics.json',
        'knowledge/official_sources.json',
        'docs/evidence/source_health.json',
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


def test_three_tier_pigeonhole_obstruction_and_sibling_audit_certificates():
    cert = json.loads((ROOT / 'evidence/registry_obstructions_certificate.json').read_text(encoding='utf-8'))
    pub_cert = json.loads((ROOT / 'docs/evidence/registry_obstructions_certificate.json').read_text(encoding='utf-8'))
    assert cert == pub_cert
    assert cert['scientific_experiments_performed'] == 0
    assert cert['submission_slots_used'] == 0
    assert cert['allowed_off_catalogue_pixels'] == 5106385
    assert cert['tier_1_literal_positive_support']['bounds']['uncovered_allowed_pixels'] == 0
    assert cert['tier_2_budget_matched_v3_plateaus']['n_zero_uncovered_witnesses'] == 4
    for w in cert['tier_2_budget_matched_v3_plateaus']['witnesses']:
        assert w['budget_matched_v3_bounds']['uncovered_allowed_pixels'] == 0
        assert w['budget_matched_v3_bounds']['blocks_every_nonempty_candidate'] is True
    for w in cert['tier_3_strictly_binary_lattice_pigeonhole']['witnesses']:
        assert w['is_strictly_binary_0_1_in_footprint'] is True
        assert w['classified_dense_by_v3_threshold_0p20'] is False
        assert w['budget_matched_v3_bounds']['uncovered_allowed_pixels'] == 6514
        assert w['budget_matched_v3_bounds']['pigeonhole_min_overlap_exact_rational'] == '15570/18827'
        assert w['budget_matched_v3_bounds']['max_passable_dot_budget_at_0p70_limit'] == 21713
        assert w['budget_matched_v3_bounds']['blocks_every_37654_dot_candidate'] is True

    by_repo = {r['repo']: r for r in cert['cross_sibling_uniqueness_audit']}
    assert {'GEMSDOE32', 'GEMSDOE79', 'GEMSDOE79-H79-NHR', 'GEMSDOE79-G79-THVC',
            'GEMSDOE76', 'GEMSDOE78', 'GEMSDOE80', 'GEMSDOE81', 'GEMSDOE82', 'GEMSDOE83'} == set(by_repo)
    for repo in ('GEMSDOE76', 'GEMSDOE78', 'GEMSDOE80', 'GEMSDOE81', 'GEMSDOE82', 'GEMSDOE83'):
        assert by_repo[repo]['passes_unmodified_992_v3_gate'] is False
        assert by_repo[repo]['informative_collisions_gt_0p70_among_26'] >= 11
    assert by_repo['GEMSDOE79-H79-NHR']['passes_excess_overlap_le_0p70_on_26_informative_set'] is False
    assert by_repo['GEMSDOE79-G79-THVC']['passes_excess_overlap_le_0p70_on_26_informative_set'] is False
    assert by_repo['GEMSDOE83']['passes_excess_overlap_le_0p70_on_26_informative_set'] is True

    delta = json.loads((ROOT / 'registry/registry_delta.json').read_text(encoding='utf-8'))
    pub_delta = json.loads((ROOT / 'docs/evidence/registry_delta.json').read_text(encoding='utf-8'))
    assert delta == pub_delta
    assert delta['n_new_rasters'] >= 207
    assert 'GEMSDOE79' not in {r['repo'] for r in delta['repositories']}


def test_official_sources_and_health_synced_on_2026_10_22():
    sources = json.loads((ROOT / 'knowledge/official_sources.json').read_text(encoding='utf-8'))
    health = json.loads((ROOT / 'docs/evidence/source_health.json').read_text(encoding='utf-8'))
    assert sources['reviewed_date_utc'] == '2026-10-22'
    assert health['scientific_claims_reviewed_date'] == '2026-10-22'
    assert health['leaderboard_observation']['observed_date'] == '2026-10-22'
    assert health['leaderboard_observation']['public_dti'] == 0.4413
    ids = {s['id'] for s in sources['sources']}
    assert {'DD-PROBLEM', 'DD-TIMELINE-PRIZES', 'DD-MASK', 'DD-NEW-FAULT-DEF',
            'DD-POOL', 'DOE-RULES', 'USGS-GEODAWN', 'GDR-1391',
            'EPSG-32611', 'PRIMARY-TVERSKY-1977', 'SIBLING-GEMSDOE32-PAGES'} <= ids


def test_every_sha256_cited_in_session_6d4a2fdf_review_matches_machine_receipts():
    import re
    import reproduce_artifact
    card = json.loads((ROOT / 'run_card.json').read_text(encoding='utf-8'))
    cert = json.loads((ROOT / 'evidence/registry_obstructions_certificate.json').read_text(encoding='utf-8'))
    lineage = json.loads((ROOT / 'evidence/family_lineage_forensics.json').read_text(encoding='utf-8'))
    dcard = json.loads((ROOT / 'archive/h79_dilstep_6444be2d/run_card_dilstep.json').read_text(encoding='utf-8'))
    known_full_hashes = {
        card['raster_sha256'], card['zip_sha256'],
        dcard['raster_sha256'], dcard['zip_sha256'],
        reproduce_artifact.NHR_RASTER_SHA256,
        'b882f55d38a0020d1b4773a5f2db8d7eddc401fb38b5d58a98758c19b99a6bc7',
    }
    known_prefixes = {h[:8] for h in known_full_hashes}
    known_prefixes.add(cert['tier_1_literal_positive_support']['witness_sha256'][:8])
    for w in cert['tier_2_budget_matched_v3_plateaus']['witnesses'] + cert['tier_3_strictly_binary_lattice_pigeonhole']['witnesses']:
        known_prefixes.add(w['sha256'][:8])
    for r in cert['cross_sibling_uniqueness_audit']:
        known_prefixes.add(r['sha256'][:8])
    for r in lineage['scored_landmarks']:
        if r.get('found'):
            known_prefixes.add(r['source']['sha256'][:8])

    review_txt = (ROOT / 'reports/session_review_6d4a2fdf.md').read_text(encoding='utf-8')
    for full_h in re.findall(r'\b[0-9a-f]{64}\b', review_txt):
        assert full_h in known_full_hashes, f'Unverified 64-hex hash {full_h} in session review'
    for short_h in re.findall(r'\b([0-9a-f]{8})…', review_txt):
        assert short_h in known_prefixes, f'Unverified 8-hex hash prefix {short_h}… in session review'

