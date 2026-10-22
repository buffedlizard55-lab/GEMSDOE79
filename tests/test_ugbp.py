"""G79-UGBP frozen-recipe unit tests (no holdout, no raster downloads)."""
import numpy as np

from gems79.ugbp import classify, emit_dotted


def _site(tq, tcat, tout, row=10, col=10):
    return {"row": row, "col": col, "tq": tq, "tc": np.nan,
            "tcat": tcat, "tout": tout}


def test_classify_frozen_thresholds():
    sites = [
        _site(166.0, 209.0, 77.0),    # distal: d1=43, drop=89, Tcat>=110
        _site(120.0, 118.0, 90.0),    # proximal: d1=-2 in [-40,15], Tq>=100
        _site(60.0, 200.0, 30.0),     # neither: Tq too cold / drop gate on distal fails Tq? drop=30<40
        _site(np.nan, 200.0, 30.0),   # missing quartz: skipped
    ]
    prox, distal, info = classify(sites)
    assert info["sites_total"] == 4
    assert len(distal) == 1 and distal[0]["w"] > 0
    assert len(prox) == 1 and prox[0]["w"] > 0


def test_emit_separation_and_exclusion():
    fp = np.ones((60, 60), bool)
    visible = np.zeros((60, 60), bool)
    visible[30, :] = True
    rng = np.random.default_rng(0)
    score = rng.random((60, 60)).astype(np.float32)
    dots = emit_dotted(score, visible, fp, budget=50, min_sep=2.8)
    assert 0 < dots.sum() <= 50
    from scipy import ndimage as ndi
    assert ndi.distance_transform_edt(~visible)[dots].min() > 2.0
    ys, xs = np.nonzero(dots)
    for i in range(len(ys)):
        d2 = (ys[i + 1:] - ys[i]) ** 2 + (xs[i + 1:] - xs[i]) ** 2
        assert (d2 >= 2.8 ** 2 - 1e-9).all()
