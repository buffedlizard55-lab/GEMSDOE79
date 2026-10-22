"""Regression tests for chance-calibrated-v4 (IR-79-139) and registry delta path filter (IR-79-138)."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import rasterio
from affine import Affine

from gems57 import uniqueness
from gems79.uniqueness_v4 import compare_array_to_registry_v4
from scripts.registry_delta_git import is_prediction


def _write_test_tif(path: Path, arr: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=arr.shape[0],
        width=arr.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine.translation(243350.0, 4508550.0) @ Affine.scale(100.0, -100.0),
    ) as dst:
        dst.write(arr.astype(np.float32), 1)


def test_chance_calibrated_v4_handles_lattice_vs_subsample_vs_sparse_duplicate(tmp_path: Path) -> None:
    shape = (100, 100)
    fp = np.ones(shape, dtype=bool)
    cat = np.zeros(shape, dtype=bool)
    cat[0, :] = True
    allowed = fp & ~cat

    lattice = np.zeros(shape, dtype=np.float32)
    lattice[2::5, 2::5] = 1.0
    lattice[cat] = 0.0
    lattice_path = tmp_path / "lattice.tif"
    _write_test_tif(lattice_path, lattice)

    plateau = np.full(shape, 0.5, dtype=np.float32)
    plateau_path = tmp_path / "plateau.tif"
    _write_test_tif(plateau_path, plateau)

    sparse = np.zeros(shape, dtype=np.float32)
    sparse[15, 10:90:4] = 1.0
    sparse_path = tmp_path / "sparse.tif"
    _write_test_tif(sparse_path, sparse)

    idx = {
        "complete_accessible_scan": True,
        "rasters": [
            {"repo_first": "13GEMSDOE", "sources": ["lattice"], "cache_file": str(lattice_path), "sha256": uniqueness._sha(lattice_path)},
            {"repo_first": "GEMSDOE48", "sources": ["plateau"], "cache_file": str(plateau_path), "sha256": uniqueness._sha(plateau_path)},
            {"repo_first": "GEMSDOE53", "sources": ["sparse"], "cache_file": str(sparse_path), "sha256": uniqueness._sha(sparse_path)},
        ],
    }

    rng = np.random.default_rng(7901)
    cand_indep = np.zeros(shape, dtype=np.float32)
    allowed_idx = np.flatnonzero(allowed)
    cand_indep.ravel()[rng.choice(allowed_idx, size=40, replace=False)] = 1.0

    r_v3 = uniqueness.compare_array_to_registry(cand_indep, idx, fp, dot_definition="budget-matched-v3", allowed=allowed)
    r_v4 = compare_array_to_registry_v4(cand_indep, idx, fp, allowed=allowed)
    assert r_v3["unique"] is False and r_v3["duplicate_count"] == 2
    assert r_v4["unique"] is True and r_v4["duplicate_count"] == 0
    assert r_v4["worst_informative_dot_overlap"] <= 0.70

    cand_sub = np.zeros(shape, dtype=np.float32)
    lat_pts = np.flatnonzero(lattice > 0)
    cand_sub.ravel()[rng.choice(lat_pts, size=40, replace=False)] = 1.0
    r_sub = compare_array_to_registry_v4(cand_sub, idx, fp, allowed=allowed)
    assert r_sub["unique"] is False and r_sub["duplicate_count"] >= 1
    assert any(r["submission"] == "lattice" and r["duplicate_by_overlap"] for r in r_sub["rows"])

    cand_sparse_dup = sparse.copy()
    r_sp = compare_array_to_registry_v4(cand_sparse_dup, idx, fp, allowed=allowed)
    assert r_sp["unique"] is False
    assert any(r["submission"] == "sparse" and r["duplicate_by_overlap"] for r in r_sp["rows"])


def test_delta_filter_excludes_raw_inputs_and_catches_archived_predictions() -> None:
    assert not is_prediction("data/raw/existing_faults.tif")
    assert not is_prediction("data/sample_submission.tif")
    assert is_prediction("docs/downloads/cand.tif")
    assert is_prediction("docs/archive/cand.tif")
