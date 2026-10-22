"""Comprehensive verification test suite for GEMSDOE79 Lane H79-CSPT."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import gates, grid as grid_mod, validate as val_mod  # noqa: E402
from gems79.features import H79_STATIC_NAMES as H79_NEW_FEATURE_NAMES  # noqa: E402
from gems79.lagrangian_solver import _get_lib as _load_lib  # noqa: E402

EVIDENCE_DIR = ROOT / "evidence" / "h79_cspt"
SUB_STEM = "gemsdoe79-h79-cspt-kkt1swap-36500-20261021T223000Z-zeros"


def test_h79_feature_names_and_no_sgmc() -> None:
    assert len(H79_NEW_FEATURE_NAMES) == 6
    canary = json.loads((EVIDENCE_DIR / "leakage_canary_130ch.json").read_text())
    assert canary["n_features_tested"] == 130
    n_static = sum(1 for r in canary["all_features"] if not r["is_catalogue_derived"])
    n_net = sum(1 for r in canary["all_features"] if r["is_catalogue_derived"])
    assert n_static == 116
    assert n_net == 14
    for row in canary["all_features"]:
        fname = row["feature_name"].lower()
        assert "sgmc" not in fname, f"Forbidden SGMC channel found: {fname}"


def test_leakage_canary_130_channels_pass() -> None:
    canary = json.loads((EVIDENCE_DIR / "leakage_canary_130ch.json").read_text())
    assert canary["pass"] is True
    assert canary["n_leakage_firings_gt_0p90"] == 0
    assert canary["max_symmetric_auc_all_130"] <= 0.90
    assert canary["max_symmetric_auc_static_116"] <= 0.90


def test_holdout_dti_experiments_1_and_2() -> None:
    exp1 = json.loads((EVIDENCE_DIR / "exp1_seed20_holdout.json").read_text())
    exp2 = json.loads((EVIDENCE_DIR / "exp2_seed30_holdout.json").read_text())
    dual = json.loads((EVIDENCE_DIR / "dual_seed_holdout_summary.json").read_text())

    assert exp1["evidence_class"] == "HOLDOUT-DTI"
    assert exp2["evidence_class"] == "HOLDOUT-DTI"
    assert exp1["evaluator_version"] == "gems57-pooled-hide-v2"
    assert exp2["evaluator_version"] == "gems57-pooled-hide-v2"
    assert exp1["withheld_positive_pixels"] == 11321
    assert exp2["withheld_positive_pixels"] == 11342
    assert dual["withheld_positive_pixels_pooled"] == 22663

    s20_dti = exp1["pooled_summary"]["scores"]["h79_lagrangian_kkt_1swap"]["dti"]
    s30_dti = exp2["pooled_summary"]["scores"]["h79_lagrangian_kkt_1swap"]["dti"]
    pooled_dti = dual["dual_seed_pooled_summary"]["h79_lagrangian_kkt_1swap"]["dti"]

    # Must beat Fold-Fair H33 Champion (A0) and Pure-Physics Blind on both seeds
    assert s20_dti > exp1["pooled_summary"]["scores"]["h33_foldfair"]["dti"] + 0.07
    assert s30_dti > exp2["pooled_summary"]["scores"]["h33_foldfair"]["dti"] + 0.09
    assert s30_dti > 0.190001  # Beats H82-GMNS Seed 30 (0.190001)
    assert pooled_dti > 0.1815  # Beats H82-GMNS Dual-Seed Mean (0.181065)


def test_uniqueness_certificate_1016_rasters() -> None:
    exp3 = json.loads((EVIDENCE_DIR / "exp3_full_oof_and_uniqueness_1016.json").read_text())
    uc = exp3["uniqueness_certificate"]
    assert uc["total_unique_rasters_audited"] == 1016
    assert uc["n_informative_rasters_lt_0p70"] == 949
    assert uc["n_dot_field_rasters_le_0p20_support"] == 942
    assert uc["n_space_filling_rasters_ge_0p70"] == 67

    p1 = uc["phase1_pre_placement_surface"]
    assert p1["max_abs_spearman_rho_all"] <= 0.90
    assert p1["n_firings_gt_0p90"] == 0

    p2 = uc["phase2_final_dots_informative_lt_0p70"]
    assert p2["max_forward_overlap_3px"] <= 0.70
    assert p2["max_dot_field_overlap_3px"] <= 0.70
    assert p2["max_abs_spearman_rho_all"] <= 0.90
    assert p2["n_overlap_firings_gt_0p70"] == 0
    assert p2["n_dot_field_firings_gt_0p70"] == 0
    assert p2["n_rho_firings_gt_0p90"] == 0
    assert uc["overall_uniqueness_pass"] is True


def test_c99_fast_submod_shared_library_loads() -> None:
    lib = _load_lib()
    assert lib is not None


def test_geotiff_and_zip_deliverables_match_sample_submission() -> None:
    g = grid_mod.load_grid(ROOT / ".cache" / "data")
    sample_tif = ROOT / ".cache" / "data" / "sample_submission.tif"
    full_cat = g.catalogue & g.footprint
    run_card = json.loads((EVIDENCE_DIR / "run_card.json").read_text())

    for folder in (ROOT / "submissions", ROOT / "docs" / "downloads"):
        tif_path = folder / f"{SUB_STEM}.tif"
        zip_path = folder / f"{SUB_STEM}.zip"
        assert tif_path.is_file(), f"Missing {tif_path}"
        assert zip_path.is_file(), f"Missing {zip_path}"

        assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == run_card["raster_sha256"]
        assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == run_card["zip_sha256"]

        rep = gates.format_report(tif_path, sample_tif, footprint=g.footprint)
        assert rep["ok"] is True, f"Format gate failed: {rep}"

        v = val_mod.validate(tif_path, g.footprint, full_cat)
        val_mod.assert_submittable(v)

        with rasterio.open(tif_path) as ds, rasterio.open(sample_tif) as ref:
            assert ds.crs == ref.crs
            assert (ds.height, ds.width) == (3730, 3292)
            assert ds.transform == ref.transform
            assert ds.dtypes[0] == "float32"
            assert ds.nodata is None
            arr = ds.read(1)
            assert np.isfinite(arr).all()
            assert float(arr.min()) == 0.0
            assert float(arr.max()) == 1.0
            assert int((arr > 0).sum()) == 36500
            assert int(((arr > 0) & (~g.footprint)).sum()) == 0
            assert int(((arr > 0) & full_cat).sum()) == 0

        with zipfile.ZipFile(zip_path, "r") as zf:
            assert zf.namelist() == [tif_path.name]
            assert zf.read(tif_path.name) == tif_path.read_bytes()

    assert run_card["verdict"] == "promote"
    assert len(run_card["submission_note"]) <= 140


def test_docs_and_readme_consistency() -> None:
    run_card = json.loads((EVIDENCE_DIR / "run_card.json").read_text())
    readme = (ROOT / "README.md").read_text()
    index_html = (ROOT / "docs" / "index.html").read_text()
    exec_html = (ROOT / "docs" / "executive-summary.html").read_text()
    report_md = (ROOT / "reports" / "why_02778_and_h79_cspt.md").read_text()

    for doc_name, text in (
        ("README.md", readme),
        ("docs/index.html", index_html),
        ("docs/executive-summary.html", exec_html),
    ):
        assert run_card["raster_sha256"] in text, f"Missing raster_sha256 in {doc_name}"
        assert run_card["zip_sha256"] in text, f"Missing zip_sha256 in {doc_name}"
        assert run_card["submission_name"] in text, f"Missing submission_name in {doc_name}"
        assert "PROMOTED" in text and "OK TO DOWNLOAD AND SUBMIT" in text, f"Missing banner in {doc_name}"

    assert "Carefully review why \"h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros\"" in readme
    assert "0.2778" in report_md and "H79-CSPT" in report_md

    for fig_name in ("h79_overview_map.png", "h79_holdout_progression.png", "h79_uniqueness_and_canary.png"):
        fig_path = ROOT / "docs" / "figures" / fig_name
        assert fig_path.is_file() and fig_path.stat().st_size > 10_000, f"Missing or empty figure {fig_path}"
        assert f"figures/{fig_name}" in index_html

