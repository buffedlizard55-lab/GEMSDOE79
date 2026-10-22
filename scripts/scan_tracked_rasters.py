#!/usr/bin/env python3
"""Read-only scan of every git-tracked GeoTIFF: grid metadata, NaN count, value range.

Purpose: check the official submission rule ("values between 0 and 1"; "data outside
the bounds is null or nan", DrivenData problem page) against each tracked raster, and
flag files whose values or fill conventions would be questioned by the organizer portal.
This script never writes a submission and never changes a run card.

Usage:  .venv/bin/python scripts/scan_tracked_rasters.py [--out evidence/review_b40c0d45/tracked_raster_scan.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def tracked_tifs() -> list[str]:
    files = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True,
                           text=True, check=True).stdout.split()
    return [f for f in files if f.lower().endswith((".tif", ".tiff"))]


def scan_one(rel: str) -> dict:
    p = ROOT / rel
    rec: dict = {"path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    try:
        with rasterio.open(p) as s:
            a = s.read(1).astype("float64")
            raw_nodata = s.nodata
            rec.update(
                crs=str(s.crs),
                shape=[s.height, s.width],
                dtype=s.dtypes[0],
                count=s.count,
                single_band=bool(s.count == 1),
                nodata=None if raw_nodata is None or not np.isfinite(raw_nodata) else float(raw_nodata),
                nodata_is_nan=bool(raw_nodata is not None and np.isnan(raw_nodata)),
                transform=[float(v) for v in tuple(s.transform)[:6]],
            )
        finite = np.isfinite(a)
        n_fin = int(finite.sum())
        vals = a[finite]
        rec.update(
            n_nan=int(np.isnan(a).sum()),
            n_inf=int(np.isinf(a).sum()),
            n_finite=n_fin,
            n_zero=int((vals == 0).sum()) if n_fin else 0,
            n_positive=int((vals > 0).sum()) if n_fin else 0,
            min=float(vals.min()) if n_fin else None,
            max=float(vals.max()) if n_fin else None,
            n_outside_0_1=int(((vals < 0) | (vals > 1)).sum()) if n_fin else 0,
        )
    except Exception as exc:  # record, never hide
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/review_b40c0d45/tracked_raster_scan.json")
    args = ap.parse_args()
    records = [scan_one(f) for f in tracked_tifs()]
    flagged = [r["path"] for r in records
               if r.get("error") or r.get("n_outside_0_1") or r.get("n_inf")]
    out = {
        "schema": "tracked_raster_scan.v1",
        "rule_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "n_tracked_rasters": len(records),
        "flagged_outside_0_1_or_error": flagged,
        "records": records,
    }
    dest = ROOT / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    print(f"scanned {len(records)} tracked rasters; flagged {len(flagged)} -> {dest.relative_to(ROOT)}")
    for r in records:
        if r["path"] in flagged:
            print(f"  FLAG {r['path']}: min={r.get('min')} max={r.get('max')} "
                  f"outside[0,1]={r.get('n_outside_0_1')} error={r.get('error')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
