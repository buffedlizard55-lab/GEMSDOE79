"""Unit and artifact-integrity tests for session 6da2620c (lane G79-CSKD)."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems79.cskd import (  # noqa: E402
    CSKD_ALL_FEATURE_NAMES,
    CSKD_MECH_NAMES,
    CSKD_STATIC_NAMES,
    _fft_flightline_notch_and_kloc,
    _infill_2d_sentinels,
    _release_mm,
    blend_counterfactual_posteriors,
    build_cskd_training_shards,
    compute_cskd_mechanics,
)


def test_cskd_feature_lists_have_exact_cardinalities_and_unique_names():
    assert len(CSKD_STATIC_NAMES) == 84
    assert len(CSKD_MECH_NAMES) == 18
    assert len(CSKD_ALL_FEATURE_NAMES) == 102
    assert len(set(CSKD_ALL_FEATURE_NAMES)) == 102


def test_infill_2d_sentinels_eliminates_negative_sentinels_without_gradient_spikes():
    arr = np.full((32, 32), 1250.0, dtype=np.float32)
    arr[0, :] = -999999.0
    arr[:, -1] = -999999.0
    cleaned = _infill_2d_sentinels(arr, arr > -1e5)
    assert cleaned.shape == (32, 32) and cleaned.dtype == np.float32
    assert np.allclose(cleaned, 1250.0)


def test_fft_notch_and_kloc_suppress_ew_flightline_corrugation_and_detect_ns_contact():
    h, w = 128, 128
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    step = (np.tanh((xx - 64.0) / 2.0) * 80.0).astype(np.float32)
    corrugation = (35.0 * np.sin(2.0 * np.pi * yy / 4.0)).astype(np.float32)  # 400 m E-W flight lines
    hgm_clean, kloc_clean = _fft_flightline_notch_and_kloc(step, dx_m=100.0)
    hgm_corr, kloc_corr = _fft_flightline_notch_and_kloc(step + corrugation, dx_m=100.0)

    assert np.all(np.isfinite(hgm_corr)) and np.all(np.isfinite(kloc_corr))
    # Horizontal gradient & local wavenumber still peak sharply along the N-S fault contact x=64
    assert float(np.mean(hgm_corr[32:96, 63:66])) > 4.0 * float(np.mean(hgm_corr[32:96, 12:24]))
    assert float(np.mean(kloc_clean[32:96, 63:66])) > 1.8 * float(np.mean(kloc_clean[32:96, 12:24]))


def test_coulomb_shadow_slip_deficit_and_decontaminated_shards(tmp_path):
    h, w = 140, 140
    fp = np.ones((h, w), dtype=bool)
    n_fp = int(fp.sum())
    vis = np.zeros((h, w), dtype=bool)
    # Multiple fault segments so inner component hiding has >= 4 components
    vis[15:52, 70] = True
    vis[64:102, 70] = True
    vis[20:55, 25] = True
    vis[80:118, 110] = True
    vis[30:65, 115] = True

    cues_path = tmp_path / "cues.npz"
    np.savez(
        cues_path,
        scarp_step=np.full(n_fp, 0.6, dtype=np.float32),
        grav_bdepth=np.full(n_fp, 0.5, dtype=np.float32),
        hydro=np.full(n_fp, 0.3, dtype=np.float32),
        throw_proxy=np.full(n_fp, 0.7, dtype=np.float32),
        clean_scarp=np.full(n_fp, 0.6, dtype=np.float32),
    )

    mech_fp = compute_cskd_mechanics(vis, fp, cues_path)
    assert mech_fp.shape == (n_fp, 18) and mech_fp.dtype == np.float32
    mech_2d = mech_fp.reshape(h, w, 18)

    idx_shadow = CSKD_MECH_NAMES.index("net_coulomb_shadow")
    idx_deficit = CSKD_MECH_NAMES.index("net_slip_deficit_front")
    idx_tip = CSKD_MECH_NAMES.index("net_tip_fwd_35px")

    # Broadside shadow (row 33, col 77 — 7 px broadside to segment midpoint) > relay gap (row 58, col 70)
    assert float(mech_2d[33, 77, idx_shadow]) > float(mech_2d[58, 70, idx_shadow]) + 0.20
    # Relay gap (row 58, col 70) has much stronger forward crack-tip propagation than broadside flank
    assert float(mech_2d[58, 70, idx_tip]) > float(mech_2d[33, 77, idx_tip]) * 2.5
    # Unmapped far-field range front (row 120, col 30) has higher slip-deficit than dense fault interior
    assert float(mech_2d[120, 30, idx_deficit]) > float(mech_2d[35, 70, idx_deficit])

    # Verify decontaminated shard builder strictly excludes 0 < d_sim <= 3.0 px
    mm_path = tmp_path / "static.mmap"
    mm = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=(n_fp, 84))
    mm[:] = 0.25
    mm.flush()

    quad_2d = np.zeros((h, w), dtype=np.int8)
    quad_2d[:70, 70:] = 1
    quad_2d[70:, :70] = 2
    quad_2d[70:, 70:] = 3

    shards, _ = build_cskd_training_shards(
        visible_mask=vis,
        footprint=fp,
        quad_fp=quad_2d[fp],
        static_mm=mm,
        mmap_path=mm_path,
        cues_npz_path=cues_path,
        n_draws=1,
        buffer_px=3,
        neg_per_quad_per_draw=400,
        seed_base=79,
    )
    _release_mm(mm, mm_path)

    d_idx = 84 + CSKD_MECH_NAMES.index("net_log_dist")
    for qid, sdict in shards.items():
        xq = sdict["X"]
        if xq.shape[0] > 0:
            assert float(np.min(xq[:, d_idx])) > float(np.log1p(3.0)), f"Contaminated <=3px pixel leaked into shard {qid}"

    # Verify mass-conserving counterfactual blend preserves [0, 1] bounds and boosts far-field pure physics
    p_full = np.array([[0.8, 0.1], [0.5, 0.2]], dtype=np.float32)
    q_full = np.array([[0.9, 0.15], [0.6, 0.25]], dtype=np.float32)
    p_zero = np.array([[0.1, 0.9], [0.4, 0.6]], dtype=np.float32)
    q_zero = np.array([[0.15, 0.95], [0.45, 0.7]], dtype=np.float32)
    d_grid = np.array([[3.5, 50.0], [8.0, 35.0]], dtype=np.float32)
    allow = np.ones((2, 2), dtype=bool)
    p_cf, q_cf = blend_counterfactual_posteriors(
        p_full, q_full, p_zero, q_zero, d_grid, allow, w_base=0.05, w_far=0.25
    )
    assert np.all((p_cf >= 0.0) & (p_cf <= 1.0)) and np.all((q_cf >= 0.0) & (q_cf <= 1.0))
    assert float(p_cf[0, 1]) > float(p_full[0, 1]) + 0.10  # far-field receives counterfactual pure-physics lift


def test_g79_cskd_archived_artifacts_and_receipts_are_complete_and_valid():
    prereg = json.loads((ROOT / "registry/preregistration_g79_cskd.json").read_text())
    canary = json.loads((ROOT / "evidence/g79_cskd_leakage_canary.json").read_text())
    results = json.loads((ROOT / "evidence/g79_cskd_results.json").read_text())
    src_rec = json.loads((ROOT / "evidence/cskd_sources_receipt.json").read_text())
    rc = json.loads((ROOT / "archive/g79_cskd_6da2620c/run_card_cskd.json").read_text())

    assert prereg["status"] == "closed"
    assert canary["gate_passed"] is True
    assert canary["n_features_tested"] == 102
    assert canary["overall_max_symmetric_auc"] <= 0.90

    for blob_txt in (json.dumps(src_rec), json.dumps(rc)):
        assert "/home/user" not in blob_txt

    s20 = results["seed20"]["official_evaluate_all"]["scores"]["EXP-CSKD-3_counterfactual_cc"]["dti"]
    s30 = results["seed30"]["official_evaluate_all"]["scores"]["EXP-CSKD-3_counterfactual_cc"]["dti"]
    assert s30 > 0.214  # All-time GEMSDOE79 Seed-30 record (0.214488)
    assert 0.5 * (s20 + s30) > 0.196  # Beats G79-THVC 2-seed mean (0.192442)
    assert results["comparison_vs_g79_thvc"]["beats_thvc_on_both_seeds"] is False
    assert results["comparison_vs_g79_thvc"]["promoted_to_canonical_downloads"] is False

    assert results["pre_placement_surface_audit"]["registry_rasters_expected"] == 1221
    assert results["pre_placement_surface_audit"]["max_abs_spearman"] <= 0.90
    assert results["post_placement_dot_audit"]["max_abs_spearman"] <= 0.90
    assert (
        results["post_placement_dot_audit"]["key_peer_overlaps"]["GEMSDOE83_h83_gvcd"]["forward_overlap_3px"]
        <= 0.70
    )

    tif_path = ROOT / rc["submission_file"]
    zip_path = ROOT / rc["zip_file"]
    assert tif_path.is_file() and zip_path.is_file()
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == rc["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == rc["zip_sha256"]
    assert len(rc["submission_note"]) <= 140
    assert rc["verdict"] == "negative" and rc["ok_to_submit"] is False and rc["ok_to_download"] is True

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()

    with rasterio.open(ROOT / "data/reference/sample_submission.tif") as ref_ds, rasterio.open(
        ROOT / "data/reference/existing_faults.tif"
    ) as cat_ds, rasterio.open(tif_path) as sub_ds:
        assert sub_ds.crs == ref_ds.crs
        assert sub_ds.shape == ref_ds.shape == (3730, 3292)
        assert sub_ds.transform == ref_ds.transform
        arr = sub_ds.read(1)
        fp = np.isfinite(ref_ds.read(1))
        cat = (cat_ds.read(1) > 0) & fp
        assert arr.dtype == np.float32
        assert int(np.isnan(arr).sum()) == 0
        assert int(np.isinf(arr).sum()) == 0
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
        assert set(np.unique(arr)).issubset({0.0, 1.0})
        assert int((arr > 0).sum()) == 42000
        assert int(((arr > 0) & ~fp).sum()) == 0
        assert int(((arr > 0) & cat).sum()) == 0

    readme_txt = (ROOT / "README.md").read_text()
    assert rc["raster_sha256"] in readme_txt
    assert rc["zip_sha256"] in readme_txt
    assert rc["submission_note"] in readme_txt
    assert f"({rc['submission_note_length']} / 140` chars)" in readme_txt or f"(`{rc['submission_note_length']} / 140` chars)" in readme_txt

