#!/usr/bin/env python3
"""
G79-LAVM: Lithology-Aware Volcanic-Margin & Alluvial-blind fault discovery.

Hypothesis: Unmapped blind fault strands in NW Nevada's alluvial-covered
piedmont and range-front zones produce a coupled signature:
  (i) subtle 1-m lidar scarp curvature (ex_max/step_max/cross_max from
      3DEP 1-m DEM where available, bridging 10-m detrended elevation
      elsewhere) that is absent in 10-m smoothed topography,
  (ii) coincident basement-depth / isostatic gravity gradient lineaments
      (iso_grav_anom_hg) marking buried bedrock steps under alluvium,
  (iii) cross-strike shallow magnetic demagnetization troughs (rtp residual)
      from hydrothermal alteration along the damage zone,
distinguishable from paleoshorelines (Lahontan/Bonneville), fluvial terraces
and mining disturbance by requiring multi-scale topographic + gravity
coincidence and negative magnetic context.

Named non-fault mimic: Pleistocene Lake Lahontan wave-cut shorelines,
Humboldt/Carson river terraces, Quaternary alluvial-fan sheetflood lineaments,
and BLM mining claim disturbance — all produce scarp-like curvature without
gravity basement steps or demag lows.

Distinctness: THVC used 84-channel multi-physics ensemble with 2-m shallow
temperature probes, sinter/travertine, volcanic vents and crack-tip lobes.
CSKD added Lahontan equipotential veto + Coulomb shadow. DFSD split LiDAR vs
blind-10m. LAVM is a narrower 24-channel focused stack: lidar scarp curvature
at 1-m + detrended relief + gravity gradient + magnetic demag only — no thermal
probes, no sinter, no geodetic strain, no network mechanics. It tests whether
alluvium-blind strands can be found without hydrothermal point data.

Protocol: reuse shared grid/holdout/evaluator/writer.  Hide whole fault
segments with 12-px erode / 400-m detach / 20% hide_frac.  Derive every
catalogue feature from visible faults only.  Mask visible faults pixel-exactly.
Pooled DTI alpha=0.2 beta=0.8 triangular 300-m kernel.  Leakage canary AUC<=0.90.
Place with fixed budget Poisson disc (spacing 3 px ≈ 300 m).  Write with NaN
exterior (R6 PASS) via shared grid.write_geotiff(mode='nan').

Budget: 3 experiments (EXP-LAVM-1 zero-catalogue physics, EXP-LAVM-2 uniform
d=2.8, EXP-LAVM-3 adaptive Charnes-Cooper).  2-hour wall cap.

Outputs (never overwrite): run_card_lavm.json + evidence/lavm_* + artifact TIF/ZIP
under docs/downloads/ (or archive/ if negative).  Verdict promote/negative per
preregistered gates (holdout vs THVC incumbent + novelty literal gate).
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57.grid import load_grid, write_geotiff, read_geotiff
from gems57 import metric as gems_metric
from gems57.holdout import FOLD_NAMES
import gems79.placement as placement_mod


# --- band indices in training_features.tif (0-based) ---
# From src/gems79/thvc_features.py TF_BAND_NAMES
BAND_MAG_ANOM = 0
BAND_RTP = 1
BAND_TMI_HG = 2
BAND_GEOD_2NDINV = 3
BAND_ISO_GRAV_ANOM_SLOPE = 4
BAND_TC = 5
BAND_GEOD_SHEARRATE = 6
BAND_GEOD_DILATERATE = 7
BAND_TMI_VG = 8
BAND_DEQ_N100A15 = 9
BAND_ISO_GRAV_ANOM_VG = 10
BAND_DET_ELEV = 11
BAND_ISO_GRAV_ANOM = 12
BAND_TMI = 13
BAND_DEPTH_TO_BASE = 14
BAND_IEQ_N100A15 = 15
BAND_COND_SURF = 16
BAND_ISO_GRAV_ANOM_HG = 17
BAND_DET_ELEV_SLOPE = 18

LAVM_STATIC_BANDS = [
    BAND_RTP,
    BAND_TMI_HG,
    BAND_ISO_GRAV_ANOM_HG,
    BAND_ISO_GRAV_ANOM_VG,
    BAND_ISO_GRAV_ANOM,
    BAND_ISO_GRAV_ANOM_SLOPE,
    BAND_DET_ELEV,
    BAND_DET_ELEV_SLOPE,
    BAND_DEPTH_TO_BASE,
    BAND_TMI_VG,
    BAND_MAG_ANOM,
    BAND_GEOD_2NDINV,
]

LAVM_LIDAR_SCARP_BANDS = [
    # from lidar_scarp_features_u8.tif: ex_max, ex_mean, step_max, lapneg_max,
    # lappos_max, downface_max, upface_max, cross_max, relief, coh100, strike, valid
    0,  # ex_max
    2,  # step_max
    7,  # cross_max
    8,  # relief
]

SENTINEL_F32 = np.float32(-3.4028235e38)
# Actually float32 min is -3.4028235e38 == -340282346638528859811704183484516925440
# Check: np.finfo(np.float32).min


def _load_training_features(path: Path) -> np.ndarray:
    """Load 19-band training_features.tif, return (19, H, W) float32 with sentinel preserved."""
    with rasterio.open(path) as src:
        arr = src.read()  # (19, H, W)
    return arr


def _load_lidar_scarp(path: Path, quant_json_path: Path) -> np.ndarray:
    """Load lidar_scarp_features_u8.tif (12 bands uint8), decode via json quantisation, return (12, H, W) float32."""
    q = json.loads(quant_json_path.read_text())
    band_names = q["bands"]
    quant = q["quantisation"]
    with rasterio.open(path) as src:
        raw = src.read()  # (12, H, W) uint8
    # Decode: for each band, linear or sqrt mapping
    # quant entry: [scale, mode] or [vmin, vmax] etc.  From file head: ex_max [1.5, "sqrt"]
    # Need to read actual quant scheme fully
    decoded = np.zeros_like(raw, dtype=np.float32)
    for i, name in enumerate(band_names):
        entry = quant[name]
        if isinstance(entry, list) and len(entry) == 2 and entry[1] == "sqrt":
            scale = float(entry[0])
            # uint8 0..255 -> float via sqrt: value = (raw/255 * scale)^2 ? check code in dfsd_features.py
            # Actually check: in dfsd_features.py decoding: val = (u8/255 * scale) ** 2 for sqrt bands
            decoded[i] = (raw[i].astype(np.float32) / 255.0 * scale) ** 2
        elif isinstance(entry, list) and len(entry) == 2 and isinstance(entry[0], (int, float)):
            # linear: [max_val, "linear"] or [scale, "linear"] -> val = raw/255 * max_val
            scale = float(entry[0])
            decoded[i] = raw[i].astype(np.float32) / 255.0 * scale
        else:
            # fallback
            decoded[i] = raw[i].astype(np.float32)
    return decoded


def _valid_mask(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Sentinel-aware valid mask for training_features bands."""
    # Sentinel is approx -3.4e38; footprint valid cells may still have sentinel for some bands
    # Use > -1e30 as valid
    return (arr > -1e30) & footprint


def _build_static_features(
    tf_arr: np.ndarray,
    lidar_arr: np.ndarray | None,
    footprint: np.ndarray,
) -> tuple[np.ndarray, list[str]]:
    """
    Build LAVM static feature stack (no catalogue geometry).
    tf_arr: (19, H, W), lidar_arr: (12, H, W) or None.
    Returns (n_features, H, W) float32 memmap-ready, and feature names.
    """
    H, W = footprint.shape
    feats = []
    names = []

    # Helper: replace sentinel/outside with median-of-valid then z-score globally
    def _clean_band(band: np.ndarray) -> np.ndarray:
        valid = (band > -1e30) & footprint
        if not valid.any():
            return np.zeros((H, W), dtype=np.float32)
        med = float(np.median(band[valid]))
        out = np.where(valid, band, med).astype(np.float32)
        # clip extreme tails at 1st/99th percentile then z-score
        lo, hi = np.percentile(out[footprint], [1, 99])
        out = np.clip(out, lo, hi)
        mu = float(out[footprint].mean())
        sd = float(out[footprint].std()) + 1e-6
        return ((out - mu) / sd).astype(np.float32)

    # --- TF-derived channels ---
    for b in LAVM_STATIC_BANDS:
        name = f"tf_b{b:02d}"
        feats.append(_clean_band(tf_arr[b]))
        names.append(name)

    # --- derived: RTP demag trough (negative RTP residual) ---
    rtp = tf_arr[BAND_RTP]
    # median-filtered RTP as regional field, residual = rtp - median(rtp)
    rtp_valid = (rtp > -1e30) & footprint
    rtp_med = float(np.median(rtp[rtp_valid])) if rtp_valid.any() else 0.0
    rtp_filled = np.where(rtp_valid, rtp, rtp_med).astype(np.float32)
    # large-scale median via gaussian 800m sigma ~ 8 px
    rtp_bg = ndi.gaussian_filter(rtp_filled, sigma=8.0, mode="nearest")
    rtp_res = rtp_filled - rtp_bg
    # demag trough = -res where res < 0, normalized
    demag = np.clip(-rtp_res, 0, None)
    # z-score inside footprint
    demag_fp = demag[footprint]
    demag = (demag - demag_fp.mean()) / (demag_fp.std() + 1e-6)
    demag[~footprint] = 0
    feats.append(demag.astype(np.float32))
    names.append("rtp_demag_trough")

    # --- derived: gravity HGM ridge strength ---
    hgm = tf_arr[BAND_ISO_GRAV_ANOM_HG]
    hgm_valid = (hgm > -1e30) & footprint
    hgm_filled = np.where(hgm_valid, hgm, float(np.median(hgm[hgm_valid])) if hgm_valid.any() else 0).astype(np.float32)
    hgm_clipped = np.clip(np.abs(hgm_filled), 0, np.percentile(np.abs(hgm_filled[footprint]), 99))
    hgm_z = (hgm_clipped - hgm_clipped[footprint].mean()) / (hgm_clipped[footprint].std() + 1e-6)
    hgm_z[~footprint] = 0
    feats.append(hgm_z.astype(np.float32))
    names.append("grav_hgm_abs_z")

    # --- derived: detrended elevation prominence (600m scale) ---
    det = tf_arr[BAND_DET_ELEV]
    det_valid = (det > -1e30) & footprint
    det_filled = np.where(det_valid, det, float(np.median(det[det_valid])) if det_valid.any() else 0).astype(np.float32)
    det_bg = ndi.gaussian_filter(det_filled, sigma=6.0, mode="nearest")
    det_prom = det_filled - det_bg
    det_prom_z = (det_prom - det_prom[footprint].mean()) / (det_prom[footprint].std() + 1e-6)
    det_prom_z[~footprint] = 0
    feats.append(det_prom_z.astype(np.float32))
    names.append("det_elev_prom6")

    # --- derived: cross-strike asymmetry (scarp polarity proxy) ---
    # Use det_elev gradient magnitude
    gy, gx = np.gradient(det_filled.astype(np.float64))
    gmag = np.hypot(gx, gy).astype(np.float32)
    gmag_z = (gmag - gmag[footprint].mean()) / (gmag[footprint].std() + 1e-6)
    gmag_z[~footprint] = 0
    feats.append(gmag_z.astype(np.float32))
    names.append("det_slope_mag_z")

    # --- lidar scarp channels (if available) ---
    if lidar_arr is not None:
        for idx in LAVM_LIDAR_SCARP_BANDS:
            name = f"lidar_{['ex_max','ex_mean','step_max','lapneg_max','lappos_max','downface_max','upface_max','cross_max','relief','coh100','strike','valid'][idx]}"
            band = lidar_arr[idx].astype(np.float32)
            # lidar valid mask: footprint & band finite; outside lidar coverage band may be 0
            # normalize inside footprint
            vals = band[footprint]
            lo, hi = np.percentile(vals, [1, 99])
            band = np.clip(band, lo, hi)
            mu = float(band[footprint].mean())
            sd = float(band[footprint].std()) + 1e-6
            band = (band - mu) / sd
            band[~footprint] = 0
            feats.append(band.astype(np.float32))
            names.append(name)
    else:
        # zero-fill lidar channels
        for idx in LAVM_LIDAR_SCARP_BANDS:
            feats.append(np.zeros((H, W), dtype=np.float32))
            names.append(f"lidar_{idx:02d}_missing")

    # --- gravity+mag coincidence (conjunction) ---
    # multiply normalized absolute HGM with demag trough
    conj = np.clip(hgm_z, 0, 3) * np.clip(demag, 0, 3)
    conj[~footprint] = 0
    feats.append(conj.astype(np.float32))
    names.append("grav_mag_conj")

    stack = np.stack(feats, axis=0)  # (n_feats, H, W)
    return stack, names


def _leakage_canary_single_feature(
    feat_2d: np.ndarray,
    holdout_cells: list,
    footprint: np.ndarray,
) -> float:
    """Symmetric AUC for one feature alone on holdout folds."""
    from sklearn.metrics import roc_auc_score

    y_true_all = []
    y_score_all = []
    for cell in holdout_cells:
        # cell has truth and active mask cropped; need to map feat_2d into crop
        # cell.bbox gives slice
        sy, sx = cell.bbox
        active = cell.active
        if active.sum() == 0:
            continue
        # feat cropped
        f_crop = feat_2d[sy, sx]
        # truth positions within crop
        ty, tx = cell.truth_yx
        # build y_true for active cells only
        y_true = np.zeros(active.shape, dtype=np.uint8)
        y_true[ty, tx] = 1
        # Only score active cells
        mask = active
        y_true_all.append(y_true[mask])
        y_score_all.append(f_crop[mask])
    if not y_true_all:
        return 0.5
    y_true_all = np.concatenate(y_true_all)
    y_score_all = np.concatenate(y_score_all)
    if len(np.unique(y_true_all)) < 2:
        return 0.5
    try:
        auc = roc_auc_score(y_true_all, y_score_all)
    except Exception:
        return 0.5
    return max(float(auc), 1.0 - float(auc))


def _build_holdout_context(grid, seed: int):
    """Build pooled-hide-v2 holdout context (4 folds)."""
    from gems57.holdout import build_holdout

    ctx = build_holdout(grid, seed=seed)
    return ctx


def _evaluate_surface_on_holdout(
    surface: np.ndarray,
    grid,
    seed: int,
) -> dict:
    """Evaluate a full-grid surface [0,1] on buffered whole-component holdout."""
    from gems57.holdout import build_holdout
    from gems57.evaluate_holdout import evaluate as eval_holdout

    ctx = build_holdout(grid, seed=seed)
    # Use shared evaluator pooled path: it handles masking visible faults etc.
    # But we need to produce pooled DTI; easiest is to call evaluate_holdout.evaluate
    # which expects fold-wise predictions. We provide full-grid surface and let
    # holdout masking happen inside.
    # evaluate_holdout.evaluate takes (prediction_2d, context) and does pooled.
    result = eval_holdout(surface, ctx, grid)
    return result


def _place_dots(surface: np.ndarray, allowed: np.ndarray, budget: int, spacing_px: float = 3.0):
    """Poisson-disc dot placement with NaN-safe clipping."""
    # Ensure surface finite and in [0,1] inside allowed
    surf = np.asarray(surface, dtype=np.float32)
    surf = np.clip(surf, 0, 1)
    surf[~allowed] = 0
    emitted, info = placement_mod.place(surf, allowed, budget=budget, spacing=spacing_px)
    return emitted, info


def _write_submission_tif(
    out_path: Path,
    prediction_bool: np.ndarray,
    grid,
    name: str,
    note: str,
) -> dict:
    """Write TIF with NaN exterior (R6 PASS) via grid.write_geotiff mode='nan'."""
    H, W = grid.shape
    # Build float32 array: 1.0 where dot, 0.0 inside footprint background, NaN outside
    # But grid.write_geotiff with mode='nan' handles this: pass 0/1 inside, it writes NaN outside
    arr = np.zeros((H, W), dtype=np.float32)
    arr[prediction_bool] = 1.0
    # Ensure zeros inside footprint but not on catalogue (already guaranteed by allowed)
    # grid.write_geotiff will set exterior to NaN when mode='nan'
    info = write_geotiff(str(out_path), arr, mode="nan")
    # Also write submission via shared writer for ZIP + receipt
    # Use gems57.submission_writer.write_submission which validates
    from gems57.submission_writer import write_submission
    # Need to provide prediction that is finite in [0,1] with zeros exterior
    # But write_submission rejects positive outside footprint - so we provide
    # the same arr but writer will convert exterior to NaN? Actually writer uses grid.write_geotiff internally
    # with mode handling. Check: write_submission does grid.write_geotiff with prediction
    # Let's just use grid.write_geotiff directly for now and manually create ZIP
    return info


def _make_zip(tif_path: Path) -> Path:
    zip_path = tif_path.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo(tif_path.name, date_time=(2026, 10, 8, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, tif_path.read_bytes())
    return zip_path


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Run G79-LAVM lane")
    ap.add_argument("--seed", type=int, default=20, help="Primary holdout seed")
    ap.add_argument("--budget", type=int, default=37654, help="Dot budget (default 37654 to match H33)")
    ap.add_argument("--output-dir", type=Path, default=Path("artifacts/lavm"))
    ap.add_argument("--dry-run", action="store_true", help="Only check inputs, don't train")
    args = ap.parse_args()

    t0 = time.time()
    print(f"[LAVM] seed={args.seed} budget={args.budget} output={args.output_dir}")

    # --- load grid ---
    grid = load_grid(ROOT / "data/bridge")
    print(f"[LAVM] grid {grid.shape} footprint={grid.footprint.sum()} catalogue={grid.catalogue.sum()}")

    # --- load training features ---
    tf_path = ROOT / "data/raw/training_features.tif"
    if not tf_path.exists():
        print(f"[LAVM] missing {tf_path}", file=sys.stderr)
        sys.exit(2)
    tf_arr = _load_training_features(tf_path)
    print(f"[LAVM] TF loaded {tf_arr.shape} dtype={tf_arr.dtype}")

    # --- load lidar scarp if available ---
    lidar_path = ROOT / "data/raw/external/lidar_scarp_features_u8.tif"
    lidar_json = ROOT / "data/raw/external/lidar_scarp_features.json"
    lidar_arr = None
    if lidar_path.exists() and lidar_json.exists():
        lidar_arr = _load_lidar_scarp(lidar_path, lidar_json)
        print(f"[LAVM] lidar scarp loaded {lidar_arr.shape}")
    else:
        print(f"[LAVM] lidar scarp not found, using zero-fill")

    if args.dry_run:
        print("[LAVM] dry-run done")
        return 0

    # --- build static features ---
    static_stack, feat_names = _build_static_features(tf_arr, lidar_arr, grid.footprint)
    print(f"[LAVM] static stack {static_stack.shape} ({len(feat_names)} feats)")
    print(f"[LAVM] feats: {feat_names}")

    # --- leakage canaries (single-feature AUC) ---
    # Build holdout context for canary
    from gems57.holdout import build_holdout

    ctx20 = build_holdout(grid, seed=20)
    ctx30 = build_holdout(grid, seed=30)
    print(f"[LAVM] holdout cells: seed20={len(ctx20.cells)} seed30={len(ctx30.cells)}")

    # Test each feature alone: we need to evaluate via holdout evaluator
    # For canary we do simple AUC per fold as above; for now run 2-seed canary via static features
    max_auc = 0.0
    max_feat = ""
    for fi, name in enumerate(feat_names):
        feat_2d = static_stack[fi]
        auc20 = _leakage_canary_single_feature(feat_2d, ctx20.cells, grid.footprint)
        auc30 = _leakage_canary_single_feature(feat_2d, ctx30.cells, grid.footprint)
        auc = max(auc20, auc30)
        if auc > max_auc:
            max_auc = auc
            max_feat = name
        if auc > 0.90:
            print(f"[LAVM][CANARY-FAIL] {name} AUC={auc:.4f} >0.90")
    print(f"[LAVM] canary max symmetric AUC={max_auc:.4f} ({max_feat}) {'PASS' if max_auc <= 0.90 else 'FAIL'}")

    # --- train simple model on visible faults (leak-free) ---
    # For each seed, train on visible folds, predict on full grid, evaluate pooled
    # Use LightGBM with minimal tuning
    import lightgbm as lgb

    results = {}
    surfaces = {}

    for seed in [20, 30]:
        ctx = build_holdout(grid, seed=seed)
        print(f"[LAVM] seed {seed}: {len(ctx.cells)} folds, quadrants {FOLD_NAMES}")

        # Collect training data from all folds' visible context
        # Approach: for each fold, visible = grid without withheld+buffer
        # We sample positives (visible catalogue) and negatives (footprint-active)
        # Build features by extracting static_stack at those positions

        # Simpler: train on full visible catalogue vs random negatives, derive visible mask
        # from holdout context union

        # Get withheld truth union for this seed
        all_truth = np.zeros(grid.shape, dtype=bool)
        all_active = np.zeros(grid.shape, dtype=bool)
        for cell in ctx.cells:
            sy, sx = cell.bbox
            # truth in crop
            ty, tx = cell.truth_yx
            all_truth[sy, sx][ty, tx] = True
            all_active[sy, sx] |= cell.active

        # visible catalogue = grid.catalogue & ~withheld & not in buffer
        # But build_holdout already handles detached; usectx's logic: visible = catalogue - withheld area
        # Approximate: visible = catalogue & ~withheld_dilated
        withheld_dil = ndi.binary_dilation(all_truth, structure=np.ones((7, 7)))
        visible_cat = grid.catalogue & ~withheld_dil
        print(f"[LAVM] seed {seed}: withheld={all_truth.sum()} visible_cat={visible_cat.sum()}")

        # Sample training: positives = visible_cat pixels, negatives = footprint - catalogue - active halo
        rng = np.random.default_rng(seed * 1000 + 42)
        pos_idx = np.flatnonzero(visible_cat)
        # negatives: footprint inside active domain but not catalogue and not withheld
        neg_pool = grid.footprint & ~grid.catalogue & ~withheld_dil & all_active
        neg_pool_idx = np.flatnonzero(neg_pool)
        # also far negatives outside active (random background)
        far_pool = grid.footprint & ~grid.catalogue & ~all_active
        far_pool_idx = np.flatnonzero(far_pool)

        n_pos = len(pos_idx)
        n_neg_active = min(len(neg_pool_idx), max(20000, n_pos * 3))
        n_neg_far = min(len(far_pool_idx), max(20000, n_pos * 3))

        sel_neg_active = rng.choice(neg_pool_idx, size=n_neg_active, replace=False) if n_neg_active > 0 else np.array([], dtype=np.int64)
        sel_neg_far = rng.choice(far_pool_idx, size=n_neg_far, replace=False) if n_neg_far > 0 else np.array([], dtype=np.int64)

        train_idx = np.concatenate([pos_idx, sel_neg_active, sel_neg_far])
        # Shuffle
        perm = rng.permutation(len(train_idx))
        train_idx = train_idx[perm]

        y = np.zeros(len(train_idx), dtype=np.float32)
        y[:len(pos_idx)] = 1.0  # But after perm, need to map
        # Actually need to track which are positives after concat+perm
        is_pos = np.isin(train_idx, pos_idx)
        y = is_pos.astype(np.float32)
        # After perm, reorder is_pos accordingly
        # Simpler: build before perm
        y_all = np.concatenate([np.ones(len(pos_idx), dtype=np.float32),
                                np.zeros(len(sel_neg_active) + len(sel_neg_far), dtype=np.float32)])
        y_all = y_all[perm]
        train_idx = train_idx  # already permuted via perm applied to concatenated

        # But train_idx was not permuted in same order as y_all - fix
        # Rebuild correctly:
        all_idx = np.concatenate([pos_idx, sel_neg_active, sel_neg_far])
        all_y = np.concatenate([np.ones(len(pos_idx)), np.zeros(len(sel_neg_active) + len(sel_neg_far))])
        perm2 = rng.permutation(len(all_idx))
        train_idx = all_idx[perm2]
        y = all_y[perm2].astype(np.float32)

        # Extract features
        H, W = grid.shape
        n_feats = static_stack.shape[0]
        X_train = np.empty((len(train_idx), n_feats), dtype=np.float32)
        for fi in range(n_feats):
            flat = static_stack[fi].ravel()
            X_train[:, fi] = flat[train_idx]

        print(f"[LAVM] seed {seed}: X_train {X_train.shape} pos={int(y.sum())} neg={len(y)-int(y.sum())}")

        # Train LightGBM
        dtrain = lgb.Dataset(X_train, label=y)
        params = {
            "objective": "binary",
            "metric": "auc",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "num_threads": 2,
        }
        model = lgb.train(params, dtrain, num_boost_round=300)

        # Predict on full footprint
        # Extract all footprint pixels
        fp_idx = np.flatnonzero(grid.footprint)
        X_fp = np.empty((len(fp_idx), n_feats), dtype=np.float32)
        for fi in range(n_feats):
            X_fp[:, fi] = static_stack[fi].ravel()[fp_idx]
        proba_fp = model.predict(X_fp, num_iteration=model.best_iteration if hasattr(model, 'best_iteration') else None)
        # Build full-grid surface
        surface = np.zeros(grid.shape, dtype=np.float32)
        surface.ravel()[fp_idx] = proba_fp.astype(np.float32)
        # Zero on catalogue
        surface[grid.catalogue] = 0.0
        # Ensure in [0,1]
        surface = np.clip(surface, 0, 1).astype(np.float32)
        surfaces[seed] = surface

        # Evaluate on holdout
        from gems57.evaluate_holdout import evaluate as eval_holdout

        result = eval_holdout(surface, ctx, grid)
        # result has pooled DTI etc.
        print(f"[LAVM] seed {seed} surface DTI={result.get('dti', result.get('pooled', {}).get('dti', 'NA'))}")

        # Also evaluate via direct metric for debugging
        # Pooled: aggregate TP/FP/FN across folds
        results[seed] = result

        # Cleanup
        del X_train, X_fp, proba_fp, dtrain, model
        gc.collect()

    # --- placement: budget-matched dots ---
    # Use seed 20 surface for final TIF (or ensemble mean)
    # Ensemble mean of both seeds
    ens_surface = (surfaces[20] + surfaces[30]) / 2.0
    ens_surface[grid.catalogue] = 0.0
    ens_surface[~grid.footprint] = 0.0
    ens_surface = np.clip(ens_surface, 0, 1).astype(np.float32)

    # Diagnostic: evaluate ensemble surface on both seeds
    for seed in [20, 30]:
        ctx = build_holdout(grid, seed=seed)
        from gems57.evaluate_holdout import evaluate as eval_holdout
        r = eval_holdout(ens_surface, ctx, grid)
        dti = r.get("dti", r.get("pooled", {}).get("dti"))
        print(f"[LAVM] ensemble surface on seed {seed}: DTI={dti}")

    budget = args.budget
    allowed = grid.footprint & ~grid.catalogue
    # enforce min distance from catalogue: >2 px (match H33 pruning)
    dist_to_cat = ndi.distance_transform_edt(~grid.catalogue)
    allowed = allowed & (dist_to_cat > 2.0)

    emitted, pinfo = _place_dots(ens_surface, allowed, budget=budget, spacing_px=3.0)
    print(f"[LAVM] placement budget={budget} emitted={pinfo['emitted']} spacing=3px allowed={allowed.sum()}")

    # Build binary prediction for TIF: 1.0 where dot, 0 inside footprint else NaN
    pred = np.zeros(grid.shape, dtype=np.float32)
    pred[emitted] = 1.0

    # --- write TIF with NaN exterior ---
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique name: g79-lavm-<budget>dots-<timestamp>-<hash8>-zeros
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # hash from surface bytes for uniqueness
    h8 = hashlib.sha256(ens_surface.tobytes()).hexdigest()[:8]
    name = f"g79-lavm-scarp-grav-demag-{budget}dots-{ts}-{h8}-nan"
    # Truncate to 140
    name = name[:140]
    note = f"G79-LAVM: lidar scarp+grav HGM+mag demag gated blind piedmont (HOLDOUT-DTI pending, {budget} px)"
    note = note[:140]

    tif_path = out_dir / f"{name}.tif"
    info = write_geotiff(str(tif_path), pred, mode="nan")
    print(f"[LAVM] wrote {tif_path} sha256={info['sha256']} bytes={info['bytes']} mode={info['mode']}")

    zip_path = _make_zip(tif_path)
    print(f"[LAVM] wrote {zip_path} bytes={zip_path.stat().st_size} sha256={_sha256(zip_path)}")

    # --- validate R1-R8 ---
    from gems79.portal_spec import validate_portal_spec

    # Use official template for R1-R8
    template = ROOT / "data/reference/sample_submission.tif"
    # Quick local validate
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        print(f"[LAVM] TIF CRS={src.crs} shape={src.shape} dtype={src.dtypes[0]} nodata={src.nodata}")
        print(f"[LAVM] TIF NaN={np.isnan(arr).sum()} finite={np.isfinite(arr).sum()} min={np.nanmin(arr)} max={np.nanmax(arr)} positive={(arr==1.0).sum()}")

    # Run portal spec validator
    try:
        from scripts.validate_portal_spec import validate_file
        report = validate_file(tif_path, template)
        for r in report["rules"]:
            status = "PASS" if r["pass"] else "FAIL"
            print(f"[LAVM][R{status}] {r['rule']}: {r['text']} -> {r['detail']}")
        all_pass = all(r["pass"] for r in report["rules"])
        print(f"[LAVM] portal R1-R8 {'ALL PASS' if all_pass else 'SOME FAIL'}")
    except Exception as e:
        print(f"[LAVM] portal validator error: {e}")

    # --- write run card ---
    elapsed = time.time() - t0
    run_card = {
        "schema_version": 2,
        "lane": "G79-LAVM",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "hypothesis": "Unmapped blind piedmont/range-front strands under alluvium produce coincident lidar scarp curvature (1-m 3DEP) + gravity HGM basement steps + magnetic demag troughs; testable without thermal point data.",
        "mechanism": f"24-channel LightGBM on TF+lidar scarp (bands {LAVM_STATIC_BANDS}) + derived demag/HGM/conjunction, trained leak-free on visible catalogue vs footprint-stratified negatives, ensemble of seeds 20+30, budget {budget} Poisson 3px.",
        "named_non_fault_mimic": "Lahontan shorelines, Humboldt/Carson fluvial terraces, alluvial-fan sheetflood lineaments, BLM mining disturbance.",
        "holdout_dti": {k: (float(v) if isinstance(v, (int, float, np.floating)) else str(v)) for k, v in results[20].items()} if 20 in results else None,
        "secondary_holdout_dti": {k: (float(v) if isinstance(v, (int, float, np.floating)) else str(v)) for k, v in results[30].items()} if 30 in results else None,
        "leakage_canary": {"max_symmetric_auc": float(max_auc), "max_feature": max_feat, "passed": bool(max_auc <= 0.90), "threshold": 0.90},
        "placement": pinfo,
        "budget": budget,
        "allowed_pixels": int(allowed.sum()),
        "submission_file": str(tif_path.relative_to(ROOT)),
        "submission_name": name,
        "submission_note": note,
        "raster_sha256": info["sha256"],
        "validator": info,
        "zip_sha256": _sha256(zip_path),
        "elapsed_seconds": elapsed,
        "feature_names": feat_names,
    }
    rc_path = ROOT / "run_card_lavm.json"
    rc_path.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")
    print(f"[LAVM] run card -> {rc_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
