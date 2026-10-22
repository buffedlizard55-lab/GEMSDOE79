#!/usr/bin/env python3
"""Informative duplicate check: candidate dots vs registry DOT FIELDS only
(positive support <=200k cells; excludes space-filling plateau surfaces that
flag any map, IR-79-53). Supplementary to shared gate, not a replacement."""
import json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"vendor"), str(ROOT/"scripts")]
if __name__ == "__main__":
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "H79-FF1",
        reason="H79-FF1 is stopped and archived; informative-overlap receipt in evidence/ff1/ is frozen.",
    )
from nhr_uniqueness import inventory
from gems57.grid import load_grid
grid = load_grid(ROOT/"data/reference")
inv, expected = inventory()
cand_files = {"provisional": ROOT/".cache/ff1/provisional_dots.npy", "final": ROOT/".cache/ff1/final_dots.npy"}
out = {}
for name, p in cand_files.items():
    if not p.exists(): continue
    dots = np.load(p); ys, xs = np.nonzero(dots)
    rows = []
    for r in inv["rasters"]:
        try:
            with rasterio.open(r["cache_file"]) as src:
                if src.shape != grid.shape: continue
                a = src.read(1)
        except Exception: continue
        theirs = np.isfinite(a) & (a > 0) & grid.footprint
        n = int(theirs.sum())
        if n == 0 or n > 200_000: continue
        d = ndi.distance_transform_edt(~theirs)
        rows.append(dict(submission=r["sources"][0] if r["sources"] else r["repo_first"], their_dots=n,
                         overlap=float((d[ys, xs] <= 3).mean())))
    rows.sort(key=lambda x: -x["overlap"])
    out[name] = dict(dot_fields_checked=len(rows), worst=rows[0], top10=rows[:10],
                     n_gt_0_70=sum(x["overlap"] > 0.70 for x in rows))
    print(name, out[name]["worst"], "gt70:", out[name]["n_gt_0_70"], flush=True)
(ROOT/"evidence/ff1/informative_overlap.json").write_text(json.dumps(out, indent=2)+"\n")
