"""Unit and regression checks for scripts/scan_tracked_rasters.py and requirements.txt."""
import importlib.util
from pathlib import Path
import re

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("scan_tracked_rasters", ROOT / "scripts" / "scan_tracked_rasters.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _write_tif(path: Path, arr: np.ndarray, nodata=None) -> None:
    if arr.ndim == 2:
        arr = arr[None, ...]
    profile = dict(
        driver="GTiff",
        height=arr.shape[1],
        width=arr.shape[2],
        count=arr.shape[0],
        dtype=str(arr.dtype),
        crs="EPSG:32611",
        transform=from_origin(0, 100, 100, 100),
        nodata=nodata,
    )
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr)


def test_detects_float32_min_sentinel_that_causes_portal_range_error(tmp_path: Path):
    arr = np.zeros((4, 4), dtype=np.float32)
    arr[0, 0] = np.float32(-3.4028235e38)
    arr[1, 1] = 1.0
    p = tmp_path / "sentinel.tif"
    _write_tif(p, arr, nodata=float(np.float32(-3.4028235e38)))
    rec = mod.scan_one(p)
    assert rec["n_sentinel"] == 1
    assert rec["n_outside_0_1"] == 1
    assert rec["min"] < -1e30


def test_scans_all_bands_and_catches_out_of_range_second_band(tmp_path: Path):
    arr = np.zeros((2, 3, 3), dtype=np.float32)
    arr[0, :, :] = 0.5  # band 1 clean
    arr[1, 2, 2] = 1.75  # band 2 violates [0, 1]
    p = tmp_path / "multiband.tif"
    _write_tif(p, arr)
    rec = mod.scan_one(p)
    assert rec["count"] == 2
    assert rec["bands_checked"] == 2
    assert rec["n_outside_0_1"] == 1
    assert rec["max"] == pytest.approx(1.75)


def test_refuses_overwrite_without_force(tmp_path: Path, monkeypatch):
    p = tmp_path / "clean.tif"
    _write_tif(p, np.array([[0.0, 1.0], [np.nan, 0.25]], dtype=np.float32))
    all_nan = tmp_path / "all_nan.tif"
    _write_tif(all_nan, np.full((2, 2), np.nan, dtype=np.float32))
    monkeypatch.setattr(mod, "tracked_tifs", lambda: [str(p), str(all_nan)])
    out = tmp_path / "out.json"
    assert mod.main(["--out", str(out)]) == 0
    import json
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert str(all_nan) in doc["flagged_outside_0_1_or_error"]
    assert str(p) not in doc["flagged_outside_0_1_or_error"]
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        mod.main(["--out", str(out)])
    assert mod.main(["--out", str(out), "--force"]) == 0


def test_requirements_txt_has_no_duplicate_package_specifiers():
    lines = [
        ln.strip()
        for ln in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    pkg_names = [re.split(r"[<>=!~\[\s]", ln, maxsplit=1)[0].lower().replace("_", "-") for ln in lines]
    assert len(pkg_names) == len(set(pkg_names)), f"Duplicate package(s) in requirements.txt: {pkg_names}"
