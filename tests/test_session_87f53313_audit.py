"""Regression tests for session 87f53313 code fixes and repository invariants.

Uses synthetic fixtures and local repository metadata only; never runs a
competition experiment or modifies frozen evidence receipts.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from bs4 import BeautifulSoup
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems79.evidence_summary import load_json  # noqa: E402
import check_site as check_site_mod  # noqa: E402
import verify_overlap_witness as witness_mod  # noqa: E402


def _load_script_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


scan_mod = _load_script_module("scan_tracked_rasters", "scripts/scan_tracked_rasters.py")
halo_mod = _load_script_module("measure_registry_halo_87f", "scripts/measure_registry_halo.py")


def test_no_duplicate_dict_keys_in_scripts_or_src():
    duplicates = []
    for folder in ("scripts", "src"):
        for path in sorted((ROOT / folder).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Dict):
                    seen: set[str] = set()
                    for key in node.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            if key.value in seen:
                                duplicates.append(f"{path.relative_to(ROOT)}:{key.lineno}:{key.value}")
                            seen.add(key.value)
    assert duplicates == []


def test_requirements_txt_has_unique_package_specifiers():
    pkgs = []
    for raw in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pkg = re.split(r"[<>=!~;\[\s]", line, maxsplit=1)[0].lower()
        pkgs.append(pkg)
    assert len(pkgs) == len(set(pkgs)), f"Duplicate package declarations in requirements.txt: {pkgs}"


def test_verify_overlap_witness_normalizes_relative_path_and_creates_nested_report_dir(tmp_path, monkeypatch):
    # Re-use live repo witness if restored, or synthesize via witness_root pattern.
    cache_tif = ROOT / ".cache/registry" / f"{witness_mod.UNIVERSAL_WITNESS_BLOB}.tif"
    if cache_tif.is_file():
        report = witness_mod.verify_witness(ROOT, restore=False)
        wf = report["measured_certificate"]["witness_file"]
        assert wf == f".cache/registry/{witness_mod.UNIVERSAL_WITNESS_BLOB}.tif"
        assert "/home/user/" not in json.dumps(report)

        nested_out = tmp_path / "nested" / "sub" / "witness_report.json"
        monkeypatch.setattr(sys, "argv", ["verify_overlap_witness.py", "--report", str(nested_out)])
        assert witness_mod.main() == 0
        written = load_json(nested_out)
        assert written["all_checks_passed"] is True
        assert "/home/user/" not in nested_out.read_text(encoding="utf-8")


def test_scan_tracked_rasters_flags_multiband_and_nodata_sentinel_and_protects_existing_out(tmp_path, monkeypatch):
    transform = from_origin(0, 400, 100, 100)

    # 1) Multi-band raster where band 1 is valid [0,1] and band 2 has 1.5 -> must flag!
    mb_path = tmp_path / "multiband.tif"
    with rasterio.open(
        mb_path, "w", driver="GTiff", height=4, width=4, count=2,
        dtype="float32", crs="EPSG:32611", transform=transform, nodata=None,
    ) as dst:
        dst.write(np.zeros((4, 4), dtype="float32"), 1)
        b2 = np.zeros((4, 4), dtype="float32")
        b2[2, 2] = 1.5
        dst.write(b2, 2)
    rec_mb = scan_mod.scan_one("multiband.tif", root=tmp_path)
    assert rec_mb["count"] == 2
    assert rec_mb["n_outside_0_1"] == 1
    assert scan_mod.is_flagged(rec_mb) is True

    # 2) Single-band raster with valid [0,1] values but toxic float32 sentinel nodata tag -> must flag!
    sent_path = tmp_path / "sentinel_nodata.tif"
    with rasterio.open(
        sent_path, "w", driver="GTiff", height=4, width=4, count=1,
        dtype="float32", crs="EPSG:32611", transform=transform, nodata=-3.4028234663852886e38,
    ) as dst:
        dst.write(np.zeros((4, 4), dtype="float32"), 1)
    rec_sent = scan_mod.scan_one("sentinel_nodata.tif", root=tmp_path)
    assert rec_sent["nodata_outside_0_1"] is True
    assert scan_mod.is_flagged(rec_sent) is True

    # 3) Single-band raster with nodata=NaN and valid [0,1] interior -> not flagged, nodata_is_nan=True
    nan_path = tmp_path / "nan_nodata.tif"
    arr_nan = np.zeros((4, 4), dtype="float32")
    arr_nan[0, :] = np.nan
    arr_nan[2, 2] = 1.0
    with rasterio.open(
        nan_path, "w", driver="GTiff", height=4, width=4, count=1,
        dtype="float32", crs="EPSG:32611", transform=transform, nodata=float("nan"),
    ) as dst:
        dst.write(arr_nan, 1)
    rec_nan = scan_mod.scan_one("nan_nodata.tif", root=tmp_path)
    assert rec_nan["nodata"] is None
    assert rec_nan["nodata_is_nan"] is True
    assert rec_nan["nodata_outside_0_1"] is False
    assert scan_mod.is_flagged(rec_nan) is False

    # 4) CLI refuses to overwrite existing output file unless --overwrite is passed, and handles external tmp_path
    existing = tmp_path / "out" / "scan.json"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("immutable\n", encoding="utf-8")
    monkeypatch.setattr(scan_mod, "tracked_tifs", lambda root=ROOT: [])
    monkeypatch.setattr(sys, "argv", ["scan_tracked_rasters.py", "--out", str(existing)])
    with pytest.raises((FileExistsError, SystemExit)):
        scan_mod.main()
    assert existing.read_text(encoding="utf-8") == "immutable\n"

    fresh = tmp_path / "out" / "fresh_scan.json"
    monkeypatch.setattr(sys, "argv", ["scan_tracked_rasters.py", "--out", str(fresh)])
    assert scan_mod.main() == 0
    assert load_json(fresh)["n_tracked_rasters"] == 0


def test_measure_registry_halo_computes_off_catalogue_domain_and_pigeonhole(tmp_path):
    transform = from_origin(0, 1000, 100, 100)
    fp = np.ones((10, 10), dtype="float32")
    fp[0, :] = np.nan  # 90 finite footprint cells
    cat = np.zeros((10, 10), dtype="float32")
    cat[1, :5] = 1.0  # 5 catalogue cells inside footprint -> 85 allowed off-catalogue cells
    reg = np.zeros((10, 10), dtype="float32")
    reg[5, 5] = 1.0  # 1 dot at (5,5): radius-3 disk covers 29 cells, all in rows 2..8 (off catalogue)

    for name, arr in (
        ("sample_submission.tif", fp),
        ("existing_faults.tif", cat),
        ("reg.tif", reg),
    ):
        with rasterio.open(
            tmp_path / name, "w", driver="GTiff", height=10, width=10, count=1,
            dtype="float32", crs="EPSG:32611", transform=transform, nodata=None,
        ) as dst:
            dst.write(arr, 1)

    out = halo_mod.measure(tmp_path / "reg.tif", tmp_path / "sample_submission.tif", radius_px=3)
    assert out["allowed_cells_finite_footprint"] == 90
    assert out["catalogue_positive_cells_in_footprint"] == 5
    assert out["off_catalogue_allowed_cells"] == 85
    assert out["off_catalogue_halo_covered_cells"] == 29
    assert out["off_catalogue_uncovered_cells"] == 56

    bad_cat = tmp_path / "bad_cat.tif"
    with rasterio.open(
        bad_cat, "w", driver="GTiff", height=8, width=8, count=1,
        dtype="float32", crs="EPSG:32611", transform=transform, nodata=None,
    ) as dst:
        dst.write(np.zeros((8, 8), dtype="float32"), 1)
    with pytest.raises(ValueError, match="catalogue raster grid"):
        halo_mod.measure(
            tmp_path / "reg.tif", tmp_path / "sample_submission.tif",
            radius_px=3, catalogue_path=bad_cat,
        )
    with pytest.raises(FileNotFoundError):
        halo_mod.measure(
            tmp_path / "reg.tif", tmp_path / "sample_submission.tif",
            radius_px=3, catalogue_path=tmp_path / "missing_cat.tif",
        )


def test_check_site_detects_stale_irregularities_html(tmp_path, monkeypatch):
    # Verify that check_site() fails if reports/irregularities.md has an extra IR row absent from docs/irregularities.html.
    orig_ir = (ROOT / "reports/irregularities.md").read_text(encoding="utf-8")
    real_read_text = Path.read_text

    def fake_read_text(self: Path, *args, **kwargs):
        if self.resolve() == (ROOT / "reports/irregularities.md").resolve():
            return orig_ir + "\n| IR-79-99999 | synthetic stale check | synthetic resolution |\n"
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    with pytest.raises(AssertionError, match="out of sync with reports/irregularities.md"):
        check_site_mod.check_site()


def test_session_87f53313_evidence_strict_json_and_no_workspace_path_leaks():
    ev_dir = ROOT / "evidence" / "review_87f53313"
    json_files = sorted(ev_dir.glob("*.json"))
    assert len(json_files) == 8
    for path in json_files:
        raw = path.read_text(encoding="utf-8")
        assert "/home/user/" not in raw, f"Workspace path leaked in {path}"
        parsed = load_json(path)
        assert isinstance(parsed, dict)
    ir_txt = (ROOT / "reports/irregularities.md").read_text(encoding="utf-8")
    for ir_id in ("IR-79-188", "IR-79-189", "IR-79-190"):
        assert ir_id in ir_txt
