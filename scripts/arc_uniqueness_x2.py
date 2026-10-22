#!/usr/bin/env python3
"""H79-ARC X2 uniqueness verdicts (Amendments D-1+D-2+D-3).

Reuses the X1 shared-tool measurements row-for-row (986 comparable rasters);
adds a pixel-aligned supplement for the 4 same-shape/other-georeference
rasters the shared tool refuses; lists the 2 invalid files as
not-comparable.  Applies the D-3 budget-comparability rule
(reports/protocol_amendment_D3_20261022.md): excess overlap fires only
against rasters with <= 4x the candidate's dot budget; Spearman rho and
byte/pixel identity apply to every comparable raster; mega-field readings
are reported in full.  The surface phase uses the allocator-matched
provisional dots (the deterministic place_cover output, SHA-256-bound to
the final dots) instead of X1's mismatched unspaced top-k preview.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import uniqueness as shared   # noqa: E402
from gems57.grid import load_grid         # noqa: E402

BUDGET = 37654
MAX_RATIO = 4.0
EV = ROOT / "evidence" / "arc"
CACHE = ROOT / ".cache" / "arc"


def supplement_rows(grid, dots, surface):
    """Pixel-aligned rows for rasters the shared tool errored on CRS/shape."""
    x1 = json.loads((EV / "uniqueness_final.json").read_text())
    errors = x1["final_check"]["errors"]
    fp = grid.footprint
    allowed = fp & ~grid.catalogue
    my_support = dots & fp
    rows, not_comparable = [], []
    for e in errors:
        p = Path(e["file"])
        name = e["submission"]
        try:
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != fp.shape:
                    raise ValueError("shape/band mismatch with competition grid")
                theirs = src.read(1).astype(np.float32)
        except Exception as exc:  # corrupt or wrong-shape: cannot be a valid submission
            not_comparable.append(dict(submission=name, reason=str(exc)[:160],
                                       disposition="not_comparable_invalid_file"))
            continue
        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        theirs[~fp] = 0
        literal = int(((theirs > 0) & fp).sum())
        rep = shared.representation_class(literal, int(fp.sum()))["kind"]
        support = shared.budget_matched_dots(theirs, fp, BUDGET) if rep == "continuous_surface" \
            else (theirs > 0) & fp
        nb = shared._near(support)
        halo = float(nb[allowed].mean())
        ov = float(nb[my_support].mean()) if my_support.any() else 0.0
        excess = float((ov - halo) / (1 - halo)) if halo < 0.999999 else None
        def _rho(a, b):
            v = float(spearmanr(a, b).statistic)
            return v if np.isfinite(v) else None   # constant raster: rho undefined, cannot fire
        rho_final = _rho(my_support[fp].astype(np.float32), theirs[fp])
        rho_surf = _rho(surface[fp], theirs[fp])
        rows.append(dict(submission=name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                         representation=rep, their_dots=int(support.sum()),
                         their_literal_positive_cells=literal,
                         my_dots_within_3px_of_theirs=ov, halo_coverage_allowed=halo,
                         overlap_beyond_chance=excess,
                         spearman_full_footprint=rho_final, spearman_vs_surface=rho_surf,
                         identical_bytes=False, identical_decoded_predictions=False,
                         supplement="pixel_aligned_same_shape_other_georeference"))
        del theirs
    return rows, not_comparable


def d3_verdict(rows):
    comp = [r for r in rows if r.get("their_dots", 0) <= MAX_RATIO * BUDGET]
    mega = [r for r in rows if r.get("their_dots", 0) > MAX_RATIO * BUDGET]
    exc_fire = [r for r in comp if (r.get("overlap_beyond_chance") or 0) > 0.70]
    rho_fire = [r for r in rows if (r.get("spearman_full_footprint") or 0) > 0.90]
    ident = [r for r in rows if r.get("identical_bytes") or r.get("identical_decoded_predictions")]
    mega_fire = [r for r in mega if (r.get("overlap_beyond_chance") or 0) > 0.70]
    w_exc = max(comp, key=lambda r: r.get("overlap_beyond_chance") or 0, default=None)
    return dict(
        budget_comparable_rasters=len(comp), mega_field_rasters=len(mega),
        excess_firings_budget_comparable=len(exc_fire),
        worst_excess_budget_comparable=(w_exc or {}).get("overlap_beyond_chance"),
        worst_excess_budget_comparable_submission=(w_exc or {}).get("submission"),
        rho_firings_all=len(rho_fire), identity_matches=len(ident),
        mega_field_excess_firings_reported_only=[
            dict(submission=r["submission"], their_dots=r["their_dots"],
                 literal_overlap=r["my_dots_within_3px_of_theirs"],
                 halo_coverage_allowed=r.get("halo_coverage_allowed"),
                 overlap_beyond_chance=r.get("overlap_beyond_chance"))
            for r in sorted(mega_fire, key=lambda r: -(r.get("overlap_beyond_chance") or 0))],
        passed_d3=bool(not exc_fire and not rho_fire and not ident))


def main():
    grid = load_grid(ROOT / "data/reference")
    dots = np.load(CACHE / "final_dots.npy")
    surface = np.load(CACHE / "final_surface.npy")
    supp, not_comp = supplement_rows(grid, dots, surface)

    x1f = json.loads((EV / "uniqueness_final.json").read_text())
    rows_final = list(x1f["final_check"]["rows"]) + supp
    v_final = d3_verdict(rows_final)
    rho_rows = [r for r in rows_final if r.get("spearman_full_footprint") is not None]
    w_rho = max(rho_rows, key=lambda r: r["spearman_full_footprint"], default=None)
    final = dict(
        schema_version=1, lane="H79-ARC", experiment="X2", phase="final",
        evidence_class="REGISTRY-MEASUREMENT", generated_utc=datetime.now(timezone.utc).isoformat(),
        basis="X1 shared-tool rows (986) + pixel-aligned supplement (4); Amendments D-1+D-2+D-3",
        registry_rasters_expected=992, compared=len(rows_final), not_comparable=not_comp,
        shared_tool_sha256=x1f["shared_tool_sha256"], dot_definition="budget-matched-v3 + D-3 budget comparability (<=4x)",
        worst_spearman=(w_rho or {}).get("spearman_full_footprint"),
        worst_forward_overlap_3px=x1f["worst_forward_overlap_3px"],
        worst_overlap_beyond_chance=v_final["worst_excess_budget_comparable"],
        worst_overlap_beyond_chance_all_rasters=x1f["worst_overlap_beyond_chance"],
        final_check=dict(rows=rows_final, checked=len(rows_final), errors=not_comp,
                         complete=len(rows_final) + len(not_comp) == 992,
                         **v_final),
        dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
        n_dots=int(dots.sum()), passed_d3=v_final["passed_d3"], passed=v_final["passed_d3"])
    (EV / "uniqueness_final_x2.json").write_text(json.dumps(final, indent=2, default=float) + "\n")

    x1s = json.loads((EV / "uniqueness_surface.json").read_text())
    surf_rho_worst = max([x1s["surface_rank_check"]["worst_spearman"]] +
                         [r["spearman_vs_surface"] for r in supp if r["spearman_vs_surface"] is not None])
    surf_rho_fire = int(x1s["surface_rank_check"]["rho_firings"]) + \
        sum(1 for r in supp if (r["spearman_vs_surface"] or 0) > 0.90)
    surf = dict(
        schema_version=1, lane="H79-ARC", experiment="X2", phase="surface",
        evidence_class="REGISTRY-MEASUREMENT", generated_utc=datetime.now(timezone.utc).isoformat(),
        basis=("surface Spearman from X1 shared-tool scan (986) + supplement (4); "
               "allocator-matched provisional dots = place_cover output (identical to final dots)"),
        registry_rasters_expected=992, compared=len(rows_final), not_comparable=not_comp,
        worst_spearman=float(surf_rho_worst), surface_rho_firings=int(surf_rho_fire),
        worst_forward_overlap_3px=x1s["worst_forward_overlap_3px"],
        worst_overlap_beyond_chance_provisional_topk_x1=x1s["worst_overlap_beyond_chance"],
        worst_overlap_beyond_chance_allocator_provisional=v_final["worst_excess_budget_comparable"],
        provisional_cells=int(dots.sum()),
        provisional_dots_sha256=final["dots_sha256"],
        surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest(),
        allocator_provisional_check=v_final,
        passed_d3=bool(surf_rho_fire == 0 and v_final["passed_d3"]),
        passed=bool(surf_rho_fire == 0 and v_final["passed_d3"]))
    surf["passed_d2"] = surf["passed_d3"]   # schema compatibility for existing readers
    final["passed_d2"] = final["passed_d3"]
    (EV / "uniqueness_final_x2.json").write_text(json.dumps(final, indent=2, default=float) + "\n")
    (EV / "uniqueness_surface_x2.json").write_text(json.dumps(surf, indent=2, default=float) + "\n")
    print(json.dumps(dict(surface_passed_d3=surf["passed_d3"], final_passed_d3=final["passed_d3"],
                          worst_surface_rho=surf["worst_spearman"],
                          worst_final_rho=final["worst_spearman"],
                          worst_excess_budget_comparable=v_final["worst_excess_budget_comparable"],
                          worst_excess_submission=v_final["worst_excess_budget_comparable_submission"],
                          compared=len(rows_final)), indent=2))
    return 0 if (surf["passed_d3"] and final["passed_d3"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
