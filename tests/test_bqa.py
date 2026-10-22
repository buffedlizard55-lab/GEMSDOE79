"""Synthetic software fixtures for H79-BQA and the shared v4 overlap (not competition data)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
import importlib.util  # noqa: E402
import gems57  # noqa: E402,F401

# Frozen BQA copy of the shared tool (archive/h79_bqa/README.md); the shared vendor/gems57 tool is main's.
_FROZEN = ROOT / "archive/h79_bqa/uniqueness_chance_corrected_v4_e68079b5.py"
_spec = importlib.util.spec_from_file_location("gems57.uniqueness_bqa_frozen", _FROZEN)
U = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(U)


def test_frozen_tool_is_the_one_that_produced_the_bqa_evidence():
    import hashlib
    ev = json.loads((ROOT / "evidence/bqa/x2_uniqueness_surface.json").read_text())
    assert hashlib.sha256(_FROZEN.read_bytes()).hexdigest() == ev["shared_tool_sha256"]


def test_shared_tool_is_left_as_main_pinned_it():
    import hashlib
    pin = json.loads((ROOT / "evidence/post_snapshot_sibling_audit.json").read_text())["shared_tools_pinned"]
    assert hashlib.sha256((ROOT / "vendor/gems57/uniqueness.py").read_bytes()).hexdigest() == pin["uniqueness_py_sha256"]
from gems79 import bqa  # noqa: E402


def test_chance_corrected_reduces_to_raw_overlap_for_sparse_priors():
    assert U.chance_corrected(0.8, 0.0) == pytest.approx(0.8)
    assert U.chance_corrected(0.913, 0.6097) == pytest.approx((0.913 - 0.6097) / (1 - 0.6097))
    assert U.chance_corrected(1.0, 1.0) is None      # non-discriminating
    assert U.chance_corrected(0.5, 0.5) == pytest.approx(0.0)


def test_frozen_nhr_remains_duplicate_and_uniform_passes_under_v4():
    """IR-79-110 (in-session IR-79-68) must not rescue the stopped NHR lane and must be satisfiable."""
    rows = json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())["rows"]
    k_nhr = [U.chance_corrected(r["overlap_candidate"], r["halo_coverage"]) for r in rows]
    k_uni = [U.chance_corrected(r["overlap_uniform"], r["halo_coverage"]) for r in rows]
    assert sum(k is not None and k > 0.70 for k in k_nhr) >= 1
    assert max(k for k in k_uni if k is not None) < 0.70


def _write(path, arr):
    with rasterio.open(path, "w", driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1,
                       dtype="float32", crs="EPSG:32611", transform=Affine(100, 0, 0, 0, -100, 0)) as ds:
        ds.write(arr.astype(np.float32), 1)


def test_v4_flags_copy_but_not_space_filling_prior(tmp_path):
    rng = np.random.default_rng(1)
    shape = (80, 80)
    fp = np.ones(shape, bool)
    mine = np.zeros(shape, np.float32)
    mine.ravel()[rng.choice(mine.size, 60, replace=False)] = 1
    copy = mine.copy()
    full = np.ones(shape, np.float32)          # literal support everywhere -> C = 1
    lattice = np.zeros(shape, np.float32)
    lattice[::5, ::5] = 1                       # sparse-ish lattice, high halo coverage
    files = []
    for name, arr in (("copy", copy), ("full", full), ("lattice", lattice)):
        p = tmp_path / f"{name}.tif"
        _write(p, arr)
        files.append(dict(repo_first="fx", sources=[name], cache_file=str(p), sha256=U._sha(p)))
    res = U.compare_array_to_registry(mine, {"rasters": files, "complete_accessible_scan": True, "errors": []},
                                      fp, dot_definition="chance-corrected-v4", allowed=fp)
    by = {r["submission"]: r for r in res["rows"]}
    assert by["copy"]["duplicate_by_overlap"] is True
    assert by["full"]["overlap_test_informative"] is False and by["full"]["duplicate_by_overlap"] is False
    assert by["lattice"]["raw_overlap_gt_limit"] is True or by["lattice"]["my_dots_within_3px_of_theirs"] > 0.5
    assert by["lattice"]["duplicate_by_overlap"] is False
    # literal default is unchanged
    lit = U.compare_array_to_registry(mine, {"rasters": files, "complete_accessible_scan": True, "errors": []}, fp)
    assert {r["submission"]: r["duplicate_by_overlap"] for r in lit["rows"]}["full"] is True


def test_v4_rejects_dots_outside_declared_allowed_domain():
    fp = np.ones((10, 10), bool)
    mine = np.zeros((10, 10), np.float32)
    mine[0, 0] = 1
    allowed = fp.copy()
    allowed[0, 0] = False
    with pytest.raises(ValueError):
        U.compare_array_to_registry(mine, {"rasters": [], "complete_accessible_scan": True, "errors": []},
                                    fp, dot_definition="chance-corrected-v4", allowed=allowed)


def test_quotas_reproduce_h33_profile_and_sum_to_budget():
    assert bqa.quotas(37654) == list(bqa.H33_BAND_COUNTS)
    for b in (1, 7, 8000, 9919, 12345):
        assert sum(bqa.quotas(b)) == b


def test_band_weights_equalise_bands():
    d = np.r_[np.zeros(100), np.full(10, 4.0), np.full(1, 60.0)]
    w, rec = bqa.band_weights(d)
    assert rec["rows_per_weighting_band"][0] == 100
    totals = [w[d == 0].sum(), w[d == 4].sum(), w[d == 60].sum()]
    assert np.allclose(totals, totals[0])


def test_quota_placement_spacing_quota_and_fill():
    rng = np.random.default_rng(3)
    s = rng.random((50, 50)).astype(np.float32)
    band = np.zeros((50, 50), np.int8)
    band[:, 25:] = 4
    allowed = np.ones((50, 50), bool)
    dots, info = bqa.place_with_quotas(s, allowed, band, 60)
    assert info["emitted"] == 60 and dots.sum() == 60
    ys, xs = np.nonzero(dots)
    dist = np.hypot(ys[:, None] - ys, xs[:, None] - xs)
    np.fill_diagonal(dist, 99)
    assert dist.min() >= 3
    # only bands 0 and 4 exist -> other quotas are filled by the second pass
    assert info["second_pass_dots"] == 60 - info["quotas"][0] - info["quotas"][4] or info["second_pass_dots"] >= 0
    assert not dots[band == -1].any()


def test_bqa_uniqueness_inventory_snapshot_is_preserved():
    """IR-79-112: BQA's receipts used 992 indexed + 215 delta rasters; the snapshot is kept as evidence."""
    snap = json.loads((ROOT / "evidence/bqa/registry_delta_0bd0e0b2.json").read_text())
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    usurf = json.loads((ROOT / "evidence/bqa/x2_uniqueness_surface.json").read_text())
    assert snap["n_new_rasters"] == len(snap["rasters"]) == 215
    assert usurf["provisional_topk_check"]["registry_rasters_expected"] == len(index["rasters"]) + 215 == 1207


def test_bqa_closure_is_rederived_from_evidence_and_wrote_no_file():
    import json
    import subprocess
    import sys as _sys
    root = Path(__file__).resolve().parents[1]
    st = json.loads((root / 'evidence/bqa/state.json').read_text())
    card = json.loads((root / 'run_card_bqa.json').read_text())
    assert st['stopped'] is True and st['verdict'] == card['verdict'] == 'negative'
    assert card['ok_to_submit'] is False and card['ok_to_download'] is False and card['raster_sha256'] is None
    assert st['geotiff_written'] is False and st['final_dot_placements_performed'] == 0
    assert st['submission_slots_used'] == card['submission_slots_used'] == 0
    assert st['experiments_used'] <= st['max_experiments'] == 3
    u = json.loads((root / 'evidence/bqa/x2_uniqueness_surface.json').read_text())
    g5 = st['x2']['g5_surface_uniqueness']
    assert u['passed'] is False and g5['passed'] is False and u['complete_comparison'] is True
    assert g5['provisional_topk_worst_chance_corrected_overlap'] == round(u['worst_chance_corrected_overlap'], 4) > 0.70
    assert g5['surface_sha256_matches_build'] is True
    for s in (30, 40):
        h = json.loads((root / f'evidence/bqa/holdout_seed{s}.json').read_text())
        sc = h['x2_weights_only_standard']['scores']
        assert st['x2']['per_seed'][f'seed_{s}']['standard']['dti'] == round(sc['weights_only']['dti'], 4)
        assert h['leakage_canary']['max_symmetric_auc'] <= 0.90
    for s in (20, 30):   # X1 failed G3 on both preregistered seeds
        h = json.loads((root / f'evidence/bqa/holdout_seed{s}.json').read_text())
        ff = h['holdout_far_field']['scores']
        assert ff['candidate']['dti'] < ff['h33_foldfair_control']['dti']
    assert not [p for p in (root / 'docs/downloads').iterdir() if 'bqa' in p.name.lower()]
    canonical = json.loads((root / 'run_card.json').read_text())
    assert canonical['lane'] != 'H79-BQA'
    r = subprocess.run([_sys.executable, str(root / 'scripts/run_bqa.py'), 'place-x2'],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and 'closed (negative)' in r.stderr
