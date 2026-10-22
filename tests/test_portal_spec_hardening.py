"""Synthetic software fixtures only: no geological model, score, or submission."""
from __future__ import annotations

import json
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import gems79.portal_spec as portal
import validate_portal_spec as cli


@pytest.fixture
def rasters(tmp_path):
    values = np.full((4, 5), 0.5, dtype='float32')
    values[0] = np.nan
    profile = {'driver': 'GTiff', 'height': 4, 'width': 5, 'count': 1,
               'dtype': 'float32', 'crs': 'EPSG:32611',
               'transform': from_origin(243350, 4508550, 100, 100),
               'nodata': float('nan')}
    template = tmp_path / 'sample.tif'
    with rasterio.open(template, 'w', **profile) as dst:
        dst.write(values, 1)
    return template, values, profile


def write_tif(path, values, profile, **changes):
    profile = dict(profile, **changes)
    with rasterio.open(path, 'w', **profile) as dst:
        for band in range(1, profile['count'] + 1):
            dst.write(values, band)
    return path


def wrap(path, destination, name='prediction.tif'):
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(path, arcname=name)
    return destination


def assert_complete_negative(report):
    assert report['ok'] is False
    assert [row['rule'] for row in report['rules']] == list(portal.RULES)
    assert all(type(row['pass']) is bool for row in report['rules'])
    assert len(report['rules']) == len({row['rule'] for row in report['rules']}) == 8
    assert report['organizer_acceptance_established'] is False
    json.dumps(report, allow_nan=False)


def test_zip_cannot_erase_inner_multiband_rejection(rasters, tmp_path):
    template, values, profile = rasters
    two = write_tif(tmp_path / 'two.tif', values, profile, count=2)
    zipped = wrap(two, tmp_path / 'two.zip')
    for path in (two, zipped):
        report = portal.validate_portal_file(path, template)
        assert_complete_negative(report)
        assert 'R1' in report['failed_rules']
        assert '2 band(s)' in report['rules'][0]['detail']


def test_zip_single_band_is_not_falsely_blocked(rasters, tmp_path):
    template, _, _ = rasters
    zipped = wrap(template, tmp_path / 'good.zip')
    report = portal.validate_portal_file(zipped, template)
    assert portal.portal_report_passed(report)
    assert report['inner_tif'] == 'prediction.tif'


def test_interior_validity_mask_cannot_hide_raw_finite_predictions(rasters, tmp_path):
    template, values, profile = rasters
    path = tmp_path / 'hidden.tif'
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(path, 'w', **profile) as dst:
            dst.write(values, 1)
            mask = np.where(np.isfinite(values), 255, 0).astype('uint8')
            mask[2, 2] = 0
            dst.write_mask(mask)
    for candidate in (path, wrap(path, tmp_path / 'hidden.zip')):
        report = portal.validate_portal_file(candidate, template)
        assert_complete_negative(report)
        assert 'R7' in report['failed_rules']
        assert report['cells']['inside_invalid_mask'] == 1
        assert report['cells']['inside_nonfinite'] == 0


@pytest.mark.parametrize('case', ['missing_artifact', 'missing_template', 'corrupt_template',
                                 'corrupt_zip', 'bad_tiff_in_zip', 'empty_file', 'wrong_extension'])
def test_input_errors_are_complete_private_negative_reports(rasters, tmp_path, case):
    template, values, profile = rasters
    path = write_tif(tmp_path / 'prediction.tif', values, profile)
    if case == 'missing_artifact':
        path = tmp_path / 'private-location' / 'missing.tif'
    elif case == 'missing_template':
        template = tmp_path / 'private-location' / 'missing-template.tif'
    elif case == 'corrupt_template':
        template = tmp_path / 'bad_template.tif'
        template.write_bytes(b'not a TIFF')
    elif case == 'corrupt_zip':
        path = tmp_path / 'broken.zip'
        path.write_bytes(b'not a ZIP')
    elif case == 'bad_tiff_in_zip':
        bad = tmp_path / 'broken.tif'
        bad.write_bytes(b'not a TIFF')
        path = wrap(bad, tmp_path / 'broken_inner.zip')
    elif case == 'empty_file':
        path.write_bytes(b'')
    else:
        wrong = path.with_suffix('.png')
        shutil.copyfile(path, wrong)
        path = wrong
    report = portal.validate_portal_file(path, template)
    assert_complete_negative(report)
    assert str(tmp_path) not in json.dumps(report)
    assert not portal.portal_report_passed(report)


@pytest.mark.parametrize('member', ['../escape.tif', '/absolute.tif', 'C:/drive.tif',
                                   'folder\\escape.tif'])
def test_unsafe_zip_member_refuses_without_extraction(rasters, tmp_path, member):
    template, _, _ = rasters
    path = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(member, template.read_bytes())
    report = portal.validate_portal_file(path, template)
    assert_complete_negative(report)
    assert 'R1' in report['failed_rules']
    assert not (tmp_path.parent / 'escape.tif').exists()


def test_symlink_zip_member_refuses(rasters, tmp_path):
    template, _, _ = rasters
    path = tmp_path / 'link.zip'
    info = zipfile.ZipInfo('prediction.tif')
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(info, b'/private/file')
    report = portal.validate_portal_file(path, template)
    assert_complete_negative(report)
    assert 'R1' in report['failed_rules']


def test_zip_inspection_limit_applies_before_inflation(rasters, tmp_path, monkeypatch):
    template, _, _ = rasters
    path = tmp_path / 'large_member.zip'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('prediction.tif', b'0' * 20000)
    monkeypatch.setattr(portal, 'MAX_INSPECTION_BYTES', 1000)
    assert path.stat().st_size < 1000
    report = portal.validate_portal_file(path, template)
    assert_complete_negative(report)
    assert 'R1' in report['failed_rules']
    assert report['cells'] == {'compared': False}


def test_empty_reference_footprint_cannot_vacuously_pass(tmp_path, rasters):
    _, values, profile = rasters
    template = write_tif(tmp_path / 'empty_reference.tif', np.full_like(values, np.nan), profile)
    candidate = write_tif(tmp_path / 'candidate.tif', values, profile)
    report = portal.validate_portal_file(candidate, template)
    assert_complete_negative(report)
    assert report['inspection_error']['stage'] == 'read_template'


def test_artifact_changed_during_inspection_cannot_reuse_old_hash(rasters, tmp_path, monkeypatch):
    template, values, profile = rasters
    candidate = write_tif(tmp_path / 'prediction.tif', values, profile)
    inspect = portal._validate_tif

    def mutate_after_read(path, reference, report):
        inspect(path, reference, report)
        with candidate.open('ab') as stream:
            stream.write(b'trailing bytes changed the identity')

    monkeypatch.setattr(portal, '_validate_tif', mutate_after_read)
    report = portal.validate_portal_file(candidate, template)
    assert_complete_negative(report)
    assert report['bytes_stable_during_validation'] is False
    assert report['inspection_error']['stage'] == 'verify_stable_bytes'


@pytest.mark.parametrize('change', ['partial', 'duplicate_rule', 'truthy_pass', 'aggregate_only',
                                   'wrong_hash', 'wrong_reference', 'error', 'unstable'])
def test_aggregate_pass_cannot_override_report_contract(rasters, change):
    template, _, _ = rasters
    report = portal.validate_portal_file(template, template)
    expected_sha, expected_ref = report['sha256'], report['template_sha256']
    assert portal.portal_report_passed(report, expected_sha256=expected_sha,
                                      expected_template_sha256=expected_ref)
    changed = deepcopy(report)
    if change == 'partial':
        changed['rules'].pop()
    elif change == 'duplicate_rule':
        changed['rules'][0] = deepcopy(changed['rules'][1])
    elif change == 'truthy_pass':
        changed['rules'][0]['pass'] = 1
    elif change == 'aggregate_only':
        changed.pop('rules')
    elif change == 'wrong_hash':
        changed['sha256'] = 'a' * 64
    elif change == 'wrong_reference':
        changed['template_sha256'] = 'b' * 64
    elif change == 'error':
        changed['inspection_error'] = {'type': 'ValueError'}
    else:
        changed['bytes_stable_during_validation'] = False
    assert not portal.portal_report_passed(changed, expected_sha256=expected_sha,
                                          expected_template_sha256=expected_ref)


def test_cli_keeps_batch_failures_and_never_overwrites_evidence(rasters, tmp_path, capsys):
    template, _, _ = rasters
    destination = tmp_path / 'reports' / 'new.json'
    code = cli.main([str(template), str(tmp_path / 'missing.tif'),
                     '--template', str(template), '--json', str(destination)])
    assert code == 2
    reports = json.loads(destination.read_text())
    assert reports[0]['ok'] is True
    assert_complete_negative(reports[1])
    before = destination.read_bytes()
    assert cli.main([str(template), '--template', str(template), '--json', str(destination)]) == 2
    assert destination.read_bytes() == before
    captured = capsys.readouterr()
    assert 'Traceback' not in captured.out + captured.err
    assert 'existing evidence was not replaced' in captured.err
