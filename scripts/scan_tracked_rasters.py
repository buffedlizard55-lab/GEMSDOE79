#!/usr/bin/env python3
"""Read-only scan of every git-tracked GeoTIFF: grid metadata, NaN count, sentinels, value range.

Purpose: check the official submission rule ("values between 0 and 1"; "data outside
the bounds is null or nan", DrivenData problem page) across all bands of each tracked
raster, and flag files whose values, float32 nodata sentinels (e.g. -3.4028235e+38,
-9999), or fill conventions would be rejected by the organizer portal.
This script never writes a submission and never changes a run card.

Usage:  .venv/bin/python scripts/scan_tracked_rasters.py [--out evidence/review_efdbc11f/tracked_raster_scan.json] [--force]
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
FLOAT32_SENTINELS = (-3.4028235e38, -9999.0, -999.0, 9999.0, 1.0e30)


def _rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def tracked_tifs() -> list[str]:
    files = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return sorted(f for f in files if f.lower().endswith((".tif", ".tiff")))


def _count_sentinels(vals_f32: np.ndarray) -> int:
    if vals_f32.size == 0:
        return 0
    hit = np.zeros(vals_f32.shape, dtype=bool)
    for sent in FLOAT32_SENTINELS:
        if abs(sent) > 1.0e30:
            hit |= vals_f32 <= np.float32(-3.0e38)
        else:
            hit |= vals_f32 == np.float32(sent)
    return int(hit.sum())


def scan_one(rel: str | Path) -> dict:
    p = Path(rel) if Path(rel).is_absolute() else (ROOT / rel)
    label = _rel_path(p)
    rec: dict = {"path": label, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    try:
        with rasterio.open(p) as s:
            arr = s.read()
            a = arr.astype("float64", copy=False)
            raw_nodata = s.nodata
            rec.update(
                crs=str(s.crs),
                shape=[s.height, s.width],
                dtype=s.dtypes[0],
                dtypes=list(s.dtypes),
                count=s.count,
                single_band=bool(s.count == 1),
                bands_checked=int(arr.shape[0]),
                nodata=None if raw_nodata is None or not np.isfinite(raw_nodata) else float(raw_nodata),
                nodata_is_nan=bool(raw_nodata is not None and np.isnan(raw_nodata)),
                transform=[float(v) for v in tuple(s.transform)[:6]],
            )
        finite = np.isfinite(a)
        n_fin = int(finite.sum())
        vals = a[finite]
        vals_f32 = arr[finite].astype(np.float32, copy=False) if n_fin else np.empty(0, dtype=np.float32)
        n_sent = _count_sentinels(vals_f32) if n_fin else 0
        rec.update(
            n_nan=int(np.isnan(a).sum()),
            n_inf=int(np.isinf(a).sum()),
            n_finite=n_fin,
            n_zero=int((vals == 0).sum()) if n_fin else 0,
            n_positive=int((vals > 0).sum()) if n_fin else 0,
            n_sentinel=n_sent,
            min=float(vals.min()) if n_fin else None,
            max=float(vals.max()) if n_fin else None,
            n_outside_0_1=int(((vals < 0) | (vals > 1)).sum()) if n_fin else 0,
            non_single_band_float32=bool(rec["count"] != 1 or any(dt != "float32" for dt in rec["dtypes"])),
        )
    except Exception as exc:  # record, never hide
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="evidence/review_efdbc11f/tracked_raster_scan.json")
    ap.add_argument("--force", action="store_true", help="allow overwriting an existing --out file")
    args = ap.parse_args(argv)
    dest = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    if dest.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing {dest}; pass --force to overwrite")
    records = [scan_one(f) for f in tracked_tifs()]
    flagged = [
        r["path"]
        for r in records
        if (
            r.get("error")
            or r.get("n_outside_0_1")
            or r.get("n_inf")
            or r.get("n_sentinel")
            or r.get("n_finite", 0) == 0
        )
    ]
    out = {
        "schema": "tracked_raster_scan.v2",
        "rule_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "n_tracked_rasters": len(records),
        "flagged_outside_0_1_or_error": flagged,
        "records": records,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"scanned {len(records)} tracked rasters; flagged {len(flagged)} -> {_rel_path(dest)}")
    for r in records:
        if r["path"] in flagged:
            print(
                f"  FLAG {r['path']}: min={r.get('min')} max={r.get('max')} "
                f"outside[0,1]={r.get('n_outside_0_1')} sentinel={r.get('n_sentinel')} error={r.get('error')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
