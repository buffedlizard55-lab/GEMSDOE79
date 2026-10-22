"""Verification suite for Lane H79-PFSD (session arena/9574eb05-gemsdoe79)."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems79.pfsd_features import (
    PFSD_ALL_FEATURE_NAMES,
    PFSD_STATIC_FEATURE_NAMES,
    _axial_tangent_cos_sin_from_grad,
    _fft_upward_continue_c64,
    _province_zscore_35km,
)
from gems79.pfsd_model import equilibrate_quadrant_posteriors

ROOT = Path(__file__).resolve().parents[1]
TIF_SHA256 = "23cc11b49380e7e6eac772157b3b9538e3fc44559b871d69e1fe3fa2faa2bf84"
ZIP_SHA256 = "68aea1e223041cda84aa81ce7fd2013ac7ff0b25bf1a9245455df1f7a6ce9813"
PREREG_SHA256 = "81a0770e97c7eb520971478fc7512e0e4e076b41d96803c8e3ace076b99ea77c"


def test_pfsd_preregistration_hash_and_channel_schema():
    prereg_path = ROOT / "registry" / "preregistration_pfsd.json"
    assert hashlib.sha256(prereg_path.read_bytes()).hexdigest() == PREREG_SHA256
    recorded = (ROOT / "evidence/pfsd/preregistration_pfsd_sha256.txt").read_text().split()[0]
    assert recorded == PREREG_SHA256

    assert len(PFSD_STATIC_FEATURE_NAMES) == 92
    assert len(PFSD_ALL_FEATURE_NAMES) == 106
    assert len(set(PFSD_ALL_FEATURE_NAMES)) == 106
    assert "dist_known_fault_px" not in PFSD_ALL_FEATURE_NAMES


def test_pfsd_spectral_and_axial_primitives():
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    wave = np.sin(2.0 * np.pi * xx / 16.0).astype(np.float32)
    res = _fft_upward_continue_c64(wave, (300.0, 1500.0), dx_m=100.0)
    u300, u1500 = res[300.0], res[1500.0]
    assert u300.shape == (64, 64) and u300.dtype == np.float32
    assert np.isfinite(u300).all() and np.isfinite(u1500).all()
    assert float(np.std(u1500)) < float(np.std(u300))

    # Axial strike invariance under gradient sign flip and orthogonality at pi/2
    gy = np.zeros((4, 4), dtype=np.float32)
    gx = np.ones((4, 4), dtype=np.float32)
    c2_a, s2_a = _axial_tangent_cos_sin_from_grad(gy, gx)
    c2_b, s2_b = _axial_tangent_cos_sin_from_grad(-gy, -gx)
    c2_orth, s2_orth = _axial_tangent_cos_sin_from_grad(gx, gy)
    assert np.allclose(c2_a * c2_b + s2_a * s2_b, 1.0)
    assert np.allclose(c2_a * c2_orth + s2_a * s2_orth, -1.0)

    fp = np.ones((200, 200), dtype=bool)
    yy2, xx2 = np.mgrid[0:200, 0:200].astype(np.float32)
    field2 = np.sin(2.0 * np.pi * xx2 / 40.0).astype(np.float32)
    pz_a = _province_zscore_35km(field2, fp)
    pz_b = _province_zscore_35km(2.5 * field2 + 5.0, fp)
    assert pz_a.shape == (200, 200) and np.isfinite(pz_a).all()
    assert np.allclose(pz_a, pz_b, atol=1e-2)


def test_pfsd_quadrant_equilibration_identity_and_bounds():
    rng = np.random.default_rng(79)
    p = rng.uniform(0.0, 0.2, size=(20, 20)).astype(np.float32)
    q = rng.uniform(0.0, 0.6, size=(20, 20)).astype(np.float32)
    quad = np.zeros((20, 20), dtype=np.int8)
    quad[:10, 10:] = 1
    quad[10:, :10] = 2
    quad[10:, 10:] = 3
    q[quad == 2] *= 0.25
    allow = np.ones((20, 20), dtype=bool)

    p0, q0 = equilibrate_quadrant_posteriors(p, q, quad, allow, gamma=0.0)
    assert np.allclose(p0, p) and np.allclose(q0, q)

    pe, qe = equilibrate_quadrant_posteriors(p, q, quad, allow, gamma=0.5)
    assert np.all((pe >= 0.0) & (pe <= 1.0))
    assert np.all((qe >= 0.0) & (qe <= 1.0))
    # Under-scaled quadrant 2 receives boost while intra-quadrant order is preserved
    assert float(qe[quad == 2].mean()) > float(q[quad == 2].mean())
    assert np.array_equal(np.argsort(qe[quad == 2].ravel()), np.argsort(q[quad == 2].ravel()))


def test_pfsd_archived_artifacts_holdout_records_and_uniqueness_receipts():
    arch = ROOT / "archive" / "h79_pfsd_9574eb05"
    stem = "h79-pfsd-equilcc-20261022-2c5d5fd3-zeros-DO-NOT-SUBMIT"
    tif_path = arch / f"{stem}.tif"
    zip_path = arch / f"{stem}.zip"
    rc_path = arch / "run_card_pfsd.json"

    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == TIF_SHA256
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == ZIP_SHA256
    assert rc_path.read_bytes() == (ROOT / "evidence/pfsd/run_card_pfsd.json").read_bytes()

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert names == [f"{stem}.tif"]
        assert hashlib.sha256(zf.read(names[0])).hexdigest() == TIF_SHA256

    with rasterio.open(tif_path) as ds:
        assert str(ds.crs) == "EPSG:32611"
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        arr = ds.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        assert int((arr > 0).sum()) == 39250
        assert set(np.unique(arr).tolist()) == {0.0, 1.0}

    rc = json.loads(rc_path.read_text())
    assert rc["verdict"] == "negative"
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit"] is False
    assert rc["weekly_slot_spent"] is False
    assert len(rc["submission_note"]) <= 140
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["max_symmetric_auc"] <= 0.90

    # Verify scientific breakthroughs on both seeds
    s20 = rc["holdout_dti"]["seed_20"]
    s30 = rc["holdout_dti"]["seed_30"]
    assert s20["EXP_PFSD_1_uncorrupted_pure_physics"]["dti"] > s20["C2_h33_analogue_foldfair"]["dti"]
    assert s30["EXP_PFSD_1_uncorrupted_pure_physics"]["dti"] > s30["C2_h33_analogue_foldfair"]["dti"]
    assert s20["EXP_PFSD_2_pfsd_uniform_d28"]["dti"] > 0.185
    assert s30["EXP_PFSD_2_pfsd_uniform_d28"]["dti"] > 0.175

    # Verify uniqueness audit receipts & GEMSDOE83 clearance
    ua = rc["uniqueness_audit"]
    assert ua["comparable_rasters"] == 1213
    assert ua["pre_placement_surface"]["max_abs_spearman"] <= 0.90
    assert ua["post_placement_dots"]["max_abs_spearman"] <= 0.90
    assert ua["post_placement_dots"]["key_peer_comparisons"]["GEMSDOE83_gvcd"]["forward_overlap_3px"] <= 0.70
    assert ua["post_placement_dots"]["key_peer_comparisons"]["H33_GEMSDOE32"]["forward_overlap_3px"] <= 0.70

    for jfile in list((ROOT / "evidence/pfsd").glob("*.json")) + list(arch.glob("*.json")):
        txt = jfile.read_text()
        assert "/home/user/GEMSDOE79" not in txt, f"Machine path leaked in {jfile}"
