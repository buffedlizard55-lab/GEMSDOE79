"""H79-FFAS: closed-form surface, 2 px collar, informative-halo-v4 uniqueness."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine

from gems57 import uniqueness
from gems79 import ffas

ROOT = Path(__file__).resolve().parents[1]


def test_preregistration_predates_results_and_names_the_lane():
    p = json.loads((ROOT / "registry/preregistration_ffas.json").read_text())
    assert p["lane"] == "H79-FFAS"
    assert p["registered_before_any_holdout_result"] is True
    assert p["registered_utc"] == "2026-10-22T03:49:08Z"
    assert p["uniqueness"]["overlap_mode"] == "informative-halo-v4"
    assert p["fixed_parameters"]["upface_boost"] == 2.0
    assert p["fixed_parameters"]["logistic_d0_px"] == 8.0
    hyp = (ROOT / "research/hypotheses_ffas.md").read_text()
    assert "before" in hyp.lower() and "H79-FFAS" in hyp
    assert "antislope" in hyp.lower()


def test_logistic_is_half_at_centre_and_farfield_rises():
    vis = np.zeros((21, 21), bool)
    vis[10, 10] = True
    w = ffas.logistic_farfield(vis, d0=8.0, scale=3.0)
    # distance 8 px along axis from (10,10) is (10,2) or (10,18)
    assert abs(float(w[10, 2]) - 0.5) < 1e-6
    assert w[10, 10] < 0.07          # at the catalogue pixel
    assert w[10, 0] > w[10, 2]       # farther => larger weight


def test_allowed_mask_is_pixel_exact_plus_2px_collar():
    fp = np.ones((15, 15), bool)
    cat = np.zeros((15, 15), bool); cat[7, 7] = True
    allow = ffas.allowed_mask(fp, cat, cat)
    assert not allow[7, 7]
    assert not allow[7, 8]           # 1 px away
    assert not allow[7, 9]           # 2 px away is NOT > 2
    assert allow[7, 10]              # 3 px away is allowed


def test_surface_is_unit_interval_and_zero_on_catalogue():
    rng = np.random.default_rng(0)
    bands = {n: rng.integers(0, 256, size=(20, 20)).astype(np.float32)
             for n in ffas.BANDS}
    bands["valid"] = np.full((20, 20), 255, np.float32)
    vis = np.zeros((20, 20), bool); vis[2, 2] = True
    fp = np.ones((20, 20), bool)
    s = ffas.surface(bands, vis, fp, vis)
    assert s.shape == (20, 20)
    assert np.isfinite(s).all() and s.min() >= 0 and s.max() <= 1
    assert s[2, 2] == 0


def _tif(path, arr):
    with rasterio.open(path, "w", driver="GTiff", width=arr.shape[1], height=arr.shape[0],
                       count=1, dtype="float32", crs="EPSG:32611",
                       transform=Affine(100, 0, 1000, 0, -100, 9000)) as d:
        d.write(arr.astype(np.float32), 1)
    return [{"file": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}]


def test_v4_skips_vacuous_spacefilling_overlap_but_keeps_sparse_and_rho(tmp_path):
    fp = np.ones((30, 30), bool)
    mine = np.zeros((30, 30), np.float32); mine[2, 2] = mine[2, 10] = 1
    # space-filling prior: every cell positive. Literal and v3-constant still overlap=1.
    dense = _tif(tmp_path / "dense.tif", np.full((30, 30), 0.4, np.float32))
    lit = uniqueness.compare_array_to_registry(mine, dense, fp)
    v4 = uniqueness.compare_array_to_registry(
        mine, dense, fp, overlap_mode="informative-halo-v4")
    assert lit["rows"][0]["duplicate_by_overlap"] is True
    assert v4["rows"][0]["halo_coverage"] == 1.0
    assert v4["rows"][0]["overlap_vacuous"] is True
    assert v4["rows"][0]["duplicate_by_overlap"] is False   # vacuous, skipped
    # sparse overlapping prior still fires under v4 (both candidate dots sit on it)
    close = np.zeros((30, 30), np.float32); close[2, 2] = close[2, 10] = 1
    sp = _tif(tmp_path / "sparse.tif", close)
    r = uniqueness.compare_array_to_registry(
        mine, sp, fp, overlap_mode="informative-halo-v4")["rows"][0]
    assert r["representation"] == "dot_field"
    assert r["halo_coverage"] <= 0.70
    assert r["my_dots_within_3px_of_theirs"] > 0.70
    assert r["duplicate_by_overlap"] is True
    with pytest.raises(ValueError):
        uniqueness.compare_array_to_registry(mine, sp, fp, overlap_mode="made-up")


def test_v3_default_unchanged_for_historical_nhr_tests(tmp_path):
    """Default overlap_mode remains literal-threshold so NHR evidence stays valid."""
    fp = np.ones((30, 30), bool)
    mine = np.zeros((30, 30), np.float32); mine[2, 2] = 1
    const = _tif(tmp_path / "const.tif", np.full((30, 30), .2, np.float32))
    r = uniqueness.compare_array_to_registry(
        mine, const, fp, dot_definition="budget-matched-v3")["rows"][0]
    assert r["duplicate_by_overlap"] is True
    assert r.get("overlap_mode", "literal-threshold") == "literal-threshold"
