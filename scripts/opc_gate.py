#!/usr/bin/env python3
"""Independent, read-only re-check of the G79-OPC run card (gates G1-G5).

Every value is re-derived from the evidence files and the TIFF bytes. The card is not trusted.
Exit 0 means every gate passes and the lane is OK to submit. Exit 2 means NO (the normal state for this lane).
This script never sets ok_to_submit for the project; only scripts/select_submission.py does that.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]

THVC = {20: 0.1905, 30: 0.1944}
BEST_MEAN = 0.1963


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def evaluate() -> dict:
    card = json.loads((ROOT / "run_card_opc.json").read_text())
    pre = ROOT / "registry/preregistration_g79_opc.json"
    pre_ok = sha(pre) == (ROOT / "registry/preregistration_g79_opc.sha256").read_text().split()[0]
    s = {k: json.loads((ROOT / f"evidence/opc/seed{k}.json").read_text()) for k in (20, 30)}
    dti = {k: s[k]["official_evaluate_all"]["scores"]["EXP-OPC-2_full"]["dti"] for k in s}
    canary = max(s[k]["canary"]["max_symmetric_auc"] for k in s)
    nov = [json.loads((ROOT / f"evidence/opc/novelty_{p}.json").read_text())
           for p in ("pre_placement_surface", "final_dots")]
    tif = ROOT / card["raster"]["path"]
    from validate_submission import validate_path
    fmt = validate_path(tif)
    from gems79.portal_spec import validate_portal_file
    tpl = ROOT / "data/reference/sample_submission.tif"
    official = [validate_portal_file(str(f), str(tpl)) for f in (tif, ROOT / card["raster"]["zip"])]
    g = {
        "G0_preregistration_sha_intact": pre_ok,
        "G1_format_validator": bool(fmt["format_passed"]) and sha(tif) == card["raster"]["sha256"],
        "G1b_official_portal_spec_R1_R8": all(o["ok"] for o in official),
        "G2_canary_le_0.90": canary <= 0.90,
        "G3_beats_holdout_best": dti[20] > THVC[20] and dti[30] > THVC[30] and (dti[20] + dti[30]) / 2 > BEST_MEAN,
        "G4_novelty_D3_both_phases": all(n.get("unique_under_D3") is True and n["complete_accessible_scan"] for n in nov),
    }
    g["G5_card_agrees"] = (card["ok_to_submit"] == all(g.values())
                           and card["submission_name"].endswith("-DO-NOT-SUBMIT") != all(g.values())
                           and len(card["note"]) <= 140)
    ok = all(g.values()) and card["ok_to_submit"] is True
    return dict(gates=g, official_failed_rules=sorted({x for o in official for x in o["failed_rules"]}), holdout_dti=dti, two_seed_mean=(dti[20] + dti[30]) / 2, canary_max=canary,
                tif=card["raster"]["path"], ok_to_download=bool(g["G1_format_validator"]),
                ok_to_submit=ok, verdict=card["verdict"])


def main() -> int:
    r = evaluate()
    print(json.dumps(r, indent=1))
    print(f"OK TO DOWNLOAD (research): {'YES' if r['ok_to_download'] else 'NO'}")
    print(f"OK TO SUBMIT: {'YES' if r['ok_to_submit'] else 'NO'}")
    # A NO verdict is a valid result; exit 2 only signals NO to shell callers.
    # Inconsistency (G5 false) is an error: exit 1.
    if not r["gates"]["G5_card_agrees"]:
        return 1
    return 0 if r["ok_to_submit"] else 2


if __name__ == "__main__":
    sys.exit(main())
