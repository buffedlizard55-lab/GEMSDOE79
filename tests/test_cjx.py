import numpy as np
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "src"),
                str(Path(__file__).resolve().parents[1] / "vendor")]
from gems79.cjx import build_cjx, catalogue_endpoints


def test_cjx_catalogue_free_and_bounded():
    rng = np.random.default_rng(0)
    fp = np.ones((60, 60), bool)
    bands = {"rtp": rng.normal(size=(60, 60)).astype(np.float32),
             "iso_grav_anom": rng.normal(size=(60, 60)).astype(np.float32)}
    out = build_cjx(bands, fp)
    for v in out.values():
        assert np.isfinite(v).all()


def test_cjx_step_edge_scores_above_noise():
    fp = np.ones((80, 80), bool)
    step = np.where(np.indices((80, 80))[1] > 40, 10.0, -10.0).astype(np.float32)
    noise = np.random.default_rng(1).normal(size=(80, 80)).astype(np.float32)
    a = build_cjx({"rtp": step, "iso_grav_anom": step}, fp)["cjx_v1_edge"]
    b = build_cjx({"rtp": noise, "iso_grav_anom": noise}, fp)["cjx_v1_edge"]
    assert a[:, 39:42].mean() > b.mean()  # coincident step ridge beats noise background


def test_endpoints():
    vis = np.zeros((10, 10), bool)
    vis[5, 2:6] = True
    ep = catalogue_endpoints(vis)
    assert ep[5, 2] and ep[5, 5] and ep.sum() == 2


def test_cjx_gate_fails_closed_on_incomplete_registry_and_runs_clean_readonly():
    import json
    import subprocess
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "scripts"))
    import cjx_gate
    assert cjx_gate.evaluate_novelty_bounds(
        n_checked=0, n_expected=992, rho_surface=0.0, rho_dots=0.0, overlap_dots=0.0
    ) is False
    assert cjx_gate.evaluate_novelty_bounds(
        n_checked=991, n_expected=992, rho_surface=0.1, rho_dots=0.1, overlap_dots=0.2
    ) is False
    assert cjx_gate.evaluate_novelty_bounds(
        n_checked=992, n_expected=992, rho_surface=0.1, rho_dots=0.1, overlap_dots=0.2
    ) is True

    before = (root / "run_card_cjx.json").read_bytes()
    proc = subprocess.run([sys.executable, str(root / "scripts/cjx_gate.py"), "--verify-readonly"], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 2
    out = json.loads(proc.stdout)
    assert out["ok_to_download"] is True
    assert out["ok_to_submit"] is False
    assert out["gates_passed"]["G1_format"] is True
    assert out["gates_passed"]["G2_canary"] is True
    assert out["gates_passed"]["G3_holdout"] is False
    assert out["gates_passed"]["G4_novelty"] is False
    assert (root / "run_card_cjx.json").read_bytes() == before

