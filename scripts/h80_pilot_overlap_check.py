#!/usr/bin/env python3
"""Surface and dot overlap check for the H80 pilots (protocol item 1). Corrected at session 842c8c7c.

For each seed (20, 30) this regenerates, with the pilots' own functions and their own per-seed
mask (footprint & distance-from-visible > 2 px, from holdout.buffered_component_draw), the dots of:
  * DRAPE arm A (notch) and arm B (control, no notch)
  * RADIO arm A (thorium-normalised K residual) and arm B (raw K)
and measures against registry rasters (no holdout truth is used):
  * dot overlap: fraction of pilot dots within 3 px of a registry dot
  * surface rank correlation: Spearman between the pilot score and the registry mask
Comparators: H33 (GEMSDOE32, blob 17a768...), D2.8 (GEMSDOE25, blob bfb7e8...),
G79-THVC (docs/downloads canonical TIF, sha256 d3db2e95...).
Correction note: an earlier version used the full-catalogue mask and took build_scores' second return
value (the raw-K control) as the RADIO arm A. Both errors are fixed here.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
import run_h80_drape_pilot as D  # noqa: E402
import run_h80_radio_pilot as R  # noqa: E402

COMPARATORS = {
    "H33_GEMSDOE32": ROOT / ".cache/registry/17a76895f68174cc93f3cb1597d25686f6d6bc67.tif",
    "D2.8_GEMSDOE25": ROOT / ".cache/registry/bfb7e86d046dd178c3d6ab60522861b5464dd420.tif",
    "G79-THVC_canonical": ROOT / "docs/downloads/g79-thvc-ccsubmod-20261021-b262e265-zeros-DO-NOT-SUBMIT.tif",
}


def within3(dots_a, dots_b):
    if dots_a.sum() == 0 or dots_b.sum() == 0:
        return 0.0
    dist = ndi.distance_transform_edt(~dots_b)
    return float((dist[dots_a] <= D.SEP_PX).mean())


def place(score_raw, allowed, footprint):
    s = D.normalise(score_raw, allowed)
    cand = np.flatnonzero((allowed & footprint).ravel())
    order = cand[np.argsort(-s.ravel()[cand], kind="stable")]
    return D.greedy_place(order, footprint.shape, D.BUDGET, D.SEP_PX), s


def main():
    grid = load_grid(ROOT / "data/raw")
    fp = grid.footprint
    comp = {}
    for name, p in COMPARATORS.items():
        with rasterio.open(p) as ds:
            a = ds.read(1)
        comp[name] = (np.isfinite(a) & (a > 0) & fp)
    rtp = D.load_rtp()
    s_notch = D.tilt_edge_score(rtp, fp, notch=True)
    s_ctrl = D.tilt_edge_score(rtp, fp, notch=False)
    del rtp
    k, th, _ = R.load_k_th()
    s_radio_a, s_radio_b, _ = R.build_scores(k, th, fp)  # (Th-normalised residual, raw K)
    idx = np.flatnonzero(fp.ravel())[::7]
    out = {"per_seed": {}, "comparators": {}}
    for seed in (20, 30):
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, buffer_px=3, boundary_px=12)
        d_vis = ndi.distance_transform_edt(~folds[0]["visible"])
        allowed = fp & (d_vis > 2.0)  # identical to the pilots' per-seed mask
        rec = {}
        for label, raw in (("DRAPE_A_notch", s_notch), ("DRAPE_B_control", s_ctrl),
                           ("RADIO_A_th_normalised_K", s_radio_a), ("RADIO_B_raw_K", s_radio_b)):
            dots, s = place(raw, allowed, fp)
            r = {"dots": int(dots.sum()), "within_3px": {}, "spearman": {}}
            for cname, cmask in comp.items():
                r["within_3px"][cname] = round(within3(dots, cmask), 4)
                r["spearman"][cname] = round(float(spearmanr(s.ravel()[idx], cmask.ravel()[idx]).statistic), 4)
            rec[label] = r
        out["per_seed"][str(seed)] = rec
    for cname, p in COMPARATORS.items():
        out["comparators"][cname] = {"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                      "positive_pixels_in_footprint": int(comp[cname].sum())}
    worst_overlap = max(v for s in out["per_seed"].values() for r in s.values() for v in r["within_3px"].values())
    worst_rho = max(abs(v) for s in out["per_seed"].values() for r in s.values() for v in r["spearman"].values())
    out["summary"] = {"max_within_3px": round(worst_overlap, 4), "max_abs_spearman": round(worst_rho, 4),
                      "rule": "duplicate if rank corr > 0.90 or > 70 pct of dots within 3 px of one registry raster",
                      "result": "NOT DUPLICATES" if (worst_overlap <= 0.70 and worst_rho <= 0.90) else "DUPLICATE RULE TRIGGERED"}
    Path(ROOT / "evidence/h80_pilot_overlap_check.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["summary"], indent=2))


if __name__ == "__main__":
    main()
