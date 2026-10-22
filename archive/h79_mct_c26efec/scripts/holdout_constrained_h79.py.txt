#!/usr/bin/env python3
"""Experiment 3 (amendment A1): does enforcing the duplicate rule *by construction* — at most 68 %
of dots inside the 3-px halo of ANY prior raster that the unconstrained candidate overlapped
> 0.60 — cost holdout performance?  Re-uses the cached OOF continuity surfaces of experiments 1–2
(no retraining), same folds, same evaluator; paired CIs vs the unconstrained emission.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import holdout as HO, evaluate_holdout as EH  # noqa: E402
from gems79 import data as D, trace as T  # noqa: E402

PROC = ROOT / "data" / "cache" / "holdout"


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def select_priors(threshold=0.60):
    audit = json.loads((ROOT / "evidence" / "registry_audit_h79.json").read_text())
    rows = [r for r in audit["rows"] if "error" not in r and r["halo_coverage"] < 0.70 and r["forward_overlap"] > threshold]
    seen, picked = set(), []
    for r in sorted(rows, key=lambda r: -r["forward_overlap"]):
        k = (r["their_dots"], round(r["halo_coverage"], 6), round(r["forward_overlap"], 6))
        if k in seen:
            continue
        seen.add(k); picked.append(r)
    return picked


def main():
    grid = D.load_grid(); foot = grid.footprint
    priors = select_priors()
    log(f"{len(priors)} distinct discriminating priors with unconstrained overlap > 0.60")
    bits, nh = T.halo_bits_from_rasters([ROOT / r["file"] for r in priors], foot)
    out = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": EH.VERSION, "amendment": "A1 multi-prior cap 0.68",
           "priors_capped": [{"file": r["file"], "their_dots": r["their_dots"], "unconstrained_overlap": r["forward_overlap"], "halo_coverage": r["halo_coverage"]} for r in priors],
           "seeds": {}}
    B = 37_654
    for seed in (30, 20):
        folds, _ = HO.buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        s = np.load(PROC / f"oof_s_seed{seed}.npy")
        allowed = T.allowed_domain(foot, visible, 2.0)
        tot = sum(int((f["region"] & allowed).sum()) for f in folds)
        arms = {}
        for name in ("unconstrained", "capped_0.68"):
            dots = np.zeros(foot.shape, bool); infos = []
            for f in folds:
                a = f["region"] & allowed
                b = int(round(B * int(a.sum()) / max(tot, 1)))
                if name == "unconstrained":
                    d, info = T.emit_dots(s, a, b)
                else:
                    d, info = T.emit_dots_multi(s, a, b, bits, nh, cap_share=0.68)
                dots |= d; infos.append(info)
            terms = None; per = {}
            for f in folds:
                res, t = EH.evaluate(dots.astype(np.float32), f, valid=foot, block_side=200)
                per[f["name"]] = {"dti": res["dti"], "n_truth": res["n_truth"], "emitted": res["n_emitted"]}
                terms = t if terms is None else terms + t
            arms[name] = {"terms": terms, "dots": int(dots.sum()), "per_fold": per, "emit_info": infos,
                          "pooled_holdout_dti": float(EH.from_terms(terms.sum(axis=0)))}
            log(f"seed {seed} {name}: pooled HOLDOUT-DTI={arms[name]['pooled_holdout_dti']:.4f} dots={int(dots.sum())}")
        summ = EH.pooled_summary({k: v["terms"] for k, v in arms.items()}, draws=1000, seed=520810, candidate="capped_0.68")
        out["seeds"][f"seed{seed}"] = {"withheld_positive_pixels": int(folds[0]["hidden_all"].sum()),
                                       "arms": {k: {kk: vv for kk, vv in v.items() if kk != "terms"} for k, v in arms.items()},
                                       "pooled_summary": summ}
    (ROOT / "evidence" / "holdout_h79_constrained.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    log("wrote evidence/holdout_h79_constrained.json")


if __name__ == "__main__":
    main()
