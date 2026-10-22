"""Offline validator for the OFFICIAL GEMS submission format, rule by rule.

Rules are transcribed from the DrivenData problem page (Submission format
section) and checked against the official template ``sample_submission.tif``:

  R1  one GeoTIFF layer (a ZIP must contain exactly one .tif member)
  R2  datatype float32
  R3  CRS EPSG:32611
  R4  same shape, transform, resolution (100 m) and bounds as the template
  R5  nodata is absent or NaN (the template uses NaN)
  R6  data outside the bounds is null or NaN  -> every template-NaN cell is NaN
  R7  every cell inside the bounds is a finite number (no NaN, no inf)
  R8  every value inside the bounds is between 0 and 1 (inclusive)

A PASS here is a local format statement only. It does not establish organizer
acceptance, uniqueness, novelty or a slot. The portal's own message is not
reproduced by this module; see ``docs/executive-summary.html`` for the
unverified-cause note.
"""
from __future__ import annotations

import hashlib
import tempfile
import zipfile
import zlib
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = ROOT / 'data' / 'reference' / 'sample_submission.tif'
OFFICIAL_CRS = 'EPSG:32611'
OFFICIAL_RES = 100.0
VALIDATOR_VERSION = 'gems79-portal-format-v2'
OFFICIAL_PAGE = 'https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/'

RULES = {
    'R1': 'single GeoTIFF layer (ZIP: exactly one .tif member)',
    'R2': 'datatype float32',
    'R3': 'CRS EPSG:32611',
    'R4': 'shape, transform, 100 m resolution and bounds equal the template',
    'R5': 'nodata absent or NaN',
    'R6': 'data outside the bounds is null or NaN',
    'R7': 'every in-bounds cell is finite (no NaN, no inf)',
    'R8': 'every in-bounds value is between 0 and 1 inclusive',
}


def _rel(path) -> str:
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.name


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _check(results, rule, ok, detail):
    results.append({'rule': rule, 'text': RULES[rule], 'pass': bool(ok), 'detail': detail})


def _validate_tif(path: Path, template: Path, out: dict) -> None:
    results = out['rules']
    with rasterio.open(template) as ref:
        ref_arr = ref.read(1)
        ref_shape, ref_tr, ref_crs, ref_bounds = ref.shape, tuple(ref.transform)[:6], ref.crs, ref.bounds
    ref_outside = np.isnan(ref_arr)  # official template: NaN exterior
    ref_inside = ~ref_outside

    with rasterio.open(path) as src:
        _check(results, 'R1', src.driver == 'GTiff' and src.count == 1,
               f'driver {src.driver}; {src.count} band(s)')
        _check(results, 'R2', src.dtypes[0] == 'float32', f'dtype {src.dtypes[0]}')
        crs_ok = src.crs is not None and src.crs.to_string() == OFFICIAL_CRS
        _check(results, 'R3', crs_ok, f'CRS {src.crs}')
        tr = tuple(src.transform)[:6]
        geom_ok = (src.shape == ref_shape and tr == ref_tr and src.res == (OFFICIAL_RES, OFFICIAL_RES)
                   and tuple(src.bounds) == tuple(ref_bounds))
        _check(results, 'R4', geom_ok,
               f'shape {src.shape} vs {ref_shape}; transform match {tr == ref_tr}; res {src.res}; '
               f'bounds match {tuple(src.bounds) == tuple(ref_bounds)}')
        nd = src.nodata
        nd_ok = nd is None or (isinstance(nd, float) and np.isnan(nd))
        _check(results, 'R5', nd_ok, f'nodata {nd!r}')
        arr = src.read(1, masked=False) if geom_ok else None

    if arr is None:
        # Geometry mismatch: remaining per-cell rules are undefined; mark them failed.
        for rule in ('R6', 'R7', 'R8'):
            _check(results, rule, False, 'not evaluated: grid differs from template')
        out['cells'] = {'compared': False}
        return

    outside_bad = int((~np.isnan(arr[ref_outside])).sum())
    _check(results, 'R6', outside_bad == 0,
           f'{outside_bad} non-NaN cell(s) outside the template bounds (of {int(ref_outside.sum())})')
    inside_vals = arr[ref_inside]
    nonfinite = int((~np.isfinite(inside_vals)).sum())
    _check(results, 'R7', nonfinite == 0, f'{nonfinite} NaN/inf cell(s) inside the bounds')
    finite = inside_vals[np.isfinite(inside_vals)]
    oor = int(((finite < 0) | (finite > 1)).sum())
    lo = float(finite.min()) if finite.size else None
    hi = float(finite.max()) if finite.size else None
    _check(results, 'R8', oor == 0 and finite.size == inside_vals.size,
           f'{oor} value(s) outside [0,1] inside bounds; min {lo}, max {hi}')
    out['cells'] = {
        'compared': True,
        'inside_cells': int(ref_inside.sum()),
        'outside_cells': int(ref_outside.sum()),
        'outside_non_nan': outside_bad,
        'inside_nonfinite': nonfinite,
        'inside_out_of_range': oor,
        'inside_min': lo,
        'inside_max': hi,
        'inside_positive': int((finite > 0).sum()),
        'inside_mass': float(finite.astype(np.float64).sum()),
    }


def validate_portal_file(path, template=DEFAULT_TEMPLATE) -> dict:
    """Validate a .tif or a single-TIFF .zip against the official rules."""
    path, template = Path(path), Path(template)
    out = {'validator_version': VALIDATOR_VERSION,
           'file': _rel(path), 'sha256': None, 'bytes': None,
           'template': _rel(template), 'template_sha256': None,
           'official_source': OFFICIAL_PAGE, 'rules': [], 'cells': {'compared': False}}
    try:
        out['sha256'] = _sha256(path)
        out['bytes'] = path.stat().st_size
        out['template_sha256'] = _sha256(template)
        if path.suffix.lower() == '.zip':
            with zipfile.ZipFile(path) as z:
                bad = z.testzip()
                members = [i for i in z.infolist() if not i.is_dir()]
                names = [i.filename for i in members]
                tifs = [n for n in names if n.lower().endswith(('.tif', '.tiff'))]
                zip_detail = f'zip members {names}; CRC error {bad!r}'
                _check(out['rules'], 'R1', bad is None and len(names) == 1 and len(tifs) == 1,
                       zip_detail)
                if out['rules'][0]['pass']:
                    # Keep the container and raster checks separate until both
                    # finish. Dropping the inner R1 would approve multi-band ZIPs.
                    inner = {'rules': [], 'cells': {'compared': False}}
                    with tempfile.TemporaryDirectory() as tmp:
                        extracted = Path(tmp) / Path(tifs[0]).name
                        extracted.write_bytes(z.read(tifs[0]))
                        _validate_tif(extracted, template, inner)
                    inner_r1 = inner['rules'][0]
                    out['rules'][0]['pass'] = inner_r1['pass']
                    out['rules'][0]['detail'] = zip_detail + '; ' + inner_r1['detail']
                    out['rules'].extend(inner['rules'][1:])
                    out['cells'] = inner['cells']
                    out['inner_tif'] = tifs[0]
        else:
            _validate_tif(path, template, out)
    except (OSError, zipfile.BadZipFile, rasterio.errors.RasterioIOError,
            NotImplementedError, RuntimeError, EOFError, zlib.error) as exc:
        # Invalid/missing inputs and unsupported/encrypted ZIPs are refusals,
        # not tracebacks or partial PASS results. Never authorize a submission.
        out['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
        existing_r1 = next((r for r in out['rules'] if r['rule'] == 'R1'), None)
        if existing_r1 is None:
            _check(out['rules'], 'R1', False, f'cannot inspect input/template: {exc}')
        else:
            existing_r1.update({'pass': False, 'detail': f'cannot inspect archive/raster: {exc}'})
    # Every outcome has exactly one result per rule. Uninspected rules fail
    # closed, including malformed ZIPs and mismatched/absent input files.
    checked = {r['rule'] for r in out['rules']}
    for rule in RULES:
        if rule not in checked:
            _check(out['rules'], rule, False, 'not evaluated: input/template could not be inspected')
    out['rules'].sort(key=lambda r: r['rule'])
    out['failed_rules'] = [r['rule'] for r in out['rules'] if not r['pass']]
    out['ok'] = bool(out['rules']) and not out['failed_rules'] and len(out['rules']) == len(RULES)
    return out


def make_example_like(template, values, path):
    """Write a float32 GeoTIFF on the template grid: NaN outside, ``values`` inside.

    Test helper only; it is not a candidate generator and writes no submission.
    """
    template = Path(template)
    with rasterio.open(template) as ref:
        profile = ref.profile.copy()
        profile.update(dtype='float32', count=1, nodata=float('nan'), compress='lzw')
        tmpl = ref.read(1)
    arr = np.where(np.isnan(tmpl), np.nan, np.asarray(values, dtype=np.float32)).astype(np.float32)
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
    return Path(path)
