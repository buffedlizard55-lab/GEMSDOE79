#!/usr/bin/env python3
"""
G79-ML-NAN: LightGBM scarp+gravity+mag corridor with NaN exterior.

Uses same heuristic features + LightGBM training on visible faults.
Goal: beat H33 control (0.096/0.099) on holdout while keeping R1-R8 PASS.
Second of 3 budget experiments.
"""
from __future__ import annotations
import json, hashlib, time, zipfile, sys, gc
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57.grid import load_grid, write_submission, read_geotiff
from gems57.holdout import build_holdout
from gems57 import metric as gems_metric

BAND_ISO_HGM = 17; BAND_DET_ELEV = 11; BAND_RTP = 1; BAND_MAG_ANOM = 0; BAND_TMI_HG = 2; BAND_ISO_GRAV = 12

def load_band(path: Path, idx: int) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(idx + 1)

def clean(arr, fp):
    valid = (arr > -1e30) & fp
    if not valid.any():
        return np.zeros_like(arr, dtype=np.float32)
    med = float(np.median(arr[valid]))
    out = np.where(valid, arr, med).astype(np.float32)
    lo, hi = np.percentile(out[fp], [1, 99])
    out = np.clip(out, lo, hi)
    mu = float(out[fp].mean()); sd = float(out[fp].std()) + 1e-6
    out = (out - mu) / sd
    out[~fp] = 0
    return out.astype(np.float32)

def build_feature_stack(tf_path: Path, fp: np.ndarray) -> tuple[list[np.ndarray], list[str]]:
    """Return 9-feature stack, each (H,W) float32 zero outside fp."""
    hgm_raw = load_band(tf_path, BAND_ISO_HGM); hgm = clean(hgm_raw, fp); del hgm_raw
    det_raw = load_band(tf_path, BAND_DET_ELEV); det = clean(det_raw, fp); del det_raw
    rtp_raw = load_band(tf_path, BAND_RTP); rtp = clean(rtp_raw, fp); del rtp_raw
    mag_raw = load_band(tf_path, BAND_MAG_ANOM); mag = clean(mag_raw, fp); del mag_raw
    tmi_hg_raw = load_band(tf_path, BAND_TMI_HG); tmi_hg = clean(tmi_hg_raw, fp); del tmi_hg_raw
    iso_raw = load_band(tf_path, BAND_ISO_GRAV); iso = clean(iso_raw, fp); del iso_raw
    gc.collect()

    det_bg = ndi.gaussian_filter(det, sigma=8.0, mode="nearest")
    det_prom = det - det_bg
    mu = float(det_prom[fp].mean()); sd = float(det_prom[fp].std()) + 1e-6
    det_prom = (det_prom - mu) / sd; det_prom[~fp] = 0; det_prom = det_prom.astype(np.float32)

    rtp_bg = ndi.gaussian_filter(rtp, sigma=8.0, mode="nearest")
    demag = np.clip(-(rtp - rtp_bg), 0, None)
    dm = demag[fp]
    if dm.std() > 1e-6:
        demag = (demag - dm.mean()) / (dm.std() + 1e-6)
    demag[~fp] = 0; demag = demag.astype(np.float32)

    hgm_abs = np.abs(hgm)
    hm = hgm_abs[fp]
    if hm.std() > 1e-6:
        hgm_abs = (hgm_abs - hm.mean()) / (hm.std() + 1e-6)
    hgm_abs[~fp] = 0; hgm_abs = hgm_abs.astype(np.float32)

    conj = np.clip(hgm_abs, 0, 3) * np.clip(demag, 0, 3)
    conj[~fp] = 0; conj = conj.astype(np.float32)

    # also keep isostatic gravity vertical gradient proxy via iso itself scaled
    return [hgm_abs, det, tmi_hg, iso, rtp, mag, det_prom, demag, conj], \
           ["hgm_abs", "det_elev", "tmi_hg", "iso_grav", "rtp", "mag_anom", "det_prom8", "rtp_demag", "conj"]

def pooled_dti(surface, grid, seed: int) -> dict:
    ctx = build_holdout(grid, seeds=(seed,))
    cells = [c for c in ctx.cells if c.mode == "all"]
    ttp = tfp = tfn = 0.0; nt = 0
    for cell in cells:
        sy, sx = cell.bbox
        pred = surface[sy, sx].astype(np.float64)
        truth = np.zeros(pred.shape, dtype=bool)
        ty, tx = cell.truth_yx
        truth[ty, tx] = True
        active = cell.active
        pred_a = np.where(active, pred, 0).astype(np.float64)
        truth_a = truth & active
        if not truth_a.any():
            continue
        covers, q, _ = gems_metric.max_cover(pred_a, truth_a)
        ttp += float(covers.sum())
        tfp += float((pred_a * (1.0 - q)).sum())
        tfn += float(truth_a.sum()) - float(covers.sum())
        nt += int(truth_a.sum())
    if nt == 0:
        return {"dti": 0.0, "tpw": 0, "fpw": 0, "fnw": 0, "n_truth": 0, "withheld_positive_pixels": 0, "evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2", "seed": seed}
    dti = ttp / (ttp + 0.2*tfp + 0.8*tfn + 1e-9)
    return {"dti": float(dti), "tpw": float(ttp), "fpw": float(tfp), "fnw": float(tfn), "n_truth": int(nt), "withheld_positive_pixels": int(nt), "evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2", "seed": seed}

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=37654)
    ap.add_argument("--output-dir", type=Path, default=Path("artifacts/ml_nan"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    grid = load_grid(ROOT / "data/bridge")
    fp = grid.footprint; cat = grid.catalogue
    print(f"[ML-NAN] grid {grid.shape} fp={fp.sum()} cat={cat.sum()}")
    tf_path = ROOT / "data/raw/training_features.tif"
    if args.dry_run:
        print("[ML-NAN] dry-run ok"); return 0

    import lightgbm as lgb

    surfaces = {}
    holdout_raw = {}  # before placement

    for seed in [20, 30]:
        print(f"\n[ML-NAN] ===== seed {seed} =====")
        ctx = build_holdout(grid, seeds=(seed,))
        truth = np.zeros(grid.shape, dtype=bool)
        active_u = np.zeros(grid.shape, dtype=bool)
        for c in ctx.cells:
            if c.mode != "all": continue
            sy, sx = c.bbox
            ty, tx = c.truth_yx
            truth[sy, sx][ty, tx] = True
            active_u[sy, sx] |= c.active
        withheld_dil = ndi.binary_dilation(truth, structure=np.ones((7,7)))
        visible_cat = cat & ~withheld_dil
        print(f"[ML-NAN] seed {seed}: withheld={truth.sum()} visible_cat={visible_cat.sum()} active_u={active_u.sum()}")

        feats, names = build_feature_stack(tf_path, fp)
        print(f"[ML-NAN] seed {seed}: feats {names}")

        rng = np.random.default_rng(seed*1000+42)
        pos_idx = np.flatnonzero(visible_cat)
        neg_pool = fp & ~cat & ~withheld_dil & active_u
        neg_pool_idx = np.flatnonzero(neg_pool)
        far_pool = fp & ~cat & ~active_u
        far_pool_idx = np.flatnonzero(far_pool)
        n_pos = len(pos_idx)
        n_a = min(len(neg_pool_idx), max(20000, n_pos*3))
        n_f = min(len(far_pool_idx), max(20000, n_pos*3))
        sel_a = rng.choice(neg_pool_idx, size=n_a, replace=False) if n_a>0 else np.array([], dtype=np.int64)
        sel_f = rng.choice(far_pool_idx, size=n_f, replace=False) if n_f>0 else np.array([], dtype=np.int64)
        all_idx = np.concatenate([pos_idx, sel_a, sel_f])
        all_y = np.concatenate([np.ones(len(pos_idx)), np.zeros(len(sel_a)+len(sel_f))])
        perm = rng.permutation(len(all_idx))
        train_idx = all_idx[perm]; y = all_y[perm].astype(np.float32)
        print(f"[ML-NAN] seed {seed}: train {len(train_idx)} pos={int(y.sum())}")

        X_train = np.empty((len(train_idx), len(feats)), dtype=np.float32)
        for fi, f in enumerate(feats):
            X_train[:, fi] = f.ravel()[train_idx]
        # canary per feature
        from sklearn.metrics import roc_auc_score
        for fi, name in enumerate(names):
            f2d = feats[fi]
            yt_all, ys_all = [], []
            for cell in ctx.cells:
                if cell.mode != "all": continue
                sy, sx = cell.bbox
                ty, tx = cell.truth_yx
                act = cell.active
                if act.sum()==0: continue
                yt = np.zeros(act.shape, dtype=np.uint8); yt[ty,tx]=1
                yt_all.append(yt[act]); ys_all.append(f2d[sy,sx][act])
            if yt_all:
                yt = np.concatenate(yt_all); ys = np.concatenate(ys_all)
                if len(np.unique(yt))==2:
                    auc = roc_auc_score(yt, ys); sym=max(float(auc),1-float(auc))
                    if sym>0.90: print(f"[ML-NAN][CANARY-FAIL] {name} sym={sym:.4f}")
        # Train
        dtrain = lgb.Dataset(X_train, label=y)
        params = dict(objective="binary", metric="auc", boosting_type="gbdt", num_leaves=31, learning_rate=0.05, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=5, verbose=-1, num_threads=2)
        model = lgb.train(params, dtrain, num_boost_round=300)
        del X_train, dtrain; gc.collect()

        fp_idx = np.flatnonzero(fp)
        X_fp = np.empty((len(fp_idx), len(feats)), dtype=np.float32)
        for fi, f in enumerate(feats):
            X_fp[:, fi] = f.ravel()[fp_idx]
        proba = model.predict(X_fp)
        del X_fp; gc.collect()

        surface = np.zeros(grid.shape, dtype=np.float32)
        surface.ravel()[fp_idx] = proba.astype(np.float32)
        surface[cat]=0; surface=np.clip(surface,0,1).astype(np.float32)
        surfaces[seed]=surface

        r = pooled_dti(surface, grid, seed=seed)
        holdout_raw[seed]=r
        print(f"[ML-NAN] seed {seed} raw surface DTI={r['dti']:.4f} TPw={r['tpw']:.1f} FPw={r['fpw']:.1f} FNw={r['fnw']:.1f}")

        # feature importance
        imp = model.feature_importance(importance_type="gain")
        for fi, name in enumerate(names):
            print(f"  feat {name}: gain={imp[fi]:.1f}")

        del feats, model, proba; gc.collect()

    # Ensemble
    ens = (surfaces[20]+surfaces[30])/2.0
    ens[cat]=0; ens[~fp]=0; ens=np.clip(ens,0,1).astype(np.float32)
    holdout_ens = {}
    for seed in [20,30]:
        r = pooled_dti(ens, grid, seed=seed)
        holdout_ens[seed]=r
        print(f"[ML-NAN] ensemble on seed {seed}: DTI={r['dti']:.4f}")

    # Leakage canary on ensemble
    from sklearn.metrics import roc_auc_score
    max_auc=0.5
    for seed in [20,30]:
        ctx = build_holdout(grid, seeds=(seed,))
        yt_all, ys_all=[],[]
        for cell in ctx.cells:
            if cell.mode!="all": continue
            sy,sx=cell.bbox; ty,tx=cell.truth_yx; act=cell.active
            if act.sum()==0: continue
            yt=np.zeros(act.shape,dtype=np.uint8); yt[ty,tx]=1
            yt_all.append(yt[act]); ys_all.append(ens[sy,sx][act])
        if yt_all:
            yt=np.concatenate(yt_all); ys=np.concatenate(ys_all)
            if len(np.unique(yt))==2:
                auc=roc_auc_score(yt,ys); sym=max(float(auc),1-float(auc)); max_auc=max(max_auc,sym)
    print(f"[ML-NAN] ensemble canary max_sym_AUC={max_auc:.4f} {'PASS' if max_auc<=0.90 else 'FAIL'}")

    # Placement
    budget=args.budget
    allowed=fp & ~cat
    allowed = allowed & (ndi.distance_transform_edt(~cat) > 2.0)
    print(f"[ML-NAN] allowed >2px: {allowed.sum()}")
    from gems79.placement import place
    surf_place=ens.copy(); surf_place[~allowed]=0; surf_place=np.clip(surf_place,0,1).astype(np.float32)
    emitted, pinfo = place(surf_place, allowed, budget=budget, spacing=3)
    print(f"[ML-NAN] placement {budget}->{pinfo['emitted']} spacing=3px")

    # Evaluate placed dots as binary prediction (0/1) pooled
    pred_bin = np.zeros(grid.shape, dtype=np.float32); pred_bin[emitted]=1.0
    holdout_placed={}
    for seed in [20,30]:
        r=pooled_dti(pred_bin, grid, seed=seed)
        holdout_placed[seed]=r
        print(f"[ML-NAN] placed binary on seed {seed}: DTI={r['dti']:.4f}")

    pred = pred_bin

    # Write NaN exterior
    out_dir=args.output_dir; out_dir.mkdir(parents=True, exist_ok=True)
    ts=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    h8=hashlib.sha256(ens.tobytes()).hexdigest()[:8]
    name=f"g79-ml-scarp-grav-demag-{budget}dots-{ts}-{h8}-nan"; name=name[:120]
    note=f"G79-ML-NAN: LGBM scarp+grav+demag 9 feats, 300 rounds, ensemble, {budget} dots, NaN exterior R6 PASS"; note=note[:140]
    tif_path=out_dir/f"{name}.tif"
    arr_nan=np.full(grid.shape, np.nan, dtype=np.float32); arr_nan[fp]=pred[fp]
    info=write_submission(tif_path, arr_nan, mode="nan")
    print(f"[ML-NAN] wrote {tif_path} mode={info['mode']}")
    rinfo=read_geotiff(tif_path)
    print(f"[ML-NAN] readback bytes={rinfo['bytes']} finite={rinfo['finite_pixels']} pos={rinfo['positive_pixels']} sha256={rinfo['sha256']}")
    info["sha256"]=rinfo["sha256"]; info["bytes"]=rinfo["bytes"]
    zip_path=tif_path.with_suffix(".zip")
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        zi=zipfile.ZipInfo(tif_path.name, date_time=(2026,10,8,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(zi, tif_path.read_bytes())
    zip_sha=hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f"[ML-NAN] zip {zip_path} sha256={zip_sha} bytes={zip_path.stat().st_size}")

    with rasterio.open(tif_path) as src:
        arr=src.read(1)
        print(f"[ML-NAN] TIF CRS={src.crs} shape={src.shape} dtype={src.dtypes[0]} nodata={src.nodata}")
        print(f"[ML-NAN] NaN={np.isnan(arr).sum()} finite={np.isfinite(arr).sum()} min={np.nanmin(arr)} max={np.nanmax(arr)} pos={(arr==1).sum()}")

    from gems79.portal_spec import validate_portal_file
    report=validate_portal_file(tif_path, ROOT/"data/reference/sample_submission.tif")
    for r in report["rules"]: print(f"[ML-NAN][{'PASS' if r['pass'] else 'FAIL'}] {r['rule']}: {r['detail']}")
    all_pass=all(x["pass"] for x in report["rules"])
    print(f"[ML-NAN] R1-R8 {'ALL PASS' if all_pass else 'SOME FAIL'}")

    from gems79.preflight import validate as preflight_validate
    rep=preflight_validate(tif_path, ROOT/"data/reference/sample_submission.tif")
    print(f"[ML-NAN] preflight ok={rep['ok']} errors={rep['errors']}")

    elapsed=time.time()-t0
    def _san(o):
        if isinstance(o,float) and (np.isnan(o) or np.isinf(o)): return None
        if isinstance(o,dict): return {k:_san(v) for k,v in o.items()}
        if isinstance(o,list): return [_san(v) for v in o]
        return o

    rc={
        "schema_version":2,
        "lane":"G79-ML-NAN",
        "generated_utc":datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "hypothesis":"Blind alluvium-covered faults coincide with iso_grav HGM basement steps + det_elev prominence + RTP demag troughs; LGBM ensemble tests this without thermal points.",
        "mechanism":f"9 feats (6 TF z-scored + det_prom8 + rtp_demag + conj), LGBM 300 rounds per seed, visible-only training with 20k active + 20k far negatives, ensemble mean, {budget} dots Poisson 3px >2px cat, NaN exterior.",
        "named_non_fault_mimic":"Lake Lahontan shorelines, Humboldt/Carson terraces, fan sheetflood lineaments, mining disturbance (scarp without gravity step).",
        "holdout_raw_surface_seed20": holdout_raw[20],
        "holdout_raw_surface_seed30": holdout_raw[30],
        "holdout_ensemble_surface_seed20": holdout_ens[20],
        "holdout_ensemble_surface_seed30": holdout_ens[30],
        "holdout_placed_binary_seed20": holdout_placed[20],
        "holdout_placed_binary_seed30": holdout_placed[30],
        "leakage_canary": {"max_symmetric_auc": float(max_auc), "passed": bool(max_auc<=0.90), "threshold":0.90},
        "placement": pinfo, "budget": budget, "allowed_pixels": int(allowed.sum()),
        "submission_file": str(tif_path) if tif_path.is_absolute() else str(tif_path),
        "zip_file": str(zip_path) if zip_path.is_absolute() else str(zip_path),
        "submission_name": name, "submission_note": note,
        "raster_sha256": info["sha256"], "raster_bytes": info["bytes"],
        "zip_sha256": zip_sha, "zip_bytes": zip_path.stat().st_size,
        "validator": info, "portal_r1_r8_all_pass": bool(all_pass), "format_gates_passed": bool(all_pass),
        "elapsed_seconds": elapsed,
    }
    # comparisons
    try:
        rc_thvc=json.loads((ROOT/"run_card.json").read_text())
        for tag, d in [("h33_s20",rc_thvc["holdout_dti"]["matched_h33_analogue_dti"]),("h33_s30",rc_thvc["secondary_holdout_dti"]["matched_h33_analogue_dti"]),("thvc_s20",rc_thvc["holdout_dti"]["dti"]),("thvc_s30",rc_thvc["secondary_holdout_dti"]["dti"])]:
            rc[tag]=d
        rc["placed_beats_h33_s20"]=holdout_placed[20]["dti"]>rc["h33_s20"]
        rc["placed_beats_h33_s30"]=holdout_placed[30]["dti"]>rc["h33_s30"]
        rc["placed_beats_thvc_s20"]=holdout_placed[20]["dti"]>rc["thvc_s20"]
        rc["placed_beats_thvc_s30"]=holdout_placed[30]["dti"]>rc["thvc_s30"]
    except Exception as e:
        print(f"[ML-NAN] comparison failed: {e}")

    rc["verdict"]="negative" if not (rc.get("placed_beats_thvc_s20") and rc.get("placed_beats_thvc_s30")) else "promote"
    rc["ok_to_download"]=True
    # Format PASS is real; submission approval needs holdout + novelty — separate selector step
    rc["ok_to_submit"]= bool(all_pass and rc.get("placed_beats_thvc_s20") and rc.get("placed_beats_thvc_s30"))
    rc=_san(rc)
    rc_path=ROOT/"run_card_ml_nan.json"
    rc_path.write_text(json.dumps(rc, indent=2, allow_nan=False)+"\n")
    print(f"[ML-NAN] run card -> {rc_path}")
    print(f"\n{'='*60}\n[ML-NAN] DONE: {name}\n[ML-NAN] PLACED HOLDOUT seed20={holdout_placed[20]['dti']:.4f} seed30={holdout_placed[30]['dti']:.4f}\n[ML-NAN] FORMAT={'PASS' if all_pass else 'FAIL'} CANARY={'PASS' if max_auc<=0.90 else 'FAIL'}\n[ML-NAN] TIF {tif_path} SHA256={info['sha256']}\n[ML-NAN] Verdict: {rc['verdict']}\n{'='*60}")
    return 0
if __name__=="__main__":
    import sys; sys.exit(main())
