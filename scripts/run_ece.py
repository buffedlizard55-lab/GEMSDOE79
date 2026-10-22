#!/usr/bin/env python3
"""G79-ECE: enriched-coverage emission. EXP-2 (see registry/preregistration_g79_ece.json).

The claim under test: with alpha=0.2 / beta=0.8 and a 300 m kernel, the metric is
coverage-dominated, so at a fixed dot cost the best emission is a kernel-spaced
(3 px) lattice over a physically enriched corridor prior rather than the top-ranked
pixels of a classifier.  The corridor prior uses geophysics only (magnetic
structure-tensor coherence and the magnetic tilt contact angle), so it carries no
catalogue information and cannot leak through a hide-and-recover fold.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout, holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems79 import mfx  # noqa: E402

NAME = "gems79-ece-corridor-lattice-20261022"
NOTE = "G79-ECE 3px lattice on magnetic coherence+tilt corridors, coverage-optimal"
COH_T = 0.50
TILT_T = 0.25
PITCH = 3
MAX_DOTS = 190_000
THVC = {"seed20": 0.190517, "seed30": 0.194366}
FEATURE_SHA = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tilt_angle(chan: mfx.ChannelStack, band: int = 2) -> np.ndarray:
    """atan2(dz, |grad_h|) of the RTP amplitude, dimensionless in [-pi/2, pi/2]."""
    a = ndi.gaussian_filter(mfx._filled(chan[band]), 1.0)
    gy, gx = np.gradient(a)
    hgm = np.hypot(gx, gy)
    # vertical derivative at this grid: use the drilled TMI vertical gradient band 9
    # when available, otherwise the Laplacian-free finite difference is not used and
    # the tilt is taken from the horizontal gradient ratio only.
    if 9 not in chan.data:
        raise ValueError("band 9 (TMI vertical gradient) is required for the tilt angle")
    dz = ndi.gaussian_filter(mfx._filled(chan[9]), 1.0)
    return np.arctan2(dz, np.maximum(hgm, 1e-6)).astype(np.float32)


def lattice(shape, pitch: int = PITCH) -> np.ndarray:
    """Quasi-hexagonal kernel-spaced lattice: one dot every ``pitch`` px."""
    mask = np.zeros(shape, bool)
    cols = np.arange(shape[1])
    for y in range(0, shape[0], pitch):
        off = 0 if (y // pitch) % 2 == 0 else pitch // 2
        mask[y, (cols + off) % pitch == 0] = True
    return mask


def enrichment(region: np.ndarray, active: np.ndarray, truth: np.ndarray) -> dict:
    """Truth density inside a corridor region relative to outside it."""
    inside = int((region & active).sum())
    outside = int((~region & active).sum())
    tin = int((region & active & truth).sum())
    tout = int((active & truth & ~region).sum())
    din = tin / inside if inside else 0.0
    dout = tout / outside if outside else 0.0
    return {"region_px": inside, "truth_in_region": tin, "truth_outside": tout,
            "density_inside": din, "density_outside": dout,
            "enrichment": (din / dout) if dout > 0 else None}


def main() -> int:
    t0 = time.time()
    grid = load_grid(ROOT / "data" / "reference")
    fp, cat = grid.footprint, grid.catalogue
    feat = ROOT / "data/raw/training_features.tif"
    if sha256(feat) != FEATURE_SHA:
        raise SystemExit("feature stack sha256 mismatch; refusing to run")
    # band 9 (TMI vertical gradient) is needed for the tilt angle, so it is added
    # to the model band list for this lane even though G79-MFX did not use it.
    chan = mfx.load_channels(feat, fp, tuple(sorted(set(mfx.MODEL_BANDS) | {9})))
    coh = mfx.structure_coherence(chan)
    tilt = tilt_angle(chan)
    variants = {
        "A_coherence": coh > COH_T,
        "B_tilt": np.abs(tilt) < TILT_T,
        "C_union": (coh > COH_T) | (np.abs(tilt) < TILT_T),
    }
    del tilt
    out = {"lane": "G79-ECE", "preregistration": "registry/preregistration_g79_ece.json",
           "fixed": {"coherence_threshold": COH_T, "tilt_threshold": TILT_T,
                     "lattice_px": PITCH, "max_dots": MAX_DOTS},
           "input_receipts": {"training_features_sha256": FEATURE_SHA},
           "holdout": {}, "variants": {}}
    for key, region in variants.items():
        out["variants"][key] = {"region_fraction_of_footprint": float((region & fp).sum() / fp.sum())}
    lat = lattice(fp.shape)
    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        masked_known = folds[0]["masked_known"]
        truth = np.zeros(fp.shape, bool)
        for f in folds:
            truth |= f["truth"]
        active = fp & ~masked_known
        entry = {"enrichment": {}, "arms": {}}
        for key, region in variants.items():
            entry["enrichment"][key] = enrichment(region, active, truth)
        per_arm = {}
        for key, region in variants.items():
            allowed = active & region
            dots = lat & allowed
            if dots.sum() > MAX_DOTS:
                keep = np.flatnonzero(dots.ravel())[:MAX_DOTS]
                dots = np.zeros(fp.shape, bool)
                dots.ravel()[keep] = True
            per_arm[key] = dots
        terms_arms = {}
        for key, dots in per_arm.items():
            terms = []
            for f in folds:
                _r, trm = evaluate_holdout.evaluate(dots.astype(np.float32), f, fp)
                terms.append(trm)
            terms_arms[key] = np.vstack(terms)
        rng = np.random.default_rng(seed + 999)
        idx = np.flatnonzero(active.ravel())
        pick = rng.choice(idx, size=min(int(per_arm["C_union"].sum()), idx.size), replace=False)
        uni = np.zeros(fp.shape, bool)
        uni.ravel()[pick] = True
        u_terms = []
        for f in folds:
            _r, trm = evaluate_holdout.evaluate(uni.astype(np.float32), f, fp)
            u_terms.append(trm)
        terms_arms["UNIFORM"] = np.vstack(u_terms)
        pooled = evaluate_holdout.pooled_summary(terms_arms, draws=1000, seed=520810,
                                                 candidate="C_union")
        entry["arms"] = {k: {"dti": pooled["scores"][k]["dti"],
                             "ci95": pooled["scores"][k]["ci95"],
                             "withheld_positive_pixels": pooled["scores"][k]["withheld_positive_pixels"],
                             "dots": int(per_arm[k].sum()) if k in per_arm else int(uni.sum())}
                         for k in pooled["scores"]}
        entry["paired_differences"] = pooled["paired_differences"]
        entry["incumbent"] = THVC[f"seed{seed}"]
        out["holdout"][f"seed{seed}"] = entry
        print(f"seed{seed} " + " ".join(f"{k}={v['dti']:.4f}" for k, v in entry["arms"].items())
              + f" enrichC={entry['enrichment']['C_union']['enrichment']:.2f}", flush=True)
        del folds, uni, per_arm, terms_arms

    # ---- final artifact: full catalogue, primary variant C ----
    region = variants["C_union"]
    allowed = fp & ~cat & region
    dots = lat & allowed
    if dots.sum() > MAX_DOTS:
        keep = np.flatnonzero(dots.ravel())[:MAX_DOTS]
        dots = np.zeros(fp.shape, bool)
        dots.ravel()[keep] = True
    dist_cat = ndi.distance_transform_edt(~cat)
    out["final"] = {"dots": int(dots.sum()),
                    "pct_footprint": float(100.0 * dots.sum() / fp.sum()),
                    "median_dist_to_catalogue_m": float(np.median(dist_cat[dots]) * 100.0),
                    "frac_gt_1km_from_catalogue": float((dist_cat[dots] > 10).mean()),
                    "on_catalogue": int((dots & cat).sum())}
    dest = ROOT / "docs" / "downloads" / f"{NAME}-{int(dots.sum())}dots.tif"
    for suf in (".tif", ".zip", ".json"):
        q = dest.with_suffix(suf)
        if q.exists():
            q.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    receipt = write_submission(dest, dots.astype(np.float32),
                               ROOT / "data/reference/sample_submission.tif", fp,
                               note=NOTE, name=NAME, catalogue=cat,
                               metadata={"lane": "G79-ECE", "pitch_px": PITCH})
    out["submission"] = {"name": NAME, "note": NOTE, "note_chars": len(NOTE),
                         "file": str(dest.relative_to(ROOT)), "sha256": sha256(dest),
                         "bytes": dest.stat().st_size, "dots": int(dots.sum()),
                         "validator_all_checks_passed": receipt["validator"]["all_checks_passed"],
                         "validator_checks": receipt["validator"]["checks"]}
    out["elapsed_s"] = round(time.time() - t0, 1)
    (ROOT / "evidence" / "ece_experiment2.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(json.dumps(out["final"], indent=1), flush=True)
    print("wrote", out["submission"]["file"], out["submission"]["sha256"][:16], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
