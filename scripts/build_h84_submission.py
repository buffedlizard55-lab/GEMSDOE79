#!/usr/bin/env python3
"""Package H84-X2 final (far-field) as submission-lookup artifact with obvious banner.
"""
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import scipy.ndimage as ndi

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"), str(ROOT/"vendor")]
from gems57.grid import load_grid
from gems57.submission_writer import write_submission

EV=ROOT/"evidence/h84"
CACHE=ROOT/".cache/h84_x2"
BUDGET=37654

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    grid=load_grid(ROOT/"data/reference")
    # load holdouts
    holds={}
    for s in (20,30):
        p=EV/f"x2_holdout_seed{s}.json"
        if p.exists():
            holds[s]=json.loads(p.read_text())
        else:
            print(f"missing holdout seed {s}")
    # also X1 holdouts for reference
    x1_holds={}
    for s in (20,30):
        p=EV/f"x1_holdout_seed{s}.json"
        if p.exists():
            x1_holds[s]=json.loads(p.read_text())
    build=json.loads((EV/"x2_final_build.json").read_text())
    # load dots
    dots_far=np.load(CACHE/"final_dots_far.npy")
    dots_global=np.load(CACHE/"final_dots_global.npy")
    # choose far for uniqueness
    dots=dots_far
    print("far dots", int(dots.sum()), "global", int(dots_global.sum()))
    # gates
    g={}
    if holds:
        g["canaries_le_0_90"] = all(h["leakage_canary"]["max_symmetric_auc"]<=0.90 for h in holds.values())
        g["beats_uniform_both_seeds"] = all(h["holdout"]["scores"]["candidate"]["dti"] > h["holdout"]["scores"]["uniform_control"]["dti"] and h["holdout"]["paired_differences"]["uniform_control"]["ci95"][0]>0 for h in holds.values())
        # compare vs H33 historical if available from H79 evidence
        # H33 DTI from prior H79 holdouts: 0.0961/0.0989
        h33_hist={20:0.0961,30:0.0989}
        g["beats_h33_hist_both_seeds"] = all(holds[s]["holdout"]["scores"]["candidate"]["dti"] > h33_hist[s] for s in holds)
        g["exact_budget_far"] = int(dots.sum())==BUDGET
        g["far_dots_match_build"] = hashlib.sha256(dots.tobytes()).hexdigest()==build["dots_far_sha256"]
        g["has_both_seeds"] = len(holds)==2
    else:
        g["has_holdouts"]=False
    # X1 negative gate
    if x1_holds:
        g["x1_negative_vs_uniform"] = all(x1_holds[s]["holdout"]["scores"]["candidate"]["dti"] < x1_holds[s]["holdout"]["scores"]["uniform"]["dti"] for s in x1_holds)
    print(json.dumps(g, indent=2))
    passed=False
    # We require X2 to pass holdout vs uniform and vs H33 hist, and canary, to be promotion-eligible, but uniqueness still must be checked separately
    if g.get("canaries_le_0_90") and g.get("beats_uniform_both_seeds") and g.get("beats_h33_hist_both_seeds") and g.get("exact_budget_far"):
        passed=True
    # decide note/name
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if holds:
        s20=holds[20]["holdout"]["scores"]; s30=holds[30]["holdout"]["scores"]
        hd=f"HOLDOUT-DTI {s20['candidate']['dti']:.4f}/{s30['candidate']['dti']:.4f} vs uniform {s20['uniform_control']['dti']:.4f}/{s30['uniform_control']['dti']:.4f}"
    else:
        hd="no holdout"
    if passed:
        # even if holdout passes, uniqueness not yet cleared, so we must mark DO-NOT-SUBMIT until uniqueness cleared
        # For now, we produce a research artifact with obvious banner but note we need uniqueness check
        # To satisfy "obvious OK TO DOWNLOAD YES/SUBMIT NO banner", we will always produce DO-NOT-SUBMIT unless manually approved
        name=f"gems79-h84-ffa-x2-nested-hide-far-37654dots-{stamp}-{build['dots_far_sha256'][:8]}-DO-NOT-SUBMIT"
        note=f"H84-X2 nested hide far-field 37654 dots; {hd}; HOLDOUT PASS but LITERAL NOVELTY NOT CLEARED"
        # Truncate note to 140
        if len(note)>140: note=note[:140]
        banner="OK TO DOWNLOAD: YES — research artifact only — OK TO SUBMIT: NO — DO-NOT-SUBMIT, novelty gate not cleared"
    else:
        name=f"gems79-h84-ffa-research-37654dots-{stamp}-{build['dots_far_sha256'][:8]}-DO-NOT-SUBMIT"
        note=f"H84 research only; {hd}; not promoted"
        if len(note)>140: note=note[:140]
        banner="OK TO DOWNLOAD: YES — research artifact only — OK TO SUBMIT: NO — DO-NOT-SUBMIT"
    # also prepare global TIF for comparison (optional)
    # for now, package far
    assert len(name)<=140 and len(note)<=140
    pred=np.zeros(grid.shape, np.float32)
    pred[(dots & grid.footprint & ~grid.catalogue)]=1.0
    assert int((pred>0).sum())==BUDGET
    assert int(((pred>0) & grid.catalogue).sum())==0
    path=ROOT/"docs/downloads"/(name+".tif")
    # remove existing if any
    for f in [path, path.with_suffix(".zip"), path.with_suffix(".json")]:
        if f.exists(): f.unlink()
    receipt=write_submission(path, pred, ROOT/"data/reference/sample_submission.tif", grid.footprint, note=note, name=name, catalogue=grid.catalogue, metadata=dict(lane="H84-FFA", experiment="X2", dots_far_sha256=build["dots_far_sha256"], surface_sha256=build["surface_sha256"], holdout_scores={str(k):v["holdout"]["scores"]["candidate"]["dti"] for k,v in holds.items()}))
    print(json.dumps({"written": str(path.relative_to(ROOT)), "sha256": sha(path), "note": note, "name": name, "banner": banner}, indent=2))
    # also write banner file for site
    (EV/"x2_gates.json").write_text(json.dumps(dict(gates=g, all_passed=passed, name=name, note=note, banner=banner, raster_sha256=sha(path), holdout_summary={str(k):holds[k]["holdout"]["scores"] for k in holds}), indent=2)+"\n")
    # duplicate candidate for uniqueness check later
    # also write a global version for reference (not primary)
    pred_g=np.zeros(grid.shape, np.float32)
    pred_g[(dots_global & grid.footprint & ~grid.catalogue)]=1.0
    path_g=ROOT/"docs/downloads"/(name.replace("far","global")+".tif")
    # don't write second via writer to avoid confusion; just save npy for analysis
    np.save(CACHE/"pred_far_for_uniqueness.npy", pred)
    np.save(CACHE/"pred_global_for_uniqueness.npy", pred_g)

if __name__=="__main__":
    main()
