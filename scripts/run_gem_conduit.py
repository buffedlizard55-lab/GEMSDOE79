#!/usr/bin/env python3
"""Lane G79-GEM: concealed-geothermal-conduit surface (single method lane).

Builds a catalogue-independent surface from two training_feature channels:
  band 18 iso_grav_anom_hg (gravity-gradient edge) x (1 - band 1 mag_anom rank)
  (magnetic demagnetization low), zeroed on the mapped catalogue and outside
  the footprint, normalised to [0,1].

Runs the hide-and-recover holdout (gems57-pooled-hide-v2, alpha 0.2, beta 0.8,
300 m triangular kernel) on seeds 20 and 30, with a feature-alone leakage
canary for each channel, then emits sparse dots and writes a locally validated
submission GeoTIFF + ZIP.  Nothing here is organizer-accepted: ok_to_submit is
NO unless a separate selector binds a receipt and the account shows a free
weekly slot on DrivenData (both are login-gated and outside this checkout).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from gems57 import grid as G, holdout as HO, evaluate_holdout as EH, metric as M  # noqa: E402
from gems57.emit import emit_decimated, emit_prefix, expected_credit  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems57.validate import validate  # noqa: E402
from gems79.gem_conduit import build_conduit_surface, sym_auc  # noqa: E402

BUDGET_DOTS = 37_654
CANVAS_NEG = 200_000
SEEDS = (20, 30)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def from_terms(terms):
    a = np.asarray(terms, dtype=float)
    tp, fp, fn = a[..., 0], a[..., 1], a[..., 2]
    return float(tp.sum() / (tp.sum() + M.ALPHA * fp.sum() + M.BETA * fn.sum() + M.EPS))


def to_native(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.generic,)):
        return o.item()
    if isinstance(o, dict):
        return {k: to_native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_native(v) for v in o]
    return o


def bootstrap_ci(terms_all: np.ndarray, draws: int = 1000, seed: int = 1):
    n = int(terms_all.shape[0])
    rng = np.random.default_rng(seed)
    out = np.empty(draws, np.float64)
    for k in range(draws):
        pick = rng.integers(0, n, size=n)
        t = terms_all[pick].sum(axis=0)
        out[k] = t[0] / (t[0] + M.ALPHA * t[1] + M.BETA * t[2] + M.EPS)
    return [float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))]


def neg_sample(rng, footprint, hidden, visible, n):
    dist_vis = ndi.distance_transform_edt(~visible)
    pool = np.flatnonzero(footprint & (dist_vis > 3) & ~hidden)
    if pool.size == 0:
        pool = np.flatnonzero(footprint & ~hidden)
    take = min(n, pool.size)
    return rng.choice(pool, size=take, replace=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=20, help="single holdout seed to run (default 20)")
    ap.add_argument("--both-seeds", action="store_true",
                    help="run seeds 20 and 30 and report the 2-seed pooled CI")
    args = ap.parse_args()

    t0 = time.time()
    stack = ROOT / "data" / "raw" / "training_features.tif"
    sample = ROOT / "data" / "raw" / "sample_submission.tif"
    grid = G.load_grid(ROOT / "data" / "raw")
    foot, cat = grid.footprint, grid.catalogue
    allowed = foot & ~cat
    print(f"grid {grid.shape} footprint {int(foot.sum())} catalogue {int(cat.sum())}"
          f" allowed {int(allowed.sum())}", flush=True)

    built = build_conduit_surface(stack, foot, cat)
    built.pop("valid", None)  # not JSON-serializable; not needed downstream
    surface = built["surface"]
    print(f"conduit surface: positive {built['positive_pixels']:,} max {built['surface_max']:.4f}",
          flush=True)

    # ---------- leakage canary: each feature alone ----------
    rng = np.random.default_rng(79000)
    canary = {}
    for name, feat in (("gravity_edge_rank", built["g_edge_rank"]),
                       ("mag_demag_low", built["mag_low"])):
        aucs = []
        for seed in SEEDS:
            folds, _ = HO.buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
            hidden = folds[0]["hidden_all"]
            visible = folds[0]["visible"]
            pos = np.flatnonzero(hidden)
            neg = neg_sample(rng, foot, hidden, visible, CANVAS_NEG)
            aucs.append(sym_auc(feat, pos, neg))
        canary[name] = {"auc_per_seed": aucs, "max_sym_auc": float(max(aucs))}
        print(f"canary {name}: seed AUCs {[round(a,4) for a in aucs]} max {max(aucs):.4f}",
              flush=True)
    leak = [n for n, c in canary.items() if c["max_sym_auc"] > 0.90]
    print(f"leakage channels >0.90: {leak}", flush=True)

    # ---------- holdout: combined surface -> sparse dots -> submission ----------
    ek = expected_credit(surface)
    ek = np.where(allowed, ek, 0.0)
    ranked, _ = emit_decimated(surface, allowed, tile_px=3, floor=0.0)

    results = {"lane": "G79-GEM", "method": "concealed-conduit gravity-edge x mag-demag",
               "evidence_class": "HOLDOUT-DTI", "evaluator_version": EH.VERSION,
               "alpha": M.ALPHA, "beta": M.BETA, "kernel_radius_m": M.R_M,
               "budget_dots": BUDGET_DOTS, "canary": canary,
               "leakage_channels_gt_0p90": leak, "surface": built}

    seeds = SEEDS if args.both_seeds else (args.seed,)
    all_terms = []
    for seed in seeds:
        folds, _ = HO.buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        hidden_all = np.logical_or.reduce([f["hidden_all"] for f in folds])
        k_truth = int(hidden_all.sum())
        dots = emit_prefix(ranked, BUDGET_DOTS)
        dots = dots & allowed  # never on catalogue
        per = {}
        fold_terms = []
        for f in folds:
            res, terms = EH.evaluate(dots.astype(np.float32), f,
                                     valid=grid.footprint & f["region"])
            per[f["name"]] = {"dti": float(res["dti"]), "n_truth": int(res["n_truth"]),
                              "emitted": int(res["n_emitted"])}
            fold_terms.append(terms)
        terms_seed = np.concatenate(fold_terms, axis=0)
        totals = terms_seed.sum(axis=0)
        pooled_seed = totals[0] / (totals[0] + M.ALPHA * totals[1] + M.BETA * totals[2] + M.EPS)
        ci = bootstrap_ci(terms_seed)
        print(f"seed {seed}: withheld {k_truth:,} dots {int(dots.sum()):,}"
              f" pooled HOLDEOUT-DTI {pooled_seed:.4f} CI [{ci[0]:.4f}, {ci[1]:.4f}]"
              f" per_fold { {k: round(v2['dti'],4) for k,v2 in per.items()} }", flush=True)
        results[f"seed{seed}"] = {"withheld_positive_pixels": k_truth,
                                  "dots": int(dots.sum()),
                                  "pooled_dti": pooled_seed, "ci95": ci,
                                  "per_fold": per, "fold_receipts": [f["receipt"] for f in folds]}
        all_terms.append(terms_seed)

    # 2-seed summary
    terms_all = np.concatenate(all_terms, axis=0)
    totals = terms_all.sum(axis=0)
    pooled = totals[0] / (totals[0] + M.ALPHA * totals[1] + M.BETA * totals[2] + M.EPS)
    ci2 = bootstrap_ci(terms_all, seed=2)
    per_seed = [results[f"seed{s}"]["pooled_dti"] for s in seeds]
    print(f"2-seed pooled HOLDEOUT-DTI {pooled:.4f} CI [{ci2[0]:.4f}, {ci2[1]:.4f}]"
          f" per_seed {[round(p,4) for p in per_seed]}", flush=True)
    results["two_seed"] = {"pooled_dti": float(pooled), "ci95": ci2,
                           "per_seed": per_seed, "withheld_positive_pixels": int(totals[3])}
    results["best_holdout_dti"] = float(pooled)

    # ---------- write submission (binary dots, best holdout surface) ----------
    prediction = dots.astype(np.float32)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    digest = sha256_file(stack)[:12]
    name = f"gems79-gem-conduit-gravity-maglow-{int(prediction.sum())}dots-{stamp}-{digest}"
    if len(name) > 140:
        name = name[:140]
    note = ("GEMSDOE79 G79-GEM concealed conduit: gravity-gradient x magnetic-low "
            "blind-fault surface, top dots; HOLDEOUT-DTI research only")
    if len(note) > 140:
        note = note[:140]

    out_dir = ROOT / "artifacts" / "gem_conduit"
    out_dir.mkdir(parents=True, exist_ok=True)
    tif_path = out_dir / f"{name}.tif"

    receipt = write_submission(
        tif_path, prediction, sample, foot,
        name=name, note=note, catalogue=cat,
        metadata={"lane": "G79-GEM", "method": "concealed-conduit",
                  "holdout": to_native(results), "canary": to_native(canary),
                  "budget_dots": BUDGET_DOTS},
    )
    print(f"wrote {tif_path} ({receipt['bytes']} bytes, sha256 {receipt['sha256'][:12]}…)",
          flush=True)

    # ---------- local format validation ----------
    from scripts.validate_submission import validate_path  # noqa: E402
    val = validate_path(tif_path)
    print(f"format validation: passed={val['format_passed']}", flush=True)
    results["format_validation"] = val

    # ---------- run card + status ----------
    card = {
        "schema_version": 2, "lane": "G79-GEM",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": ("Concealed geothermal conduit faults (blind, absent from the "
                       "USGS/INGENIOUS catalogue) coincide with a strong isostatic-gravity "
                       "horizontal-gradient edge and a magnetic-anomaly low "
                       "(hydrothermal demagnetization/smectite alteration). "
                       "Surface = gravity-edge rank x (1 - magnetic-anomaly rank), "
                       "zeroed on the catalogue and outside the footprint."),
        "mechanism": ("Two training_feature channels (band 18 iso_grav_anom_hg, band 1 "
                      "mag_anom) -> empirical unit ranks -> product surface -> top "
                      f"{BUDGET_DOTS} dots via kernel-credit ranking; sparse binary "
                      "emission in [0,1], zero outside footprint and on mapped faults."),
        "named_non_fault_mimic": ("Pleistocene pluvial shoreline benches, fluvial terrace "
                                  "risers, welded caldera cooling joints, and lateral "
                                  "thermal outflow plumes can also produce gravity/magnetic "
                                  "edges or lows without being geothermal faults."),
        "holdout_dti": {
            "evidence_class": "HOLDEOUT-DTI", "evaluator_version": EH.VERSION,
            "dti": float(pooled), "ci95": ci2,
            "withheld_positive_pixels": int(totals[3]),
            "per_seed": {f"seed_{s}": {"dti": results[f"seed{s}"]["pooled_dti"],
                                       "ci95": results[f"seed{s}"]["ci95"],
                                       "withheld_positive_pixels": results[f"seed{s}"]["withheld_positive_pixels"]}
                         for s in seeds},
            "source_pointer": "scripts/run_gem_conduit.py",
        },
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY",
            "auc": float(max(c["max_sym_auc"] for c in canary.values())),
            "passed": bool(len(leak) == 0),
            "required_threshold": 0.90,
            "features_cleared": len(canary),
            "n_suspicious_gt_0p90": len(leak),
            "per_feature": canary,
        },
        "submission_file": f"artifacts/gem_conduit/{name}.tif",
        "zip_file": f"artifacts/gem_conduit/{name}.zip",
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "submission_name": name,
        "submission_note": note,
        "positive_pixels": int(prediction.sum()),
        "validator": receipt["validator"],
        "runtime_s": round(time.time() - t0, 1),
        "ok_to_download": bool(val["format_passed"]),
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "verdict": "negative_research_artifact",
        "blockers": [
            "No DrivenData login: cannot auto-subscribe or obtain an organizer receipt.",
            "Weekly slot / eligibility not observable from this checkout (account-side).",
            "protocol_unique not measured vs the full 992-raster registry (registry rasters not cached locally).",
        ],
        "note": "OK TO DOWNLOAD: YES (locally validated research GeoTIFF). OK TO SUBMIT: NO "
                "(no organizer receipt; weekly slot unverified; submit manually via DrivenData if desired).",
    }
    card_path = ROOT / "run_card_gem_conduit.json"
    card_path.write_text(json.dumps(to_native(card), indent=2, allow_nan=False) + "\n")
    print(f"wrote run card {card_path}", flush=True)

    status = {
        "ok_to_download": bool(val["format_passed"]),
        "ok_to_submit": False,
        "verdict": "negative",
        "decision_line": "OK TO DOWNLOAD: YES. OK TO SUBMIT: NO.",
        "file": f"artifacts/gem_conduit/{name}.tif",
        "zip": f"artifacts/gem_conduit/{name}.zip",
        "sha256": receipt["sha256"],
        "name": name,
        "note": note,
        "holdout_dti": float(pooled),
        "holdout_ci95": ci2,
        "account_side_conditions": [
            "A free weekly slot must be shown on your DrivenData submission page.",
            "You must be a registered, eligible participant who accepted the competition rules.",
        ],
        "scope": "Novel research artifact generated by lane G79-GEM; locally format-validated only. "
                 "Not organizer acceptance or a uniqueness clearance vs the full registry.",
    }
    status_path = ROOT / "docs" / "status_gem_conduit.json"
    status_path.write_text(json.dumps(status, indent=2) + "\n")
    print(f"wrote status {status_path}", flush=True)
    print(json.dumps(status, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
