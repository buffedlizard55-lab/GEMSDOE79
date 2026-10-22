"""Regression tests for session f0d99a40 (IR-79-148 through IR-79-154)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]


def test_readme_single_prompt_heading_and_verbatim_prompt_restored(tmp_path):
    from verify_project import publication_contract_checks

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count("## Original project prompt") == 1
    assert "## Original project prompt` (`IR-79-81`)" not in readme
    assert "https://buffedlizard55-lab.github.io/GEMSDOE41/docs/index.html" in readme
    for n in (74, 75, 76, 77):
        assert f"GEMSDOE{n}:[https://buffedlizard55-lab.github.io/GEMSDOE{n}/]" in readme
    for n in range(78, 89):
        assert f"GEMSDOE{n}: [https://buffedlizard55-lab.github.io/GEMSDOE{n}/]" in readme
    assert (
        'I want to have a validation gates in place so I never get the '
        '"Predicted values must be in range [0, 1]" error again when I submit '
        "my TIF file to the competition."
    ) in readme

    # Verify duplicate heading splice is rejected by publication_contract_checks
    card = json.loads((ROOT / "run_card.json").read_text(encoding="utf-8"))
    for d in ("docs/downloads", "submissions", "registry", "reports"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    for rel in (
        card["submission_file"],
        card["zip_file"],
        "registry/registry_index.json",
        "registry/registry_receipt.json",
        "reports/irregularities.md",
    ):
        (tmp_path / rel).write_bytes((ROOT / rel).read_bytes())
    (tmp_path / "README.md").write_text(
        "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. "
        f"{card['raster_sha256']}\n"
        "## Original project prompt splice\n"
        "OK TO SUBMIT: YES.\n"
        "## Original project prompt — read at the start of every session\n"
        "<details>\nprompt\n</details>\n",
        encoding="utf-8",
    )
    checks = publication_contract_checks(tmp_path, card)
    assert checks["readme_matches_card_decision"] is False


def test_etp_and_cfskd_forensic_remediation():
    etp_audit = json.loads((ROOT / "evidence/etp_forensic_audit_f40e4f2e.json").read_text(encoding="utf-8"))
    prereg_sha = hashlib.sha256(
        (ROOT / "archive/g79_etp_incoming_45998a01/preregistration_etp.json").read_bytes()
    ).hexdigest()
    assert etp_audit["irregularities_verified"]["actual_preregistration_file_sha256"] == prereg_sha
    assert round(etp_audit["measured_holdout_dti_gems57_pooled_hide_v2"]["seed_20"]["etp_v2_foldfair_34500"]["dti"], 4) == 0.0968
    assert round(etp_audit["measured_holdout_dti_gems57_pooled_hide_v2"]["seed_30"]["etp_v2_foldfair_34500"]["dti"], 4) == 0.1061

    cfskd_src = (ROOT / "scripts/validate_cfskd.py").read_text(encoding="utf-8")
    assert "distance_transform_edt" in cfskd_src
    assert "binary_dilation(rd,iterations=3)" not in cfskd_src


def test_local_gems79_concurrent_lanes_audit_reproducible():
    from audit_post_snapshot_siblings import build_local_gems79_concurrent_lanes_audit

    computed = build_local_gems79_concurrent_lanes_audit(ROOT)
    ev_doc = json.loads((ROOT / "evidence/post_snapshot_sibling_audit.json").read_text(encoding="utf-8"))
    pub_doc = json.loads((ROOT / "docs/evidence/post_snapshot_sibling_audit.json").read_text(encoding="utf-8"))
    assert ev_doc["local_gems79_concurrent_lanes_audit"] == computed
    assert pub_doc["local_gems79_concurrent_lanes_audit"] == computed
    assert computed["G79-ETP_v1_quarantined"]["overlap_vs_g79_thvc_canonical"] > 0.70
    assert set(computed) >= {
        "H79-DILSTEP_active",
        "H79-NHR_archived",
        "G79-MAG_quarantined",
        "G79-THVC_canonical",
        "H79-FNHR_archived",
        "G79-ETP_v1_quarantined",
        "G79-ETP_v2_quarantined",
        "G79-CFSKD_archived",
    }


def test_irregularities_159_through_164_and_review_report():
    assert (ROOT / "reports/session_review_f0d99a40.md").is_file()
    ir_txt = (ROOT / "reports/irregularities.md").read_text(encoding="utf-8")
    ir_ids = re.findall(r"^\|\s*(IR-79-\d+)\s*\|", ir_txt, flags=re.M)
    # Preserve this review's historical prefix, while allowing later append-only reviews.
    assert len(ir_ids) == len(set(ir_ids)) and len(ir_ids) >= 164
    assert {f"IR-79-{n:02d}" for n in range(1, 165)} <= set(ir_ids)
    for n in range(159, 165):
        assert f"IR-79-{n}" in ir_ids
