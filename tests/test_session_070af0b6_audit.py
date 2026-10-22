from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_requirements_txt_declares_lightgbm_and_matplotlib():
    req_txt = (ROOT / "requirements.txt").read_text()
    req_lock = (ROOT / "requirements.lock").read_text()
    assert "lightgbm" in req_txt and "lightgbm==" in req_lock
    assert "matplotlib" in req_txt and "matplotlib==" in req_lock


def test_run_card_paths_are_repo_relative_across_all_copies():
    copies = [
        ROOT / "run_card.json",
        ROOT / "evidence/run_card.json",
        ROOT / "docs/run-card.json",
        ROOT / "docs/evidence/run_card.json",
    ]
    raw = copies[0].read_bytes()
    for p in copies[1:]:
        assert p.read_bytes() == raw
    card = json.loads(raw)
    assert card["lane"] == "G79-THVC"
    for key in ("validator", "validator_output"):
        fval = card[key]["file"]
        assert not fval.startswith("/"), f"Machine-specific absolute path in {key}.file: {fval}"
        assert fval == card["submission_file"]


def test_h79_step_and_dilstep_archived_intact_and_runner_refuses_rerun():
    arch = ROOT / "archive/h79_step_21642326"
    tif = arch / "downloads/gems79-h79-step-37654dots-20261022T043422Z-a99bb5c2-DO-NOT-SUBMIT.tif"
    zf = arch / "downloads/gems79-h79-step-37654dots-20261022T043422Z-a99bb5c2-DO-NOT-SUBMIT.zip"
    rc = arch / "run_card_step.json"
    assert tif.is_file() and zf.is_file() and rc.is_file()
    step_card = json.loads(rc.read_text())
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == step_card["raster_sha256"]
    assert hashlib.sha256(zf.read_bytes()).hexdigest() == step_card["zip_sha256"]

    darch = ROOT / "archive/h79_dilstep_6444be2d"
    dtif = darch / "downloads/gems79-h79-dilstep-research-37654dots-20261022T045200Z-7dd0d54b-DO-NOT-SUBMIT.tif"
    drc = darch / "run_card_dilstep.json"
    assert dtif.is_file() and drc.is_file()
    assert hashlib.sha256(dtif.read_bytes()).hexdigest() == json.loads(drc.read_text())["raster_sha256"]

    downloads_tifs = sorted(p.name for p in (ROOT / "docs/downloads").glob("*.tif"))
    assert downloads_tifs == ["g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif"]

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_edge_lane.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "no files changed" in proc.stderr.lower()


def test_exact_dti_algebra_pigeonhole_bounds_and_unique_ir_ids():
    c_2778 = (0.8 * 0.2778) / (1.0 - 0.2 * 0.2778)
    c_3195 = (0.8 * 0.3195) / (1.0 - 0.2 * 0.3195)
    c_4413 = (0.8 * 0.4413) / (1.0 - 0.2 * 0.4413)
    assert round(c_2778 * 100, 2) == 23.53
    assert round(c_3195 * 100, 2) == 27.30
    assert round(c_4413 * 100, 2) == 38.72

    audit = json.loads((ROOT / "evidence/post_index_sibling_audit_20261022.json").read_text())
    tier3 = audit["pigeonhole_obstruction_tiers"]["tier3_sparse_support_regular_lattice_pigeonhole"]
    assert tier3["uncovered_allowed_cells"] == 6514
    assert tier3["min_overlap_at_35093_dots_g79_thvc"] > 0.81
    assert tier3["min_overlap_at_37654_dots_h33_budget"] > 0.82
    assert audit["pairwise_matrix_10_candidates"]["G79-THVC (GEMSDOE79)"]["GEMSDOE83 (h83-gvcd-dink300)"]["dot_overlap_3px"] > 0.70
    assert len(audit["gemsdoe79_16_lanes_summary"]["lanes_ranked_by_seed20_holdout_dti"]) == 17

    ir_txt = (ROOT / "reports/irregularities.md").read_text(encoding="utf-8")
    ir_ids = re.findall(r"\|\s*(IR-79-\d+)\s*\|", ir_txt)
    # 126 at 070af0b6; +4 BER (127..130); +5 MRND (131..135); +7 FNHR (136..142); +1 5fb439d3 (143); +5 d7da950d (144..148).
    assert len(ir_ids) == len(set(ir_ids)) == 148


def test_executive_summary_and_sources_surface_caveats_and_date():
    exec_html = (ROOT / "docs/executive-summary.html").read_text()
    assert "IR-79-69" in exec_html
    assert "IR-79-122" in exec_html
    assert "post_index_sibling_audit_20261022.json" in exec_html

    sources = json.loads((ROOT / "knowledge/official_sources.json").read_text())
    health = json.loads((ROOT / "docs/evidence/source_health.json").read_text())
    assert sources["reviewed_date_utc"] == "2026-10-22"
    assert health["scientific_claims_reviewed_date"] == sources["reviewed_date_utc"]
    assert health["leaderboard_observation"]["public_dti"] == 0.4413
