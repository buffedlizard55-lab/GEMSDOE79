#!/usr/bin/env python3
"""H80-RADIO-PILOT: single-feature zero-catalogue pilot (registry/preregistration_h80_radio_pilot.json).

Reuses the shared template (vendor/gems57): folds, evaluator, metric, pooled bootstrap.
Imports the placement and per-fold scoring helpers from the DRAPE pilot so that the two
pilots share identical placement and evaluation code (no private fork of the scorer).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.linear_model import HuberRegressor
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import evaluate_holdout as eh  # noqa: E402
from gems57 import holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.evaluate_holdout import pooled_summary  # noqa: E402
from run_h80_drape_pilot import BUDGET, SEP_PX, greedy_place, normalise, pooled_terms  # noqa: E402

OUT = ROOT / "evidence" / "h80_radio_pilot"
SIGMA_PX = 2.0


def load_k_th() -> tuple[np.ndarray, np.ndarray, dict]:
    with rasterio.open(ROOT / "data/raw/external/geodawn_rad_u8.tif") as ds:
        names = [str(d) for d in ds.descriptions]
        if names[0] != "K" or names[1] != "Th":
            raise RuntimeError(f"unexpected band names {names}")
        k = ds.read(1).astype(np.float64)
        th = ds.read(2).astype(np.float64)
    return k, th, {"band_names": names[:4]}


def robust_sigma(x: np.ndarray) -> float:
    med = np.median(x)
    return float(1.4826 * np.median(np.abs(x - med)))


def build_scores(k: np.ndarray, th: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    valid = footprint & (k > 0) & (th > 0)   # uint8 zero treated as missing (see preregistration)
    info = {"valid_cells": int(valid.sum()), "footprint_cells": int(footprint.sum()),
            "k_zero_in_footprint": int((footprint & (k == 0)).sum()),
            "th_zero_in_footprint": int((footprint & (th == 0)).sum())}
    model = HuberRegressor().fit(th[valid].reshape(-1, 1), k[valid])
    info["huber_slope"] = float(model.coef_[0])
    info["huber_intercept"] = float(model.intercept_)
    resid = np.where(valid, k - (model.intercept_ + model.coef_[0] * th), 0.0)
    raw = np.where(valid, k, 0.0)
    out = []
    for field in (resid, raw):
        mu = float(np.median(field[valid]))
        sd = robust_sigma(field[valid])
        z = (field - mu) / (sd if sd > 0 else 1.0)
        z = np.where(valid, z, 0.0)
        sm = ndi.gaussian_filter(z, SIGMA_PX)
        out.append(np.where(footprint, np.maximum(sm, 0.0), 0.0).astype(np.float32))
    return out[0], out[1], info


def run_seed(seed: int, grid, s_a: np.ndarray, s_b: np.ndarray, rng_seed: int) -> dict:
    t0 = time.time()
    folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    hidden_all = folds[0]["hidden_all"]
    d_vis = ndi.distance_transform_edt(~visible)
    allowed = grid.footprint & (d_vis > 2.0)
    n_withheld = int(sum(int(np.asarray(f["truth"], bool).sum()) for f in folds))
    rng = np.random.default_rng(rng_seed)
    arms, aucs, emitted = {}, {}, {}
    for name, s_raw in (("A_th_normalised_K", s_a), ("B_control_raw_K", s_b)):
        s = normalise(s_raw, allowed)
        cand = np.flatnonzero((allowed & grid.footprint).ravel())
        order = cand[np.argsort(-s.ravel()[cand], kind="stable")]
        dots = greedy_place(order, grid.footprint.shape, BUDGET, SEP_PX)
        terms, _ = pooled_terms(dots.astype(np.float32), folds, grid.footprint)
        arms[name] = terms
        emitted[name] = int(dots.sum())
        pos = np.flatnonzero((hidden_all & allowed).ravel())
        neg_pool = np.flatnonzero((allowed & ~hidden_all).ravel())
        neg = rng.choice(neg_pool, size=min(300_000, neg_pool.size), replace=False)
        y = np.r_[np.ones(pos.size), np.zeros(neg.size)]
        sc = np.r_[s.ravel()[pos], s.ravel()[neg]]
        aucs[name] = float(roc_auc_score(y, sc))
    # Same random comparator design and RNG seed as the DRAPE pilot (identical C0 by construction).
    rng_c0 = np.random.default_rng(900 + seed)
    cand_r = np.flatnonzero((allowed & grid.footprint).ravel())
    perm = rng_c0.permutation(cand_r)
    dots_c0 = greedy_place(perm, grid.footprint.shape, BUDGET, SEP_PX)
    terms_c0, _ = pooled_terms(dots_c0.astype(np.float32), folds, grid.footprint)
    arms["C0_random"] = terms_c0
    emitted["C0_random"] = int(dots_c0.sum())
    summary = pooled_summary(arms, draws=1000, seed=520810 + seed, candidate="A_th_normalised_K")
    out = dict(seed=seed, evaluator_version=eh.VERSION, withheld_positive_pixels=n_withheld,
               expected_receipt_withheld_positive_pixels={20: 11321, 30: 11342}.get(seed),
               emitted_dots=emitted, leakage_canary_auc_single_score={k: round(v, 4) for k, v in aucs.items()},
               pooled_summary=summary, runtime_s=round(time.time() - t0, 1))
    for name in arms:
        sc = summary["scores"][name]
        print(f"  seed {seed} {name:20s} HOLDOUT-DTI={sc['dti']:.4f} CI95={[round(x, 4) for x in sc['ci95']]}", flush=True)
    for k2, v in summary["paired_differences"].items():
        print(f"  seed {seed} A - {k2}: delta={v['delta']:+.4f} CI95={[round(x, 4) for x in v['ci95']]}", flush=True)
    print(f"  seed {seed} withheld={n_withheld} AUC={out['leakage_canary_auc_single_score']}", flush=True)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    grid = load_grid(ROOT / "data/raw")
    k, th, meta = load_k_th()
    s_a, s_b, info = build_scores(k, th, grid.footprint)
    results = [run_seed(seed, grid, s_a, s_b, rng_seed=900 + seed) for seed in (20, 30)]
    for r in results:
        (OUT / f"seed{r['seed']}.json").write_text(json.dumps(r, indent=2) + "\n")
    summary = {"lane": "H80-RADIO-PILOT", "evidence_class": "HOLDOUT-DTI", "evaluator_version": eh.VERSION,
               "input_meta": meta, "score_meta": info,
               "bar_to_spend_slot": {"seed20": 0.1905, "seed30": 0.1944},
               "results": results}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("wrote", OUT / "summary.json")


if __name__ == "__main__":
    main()
