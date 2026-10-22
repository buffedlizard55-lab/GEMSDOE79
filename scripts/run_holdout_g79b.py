#!/usr/bin/env python3
"""Lane G79B-SDPT — preregistered hide-and-recover holdout (experiment E1).

Evaluator: unmodified vendor gems57.evaluate_holdout (gems57-pooled-hide-v2),
alpha 0.2, beta 0.8, 300 m triangular kernel. Split:
gems57.holdout.buffered_component_draw (whole components, buffer 3 px) seeds
30/20 — the identical draws used by the archived H79-MCT runs, so archived
numbers are directly comparable. Arms (registry/preregistration_g79b.json):
A0_random, A1_control_h79_pixel (30 ch), A2_sdpt_pixel (all ch),
A3_sdpt_trace (A2 + trace objects), REF_h19_5_redot (label-aware reference).
Every emitted number is HOLDOUT-DTI with withheld counts + paired 95% CIs.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import holdout as HO, evaluate_holdout as EH, metric as M  # noqa: E402
from gems79b import data as D, features as F, model as MD, trace as T  # noqa: E402

PROC = ROOT / "data" / "cache" / "holdout_g79b"
BUDGET = 37_654


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def h19_path() -> Path | None:
    idx = json.loads((ROOT / "registry" / "registry_index.json").read_text())
    for r in idx["rasters"]:
        if r["blob"] == "5d1a920f40fa3a589e91248c1309761e44d45da8":
            p = ROOT / ".cache" / "registry" / (r["blob"] + ".tif")
            return p if p.exists() else None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=30)
    args = ap.parse_args()
    from gems79.lifecycle import require_open_lane
    require_open_lane(ROOT, "G79B-SDPT")
    seed = args.seed
    t0 = time.time()
    PROC.mkdir(parents=True, exist_ok=True)
    F.build()
    grid = D.load_grid()
    foot, cat = grid.footprint, grid.catalogue
    folds, _ = HO.buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
    hidden, visible = folds[0]["hidden_all"], folds[0]["visible"]
    receipts = [f["receipt"] for f in folds]
    log(f"seed {seed}: withheld={int(hidden.sum())} visible={int(visible.sum())} catalogue={int(cat.sum())}")

    stack = np.load(F.STACK, mmap_mode="r")
    rng = np.random.default_rng(79_000 + seed)
    dist_vis = ndi.distance_transform_edt(~visible)

    # ---- leakage canary: every channel alone vs withheld positives ----
    pos_idx = np.flatnonzero(hidden)
    neg_pool = np.flatnonzero(foot & (dist_vis > 3) & ~hidden)
    neg_idx = rng.choice(neg_pool, size=min(200_000, neg_pool.size), replace=False)
    cidx = np.concatenate([pos_idx, neg_idx])
    yc = np.concatenate([np.ones(pos_idx.size), np.zeros(neg_idx.size)])
    order = np.argsort(cidx)
    Xc = np.asarray(stack.reshape(-1, stack.shape[2])[cidx[order]], dtype=np.float32)
    yc = yc[order]
    canary = {}
    for j, name in enumerate(F.CHANNELS):
        v = Xc[:, j]
        m = np.isfinite(v)
        canary[name] = float(roc_auc_score(yc[m], v[m])) if m.sum() > 1000 and len(np.unique(yc[m])) == 2 else None
    leak = [n for n, a in canary.items() if a is not None and max(a, 1 - a) > 0.90]
    worst = max(((max(a, 1 - a), n) for n, a in canary.items() if a is not None))
    log(f"canary worst: {worst[1]} symAUC={worst[0]:.4f}; leakage(>0.90)={leak}")
    del Xc
    gc.collect()

    results = {
        "evidence_class": "HOLDOUT-DTI", "lane": "G79B-SDPT", "evaluator_version": EH.VERSION,
        "implementation": EH.implementation_hashes(), "alpha": M.ALPHA, "beta": M.BETA,
        "kernel_radius_px": M.RADIUS_PX, "holdout_seed": seed,
        "withheld_positive_pixels": int(hidden.sum()),
        "visible_catalogue_pixels": int(visible.sum()),
        "fold_receipts": receipts, "canary_auc": canary,
        "canary_worst": {"channel": worst[1], "sym_auc": worst[0]},
        "leakage_channels_gt_0p90": leak, "features": F.CHANNELS,
        "base_features": F.BASE_CHANNELS, "new_features": F.NEW_CHANNELS, "hgb": MD.HGB_KW,
        "budget": BUDGET, "exclusion_px": 2.0, "min_sep_px": 2.8, "arms": {},
    }
    if leak:
        results["verdict"] = "STOP-LEAKAGE"
        out = ROOT / "evidence" / f"holdout_g79b_seed{seed}.json"
        out.write_text(json.dumps(results, indent=2) + "\n")
        log("LEAKAGE CANARY FAILED", leak)
        return

    # ---- OOF surfaces (LOQO), A1 control cols and A2 all cols ----
    def oof(cols, tag):
        path = PROC / f"oof_{tag}_seed{seed}.npy"
        if path.exists():
            log(f"loaded cached OOF {tag}")
            return np.load(path)
        p = np.zeros(foot.shape, np.float32)
        for k, fold in enumerate(folds):
            train_region = np.zeros_like(foot)
            for j, f2 in enumerate(folds):
                if j != k:
                    train_region |= f2["region"]
            idx, y, info = MD.sample_training(visible, train_region, foot, rng)
            log(f"{tag} fold {fold['name']}: train {info}")
            clf = MD.fit(stack, cols, idx, y, tag=f"{tag}/{fold['name']}")
            p += MD.predict(clf, stack, cols, fold["region"] & foot)
            del clf
            gc.collect()
        np.save(path, p)
        return p

    p1 = oof(MD.cols_for(F.BASE_CHANNELS), "A1")
    p2 = oof(MD.cols_for(F.CHANNELS), "A2")

    sr_path = PROC / "step_rank.npy"
    if sr_path.exists():
        step_rank = np.load(sr_path)
    else:
        step_rank = F.rank01(np.array(stack[:, :, F.IDX["lid_step_max"]]), foot)
        np.save(sr_path, step_rank)
    s3, seg_info = T.trace_surface(p2, step_rank, foot)
    np.save(PROC / f"oof_A3_seed{seed}.npy", s3)
    results["trace_info"] = seg_info
    log(f"A3 trace surface {seg_info}")

    allowed = T.allowed_domain(foot, visible, 2.0)

    def emit_pooled(surface, budget=BUDGET):
        tot = sum(int((f["region"] & allowed).sum()) for f in folds)
        dots = np.zeros(foot.shape, bool)
        infos = []
        for f in folds:
            a = f["region"] & allowed
            b = int(round(budget * int(a.sum()) / max(tot, 1)))
            d, info = T.emit_dots(surface, a, b)
            dots |= d
            infos.append(info)
        return dots, infos

    def score(dots):
        terms = None
        per = {}
        for f in folds:
            res, t = EH.evaluate(dots.astype(np.float32), f, valid=foot, block_side=200)
            per[f["name"]] = {"dti": res["dti"], "n_truth": res["n_truth"], "emitted": res["n_emitted"]}
            terms = t if terms is None else terms + t
        return per, terms

    terms_by_arm = {}
    arms = [("A1_control_h79_pixel", p1), ("A2_sdpt_pixel", p2), ("A3_sdpt_trace", s3)]
    for name, surf in arms:
        dots, infos = emit_pooled(surf)
        per, terms = score(dots)
        terms_by_arm[name] = terms
        results["arms"][name] = {"dots": int(dots.sum()), "per_fold": per,
                                 "pooled_holdout_dti": float(EH.from_terms(terms.sum(axis=0))),
                                 "emit_info": infos}
        np.save(PROC / f"dots_{name}_seed{seed}.npy", dots)
        log(f"{name}: pooled HOLDOUT-DTI={results['arms'][name]['pooled_holdout_dti']:.4f} dots={int(dots.sum())}")

    r = np.random.default_rng(999).random(foot.shape, dtype=np.float32) * foot
    dots_r, _ = emit_pooled(r)
    per, terms = score(dots_r)
    terms_by_arm["A0_random"] = terms
    results["arms"]["A0_random"] = {"dots": int(dots_r.sum()), "per_fold": per,
                                    "pooled_holdout_dti": float(EH.from_terms(terms.sum(axis=0)))}
    log(f"A0_random: pooled HOLDOUT-DTI={results['arms']['A0_random']['pooled_holdout_dti']:.4f}")
    del r

    hp = h19_path()
    if hp is not None:
        with rasterio.open(hp) as src:
            h = src.read(1)
        h = np.where(np.isfinite(h), h, 0).astype(np.float32)
        dots_h, _ = emit_pooled(h)
        per, terms = score(dots_h)
        terms_by_arm["REF_h19_5_redot"] = terms
        results["arms"]["REF_h19_5_redot"] = {
            "dots": int(dots_h.sum()), "per_fold": per,
            "pooled_holdout_dti": float(EH.from_terms(terms.sum(axis=0))),
            "caveat": "H19-5 surface was fitted with the FULL catalogue (withheld segments included); label-aware upper reference, not a fair arm"}
        log(f"REF_h19_5_redot: pooled HOLDOUT-DTI={results['arms']['REF_h19_5_redot']['pooled_holdout_dti']:.4f}")
        del h, dots_h

    results["pooled_summary_candidate_A2"] = EH.pooled_summary(
        terms_by_arm, draws=1000, seed=520810, candidate="A2_sdpt_pixel")
    results["pooled_summary_candidate_A3"] = EH.pooled_summary(
        terms_by_arm, draws=1000, seed=520810, candidate="A3_sdpt_trace")
    results["runtime_s"] = round(time.time() - t0, 1)
    out = ROOT / "evidence" / f"holdout_g79b_seed{seed}.json"
    out.write_text(json.dumps(results, indent=2, default=float) + "\n")
    log(f"wrote {out} ({results['runtime_s']}s)")


if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError
    try:
        main()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
