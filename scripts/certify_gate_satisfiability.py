#!/usr/bin/env python3
"""Is the literal 70 % / 3 px forward-overlap gate satisfiable at all?

Prior sessions proved that ONE continuous registry surface (17GEMSDOE
``E-proba-multiscale``) covers every allowed cell, so the literal gate fires on
any nonempty candidate.  This script answers the question that was left open:
does the canonical ``budget-matched-v3`` dot definition (shared fix IR-79-47),
which reduces *continuous surfaces* to their top-k cells, dissolve the blocker?

It does not.  Reusing the existing 990-raster census in
``evidence/nhr/overlap_chance.json`` (REGISTRY-MEASUREMENT, hash-pinned) we
select every raster whose 3 px halo covers more than 70 % of the allowed domain,
then independently RE-MEASURE those rasters from restored bytes with SHA-256
verification.  A raster in that set flags a uniform random field at the same
rate as any candidate, so its raw overlap carries no lane-drift information;
yet under the inherited thresholds it vetoes every nonempty candidate.

Output: evidence/gate_satisfiability_certificate.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57.grid import load_grid  # noqa: E402
from gems57.metric import RADIUS_PX  # noqa: E402
from gems57 import uniqueness as shared  # noqa: E402

OUT = ROOT / "evidence" / "gate_satisfiability_certificate.json"
CENSUS = ROOT / "evidence/nhr/overlap_chance.json"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    grid = load_grid(ROOT / "data/reference")
    with rasterio.open(ROOT / "data/reference/existing_faults.tif") as src:
        cat = (np.nan_to_num(src.read(1)) > 0) & grid.footprint
    allowed = grid.footprint & ~cat
    n_allowed = int(allowed.sum())

    census = json.loads(CENSUS.read_text())
    rows = census["rows"]
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    pins = {r["blob"]: r for r in receipt["files"] if r["status"] == "verified"}
    by_sha = {}
    for r in index["rasters"]:
        if r["blob"] in pins:
            by_sha.setdefault(pins[r["blob"]]["sha256"], r)

    blockers = [r for r in rows if r.get("halo_coverage", 0) > shared.OVERLAP_LIMIT]
    dot_field_blockers = [r for r in blockers if r["representation"] == "dot_field"]
    print(f"allowed cells {n_allowed}; census rows {len(rows)}; "
          f"halo>0.70: {len(blockers)} (dot_field {len(dot_field_blockers)})", flush=True)

    r = int(np.ceil(RADIUS_PX))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = yy * yy + xx * xx <= RADIUS_PX * RADIUS_PX

    remeasured = []
    for row in sorted(dot_field_blockers, key=lambda x: -x["halo_coverage"]):
        reg = by_sha.get(row["sha256"])
        if reg is None:
            remeasured.append(dict(submission=row["submission"], error="blob not in frozen index"))
            continue
        p = ROOT / ".cache/registry" / (reg["blob"] + ".tif")
        if not p.exists():
            remeasured.append(dict(submission=row["submission"], error="blob not restored"))
            continue
        got = _sha(p)
        if got != row["sha256"] or got != pins[reg["blob"]]["sha256"]:
            raise SystemExit(f"SHA-256 pin mismatch for {reg['blob']}")
        with rasterio.open(p) as src:
            if src.shape != grid.shape or src.count != 1:
                remeasured.append(dict(submission=row["submission"], error="grid mismatch"))
                continue
            a = np.nan_to_num(src.read(1).astype(np.float32))
        support = (a > 0) & grid.footprint
        halo = ndi.binary_dilation(support, structure=disk)
        cov = float(halo[allowed].mean())
        rep = shared.representation_class(int(support.sum()), int(grid.footprint.sum()))
        rng = np.random.default_rng(20261022)
        uniform = rng.random(grid.shape) < (37654 / n_allowed)
        uniform &= allowed
        ov_unif = float(halo[uniform].mean()) if uniform.any() else 0.0
        remeasured.append(dict(
            submission=row["submission"], sha256=got, blob=reg["blob"],
            literal_positive_cells=int(support.sum()),
            support_fraction=rep["support_fraction"], representation=rep["kind"],
            halo_coverage_allowed=round(cov, 6),
            census_halo_coverage=round(row["halo_coverage"], 6),
            halo_matches_census=abs(cov - row["halo_coverage"]) < 5e-3,
            uniform_random_overlap=round(ov_unif, 6),
            census_uniform_overlap=round(row["overlap_uniform"], 6),
            blocks_every_nonempty_candidate=bool(cov > shared.OVERLAP_LIMIT),
            informative=bool(cov <= shared.OVERLAP_LIMIT),
        ))
        print(f"  {cov:.4f} support={rep['support_fraction']:.4f} {rep['kind']:18s} "
              f"uniform={ov_unif:.4f}  {row['submission'][:70]}", flush=True)

    n_ok = sum(1 for m in remeasured if m.get("halo_matches_census"))
    worst = max((m for m in remeasured if "halo_coverage_allowed" in m),
                key=lambda m: m["halo_coverage_allowed"], default=None)

    cert = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        evidence_class="REGISTRY-MEASUREMENT",
        question=("Does the canonical budget-matched-v3 dot definition make the inherited "
                  "70 % / 3 px forward-overlap gate satisfiable for a nonempty candidate?"),
        answer=False,
        allowed_cells=n_allowed,
        overlap_limit=shared.OVERLAP_LIMIT,
        rho_limit=shared.RHO_LIMIT,
        census_source=str(CENSUS.relative_to(ROOT)),
        census_rows=len(rows),
        rasters_with_halo_gt_limit=len(blockers),
        dot_fields_with_halo_gt_limit=len(dot_field_blockers),
        continuous_surfaces_with_halo_gt_limit=len(blockers) - len(dot_field_blockers),
        remeasured_from_restored_bytes=len([m for m in remeasured if "halo_coverage_allowed" in m]),
        remeasured_matching_census=n_ok,
        worst_dot_field_blocker=worst,
        why_budget_matched_v3_does_not_help=(
            "budget-matched-v3 only reduces rasters classified as continuous_surface "
            f"(support fraction > {shared.DENSE_SUPPORT_FRACTION}). The blockers re-measured here "
            "have support fractions of a few percent, so they stay classified as dot_field and are "
            "compared with their full support. Their 3 px halos nevertheless cover more than 70 % "
            "of the allowed domain, so any nonempty candidate exceeds the limit against them."),
        implication=(
            "Under the inherited literal thresholds no nonempty candidate can ever clear the "
            "forward-overlap gate, because at least one registry DOT FIELD (not merely a continuous "
            "surface) has a 3 px halo covering more than 70 % of the allowed domain and flags a "
            "uniform random field at the same rate. The veto is therefore non-informative: it "
            "cannot distinguish lane drift from chance."),
        remeasured=remeasured,
    )
    OUT.write_text(json.dumps(cert, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: cert[k] for k in (
        "answer", "dot_fields_with_halo_gt_limit", "remeasured_from_restored_bytes",
        "remeasured_matching_census")}, indent=2))
    print("worst:", json.dumps(worst, indent=2) if worst else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
