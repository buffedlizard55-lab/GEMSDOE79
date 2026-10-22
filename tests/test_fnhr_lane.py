"""End-to-end tests for lane H79-FNHR (F1, F2, F3), IR-79-57..63, and site assets."""
from __future__ import annotations

import hashlib
import json
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_three_fnhr_arms_beat_h33_on_both_seeds_and_pass_canaries():
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


def test_sparse_competition_uniqueness_and_wide_sweep_diagnosis_recorded():
    diag = json.loads((ROOT / "evidence/fnhr/like_for_like_diagnostic.json").read_text())
    sp = diag["comparable_sparse_dot_fields_le_75308"]
    sw = diag["wide_sweep_blockers_gt_75308_le_0p70_halo"]
    assert sp["count"] >= 900
    assert sp["duplicates_over_0p70"] == 0
    assert sp["max_overlap_3px"] <= 0.70
    assert sp["overlap_vs_h33_exact_3px"] < 0.50
    assert sw["count"] == 25
    assert sw["min_their_dots"] > 75308
    assert sw["h33_incumbent_own_overlap_vs_coverage_v3_wide"] > 0.90


def test_all_session_irregularities_documented():
    irr = (ROOT / "reports/irregularities.md").read_text()
    for ir_id in ("IR-79-57", "IR-79-58", "IR-79-59", "IR-79-60", "IR-79-61", "IR-79-62", "IR-79-63"):
        assert ir_id in irr, ir_id


def test_published_downloads_world_readable_and_original_prompt_untouched():
    for f in (ROOT / "docs/downloads").iterdir():
        mode = stat.S_IMODE(f.stat().st_mode)
        assert mode & 0o444 == 0o444, (f, oct(mode))
    for svg in ("docs/assets/fnhr-pareto-curve.svg", "docs/assets/fnhr-overlap-spectrum.svg"):
        txt = (ROOT / svg).read_text()
        assert txt.startswith("<svg ") and "</svg>" in txt
    head_prompt = subprocess.check_output(["git", "show", "HEAD:README.md"], cwd=ROOT, text=True).split(
        "## Original project prompt", 1
    )[1]
    curr_prompt = (ROOT / "README.md").read_text().split("## Original project prompt", 1)[1]
    assert curr_prompt == head_prompt
