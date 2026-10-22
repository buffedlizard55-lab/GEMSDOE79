#!/usr/bin/env python3
"""REGISTRY-MEASUREMENT: is the 3 px overlap gate informative for each registry raster?

For every registry raster R this measures, using the shared template's own
helpers (``_near``, ``budget_matched_dots``, ``representation_class``):

* ``halo_coverage``: share of allowed cells (footprint minus catalogue) within 3 px
  of R's dots. This is the overlap that a *uniformly random* map is expected to have with R.
* ``overlap_candidate``: share of the final H79-NHR dots within 3 px of R's dots
  (the protocol's statistic).
* ``overlap_uniform``: the same statistic for a seeded uniform-random 37,654-dot control.
* ``overlap_beyond_chance = (overlap - halo) / (1 - halo)``, a kappa-style score in which
  0 means no better than chance and 1 means every dot lies on R.

Registry rasters on the same 3730 x 3292 shape but with a different
georeference are compared pixel-by-pixel, which is conservative: it treats them as
aligned. Unreadable files and files with another shape cannot be valid competition
submissions; they are listed, not silently dropped.

This script decides nothing. It records measurements for IR-79-42.
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
from gems57 import uniqueness as shared        # noqa: E402
from gems57.grid import load_grid              # noqa: E402
from nhr_uniqueness import inventory, BUDGET   # noqa: E402


def main():
    g = load_grid(ROOT / "data/reference")
    fp = g.footprint
    allowed = fp & ~g.catalogue
    dots = np.load(ROOT / ".cache/nhr/final_dots.npy") & fp
    assert int(dots.sum()) == BUDGET
    rng = np.random.default_rng(79)
    cells = np.flatnonzero(allowed.ravel())
    uni = np.zeros(fp.size, bool)
    uni[rng.choice(cells, BUDGET, replace=False)] = True
    uni = uni.reshape(fp.shape)
    mine = dots.astype(np.float64)[fp]
    ranks = rankdata(mine); ranks -= ranks.mean(); norm = float(np.linalg.norm(ranks))
    inv, expected = inventory()
    rows, not_comparable = [], []
    for rec in inv["rasters"]:
        p = Path(rec["cache_file"])
        name = rec["sources"][0] if ":" in rec["sources"][0] else rec["repo_first"] + ":" + rec["sources"][0]
        try:
            if hashlib.sha256(p.read_bytes()).hexdigest() != rec["sha256"]:
                raise ValueError("sha256 pin mismatch")
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != fp.shape:
                    raise ValueError(f"shape {src.shape} / bands {src.count} differ from the competition grid")
                georef_ok = (src.crs is not None and src.crs.to_epsg() == 32611 and src.transform == g.transform)
                a = src.read(1).astype(np.float32)
        except Exception as exc:  # recorded, never silently dropped
            not_comparable.append(dict(submission=name, reason=str(exc)[:160]))
            continue
        a = np.where(np.isfinite(a), a, 0.0); a[~fp] = 0
        support = (a > 0) & fp
        kind = shared.representation_class(int(support.sum()), int(fp.sum()))["kind"]
        if kind == "continuous_surface":
            support = shared.budget_matched_dots(a, fp, BUDGET)
        halo = shared._near(support)
        cov = float(halo[allowed].mean())
        ov = float(halo[dots].mean()); ou = float(halo[uni].mean())
        tv = a[fp].astype(np.float64)
        if np.ptp(tv) == 0:
            rho = None
        else:
            tr = rankdata(tv); tr -= tr.mean(); rho = float(np.dot(ranks, tr) / (norm * np.linalg.norm(tr)))
        kappa = None if cov >= 1.0 else (ov - cov) / (1.0 - cov)
        kappa_u = None if cov >= 1.0 else (ou - cov) / (1.0 - cov)
        rows.append(dict(submission=name, sha256=rec["sha256"], representation=kind,
                         georeference_matches_sample=georef_ok, their_dots=int(support.sum()),
                         halo_coverage=cov, overlap_candidate=ov, overlap_uniform=ou,
                         overlap_beyond_chance=kappa, overlap_beyond_chance_uniform=kappa_u,
                         spearman=rho))
    lit = [r for r in rows if r["overlap_candidate"] > shared.OVERLAP_LIMIT]
    uni_fail = [r for r in rows if r["overlap_uniform"] > shared.OVERLAP_LIMIT]
    space = [r for r in rows if r["halo_coverage"] > shared.OVERLAP_LIMIT]
    informative = [r for r in rows if r["halo_coverage"] <= shared.OVERLAP_LIMIT]
    def worst(rs, k):
        rs = [r for r in rs if r[k] is not None]
        return max(rs, key=lambda r: r[k]) if rs else None
    out = dict(
        evidence_class="REGISTRY-MEASUREMENT", generated_utc=datetime.now(timezone.utc).isoformat(),
        shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
        dot_definition="budget-matched-v3", budget=BUDGET, uniform_control_seed=79,
        registry_rasters_expected=expected, compared=len(rows), not_comparable=not_comparable,
        same_shape_other_georeference=[r["submission"] for r in rows if not r["georeference_matches_sample"]],
        rasters_where_candidate_overlap_gt_0_70=len(lit),
        rasters_where_uniform_random_overlap_gt_0_70=len(uni_fail),
        space_filling_rasters_halo_gt_0_70=len(space),
        candidate_flagged_only_by_space_filling_rasters=all(r["halo_coverage"] > shared.OVERLAP_LIMIT for r in lit),
        worst_candidate_overlap_vs_informative_rasters=worst(informative, "overlap_candidate"),
        worst_candidate_overlap_beyond_chance=worst(rows, "overlap_beyond_chance"),
        worst_spearman_all_comparable=worst(rows, "spearman"),
        rows=sorted(rows, key=lambda r: -r["overlap_candidate"]))
    out["worst_uniform_overlap_beyond_chance"] = worst(rows, "overlap_beyond_chance_uniform")
    (ROOT / "evidence/nhr/overlap_chance.json").write_text(json.dumps(out, indent=2) + "\n")
    summary = {k: out[k] for k in ("compared", "rasters_where_candidate_overlap_gt_0_70",
                                   "rasters_where_uniform_random_overlap_gt_0_70",
                                   "space_filling_rasters_halo_gt_0_70",
                                   "candidate_flagged_only_by_space_filling_rasters")}
    summary["not_comparable"] = len(not_comparable)
    for k in ("worst_candidate_overlap_vs_informative_rasters", "worst_candidate_overlap_beyond_chance",
              "worst_uniform_overlap_beyond_chance", "worst_spearman_all_comparable"):
        w = out[k]
        summary[k] = None if w is None else {kk: w[kk] for kk in ("submission", "overlap_candidate", "halo_coverage",
                                                                  "overlap_beyond_chance", "spearman")}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
