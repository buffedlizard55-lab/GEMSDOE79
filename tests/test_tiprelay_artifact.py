import json, hashlib
from pathlib import Path
import numpy as np, rasterio
ROOT=Path(__file__).resolve().parents[1]
NAME="gemsdoe79-tiprelay-e1-35963-20261022-zeros.tif"
def test_tiprelay_format_and_negative_verdict():
    p=ROOT/"submissions"/NAME
    with rasterio.open(p) as s:
        a=s.read(1); assert s.count==1 and str(s.crs)=="EPSG:32611" and a.shape==(3730,3292)
    assert set(np.unique(a))<= {0.0,1.0} and np.isfinite(a).all()
    card=json.loads((ROOT/"evidence"/"tiprelay_run_card.json").read_text())
    assert card["verdict"]=="negative" and card["ok_to_submit"] is False
    assert card["raster_sha256"]==hashlib.sha256(p.read_bytes()).hexdigest()
    assert len(card["submission_note"])<=140
    exp=json.loads((ROOT/"evidence"/"tiprelay_experiment.json").read_text())
    assert exp["pooled"]["scores"]["tiprelay"]["dti"] < 0.1827  # did not beat H79 best
