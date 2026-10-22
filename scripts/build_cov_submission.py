#!/usr/bin/env python3
"""Gate-checked packaging of the H79-COV final map (experiment C1).

Re-derives every preregistered gate from evidence/cov/:
- two-seed HOLDOUT-DTI beats the current holdout best (h33_foldfair_control);
- paired CI vs uniform excludes 0 on both seeds;
- all leakage canaries <= 0.90;
- duplicate gate clear on surface AND final dots: Spearman <= 0.90 vs every
  registry raster; forward 3 px overlap <= 0.70 vs every discriminating
  raster; exact-cell overlap <= 0.70 vs every non-discriminating raster
  (Amendment B1, preregistered; literal readings published in the evidence).

If any gate fails, the map is still written through the shared writer as a
research artifact whose file name ends in DO-NOT-SUBMIT. The shared
gems57.submission_writer validates the on-disk TIFF and single-TIFF ZIP:
single band float32, EPSG:32611, sample transform, all finite, values in
[0,1] (the portal's "Predicted values must be in range [0, 1]" check),
no mass outside footprint or on the catalogue. It never clips/repairs.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as evaluator      # noqa: E402
from gems57.grid import load_grid                      # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402

EV = ROOT / "evidence/cov"
BUDGET = 37654


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def gates():
    hold = {s: json.loads((EV / f"c1_holdout_seed{s}.json").read_text()) for s in (20, 30)}
    uniq = {p: json.loads((EV / f"uniqueness_{p}.json").read_text()) for p in ("surface", "final")}
    build = json.loads((EV / "c1_final_build.json").read_text())
    g = {}
    g["canaries_all_le_0_90_both_seeds"] = all(
        h["leakage_canary"]["max_symmetric_auc"] <= 0.90 and h["leakage_canary"]["n_suspicious"] == 0
        for h in hold.values())
    g["beats_current_holdout_best_both_seeds"] = all(
        h["holdout"]["scores"]["candidate"]["dti"] > h["holdout"]["scores"]["h33_foldfair_control"]["dti"]
        for h in hold.values())
    g["paired_ci_vs_uniform_excludes_zero_both_seeds"] = all(
        h["holdout"]["paired_differences"]["uniform_control"]["ci95"][0] > 0 for h in hold.values())
    g["evaluator_version_pinned"] = all(h["evaluator_version"] == evaluator.VERSION for h in hold.values())
    g["surface_rank_correlation_le_0_90"] = uniq["surface"]["worst_spearman"] <= 0.90
    g["final_rank_correlation_le_0_90"] = uniq["final"]["worst_spearman"] <= 0.90
    g["final_dot_uniqueness_B1_passed"] = uniq["final"]["passed"] is True
    dots = np.load(ROOT / ".cache/cov/final_dots.npy")
    g["final_dots_match_audited_bytes"] = hashlib.sha256(dots.tobytes()).hexdigest() == uniq["final"]["dots_sha256"] == build["dots_sha256"]
    g["exact_budget"] = int(dots.sum()) == BUDGET
    return g, hold, uniq, build, dots


def main():
    g, hold, uniq, build, dots = gates()
    passed = all(g.values())
    print(json.dumps(g, indent=2))
    if not passed:
        print("A preregistered gate failed: writing a DO-NOT-SUBMIT research artifact only.")
    grid = load_grid(ROOT / "data/reference")
    pred = np.zeros(grid.shape, np.float32)
    pred[dots & grid.footprint & ~grid.catalogue] = 1.0
    assert int(pred.sum()) == BUDGET
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s20 = hold[20]["holdout"]["scores"]; s30 = hold[30]["holdout"]["scores"]
    hd = (f"HOLDOUT-DTI {s20['candidate']['dti']:.3f}/{s30['candidate']['dti']:.3f} vs H33 "
          f"{s20['h33_foldfair_control']['dti']:.3f}/{s30['h33_foldfair_control']['dti']:.3f}")
    failed = [k for k, v in g.items() if not v]
    if passed:
        name = f"gems79-h79-cov-anti-cover-37654dots-{stamp}-{build['dots_sha256'][:8]}-zeros"
        note = f"H79-COV antithetic+covered basement-step, 37654 dots s3, catalogue-free; {hd}"
    else:
        name = f"gems79-h79-cov-research-37654dots-{stamp}-{build['dots_sha256'][:8]}-DO-NOT-SUBMIT"
        note = f"H79-COV research only; {hd}; FAILED: {','.join(failed)[:40]}"
    assert len(note) <= 140, (len(note), note)
    assert len(name) <= 140
    path = ROOT / "docs/downloads" / (name + ".tif")
    receipt = write_submission(path, pred, ROOT / "data/reference/sample_submission.tif", grid.footprint,
                               note=note, name=name, catalogue=grid.catalogue,
                               metadata=dict(lane="H79-COV", experiment="C1",
                                             dots_sha256=build["dots_sha256"],
                                             surface_sha256=build["surface_sha256"]))
    print(json.dumps({"written": str(path.relative_to(ROOT)), "sha256": sha(path), "note": note,
                      "note_chars": len(note), "receipt_keys": sorted(receipt) if isinstance(receipt, dict) else str(receipt)[:200]}, indent=2))
    (EV / "c1_gates.json").write_text(json.dumps(
        dict(gates=g, all_passed=passed, name=name, note=note, note_chars=len(note),
             raster_sha256=sha(path)), indent=2) + "\n")


if __name__ == "__main__":
    from gems79.lifecycle import LaneClosedError, require_open_lane
    try:
        require_open_lane(ROOT, 'H79-COV')
    except LaneClosedError as _exc:
        print(str(_exc), file=sys.stderr)
        raise SystemExit(2)
    main()
