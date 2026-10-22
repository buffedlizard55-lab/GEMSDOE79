#!/usr/bin/env python3
"""H79-DCE experiment X1: decorrelated cover emission over the H79-NHR credit surface.

Stages
------
  surface   rebuild the nested hide-to-recover kernel-credit surface EXACTLY as
            H79-NHR X1 (same shared stack builder, same preregistered parameters
            and seeds; no retuning) and store it under .cache/dce/. The rebuilt
            surface hash is compared with the frozen X1 receipt
            (evidence/nhr/x1_final_build.json) for reproducibility only.
  atrisk    derive the capped registry set (per registry/preregistration_dce.json)
            and cache its 3 px halos.
  holdout   leave-one-quadrant-out models on nested hides (identical folds,
            rows, model and seeds as X1) scoring the preregistered arms:
            candidate (collar + tile cover + collision ceiling),
            cover_uncapped_control (collar + tile cover, no ceiling),
            topk_collar_control (X1's Poisson placement + collar),
            x1_topk_reproduction (X1's exact placement rule),
            h33_foldfair_control (promotion bar), uniform_control.
  final     capped emission on the final surface -> dots + build receipt.

All scores written here are HOLDOUT-DTI from gems57-pooled-hide-v2. Nothing is
tuned on the holdout: every parameter comes from registry/preregistration_dce.json.
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
from gems79 import nhr                                     # noqa: E402
from gems79 import dce                                     # noqa: E402
from gems79.placement import place                         # noqa: E402
import analyze_h33                                         # noqa: E402
from run_experiment import canaries                        # noqa: E402  (shared canary, reused)
import run_nhr                                             # noqa: E402  (shared X1 machinery, reused)

PREREG = json.loads((ROOT / "registry/preregistration_dce.json").read_text())
FIX = PREREG["fixed_parameters"]
BUDGET = FIX["budget"]
OUT = ROOT / "evidence" / "dce"
CACHE = ROOT / ".cache" / "dce"


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


def stage_surface():
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = run_nhr.Stack(grid)
    cat = grid.catalogue
    log("surface: nested rows over the whole footprint (X1 parameters, seed 790000)")
    X, y, rec = run_nhr.training_rows(stack, cat, grid.footprint, 790000)
    m = run_nhr.fit(X, y, 790000)
    del X, y; gc.collect()
    geom = stack.geometry(cat)
    allowed = grid.footprint & ~cat
    surf = run_nhr.predict_surface(m, stack, allowed, geom, True)
    v = surf[allowed]
    norm = np.zeros(grid.shape, np.float32)
    norm[allowed] = ((v - v.min()) / max(float(np.ptp(v)), 1e-12)).astype(np.float32)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_surface.npy", norm)
    surface_sha = hashlib.sha256(norm.tobytes()).hexdigest()
    x1 = json.loads((ROOT / "evidence/nhr/x1_final_build.json").read_text())
    meta = dict(
        lane="H79-DCE", stage="surface", evidence_class="RASTER-MEASUREMENT, NOT A SCORE",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        runtime_s=round(time.time() - t0, 1),
        nested=rec,
        surface_sha256=surface_sha,
        x1_recorded_surface_sha256=x1["surface_sha256"],
        surface_hash_matches_frozen_x1_receipt=bool(surface_sha == x1["surface_sha256"]),
        static_stack_inputs=stack.meta["inputs_sha256"],
        note=("Surface rebuilt with the identical shared stack builder, parameters and seed as "
              "H79-NHR X1; no parameter of the model or training was changed in this lane."),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "surface_build.json").write_text(json.dumps(meta, indent=2, default=float) + "\n")
    log("surface sha256", surface_sha, "matches X1:", meta["surface_hash_matches_frozen_x1_receipt"])


def stage_atrisk():
    """Freeze the capped set from a fast scan of THIS lane's uncapped emission.

    Preregistered rule (registry/preregistration_dce.json): place the uncapped
    tile-cover emission (collar included, budget 37654) on the final surface,
    scan every ordinary registry raster (uniform chance <= 0.70), and freeze as
    capped every raster whose overlap with those uncapped dots exceeds 0.50.
    This runs BEFORE the holdout so the holdout candidate arm and the final
    artifact face the identical constraint set.
    """
    t0 = time.time()
    import rasterio

    from gems57 import uniqueness as shared

    grid = load_grid(ROOT / "data/reference")
    surface = np.load(CACHE / "final_surface.npy")
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    allowed = grid.footprint & (d_cat > FIX["collar_px"])
    uncapped, unc_info = dce.place_cover(surface, allowed, BUDGET, tile_px=FIX["tile_px"])
    np.save(CACHE / "uncapped_dots.npy", uncapped)
    my_flat = np.flatnonzero(uncapped.ravel())
    log("uncapped emission placed:", int(uncapped.sum()))

    chance = json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())
    rows = [r for r in chance["rows"] if "error" not in r
            and r.get("overlap_uniform") is not None and r["overlap_uniform"] <= 0.70]
    vacuous = {r["sha256"]: r["overlap_uniform"] for r in chance["rows"]
               if "error" not in r and r.get("overlap_uniform") is not None
               and r["overlap_uniform"] > 0.70}
    overlaps = []
    for n, r in enumerate(rows):
        p = ROOT / ".cache/registry" / (r_blob(r) + ".tif")
        with rasterio.open(p) as src:
            theirs = src.read(1).astype(np.float32)
        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        theirs[~grid.footprint] = 0
        support = (theirs > 0) & grid.footprint
        if r["representation"] == "continuous_surface":
            support = shared.budget_matched_dots(theirs, grid.footprint, BUDGET)
        halo = dce.three_px_halo(support)
        ov = float(halo.ravel()[my_flat].mean())
        overlaps.append(dict(sha256=r["sha256"], submission=r["submission"],
                             chance=r["overlap_uniform"], uncapped_overlap=ov,
                             representation=r["representation"]))
        if (n + 1) % 100 == 0:
            log("atrisk scan", n + 1, "/", len(rows))
    seed_thr = FIX["atrisk_seed_threshold"]
    seed_set = [r for r in overlaps if r["uncapped_overlap"] > seed_thr]
    halos, sources = {}, []
    for r in seed_set:
        p = ROOT / ".cache/registry" / (r_blob(r) + ".tif")
        with rasterio.open(p) as src:
            theirs = src.read(1).astype(np.float32)
        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        theirs[~grid.footprint] = 0
        support = (theirs > 0) & grid.footprint
        if r["representation"] == "continuous_surface":
            support = shared.budget_matched_dots(theirs, grid.footprint, BUDGET)
        halos[r["sha256"]] = dce.pack_halo(dce.three_px_halo(support))
        sources.append(r)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE / "atrisk_halos.npz", **halos)
    top = sorted(overlaps, key=lambda r: -r["uncapped_overlap"])[:20]
    meta = dict(
        lane="H79-DCE", stage="atrisk", evidence_class="REGISTRY-MEASUREMENT",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        runtime_s=round(time.time() - t0, 1),
        collision_ceiling=FIX["collision_ceiling"], atrisk_seed_threshold=seed_thr,
        uncapped_placement=unc_info, ordinary_rasters_scanned=len(rows),
        capped_rasters=len(halos), capped_sources=sources,
        worst_uncapped_overlaps=top,
        vacuous_rasters_excluded_from_ceiling=len(vacuous),
        chance_reference="evidence/nhr/overlap_chance.json (uniform control seed 79, budget 37654)",
        note=("Capped set frozen from this lane's own uncapped emission before the holdout; "
              "the authoritative final scan may still add rasters per the preregistered "
              "fixed-point rule."),
    )
    (OUT / "atrisk_build.json").write_text(json.dumps(meta, indent=2) + "\n")
    log("capped rasters:", len(halos), "| vacuous (beyond-chance only):", len(vacuous),
        "| worst uncapped:", round(top[0]["uncapped_overlap"], 3), top[0]["submission"][:60])


_BLOB_BY_ALIAS = None


def r_blob(row):
    """Map an overlap_chance row (submission = 'repo:path' alias) to its registry blob."""
    global _BLOB_BY_ALIAS
    if _BLOB_BY_ALIAS is None:
        idx = json.loads((ROOT / "registry/registry_index.json").read_text())
        delta = json.loads((ROOT / "registry/registry_delta.json").read_text())
        by = {}
        for r in idx["rasters"]:
            for a in r.get("aliases", [r["path"]]):
                by[a] = r["blob"]
        for r in delta["rasters"]:
            for a in r.get("aliases", [r["path"]]):
                by[a] = r["blob"]
        _BLOB_BY_ALIAS = by
    sub = row["submission"]
    for key in (sub, sub.split(":", 1)[1] if ":" in sub else sub):
        if key in _BLOB_BY_ALIAS:
            return _BLOB_BY_ALIAS[key]
    raise KeyError(f"registry blob not found for {sub}")


def nhr_support_budget(theirs, footprint, k):
    from gems57 import uniqueness as shared
    return shared.budget_matched_dots(theirs, footprint, k)


def stage_holdout(seed):
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = run_nhr.Stack(grid)
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    quad = quadrant_ids(grid.footprint)
    geom_vis = stack.geometry(visible)

    # ---- leakage canaries: identical shared procedure and inputs as X1 ----
    log("canaries")
    class LazyFeatures:
        def __init__(self):
            self.names = list(stack.static_names) + ["geom_" + n for n in nhr.GEOMETRY_NAMES]
        def items(self):
            fpi = np.flatnonzero(grid.footprint)
            for j, n in enumerate(stack.static_names):
                col = np.zeros(grid.footprint.size, np.float32)
                col[fpi] = np.nan_to_num(np.asarray(stack.static[:, j], np.float32), nan=-99.0)
                yield n, col.reshape(grid.shape)
            for n in nhr.GEOMETRY_NAMES:
                yield "geom_" + n, np.nan_to_num(geom_vis[n], nan=-99.0)
    feats = LazyFeatures()
    c_rows = canaries(feats, folds, seed)
    del feats; gc.collect()
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                  worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
                  n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"] == n)
                                   for n in {r["feature"] for r in c_rows}})
    log("canary max", canary["max_symmetric_auc"], canary["worst"]["feature"])

    atrisk = dce.load_atrisk_halos()
    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    terms, fold_receipts = {}, []
    for fold in folds:
        q = fold["fold"]
        train_region = grid.footprint & (quad != q) & (quad >= 0)
        log(f"fold {fold['name']}: nested rows")
        X, y, rec = run_nhr.training_rows(stack, visible, train_region, seed * 100 + q)
        log(f"fold {fold['name']}: fit ({X.shape})")
        m_full = run_nhr.fit(X, y, seed * 100 + q)
        del X, y; gc.collect()
        region = fold["region"]
        allowed_x1 = region & grid.footprint & ~fold["masked_known"]
        s_full = run_nhr.predict_surface(m_full, stack, allowed_x1, geom_vis, True)
        del m_full; gc.collect()
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = sy, sx
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        # Emission surface for every surface arm: the raw full-grid fold
        # prediction s_full — exactly the surface form the H79-NHR X1 holdout
        # used (its reproduction arm reproduces the frozen X1 numbers), with no
        # per-fold normalisation or outside-mask zeroing. The final artifact is
        # placed from the hash-pinned X1 surface artifact (final_surface.npy),
        # exactly as X1's own final placement was; the fold/final surface-form
        # symmetry therefore matches the X1 template this lane reuses.
        d_vis = ndi.distance_transform_edt(~fold["visible"])
        collar_full = grid.footprint & (d_vis > FIX["collar_px"])
        allowed_cce = region & collar_full & ~fold["masked_known"]
        arms = {}
        cand_dots, cand_info = dce.place_capped(s_full, allowed_cce, budget, atrisk,
                                                ceiling=FIX["collision_ceiling"])
        arms["candidate"] = cand_dots
        unc_dots, unc_info = dce.place_cover(s_full, allowed_cce, budget)
        arms["cover_uncapped_control"] = unc_dots
        tk_dots, tk_info = place(s_full, allowed_cce, budget)
        arms["topk_collar_control"] = tk_dots
        x1_dots, x1_info = place(s_full, allowed_x1, budget)
        arms["x1_topk_reproduction"] = x1_dots
        arms["uniform_control"] = rng_surface
        placements = dict(candidate=cand_info, cover_uncapped_control=unc_info,
                          topk_collar_control=tk_info, x1_topk_reproduction=x1_info)
        for name, surf in arms.items():
            _, bt = evaluator.evaluate(surf[sl].astype(np.float32), local, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
        h33_ff = (d28_pos[sl] & region[sl] & (d_vis[sl] > 2)).astype(np.float32)
        _, bt = evaluator.evaluate(h33_ff, local, grid.footprint[sl],
                                   origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt
        fold_receipts.append(dict(fold=fold["name"], budget=budget, nested=rec,
                                  placements=placements,
                                  withheld_truth=int((fold["truth"] & region).sum())))
        del s_full; gc.collect()
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    out = dict(schema_version=1, lane="H79-DCE", experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time() - t0, 1), leakage_canary=canary,
               holdout=summary, folds=fold_receipts,
               h33_control_source=d28src, feature_names=stack.names,
               static_stack_inputs=stack.meta["inputs_sha256"],
               arms=list(terms.keys()))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"dce_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    s = summary["scores"]
    log({k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in s.items()})


def stage_final():
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    surface = np.load(CACHE / "final_surface.npy")
    atrisk = dce.load_atrisk_halos()
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    allowed = grid.footprint & (d_cat > FIX["collar_px"])
    dots, info = dce.place_capped(surface, allowed, BUDGET, atrisk,
                                  ceiling=FIX["collision_ceiling"])
    np.save(CACHE / "final_dots.npy", dots)
    meta = dict(
        lane="H79-DCE", stage="final", evidence_class="RASTER-MEASUREMENT, NOT A SCORE",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        runtime_s=round(time.time() - t0, 1),
        placement=info, n_dots=int(dots.sum()),
        dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
        surface_sha256=hashlib.sha256(surface.tobytes()).hexdigest(),
        capped_rasters=len(atrisk),
        note="Capped tile-cover emission; see registry/preregistration_dce.json.")
    (OUT / "final_build.json").write_text(json.dumps(meta, indent=2, default=float) + "\n")
    log(meta["n_dots"], info)


STAGES = dict(surface=stage_surface, atrisk=stage_atrisk,
              holdout=stage_holdout, final=stage_final)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=sorted(STAGES))
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    STAGES[a.stage](seed=a.seed) if a.stage == "holdout" else STAGES[a.stage]()
