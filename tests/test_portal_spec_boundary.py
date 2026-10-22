"""Small software fixtures only: no scientific candidate or score is produced."""
import json
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems79.portal_spec import validate_portal_file


@pytest.fixture
def rasters(tmp_path):
    profile = dict(driver='GTiff', height=3, width=4, count=1, dtype='float32',
                   crs='EPSG:32611', transform=from_origin(243350, 4508550, 100, 100),
                   nodata=float('nan'))
    arr = np.zeros((3, 4), dtype=np.float32)
    arr[0, 0] = np.nan
    template = tmp_path / 'template.tif'
    with rasterio.open(template, 'w', **profile) as dst:
        dst.write(arr, 1)
    return template, profile, arr


def test_zip_does_not_discard_inner_multiband_failure(tmp_path, rasters):
    template, profile, arr = rasters
    profile['count'] = 2
    tif = tmp_path / 'two.tif'
    with rasterio.open(tif, 'w', **profile) as dst:
        dst.write(arr, 1)
        dst.write(arr, 2)
    archive = tmp_path / 'two.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.write(tif, 'two.tif')
    direct = validate_portal_file(tif, template)
    zipped = validate_portal_file(archive, template)
    assert direct['failed_rules'] == zipped['failed_rules'] == ['R1']
    assert not zipped['ok']
    assert len(zipped['rules']) == 8


def test_one_band_archive_still_passes(tmp_path, rasters):
    template, _, _ = rasters
    archive = tmp_path / 'ok.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.write(template, 'one.tif')
    result = validate_portal_file(archive, template)
    assert result['ok'] and len(result['rules']) == 8
    assert result['does_not_approve_submission'] is True


@pytest.mark.parametrize('kind', ['absent', 'corrupt_tif_member', 'missing_template'])
def test_inspection_failure_is_serializable_refusal(tmp_path, rasters, kind):
    template, _, _ = rasters
    candidate = tmp_path / 'absent.tif'
    if kind == 'corrupt_tif_member':
        candidate = tmp_path / 'bad.zip'
        with zipfile.ZipFile(candidate, 'w') as z:
            z.writestr('bad.tif', b'not a raster')
    elif kind == 'missing_template':
        candidate, template = template, candidate
    result = validate_portal_file(candidate, template)
    assert result['ok'] is False
    assert result['does_not_approve_submission'] is True
    assert result['inspection_error']['type']
    assert str(tmp_path) not in json.dumps(result, allow_nan=False)


def test_renamed_vrt_is_not_a_geotiff(tmp_path, rasters):
    template, _, _ = rasters
    from rasterio.shutil import copy
    candidate = tmp_path / 'disguised.tif'
    copy(template, candidate, driver='VRT')
    result = validate_portal_file(candidate, template)
    assert not result['ok'] and 'R1' in result['failed_rules']
