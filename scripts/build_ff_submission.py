#!/usr/bin/env python3
"""H79-FF1 packaging: re-derive gates; shared writer only. Any gate failure =>
DO-NOT-SUBMIT research artifact under archive/g79_ff1/downloads/ (never docs/downloads,
whose single canonical pair belongs to the selector-owned card)."""
from __future__ import annotations
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"vendor"), str(ROOT/"scripts")]
from gems57.grid import load_grid
from gems57.submission_writer import write_submission
EV = ROOT/"evidence/ff1"; BUDGET = 37654
def main():
    from gems79.lifecycle import enforce_open_lane
    enforce_open_lane(
        ROOT,
        "H79-FF1",
        reason="H79-FF1 is stopped and archived (HOLDOUT-DTI 0.0250/0.0249 < uniform; surface duplicate).",
    )
    hold = {s: json.loads((EV/f"x1_holdout_seed{s}.json").read_text()) for s in (20,30)}
    uniq_s = json.loads((EV/"uniqueness_surface.json").read_text())
    inf = json.loads((EV/"informative_overlap.json").read_text())
    dots = np.load(ROOT/".cache/ff1/final_dots.npy")
    s20, s30 = (hold[s]["holdout"]["scores"] for s in (20,30))
    gates = dict(
      canary_le_0_90_both_seeds=all(hold[s]["leakage_canary"]["max_symmetric_auc"] <= 0.90 for s in (20,30)),
      beats_h33_control_both_seeds=all(hold[s]["holdout"]["scores"]["candidate"]["dti"] > hold[s]["holdout"]["scores"]["h33_foldfair_control"]["dti"] for s in (20,30)),
      surface_spearman_le_0_90=uniq_s["worst_spearman"] <= 0.90,
      informative_dotfield_overlap_le_0_70=inf["final"]["n_gt_0_70"] == 0,
      literal_gate_note="literal shared gate flags space-filling plateau rasters (IR-79-53); recorded, not waived",
      exact_budget=int(dots.sum()) == BUDGET)
    passed = all(v is True for k, v in gates.items() if k != "literal_gate_note")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha_dots = hashlib.sha256(dots.tobytes()).hexdigest()
    name = f"gems79-h79ff1-farfield1-3km-37654dots-{stamp}-{sha_dots[:8]}" + ("" if passed else "-DO-NOT-SUBMIT")
    note = f"H79-FF1 far-field 1-3km band; HOLDOUT-DTI {s20['candidate']['dti']:.4f}/{s30['candidate']['dti']:.4f} vs H33 {s20['h33_foldfair_control']['dti']:.4f}/{s30['h33_foldfair_control']['dti']:.4f}; verdict negative"[:140]
    grid = load_grid(ROOT/"data/reference")
    pred = np.zeros(grid.shape, np.float32); pred[dots & grid.footprint & ~grid.catalogue] = 1.0
    assert int(pred.sum()) == BUDGET
    outdir = ROOT/"archive/g79_ff1/downloads" if not passed else ROOT/"docs/downloads"
    path = outdir/f"{name}.tif"
    receipt = write_submission(path, pred, ROOT/"data/reference/sample_submission.tif", grid.footprint,
                               note=note, name=name, catalogue=grid.catalogue,
                               metadata=dict(lane="H79-FF1", gates=gates, ok_to_submit=False))
    card = dict(schema_version="gems79-run-card-v2", lane="H79-FF1", generated_utc=datetime.now(timezone.utc).isoformat(),
      hypothesis=json.loads((ROOT/"registry/preregistration_ff1.json").read_text())["hypothesis"],
      mechanism=json.loads((ROOT/"registry/preregistration_ff1.json").read_text())["mechanism"],
      named_non_fault_process="Pluvial Lake Lahontan shoreline/terrace risers and incised channel banks",
      holdout_dti=dict(evidence_class="HOLDOUT-DTI", evaluator_version=hold[20]["evaluator_version"],
        per_seed={f"seed_{s}": dict(candidate=hold[s]["holdout"]["scores"]["candidate"], h33_foldfair_control=hold[s]["holdout"]["scores"]["h33_foldfair_control"],
          uniform_control=hold[s]["holdout"]["scores"]["uniform_control"], unrestricted_nhr_reference=hold[s]["holdout"]["scores"]["unrestricted_nhr_reference"],
          withheld_positive_pixels=sum(f["withheld_truth"] for f in hold[s]["folds"])) for s in (20,30)}),
      leakage_canary=dict(per_seed={f"seed_{s}": hold[s]["leakage_canary"]["max_symmetric_auc"] for s in (20,30)}, threshold=0.90, passed=gates["canary_le_0_90_both_seeds"]),
      uniqueness=dict(surface_worst_spearman=uniq_s["worst_spearman"], literal_gate_worst_overlap=uniq_s["worst_forward_overlap_3px"],
        literal_gate_flag="space-filling plateau raster (IR-79-53)", informative_final=inf["final"], informative_provisional=inf["provisional"]),
      gates=gates, raster_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), dots_sha256=sha_dots,
      validator=receipt, submission_name=name, submission_note=note, note_chars=len(note),
      ok_to_submit=False, verdict="negative",
      verdict_reason="Far-field band candidate HOLDOUT-DTI 0.0944/0.0931 does not beat H33 fold-fair control 0.0961/0.0989 on either seed; band costs ~0.049-0.059 vs unrestricted NHR surface. Do not upload; 0 weekly slots used.")
    (ROOT/"run_card_ff1.json").write_text(json.dumps(card, indent=2, default=float)+"\n")
    (outdir/f"{name}.run_card.json").write_text(json.dumps(card, indent=2, default=float)+"\n")
    print(json.dumps(dict(name=name, passed_all_gates=passed, gates=gates, path=str(path), raster_sha256=card["raster_sha256"]), indent=2))
if __name__ == "__main__": main()
