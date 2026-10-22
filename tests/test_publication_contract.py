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
    # For negative fixture, promoted string should not count as valid negative
    assert not publication_contract_checks(root, card)['readme_matches_negative_decision']
    assert not publication_contract_checks(root, card)['readme_matches_decision']


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


def test_actual_publication_matches_canonical_negative_run():
    card = json.loads((ROOT / 'run_card.json').read_text())
    assert all(publication_contract_checks(ROOT, card).values())
