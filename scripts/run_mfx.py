#!/usr/bin/env python3
"""G79-MFX end-to-end experiment: holdout (seeds 20/30) -> final TIF -> novelty.

Preregistration: registry/preregistration_g79_mfx.json (written before this ran).

Stages
------
1. Read the pinned 19-band stack (data/raw/training_features.tif, SHA-256 checked
   against registry/data_manifest.json before use).
2. Per hide-and-recover seed: cut a template bank from the VISIBLE catalogue only,
   matched-filter the study area, fit a 4-quadrant out-of-fold LightGBM on pointwise
   channels, prior-correct the posterior, emit exactly 40,000 dots with the shared
   3-px decimated allocator, and score with the shared evaluator against a
   budget-matched UNIFORM control.
3. Repeat on the full catalogue for the final artifact, write it with the shared
   fail-closed writer, then measure dot overlap against every local prior raster and
   against fetched top-scoring predecessor rasters.

Nothing here uploads, promotes, or spends a weekly slot.
"""
from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout, holdout  # noqa: E402
from gems57.emit import emit_decimated, emit_prefix  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.metric import RADIUS_PX  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems57 import uniqueness  # noqa: E402
from gems79 import mfx  # noqa: E402

NAME = "gems79-mfx-sigtransfer-40000dots-20261022"
NOTE = "G79-MFX catalogue-template matched filter, 4-quadrant OOF, 40k dots"
BUDGET = 40_000
PRUNE_PX = 2
TILE_PX = 3
THVC = {"seed20": 0.190517, "seed30": 0.194366}
FEATURE_SHA = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
RAW = ROOT / "data" / "raw"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def quadrant(shape, footprint):
    return holdout.quadrant_ids(footprint)


def sample_rows(mask: np.ndarray, cap: int, rng) -> np.ndarray:
    idx = np.flatnonzero(mask.ravel())
    if idx.size > cap:
        idx = rng.choice(idx, size=cap, replace=False)
        idx.sort()
    return idx


def design_rows(channels: dict[str, np.ndarray], names: list[str], idx: np.ndarray) -> np.ndarray:
    X = np.empty((idx.size, len(names)), np.float32)
    for j, n in enumerate(names):
        col = channels[n].ravel()
        X[:, j] = col[idx]
    X[~np.isfinite(X)] = 0.0
    return X


def fit_predict_oof(channels: dict[str, np.ndarray], names: list[str], visible: np.ndarray,
                    footprint: np.ndarray, quad: np.ndarray, seed: int,
                    *, pos_cap: int = 30_000, neg_cap: int = 90_000,
                    n_estimators: int = 250) -> tuple[np.ndarray, dict]:
    import lightgbm as lgb

    rng = np.random.default_rng(seed + 4242)
    dist = np.minimum(channels["dist_visible_px"], 40.0)
    posterior = np.zeros(footprint.shape, np.float32)
    stats = {"folds": []}
    for q in range(4):
        trainable = footprint & (quad != q) & (quad >= 0)
        pos = trainable & visible
        neg = trainable & (dist > 3.0) & ~visible
        pi = sample_rows(pos, pos_cap, rng)
        ni = sample_rows(neg, neg_cap, rng)
        idx = np.concatenate([pi, ni])
        X = design_rows(channels, names, idx)
        y = np.r_[np.ones(pi.size, np.int8), np.zeros(ni.size, np.int8)]
        model = lgb.LGBMClassifier(
            n_estimators=n_estimators, learning_rate=0.06, num_leaves=63,
            min_child_samples=40, subsample=0.8, subsample_freq=1,
            colsample_bytree=0.8, reg_lambda=1.0, n_jobs=2, random_state=seed + q,
            verbose=-1,
        )
        model.fit(X, y)
        del X, idx
        sample_pi = pi.size / max(pi.size + ni.size, 1)
        true_pi = float((visible & footprint).sum() / max(footprint.sum(), 1))
        target = footprint & (quad == q)
        rows = np.flatnonzero(target.any(axis=1))
        if rows.size == 0:
            continue
        y0, y1 = int(rows[0]), int(rows[-1]) + 1
        step = 256
        for a in range(y0, y1, step):
            b = min(a + step, y1)
            block_mask = target[a:b]
            if not block_mask.any():
                continue
            flat = np.flatnonzero(block_mask.ravel())
            Xb = np.empty((flat.size, len(names)), np.float32)
            for j, n in enumerate(names):
                Xb[:, j] = channels[n][a:b].ravel()[flat]
            Xb[~np.isfinite(Xb)] = 0.0
            p = model.predict_proba(Xb)[:, 1].astype(np.float32)
            del Xb
            buf = np.zeros(block_mask.size, np.float32)
            buf[flat] = p
            posterior[a:b] = buf.reshape(block_mask.shape)
        stats["folds"].append({
            "fold": q, "train_pos": int(pi.size), "train_neg": int(ni.size),
            "sample_pi": sample_pi, "true_pi": true_pi,
            "importance_top": sorted(
                zip(names, model.feature_importances_.tolist()),
                key=lambda t: -t[1])[:8],
        })
    return mfx.prior_correct(np.clip(posterior, 0, 1), sample_pi=0.25, true_pi=stats["folds"][0]["true_pi"]), stats


def canaries(channels: dict[str, np.ndarray], names: list[str], active: np.ndarray,
             truth: np.ndarray, seed: int) -> dict:
    rng = np.random.default_rng(seed + 17)
    pos = np.flatnonzero((active & truth).ravel())
    dtr = ndi.distance_transform_edt(~truth)
    neg = np.flatnonzero((active & ~truth & (dtr > 3)).ravel())
    if neg.size > pos.size * 3:
        neg = rng.choice(neg, size=pos.size * 3, replace=False)
        neg.sort()
    idx = np.r_[pos, neg]
    y = np.r_[np.ones(pos.size), np.zeros(neg.size)]
    out = {}
    for n in names:
        s = channels[n].ravel()[idx]
        s = np.nan_to_num(s, nan=0.0, posinf=0.0, neginf=0.0)
        if np.ptp(s) == 0:
            out[n] = {"auc": None, "symmetric_auc": None, "note": "constant"}
            continue
        a = float(roc_auc_score(y, s))
        out[n] = {"auc": a, "symmetric_auc": max(a, 1 - a)}
    out["_n_pos"] = int(pos.size)
    out["_n_neg"] = int(neg.size)
    out["_max_symmetric_auc"] = max(
        v["symmetric_auc"] for k, v in out.items()
        if isinstance(v, dict) and v.get("symmetric_auc") is not None)
    return out


def emit_dots(posterior: np.ndarray, allowed: np.ndarray, budget: int = BUDGET):
    ranked, tile_credit = emit_decimated(posterior, allowed, tile_px=TILE_PX)
    dots = emit_prefix(ranked, budget)
    return dots, {"n_ranked_tiles": int(ranked.max()), "n_dots": int(dots.sum())}


def local_prior_rasters() -> list[Path]:
    out = []
    for p in sorted(ROOT.rglob("*.tif")):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("data/raw") or rel.startswith("data/reference"):
            continue
        out.append(p)
    return out


def dot_overlap(mine: np.ndarray, theirs_support: np.ndarray) -> dict:
    near = ndi.distance_transform_edt(~theirs_support) <= RADIUS_PX
    fwd = float((mine & near).sum() / max(mine.sum(), 1))
    rev_near = ndi.distance_transform_edt(~mine) <= RADIUS_PX
    rev = float((theirs_support & rev_near).sum() / max(theirs_support.sum(), 1))
    inter = float((mine & theirs_support).sum())
    union = float((mine | theirs_support).sum())
    return {"forward_overlap": fwd, "reverse_overlap": rev,
            "jaccard": float(inter / union) if union else 0.0}


def novelty(mine: np.ndarray, footprint: np.ndarray, extra: list[Path],
            exclude: set[Path] | None = None) -> dict:
    """Dot overlap against every local prior plus fetched top predecessors."""
    exclude = {p.resolve() for p in (exclude or set())}
    rows = []
    for p in local_prior_rasters() + extra:
        if p.resolve() in exclude:
            continue  # never score the candidate against itself
        try:
            with rasterio.open(p) as src:
                if src.count < 1 or (src.height, src.width) != mine.shape:
                    continue
                a = src.read(1).astype(np.float32)
        except Exception as exc:  # unreadable prior is reported, never silently skipped
            rows.append({"file": str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p),
                         "error": str(exc)[:120]})
            continue
        a = np.where(np.isfinite(a), a, 0.0)
        support = (a > 0) & footprint
        if support.sum() == 0:
            continue
        r = dot_overlap(mine, support)
        r.update({"file": str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p),
                  "prior_dots": int(support.sum())})
        rows.append(r)
    ok = [r for r in rows if "forward_overlap" in r]
    return {
        "n_compared": len(ok),
        "n_unreadable": len(rows) - len(ok),
        "max_forward_overlap": max((r["forward_overlap"] for r in ok), default=None),
        "max_reverse_overlap": max((r["reverse_overlap"] for r in ok), default=None),
        "max_jaccard": max((r["jaccard"] for r in ok), default=None),
        "worst_forward": max(ok, key=lambda r: r["forward_overlap"]) if ok else None,
        "rows": rows,
    }


def fetch_top_priors(limit: int = 12) -> tuple[list[Path], list[dict]]:
    """Fetch top-scoring predecessor rasters from their public GitHub mirrors."""
    idx = json.loads((ROOT / "registry" / "historical_index.json").read_text())
    scored = sorted([r for r in idx["scored"] if r.get("public_score") is not None],
                    key=lambda r: -r["public_score"])[:limit]
    dest = ROOT / ".cache" / "registry_top_priors"
    dest.mkdir(parents=True, exist_ok=True)
    out, log = [], []
    for r in scored:
        full = r["repo"] if "/" in r["repo"] else f"buffedlizard55-lab/{r['repo']}"
        name = f"{r['repo']}__{Path(r['path']).name}"
        p = dest / name
        if not p.exists() or p.stat().st_size == 0:
            try:
                subprocess.run(["gh", "api", f"repos/{full}/contents/{r['path']}",
                                "-H", "Accept: application/vnd.github.raw"],
                               stdout=p.open("wb"), stderr=subprocess.PIPE, check=True,
                               timeout=120)
            except Exception as exc:
                log.append({"repo": r["repo"], "path": r["path"], "error": str(exc)[:160]})
                p.unlink(missing_ok=True)
                continue
        out.append(p)
        log.append({"repo": r["repo"], "path": r["path"], "score": r["public_score"],
                    "bytes": p.stat().st_size})
    return out, log


def main() -> int:
    t0 = time.time()
    grid = load_grid(ROOT / "data" / "reference")
    fp, cat = grid.footprint, grid.catalogue
    feat = RAW / "training_features.tif"
    if sha256(feat) != FEATURE_SHA:
        raise SystemExit("training_features.tif SHA-256 mismatch; refusing to use it")
    out: dict = {
        "lane": "G79-MFX",
        "preregistration": "registry/preregistration_g79_mfx.json",
        "hypothesis": "Unmapped faults reproduce the multi-band 15x15 px geophysical "
                      "signature of mapped catalogue faults, so a matched filter whose "
                      "templates are cut from visible catalogue pixels recovers them "
                      "without relying on proximity to a mapped trace.",
        "named_non_fault_process": "Miocene basalt dyke swarms and shallow lithologic "
                                   "contacts; residual mimic is measured, not assumed away.",
        "input_receipts": {"training_features_sha256": FEATURE_SHA,
                           "existing_faults_sha256": sha256(ROOT / "data/reference/existing_faults.tif"),
                           "sample_submission_sha256": sha256(ROOT / "data/reference/sample_submission.tif")},
        "holdout": {},
        "elapsed_s": {},
    }
    print("loading channels", flush=True)
    chan = mfx.load_channels(feat, fp, mfx.MODEL_BANDS)
    coh = mfx.structure_coherence(chan)
    quad = quadrant(fp.shape, fp)

    for seed in (20, 30):
        t = time.time()
        folds, _q = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3,
                                                   boundary_px=12)
        visible = folds[0]["visible"]
        masked_known = folds[0]["masked_known"]
        truth = np.zeros(fp.shape, bool)
        for f in folds:
            truth |= f["truth"]
        tpl15 = mfx.template_bank(chan, visible, count=mfx.N_TEMPLATES,
                                  size=mfx.TEMPLATE_SIZE, seed=seed)
        ncc15 = mfx.ncc_score(chan, tpl15, size=mfx.TEMPLATE_SIZE, footprint=fp)
        del tpl15
        tpl21 = mfx.template_bank(chan, visible, count=mfx.N_TEMPLATES,
                                  size=mfx.SECOND_SCALE_SIZE, seed=seed + 1)
        ncc21 = mfx.ncc_score(chan, tpl21, size=mfx.SECOND_SCALE_SIZE, footprint=fp)
        del tpl21
        channels = mfx.build_channels(chan, visible, footprint=fp, ncc_small=ncc15,
                                      ncc_big=ncc21, coh=coh)
        names = list(channels)
        print(f"seed{seed}: features ready ({time.time()-t:.1f}s, {len(names)} channels)", flush=True)
        post, fit_stats = fit_predict_oof(channels, names, visible, fp, quad, seed)
        can = canaries(channels, names, fp & ~masked_known, truth, seed)
        dist_vis = channels["dist_visible_px"]
        allowed = fp & ~masked_known & (dist_vis > PRUNE_PX)
        dots, emit_stats = emit_dots(post, allowed)
        rng = np.random.default_rng(seed + 999)
        idx = np.flatnonzero(allowed.ravel())
        pick = rng.choice(idx, size=min(int(dots.sum()), idx.size), replace=False)
        uniform = np.zeros(fp.shape, bool)
        uniform.ravel()[pick] = True
        arms = {}
        for nm, d in (("MFX", dots), ("UNIFORM", uniform)):
            terms = []
            for f in folds:
                _res, trm = evaluate_holdout.evaluate(d.astype(np.float32), f, fp)
                terms.append(trm)
            arms[nm] = np.vstack(terms)
        pooled = evaluate_holdout.pooled_summary(arms, draws=1000, seed=520810,
                                                 candidate="MFX")
        entry = {
            "pooled": pooled,
            "emitted_pixels": int(dots.sum()),
            "on_visible_catalogue": int((dots & visible).sum()),
            "continuous_surface_stats": {
                "mean": float(post[fp].mean()), "max": float(post[fp].max()),
                "frac_gt_0.5": float((post[fp] > 0.5).mean()),
            },
            "canaries": can,
            "fit": fit_stats,
            "emission": emit_stats,
            "elapsed_s": round(time.time() - t, 1),
        }
        out["holdout"][f"seed{seed}"] = entry
        print(f"seed{seed} HOLDOUT-DTI MFX={pooled['scores']['MFX']['dti']:.4f} "
              f"CI={pooled['scores']['MFX']['ci95']} n={pooled['scores']['MFX']['withheld_positive_pixels']} "
              f"UNIFORM={pooled['scores']['UNIFORM']['dti']:.4f} "
              f"canary_max={can['_max_symmetric_auc']:.3f}", flush=True)
        del ncc15, ncc21, channels, post, dots, uniform, arms

    # ---- final artifact on the full catalogue ----
    t = time.time()
    tpl15 = mfx.template_bank(chan, cat, count=mfx.N_TEMPLATES, size=mfx.TEMPLATE_SIZE, seed=7)
    ncc15 = mfx.ncc_score(chan, tpl15, size=mfx.TEMPLATE_SIZE, footprint=fp)
    del tpl15
    tpl21 = mfx.template_bank(chan, cat, count=mfx.N_TEMPLATES, size=mfx.SECOND_SCALE_SIZE, seed=8)
    ncc21 = mfx.ncc_score(chan, tpl21, size=mfx.SECOND_SCALE_SIZE, footprint=fp)
    del tpl21
    channels = mfx.build_channels(chan, cat, footprint=fp, ncc_small=ncc15,
                                  ncc_big=ncc21, coh=coh)
    names = list(channels)
    post, fit_stats = fit_predict_oof(channels, names, cat, fp, quad, 79)
    dist_vis = channels["dist_visible_px"]
    allowed = fp & (dist_vis > PRUNE_PX) & ~cat
    dots, emit_stats = emit_dots(post, allowed)
    out["final"] = {"emitted_pixels": int(dots.sum()), "emission": emit_stats,
                    "fit": fit_stats,
                    "off_catalogue_fraction": float((dist_vis[dots] > 10).mean()),
                    "median_dist_to_catalogue_m": float(np.median(dist_vis[dots]) * 100.0),
                    "surface_stats": {"mean": float(post[fp].mean()),
                                      "max": float(post[fp].max())}}
    print("final dots", int(dots.sum()), "off-cat>1km frac",
          round(out["final"]["off_catalogue_fraction"], 3), flush=True)

    dest = ROOT / "docs" / "downloads" / f"{NAME}.tif"
    for suf in (".tif", ".zip", ".json"):
        q = dest.with_suffix(suf)
        if q.exists():
            q.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    receipt = write_submission(dest, dots.astype(np.float32),
                               ROOT / "data/reference/sample_submission.tif", fp,
                               note=NOTE, name=NAME, catalogue=cat,
                               metadata={"lane": "G79-MFX", "budget": BUDGET,
                                         "prune_px": PRUNE_PX, "tile_px": TILE_PX})
    out["submission"] = {
        "name": NAME, "note": NOTE, "note_chars": len(NOTE),
        "file": str(dest.relative_to(ROOT)), "sha256": sha256(dest),
        "bytes": dest.stat().st_size, "dots": int(dots.sum()),
        "validator_all_checks_passed": receipt["validator"]["all_checks_passed"],
        "validator_checks": receipt["validator"]["checks"],
    }
    print("wrote", out["submission"]["file"], out["submission"]["sha256"][:16], flush=True)

    extra, fetch_log = fetch_top_priors()
    out["novelty"] = {"scope": "every local prior raster in this checkout plus fetched "
                               "top-scoring predecessor rasters from their public GitHub "
                               "mirrors; the full 992-raster registry is NOT re-restored here",
                      "fetches": fetch_log, **novelty(dots, fp, extra, exclude={dest})}
    out["elapsed_s"]["total"] = round(time.time() - t0, 1)
    (ROOT / "evidence" / "mfx_experiment1.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    print("novelty max_forward_overlap", out["novelty"]["max_forward_overlap"],
          "n_compared", out["novelty"]["n_compared"], flush=True)
    print("total elapsed", out["elapsed_s"]["total"], "s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
