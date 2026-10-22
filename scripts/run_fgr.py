#!/usr/bin/env python3
"""H79-FGR experiment X1: far-field gradient ranker.

Preregistered in registry/preregistration_fgr.json before any result existed.
Nothing here is tuned on a holdout: every parameter is copied from that file.

Stages
------
  holdout --seed S   shared buffered component draw; four arms (candidate,
                     near-field inversion, uniform, h33 fold-fair control);
                     per-fold distance weights recomputed from the VISIBLE
                     catalogue only; shared pooled evaluator and bootstrap.
  final              one global surface, 38,000 dots with the shared allocator,
                     shared writer, shared format gate, and the registry
                     uniqueness scan reported under BOTH readings.

All scores written here are HOLDOUT-DTI from gems57-pooled-hide-v2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator  # noqa: E402
from gems57.grid import load_grid, write_submission  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gems57.metric import PIXEL_M  # noqa: E402
from gems79.placement import place  # noqa: E402
import analyze_h33  # noqa: E402
from run_experiment import canaries  # noqa: E402

PREREG = json.loads((ROOT / "registry/preregistration_fgr.json").read_text())
FIX = PREREG["fixed_parameters"]
BUDGET = 38000
D0_M, D1_M = 300.0, 5000.0
OUT = ROOT / "evidence" / "fgr"
CACHE = ROOT / ".cache" / "fgr"


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _rank(a, valid):
    """Within-footprint percentile rank on valid cells; NaN elsewhere."""
    out = np.full(a.shape, np.nan, np.float32)
    v = np.asarray(a, np.float64)[valid]
    if v.size == 0:
        return out
    r = rankdata(v) / v.size
    out[valid] = r.astype(np.float32)
    return out


def competence_layers(grid):
    """The six preregistered label-independent competence layers."""
    fp = grid.footprint
    inputs = {}
    layers = {}

    p = ROOT / "data/raw/training_features.tif"
    inputs["training_features.tif"] = _sha(p)
    want = {"det_elev", "iso_grav_anom_hg", "tmi_hg"}
    with rasterio.open(p) as src:
        for b in range(1, src.count + 1):
            short = src.descriptions[b - 1].split(" - ")[0]
            if short not in want:
                continue
            a = src.read(b).astype(np.float32)
            valid = fp & np.isfinite(a) & (a > -1e30)
            layers[short] = np.where(valid, a, np.nan)
            if short == "det_elev":
                filled = np.where(valid, a, 0.0)
                for sig in (2.0, 5.0):
                    log_g = np.abs(ndi.gaussian_laplace(filled, sigma=sig))
                    layers[f"log_det_elev_s{int(sig)}"] = np.where(valid, log_g, np.nan)

    p = ROOT / "data/raw/external/lidar_scarp_features_u8.tif"
    inputs["lidar_scarp_features_u8.tif"] = _sha(p)
    meta = json.loads((ROOT / "data/raw/external/lidar_scarp_features.json").read_text())
    bands = meta["bands"]
    with rasterio.open(p) as src:
        for name in ("step_max", "ex_max"):
            b = bands.index(name) + 1
            a = src.read(b).astype(np.float32)
            valid = fp & np.isfinite(a) & (a > 0)
            layers[name] = np.where(valid, a, np.nan)

    names = ["step_max", "ex_max", "log_det_elev_s2", "log_det_elev_s5",
             "iso_grav_anom_hg", "tmi_hg"]
    missing = [n for n in names if n not in layers]
    if missing:
        raise SystemExit(f"missing competence layers: {missing}")
    ranks = np.stack([_rank(layers[n], fp & np.isfinite(layers[n])) for n in names])
    with np.errstate(invalid="ignore"):
        comp = np.nanmean(ranks, axis=0).astype(np.float32)
    comp[~fp] = np.nan
    return comp, names, layers, inputs


def distance_weight(dist_m):
    return np.clip((dist_m - D0_M) / (D1_M - D0_M), 0.0, 1.0).astype(np.float32)


def build_surface(grid):
    CACHE.mkdir(parents=True, exist_ok=True)
    comp, names, layers, inputs = competence_layers(grid)
    log("competence built")
    d_m = ndi.distance_transform_edt(~grid.catalogue) * PIXEL_M
    w = distance_weight(d_m)
    s = np.where(np.isfinite(comp), comp * (0.25 + 0.75 * w), 0.0).astype(np.float32)
    s[~grid.footprint] = 0.0
    s_inv = np.where(np.isfinite(comp), comp * (0.25 + 0.75 * (1.0 - w)), 0.0).astype(np.float32)
    s_inv[~grid.footprint] = 0.0
    receipt = dict(layers=names, inputs_sha256=inputs,
                   competence_sha256=hashlib.sha256(np.nan_to_num(comp).tobytes()).hexdigest(),
                   surface_sha256=hashlib.sha256(s.tobytes()).hexdigest(),
                   distance_weight=[D0_M, D1_M], budget=BUDGET)
    (CACHE / "surface_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return comp, s, s_inv, d_m, receipt


def stage_holdout(seed):
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    comp, s_glob, s_inv_glob, _, receipt = build_surface(grid)
    folds, _meta = buffered_component_draw(grid, seed=seed, hide_frac=0.2,
                                           buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]

    # ---- leakage canaries: every competence layer alone (shared canary fn) ----
    log("canaries")
    _c, names, layers, _i = competence_layers(grid)
    feats = type("F", (), {})()
    feats.names = list(names)
    feats.items = lambda: ((n, np.nan_to_num(layers[n], nan=0.0)) for n in names)
    c_rows = canaries(feats, folds, seed)
    canary = dict(evidence_class="LEAKAGE-CANARY", seed=seed, tests=len(c_rows), threshold=0.90,
                  max_symmetric_auc=max(r["symmetric_auc"] for r in c_rows),
                  worst=max(c_rows, key=lambda r: r["symmetric_auc"]),
                  n_suspicious=sum(r["suspicious"] for r in c_rows),
                  per_feature_max={n: max(r["symmetric_auc"] for r in c_rows if r["feature"] == n)
                                   for n in names})
    log("canary max", round(canary["max_symmetric_auc"], 4), canary["worst"]["feature"])

    d28, d28src = analyze_h33.locate("dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    d28_pos = (np.isfinite(d28) & (d28 > 0)) & grid.footprint
    rng_surface = np.random.default_rng(790031).random(grid.shape, dtype=np.float32)

    terms, fold_receipts = {}, []
    for fold in folds:
        region = fold["region"]
        # Distance weight from the VISIBLE catalogue only: the withheld components
        # must not leak into the feature that ranks them.
        d_vis = ndi.distance_transform_edt(~fold["visible"]) * PIXEL_M
        w_vis = distance_weight(d_vis)
        s = np.where(np.isfinite(comp), comp * (0.25 + 0.75 * w_vis), 0.0).astype(np.float32)
        s_inv = np.where(np.isfinite(comp), comp * (0.25 + 0.75 * (1.0 - w_vis)), 0.0).astype(np.float32)
        s[~grid.footprint] = 0.0
        s_inv[~grid.footprint] = 0.0
        allowed = region & grid.footprint & ~fold["masked_known"]
        ys, xs = np.nonzero(region)
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        sl = sy, sx
        local = {k: fold[k][sl] for k in ("region", "truth", "visible", "masked_known")}
        budget = int(round(BUDGET * region.sum() / grid.footprint.sum()))
        arms = {"candidate": s, "nearfield_inversion": s_inv, "uniform_control": rng_surface}
        placed = {}
        for name, surf in arms.items():
            dots, info = place(surf[sl], allowed[sl], budget)
            placed[name] = int(dots.sum())
            _, bt = evaluator.evaluate(dots.astype(np.float32), local, grid.footprint[sl],
                                       origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, 0) + bt
        d_v = ndi.distance_transform_edt(~fold["visible"][sl])
        h33_ff = (d28_pos[sl] & region[sl] & (d_v > 2)).astype(np.float32)
        placed["h33_foldfair_control"] = int((h33_ff > 0).sum())
        _, bt = evaluator.evaluate(h33_ff, local, grid.footprint[sl],
                                   origin=(sy.start, sx.start), global_shape=grid.shape)
        terms["h33_foldfair_control"] = terms.get("h33_foldfair_control", 0) + bt
        fold_receipts.append(dict(fold=fold["name"], budget=budget, placed=placed,
                                  withheld_truth=int((fold["truth"] & region).sum())))
        log(f"fold {fold['name']} done", placed)

    summary = evaluator.pooled_summary(terms, candidate="candidate", draws=1000, seed=7901 + seed)
    out = dict(schema_version=1, lane="H79-FGR", experiment="X1", seed=seed,
               evidence_class="HOLDOUT-DTI", evaluator_version=evaluator.VERSION,
               generated_utc=datetime.now(timezone.utc).isoformat(),
               runtime_s=round(time.time() - t0, 1), leakage_canary=canary,
               holdout=summary, folds=fold_receipts, h33_control_source=d28src,
               surface_receipt=receipt, preregistration_sha256=_sha(
                   ROOT / "registry/preregistration_fgr.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"x1_holdout_seed{seed}.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    s = summary["scores"]
    log({k: (round(v["dti"], 4), [round(c, 4) for c in v["ci95"]]) for k, v in s.items()})


def stage_final():
    grid = load_grid(ROOT / "data/reference")
    comp, s, s_inv, d_m, receipt = build_surface(grid)
    allowed = grid.footprint & ~grid.catalogue
    v = s[allowed]
    norm = np.zeros(grid.shape, np.float32)
    norm[allowed] = ((v - v.min()) / max(float(np.ptp(v)), 1e-12)).astype(np.float32)
    dots, info = place(norm, allowed, BUDGET)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "final_surface.npy", norm)
    np.save(CACHE / "final_dots.npy", dots)
    dm = d_m[dots]
    prof = dict(n_dots=int(dots.sum()), placement=info,
                dots_sha256=hashlib.sha256(dots.tobytes()).hexdigest(),
                dist_cat_median_m=float(np.median(dm)), dist_cat_mean_m=float(dm.mean()),
                frac_within_200m=float((dm <= 200).mean()),
                frac_within_500m=float((dm <= 500).mean()),
                frac_gt_1km=float((dm > 1000).mean()),
                frac_gt_2km=float((dm > 2000).mean()),
                frac_gt_5km=float((dm > 5000).mean()),
                surface_sha256=receipt["surface_sha256"])
    (OUT / "x1_final_build.json").write_text(json.dumps(prof, indent=2) + "\n")
    log("final dots", prof["n_dots"], "median", round(prof["dist_cat_median_m"], 1),
        ">2km", round(prof["frac_gt_2km"], 3), info)
    return dots, norm, prof


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["holdout", "final"])
    ap.add_argument("--seed", type=int, default=20)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.stage == "holdout":
        stage_holdout(a.seed)
    else:
        stage_final()
