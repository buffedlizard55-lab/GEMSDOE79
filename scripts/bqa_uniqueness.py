#!/usr/bin/env python3
"""Protocol rule 1 for H79-BQA: surface (pre-placement) and final-dot duplicate gates.

All novelty arithmetic is the shared ``gems57.uniqueness.compare_array_to_registry``
with ``dot_definition='chance-corrected-v4'`` (IR-79-111, recorded in-session as IR-79-68; registry/protocol_clarification_v4.json).
Thresholds unchanged: Spearman > 0.90 blocks; chance-corrected 3 px overlap
kappa = (O - C)/(1 - C) > 0.70 blocks; byte / decoded-pixel identity blocks.
The raw (v3) overlap reading is reported next to it for readers who reject IR-79-111.

Phases
------
surface  full-surface Spearman of the continuous pre-placement surface, plus the
         provisional dot set (top-quota cells of each distance band, no spacing).
final    Spearman and chance-corrected overlap of the placed dots.

The registry is compared in two worker processes (2 CPUs); rows are merged and
summarised by the shared ``summarize_registry_rows``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared        # noqa: E402
from gems57.grid import load_grid              # noqa: E402
from gems79 import bqa                         # noqa: E402
from nhr_uniqueness import inventory           # noqa: E402  (index + delta, hash-pinned)

CACHE = ROOT / ".cache/bqa"
OUT = ROOT / "evidence/bqa"
DEF = "chance-corrected-v4"
BUDGET = 37654
_G = {}


def _init(cand_path, include_reverse):
    grid = load_grid(ROOT / "data/reference")
    _G.update(grid=grid, mine=np.load(cand_path), rev=include_reverse,
              allowed=grid.footprint & ~grid.catalogue,
              eg=(grid.shape, grid.crs, grid.transform))


def _work(chunk):
    g = _G["grid"]
    res = shared.compare_array_to_registry(
        _G["mine"], {"rasters": chunk, "complete_accessible_scan": True, "errors": []},
        g.footprint, include_reverse=_G["rev"], expected_grid=_G["eg"],
        dot_definition=DEF, allowed=_G["allowed"])
    return res["rows"], res["my_dots"], res["candidate_decoded_sha256"], res["candidate_rank_variation"]


WORKERS = 2


def compare(candidate: np.ndarray, tag: str, include_reverse: bool):
    inv, expected = inventory()
    path = CACHE / f"_cand_{tag}.npy"
    np.save(path, candidate.astype(np.float32))
    recs = inv["rasters"]
    chunks = [recs[i::WORKERS] for i in range(WORKERS)]
    with mp.get_context("fork").Pool(WORKERS, initializer=_init, initargs=(path, include_reverse)) as pool:
        parts = pool.map(_work, chunks)
    rows = [r for p in parts for r in p[0]]
    summary = shared.summarize_registry_rows(
        rows, registry_rasters_expected=expected,
        complete_accessible_scan=inv["complete_accessible_scan"],
        source_errors=inv["errors"],
        candidate_meta=dict(my_file=None, my_dots=parts[0][1], candidate_decoded_sha256=parts[0][2],
                            candidate_rank_variation=parts[0][3]),
        scope="Indexed public owner-repository inventory (frozen index + git delta); not a complete organizer registry.")
    out = digest_rows(summary, expected)
    out.update(resolve_errors(candidate.astype(np.float32), summary["rows"], expected, out))
    path.unlink()
    return out


def resolve_errors(mine, rows, expected, digest):
    """Disposition of rows the shared tool could not compare on the reference grid.

    * same shape, different CRS/transform: compared PIXEL-ONLY with the shared
      helpers (conservative: a re-georeferenced copy of the same pixels must still
      be caught);
    * unreadable or off-grid shape: recorded as not a competition-grid raster
      (the organizer's validator would reject it, so it cannot be a submission).
    """
    import rasterio
    from scipy.stats import rankdata
    grid = load_grid(ROOT / "data/reference")
    fp = grid.footprint
    allowed = fp & ~grid.catalogue
    mine_dots = (mine > 0) & fp
    k = int(mine_dots.sum())
    ranks = rankdata(mine[fp]).astype(np.float64)
    ranks -= ranks.mean()
    pixel_only, dispositions = [], []
    for r in rows:
        if "error" not in r:
            continue
        f = Path(r["file"]) if Path(r["file"]).is_absolute() else ROOT / r["file"]
        try:
            with rasterio.open(f) as src:
                shape_ok = src.count == 1 and src.shape == fp.shape
                theirs = src.read(1).astype(np.float32) if shape_ok else None
        except Exception as exc:  # unreadable TIFF
            dispositions.append(dict(submission=r["submission"], reason=f"unreadable: {exc}"[:200]))
            continue
        if theirs is None:
            dispositions.append(dict(submission=r["submission"], reason="shape/band count differs from the competition grid"))
            continue
        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        theirs[~fp] = 0
        support = (theirs > 0) & fp
        if shared.representation_class(int(support.sum()), int(fp.sum()))["kind"] == "continuous_surface":
            support = shared.budget_matched_dots(theirs, fp, k)
        halo = shared._near(support)
        ov = float(halo[mine_dots].mean()) if k else 0.0
        cov = float(halo[allowed].mean())
        kap = shared.chance_corrected(ov, cov)
        tv = theirs[fp]
        rho = None
        if np.ptp(tv) and np.linalg.norm(ranks):
            tr = rankdata(tv).astype(np.float64); tr -= tr.mean()
            rho = float(np.dot(ranks, tr) / (np.linalg.norm(ranks) * np.linalg.norm(tr)))
        pixel_only.append(dict(submission=r["submission"], reason=r["error"], spearman_full_footprint=rho,
                               my_dots_within_3px_of_theirs=ov, their_halo_coverage_allowed=cov,
                               chance_corrected_overlap=kap,
                               duplicate=bool((rho is not None and rho > shared.RHO_LIMIT) or
                                              (kap is not None and kap > shared.OVERLAP_LIMIT))))
    resolved = digest["checked"] + len(pixel_only) + len(dispositions)
    return dict(pixel_only_rows=pixel_only, dispositions=dispositions,
                pixel_only_duplicates=sum(x["duplicate"] for x in pixel_only),
                complete_with_dispositions=bool(resolved == expected),
                worst_pixel_only_spearman=max((x["spearman_full_footprint"] for x in pixel_only
                                               if x["spearman_full_footprint"] is not None), default=None),
                worst_pixel_only_kappa=max((x["chance_corrected_overlap"] for x in pixel_only
                                            if x["chance_corrected_overlap"] is not None), default=None))


def digest_rows(summary, expected):
    rows = [r for r in summary["rows"] if "error" not in r]
    info = [r for r in rows if r.get("overlap_test_informative")]
    rho_rows = [r for r in rows if r.get("spearman_full_footprint") is not None]
    worst_k = max(info, key=lambda r: r["chance_corrected_overlap"], default=None)
    worst_raw = max(rows, key=lambda r: r["my_dots_within_3px_of_theirs"], default=None)
    worst_rho = max(rho_rows, key=lambda r: r["spearman_full_footprint"], default=None)

    def brief(r, *keys):
        return None if r is None else {k: r.get(k) for k in ("submission", "sha256", "representation",
                                                            "their_dots", *keys)}
    top = sorted(info, key=lambda r: -r["chance_corrected_overlap"])[:10]
    return dict(
        registry_rasters_expected=expected, checked=len(rows),
        errors=[{k: r.get(k) for k in ("submission", "error")} for r in summary["rows"] if "error" in r],
        complete=bool(summary["complete_accessible_scan"] and len(rows) == expected),
        my_dots=summary["my_dots"], candidate_decoded_sha256=summary["candidate_decoded_sha256"],
        worst_spearman=brief(worst_rho, "spearman_full_footprint"),
        worst_chance_corrected_overlap=brief(worst_k, "chance_corrected_overlap",
                                             "my_dots_within_3px_of_theirs", "their_halo_coverage_allowed"),
        worst_raw_overlap=brief(worst_raw, "my_dots_within_3px_of_theirs", "their_halo_coverage_allowed",
                                "chance_corrected_overlap"),
        non_discriminating_rasters=len(rows) - len(info),
        v4_overlap_firings=sum(bool(r["duplicate_by_overlap"]) for r in rows),
        raw_v3_overlap_firings=sum(r["my_dots_within_3px_of_theirs"] > shared.OVERLAP_LIMIT for r in rows),
        rho_firings=sum(bool(r["duplicate_by_rho"]) for r in rows),
        identical_bytes=sum(bool(r["identical_bytes"]) for r in rows),
        identical_decoded=sum(bool(r["identical_decoded_predictions"]) for r in rows),
        top10_chance_corrected=[brief(r, "chance_corrected_overlap", "my_dots_within_3px_of_theirs",
                                      "their_halo_coverage_allowed", "spearman_full_footprint") for r in top],
        shared_duplicate_count=summary["duplicate_count"], shared_unique=summary["unique"])


def provisional_dots(surface, band):
    """Top-quota cells per distance band (no spacing) -- the pre-placement dot preview."""
    out = np.zeros(surface.shape, bool)
    for b, q in enumerate(bqa.quotas(BUDGET)):
        idx = np.flatnonzero((band == b) & (surface > 0))
        if idx.size:
            take = idx[np.argsort(-surface.ravel()[idx], kind="stable")[:q]]
            out.ravel()[take] = True
    return out


def run(phase):
    base = dict(schema_version=1, lane="H79-BQA", phase=phase, evidence_class="REGISTRY-MEASUREMENT",
                generated_utc=datetime.now(timezone.utc).isoformat(),
                shared_tool="gems57.uniqueness.compare_array_to_registry",
                shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
                dot_definition=DEF, protocol_clarification="IR-79-111 (in-session IR-79-68)",
                rho_limit=shared.RHO_LIMIT, overlap_limit=shared.OVERLAP_LIMIT)
    x2 = phase.endswith("-x2")
    if x2:
        base.update(experiment="X2", amendment="A1")
    if phase in ("surface", "surface-x2"):
        surface = np.load(CACHE / ("x2_final_surface.npy" if x2 else "final_surface.npy"))
        s = compare(surface, "surface", False)
        if x2:   # X2 placement is global: preview = global top-k cells of the allowed domain
            grid = load_grid(ROOT / "data/reference")
            prov = shared.budget_matched_dots(surface, grid.footprint & ~grid.catalogue, BUDGET)
        else:
            prov = provisional_dots(surface, np.load(CACHE / "final_band.npy"))
        p = compare(prov.astype(np.float32), "prov", False)
        rho = max(x["worst_spearman"]["spearman_full_footprint"] for x in (s, p) if x["worst_spearman"])
        kap = p["worst_chance_corrected_overlap"]["chance_corrected_overlap"] if p["worst_chance_corrected_overlap"] else 0.0
        complete = s["complete_with_dispositions"] and p["complete_with_dispositions"]
        ident = (s["identical_bytes"] + s["identical_decoded"] + p["identical_bytes"] + p["identical_decoded"]
                 + s["pixel_only_duplicates"] + p["pixel_only_duplicates"])
        base.update(surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest(),
                    surface_rank_check=s, provisional_topk_check=p, provisional_cells=int(prov.sum()))
    else:
        dots = np.load(CACHE / ("x2_final_dots.npy" if x2 else "final_dots.npy"))
        f = compare(dots.astype(np.float32), "final", True)
        rho = f["worst_spearman"]["spearman_full_footprint"] if f["worst_spearman"] else None
        kap = f["worst_chance_corrected_overlap"]["chance_corrected_overlap"] if f["worst_chance_corrected_overlap"] else 0.0
        complete = f["complete_with_dispositions"]
        ident = f["identical_bytes"] + f["identical_decoded"] + f["pixel_only_duplicates"]
        base.update(dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(), final_check=f)
    duplicate = bool((rho is not None and rho > shared.RHO_LIMIT) or kap > shared.OVERLAP_LIMIT or ident)
    base.update(worst_spearman=rho, worst_chance_corrected_overlap=kap, complete_comparison=complete,
                duplicate=duplicate, passed=bool(complete and not duplicate))
    OUT.mkdir(parents=True, exist_ok=True)
    name = f"x2_uniqueness_{phase[:-3]}.json" if x2 else f"uniqueness_{phase}.json"
    (OUT / name).write_text(
        json.dumps(base, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n")
    print(json.dumps({k: base[k] for k in ("phase", "worst_spearman", "worst_chance_corrected_overlap",
                                            "complete_comparison", "duplicate", "passed")}, indent=2))
    return base


if __name__ == "__main__":
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "H79-BQA",
        reason="H79-BQA is closed (verdict=negative, duplicate surface; uniqueness receipts frozen).",
    )
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["surface", "final", "surface-x2", "final-x2"])
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    WORKERS = max(1, a.workers)
    run(a.phase)
