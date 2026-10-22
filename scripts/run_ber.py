#!/usr/bin/env python3
"""G79-BER experiment X1 (registry/preregistration_ber.json).

Stages (sequencing is a gate, not a suggestion):

  features            build/verify cached static + new feature stacks
  holdout --seed S    leakage canaries, then LOQO per-band models on nested
                      hides; candidate / h33-fold-fair / uniform / banded-
                      uniform arms through the shared pooled evaluator
  final               per-band models on nested hides of the full catalogue;
                      band surfaces + combined rank surface + provisional
                      top-quota dots are cached (NO placement yet)
  uniqueness surface  amendment D-2 gate on the surface + provisional dots.
                      Placement refuses to run unless this passed.
  place               per-band quotas under one global 3 px spacing mask
  uniqueness final    amendment D-2 gate on the placed dots

All scores are HOLDOUT-DTI from gems57-pooled-hide-v2.  Nothing is tuned on
the holdout or the registry: every parameter comes from the preregistration.
This runner refuses all mutating stages once run_card_ber.json exists (the
lane's terminal card), so a stopped lane cannot be silently restarted.
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
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator          # noqa: E402
from gems57 import metric                                  # noqa: E402
from gems57 import uniqueness as shared                    # noqa: E402
from gems57.grid import load_grid                          # noqa: E402
from gems57.holdout import buffered_component_draw, quadrant_ids  # noqa: E402
from gems79 import ber, nhr                                # noqa: E402
from gems79.placement import place, place_banded           # noqa: E402
import analyze_h33                                         # noqa: E402
from run_experiment import canaries                        # noqa: E402
from nhr_uniqueness import inventory                       # noqa: E402

PREREG = json.loads((ROOT / "registry/preregistration_ber.json").read_text())
FIX = PREREG["fixed_parameters"]
BUDGET = int(FIX["budget"])
OUT = ROOT / "evidence" / "ber"
CACHE = ROOT / ".cache" / "ber"
CARD = ROOT / "run_card_ber.json"
MIN_BAND_POSITIVES = 3000


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


def require_lane_open():
    if CARD.exists():
        raise SystemExit("G79-BER: terminal run card exists; lane is closed. "
                         "Do not restart, retune or repackage it. No files changed.")


class Stack:
    """Cached static + new footprint-row matrices + visible-catalogue geometry."""

    def __init__(self, grid):
        self.grid = grid
        self.static, self.static_names, self.meta = nhr.build_static_stack(grid.footprint)
        self.new, self.new_names, self.new_meta = ber.build_new_stack(grid.footprint)
        self.row_of = np.full(grid.footprint.size, -1, np.int64)
        fpi = np.flatnonzero(grid.footprint)
        self.row_of[fpi] = np.arange(fpi.size)
        self.lstrike, self.lcoh = nhr.read_lidar_orientation(grid.footprint)

    def geometry(self, visible):
        return nhr.geometry_features(visible, self.grid.footprint, self.lstrike, self.lcoh)

    @property
    def names(self):
        return list(self.static_names) + list(self.new_names) + list(ber.GEOMETRY_NAMES_BER)

    def rows(self, flat_idx, geom):
        r = self.row_of[flat_idx]
        st = np.asarray(self.static[r], np.float32)
        nw = np.asarray(self.new[r], np.float32)
        g = np.stack([geom[n].ravel()[flat_idx] for n in ber.GEOMETRY_NAMES_BER], axis=1)
        return np.concatenate([st, nw, g], axis=1)


def training_rows_banded(stack, context, region, seed):
    """Nested hide-and-recover rows with per-row distance band (visible-only)."""
    rng = np.random.default_rng(seed)
    fp = stack.grid.footprint
    X, y, b = [], [], []
    receipts = []
    for rep in range(FIX["nested_replicates_per_model"]):
        hidden, remaining = nhr.nested_hide(context, region, rng,
                                            FIX["nested_hide_fraction"],
                                            FIX["nested_buffer_px"])
        t = nhr.kernel_target(hidden)
        geom = stack.geometry(remaining)
        dist = ndi.distance_transform_edt(~remaining)
        bands = ber.band_ids(dist)
        base = region & fp & ~context & (bands >= 0)
        pos = np.flatnonzero(base & (t > 0))
        neg_pool = np.flatnonzero(base & (t == 0))
        neg = rng.choice(neg_pool, min(FIX["negatives_sampled_per_replicate"], neg_pool.size),
                         replace=False)
        idx = np.concatenate([pos, neg])
        X.append(stack.rows(idx, geom))
        y.append(t.ravel()[idx])
        b.append(bands.ravel()[idx].astype(np.int16))
        receipts.append(dict(replicate=rep, hidden_pixels=int(hidden.sum()),
                             positive_rows=int(pos.size), negative_rows=int(neg.size),
                             positives_per_band=[int((bands.ravel()[pos] == k).sum())
                                                 for k in range(len(ber.BANDS_PX))]))
        del geom, t, hidden, remaining, dist, bands
        gc.collect()
    return np.concatenate(X), np.concatenate(y), np.concatenate(b), receipts


def fit_band_models(X, y, bands, seed):
    """One HGB per band; preregistered merge-with-neighbour fallback."""
    models, merges = {}, {}
    pos_per_band = [int(((bands == k) & (y > 0)).sum()) for k in range(len(ber.BANDS_PX))]
    for k in range(len(ber.BANDS_PX)):
        train_bands = [k]
        if pos_per_band[k] < MIN_BAND_POSITIVES:
            neighbour = k - 1 if k > 0 else k + 1
            train_bands = sorted({k, neighbour})
            merges[k] = train_bands
        sel = np.isin(bands, train_bands)
        if sel.sum() == 0 or int((y[sel] > 0).sum()) == 0:
            models[k] = None
            merges[k] = merges.get(k, train_bands) + ["no_rows_constant_zero"]
            continue
        m = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=63,
                                          min_samples_leaf=200, l2_regularization=1.0,
                                          random_state=seed * 10 + k, early_stopping=False)
        m.fit(X[sel], y[sel])
        models[k] = m
    return models, dict(positive_rows_per_band=pos_per_band, merges={str(k): v for k, v in merges.items()})


def predict_band_surfaces(models, stack, allowed, band_id, geom, bbox=None, chunk=300_000):
    """Per-band predicted surfaces (full grid, or cropped to ``bbox`` slices)."""
    shape = allowed.shape
    if bbox is None:
        bbox = (slice(None), slice(None))
        oy = ox = 0
    else:
        oy, ox = int(bbox[0].start or 0), int(bbox[1].start or 0)
    crop_shape = allowed[bbox].shape
    width = shape[1]
    surfaces = []
    for k in range(len(ber.BANDS_PX)):
        surf = np.zeros(crop_shape, np.float32)
        cells = allowed[bbox] & (band_id[bbox] == k)
        cy, cx = np.nonzero(cells)
        if cy.size:
            flat_idx = (cy + oy) * width + (cx + ox)
            model = models.get(k)
            if model is None:
                surf[cy, cx] = np.float32(1e-6)
            else:
                pred = np.empty(cy.size, np.float32)
                for s in range(0, cy.size, chunk):
                    pred[s:s + chunk] = model.predict(stack.rows(flat_idx[s:s + chunk], geom))
                lo = float(pred.min())
                if lo <= 0:
                    pred = pred - lo + np.float32(1e-6)
                surf[cy, cx] = pred
                del pred
        surfaces.append(surf)
    return surfaces


def stage_features():
    require_lane_open()
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    receipt = dict(lane="G79-BER", static_names=list(stack.static_names),
                   new_names=list(stack.new_names),
                   geometry_names=list(ber.GEOMETRY_NAMES_BER),
                   n_features=len(stack.names),
                   static_inputs_sha256=stack.meta["inputs_sha256"],
                   new_inputs_sha256=stack.new_meta["inputs_sha256"],
                   new_stack_meta={k: v for k, v in stack.new_meta.items() if k != "names"})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "feature_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    log("features:", receipt["n_features"], "static", len(stack.static_names),
        "new", len(stack.new_names))
    return receipt


def stage_holdout(seed):
    require_lane_open()
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    quad = quadrant_ids(grid.footprint)
    geom_vis = stack.geometry(visible)
    dist_vis = ndi.distance_transform_edt(~visible)
    band_vis = ber.band_ids(dist_vis)

    # ---- leakage canaries: every input feature alone, BEFORE any score ----
    log("canaries")
    class LazyFeatures:
        def __init__(self):
            self.names = list(stack.names)

        def items(self):
            fpi = np.flatnonzero(grid.footprint)
            for mat, names, base in ((stack.static, stack.static_names, 0),
                                     (stack.new, stack.new_names, 0)):
                for j, n in enumerate(names):
                    col = np.zeros(grid.footprint.size, np.float32)
                    col[fpi] = np.nan_to_num(np.asarray(mat[:, j], np.float32), nan=-99.0)
                    yield n, col.reshape(grid.shape)
                    del col
            for n in ber.GEOMETRY_NAMES_BER:
                yield "geom_" + n, np.nan_to_num(geom_vis[n], nan=-99.0)
    feats = LazyFeatures()
    c_rows = canaries(feats, folds, seed)
    del feats
    gc.collect()
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                  worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
                  n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"] == n)
                                   for n in {r["feature"] for r in c_rows}})
    log("canary max", canary["max_symmetric_auc"], canary["worst"]["feature"])
    if canary["n_suspicious"]:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"x1_canary_stop_seed{seed}.json").write_text(json.dumps(
            dict(leakage_canary=canary, stop="canary > 0.90: leakage until proven otherwise"),
            indent=2, default=float) + "\n")
        raise SystemExit(f"LEAKAGE CANARY STOP seed {seed}: see evidence/ber/x1_canary_stop_seed{seed}.json")

    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = np.isfinite(d28) & (d28 > 0) & grid.footprint
    del d28
    rng_surface = np.random.default_rng(790021).random(grid.shape, dtype=np.float32)
    terms, fold_receipts = {}, []
    stratified = {arm: dict(credit=[0.0] * 5, n=[0] * 5) for arm in ("candidate", "h33_foldfair_control")}
    for fold in folds:
        q = fold["fold"]
        train_region = grid.footprint & (quad != q) & (quad >= 0)
        log(f"fold {fold['name']}: banded nested rows")
        X, y, brow, rec = training_rows_banded(stack, visible, train_region, seed * 100 + q)
        log(f"fold {fold['name']}: fit band models ({X.shape})")
        models, fit_info = fit_band_models(X, y, brow, seed * 100 + q)
        del X, y, brow
        gc.collect()
        region = fold["region"]
        allowed = region & grid.footprint & ~fold["masked_known"] & (band_vis >= 0)
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = (sy, sx)
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        budget = int(round(BUDGET * int(region.sum()) / int(grid.footprint.sum())))
        counts = [int((allowed & (band_vis == k)).sum()) for k in range(len(ber.BANDS_PX))]
        quotas = ber.largest_remainder(budget, counts)
        band_surfaces = predict_band_surfaces(models, stack, allowed, band_vis, geom_vis, bbox=sl)
        band_allowed = [(allowed[sl] & (band_vis[sl] == k)) for k in range(len(ber.BANDS_PX))]
        cand_dots, placed_info = place_banded(band_surfaces, band_allowed, quotas)
        del band_surfaces, models
        uni_dots, _ = place(rng_surface[sl], allowed[sl], budget)
        band_uni_dots, _ = place_banded([rng_surface[sl]] * len(quotas), band_allowed, quotas)
        d_vis_crop = dist_vis[sl]
        h33_dots = (d28_pos[sl] & region[sl] & (d_vis_crop > 2))
        arms = {"candidate": cand_dots, "uniform_control": uni_dots,
                "banded_uniform_control": band_uni_dots,
                "h33_foldfair_control": h33_dots.astype(bool)}
        for name, dots in arms.items():
            _, bt = evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
            if name in stratified:
                credit, _, _ = metric.max_cover(dots.astype(np.float32), local["truth"])
                tb = band_vis[sl][local["truth"]]
                for k in range(len(ber.BANDS_PX)):
                    m = tb == k
                    stratified[name]["credit"][k] += float(credit[m].sum())
                    stratified[name]["n"][k] += int(m.sum())
                del credit
        fold_receipts.append(dict(fold=fold["name"], budget=budget,
                                  allowed_per_band=counts, quotas=quotas,
                                  placed_per_band=[i["emitted"] for i in placed_info],
                                  fit=fit_info, nested=rec,
                                  withheld_truth=int((fold["truth"] & region).sum())))
        del cand_dots, uni_dots, band_uni_dots, h33_dots, band_allowed
        gc.collect()
        log(f"fold {fold['name']} done")
    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7900 + seed)
    out = dict(schema_version=1, lane="G79-BER", experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time() - t0, 1), leakage_canary=canary,
               holdout=summary, folds=fold_receipts,
               stratified_kernel_credit_by_truth_band={
                   arm: dict(bands_px=[list(map(lambda v: v, b)) for b in ber.BANDS_PX],
                             credit=v["credit"], truth_pixels=v["n"],
                             credit_per_truth_pixel=[(c / n if n else None)
                                                     for c, n in zip(v["credit"], v["n"])])
                   for arm, v in stratified.items()},
               h33_control_source=d28src, feature_names=stack.names,
               static_stack_inputs=stack.meta["inputs_sha256"],
               new_stack_inputs=stack.new_meta["inputs_sha256"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"x1_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    s = summary["scores"]
    log({k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in s.items()})


def stage_final():
    require_lane_open()
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    stack = Stack(grid)
    cat = grid.catalogue
    log("final: banded nested rows over the whole footprint")
    X, y, brow, rec = training_rows_banded(stack, cat, grid.footprint, 790000)
    models, fit_info = fit_band_models(X, y, brow, 790000)
    del X, y, brow
    gc.collect()
    geom = stack.geometry(cat)
    dist = ndi.distance_transform_edt(~cat)
    band_id = ber.band_ids(dist)
    allowed = grid.footprint & ~cat & (band_id >= 0)
    counts = [int((allowed & (band_id == k)).sum()) for k in range(len(ber.BANDS_PX))]
    quotas = ber.largest_remainder(BUDGET, counts)
    band_surfaces = predict_band_surfaces(models, stack, allowed, band_id, geom)
    rank_surface = ber.within_band_ranks(band_surfaces, band_id, allowed)
    provisional = ber.provisional_topk(rank_surface, band_id, allowed, quotas)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_band_surfaces.npy", np.stack(band_surfaces).astype(np.float32))
    np.save(CACHE / "final_rank_surface.npy", rank_surface)
    np.save(CACHE / "provisional_dots.npy", provisional)
    meta = dict(nested=rec, fit=fit_info, allowed_per_band=counts, quotas=quotas,
                allowed_cells=int(allowed.sum()),
                rank_surface_sha256=hashlib.sha256(rank_surface.tobytes()).hexdigest(),
                provisional_dots_sha256=hashlib.sha256(provisional.tobytes()).hexdigest(),
                provisional_dots=int(provisional.sum()),
                feature_names=stack.names, runtime_s=round(time.time() - t0, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "x1_final_surface.json").write_text(json.dumps(meta, indent=2) + "\n")
    log("final surface cached; quotas", quotas, "provisional", meta["provisional_dots"])


def _allowed_final(grid):
    dist = ndi.distance_transform_edt(~grid.catalogue)
    band_id = ber.band_ids(dist)
    allowed = grid.footprint & ~grid.catalogue & (band_id >= 0)
    return allowed, band_id, dist


def stage_uniqueness(phase):
    require_lane_open()
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    allowed, _, _ = _allowed_final(grid)
    inv, expected = inventory()
    eg = (grid.shape, grid.crs, grid.transform)
    if phase == "surface":
        dots = np.load(CACHE / "provisional_dots.npy")
        surface = np.load(CACHE / "final_rank_surface.npy")
    else:
        dots = np.load(CACHE / "final_dots.npy")
        surface = None
    def prog(i, n, row):
        if i % 100 == 0 or i == n:
            log(f"uniqueness {phase} {i}/{n}")
    res = shared.compare_array_to_registry_d2(dots, inv, grid.footprint, allowed,
                                              candidate_surface=surface, expected_grid=eg,
                                              progress=prog)
    out = dict(schema_version=1, lane="G79-BER", phase=phase,
               evidence_class="REGISTRY-MEASUREMENT",
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time() - t0, 1),
               shared_tool="gems57.uniqueness.compare_array_to_registry_d2",
               shared_tool_sha256=hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
               registry_rasters_expected=expected,
               dots_sha256=hashlib.sha256(np.ascontiguousarray(dots).tobytes()).hexdigest(),
               rank_surface=(phase == "surface"),
               result=res)
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2, default=float).replace(str(ROOT) + "/", "")
    (OUT / f"uniqueness_{phase}.json").write_text(text + "\n")
    log(json.dumps({k: res[k] for k in ("unique_under_D2", "complete_accessible_scan",
                                         "worst_spearman_full_footprint",
                                         "worst_chance_corrected_overlap",
                                         "worst_literal_forward_overlap",
                                         "duplicate_count_d2")}, indent=2))


def stage_place():
    require_lane_open()
    gate_path = OUT / "uniqueness_surface.json"
    if not gate_path.exists():
        raise SystemExit("REFUSED: surface uniqueness gate has not run. "
                         "Run `uniqueness surface` first (protocol: check the surface before placement).")
    gate = json.loads(gate_path.read_text())
    res = gate.get("result", {})
    if not (res.get("unique_under_D2") is True and res.get("complete_accessible_scan") is True):
        raise SystemExit("REFUSED: surface failed the amendment D-2 uniqueness gate "
                         "(or the scan is incomplete). Lane stops before placement; "
                         "no capping, jitter or retuning. See evidence/ber/uniqueness_surface.json")
    grid = load_grid(ROOT / "data/reference")
    allowed, band_id, _ = _allowed_final(grid)
    build = json.loads((OUT / "x1_final_surface.json").read_text())
    quotas = build["quotas"]
    band_surfaces = list(np.load(CACHE / "final_band_surfaces.npy"))
    band_allowed = [(allowed & (band_id == k)) for k in range(len(ber.BANDS_PX))]
    dots, infos = place_banded(band_surfaces, band_allowed, quotas)
    np.save(CACHE / "final_dots.npy", dots)
    meta = dict(placement_per_band=infos, quotas=quotas,
                dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
                n_dots=int(dots.sum()),
                surface_gate="evidence/ber/uniqueness_surface.json: unique_under_D2=true")
    (OUT / "x1_placement.json").write_text(json.dumps(meta, indent=2) + "\n")
    log(meta)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["features", "holdout", "final", "uniqueness", "place"])
    ap.add_argument("phase", nargs="?", choices=["surface", "final"])
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    if a.stage == "features":
        stage_features()
    elif a.stage == "holdout":
        stage_holdout(a.seed)
    elif a.stage == "final":
        stage_final()
    elif a.stage == "uniqueness":
        if not a.phase:
            raise SystemExit("uniqueness requires phase surface|final")
        stage_uniqueness(a.phase)
    else:
        stage_place()
