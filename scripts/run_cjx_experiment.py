#!/usr/bin/env python3
"""G79-CJX experiment 1-2: canary AUCs + pooled HOLDOUT-DTI (gems57-pooled-hide-v2).

Catalogue-free surface; dots emitted per seed from the *visible*-catalogue
allowance (>2 px) exactly as in run_g79_thvc.py, budget 37,654, sep 2.8 px.
Controls on identical folds: uniform random (same budget) — H33 fold-fair and
G79-THVC numbers are quoted from frozen receipts, never recomputed here.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
import rasterio
from gems57.grid import load_grid
from gems57 import evaluate_holdout, holdout
from gems79.cjx import build_cjx
from gems79.lifecycle import enforce_open_lane
from gems79.thvc_model import poisson_disk_emit

OUT = ROOT / "evidence" / "cjx"
BUDGET = 37_654


def sym_auc(scores, y):
    from sklearn.metrics import roc_auc_score
    a = roc_auc_score(y, scores)
    return float(max(a, 1 - a)), float(a)


def main():
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    footprint, catalogue = grid.footprint, grid.catalogue
    with rasterio.open(ROOT / "data/raw/training_features.tif") as ds:
        bands = {"rtp": ds.read(2).astype(np.float32),
                 "iso_grav_anom": ds.read(13).astype(np.float32)}
    print("building CJX channels...", flush=True)
    ch = build_cjx(bands, footprint)
    np.savez_compressed(OUT / "cjx_surface.npz",
                        **{k: v.astype(np.float16) for k, v in ch.items()})
    print(f"channels built {time.time()-t0:.0f}s", flush=True)

    arms_surface = {"CJX_v1_edge": ch["cjx_v1_edge"], "CJX_v2_junction": ch["cjx_v2_junction"]}
    canary_names = ["pers_rtp", "pers_grav", "coincidence", "concordance",
                    "discord_max", "cjx_v1_edge", "cjx_v2_junction"]
    results = {"lane": "G79-CJX", "evaluator_version": evaluate_holdout.VERSION,
               "evidence_class": "HOLDOUT-DTI", "budget": BUDGET, "seeds": {}}
    for seed in (20, 30):
        folds, quad = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        visible = folds[0]["visible"]
        allow = footprint & (ndi.distance_transform_edt(~visible) > 2.0)
        hidden_all = folds[0]["hidden_all"]
        # ---- leakage canary: each channel alone, withheld vs active negatives
        rng = np.random.default_rng(seed)
        pos_idx = np.flatnonzero((hidden_all & footprint).ravel())
        neg_pool = np.flatnonzero((footprint & ~catalogue).ravel())
        neg_idx = rng.choice(neg_pool, size=min(60000, len(neg_pool)), replace=False)
        canaries = {}
        for name in canary_names:
            flat = ch[name].ravel()
            s = np.concatenate([flat[pos_idx], flat[neg_idx]])
            y = np.r_[np.ones(len(pos_idx)), np.zeros(len(neg_idx))]
            s_, raw = sym_auc(s, y)
            canaries[name] = {"symmetric_auc": s_, "raw_auc": raw,
                              "n_withheld_positive_pixels_sampled": int(len(pos_idx))}
        # ---- dot emission + pooled DTI
        preds = {}
        for arm, surf in arms_surface.items():
            preds[arm] = poisson_disk_emit(surf, allow, budget=BUDGET, min_dist_px=2.8)
        flat_allow = np.flatnonzero(allow)
        rnd = np.zeros(footprint.shape, np.float32)
        rnd.ravel()[rng.choice(flat_allow, size=BUDGET, replace=False)] = 1.0
        preds["C0_random"] = rnd
        terms = {}
        for arm, pred in preds.items():
            acc = None
            for fold in folds:
                _, f_terms = evaluate_holdout.evaluate(pred, fold, footprint)
                acc = f_terms if acc is None else acc + f_terms
            terms[arm] = acc
        pooled = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810 + seed,
                                                 candidate="CJX_v2_junction")
        # also candidate=v1 summary via from_terms
        results["seeds"][str(seed)] = {
            "withheld_positive_pixels": pooled["scores"]["CJX_v2_junction"]["withheld_positive_pixels"],
            "canaries": canaries,
            "max_canary_symmetric_auc": max(c["symmetric_auc"] for c in canaries.values()),
            "pooled": pooled,
            "dots": {k: int((v > 0).sum()) for k, v in preds.items()},
        }
        for k, v in pooled["scores"].items():
            print(f"seed{seed} {k}: HOLDOUT-DTI={v['dti']:.4f} CI{v['ci95']} n={v['withheld_positive_pixels']}", flush=True)
        print(f"seed{seed} max canary AUC={results['seeds'][str(seed)]['max_canary_symmetric_auc']:.4f}", flush=True)
        np.savez_compressed(OUT / f"cjx_dots_seed{seed}.npz",
                            **{k: (v > 0) for k, v in preds.items()})
    results["elapsed_s"] = round(time.time() - t0, 1)
    (OUT / "cjx_holdout.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({s: {k: v["dti"] for k, v in d["pooled"]["scores"].items()}
                      for s, d in results["seeds"].items()}, indent=2))


if __name__ == "__main__":
    enforce_open_lane(ROOT, "G79-CJX", reason="3-experiment CJX budget exhausted")
    OUT.mkdir(parents=True, exist_ok=True)
    main()
