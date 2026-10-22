#!/usr/bin/env python3
"""Read-only scan of every git-tracked GeoTIFF: grid metadata, NaN count, value range.

Purpose: check the official submission rule ("values between 0 and 1"; "data outside
the bounds is null or nan", DrivenData problem page) across all bands of each tracked
raster, and flag files with out-of-range values, Inf, read errors, or float32 nodata
sentinels (such as -3.4028235e+38 / -9999) that trigger portal range rejections.
This script never writes a submission and never changes a run card.

Usage:  .venv/bin/python scripts/scan_tracked_rasters.py [--out PATH] [--force]
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
SENTINELS_F32 = np.array([-9999.0, -999.0, 9999.0, -3.4e38, 1e30], dtype=np.float32)


def _repo_rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def tracked_tifs() -> list[str]:
    files = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [f for f in files if f.lower().endswith((".tif", ".tiff"))]


def scan_one(path_or_rel: str | Path) -> dict:
    p = Path(path_or_rel)
    if not p.is_absolute():
        p = ROOT / p
    rel = _repo_rel(p)
    rec: dict = {"path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    try:
        with rasterio.open(p) as s:
            raw = s.read()  # all bands: (count, height, width)
            a = raw.astype("float64", copy=False)
            rec.update(
                crs=str(s.crs),
                shape=[s.height, s.width],
                dtype=s.dtypes[0],
                dtypes_all=list(s.dtypes),
                count=s.count,
                bands_checked=int(raw.shape[0]),
                nodata=None if s.nodata is None or not np.isfinite(s.nodata) else float(s.nodata),
                transform=[float(v) for v in tuple(s.transform)[:6]],
            )
        finite = np.isfinite(a)
        n_fin = int(finite.sum())
        vals = a[finite]
        vals_f32 = raw[finite].astype("float32", copy=False) if n_fin else np.empty(0, dtype=np.float32)
        n_sent = int((np.isin(vals_f32, SENTINELS_F32) | (np.abs(vals) > 1e30)).sum()) if n_fin else 0
        rec.update(
            n_nan=int(np.isnan(a).sum()),
            n_inf=int(np.isinf(a).sum()),
            n_finite=n_fin,
            n_zero=int((vals == 0).sum()) if n_fin else 0,
            n_positive=int((vals > 0).sum()) if n_fin else 0,
            min=float(vals.min()) if n_fin else None,
            max=float(vals.max()) if n_fin else None,
            n_outside_0_1=int(((vals < 0) | (vals > 1)).sum()) if n_fin else 0,
            n_sentinel=n_sent,
        )
    except Exception as exc:  # record, never hide
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="evidence/review_efdbc11f/tracked_raster_scan.json")
    ap.add_argument("--force", action="store_true", help="allow overwriting an existing --out file")
    args = ap.parse_args(argv)
    dest = Path(args.out)
    if not dest.is_absolute():
        dest = ROOT / dest
    if dest.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {dest}; pass --force or a new --out path")
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
    non_single_float32 = [
        r["path"]
        for r in records
        if not r.get("error") and (r.get("count") != 1 or r.get("dtype") != "float32")
    ]
    out = {
        "schema": "tracked_raster_scan.v2",
        "rule_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "n_tracked_rasters": len(records),
        "flagged_outside_0_1_or_error": flagged,
        "non_single_band_float32": non_single_float32,
        "records": records,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    print(f"scanned {len(records)} tracked rasters; flagged {len(flagged)} -> {_repo_rel(dest)}")
    for r in records:
        if r["path"] in flagged:
            print(
                f"  FLAG {r['path']}: min={r.get('min')} max={r.get('max')} "
                f"outside[0,1]={r.get('n_outside_0_1')} sentinel={r.get('n_sentinel')} error={r.get('error')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
