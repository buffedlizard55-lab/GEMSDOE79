#!/usr/bin/env python3
"""One-pass H79-DILSTEP registry scan.

Reads each hash-verified raster once. Spearman of the continuous surface and
forward overlap of the provisional dots use the same formulas as
vendor/gems57/uniqueness.py (budget-matched-v3 for continuous priors). The
operative stop rule is IR-79-67: rho > 0.90 always stops; overlap > 0.70
stops only when that prior's own 3 px halo covers at most 0.70 of allowed
cells. Literal overlap is recorded and is not called uniqueness.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57.grid import TRANSFORM, load_grid  # noqa: E402
from gems57.uniqueness import (  # noqa: E402
    OVERLAP_LIMIT,
    RHO_LIMIT,
    _near,
    budget_matched_dots,
    representation_class,
)
from nhr_uniqueness import inventory  # noqa: E402

RAW = ROOT / "data/raw"
CACHE = ROOT / ".cache/dilstep"
OUT = ROOT / "evidence/dilstep"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def centered_ranks(values: np.ndarray):
    ranks = rankdata(values).astype(np.float64)
    ranks -= ranks.mean()
    return ranks, float(np.linalg.norm(ranks))


def rho_against(ranks, norm, tv: np.ndarray):
    """Match gems57.uniqueness.compare_array_to_registry."""
    if norm == 0 or np.ptp(tv) == 0:
        return None
    if np.all((tv == 0) | (tv == 1)):
        tb = tv > 0
        nt = int(tb.sum())
        n = len(tv)
        if nt == 0 or nt == n:
            return None
        return float(ranks[tb].sum() / (norm * np.sqrt(nt * (n - nt) / n)))
    tr = rankdata(tv).astype(np.float64)
    tr -= tr.mean()
    denom = norm * float(np.linalg.norm(tr))
    if denom == 0:
        return None
    return float(np.dot(ranks, tr) / denom)


def main() -> int:
    grid = load_grid(RAW)
    footprint = grid.footprint
    allowed = footprint & ~grid.catalogue
    dots = np.load(CACHE / "provisional_dots.npy").astype(bool) & footprint
    surface = np.load(CACHE / "surface_unit.npy").astype(np.float32)
    surface = np.where(np.isfinite(surface), surface, 0)
    surface[~footprint] = 0
    fp_idx = footprint
    surface_ranks, surface_norm = centered_ranks(surface[fp_idx])
    inv, expected = inventory()
    rows = []
    not_comparable = []
    hash_failures = []
    worst_rho = -1.0
    worst_rho_name = None
    worst_overlap = -1.0
    worst_overlap_name = None
    informative_flags = []
    waived = []
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] scan {expected}", flush=True)
    for i, rec in enumerate(inv["rasters"], start=1):
        name = rec["sources"][0] if ":" in rec["sources"][0] else rec["repo_first"] + ":" + rec["sources"][0]
        path = Path(rec["cache_file"])
        try:
            digest = sha256_file(path)
            if digest != rec["sha256"]:
                hash_failures.append({"submission": name, "error": "registry SHA256 pin mismatch"})
                continue
            with rasterio.open(path) as src:
                if src.count != 1 or src.shape != grid.shape:
                    raise ValueError("registry grid or band-count mismatch")
                if src.crs is None or src.crs.to_epsg() != 32611 or src.transform != TRANSFORM:
                    raise ValueError("registry CRS/transform mismatch")
                theirs = src.read(1).astype(np.float32)
            theirs = np.where(np.isfinite(theirs), theirs, 0.0)
            theirs[~footprint] = 0
            tv = theirs[fp_idx]
            literal = int(((theirs > 0) & footprint).sum())
            kind = representation_class(literal, int(footprint.sum()))["kind"]
            rho = rho_against(surface_ranks, surface_norm, tv)
            support = (theirs > 0) & footprint
            if kind == "continuous_surface":
                support = budget_matched_dots(theirs, footprint, int(dots.sum()))
            near = _near(support)
            overlap = float(near[dots].mean()) if dots.any() else 0.0
            halo = None
            row = {
                "submission": name,
                "sha256": digest,
                "representation": kind,
                "their_literal_positive_cells": literal,
                "their_dots": int(support.sum()),
                "spearman_surface": rho,
                "overlap": overlap,
            }
            if rho is not None and rho > worst_rho:
                worst_rho, worst_rho_name = rho, name
            if overlap > worst_overlap:
                worst_overlap, worst_overlap_name = overlap, name
            if rho is not None and rho > RHO_LIMIT:
                row["rho_flag"] = True
            if overlap > OVERLAP_LIMIT:
                halo = float(near[allowed].mean())
                row["halo_coverage"] = halo
                if halo <= 0.70:
                    informative_flags.append(row)
                else:
                    waived.append({"submission": name, "overlap": overlap, "halo_coverage": halo, "representation": kind})
            if row.get("rho_flag") or overlap > 0.50 or halo is not None:
                rows.append(row)
        except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
            not_comparable.append({"submission": name, "file": rec["cache_file"], "error": str(exc)})
        if i % 50 == 0 or i == expected:
            print(f"  {i}/{expected} worst_rho={worst_rho:.4f} worst_overlap={worst_overlap:.4f} informative={len(informative_flags)}", flush=True)
    rho_flags = [row["submission"] for row in rows if row.get("rho_flag")]
    passed = not rho_flags and not informative_flags and not hash_failures
    report = {
        "schema_version": 1,
        "lane": "H79-DILSTEP",
        "phase": "surface",
        "evidence_class": "REGISTRY-MEASUREMENT",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "definition": "IR-79-67. Spearman of the continuous unit surface > 0.90 stops. Forward overlap of the provisional 37,654 dots > 0.70 stops only if that prior's 3 px halo covers <= 0.70 of allowed cells. Continuous priors use shared budget-matched-v3 dots. Literal overlap is printed as worst_overlap and is not the operative flag.",
        "shared_helpers": ["gems57.uniqueness.budget_matched_dots", "gems57.uniqueness.representation_class", "gems57.uniqueness._near"],
        "shared_tool_sha256": sha256_file(ROOT / "vendor/gems57/uniqueness.py"),
        "dot_definition_for_continuous": "budget-matched-v3",
        "rho_limit": RHO_LIMIT,
        "overlap_limit": OVERLAP_LIMIT,
        "registry_rasters_expected": expected,
        "compared": expected - len(not_comparable) - len(hash_failures),
        "not_comparable": not_comparable,
        "hash_failures": hash_failures,
        "my_dots": int(dots.sum()),
        "surface_decoded_sha256": hashlib.sha256(np.ascontiguousarray(surface).tobytes()).hexdigest(),
        "dots_decoded_sha256": hashlib.sha256(np.ascontiguousarray(dots.astype(np.uint8)).tobytes()).hexdigest(),
        "worst_spearman_surface": worst_rho if worst_rho_name else None,
        "worst_rho_submission": worst_rho_name,
        "worst_overlap_budget_matched": worst_overlap if worst_overlap_name else None,
        "worst_overlap_submission": worst_overlap_name,
        "operative": {
            "passed": passed,
            "rho_flags": rho_flags,
            "informative_overlap_flags": informative_flags,
            "noninformative_overlap_waived_count": len(waived),
            "noninformative_overlap_waived_worst": max(waived, key=lambda r: r["overlap"]) if waived else None,
        },
        "surface_gate_passed": passed,
        "high_overlap_or_rho_rows": rows,
        "literal_unique": False,
        "literal_note": "Literal overlap is not uniqueness. The witness raster covers every allowed cell, so every nonempty candidate has literal overlap 1.0 against it. That fact is recorded in evidence/universal_overlap_certificate.json and is not re-measured here.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "uniqueness_surface.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("surface_gate_passed", passed, "worst_rho", worst_rho, "informative", len(informative_flags), flush=True)
    return 0 if passed else 2


if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError, require_open_lane
    try:
        require_open_lane(ROOT, 'H79-DILSTEP')
    except LaneClosedError as _exc:
        print(str(_exc), file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
