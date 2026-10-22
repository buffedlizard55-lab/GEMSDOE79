#!/usr/bin/env python3
"""G79-MDSC-8e58a8d0 E1: multi-altitude upward-continuation structural-index screen.

Frozen design: registry/preregistration_mdsc_8e58a8d0.json. Reuses vendor/gems57
holdout folds + pooled evaluator and the H80 pilots' placement helpers (no forks).
Zero catalogue-derived features: the surface is a pure function of the rtp band.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import rasterio
import scipy.fft as sfft
from scipy import ndimage as ndi
from scipy.signal.windows import tukey
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import evaluate_holdout as eh
from gems57 import holdout
from gems57.grid import load_grid
from gems57.evaluate_holdout import pooled_summary
from run_h80_drape_pilot import BUDGET, SEP_PX, greedy_place, normalise, pooled_terms

OUT = ROOT / "evidence" / "mdsc_8e58a8d0"
CACHE = ROOT / ".cache" / "mdsc_8e58a8d0"
DZ_PX = (1.5, 3.0, 6.0)  # 150 / 300 / 600 m at 100 m pixels


def trap(x, lo0, lo1, hi1, hi0):
    return np.clip(np.minimum((x - lo0) / (lo1 - lo0), (hi0 - x) / (hi0 - hi1)), 0, 1)


def build_surface(footprint):
    with rasterio.open(ROOT / "data/raw/training_features.tif") as ds:
        assert str(ds.descriptions[1]).startswith("rtp "), ds.descriptions[1]
        rtp = ds.read(2).astype(np.float32)
    missing = ~np.isfinite(rtp) | (rtp <= -1e30) | ~footprint
    med = np.float32(np.median(rtp[footprint & ~missing]))
    f = np.where(missing, med, rtp).astype(np.float64)
    f -= float(med)
    taper = (tukey(f.shape[0], 0.1)[:, None] * tukey(f.shape[1], 0.1)[None, :])
    F = sfft.fft2(f * taper)
    h, w = f.shape
    kx = (2 * np.pi * sfft.fftfreq(w))[None, :]
    ky = (2 * np.pi * sfft.fftfreq(h))[:, None]
    kmag = np.sqrt(kx * kx + ky * ky)
    hg = {}
    up150 = None
    for dz in (0.0,) + DZ_PX:
        Fz = F * np.exp(-kmag * dz) if dz > 0 else F
        dx = np.real(sfft.ifft2(Fz * (1j * kx)))
        dy = np.real(sfft.ifft2(Fz * (1j * ky)))
        hg[dz] = np.hypot(dx, dy).astype(np.float32)
        if dz == 1.5:
            up150 = np.real(sfft.ifft2(Fz)).astype(np.float32)
    del F
    hg0 = hg[0.0]
    eps = np.float32(np.percentile(hg0[footprint], 50.0)) * np.float32(1e-3)
    r1 = (hg[1.5] / np.maximum(hg0, eps)).astype(np.float64)
    r2 = (hg[6.0] / np.maximum(hg0, eps)).astype(np.float64)
    a1 = -np.log(np.clip(r1, 1e-4, 0.999))
    a2 = -np.log(np.clip(r2, 1e-4, 0.999))
    valid = footprint & (hg0 > eps) & (r1 > 1e-4) & (r1 < 0.999) & (r2 > 1e-4) & (r2 < r1)
    z_tab = np.logspace(np.log10(0.05), np.log10(60.0), 800)
    q_tab = np.log1p(6.0 / z_tab) / np.log1p(1.5 / z_tab)  # increasing 1..4
    q = np.where(valid & (a1 > 0), a2 / np.maximum(a1, 1e-12), np.nan)
    z_px = np.interp(np.clip(q, q_tab[0], q_tab[-1]), q_tab, z_tab)
    nplus1 = a1 / np.log1p(1.5 / z_px)
    z_m = np.where(valid, z_px * 100.0, 0.0)
    nn = np.where(valid, nplus1 - 1.0, 99.0)
    wz = np.where(valid, trap(z_m, 25, 50, 400, 800), 0.0).astype(np.float32)
    wn = np.where(valid, trap(nn, -0.3, 0.0, 0.6, 1.2), 0.0).astype(np.float32)
    qhg = float(np.percentile(hg0[footprint], 99.0))
    amp = np.clip(hg0 / qhg, 0, 1).astype(np.float32)
    s_a = (amp * wz * wn).astype(np.float32)
    s_a[~footprint] = 0
    s_b = amp.copy(); s_b[~footprint] = 0
    info = dict(valid_ratio_cells=int(valid.sum()), footprint_cells=int(footprint.sum()),
                z_m_p50_valid=float(np.median(z_m[valid])), n_p50_valid=float(np.median(nn[valid])),
                frac_valid_in_window=float(((wz > 0) & (wn > 0) & valid).sum() / max(int(valid.sum()), 1)))
    # cross-check only: rank agreement of FFT up-continuation with shipped TMI_up150 band
    with rasterio.open(ROOT / "data/raw/external/geodawn_extensions_u8.tif") as ds:
        assert ds.descriptions[3] == "TMI_up150", ds.descriptions
        up_band = ds.read(4)
    rng = np.random.default_rng(8)
    idx = np.flatnonzero((footprint & (up_band > 0)).ravel())
    sel = rng.choice(idx, size=min(200_000, idx.size), replace=False)
    info["spearman_fft_up150_vs_TMI_up150_band_sample200k"] = float(
        spearmanr(up150.ravel()[sel], up_band.ravel()[sel]).statistic)
    feats = dict(HG0=hg0, Wz=wz, WN=wn, A_mdsc=s_a, B_hg=s_b)
    return s_a, s_b, feats, info


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
    for name, s_raw in (("A_mdsc_screened", s_a), ("B_control_hg_only", s_b)):
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
    summary = pooled_summary(arms, draws=1000, seed=520810 + seed, candidate="A_mdsc_screened")
    out = dict(seed=seed, evidence_class="HOLDOUT-DTI", evaluator_version=eh.VERSION,
               withheld_positive_pixels=n_withheld,
               expected_receipt_withheld_positive_pixels={20: 11321, 30: 11342}.get(seed),
               emitted_dots=emitted, leakage_canary_single_feature=canary,
               pooled_summary=summary, runtime_s=round(time.time() - t0, 1))
    for name in arms:
        sc = summary["scores"][name]
        print(f"  seed {seed} {name:20s} HOLDOUT-DTI={sc['dti']:.4f} CI95={[round(x,4) for x in sc['ci95']]}", flush=True)
    print(f"  seed {seed} canary={ {k: v['symmetric'] for k, v in canary.items()} }", flush=True)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True); CACHE.mkdir(parents=True, exist_ok=True)
    grid = load_grid(ROOT / "data/raw")
    s_a, s_b, feats, info = build_surface(grid.footprint)
    np.save(CACHE / "surface_A.npy", s_a); np.save(CACHE / "surface_B.npy", s_b)
    print("surface info:", json.dumps(info), flush=True)
    results = [run_seed(seed, grid, s_a, s_b, feats) for seed in (20, 30)]
    for r in results:
        (OUT / f"seed{r['seed']}.json").write_text(json.dumps(r, indent=2) + "\n")
    (OUT / "summary.json").write_text(json.dumps(dict(
        lane="G79-MDSC-8e58a8d0", experiment="E1", evidence_class="HOLDOUT-DTI",
        evaluator_version=eh.VERSION, surface_info=info,
        bar_to_spend_slot_THVC={"seed20": 0.1905, "seed30": 0.1944}, results=results), indent=2) + "\n")
    print("wrote", OUT / "summary.json")


if __name__ == "__main__":
    main()
