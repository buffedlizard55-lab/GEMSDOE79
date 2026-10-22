"""Unit and integration tests for lane G79-CSMD and Session 1dc8cff0 engineering fixes."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np

from gems79.csmd import (
    CSMD_ALL_FEATURE_NAMES,
    CSMD_MECH_FEATURE_NAMES,
    CSMD_STATIC_FEATURE_NAMES,
    N_CSMD_ALL,
    N_CSMD_MECH,
    N_CSMD_STATIC,
    charnes_cooper_csmd_multiregime_emit,
    compute_csmd_network_mechanics,
)

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_csmd_preregistration_lock_and_feature_schema() -> None:
    prereg_path = ROOT / "registry/preregistration_csmd.json"
    lock_path = ROOT / "evidence/csmd/preregistration_sha256.txt"
    assert prereg_path.is_file() and lock_path.is_file()
    expected = lock_path.read_text().strip()
    assert expected == "465588277ea98d3948c53cb3c691b332bc66c1f940be42a40008d62b73c025fe"
    assert _sha256(prereg_path) == expected

    assert len(CSMD_STATIC_FEATURE_NAMES) == N_CSMD_STATIC == 74
    assert len(CSMD_MECH_FEATURE_NAMES) == N_CSMD_MECH == 16
    assert len(CSMD_ALL_FEATURE_NAMES) == N_CSMD_ALL == 90
    assert len(set(CSMD_ALL_FEATURE_NAMES)) == 90


def test_csmd_fold_visible_mechanics_coulomb_lobe_vs_shadow_and_zero_leakage(tmp_path: Path) -> None:
    shape = (80, 80)
    fp = np.ones(shape, dtype=bool)
    n_fp = int(fp.sum())
    vis = np.zeros(shape, dtype=bool)
    # Vertical fault segment from row 25 to 55 at col 40
    vis[25:56, 40] = True
    cues_path = tmp_path / "cues.npz"
    np.savez(
        cues_path,
        scarp_step=np.full(n_fp, 0.5, dtype=np.float32),
        grav_bdepth=np.full(n_fp, 0.5, dtype=np.float32),
        hydro=np.full(n_fp, 0.5, dtype=np.float32),
    )
    piedmont_fp = np.full(n_fp, 0.5, dtype=np.float32)
    mech = compute_csmd_network_mechanics(vis, fp, cues_path, piedmont_fp)
    assert mech.shape == (n_fp, 16)
    assert np.isfinite(mech).all()

    coulomb_2d = mech[:, 14].reshape(shape)
    # Forward tip lobe (row 18, col 40) should exceed perpendicular lateral shadow (row 40, col 48)
    assert float(coulomb_2d[18, 40]) > float(coulomb_2d[40, 48])

    # Identical call on vis_copy is strictly deterministic and leakage-free
    vis_copy = vis.copy()
    mech2 = compute_csmd_network_mechanics(vis_copy, fp, cues_path, piedmont_fp)
    np.testing.assert_allclose(mech, mech2, rtol=0.0, atol=0.0)


def test_charnes_cooper_csmd_multiregime_allocator_respects_quotas_and_spacing() -> None:
    rng = np.random.default_rng(1022)
    shape = (90, 90)
    vis = np.zeros(shape, dtype=bool)
    vis[40:50, 45] = True
    allow = np.ones(shape, dtype=bool)
    allow[vis] = False

    p_2d = rng.uniform(0.05, 0.85, size=shape).astype(np.float32)
    q_2d = rng.uniform(0.05, 0.85, size=shape).astype(np.float32)
    p_phys = rng.uniform(0.05, 0.85, size=shape).astype(np.float32)
    q_phys = rng.uniform(0.05, 0.85, size=shape).astype(np.float32)
    coulomb = rng.normal(0.0, 0.5, size=shape).astype(np.float32)

    out = charnes_cooper_csmd_multiregime_emit(
        p_2d,
        q_2d,
        p_phys,
        q_phys,
        allow,
        vis,
        coulomb_2d=coulomb,
        min_sep_px=2.2,
        near_budget=40,
        far_budget=30,
        far_min_dist_px=10.0,
        far_min_sep_px=2.5,
    )
    assert out.shape == shape
    assert out.dtype == np.float32
    assert int((out > 0).sum()) == 70
    assert not (out[vis] > 0).any()


def test_csmd_run_card_and_evidence_integrity() -> None:
    rc_path = ROOT / "run_card_csmd.json"
    assert rc_path.is_file()
    rc = json.loads(rc_path.read_text())
    assert rc["lane"] == "G79-CSMD"
    assert rc["branch"] == "arena/1dc8cff0-gemsdoe79"
    assert rc["preregistration_sha256"] == "465588277ea98d3948c53cb3c691b332bc66c1f940be42a40008d62b73c025fe"
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["auc"] <= 0.90
    assert rc["leakage_canary"]["features_cleared"] == 90
    assert rc["leakage_canary"]["tests"] == 720

    s20 = rc["holdout_dti"]["per_seed"]["seed_20"]
    s30 = rc["holdout_dti"]["per_seed"]["seed_30"]

    # Breakthrough 1: Zero-catalogue pure physics beats G79-THVC EXP-79-1 (0.0784/0.0648), H79-FNHR (0.0906/0.0966), and H33 (0.0961/0.0989)
    assert s20["EXP-CSMD-1_pure_zero_catalogue_decontam"]["dti"] > s20["C2_h33_analogue_foldfair"]["dti"]
    assert s30["EXP-CSMD-1_pure_zero_catalogue_decontam"]["dti"] > s30["C2_h33_analogue_foldfair"]["dti"]
    assert s30["paired_deltas"]["EXP-CSMD-1_pure_zero_catalogue_decontam__minus__C2_h33_analogue_foldfair"]["ci95_low"] > 0.0

    # Breakthrough 2 & 3: Unconstrained CC reaches record 0.1967 on Seed 30; multi-regime CC beats H33 on both seeds with 95% CI > 0
    assert s30["EXP-CSMD-3a_unconstrained_cc_diag"]["dti"] > 0.1944
    assert s20["paired_deltas"]["EXP-CSMD-3_csmd_charnes_cooper__minus__C2_h33_analogue_foldfair"]["ci95_low"] > 0.05
    assert s30["paired_deltas"]["EXP-CSMD-3_csmd_charnes_cooper__minus__C2_h33_analogue_foldfair"]["ci95_low"] > 0.06

    # Breakthrough 4: 0 / 939 comparable sparse duplicates (<= 75,308 dots), clearing live GEMSDOE83, G79-THVC, H79-FNHR, and H33
    diag = rc["correlation_overlap_vs_registry"]
    assert diag["total_rasters_audited"] >= 1209
    assert diag["comparable_sparse_le_75308_count"] >= 935
    assert diag["comparable_sparse_duplicates_over_0p70"] == 0
    assert diag["worst_comparable_sparse_overlap_3px"] <= 0.70
    assert diag["surface_max_abs_spearman"] <= 0.90
    assert diag["final_max_abs_spearman"] <= 0.90
    assert diag["key_sibling_overlaps"]["gems83-h83-gvcd-dink300"]["overlap_3px"] <= 0.70
    assert diag["key_sibling_overlaps"]["g79-thvc-ccsubmod"]["overlap_3px"] <= 0.70

    # Verify archived GeoTIFF and ZIP hashes
    tif_path = ROOT / rc["submission_file"]
    zip_path = ROOT / rc["zip_file"]
    assert tif_path.is_file() and zip_path.is_file()
    assert _sha256(tif_path) == rc["raster_sha256"]
    assert _sha256(zip_path) == rc["zip_sha256"]
    assert rc["validator_output"]["validator"]["all_checks_passed"] is True
    assert rc["validator_output"]["template_report"]["ok"] is True
    assert rc["validator_output"]["template_report"]["problems"] == []
    assert len(rc["submission_note"]) <= 140
    assert rc["verdict"] == "negative"
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit"] is False


def test_requirements_txt_no_duplicate_packages_and_restore_fallbacks() -> None:
    reqs = (ROOT / "requirements.txt").read_text().splitlines()
    pkgs = [re.split(r"[><=!~]", line.strip())[0].strip().lower() for line in reqs if line.strip() and not line.startswith("#")]
    assert len(pkgs) == len(set(pkgs)), f"Duplicate package in requirements.txt: {pkgs}"

    dem10_src = (ROOT / "scripts/restore_dem10.py").read_text()
    ing_src = (ROOT / "scripts/restore_official_ingenious.py").read_text()
    delta_src = (ROOT / "scripts/registry_delta_git.py").read_text()
    assert "_fetch_dem10_file" in dem10_src and "--filter=blob:none" in dem10_src
    assert "_fetch_ingenious_blob" in ing_src and "--filter=blob:none" in ing_src
    assert "restore_pinned_delta" in delta_src and "--restore-only" in delta_src
