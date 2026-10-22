"""End-to-end verification tests for Session d7da950d (Lane G79-DFSD & PR #70 quarantine)."""
from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

from gems79.dfsd_features import (
    DFSD_ALL_FEATURE_NAMES,
    DFSD_EXTRA_MECH_NAMES,
    DFSD_EXTRA_STATIC_NAMES,
    DFSD_MECH_NAMES,
    DFSD_STATIC_NAMES,
    FORBIDDEN_POINT_COLUMNS,
    FORBIDDEN_RASTER_INPUTS,
)
from validate_submission import validate_path

ROOT = Path(__file__).resolve().parents[1]


def test_dfsd_feature_schema_and_anti_leakage_invariants():
    assert len(DFSD_EXTRA_STATIC_NAMES) == 20
    assert len(DFSD_STATIC_NAMES) == 90
    assert len(DFSD_EXTRA_MECH_NAMES) == 3
    assert len(DFSD_MECH_NAMES) == 17
    assert len(DFSD_ALL_FEATURE_NAMES) == 107
    assert len(set(DFSD_ALL_FEATURE_NAMES)) == 107
    assert {"dist_known_fault_px", "known_fault", "label"} <= FORBIDDEN_POINT_COLUMNS
    assert {"derived_sgmc_faults_100m_u8.tif", "gdr_qfaults_traces.csv"} <= FORBIDDEN_RASTER_INPUTS
    for fn in DFSD_ALL_FEATURE_NAMES:
        assert "dist_known_fault" not in fn and "sgmc" not in fn and "qfault" not in fn


def test_dfsd_artifact_bytes_zip_permissions_and_card_parity():
    card = json.loads((ROOT / "run_card_dfsd.json").read_text())
    arch_card = json.loads((ROOT / "archive/g79_dfsd_d7da950d/run_card_dfsd.json").read_text())
    res = json.loads((ROOT / "evidence/g79_dfsd_results.json").read_text())
    assert card == arch_card
    assert card["lane"] == "G79-DFSD"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True and card["ok_to_submit"] is False
    assert card["submission_slots_used"] == 0
    assert card["experiment_count"] == card["max_experiments"] == 3

    prereg_sha = hashlib.sha256((ROOT / "registry/preregistration_g79_dfsd.json").read_bytes()).hexdigest()
    assert prereg_sha == (ROOT / "evidence/preregistration_g79_dfsd_sha256.txt").read_text().strip()
    assert card["preregistration_sha256"] == res["preregistration_sha256"] == prereg_sha

    tif = ROOT / card["submission_file"]
    zf = ROOT / card["zip_file"]
    assert tif.is_file() and zf.is_file()
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zf.read_bytes()).hexdigest() == card["zip_sha256"]
    assert stat.S_IMODE(tif.stat().st_mode) == 0o644
    assert stat.S_IMODE(zf.stat().st_mode) == 0o644

    fmt = validate_path(tif)
    assert fmt["format_passed"] is True
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
    assert np.isfinite(arr).all()
    assert set(np.unique(arr).tolist()) <= {0.0, 1.0}
    assert int((arr == 1.0).sum()) == card["positive_pixels"] == 20611

    with zipfile.ZipFile(zf) as zarch:
        assert zarch.namelist() == [tif.name]
        assert zarch.testzip() is None
        assert zarch.read(tif.name) == tif.read_bytes()

    # Verify all 856 canary tests passed and zero-catalogue record + Seed 30 posterior gain match exact evaluator JSON
    assert res["seed20"]["leakage_canary"]["all_passed"] is True
    assert res["seed30"]["leakage_canary"]["all_passed"] is True
    assert res["seed20"]["leakage_canary"]["max_symmetric_auc"] <= 0.90
    assert res["seed30"]["leakage_canary"]["max_symmetric_auc"] <= 0.90
    s30_scores = res["seed30"]["official_evaluate_all"]["scores"]
    assert s30_scores["EXP-DFSD-1_pure_zero_catalogue"]["dti"] > s30_scores["C2_h33_analogue_foldfair"]["dti"]
    assert s30_scores["EXP-DFSD-2_uniform_d28"]["dti"] > 0.175

    # Verify EXP-DFSD-1 pure-physics peer overlaps are all strictly <= 0.70 across all 6 champion peers
    peers = res["exp_dfsd_1_pure_physics_uniqueness_diagnostic"]["peer_overlaps_3px"]
    assert len(peers) == 6
    assert all(v["forward_overlap_3px"] <= 0.70 for v in peers.values())


def test_pr70_etp_quarantine_integrity_and_no_rogue_downloads():
    assert (ROOT / "archive/g79_etp_incoming_45998a01/README.md").is_file()
    assert not (ROOT / "data/bridge").exists()
    active_tifs = {p.name for p in (ROOT / "docs/downloads").glob("*.tif")}
    # The canonical artifact plus any probe explicitly declared in
    # registry/published_probes.json; nothing else may be published.
    from verify_project import declared_probe_names
    assert active_tifs == {"g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif"} | declared_probe_names(ROOT)
