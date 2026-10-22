#!/usr/bin/env python3
"""Lane H79-MCT — hide-and-recover holdout experiment (pre-registered arms).

Evaluator: unmodified vendor ``gems57.evaluate_holdout`` (gems57-pooled-hide-v2), alpha 0.2,
beta 0.8, 300 m triangular kernel, visible catalogue masked pixel-exactly.  Whole catalogue
components are withheld inside label-blind eroded quadrants (``buffered_component_draw``),
features are computed from the visible catalogue only (here: no catalogue feature at all),
and every number written is HOLDOUT-DTI with withheld-positive counts and paired 95 % CIs.

Arms
----
C0_random        uniform random surface                                 (control)
C1_pixel         HGB scarp likelihood p, no continuity                   (lane baseline)
C2_continuity    S = sqrt(p * Sato(p))                                   (PRIMARY)
C3_continuity_q  C2 + uniqueness quota (<= 66 % of dots inside H19-5 halo; as shipped)
REF_h19_5_redot  static H19-5 line set re-dotted fold-fair                (label-aware reference)
REF_champion     archived 0.2778 dots as published                        (label-aware reference)
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
from gems79 import data as D, features as F, model as MD, trace as T  # noqa: E402

PROC = ROOT / "data" / "cache" / "holdout"
CHAMPION = ROOT / "data" / "registry" / "GEMSDOE68__17a76895f6__GEMSDOE32__h33-2-b2-zeros.tif"


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=30)
    ap.add_argument("--budgets", default="25000,37654,50000")
    ap.add_argument("--exclusion", type=float, default=2.0)
    ap.add_argument("--mix", type=float, default=0.5)
    ap.add_argument("--quota", type=float, default=0.66)
    args = ap.parse_args()
    t0 = time.time()
    PROC.mkdir(parents=True, exist_ok=True)
    F.build()
    grid = D.load_grid()
    foot, cat = grid.footprint, grid.catalogue
    folds, _ = HO.buffered_component_draw(grid, seed=args.seed, hide_frac=0.20, buffer_px=3)
    hidden, visible = folds[0]["hidden_all"], folds[0]["visible"]
    receipts = [f["receipt"] for f in folds]
    log(f"seed {args.seed}: withheld positives={int(hidden.sum())} visible={int(visible.sum())} catalogue={int(cat.sum())}")

    stack = np.load(F.STACK, mmap_mode="r")
    cols = MD.feature_columns()
    rng = np.random.default_rng(79_000 + args.seed)
    dist_vis = ndi.distance_transform_edt(~visible)

    # ---------- leakage canary: every channel alone vs withheld positives ----------
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
        "evidence_class": "HOLDOUT-DTI", "lane": "H79-MCT", "evaluator_version": EH.VERSION,
        "implementation": EH.implementation_hashes(), "alpha": M.ALPHA, "beta": M.BETA,
        "kernel_radius_px": M.RADIUS_PX, "holdout_seed": args.seed,
        "withheld_positive_pixels": int(hidden.sum()), "visible_catalogue_pixels": int(visible.sum()),
        "fold_receipts": receipts, "canary_auc": canary, "canary_worst": {"channel": worst[1], "sym_auc": worst[0]},
        "leakage_channels_gt_0p90": leak, "features": F.CHANNELS, "hgb": MD.HGB_KW,
        "exclusion_px": args.exclusion, "mix": args.mix, "quota_share": args.quota, "arms": {},
    }
    if leak:
        results["verdict"] = "STOP-LEAKAGE"
        (ROOT / "evidence" / f"holdout_h79_seed{args.seed}.json").write_text(json.dumps(results, indent=2) + "\n")
        log("LEAKAGE CANARY FAILED", leak)
        return

    # ---------- OOF scarp likelihood (LOQO; catalogue-free features) ----------
    oof_path = PROC / f"oof_p_seed{args.seed}.npy"
    if oof_path.exists():
        p = np.load(oof_path)
        log("loaded cached OOF p")
    else:
        p = np.zeros(foot.shape, np.float32)
        for k, fold in enumerate(folds):
            train_region = np.zeros_like(foot)
            for j, f2 in enumerate(folds):
                if j != k:
                    train_region |= f2["region"]
            idx, y, info = MD.sample_training(visible, train_region, foot, rng)
            log(f"fold {fold['name']}: train {info}")
            clf = MD.fit(stack, cols, idx, y, tag=fold["name"])
            p += MD.predict(clf, stack, cols, fold["region"] & foot)
            del clf
            gc.collect()
        np.save(oof_path, p)
        log(f"OOF p done ({time.time() - t0:.0f}s)")

    s = T.continuity_surface(p, foot, mix=args.mix)
    np.save(PROC / f"oof_s_seed{args.seed}.npy", s)
    allowed = T.allowed_domain(foot, visible, args.exclusion)
    h19 = D.read_h19_5_support()
    h19_halo = T.halo(h19, 3.0)

    def emit_pooled(surface, budget, quota_mask=None, quota_share=1.0):
        tot = sum(int((f["region"] & allowed).sum()) for f in folds)
        dots = np.zeros(foot.shape, bool)
        infos = []
        for f in folds:
            a = f["region"] & allowed
            b = int(round(budget * int(a.sum()) / max(tot, 1)))
            d, info = T.emit_dots(surface, a, b, quota_mask=quota_mask, quota_share=quota_share)
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

    budgets = [int(b) for b in args.budgets.split(",")]
    terms_by_arm = {}
    scan = {}
    for B in budgets:
        for arm, surf in (("C1_pixel", p), ("C2_continuity", s)):
            dots, infos = emit_pooled(surf, B)
            per, terms = score(dots)
            pooled = float(EH.from_terms(terms.sum(axis=0)))
            scan[f"{arm}_B{B}"] = {"arm": arm, "budget": B, "dots": int(dots.sum()), "pooled_holdout_dti": pooled, "per_fold": per}
            terms_by_arm[f"{arm}_B{B}"] = terms
            log(f"{arm} B={B}: pooled HOLDOUT-DTI={pooled:.4f} dots={int(dots.sum())}")
    results["budget_scan"] = scan
    best = max((v["pooled_holdout_dti"], -v["budget"], k) for k, v in scan.items() if v["arm"] == "C2_continuity")
    B_sel = -best[1]
    results["selected_budget_on_holdout"] = B_sel
    log(f"selected budget (holdout optimum of C2): {B_sel}")

    # final arms at the champion-anchored budget (37,654) AND the holdout optimum
    for B in sorted({37_654, B_sel}):
        tag = f"B{B}"
        dots_q, infos = emit_pooled(s, B, quota_mask=h19_halo, quota_share=args.quota)
        per, terms = score(dots_q)
        terms_by_arm[f"C3_continuity_q_{tag}"] = terms
        results["arms"][f"C3_continuity_q_{tag}"] = {
            "dots": int(dots_q.sum()), "per_fold": per, "pooled_holdout_dti": float(EH.from_terms(terms.sum(axis=0))),
            "dots_in_h19_halo": int((dots_q & h19_halo).sum()), "emit_info": infos}
        log(f"C3_continuity_q {tag}: pooled HOLDOUT-DTI={results['arms'][f'C3_continuity_q_{tag}']['pooled_holdout_dti']:.4f} in-halo={int((dots_q & h19_halo).sum())}")
        np.save(PROC / f"dots_C3_seed{args.seed}_{tag}.npy", dots_q)
        # random control
        r = np.random.default_rng(999).random(foot.shape, dtype=np.float32) * foot
        dots_r, _ = emit_pooled(r, B)
        per, terms = score(dots_r)
        terms_by_arm[f"C0_random_{tag}"] = terms
        results["arms"][f"C0_random_{tag}"] = {"dots": int(dots_r.sum()), "per_fold": per, "pooled_holdout_dti": float(EH.from_terms(terms.sum(axis=0)))}
        log(f"C0_random {tag}: pooled HOLDOUT-DTI={results['arms'][f'C0_random_{tag}']['pooled_holdout_dti']:.4f}")
        del r
        # label-aware references
        with rasterio.open(D.H19_5) as src:
            h = src.read(1)
        h = np.where(np.isfinite(h), h, 0).astype(np.float32)
        dots_h, _ = emit_pooled(h, B)
        per, terms = score(dots_h)
        terms_by_arm[f"REF_h19_5_redot_{tag}"] = terms
        results["arms"][f"REF_h19_5_redot_{tag}"] = {
            "dots": int(dots_h.sum()), "per_fold": per, "pooled_holdout_dti": float(EH.from_terms(terms.sum(axis=0))),
            "caveat": "H19-5 surface was fitted with the FULL catalogue (withheld segments included); label-aware upper reference, not a fair arm"}
        log(f"REF_h19_5_redot {tag}: pooled HOLDOUT-DTI={results['arms'][f'REF_h19_5_redot_{tag}']['pooled_holdout_dti']:.4f}")
        del h, dots_h
    if CHAMPION.exists():
        with rasterio.open(CHAMPION) as src:
            c = src.read(1)
        c = np.where(np.isfinite(c), c, 0) > 0
        per, terms = score(c)
        terms_by_arm["REF_champion_static"] = terms
        results["arms"]["REF_champion_static"] = {
            "dots": int(c.sum()), "per_fold": per, "pooled_holdout_dti": float(EH.from_terms(terms.sum(axis=0))),
            "caveat": "archived 0.2778 dots pruned with the FULL catalogue incl. withheld segments; reference only"}
        log(f"REF_champion_static: pooled HOLDOUT-DTI={results['arms']['REF_champion_static']['pooled_holdout_dti']:.4f}")

    cand = f"C3_continuity_q_B37654"
    results["pooled_summary"] = EH.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate=cand)
    results["runtime_s"] = round(time.time() - t0, 1)
    out = ROOT / "evidence" / f"holdout_h79_seed{args.seed}.json"
    out.write_text(json.dumps(results, indent=2, default=float) + "\n")
    log(f"wrote {out} ({results['runtime_s']}s)")


if __name__ == "__main__":
    main()
