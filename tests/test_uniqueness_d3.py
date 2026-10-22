"""Amendment D-3 (IR-79-229): chance-corrected saturated-halo branch.

D-3 changes ONLY the branch of D-2 that applies when a prior's 3 px halo
saturates the allowed domain. The default ('exact-d2') must reproduce D-2
exactly; the D-3 branch must still catch lattice copies and stop plateau
diagnostics (dot-equivalent set = whole allowed domain) from vetoing every map.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.uniqueness import (  # noqa: E402
    HALO_SATURATION, d2_row_decision, d3_exact_decision)


def test_default_branch_is_unchanged_d2():
    a = d2_row_decision(forward_overlap=1.0, halo_coverage=1.0, exact_overlap=1.0,
                        spearman=0.0, identical=False)
    assert a["overlap_test"] == "exact_cell_halo_saturated" and a["duplicate_d2"] is True
    assert "saturated_branch" not in a


def test_plateau_prior_is_noninformative_under_d3_but_rho_still_binds():
    d = d2_row_decision(forward_overlap=1.0, halo_coverage=1.0, exact_overlap=1.0,
                        spearman=0.0013, identical=False,
                        saturated_branch="chance-corrected-d3", exact_expected=1.0)
    assert d["duplicate_d2"] is False
    assert d["overlap_test"] == "exact_cell_plateau_noninformative_d3"
    r = d2_row_decision(forward_overlap=1.0, halo_coverage=1.0, exact_overlap=1.0,
                        spearman=0.95, identical=False,
                        saturated_branch="chance-corrected-d3", exact_expected=1.0)
    assert r["duplicate_d2"] is True
    i = d2_row_decision(forward_overlap=1.0, halo_coverage=1.0, exact_overlap=1.0,
                        spearman=0.0, identical=True,
                        saturated_branch="chance-corrected-d3", exact_expected=1.0)
    assert i["duplicate_d2"] is True


def test_lattice_copy_still_duplicate_and_chance_lattice_passes():
    e = 206_895 / 5_106_385  # 13GEMSDOE lattice support over allowed cells
    copy = d2_row_decision(forward_overlap=1.0, halo_coverage=0.9995 + 0.0005,
                           exact_overlap=0.98, spearman=0.0, identical=False,
                           saturated_branch="chance-corrected-d3", exact_expected=e)
    assert copy["duplicate_d2"] is True
    chance = d2_row_decision(forward_overlap=1.0, halo_coverage=1.0,
                             exact_overlap=e, spearman=0.0, identical=False,
                             saturated_branch="chance-corrected-d3", exact_expected=e)
    assert chance["duplicate_d2"] is False


def test_unsaturated_branch_identical_between_d2_and_d3():
    for ov, h in [(0.913, 0.610), (0.814, 0.204), (0.615, 0.61), (0.70, 0.0)]:
        a = d2_row_decision(forward_overlap=ov, halo_coverage=h, exact_overlap=0.1,
                            spearman=0.1, identical=False)
        b = d2_row_decision(forward_overlap=ov, halo_coverage=h, exact_overlap=0.1,
                            spearman=0.1, identical=False,
                            saturated_branch="chance-corrected-d3", exact_expected=0.1)
        assert a["duplicate_d2"] == b["duplicate_d2"]
        assert a["overlap_test"] == b["overlap_test"] == "chance_corrected_halo"


def test_d3_requires_expectation_and_known_branch():
    with pytest.raises(ValueError):
        d3_exact_decision(0.5, None)
    with pytest.raises(ValueError):
        d2_row_decision(forward_overlap=1.0, halo_coverage=1.0, exact_overlap=1.0,
                        spearman=0.0, identical=False, saturated_branch="bogus")


def test_d3_threshold_algebra():
    by, corr, test = d3_exact_decision(0.71, 0.0)
    assert by is True and abs(corr - 0.71) < 1e-12
    by, corr, _ = d3_exact_decision(0.80, 0.5)  # corrected 0.6 <= 0.70
    assert by is False and abs(corr - 0.6) < 1e-12
    by, corr, test = d3_exact_decision(1.0, HALO_SATURATION)
    assert by is False and corr is None and test.endswith("noninformative_d3")


def test_end_to_end_small_grid_plateau_and_copy(tmp_path):
    import rasterio
    from rasterio.transform import from_origin
    from gems57.uniqueness import compare_array_to_registry_d2
    H = W = 60
    fp = np.ones((H, W), bool)
    allowed = fp.copy()
    rng = np.random.default_rng(1)
    cand = np.zeros((H, W), bool)
    cand.ravel()[rng.choice(H * W, 80, replace=False)] = True
    plateau = np.full((H, W), 0.5, np.float32)
    files = []
    for name, arr in (("plateau", plateau), ("copy", cand.astype(np.float32))):
        p = tmp_path / f"{name}.tif"
        with rasterio.open(p, "w", driver="GTiff", height=H, width=W, count=1,
                           dtype="float32", crs="EPSG:32611",
                           transform=from_origin(0, 0, 100, 100)) as dst:
            dst.write(arr, 1)
        files.append(dict(repo="t", submission=name, file=str(p), sha256=None))
    d2 = compare_array_to_registry_d2(cand, files, fp, allowed)
    d3 = compare_array_to_registry_d2(cand, files, fp, allowed,
                                      saturated_branch="chance-corrected-d3")
    fire2 = {f["submission"] for f in d2["d2_firings"]}
    fire3 = {f["submission"] for f in d3["d2_firings"]}
    assert fire2 == {"plateau", "copy"}
    assert fire3 == {"copy"}
    assert d3["gate"] == "amendment-D3" and d2["gate"] == "amendment-D2"
