#!/usr/bin/env python3
"""Place H79-ARC final dots - only after the surface uniqueness check exists.

Sequencing (protocol rule 1): scripts/arc_uniqueness.py surface must have
run on the exact cached surface before any dot is placed.  If that check
failed, placement still runs so the negative result has auditable bytes
(repo precedent: E1/H79-NHR research artifacts), but finalize_arc.py will
label the file DO-NOT-SUBMIT and the selector will refuse it.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid      # noqa: E402
from gems79.cover import place_cover   # noqa: E402

BUDGET = 37654
CACHE = ROOT / ".cache" / "arc"
OUT = ROOT / "evidence" / "arc"


def main():
    surf_check = json.loads((OUT / "uniqueness_surface.json").read_text())
    surface = np.load(CACHE / "final_surface.npy")
    surf_sha = hashlib.sha256(surface.tobytes()).hexdigest()
    if surf_check.get("surface_sha256") != surf_sha:
        raise SystemExit("surface uniqueness check does not match cached surface; refusing")
    allowed = np.load(CACHE / "final_allowed.npy")
    grid = load_grid(ROOT / "data/reference")
    dots, info = place_cover(surface, allowed, BUDGET)
    dots = dots & grid.footprint & ~grid.catalogue
    np.save(CACHE / "final_dots.npy", dots)
    meta = dict(placement=info, surface_sha256=surf_sha,
                dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
                n_dots=int(dots.sum()),
                surface_gate_passed_d2=surf_check.get("passed_d2"))
    (OUT / "x1_final_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
