#!/usr/bin/env python3
"""Protocol rule 1 for H79-COV: surface and final-dot duplicate gates.

Novelty mathematics is the shared template's
``gems57.uniqueness.compare_array_to_registry`` with
``dot_definition='budget-matched-v3'`` (IR-79-47). Thresholds unchanged:
Spearman > 0.90, or > 70% of my dots within 3 px of one registry raster's
dots => duplicate => stop.

The final phase additionally records, for every registry raster, its 3 px
halo coverage of the allowed domain and the exact-cell dot overlap, and
applies the preregistered Amendment-B1 discriminating classification
(registry/preregistration_g79cov_20261022.json; precedent
registry/preregistration_g79b_amendment_B1.json): priors whose halo covers
>= 0.70 of the allowed domain are non-discriminating for the halo test
(the literal test is unsatisfiable against them at this budget — B1
infeasibility proof) and are instead tested by exact-cell overlap <= 0.70.
Spearman <= 0.90 applies to every raster. Literal readings are published.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared        # noqa: E402
from gems57.grid import load_grid              # noqa: E402
from nhr_uniqueness import inventory, BUDGET   # noqa: E402

OUT = ROOT / "evidence" / "cov"
CACHE = ROOT / ".cache" / "cov"


def compact(res, keys):
    rows = [r for r in res["rows"] if "error" not in r]
    out = {}
    for k in keys:
        vals = [r for r in rows if r.get(k) is not None]
        w = max(vals, key=lambda r: r[k]) if vals else None
        out["worst_" + k] = None if w is None else dict(
            value=w[k], submission=w["submission"],
            representation=w.get("representation"), their_dots=w.get("their_dots"))
    out.update(checked=len(rows), errors=[r for r in res["rows"] if "error" in r],
               complete=res["complete_accessible_scan"])
    return out


def halo_exact_pass(grid, dots, inv):
    """Per-raster halo coverage + exact-cell overlap (shared helpers only)."""
    fp = grid.footprint
    allowed = fp & ~grid.catalogue
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
                a = src.read(1).astype(np.float32)
        except Exception as exc:
            not_comparable.append(dict(submission=name, sha256=rec["sha256"], reason=str(exc)[:160]))
            continue
        a = np.where(np.isfinite(a), a, 0.0); a[~fp] = 0
        support = (a > 0) & fp
        kind = shared.representation_class(int(support.sum()), int(fp.sum()))["kind"]
        if kind == "continuous_surface":
            support = shared.budget_matched_dots(a, fp, BUDGET)
        halo = shared._near(support)
        rows.append(dict(submission=name, sha256=rec["sha256"], representation=kind,
                         their_dots=int(support.sum()),
                         halo_coverage=float(halo[allowed].mean()),
                         overlap_candidate=float(halo[dots].mean()),
                         exact_overlap=float(support[dots].mean())))
        del a, support, halo
    return rows, not_comparable


def run(phase):
    grid = load_grid(ROOT / "data/reference")
    inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    result = dict(schema_version=1, lane="H79-COV", phase=phase,
                  evidence_class="REGISTRY-MEASUREMENT",
                  generated_utc=datetime.now(timezone.utc).isoformat(),
                  shared_tool="gems57.uniqueness.compare_array_to_registry",
                  shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
                  dot_definition="budget-matched-v3", rho_limit=shared.RHO_LIMIT,
                  overlap_limit=shared.OVERLAP_LIMIT, registry_rasters_expected=expected)
    if phase == "surface":
        surface = np.load(CACHE / "final_surface.npy")
        r_s = shared.compare_array_to_registry(surface, inv, grid.footprint, include_reverse=False,
                                               expected_grid=eg, dot_definition="budget-matched-v3")
        prov = shared.budget_matched_dots(surface, grid.footprint & ~grid.catalogue, BUDGET).astype(np.float32)
        r_p = shared.compare_array_to_registry(prov, inv, grid.footprint, include_reverse=False,
                                               expected_grid=eg, dot_definition="budget-matched-v3")
        s_c = compact(r_s, ("spearman_full_footprint",))
        p_c = compact(r_p, ("my_dots_within_3px_of_theirs", "spearman_full_footprint"))
        rho = s_c["worst_spearman_full_footprint"]["value"]
        ov = p_c["worst_my_dots_within_3px_of_theirs"]["value"]
        result.update(surface_rank_check=s_c, provisional_topk_check=p_c,
                      provisional_cells=int(prov.sum()),
                      surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest())
        complete = s_c["complete"] and p_c["complete"] and not s_c["errors"] and not p_c["errors"] \
            and s_c["checked"] == p_c["checked"] == expected
        duplicate = bool((rho is not None and rho > shared.RHO_LIMIT) or ov > shared.OVERLAP_LIMIT)
        result.update(worst_spearman=rho, worst_forward_overlap_3px=ov,
                      complete_comparison=complete, duplicate=duplicate,
                      passed=bool(complete and not duplicate),
                      note="Surface phase has no placed dots, so the B1 exact-cell test does not apply; a literal firing here is adjudicated on the final dots, never silently dropped.")
    else:
        dots_bool = np.load(CACHE / "final_dots.npy")
        dots = dots_bool.astype(np.float32)
        r_f = shared.compare_array_to_registry(dots, inv, grid.footprint, include_reverse=True,
                                               expected_grid=eg, dot_definition="budget-matched-v3")
        f_c = compact(r_f, ("my_dots_within_3px_of_theirs", "spearman_full_footprint", "jaccard_dot_sets"))
        rho = f_c["worst_spearman_full_footprint"]["value"]
        ov = f_c["worst_my_dots_within_3px_of_theirs"]["value"]
        he_rows, not_comparable = halo_exact_pass(grid, dots_bool & grid.footprint, inv)
        by_sha = {r["sha256"]: r for r in he_rows}
        merged = []
        for r in r_f["rows"]:
            if "error" in r:
                continue
            h = by_sha.get(r["sha256"], {})
            merged.append(dict(submission=r["submission"], sha256=r["sha256"],
                               representation=r["representation"], their_dots=r["their_dots"],
                               spearman=r["spearman_full_footprint"],
                               forward_overlap=r["my_dots_within_3px_of_theirs"],
                               halo_coverage=h.get("halo_coverage"),
                               exact_overlap=h.get("exact_overlap")))
        disc = [m for m in merged if m["halo_coverage"] is not None and m["halo_coverage"] < 0.70]
        nondisc = [m for m in merged if m["halo_coverage"] is not None and m["halo_coverage"] >= 0.70]
        worst_disc = max(disc, key=lambda m: m["forward_overlap"]) if disc else None
        worst_exact = max(nondisc, key=lambda m: (m["exact_overlap"] or 0)) if nondisc else None
        b1_firings = [m for m in disc if m["forward_overlap"] > shared.OVERLAP_LIMIT] + \
                     [m for m in nondisc if (m["exact_overlap"] or 0) > shared.OVERLAP_LIMIT]
        rho_firings = [m for m in merged if m["spearman"] is not None and m["spearman"] > shared.RHO_LIMIT]
        literal_firings = [m for m in merged if m["forward_overlap"] > shared.OVERLAP_LIMIT]
        complete = f_c["complete"] and not f_c["errors"] and f_c["checked"] == expected \
            and len(merged) + len(not_comparable) >= expected - len(f_c["errors"])
        duplicate_b1 = bool(b1_firings or rho_firings)
        result.update(final_check=f_c, my_dots=int(dots.sum()),
                      dots_sha256=hashlib.sha256(dots_bool.tobytes()).hexdigest(),
                      worst_spearman=rho, worst_forward_overlap_3px=ov,
                      complete_comparison=bool(complete),
                      amendment_B1=dict(
                          discriminating_rasters=len(disc), non_discriminating_rasters=len(nondisc),
                          worst_discriminating_forward_overlap=worst_disc,
                          worst_non_discriminating_exact_overlap=worst_exact,
                          b1_firings=b1_firings, rho_firings=rho_firings,
                          literal_firings_count=len(literal_firings),
                          literal_firings=sorted(literal_firings, key=lambda m: -m["forward_overlap"])[:30],
                          not_comparable=not_comparable),
                      top10_overlap=sorted(merged, key=lambda m: -m["forward_overlap"])[:10],
                      duplicate=duplicate_b1,
                      duplicate_literal_reading=bool(literal_firings or rho_firings),
                      passed=bool(complete and not duplicate_b1))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"uniqueness_{phase}.json"
    out.write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(json.dumps({k: result[k] for k in ("worst_spearman", "worst_forward_overlap_3px",
                                             "complete_comparison", "duplicate", "passed")
                      if k in result}, indent=2))
    if phase == "final":
        print(json.dumps(result["amendment_B1"], indent=2, default=float)[:3000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["surface", "final"])
    run(ap.parse_args().phase)
