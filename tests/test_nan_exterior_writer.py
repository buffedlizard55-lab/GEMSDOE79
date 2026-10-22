"""Synthetic software fixtures only: no geological model or submission candidate."""
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

from gems57 import grid, gates
from gems57.submission_writer import write_submission
from gems57.validate import validate
from gems79.portal_spec import validate_portal_file

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/reference/sample_submission.tif'


@pytest.fixture(scope='module')
def arrays():
    with rasterio.open(SAMPLE) as src:
        fp = np.isfinite(src.read(1))
    p = np.zeros(fp.shape, dtype=np.float32)
    p[tuple(np.argwhere(fp)[0])] = .75
    return fp, p


def test_nan_export_roundtrip_passes_both_validators(tmp_path, arrays):
    fp, p = arrays
    path = tmp_path / 'synthetic-software-test.tif'
    receipt = write_submission(path, p, SAMPLE, fp, name='software fixture',
                               note='NOT A SCIENTIFIC CANDIDATE', exterior='nan')
    assert receipt['exterior_encoding'] == 'nan'
    assert receipt['approved_for_weekly_slot'] is False
    assert receipt['validator']['all_checks_passed']
    json.dumps(receipt, allow_nan=False)
    for file in (path, path.with_suffix('.zip')):
        assert validate_portal_file(file, SAMPLE)['ok']
    with rasterio.open(path) as src:
        a = src.read(1)
    assert np.isnan(a[~fp]).all()
    assert np.array_equal(a[fp], p[fp])
    assert np.isfinite(p).all()  # caller's buffer untouched
    with zipfile.ZipFile(path.with_suffix('.zip')) as z:
        assert z.namelist() == [path.name]
        assert z.read(path.name) == path.read_bytes()
    assert not validate(path, fp)['all_checks_passed']  # default legacy policy unchanged
    with pytest.raises(FileExistsError):
        write_submission(path, p, SAMPLE, fp, name='fixture', note='fixture', exterior='nan')


@pytest.mark.parametrize('bad', [-.001, 1.001, np.nan, np.inf, -np.inf, 1+2j])
def test_nan_mode_does_not_repair_invalid_predictions(tmp_path, bad):
    p = np.zeros((3, 3), dtype=np.complex64 if isinstance(bad, complex) else np.float32)
    p[1, 1] = bad
    with pytest.raises(ValueError):
        write_submission(tmp_path/'bad.tif', p, SAMPLE, np.ones(p.shape, bool),
                         name='test', note='test', exterior='nan')
    assert not list(tmp_path.iterdir())


def test_nan_mode_requires_exact_template_footprint(tmp_path, arrays):
    fp, p = arrays
    wrong = fp.copy()
    wrong.flat[0] = ~wrong.flat[0]
    with pytest.raises(ValueError, match='footprint'):
        write_submission(tmp_path/'bad.tif', p, SAMPLE, wrong,
                         name='test', note='test', exterior='nan')
    assert not list(tmp_path.iterdir())


def test_grid_nan_mode_rejects_zero_exterior_and_nonfinite_interior(tmp_path, arrays):
    fp, p = arrays
    with pytest.raises(ValueError, match='finite interior'):
        grid.write_geotiff(tmp_path/'bad.tif', p, nan_footprint=fp)
    a = p.copy()
    a[~fp] = np.nan
    a[tuple(np.argwhere(fp)[0])] = np.nan
    with pytest.raises(ValueError, match='finite interior'):
        grid.write_geotiff(tmp_path/'bad.tif', a, nan_footprint=fp)
    assert not list(tmp_path.iterdir())


def test_unknown_mode_and_missing_mask_fail_closed(tmp_path, arrays):
    fp, p = arrays
    with pytest.raises(ValueError):
        write_submission(tmp_path/'bad.tif', p, SAMPLE, fp, name='test', note='test', exterior='auto')
    with pytest.raises(ValueError):
        validate(SAMPLE, exterior='nan')
    with pytest.raises(ValueError):
        gates.format_report(SAMPLE, SAMPLE, exterior='nan')
