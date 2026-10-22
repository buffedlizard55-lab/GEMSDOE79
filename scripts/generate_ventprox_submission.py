#!/usr/bin/env python3
"""Generate a unique research-only TIF: geothermal vent proximity (GDR vents).

NOT a submission. OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.
"""
from __future__ import annotations
import csv, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid
from gems57.submission_writer import write_submission
from gems57 import validate as V

OUT_DIR = ROOT / "artifacts" / "ventprox"
OUT_DIR.mkdir(parents=True, exist_ok=True)

grid = load_grid(ROOT / "data" / "reference")
fp = grid.footprint
cat = grid.catalogue
h, w = fp.shape

# Build vent proximity surface.
vents = list(csv.DictReader(open(ROOT / "data/raw/external/gdr_volcanic_vents_in_footprint.csv")))
score = np.zeros((h, w), dtype=np.float64)
sigma = 8.0
for v in vents:
    r, c = int(v["row"]), int(v["col"])
    if not (0 <= r < h and 0 <= c < w):
        continue
    yy, xx = np.ogrid[:h, :w]
    g = np.exp(-((yy - r) ** 2 + (xx - c) ** 2) / (2 * sigma * sigma))
    score += g

score = np.where(fp, score, 0.0)
score = np.where(~cat, score, 0.0)
score = np.maximum(score, 0.0)
if score.max() > 0:
    score = score / score.max()

# Sparse top-k.
K = 12000
fp_vals = score[fp]
if len(fp_vals) >= K:
    thr = np.partition(fp_vals, len(fp_vals) - K)[len(fp_vals) - K]
    score = np.where((score >= thr) & (score > 0) & fp, score, 0.0)
if score.max() > 0:
    score = score / score.max()
score = np.clip(score, 0.0, 1.0).astype(np.float32)
score = np.where(fp, score, 0.0).astype(np.float32)

n_pos = int((score > 0).sum())
print("vents", len(vents), "positive", n_pos)

name = f"gems79-ventprox-geothermalvents-{n_pos}dots-20261022"
note = "GEMSDOE79 vent-proximity: Gaussian around GDR volcanic vents, zero on catalogue faults, research only"
assert len(name) <= 140 and len(note) <= 140

timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
stem = f"{name}-{timestamp}-zeros-DO-NOT-SUBMIT"
tif_path = OUT_DIR / f"{stem}.tif"

sample = ROOT / "data/reference/sample_submission.tif"
receipt = write_submission(
    tif_path, score, sample, grid.footprint,
    note=note, name=f"{name}-{timestamp}-zeros-DO-NOT-SUBMIT",
    catalogue=grid.catalogue,
    metadata={"method": "vent proximity gaussian", "vents": len(vents), "sigma_px": sigma, "top_k": K},
)
validation = V.validate(tif_path, grid.footprint, grid.catalogue)
print(json.dumps({"all_checks_passed": validation["all_checks_passed"], "positive": validation["emitted_positive_pixels"]}, indent=2))

receipt["validator"] = validation
receipt["raster_sha256"] = hashlib.sha256(tif_path.read_bytes()).hexdigest()
import zipfile
zip_path = tif_path.with_suffix(".zip")
receipt["zip_sha256"] = hashlib.sha256(zip_path.read_bytes()).hexdigest()
receipt["ok_to_download"] = bool(validation.get("all_checks_passed", False))
receipt["ok_to_submit"] = False
receipt["submit_blockers"] = ["research_only_artifact", "novelty_not_cleared", "holdout_not_measured"]
receipt_path = tif_path.with_suffix(".json")
receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
print("Wrote", tif_path)
print("sha256", receipt["raster_sha256"])
