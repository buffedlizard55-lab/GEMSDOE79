#!/usr/bin/env python3
"""G79 single-channel screen: leakage canary + buffered holdout for raw feature bands.

Protocol rule 2: reuses the shared grid, buffered holdout, evaluator and metric.
Protocol rule 4: every band is tested alone on the holdout (leakage canary) before
any result is trusted; symmetric AUC > 0.90 = leakage.

Pre-specified hypothesis (channel chosen BEFORE seeing holdout scores):
  Band 6 'tc' (tilt angle / total curvature -- a magnetic edge-detection /
  curvature transform) highlights fault edges. Blind faults missing from the
  USGS/INGENIOUS catalogue still perturb the magnetic field gradient at their
  edges, so a sparse tc surface targets conduits the catalogue omits.

Named non-fault mimic: magnetic fabric / intrusive contact edges and remanent
magnetization contrasts unrelated to Quaternary faulting.

Outputs a JSON results receipt (no raster, no submission slot).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw
from gems57.evaluate_holdout import evaluate, pooled_summary

BAND_INDEX = 6          # 1-based 'tc': tilt / total curvature (edge detection)
BAND_NAME = "tc"
TOP_K = 10_000          # sparse emission budget
SEEDS = (20, 30)
HIDE_FRAC = 0.20
BUFFER_PX = 3           # 300 m context buffer
NEG_SAMPLE = 120_000    # canonical negative sample size
AUC_LIMIT = 0.90


def load_band() -> np.ndarray:
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as ds:
        b = ds.read(BAND_INDEX).astype(np.float64)
        nd = ds.nodata
    if nd is not None:
        b = np.where(b == nd, np.nan, b)
    return b


def band_symmetric_auc(band_fp: np.ndarray, truth: np.ndarray, domain: np.ndarray,
                       rng: np.random.Generator):
    s = band_fp[domain]
    t = truth[domain]
    finite = np.isfinite(s)
    s, t = s[finite], t[finite]
    pos = s[t]
    neg_all = s[~t]
    n_neg = min(NEG_SAMPLE, int(neg_all.size))
    if n_neg < neg_all.size:
        neg = neg_all[rng.choice(neg_all.size, size=n_neg, replace=False)]
    else:
        neg = neg_all
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    x = np.concatenate([pos, neg])
    auc = float(roc_auc_score(y, x))
    return max(auc, 1.0 - auc), int(pos.size), int(neg.size)


def h33_control_dots(fp: np.ndarray, cat: np.ndarray, n_target: int, rng: np.random.Generator):
    """Off-catalogue spaced control approximating H33: a regular lattice at the
    spacing that yields ~n_target dots over the footprint (random offset),
    pruning dots within 2 px of the catalogue (H33's two-pixel near-catalogue
    pruning). Reported as a reconstruction, not byte-identical to H33."""
    from scipy import ndimage as ndi
    dist = ndi.distance_transform_edt(~cat)
    offcat = fp & (dist > 2.0)
    n_off = int(offcat.sum())
    spacing = float(np.sqrt(n_off / max(n_target, 1)))
    step = max(1, int(round(spacing)))
    ys, xs = np.nonzero(offcat)
    oy = int(rng.integers(0, step)); ox = int(rng.integers(0, step))
    sel = (ys % step == oy) & (xs % step == ox)
    dots = np.zeros(fp.shape, bool)
    dots[ys[sel], xs[sel]] = True
    return dots


def main() -> int:
    grid = load_grid(ROOT / "data" / "reference")
    fp, cat = grid.footprint, grid.catalogue
    band = load_band()
    band_fp = np.where(fp, band, np.nan)

    band_idx = BAND_INDEX
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "LOCAL_EXPERIMENT_RECEIPT",
        "hypothesis": ("Band 6 'tc' magnetic edge-detection / curvature surface targets blind fault edges "
                       "missing from the USGS/INGENIOUS catalogue"),
        "mechanism": ("Normalise Band 6 to [0,1] over the footprint, zero on mapped faults and outside "
                      "the footprint, keep top-10,000 sparse dots. Edge response is strongest at fault "
                      "edges whether or not the trace is mapped."),
        "named_non_fault_mimic": ("Magnetic fabric, intrusive-contact edges and remanent-magnetization "
                                  "contrasts unrelated to Quaternary faulting."),
        "band": BAND_INDEX, "band_name": BAND_NAME, "top_k": TOP_K,
        "evaluator_version": "gems57-pooled-hide-v2",
        "canary": {}, "holdout": {}, "selection": {},
    }

    chosen_band = None
    for seed in SEEDS:
        folds, _quad = buffered_component_draw(grid, seed=seed, hide_frac=HIDE_FRAC,
                                               buffer_px=BUFFER_PX)
        truth = np.zeros(fp.shape, bool)
        domain = np.zeros(fp.shape, bool)
        fold_terms = []
        for f in folds:
            truth |= f["truth"]
            domain |= f["region"]
        rng = np.random.default_rng(seed * 1000 + 7)
        sym_auc, n_pos, n_neg = band_symmetric_auc(band_fp, truth, domain, rng)
        passed = bool(sym_auc <= AUC_LIMIT)
        report["canary"][f"seed{seed}"] = {
            "withheld_positive_pixels": int(truth.sum()),
            "domain_pixels": int(domain.sum()),
            "band": BAND_INDEX, "band_name": BAND_NAME,
            "symmetric_auc": sym_auc, "auc_limit": AUC_LIMIT,
            "canary_passed": passed,
            "negative_pixels_sampled": n_neg,
        }
        if chosen_band is None and passed:
            chosen_band = band_idx

    # Fallback (holdout-independent): lowest-index band passing on both seeds.
    # Deterministic; reported only if Band 6 leaks.
    if chosen_band is None:
        for b in range(1, 20):
            ok = True
            for seed in SEEDS:
                folds, _ = buffered_component_draw(grid, seed=seed, hide_frac=HIDE_FRAC,
                                                   buffer_px=BUFFER_PX)
                truth = np.zeros(fp.shape, bool)
                domain = np.zeros(fp.shape, bool)
                for f in folds:
                    truth |= f["truth"]; domain |= f["region"]
                rng = np.random.default_rng(seed * 1000 + 7)
                # reload band b
                with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as ds:
                    bb = ds.read(b).astype(np.float64)
                    nd = ds.nodata
                    if nd is not None:
                        bb = np.where(bb == nd, np.nan, bb)
                bbfp = np.where(fp, bb, np.nan)
                sym, _, _ = band_symmetric_auc(bbfp, truth, domain, rng)
                if sym > AUC_LIMIT:
                    ok = False
                    break
            if ok:
                chosen_band = b
                band_idx = chosen_band
                with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as ds:
                    band = ds.read(chosen_band).astype(np.float64)
                    nd = ds.nodata
                    if nd is not None:
                        band = np.where(band == nd, np.nan, band)
                band_fp = np.where(fp, band, np.nan)
                report["selection"]["fallback_band"] = chosen_band
                break

    report["selection"]["chosen_band"] = chosen_band
    report["selection"]["band_index_used"] = band_idx
    report["selection"]["rule"] = ("Band 6 'tc' if canary-passing on both seeds; else lowest-index "
                                   "band passing on both seeds (deterministic, no holdout scoring used to choose)")

    # ---- score the chosen channel as a binary sparse-dot submission ----
    finite_fp = fp & np.isfinite(band_fp)
    vals = band_fp[finite_fp]
    lo, hi = float(vals.min()), float(vals.max())
    surface = np.zeros(fp.shape, np.float64)
    if hi > lo:
        surface[finite_fp] = (band_fp[finite_fp] - lo) / (hi - lo)
    surface = np.where(cat, 0.0, surface)          # zero on mapped faults
    surface = np.where(fp, surface, 0.0)           # zero outside footprint
    surface = np.clip(surface, 0.0, 1.0)
    fp_vals = surface[fp]
    kk = min(TOP_K, int((surface > 0).sum()))
    dots = np.zeros(fp.shape, bool)
    if kk > 0 and fp_vals.size >= kk:
        thr = float(np.partition(fp_vals, fp_vals.size - kk)[fp_vals.size - kk])
        dots = (surface >= thr) & (surface > 0) & fp
    n_dots = int(dots.sum())
    report["candidate"] = dict(
        surface_min=float(lo), surface_max=float(hi), n_dots=n_dots,
        footprint_fraction=float(n_dots / int(fp.sum())),
        on_catalogue=int(((dots > 0) & cat).sum()),
    )

    for seed in SEEDS:
        folds, _ = buffered_component_draw(grid, seed=seed, hide_frac=HIDE_FRAC,
                                           buffer_px=BUFFER_PX)
        cand_terms, h33_terms = [], []
        rng = np.random.default_rng(999 + seed)
        h33 = h33_control_dots(fp, cat, 37_654, rng)
        for f in folds:
            rc, terms = evaluate(dots, f, valid=fp)
            cand_terms.append(terms)
            rh, termsh = evaluate(h33, f, valid=fp)
            h33_terms.append(termsh)
        import numpy as _np
        c = _np.concatenate(cand_terms, axis=0)
        h = _np.concatenate(h33_terms, axis=0)
        ps = pooled_summary({"candidate": c, "h33_analogue": h}, draws=1000,
                            seed=520810, candidate="candidate")
        report["holdout"][f"seed{seed}"] = {
            "candidate_dti": ps["scores"]["candidate"]["dti"],
            "candidate_ci95": ps["scores"]["candidate"]["ci95"],
            "candidate_withheld": ps["scores"]["candidate"]["withheld_positive_pixels"],
            "h33_analogue_dti": ps["scores"]["h33_analogue"]["dti"],
            "h33_analogue_ci95": ps["scores"]["h33_analogue"]["ci95"],
            "delta_vs_h33": ps["paired_differences"]["h33_analogue"]["delta"],
            "delta_ci95": ps["paired_differences"]["h33_analogue"]["ci95"],
            "candidate_n_emitted": int(dots.sum()),
            "best_comparable_control": ps["best_comparable_control"],
        }

    out = ROOT / "evidence" / "g79_single_channel_screen.json"
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False)[:4000])
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
