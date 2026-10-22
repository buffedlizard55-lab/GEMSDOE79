#!/usr/bin/env python3
"""Uniqueness audit helpers for G79B (shared gems57 tool, unmodified).

compare_full() runs vendor gems57.uniqueness.compare_array_to_registry over
all 992 hash-verified registry rasters and applies the template's own
two_phase_summary (Decision D-1 resolution, see
registry/preregistration_g79b.json). extra_continuous() adds the two
stricter-than-template tests for continuous-surface priors: forward 3 px
overlap of the candidate dots against their >=0.5 cells and their
top-37,654 cells.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import uniqueness as U  # noqa: E402
from gems79.lifecycle import enforce_open_lane  # noqa: E402
from gems79b import data as D  # noqa: E402

K = 37_654


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def registry_records():
    index = json.loads((ROOT / "registry" / "registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry" / "registry_receipt.json").read_text())
    pins = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    records = []
    for row in index["rasters"]:
        records.append({
            "repo": row["repo"],
            "submission": row["repo"] + ":" + row["path"],
            "file": str(ROOT / ".cache" / "registry" / (row["blob"] + ".tif")),
            "sha256": pins[row["blob"]]["sha256"],
            "blob": row["blob"],
            "aliases": row.get("aliases", []),
        })
    return records


def compare_full(mine, phase, out_path, file_sha256=None):
    grid = D.load_grid()
    records = registry_records()

    def prog(i, n, row):
        if i % 50 == 0 or i == n:
            log(f"{phase} compare {i}/{n}")

    result = U.compare_array_to_registry(
        np.asarray(mine, np.float32), records, grid.footprint,
        file_sha256=file_sha256, include_reverse=True, progress=prog,
        expected_grid=(grid.shape, grid.crs, grid.transform))
    rows = result["rows"]
    two = U.two_phase_summary(rows, int(grid.footprint.sum()), expected_rasters=len(records))
    audit = {
        "phase": phase, "evidence_class": "REGISTRY-MEASUREMENT",
        "shared_tool": "gems57.uniqueness.compare_array_to_registry + two_phase_summary",
        "shared_tool_sha256": hashlib.sha256((ROOT / "vendor/gems57/uniqueness.py").read_bytes()).hexdigest(),
        "registry_expected": len(records),
        "registry_checked": sum(1 for r in rows if "error" not in r),
        "registry_errors": [r for r in rows if "error" in r],
        "candidate_decoded_sha256": result["candidate_decoded_sha256"],
        "candidate_file_sha256": file_sha256,
        "my_dots": result["my_dots"],
        "byte_unique_among_checked": result["byte_unique_among_checked"],
        "pixel_unique_among_checked": result["pixel_unique_among_checked"],
        "two_phase": two,
        "rows": rows,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(audit, indent=1, default=float) + "\n")
    log(f"{phase}: checked={audit['registry_checked']} errors={len(audit['registry_errors'])} "
        f"worst_rho={two['literal_reading']['worst_spearman_full_footprint']} "
        f"worst_dotfield_overlap={two['like_for_like_reading']['worst_forward_overlap_dot_fields']} "
        f"literal_firings={two['literal_reading']['forward_overlap_firings']}")
    return audit


def _halo_overlap(my_dots, their_mask):
    if not my_dots.any() or not their_mask.any():
        return 0.0
    return float(U._near(their_mask)[my_dots].mean())


def extra_continuous(final_dots, surface_topk, rows, out_path):
    """Stricter continuous-prior tests (preregistered). Candidate must have
    <=0.70 forward overlap against BOTH the >=0.5 cells and the top-K cells
    of every continuous-surface prior (support > 20% of footprint)."""
    grid = D.load_grid()
    fp = grid.footprint
    fp_idx = np.flatnonzero(fp)
    cont = [r for r in rows if "error" not in r
            and U.representation_class(int(r["their_dots"]), int(fp.sum()))["kind"] == "continuous_surface"]
    from gems79b import trace as T
    allowed = T.allowed_domain(fp, grid.catalogue, 2.0)
    out_rows = []
    for i, r in enumerate(cont, 1):
        with rasterio.open(r["file"]) as src:
            a = src.read(1).astype(np.float32)
        a = np.where(np.isfinite(a), a, 0.0)
        vals = a[fp]
        ge05 = fp & (a >= 0.5)
        cov = float(T.halo(ge05, 3.0)[allowed].mean())
        top = np.argpartition(vals, -K)[-K:]
        topk = np.zeros(a.shape, bool)
        topk.ravel()[fp_idx[top]] = True
        row = {
            "submission": r["submission"], "sha256": r["sha256"], "their_dots": r["their_dots"],
            "n_ge_0p5": int(ge05.sum()),
            "ge05_halo_coverage_allowed": cov, "ge05_discriminating": bool(cov < 0.70),
            "final_overlap_vs_ge05": _halo_overlap(final_dots, ge05),
            "final_exact_overlap_vs_ge05": float(ge05[np.asarray(final_dots, bool)].mean()),
            "final_overlap_vs_topk": _halo_overlap(final_dots, topk),
            "surface_topk_overlap_vs_ge05": _halo_overlap(surface_topk, ge05),
            "surface_topk_overlap_vs_topk": _halo_overlap(surface_topk, topk),
        }
        out_rows.append(row)
        if i % 20 == 0:
            log(f"extra-continuous {i}/{len(cont)}")
    worst = max((max(r["final_overlap_vs_ge05"], r["final_overlap_vs_topk"]) for r in out_rows), default=0.0)
    worst_topk = max((r["final_overlap_vs_topk"] for r in out_rows), default=0.0)
    disc_bad = [r for r in out_rows if r["ge05_discriminating"] and r["final_overlap_vs_ge05"] > 0.70]
    amended = bool(worst_topk <= 0.70 and not disc_bad)
    audit = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "test": "candidate forward 3px overlap vs continuous priors' >=0.5 and top-37654 cells",
        "continuous_priors_checked": len(out_rows), "worst_final_overlap": worst,
        "worst_final_overlap_topk": worst_topk, "limit": 0.70,
        "passed": bool(worst <= 0.70),
        "passed_amended_B2": amended,
        "amendment": "B2: >=0.5 leg binds only where discriminating (halo coverage < 0.70); top-K + Spearman bind everywhere. See registry/preregistration_g79b_amendment_B2.json",
        "rows": out_rows,
    }
    Path(out_path).write_text(json.dumps(audit, indent=1, default=float) + "\n")
    log(f"extra-continuous: {len(out_rows)} priors, worst final overlap={worst:.4f}, passed={audit['passed']}")
    return audit


def classify_firings(candidate_dots, firing_rows):
    """Amendment B1 classification of dot-field firings (>0.70 halo overlap):
    discriminating iff the prior's 3 px halo covers < 0.70 of the allowed
    domain. Returns one row per unique decoded support with halo coverage
    and exact-cell overlap for the candidate dots."""
    grid = D.load_grid()
    from gems79b import trace as T
    allowed = T.allowed_domain(grid.footprint, grid.catalogue, 2.0)
    dots = np.asarray(candidate_dots, bool)
    seen = {}
    for r in firing_rows:
        seen.setdefault(r["decoded_sha256"], r)
    out = []
    for r in seen.values():
        with rasterio.open(r["file"]) as src:
            a = src.read(1)
        sup = np.isfinite(a) & (a > 0) & grid.footprint
        cov = float(T.halo(sup, 3.0)[allowed].mean())
        out.append({
            "submission": r["submission"], "file": r["file"], "sha256": r["sha256"],
            "decoded_sha256": r["decoded_sha256"], "their_dots": r["their_dots"],
            "halo_overlap": r["my_dots_within_3px_of_theirs"],
            "halo_coverage_allowed": cov,
            "exact_dot_overlap": float(sup[dots].mean()) if dots.any() else 0.0,
            "discriminating": bool(cov < 0.70),
        })
    return sorted(out, key=lambda o: -o["halo_overlap"])


def disposition_errors(candidate, rows):
    """Individually disposition registry files the shared tool cannot compare
    (wrong transform/shape or unreadable). Shape-matching files are measured
    with the shared U.surface_rho / U.dot_overlap array functions as-if
    pixel-aligned (a screening upper bound; their stored transform is NOT
    the competition grid, so they could never be scored submissions).
    Non-grid/unreadable files are recorded byte-distinct by their pinned
    sha256 and cannot represent a grid prediction at all."""
    grid = D.load_grid()
    fp = grid.footprint
    cand = np.asarray(candidate, np.float32)
    out = []
    for r in rows:
        if "error" not in r:
            continue
        rec = {"submission": r["submission"], "file": r["file"],
               "shared_tool_error": r["error"], "sha256": r.get("sha256")}
        try:
            with rasterio.open(r["file"]) as src:
                meta = {"count": src.count, "shape": [src.height, src.width],
                        "crs": str(src.crs), "transform": list(tuple(src.transform)[:6])}
                arr = src.read(1).astype(np.float32) if src.count >= 1 else None
        except Exception as e:  # unreadable/corrupt TIFF
            rec.update({"disposition": "unreadable_not_a_grid_prediction", "open_error": str(e)[:200]})
            out.append(rec)
            continue
        rec["meta"] = meta
        if arr is None or arr.shape != fp.shape:
            rec.update({"disposition": "wrong_shape_not_competition_grid"})
            out.append(rec)
            continue
        theirs = np.where(np.isfinite(arr), arr, 0.0)
        theirs[~fp] = 0
        rho = U.surface_rho(cand, theirs, fp)
        rec.update({
            "disposition": "wrong_transform_measured_as_if_pixel_aligned",
            "spearman_full_footprint_asif": (rho["spearman_full_footprint"]
                                              if np.isfinite(rho["spearman_full_footprint"]) else None),
            "forward_overlap_3px_asif": U.dot_overlap(cand, theirs),
            "their_dots": int((theirs > 0).sum()),
            "representation": U.representation_class(int((theirs > 0).sum()), int(fp.sum()))["kind"],
        })
        out.append(rec)
    return out


def topk_mask(surface, allowed, k=K):
    """Top-k allowed surface cells (row-major tie-break) as a dot proxy."""
    key = np.where(allowed & (surface > 0), surface, -np.inf).astype(np.float32).ravel()
    part = np.argpartition(key, -k)[-k:]
    part = part[np.isfinite(key[part])]
    m = np.zeros(key.size, bool)
    m[part] = True
    return m.reshape(surface.shape)


if __name__ == "__main__":
    enforce_open_lane(ROOT, "G79B-SDPT")
