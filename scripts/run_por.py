#!/usr/bin/env python3
"""G79-POR: 50/50 collar + corridor portfolio emission. EXP-3.

See registry/preregistration_g79_por.json.  Two mutually exclusive readings of where
the unmapped faults are get half the dot budget each:

* collar   - 3 px lattice in the 3-12 px annulus around the mapped catalogue, the
             regime the hide-and-recover instrument can actually validate;
* corridor - 3 px lattice inside the magnetic coherence / tilt contact corridors
             beyond 12 px, the blind-basin regime only the hidden test can score.

No classifier and no score ranking are involved: the emission is a fixed geometric
allocation, which is what makes the holdout number interpretable.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout, holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems79 import mfx  # noqa: E402
import run_ece  # noqa: E402

NAME = "gems79-por-collar-corridor-40000dots-20261022"
NOTE = "G79-POR 50/50 collar (3-12px) + geophysical corridor 3px lattices, 40k dots"
COLLAR_IN, COLLAR_OUT, CORRIDOR_MIN = 3, 12, 12
ARM = 20_000
FEATURE_SHA = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def take(mask: np.ndarray, cap: int) -> np.ndarray:
    """Raster-order prefix of a mask (deterministic, no ranking)."""
    out = np.zeros(mask.shape, bool)
    idx = np.flatnonzero(mask.ravel())
    if idx.size == 0:
        return out
    if idx.size > cap:
        idx = idx[:cap]
    out.ravel()[idx] = True
    return out


def arms(catalogue: np.ndarray, footprint: np.ndarray, corridor: np.ndarray,
         blocked: np.ndarray, *, arm: int = ARM, lat: np.ndarray | None = None) -> dict:
    lat = run_ece.lattice(footprint.shape) if lat is None else lat
    dcat = ndi.distance_transform_edt(~catalogue)
    collar_zone = footprint & ~blocked & (dcat >= COLLAR_IN) & (dcat <= COLLAR_OUT)
    corridor_zone = footprint & ~blocked & corridor & (dcat > CORRIDOR_MIN)
    return {
        "collar": take(lat & collar_zone, arm),
        "corridor": take(lat & corridor_zone, arm),
    }


def evaluate_dots(dots: np.ndarray, folds, fp: np.ndarray) -> np.ndarray:
    terms = []
    for f in folds:
        _r, trm = evaluate_holdout.evaluate(dots.astype(np.float32), f, fp)
        terms.append(trm)
    return np.vstack(terms)


def main() -> int:
    t0 = time.time()
    grid = load_grid(ROOT / "data" / "reference")
    fp, cat = grid.footprint, grid.catalogue
    feat = ROOT / "data/raw/training_features.tif"
    if sha256(feat) != FEATURE_SHA:
        raise SystemExit("feature stack sha256 mismatch")
    chan = mfx.load_channels(feat, fp, tuple(sorted(set(mfx.MODEL_BANDS) | {9})))
    coh = mfx.structure_coherence(chan)
    tilt = run_ece.tilt_angle(chan)
    corridor = (coh > run_ece.COH_T) | (np.abs(tilt) < run_ece.TILT_T)
    del tilt
    lat = run_ece.lattice(fp.shape)
    out = {"lane": "G79-POR", "preregistration": "registry/preregistration_g79_por.json",
           "fixed": {"collar_px": [COLLAR_IN, COLLAR_OUT], "corridor_min_px": CORRIDOR_MIN,
                     "arm_budget": ARM, "lattice_px": run_ece.PITCH},
           "input_receipts": {"training_features_sha256": FEATURE_SHA},
           "holdout": {}}
    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        visible, masked_known = folds[0]["visible"], folds[0]["masked_known"]
        truth = np.zeros(fp.shape, bool)
        for f in folds:
            truth |= f["truth"]
        a = arms(visible, fp, corridor, masked_known, lat=lat)
        hybrid = a["collar"] | a["corridor"]
        rng = np.random.default_rng(seed + 999)
        allowed = fp & ~masked_known
        idx = np.flatnonzero(allowed.ravel())
        pick = rng.choice(idx, size=min(int(hybrid.sum()), idx.size), replace=False)
        uni = np.zeros(fp.shape, bool)
        uni.ravel()[pick] = True
        arms_terms = {
            "COLLAR": evaluate_dots(a["collar"], folds, fp),
            "CORRIDOR": evaluate_dots(a["corridor"], folds, fp),
            "HYBRID": evaluate_dots(hybrid, folds, fp),
            "UNIFORM": evaluate_dots(uni, folds, fp),
        }
        pooled = evaluate_holdout.pooled_summary(arms_terms, draws=1000, seed=520810,
                                                 candidate="HYBRID")
        out["holdout"][f"seed{seed}"] = {
            "scores": {k: {"dti": pooled["scores"][k]["dti"],
                           "ci95": pooled["scores"][k]["ci95"],
                           "withheld_positive_pixels": pooled["scores"][k]["withheld_positive_pixels"]}
                       for k in pooled["scores"]},
            "dots": {k: int(v.sum()) for k, v in a.items()},
            "hybrid_dots": int(hybrid.sum()),
        }
        s = out["holdout"][f"seed{seed}"]["scores"]
        print(f"seed{seed} " + " ".join(f"{k}={s[k]['dti']:.4f}" for k in s), flush=True)
        del folds, uni, arms_terms

    a = arms(cat, fp, corridor, cat, lat=lat)
    hybrid = a["collar"] | a["corridor"]
    dcat = ndi.distance_transform_edt(~cat)
    out["final"] = {"dots": int(hybrid.sum()), "collar_dots": int(a["collar"].sum()),
                    "corridor_dots": int(a["corridor"].sum()),
                    "on_catalogue": int((hybrid & cat).sum()),
                    "median_dist_to_catalogue_m": float(np.median(dcat[hybrid]) * 100.0),
                    "frac_gt_1km_from_catalogue": float((dcat[hybrid] > 10).mean())}
    dest = ROOT / "docs" / "downloads" / f"{NAME}.tif"
    for suf in (".tif", ".zip", ".json"):
        q = dest.with_suffix(suf)
        if q.exists():
            q.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    receipt = write_submission(dest, hybrid.astype(np.float32),
                               ROOT / "data/reference/sample_submission.tif", fp,
                               note=NOTE, name=NAME, catalogue=cat,
                               metadata={"lane": "G79-POR", "arm_budget": ARM})
    out["submission"] = {"name": NAME, "note": NOTE, "note_chars": len(NOTE),
                         "file": str(dest.relative_to(ROOT)), "sha256": sha256(dest),
                         "bytes": dest.stat().st_size, "dots": int(hybrid.sum()),
                         "validator_all_checks_passed": receipt["validator"]["all_checks_passed"],
                         "validator_checks": receipt["validator"]["checks"]}
    out["elapsed_s"] = round(time.time() - t0, 1)
    (ROOT / "evidence" / "por_experiment3.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(json.dumps(out["final"], indent=1), flush=True)
    print("wrote", out["submission"]["file"], out["submission"]["sha256"][:16], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
