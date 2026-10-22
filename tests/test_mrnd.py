"""Unit and evidence-integrity tests for H79-MRND (Experiment M1)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from gems79 import mrnd

ROOT = Path(__file__).resolve().parents[1]


def test_lidar_decode_sqrt_and_linear_match_metadata_spec():
    q = np.array([0, 1, 128, 255], dtype=np.uint8)
    s = mrnd.decode_lidar_band(q, xmax=1.5, mode="sqrt")
    assert np.isnan(s[0])
    assert s[1] == pytest.approx(0.0)
    assert s[2] == pytest.approx(1.5 * ((127.0 / 254.0) ** 2), rel=1e-5)
    assert s[3] == pytest.approx(1.5, rel=1e-5)

    lin = mrnd.decode_lidar_band(q, xmax=180.0, mode="linear")
    assert np.isnan(lin[0])
    assert lin[1] == pytest.approx(0.0)
    assert lin[2] == pytest.approx(180.0 * (127.0 / 254.0), rel=1e-5)
    assert lin[3] == pytest.approx(180.0, rel=1e-5)


def test_scarp_vs_channel_separates_normal_scarp_from_drainage_bank():
    up = np.array([[0.8, 0.05]], dtype=np.float32)
    dn = np.array([[0.2, 0.05]], dtype=np.float32)
    cr = np.array([[0.05, 0.8]], dtype=np.float32)
    idx = mrnd.scarp_vs_channel_index(up, dn, cr)
    assert idx[0, 0] > 0.8
    assert idx[0, 1] < -0.8


def test_hydrothermal_csv_ingest_drops_known_fault_distance_column(tmp_path):
    ws = tmp_path / "ws.csv"
    ws.write_text(
        "layer,name,thermalclass,row,col,utm_x,utm_y,dist_known_fault_px,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c\n"
        "springs,HotA,Hot ,10,12,0,0,0.0,85.0,145.0,120.0,130.0\n"
        "wells,ColdB,Cold,30,35,0,0,0.0,14.0,35.0,,\n",
        encoding="utf-8",
    )
    vv = tmp_path / "vv.csv"
    vv.write_text(
        "name,rock_type,age,row,col,dist_known_fault_px\n"
        "Dome1,rhyolite,Quaternary,20,22,0.0\n",
        encoding="utf-8",
    )
    fp = np.ones((48, 48), dtype=bool)
    out = mrnd.rasterize_hydrothermal_features(ws, vv, (48, 48), fp)
    assert out["hydro_temp_plume_s6"][10, 12] > out["hydro_temp_plume_s6"][30, 35] * 10.0
    assert out["hydro_geotherm_s8"][10, 12] > 0.0
    assert out["log_dist_thermal_spring"][10, 12] == pytest.approx(0.0)
    assert out["log_dist_volcanic_vent"][20, 22] == pytest.approx(0.0)


@pytest.mark.parametrize("orientation", ["horizontal", "vertical", "diagonal"])
def test_crack_tip_cone_projects_along_fault_strike(orientation):
    vis = np.zeros((81, 81), dtype=bool)
    if orientation == "horizontal":
        vis[40, 20:41] = True
        ahead, side = (40, 48), (48, 40)
    elif orientation == "vertical":
        vis[20:41, 40] = True
        ahead, side = (48, 40), (40, 48)
    else:
        for k in range(20, 41):
            vis[k, k] = True
        ahead, side = (47, 47), (33, 47)
    fp = np.ones_like(vis)
    nan_field = np.full(vis.shape, np.nan, dtype=np.float32)
    geom = mrnd.geometry_features(vis, fp, nan_field, nan_field)
    cone = geom["tip_propagation_cone"]
    assert cone[ahead] > cone[side] * 3.0


def test_calibrate_regime_surface_enforces_exact_pre_nms_shares():
    shape = (100, 100)
    allowed = np.ones(shape, dtype=bool)
    reg = np.zeros(shape, dtype=np.int8)
    reg[:, 33:67] = 1
    reg[:, 67:] = 2
    rng = np.random.default_rng(42)
    raw = {r: rng.normal(size=int((reg == r).sum())).astype(np.float32) for r in (0, 1, 2)}
    can = np.zeros(shape, dtype=np.float32)
    budget = 1000
    surf = mrnd.calibrate_regime_surface(raw, reg, allowed, can, canyon_weight=0.45, budget_scale=budget)
    assert surf.min() > 0.0 and surf.max() <= 1.0
    top = np.zeros(shape, dtype=bool)
    top.ravel()[np.argsort(-surf.ravel(), kind="stable")[:budget]] = True
    shares = [float((top & (reg == r)).sum()) / budget for r in (0, 1, 2)]
    assert shares == pytest.approx([0.24, 0.34, 0.42], abs=0.002)


def test_preregistration_hash_lock_is_intact():
    prereg_bytes = (ROOT / "registry/preregistration_mrnd.json").read_bytes()
    expected = (ROOT / "evidence/preregistration_mrnd_sha256.txt").read_text().strip()
    assert hashlib.sha256(prereg_bytes).hexdigest() == expected
    prereg = json.loads(prereg_bytes)
    assert prereg["registered_before_any_result"] is True
    assert prereg["budget_cap"]["max_experiments"] == 3


def test_recorded_mrnd_holdout_and_surface_card_reconcile_cleanly():
    card = json.loads((ROOT / "run_card_mrnd.json").read_text())
    assert card["lane"] == "H79-MRND"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["submission_slots_used"] == 0
    assert card["experiment_count"] == 1 <= card["max_experiments"] == 3
    assert not (ROOT / ".cache/mrnd/final_dots.npy").exists()

    for seed in (20, 30):
        ev = json.loads((ROOT / f"evidence/mrnd/m1_holdout_seed{seed}.json").read_text())
        assert ev["evaluator_version"] == "gems57-pooled-hide-v2"
        assert ev["leakage_canary"]["max_symmetric_auc"] <= 0.90
        assert ev["leakage_canary"]["n_suspicious"] == 0
        sc = ev["holdout"]["scores"]
        df = ev["holdout"]["paired_differences"]
        assert sc["candidate"]["dti"] > sc["h33_foldfair_control"]["dti"]
        assert sc["candidate"]["dti"] > sc["ablation_single_regime_static"]["dti"]
        assert df["ablation_single_regime_static"]["ci95"][0] > 0
        assert df["uniform_control"]["ci95"][0] > 0

    ev30 = json.loads((ROOT / "evidence/mrnd/m1_holdout_seed30.json").read_text())
    assert ev30["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"][0] > 0
    assert card["surface_uniqueness"]["worst_spearman"] <= 0.90
    assert card["surface_uniqueness"]["normal_budget_le_167k_flagged"] == 0


@pytest.mark.parametrize("stage_args", [["holdout", "--seed", "20"], ["final"]])
def test_closed_mrnd_lane_refuses_rerun_without_mutating_files(stage_args):
    tracked = [ROOT / "run_card_mrnd.json"] + sorted((ROOT / "evidence/mrnd").glob("*.json"))
    before = {p: p.read_bytes() for p in tracked}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_mrnd.py"), *stage_args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert "lane is closed (negative)" in proc.stderr
    assert "No files changed." in proc.stderr
    assert all(p.read_bytes() == raw for p, raw in before.items())
