"""Local, fail-closed checks of the published GEMS submission-format text.

R1--R8 are transcribed from the DrivenData problem page and calibrated against
our pinned sample. This is NOT the organizer's validator or an acceptance
receipt. In particular R6 conservatively requires the sample's NaN exterior;
it does not establish why an earlier, unavailable upload was rejected.

All ordinary inspection failures return a complete negative report. ZIP
packaging and the contained raster must BOTH meet R1. No prediction is repaired,
clipped, regenerated, or approved for a submission slot here.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = ROOT / 'data' / 'reference' / 'sample_submission.tif'
PINNED_TEMPLATE_SHA256 = '2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc'
VALIDATOR_VERSION = 'gems79-official-text-format-v2'
OFFICIAL_CRS = 'EPSG:32611'
OFFICIAL_RES = 100.0
OFFICIAL_PAGE = 'https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/'
# An operational inspection bound, NOT an organizer file-size rule. The pinned
# uncompressed float32 grid is about 49 MB. Do not inflate arbitrary ZIP bombs.
MAX_INSPECTION_BYTES = 512 * 1024 * 1024

RULES = {
    'R1': 'single GeoTIFF layer (ZIP: exactly one TIFF file with one band)',
    'R2': 'datatype float32',
    'R3': 'CRS EPSG:32611',
    'R4': 'shape, transform, 100 m resolution and bounds equal the template',
    'R5': 'nodata absent or NaN',
    'R6': 'data outside the footprint is null or NaN (sample-mask interpretation)',
    'R7': 'every in-footprint cell is finite and valid (no NaN, inf or masked data)',
    'R8': 'every in-footprint value is between 0 and 1 inclusive',
}


def _rel(path) -> str:
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _check(results, rule, ok, detail):
    """Conjoin subchecks of one rule; a wrapper must not erase an inner FAIL."""
    for row in results:
        if row['rule'] == rule:
            row['pass'] = row['pass'] is True and bool(ok)
            row['detail'] += '; ' + detail
            return
    results.append({'rule': rule, 'text': RULES[rule], 'pass': bool(ok), 'detail': detail})


def _load_template(template):
    # A competition GeoTIFF must carry its own grid. Do not let a local PAM
    # sidecar/world file repair metadata that would be absent in an upload.
    with rasterio.Env(GDAL_PAM_ENABLED=False), rasterio.open(template, GEOREF_SOURCES='INTERNAL') as ref:
        self_contained = all(Path(f).resolve() == Path(template).resolve() for f in ref.files)
        if (not self_contained or ref.width * ref.height * 4 > MAX_INSPECTION_BYTES
                or ref.driver != 'GTiff' or ref.count != 1 or ref.dtypes != ('float32',)
                or ref.crs is None or ref.crs.to_epsg() != 32611
                or ref.res != (OFFICIAL_RES, OFFICIAL_RES)
                or ref.transform.a != OFFICIAL_RES or ref.transform.e != -OFFICIAL_RES
                or ref.transform.b != 0 or ref.transform.d != 0):
            raise ValueError('invalid reference grid')
        values = ref.read(1, masked=False)
        inside = np.isfinite(values)
        if (not inside.any() or np.isinf(values).any()
                or not np.all((values[inside] >= 0) & (values[inside] <= 1))
                or not np.all(ref.read_masks(1)[inside] > 0)):
            raise ValueError('invalid reference footprint')
        return inside, ref.shape, tuple(ref.transform)[:6], tuple(ref.bounds)


def _validate_tif(path: Path, reference, out: dict) -> None:
    results = out['rules']
    inside, ref_shape, ref_tr, ref_bounds = reference
    with rasterio.Env(GDAL_PAM_ENABLED=False), rasterio.open(path, GEOREF_SOURCES='INTERNAL') as src:
        is_tiff = src.driver == 'GTiff'
        self_contained = all(Path(f).resolve() == Path(path).resolve() for f in src.files)
        _check(results, 'R1', is_tiff and src.count == 1 and self_contained,
               f'driver {src.driver}; {src.count} band(s); self-contained {self_contained}')
        _check(results, 'R2', bool(src.dtypes) and all(d == 'float32' for d in src.dtypes),
               f'dtype(s) {src.dtypes}')
        _check(results, 'R3', src.crs is not None and src.crs.to_epsg() == 32611,
               f'CRS {src.crs}')
        tr = tuple(src.transform)[:6]
        geom_ok = (src.shape == ref_shape and tr == ref_tr
                   and src.res == (OFFICIAL_RES, OFFICIAL_RES)
                   and tuple(src.bounds) == ref_bounds)
        _check(results, 'R4', geom_ok,
               f'shape {src.shape} vs {ref_shape}; transform match {tr == ref_tr}; '
               f'res {src.res}; bounds match {tuple(src.bounds) == ref_bounds}')
        nd = src.nodata
        _check(results, 'R5', nd is None or bool(np.isnan(nd)), f'nodata {nd!r}')
        # Do not read a disguised VRT or another driver through this TIFF API.
        if not (geom_ok and is_tiff and src.count > 0):
            return
        arr = src.read(1, masked=False)
        validity = src.read_masks(1) > 0

    outside = ~inside
    outside_bad = int(np.count_nonzero(~np.isnan(arr[outside])))
    _check(results, 'R6', outside_bad == 0,
           f'{outside_bad} non-NaN exterior cell(s) of {int(outside.sum())}')
    vals = arr[inside]
    nonfinite = int(np.count_nonzero(~np.isfinite(vals)))
    invalid = int(np.count_nonzero(~validity[inside]))
    _check(results, 'R7', nonfinite == 0 and invalid == 0,
           f'{nonfinite} NaN/inf and {invalid} masked cell(s) inside the footprint')
    finite = vals[np.isfinite(vals)]
    oor = int(np.count_nonzero((finite < 0) | (finite > 1)))
    lo = float(finite.min()) if finite.size else None
    hi = float(finite.max()) if finite.size else None
    _check(results, 'R8', oor == 0 and finite.size == vals.size,
           f'{oor} value(s) outside [0,1] inside footprint; min {lo}, max {hi}')
    out['cells'] = {
        'compared': True,
        'inside_cells': int(inside.sum()),
        'outside_cells': int(outside.sum()),
        'outside_non_nan': outside_bad,
        'inside_nonfinite': nonfinite,
        'inside_invalid_mask': invalid,
        'inside_out_of_range': oor,
        'inside_min': lo,
        'inside_max': hi,
        'inside_positive': int(np.count_nonzero(finite > 0)),
        'inside_mass': float(finite.astype(np.float64).sum()),
    }


def _safe_member(info) -> bool:
    name = info.filename
    parts = PurePosixPath(name).parts
    filetype = stat.S_IFMT(info.external_attr >> 16)
    return (not name.startswith('/') and '\\' not in name
            and not re.match(r'^[A-Za-z]:', name) and '..' not in parts
            and filetype in (0, stat.S_IFREG) and not (info.flag_bits & 1)
            and 0 < info.file_size <= MAX_INSPECTION_BYTES)


def _validate_zip(path, reference, out):
    with zipfile.ZipFile(path) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        valid = (len(members) == 1
                 and members[0].filename.lower().endswith(('.tif', '.tiff'))
                 and _safe_member(members[0]))
        _check(out['rules'], 'R1', valid,
               f'{len(members)} file member(s); safe, unencrypted single-TIFF packaging {valid}')
        if not valid:
            return
        info = members[0]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                extracted = Path(tmp) / 'prediction.tif'
                # ZipExtFile validates CRC while reading. Stream to disk, rather
                # than testzip()+read() inflating and allocating it twice.
                with archive.open(info) as source, extracted.open('wb') as target:
                    shutil.copyfileobj(source, target, length=1 << 20)
                if extracted.stat().st_size != info.file_size:
                    raise ValueError('ZIP member length changed during inspection')
                _validate_tif(extracted, reference, out)
        except Exception:
            _check(out['rules'], 'R1', False, 'contained TIFF/CRC inspection failed')
            raise
        out['inner_tif'] = info.filename


def _finalize(out):
    for rule in RULES:
        if not any(row['rule'] == rule for row in out['rules']):
            _check(out['rules'], rule, False, 'not evaluated: inspection or prerequisite failed')
    out['rules'].sort(key=lambda row: row['rule'])
    out['failed_rules'] = [row['rule'] for row in out['rules'] if row['pass'] is not True]
    out['ok'] = (not out['failed_rules'] and 'inspection_error' not in out
                 and out['bytes_stable_during_validation'] is True)
    return out


def validate_portal_file(path, template=DEFAULT_TEMPLATE) -> dict:
    """Return all eight rule decisions, including for corrupt or missing inputs.

    A custom template supports explicit diagnostic/test use only. Submission
    readiness additionally binds the result to the pinned reference SHA-256.
    No error message includes arbitrary exception text or private directory paths.
    """
    out = {
        'schema_version': 2, 'validator_version': VALIDATOR_VERSION,
        'validation_class': 'LOCAL-OFFICIAL-TEXT-FORMAT, NOT ORGANIZER ACCEPTANCE',
        'official_source': OFFICIAL_PAGE, 'rules': [], 'cells': {'compared': False},
        'file': None, 'sha256': None, 'bytes': None,
        'template': None, 'template_sha256': None,
        'bytes_stable_during_validation': False,
        'organizer_acceptance_established': False,
        'inspection_policy': {'max_file_or_zip_member_bytes': MAX_INSPECTION_BYTES,
                              'not_an_organizer_size_rule': True},
    }
    stage = 'resolve_input'
    try:
        path, template = Path(path), Path(template)
        out.update(file=_rel(path), template=_rel(template))
        stage = 'read_artifact'
        size = path.stat().st_size
        if not path.is_file() or not 0 < size <= MAX_INSPECTION_BYTES:
            raise ValueError('artifact exceeds inspection limits or is not a nonempty file')
        out.update(bytes=size, sha256=_sha256(path))
        stage = 'read_template'
        if not template.is_file() or not 0 < template.stat().st_size <= MAX_INSPECTION_BYTES:
            raise ValueError('reference exceeds inspection limits or is not a nonempty file')
        out['template_sha256'] = _sha256(template)
        if (template.resolve() == DEFAULT_TEMPLATE.resolve()
                and out['template_sha256'] != PINNED_TEMPLATE_SHA256):
            raise ValueError('pinned reference bytes differ')
        reference = _load_template(template)
        stage = 'inspect_artifact'
        if path.suffix.lower() == '.zip':
            _validate_zip(path, reference, out)
        elif path.suffix.lower() in ('.tif', '.tiff'):
            _validate_tif(path, reference, out)
        else:
            _check(out['rules'], 'R1', False, 'expected .tif, .tiff or .zip extension')
        stage = 'verify_stable_bytes'
        out['bytes_stable_during_validation'] = (
            path.stat().st_size == size and _sha256(path) == out['sha256']
            and _sha256(template) == out['template_sha256'])
        if not out['bytes_stable_during_validation']:
            raise ValueError('input changed during inspection')
    except Exception as exc:
        # CLI/library inspection boundary: never reuse stale PASS on an error.
        # Interrupts and process termination (BaseException) still propagate.
        out['inspection_error'] = {'stage': stage, 'type': type(exc).__name__}
    return _finalize(out)


def portal_report_passed(report, *, expected_sha256=None, expected_template_sha256=None):
    """Check a complete, byte-bound v2 report, not a self-reported PASS flag."""
    if not isinstance(report, dict):
        return False
    if (report.get('validator_version') != VALIDATOR_VERSION
            or report.get('ok') is not True or report.get('failed_rules') != []
            or report.get('bytes_stable_during_validation') is not True
            or 'inspection_error' in report):
        return False
    rows = report.get('rules')
    if (not isinstance(rows, list) or len(rows) != len(RULES)
            or any(not isinstance(row, dict) for row in rows)
            or any(sum(row.get('rule') == rule for row in rows) != 1 for rule in RULES)
            or any(row.get('pass') is not True for row in rows)):
        return False
    for field, expected in (('sha256', expected_sha256), ('template_sha256', expected_template_sha256)):
        actual = report.get(field)
        if (not isinstance(actual, str) or re.fullmatch(r'[0-9a-f]{64}', actual) is None
                or (expected is not None and actual != expected)):
            return False
    return True


def make_example_like(template, values, path):
    """Synthetic test helper only; not a scientific candidate generator."""
    template = Path(template)
    with rasterio.open(template) as ref:
        profile = ref.profile.copy()
        profile.update(dtype='float32', count=1, nodata=float('nan'), compress='lzw')
        tmpl = ref.read(1)
    arr = np.where(np.isnan(tmpl), np.nan, np.asarray(values, dtype=np.float32)).astype(np.float32)
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
    return Path(path)
