#!/usr/bin/env python3
"""Which offline proxy actually tracks the organiser's score?

The repo's inherited HOLDOUT-DTI withholds *catalogue* components, so it rewards
dots placed near mapped faults.  The artifact-linked study in
``evidence/score_geometry_study.json`` measured the opposite gradient in the
reported scores: inside the family's best habitat, median distance to the
catalogue correlates +0.905 with the reported score and the fraction of dots
within 500 m correlates -0.912.  A proxy that rewards proximity therefore cannot
be used to select a far-field candidate.

This script fixes FIVE candidate truth proxies up front -- all derived only from
restored, SHA-256-pinned public inputs, never from a registry raster -- scores
every ledger-matched family artifact against each with the official pooled DTI
(alpha 0.2, beta 0.8, 300 m triangular kernel, catalogue pixels masked), and
reports the rank correlation with the USER-REPORTED scores.

Every proxy is reported, including the ones that fail.  Selecting a proxy is a
meta-validation on 94 noisy user-reported pairings, and that limitation is
carried into the run card rather than hidden.

Output: evidence/proxy_validation.json
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57.grid import load_grid  # noqa: E402
from gems57.metric import dti_binary, kernel  # noqa: E402

OUT = ROOT / "evidence" / "proxy_validation.json"
S8 = np.ones((3, 3), bool)


def build_proxies(grid, cat):
    fp = grid.footprint
    cat3 = ndi.binary_dilation(cat, iterations=3)
    proxies = {}

    with rasterio.open(ROOT / "data/raw/external/derived_sgmc_faults_100m_u8.tif") as s:
        sg = (np.nan_to_num(s.read(1)) > 0) & fp
    lab, n = ndi.label(sg & ~cat3, structure=S8)
    sizes = ndi.sum_labels(np.ones_like(lab, float), lab, range(1, n + 1))
    big = np.isin(lab, 1 + np.flatnonzero(sizes >= 5))
    proxies["P1_xcd_sgmc_offcat_ge5px"] = dict(
        truth=big,
        definition=("SGMC compilation pixels more than 300 m from the competition catalogue, "
                    "keeping 8-connected components of at least 5 pixels"),
        source="data/raw/external/derived_sgmc_faults_100m_u8.tif")
    proxies["P2_sgmc_all"] = dict(
        truth=sg, definition="every SGMC compilation pixel inside the footprint",
        source="data/raw/external/derived_sgmc_faults_100m_u8.tif")
    # P3 is degenerate BY CONSTRUCTION and is kept only to prove the point: the
    # organiser masks catalogue pixels, so "the catalogue as truth" leaves zero
    # scored truth pixels. The organiser's truth therefore cannot be the catalogue.
    proxies["P3_catalogue_degenerate"] = dict(
        truth=cat,
        definition=("the competition catalogue itself, which is degenerate under the organiser's "
                    "own catalogue mask and is retained only as a proof that the scored truth "
                    "cannot be the catalogue"),
        source="data/reference/existing_faults.tif")

    # Qfaults named traces, rasterised from their in-footprint centroids.
    with (ROOT / "data/raw/external/gdr_qfaults_traces.csv").open() as f:
        qf = [r for r in csv.DictReader(f)]
    h, w = grid.shape
    qpts = np.zeros((h, w), bool)
    qoff = np.zeros((h, w), bool)
    n_in = n_off = 0
    for r in qf:
        try:
            rr, cc = int(float(r["centroid_row"])), int(float(r["centroid_col"]))
        except (KeyError, ValueError):
            continue
        if not (0 <= rr < h and 0 <= cc < w) or not fp[rr, cc]:
            continue
        n_in += 1
        qpts[rr, cc] = True
        if not cat3[rr, cc]:
            n_off += 1
            qoff[rr, cc] = True
    proxies["P4_qfaults_centroids_offcat"] = dict(
        truth=qoff,
        definition=(f"centroids of named Qfaults traces inside the footprint that lie more than "
                    f"300 m from the competition catalogue ({n_off} of {n_in} in-footprint centroids)"),
        source="data/raw/external/gdr_qfaults_traces.csv")
    proxies["P5_qfaults_centroids_all"] = dict(
        truth=qpts, definition=f"every in-footprint named Qfaults trace centroid ({n_in})",
        source="data/raw/external/gdr_qfaults_traces.csv")
    return proxies


def main() -> int:
    grid = load_grid(ROOT / "data/reference")
    fp = grid.footprint
    with rasterio.open(ROOT / "data/reference/existing_faults.tif") as s:
        cat = (np.nan_to_num(s.read(1)) > 0) & fp
    proxies = build_proxies(grid, cat)

    # Precompute per-proxy distance transforms once.
    for name, p in proxies.items():
        t = p["truth"] & fp & ~cat          # organiser masks catalogue pixels
        p["scored_truth"] = t
        p["n_truth"] = int(t.sum())
        p["edt_truth"] = ndi.distance_transform_edt(~t) if t.any() else None
        print(f"{name}: {p['n_truth']} scored truth pixels", flush=True)

    study = json.loads((ROOT / "evidence/score_geometry_study.json").read_text())
    arts = [r for r in study["rows"] if r.get("matched") and r.get("n_dots")]
    print(f"artifacts: {len(arts)}", flush=True)

    results = []
    for i, a in enumerate(arts):
        p = ROOT / ".cache/registry" / (a["blob"] + ".tif")
        with rasterio.open(p) as s:
            v = np.nan_to_num(s.read(1).astype(np.float32))
        dots = (v > 0) & fp
        edt_p = ndi.distance_transform_edt(~dots)
        row = dict(submission_name=a["submission_name"], site=a["site"], score=a["score"],
                   n_dots=a["n_dots"], blob=a["blob"],
                   dist_cat_median_m=a["dist_cat_median_m"])
        for name, pr in proxies.items():
            t = pr["scored_truth"]
            if not t.any() or pr["edt_truth"] is None:
                row[name] = None
                continue
            tp = float(kernel(edt_p[t]).sum())
            fn = pr["n_truth"] - tp
            fpix = float((1.0 - kernel(pr["edt_truth"][dots])).sum())
            val = tp / (tp + 0.2 * fpix + 0.8 * fn + 1e-12)
            row[name] = round(float(val), 6) if np.isfinite(val) else None
        results.append(row)
        if (i + 1) % 20 == 0:
            print(f"  scored {i+1}/{len(arts)}", flush=True)

    y = np.array([r["score"] for r in results])
    summary = {}
    for name in proxies:
        x = np.array([r[name] for r in results], float)
        ok = np.isfinite(x)
        rho, pv = (spearmanr(x[ok], y[ok]) if ok.sum() > 2 and np.ptp(x[ok]) > 0
                   else (float("nan"), float("nan")))
        # rank correlation restricted to the family's competitive regime
        top = y >= 0.15
        rho_top = float(spearmanr(x[top], y[top]).statistic) if (top & ok).sum() > 8 else None
        degenerate = int(ok.sum()) == 0 or proxies[name]["n_truth"] == 0
        summary[name] = dict(n=int(ok.sum()), n_truth=int(proxies[name]["n_truth"]),
                             degenerate_by_construction=degenerate,
                             spearman_all=(None if degenerate or not np.isfinite(rho) else float(rho)),
                             p_value_all=(None if degenerate or not np.isfinite(pv) else float(pv)),
                             spearman_score_ge_0_15=rho_top,
                             definition=proxies[name]["definition"],
                             source=proxies[name]["source"])
        print(f"{name}: n={int(ok.sum())} rho_all={rho:+.4f} p={pv:.2e} "
              f"rho(score>=0.15)={rho_top}", flush=True)

    out = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        evidence_class="RASTER-MEASUREMENT + USER-REPORTED score pairing",
        metric="official pooled DTI, alpha 0.2, beta 0.8, 300 m triangular kernel, catalogue pixels masked",
        scope=("Meta-validation of offline proxies against USER-REPORTED family scores. No proxy here "
               "is ORGANIZER-CONFIRMED, and no leaderboard score is projected. Choosing a proxy on the "
               "same 94 pairings it is then judged by is an acknowledged selection risk."),
        n_artifacts=len(results),
        proxies=summary,
        rows=results,
    )
    txt = json.dumps(out, indent=2, allow_nan=False)
    OUT.write_text(txt + "\n")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
