#!/usr/bin/env python3
"""H80-DRAPE-PILOT: single-feature zero-catalogue pilot (see registry/preregistration_h80_drape_pilot.json).

Reuses the shared template: vendor/gems57 holdout folds (buffered_component_draw),
evaluate_holdout.evaluate / pooled_summary, metric (official DTI), and the
written preregistration. Nothing here edits the shared module.

Arms (per seed):
  A_notch            flight-line notched RTP -> tilt-edge score -> fixed-budget placement
  B_control_no_notch identical transform, no notch
  C0_random          uniform random placement, same spacing and budget
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
import scipy.fft as sfft
from scipy import ndimage as ndi
from scipy.signal.windows import tukey
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import evaluate_holdout as eh  # noqa: E402
from gems57 import holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402

BUDGET = 37654          # comparator budget (H33 / C0 dot count)
SEP_PX = 3.0            # minimum dot separation in pixels (300 m)
NOTCH_TOL = 0.02        # cycles per pixel
NOTCH_FREQS = (0.25, 0.5)  # 400 m and 200 m flight-line spacing at 100 m pixels
TILT_SCALE = 0.15       # radians
OUT = ROOT / "evidence" / "h80_drape_pilot"


def load_rtp() -> np.ndarray:
    with rasterio.open(ROOT / "data/raw/training_features.tif") as ds:
        if not str(ds.descriptions[1]).startswith("rtp "):
            raise RuntimeError(f"unexpected band 2 description {ds.descriptions[1]!r}")
        return ds.read(2).astype(np.float32)


def notch_mask(shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    fy = np.abs(sfft.fftfreq(h)).astype(np.float32)
    fx = np.abs(sfft.fftfreq(w)).astype(np.float32)
    band_y = np.zeros(h, bool)
    for f0 in NOTCH_FREQS:
        band_y |= np.abs(fy - f0) <= NOTCH_TOL
    band_x = fx <= NOTCH_TOL
    return band_y[:, None] & band_x[None, :]


def tilt_edge_score(rtp: np.ndarray, footprint: np.ndarray, notch: bool) -> np.ndarray:
    f = rtp.astype(np.float32).copy()
    # training_features nodata is -3.4028234663852886e+38 (finite!). Mask it as the shared
    # feature code does (gems79/features.py: isfinite & > -1e38 & != nodata).
    missing = ~np.isfinite(f) | (f <= -1e30) | ~footprint
    med = np.float32(np.median(f[footprint & ~missing]))
    f[missing] = med
    f -= med
    taper = (tukey(f.shape[0], 0.1)[:, None] * tukey(f.shape[1], 0.1)[None, :]).astype(np.float32)
    F = sfft.fft2(f * taper)
    if notch:
        F[notch_mask(f.shape)] = 0
    h, w = f.shape
    kx = (2 * np.pi * sfft.fftfreq(w)).astype(np.float32)[None, :]
    ky = (2 * np.pi * sfft.fftfreq(h)).astype(np.float32)[:, None]
    kmag = np.sqrt(kx * kx + ky * ky).astype(np.float32)
    vz = np.real(sfft.ifft2(F * kmag)).astype(np.float32)
    dx = np.real(sfft.ifft2(F * (1j * kx))).astype(np.float32)
    dy = np.real(sfft.ifft2(F * (1j * ky))).astype(np.float32)
    del F
    hgrad = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(vz, hgrad).astype(np.float32)
    gy, gx = np.gradient(theta)
    gmag = np.sqrt(gx * gx + gy * gy)
    s = gmag * np.exp(-(theta / TILT_SCALE) ** 2)
    s = np.where(footprint, s, 0).astype(np.float32)
    return s


def normalise(s: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    q = float(np.percentile(s[allowed], 99.0))
    if not q > 0:
        raise RuntimeError("degenerate score surface")
    return np.clip(s / q, 0, 1).astype(np.float32)


def greedy_place(order_idx: np.ndarray, shape: tuple[int, int], budget: int, sep: float) -> np.ndarray:
    """Accept candidates in the given order if >= sep px from every accepted dot."""
    r = int(np.ceil(sep))
    offs = [(j, i) for j in range(-r, r + 1) for i in range(-r, r + 1)
            if 0 < np.hypot(j, i) < sep]
    blocked = np.zeros(shape, bool)
    h, w = shape
    out = np.zeros(shape, bool)
    n = 0
    for flat in order_idx:
        y, x = divmod(int(flat), w)
        if blocked[y, x]:
            continue
        out[y, x] = True
        n += 1
        for j, i in offs:
            yy, xx = y + j, x + i
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True
        blocked[y, x] = True
        if n >= budget:
            break
    return out


def pooled_terms(p: np.ndarray, folds: list[dict], footprint: np.ndarray) -> tuple[np.ndarray, int]:
    total = None
    n_truth = 0
    for fold in folds:
        _, terms = eh.evaluate(p.astype(np.float64), fold, footprint, block_side=200)
        total = terms if total is None else total + terms
        n_truth += int(np.asarray(fold["truth"], bool).sum())
    return total, n_truth


def run_seed(seed: int, grid, rtp, s_notch_raw, s_ctrl_raw, rng_seed: int) -> dict:
    t0 = time.time()
    folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    hidden_all = folds[0]["hidden_all"]
    d_vis = ndi.distance_transform_edt(~visible)
    allowed = grid.footprint & (d_vis > 2.0)
    n_withheld = int(sum(int(np.asarray(f["truth"], bool).sum()) for f in folds))

    arms = {}
    aucs = {}
    rng = np.random.default_rng(rng_seed)
    for name, s_raw in (("A_notch", s_notch_raw), ("B_control_no_notch", s_ctrl_raw)):
        s = normalise(s_raw, allowed)
        cand = np.flatnonzero((allowed & grid.footprint).ravel())
        order = cand[np.argsort(-s.ravel()[cand], kind="stable")]
        dots = greedy_place(order, grid.footprint.shape, BUDGET, SEP_PX)
        p = dots.astype(np.float32)
        terms, n_truth = pooled_terms(p, folds, grid.footprint)
        arms[name] = (terms, int(dots.sum()))
        # leakage canary: score alone, not the dots
        pos = np.flatnonzero((hidden_all & allowed).ravel())
        neg_pool = np.flatnonzero((allowed & ~hidden_all).ravel())
        neg = rng.choice(neg_pool, size=min(300_000, neg_pool.size), replace=False)
        y = np.r_[np.ones(pos.size), np.zeros(neg.size)]
        sc = np.r_[s.ravel()[pos], s.ravel()[neg]]
        aucs[name] = float(roc_auc_score(y, sc))
        del s, order, cand

    cand_r = np.flatnonzero((allowed & grid.footprint).ravel())
    perm = rng.permutation(cand_r)
    dots_c0 = greedy_place(perm, grid.footprint.shape, BUDGET, SEP_PX)
    terms_c0, _ = pooled_terms(dots_c0.astype(np.float32), folds, grid.footprint)
    arms["C0_random"] = (terms_c0, int(dots_c0.sum()))

    from gems57.evaluate_holdout import pooled_summary
    summary = pooled_summary({k: v[0] for k, v in arms.items()}, draws=1000, seed=520810 + seed,
                             candidate="A_notch")
    out = dict(
        seed=seed,
        evaluator_version=eh.VERSION,
        withheld_positive_pixels=n_withheld,
        expected_receipt_withheld_positive_pixels={20: 11321, 30: 11342}.get(seed),
        emitted_dots={k: v[1] for k, v in arms.items()},
        leakage_canary_auc_single_score={k: round(v, 4) for k, v in aucs.items()},
        pooled_summary=summary,
        runtime_s=round(time.time() - t0, 1),
    )
    print(json.dumps({k: out[k] for k in ("seed", "withheld_positive_pixels", "emitted_dots",
                                          "leakage_canary_auc_single_score", "runtime_s")}), flush=True)
    for name in arms:
        sc = summary["scores"][name]
        print(f"  {name:20s} HOLDOUT-DTI={sc['dti']:.4f} CI95={sc['ci95']}", flush=True)
    d = summary["paired_differences"]
    for k, v in d.items():
        print(f"  A_notch - {k}: delta={v['delta']:+.4f} CI95={v['ci95']}", flush=True)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    grid = load_grid(ROOT / "data/raw")
    rtp = load_rtp()
    s_notch_raw = tilt_edge_score(rtp, grid.footprint, notch=True)
    s_ctrl_raw = tilt_edge_score(rtp, grid.footprint, notch=False)
    del rtp
    results = []
    for seed in (20, 30):
        res = run_seed(seed, grid, None, s_notch_raw, s_ctrl_raw, rng_seed=900 + seed)
        (OUT / f"seed{seed}.json").write_text(json.dumps(res, indent=2) + "\n")
        results.append(res)
    summary = {
        "lane": "H80-DRAPE-PILOT",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": eh.VERSION,
        "bar_to_spend_slot": {"seed20": 0.1905, "seed30": 0.1944, "source": "G79-THVC run_card.json (HOLDOUT-DTI, not organizer-confirmed)"},
        "results": results,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("wrote", OUT / "summary.json")


if __name__ == "__main__":
    sys.path[:0] = [str(ROOT / "src")]
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "H80-DRAPE-PILOT",
        reason="H80-DRAPE-PILOT is stopped negative (-0.0002 / -0.0018 vs control; IR-79-150).",
    )
    main()
