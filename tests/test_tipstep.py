import json, hashlib, zipfile
from pathlib import Path
import numpy as np, rasterio
ROOT=Path(__file__).resolve().parents[1]
TIF=ROOT/'artifacts/tipstep/gems79-tipstep-20261022-29259dots-zeros.tif'
def test_tipstep_unique_valid_negative():
    card=json.loads((ROOT/'run_card_tipstep.json').read_text())
    assert hashlib.sha256(TIF.read_bytes()).hexdigest()==card['raster']['sha256']=='4c36113dab6062fbcfc1ae142c8e33e01b81261f127aab545b76f8789ee55b4a'
    with rasterio.open(TIF) as d:
        a=d.read(1); assert d.count==1 and str(d.crs)=='EPSG:32611' and (d.height,d.width)==(3730,3292)
    assert np.isfinite(a).all() and a.min()>=0 and a.max()<=1 and int((a>0).sum())==29259
    assert card['ok_to_download'] is True and card['ok_to_submit'] is False and card['verdict']=='negative'
    assert card['holdout']['seed20']['dti']==0.0927 and len(card['submission_note'])<=140
    with zipfile.ZipFile(TIF.with_suffix('.zip')) as z: assert z.read(TIF.name)==TIF.read_bytes()
    nov=json.loads((ROOT/'evidence/tipstep_novelty_local.json').read_text())
    assert nov['sparse_dot_rasters']['duplicates']==[] and nov['sparse_dot_rasters']['max_overlap']<0.70


def test_tipstep_portal_and_control_limitations_are_explicit():
    from gems79.portal_spec import validate_portal_file
    card = json.loads((ROOT / 'run_card_tipstep.json').read_text())
    report = validate_portal_file(TIF)
    assert report['failed_rules'] == ['R6']
    assert 'undiagnosed' in card['validator']['outside_footprint']
    assert 'not comparable' in card['verdict_reason']
    assert any('UNIFORM control' in item for item in card['audit_limitations'])
    assert card['ok_to_submit'] is False and card['verdict'] == 'negative'


def test_tipstep_page_is_generated_with_fifteen_page_contract():
    from build_site import tipstep_page
    page = tipstep_page()
    assert 'Byte-distinct research TIF. Do not submit.' in page
    assert 'FAIL R6' in page
    assert 'Uniform-control caveat' in page
    assert 'will NOT trigger' not in page
    assert 'NaN-outside exports fail the range check' not in page
