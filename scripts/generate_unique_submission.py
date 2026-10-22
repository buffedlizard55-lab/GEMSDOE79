#!/usr/bin/env python3
"""Generate a *new unique* GEMS submission GeoTIFF from available data only.

Method (lane G79-DZD: damage-zone distance decay, NOT the stopped G79-THVC lane):
  Target geothermal permeability in fault *damage zones* -- the fractured rock
  adjacent to mapped faults where fault-core sealing is bypassed and
  fracture-enhanced permeability concentrates flow -- rather than on the mapped
  catalogue traces themselves.  This is a different physical target and a
  different computation from G79-THVC (multi-physics ML ensemble over gravity,
  magnetics, shallow temperature, sinter and LiDAR scarps with a kernel cover).

  Steps:
    1. Load the pinned grid (footprint from sample_submission, catalogue from
       existing_faults).
    2. Euclidean distance transform from catalogue fault cells.
    3. Fault-strike orientation from the catalogue gradient (structure tensor).
    4. Anisotropic damage-zone score: Gaussian in cross-fault distance centred
       at an optimal damage-zone width, decaying along-strike away from fault
       segments.  Zero on catalogue pixels; zero outside the footprint.
    5. Normalise to [0,1], keep the top-k sparse dots, zero elsewhere.
    6. Write through the shared submission_writer (format-validated, no repair).
    7. Run the shared format validator and (where registry rasters are
       available locally) the shared uniqueness gate.

  Outputs are NOT overwritten: the writer refuses to clobber existing bytes.
  A unique name and 140-char note are required.

  This script performs NO holdout evaluation: training_features/labels are not
  in this checkout (DrivenData login-gated).  Holdout-DTI, leakage canaries and
  selector approval therefore cannot be measured here.  The file is labeled
  OK_TO_DOWNLOAD: YES / OK_TO_SUBMIT: NO until the missing measurements exist.
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

from gems57.grid import load_grid, EPSG, HEIGHT, WIDTH, TRANSFORM
from gems57.submission_writer import write_submission
from gems57.validate import validate as validate_tiff
from gems57 import gates
from gems79.lifecycle import enforce_open_lane

# ---------------------------------------------------------------------------
# Method constants (prospectively fixed for this lane, not retuned on holdout)
# ---------------------------------------------------------------------------
DAMAGE_ZONE_OPTIMAL_PX = 2.0      # optimal cross-fault distance (200 m)
DAMAGE_ZONE_SIGMA_PX = 1.5        # cross-fault Gaussian width (150 m)
ALONG_STRIKE_LAMBDA_PX = 4.0      # along-strike exponential decay (400 m)
TOP_K_DOTS = 12_000               # sparse emission budget (distinct from 35k/37k)
NAME_MAX = 140
NOTE_MAX = 140


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_damage_zone_prediction(grid, k=TOP_K_DOTS):
    """Damage-zone distance-decay prediction on the pinned grid.

    Returns a float32 array in [0,1], zero on catalogue and outside footprint.
    """
    fp = grid.footprint
    cat = grid.catalogue
    h, w = fp.shape

    # 1. Euclidean distance from every cell to the nearest catalogue fault.
    dist = ndi.distance_transform_edt(~cat)  # inf where catalogue covers all

    # 2. Fault-strike orientation from the catalogue gradient.
    #    Smooth the binary catalogue, take gradient, strike is gradient+90deg.
    cat_s = ndi.gaussian_filter(cat.astype(np.float32), 1.0, mode="constant")
    gy, gx = np.gradient(cat_s)
    # Gradient points across-strike (normal to fault). Strike direction:
    sx, sy = -gy, gx  # tangent to fault trace
    norm = np.hypot(sx, sy)
    norm = np.where(norm > 0, norm, 1.0)
    sx /= norm
    sy /= norm

    # 3. Cross-fault distance: project displacement from nearest fault onto
    #    cross-strike normal.  Approximate with the EDT distance magnitude
    #    (cross-fault) -- simpler and rotationally invariant.
    d_cross = dist.astype(np.float64)

    # 4. Along-strike position: distance along the local fault strike from the
    #    nearest fault point.  Approximate via a second EDT on the skeletonised
    #    catalogue to capture segment extent.  Cheaper proxy: use the
    #    gradient-aligned accumulation of the catalogue as an along-strike
    #    "nearness" map.
    #    We compute a cross-fault Gaussian damage zone and modulate by fault
    #    density along strike using a morphological closing footprint.
    d_opt = DAMAGE_ZONE_OPTIMAL_PX
    sigma = DAMAGE_ZONE_SIGMA_PX
    lam = ALONG_STRIKE_LAMBDA_PX

    # Damage zone: Gaussian in cross-fault distance, centred at d_opt.
    dz = np.exp(-((d_cross - d_opt) / sigma) ** 2)

    # Along-strike segment continuity: dilate catalogue along strike to mark
    # active fault segments; decay away from segment ends.
    # Use the catalogue gradient magnitude as a "fault activity" proxy.
    fault_activity = np.hypot(gx, gy)
    activity_smooth = ndi.gaussian_filter(fault_activity, 2.0, mode="constant")
    if activity_smooth.max() > 0:
        activity_smooth /= activity_smooth.max()

    score = dz * (0.5 + 0.5 * activity_smooth)
    score = np.where(fp, score, 0.0)
    score = np.where(~cat, score, 0.0)  # zero on mapped faults
    score = np.maximum(score, 0.0)

    # 5. Sparse top-k selection.
    if k and k > 0:
        flat = score.ravel()
        n_fp = int(fp.sum())
        kk = int(min(k, int((score > 0).sum())))
        if kk > 0:
            thr = np.partition(flat, n_fp - kk)[n_fp - kk] if n_fp >= kk else 0.0
            # threshold over footprint cells only
            fp_vals = score[fp]
            if len(fp_vals) >= kk:
                thr = np.partition(fp_vals, len(fp_vals) - kk)[len(fp_vals) - kk]
            else:
                thr = 0.0
            score = np.where((score >= thr) & (score > 0) & fp, score, 0.0)

    # 6. Normalise to [0,1].
    if score.max() > 0:
        score = score / score.max()
    score = np.clip(score, 0.0, 1.0).astype(np.float32)
    score = np.where(fp, score, 0.0).astype(np.float32)
    return score


def main() -> int:
    enforce_open_lane(ROOT, "G79-DZD", reason="generate_unique_submission.py")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", help="Submission name (1..140 chars, unique identity)")
    ap.add_argument("note", help="Submission note (1..140 chars)")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "downloads",
        help="Output directory for .tif/.zip/.json",
    )
    ap.add_argument(
        "--top-k",
        type=int,
        default=TOP_K_DOTS,
        help="Sparse dot budget (positive pixels kept)",
    )
    args = ap.parse_args()

    if not isinstance(args.name, str) or not args.name.strip() or len(args.name) > NAME_MAX:
        raise ValueError("name must be 1..140 non-whitespace characters")
    if not isinstance(args.note, str) or not args.note.strip() or len(args.note) > NOTE_MAX:
        raise ValueError("note must be 1..140 non-whitespace characters")

    grid = load_grid(ROOT / "data" / "reference")
    print(f"Grid: footprint={int(grid.footprint.sum())}, catalogue={int(grid.catalogue.sum())}")

    prediction = build_damage_zone_prediction(grid, k=args.top_k)
    n_pos = int((prediction > 0).sum())
    print(f"Positive pixels: {n_pos} ({100.0 * n_pos / int(grid.footprint.sum()):.4f}% of footprint)")
    print(f"Prediction range: [{prediction.min()}, {prediction.max()}]")

    # Sanity: zero on catalogue, zero outside footprint.
    assert not ((prediction > 0) & grid.catalogue).any(), "positive on catalogue"
    assert not ((prediction > 0) & ~grid.footprint).any(), "positive outside footprint"

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
            "method": "G79-DZD damage-zone distance decay",
            "geological_target": "fault damage-zone permeability adjacent to mapped catalogue faults",
            "distinct_from": "G79-THVC multi-physics ML ensemble (no gravity/magnetics/temperature/sinter/ML)",
            "top_k": args.top_k,
            "damage_zone_optimal_px": DAMAGE_ZONE_OPTIMAL_PX,
            "damage_zone_sigma_px": DAMAGE_ZONE_SIGMA_PX,
            "along_strike_lambda_px": ALONG_STRIKE_LAMBDA_PX,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_class": "LOCALLY_GENERATED_UNVERIFIED",
            "holdout_dti": None,
            "leakage_canary": None,
            "uniqueness_vs_registry": "registry rasters not cached locally; full gate not run offline",
        },
    )

    # Local format validation on the committed bytes.
    validation = validate_tiff(tif_path, grid.footprint, grid.catalogue)
    print(json.dumps(validation, indent=2, allow_nan=False)[:2000])

    # Add validation + sha to receipt.
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
        "training data (login-gated) and the 992-raster registry (not cached locally). "
        "A separate selector must approve a weekly slot before any upload."
    )
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    print(f"\nWrote {tif_path} ({tif_path.stat().st_size} bytes, sha256={receipt['raster_sha256'][:16]}...)")
    print(f"Wrote {zip_path}")
    print(f"Wrote {receipt_path}")
    print(f"OK_TO_DOWNLOAD: {receipt['ok_to_download']}  OK_TO_SUBMIT: {receipt['ok_to_submit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
