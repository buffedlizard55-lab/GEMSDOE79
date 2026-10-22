#!/usr/bin/env python3
"""Automated OK-TO-DOWNLOAD / OK-TO-SUBMIT decision for lane G79B-SDPT.

No human inspection: re-reads run_card_g79b.json, recomputes the TIFF
SHA-256 from disk, re-runs the shared gems57 format validator on the actual
bytes, and re-checks every preregistered gate (G1-G5). Exit 0 = promote
(project gates pass; the owner/selector may spend a slot), 2 = negative.
Organizer acceptance and account weekly capacity can only be known on the
DrivenData submission page and are never claimed here. Fails closed on any
missing/malformed evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))


def decide(root=ROOT):
    root = Path(root)
    blockers = []
    card = {}
    try:
        card = json.loads((root / "run_card_g79b.json").read_text())
        if not isinstance(card, dict):
            raise ValueError("run card not an object")
    except Exception as e:
        return {"ok_to_download": False, "ok_to_submit": False, "verdict": "negative",
                "blockers": [f"run_card_unreadable:{type(e).__name__}"],
                "human_inspection_required": False, "organizer_acceptance_established": False}

    name = card.get("submission_name", "")
    # Lane archived under the concurrent-lane quarantine layout on merge;
    # the canonical docs/downloads artifact belongs to G79-THVC.
    tif = root / "archive" / "g79b_sdpt_67557396" / "downloads" / f"{name}.tif"
    zf = tif.with_suffix(".zip")
    sha_ok = fmt_ok = zip_ok = False
    vr = None
    if not tif.exists():
        blockers.append("submission_tif_missing")
    else:
        actual = hashlib.sha256(tif.read_bytes()).hexdigest()
        sha_ok = actual == card.get("raster_sha256")
        if not sha_ok:
            blockers.append("raster_bytes_do_not_match_run_card")
        try:
            from gems57 import validate as V
            from gems79b import data as D
            g = D.load_grid()
            vr = V.validate(tif, g.footprint, g.catalogue)
            fmt_ok = bool(vr["all_checks_passed"] and vr["meta"]["nodata"] is None
                          and vr["emitted_positive_pixels"] == 37654
                          and vr["min"] >= 0.0 and vr["max"] <= 1.0 and vr["n_nan"] == 0)
            if not fmt_ok:
                blockers.append("format_validator_failed")
        except Exception as e:
            blockers.append(f"format_validator_error:{type(e).__name__}")
        try:
            with zipfile.ZipFile(zf) as z:
                zip_ok = bool(z.namelist() == [tif.name]
                              and hashlib.sha256(z.read(tif.name)).hexdigest() == card.get("raster_sha256"))
            if not zip_ok:
                blockers.append("zip_roundtrip_failed")
        except Exception:
            blockers.append("zip_missing_or_unreadable")

    gates = card.get("gates", {})
    for gname, blocker in [("G1_canary_le_0.90", "leakage_canary_not_cleared"),
                           ("G2_beats_random_CI", "holdout_not_above_random"),
                           ("G3_beats_current_holdout_best_both_seeds_unconstrained", "current_holdout_best_not_beaten_unconstrained"),
                           ("G4_registry_uniqueness_surface_and_final", "registry_uniqueness_not_cleared"),
                           ("G5_format_validator", "card_format_gate_false"),
                           ("E2_capped_emission_still_beats_control_both_seeds", "capped_emission_below_control_E2")]:
        if gates.get(gname) is not True:
            blockers.append(blocker)
    if card.get("verdict") != "promote":
        blockers.append("card_verdict_not_promote")
    if card.get("ok_to_submit") is not True:
        blockers.append("card_ok_to_submit_not_true")

    submit = not blockers
    return {
        "lane": "G79B-SDPT",
        "file": f"archive/g79b_sdpt_67557396/downloads/{name}.tif",
        "zip": f"archive/g79b_sdpt_67557396/downloads/{name}.zip",
        "sha256": card.get("raster_sha256"), "sha_matches_disk": sha_ok,
        "submission_name": name, "note": card.get("note"), "note_chars": card.get("note_chars"),
        "ok_to_download": bool(sha_ok and fmt_ok), "ok_to_submit": submit,
        "verdict": "promote" if submit else "negative", "blockers": blockers,
        "gates": gates, "zip_ok": zip_ok,
        "human_inspection_required": False,
        "organizer_acceptance_established": False,
        "scope": ("Project gates only (format + leakage canary + hide-and-recover holdout + "
                  "992-raster registry uniqueness). Weekly slot capacity and portal acceptance "
                  "are visible only on the signed-in DrivenData submission page."),
    }


def main():
    r = decide()
    print(json.dumps(r, indent=2, allow_nan=False))
    return 0 if r["ok_to_submit"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
