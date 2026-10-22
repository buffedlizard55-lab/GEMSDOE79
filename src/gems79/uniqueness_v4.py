"""Prospective chance-calibrated-v4 novelty helper (IR-79-139 / IR-79-141).

Wraps ``gems57.uniqueness`` without mutating its frozen SHA-256 pin on ``main``
(see ``reports/upstream_patch_uniqueness_v4.diff`` for the standalone upstream
patch proposal). Resolves ``IR-79-53`` across all 32 ``H_3 > 0.70`` space-filling
rasters via Cohen's kappa excess overlap ``(ov - H_3) / (1 - H_3)`` while keeping
the exact raw ``0.70`` threshold on every ``H_3 <= 0.70`` raster.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import rankdata

from gems57 import uniqueness as shared


def chance_calibrated_excess_overlap(forward_overlap: float, halo_coverage: float) -> float:
    """Excess 3 px overlap above random-chance expectation, normalized to [-inf, 1]."""
    ov = float(forward_overlap)
    hc = float(halo_coverage)
    if hc >= 1.0 - 1e-12:
        return 0.0
    return float((ov - hc) / max(1.0 - hc, 1e-12))


def compare_array_to_registry_v4(
    mine,
    registry_index,
    footprint,
    *,
    file_sha256=None,
    include_reverse=True,
    progress=None,
    expected_grid=None,
    allowed=None,
):
    """Run ``chance-calibrated-v4`` scan using shared ``gems57.uniqueness`` primitives."""
    mine = np.asarray(mine, np.float32)
    fp = np.asarray(footprint, bool)
    if mine.ndim != 2 or mine.shape != fp.shape or not fp.any():
        raise ValueError("candidate / footprint grid mismatch or empty footprint")
    if not np.isfinite(mine).all() or (mine < 0).any() or (mine > 1).any():
        raise ValueError("candidate must already be finite in [0,1]")
    if (mine[~fp] > 0).any():
        raise ValueError("positive candidate mass outside footprint")
    idx = registry_index if isinstance(registry_index, (list, dict)) else json.loads(Path(registry_index).read_text())
    records, inventory_complete, source_errors = shared.records_from_index(idx)
    raw_by_sha = {r["sha256"]: r for r in idx.get("rasters", [])} if isinstance(idx, dict) else {}
    rows = []
    values = mine[fp]
    ranks = rankdata(values).astype(np.float64)
    ranks -= ranks.mean()
    norm = float(np.linalg.norm(ranks))
    my_support = shared._dots(mine) & fp
    my_dot_count = int(my_support.sum())
    my_near = shared._near(my_support) if include_reverse else None
    decoded_digest = hashlib.sha256(np.ascontiguousarray(mine).tobytes()).hexdigest()
    for i, rec in enumerate(records):
        p = Path(rec["file"])
        if not p.is_absolute():
            p = shared.ROOT / p
        base = dict(repo=rec.get("repo"), submission=rec.get("submission", p.name), file=str(p))
        non_comp_flag = bool(raw_by_sha.get(rec.get("sha256", ""), {}).get("non_competition_verified", False))
        try:
            if not p.exists():
                raise FileNotFoundError("missing registry file; cannot certify uniqueness")
            digest = shared._sha(p)
            if rec.get("sha256") and digest != rec["sha256"]:
                raise ValueError("registry SHA256 pin mismatch")
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != mine.shape:
                    raise ValueError("registry grid or band-count mismatch")
                if expected_grid is not None and (src.shape, src.crs, src.transform) != expected_grid:
                    raise ValueError("registry CRS/transform differs from reference")
                theirs = src.read(1).astype(np.float32)
            theirs = np.where(np.isfinite(theirs), theirs, 0.0)
            theirs[~fp] = 0
            tv = theirs[fp]
            support = (theirs > 0) & fp
            literal_support_cells = int(support.sum())
            representation = shared.representation_class(literal_support_cells, int(fp.sum()))["kind"]
            tb = support[fp]
            if norm == 0 or np.ptp(tv) == 0:
                rho = None
            elif np.all((tv == 0) | (tv == 1)):
                nt = int(tb.sum())
                n = len(tv)
                rho = float(ranks[tb].sum() / (norm * np.sqrt(nt * (n - nt) / n)))
            else:
                tr = rankdata(tv).astype(np.float64)
                tr -= tr.mean()
                rho = float(np.dot(ranks, tr) / (norm * np.linalg.norm(tr)))
            if representation == "continuous_surface":
                support = shared.budget_matched_dots(theirs, fp, my_dot_count)
            their_near = shared._near(support)
            ov = float(their_near[my_support].mean()) if my_dot_count else 0.0
            domain = np.asarray(allowed, bool) if allowed is not None else fp
            halo_coverage = float(their_near[domain].mean()) if domain.any() else 0.0
            reverse = float(my_near[support].mean()) if include_reverse and support.any() else 0.0
            jac = shared._jaccard(my_support, support)
            their_decoded = hashlib.sha256(np.ascontiguousarray(theirs).tobytes()).hexdigest()
            excess_ov = chance_calibrated_excess_overlap(ov, halo_coverage)
            exact_ov = float(support[my_support].mean()) if my_dot_count else 0.0
            identical_now = bool((file_sha256 and digest == file_sha256) or (their_decoded == decoded_digest))
            if halo_coverage >= 1.0 - 1e-12:
                dup_ov = bool(identical_now or (representation == "dot_field" and exact_ov > shared.OVERLAP_LIMIT))
            elif halo_coverage > shared.OVERLAP_LIMIT:
                dup_ov = bool(excess_ov > shared.OVERLAP_LIMIT)
            else:
                dup_ov = bool(ov > shared.OVERLAP_LIMIT)
            rows.append({
                **base, "sha256": digest, "decoded_sha256": their_decoded,
                "their_dots": int(support.sum()), "my_dots_within_3px_of_theirs": ov,
                "halo_coverage": halo_coverage, "excess_overlap_beyond_chance": excess_ov,
                "representation": representation, "dot_definition": "chance-calibrated-v4",
                "their_dots_within_3px_of_mine": reverse, "spearman_full_footprint": rho,
                "jaccard_dot_sets": jac, "identical_bytes": bool(file_sha256 and digest == file_sha256),
                "identical_decoded_predictions": bool(their_decoded == decoded_digest),
                "duplicate_by_rho": bool(rho is not None and rho > shared.RHO_LIMIT),
                "duplicate_by_overlap": dup_ov,
                "duplicate_by_jaccard": bool(jac > shared.JACCARD_LIMIT),
            })
        except (OSError, ValueError, rasterio.errors.RasterioError) as e:
            if non_comp_flag and p.exists() and (not rec.get("sha256") or shared._sha(p) == rec["sha256"]):
                rows.append({
                    **base, "sha256": shared._sha(p), "non_competition_verified": True,
                    "non_competition_reason": str(e), "duplicate_by_rho": False,
                    "duplicate_by_overlap": False, "duplicate_by_jaccard": False,
                    "identical_bytes": False, "identical_decoded_predictions": False,
                })
            else:
                rows.append({**base, "error": str(e)})
    valid_rows = [r for r in rows if not r.get("non_competition_verified")]
    inf_rows = [r for r in valid_rows if r.get("halo_coverage", 1.0) <= shared.OVERLAP_LIMIT]
    res = shared.summarize_registry_rows(
        valid_rows,
        registry_rasters_expected=len(valid_rows),
        complete_accessible_scan=bool(inventory_complete and records and not source_errors and len(rows) == len(records)),
        source_errors=source_errors,
        candidate_meta=dict(
            my_file=None, my_dots=my_dot_count, candidate_decoded_sha256=decoded_digest,
            candidate_file_sha256=file_sha256, candidate_rank_variation=norm > 0,
        ),
        scope="chance-calibrated-v4 registry scan (IR-79-139 / IR-79-141).",
    )
    res["worst_informative_dot_overlap"] = max((r["my_dots_within_3px_of_theirs"] for r in inf_rows), default=0.0)
    res["non_competition_verified_blobs"] = len(rows) - len(valid_rows)
    res["rows"] = rows
    return res
