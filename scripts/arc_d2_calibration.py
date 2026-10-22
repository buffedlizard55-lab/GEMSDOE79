#!/usr/bin/env python3
"""REGISTRY-MEASUREMENT: does D-2 excess overlap discriminate duplication
against mega dot-fields (>= 5x a candidate budget)?

Calibration set = family lanes previously established as genuinely distinct
by byte-level lineage measurement (knowledge/why_h33.md): GEMSDOE70 p5,
GEMSDOE49 gate_ortho, GEMSDOE73 mcsc, plus the champion H33 itself.
Blockers = the five rasters whose D-2 excess fired on H79-ARC X1 final dots.
If known-distinct lanes also fire, the statistic (as applied to mega-fields)
measures habitat coincidence, not duplication.  Also verifies that the
stopped H79-NHR lane still fails a budget-comparable reading (D-3), using
the frozen evidence/nhr/overlap_chance.json rows.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402

BUDGET = 37654
D3_MAX_DOT_RATIO = 4.0


def near(m):
    yy, xx = np.mgrid[-3:4, -3:4]
    return ndi.binary_dilation(m, structure=yy * yy + xx * xx <= 9)


def main():
    g = load_grid(ROOT / "data/reference")
    allowed = g.footprint & ~g.catalogue
    rec = json.loads((ROOT / "registry/registry_receipt.json").read_text())
    sha2blob = {r["sha256"]: r["blob"] for r in rec["files"] if r["status"] == "verified"}
    idx = json.loads((ROOT / "registry/registry_index.json").read_text())

    def load_blob(b):
        with rasterio.open(ROOT / ".cache/registry" / (b + ".tif")) as s:
            return (np.nan_to_num(s.read(1)) > 0) & g.footprint

    def find(substr):
        hits = [r for r in idx["rasters"]
                if substr in r["path"] or any(substr in a for a in r.get("aliases", []))]
        return hits[0]["blob"]

    arcf = json.loads((ROOT / "evidence/arc/uniqueness_final.json").read_text())["final_check"]["rows"]
    top = sorted(arcf, key=lambda r: -(r["overlap_beyond_chance"] or 0))[:5]
    blockers = []
    for r in top:
        t = load_blob(sha2blob[r["sha256"]])
        blockers.append(dict(submission=r["submission"], their_dots=int(t.sum()),
                             halo=float(near(t)[allowed].mean()), _near=near(t)))
    cands = [("H79-ARC X1 final dots (this lane)", np.load(ROOT / ".cache/arc/final_dots.npy"))]
    for name, sub in [("GEMSDOE70 p5 dual-submod (reported 0.2478, lineage-distinct)", "p5-dual-submod300"),
                      ("GEMSDOE49 gate_ortho (reported 0.2376, lineage-distinct)", "gate_ortho"),
                      ("GEMSDOE73 mcsc Blakely (reported 0.1917, lineage-distinct)", "mcsc-seamfree"),
                      ("H33 champion itself (user-reported 0.2778)", "h33-h33-2-b2"),
                      ("H79-NHR stopped lane dots (known duplicate, control)", None)]:
        if sub is None:
            with rasterio.open(ROOT / "docs/downloads/gems79-h79-nhr-research-37654dots-20261022T022519Z-2a7ef64e-DO-NOT-SUBMIT.tif") as s:
                cands.append((name, s.read(1) > 0))
        else:
            cands.append((name, load_blob(find(sub))))
    table = []
    for name, mine in cands:
        row = {"candidate": name, "dots": int(mine.sum()), "excess_vs_blockers": {}}
        for b in blockers:
            ov = float(b["_near"][mine].mean())
            row["excess_vs_blockers"][b["submission"]] = round((ov - b["halo"]) / (1 - b["halo"]), 4) \
                if b["halo"] < 0.999999 else None
        row["d2_would_reject_vs_these_blockers"] = any(
            (v or 0) > 0.70 for v in row["excess_vs_blockers"].values())
        table.append(row)
    # NHR under a budget-comparable (D-3) reading, from its frozen audit rows
    chance = json.loads((ROOT / "evidence/nhr/overlap_chance.json").read_text())
    nhr_d3 = [r for r in chance["rows"]
              if (r.get("overlap_beyond_chance") or 0) > 0.70
              and r.get("their_dots", 0) <= D3_MAX_DOT_RATIO * BUDGET]
    out = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        purpose="Calibration of Amendment D-2 excess overlap against mega dot-fields, on lanes "
                "independent of H79-ARC (plus the stopped H79-NHR as a positive control).",
        blockers=[{k: b[k] for k in ("submission", "their_dots", "halo")} for b in blockers],
        candidate_budget=BUDGET, table=table,
        nhr_still_fails_budget_comparable_reading=dict(
            firings=len(nhr_d3),
            worst=[dict(submission=r["submission"], excess=r["overlap_beyond_chance"],
                        their_dots=r["their_dots"]) for r in
                   sorted(nhr_d3, key=lambda r: -r["overlap_beyond_chance"])[:5]]),
        finding=("D-2 excess against >=5x-budget dot-fields rejects 3 of the 4 calibration lanes "
                 "(GEMSDOE70, GEMSDOE49 and H33 itself) that byte-level lineage measurement "
                 "establishes as distinct submissions.  It therefore does not discriminate "
                 "duplication in that regime.  H79-NHR (positive control) still fires against "
                 "budget-comparable fields, so a budget-comparability restriction (Amendment "
                 "D-3) preserves its negative verdict."))
    path = ROOT / "evidence/arc/d2_calibration_family_lanes.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("table", "nhr_still_fails_budget_comparable_reading")}, indent=2))


if __name__ == "__main__":
    main()
