#!/usr/bin/env python3
"""G79-STEPCO S2-COVER: kernel-cover placement on the frozen S1 surfaces.

Single preregistered change vs S1 (see
registry/preregistration_g79stepco_s2_amendment_20261022.json): dots are ranked
by gems57.emit.expected_credit(p) instead of p. Everything else - folds, fits
(cached surfaces), allocator, budget, masks, controls, evaluator - is S1's.
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
from gems57 import evaluate_holdout as evaluator
from gems57 import uniqueness as shared
from gems57.emit import expected_credit
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw
from gems57.submission_writer import write_submission
from gems79.placement import place
import run_stepco_experiment as s1

BUDGET = s1.BUDGET
CACHE, EV = s1.CACHE, s1.EV


def holdout_seed(grid, support, seed, d28_pos, dem_step):
    surface = np.load(CACHE / f"surface_s1_seed{seed}.npy", mmap_mode="r")
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    rng_surface = np.random.default_rng(79221022).random(grid.shape, dtype=np.float32)
    terms, per_fold = {}, []
    for fold in folds:
        ys, xs = np.nonzero(fold["region"])
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = (sy, sx)
        local_fold = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
        allowed = support[sl] & fold["region"][sl] & (d_vis > 2)
        budget = int(round(BUDGET * fold["region"].sum() / grid.footprint.sum()))
        cover = expected_credit(np.asarray(surface[sl], dtype=np.float32))
        arms = {"candidate": cover, "uniform_control": rng_surface[sl],
                "dem_step_only_control": np.asarray(dem_step[sl], dtype=np.float32)}
        for name, surf in arms.items():
            dots, _ = place(np.asarray(surf, dtype=np.float32), allowed, budget)
            res, bt = evaluator.evaluate(dots.astype(np.float32), local_fold,
                                         grid.footprint[sl], origin=(sy.start, sx.start),
                                         global_shape=grid.shape)
            terms[name] = terms.get(name, np.zeros_like(bt)) + bt
            per_fold.append({"arm": name, "fold": fold["name"], **res})
            print(f"S2 HOLDOUT-DTI seed={seed} {fold['name']} {name}: {res['dti']:.4f}", flush=True)
        h33 = (d28_pos[sl] & fold["region"][sl] & (d_vis > 2)).astype(np.float32)
        res, bt = evaluator.evaluate(h33, local_fold, grid.footprint[sl],
                                     origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", np.zeros_like(bt)) + bt
        per_fold.append({"arm": "h33_foldfair_control", "fold": fold["name"], **res})
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    summary.update(seed=seed, per_fold=per_fold, evidence_class="HOLDOUT-DTI",
                   experiment="S2-COVER", placement_ranking="gems57.emit.expected_credit(p)")
    s1.write_json(EV / f"holdout_s2_seed{seed}.json", summary)
    return summary


def main():
    started = datetime.now(timezone.utc)
    grid = load_grid(ROOT / "data/reference")
    support = np.load(CACHE / "support.npy")
    dem_step = np.load(CACHE / "det_elev_step.npy", mmap_mode="r")
    records_obj = s1.registry_records()
    by_sha = {r["sha256"]: r for r in records_obj["records"]}
    with rasterio.open(by_sha[s1.D28_SHA256]["file"]) as ds:
        d28 = ds.read(1)
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    del d28

    summaries = [holdout_seed(grid, support, s, d28_pos, dem_step) for s in (20, 30)]
    gates = {}
    for s in summaries:
        sc, pd_ = s["scores"], s["paired_differences"]
        gates[f"seed_{s['seed']}"] = {
            "candidate_dti": sc["candidate"]["dti"],
            "beats_uniform_point": sc["candidate"]["dti"] > sc["uniform_control"]["dti"],
            "beats_dem_step_point": sc["candidate"]["dti"] > sc["dem_step_only_control"]["dti"],
            "beats_h33_foldfair_ci95_above_0": pd_["h33_foldfair_control"]["ci95"][0] > 0}
    holdout_pass = all(all(v.values()) for v in
                       [{k: v for k, v in g.items() if k != "candidate_dti"} for g in gates.values()])
    print(json.dumps({"s2_holdout_gates": gates, "holdout_pass": holdout_pass}, indent=2), flush=True)

    surface = np.asarray(np.load(CACHE / "surface_s1_final.npy", mmap_mode="r"))
    surf_sha = hashlib.sha256(np.ascontiguousarray(surface).tobytes()).hexdigest()
    uni_surface = json.loads((EV / "uniqueness_s1_surface.json").read_text())
    worst_rho = uni_surface["two_phase_summary"]["literal_reading"]["worst_spearman_full_footprint"]
    rho_dup = bool(worst_rho is not None and worst_rho > shared.RHO_LIMIT)
    state = {"experiment": "S2-COVER", "started_utc": started.isoformat(),
             "holdout_gates": gates, "holdout_pass": holdout_pass,
             "surface_sha256": surf_sha, "surface_worst_rho": worst_rho,
             "duplicate_by_surface_rho": rho_dup,
             "surface_uniqueness_source": "evidence/stepco/uniqueness_s1_surface.json (identical surface)"}
    if rho_dup:
        state.update(verdict="negative", stop_reason="duplicate_surface_rank_correlation")
        s1.write_json(EV / "experiment_s2_state.json", state)
        print(json.dumps(state, indent=2))
        return

    emission = np.where(grid.footprint & ~grid.catalogue, surface, 0.0).astype(np.float32)
    cover = expected_credit(emission)
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    allowed = grid.footprint & support & (d_cat > 2)
    dots, placement = place(cover, allowed, BUDGET, spacing=3)
    prediction = dots.astype(np.float32)
    uni_final = s1.uniqueness_phase(prediction, grid, records_obj, "final_s2", my_dots=dots)
    two = uni_final["two_phase_summary"]
    like = two["like_for_like_reading"]
    dup_final = bool(like["duplicate"])
    mb_worst = uni_final.get("matched_budget_worst_overlap")
    if mb_worst is not None and mb_worst > shared.OVERLAP_LIMIT:
        dup_final = True
    promote = bool(holdout_pass and not dup_final)
    state.update(placement=placement, duplicate_final_dots=dup_final,
                 matched_budget_worst_overlap=mb_worst,
                 final_worst_dotfield_overlap=like["worst_forward_overlap_dot_fields"],
                 final_worst_rho=two["literal_reading"]["worst_spearman_full_footprint"],
                 literal_worst_overlap=two["literal_reading"]["worst_forward_overlap"],
                 verdict="promote" if promote else "negative")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = "zeros" if promote else "DO-NOT-SUBMIT"
    name = f"gems79-stepco-s2cover-37654dots-{stamp}-{surf_sha[:8]}-{suffix}"
    note = f"GEMSDOE79 STEPCO S2-COVER: step-dipole HGB + kernel-cover dots 37654 s3 cat>2px {stamp}"[:140]
    out = ROOT / "docs/downloads" / f"{name}.tif"
    receipt_w = write_submission(out, prediction, ROOT / "data/reference/sample_submission.tif",
                                 grid.footprint, note=note, name=name,
                                 catalogue=grid.catalogue,
                                 metadata={"lane": "G79-STEPCO", "experiment": "S2-COVER",
                                           "surface_sha256": surf_sha, "verdict": state["verdict"],
                                           "human_inspection_required": False})
    state.update(submission_name=name, submission_note=note,
                 submission_file=str(out.relative_to(ROOT)),
                 raster_sha256=receipt_w["sha256"], writer_receipt=receipt_w,
                 byte_distinct_from_all_992_pins=receipt_w["sha256"] not in set(records_obj["all_pin_sha256"]),
                 finished_utc=datetime.now(timezone.utc).isoformat())
    s1.write_json(EV / "experiment_s2_state.json", state)
    print(json.dumps({k: state[k] for k in ("verdict", "submission_file", "raster_sha256",
                                             "holdout_pass", "duplicate_final_dots")}, indent=2))


if __name__ == "__main__":
    main()
