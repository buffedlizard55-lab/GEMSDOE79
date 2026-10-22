"""Rule-by-rule tests for the official-format validator (src/gems79/portal_spec.py).

Calibration: the official template must pass; the project's zero-filled research
TIFFs must fail exactly R6 (outside-bounds cells are 0, not null/NaN). Fixtures
are written to pytest's tmp_path only; no submission file is created.
"""
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

from gems79.portal_spec import (DEFAULT_TEMPLATE, RULES, make_example_like,
                                validate_portal_file)

ROOT = Path(__file__).resolve().parents[1]
THVC = ROOT / 'docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif'


def _failed(path):
    rep = validate_portal_file(path, DEFAULT_TEMPLATE)
    return rep, set(rep['failed_rules'])


def _inside_cell(k=0):
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        return tuple(np.argwhere(~np.isnan(ref.read(1)))[k])


def _interior_values(rng_seed=0):
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        shape = ref.shape
    rng = np.random.default_rng(rng_seed)
    return rng.random(shape, dtype=np.float32)


def test_official_template_passes_every_rule():
    rep, failed = _failed(DEFAULT_TEMPLATE)
    assert rep['ok'] is True and failed == set()
    assert [r['rule'] for r in rep['rules']] == sorted(RULES)
    assert rep['cells']['outside_cells'] == 7111787
    assert rep['cells']['inside_cells'] == 5167373


def test_project_zero_filled_research_tif_fails_only_r6():
    rep, failed = _failed(THVC)
    assert rep['ok'] is False
    assert failed == {'R6'}, 'the only spec deviation should be zero fill outside the bounds'
    assert rep['cells']['inside_out_of_range'] == 0 and rep['cells']['inside_nonfinite'] == 0
    assert rep['cells']['outside_non_nan'] == 7111787


def test_same_interior_with_nan_exterior_passes(tmp_path):
    with rasterio.open(THVC) as src:
        thvc = src.read(1)
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        inside = ~np.isnan(ref.read(1))
    values = np.where(inside, thvc, np.nan).astype(np.float32)
    out = make_example_like(DEFAULT_TEMPLATE, values, tmp_path / 'nan_exterior.tif')
    rep, failed = _failed(out)
    assert failed == set() and rep['ok'] is True


def test_value_above_one_fails_r8(tmp_path):
    vals = _interior_values()
    vals[_inside_cell(5)] = np.float32(1.0000001)
    _, failed = _failed(make_example_like(DEFAULT_TEMPLATE, vals, tmp_path / 'hi.tif'))
    assert failed == {'R8'}


def test_negative_value_fails_r8(tmp_path):
    vals = _interior_values()
    vals[_inside_cell(7)] = np.float32(-0.5)
    _, failed = _failed(make_example_like(DEFAULT_TEMPLATE, vals, tmp_path / 'neg.tif'))
    assert failed == {'R8'}


def test_nan_inside_footprint_fails_r7(tmp_path):
    vals = _interior_values()
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        inside = np.argwhere(~np.isnan(ref.read(1)))
    r, c = inside[0]
    vals[r, c] = np.nan
    _, failed = _failed(make_example_like(DEFAULT_TEMPLATE, vals, tmp_path / 'nan_in.tif'))
    assert 'R7' in failed


def test_inf_inside_footprint_fails_r7(tmp_path):
    vals = _interior_values()
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        inside = np.argwhere(~np.isnan(ref.read(1)))
    r, c = inside[0]
    vals[r, c] = np.inf
    _, failed = _failed(make_example_like(DEFAULT_TEMPLATE, vals, tmp_path / 'inf_in.tif'))
    assert 'R7' in failed


def test_wrong_datatype_fails_r2(tmp_path):
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        profile = ref.profile.copy()
        arr = ref.read(1).astype(np.float64)
    profile.update(dtype='float64')
    path = tmp_path / 'f64.tif'
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
    _, failed = _failed(path)
    assert failed == {'R2'}


def test_wrong_crs_fails_r3(tmp_path):
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        profile = ref.profile.copy()
        arr = ref.read(1)
    profile.update(crs='EPSG:4326')
    path = tmp_path / 'crs.tif'
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
    _, failed = _failed(path)
    assert failed == {'R3'}


def test_two_bands_fail_r1(tmp_path):
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        profile = ref.profile.copy()
        arr = ref.read(1)
    profile.update(count=2)
    path = tmp_path / 'two.tif'
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
        dst.write(arr, 2)
    _, failed = _failed(path)
    assert 'R1' in failed


def test_numeric_nodata_fails_r5(tmp_path):
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        profile = ref.profile.copy()
        arr = ref.read(1)
    profile.update(nodata=-9999.0)
    path = tmp_path / 'nd.tif'
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
    _, failed = _failed(path)
    assert failed == {'R5'}


def test_shifted_transform_fails_r4_and_marks_cell_rules_unevaluated(tmp_path):
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        profile = ref.profile.copy()
        arr = ref.read(1)
        tr = ref.transform
    profile.update(transform=tr @ tr.__class__.translation(100, 0))
    path = tmp_path / 'shift.tif'
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
    rep, failed = _failed(path)
    assert 'R4' in failed and {'R6', 'R7', 'R8'} <= failed
    assert rep['cells'] == {'compared': False}


def test_single_tif_zip_is_checked_and_two_member_zip_fails(tmp_path):
    vals = _interior_values()
    tif = make_example_like(DEFAULT_TEMPLATE, vals, tmp_path / 'ok.tif')
    good = tmp_path / 'good.zip'
    with zipfile.ZipFile(good, 'w') as z:
        z.write(tif, arcname='ok.tif')
    rep, failed = _failed(good)
    assert failed == set() and rep['inner_tif'] == 'ok.tif'

    bad = tmp_path / 'two.zip'
    with zipfile.ZipFile(bad, 'w') as z:
        z.write(tif, arcname='ok.tif')
        z.write(tif, arcname='copy.tif')
    _, failed = _failed(bad)
    assert 'R1' in failed


def test_not_a_raster_is_rejected(tmp_path):
    path = tmp_path / 'junk.tif'
    path.write_bytes(b'not a tiff')
    rep, failed = _failed(path)
    assert rep['ok'] is False and 'R1' in failed


def test_zipped_two_band_tiff_must_not_lose_inner_r1_failure(tmp_path):
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        profile, arr = ref.profile.copy(), ref.read(1)
    profile.update(count=2)
    tif = tmp_path / 'two_bands.tif'
    with rasterio.open(tif, 'w', **profile) as dst:
        dst.write(arr, 1)
        dst.write(arr, 2)
    archive = tmp_path / 'two_bands.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(tif, arcname=tif.name)
    report, failed = _failed(archive)
    assert not report['ok']
    assert failed == {'R1'}
    assert len(report['rules']) == len(RULES)
    assert '2 band(s)' in report['rules'][0]['detail']


def test_zip_with_unreadable_inner_tiff_returns_failed_report(tmp_path):
    archive = tmp_path / 'junk.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('junk.tif', b'not a raster')
    report, failed = _failed(archive)
    assert not report['ok'] and 'R1' in failed
    assert len(report['rules']) == len(RULES)


def test_missing_file_returns_failed_report(tmp_path):
    report, failed = _failed(tmp_path / 'missing.tif')
    assert not report['ok'] and 'R1' in failed
    assert report['sha256'] is None
    assert len(report['rules']) == len(RULES)


def test_non_geotiff_with_tif_extension_is_rejected(tmp_path):
    # GDAL auto-detects formats regardless of the filename suffix.
    path = tmp_path / 'actually_envi.tif'
    with rasterio.open(DEFAULT_TEMPLATE) as ref:
        profile, arr = ref.profile.copy(), ref.read(1)
    profile = {k: v for k, v in profile.items()
               if k not in {'blockxsize', 'blockysize', 'compress', 'interleave', 'tiled'}}
    profile.update(driver='ENVI')
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
    report, failed = _failed(path)
    assert not report['ok'] and 'R1' in failed


def test_corrupt_zip_returns_all_failed_rules(tmp_path):
    path = tmp_path / 'broken.zip'
    path.write_bytes(b'PK\x03\x04not an archive')
    report, failed = _failed(path)
    assert not report['ok'] and failed == set(RULES)
    assert report['error']['type'] == 'BadZipFile'


def test_missing_template_cannot_produce_partial_pass(tmp_path):
    report = validate_portal_file(DEFAULT_TEMPLATE, tmp_path / 'missing_template.tif')
    assert not report['ok']
    assert set(report['failed_rules']) == set(RULES)
    assert report['template_sha256'] is None


def test_cli_continues_after_missing_input_and_writes_strict_json(tmp_path):
    import json
    import subprocess
    import sys

    output = tmp_path / 'report.json'
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/validate_portal_spec.py'),
         str(tmp_path / 'missing.tif'), str(DEFAULT_TEMPLATE), '--json', str(output)],
        capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert 'Traceback' not in result.stderr
    reports = json.loads(output.read_text())
    assert len(reports) == 2
    assert not reports[0]['ok'] and reports[1]['ok']
    assert len(reports[0]['rules']) == len(RULES)


def test_zip_crc_error_is_a_refusal(tmp_path):
    archive = tmp_path / 'bad_crc.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as z:
        z.writestr('one.tif', b'payload_to_corrupt')
    payload = archive.read_bytes().replace(b'payload_to_corrupt', b'PAYLOAD_to_corrupt')
    archive.write_bytes(payload)
    report, failed = _failed(archive)
    assert not report['ok'] and failed == set(RULES)
    assert "CRC error 'one.tif'" in report['rules'][0]['detail']


@pytest.mark.parametrize('error_kind', ['truncated', 'deflate'])
def test_zip_decompression_errors_return_complete_refusal(tmp_path, monkeypatch, error_kind):
    import zlib

    archive = tmp_path / 'decompression_error.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('one.tif', b'placeholder')

    def broken_testzip(self):
        if error_kind == 'truncated':
            raise EOFError('truncated compressed stream')
        raise zlib.error('invalid compressed stream')

    monkeypatch.setattr(zipfile.ZipFile, 'testzip', broken_testzip)
    report, failed = _failed(archive)
    assert not report['ok'] and failed == set(RULES)
    assert report['validator_version'] == 'gems79-portal-format-v2'
