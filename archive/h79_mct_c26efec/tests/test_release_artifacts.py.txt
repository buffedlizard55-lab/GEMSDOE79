"""Consistency of the shipped artefacts (skipped when they are absent, e.g. on a fresh clone)."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
rasterio = pytest.importorskip("rasterio")


def _status():
    p = ROOT / "docs" / "status.json"
    if not p.exists():
        pytest.skip("no status.json yet")
    return json.loads(p.read_text())


def test_status_file_hash_and_name_agree_with_run_card_and_tif():
    st = _status()
    card = json.loads((ROOT / "evidence" / "run_card_h79.json").read_text())
    tif = ROOT / "docs" / st["file"]
    assert tif.exists()
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == st["sha256"] == card["raster"]["sha256"]
    assert st["name"] == card["raster"]["name"] and tif.stem == st["name"]
    assert len(st["note"]) <= 140 and st["note"].strip()
    assert st["ok_to_submit"] == (card["verdict"] == "promote")


def test_tif_is_single_band_float32_unit_interval_on_the_sample_grid():
    st = _status()
    tif = ROOT / "docs" / st["file"]
    with rasterio.open(tif) as src:
        assert src.count == 1 and src.dtypes[0] == "float32"
        assert src.crs.to_epsg() == 32611 and src.shape == (3730, 3292)
        assert list(src.transform)[:6] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
        a = src.read(1)
    assert np.isfinite(a).all() and a.min() >= 0.0 and a.max() <= 1.0
    assert int((a > 0).sum()) == st["dots"]


def test_no_positive_mass_on_catalogue_when_bridge_is_present():
    st = _status()
    bridge = ROOT / "data" / "bridge" / "existing_faults.tif"
    if not bridge.exists():
        pytest.skip("bridge rasters not restored")
    with rasterio.open(ROOT / "docs" / st["file"]) as src:
        a = src.read(1)
    with rasterio.open(bridge) as src:
        cat = src.read(1) == 1
    assert not (a[cat] > 0).any()


def test_every_holdout_number_is_labelled():
    card_p = ROOT / "evidence" / "run_card_h79.json"
    if not card_p.exists():
        pytest.skip("no run card yet")
    card = json.loads(card_p.read_text())
    for seed, h in card["holdout"].items():
        assert h["evidence_class"] == "HOLDOUT-DTI"
        assert h["evaluator_version"] == "gems57-pooled-hide-v2"
        assert h["withheld_positive_pixels"] > 10_000
        assert len(h["ci95"]) == 2 and h["ci95"][0] <= h["dti"] <= h["ci95"][1]
    assert card["organizer_confirmed_score"] is None or isinstance(card["organizer_confirmed_score"], float)
