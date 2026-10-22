#!/usr/bin/env python3
"""Comprehensive post-snapshot cross-organization registry & sibling candidate audit.

Reads the 992 SHA-256-pinned frozen registry rasters plus all newly recovered
cross-ref / post-snapshot prediction rasters from `registry/registry_delta.json`
(1,199 immutable GeoTIFF blobs across all 92 non-self `GEMS*` owner repositories),
and writes machine-verifiable byte forensics to `evidence/post_snapshot_sibling_audit.json`.

Every Spearman correlation, literal 3-px forward overlap, and `budget-matched-v3`
3-px forward overlap (evaluated at each candidate's own exact emitted dot count) is
computed identically to unmodified `vendor/gems57/uniqueness.py` across ALL comparable
rasters in the 1,199-blob inventory and spot-verified directly against
`gems57.uniqueness.compare_array_to_registry`.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import warnings

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import uniqueness as shared  # noqa: E402
from gems57.gates import format_report  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.validate import validate as shared_validate  # noqa: E402


OFFSETS_3PX = tuple(
    (dr, dc)
    for dr in range(-3, 4)
    for dc in range(-3, 4)
    if dr * dr + dc * dc <= 9
)
DR_ARR = np.array([d[0] for d in OFFSETS_3PX], dtype=np.int32)
DC_ARR = np.array([d[1] for d in OFFSETS_3PX], dtype=np.int32)


def disk3_halo(mask: np.ndarray) -> np.ndarray:
    """Exact 3.0-pixel Euclidean dilation matching `distance_transform_edt(~mask) <= 3.0`."""
    h, w = mask.shape
    out = np.zeros((h, w), dtype=bool)
    for dr, dc in OFFSETS_3PX:
        r_src0 = max(0, -dr)
        r_src1 = h - max(0, dr)
        c_src0 = max(0, -dc)
        c_src1 = w - max(0, dc)
        out[r_src0 + dr:r_src1 + dr, c_src0 + dc:c_src1 + dc] |= mask[r_src0:r_src1, c_src0:c_src1]
    return out


def verify_exact_disk3_equivalence() -> dict:
    rng = np.random.default_rng(790306)
    probe = rng.random((96, 112)) < 0.015
    probe[0, 0] = True
    probe[-1, -1] = True
    edt_halo = ndi.distance_transform_edt(~probe) <= 3.0
    fast_halo = disk3_halo(probe)
    if not np.array_equal(edt_halo, fast_halo):
        raise AssertionError("disk3_halo differed from scipy distance_transform_edt <= 3.0")
    cand = rng.random((96, 112)) < 0.01
    ov_shared = shared.dot_overlap(cand, probe)
    ov_fast = float(fast_halo[cand].mean())
    if abs(ov_shared - ov_fast) > 1e-12:
        raise AssertionError(f"Overlap mismatch: {ov_shared} vs {ov_fast}")
    return {
        "n_offsets_in_3px_disk": len(OFFSETS_3PX),
        "matches_edt_le_3_exact": True,
        "matches_gems57_dot_overlap_exact": True,
    }


LOCAL_GEMS79_LANE_SPECS = {
    "H79-DILSTEP_active": {
        "path": "docs/downloads/gems79-h79-dilstep-research-37654dots-20261022T045200Z-7dd0d54b-DO-NOT-SUBMIT.tif",
        "archive_fallback": "archive/h79_dilstep_6444be2d/downloads/gems79-h79-dilstep-research-37654dots-20261022T045200Z-7dd0d54b-DO-NOT-SUBMIT.tif",
        "overlap_vs_13gemsdoe_r13_lattice_s5": 0.998486,
        "overlap_vs_gemsdoe3_coverage_v3_wide": 0.802013,
    },
    "H79-NHR_archived": {
        "path": "archive/h79_nhr/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif",
        "overlap_vs_13gemsdoe_r13_lattice_s5": 0.995485,
        "overlap_vs_gemsdoe3_coverage_v3_wide": 0.912971,
    },
    "G79-MAG_quarantined": {
        "path": "archive/g79_mag_730d5ee7/downloads/gems79-g79-mag-37654dots-20261022T060000Z-e48a9293.tif",
        "overlap_vs_13gemsdoe_r13_lattice_s5": 0.990864,
        "overlap_vs_gemsdoe3_coverage_v3_wide": 0.673766,
    },
    "G79-THVC_canonical": {
        "path": "docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif",
        "archive_fallback": "archive/g79_thvc_33e1f8ec/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif",
        "overlap_vs_13gemsdoe_r13_lattice_s5": 0.998461,
        "overlap_vs_gemsdoe3_coverage_v3_wide": 0.816516,
    },
    "H79-FNHR_archived": {
        "path": "archive/h79_fnhr_a57e2a7f/gems79-h79-fnhr-f3-37654dots-20261022T051800Z-fae5cf3a-DO-NOT-SUBMIT.tif",
        "overlap_vs_13gemsdoe_r13_lattice_s5": 0.995698,
        "overlap_vs_gemsdoe3_coverage_v3_wide": 0.838424,
    },
    "G79-ETP_v1_quarantined": {
        "path": "archive/g79_etp_incoming_45998a01/downloads/g79-etp-elastic-tip-28761dots-20261022T140921Z-e2203dcf-zeros.tif",
        "overlap_vs_g79_thvc_canonical": 0.815166,
    },
    "G79-ETP_v2_quarantined": {
        "path": "archive/g79_etp_incoming_45998a01/downloads/g79-etp-relay-ramp-34500dots-20261022T140951Z-ce6c5fca-zeros.tif",
        "overlap_vs_g79_thvc_canonical": 0.478087,
    },
    "G79-CFSKD_archived": {
        "path": "archive/g79_cfskd_bda00cff/g79-cfskd-exp3-20261022-bda00cff-zeros-DO-NOT-SUBMIT.tif",
        "overlap_vs_g79_thvc_canonical": 0.541934,
    },
}


def build_local_gems79_concurrent_lanes_audit(root: Path = ROOT, grid=None) -> dict:
    """Reproducibly build the local_gems79_concurrent_lanes_audit section (resolves IR-79-130)."""
    root = Path(root)
    if grid is None:
        ref_dir = root / "data/raw" if (root / "data/raw/sample_submission.tif").exists() else root / "data/reference"
        grid = load_grid(ref_dir)
    out = {}
    for key, spec in LOCAL_GEMS79_LANE_SPECS.items():
        rel_path = spec["path"]
        tif_path = root / rel_path
        if not tif_path.exists() and "archive_fallback" in spec:
            tif_path = root / spec["archive_fallback"]
        if not tif_path.exists():
            continue
        val = shared_validate(tif_path, footprint=grid.footprint, catalogue=grid.catalogue)
        entry = {
            "path": rel_path,
            "sha256": hashlib.sha256(tif_path.read_bytes()).hexdigest(),
            "emitted_positive_pixels": int(val["emitted_positive_pixels"]),
            "format_all_checks_passed": bool(val["all_checks_passed"]),
        }
        for k, v in spec.items():
            if k not in ("path", "archive_fallback"):
                entry[k] = v
        out[key] = entry
    return out


PROMPT_SIBLING_CANDIDATES = [
    {
        "repo": "GEMSDOE76",
        "needle": "gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros",
        "prompt_status": "unscored_prompt_entry",
        "reported_holdout": {
            "dti": None,
            "evaluator": "GEMSDOE76 repo card",
            "notes": "Listed with empty score colon (`:`) in user prompt.",
        },
    },
    {
        "repo": "GEMSDOE78",
        "needle": "gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros",
        "prompt_status": "unscored_prompt_entry",
        "reported_holdout": {
            "dti": 0.1771,
            "ci95": [0.1602, 0.1959],
            "seed": 20,
            "withheld_positives": 11321,
            "evaluator": "gems57-pooled-hide-v2",
            "repo_incumbent_beaten": False,
            "notes": (
                "Did not beat GEMSDOE78's own overall incumbent CTRL_A2 (0.1826 vs 0.1771); "
                "cleared its own sibling H78-A overlap gate by only 53 dots (0.6988 <= 0.7000) "
                "using a repo-local top-K/Jaccard exemption (IR-78-22-03)."
            ),
        },
    },
    {
        "repo": "GEMSDOE79",
        "needle": "gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT",
        "prompt_status": "unscored_blocked_research_only",
        "local_path": "archive/h79_nhr/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif",
        "reported_holdout": {
            "dti": 0.1431,
            "ci95": [0.1281, 0.1574],
            "seed": 20,
            "seed_30_dti": 0.1522,
            "seed_30_ci95": [0.1335, 0.1696],
            "withheld_positives": 11321,
            "evaluator": "gems57-pooled-hide-v2",
            "repo_incumbent_beaten": True,
            "notes": (
                "Beats fold-fair H33 control on both seeds (+0.0470 seed 20, +0.0533 seed 30), "
                "but collides > 0.70 with ordinary family dot fields (max 0.9130) as well as "
                "space-filling priors; stopped cleanly with verdict=negative, ok_to_submit=false."
            ),
        },
    },
    {
        "repo": "GEMSDOE80",
        "needle": "gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros",
        "prompt_status": "unscored_prompt_entry",
        "reported_holdout": {
            "dti": 0.2349,
            "ci95": [0.2207, 0.2483],
            "withheld_positives": 18313,
            "evaluator": "GEMSDOE80-evaluate_holdout.py-v2 (PRIVATE FORK — NOT COMPARABLE)",
            "repo_incumbent_beaten": True,
            "notes": (
                "Evaluated on a private Voronoi evaluator fork (`GEMSDOE80-evaluate_holdout.py-v2`, "
                "18,313 withheld positives across 957/3,199 segments) rather than shared "
                "`gems57-pooled-hide-v2`; checked uniqueness against only 20 local TIFs; "
                "mislabelled 92 historical prompt numbers as ORGANIZER-CONFIRMED without receipts; "
                "companion `-nan.tif` files remain in `docs/downloads/` and `docs/submissions/`."
            ),
        },
    },
    {
        "repo": "GEMSDOE81",
        "needle": "gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros",
        "prompt_status": "unscored_prompt_entry",
        "reported_holdout": {
            "dti": 0.2170,
            "ci95": [0.2086, 0.2248],
            "withheld_positives": 22641,
            "evaluator": "gems57-pooled-hide-v2 (pooled 2-draw)",
            "repo_incumbent_beaten": True,
            "notes": (
                "Pure catalogue-continuation ring surface (`CONT`, no geophysics); checked uniqueness "
                "against only 5 rasters (H33, D2.8, and 3 internal GEMSDOE81 files) instead of the "
                "full sibling registry; IR-81-06 explicitly warns continuation exploits whole-component split geometry."
            ),
        },
    },
    {
        "repo": "GEMSDOE82",
        "needle": "gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros",
        "prompt_status": "unscored_prompt_entry",
        "reported_holdout": {
            "dti": 0.12533,
            "ci95": [0.10580, 0.14557],
            "seed": 20,
            "withheld_positives": 11321,
            "evaluator": "gems57-pooled-hide-v2",
            "repo_incumbent_beaten": True,
            "notes": (
                "Lower Seed-20 shared HOLDOUT-DTI (0.1253) than stopped GEMSDOE79 H79-NHR (0.1431); "
                "exempted dense/lattice rasters silently (`uniqueness_audit_1026.json`), mislabelled "
                "92 prompt scores as ORGANIZER-CONFIRMED without receipts, and left two `-nan.tif` files in `docs/downloads/`."
            ),
        },
    },
    {
        "repo": "GEMSDOE83",
        "needle": "gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros",
        "prompt_status": "unscored_prompt_entry",
        "reported_holdout": {
            "dti": 0.206817,
            "ci95": [0.192711, 0.219822],
            "seed": 20,
            "seed_20_dti": 0.199862,
            "seed_30_dti": 0.213755,
            "withheld_positives": 22663,
            "evaluator": "gems57-pooled-hide-v2 (dual-seed)",
            "repo_incumbent_beaten": True,
            "notes": (
                "Scanned only 119 rasters (omitting >1,000 family blobs), enforced post-hoc placement "
                "`overlap_cap = 0.650` (yielding 0.649997 right at its cap), repeated the misattributed "
                "`GEMSDOE49 = 0.3195` claim, mislabelled prompt numbers as ORGANIZER-CONFIRMED, and left "
                "three `-nan.tif` files in `docs/downloads/`."
            ),
        },
    },
    {
        "repo": "GEMSDOE32",
        "needle": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
        "prompt_status": "historical_family_best_report_0.2778",
        "reported_holdout": {
            "dti": 0.0961,
            "ci95": [0.0837, 0.1086],
            "seed": 20,
            "seed_30_dti": 0.0989,
            "seed_30_ci95": [0.0842, 0.1120],
            "withheld_positives": 11321,
            "evaluator": "gems57-pooled-hide-v2 (fold-fair H33 control)",
            "repo_incumbent_beaten": None,
            "notes": "Highest user-reported family public DTI (0.2778 UNVERIFIED HISTORICAL REPORT; 37,654 binary dots).",
        },
    },
]


def load_all_registry_entries() -> tuple[list[dict], list[dict], list[dict]]:
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    receipt = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    delta = json.loads((ROOT / "registry/registry_delta.json").read_text())
    pins = {r["blob"]: r["sha256"] for r in receipt["files"] if r["status"] == "verified"}
    frozen_entries = []
    for r in index["rasters"]:
        aliases = r.get("aliases", [f"{r['repo']}:{r['path']}"])
        frozen_entries.append({
            "source_set": "frozen_snapshot",
            "repo": r["repo"],
            "path": r["path"],
            "submission": aliases[0],
            "aliases": aliases,
            "blob": r["blob"],
            "sha256": pins[r["blob"]],
            "size": r["size"],
            "file": ROOT / ".cache/registry" / f"{r['blob']}.tif",
        })
    delta_entries = []
    for r in delta["rasters"]:
        aliases = r.get("aliases", [f"{r['repo']}:{r['path']}"])
        delta_entries.append({
            "source_set": "post_snapshot_delta",
            "repo": r["repo"],
            "path": r["path"],
            "submission": aliases[0],
            "aliases": aliases,
            "blob": r["blob"],
            "sha256": r["sha256"],
            "size": r["size"],
            "file": ROOT / ".cache/registry" / f"{r['blob']}.tif",
        })
    return frozen_entries, delta_entries, frozen_entries + delta_entries


def inspect_single_raster(
    entry: dict,
    expected_shape: tuple[int, int],
    expected_crs: str,
    expected_transform,
    footprint: np.ndarray,
    n_fp: int,
    allowed: np.ndarray,
    n_allowed: int,
    cand_precomp: dict[str, dict],
) -> dict:
    path = entry["file"]
    base = {
        "source_set": entry["source_set"],
        "repo": entry["repo"],
        "submission": entry["submission"],
        "blob": entry["blob"],
        "sha256": entry["sha256"],
        "size": entry["size"],
    }
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with rasterio.open(path) as ds:
                crs_str = str(ds.crs) if ds.crs else ""
                if ds.count != 1 or ds.shape != expected_shape or crs_str != expected_crs or ds.transform != expected_transform:
                    return {
                        **base,
                        "comparable": False,
                        "non_comparable_reason": f"grid_mismatch(count={ds.count},shape={ds.shape},crs={crs_str})",
                    }
                arr = ds.read(1).astype(np.float32, copy=False)
    except Exception as exc:
        return {**base, "comparable": False, "non_comparable_reason": f"unreadable({type(exc).__name__})"}

    n_nan_total = int(np.isnan(arr).sum())
    n_nan_in_fp = int(np.isnan(arr[footprint]).sum())
    n_inf_total = int(np.isinf(arr).sum())
    finite = np.isfinite(arr)
    min_val = float(arr[finite].min()) if finite.any() else None
    max_val = float(arr[finite].max()) if finite.any() else None
    out_of_range = bool(
        n_nan_total > 0 or n_inf_total > 0 or (min_val is not None and (min_val < 0.0 or max_val > 1.0))
    )

    theirs = np.where(finite, arr, 0.0)
    theirs = np.where(footprint, theirs, 0.0)
    tv = theirs[footprint]
    lit_dots = theirs > 0.0
    lit_n = int(lit_dots.sum())
    rep = shared.representation_class(lit_n, n_fp)["kind"]

    lit_halo = disk3_halo(lit_dots)
    lit_cov_cells = int((lit_halo & allowed).sum())
    lit_cov = float(lit_cov_cells / n_allowed)

    if rep == "continuous_surface":
        bm37_dots = shared.budget_matched_dots(theirs, footprint, 37654)
        bm37_n = int(bm37_dots.sum())
        bm37_halo = disk3_halo(bm37_dots)
        bm37_cov_cells = int((bm37_halo & allowed).sum())
        bm37_cov = float(bm37_cov_cells / n_allowed)
    else:
        bm37_dots = lit_dots
        bm37_halo = lit_halo
        bm37_n = lit_n
        bm37_cov_cells = lit_cov_cells
        bm37_cov = lit_cov

    # Exact full-footprint Spearman rank correlation matching `gems57.uniqueness.compare_array_to_registry`
    spearmans = {}
    tb = lit_dots[footprint]
    is_const = bool(np.ptp(tv) == 0)
    is_binary = (not is_const) and bool(np.all((tv == 0.0) | (tv == 1.0)))
    if is_const:
        for cid in cand_precomp:
            spearmans[cid] = None
    elif is_binary:
        nt = int(tb.sum())
        denom_t = float(np.sqrt(nt * (n_fp - nt) / n_fp))
        for cid, info in cand_precomp.items():
            spearmans[cid] = float(info["ranks"][tb].sum() / (info["norm"] * denom_t))
    else:
        tr = rankdata(tv).astype(np.float64)
        tr -= tr.mean()
        norm_tr = float(np.linalg.norm(tr))
        for cid, info in cand_precomp.items():
            spearmans[cid] = float(np.dot(info["ranks"], tr) / (info["norm"] * norm_tr))

    bm_by_k: dict[int, tuple[np.ndarray, float]] = {37654: (bm37_halo, bm37_cov)}
    overlaps_lit = {}
    overlaps_bm = {}
    halo_cov_bm_by_cand = {}
    for cid, info in cand_precomp.items():
        rs, cs = info["rs"], info["cs"]
        overlaps_lit[cid] = float(lit_halo[rs, cs].mean())
        ck = info["k"]
        if rep == "continuous_surface":
            if ck not in bm_by_k:
                bmk = shared.budget_matched_dots(theirs, footprint, ck)
                bmk_halo = disk3_halo(bmk)
                bmk_cov = float(int((bmk_halo & allowed).sum()) / n_allowed)
                bm_by_k[ck] = (bmk_halo, bmk_cov)
            bmk_halo, bmk_cov = bm_by_k[ck]
            overlaps_bm[cid] = float(bmk_halo[rs, cs].mean())
            halo_cov_bm_by_cand[cid] = bmk_cov
        else:
            overlaps_bm[cid] = overlaps_lit[cid]
            halo_cov_bm_by_cand[cid] = lit_cov

    return {
        **base,
        "comparable": True,
        "n_nan_total": n_nan_total,
        "n_nan_in_footprint": n_nan_in_fp,
        "n_inf_total": n_inf_total,
        "min_finite": min_val,
        "max_finite": max_val,
        "fails_portal_0_1_or_nan_check": out_of_range,
        "representation": rep,
        "literal_dots": lit_n,
        "literal_halo_allowed_cells": lit_cov_cells,
        "literal_halo_coverage": lit_cov,
        "literal_uncovered_allowed_cells": n_allowed - lit_cov_cells,
        "bm37654_dots": bm37_n,
        "bm37654_halo_allowed_cells": bm37_cov_cells,
        "bm37654_halo_coverage": bm37_cov,
        "bm37654_uncovered_allowed_cells": n_allowed - bm37_cov_cells,
        "spearman_full_footprint": spearmans,
        "overlaps_literal": overlaps_lit,
        "overlaps_bm": overlaps_bm,
        "halo_coverage_bm": halo_cov_bm_by_cand,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    equivalence = verify_exact_disk3_equivalence()
    grid = load_grid(ROOT / "data/reference")
    footprint = grid.footprint
    n_fp = int(footprint.sum())
    catalogue = grid.catalogue
    allowed = footprint & (~catalogue)
    n_allowed = int(allowed.sum())
    d_cat = ndi.distance_transform_edt(~catalogue)
    H, W = grid.shape
    mid_r, mid_c = H // 2, W // 2

    frozen_entries, delta_entries, all_entries = load_all_registry_entries()

    cand_arrays: dict[str, np.ndarray] = {}
    cand_meta: dict[str, dict] = {}
    cand_precomp: dict[str, dict] = {}

    for spec in PROMPT_SIBLING_CANDIDATES:
        cid = f"{spec['repo']}:{spec['needle']}"
        if spec.get("local_path"):
            tif_path = ROOT / spec["local_path"]
            data = tif_path.read_bytes()
            sha256 = hashlib.sha256(data).hexdigest()
            blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            matched_path = spec["local_path"]
        else:
            hits = [
                e for e in all_entries
                if e["repo"] == spec["repo"]
                and any(spec["needle"].lower() in a.lower() for a in e["aliases"])
            ]
            if not hits:
                hits = [
                    e for e in all_entries
                    if any(spec["needle"].lower() in a.lower() for a in e["aliases"])
                ]
            if not hits:
                raise FileNotFoundError(f"Could not find {cid} in 1,199-raster family inventory")
            hit = hits[0]
            tif_path = hit["file"]
            data = tif_path.read_bytes()
            sha256 = hit["sha256"]
            blob = hit["blob"]
            matched_path = hit["path"]

        val = shared_validate(tif_path, footprint, catalogue)
        fmt = format_report(tif_path, ROOT / "data/reference/sample_submission.tif", footprint=footprint)
        with rasterio.open(tif_path) as ds:
            arr = ds.read(1).astype(np.float32)
        pos = np.isfinite(arr) & (arr > 0.0) & footprint
        rs, cs = np.nonzero(pos)
        vals_fp = arr[footprint]
        ranks = rankdata(vals_fp).astype(np.float64)
        ranks -= ranks.mean()
        norm = float(np.linalg.norm(ranks))

        n_pos = int(pos.sum())
        cand_arrays[cid] = arr
        cand_precomp[cid] = {
            "k": n_pos,
            "rs": rs,
            "cs": cs,
            "ranks": ranks,
            "norm": norm,
        }

        dvals = d_cat[pos]
        q_nw = int(pos[:mid_r, :mid_c].sum())
        q_ne = int(pos[:mid_r, mid_c:].sum())
        q_sw = int(pos[mid_r:, :mid_c].sum())
        q_se = int(pos[mid_r:, mid_c:].sum())
        cand_meta[cid] = {
            "repo": spec["repo"],
            "candidate_name": spec["needle"],
            "matched_path": matched_path,
            "blob": blob,
            "sha256": sha256,
            "bytes": len(data),
            "prompt_status": spec["prompt_status"],
            "reported_holdout": spec["reported_holdout"],
            "format_validation": {
                "all_checks_passed": bool(val["all_checks_passed"] and fmt["ok"]),
                "in_unit_interval_everywhere": bool(
                    val["checks"]["range_0_1_guaranteed"]
                    and val["checks"]["no_nan_anywhere"]
                    and val["checks"]["no_inf_anywhere"]
                ),
                "n_nan": int(val["n_nan"]),
                "n_infinite": int(val["n_infinite"]),
                "min": float(val["min"]),
                "max": float(val["max"]),
                "emitted_positive_pixels": n_pos,
                "on_catalogue_pixels": int((pos & catalogue).sum()),
            },
            "spatial_forensics": {
                "min_distance_to_catalogue_px": round(float(dvals.min()), 4),
                "median_distance_to_catalogue_px": round(float(np.median(dvals)), 4),
                "p90_distance_to_catalogue_px": round(float(np.quantile(dvals, 0.90)), 4),
                "dots_within_200m_of_catalogue": int((dvals <= 2.0).sum()),
                "dots_200m_to_500m_of_catalogue": int(((dvals > 2.0) & (dvals <= 5.0)).sum()),
                "fraction_over_1km_from_catalogue": round(float((dvals > 10.0).mean()), 6),
                "quadrant_dots": {"NW": q_nw, "NE": q_ne, "SW": q_sw, "SE": q_se},
                "quadrant_shares": {
                    "NW": round(q_nw / n_pos, 4),
                    "NE": round(q_ne / n_pos, 4),
                    "SW": round(q_sw / n_pos, 4),
                    "SE": round(q_se / n_pos, 4),
                },
            },
        }

    nhr_cid = "GEMSDOE79:gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT"
    expected_crs = str(grid.crs)

    with cf.ThreadPoolExecutor(6) as pool:
        inspected = list(pool.map(
            lambda e: inspect_single_raster(
                e, grid.shape, expected_crs, grid.transform,
                footprint, n_fp, allowed, n_allowed, cand_precomp,
            ),
            all_entries,
        ))

    comp = [r for r in inspected if r["comparable"]]
    non_comp = [r for r in inspected if not r["comparable"]]
    comp_frozen = [r for r in comp if r["source_set"] == "frozen_snapshot"]
    comp_delta = [r for r in comp if r["source_set"] == "post_snapshot_delta"]

    # Direct exact cross-verification against unmodified `shared.compare_array_to_registry` on 3 diverse priors
    probe_entries = [all_entries[0], all_entries[len(all_entries) // 2], delta_entries[0]]
    shared_records = [
        {"repo": p["repo"], "submission": p["submission"], "file": str(p["file"]), "sha256": p["sha256"]}
        for p in probe_entries
    ]
    direct_bm = shared.compare_array_to_registry(
        cand_arrays[nhr_cid],
        shared_records,
        footprint,
        file_sha256=cand_meta[nhr_cid]["sha256"],
        include_reverse=False,
        expected_grid=(grid.shape, grid.crs, grid.transform),
        dot_definition="budget-matched-v3",
    )
    by_blob = {r["blob"]: r for r in comp}
    for pr, drow in zip(probe_entries, direct_bm["rows"]):
        fast_row = by_blob[pr["blob"]]
        if abs(fast_row["overlaps_bm"][nhr_cid] - drow["my_dots_within_3px_of_theirs"]) > 1e-12:
            raise AssertionError("Mismatch against shared.compare_array_to_registry overlap")
        if drow["spearman_full_footprint"] is not None:
            if abs(fast_row["spearman_full_footprint"][nhr_cid] - drow["spearman_full_footprint"]) > 1e-12:
                raise AssertionError("Mismatch against shared.compare_array_to_registry spearman")

    # Pigeonhole witnesses
    pigeonhole_witnesses_literal = sorted(
        comp, key=lambda r: (r["literal_uncovered_allowed_cells"], -r["literal_dots"])
    )[:8]
    pigeonhole_witnesses_bm = sorted(
        comp, key=lambda r: (r["bm37654_uncovered_allowed_cells"], -r["bm37654_dots"])
    )[:8]
    binary_dot_witnesses = sorted(
        [r for r in comp if r["representation"] == "dot_field" and r["bm37654_halo_coverage"] > 0.70],
        key=lambda r: r["bm37654_uncovered_allowed_cells"],
    )

    def pigeonhole_summary(row: dict, mode_prefix: str) -> dict:
        uncov = int(row[f"{mode_prefix}_uncovered_allowed_cells"])
        halo_cells = int(row[f"{mode_prefix}_halo_allowed_cells"])
        min_k_always_gt_070 = int(np.floor(uncov / 0.30)) + 1
        return {
            "repo": row["repo"],
            "submission": row["submission"],
            "blob": row["blob"],
            "sha256": row["sha256"],
            "source_set": row["source_set"],
            "dots": int(row[f"{mode_prefix}_dots"]),
            "representation": row["representation"],
            "halo_allowed_cells": halo_cells,
            "uncovered_allowed_cells": uncov,
            "halo_coverage": round(float(row[f"{mode_prefix}_halo_coverage"]), 8),
            "min_dot_budget_forced_gt_0_70_for_every_map": min_k_always_gt_070,
            "guaranteed_min_overlap_at_37654_dots": round(max(0.0, 1.0 - uncov / 37654.0), 6),
            "guaranteed_min_overlap_at_44090_dots": round(max(0.0, 1.0 - uncov / 44090.0), 6),
        }

    top_binary_witness = pigeonhole_summary(binary_dot_witnesses[0], "bm37654")

    # Exact full-1,199-raster uniqueness summary for every prompt candidate
    candidate_audits = []
    for cid, meta in cand_meta.items():
        self_sha = meta["sha256"]
        self_repo = meta["repo"]
        others_all = [r for r in comp if r["sha256"] != self_sha]
        others_cross_repo = [r for r in others_all if r["repo"] != self_repo]

        def summarize_scope(rows_scope: list[dict]) -> dict:
            lit_gt = [r for r in rows_scope if r["overlaps_literal"][cid] > 0.70]
            bm_gt = [r for r in rows_scope if r["overlaps_bm"][cid] > 0.70]
            inf_rows = [r for r in rows_scope if r["halo_coverage_bm"][cid] <= 0.70]
            inf_gt = [r for r in inf_rows if r["overlaps_bm"][cid] > 0.70]
            worst_inf = max(inf_rows, key=lambda r: r["overlaps_bm"][cid])
            sparse_rows = [
                r for r in rows_scope
                if r["representation"] == "dot_field" and 0 < r["literal_dots"] <= 60000
            ]
            sparse_gt = [r for r in sparse_rows if r["overlaps_literal"][cid] > 0.70]
            worst_sparse = max(sparse_rows, key=lambda r: r["overlaps_literal"][cid])
            rho_rows = [r for r in rows_scope if r["spearman_full_footprint"][cid] is not None]
            worst_pos_rho = max(rho_rows, key=lambda r: r["spearman_full_footprint"][cid])
            worst_abs_rho = max(rho_rows, key=lambda r: abs(r["spearman_full_footprint"][cid]))
            non_trivial_halo = [r for r in rows_scope if r["halo_coverage_bm"][cid] < 0.999999]
            worst_excess = max(
                non_trivial_halo,
                key=lambda r: (r["overlaps_bm"][cid] - r["halo_coverage_bm"][cid]) / (1.0 - r["halo_coverage_bm"][cid]),
            )
            excess_val = (
                (worst_excess["overlaps_bm"][cid] - worst_excess["halo_coverage_bm"][cid])
                / (1.0 - worst_excess["halo_coverage_bm"][cid])
            )
            return {
                "n_rasters_compared": len(rows_scope),
                "literal_rasters_gt_0_70": len(lit_gt),
                "budget_matched_v3_rasters_gt_0_70": len(bm_gt),
                "informative_non_space_filling_rasters_gt_0_70": len(inf_gt),
                "passes_non_space_filling_0_70_gate": len(inf_gt) == 0,
                "sparse_le_60k_dot_rasters_compared": len(sparse_rows),
                "sparse_le_60k_dot_rasters_gt_0_70": len(sparse_gt),
                "passes_sparse_le_60k_0_70_gate": len(sparse_gt) == 0,
                "worst_sparse_le_60k_match": {
                    "repo": worst_sparse["repo"],
                    "submission": worst_sparse["submission"],
                    "source_set": worst_sparse["source_set"],
                    "dots": worst_sparse["literal_dots"],
                    "overlap_3px": round(worst_sparse["overlaps_literal"][cid], 6),
                    "chance_halo_coverage": round(worst_sparse["literal_halo_coverage"], 6),
                },
                "passes_spearman_0_90_gate": float(worst_pos_rho["spearman_full_footprint"][cid]) <= 0.90,
                "worst_spearman_full_footprint": {
                    "repo": worst_pos_rho["repo"],
                    "submission": worst_pos_rho["submission"],
                    "rho": round(float(worst_pos_rho["spearman_full_footprint"][cid]), 6),
                    "max_abs_rho": round(abs(float(worst_abs_rho["spearman_full_footprint"][cid])), 6),
                    "max_abs_rho_submission": worst_abs_rho["submission"],
                },
                "worst_informative_match": {
                    "repo": worst_inf["repo"],
                    "submission": worst_inf["submission"],
                    "source_set": worst_inf["source_set"],
                    "sha256": worst_inf["sha256"],
                    "overlap_3px": round(worst_inf["overlaps_bm"][cid], 6),
                    "chance_halo_coverage": round(worst_inf["halo_coverage_bm"][cid], 6),
                },
                "top_5_informative_matches": [
                    {
                        "repo": r["repo"],
                        "submission": r["submission"],
                        "source_set": r["source_set"],
                        "overlap_3px": round(r["overlaps_bm"][cid], 6),
                        "chance_halo_coverage": round(r["halo_coverage_bm"][cid], 6),
                    }
                    for r in sorted(inf_rows, key=lambda x: x["overlaps_bm"][cid], reverse=True)[:5]
                ],
                "worst_excess_over_chance_match": {
                    "repo": worst_excess["repo"],
                    "submission": worst_excess["submission"],
                    "overlap_3px": round(worst_excess["overlaps_bm"][cid], 6),
                    "chance_halo_coverage": round(worst_excess["halo_coverage_bm"][cid], 6),
                    "excess_overlap_ratio": round(float(excess_val), 6),
                },
            }

        candidate_audits.append({
            **meta,
            "uniqueness_all_other_family_blobs": summarize_scope(others_all),
            "uniqueness_cross_repo_priors_only": summarize_scope(others_cross_repo),
        })

    # Exact pairwise forward 3-px overlap matrix among all 8 audited candidates
    pairwise_candidates = {}
    for cid_a in cand_meta:
        pairwise_candidates[cid_a] = {}
        for cid_b in cand_meta:
            if cid_a == cid_b:
                pairwise_candidates[cid_a][cid_b] = 1.0
            else:
                ov = shared.dot_overlap(cand_arrays[cid_a] > 0, cand_arrays[cid_b] > 0)
                pairwise_candidates[cid_a][cid_b] = round(float(ov), 6)

    delta_inf_gt_nhr = [
        r for r in comp_delta
        if r["halo_coverage_bm"][nhr_cid] <= 0.70 and r["overlaps_bm"][nhr_cid] > 0.70
    ]
    delta_sf_gt_nhr = [
        r for r in comp_delta
        if r["halo_coverage_bm"][nhr_cid] > 0.70 and r["overlaps_bm"][nhr_cid] > 0.70
    ]
    delta_nan_files = [
        {
            "repo": r["repo"],
            "submission": r["submission"],
            "blob": r["blob"],
            "sha256": r["sha256"],
            "n_nan_total": r["n_nan_total"],
            "n_nan_in_footprint": r["n_nan_in_footprint"],
            "min_finite": r["min_finite"],
            "max_finite": r["max_finite"],
        }
        for r in comp_delta
        if r["fails_portal_0_1_or_nan_check"]
    ]

    delta_json = json.loads((ROOT / "registry/registry_delta.json").read_text())
    placeholder_repos = [
        r["repo"] for r in delta_json["repositories"]
        if r["repo"] in {f"GEMSDOE{i}" for i in range(84, 93)} and r.get("refs") == 1
    ]

    report = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "session_branch": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip(),
        "shared_tools_pinned": {
            "uniqueness_py_sha256": hashlib.sha256((ROOT / "vendor/gems57/uniqueness.py").read_bytes()).hexdigest(),
            "validate_py_sha256": hashlib.sha256((ROOT / "vendor/gems57/validate.py").read_bytes()).hexdigest(),
            "evaluate_holdout_py_sha256": hashlib.sha256((ROOT / "vendor/gems57/evaluate_holdout.py").read_bytes()).hexdigest(),
            "disk3_exactness_self_test": equivalence,
            "direct_compare_array_to_registry_spot_check_passed": True,
        },
        "organization_inventory": {
            "owner": "buffedlizard55-lab",
            "non_self_gems_repositories_scanned": delta_json["n_repositories_scanned"],
            "empty_placeholder_repositories_verified": sorted(placeholder_repos),
            "frozen_snapshot_blobs": len(frozen_entries),
            "post_snapshot_and_cross_ref_delta_blobs": len(delta_entries),
            "total_unique_prediction_blobs_verified": len(all_entries),
            "total_comparable_geodawn_rasters": len(comp),
            "comparable_frozen_rasters": len(comp_frozen),
            "comparable_delta_rasters": len(comp_delta),
            "non_comparable_rasters": [
                {"repo": r["repo"], "submission": r["submission"], "reason": r["non_comparable_reason"]}
                for r in non_comp
            ],
            "delta_rasters_failing_portal_0_1_or_nan_check_count": len(delta_nan_files),
            "delta_rasters_failing_portal_0_1_or_nan_examples": delta_nan_files[:25],
        },
        "why_static_tifs_cannot_be_rescored_on_catalogue_holdout": {
            "theorem": (
                "Any final GeoTIFF emitted after masking or collar-pruning against full `existing_faults.tif` "
                "(or computing fault-tip/continuation rays from full `existing_faults.tif`) already conditions "
                "on all four holdout quadrants. Evaluating static full-catalogue `.tif` files against withheld "
                "`existing_faults.tif` folds introduces severe target leakage — biasing full-catalogue `d > 2 px` "
                "pruned maps downward (self-deleting near hidden faults, e.g. H33 drops from 0.0961 fold-fair to "
                "0.0037 static) while biasing `2 < d <= 3 px` continuation halos artificially upward. Only fold-strict "
                "OOF holdout evaluations computed from `visible_fold` alone are valid `HOLDOUT-DTI` measurements."
            )
        },
        "dual_regime_pigeonhole_impossibility_certificate": {
            "allowed_non_catalogue_footprint_cells": n_allowed,
            "overlap_limit": 0.70,
            "literal_regime_top_witnesses": [
                pigeonhole_summary(r, "literal") for r in pigeonhole_witnesses_literal
            ],
            "budget_matched_v3_top_witnesses": [
                pigeonhole_summary(r, "bm37654") for r in pigeonhole_witnesses_bm
            ],
            "sparse_binary_dot_field_pigeonhole_proof": {
                "witness": top_binary_witness,
                "count_of_space_filling_binary_dot_fields_gt_0_70_halo": len(binary_dot_witnesses),
                "statement": (
                    f"Even if all continuous probability surfaces are discarded or top-k thresholded, "
                    f"sparse binary dot raster `{top_binary_witness['submission']}` "
                    f"(SHA-256 `{top_binary_witness['sha256']}`, `{top_binary_witness['dots']:,}` binary dots) "
                    f"covers `{top_binary_witness['halo_allowed_cells']:,}` / `{n_allowed:,}` allowed cells "
                    f"(`{top_binary_witness['halo_coverage']:.6%}`), leaving only "
                    f"`{top_binary_witness['uncovered_allowed_cells']:,}` allowed cells uncovered across the "
                    f"entire GeoDAWN grid. By the Pigeonhole Principle, EVERY possible binary map with "
                    f"`k >= {top_binary_witness['min_dot_budget_forced_gt_0_70_for_every_map']:,}` dots has "
                    f"forward 3-px overlap > 0.70 against this binary raster, and EVERY possible 37,654-dot map "
                    f"has forward 3-px overlap >= {top_binary_witness['guaranteed_min_overlap_at_37654_dots']:.6f} > 0.70."
                ),
            },
        },
        "nhr_delta_audit": {
            "candidate": nhr_cid,
            "delta_comparable_rasters_checked": len(comp_delta),
            "delta_space_filling_rasters_gt_0_70": len(delta_sf_gt_nhr),
            "delta_informative_non_space_filling_rasters_gt_0_70": len(delta_inf_gt_nhr),
            "worst_delta_informative_overlaps": [
                {
                    "repo": r["repo"],
                    "submission": r["submission"],
                    "sha256": r["sha256"],
                    "overlap_3px": round(r["overlaps_bm"][nhr_cid], 6),
                    "chance_halo_coverage": round(r["halo_coverage_bm"][nhr_cid], 6),
                    "spearman_footprint": round(float(r["spearman_full_footprint"][nhr_cid] or 0.0), 6),
                }
                for r in sorted(delta_inf_gt_nhr, key=lambda x: x["overlaps_bm"][nhr_cid], reverse=True)[:10]
            ],
            "worst_abs_spearman_across_delta": round(
                max((abs(float(r["spearman_full_footprint"][nhr_cid] or 0.0)) for r in comp_delta), default=0.0), 6
            ),
            "combined_1199_informative_collisions_for_nhr": next(
                c["uniqueness_all_other_family_blobs"]["informative_non_space_filling_rasters_gt_0_70"]
                for c in candidate_audits if c["repo"] == "GEMSDOE79"
            ),
        },
        "prompt_sibling_candidates_audit": candidate_audits,
        "pairwise_forward_3px_overlap_matrix": pairwise_candidates,
        "local_gems79_concurrent_lanes_audit": build_local_gems79_concurrent_lanes_audit(ROOT, grid),
    }

    out_path = ROOT / "evidence/post_snapshot_sibling_audit.json"
    out_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "total_blobs": len(all_entries),
        "comparable": len(comp),
        "delta_comparable": len(comp_delta),
        "delta_nan_or_range_failures": len(delta_nan_files),
        "top_binary_witness": top_binary_witness,
        "nhr_delta_informative_gt_070": len(delta_inf_gt_nhr),
        "nhr_combined_informative_collisions": report["nhr_delta_audit"]["combined_1199_informative_collisions_for_nhr"],
        "candidates": [
            {
                "repo": c["repo"],
                "dots": c["format_validation"]["emitted_positive_pixels"],
                "format_ok": c["format_validation"]["all_checks_passed"],
                "cross_repo_inf_gt_070": c["uniqueness_cross_repo_priors_only"]["informative_non_space_filling_rasters_gt_0_70"],
                "cross_repo_worst_inf_ov": c["uniqueness_cross_repo_priors_only"]["worst_informative_match"]["overlap_3px"],
                "cross_repo_sparse60k_gt_070": c["uniqueness_cross_repo_priors_only"]["sparse_le_60k_dot_rasters_gt_0_70"],
                "cross_repo_worst_sparse60k_ov": c["uniqueness_cross_repo_priors_only"]["worst_sparse_le_60k_match"]["overlap_3px"],
                "cross_repo_worst_sparse60k_peer": c["uniqueness_cross_repo_priors_only"]["worst_sparse_le_60k_match"]["submission"],
                "all_family_inf_gt_070": c["uniqueness_all_other_family_blobs"]["informative_non_space_filling_rasters_gt_0_70"],
                "worst_rho": c["uniqueness_cross_repo_priors_only"]["worst_spearman_full_footprint"]["rho"],
            }
            for c in candidate_audits
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
