#!/usr/bin/env python3
"""G79-TDW experiment 1 (of max 3): surface, canaries, hide-and-recover holdout,
final emission via shared writer, format validation, local novelty scan.
No slot is spent; verdict promote only if every gate passes (see run card).
"""
from __future__ import annotations
import json, sys, time, hashlib
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"vendor")]
from gems57.grid import load_grid
from gems57 import holdout, evaluate_holdout
from gems57.submission_writer import write_submission
from gems57.validate import validate as shared_validate
from gems79.tdw import build_tdw_features, greedy_emit

BUDGET = 37654
NAME = "gems79-tdw-tiltworm-37654dots-20261022"
NOTE = "G79-TDW destriped tilt-depth worms, gravity-concordant, 37654 dots, zeros outside footprint"

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b""): h.update(b)
    return h.hexdigest()

def main():
    t0=time.time()
    grid = load_grid(ROOT/"data"/"reference")
    fp, cat = grid.footprint, grid.catalogue
    print(f"footprint={fp.sum()} catalogue={cat.sum()}", flush=True)
    with rasterio.open(ROOT/"data"/"raw"/"training_features.tif") as ds:
        print("bands", ds.count, ds.dtypes[0], ds.crs, flush=True)
        bands = {"rtp": ds.read(2).astype(np.float64), "elev": ds.read(12).astype(np.float64),
                 "grav": ds.read(13).astype(np.float64), "tmi": ds.read(14).astype(np.float64),
                 "depth": ds.read(15).astype(np.float64)}
    feats = build_tdw_features(bands, fp)
    surf = feats["surface"]
    print("surface built", surf.max(), float((surf>0).sum()), flush=True)
    # ---- leakage canaries per seed (feature alone, withheld pos vs far negs) ----
    canaries = {}
    hold = {}
    for seed in (20, 30):
        folds, quad = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        truth_all = np.zeros(fp.shape, bool)
        for f in folds: truth_all |= f["truth"]
        vis = folds[0]["visible"]
        d_truth = ndi.distance_transform_edt(~truth_all); d_vis = ndi.distance_transform_edt(~vis)
        active = fp & ~folds[0]["masked_known"]
        pos = active & truth_all
        negpool = active & ~truth_all & (d_truth>3) & (d_vis>3)
        rng = np.random.default_rng(seed)
        neg_idx = np.flatnonzero(negpool.ravel()); pos_idx = np.flatnonzero(pos.ravel())
        neg_s = rng.choice(neg_idx, size=min(neg_idx.size, pos_idx.size*3), replace=False)
        aucs = {}
        for k, v in feats.items():
            if k=="surface": continue
            y = np.concatenate([np.ones(pos_idx.size), np.zeros(neg_s.size)])
            s = np.concatenate([np.asarray(v).ravel()[pos_idx], np.asarray(v).ravel()[neg_s]])
            a = float(roc_auc_score(y, s)); aucs[k] = {"auc": a, "symmetric_auc": max(a, 1-a)}
        canaries[f"seed{seed}"] = {"withheld": int(pos_idx.size), "features": aucs,
            "max_symmetric_auc": max(v["symmetric_auc"] for v in aucs.values())}
        print(f"seed{seed} canary maxAUC={canaries[f'seed{seed}']['max_symmetric_auc']:.4f} withheld={pos_idx.size}", flush=True)
        # ---- holdout emission per fold: candidate vs uniform control ----
        terms = {}
        for arm in ("TDW", "UNIFORM"):
            per_terms = []
            tot_emit = 0
            for f in folds:
                region_fp = int((fp & f["region"]).sum())
                b = int(round(BUDGET * region_fp / int(fp.sum())))
                allowed = fp & f["region"] & ~f["masked_known"]
                if arm=="TDW":
                    s = np.where(allowed, surf, 0.0)
                else:
                    rr = np.random.default_rng(seed*100+f["fold"]); s = np.where(allowed, rr.random(surf.shape), 0.0)
                dots = greedy_emit(s, allowed, b, 2.8)
                tot_emit += int(dots.sum())
                pred = dots.astype(np.float32)
                res, trm = evaluate_holdout.evaluate(pred, f, fp)
                per_terms.append(trm)
            terms[arm] = (per_terms, tot_emit)
        # pooled_summary needs aligned block terms: evaluate() returns per-fold terms on cropped grids;
        # pool manually via summed tp/fp/fn + bootstrap on concatenated terms padded to common length
        # Use shared pooled_summary by stacking fold terms with global block alignment fallback:
        # Simpler: compute pooled DTI from summed components and CI via block bootstrap on terms concat.
        pooled = {}
        for arm,(pts,te) in terms.items():
            arr = np.vstack(pts); s = arr.sum(axis=0)
            dti = float(s[0]/(s[0]+0.2*s[1]+0.8*s[2]+1e-12))
            pooled[arm] = {"dti": dti, "tpw": float(s[0]), "fpw": float(s[1]), "fnw": float(s[2]),
                           "withheld": int(round(s[3])), "emitted_in_folds": int(te)}
            # bootstrap CI over spatial blocks (rows of arr)
            rngb = np.random.default_rng(520810)
            nb = arr.shape[0]; draws=[]
            for _ in range(1000):
                pick = rngb.integers(0, nb, size=nb); ss = arr[pick].sum(axis=0)
                draws.append(ss[0]/(ss[0]+0.2*ss[1]+0.8*ss[2]+1e-12))
            pooled[arm]["ci95"] = [float(np.quantile(draws,0.025)), float(np.quantile(draws,0.975))]
        # paired diff TDW-UNIFORM bootstrap
        a1, a2 = np.vstack(terms["TDW"][0]), np.vstack(terms["UNIFORM"][0])
        # align lengths by truncating to min (same folds -> same block count expected); if differ, resample separately is invalid -> pad
        n = min(len(a1), len(a2)); a1, a2 = a1[:n], a2[:n]
        rngb = np.random.default_rng(520811); diffs=[]
        for _ in range(1000):
            pick = rngb.integers(0, n, size=n)
            def dti(a): s=a[pick].sum(axis=0); return s[0]/(s[0]+0.2*s[1]+0.8*s[2]+1e-12)
            diffs.append(dti(a1)-dti(a2))
        hold[f"seed{seed}"] = {"arms": pooled, "paired_TDW_minus_UNIFORM": {"delta": pooled["TDW"]["dti"]-pooled["UNIFORM"]["dti"], "ci95": [float(np.quantile(diffs,0.025)), float(np.quantile(diffs,0.975))]}}
        print(f"seed{seed} HOLDOUT-DTI TDW={pooled['TDW']['dti']:.4f} {pooled['TDW']['ci95']} n={pooled['TDW']['withheld']} UNIFORM={pooled['UNIFORM']['dti']:.4f}", flush=True)
    # ---- final emission (full catalogue) ----
    dcat = ndi.distance_transform_edt(~cat)
    allowed_final = fp & ~cat & (dcat > 2.0)
    dots = greedy_emit(np.where(allowed_final, surf, 0.0), allowed_final, BUDGET, 2.8)
    pred = dots.astype(np.float32)
    print(f"final dots={int(dots.sum())} onCat={int((dots&cat).sum())} outsideFP={int((dots&~fp).sum())}", flush=True)
    outdir = ROOT/"docs"/"downloads"; outdir.mkdir(parents=True, exist_ok=True)
    tif = outdir/f"{NAME}.tif"
    receipt = write_submission(tif, pred, ROOT/"data"/"reference"/"sample_submission.tif", fp, note=NOTE, name=NAME, catalogue=cat, metadata={"lane":"G79-TDW","session":"0be4d7bb","budget":BUDGET})
    print("written", tif, receipt.get("sha256") if isinstance(receipt,dict) else receipt, flush=True)
    val = shared_validate(tif, fp, cat)
    ev = {"lane":"G79-TDW","session":"0be4d7bb","budget":BUDGET,"final_dots":int(dots.sum()),
          "canaries":canaries,"holdout":hold,"validator":val,"raster_sha256":sha(tif),
          "runtime_s": time.time()-t0, "evaluator":"gems57-pooled-hide-v2 (evaluate_holdout.evaluate + summed pooled DTI; 20km-block bootstrap CI)"}
    (ROOT/"evidence"/"tdw").mkdir(parents=True, exist_ok=True)
    (ROOT/"evidence"/"tdw"/"experiment1.json").write_text(json.dumps(ev, indent=2))
    print(json.dumps({"holdout":{k:v["arms"]["TDW"] for k,v in hold.items()},"canary_max":{k:v["max_symmetric_auc"] for k,v in canaries.items()},"validator_pass":val["all_checks_passed"]}, indent=2))
if __name__=="__main__": main()
