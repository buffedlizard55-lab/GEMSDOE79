"""Tests for the H79-DCE lane and the shared uniqueness v4 amendments (IR-79-57/58)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness
from gems79 import dce


def _tif(path, arr):
    h, w = arr.shape
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
                       crs="EPSG:32611", transform=rasterio.Affine(100, 0, 0, 0, -100, 0)) as s:
        s.write(np.asarray(arr, np.float32), 1)
    return {"file": str(path), "sha256": None}


# ---------------------------------------------------------------- v4: vacuous
def test_vacuous_overlap_blocks_only_beyond_chance(tmp_path):
    fp = np.ones((40, 40), bool)
    # registry dot field whose halo covers > 70% of the grid -> chance > 0.70
    theirs = np.zeros((40, 40), np.float32)
    theirs[:, :33] = 1.0
    reg = [_tif(tmp_path / "wide.tif", theirs)]
    mine = np.zeros((40, 40), np.float32)
    mine[2:8, 2:8] = 1          # 36 dots far from the halo edge, overlap = 1.0
    digest = hashlib.sha256((tmp_path / "wide.tif").read_bytes()).hexdigest()
    lit = uniqueness.compare_array_to_registry(mine, reg, fp)
    row = lit["rows"][0]
    assert row["duplicate_by_overlap"]                    # literal reading blocks
    v4 = uniqueness.compare_array_to_registry(mine, reg, fp, uniform_chance={digest: 0.80})
    r = v4["rows"][0]
    assert r["vacuous_overlap_test"] and r["overlap_chance"] == 0.80
    # overlap 1.0 vs chance 0.8: beyond-chance 0.2 exceeds the 95% margin -> still blocks
    assert r["duplicate_by_overlap_beyond_chance"] is True
    v4b = uniqueness.compare_array_to_registry(mine, reg, fp, uniform_chance={digest: 1.0})
    rb = v4b["rows"][0]
    # overlap 1.0 == chance 1.0: not beyond chance -> vacuously cleared
    assert rb["duplicate_by_overlap_beyond_chance"] is False
    assert rb["overlap_beyond_chance"] == 0.0


def test_missing_chance_entry_keeps_literal_fail_closed(tmp_path):
    fp = np.ones((40, 40), bool)
    theirs = np.zeros((40, 40), np.float32)
    theirs[:, :33] = 1.0
    reg = [_tif(tmp_path / "wide.tif", theirs)]
    mine = np.zeros((40, 40), np.float32)
    mine[2:8, 2:8] = 1
    res = uniqueness.compare_array_to_registry(mine, reg, fp, uniform_chance={"deadbeef": 0.99})
    row = res["rows"][0]
    assert row["overlap_chance"] is None and row["vacuous_overlap_test"] is False
    assert row["duplicate_by_overlap"]            # no measured chance -> literal stands


def test_beyond_chance_margin_scales_and_is_positive():
    assert uniqueness.beyond_chance_margin(0.75, 37654) > 0
    assert uniqueness.beyond_chance_margin(0.75, 37654) < uniqueness.beyond_chance_margin(0.75, 1000)
    assert uniqueness.beyond_chance_margin(1.0, 100) == 0.0
    assert uniqueness.beyond_chance_margin(0.5, 0) == 0.0


# -------------------------------------------------------- v4: not comparable
def test_not_comparable_shape_mismatch_is_excluded_not_fatal(tmp_path):
    fp = np.ones((40, 40), bool)
    small = np.zeros((8, 12), np.float32)
    reg = [_tif(tmp_path / "small.tif", small)]
    mine = np.zeros((40, 40), np.float32)
    mine[5, 5] = mine[30, 30] = 1
    res = uniqueness.compare_array_to_registry(mine, reg, fp, expected_grid=None)
    row = res["rows"][0]
    assert row.get("not_comparable") and row["not_comparable_reason"] == "grid_or_band_count_mismatch"
    assert res["not_comparable_rasters"] and res["not_comparable_rasters"][0]["reason"] == "grid_or_band_count_mismatch"


def test_missing_file_still_fails_closed(tmp_path):
    fp = np.ones((40, 40), bool)
    reg = [{"file": str(tmp_path / "ghost.tif"), "sha256": None}]
    mine = np.zeros((40, 40), np.float32)
    mine[5, 5] = 1
    res = uniqueness.compare_array_to_registry(mine, reg, fp)
    assert "error" in res["rows"][0]
    assert res["not_comparable_rasters"] == []


def test_undecodable_tiff_is_not_comparable(tmp_path):
    p = tmp_path / "broken.tif"
    p.write_bytes(b"not a tiff at all but raises a specific error")
    fp = np.ones((40, 40), bool)
    reg = [{"file": str(p), "sha256": None}]
    mine = np.zeros((40, 40), np.float32)
    mine[5, 5] = 1
    res = uniqueness.compare_array_to_registry(mine, reg, fp)
    row = res["rows"][0]
    assert "error" in row or row.get("not_comparable")   # never silently dropped


# ------------------------------------------------------------------- emission
def test_place_cover_one_dot_per_tile_and_budget():
    rng = np.random.default_rng(0)
    surface = rng.random((60, 60)).astype(np.float32)
    allowed = np.ones((60, 60), bool)
    dots, info = dce.place_cover(surface, allowed, 50, tile_px=3)
    assert info["emitted"] == 50 and dots.sum() == 50
    # at most one dot per 3x3 tile
    ys, xs = np.nonzero(dots)
    tiles = set(zip(ys // 3, xs // 3))
    assert len(tiles) == dots.sum()


def test_place_capped_respects_every_allowance():
    rng = np.random.default_rng(1)
    surface = rng.random((80, 80)).astype(np.float32)
    allowed = np.ones((80, 80), bool)
    h1 = np.zeros((80, 80), bool); h1[:, :60] = True      # 75% of area
    h2 = np.zeros((80, 80), bool); h2[20:, :] = True      # 75% of area
    budget, ceiling = 200, 0.8
    dots, info = dce.place_capped(surface, allowed, budget, {"a": h1, "b": h2}, ceiling=ceiling)
    assert dots.sum() == budget
    assert info["per_raster"]["a"]["placed_in_halo"] <= int(np.floor(ceiling * budget))
    assert info["per_raster"]["b"]["placed_in_halo"] <= int(np.floor(ceiling * budget))
    # a tighter ceiling can bind and leave the budget unfilled: allowances still hold
    dots_t, info_t = dce.place_capped(surface, allowed, budget, {"a": h1, "b": h2}, ceiling=0.5)
    assert dots_t.sum() <= budget
    assert info_t["per_raster"]["a"]["placed_in_halo"] <= int(np.floor(0.5 * budget))
    assert info_t["per_raster"]["b"]["placed_in_halo"] <= int(np.floor(0.5 * budget))
    # determinism
    dots2, _ = dce.place_capped(surface, allowed, budget, {"a": h1, "b": h2}, ceiling=ceiling)
    assert np.array_equal(dots, dots2)


def test_place_capped_skips_only_when_needed():
    # with a generous ceiling the capped emission equals the uncapped one
    rng = np.random.default_rng(2)
    surface = rng.random((50, 50)).astype(np.float32)
    allowed = np.ones((50, 50), bool)
    h = np.zeros((50, 50), bool); h[10:20, 10:20] = True
    d1, i1 = dce.place_capped(surface, allowed, 40, {"h": h}, ceiling=1.0)
    d2, i2 = dce.place_cover(surface, allowed, 40)
    assert np.array_equal(d1, d2)
    assert i1["skipped_by_ceiling"] == 0


def test_three_px_halo_matches_disk_geometry():
    supp = np.zeros((21, 21), bool); supp[10, 10] = True
    halo = dce.three_px_halo(supp)
    yy, xx = np.mgrid[0:21, 0:21]
    expect = (yy - 10) ** 2 + (xx - 10) ** 2 <= 9
    assert np.array_equal(halo, expect) and halo.sum() == 29


def test_packed_halo_roundtrip():
    rng = np.random.default_rng(3)
    h = rng.random((37, 29)) < 0.3
    bits = dce.pack_halo(h)
    assert bits.dtype == np.uint8 and bits.ndim == 1
    assert np.array_equal(dce.unpack_halo(bits, h.shape), h)
    # packed halos are accepted by place_capped and give identical dots
    surface = rng.random((37, 29)).astype(np.float32)
    allowed = np.ones((37, 29), bool)
    d1, _ = dce.place_capped(surface, allowed, 20, {"h": h}, ceiling=0.9)
    d2, _ = dce.place_capped(surface, allowed, 20, {"h": bits}, ceiling=0.9)
    assert np.array_equal(d1, d2)
