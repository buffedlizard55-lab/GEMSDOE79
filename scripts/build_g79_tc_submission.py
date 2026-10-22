#!/usr/bin/env python3
"""Build a *new unique* GEMS research GeoTIFF from the measured Band-6 'tc'
(magnetic tilt / total-curvature edge-detection) channel.

Lane `G79-TC`: single-channel edge-detection surface from the cached 19-band
training feature stack -- distinct from G79-THVC (84-channel ensemble), G79-DZD
(damage-zone distance decay) and G79-CJX (potential-field junctions).

Method (prospectively fixed, not retuned on holdout):
  1. Load Band 6 'tc' from data/raw/training_features.tif (pinned mirror).
  2. Min-max normalise to [0,1] over finite footprint cells.
  3. Zero on mapped USGS/INGENIOUS catalogue faults; zero outside footprint.
  4. Keep the top-10,000 sparse dots; binary {0,1}; hence finite and in [0,1].
  5. Write through the shared submission_writer (format-validated, no repair)
     and re-validate the on-disk bytes with the shared validator.
  6. Record a lane run card: hypothesis, mechanism, named non-fault mimic,
     HOLDOUT-DTI + 95% CI (measured, seeds 20/30), leakage canary, registry
     overlap (blocked by the pinned universal witness), raster SHA-256,
     validator output, submission name + note (<=140 chars), verdict.

This script performs NO competition upload. The file is labeled
OK_TO_DOWNLOAD: YES / OK_TO_SUBMIT: NO because (a) holdout-DTI is far below
the incumbent, (b) the literal novelty gate blocks every nonempty candidate
under the pinned 17GEMSDOE full-footprint witness, (c) no selector has
approved a slot, and (d) no organizer receipt exists.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid, EPSG, HEIGHT, WIDTH, TRANSFORM
from gems57.submission_writer import write_submission
from gems57.validate import validate as validate_tiff

BAND_INDEX = 6          # 'tc' tilt / total curvature (edge detection)
TOP_K = 10_000
NAME_MAX = 140
NOTE_MAX = 140


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_tc_dots(grid):
    fp = grid.footprint
    cat = grid.catalogue
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as ds:
        band = ds.read(BAND_INDEX).astype(np.float64)
        nd = ds.nodata
    if nd is not None:
        band = np.where(band == nd, np.nan, band)
    band_fp = np.where(fp, band, np.nan)
    finite_fp = fp & np.isfinite(band_fp)
    vals = band_fp[finite_fp]
    lo, hi = float(vals.min()), float(vals.max())
    surface = np.zeros(fp.shape, np.float64)
    if hi > lo:
        surface[finite_fp] = (band_fp[finite_fp] - lo) / (hi - lo)
    surface = np.where(cat, 0.0, surface)      # zero on mapped faults
    surface = np.where(fp, surface, 0.0)       # zero outside footprint
    surface = np.clip(surface, 0.0, 1.0)
    fp_vals = surface[fp]
    kk = min(TOP_K, int((surface > 0).sum()))
    dots = np.zeros(fp.shape, np.float32)
    if kk > 0 and fp_vals.size >= kk:
        thr = float(np.partition(fp_vals, fp_vals.size - kk)[fp_vals.size - kk])
        dots = ((surface >= thr) & (surface > 0) & fp).astype(np.float32)
    return dots, lo, hi, kk


def main() -> int:
    grid = load_grid(ROOT / "data" / "reference")
    print(f"Grid: footprint={int(grid.footprint.sum())}, catalogue={int(grid.catalogue.sum())}")
    dots, lo, hi, kk = build_tc_dots(grid)
    n_pos = int((dots > 0).sum())
    print(f"Band {BAND_INDEX} 'tc': surface range [{lo}, {hi}]; top-{kk}; positive pixels {n_pos}")
    print(f"Dot range [{dots.min()}, {dots.max()}]; on catalogue={int(((dots > 0) & grid.catalogue).sum())}; "
          f"outside footprint={int(((dots > 0) & ~grid.footprint).sum())}")
    assert not ((dots > 0) & grid.catalogue).any(), "positive on catalogue"
    assert not ((dots > 0) & ~grid.footprint).any(), "positive outside footprint"
    assert np.isfinite(dots).all() and dots.min() >= 0 and dots.max() <= 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"g79-tc-edge-curvature-{kk}dots-{timestamp}-DO-NOT-SUBMIT"
    assert 0 < len(name) <= NAME_MAX
    note = ("G79-TC: Band 6 magnetic tilt/curvature edge surface, zero on mapped faults, "
            f"{kk} sparse dots, [0,1]")
    assert 0 < len(note) <= NOTE_MAX, len(note)

    out_dir = ROOT / "artifacts" / "g79_tc"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = name
    tif_path = out_dir / f"{stem}.tif"
    zip_path = tif_path.with_suffix(".zip")
    receipt_path = tif_path.with_suffix(".json")

    sample = ROOT / "data" / "reference" / "sample_submission.tif"
    receipt = write_submission(
        tif_path,
        dots,
        sample=sample,
        footprint=grid.footprint,
        catalogue=grid.catalogue,
        note=note,
        name=name,
        metadata={
            "method": "G79-TC single-channel magnetic edge-detection (Band 6 tc)",
            "geological_target": "blind fault edges missing from the USGS/INGENIOUS catalogue",
            "band": BAND_INDEX, "band_name": "tc",
            "surface_min": lo, "surface_max": hi,
            "top_k": kk, "positive_pixels": n_pos,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_class": "LOCALLY_GENERATED_MEASURED_NEGATIVE",
            "source_feature_stack": "data/raw/training_features.tif (sha256 4371c82e...)",
        },
    )

    validation = validate_tiff(tif_path, grid.footprint, grid.catalogue)
    print(json.dumps(validation, indent=2, allow_nan=False)[:2500])

    # ---- lane run card (protocol rule 5) ----
    holdout = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": "gems57-pooled-hide-v2",
        "alpha": 0.2, "beta": 0.8, "triangular_radius_m": 300,
        "per_seed": {
            "seed_20": {"dti": 0.0017808386751360411,
                        "ci95": [0.0002524377420726441, 0.0035880773068268455],
                        "withheld_positive_pixels": 11321},
            "seed_30": {"dti": 0.000617214278911799,
                        "ci95": [0.0, 0.0015195050603299483],
                        "withheld_positive_pixels": 11342},
        },
        "source_pointer": "evidence/g79_single_channel_screen.json",
        "note": "Measured single-channel Band-6 tc holdout-DTI; negative vs the G79-THVC incumbent "
                "(0.1905 / 0.1944) and vs the H33 analogue control.",
    }
    canary = {
        "evidence_class": "LEAKAGE-CANARY",
        "threshold": 0.90,
        "per_seed": {
            "seed20": {"max_symmetric_auc": 0.528913585372317, "passed": True},
            "seed30": {"max_symmetric_auc": 0.5444027166725445, "passed": True},
        },
        "passed": True,
        "source": "evidence/g79_single_channel_screen.json",
    }
    card = {
        "schema_version": 1,
        "lane": "G79-TC",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": ("Band 6 'tc' (magnetic tilt / total curvature, an edge-detection / curvature "
                       "transform) surfaces blind fault edges missing from the USGS/INGENIOUS catalogue; "
                       "unmapped blind faults still perturb the magnetic field gradient at their edges."),
        "mechanism": ("Min-max normalise Band 6 to [0,1] over the footprint; zero on mapped catalogue "
                      "faults and outside the footprint; keep top-10,000 sparse binary dots. Single "
                      "deterministic channel -- no ML, no multi-physics stack, no kernel cover."),
        "named_non_fault_mimic": ("Magnetic fabric, intrusive-contact edges and remanent-magnetization "
                                  "contrasts unrelated to Quaternary faulting."),
        "distinct_from": "G79-THVC (84-channel ensemble), G79-DZD (damage-zone distance decay), G79-CJX (junctions)",
        "holdout_dti": holdout,
        "leakage_canary": canary,
        "correlation_overlap_vs_registry": {
            "registry_rasters_expected": 1108,
            "registry_rasters_checked": 0,
            "detail": "992-raster registry not cached locally; full scan not runnable offline. "
                      "The pinned universal-overlap witness (17GEMSDOE E-proba-multiscale) covers "
                      "100.0% of allowed cells, so under the literal protocol rule any nonempty "
                      "candidate has 3-px forward overlap 1.0000 > 0.70 -- uniqueness is BLOCKED, "
                      "not merely unmeasured. Rank correlation vs registry therefore not cleared.",
            "surface_rank_correlation": None,
            "final_dot_overlap": None,
            "literal_gate_blocked": True,
        },
        "raster_sha256": _sha256(tif_path),
        "zip_sha256": _sha256(zip_path),
        "bytes": tif_path.stat().st_size,
        "validator": validation,
        "validator_output": validation,
        "all_checks_passed": bool(validation.get("all_checks_passed", False)),
        "submission_name": name,
        "submission_note": note,
        "submission_note_chars": len(note),
        "tif": f"{stem}.tif",
        "zip": f"{stem}.zip",
        "artifact_dir": "artifacts/g79_tc",
        "generator": "scripts/build_g79_tc_submission.py",
        "ok_to_download": bool(validation.get("all_checks_passed", False)),
        "ok_to_submit": False,
        "verdict": "negative",
        "submission_slots_used": 0,
        "approved_for_weekly_slot": False,
        "selector_receipt": None,
        "organizer_submission_receipt": None,
        "blockers": [
            "holdout_dti_far_below_incumbent_tc_single_channel_0.0018_vs_0.1905",
            "literal_novelty_blocked_universal_witness_100_percent_footprint_coverage",
            "full_registry_uniqueness_not_runnable_offline",
            "no_selector_slot_approval",
            "no_organizer_submission_receipt",
        ],
        "message": (
            "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO. Locally format-valid unique raster ([0,1], no NaN, "
            "matching CRS/shape/transform). Holdout-DTI measured (~0.0018), far below the incumbent; "
            "literal novelty gate blocked by the pinned full-footprint witness; no selector approval or "
            "organizer receipt. Do not upload."
        ),
    }
    card["holdout_dti"].update({
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": "gems57-pooled-hide-v2",
        "dti": 0.0017808386751360411,
        "ci95": [0.0002524377420726441, 0.0035880773068268455],
        "withheld_positive_pixels": 11321,
        "seed": 20,
        "headline_seed": 20,
    })
    card["secondary_holdout_dti"] = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": "gems57-pooled-hide-v2",
        "dti": 0.000617214278911799,
        "ci95": [0.0, 0.0015195050603299483],
        "withheld_positive_pixels": 11342,
        "seed": 30,
    }
    card["leakage_canary"].update({
        "evidence_class": "LEAKAGE-CANARY",
        "auc": 0.5444027166725445,
        "passed": True,
        "features_cleared": 1,
        "required_threshold": 0.90,
        "n_features_tested": 1,
        "n_suspicious_gt_0p90": 0,
        "max_feature": "tc_band_6",
        "source": "evidence/g79_single_channel_screen.json",
    })
    card_path = out_dir / "run_card_g79_tc.json"
    card_path.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")

    receipt["validator"] = validation
    receipt["raster_sha256"] = _sha256(tif_path)
    receipt["zip_sha256"] = _sha256(zip_path)
    receipt["ok_to_download"] = card["ok_to_download"]
    receipt["ok_to_submit"] = False
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    print(f"\nWrote {tif_path} ({tif_path.stat().st_size} bytes, sha256={_sha256(tif_path)[:16]}...)")
    print(f"Wrote {zip_path}")
    print(f"Wrote {card_path}")
    print(f"Wrote {receipt_path}")
    print(f"OK_TO_DOWNLOAD: {card['ok_to_download']}  OK_TO_SUBMIT: {card['ok_to_submit']}")
    print("VERDICT: negative -- DO NOT SUBMIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
