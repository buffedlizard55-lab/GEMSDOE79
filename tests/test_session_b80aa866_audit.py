"""Regression tests for session b80aa866 audit (IR-79-181..IR-79-183)."""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_agents_md_paths_and_ir_references_resolve():
    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    ir_text = (ROOT / "reports/irregularities.md").read_text(encoding="utf-8")
    ir_ids = set(re.findall(r"\bIR-79-\d+\b", ir_text))

    backticks = [b.split()[0] for b in re.findall(r"`([^`]+)`", agents_text)]
    path_candidates = [
        b
        for b in backticks
        if (
            b.startswith(
                (
                    "archive/",
                    "artifacts/",
                    "registry/",
                    "evidence/",
                    "docs/",
                    "knowledge/",
                    "research/",
                    "reports/",
                    "scripts/",
                    "src/",
                    "vendor/",
                )
            )
            or b in ("README.md", "AGENTS.md", "run_card.json")
            or (b.startswith("run_card_") and b.endswith(".json"))
        )
        and "*" not in b
    ]
    missing_paths = [p for p in path_candidates if not (ROOT / p).exists()]
    assert not missing_paths, f"Missing paths in AGENTS.md: {missing_paths}"

    agents_irs = sorted(set(re.findall(r"\bIR-79-\d+\b", agents_text)))
    missing_irs = [i for i in agents_irs if i not in ir_ids]
    assert not missing_irs, f"Missing IR IDs in AGENTS.md: {missing_irs}"
    assert "IR-79-158" in agents_irs
    assert "IR-79-162" in agents_irs
    assert "archive/g79b_sdpt_a3/" not in agents_text
    assert "archive/h79_ff/" not in agents_text


def test_six_closed_lane_scripts_guarded_and_canonical_thvc_referenced():
    lifecycle_test_text = (ROOT / "tests/test_lane_lifecycle.py").read_text(encoding="utf-8")
    for script_name in (
        "audit_g79b.py",
        "build_cjx_page.py",
        "run_cjx_experiment.py",
        "run_cjx_exp3.py",
        "build_cjx_submission.py",
        "cjx_gate.py",
        "cjx_sparse_novelty_diagnostic.py",
    ):
        assert f"('{script_name}'" in lifecycle_test_text
        script_text = (ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "enforce_open_lane" in script_text

    for g79b_script in ("build_site_g79b.py", "submission_status_g79b.py"):
        text = (ROOT / "scripts" / g79b_script).read_text(encoding="utf-8")
        assert "H79-NHR" not in text
        assert "G79-THVC" in text


def test_halo_domain_reconciliation_and_cjx_sibling_audit():
    rec = json.loads((ROOT / "evidence/review_b80aa866/halo_domain_reconciliation.json").read_text(encoding="utf-8"))
    ident = rec["identity"]
    assert ident["finite_footprint_cells"] == 5167373
    assert ident["visible_catalogue_in_footprint_cells"] == 60988
    assert ident["off_catalogue_allowed_cells"] == 5106385
    assert ident["exact_algebraic_difference_holds"] is True

    b13 = rec["blocker_13GEMSDOE_r13_lattice_s5"]
    assert not b13["footprint_path"].startswith("/")
    assert not b13["catalogue_path"].startswith("/")
    assert b13["halo_covered_allowed_cells"] == 5160724
    assert b13["uncovered_allowed_cells"] == 6649
    assert b13["off_catalogue_halo_covered_cells"] == 5099871
    assert b13["off_catalogue_uncovered_cells"] == 6514
    assert b13["uncovered_cells_on_catalogue"] == 135
    assert b13["off_catalogue_uncovered_cells"] + b13["uncovered_cells_on_catalogue"] == b13["uncovered_allowed_cells"]
    assert round(b13["off_catalogue_halo_coverage_fraction"], 6) == 0.998724

    sibling_audit = json.loads((ROOT / "evidence/post_snapshot_sibling_audit.json").read_text(encoding="utf-8"))
    cjx_row = sibling_audit["local_gems79_concurrent_lanes_audit"]["G79-CJX_archived"]
    assert cjx_row["sha256"] == "a422d9a08a07a089f304a0ce7f76eca35bcfeff82877af7ee5034e3f94c294e1"
    assert cjx_row["emitted_positive_pixels"] == 37654
    assert cjx_row["overlap_vs_g79_thvc_canonical"] == 0.511871
    assert cjx_row["overlap_vs_13gemsdoe_r13_lattice_s5"] == 0.989085

    h33 = json.loads((ROOT / "evidence/review_b80aa866/h33_lineage_verification.json").read_text(encoding="utf-8"))
    assert h33["d28_positive_pixels"] == 44090
    assert h33["h33_positive_pixels"] == 37654
    assert h33["deleted_near_catalogue_pixels"] == 6436
    assert h33["exact_pruning_identity_holds"] is True

    audit = json.loads((ROOT / "evidence/review_b80aa866/agents_and_lifecycle_audit.json").read_text(encoding="utf-8"))
    assert audit["agents_md_integrity"]["all_paths_and_irs_valid"] is True
    assert audit["scientific_experiments_performed"] == 0
    assert audit["competition_slots_used"] == 0
