#!/usr/bin/env python3
"""Gate-checked packaging of the H79-DCE final map.

Re-derives every preregistered gate from evidence/dce/:
- two-seed HOLDOUT-DTI beats the H33 fold-fair control (the current holdout
  best among promotable candidates) with paired CIs excluding zero;
- all leakage canaries are <= 0.90;
- the final-dot duplicate gate (shared tool, v4 amendments) is clear and complete;
- the cap fixed point converged with exactly 37,654 dots.

If any gate fails, the map is still written through the shared writer as a
research artifact whose file name ends in DO-NOT-SUBMIT and whose note states
the failure. It is never presented as a submission. The shared
gems57.submission_writer validates the on-disk TIFF and the single-TIFF ZIP in
both cases.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator      # noqa: E402
from gems57.grid import load_grid                      # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402

EV = ROOT / "evidence/dce"
BUDGET = 37654


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def gates():
    hold = {s: json.loads((EV / f"dce_holdout_seed{s}.json").read_text()) for s in (20, 30)}
    uniq = json.loads((EV / "uniqueness_final.json").read_text())
    build = json.loads((EV / "final_build.json").read_text())
    atrisk = json.loads((EV / "atrisk_build.json").read_text())
    g = {}
    g["canaries_all_le_0_90_both_seeds"] = all(
        h["leakage_canary"]["max_symmetric_auc"] <= 0.90 and h["leakage_canary"]["n_suspicious"] == 0
        for h in hold.values())
    g["beats_current_holdout_best_both_seeds"] = all(
        h["holdout"]["scores"]["candidate"]["dti"] > h["holdout"]["scores"]["h33_foldfair_control"]["dti"]
        for h in hold.values())
    g["paired_ci_vs_h33_excludes_zero_both_seeds"] = all(
        h["holdout"]["paired_differences"]["h33_foldfair_control"]["ci95"][0] > 0 for h in hold.values())
    g["paired_ci_vs_uniform_excludes_zero_both_seeds"] = all(
        h["holdout"]["paired_differences"]["uniform_control"]["ci95"][0] > 0 for h in hold.values())
    g["evaluator_version_pinned"] = all(h["evaluator_version"] == evaluator.VERSION for h in hold.values())
    g["final_rank_correlation_le_0_90"] = uniq["worst_spearman"] <= 0.90
    g["final_uniqueness_passed"] = uniq["passed"] is True
    g["final_uniqueness_complete"] = uniq["complete_comparison"] is True
    g["final_forward_overlap_le_0_70"] = uniq["worst_forward_overlap_3px"] <= 0.70
    g["beyond_chance_clear_on_vacuous"] = (
        uniq.get("worst_beyond_chance_among_vacuous") is None or
        uniq["worst_beyond_chance_among_vacuous"]["value"] <= uniq["worst_beyond_chance_among_vacuous"]["margin"])
    g["cap_fixed_point_converged"] = json.loads(
        (EV / "cap_convergence.json").read_text())["converged"] is True
    g["cap_fixed_point_no_post_holdout_additions"] = not json.loads(
        (EV / "cap_convergence.json").read_text())["additions"]
    g["dots_exactly_budget"] = build["n_dots"] == BUDGET
    g["surface_hash_verified_against_x1_receipt"] = json.loads(
        (EV / "surface_build.json").read_text())["surface_hash_matches_frozen_x1_receipt"] is True
    g["x1_reproduction_arm_present"] = all(
        "x1_topk_reproduction" in h["holdout"]["scores"] for h in hold.values())
    return g


def main():
    grid = load_grid(ROOT / "data/reference")
    g = gates()
    dots = np.load(ROOT / ".cache/dce/final_dots.npy")
    prediction = dots.astype(np.float32)
    hold = {s: json.loads((EV / f"dce_holdout_seed{s}.json").read_text()) for s in (20, 30)}

    all_passed = all(g.values())
    d = {s: hold[s]["holdout"]["scores"] for s in (20, 30)}
    dots_sha8 = hashlib.sha256(np.ascontiguousarray(prediction).tobytes()).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if all_passed:
        name = f"gems79-h79-dce-cover-37654dots-{stamp}-{dots_sha8}"
        note = (f"H79-DCE capped cover emission; HOLDOUT-DTI {d[20]['candidate']['dti']:.4f}/"
                f"{d[30]['candidate']['dti']:.4f} vs H33 {d[20]['h33_foldfair_control']['dti']:.4f}/"
                f"{d[30]['h33_foldfair_control']['dti']:.4f}; unique vs 986 comparable rasters")
    else:
        failed = [k for k, v in g.items() if not v]
        name = f"gems79-h79-dce-cover-37654dots-{stamp}-{dots_sha8}-DO-NOT-SUBMIT"
        note = f"H79-DCE research only; failed gates: {', '.join(failed)[:80]}"
    assert len(name) <= 140 and len(note) <= 140, (len(name), len(note))

    out_dir = ROOT / "docs/downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    # a re-run regenerates the same raster bytes from the frozen final dots;
    # remove the previous lane artifact so exactly one canonical pair remains
    for stale in out_dir.glob("gems79-h79-dce-cover-*"):
        stale.unlink()
    path = out_dir / (name + ".tif")
    write_submission(path, prediction, ROOT / "data/reference/sample_submission.tif",
                     grid.footprint, note=note, name=name, catalogue=grid.catalogue)
    receipt = json.loads(path.with_suffix(".json").read_text())
    gate_receipt = dict(
        lane="H79-DCE", generated_utc=datetime.now(timezone.utc).isoformat(),
        raster_sha256=sha(path), name=name, note=note, gates=g, all_passed=all_passed,
        failed_gates=[k for k, v in g.items() if not v])
    (EV / "dce_gates.json").write_text(json.dumps(gate_receipt, indent=2) + "\n")
    print(json.dumps(gate_receipt, indent=2))
    return 0 if all_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
