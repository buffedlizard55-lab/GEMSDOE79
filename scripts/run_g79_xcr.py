#!/usr/bin/env python3
"""G79-XCR runner: two-instrument validation and exact marginal-DTI emission.

    python scripts/run_g79_xcr.py build                 # static channel memmap
    python scripts/run_g79_xcr.py holdout --seed 20     # I1 + I2, three arms
    python scripts/run_g79_xcr.py final                 # fit, emit, gate, write TIF

Every number written here is labelled: HOLDOUT-DTI (gems57-pooled-hide-v2) for
instrument I1, SGMC-PROXY-DTI for instrument I2.  Neither is an organizer score.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout as evaluator  # noqa: E402
from gems57.emit import greedy_allocate  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gems79 import xcr  # noqa: E402
from gems79.placement import place  # noqa: E402
from run_experiment import canaries  # noqa: E402

OUT = ROOT / "evidence" / "xcr"
CACHE = ROOT / ".cache" / "xcr"
STACK = ROOT / "data" / "raw" / "training_features.tif"
PREREG = ROOT / "registry" / "preregistration_g79_xcr.json"
PREREG_PIN = ROOT / "evidence" / "xcr" / "preregistration_sha256.txt"
SGMC = ROOT / "data" / "raw" / "external" / "derived_sgmc_faults_100m_u8.tif"
H33_BUDGET = 37_654


def log(*a) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}]", *a, flush=True)


def pin_preregistration() -> str:
    digest = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    PREREG_PIN.parent.mkdir(parents=True, exist_ok=True)
    if PREREG_PIN.exists():
        if PREREG_PIN.read_text().strip() != digest:
            raise RuntimeError("preregistration changed after it was pinned")
        return digest
    PREREG_PIN.write_text(digest + "\n")
    return digest


def check_preregistration() -> str:
    digest = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    if not PREREG_PIN.exists() or PREREG_PIN.read_text().strip() != digest:
        raise RuntimeError("preregistration SHA-256 pin mismatch; refusing to run")
    return digest


def static_path() -> Path:
    return CACHE / "static.npy"


def build_static() -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    if static_path().exists():
        meta = xcr.static_features(STACK, static_path())
        log("static channels already present; verified names only")
        return meta
    t0 = time.time()
    meta = xcr.static_features(STACK, static_path())
    meta["seconds"] = round(time.time() - t0, 1)
    xcr.dump(OUT / "static_channels.json", meta)
    log("static channels built in", meta["seconds"], "s")
    return meta


def load_sgmc(grid) -> np.ndarray:
    with rasterio.open(SGMC) as src:
        a = src.read(1)
    return (a > 0) & grid.footprint


def geometry_getter(mat, geom):
    n_static = mat.shape[0]
    flat_static = None

    def get(idx: np.ndarray) -> np.ndarray:
        nonlocal flat_static
        if flat_static is None:
            flat_static = mat.reshape(n_static, -1)
        vals = np.empty((n_static + geom.shape[0], idx.size), np.float32)
        vals[:n_static] = flat_static[:, idx]
        vals[n_static:] = geom.reshape(geom.shape[0], -1)[:, idx]
        return vals

    return get


def surface_for(grid, visible, mat, seed: int, region: np.ndarray | None = None):
    """Fit on ``visible`` catalogue context and predict inside ``region``."""
    fp = grid.footprint
    region = fp if region is None else (np.asarray(region, bool) & fp)
    geom = xcr.visible_geometry(visible, fp)
    x_get = geometry_getter(mat, geom)
    oof = xcr.oof_surface(x_get, visible, fp, region, groups=4, seed=seed)
    return oof["surface"], geom, oof


def score_arm(dots, grid, fold, *, sgmc_off, crop, origin, global_shape):
    """Score one cropped emission on I1 and I2 with the official DTI arithmetic."""
    fp_crop = grid.footprint[crop]
    active_fold = dict(region=fold["region"][crop], truth=fold["truth"][crop],
                       visible=fold["visible"][crop], masked_known=fold["masked_known"][crop])
    r1, terms1 = evaluator.evaluate(dots.astype(np.float32), active_fold,
                                    fp_crop, origin=origin, global_shape=global_shape)
    # I2: SGMC off-catalogue components inside the same fold region, nothing masked.
    off = (sgmc_off & fold["region"])[crop]
    fold2 = dict(region=fold["region"][crop], truth=off,
                 visible=np.zeros_like(fp_crop), masked_known=np.zeros_like(fp_crop))
    if fold2["truth"].any():
        r2, _ = evaluator.evaluate(dots.astype(np.float32), fold2, fp_crop,
                                   origin=origin, global_shape=global_shape)
        r2 = {k: r2[k] for k in ("dti", "tpw", "fpw", "fnw", "n_truth", "n_emitted")}
    else:
        r2 = {"dti": 0.0, "n_truth": 0}
    return r1, terms1, r2


def holdout(seed: int) -> dict:
    digest = check_preregistration()
    grid = load_grid(ROOT / "data" / "reference")
    mat = np.load(static_path(), mmap_mode="r")
    sgmc_off = xcr.sgmc_offcatalogue(load_sgmc(grid), grid.catalogue, grid.footprint)["off"]
    folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
    terms: dict[str, np.ndarray] = {}
    rows, canary_rows = [], []
    for fold in folds:
        ys, xs = np.nonzero(fold["region"])
        sy = slice(max(0, int(ys.min()) - 3), min(grid.height, int(ys.max()) + 4))
        sx = slice(max(0, int(xs.min()) - 3), min(grid.width, int(xs.max()) + 4))
        crop = (sy, sx)
        region = fold["region"][crop]
        visible = fold["visible"][crop]
        footprint = grid.footprint[crop]
        catalogue = grid.catalogue[crop]
        allowed = footprint & ~catalogue

        geom = xcr.visible_geometry(visible, footprint)
        x_get = geometry_getter(mat[:, sy, sx], geom)
        oof = xcr.oof_surface(x_get, visible, footprint, region, groups=4, seed=seed)
        surface = oof["surface"]

        # Canaries on both instruments, before any score is trusted.
        local_fold = dict(fold=fold["fold"], name=fold["name"], region=region,
                          truth=fold["truth"][crop], visible=visible,
                          masked_known=fold["masked_known"][crop])
        feats = {**{n: np.asarray(mat[i, sy, sx], np.float32) for i, n in enumerate(xcr.STATIC_NAMES)},
                 **{n: geom[i] for i, n in enumerate(xcr.GEOM_NAMES)}}
        canary_rows += canaries(feats, [local_fold], seed)
        fold2 = dict(fold=fold["fold"], name=fold["name"], region=region,
                     truth=(sgmc_off & fold["region"])[crop],
                     visible=np.zeros_like(region), masked_known=np.zeros_like(region))
        if fold2["truth"].any():
            canary_rows += [{**r, "instrument": "I2_SGMC"} for r in canaries(feats, [fold2], seed)]
        del feats

        # --- calibrated emission -------------------------------------------------
        # The raw regressor output is not a probability: its total expected credit
        # does not equal the truth mass, so the exact marginal test accepts
        # positive-but-meaningless background cells (measured: 29k dots, I1 0.003).
        # Rescale so that sum(expected credit) over the allowed domain equals a
        # label-blind estimate of the truth mass, then let the exact test decide.
        k_visible = float((visible & region).sum())
        k_truth = 0.25 * k_visible          # hide fraction 0.20 / visible 0.80
        dom = allowed & region
        raw = float((surface * dom).sum(dtype=np.float64))
        scale = float(min(1.0 / max(surface.max(), 1e-9), k_truth / max(raw * 0.5, 1e-9)))
        p_cal = np.clip(surface * scale, 0.0, 1.0)
        alloc = greedy_allocate(p_cal, dom, k_truth, max_dots=150_000,
                                candidate_cap=400_000, per_round=20_000, floor=1e-4)
        arms = {
            "A2_calibrated_greedy": alloc.emitted,
            "B_xcr_nms37654": place(surface, allowed & region, H33_BUDGET, spacing=3)[0],
            "D_xcr_massbudget": place(surface, allowed & region,
                                      int(round(min(H33_BUDGET, k_truth))), spacing=3)[0],
        }
        rng = np.random.default_rng(seed * 31 + fold["fold"])
        n_uni = int(arms["B_xcr_nms37654"].sum())
        ii = rng.choice(np.flatnonzero((allowed & region).ravel()), n_uni, replace=False)
        uni = np.zeros_like(region)
        uni.ravel()[ii] = True
        arms["C_uniform"] = uni

        for name, dots in arms.items():
            r1, t1, r2 = score_arm(dots, grid, fold, sgmc_off=sgmc_off, crop=crop,
                                   origin=(sy.start, sx.start), global_shape=grid.shape)
            terms[name] = terms.get(name, np.zeros_like(t1)) + t1
            rows.append({"arm": name, "fold": fold["name"], "seed": seed,
                         "n_dots": int(dots.sum()),
                         "I1_HOLDOUT_DTI": r1["dti"], "I1_n_truth": r1["n_truth"],
                         "I1_tpw": r1["tpw"], "I1_fpw": r1["fpw"], "I1_fnw": r1["fnw"],
                         "I2_SGMC_PROXY_DTI": r2["dti"], "I2_n_truth": r2["n_truth"]})
            log(f"seed {seed} {fold['name']} {name}: I1 {r1['dti']:.4f}  I2 {r2['dti']:.4f}  dots {int(dots.sum())}")
        del alloc, arms
        gc.collect()

    summary = evaluator.pooled_summary(terms, candidate="D_xcr_massbudget", draws=1000, seed=7900 + seed)
    summary.update(seed=seed, rows=rows, preregistration_sha256=digest,
                   evaluator_version=evaluator.VERSION,
                   evidence_class="HOLDOUT-DTI",
                   interpretation=("I1 = catalogue hide-and-recover. I2 = cross-catalogue recovery of "
                                   "SGMC faults absent from the catalogue (external proxy for the "
                                   "competition's new-fault population). Neither is an organizer score."))
    suspicious = [r for r in canary_rows if r["suspicious"]]
    xcr.dump(OUT / f"canaries_seed{seed}.json",
             {"passed": not suspicious, "threshold": 0.90,
              "note": "LEAKAGE-CANARY; not a DTI and not an organizer score",
              "suspicious_rows": suspicious, "rows": canary_rows})
    xcr.dump(OUT / f"holdout_seed{seed}.json", summary)
    if suspicious:
        raise SystemExit(f"leakage canary fired on {len(suspicious)} rows; stop")
    return summary


def final() -> dict:
    digest = check_preregistration()
    grid = load_grid(ROOT / "data" / "reference")
    mat = np.load(static_path(), mmap_mode="r")
    surface, geom, target = surface_for(grid, grid.catalogue, mat, seed=2026)
    exposed = surface.copy()
    xcr.dump(OUT / "final_surface_stats.json", {
        "max": float(surface.max()), "mean_footprint": float(surface[grid.footprint].mean()),
        "p50": float(np.median(surface[grid.footprint])),
        "p99": float(np.quantile(surface[grid.footprint], 0.99)),
        "positive_footprint_pixels": int((surface[grid.footprint] > 0).sum()),
        "preregistration_sha256": digest})
    allowed = grid.footprint & ~grid.catalogue
    alloc = greedy_allocate(surface, allowed, float(grid.catalogue.sum()), max_dots=150_000,
                            candidate_cap=400_000, per_round=20_000)
    log("greedy emission:", alloc.n_dots, "dots; surrogate DTI", round(alloc.surrogate_dti, 4))
    stats = {"n_dots": alloc.n_dots, "surrogate_dti": alloc.surrogate_dti,
             "expected_covered_credit": alloc.expected_covered_credit,
             "expected_self_credit": alloc.expected_self_credit, "rounds": alloc.rounds,
             "trace": alloc.trace, "k_truth_proxy": int(grid.catalogue.sum()),
             "on_catalogue": int((alloc.emitted & grid.catalogue).sum()),
             "preregistration_sha256": digest}
    xcr.dump(OUT / "final_emission.json", stats)
    np.save(CACHE / "final_dots.npy", alloc.emitted)
    np.save(CACHE / "final_surface.npy", surface.astype(np.float32))
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["build", "holdout", "final"])
    ap.add_argument("--seed", type=int, default=20)
    args = ap.parse_args()
    if args.stage == "build":
        pin_preregistration()
        build_static()
    elif args.stage == "holdout":
        holdout(args.seed)
    else:
        final()
