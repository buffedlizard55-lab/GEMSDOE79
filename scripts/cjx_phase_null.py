#!/usr/bin/env python3
"""G79-CJX preregistered falsification diagnostic: phase-randomized null.

Rebuild a single-scale (sigma=2) junction surface from power-spectrum-matched
phase-randomized RTP/gravity fields.  Junctions are a phase-alignment
phenomenon, so if the real surface's holdout skill survives phase
randomization, the junction reading is falsified (skill would be coming from
field power/texture, not from multi-strike junctions).  Diagnostic only;
never a candidate and never tuned.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import evaluate_holdout as ev  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gems79.cjx import fill_invalid, geomean2, junction_at_scale, percentile_rank, phase_randomized  # noqa: E402
from gems79.placement import place  # noqa: E402

RAW = ROOT / "data" / "raw"
CACHE = ROOT / ".cache" / "cjx"
OUT = ROOT / "evidence" / "cjx"
BUDGET = 20_000


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def main():
    grid = load_grid(RAW)
    fp, cat = grid.footprint, grid.catalogue
    null_ranks, real_ranks = {}, {}
    with rasterio.open(RAW / "training_features.tif") as s:
        for band, key, seed in ((2, "rtp", 7919), (13, "grav", 7927)):
            a = s.read(band).astype(np.float32)
            valid = np.isfinite(a) & (a > -1e30) & fp
            filled, _ = fill_invalid(a, valid)
            del a
            null_field = phase_randomized(filled, seed)
            del filled
            j_null, _sm = junction_at_scale(null_field, valid, 2.0)
            del null_field, _sm
            null_ranks[key] = percentile_rank(j_null, valid)
            del j_null
            real_ranks[key] = percentile_rank(np.load(CACHE / f"j_{key}_s2.npy"), valid)
            del valid
            log("field done", key)
    surfaces = {
        "REAL_S2": geomean2(real_ranks["rtp"], real_ranks["grav"]),
        "PHASE_NULL_S2": geomean2(null_ranks["rtp"], null_ranks["grav"]),
    }
    del null_ranks, real_ranks
    dcat = ndi.distance_transform_edt(~cat)
    n_glob = int((fp & (dcat > 2)).sum())
    del dcat
    results = {}
    for seed in (20, 30):
        folds, _ = buffered_component_draw(grid, seed=seed, buffer_px=3)
        terms = {k: None for k in surfaces}
        for arm, surf_full in surfaces.items():
            for fold in folds:
                dknown = ndi.distance_transform_edt(~fold["masked_known"])
                allowed = fold["region"] & fp & ~fold["masked_known"] & (dknown > 2)
                del dknown
                budget = int(round(BUDGET * int(allowed.sum()) / n_glob))
                dots, _info = place(np.where(allowed, surf_full, 0).astype(np.float32),
                                    allowed, budget, spacing=3)
                _, term = ev.evaluate(dots.astype(np.float32), fold, fp)
                terms[arm] = term if terms[arm] is None else terms[arm] + term
                del allowed, dots, term
            log("seed", seed, arm, "done")
        results[f"seed{seed}"] = ev.pooled_summary(
            terms, draws=1000, seed=520810 + seed, candidate="REAL_S2")
        log("seed", seed, {k: round(v["dti"], 4) for k, v in results[f"seed{seed}"]["scores"].items()})
        del folds, terms
    payload = {
        "evidence_class": "HOLDOUT-DTI diagnostic (falsification null, not a candidate)",
        "evaluator_version": ev.VERSION,
        "phase_randomization_seeds": {"rtp": 7919, "grav": 7927},
        "per_seed": results,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phase_null.json").write_text(json.dumps(payload, indent=2) + "\n")
    log("written evidence/cjx/phase_null.json")


if __name__ == "__main__":
    main()
