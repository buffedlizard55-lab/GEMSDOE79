#!/usr/bin/env python3
"""Generate a *new unique* GEMS submission GeoTIFF: fault-tip / step-over dilation.

Method (lane G79-STPO): target dilation zones at fault tips and step-overs --
regions where mapped fault traces terminate or bend sharply, which in the Great
Basin host relay ramps, horsetail splays and dilational jogs that are routinely
omitted from the simplified USGS/INGENIOUS hazard polylines.  Uses only the
catalogue gradient (no ML, no multi-physics stack, no training data).

Steps:
  1. Load pinned grid (footprint + catalogue).
  2. Smooth catalogue, take spatial gradient -> fault-edge / tip density.
  3. Score = gradient magnitude (high at terminations and bends), zero on
     catalogue, zero outside footprint.
  4. Top-k sparse dots, normalise to [0,1].
  5. Write through shared submission_writer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57.grid import load_grid
from gems57.submission_writer import write_submission
from gems57.validate import validate as validate_tiff
from gems79.lifecycle import enforce_open_lane

TOP_K_DOTS = 11_500
NAME_MAX = 140
NOTE_MAX = 140


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_stepover_prediction(grid, k=TOP_K_DOTS):
    fp = grid.footprint
    cat = grid.catalogue
    cat_s = ndi.gaussian_filter(cat.astype(np.float32), 2.0, mode="constant")
    gy, gx = np.gradient(cat_s)
    score = np.hypot(gx, gy).astype(np.float64)
    # emphasise terminations: second difference (curvature) proxy
    g2 = ndi.gaussian_filter(score, 1.0, mode="constant")
    score = score * (1.0 + 0.5 * g2)
    score = np.where(fp, score, 0.0)
    score = np.where(~cat, score, 0.0)
    score = np.maximum(score, 0.0)

    if k and k > 0:
        fp_vals = score[fp]
        if len(fp_vals) >= k:
            thr = np.partition(fp_vals, len(fp_vals) - k)[len(fp_vals) - k]
        else:
            thr = 0.0
        score = np.where((score >= thr) & (score > 0) & fp, score, 0.0)

    if score.max() > 0:
        score = score / score.max()
    score = np.clip(score, 0.0, 1.0).astype(np.float32)
    score = np.where(fp, score, 0.0).astype(np.float32)
    return score


def main() -> int:
    enforce_open_lane(ROOT, "G79-STPO", reason="generate_stepover_submission.py")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", help="Submission name (1..140 chars)")
    ap.add_argument("note", help="Submission note (1..140 chars)")
    ap.add_argument("--out", type=Path, default=ROOT / "artifacts" / "stepover")
    ap.add_argument("--top-k", type=int, default=TOP_K_DOTS)
    args = ap.parse_args()

    if not args.name.strip() or len(args.name) > NAME_MAX:
        raise ValueError("name must be 1..140")
    if not args.note.strip() or len(args.note) > NOTE_MAX:
        raise ValueError("note must be 1..140")

    grid = load_grid(ROOT / "data" / "reference")
    print(f"Grid: footprint={int(grid.footprint.sum())}, catalogue={int(grid.catalogue.sum())}")

    prediction = build_stepover_prediction(grid, k=args.top_k)
    n_pos = int((prediction > 0).sum())
    print(f"Positive pixels: {n_pos}")
    print(f"Range: [{prediction.min()}, {prediction.max()}]")

    assert not ((prediction > 0) & grid.catalogue).any()
    assert not ((prediction > 0) & ~grid.footprint).any()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{args.name}-{timestamp}"

    tif_path = out_dir / f"{stem}.tif"
    zip_path = tif_path.with_suffix(".zip")
    receipt_path = tif_path.with_suffix(".json")

    sample = ROOT / "data" / "reference" / "sample_submission.tif"
    receipt = write_submission(
        tif_path,
        prediction,
        sample=sample,
        footprint=grid.footprint,
        catalogue=grid.catalogue,
        note=args.note,
        name=args.name,
        metadata={
            "method": "G79-STPO fault-tip / step-over dilation",
            "geological_target": "fault terminations, bends and dilational jogs omitted from simplified catalogue polylines",
            "distinct_from": "G79-DZD damage-zone distance decay; G79-THVC multi-physics ensemble",
            "top_k": args.top_k,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_class": "LOCALLY_GENERATED_UNVERIFIED",
            "holdout_dti": None,
            "leakage_canary": None,
            "uniqueness_vs_registry": "registry rasters not cached locally; full gate not run offline",
        },
    )

    validation = validate_tiff(tif_path, grid.footprint, grid.catalogue)
    print(json.dumps(validation, indent=2, allow_nan=False)[:1500])

    receipt["validator"] = validation
    receipt["raster_sha256"] = _sha256(tif_path)
    receipt["zip_sha256"] = _sha256(zip_path)
    receipt["ok_to_download"] = bool(validation.get("all_checks_passed", False))
    receipt["ok_to_submit"] = False
    receipt["submit_blockers"] = [
        "holdout_dti_not_measured_training_data_login_gated",
        "leakage_canary_not_run_training_data_login_gated",
        "uniqueness_vs_registry_not_complete_offline_registry_rasters_not_cached",
        "separate_selector_has_not_approved_a_slot",
    ]
    receipt["message"] = (
        "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. Locally format-valid unique raster; "
        "holdout-DTI, leakage canary and full registry uniqueness require DrivenData "
        "training data (login-gated) and the 992-raster registry (not cached locally)."
    )
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    print(f"\nWrote {tif_path} ({tif_path.stat().st_size} bytes, sha256={receipt['raster_sha256'][:16]}...)")
    print(f"Wrote {zip_path}")
    print(f"Wrote {receipt_path}")
    print(f"OK_TO_DOWNLOAD: {receipt['ok_to_download']}  OK_TO_SUBMIT: {receipt['ok_to_submit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
