#!/usr/bin/env python3
"""G79-CJX novelty audit vs every candidate raster whose bytes are in this
repo, plus H33 and D2.8 restored from their pinned GEMSDOE68 registry paths.

Three readings, reported separately (registry/preregistration_cjx.json):
(i) literal positive-support overlap (inherited definition);
(ii) dot-field like-for-like forward overlap and |Spearman|;
(iii) shared amendment D-2 chance-corrected overlap (vendor/gems57/uniqueness.py).
Scope is the restored subset, NOT a full-registry census.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402
from gems57.uniqueness import chance_corrected_overlap, dot_overlap, representation_class  # noqa: E402

RAW = ROOT / "data" / "raw"
CACHE = ROOT / ".cache" / "cjx"
OUT = ROOT / "evidence" / "cjx"
EXCLUDE_NAMES = {"existing_faults.tif", "labels.tif", "sample_submission.tif"}


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_band(path: Path):
    with rasterio.open(path) as s:
        if s.count != 1 or (s.height, s.width) != (3730, 3292):
            return None
        return s.read(1).astype(np.float32)


def main():
    grid = load_grid(RAW)
    fp, cat = grid.footprint, grid.catalogue
    dcat = ndi.distance_transform_edt(~cat)
    allowed = fp & (dcat > 2)
    del dcat
    surface = np.load(CACHE / "CJXFULL.npy")
    final_dots = np.load(CACHE / "final_dots.npy")
    # surface stage: pre-spacing top-20000 cells inside the allowed domain
    vals = np.where(allowed, surface, -1.0).ravel()
    top = np.argpartition(-vals, 20_000)[:20_000]
    surface_dots = np.zeros(fp.shape, bool)
    surface_dots.ravel()[top] = True
    del vals, top
    # fixed Spearman sample
    rng = np.random.default_rng(79)
    fp_idx = np.flatnonzero(fp)
    sample_idx = fp_idx[rng.choice(fp_idx.size, size=200_000, replace=False)]
    surf_sample = surface.ravel()[sample_idx].astype(np.float64)
    dots_sample = final_dots.ravel()[sample_idx].astype(np.float64)

    candidates: list[Path] = []
    for base in (ROOT / "docs" / "downloads", ROOT / "archive", CACHE / "registry"):
        if base.exists():
            candidates += sorted(base.rglob("*.tif"))
    # Never compare the candidate against itself: exclude this lane's own
    # artifact directory (a self-comparison would report a meaningless 1.0).
    own_dir = (ROOT / "archive" / "g79_cjx").resolve()
    candidates = [p for p in candidates if own_dir not in p.resolve().parents]
    rows, seen = [], {}
    for path in candidates:
        if path.name in EXCLUDE_NAMES:
            continue
        digest = sha256_file(path)
        if digest in seen:
            continue
        arr = read_band(path)
        if arr is None:
            continue
        seen[digest] = path
        finite = np.isfinite(arr)
        theirs = finite & (arr > 0) & fp
        their_dots = int(theirs.sum())
        if their_dots == 0:
            continue
        rep = representation_class(their_dots, int(fp.sum()))
        dist = ndi.distance_transform_edt(~theirs)
        halo_cov = float((dist[allowed] <= 3).mean())
        fwd_final = float((dist[final_dots] <= 3).mean()) if final_dots.any() else 0.0
        fwd_surface = float((dist[surface_dots] <= 3).mean())
        exact_final = float(theirs[final_dots].mean()) if final_dots.any() else 0.0
        del dist
        their_sample = np.nan_to_num(arr.ravel()[sample_idx].astype(np.float64))
        rho_surface = float(spearmanr(surf_sample, their_sample).statistic)
        rho_dots = float(spearmanr(dots_sample, their_sample).statistic)
        del arr, finite, theirs, their_sample
        rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name
        rows.append({
            "path": ".cache/cjx/registry/" + path.name if "cjx/registry" in rel else rel,
            "sha256": digest,
            "their_dots": their_dots,
            "representation": rep["kind"],
            "halo_coverage_of_allowed": halo_cov,
            "surface_top20000_forward_overlap_3px": fwd_surface,
            "final_forward_overlap_3px": fwd_final,
            "final_exact_overlap": exact_final,
            "spearman_surface_sample200k": rho_surface,
            "spearman_finaldots_sample200k": rho_dots,
            "d2_chance_corrected_final": chance_corrected_overlap(fwd_final, halo_cov),
        })
        log(len(rows), Path(rel).name, rep["kind"], "fwd", round(fwd_final, 4),
            "rho_s", round(rho_surface, 4))
    # Cross-check the in-loop EDT overlap against the shared vendor function on H33.
    h33 = read_band(CACHE / "registry" / "h33.tif")
    h33_dots = np.isfinite(h33) & (h33 > 0) & fp
    vendor_fwd = dot_overlap(final_dots, h33_dots)
    mine_fwd = next(r["final_forward_overlap_3px"] for r in rows if r["path"].endswith("h33.tif"))
    vendor_check = {"vendor_dot_overlap_h33": vendor_fwd, "in_loop_edt_h33": mine_fwd,
                    "agree_abs_tol_1e-9": bool(abs(vendor_fwd - mine_fwd) <= 1e-9)}
    del h33, h33_dots
    log("vendor cross-check", vendor_check)

    def worst(key, subset):
        if not subset:
            return None
        r = max(subset, key=lambda x: (abs(x[key]) if "spearman" in key else (x[key] if x[key] is not None else -1)))
        return {"value": r[key], "path": r["path"]}

    dot_rows = [r for r in rows if r["representation"] == "dot_field"]
    d2_rows = [r for r in rows if r["d2_chance_corrected_final"] is not None]
    summary = {
        "evidence_class": "REGISTRY-MEASUREMENT (restored subset)",
        "scope": (
            f"{len(rows)} unique-by-sha256 candidate rasters whose bytes are present in this repo "
            "(docs/downloads + archive/**) plus H33 (sha256 c55bafc470054e8271dcb89347a17e07fefe50de"
            "6af6e6ba6c4b169ef7ab6fa9) and D2.8 (3e78737f0da8dd2ca66cc6caac0ce8eeefcd6715707f8d1bd30"
            "91845cd9bcc30) restored from GEMSDOE68 registry paths pinned in "
            "docs/evidence/h33_remeasurement.json. NOT the frozen 1108-raster inventory and NOT an "
            "organizer census; unfetched entries are a stated limitation."
        ),
        "my_final_dots": int(final_dots.sum()),
        "shared_tool_cross_check": vendor_check,
        "reading_i_literal_positive_support": {
            "worst_final_forward_overlap": worst("final_forward_overlap_3px", rows),
            "worst_surface_forward_overlap": worst("surface_top20000_forward_overlap_3px", rows),
            "note": "Known a priori to fail for every nonempty candidate in the full inventory "
                    "(preflight witness covers 100% of allowed cells); reported, never hidden.",
        },
        "reading_ii_dotfield_like_for_like": {
            "dot_field_rasters": len(dot_rows),
            "worst_final_forward_overlap": worst("final_forward_overlap_3px", dot_rows),
            "worst_surface_forward_overlap": worst("surface_top20000_forward_overlap_3px", dot_rows),
            "worst_abs_spearman_surface": worst("spearman_surface_sample200k", rows),
            "worst_abs_spearman_finaldots": worst("spearman_finaldots_sample200k", rows),
            "passes_on_restored_subset": bool(
                dot_rows
                and worst("final_forward_overlap_3px", dot_rows)["value"] <= 0.70
                and worst("surface_top20000_forward_overlap_3px", dot_rows)["value"] <= 0.70
                and abs(worst("spearman_surface_sample200k", rows)["value"]) <= 0.90
                and abs(worst("spearman_finaldots_sample200k", rows)["value"]) <= 0.90
            ),
        },
        "reading_iii_d2_chance_corrected": {
            "defined_rows": len(d2_rows),
            "worst": worst("d2_chance_corrected_final", d2_rows),
            "saturated_rows_halo_ge_0_999999": len(rows) - len(d2_rows),
        },
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "uniqueness_restored_subset.json").write_text(json.dumps(summary, indent=2) + "\n")
    log("done", json.dumps({k: summary[k] for k in summary if k != "rows"}, indent=1)[:1500])


if __name__ == "__main__":
    main()
