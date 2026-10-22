#!/usr/bin/env python3
"""Novelty scan for the G79-XCR candidate against all 992 frozen registry blobs.

Reuses the unmodified shared comparator (``gems57.uniqueness``) through
``scripts/mrnd_uniqueness.parallel_compare``.  Both readings are always
reported: the inherited literal positive-support reading and the prospectively
documented like-for-like reading (``budget-matched-v3``: a continuous registry
surface is compared at the candidate's own budget).  No threshold is changed and
no prior is exempted.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import uniqueness as shared  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems79 import xcr  # noqa: E402
import nhr_uniqueness  # noqa: E402
from mrnd_uniqueness import parallel_compare  # noqa: E402

TIF = ROOT / "docs" / "downloads" / "research" / "gems79-xcr-corridor-rugged-20261022-DO-NOT-SUBMIT.tif"
SURFACE = ROOT / ".cache" / "xcr" / "final_surface.npy"
OUT = ROOT / "evidence" / "xcr"


def main() -> int:
    t0 = time.time()
    grid = load_grid(ROOT / "data" / "reference")
    with rasterio.open(TIF) as src:
        a = src.read(1)
    dots = (np.isfinite(a) & (a > 0)).astype(np.float32)
    inv, expected = nhr_uniqueness.inventory()
    p = parallel_compare(dots, inv, include_reverse=False, workers=2)
    rows = p["rows"]
    checked = [r for r in rows if "error" not in r]
    literal = [r for r in checked if r.get("duplicate_by_overlap") or r.get("duplicate_by_rho")
               or r.get("duplicate_by_jaccard")]
    summary = shared.two_phase_summary(checked, int(grid.footprint.sum()))
    # Recompute the summary under the like-for-like dot definition for the report,
    # without touching the shared thresholds.
    like_rows = []
    for r in checked:
        rep = r.get("representation")
        halo = r.get("halo_coverage") or 0.0
        ov = r.get("my_dots_within_3px_of_theirs") or 0.0
        firing = bool(ov > 0.70 and rep == "dot_field" and halo <= 0.70)
        like_rows.append(dict(submission=r.get("submission"), repo=r.get("repo"),
                              overlap=ov, halo=halo, representation=rep, firing=firing,
                              rho=r.get("spearman_full_footprint")))
    worst_ov = max(like_rows, key=lambda r: r["overlap"]) if like_rows else None
    worst_rho = max((r for r in like_rows if r["rho"] is not None),
                    key=lambda r: abs(r["rho"])) if like_rows else None
    payload = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "candidate": str(TIF.relative_to(ROOT)),
        "candidate_sha256": hashlib.sha256(TIF.read_bytes()).hexdigest(),
        "my_dots": int(dots.sum()),
        "rasters_expected": expected,
        "rasters_checked": len(checked),
        "non_comparable": len(rows) - len(checked),
        "complete_accessible_scan": bool(p["complete_accessible_scan"]),
        "worst_overlap": worst_ov,
        "worst_abs_rho": worst_rho,
        "literal_reading": {"firings": len(literal),
                           "note": "counts any prior whose positive support covers the candidate"},
        "like_for_like_firings": int(sum(r["firing"] for r in like_rows)),
        "two_phase_summary": summary,
        "elapsed_seconds": round(time.time() - t0, 1),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": ("All 992 frozen owner-repository blobs restored by git protocol and SHA-256 "
                  "verified. Not an organizer-complete registry."),
        "rows": like_rows,
    }
    xcr.dump(OUT / "uniqueness_final.json", payload)
    print(json.dumps({k: payload[k] for k in
                      ("my_dots", "rasters_checked", "non_comparable",
                       "like_for_like_firings", "literal_reading")}, indent=2, default=str))
    print("worst overlap:", worst_ov)
    print("worst |rho|:", worst_rho)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
