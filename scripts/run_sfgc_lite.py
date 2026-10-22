#!/usr/bin/env python3
"""E2 scoring-only: SFGC-lite signed scarp polarity (registry/preregistration_sfgc_lite_8e58a8d0_E2.json)."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import evaluate_holdout as eh
from gems57 import holdout
from gems57.grid import load_grid
from gems57.evaluate_holdout import pooled_summary
from run_h80_drape_pilot import BUDGET, SEP_PX, greedy_place, normalise, pooled_terms

OUT = ROOT / "evidence" / "sfgc_lite_8e58a8d0"


def build(footprint):
    with rasterio.open(ROOT / "data/raw/external/lidar_scarp_features_u8.tif") as ds:
        assert list(ds.descriptions)[:12] == ["ex_max","ex_mean","step_max","lapneg_max","lappos_max","downface_max","upface_max","cross_max","relief","coh100","strike","valid"], ds.descriptions
        down = ds.read(6).astype(np.float32); up = ds.read(7).astype(np.float32); valid = ds.read(12)
    with rasterio.open(ROOT / "data/raw/training_features.tif") as ds:
        assert str(ds.descriptions[17]).startswith("iso_grav_anom_hg"), ds.descriptions[17]
        ghg = ds.read(18).astype(np.float32)
    ghg[~np.isfinite(ghg) | (ghg <= -1e30)] = 0
    liv = footprint & (valid > 0) & ((up + down) > 0)
    signed = np.where(liv, (up - down) / (up + down + 5.0), 0).astype(np.float32)
    amp_raw = up + down
    amp = np.where(liv, np.clip(amp_raw / float(np.percentile(amp_raw[liv], 99.0)), 0, 1), 0).astype(np.float32)
    gstep = np.clip(np.abs(ghg) / float(np.percentile(np.abs(ghg[footprint]), 99.0)), 0, 1).astype(np.float32)
    anti = (np.clip(signed, 0, 1) * amp).astype(np.float32)
    syn = (np.clip(-signed, 0, 1) * amp * gstep).astype(np.float32)
    s_a = np.maximum(anti, syn); s_b = (np.abs(signed) * amp).astype(np.float32)
    s_a[~footprint] = 0; s_b[~footprint] = 0
    feats = dict(signed=signed, antithetic=anti, synthetic=syn, A_sfgc=s_a, B_unsigned=s_b)
    return s_a, s_b, feats, dict(lidar_valid_cells=int(liv.sum()), footprint_cells=int(footprint.sum()))


def run_seed(seed, grid, s_a, s_b, feats):
    t0 = time.time()
    folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible, hidden_all = folds[0]["visible"], folds[0]["hidden_all"]
    allowed = grid.footprint & (ndi.distance_transform_edt(~visible) > 2.0)
    n_withheld = int(sum(int(np.asarray(f["truth"], bool).sum()) for f in folds))
    rng = np.random.default_rng(900 + seed)
    pos = np.flatnonzero((hidden_all & allowed).ravel())
    neg_pool = np.flatnonzero((allowed & ~hidden_all).ravel())
    neg = rng.choice(neg_pool, size=min(300_000, neg_pool.size), replace=False)
    y = np.r_[np.ones(pos.size), np.zeros(neg.size)]
    canary = {}
    for name, s in feats.items():
        sc = np.r_[s.ravel()[pos], s.ravel()[neg]].astype(np.float64)
        a = float(roc_auc_score(y, sc)) if np.unique(sc).size > 1 else 0.5
        canary[name] = dict(auc=round(a, 4), symmetric=round(max(a, 1 - a), 4), pass_le_0p90=bool(max(a, 1 - a) <= 0.90))
    arms, emitted = {}, {}
    for name, s_raw in (("A_sfgc_lite", s_a), ("B_control_unsigned", s_b)):
        s = normalise(s_raw, allowed)
        cand = np.flatnonzero(allowed.ravel())
        order = cand[np.argsort(-s.ravel()[cand], kind="stable")]
        dots = greedy_place(order, grid.footprint.shape, BUDGET, SEP_PX)
        arms[name], _ = pooled_terms(dots.astype(np.float32), folds, grid.footprint)
        emitted[name] = int(dots.sum())
    rng_c0 = np.random.default_rng(900 + seed)
    dots_c0 = greedy_place(rng_c0.permutation(np.flatnonzero(allowed.ravel())), grid.footprint.shape, BUDGET, SEP_PX)
    arms["C0_random"], _ = pooled_terms(dots_c0.astype(np.float32), folds, grid.footprint)
    emitted["C0_random"] = int(dots_c0.sum())
    summary = pooled_summary(arms, draws=1000, seed=520810 + seed, candidate="A_sfgc_lite")
    out = dict(seed=seed, evidence_class="HOLDOUT-DTI", evaluator_version=eh.VERSION,
               withheld_positive_pixels=n_withheld, emitted_dots=emitted,
               leakage_canary_single_feature=canary, pooled_summary=summary,
               runtime_s=round(time.time() - t0, 1))
    for name in arms:
        sc = summary["scores"][name]
        print(f"  seed {seed} {name:20s} HOLDOUT-DTI={sc['dti']:.4f} CI95={[round(x,4) for x in sc['ci95']]}", flush=True)
    print(f"  seed {seed} canary={ {k: v['symmetric'] for k, v in canary.items()} }", flush=True)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    grid = load_grid(ROOT / "data/raw")
    s_a, s_b, feats, info = build(grid.footprint)
    print("info:", info, flush=True)
    results = [run_seed(s, grid, s_a, s_b, feats) for s in (20, 30)]
    (OUT / "summary.json").write_text(json.dumps(dict(
        lane="G79-MDSC-8e58a8d0", experiment="E2-SFGC-lite-scoring-only",
        evidence_class="HOLDOUT-DTI", evaluator_version=eh.VERSION, surface_info=info,
        bar_to_spend_slot_THVC={"seed20": 0.1905, "seed30": 0.1944}, results=results), indent=2) + "\n")
    print("wrote", OUT / "summary.json")


if __name__ == "__main__":
    main()
