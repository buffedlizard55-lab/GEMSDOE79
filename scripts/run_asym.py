#!/usr/bin/env python3
"""H79-ASYM experiment X1 (registry/preregistration_asym.json, commit 365b727).

Stages, in the order the protocol requires:
  surface    build the antislope excess surface S (no learning, no catalogue input),
             then the surface duplicate gate BEFORE any placement. A failure stops here.
  holdout    --seed S: canary on S/U/D/C, then leave-one-quadrant-out placement of
             candidate / uniform / H33 fold-fair arms with the shared evaluator.
  final      place 37,654 dots on the whole footprint off the catalogue, then the final
             dot duplicate gate. Only run after every earlier gate passed.

NOTE (session 2026-10-22): the holdout and final stages were NOT executed. The surface gate
stopped the lane first (IR-79-74), so this code is a reviewed template only. Run it only after
a surface pass, and record the result in a new card.

Every score written here is HOLDOUT-DTI from gems57-pooled-hide-v2.
Nothing is tuned on the holdout. Parameters come from the preregistration.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator          # noqa: E402
from gems57.grid import load_grid                          # noqa: E402
from gems57.holdout import buffered_component_draw         # noqa: E402
from gems57 import uniqueness as shared                    # noqa: E402
from gems79 import asym                                    # noqa: E402
from gems79.placement import place                         # noqa: E402
import analyze_h33                                         # noqa: E402
from run_experiment import canaries                        # noqa: E402  (shared canary, reused)
import nhr_uniqueness                                      # noqa: E402  (shared gate wrapper)

PREREG = json.loads((ROOT / "registry/preregistration_asym.json").read_text())
BUDGET = 37654
OUT = ROOT / "evidence" / "asym"
CACHE = ROOT / ".cache" / "asym"
LANE = "H79-ASYM"


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=float).replace(str(ROOT) + "/", "") + "\n")


def build_surface(grid):
    CACHE.mkdir(parents=True, exist_ok=True)
    art = asym.build(grid.footprint)
    S = art["S"]
    np.save(CACHE / "final_surface.npy", S)           # name expected by nhr_uniqueness
    info = dict(lane=LANE, p999=art["p999"], valid_cells=int(art["valid"].sum()),
                footprint_cells=int(grid.footprint.sum()),
                valid_fraction_of_footprint=float(art["valid"].sum() / grid.footprint.sum()),
                positive_cells=int((S > 0).sum()),
                S_min=float(S[grid.footprint].min()), S_max=float(S.max()),
                surface_sha256=hashlib.sha256(S.tobytes()).hexdigest(),
                lidar_inputs_sha256=asym.LIDAR.name)
    return art, info


def stage_surface():
    grid = load_grid(ROOT / "data/reference")
    art, info = build_surface(grid)
    _write(OUT / "surface_build.json", info)
    log("surface built", info)
    res = nhr_uniqueness.run("surface", lane=LANE, cache=CACHE, out_dir=OUT)
    log("surface gate passed:", res["passed"], "duplicate:", res["duplicate"])
    return res["passed"]


def stage_holdout(seed: int):
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    art = asym.build(grid.footprint)
    S, U, D, C = art["S"], art["U"], art["D"], art["C"]
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)

    log("canaries on S, U, D, C")
    feats = {}
    for name, arr in (("antislope_excess_S", S), ("upface_U", U), ("downface_D", D), ("coherence_C", C)):
        feats[name] = np.nan_to_num(arr, nan=-1.0).astype(np.float32)
    c_rows = canaries(feats, folds, seed)
    worst = max(c_rows, key=lambda r: r["symmetric_auc"])
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=worst["symmetric_auc"], worst=worst,
                  n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"] == n)
                                   for n in feats})
    log("canary max", round(canary["max_symmetric_auc"], 4), worst["feature"], worst["fold"])

    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    terms, fold_receipts = {}, []
    for fold in folds:
        region = fold["region"]
        allowed = region & grid.footprint & ~fold["masked_known"]
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = sy, sx
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        arms = {"candidate": S, "uniform_control": rng_surface}
        for name, surf in arms.items():
            dots, pinfo = place(surf[sl], allowed[sl], budget)
            _, bt = evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
            if name == "candidate":
                cand_info = pinfo
        d_vis = ndi.distance_transform_edt(~fold["visible"][sl])
        h33_ff = (d28_pos[sl] & region[sl] & (d_vis > 2)).astype(np.float32)
        _, bt = evaluator.evaluate(h33_ff, local, grid.footprint[sl],
                                   origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt
        fold_receipts.append(dict(fold=fold["name"], budget=budget, candidate_placement=cand_info,
                                  withheld_truth=int((fold["truth"] & region).sum())))
        gc.collect()
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    out = dict(schema_version=1, lane=LANE, experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time() - t0, 1), leakage_canary=canary,
               holdout=summary, folds=fold_receipts, h33_control_source=d28src,
               surface_sha256=hashlib.sha256(S.tobytes()).hexdigest())
    _write(OUT / f"x1_holdout_seed{seed}.json", out)
    s = summary["scores"]
    log({k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in s.items()})


def stage_final():
    grid = load_grid(ROOT / "data/reference")
    art, info = build_surface(grid)
    cat = grid.catalogue
    allowed = grid.footprint & ~cat
    dots, pinfo = place(art["S"], allowed, BUDGET)
    np.save(CACHE / "final_dots.npy", dots.astype(np.uint8))
    meta = dict(lane=LANE, placement=pinfo, n_dots=int(dots.sum()),
                dots_sha256=hashlib.sha256(dots.astype(np.uint8).tobytes()).hexdigest(),
                surface_sha256=info["surface_sha256"],
                dots_on_catalogue=int((dots & cat).sum()),
                dots_outside_footprint=int((dots & ~grid.footprint).sum()))
    _write(OUT / "x1_final_build.json", meta)
    log(meta)
    res = nhr_uniqueness.run("final", lane=LANE, cache=CACHE, out_dir=OUT)
    log("final gate passed:", res["passed"], "duplicate:", res["duplicate"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["surface", "holdout", "final"])
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    if a.stage == "surface":
        sys.exit(0 if stage_surface() else 2)
    if a.stage == "holdout":
        stage_holdout(a.seed)
    else:
        stage_final()
