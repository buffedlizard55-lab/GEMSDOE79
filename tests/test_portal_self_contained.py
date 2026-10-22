"""Bound standalone GeoTIFF bytes, not unshipped local GDAL sidecars."""
from pathlib import Path
import os
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems79 import portal_spec as portal


@pytest.fixture
def small(tmp_path):
    profile = dict(driver='GTiff', width=5, height=4, count=1, dtype='float32',
                   crs='EPSG:32611', transform=from_origin(243350, 4508550, 100, 100),
                   nodata=float('nan'))
    values = np.zeros((4, 5), np.float32)
    values[0] = np.nan
    template = tmp_path / 'reference.tif'
    with rasterio.open(template, 'w', **profile) as dst:
        dst.write(values, 1)
    return template, profile, values


def test_pam_sidecar_cannot_repair_missing_embedded_crs(tmp_path, small):
    template, profile, values = small
    path = tmp_path / 'missing-crs.tif'
    with rasterio.open(path, 'w', **{**profile, 'crs': None}) as dst:
        dst.write(values, 1)
    # GDAL normally honors this local repair, but the TIFF alone does not carry
    # it. These bytes must not receive a submission-format PASS.
    Path(str(path) + '.aux.xml').write_text(
        '<PAMDataset><SRS>EPSG:32611</SRS></PAMDataset>')
    with rasterio.Env(GDAL_PAM_ENABLED=True), rasterio.open(path) as src:
        assert src.crs.to_epsg() == 32611
    report = portal.validate_portal_file(path, template)
    assert report['ok'] is False
    assert 'R3' in report['failed_rules']
    assert report['bytes_stable_during_validation'] is True


def test_external_mask_is_not_part_of_standalone_tiff(tmp_path, small):
    template, profile, values = small
    path = tmp_path / 'external-mask.tif'
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(path, 'w', **profile) as dst:
            dst.write(values, 1)
            mask = np.full(values.shape, 255, np.uint8)
            mask[1, 1] = 0
            dst.write_mask(mask)
    assert Path(str(path) + '.msk').is_file()
    report = portal.validate_portal_file(path, template)
    assert report['ok'] is False
    assert {'R1', 'R7'} <= set(report['failed_rules'])


@pytest.mark.parametrize('kind', ['empty', 'directory', 'fifo'])
def test_template_must_be_nonempty_regular_file_without_blocking(tmp_path, small, kind):
    template, _, _ = small
    bad = tmp_path / 'bad-reference.tif'
    if kind == 'empty':
        bad.touch()
    elif kind == 'directory':
        bad.mkdir()
    else:
        os.mkfifo(bad)
    report = portal.validate_portal_file(template, bad)
    assert report['ok'] is False
    assert report['inspection_error']['stage'] == 'read_template'
    assert report['failed_rules'] == list(portal.RULES)


def test_compressed_template_cannot_hide_unbounded_decoded_grid(tmp_path, small, monkeypatch):
    template, profile, _ = small
    huge = tmp_path / 'oversize-decoded-reference.tif'
    with rasterio.open(huge, 'w', **{**profile, 'width': 1000, 'height': 1000,
                                   'compress': 'lzw'}) as dst:
        dst.write(np.zeros((1000, 1000), np.float32), 1)
    cap = 2 * 1024 * 1024
    assert huge.stat().st_size < cap < 4 * 1000 * 1000
    monkeypatch.setattr(portal, 'MAX_INSPECTION_BYTES', cap)
    report = portal.validate_portal_file(template, huge)
    assert report['ok'] is False
    assert report['inspection_error']['stage'] == 'read_template'
    assert report['failed_rules'] == list(portal.RULES)
