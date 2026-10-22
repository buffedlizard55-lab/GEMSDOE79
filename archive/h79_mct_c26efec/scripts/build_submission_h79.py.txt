#!/usr/bin/env python3
"""Lane H79-MCT — build the candidate submission from the full catalogue.

Steps (all deterministic, seed 79):
1. HGB scarp likelihood ``p`` trained on every catalogue pixel vs catalogue-free negatives
   (same recipe as the holdout folds), predicted over the whole footprint.
2. Continuity surface ``S = sqrt(p * Sato01(p))``.
3. 37,654 binary dots (champion-anchored budget) by decreasing ``S``, 2.8 px apart, strictly
   > 2 px from the catalogue, at most 66 % inside the 3-px halo of the H19-5 line set.
4. Written ONLY through the shared ``gems57.submission_writer.write_submission`` (which
   refuses NaN, out-of-range, outside-footprint or on-catalogue mass) to docs/downloads/.

Outputs: docs/downloads/<name>.tif/.zip/.json, data/cache/final/{p,s,dots}.npy,
evidence/build_h79.json (construction receipt).  The registry audit and the run card are
produced by scripts/audit_h79.py afterwards; nothing here declares the file submittable.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import submission_writer as SW  # noqa: E402
from gems79 import data as D, features as F, model as MD, trace as T  # noqa: E402

FINAL = ROOT / "data" / "cache" / "final"
DOWNLOADS = ROOT / "docs" / "downloads"


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=37_654)
    ap.add_argument("--exclusion", type=float, default=2.0)
    ap.add_argument("--mix", type=float, default=0.5)
    ap.add_argument("--quota", type=float, default=0.66)
    ap.add_argument("--stamp", default=time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    ap.add_argument("--cap-from-audit", default=None,
                    help="registry audit JSON of a previous build; every discriminating prior whose forward "
                         "overlap exceeded --cap-threshold there gets a per-prior cap (amendment A1)")
    ap.add_argument("--cap-threshold", type=float, default=0.60)
    ap.add_argument("--cap-share", type=float, default=0.68)
    args = ap.parse_args()
    t0 = time.time()
    FINAL.mkdir(parents=True, exist_ok=True)
    F.build()
    grid = D.load_grid()
    foot, cat = grid.footprint, grid.catalogue
    stack = np.load(F.STACK, mmap_mode="r")
    cols = MD.feature_columns()
    rng = np.random.default_rng(79)

    p_path = FINAL / "p_full.npy"
    if p_path.exists():
        p = np.load(p_path)
        log("loaded cached full-catalogue p")
        train_info = json.loads((FINAL / "train_info.json").read_text())
    else:
        idx, y, train_info = MD.sample_training(cat, foot, foot, rng, max_pos=60_988)
        log(f"full-catalogue training set {train_info}")
        clf = MD.fit(stack, cols, idx, y, tag="FULL")
        train_info["feature_importance_note"] = "HGB has no native importances; see holdout canary AUCs"
        p = MD.predict(clf, stack, cols, foot)
        np.save(p_path, p)
        (FINAL / "train_info.json").write_text(json.dumps(train_info, indent=2))
        del clf
        gc.collect()
        log(f"p predicted over footprint ({time.time() - t0:.0f}s)")

    s = T.continuity_surface(p, foot, mix=args.mix)
    np.save(FINAL / "s_full.npy", s)
    allowed = T.allowed_domain(foot, cat, args.exclusion)
    h19 = D.read_h19_5_support()
    h19_halo = T.halo(h19, 3.0)
    capped_priors = []
    if args.cap_from_audit:
        audit = json.loads(Path(args.cap_from_audit).read_text())
        seen = set()
        for r in sorted((r for r in audit["rows"] if "error" not in r and r["halo_coverage"] < 0.70
                         and r["forward_overlap"] > args.cap_threshold), key=lambda r: -r["forward_overlap"]):
            k = (r["their_dots"], round(r["halo_coverage"], 6), round(r["forward_overlap"], 6))
            if k not in seen:
                seen.add(k)
                capped_priors.append({"file": r["file"], "their_dots": r["their_dots"],
                                      "unconstrained_overlap": r["forward_overlap"], "halo_coverage": r["halo_coverage"]})
        log(f"amendment A1: capping {len(capped_priors)} distinct priors at {args.cap_share:.2f} of the budget each")
        bits, nh = T.halo_bits_from_rasters([ROOT / c["file"] for c in capped_priors], foot)
        # the H19-5 halo is capped as well (pre-registered quota), as one more bit
        if nh < 63:
            bits |= (h19_halo.astype(np.int64) << nh)
            nh += 1
        dots, info = T.emit_dots_multi(s, allowed, args.budget, bits, nh, cap_share=args.cap_share, candidate_factor=40)
        del bits
    else:
        dots, info = T.emit_dots(s, allowed, args.budget, quota_mask=h19_halo, quota_share=args.quota)
    np.save(FINAL / "dots_full.npy", dots)
    log(f"dots: {info}")

    pred = np.where(dots, np.float32(1.0), np.float32(0.0))
    pred[~foot] = 0.0
    sha8 = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    tag = "capped" if capped_priors else "continuity"
    name = f"gems79-h79-mct-{tag}-{args.budget}-{args.stamp}-{sha8}-zeros"
    note = ("H79-MCT terrain-only lidar+10m scarp likelihood x Sato line-continuity; "
            f"{int(dots.sum())} binary dots 2.8px apart >2px off catalogue; zeros outside")
    assert len(note) <= 140, len(note)

    # construction diagnostics
    dist_cat = ndi.distance_transform_edt(~cat)
    dcat = dist_cat[dots]
    lid_ok = D.lidar_valid()
    ys, xs = np.nonzero(dots)
    pts = np.stack([ys, xs], 1)
    from scipy.spatial import cKDTree
    nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    diag = {
        "dots": int(dots.sum()), "budget": args.budget, "emit_info": info,
        "amendment_A1_capped_priors": capped_priors, "cap_share": args.cap_share if capped_priors else None,
        "min_dist_to_catalogue_px": float(dcat.min()), "dist_to_catalogue_km_pct": {
            "<=0.4": float((dcat <= 4).mean()), "0.4-2": float(((dcat > 4) & (dcat <= 20)).mean()),
            "2-6": float(((dcat > 20) & (dcat <= 60)).mean()), ">6": float((dcat > 60).mean())},
        "nn_spacing_px_pct": {k: float(np.percentile(nn, q)) for k, q in (("p5", 5), ("p50", 50), ("p95", 95))},
        "dots_in_h19_5_halo": int((dots & h19_halo).sum()),
        "share_in_h19_5_halo": float((dots & h19_halo).sum() / dots.sum()),
        "dots_in_lidar_gap": int((dots & ~lid_ok).sum()),
        "share_in_lidar_gap": float((dots & ~lid_ok).sum() / dots.sum()),
        "lidar_gap_share_of_allowed": float((allowed & ~lid_ok).sum() / allowed.sum()),
        "s_threshold_last_dot": float(s[dots].min()), "s_p50_dots": float(np.median(s[dots])),
    }
    log(json.dumps(diag, indent=1))

    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    out = DOWNLOADS / f"{name}.tif"
    receipt = SW.write_submission(out, pred, D.RAW / "sample_submission.tif", foot, note=note, name=name,
                                  catalogue=cat, metadata={"lane": "H79-MCT", "construction": diag,
                                                           "training": train_info, "mix": args.mix,
                                                           "exclusion_px": args.exclusion, "quota": args.quota})
    build = {"evidence_class": "BUILD-RECEIPT", "lane": "H79-MCT", "name": name, "note": note, "note_chars": len(note),
             "tif": str(out.relative_to(ROOT)), "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
             "decoded_sha256": hashlib.sha256(pred.tobytes()).hexdigest(), "construction": diag,
             "training": train_info, "writer_receipt": receipt if isinstance(receipt, dict) else str(receipt),
             "features": F.CHANNELS, "hgb": MD.HGB_KW, "runtime_s": round(time.time() - t0, 1),
             "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (ROOT / "evidence" / "build_h79.json").write_text(json.dumps(build, indent=2, default=str) + "\n")
    log(f"wrote {out} sha256={build['sha256']}")


if __name__ == "__main__":
    main()
