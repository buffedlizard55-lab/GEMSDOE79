#!/usr/bin/env python3
"""Experiment E2 (cap contingency fired): HOLDOUT-DTI cost of the Amendment-B1
per-prior 0.68 cap, measured on the cached OOF A3 surfaces with identical
folds/evaluator/emission. Writes evidence/cap_cost_g79b.json. No retuning."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import holdout as HO, evaluate_holdout as EH  # noqa: E402
from gems79b import data as D, trace as T  # noqa: E402

PROC = ROOT / "data/cache/holdout_g79b"
BUDGET = 37_654


def main():
    from gems79.lifecycle import require_open_lane
    require_open_lane(ROOT, "G79B-SDPT")
    emit_info = json.loads((ROOT / "data/cache/final_g79b/emit_info.json").read_text())
    caps = emit_info.get("capped_priors")
    if not caps:
        (ROOT / "evidence/cap_cost_g79b.json").write_text(json.dumps(
            {"cap_fired": False, "cost": None}, indent=2) + "\n")
        print("cap contingency did not fire; E2 not needed")
        return
    assert len(caps) <= 63, "bit-packed cap path requires <= 63 priors"
    grid = D.load_grid()
    foot = grid.footprint
    bits = np.zeros(foot.shape, np.int64)
    for j, rec in enumerate(caps):
        with rasterio.open(rec["file"]) as src:
            a = src.read(1)
        bits |= (T.halo(np.isfinite(a) & (a > 0), 3.0).astype(np.int64) << j)
        print(f"halo {j + 1}/{len(caps)}", flush=True)
    out = {"cap_fired": True, "n_priors_capped": len(caps), "cap_share": 0.68,
           "evidence_class": "HOLDOUT-DTI", "evaluator_version": EH.VERSION, "seeds": {}}
    for seed in (20, 30):
        folds, _ = HO.buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        allowed = T.allowed_domain(foot, visible, 2.0)
        surf = np.load(PROC / f"oof_A3_seed{seed}.npy")
        tot = sum(int((f["region"] & allowed).sum()) for f in folds)
        dots = np.zeros(foot.shape, bool)
        for f in folds:
            a = f["region"] & allowed
            b = int(round(BUDGET * int(a.sum()) / max(tot, 1)))
            d, info = T.emit_dots_multi(surf, a, b, bits, len(caps), cap_share=0.68,
                                        candidate_factor=140)
            print(seed, f["name"], info, flush=True)
            dots |= d
        terms = None
        for f in folds:
            _, t = EH.evaluate(dots.astype(np.float32), f, valid=foot, block_side=200)
            terms = t if terms is None else terms + t
        capped = float(EH.from_terms(terms.sum(axis=0)))
        base = json.loads((ROOT / f"evidence/holdout_g79b_seed{seed}.json").read_text())
        unc = base["arms"]["A3_sdpt_trace"]["pooled_holdout_dti"]
        ctrl = base["arms"]["A1_control_h79_pixel"]["pooled_holdout_dti"]
        arch = {20: 0.1095, 30: 0.1152}[seed]
        out["seeds"][str(seed)] = {
            "unconstrained_A3": unc, "capped_A3": capped, "cap_cost": capped - unc,
            "control_A1": ctrl, "archived_best_H79_C2": arch,
            "capped_vs_control": capped - ctrl, "capped_vs_archived_best": capped - arch,
            "dots_emitted": int(dots.sum()),
            "withheld_positive_pixels": base["withheld_positive_pixels"]}
        print(seed, out["seeds"][str(seed)], flush=True)
    (ROOT / "evidence/cap_cost_g79b.json").write_text(json.dumps(out, indent=2, default=float) + "\n")


if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError
    try:
        main()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
