"""Comprehensive unit, physical, allocator, and receipt audit tests for canonical G79-DCMS (session a30a4118)."""
from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems79.dcms_features import ALL_DCMS_NAMES, MECH_DCMS_NAMES, STATIC_DCMS_NAMES  # noqa: E402
from gems79.dcms_model import dinkelbach_submodular_emit  # noqa: E402
from gems79.evidence_summary import build_summary  # noqa: E402
from reproduce_artifact import reproduce_dcms, reproduce_thvc  # noqa: E402


def test_dcms_feature_manifest_counts_and_disjointness():
    assert len(STATIC_DCMS_NAMES) == 98
    assert len(MECH_DCMS_NAMES) == 20
    assert len(ALL_DCMS_NAMES) == 118
    assert len(set(ALL_DCMS_NAMES)) == 118


def test_median_scale_dinkelbach_submodular_allocator_invariants():
    rng = np.random.default_rng(7901)
    h, w = 80, 90
    allowed = np.ones((h, w), dtype=bool)
    allowed[:4, :] = False
    p = rng.uniform(1e-5, 2e-4, size=(h, w)).astype(np.float32)
    q = rng.uniform(5e-4, 2e-3, size=(h, w)).astype(np.float32)
    # Plant a sharp linear fault scarp along column 44
    p[10:70, 44] = 0.08
    q[10:70, 43:46] = 0.25
    em = dinkelbach_submodular_emit(
        p, q, allowed,
        lambda_fp=0.20, min_sep_px=1.85, crest_gamma=1.0,
        max_budget=26, min_budget=5, candidate_pool=5_000,
    )
    assert em.dtype == np.float32
    assert set(np.unique(em).tolist()) <= {0.0, 1.0}
    assert int(em[~allowed].sum()) == 0
    assert int((em > 0).sum()) == 26
    # Every single emitted dot sits directly on the planted column-44 fault crest
    assert int((em[10:70, 44] > 0).sum()) == 26


def test_canonical_dcms_beats_thvc_and_h33_across_both_seeds_and_regimes():
    card = json.loads((ROOT / "run_card.json").read_text())
    summary = build_summary(ROOT, card)
    assert summary["lane"] == "G79-DCMS"
    assert summary["h33_control_beaten_both_seeds"] is True
    assert summary["thvc_incumbent_beaten_both_seeds"] is True
    assert summary["canaries"]["feature_count"] == 118
    assert summary["canaries"]["feature_seed_tests"] == 236
    assert summary["canaries"]["passed"] is True

    res = json.loads((ROOT / "evidence/dcms_results.json").read_text())
    for seed_key in ("seed20", "seed30"):
        reg = res[seed_key]["regime_decomposition"]
        for rname, rblock in reg.items():
            sc = rblock["scores"]
            assert sc["EXP-DCMS-3_calibrated_dinkelbach"] > sc["C3_g79_thvc_incumbent"], (seed_key, rname)
            assert sc["EXP-DCMS-3_calibrated_dinkelbach"] > sc["C2_h33_analogue_foldfair"], (seed_key, rname)


def test_1201_blob_audit_clears_all_le45k_siblings_while_honestly_blocking_submit():
    card = json.loads((ROOT / "run_card.json").read_text())
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["submission_slots_used"] == 0

    dot_doc = json.loads((ROOT / "evidence/dcms_dot_uniqueness_1201.json").read_text())
    assert dot_doc["registry_rasters_expected"] == 1201
    assert dot_doc["registry_rasters_checked"] == 1191
    assert dot_doc["max_abs_spearman"] <= 0.90
    le45 = [r for r in dot_doc["rows"] if "error" not in r and int(r["their_dots"]) <= 45_000]
    assert max(float(r["my_dots_within_3px_of_theirs"]) for r in le45) <= 0.70
    assert dot_doc["worst_dot_overlap"] == 1.0


def test_both_dcms_and_archived_thvc_reproduce_exact_bytes_and_runner_is_locked():
    dcms_rep = reproduce_dcms(ROOT)
    assert dcms_rep["exact_tiff_recovery"] is True
    assert dcms_rep["exact_single_tiff_zip_recovery"] is True
    assert dcms_rep["positive_pixels"] == 36404

    thvc_rep = reproduce_thvc(ROOT)
    assert thvc_rep["exact_tiff_recovery"] is True
    assert thvc_rep["exact_single_tiff_zip_recovery"] is True
    assert thvc_rep["positive_pixels"] == 35093

    for f in (ROOT / "docs/downloads").iterdir():
        assert (stat.S_IMODE(f.stat().st_mode) & 0o444) == 0o444

    # Verify zero absolute sandbox paths leak into any evidence or download JSON
    for jp in list((ROOT / "evidence").glob("dcms_*.json")) + list((ROOT / "docs/downloads").glob("*.json")):
        assert "/home/" not in jp.read_text(), jp

    # Verify closed runner fails closed with exit code 2
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_g79_dcms.py"), "--stage", "eval"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "no files changed" in proc.stderr.lower()


def test_session_a30a4118_review_digests_and_irregularities_172_to_178():
    card = json.loads((ROOT / "run_card.json").read_text())
    rev = (ROOT / "reports/session_review_a30a4118.md").read_text()
    readme = (ROOT / "README.md").read_text().split("## Original project prompt", 1)[0]
    tif_size = f"{(ROOT / card['submission_file']).stat().st_size:,}"
    zip_size = f"{(ROOT / card['zip_file']).stat().st_size:,}"
    for doc in (rev, readme):
        assert card["raster_sha256"] in doc
        assert card["zip_sha256"] in doc
        assert tif_size in doc
        assert zip_size in doc
    for n in range(172, 179):
        ir = f"IR-79-{n}"
        assert ir in (ROOT / "reports/irregularities.md").read_text(), ir
