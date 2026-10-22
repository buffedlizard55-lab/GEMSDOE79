#!/usr/bin/env python3
"""Gate-checked packaging of the H79-NHR final map.

Refuses to repackage a terminal canonical lane. For an open run,
re-derives every preregistered gate from evidence/nhr/:
- two-seed HOLDOUT-DTI beats the current holdout best (h33_foldfair_control);
- the paired CI vs uniform excludes 0;
- all leakage canaries are <= 0.90;
- the protocol's literal duplicate rule (rho > 0.90, or > 70 % of dots within 3 px of
  one registry raster's dots) is clear on the surface AND on the final dots.

The duplicate rule is evaluated against every comparable registry raster in
evidence/nhr/overlap_chance.json and evidence/nhr/uniqueness_{surface,final}.json.

If any gate fails, the map is still written through the shared writer as a
research artifact whose file name ends in DO-NOT-SUBMIT and whose note states the failure. It
is never presented as a submission. The shared gems57.submission_writer validates the
on-disk TIFF and the single-TIFF ZIP in both cases.
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
from gems79.lifecycle import LaneClosedError, require_open_lane
from gems57 import evaluate_holdout as evaluator      # noqa: E402
from gems57.grid import load_grid                      # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402

EV = ROOT / "evidence/nhr"
BUDGET = 37654


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def gates():
    hold = {s: json.loads((EV / f"x1_holdout_seed{s}.json").read_text()) for s in (20, 30)}
    uniq = {p: json.loads((EV / f"uniqueness_{p}.json").read_text()) for p in ("surface", "final")}
    build = json.loads((EV / "x1_final_build.json").read_text())
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
    chance = json.loads((EV / "overlap_chance.json").read_text())
    flagged = [r for r in chance["rows"] if r["overlap_candidate"] > 0.70]
    g["surface_rank_correlation_le_0_90"] = uniq["surface"]["worst_spearman"] <= 0.90
    g["final_rank_correlation_le_0_90"] = uniq["final"]["worst_spearman"] <= 0.90
    g["surface_uniqueness_passed"] = uniq["surface"]["passed"] is True
    g["final_dot_uniqueness_passed"] = uniq["final"]["passed"] is True and not flagged
    dots = np.load(ROOT / ".cache/nhr/final_dots.npy")
    g["final_dots_match_audited_bytes"] = hashlib.sha256(dots.tobytes()).hexdigest() == uniq["final"]["dots_sha256"] == build["dots_sha256"]
    g["exact_budget"] = int(dots.sum()) == BUDGET
    return g, hold, uniq, build, dots


def main():
    require_open_lane(ROOT, "H79-NHR")
    g, hold, uniq, build, dots = gates()
    passed = all(g.values())
    if not passed:
        print(json.dumps(g, indent=2))
        print("A preregistered gate failed: writing a DO-NOT-SUBMIT research artifact only.")
    chance = json.loads((EV / "overlap_chance.json").read_text())
    grid = load_grid(ROOT / "data/reference")
    pred = np.zeros(grid.shape, np.float32)
    pred[dots & grid.footprint & ~grid.catalogue] = 1.0
    assert int(pred.sum()) == BUDGET
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s20 = hold[20]["holdout"]["scores"]; s30 = hold[30]["holdout"]["scores"]
    hd = (f"HOLDOUT-DTI {s20['candidate']['dti']:.3f}/{s30['candidate']['dti']:.3f} vs H33 "
          f"{s20['h33_foldfair_control']['dti']:.3f}/{s30['h33_foldfair_control']['dti']:.3f}")
    if passed:
        name = f"gems79-h79-nhr-nested-hide-recover-37654dots-{stamp}-{build['dots_sha256'][:8]}-zeros"
        note = f"H79-NHR nested hide-recover HGB kernel target, 37654 dots s3; {hd}"
    else:
        worst = chance["worst_candidate_overlap_vs_informative_rasters"]
        name = f"gems79-h79-nhr-research-37654dots-{stamp}-{build['dots_sha256'][:8]}-DO-NOT-SUBMIT"
        note = f"H79-NHR research only; {hd}; DUPLICATE: {worst['overlap_candidate']:.2f} of dots within 3px of a registry raster"
    assert len(note) <= 140 and len(name) <= 140
    path = ROOT / "docs/downloads" / (name + ".tif")
    receipt = write_submission(path, pred, ROOT / "data/reference/sample_submission.tif", grid.footprint,
                               note=note, name=name, catalogue=grid.catalogue,
                               metadata=dict(lane="H79-NHR", experiment="X1",
                                             dots_sha256=build["dots_sha256"],
                                             surface_sha256=build["surface_sha256"]))
    print(json.dumps({"written": str(path.relative_to(ROOT)), "sha256": sha(path), "note": note,
                      "note_chars": len(note)}, indent=2))
    (EV / "x1_gates.json").write_text(json.dumps(dict(gates=g, all_passed=passed, name=name, note=note,
                                                       raster_sha256=sha(path)), indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except LaneClosedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
