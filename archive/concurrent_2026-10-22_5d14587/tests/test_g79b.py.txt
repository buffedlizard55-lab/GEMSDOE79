"""G79B lane: synthetic feature-build invariants + frozen-evidence coherence."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine

from gems79 import features_g79b

ROOT = Path(__file__).resolve().parents[1]
H = W = 24
TRANSFORM = Affine(100, 0, 1000, 0, -100, 3000)


def _write(path, bands, dtype, descriptions=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, 'w', driver='GTiff', width=W, height=H, count=len(bands),
                       dtype=dtype, crs='EPSG:32611', transform=TRANSFORM) as dst:
        for i, b in enumerate(bands, 1):
            dst.write(b.astype(dtype), i)
        if descriptions:
            dst.descriptions = descriptions


def test_build_synthetic_invariants(tmp_path):
    rng = np.random.default_rng(7)
    raw = tmp_path / 'raw'
    # 19-band stack: only bands 3 and 18 carry signal in this fixture.
    stack = [rng.random((H, W), dtype=np.float32) for _ in range(19)]
    _write(raw / features_g79b.STACK, stack, 'float32')
    lidar = [rng.integers(1, 255, (H, W)) for _ in range(12)]
    lidar[11] = np.full((H, W), 255)          # valid: full coverage
    lidar[11][:4] = 0                          # top rows unsupported
    _write(raw / features_g79b.LIDAR, lidar, 'uint8')
    roads = np.full((H, W), 1000.0, np.float32)
    roads[:, :3] = 0.0                         # road-adjacent columns
    _write(raw / features_g79b.ROADS, [roads], 'float32')
    footprint = np.ones((H, W), bool)
    footprint[:, -2:] = False
    out = tmp_path / 'cache'
    counts = features_g79b.build(raw, footprint, out)
    surface = np.load(out / 'scarp_dipole_surface.npy')
    support = np.load(out / 'support.npy')
    lidar_only = np.load(out / 'lidar_only_surface.npy')
    geo_only = np.load(out / 'geo_only_surface.npy')
    # Support excludes no-lidar rows and out-of-footprint columns.
    assert not support[:4].any() and not support[:, -2:].any()
    assert counts['support_cells'] == int(support.sum())
    # Every exported feature is finite in [0,1] and zero outside support.
    for name in features_g79b.FEATURE_NAMES:
        a = np.load(out / f'{name}.npy')
        assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
    for a in (surface, lidar_only, geo_only):
        assert not (a[~support] > 0).any()
    # Candidate is exactly the geometric mean of the two control surfaces,
    # so it can never exceed both of them (AND-consensus, no amplification).
    geomean = np.sqrt(lidar_only * geo_only)
    assert np.allclose(surface, geomean, atol=1e-6)
    assert (surface <= np.maximum(lidar_only, geo_only) + 1e-6).all()
    # Road-adjacent cells carry the 0.1 suppression factor.
    seg = support & (np.indices((H, W))[1] < 3)
    assert np.allclose(np.load(out / 'road_factor.npy')[seg], 0.1)


def test_preregistration_and_card_are_consistent():
    pin = (ROOT / 'evidence/preregistration_g79b_sha256.txt').read_text().strip()
    assert hashlib.sha256((ROOT / 'registry/preregistration_g79b.json').read_bytes()).hexdigest() == pin
    card = json.loads((ROOT / 'run_card.json').read_text())
    assert card == json.loads((ROOT / 'run_card_g79b.json').read_text())
    assert card['preregistration_sha256'] == pin
    assert card['experiment_count'] == 1 and card['experiment2_contingency_condition_met'] is False
    for seed in (20, 30):
        h = json.loads((ROOT / f'evidence/holdout_g79b_seed{seed}.json').read_text())
        assert h['scores']['candidate']['dti'] == card['holdout_dti_by_seed'][f'seed_{seed}']['dti']
        assert h['scores']['candidate']['dti'] < h['scores']['h33_foldfair_control']['dti']
        assert h['paired_differences']['h33_foldfair_control']['ci95'][1] < 0
    # Uniqueness stayed inside preregistered operative limits on both phases.
    surf = json.loads((ROOT / 'evidence/uniqueness_surface_g79b.json').read_text())
    fin = json.loads((ROOT / 'evidence/uniqueness_final_g79b.json').read_text())
    assert surf['max_abs_spearman'] <= 0.90 and surf['passed_optionB_and_rho']
    assert fin['max_forward_overlap_3px_optionB'] <= 0.70 and fin['passed_optionB_and_C']
    assert card['protocol_unique'] is False  # literal full-registry rule stays uncleared
