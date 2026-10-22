"""Unit tests for G79-STFD feature invariants, quadrant-stratified LOQO shards,
visible-prevalence calibration, and scale-consistent fractional Dinkelbach emission."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from gems79.cskd import _release_mm
from gems79.lifecycle import LaneClosedError
from gems79.stfd import (
    N_STFD_ALL,
    N_STFD_MECH,
    N_STFD_STATIC,
    STFD_ALL_FEATURE_NAMES,
    STFD_MECH_NAMES,
    STFD_STATIC_NAMES,
    _group_rank_gauss,
    build_stfd_stratified_topology_shards,
    calibrate_quadrant_posteriors_to_visible_density,
    compute_stfd_mechanics,
    dinkelbach_stfd_emit,
    require_open_stfd_lane,
)

ROOT = Path(__file__).resolve().parents[1]


def test_stfd_preregistration_hash_and_schema_invariants() -> None:
    prereg = ROOT / "registry/preregistration_g79_stfd.json"
    lock = ROOT / "evidence/stfd/preregistration_sha256.txt"
    assert prereg.is_file() and lock.is_file()
    assert hashlib.sha256(prereg.read_bytes()).hexdigest() == lock.read_text().strip()

    assert len(STFD_STATIC_NAMES) == N_STFD_STATIC == 97
    assert len(STFD_MECH_NAMES) == N_STFD_MECH == 22
    assert len(STFD_ALL_FEATURE_NAMES) == N_STFD_ALL == 119
    assert len(set(STFD_ALL_FEATURE_NAMES)) == 119
    assert "abs_elev_km" not in STFD_ALL_FEATURE_NAMES
    assert "geodawn_area1_hires" not in STFD_ALL_FEATURE_NAMES


def test_group_rank_gauss_eliminates_inter_block_mean_and_scale_shift() -> None:
    rng = np.random.default_rng(79)
    g = np.array([0] * 4000 + [1] * 4000, dtype=np.int16)
    vals = np.concatenate([rng.exponential(1.0, size=4000), rng.exponential(25.0, size=4000) + 120.0]).astype(np.float32)
    z = _group_rank_gauss(vals, g)
    assert z.shape == vals.shape and z.dtype == np.float32
    assert abs(float(z[g == 0].mean())) < 1e-3
    assert abs(float(z[g == 1].mean())) < 1e-3
    assert abs(float(z[g == 0].std()) - float(z[g == 1].std())) < 1e-2


def test_stfd_hangingwall_polarity_mechanics_and_decontaminated_shards(tmp_path: Path) -> None:
    h, w = 120, 120
    fp = np.ones((h, w), dtype=bool)
    n_fp = int(fp.sum())
    vis = np.zeros((h, w), dtype=bool)
    vis[20:52, 60] = True
    vis[68:100, 60] = True
    vis[25:55, 22] = True
    vis[75:105, 95] = True

    cskd_cues = tmp_path / "cskd_cues.npz"
    np.savez(
        cskd_cues,
        scarp_step=np.full(n_fp, 0.5, dtype=np.float32),
        grav_bdepth=np.full(n_fp, 0.5, dtype=np.float32),
        hydro=np.full(n_fp, 0.4, dtype=np.float32),
        throw_proxy=np.full(n_fp, 0.6, dtype=np.float32),
        clean_scarp=np.full(n_fp, 0.5, dtype=np.float32),
    )
    # Eastward (+x = +1) hanging-wall deepening across fault at col 60
    stfd_cues = tmp_path / "stfd_cues.npz"
    np.savez(
        stfd_cues,
        hw_ny_2d=np.zeros((h, w), dtype=np.float16),
        hw_nx_2d=np.ones((h, w), dtype=np.float16),
        bdepth_km_fp=np.full(n_fp, 0.8, dtype=np.float16),
        swarm_transt_fp=np.full(n_fp, 0.5, dtype=np.float16),
        grav_bdepth_conc_fp=np.full(n_fp, 0.6, dtype=np.float16),
        rad_kd_pos_fp=np.full(n_fp, 0.4, dtype=np.float16),
        scarp_qnorm_fp=np.zeros(n_fp, dtype=np.float16),
        clean_veto_fp=np.ones(n_fp, dtype=np.float16),
        piedmont_break_fp=np.full(n_fp, 0.3, dtype=np.float16),
    )

    mech = compute_stfd_mechanics(vis, fp, cskd_cues, stfd_cues)
    assert mech.shape == (n_fp, 22) and np.all(np.isfinite(mech))
    hw_2d = mech[:, 18].reshape(h, w)
    # Eastward hanging wall (col 69) receives strong positive projection, footwall (col 51) receives 0
    assert float(hw_2d[36, 69]) > 0.5
    assert float(hw_2d[36, 51]) == 0.0

    mm_path = tmp_path / "stfd97.mmap"
    mm = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=(n_fp, N_STFD_STATIC))
    mm[:] = 0.2
    mm.flush()

    quad_2d = np.zeros((h, w), dtype=np.int8)
    quad_2d[:60, 60:] = 1
    quad_2d[60:, :60] = 2
    quad_2d[60:, 60:] = 3

    shards, draw_refs = build_stfd_stratified_topology_shards(
        vis,
        fp,
        quad_2d[fp],
        mm,
        mm_path,
        cskd_cues,
        stfd_cues,
        n_draws=2,
        neg_per_quad_per_draw=300,
    )
    _release_mm(mm, mm_path)
    assert len(draw_refs) == 2
    d_col = N_STFD_STATIC + STFD_MECH_NAMES.index("net_log_dist")
    for qid, sd in shards.items():
        assert sd["X"].shape[0] > 0
        # Stage-1 active support strictly excludes sim_known (d_sim == 0) while including 0 < d_sim <= 3.0 collar negatives!
        assert float(sd["X"][:, d_col].min()) > 0.0
        assert np.all(sd["y"][sd["X"][:, d_col] <= float(np.log1p(3.0))] == 0.0)


def test_quadrant_visible_calibration_and_dinkelbach_emitter_invariants() -> None:
    rng = np.random.default_rng(2026)
    shape = (100, 100)
    vis = np.zeros(shape, dtype=bool)
    vis[10:40, 20] = True
    vis[60:95, 25] = True  # Quadrant 2 has twice as many visible fault pixels as Quadrant 0
    vis[62:92, 35] = True
    allow = np.ones(shape, dtype=bool)
    allow[vis] = False

    quad_2d = np.zeros(shape, dtype=np.int8)
    quad_2d[:50, 50:] = 1
    quad_2d[50:, :50] = 2
    quad_2d[50:, 50:] = 3

    p_raw = np.full(shape, 0.05, dtype=np.float32)
    q_raw = np.full(shape, 0.12, dtype=np.float32)
    p_cal, q_cal, diag = calibrate_quadrant_posteriors_to_visible_density(p_raw, q_raw, vis, allow, quad_2d)
    assert float(p_cal[quad_2d == 2].mean()) > float(p_cal[quad_2d == 0].mean()) * 1.3
    assert "quad_2" in diag

    p_2d = rng.uniform(0.01, 0.35, size=shape).astype(np.float32)
    q_2d = rng.uniform(0.02, 0.45, size=shape).astype(np.float32)
    dots, info = dinkelbach_stfd_emit(
        p_2d,
        q_2d,
        p_2d,
        q_2d,
        allow,
        vis,
        min_sep_px=2.05,
        near_max_budget=90,
        near_min_budget=40,
        far_reserve_budget=25,
        far_min_dist_px=8.0,
        far_min_sep_px=2.5,
    )
    assert dots.shape == shape and dots.dtype == np.float32
    assert set(np.unique(dots)).issubset({0.0, 1.0})
    assert not (dots[vis] > 0).any()
    assert info["far_pure_physics_reserve_dots"] == 25
    assert 65 <= info["total_emitted_dots"] <= 115


def test_stfd_lifecycle_guard_blocks_closed_or_mismatched_lane(tmp_path: Path) -> None:
    rc = tmp_path / "run_card_stfd.json"
    rc.write_text('{"lane": "G79-STFD", "verdict": "negative", "stopped": true}')
    with pytest.raises(LaneClosedError):
        require_open_stfd_lane(tmp_path)


def test_stfd_sealed_artifacts_hashes_permissions_and_site_parity() -> None:
    import json
    from gems57.validate import validate

    rc_root = ROOT / "run_card_stfd.json"
    rc_ev = ROOT / "evidence/stfd/run_card_stfd.json"
    rc_docs = ROOT / "docs/evidence/run_card_stfd.json"
    assert rc_root.is_file() and rc_ev.is_file() and rc_docs.is_file()
    card = json.loads(rc_root.read_text())
    assert json.loads(rc_ev.read_text()) == card
    assert json.loads(rc_docs.read_text()) == card

    assert card["lane"] == "G79-STFD"
    assert card["status"] == "closed"
    assert card["stopped"] is True
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["ok_to_download"] is True
    assert card["submission_note_length"] <= 140
    assert card["holdout_dti"]["seed_20"]["EXP_STFD_3_dinkelbach"]["dti"] > 0.192
    assert card["holdout_dti"]["seed_30"]["EXP_STFD_3_dinkelbach"]["dti"] > 0.211
    assert card["holdout_dti"]["dual_seed_mean_dti"] > 0.202

    nov = card["uniqueness_vs_registry"]
    assert nov["comparable_prediction_rasters_audited"] >= 1270
    assert nov["pre_placement_surface"]["max_abs_spearman"] <= 0.90
    assert nov["post_placement_dots"]["max_abs_spearman"] <= 0.90
    sp = nov["sparse_like_for_like_diagnostic"]
    ext_sparse = [r for r in sp["top15_sparse_overlaps"] if r["repo"] != "GEMSDOE79"]
    assert max(r["literal_forward_overlap_3px"] for r in ext_sparse) <= 0.70

    tif_path = ROOT / card["submission_file"]
    zip_path = ROOT / card["zip_file"]
    assert tif_path.is_file() and zip_path.is_file()
    assert (tif_path.stat().st_mode & 0o004) != 0
    assert (zip_path.stat().st_mode & 0o004) != 0
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["zip_sha256"]

    val = validate(tif_path)
    assert val["all_checks_passed"] is True
    assert val["emitted_positive_pixels"] == 41000
    assert val["n_nan"] == 0
    assert val["n_infinite"] == 0

    from gems79.portal_spec import validate_portal_file

    pspec = card["official_portal_spec_v2"]
    nan_tif = ROOT / pspec["nan_exterior_companion_tif"]
    nan_zip = ROOT / pspec["nan_exterior_companion_zip"]
    assert nan_tif.is_file() and nan_zip.is_file()
    assert (nan_tif.stat().st_mode & 0o004) != 0 and (nan_zip.stat().st_mode & 0o004) != 0
    assert validate_portal_file(nan_tif)["ok"] is True
    assert validate_portal_file(nan_zip)["ok"] is True

    for fig_name in (
        "stfd_holdout_progression.png",
        "stfd_quadrant_calibration.png",
        "stfd_novelty_and_features.png",
        "stfd_live_discovery_map.png",
    ):
        fp = ROOT / "docs/figures" / fig_name
        assert fp.is_file() and fp.stat().st_size > 50_000
        assert (fp.stat().st_mode & 0o004) != 0

    host_prefix = "/home/" + "user"
    for check_file in (
        rc_root,
        ROOT / "registry/preregistration_g79_stfd.json",
        ROOT / "archive/g79_stfd_1b017e86/README.md",
        ROOT / "docs/g79-stfd.html",
        ROOT / "docs/executive-summary.html",
    ):
        assert host_prefix not in check_file.read_text(encoding="utf-8")

