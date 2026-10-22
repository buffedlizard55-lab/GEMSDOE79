#!/usr/bin/env python3
"""G79-CJX experiment 3 (final in budget): tip-steered CJX + saturated-band CJX.

Arms (frozen before any Exp-3 score is seen):
  CJX_v3_tip:      cjx_v1 * exp(-dist_to_visible_endpoint/12px) + 0.05*cjx_v1
                   Endpoints/skeleton derived ONLY from each seed's visible
                   catalogue (buffered fold), so no withheld pixel is used.
  CJX_v3_band:     cjx_v1 clipped at its in-footprint 95th percentile, so
                   extreme pluton/caldera contacts cannot monopolise the
                   budget (saturation-robust emission of the same surface).
Same folds, budget, separator and evaluator as Exp 1-2.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid
from gems57 import evaluate_holdout, holdout
from gems79.thvc_model import poisson_disk_emit

OUT = ROOT / "evidence" / "cjx"
BUDGET = 37_654
STRUCT = np.ones((3, 3), int)


from gems79.cjx import catalogue_endpoints as endpoints



def _surface_path():
    for cand in (ROOT / "evidence/cjx/cjx_surface.npz", ROOT / ".cache/cjx/cjx_surface.npz"):
        if cand.exists():
            return cand
    raise FileNotFoundError("cjx_surface.npz missing; rerun scripts/run_cjx_experiment.py")


def main():
    t0 = time.time()
    grid = load_grid(ROOT / "data/reference")
    footprint, catalogue = grid.footprint, grid.catalogue
    z = np.load(_surface_path())
    v1 = z["cjx_v1_edge"].astype(np.float32)
    results = {"lane": "G79-CJX", "experiment": 3,
               "evaluator_version": evaluate_holdout.VERSION,
               "evidence_class": "HOLDOUT-DTI", "budget": BUDGET, "seeds": {}}
    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        visible = folds[0]["visible"]
        allow = footprint & (ndi.distance_transform_edt(~visible) > 2.0)
        d_tip = ndi.distance_transform_edt(~endpoints(visible))
        surf_tip = (v1 * np.exp(-d_tip / 12.0) + 0.05 * v1).astype(np.float32)
        surf_tip[~footprint] = 0
        cap = float(np.percentile(v1[footprint], 95))
        surf_band = np.minimum(v1, cap).astype(np.float32)
        preds = {
            "CJX_v3_tip": poisson_disk_emit(surf_tip, allow, budget=BUDGET, min_dist_px=2.8),
            "CJX_v3_band": poisson_disk_emit(surf_band, allow, budget=BUDGET, min_dist_px=2.8),
        }
        rng = np.random.default_rng(seed)
        rnd = np.zeros(footprint.shape, np.float32)
        rnd.ravel()[rng.choice(np.flatnonzero(allow), size=BUDGET, replace=False)] = 1.0
        preds["C0_random"] = rnd
        terms = {}
        for arm, pred in preds.items():
            acc = None
            for fold in folds:
                _, ft = evaluate_holdout.evaluate(pred, fold, footprint)
                acc = ft if acc is None else acc + ft
            terms[arm] = acc
        pooled = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810 + seed,
                                                 candidate="CJX_v3_tip")
        results["seeds"][str(seed)] = {"pooled": pooled,
                                       "dots": {k: int((v > 0).sum()) for k, v in preds.items()}}
        for k, v in pooled["scores"].items():
            print(f"seed{seed} {k}: HOLDOUT-DTI={v['dti']:.4f} CI{v['ci95']}", flush=True)
        np.savez_compressed(OUT / f"cjx_exp3_dots_seed{seed}.npz",
                            **{k: (v > 0) for k, v in preds.items()})
    results["elapsed_s"] = round(time.time() - t0, 1)
    (OUT / "cjx_exp3_holdout.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
