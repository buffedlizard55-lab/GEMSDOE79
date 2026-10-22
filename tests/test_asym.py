"""H79-ASYM surface: decoding rule, clip, footprint and preregistration pins."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from gems79 import asym

ROOT = Path(__file__).resolve().parents[1]


def test_sqrt_decode_matches_product_quantisation():
    # q = 1 + round(254 * sqrt(x / xmax)) with xmax = 1  =>  x = ((q - 1) / 254) ** 2
    # q = 0 (no lidar) is masked by the caller in asym.build, never decoded here.
    q = np.array([1, 128, 255], np.uint8)
    got = asym._decode_sqrt(q, 1.0)
    assert got[0] == pytest.approx(0.0)
    assert got[1] == pytest.approx((127 / 254) ** 2)
    assert got[2] == pytest.approx(1.0)


def test_linear_decode_range():
    q = np.array([1, 128, 255], np.uint8)
    got = asym._decode_linear(q, 1.0)
    assert got[0] == pytest.approx(0.0)
    assert got[1] == pytest.approx(127 / 254)
    assert got[2] == pytest.approx(1.0)


def test_build_is_bounded_and_footprint_limited(tmp_path):
    # Synthetic 3-band lidar file: upface dominant on the left half, downface on the right.
    import rasterio
    from rasterio.transform import from_origin

    h, w = 40, 60
    up = np.zeros((h, w), np.uint8)
    dn = np.zeros((h, w), np.uint8)
    coh = np.zeros((h, w), np.uint8)
    up[:, :30] = 200
    dn[:, :30] = 50
    coh[:, :30] = 240
    up[:, 30:] = 40
    dn[:, 30:] = 200
    coh[:, 30:] = 240
    path = tmp_path / "lidar.tif"
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=3, dtype="uint8",
                       crs="EPSG:32611", transform=from_origin(0, 0, 100, 100)) as dst:
        dst.write(up, 1)
        dst.write(dn, 2)
        dst.write(coh, 3)
        dst.descriptions = ("upface_max", "downface_max", "coh100")
    fp = np.ones((h, w), bool)
    fp[:, -5:] = False
    art = asym.build(fp, lidar_path=path)
    S = art["S"]
    assert np.isfinite(S).all()
    assert S.min() >= 0.0 and S.max() <= 1.0
    assert (S[:, -5:] == 0).all()           # outside the footprint
    assert (S[:, 30:] == 0).all()           # downface dominates: no antislope excess
    assert S[:, :30].max() > 0              # antislope excess present on the left


def test_surface_preregistration_pins_match_code():
    prereg = json.loads((ROOT / "registry/preregistration_asym.json").read_text())
    assert prereg["lane"] == "H79-ASYM"
    assert prereg["fixed_parameters"]["budget_full_footprint"] == 37654
    assert prereg["registered_before_any_result"] is True
    lidar = ROOT / "data/raw/external/lidar_scarp_features_u8.tif"
    if lidar.exists():
        digest = hashlib.sha256(lidar.read_bytes()).hexdigest()
        assert digest == "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568"
