#!/usr/bin/env python3
"""Two-process parallel driver around UNMODIFIED ``gems57.uniqueness.compare_array_to_registry``.

Splits ``inventory()['rasters']`` cleanly across ``max_workers`` processes (default 2)
without altering a single byte of ``vendor/gems57/uniqueness.py`` or a single floating-
point result relative to ``scripts/nhr_uniqueness.py``.

Protocol execution order:
  1. ``surface`` — evaluates pre-placement continuous surface ``final_surface.npy``
     BEFORE ``final_dots.npy`` exists; writes ``evidence/mrnd/uniqueness_surface.json``
     and ``evidence/mrnd/surface_diagnostic.json``.
  2. ``final`` — runs shared deterministic 3 px NMS placement ``gems79.placement.place``
     (37,654 dots), evaluates ``final_dots.npy`` across all 992 frozen blobs, writes
     ``evidence/mrnd/uniqueness_final.json``, ``evidence/mrnd/overlap_chance.json``,
     ``evidence/mrnd/m1_final_build.json``, and locks ``m1_experiment_state.json``.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import rasterio
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import uniqueness as shared  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems79 import mrnd, nhr  # noqa: E402
from gems79.placement import place  # noqa: E402
import nhr_uniqueness  # noqa: E402

BUDGET = 37654
CACHE = ROOT / ".cache" / "mrnd"
OUT = ROOT / "evidence" / "mrnd"


def _worker_compare(task: tuple) -> list[dict]:
    arr_path, subset_rasters, include_reverse = task
    grid = load_grid(ROOT / "data/reference")
    eg = (grid.shape, grid.crs, grid.transform)
    arr = np.load(arr_path, mmap_mode="r")
    sub_inv = {"rasters": subset_rasters, "complete_accessible_scan": True, "errors": []}
    res = shared.compare_array_to_registry(
        arr,
        sub_inv,
        grid.footprint,
        include_reverse=include_reverse,
        expected_grid=eg,
        dot_definition="budget-matched-v3",
    )
    return res["rows"]


def parallel_compare(arr: np.ndarray, inv: dict, include_reverse: bool, workers: int = 2) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp_path = CACHE / "_tmp_compare_input.npy"
    np.save(tmp_path, np.asarray(arr, dtype=np.float32))
    rasters = list(inv["rasters"])
    chunks = [rasters[i::workers] for i in range(workers) if rasters[i::workers]]
    tasks = [(str(tmp_path), ch, include_reverse) for ch in chunks]
    by_key: dict[tuple[str, str], dict] = {}
    if workers <= 1 or len(tasks) == 1:
        part_lists = [_worker_compare(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=len(tasks)) as pool:
            part_lists = list(pool.map(_worker_compare, tasks))
    # Reassemble in exact deterministic inventory order
    ordered_rows: list[dict] = []
    cursors = [0] * len(part_lists)
    for idx in range(len(rasters)):
        w_id = idx % len(part_lists)
        ordered_rows.append(part_lists[w_id][cursors[w_id]])
        cursors[w_id] += 1
    try:
        tmp_path.unlink(missing_ok=True)
    except OSError:
        pass
    return {
        "rows": ordered_rows,
        "complete_accessible_scan": bool(inv.get("complete_accessible_scan", True) and not inv.get("errors")),
    }


def run_surface(workers: int = 2) -> dict:
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    inv, expected = nhr_uniqueness.inventory()
    surface = np.load(CACHE / "final_surface.npy")
    prov = shared.budget_matched_dots(surface, grid.footprint & ~grid.catalogue, BUDGET).astype(np.float32)

    print(f"[surface 1/2] scanning continuous rank correlation across {expected} blobs on {workers} workers...", flush=True)
    r_s = parallel_compare(surface, inv, include_reverse=False, workers=workers)
    print(f"[surface 2/2] scanning provisional top-{BUDGET} 3px overlap across {expected} blobs on {workers} workers...", flush=True)
    r_p = parallel_compare(prov, inv, include_reverse=False, workers=workers)

    s_c = nhr_uniqueness.compact(r_s, ("spearman_full_footprint",))
    p_c = nhr_uniqueness.compact(r_p, ("my_dots_within_3px_of_theirs", "spearman_full_footprint"))
    rho = s_c["worst_spearman_full_footprint"]["value"]
    ov = p_c["worst_my_dots_within_3px_of_theirs"]["value"]
    complete = (
        s_c["complete"]
        and p_c["complete"]
        and not s_c["errors"]
        and not p_c["errors"]
        and s_c["checked"] == p_c["checked"] == expected
    )
    duplicate = bool((rho is not None and rho > shared.RHO_LIMIT) or ov > shared.OVERLAP_LIMIT)
    result = dict(
        schema_version=1,
        lane="H79-MRND",
        phase="surface",
        evidence_class="REGISTRY-MEASUREMENT",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        runtime_s=round(time.time() - t0, 1),
        shared_tool="gems57.uniqueness.compare_array_to_registry",
        shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
        dot_definition="budget-matched-v3",
        rho_limit=shared.RHO_LIMIT,
        overlap_limit=shared.OVERLAP_LIMIT,
        registry_rasters_expected=expected,
        surface_rank_check=s_c,
        provisional_topk_check=p_c,
        provisional_cells=int(prov.sum()),
        surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest(),
        worst_spearman=rho,
        worst_forward_overlap_3px=ov,
        complete_comparison=complete,
        duplicate=duplicate,
        passed=bool(complete and not duplicate),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "uniqueness_surface.json").write_text(
        json.dumps(result, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n"
    )

    # Diagnostic partition on provisional surface top-K (reporting only, never alters verdict)
    halo_map = {r["submission"]: r for r in json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())["rows"]}
    diag_rows, diag_errors = [], []
    for r in r_p["rows"]:
        if "error" in r:
            diag_errors.append(dict(submission=r.get("submission"), error=r["error"]))
            continue
        h = halo_map.get(r["submission"])
        hc = None if h is None else float(h["halo_coverage"])
        ov_r = float(r["my_dots_within_3px_of_theirs"])
        diag_rows.append(
            dict(
                submission=r["submission"],
                representation=r["representation"],
                their_dots=r["their_dots"],
                overlap=ov_r,
                spearman=r["spearman_full_footprint"],
                halo_coverage=hc,
                space_filling=None if hc is None else bool(hc > shared.OVERLAP_LIMIT),
                beyond_chance=None if hc is None or hc >= 1 else (ov_r - hc) / (1.0 - hc),
            )
        )
    informative = [r for r in diag_rows if r["space_filling"] is False]
    dense = [r for r in diag_rows if r["space_filling"] is True]
    flagged_all = [r for r in diag_rows if r["overlap"] > shared.OVERLAP_LIMIT]
    flagged_inf = [r for r in informative if r["overlap"] > shared.OVERLAP_LIMIT]
    worst_inf = max(informative, key=lambda r: r["overlap"]) if informative else None
    diag_summary = dict(
        schema_version=1,
        lane="H79-MRND",
        evidence_class="REGISTRY-MEASUREMENT (diagnostic, not a gate)",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        surface_sha256=result["surface_sha256"],
        provisional_dots=int(prov.sum()),
        registry_rasters_expected=expected,
        compared=len(diag_rows),
        errors=diag_errors,
        space_filling_halo_gt_0_70=len(dense),
        informative_halo_le_0_70=len(informative),
        flagged_by_literal_gate_all=len(flagged_all),
        flagged_by_informative_only=len(flagged_inf),
        flagged_by_space_filling_only=len(flagged_all) - len(flagged_inf),
        worst_informative=worst_inf,
        top10_informative=sorted(informative, key=lambda r: -r["overlap"])[:10],
        worst_all=max(diag_rows, key=lambda r: r["overlap"]) if diag_rows else None,
    )
    (OUT / "surface_diagnostic.json").write_text(
        json.dumps(diag_summary, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n"
    )
    print(
        json.dumps(
            {
                "phase": "surface",
                "runtime_s": result["runtime_s"],
                "literal_passed": result["passed"],
                "worst_spearman": round(rho, 6),
                "worst_all_overlap": round(ov, 6),
                "flagged_all": len(flagged_all),
                "flagged_informative_halo_le_070": len(flagged_inf),
                "worst_informative": worst_inf,
            },
            indent=2,
        ),
        flush=True,
    )
    return result


def run_final(workers: int = 2) -> dict:
    t0 = time.time()
    prereg = json.loads((ROOT / "registry/preregistration_mrnd.json").read_text())
    fix = prereg["experiments"][0]["fixed_parameters"]
    spacing = int(fix["placement_spacing_px"])

    grid = load_grid(ROOT / "data/reference")
    allowed = grid.footprint & ~grid.catalogue
    surface = np.load(CACHE / "final_surface.npy")

    print(f"[final 1/3] placing {BUDGET} deterministic {spacing}px dots via gems79.placement.place...", flush=True)
    dots, p_info = place(surface, allowed, BUDGET, spacing=spacing)
    np.save(CACHE / "final_dots.npy", dots)
    dots_f32 = dots.astype(np.float32)

    inv, expected = nhr_uniqueness.inventory()
    print(f"[final 2/3] scanning final dot map across {expected} blobs on {workers} workers...", flush=True)
    r_f = parallel_compare(dots_f32, inv, include_reverse=True, workers=workers)

    f_c = nhr_uniqueness.compact(r_f, ("my_dots_within_3px_of_theirs", "spearman_full_footprint", "jaccard_dot_sets"))
    rho = f_c["worst_spearman_full_footprint"]["value"]
    ov = f_c["worst_my_dots_within_3px_of_theirs"]["value"]
    lit_cont = [r for r in r_f["rows"] if "error" not in r and r.get("representation") == "continuous_surface"]
    complete = f_c["complete"] and not f_c["errors"] and f_c["checked"] == expected
    duplicate = bool((rho is not None and rho > shared.RHO_LIMIT) or ov > shared.OVERLAP_LIMIT)
    dots_sha = hashlib.sha256(dots.tobytes()).hexdigest()

    result = dict(
        schema_version=1,
        lane="H79-MRND",
        phase="final",
        evidence_class="REGISTRY-MEASUREMENT",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        runtime_s=round(time.time() - t0, 1),
        shared_tool="gems57.uniqueness.compare_array_to_registry",
        shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
        dot_definition="budget-matched-v3",
        rho_limit=shared.RHO_LIMIT,
        overlap_limit=shared.OVERLAP_LIMIT,
        registry_rasters_expected=expected,
        final_check=f_c,
        my_dots=int(dots.sum()),
        dots_sha256=dots_sha,
        continuous_surface_rasters=len(lit_cont),
        dot_field_rasters=f_c["checked"] - len(lit_cont),
        top10_overlap=sorted(
            (
                {
                    "submission": r["submission"],
                    "overlap": r["my_dots_within_3px_of_theirs"],
                    "spearman": r["spearman_full_footprint"],
                    "representation": r["representation"],
                    "their_dots": r["their_dots"],
                }
                for r in r_f["rows"]
                if "error" not in r
            ),
            key=lambda d: -d["overlap"],
        )[:10],
        worst_spearman=rho,
        worst_forward_overlap_3px=ov,
        complete_comparison=complete,
        duplicate=duplicate,
        passed=bool(complete and not duplicate),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "uniqueness_final.json").write_text(
        json.dumps(result, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n"
    )

    print("[final 3/3] assembling full 990-raster overlap_chance.json + m1_final_build.json...", flush=True)
    nhr_chance = json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())
    nhr_by_sha = {r["sha256"]: r for r in nhr_chance["rows"]}

    mine_ranks = rankdata(dots.astype(np.float64)[grid.footprint])
    mine_ranks -= mine_ranks.mean()
    norm_r = float(np.linalg.norm(mine_ranks))

    chance_rows, not_comparable = [], []
    by_rec = list(zip(inv["rasters"], r_f["rows"]))
    for rec_item, r_row in by_rec:
        name = (
            rec_item["sources"][0]
            if ":" in rec_item["sources"][0]
            else rec_item["repo_first"] + ":" + rec_item["sources"][0]
        )
        prev = nhr_by_sha.get(rec_item["sha256"])
        if "error" not in r_row and prev is not None:
            cov = float(prev["halo_coverage"])
            ou = float(prev["overlap_uniform"])
            ov_c = float(r_row["my_dots_within_3px_of_theirs"])
            rho_c = r_row["spearman_full_footprint"]
            kappa = None if cov >= 1.0 else (ov_c - cov) / (1.0 - cov)
            chance_rows.append(
                dict(
                    submission=prev["submission"],
                    sha256=rec_item["sha256"],
                    representation=r_row["representation"],
                    georeference_matches_sample=True,
                    their_dots=int(r_row["their_dots"]),
                    halo_coverage=cov,
                    overlap_candidate=ov_c,
                    overlap_uniform=ou,
                    overlap_beyond_chance=kappa,
                    overlap_beyond_chance_uniform=prev["overlap_beyond_chance_uniform"],
                    spearman=rho_c,
                )
            )
            continue
        # Handle the 4 same-shape non-identical transform rasters + 2 non-full-grid fixtures directly
        p = Path(rec_item["cache_file"])
        try:
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != grid.footprint.shape:
                    raise ValueError(f"shape {src.shape} / bands {src.count} differ from the competition grid")
                georef_ok = (
                    src.crs is not None and src.crs.to_epsg() == 32611 and src.transform == grid.transform
                )
                a = src.read(1).astype(np.float32)
        except Exception as exc:
            not_comparable.append(dict(submission=name, reason=str(exc)[:160]))
            continue
        a = np.where(np.isfinite(a), a, 0.0)
        a[~grid.footprint] = 0
        support = (a > 0) & grid.footprint
        kind = shared.representation_class(int(support.sum()), int(grid.footprint.sum()))["kind"]
        if kind == "continuous_surface":
            support = shared.budget_matched_dots(a, grid.footprint, BUDGET)
        halo = shared._near(support)
        cov = float(halo[allowed].mean())
        ov_c = float(halo[dots].mean())
        ou = float(prev["overlap_uniform"]) if prev else cov
        tv = a[grid.footprint].astype(np.float64)
        rho_c = None if np.ptp(tv) == 0 else float(
            np.dot(mine_ranks, rankdata(tv) - rankdata(tv).mean())
            / (norm_r * np.linalg.norm(rankdata(tv) - rankdata(tv).mean()))
        )
        chance_rows.append(
            dict(
                submission=prev["submission"] if prev else name,
                sha256=rec_item["sha256"],
                representation=kind,
                georeference_matches_sample=georef_ok,
                their_dots=int(support.sum()),
                halo_coverage=cov,
                overlap_candidate=ov_c,
                overlap_uniform=ou,
                overlap_beyond_chance=None if cov >= 1.0 else (ov_c - cov) / (1.0 - cov),
                overlap_beyond_chance_uniform=prev["overlap_beyond_chance_uniform"] if prev else 0.0,
                spearman=rho_c,
            )
        )

    lit_flags = [r for r in chance_rows if r["overlap_candidate"] > shared.OVERLAP_LIMIT]
    uni_fail = [r for r in chance_rows if r["overlap_uniform"] > shared.OVERLAP_LIMIT]
    space = [r for r in chance_rows if r["halo_coverage"] > shared.OVERLAP_LIMIT]
    informative = [r for r in chance_rows if r["halo_coverage"] <= shared.OVERLAP_LIMIT]
    inf_flags = [r for r in informative if r["overlap_candidate"] > shared.OVERLAP_LIMIT]

    def worst(rs, k):
        rs = [r for r in rs if r[k] is not None]
        return max(rs, key=lambda r: r[k]) if rs else None

    chance_out = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        lane="H79-MRND",
        experiment="M1",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
        dot_definition="budget-matched-v3",
        budget=BUDGET,
        uniform_control_seed=79,
        registry_rasters_expected=expected,
        compared=len(chance_rows),
        not_comparable=not_comparable,
        same_shape_other_georeference=[r["submission"] for r in chance_rows if not r["georeference_matches_sample"]],
        rasters_where_candidate_overlap_gt_0_70=len(lit_flags),
        rasters_where_uniform_random_overlap_gt_0_70=len(uni_fail),
        space_filling_rasters_halo_gt_0_70=len(space),
        informative_rasters_halo_le_0_70=len(informative),
        informative_flagged_rasters_gt_0_70=len(inf_flags),
        candidate_flagged_only_by_space_filling_rasters=all(
            r["halo_coverage"] > shared.OVERLAP_LIMIT for r in lit_flags
        ),
        worst_candidate_overlap_vs_informative_rasters=worst(informative, "overlap_candidate"),
        top10_informative_rasters=sorted(informative, key=lambda r: -r["overlap_candidate"])[:10],
        worst_candidate_overlap_beyond_chance=worst(chance_rows, "overlap_beyond_chance"),
        worst_uniform_overlap_beyond_chance=worst(chance_rows, "overlap_beyond_chance_uniform"),
        worst_spearman_all_comparable=worst(chance_rows, "spearman"),
        rows=sorted(chance_rows, key=lambda r: -r["overlap_candidate"]),
    )
    (OUT / "overlap_chance.json").write_text(
        json.dumps(chance_out, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n"
    )

    lstrike, lcoh = nhr.read_lidar_orientation(grid.footprint)
    geom = mrnd.geometry_features(grid.catalogue, grid.footprint, lstrike, lcoh)
    reg_map = mrnd.regime_id_from_dist_px(geom["_dist_px"], allowed)
    d_m = geom["_dist_px"][dots] * 100.0
    reg_counts = {
        name: int((dots & (reg_map == r_idx)).sum())
        for r_idx, (name, _, _, _) in enumerate(mrnd.REGIME_SPECS)
    }
    meta_static = json.loads((CACHE / "static_stack.json").read_text())
    surf_diag = json.loads((OUT / "surface_diagnostic.json").read_text())
    build_meta = dict(
        lane="H79-MRND",
        experiment="M1",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest(),
        dots_sha256=dots_sha,
        n_dots=int(dots.sum()),
        placement=p_info,
        distance_distribution={
            "median_m": round(float(np.median(d_m)), 1),
            "p10_m": round(float(np.percentile(d_m, 10)), 1),
            "p90_m": round(float(np.percentile(d_m, 90)), 1),
            "share_le_1400m": round(float((d_m <= 1400.0).mean()), 4),
            "share_1400_to_4500m": round(float(((d_m > 1400.0) & (d_m <= 4500.0)).mean()), 4),
            "share_gt_4500m": round(float((d_m > 4500.0).mean()), 4),
            "regime_dot_counts": reg_counts,
        },
        feature_count=len(meta_static["names"]) + len(mrnd.GEOMETRY_NAMES),
        feature_names=list(meta_static["names"]) + list(mrnd.GEOMETRY_NAMES),
        surface_informative_flags=surf_diag["flagged_by_informative_only"],
        final_informative_flags=len(inf_flags),
        candidate_flagged_only_by_space_filling_rasters=chance_out[
            "candidate_flagged_only_by_space_filling_rasters"
        ],
    )
    (OUT / "m1_final_build.json").write_text(json.dumps(build_meta, indent=2) + "\n")

    surf_res = json.loads((OUT / "uniqueness_surface.json").read_text())
    all_literal_unique = bool(surf_res["passed"] and result["passed"] and not lit_flags)
    state = dict(
        lane="H79-MRND",
        experiment="M1",
        experiment_count=1,
        max_experiments=3,
        stopped=True,
        verdict="promote" if all_literal_unique else "negative",
        stop_reason=(
            None
            if all_literal_unique
            else (
                f"Unexempted gems57.uniqueness gate flagged {len(lit_flags)} rasters "
                f"({len(lit_flags) - len(inf_flags)} space-filling/lattice priors with halo_coverage > 0.70, "
                f"{len(inf_flags)}/{len(informative)} informative non-space-filling rasters). "
                "Lane closed without dense-prior exemptions."
            )
        ),
        informative_non_space_filling_surface_flags=surf_diag["flagged_by_informative_only"],
        informative_non_space_filling_final_flags=len(inf_flags),
        candidate_flagged_only_by_space_filling_rasters=chance_out[
            "candidate_flagged_only_by_space_filling_rasters"
        ],
        locked_utc=datetime.now(timezone.utc).isoformat(),
    )
    (OUT / "m1_experiment_state.json").write_text(json.dumps(state, indent=2) + "\n")

    print(
        json.dumps(
            {
                "phase": "final",
                "runtime_s": result["runtime_s"],
                "literal_passed": result["passed"],
                "worst_spearman": round(rho, 6),
                "flagged_all_990": len(lit_flags),
                "flagged_informative_960": len(inf_flags),
                "candidate_flagged_only_by_space_filling_rasters": chance_out[
                    "candidate_flagged_only_by_space_filling_rasters"
                ],
                "worst_informative": chance_out["worst_candidate_overlap_vs_informative_rasters"],
                "distance_distribution": build_meta["distance_distribution"],
            },
            indent=2,
        ),
        flush=True,
    )
    return result


if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError
    st_path = OUT / "m1_experiment_state.json"
    if st_path.exists():
        st = json.loads(st_path.read_text())
        if st.get("stopped") or st.get("verdict") in ("negative", "promote"):
            err = LaneClosedError(
                f"H79-MRND: lane is closed ({st.get('verdict', 'stopped')}). No files changed."
            )
            print(str(err), file=sys.stderr)
            raise SystemExit(2)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=["surface", "final"])
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    run_surface(a.workers) if a.phase == "surface" else run_final(a.workers)
