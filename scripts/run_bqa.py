#!/usr/bin/env python3
"""H79-BQA experiment X1 (registry/preregistration_bqa.json).

Stages (run in this order; each writes evidence/bqa/*):
  holdout --seed S  canaries + leave-one-quadrant-out two-model holdout with six arms,
                    standard and far-field (> 1 km) sub-holdout, shared evaluator.
  surface           final band-weighted model on nested hides of the full catalogue;
                    writes the continuous surface ONLY (no dots).
  (then scripts/bqa_uniqueness.py surface must pass BEFORE placement)
  place             quota placement of 37,654 dots on the frozen surface; refuses to
                    run unless the surface uniqueness receipt passed for this surface.

All DTI values written here are HOLDOUT-DTI from gems57-pooled-hide-v2. Parameters
come from the preregistration; nothing is tuned on the holdout.
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
from gems57.holdout import buffered_component_draw, quadrant_ids  # noqa: E402
from gems79 import bqa, nhr                                # noqa: E402
from gems79.placement import place                         # noqa: E402
import analyze_h33                                         # noqa: E402
import run_nhr                                             # noqa: E402  (shared stack / rows / fit / predict)
from run_experiment import canaries                        # noqa: E402

PREREG_PATH = ROOT / "registry/preregistration_bqa.json"
PREREG = json.loads(PREREG_PATH.read_text())
BUDGET = int(PREREG["fixed_parameters"]["budget"])
OUT = ROOT / "evidence" / "bqa"
CACHE = ROOT / ".cache" / "bqa"
STATE = OUT / "state.json"
FAR_FIELD_PX = 10
FINAL_SEED = 794000


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


def require_open():
    """Fail closed if the lane is terminal or the 2 h budget is exhausted."""
    if STATE.exists():
        st = json.loads(STATE.read_text())
        if st.get("verdict") not in (None, "pending", "in_progress"):
            raise SystemExit(f"H79-BQA is closed ({st.get('verdict')}); no files changed")
    reg = datetime.fromisoformat(PREREG["registered_utc"].replace("Z", "+00:00"))
    if (datetime.now(timezone.utc) - reg).total_seconds() > 2 * 3600 + 15 * 60:
        raise SystemExit("H79-BQA two-hour budget exhausted (15 min grace for packaging only)")


def weighted_fit(X, y, seed, n_static):
    dist = bqa.distance_from_log_feature(X[:, n_static])   # log_dist_visible column
    w, rec = bqa.band_weights(dist)
    return run_nhr.fit(X, y, seed, sample_weight=w), rec


def band_map(visible, footprint):
    d = ndi.distance_transform_edt(~visible)
    band = bqa.band_of_distance(d)
    band[~footprint] = -1
    return band, d


def stage_holdout(seed):
    require_open()
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = run_nhr.Stack(grid)
    n_static = len(stack.static_names)
    assert stack.names[n_static] == "log_dist_visible"
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    quad = quadrant_ids(grid.footprint)
    geom_vis = stack.geometry(visible)

    log("canaries")

    class LazyFeatures:
        def items(self):
            fpi = np.flatnonzero(grid.footprint)
            for j, n in enumerate(stack.static_names):
                col = np.zeros(grid.footprint.size, np.float32)
                col[fpi] = np.nan_to_num(np.asarray(stack.static[:, j], np.float32), nan=-99.0)
                yield n, col.reshape(grid.shape)
            for n in nhr.GEOMETRY_NAMES:
                yield "geom_" + n, np.nan_to_num(geom_vis[n], nan=-99.0)

    c_rows = canaries(LazyFeatures(), folds, seed)
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                  worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
                  n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"] == n)
                                   for n in sorted({r["feature"] for r in c_rows})})
    log("canary max", round(canary["max_symmetric_auc"], 4), canary["worst"]["feature"])

    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    del d28
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    band_full, d_vis_full = band_map(visible, grid.footprint)
    terms, terms_ff, fold_receipts = {}, {}, []
    for fold in folds:
        q = fold["fold"]
        train_region = grid.footprint & (quad != q) & (quad >= 0)
        log(f"fold {fold['name']}: nested rows")
        X, y, rec = run_nhr.training_rows(stack, visible, train_region, seed * 100 + q)
        log(f"fold {fold['name']}: fit weighted {X.shape}")
        m_w, wrec = weighted_fit(X, y, seed * 100 + q, n_static)
        log(f"fold {fold['name']}: fit unweighted")
        m_u = run_nhr.fit(X, y, seed * 100 + q)
        del X, y
        gc.collect()
        region = fold["region"]
        allowed = region & grid.footprint & ~fold["masked_known"]
        s_w = run_nhr.predict_surface(m_w, stack, allowed, geom_vis, True)
        s_u = run_nhr.predict_surface(m_u, stack, allowed, geom_vis, True)
        del m_w, m_u
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = sy, sx
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        far = d_vis_full[sl] > FAR_FIELD_PX
        local_ff = dict(local, region=local["region"] & far)
        has_ff = bool((local_ff["region"] & local["truth"] & ~local["masked_known"]).any())
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        band_l = band_full[sl]
        placed, infos = {}, {}
        placed["candidate"], infos["candidate"] = bqa.place_with_quotas(s_w[sl], allowed[sl], band_l, budget)
        placed["nhr_repro"], infos["nhr_repro"] = place(s_u[sl], allowed[sl], budget)
        placed["quota_only"], infos["quota_only"] = bqa.place_with_quotas(s_u[sl], allowed[sl], band_l, budget)
        placed["weights_only"], infos["weights_only"] = place(s_w[sl], allowed[sl], budget)
        placed["uniform_control"], infos["uniform_control"] = place(rng_surface[sl], allowed[sl], budget)
        placed["h33_foldfair_control"] = d28_pos[sl] & region[sl] & (d_vis_full[sl] > 2)
        for name, dots in placed.items():
            p = dots.astype(np.float32)
            _, bt = evaluator.evaluate(p, local, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
            if has_ff:
                _, bf = evaluator.evaluate(p, local_ff, grid.footprint[sl],
                                           origin=(sy.start, sx.start), global_shape=grid.shape)
                terms_ff[name] = terms_ff.get(name, 0) + bf
        dist_profile = {n: [int(((band_l == b) & placed[n]).sum()) for b in range(6)] for n in placed}
        fold_receipts.append(dict(fold=fold["name"], budget=budget, nested=rec, weighting=wrec,
                                  withheld_truth=int((fold["truth"] & region).sum()),
                                  withheld_truth_far_field=int((fold["truth"] & region &
                                                                (d_vis_full > FAR_FIELD_PX)).sum()),
                                  far_field_scored=has_ff,
                                  dots_per_band=dist_profile,
                                  placement={k: {kk: vv for kk, vv in v.items() if kk != "bands_px"}
                                             for k, v in infos.items()}))
        del s_w, s_u, placed
        gc.collect()
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    summary_ff = (evaluator.pooled_summary(terms_ff, candidate="candidate", draws=1000, seed=7950 + seed)
                  if terms_ff else None)
    # Amendment A1: the same terms summarised with weights_only (X2) as the reference arm.
    summary_x2 = evaluator.pooled_summary(terms, candidate="weights_only", draws=1000, seed=7900 + seed)
    summary_x2_ff = (evaluator.pooled_summary(terms_ff, candidate="weights_only", draws=1000, seed=7950 + seed)
                     if terms_ff else None)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / f"terms_seed{seed}.npz",
                        **{f"std__{k}": v for k, v in terms.items()},
                        **{f"ff__{k}": v for k, v in terms_ff.items()})
    out = dict(schema_version=1, lane="H79-BQA", experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               preregistration_sha256=hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest(),
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time() - t0, 1), leakage_canary=canary,
               holdout_standard=summary, holdout_far_field=summary_ff,
               x2_weights_only_standard=summary_x2, x2_weights_only_far_field=summary_x2_ff,
               amendment="A1 (registry/preregistration_bqa_amendment_A1.json)",
               far_field_definition_px=FAR_FIELD_PX, folds=fold_receipts,
               h33_control_source=d28src, feature_names=stack.names,
               static_stack_inputs=stack.meta["inputs_sha256"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    for tag, s in (("standard", summary), ("far_field", summary_ff)):
        if s:
            log(tag, {k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]], v["withheld_positive_pixels"])
                      for k, v in s["scores"].items()})


def stage_surface():
    require_open()
    grid = load_grid(ROOT / "data/reference")
    stack = run_nhr.Stack(grid)
    n_static = len(stack.static_names)
    cat = grid.catalogue
    log("final: nested rows over the whole footprint")
    X, y, rec = run_nhr.training_rows(stack, cat, grid.footprint, FINAL_SEED)
    m, wrec = weighted_fit(X, y, FINAL_SEED, n_static)
    del X, y
    gc.collect()
    geom = stack.geometry(cat)
    band, _ = band_map(cat, grid.footprint)
    allowed = grid.footprint & ~cat & (band >= 0)
    surf = run_nhr.predict_surface(m, stack, allowed, geom, True)
    v = surf[allowed]
    norm = np.zeros(grid.shape, np.float32)
    norm[allowed] = ((v - v.min()) / max(float(np.ptp(v)), 1e-12)).astype(np.float32)
    norm[allowed] = np.maximum(norm[allowed], 1e-6)       # every eligible cell strictly positive
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_surface.npy", norm)
    np.save(CACHE / "final_band.npy", band)
    meta = dict(nested=rec, weighting=wrec, final_seed=FINAL_SEED,
                surface_sha256=hashlib.sha256(norm.tobytes()).hexdigest(),
                band_sha256=hashlib.sha256(band.tobytes()).hexdigest(),
                eligible_cells=int(allowed.sum()), feature_names=stack.names,
                importances_note="HGB has no native importances; none reported")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "x1_surface_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    log("surface written", meta["surface_sha256"][:12], meta["eligible_cells"])


def stage_surface_x2():
    """Amendment A1: same band-weighted final model, surface on footprint & not catalogue."""
    require_open()
    grid = load_grid(ROOT / "data/reference")
    stack = run_nhr.Stack(grid)
    n_static = len(stack.static_names)
    cat = grid.catalogue
    log("X2 final: nested rows over the whole footprint")
    X, y, rec = run_nhr.training_rows(stack, cat, grid.footprint, FINAL_SEED)
    m, wrec = weighted_fit(X, y, FINAL_SEED, n_static)
    del X, y
    gc.collect()
    geom = stack.geometry(cat)
    allowed = grid.footprint & ~cat
    surf = run_nhr.predict_surface(m, stack, allowed, geom, True)
    v = surf[allowed]
    norm = np.zeros(grid.shape, np.float32)
    norm[allowed] = ((v - v.min()) / max(float(np.ptp(v)), 1e-12)).astype(np.float32)
    norm[allowed] = np.maximum(norm[allowed], 1e-6)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "x2_final_surface.npy", norm)
    meta = dict(experiment="X2", nested=rec, weighting=wrec, final_seed=FINAL_SEED,
                surface_sha256=hashlib.sha256(norm.tobytes()).hexdigest(),
                eligible_cells=int(allowed.sum()), feature_names=stack.names)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "x2_surface_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    log("X2 surface written", meta["surface_sha256"][:12], meta["eligible_cells"])


def stage_place_x2():
    require_open()
    surf = np.load(CACHE / "x2_final_surface.npy")
    sha = hashlib.sha256(surf.tobytes()).hexdigest()
    rec_path = OUT / "x2_uniqueness_surface.json"
    if not rec_path.exists():
        raise SystemExit("X2 surface uniqueness receipt missing: run bqa_uniqueness.py surface-x2 first")
    rec = json.loads(rec_path.read_text())
    if rec.get("surface_sha256") != sha or rec.get("passed") is not True:
        raise SystemExit("X2 surface uniqueness did not pass for this exact surface; placement refused")
    grid = load_grid(ROOT / "data/reference")
    allowed = grid.footprint & ~grid.catalogue
    dots, info = place(surf, allowed, BUDGET)
    np.save(CACHE / "x2_final_dots.npy", dots)
    d = ndi.distance_transform_edt(~grid.catalogue)[dots]
    meta = dict(experiment="X2", placement=info, surface_sha256=sha,
                dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(), n_dots=int(dots.sum()),
                distance_to_catalogue_px=dict(median=float(np.median(d)), mean=float(d.mean()),
                                              fraction_gt_10px=float((d > 10).mean()),
                                              fraction_le_2px=float((d <= 2).mean())))
    (OUT / "x2_final_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    log(meta["n_dots"], info, meta["distance_to_catalogue_px"])


def stage_place():
    require_open()
    surf = np.load(CACHE / "final_surface.npy")
    band = np.load(CACHE / "final_band.npy")
    sha = hashlib.sha256(surf.tobytes()).hexdigest()
    rec_path = OUT / "uniqueness_surface.json"
    if not rec_path.exists():
        raise SystemExit("surface uniqueness receipt missing: run bqa_uniqueness.py surface first")
    rec = json.loads(rec_path.read_text())
    if rec.get("surface_sha256") != sha or rec.get("passed") is not True:
        raise SystemExit("surface uniqueness did not pass for this exact surface; placement refused")
    grid = load_grid(ROOT / "data/reference")
    allowed = grid.footprint & ~grid.catalogue & (band >= 0)
    dots, info = bqa.place_with_quotas(surf, allowed, band, BUDGET)
    np.save(CACHE / "final_dots.npy", dots)
    meta = dict(placement=info, surface_sha256=sha,
                dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(), n_dots=int(dots.sum()))
    (OUT / "x1_final_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    log(meta["n_dots"], info)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["holdout", "surface", "place", "surface-x2", "place-x2"])
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    {"holdout": lambda: stage_holdout(a.seed), "surface": stage_surface, "place": stage_place,
     "surface-x2": stage_surface_x2, "place-x2": stage_place_x2}[a.stage]()
