"""Tiny synthetic software fixtures only; not competition measurements."""
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import numpy as np
import pytest
import rasterio
from affine import Affine
import verify_overlap_witness as review


@pytest.fixture
def witness_root(tmp_path, monkeypatch):
    root = tmp_path
    for directory in ('registry', 'evidence', '.cache/registry', 'vendor/gems57', 'data/reference'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    # Pin the actual shared bytes, not a local copy of its mathematics.
    shared = Path(review.__file__).parents[1] / 'vendor/gems57/uniqueness.py'
    rel = 'vendor/gems57/uniqueness.py'
    shutil.copyfile(shared, root / rel)
    (root / 'registry/template_pin.json').write_text(json.dumps({'files': [
        {'path': rel, 'sha256': hashlib.sha256(shared.read_bytes()).hexdigest()}]}))
    (root / 'registry/data_manifest.json').write_text('{"files":[]}')
    crs, transform = rasterio.crs.CRS.from_epsg(32611), Affine(100, 0, 0, 0, -100, 500)
    fp = np.ones((5, 5), dtype=bool)
    grid = SimpleNamespace(footprint=fp, catalogue=np.zeros_like(fp),
                           shape=fp.shape, crs=crs, transform=transform)
    monkeypatch.setattr(review, 'load_grid', lambda _: grid)
    provisional = root / 'fixture.tif'
    with rasterio.open(provisional, 'w', driver='GTiff', width=5, height=5,
                       count=1, dtype='float32', crs=crs, transform=transform) as ds:
        ds.write(np.full(fp.shape, .2, dtype='float32'), 1)
    data = provisional.read_bytes()
    blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
    monkeypatch.setattr(review, 'UNIVERSAL_WITNESS_BLOB', blob)
    path = root / '.cache/registry' / (blob + '.tif')
    provisional.replace(path)
    row = {'blob': blob, 'repo': 'software-fixture', 'size': len(data)}
    pin = {'blob': blob, 'status': 'verified', 'sha256': hashlib.sha256(data).hexdigest()}
    (root / 'registry/registry_index.json').write_text(json.dumps({'rasters': [row]}))
    (root / 'registry/registry_receipt.json').write_text(json.dumps({'files': [pin]}))
    cert = review.saturation_certificate(path, fp, grid.catalogue,
                                         expected_grid=(fp.shape, crs, transform))
    (root / 'evidence/universal_overlap_certificate.json').write_text(json.dumps(cert))
    return root, path


def test_frozen_witness_remeasured_without_rewriting_evidence(witness_root):
    root, _ = witness_root
    original = {p: p.read_bytes() for folder in ('registry', 'evidence') for p in (root / folder).iterdir()}
    result = review.verify_witness(root)
    assert result['all_checks_passed']
    assert result['scientific_experiments_performed'] == result['submission_slots_used'] == 0
    assert all(p.read_bytes() == data for p, data in original.items())


def test_witness_byte_tampering_is_rejected(witness_root):
    root, path = witness_root
    path.write_bytes(path.read_bytes() + b'corruption')
    with pytest.raises(ValueError, match='SHA-256/Git-blob/size'):
        review.verify_witness(root)


def test_shared_module_tampering_is_rejected(witness_root):
    root, _ = witness_root
    (root / 'vendor/gems57/uniqueness.py').write_text('modified')
    with pytest.raises(ValueError, match='Shared template pin'):
        review.verify_witness(root)


def test_mismatched_original_certificate_does_not_pass(witness_root):
    root, _ = witness_root
    path = root / 'evidence/universal_overlap_certificate.json'
    original = json.loads(path.read_text())
    original['uncovered_allowed_pixels'] = 1
    path.write_text(json.dumps(original))
    result = review.verify_witness(root)
    assert not result['all_checks_passed']
    assert result['checks']['uncovered_allowed_pixels'] is False


def test_missing_witness_does_not_fetch_without_explicit_restore(witness_root, monkeypatch):
    root, path = witness_root
    path.unlink()
    def forbidden(*_):
        pytest.fail('An offline witness check must not download')
    monkeypatch.setattr(review, 'restore_blob', forbidden)
    with pytest.raises(FileNotFoundError):
        review.verify_witness(root)


def test_reference_pin_tampering_is_rejected(witness_root):
    root, _ = witness_root
    (root / 'data/reference/sample.tif').write_bytes(b'changed reference')
    (root / 'registry/data_manifest.json').write_text(json.dumps({'files': [
        {'id': 'sample_submission', 'dest': 'sample.tif', 'sha256': '0' * 64}]}))
    with pytest.raises(ValueError, match='Reference grid pin mismatch'):
        review.verify_witness(root)


def test_report_cli_never_overwrites_existing_evidence(witness_root, monkeypatch):
    import sys
    root, _ = witness_root
    output = root / 'existing-report.json'
    output.write_text('original evidence')
    verify = review.verify_witness
    monkeypatch.setattr(review, 'verify_witness', lambda **kwargs: verify(root, **kwargs))
    monkeypatch.setattr(sys, 'argv', ['verify_overlap_witness.py', '--report', str(output)])
    with pytest.raises(FileExistsError):
        review.main()
    assert output.read_text() == 'original evidence'
