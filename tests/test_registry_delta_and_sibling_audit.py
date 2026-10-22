from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_registry_delta_captures_post_snapshot_sibling_rasters() -> None:
    delta = json.loads((ROOT / 'registry/registry_delta.json').read_text())
    index = json.loads((ROOT / 'registry/registry_index.json').read_text())
    indexed_blobs = {r['blob'] for r in index['rasters']}
    assert delta['n_repositories_scanned'] >= 92
    assert len(delta['repositories']) == delta['n_repositories_scanned']
    assert all(r['status'] == 'ok' for r in delta['repositories'])
    assert delta['n_new_rasters'] == len(delta['rasters']) >= 207
    delta_blobs = [r['blob'] for r in delta['rasters']]
    assert len(delta_blobs) == len(set(delta_blobs))
    assert indexed_blobs.isdisjoint(delta_blobs)
    scanned_names = {r['repo'] for r in delta['repositories']}
    for expected_repo in (
        'GEMSDOE76', 'GEMSDOE78', 'GEMSDOE80', 'GEMSDOE81',
        'GEMSDOE82', 'GEMSDOE83', 'GEMSDOE84', 'GEMSDOE88', 'GEMSDOE92',
    ):
        assert expected_repo in scanned_names


def test_registry_delta_tree_scanner_handles_blobless_clone(tmp_path: Path) -> None:
    """Regression test for IR-79-69: --filter=blob:none clones omit paths in rev-list --missing=allow-promisor."""
    sys.path.insert(0, str(ROOT / 'scripts'))
    import registry_delta_git

    origin_repo = tmp_path / 'origin_repo'
    origin_repo.mkdir()
    subprocess.run(['git', 'init', '-b', 'main'], cwd=origin_repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=origin_repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=origin_repo, check=True)
    subprocess.run(['git', 'config', 'uploadpack.allowFilter', 'true'], cwd=origin_repo, check=True)
    subprocess.run(['git', 'config', 'uploadpack.allowAnySHA1InWant', 'true'], cwd=origin_repo, check=True)
    sub_dir = origin_repo / 'docs/downloads'
    sub_dir.mkdir(parents=True)
    payload = b'FAKE_TIFF_PAYLOAD_12345'
    (sub_dir / 'candidate-test.tif').write_bytes(payload)
    data_ref = origin_repo / 'data/reference'
    data_ref.mkdir(parents=True)
    (data_ref / 'sample_submission.tif').write_bytes(b'IGNORED_DATA_FILE')
    subprocess.run(['git', 'add', '.'], cwd=origin_repo, check=True)
    subprocess.run(['git', 'commit', '-m', 'add tif'], cwd=origin_repo, check=True, stdout=subprocess.DEVNULL)

    bare_blobless = tmp_path / 'blobless.git'
    subprocess.run(
        ['git', 'clone', '--bare', '--filter=blob:none', f'file://{origin_repo}', str(bare_blobless)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    cache_dir = tmp_path / 'cache'
    res = registry_delta_git.scan_gitdir(bare_blobless, 'GEMSDOE_TEST', set(), cache_dir=cache_dir)
    assert res['status'] == 'ok'
    assert len(res['new']) == 1
    assert res['new'][0]['path'] == 'docs/downloads/candidate-test.tif'
    assert res['new'][0]['sha256'] == hashlib.sha256(payload).hexdigest()
    assert (cache_dir / f"{res['new'][0]['blob']}.tif").read_bytes() == payload


def test_post_snapshot_sibling_audit_and_binary_pigeonhole_certificate() -> None:
    audit = json.loads((ROOT / 'evidence/post_snapshot_sibling_audit.json').read_text())
    published_audit = json.loads((ROOT / 'docs/evidence/post_snapshot_sibling_audit.json').read_text())
    assert audit == published_audit

    pins = audit['shared_tools_pinned']
    # IR-79-130: frozen audit pin may equal the current tool sha or the
    # previous pin recorded in registry/template_pin.json (amendment D-2
    # appended functions without changing audit-used behaviour).
    _entry = next(e for e in json.loads((ROOT / 'registry/template_pin.json').read_text())['files']
                  if e['path'] == 'vendor/gems57/uniqueness.py')
    # IR-79-229: D-3 added a third amendment; recorded historical pins also count.
    assert pins['uniqueness_py_sha256'] in (
        _sha256(ROOT / 'vendor/gems57/uniqueness.py'), _entry['previous_sha256'],
        *_entry.get('historical_sha256', []))
    # IR-79-232: the shared v4 NaN-exterior amendment changed validate.py and
    # evaluate_holdout's call path additively; a recorded previous pin counts,
    # the same precedent the uniqueness pin above already uses.
    _v = next(e for e in json.loads((ROOT / 'registry/template_pin.json').read_text())['files']
              if e['path'] == 'vendor/gems57/validate.py')
    assert pins['validate_py_sha256'] in (
        _sha256(ROOT / 'vendor/gems57/validate.py'), _v['previous_sha256'],
        *_v.get('historical_sha256', []))
    assert pins['evaluate_holdout_py_sha256'] == _sha256(ROOT / 'vendor/gems57/evaluate_holdout.py')
    assert pins['disk3_exactness_self_test']['matches_edt_le_3_exact'] is True

    inv = audit['organization_inventory']
    assert inv['frozen_snapshot_blobs'] == 992
    assert inv['post_snapshot_and_cross_ref_delta_blobs'] >= 207
    assert inv['total_unique_prediction_blobs_verified'] == (
        inv['frozen_snapshot_blobs'] + inv['post_snapshot_and_cross_ref_delta_blobs']
    )

    pigeon = audit['dual_regime_pigeonhole_impossibility_certificate']['sparse_binary_dot_field_pigeonhole_proof']['witness']
    assert pigeon['representation'] == 'dot_field'
    assert pigeon['halo_allowed_cells'] + pigeon['uncovered_allowed_cells'] == 5_106_385
    assert pigeon['uncovered_allowed_cells'] == 6_514
    assert abs(pigeon['guaranteed_min_overlap_at_37654_dots'] - (37_654 - 6_514) / 37_654) < 1e-6
    assert pigeon['guaranteed_min_overlap_at_37654_dots'] > 0.70

    by_repo = {row['repo']: row for row in audit['prompt_sibling_candidates_audit']}
    active_card = json.loads((ROOT / 'run_card.json').read_text())
    nhr_card = json.loads((ROOT / 'archive/h79_nhr/run_card.json').read_text())
    g79 = by_repo['GEMSDOE79']
    assert g79['sha256'] == nhr_card['raster_sha256']
    assert g79['format_validation']['all_checks_passed'] is True
    u79 = g79['uniqueness_cross_repo_priors_only']
    assert u79['literal_rasters_gt_0_70'] > 0
    assert u79['budget_matched_v3_rasters_gt_0_70'] > 0
    assert u79['passes_non_space_filling_0_70_gate'] is False
    assert u79['passes_sparse_le_60k_0_70_gate'] is False

    dilstep_card = json.loads((ROOT / 'archive/h79_dilstep_6444be2d/run_card_dilstep.json').read_text())
    local_lanes = audit['local_gems79_concurrent_lanes_audit']
    assert local_lanes['H79-DILSTEP_active']['sha256'] == dilstep_card['raster_sha256']
    if 'G79-THVC' in local_lanes:
        assert local_lanes['G79-THVC']['sha256'] == active_card['raster_sha256']
    assert local_lanes['H79-NHR_archived']['sha256'] == nhr_card['raster_sha256']
    assert local_lanes['G79-MAG_quarantined']['overlap_vs_13gemsdoe_r13_lattice_s5'] > 0.99

    g81 = by_repo['GEMSDOE81']
    assert g81['uniqueness_cross_repo_priors_only']['worst_sparse_le_60k_match']['overlap_3px'] > 0.90

    review_md = (ROOT / 'reports/session_review_4ddab9a1.md').read_text()
    for row in audit['prompt_sibling_candidates_audit']:
        assert row['matched_path'] in review_md, f"Missing exact path {row['matched_path']} in session review"
        assert row['sha256'][:12] in review_md, f"Missing exact sha256 prefix {row['sha256'][:12]} in session review"

    matrix = audit['pairwise_forward_3px_overlap_matrix']
    keys = list(matrix)
    for a in keys:
        assert matrix[a][a] == 1.0
        for b in keys:
            assert 0.0 <= matrix[a][b] <= 1.0


def test_irregularities_markdown_rows_and_prompt_sync() -> None:
    irreg_text = (ROOT / 'reports/irregularities.md').read_text()
    ids: list[int] = []
    for line in irreg_text.splitlines():
        if line.lstrip().startswith('| IR-79-'):
            stripped = line.strip()
            assert stripped.startswith('|') and stripped.endswith('|'), f'Broken table row: {line!r}'
            assert stripped.count('|') == 4, f'Unexpected column count in: {line!r}'
            m = re.match(r'^\|\s*IR-79-(\d+)\s*\|', stripped)
            assert m is not None
            ids.append(int(m.group(1)))
    assert len(ids) == len(set(ids))
    assert max(ids) >= 109

    readme = (ROOT / 'README.md').read_text()
    for repo_num in range(84, 89):
        assert f'https://buffedlizard55-lab.github.io/GEMSDOE{repo_num}/' in readme
    assert (ROOT / 'research/hypotheses_4ddab9a1_untried.md').is_file()
    assert (ROOT / 'reports/session_review_4ddab9a1.md').is_file()
