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
