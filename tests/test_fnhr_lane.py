"""End-to-end tests for archived lane H79-FNHR (F1, F2, F3), IR-79-136..142, and SVGs."""
from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_three_fnhr_arms_beat_h33_on_both_seeds_and_pure_physics_sets_record():
    for arm in ("f1", "f2", "f3"):
        for seed in (20, 30):
            doc = json.loads((ROOT / f"evidence/fnhr/{arm}_holdout_seed{seed}.json").read_text())
            assert doc["lane"] == "H79-FNHR"
            assert doc["evaluator_version"] == "gems57-pooled-hide-v2"
            assert doc["leakage_canary"]["n_suspicious"] == 0
            assert doc["leakage_canary"]["max_symmetric_auc"] <= 0.90
            cand = doc["holdout"]["scores"]["candidate"]["dti"]
            h33 = doc["holdout"]["scores"]["h33_foldfair_control"]["dti"]
            ci_lo = doc["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"][0]
            assert cand > h33, (arm, seed, cand, h33)
            assert ci_lo > 0.0, (arm, seed, ci_lo)
    f3_s20 = json.loads((ROOT / "evidence/fnhr/f3_holdout_seed20.json").read_text())
    assert round(f3_s20["holdout"]["scores"]["ablation_no_geometry"]["dti"], 4) == 0.0906


def test_fnhr_archive_pins_and_sparse_uniqueness_vs_thvc_and_h33():
    card = json.loads((ROOT / "run_card_fnhr.json").read_text())
    assert card["lane"] == "H79-FNHR" and card["verdict"] == "negative" and card["ok_to_submit"] is False
    tif = ROOT / "archive/h79_fnhr_a57e2a7f" / Path(card["submission_file"]).name
    zp = ROOT / "archive/h79_fnhr_a57e2a7f" / Path(card["zip_file"]).name
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zp.read_bytes()).hexdigest() == card["zip_sha256"]

    diag = json.loads((ROOT / "evidence/fnhr/like_for_like_diagnostic.json").read_text())
    sp = diag["comparable_sparse_dot_fields_le_75308"]
    sw = diag["wide_sweep_blockers_gt_75308_le_0p70_halo"]
    cs = diag["cross_session_vs_canonical_g79_thvc"]
    assert sp["count"] >= 900 and sp["duplicates_over_0p70"] == 0
    assert sp["max_overlap_3px"] <= 0.70 and sp["overlap_vs_h33_exact_3px"] < 0.50
    assert sw["count"] == 25 and sw["min_their_dots"] > 75308
    assert cs["fnhr_f3_within_3px_of_thvc"] < 0.50


def test_fnhr_irregularities_monotonically_numbered_and_svgs_valid():
    irr = (ROOT / "reports/irregularities.md").read_text()
    for ir_id in ("IR-79-136", "IR-79-137", "IR-79-138", "IR-79-139", "IR-79-140", "IR-79-141", "IR-79-142"):
        assert ir_id in irr, ir_id
    for f in (ROOT / "docs/downloads").iterdir():
        mode = stat.S_IMODE(f.stat().st_mode)
        assert mode & 0o444 == 0o444, (f, oct(mode))
    for svg in ("docs/assets/fnhr-pareto-curve.svg", "docs/assets/fnhr-overlap-spectrum.svg"):
        txt = (ROOT / svg).read_text()
        assert txt.startswith("<svg ") and "</svg>" in txt
