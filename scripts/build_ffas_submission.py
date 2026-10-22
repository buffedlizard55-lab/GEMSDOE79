#!/usr/bin/env python3
"""Gate-checked packaging of the H79-FFAS final map through the shared writer."""
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

EV = ROOT / "evidence/ffas"
BUDGET = 37654


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def gates():
    hold = {s: json.loads((EV / f"x1_holdout_seed{s}.json").read_text()) for s in (20, 30)}
    uniq = {p: json.loads((EV / f"uniqueness_{p}.json").read_text()) for p in ("surface", "final")}
    build = json.loads((EV / "x1_final_build.json").read_text())
    chance = json.loads((EV / "overlap_chance.json").read_text())
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
    informative_flagged = [r for r in chance["rows"]
                           if r["overlap_candidate"] > 0.70 and r["halo_coverage"] <= 0.70]
    g["surface_rank_correlation_le_0_90"] = uniq["surface"]["worst_spearman"] <= 0.90
    g["final_rank_correlation_le_0_90"] = uniq["final"]["worst_spearman"] <= 0.90
    g["surface_uniqueness_passed"] = uniq["surface"]["passed"] is True
    g["final_dot_uniqueness_passed"] = uniq["final"]["passed"] is True and not informative_flagged
    dots = np.load(ROOT / ".cache/ffas/final_dots.npy")
    g["final_dots_match_audited_bytes"] = (
        hashlib.sha256(dots.tobytes()).hexdigest() == uniq["final"]["dots_sha256"] == build["dots_sha256"])
    g["exact_budget"] = int(dots.sum()) == BUDGET
    return g, hold, uniq, build, dots, chance, informative_flagged


def main():
    g, hold, uniq, build, dots, chance, informative_flagged = gates()
    passed = all(g.values())
    if not passed:
        print(json.dumps(g, indent=2))
        print("A preregistered gate failed: writing a DO-NOT-SUBMIT research artifact only.")
    grid = load_grid(ROOT / "data/reference")
    pred = np.zeros(grid.shape, np.float32)
    pred[dots & grid.footprint & ~grid.catalogue] = 1.0
    assert int(pred.sum()) == BUDGET
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s20 = hold[20]["holdout"]["scores"]; s30 = hold[30]["holdout"]["scores"]
    short = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    if passed:
        name = f"gems79-h79-ffas-37654dots-{stamp}-{short}"
        note = (f"H79-FFAS antislope farfield; HOLDOUT-DTI {s20['candidate']['dti']:.3f}/"
                f"{s30['candidate']['dti']:.3f} vs H33 {s20['h33_foldfair_control']['dti']:.3f}/"
                f"{s30['h33_foldfair_control']['dti']:.3f}")
    else:
        name = f"gems79-h79-ffas-research-37654dots-{stamp}-{short}-DO-NOT-SUBMIT"
        failed = [k for k, v in g.items() if not v]
        note = (f"H79-FFAS research only; HOLDOUT-DTI {s20['candidate']['dti']:.3f}/"
                f"{s30['candidate']['dti']:.3f}; FAIL {','.join(failed)[:60]}")
    note = note[:140]
    dest = ROOT / "docs/downloads" / (name + ".tif")
    dest.parent.mkdir(parents=True, exist_ok=True)
    receipt = write_submission(
        dest, pred, ROOT / "data/reference/sample_submission.tif", grid.footprint,
        note=note, name=name, catalogue=grid.catalogue,
        metadata={"lane": "H79-FFAS", "gates": g, "passed": passed})
    gate_receipt = dict(
        schema_version=1, lane="H79-FFAS", experiment="X1",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        name=name, note=note, raster_sha256=receipt["sha256"],
        zip_sha256=receipt["zip_sha256"], all_passed=passed, gates=g,
        n_informative_overlap_gt_070=len(informative_flagged),
        writer=receipt["file"],
    )
    (EV / "x1_gates.json").write_text(json.dumps(gate_receipt, indent=2, default=float) + "\n")
    print(json.dumps({"name": name, "sha256": receipt["sha256"], "all_passed": passed,
                      "note_chars": len(note)}, indent=2))


if __name__ == "__main__":
    main()
