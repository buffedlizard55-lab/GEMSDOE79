"""Regression tests for session arena/0d90d81b-gemsdoe79 forensic audit, tool fixes, and hypotheses."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_strict(path: Path) -> dict:
    def _forbid_const(val: str):
        raise ValueError(f"Non-standard JSON constant {val!r} in {path}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_forbid_const)


def test_halo_saturation_receipts_reconcile_off_catalogue_and_have_no_local_paths():
    for name in (
        "halo_saturation_13GEMSDOE_1db538e6.json",
        "halo_saturation_17GEMSDOE_Eproba_1db538e6.json",
    ):
        ev = ROOT / "evidence" / name
        doc_ev = ROOT / "docs" / "evidence" / name
        raw = ev.read_text(encoding="utf-8")
        assert "/home/user" not in raw, f"Machine path leaked in {ev}"
        assert raw == doc_ev.read_text(encoding="utf-8")
        data = _load_strict(ev)
        assert data["footprint_path"] == "data/reference/sample_submission.tif"
        assert data["catalogue_path"] == "data/reference/existing_faults.tif"
        assert data["allowed_cells_finite_footprint"] == 5_167_373
        assert data["catalogue_positive_cells_in_footprint"] == 60_988
        assert data["off_catalogue_allowed_cells"] == 5_106_385
        assert (
            data["allowed_cells_finite_footprint"] - data["catalogue_positive_cells_in_footprint"]
            == data["off_catalogue_allowed_cells"]
        )

    h13 = _load_strict(ROOT / "evidence" / "halo_saturation_13GEMSDOE_1db538e6.json")
    assert h13["uncovered_allowed_cells"] == 6_649
    assert h13["off_catalogue_uncovered_cells"] == 6_514

    h17 = _load_strict(ROOT / "evidence" / "halo_saturation_17GEMSDOE_Eproba_1db538e6.json")
    assert h17["uncovered_allowed_cells"] == 0
    assert h17["off_catalogue_uncovered_cells"] == 0


def test_tracked_raster_scan_separates_reference_masks_from_prediction_artifacts():
    scan = _load_strict(ROOT / "evidence" / "review_b40c0d45" / "tracked_raster_scan.json")
    assert scan["schema"] == "tracked_raster_scan.v2"
    assert scan["n_prediction_artifacts"] + scan["n_reference_inputs"] == scan["n_tracked_rasters"]
    assert scan["n_prediction_artifacts"] >= 29
    assert scan["flagged_prediction_artifacts"] == []
    assert set(scan["reference_inputs_outside_0_1"]).issubset(
        {r["path"] for r in scan["records"] if r["role"] == "reference_input"}
    )


def test_session_0d90d81b_audit_and_run_card_invariants():
    audit_p = ROOT / "evidence" / "session_0d90d81b_audit.json"
    rc_p = ROOT / "evidence" / "session_0d90d81b_run_card.json"
    for p, mirror in (
        (audit_p, ROOT / "docs" / "evidence" / "session_0d90d81b_audit.json"),
        (rc_p, ROOT / "docs" / "evidence" / "session_0d90d81b_run_card.json"),
    ):
        txt = p.read_text(encoding="utf-8")
        assert "/home/user" not in txt
        assert txt == mirror.read_text(encoding="utf-8")

    audit = _load_strict(audit_p)
    assert audit["family_registry_census_20261022"]["total_verified_non_self_unique_blobs"] == 1201
    assert (
        audit["family_registry_census_20261022"]["registry_index_unique_blobs"]
        + audit["family_registry_census_20261022"]["registry_delta_043119z_unique_blobs"]
        + audit["family_registry_census_20261022"]["post_043119z_new_unique_blobs"]
        == 1201
    )
    sib = audit["sibling_byte_forensics"]
    assert sib["H33_GEMSDOE32"]["sha256"].startswith("c55bafc47005")
    assert sib["H78_MGHD"]["sha256"].startswith("44429c439118")
    assert sib["H78_GFV"]["sha256"].startswith("0338383df9c3")
    assert sib["H78_GFV"]["vs_G79_THVC"]["forward_overlap_a_in_3px_of_b"] < 0.70
    assert sib["H78_MGHD"]["vs_G79_THVC"]["forward_overlap_a_in_3px_of_b"] < 0.70

    comp = audit["evaluation_protocol_comparison"]
    assert comp["H78_GFV_strict_3quad_LOQO"]["seed20_dti"] < comp["G79_THVC_strict_3quad_LOQO"]["seed20_dti"]
    assert comp["H78_GFV_strict_3quad_LOQO"]["seed30_dti"] < comp["G79_THVC_strict_3quad_LOQO"]["seed30_dti"]
    assert comp["H78_GFV_global_4quad_in_sample_benchmark"]["trains_on_test_quadrant"] is True

    rc = _load_strict(rc_p)
    assert rc["verdict"] == "negative"
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit"] is False
    assert rc["submission_slots_used"] == 0
    assert 0 < len(rc["submission_name"]) <= 140
    assert 0 < len(rc["submission_note"]) <= 140
    assert rc["validator_output"]["all_checks_passed"] is True


def test_untried_hypotheses_sources_and_irregularities_177():
    hyp_text = (ROOT / "research" / "hypotheses_0d90d81b.md").read_text(encoding="utf-8")
    assert not any(line.startswith("# ") for line in hyp_text.splitlines()), "Must not emit extra <h1> in research.html"
    for hid in ("G79-SFGC", "G79-UGBP", "G79-MDSC", "G79-PSDC", "G79-MCST"):
        assert hid in hyp_text
        assert hid in (ROOT / "docs" / "research.html").read_text(encoding="utf-8")

    sources = _load_strict(ROOT / "knowledge" / "official_sources.json")
    by_id = {s["id"]: s for s in sources["sources"]}
    assert {"USGS-QFAULTS", "UNR-NGL-MIDAS"}.issubset(by_id)
    lb = by_id["DD-LEADERBOARD"]["observation"]
    assert lb["rank_48_participant"] == "moongrega" and lb["rank_48_public_dti"] == 0.2818
    assert lb["rank_50_participant"] == "sam35" and lb["rank_50_public_dti"] == 0.2804

    feed = _load_strict(ROOT / "docs" / "evidence" / "source_health.json")
    assert feed["leaderboard_observation"]["rank_50_participant"] == "sam35"

    ir_lines = (ROOT / "reports" / "irregularities.md").read_text(encoding="utf-8").splitlines()
    nums = [
        int(m.group(1))
        for line in ir_lines
        if (m := re.match(r"^\|\s*IR-79-0*(\d+)\s*\|", line))
    ]
    assert nums == list(range(1, 185))
