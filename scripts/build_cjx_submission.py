#!/usr/bin/env python3
"""Build the final G79-CJX (v3 tip-steered) binary submission raster.

Full-catalogue version of the Exp-3 arm: endpoints from the FULL visible
catalogue (the competition catalogue), allowance >2 px from it, budget
37,654 dots, 2.8 px separation. Written via the shared submission writer
(mode='zeros': finite, in [0,1] or it raises — no clipping, no NaN).
This script only writes bytes; it does NOT approve submission. Approval is
decided solely by scripts/cjx_gate.py against the frozen gates.
"""
from __future__ import annotations
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid, write_submission
from gems79.thvc_model import poisson_disk_emit
from gems79.cjx import catalogue_endpoints as endpoints

BUDGET = 37_654



def _surface_path():
    for cand in (ROOT / "evidence/cjx/cjx_surface.npz", ROOT / ".cache/cjx/cjx_surface.npz"):
        if cand.exists():
            return cand
    raise FileNotFoundError("cjx_surface.npz missing; rerun scripts/run_cjx_experiment.py")


def main():
    grid = load_grid(ROOT / "data/reference")
    footprint, catalogue = grid.footprint, grid.catalogue
    z = np.load(_surface_path())
    v1 = z["cjx_v1_edge"].astype(np.float32)
    d_tip = ndi.distance_transform_edt(~endpoints(catalogue))
    allow = footprint & (ndi.distance_transform_edt(~catalogue) > 2.0)
    surf = (v1 * np.exp(-d_tip / 12.0) + 0.05 * v1).astype(np.float32)
    surf[~footprint] = 0
    dots = poisson_disk_emit(surf, allow, budget=BUDGET, min_dist_px=2.8)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    decoded_sha = hashlib.sha256(dots.astype(np.float32).tobytes()).hexdigest()
    name = f"g79-cjx-tipjunction-{int((dots>0).sum())}dots-{stamp}-{decoded_sha[:8]}-zeros"
    out_dir = ROOT / "artifacts/cjx"  # docs/downloads is reserved by the publication contract for the canonical artifact only
    tif = out_dir / f"{name}.tif"
    info = write_submission(tif, dots, mode="zeros")
    file_sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    import zipfile
    zip_path = out_dir / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, arcname=tif.name)
    meta = {"submission_name": name,
            "note": "G79-CJX tip-steered coincident mag+grav contact junctions, 37654 dots sep2.8px >2px off catalogue",
            "dots": int((dots > 0).sum()), "tif": tif.name, "zip": zip_path.name,
            "tif_sha256": file_sha, "decoded_array_sha256": decoded_sha,
            "writer": info, "built_utc": stamp}
    assert len(meta["note"]) <= 140
    (ROOT / "evidence/cjx/final_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
