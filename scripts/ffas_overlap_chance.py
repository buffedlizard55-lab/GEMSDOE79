#!/usr/bin/env python3
"""REGISTRY-MEASUREMENT: 3 px overlap vs chance for the H79-FFAS final dots.

Same measurements as scripts/nhr_overlap_chance.py, against the FFAS artifact.
Does not decide uniqueness (that is scripts/ffas_uniqueness.py using the shared
tool). Records halo coverage so IR-79-53 / informative-halo-v4 is auditable.
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
from gems79.lifecycle import LaneClosedError, require_open_lane  # noqa: E402
from nhr_uniqueness import inventory, BUDGET   # noqa: E402


def main():
    require_open_lane(ROOT, "H79-FFAS")
    g = load_grid(ROOT / "data/reference")
    fp = g.footprint
    allowed = fp & ~g.catalogue
    dots = np.load(ROOT / ".cache/ffas/final_dots.npy") & fp
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
        except Exception as exc:
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
            tr = rankdata(tv); tr -= tr.mean()
            rho = float(np.dot(ranks, tr) / (norm * np.linalg.norm(tr))) if norm and np.linalg.norm(tr) else None
        def beyond(o, c):
            return None if c >= 1.0 else float((o - c) / (1.0 - c))
        rows.append(dict(
            submission=name, sha256=rec["sha256"], representation=kind,
            georeference_matches_sample=bool(georef_ok),
            their_dots=int(support.sum()), halo_coverage=cov,
            overlap_candidate=ov, overlap_uniform=ou,
            overlap_beyond_chance=beyond(ov, cov),
            overlap_beyond_chance_uniform=beyond(ou, cov),
            spearman=rho,
        ))
    flagged_c = [r for r in rows if r["overlap_candidate"] > 0.70]
    flagged_u = [r for r in rows if r["overlap_uniform"] > 0.70]
    space = [r for r in rows if r["halo_coverage"] > 0.70]
    informative = [r for r in rows if r["halo_coverage"] <= 0.70]
    worst_inf = max(informative, key=lambda r: r["overlap_candidate"]) if informative else None
    out = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        lane="H79-FFAS",
        shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
        dot_definition="budget-matched-v3", overlap_mode="informative-halo-v4",
        budget=BUDGET, uniform_control_seed=79,
        registry_rasters_expected=expected, compared=len(rows),
        not_comparable=not_comparable,
        rasters_where_candidate_overlap_gt_0_70=len(flagged_c),
        rasters_where_uniform_random_overlap_gt_0_70=len(flagged_u),
        space_filling_rasters_halo_gt_0_70=len(space),
        informative_rasters=len(informative),
        candidate_flagged_only_by_space_filling_rasters=bool(
            flagged_c and all(r["halo_coverage"] > 0.70 for r in flagged_c)),
        worst_candidate_overlap_vs_informative_rasters=worst_inf,
        rows=rows,
    )
    dest = ROOT / "evidence/ffas/overlap_chance.json"
    dest.write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(json.dumps({k: out[k] for k in (
        "compared", "rasters_where_candidate_overlap_gt_0_70",
        "space_filling_rasters_halo_gt_0_70",
        "candidate_flagged_only_by_space_filling_rasters")}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
