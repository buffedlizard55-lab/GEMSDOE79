#!/usr/bin/env python3
"""DIAGNOSTIC ONLY: CJX dot overlap vs sparse registry dot-fields (support
<=5% of footprint). Cannot override the literal G4 gate in cjx_gate.py."""
import json, sys
from pathlib import Path
import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid
from gems79.lifecycle import enforce_open_lane


def main():
    grid = load_grid(ROOT / "data/reference")
    fp = grid.footprint
    meta = json.loads((ROOT / "evidence/cjx/final_build.json").read_text())
    with rasterio.open(ROOT / "artifacts/cjx" / meta["tif"]) as ds:
        dots = (ds.read(1) > 0) & fp
    yx = np.column_stack(np.nonzero(dots)).astype(float)
    idx = json.loads((ROOT / "registry/registry_index.json").read_text())
    rows, skipped = [], 0
    for r in idx["rasters"]:
        p = ROOT / ".cache/registry" / f"{r['blob']}.tif"
        if not p.exists():
            skipped += 1
            continue
        try:
            with rasterio.open(p) as ds:
                a = ds.read(1)
        except Exception:
            skipped += 1
            continue
        if a.shape != fp.shape:
            skipped += 1
            continue
        their = np.isfinite(a) & (a > 0)
        frac = float((their & fp).sum() / fp.sum())
        if frac > 0.05 or not their.any():
            continue
        tree = cKDTree(np.column_stack(np.nonzero(their)).astype(float))
        d, _ = tree.query(yx, k=1)
        rows.append({"blob": r["blob"], "path": r.get("path"),
                     "support_fraction": frac, "overlap": float((d <= 3.0).mean())})
    rows.sort(key=lambda r: -r["overlap"])
    out = {"scope": "DIAGNOSTIC ONLY - sparse dot-fields (support<=5% footprint); cannot override literal G4",
           "n_sparse_checked": len(rows), "skipped_unreadable_or_wrong_shape": skipped,
           "worst_overlap": rows[0]["overlap"] if rows else None,
           "worst_submission": rows[0]["path"] if rows else None, "top5": rows[:5]}
    (ROOT / "evidence/cjx/novelty_sparse_diagnostic.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    enforce_open_lane(ROOT, "G79-CJX", reason="terminal negative CJX diagnostic write")
    main()
