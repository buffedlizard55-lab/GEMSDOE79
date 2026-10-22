"""G79-CONJ channel/emission unit tests (synthetic geometry, no data needed)."""
import numpy as np

from gems79.conj import CONJ_FEATURE_NAMES, adaptive_dinkelbach_emit, compute_conj_channels


def _scene():
    H, W = 60, 80
    fp = np.ones((H, W), bool)
    vis = np.zeros((H, W), bool)
    vis[10:50, 40] = True          # N-S master strand
    vis[30, 40:60] = True          # E-W branch -> junction at (30, 40)
    depth = np.tile(np.linspace(0, 1000, W), (H, 1))  # deepens east
    return fp, vis, depth


def test_conj_channels_shape_finite_and_side_logic():
    fp, vis, depth = _scene()
    X = compute_conj_channels(vis, fp, depth)
    assert X.shape == (fp.sum(), len(CONJ_FEATURE_NAMES))
    assert np.isfinite(X).all()
    g = X.reshape(60, 80, -1)
    hw_near = CONJ_FEATURE_NAMES.index("conj_hw_near")
    fw_near = CONJ_FEATURE_NAMES.index("conj_fw_near")
    # Basement deepens east: east offset cell is hanging-wall, west is footwall.
    assert g[20, 45, hw_near] > 0.5
    assert g[20, 45, fw_near] == 0.0
    assert g[20, 35, fw_near] > 0.5
    assert g[20, 35, hw_near] == 0.0
    # Far corner: no conjugate signal.
    assert g[2, 2, hw_near] < 0.05


def test_conj_junction_proximity():
    fp, vis, depth = _scene()
    X = compute_conj_channels(vis, fp, depth).reshape(60, 80, -1)
    j = CONJ_FEATURE_NAMES.index("conj_junc_10")
    assert X[30, 45, j] > X[5, 5, j] + 0.5


def test_conj_empty_visible_is_zeros():
    fp, _, depth = _scene()
    X = compute_conj_channels(np.zeros_like(fp), fp, depth)
    assert X.shape == (fp.sum(), 12)
    assert float(X.max()) == 0.0


def test_dinkelbach_places_on_mass_and_stops():
    H, W = 40, 40
    p = np.zeros((H, W), np.float32)
    p[10, 10] = 0.9
    p[25, 30] = 0.8
    q = p.copy()
    allowed = np.ones((H, W), bool)
    out, info = adaptive_dinkelbach_emit(p, q, allowed, min_budget=2, max_budget=50,
                                         candidate_pool=2000, lambda_update_every=2)
    pts = {tuple(r) for r in np.argwhere(out > 0)}
    assert (10, 10) in pts and (25, 30) in pts
    assert set(np.unique(out)) <= {0.0, 1.0}
    assert info["emitted_dots"] == len(pts) >= 2
    assert info["stop_reason"] in ("marginal_utility_nonpositive", "budget_cap")
