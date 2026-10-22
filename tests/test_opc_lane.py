"""G79-OPC: geometry sanity on a synthetic grid + gate/card consistency (if the card exists)."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]


def test_strike_field_vertical_and_pair_correlation_across_strike():
    from gems79 import opc
    m = np.zeros((200, 200), bool)
    for x in range(20, 190, 8):           # parallel vertical faults 8 px apart, segmented
        for y0 in range(10, 190, 40):
            m[y0:y0 + 30, x] = True
    fp = np.ones_like(m)
    phi, coh = opc.strike_field(m)
    on = m & (coh > 0.5)
    # image coords: vertical strike = pi/2
    assert np.median(np.abs(np.cos(phi[on]))) < 0.2
    pc = opc.pair_correlation(m, fp, phi)
    g = pc["g"]                            # axis 0 = |u| along strike, axis 1 = |v| across strike
    across = g[0, 3:6].mean()              # v ~ 6-12 px, u ~ 0: neighbouring parallel faults
    assert across > 1.0 and across > g[0, 1]


def test_card_and_gate_agree():
    card_p = ROOT / "run_card_opc.json"
    if not card_p.exists():
        pytest.skip("lane not finalised")
    card = json.loads(card_p.read_text())
    assert len(card["note"]) <= 140 and len(card["submission_name"]) <= 140
    assert card["ok_to_submit"] is False and card["verdict"] == "negative"
    assert card["submission_name"].endswith("-DO-NOT-SUBMIT")
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    tif = ROOT / card["raster"]["path"]
    if not tif.exists():
        pytest.skip("artifact not present")
    r = subprocess.run([sys.executable, str(ROOT / "scripts/opc_gate.py")], capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr  # NO, but consistent (1 would mean inconsistency)
    assert "OK TO SUBMIT: NO" in r.stdout


def test_runner_refuses_after_terminal_verdict():
    if not (ROOT / "run_card_opc.json").exists():
        pytest.skip("lane not finalised")
    r = subprocess.run([sys.executable, str(ROOT / "scripts/run_g79_opc.py"), "seed20"],
                       capture_output=True, text=True)
    assert r.returncode == 2 and "closed" in r.stderr
