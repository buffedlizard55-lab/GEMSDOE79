#!/usr/bin/env python3
"""Finalize candidate A (G79-GEM concealed-conduit) as a locally validated
submission GeoTIFF + ZIP + run card + status.  All numbers are measured;
nothing is organizer-accepted."""
from __future__ import annotations

import json, sys, time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as G  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts"))
from validate_submission import validate_path  # noqa: E402

TIF = ROOT / "artifacts" / "gem_candidates" / "g79-gem-geophysics-conduit.tif"
OUT = ROOT / "artifacts" / "gem_submission"
OUT.mkdir(parents=True, exist_ok=True)

grid = G.load_grid(ROOT / "data" / "raw")
foot = grid.footprint
cat = grid.catalogue

with rasterio.open(TIF) as src:
    dots = src.read(1).astype(np.float32)
print(f"candidate A dots: {int((dots > 0).sum()):,}  range [{float(dots.min())}, {float(dots.max())}]")

stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
name = f"gems79-gem-conduit-gravity-maglow-{int((dots>0).sum())}dots-{stamp}"
if len(name) > 140:
    name = name[:140]
note = ("GEMSDOE79 G79-GEM concealed-conduit: gravity-gradient x magnetic-low blind-fault "
        "surface; negative holdout, research-only, DO NOT SUBMIT")
if len(note) > 140:
    note = note[:140]

final_tif = OUT / f"{name}.tif"

receipt = write_submission(
    final_tif, dots, ROOT / "data" / "raw" / "sample_submission.tif",
    foot, name=name, note=note, catalogue=cat,
    metadata={"lane": "G79-GEM", "method": "concealed-conduit gravity-edge x mag-demag",
              "source": "scripts/run_gem_conduit.py", "dots": int((dots > 0).sum())},
)
print(f"wrote {final_tif} ({receipt['bytes']} B, sha256 {receipt['sha256'][:12]}…)")

val = validate_path(final_tif)
print(f"format validation passed={val['format_passed']}")

card = {
    "schema_version": 2, "lane": "G79-GEM",
    "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "hypothesis": ("Concealed geothermal conduit faults (blind, absent from the USGS/INGENIOUS "
                   "catalogue) coincide with an isostatic-gravity horizontal-gradient edge and a "
                   "magnetic-anomaly low (hydrothermal demagnetization). Surface = gravity-edge "
                   "rank x (1 - magnetic-anomaly rank), zeroed on the catalogue and outside the "
                   "footprint; top dots emitted as a sparse binary field."),
    "mechanism": ("training_features band 18 (iso_grav_anom_hg) x (1 - band 1 mag_anom rank), "
                  "empirical unit ranks on the footprint, product normalised to [0,1], top-37,654 "
                  "dots via kernel-credit ranking; sparse binary emission in [0,1]."),
    "named_non_fault_mimic": ("Pluvial shoreline benches, fluvial terrace risers, welded caldera "
                              "cooling joints, lateral thermal outflow plumes can mimic gravity/mag "
                              "edges without being geothermal faults."),
    "holdout_dti": {
        "evidence_class": "HOLDEOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2",
        "dti": 0.0045, "ci95": [0.0029, 0.0064],
        "withheld_positive_pixels": 22663,
        "per_seed": {
            "seed_20": {"dti": 0.0041, "ci95": [0.0023, 0.0062], "withheld_positive_pixels": 11321},
            "seed_30": {"dti": 0.0049, "ci95": [0.0024, 0.0081], "withheld_positive_pixels": 11342},
        },
        "note": "Below the ~0.05 random control: this concealed-fault detector targets blind faults "
                "not the catalogue segments used as holdout truth. Negative result.",
        "source_pointer": "scripts/run_gem_conduit.py",
    },
    "leakage_canary": {
        "evidence_class": "LEAKAGE-CANARY", "auc": 0.5056, "passed": True,
        "required_threshold": 0.90, "features_cleared": 2,
        "n_suspicious_gt_0p90": 0,
        "per_feature": {"gravity_edge_rank": 0.5056, "mag_demag_low": 0.4998},
    },
    "correlation_overlap_vs_registry": {
        "note": "Measured vs locally cached historical rasters only (full 992-raster registry not "
                "cached locally). Candidate is distinct from all dot submissions (max dot-vs-dot "
                "forward 3-px overlap 0.2400 vs h79-dilstep), but overlaps the dense G79-FF1 "
                "fabric-offset surface at 0.8986 forward 3-px overlap (> 0.70), so the FULL "
                "literal novelty gate FAILS vs that dense prior surface.",
        "max_forward_overlap_3px_vs_local": 0.8986,
        "forward_overlap_limit": 0.70,
        "max_abs_spearman_vs_local": 0.1124,
        "spearman_limit": 0.90,
        "novelty_passed": False,
        "novelty_note": "FAIL vs dense fabric-offset prior surface; distinct from all sparse dot submissions",
    },
    "submission_file": f"artifacts/gem_submission/{name}.tif",
    "zip_file": f"artifacts/gem_submission/{name}.zip",
    "raster_sha256": receipt["sha256"],
    "zip_sha256": receipt["zip_sha256"],
    "submission_name": name,
    "submission_note": note,
    "positive_pixels": int((dots > 0).sum()),
    "validator": receipt["validator"],
    "runtime_s": None,
    "ok_to_download": bool(val["format_passed"]),
    "ok_to_submit": False,
    "approved_for_weekly_slot": False,
    "verdict": "negative_research_artifact_not_approved_for_submission",
    "blockers": [
        "Full literal novelty gate fails (0.8986 forward 3-px overlap vs dense G79-FF1 fabric-offset surface > 0.70).",
        "Holdout DTI 0.0045 is below the ~0.05 random control (negative result).",
        "No DrivenData login: cannot obtain an organizer receipt or verify a weekly slot.",
        "Weekly slot / eligibility not observable from this checkout (account-side).",
    ],
    "submission_note_display": ("OK TO DOWNLOAD: YES (locally validated research GeoTIFF). "
                                "OK TO SUBMIT: NO (novelty gate fails, holdout negative, no organizer "
                                "receipt, weekly slot unverified)."),
}
card_path = ROOT / "run_card_gem_conduit.json"
card_path.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
print(f"wrote run card {card_path}")

status = {
    "ok_to_download": bool(val["format_passed"]),
    "ok_to_submit": False,
    "verdict": "negative",
    "decision_line": "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.",
    "file": f"artifacts/gem_submission/{name}.tif",
    "zip": f"artifacts/gem_submission/{name}.zip",
    "sha256": receipt["sha256"],
    "name": name,
    "note": note,
    "holdout_dti": 0.0045,
    "holdout_ci95": [0.0029, 0.0064],
    "leakage_canary_max_auc": 0.5056,
    "novelty": {
        "forward_overlap_vs_dense_fabric_surface": 0.8986,
        "novelty_limit": 0.70,
        "novelty_passed": False,
    },
    "account_side_conditions": [
        "A free weekly slot must be shown on your DrivenData submission page (up to 3/week).",
        "You must be a registered, eligible participant who accepted the competition rules.",
    ],
    "scope": ("G79-GEM novel research artifact, locally format-validated only. Novelty gate fails vs a "
              "dense prior surface; holdout is negative (below random). Not organizer acceptance."),
}
status_path = ROOT / "docs" / "status_gem_conduit.json"
status_path.write_text(json.dumps(status, indent=2) + "\n")
print(f"wrote status {status_path}")
print(json.dumps(status, indent=2))
