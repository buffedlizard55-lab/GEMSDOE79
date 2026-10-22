"""H79-ARC lane: allocator, features, gate statistics and terminal evidence."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems79.cover import place_cover


def test_cover_allocator_exact_budget_and_spacing():
    rng = np.random.default_rng(3)
    surf = rng.uniform(size=(60, 60)).astype(np.float32)
    allowed = np.ones((60, 60), bool)
    dots, meta = place_cover(surf, allowed, 200)
    assert int(dots.sum()) == 200 and meta["exhausted"] is False
    # 3 px spacing: no two dots closer than 3 px (Chebyshev >= 3 beyond self)
    ys, xs = np.nonzero(dots)
    for i in range(len(ys)):
        d = np.maximum(np.abs(ys - ys[i]), np.abs(xs - xs[i]))
        assert int((d < 3).sum()) == 1


def test_cover_allocator_line_objective():
    surf = np.zeros((40, 40), np.float32)
    surf[:, 20] = 1.0  # one bright line
    allowed = np.ones((40, 40), bool)
    dots, meta = place_cover(surf, allowed, 8)
    assert int(dots.sum()) == 8
    assert float(meta["expected_cover"]) > 0


def test_cover_allocator_rejects_bad_input():
    import pytest
    bad = np.zeros((10, 10), np.float32); bad[0, 0] = -1.0
    with pytest.raises(ValueError):
        place_cover(bad, np.ones((10, 10), bool), 5)


def test_overlap_beyond_chance_formula_in_evidence():
    rows = _ev("uniqueness_final_x2.json")["final_check"]["rows"]
    checked = 0
    for r in rows:
        exc, halo = r.get("overlap_beyond_chance"), r.get("halo_coverage_allowed")
        n = r.get("my_dots_within_3px_of_theirs")
        if exc is None or halo is None or n is None or halo >= 0.999:
            continue
        ov = float(n)  # stored as the forward-overlap fraction despite the name
        assert abs(exc - (ov - halo) / (1.0 - halo)) < 1e-9
        checked += 1
        if checked >= 50:
            break
    assert checked > 10


def _ev(name):
    return json.loads((ROOT / "evidence/arc" / name).read_text())


def test_x2_gate_passed_and_x1_failure_preserved():
    assert _ev("uniqueness_surface_x2.json")["passed_d3"] is True
    assert _ev("uniqueness_final_x2.json")["passed_d3"] is True
    x1 = _ev("uniqueness_final.json")
    assert x1["passed_d2"] is False  # X1 negative readings preserved verbatim
    assert x1["worst_forward_overlap_3px"] == 1.0


def test_d3_gate_still_rejects_stopped_nhr():
    cal = _ev("d2_calibration_family_lanes.json")
    nhr = cal["nhr_still_fails_budget_comparable_reading"]
    assert nhr["firings"] == 3
    assert all(r["excess"] > 0.70 and r["their_dots"] <= 4 * 37654 for r in nhr["worst"])


def test_arc_terminal_state_and_preregistration():
    state = _ev("state.json")
    assert state["status"] == "terminal"
    for rel in ("registry/preregistration_arc.json",
                "registry/preregistration_arc_amendment_X2.json",
                "reports/protocol_amendment_D3_20261022.md"):
        assert (ROOT / rel).exists(), rel


def test_card_gates_consistent_with_evidence():
    card = json.loads((ROOT / "run_card.json").read_text())
    assert card["lane"] == "H79-ARC" and card["verdict"] == "promote"
    assert card["ok_to_submit"] is True
    u = card["correlation_overlap_vs_registry"]
    assert u["final_dots"]["worst_spearman"] <= 0.90
    assert u["final_dots"]["worst_overlap_beyond_chance"] <= 0.70
    assert len(card["submission_note"]) <= 140
    h = card["holdout_dti"]
    for seed in ("seed_20", "seed_30"):
        s = h["per_seed"][seed]
        assert s["candidate"]["dti"] > s["h33_foldfair_control"]["dti"]
        assert s["paired_delta_vs_uniform"]["ci95"][0] > 0
        assert s["paired_delta_vs_h33"]["ci95"][0] < 0 < s["paired_delta_vs_h33"]["ci95"][1]
