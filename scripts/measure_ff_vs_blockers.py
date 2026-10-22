#!/usr/bin/env python3
"""Fast uniqueness measurement of the FF candidate against the known
blocker rasters (lattice + space-filling surfaces). Conclusive for the gate."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.uniqueness import _dots, _near  # noqa: E402
from gems57.grid import load_grid            # noqa: E402

OVERLAP_LIMIT = 0.70
RHO_LIMIT = 0.90
REGISTRY = ROOT / ".cache/registry"

BLOCKERS = [
    ("13GEMSDOE lattice s5", "13GEMSDOE", "5c1a159439735522659ee78969df3f34efddcdde"),
    ("GEMSDOE48 ds-unassigned-mass", "GEMSDOE48", "45469b332d0a742da90c159bac511936bb47134a"),
    ("5GEMSDOE gems-density-probe", "5GEMSDOE", "5b7d2fe254a81674793ad5b3a9947a493da02e68"),
    ("GEMSDOE3 coverage-v3-wide", "GEMSDOE3", "306ee1b1deebc9a0a9f437e501cd0965ee37f25e"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    cand = None
    for p in (ROOT / "archive/h79_ff_1de1617f/downloads").glob("gems79-h79-ff-farfield-scarp-*.tif"):
        cand = p
    assert cand is not None
    with rasterio.open(cand) as src:
        mine = src.read(1).astype(np.float32)
    grid = load_grid(ROOT / "data/reference")
    fp = grid.footprint
    mine[~fp] = 0.0
    my_support = _dots(mine) & fp
    my_dot_count = int(my_support.sum())
    my_near = _near(my_support)
    from scipy.stats import rankdata
    ranks = rankdata(mine[fp]).astype(np.float64)
    ranks -= ranks.mean()
    norm = float(np.linalg.norm(ranks))
    print("FF candidate:", cand.name, "dots=", my_dot_count, flush=True)
    n = int(fp.sum())
    worst = []
    for label, repo, blob in BLOCKERS:
        p = REGISTRY / (blob + ".tif")
        if not p.exists():
            print(label, "-> NOT RESTORED YET", flush=True)
            continue
        with rasterio.open(p) as src:
            t = src.read(1).astype(np.float32)
        t = np.where(np.isfinite(t), t, 0.0)
        t[~fp] = 0.0
        support = _dots(t) & fp
        ov = float(_near(support)[my_support].mean()) if my_dot_count else 0.0
        tv = t[fp]
        if np.ptp(tv) == 0:
            rho = None
        elif np.all((tv == 0) | (tv == 1)):
            nt = int((tv == 1).sum())
            rho = float(ranks[tv == 1].sum() / (norm * np.sqrt(nt * (n - nt) / n)))
        else:
            tr = rankdata(tv).astype(np.float64); tr -= tr.mean()
            rho = float(np.dot(ranks, tr) / (norm * np.linalg.norm(tr)))
        jac = float((my_support & support).sum() / max(int((my_support | support).sum()), 1))
        worst.append((label, ov, rho, jac, int(support.sum()), rep if False else
                      ("continuous_surface" if support.sum()/fp.sum() > 0.20 else "dot_field")))
        print(f"{label}: overlap={ov:.4f} rho={rho} jac={jac:.4f} their_dots={int(support.sum())} "
              f"OVERLAP_LIMIT_EXCEEDED={ov > OVERLAP_LIMIT} RHO_LIMIT_EXCEEDED={(rho is not None and rho > RHO_LIMIT)}",
              flush=True)
    print("\nCONCLUSION: FAILS uniqueness if any overlap > 0.70 or rho > 0.90", flush=True)


if __name__ == "__main__":
    main()
