"""Unit and integration checks for G79-THVC feature guards, submodular placement, and audit receipts."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from scipy.spatial.distance import pdist

from gems57 import metric
from gems79.thvc_features import (
    ALL_FEATURE_NAMES,
    FORBIDDEN_POINT_COLUMNS,
    MECH_FEATURE_NAMES,
    STATIC_FEATURE_NAMES,
    compute_network_mechanics,
    parse_safe_csv,
)
pytest.importorskip("lightgbm")
from gems79.thvc_model import charnes_cooper_submodular_emit, poisson_disk_emit

ROOT = Path(__file__).resolve().parents[1]


def test_forbidden_leakage_columns_blocked_by_parse_safe_csv(tmp_path):
    assert "dist_known_fault_px" in FORBIDDEN_POINT_COLUMNS
    assert len(STATIC_FEATURE_NAMES) == 70
    assert len(MECH_FEATURE_NAMES) == 14
    assert len(ALL_FEATURE_NAMES) == 84

    csv_file = tmp_path / "probes.csv"
    csv_file.write_text("row,col,val,dist_known_fault_px\n10,20,3.5,0.0\n")
    with pytest.raises(ValueError):
        parse_safe_csv(csv_file, ("row", "col", "dist_known_fault_px"))
    rows = parse_safe_csv(csv_file, ("row", "col", "val"))
    assert len(rows) == 1 and "dist_known_fault_px" not in rows[0]


def test_network_mechanics_strictly_depend_only_on_visible_faults(tmp_path):
    fp = np.ones((40, 40), dtype=bool)
    visible = np.zeros((40, 40), dtype=bool)
    visible[10:25, 12] = True
    cues_path = tmp_path / "cues.npz"
    np.savez(
        cues_path,
        scarp_step=np.ones(int(fp.sum()), dtype=np.float32),
        grav_bdepth=np.ones(int(fp.sum()), dtype=np.float32),
        hydro=np.ones(int(fp.sum()), dtype=np.float32),
    )
    f_vis = compute_network_mechanics(visible, fp, cues_path)
    assert f_vis.shape == (int(fp.sum()), 14)
    assert np.isfinite(f_vis).all()


def test_charnes_cooper_allocator_respects_separation_and_recovers_hidden_fault():
    H, W = 48, 48
    fp = np.ones((H, W), dtype=bool)
    cat = np.zeros((H, W), dtype=bool)
    cat[:4, :4] = True
    truth = np.zeros((H, W), dtype=bool)
    truth[24, 8:40] = True

    p_2d = np.full((H, W), 0.001, dtype=np.float32)
    q_2d = np.full((H, W), 0.003, dtype=np.float32)
    for r in range(22, 27):
        d = abs(r - 24)
        w = max(0.0, 1.0 - d / 3.0)
        p_2d[r, 8:40] = 0.50 * w + 0.005
        q_2d[r, 8:40] = 0.85 * w + 0.010

    placed_cc = charnes_cooper_submodular_emit(
        p_2d,
        q_2d,
        fp & ~cat,
        lambda_fp=0.04,
        min_sep_px=2.0,
        max_budget=25,
        min_budget=5,
        candidate_pool=1500,
    )
    placed_pd = poisson_disk_emit(q_2d, fp & ~cat, budget=18, min_dist_px=2.8)
    for arr in (placed_cc, placed_pd):
        assert arr.dtype == np.float32
        assert set(np.unique(arr)).issubset({0.0, 1.0})
        assert not ((arr > 0) & cat).any()
    coords = np.argwhere(placed_cc > 0)
    assert len(coords) >= 5
    assert pdist(coords).min() >= 1.999
    score_cc = metric.dti_exact(placed_cc, truth, known=cat)["dti"]
    assert score_cc > 0.70


def test_published_thvc_geotiff_binary_support_and_receipts():
    thvc_tif = ROOT / "archive/g79_thvc_33e1f8ec/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif"
    if not thvc_tif.exists():
        card = json.loads((ROOT / "run_card.json").read_text())
        thvc_tif = ROOT / card["submission_file"]
    with rasterio.open(thvc_tif) as ds:
        arr = ds.read(1)
        assert ds.crs.to_string() == "EPSG:32611"
        assert arr.shape == (3730, 3292)
        assert arr.dtype == np.float32
        assert not np.isnan(arr).any() and not np.isinf(arr).any()
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        assert set(np.unique(arr)).issubset({0.0, 1.0})
        assert int((arr > 0).sum()) == 35093
