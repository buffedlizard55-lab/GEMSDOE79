#!/usr/bin/env python3
"""REGISTRY-MEASUREMENT: pre-placement (surface top-k) overlap against the registry dot
fields that flagged the final H79-NHR dots (evidence/nhr/overlap_chance.json).

Answers whether the surface check alone would already have stopped the lane.
It uses the shared helpers only.
"""
import json, sys
from pathlib import Path
import numpy as np, rasterio
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared
from gems57.grid import load_grid
from gems79.lifecycle import LaneClosedError, require_open_lane
from nhr_uniqueness import inventory, BUDGET


def main():
    require_open_lane(ROOT, "H79-NHR")
    g = load_grid(ROOT / "data/reference"); fp = g.footprint; allowed = fp & ~g.catalogue
    surface = np.load(ROOT / ".cache/nhr/final_surface.npy")
    prov = shared.budget_matched_dots(surface, allowed, BUDGET)
    chance = json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())
    flagged = {r["sha256"]: r for r in chance["rows"] if r["overlap_candidate"] > shared.OVERLAP_LIMIT and r["halo_coverage"] <= shared.OVERLAP_LIMIT}
    inv, _ = inventory(); rows = []
    for rec in inv["rasters"]:
        if rec["sha256"] not in flagged:
            continue
        with rasterio.open(rec["cache_file"]) as s:
            a = s.read(1).astype(np.float32)
        a = np.where(np.isfinite(a), a, 0); a[~fp] = 0
        halo = shared._near((a > 0) & fp)
        r = flagged[rec["sha256"]]
        rows.append(dict(submission=r["submission"], provisional_topk_overlap=float(halo[prov].mean()),
                         final_dot_overlap=r["overlap_candidate"], halo_coverage=r["halo_coverage"]))
    rows.sort(key=lambda r: -r["provisional_topk_overlap"])
    out = dict(evidence_class="REGISTRY-MEASUREMENT", provisional_cells=int(prov.sum()), rows=rows,
               surface_check_would_have_stopped=any(r["provisional_topk_overlap"] > shared.OVERLAP_LIMIT for r in rows))
    (ROOT / "evidence/nhr/surface_topk_vs_flagged.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("provisional_cells", "surface_check_would_have_stopped")}), rows[:3])


if __name__ == "__main__":
    try:
        main()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
